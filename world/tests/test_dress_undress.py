"""Tests for the third-party clothing verbs (#307, PR-H3).

Two new commands surface third-party clothing manipulation:

* ``dress <target> in <item>`` — put clothing on someone / something
* ``undress <target> [<item>]`` — remove clothing from same

Both gate on:

* Severed appendage (Appendage typeclass)
* Unconscious character (medical_state.is_unconscious())
* Dead character (medical_state.is_dead())

Conscious targets are rejected with a message hinting at the
future trust/consent layer.

This module exercises the permission helper plus the sever
pipeline's worn-items carry-forward.  Full Command.func()
integration tests require Evennia search infrastructure and are
covered separately via the live suite.

Run via::

    evennia test world.tests.test_dress_undress
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from commands.CmdClothing import _can_third_party_clothing


# ---------------------------------------------------------------------
# Permission gate
# ---------------------------------------------------------------------


class _MedicalState:
    """Minimal medical-state stub with ``is_dead`` / ``is_unconscious``
    callable surfaces."""

    def __init__(self, dead=False, unconscious=False):
        self._dead = dead
        self._unconscious = unconscious

    def is_dead(self):
        return self._dead

    def is_unconscious(self):
        return self._unconscious


def _conscious_char():
    char = SimpleNamespace(key="bob")
    char.medical_state = _MedicalState(dead=False, unconscious=False)
    return char


def _unconscious_char():
    char = SimpleNamespace(key="bob")
    char.medical_state = _MedicalState(unconscious=True)
    return char


def _dead_char():
    char = SimpleNamespace(key="bob")
    char.medical_state = _MedicalState(dead=True)
    return char


def _no_medical_target():
    """Random object with no medical_state — e.g. a room or generic
    item.  Should be rejected for safety."""
    return SimpleNamespace(key="rock")


class PermissionGate(TestCase):
    """The gate now rides world/consent.py (trust layer, #967): a caller
    with no trust grant from the target. Free-path expectations are
    unchanged from the pre-trust contract."""

    def _caller(self):
        from unittest.mock import MagicMock
        return MagicMock()

    def test_conscious_character_rejected(self):
        self.assertFalse(
            _can_third_party_clothing(self._caller(), _conscious_char()))

    def test_unconscious_character_allowed(self):
        self.assertTrue(
            _can_third_party_clothing(self._caller(), _unconscious_char()))

    def test_dead_character_allowed(self):
        self.assertTrue(
            _can_third_party_clothing(self._caller(), _dead_char()))

    def test_target_without_medical_state_rejected(self):
        """Defensive: targets that have no medical surface and aren't
        an Appendage should not silently slip through.  Future
        non-character clothing targets (mannequins, idols) will need
        their own path."""
        self.assertFalse(
            _can_third_party_clothing(self._caller(), _no_medical_target())
        )

    def test_conscious_character_with_trust_allowed(self):
        """The new path: a conscious target who has trusted the caller
        to dress them passes the gate."""
        from unittest.mock import patch
        from world.consent import grant_trust
        caller, target = self._caller(), _conscious_char()
        target.db = type("D", (), {"consent_grants": None})()
        caller.get_display_name = lambda looker=None, **k: "a medic"
        with patch("world.identity.get_apparent_uid", return_value="uid-1"):
            grant_trust(target, caller, "dress")
            self.assertTrue(_can_third_party_clothing(caller, target))

    def test_severed_appendage_allowed(self):
        """Appendage targets are universally dressable (no consent
        required — it's an object now).

        Patches the Appendage import inside the gate so we can use
        a lightweight stub class for ``isinstance``.  This isolates
        the test from Evennia typeclass spawn machinery."""
        class _FakeAppendage:
            pass
        # The gate imports Appendage inside the function body, so
        # patching ``typeclasses.items.Appendage`` is what matters.
        with patch("typeclasses.items.Appendage", _FakeAppendage):
            sentinel = _FakeAppendage()
            from unittest.mock import MagicMock
            self.assertTrue(_can_third_party_clothing(MagicMock(), sentinel))


# ---------------------------------------------------------------------
# Worn-items carry-forward via the sever pipeline
# ---------------------------------------------------------------------


class _DB:
    """Plain attribute container — mimics Evennia ``obj.db``."""


class _FakeItem:
    def __init__(self, key="item"):
        self.key = key
        self.moved_to = None

    def move_to(self, destination, quiet=False):
        self.moved_to = destination


class _FakeAppendage:
    def __init__(self):
        self.db = _DB()
        self.db.wounds_at_death = []
        self.db.longdesc_data = {}
        self.db.worn_items = {}


class _FakeCharacter:
    def __init__(self, worn_items=None, hands=None, species="human"):
        self.worn_items = {
            loc: list(items) for loc, items in (worn_items or {}).items()
        }
        self.hands = dict(hands or {"left": None, "right": None})
        self.longdesc = {}
        self.medical_state = SimpleNamespace(
            organs={}, vital_signs_updated=False,
            update_vital_signs=lambda: None,
        )
        self.db = SimpleNamespace(species=species)


class WornItemsCarryForward(TestCase):
    """Sever pipeline now writes worn items into the appendage's
    own worn_items dict so the third-party undress verb can read
    them and the renderer can surface forensic prose."""

    def test_glove_registered_at_left_hand_on_appendage(self):
        from typeclasses.items import detach_items_to_appendage
        glove = _FakeItem("glove")
        char = _FakeCharacter(worn_items={"left_hand": [glove]})
        appendage = _FakeAppendage()
        detach_items_to_appendage(char, appendage, "left_hand")
        self.assertIn("left_hand", appendage.db.worn_items)
        self.assertIn(glove, appendage.db.worn_items["left_hand"])

    def test_multi_location_item_registers_at_each_severed_loc(self):
        """A boot worn at left_foot only follows a severed left_shin
        (chain includes left_shin + left_foot).  It registers at
        left_foot on the appendage."""
        from typeclasses.items import detach_items_to_appendage
        boot = _FakeItem("boot")
        char = _FakeCharacter(worn_items={"left_foot": [boot]})
        appendage = _FakeAppendage()
        detach_items_to_appendage(
            char, appendage, ("left_shin", "left_foot")
        )
        self.assertIn("left_foot", appendage.db.worn_items)
        self.assertIn(boot, appendage.db.worn_items["left_foot"])

    def test_character_worn_items_cleared_for_moved_items(self):
        """Worn items that travel with the limb are removed from
        the character's worn_items dict."""
        from typeclasses.items import detach_items_to_appendage
        glove = _FakeItem("glove")
        char = _FakeCharacter(worn_items={"left_hand": [glove]})
        appendage = _FakeAppendage()
        detach_items_to_appendage(char, appendage, "left_hand")
        # Either the key is gone, or its list doesn't contain glove.
        worn = char.worn_items
        self.assertNotIn(glove, worn.get("left_hand", ()))

    def test_spanning_item_does_not_register_on_appendage(self):
        """A jacket spanning chest + both arms shouldn't register on
        a severed arm — it stays on the character."""
        from typeclasses.items import detach_items_to_appendage
        jacket = _FakeItem("jacket")
        char = _FakeCharacter(worn_items={
            "chest": [jacket],
            "left_arm": [jacket],
            "right_arm": [jacket],
        })
        appendage = _FakeAppendage()
        detach_items_to_appendage(
            char, appendage, ("left_arm", "left_hand")
        )
        self.assertEqual(appendage.db.worn_items, {})
        # Jacket still on the character.
        self.assertIn(jacket, char.worn_items["chest"])

    def test_appendage_worn_items_initialised_empty(self):
        """A fresh Appendage's worn_items defaults to empty dict so
        renderers / undress can iterate without None checks."""
        appendage = _FakeAppendage()
        self.assertEqual(appendage.db.worn_items, {})


# ---------------------------------------------------------------------
# Appendage.return_appearance worn-items rendering
# ---------------------------------------------------------------------


class WornItemsRendering(EvenniaTest):
    """A severed part describes its garments the way a body does (#3578).

    This class used to pin ``Appendage._build_worn_items_line`` — a
    bolted-on *"It still wears a glove, a ring, and a bracelet."*
    sentence with its own comma-and-and grammar. Owner ruling
    2026-09-16 deleted that sentence: a garment on a severed part now
    renders its ``worn_desc`` in place of the longdesc at the location
    it covers, exactly as it does on a living character and on a corpse.

    The intents carry over one-for-one — nothing renders when nothing is
    worn; each worn garment is surfaced; a garment registered at several
    locations is surfaced once — but they are asked of the real
    ``return_appearance``, because the one-garment-per-location rule is
    a property of the whole render pass, not of any line-builder inside
    it. Real objects, too: ``worn_garments()`` prunes anything without a
    ``pk`` or living anywhere but this limb (#2456/#3575), so stubs are
    pruned away and a renderer asked about a limb wearing nothing
    answers "" no matter what it does.
    """

    def setUp(self):
        super().setUp()
        self.limb = create_object("typeclasses.items.Appendage",
                                  key="a severed left arm",
                                  location=self.room1)
        self.limb.db.longdesc_data = {
            "left_arm": "His left arm is ropy with old scar tissue.",
            "left_hand": "His left hand is missing the little finger.",
        }
        self.limb.db.original_gender = "male"
        self.limb.db.source_species = "human"

    def wear(self, prose, coverage):
        """Put a garment on the limb: inside it, and in its ledger."""
        item = create_object("typeclasses.items.Item", key=prose,
                             location=self.limb)
        item.db.worn_desc = prose
        item.db.coverage = list(coverage)
        ledger = dict(self.limb.db.worn_items or {})
        for location in coverage:
            ledger.setdefault(location, []).append(item)
        self.limb.db.worn_items = ledger
        return item

    def look(self):
        return self.limb.return_appearance(self.char1)

    def test_nothing_worn_describes_no_garment(self):
        out = self.look()
        self.assertNotIn("still wears", out)
        self.assertNotIn("You see", out)
        self.assertIn("His left hand is missing the little finger.", out)

    def test_a_worn_garment_is_described(self):
        self.wear("a torn glove", ["left_hand"])
        self.assertIn("a torn glove", self.look())

    def test_it_stands_in_for_the_flesh_it_covers(self):
        self.wear("a torn glove", ["left_hand"])
        out = self.look()
        self.assertNotIn("His left hand is missing the little finger.", out)
        self.assertIn("His left arm is ropy with old scar tissue.", out)

    def test_two_garments_are_both_described(self):
        self.wear("a torn glove", ["left_hand"])
        self.wear("a leather bracer", ["left_arm"])
        out = self.look()
        self.assertIn("a torn glove", out)
        self.assertIn("a leather bracer", out)

    def test_three_garments_are_all_described(self):
        self.wear("a torn glove", ["left_hand"])
        self.wear("a leather bracer", ["left_arm"])
        self.wear("a signet ring", ["left_ring_finger"])
        out = self.look()
        for prose in ("a torn glove", "a leather bracer", "a signet ring"):
            self.assertIn(prose, out, f"{prose!r} went unrendered")

    def test_dedup_across_locations(self):
        """A garment registered at several locations renders once."""
        self.wear("a long leather coat", ["left_arm", "left_hand"])
        self.assertEqual(self.look().count("a long leather coat"), 1)

    def test_a_carried_garment_is_listed_not_worn(self):
        """Inside the limb is not worn on it: the ledger is the only
        authority, so a glove shoved into the hand is never described as
        worn and the hand under it still reads -- but it IS contents, and
        contents are listed (that line is how carried hardware is found,
        #3487)."""
        loose = create_object("typeclasses.items.Item", key="a spare glove",
                              location=self.limb)
        loose.db.worn_desc = "A spare glove, stiff with old blood, sits on {their} hand"
        loose.db.coverage = ["left_hand"]
        out = self.look()
        self.assertNotIn("stiff with old blood", out)
        self.assertIn("His left hand is missing the little finger.", out)
        self.assertIn("You see", out)
        self.assertIn("spare glove", out)

    def test_a_deleted_garment_leaves_no_trace(self):
        """The #2456 crash, asked of the renderer players actually hit."""
        glove = self.wear("a torn glove", ["left_hand"])
        glove.delete()
        out = self.look()                                # must not raise
        self.assertNotIn("a torn glove", out)
        self.assertIn("His left hand is missing the little finger.", out)


# ---------------------------------------------------------------------
# CmdBandage no longer claims "dress"
# ---------------------------------------------------------------------


class CmdBandageAliases(TestCase):
    """``dress`` was reclaimed from CmdBandage for the new
    third-party clothing command.  CmdBandage keeps ``bandage``
    primary and ``wrap`` alias."""

    def test_dress_not_in_bandage_aliases(self):
        from commands.CmdConsumption import CmdBandage
        self.assertNotIn("dress", CmdBandage.aliases)

    def test_wrap_still_in_bandage_aliases(self):
        from commands.CmdConsumption import CmdBandage
        self.assertIn("wrap", CmdBandage.aliases)

    def test_bandage_key_unchanged(self):
        from commands.CmdConsumption import CmdBandage
        self.assertEqual(CmdBandage.key, "bandage")


# ---------------------------------------------------------------------
# Command class registration contract
# ---------------------------------------------------------------------


class CommandRegistration(TestCase):

    def test_dress_command_exists(self):
        from commands.CmdClothing import CmdDress
        self.assertEqual(CmdDress.key, "dress")

    def test_undress_command_exists(self):
        from commands.CmdClothing import CmdUndress
        self.assertEqual(CmdUndress.key, "undress")

    def test_dress_in_default_cmdset(self):
        """CmdDress is registered on the character cmdset."""
        from commands.default_cmdsets import CharacterCmdSet
        cmdset = CharacterCmdSet()
        cmdset.at_cmdset_creation()
        keys = [cmd.key for cmd in cmdset.commands]
        self.assertIn("dress", keys)

    def test_undress_in_default_cmdset(self):
        from commands.default_cmdsets import CharacterCmdSet
        cmdset = CharacterCmdSet()
        cmdset.at_cmdset_creation()
        keys = [cmd.key for cmd in cmdset.commands]
        self.assertIn("undress", keys)
