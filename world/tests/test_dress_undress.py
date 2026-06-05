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

    def test_conscious_character_rejected(self):
        self.assertFalse(_can_third_party_clothing(_conscious_char()))

    def test_unconscious_character_allowed(self):
        self.assertTrue(_can_third_party_clothing(_unconscious_char()))

    def test_dead_character_allowed(self):
        self.assertTrue(_can_third_party_clothing(_dead_char()))

    def test_target_without_medical_state_rejected(self):
        """Defensive: targets that have no medical surface and aren't
        an Appendage should not silently slip through.  Future
        non-character clothing targets (mannequins, idols) will need
        their own path."""
        self.assertFalse(
            _can_third_party_clothing(_no_medical_target())
        )

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
            self.assertTrue(_can_third_party_clothing(sentinel))


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


class WornItemsRendering(TestCase):
    """``Appendage._build_worn_items_line`` surfaces the "still
    wears" forensic line in the appendage's appearance prose."""

    def _appendage_with_worn(self, worn_dict):
        """Build an object exposing the same _build_worn_items_line
        method without instantiating a real Appendage (which would
        need full Evennia DB setup)."""
        from typeclasses.items import Appendage

        class _Stub(Appendage):
            pass

        # Patch the at_object_creation guard so we can construct
        # without going through Evennia's typeclass machinery.
        stub = SimpleNamespace()
        stub.db = SimpleNamespace(worn_items=worn_dict)
        stub.get_display_name = lambda looker: "stub"
        # Bind the unbound method.
        stub._build_worn_items_line = (
            Appendage._build_worn_items_line.__get__(stub, type(stub))
        )
        return stub

    def test_empty_returns_empty_string(self):
        stub = self._appendage_with_worn({})
        self.assertEqual(stub._build_worn_items_line(None), "")

    def test_single_item_renders(self):
        glove = SimpleNamespace(get_display_name=lambda lk: "a glove")
        stub = self._appendage_with_worn({"left_hand": [glove]})
        line = stub._build_worn_items_line(None)
        self.assertIn("a glove", line)
        self.assertTrue(line.startswith("It still wears"))

    def test_two_items_renders_with_and(self):
        glove = SimpleNamespace(get_display_name=lambda lk: "a glove")
        ring = SimpleNamespace(get_display_name=lambda lk: "a ring")
        stub = self._appendage_with_worn({
            "left_hand": [glove, ring],
        })
        line = stub._build_worn_items_line(None)
        self.assertIn("a glove", line)
        self.assertIn("a ring", line)
        self.assertIn("and", line)

    def test_three_items_uses_comma_and_and(self):
        items = [
            SimpleNamespace(get_display_name=lambda lk, n=n: n)
            for n in ("a glove", "a ring", "a bracelet")
        ]
        stub = self._appendage_with_worn({"left_hand": items})
        line = stub._build_worn_items_line(None)
        self.assertIn("a glove,", line)
        self.assertIn("a ring,", line)
        self.assertIn("and a bracelet", line)

    def test_dedup_across_locations(self):
        """An item registered at multiple locations renders once."""
        coat = SimpleNamespace(get_display_name=lambda lk: "a coat")
        stub = self._appendage_with_worn({
            "chest": [coat],
            "left_arm": [coat],
        })
        line = stub._build_worn_items_line(None)
        # "a coat" should appear once, not twice.
        self.assertEqual(line.count("a coat"), 1)


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
