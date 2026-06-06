"""Unit tests for the Phase B living-character severance helpers (#245).

Four pure module-level helpers in :mod:`typeclasses.items` are
exercised against plain-Python stubs (no Evennia typeclass / DB):

* :func:`apply_living_sever_overlay` — copies a live character's
  longdesc prose + visible wounds for a location set onto a severed
  :class:`Appendage`, in the same ``db`` shape the corpse overlay
  produces.
* :func:`sever_character_body` — strips the limb's longdesc prose off
  the character and marks the limb's organs cleanly ``severed``.
* :func:`detach_items_to_appendage` — moves worn items fully contained
  within the severed cluster, plus the wielded weapon in the matching
  hand, onto the appendage.

The :data:`world.combat.constants.SEVER_HAND_BY_CONTAINER` mapping is
also covered.

Run via::

    evennia test world.tests.test_living_sever
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from typeclasses.items import (
    apply_living_sever_overlay,
    detach_items_to_appendage,
    sever_character_body,
)
from world.combat.constants import SEVER_HAND_BY_CONTAINER


class _DB:
    """Bare attribute container — matches Evennia ``obj.db`` surface."""


class _FakeAppendage:
    def __init__(self):
        self.db = _DB()
        self.db.wounds_at_death = []
        self.db.longdesc_data = {}


class _FakeOrgan:
    def __init__(self, container, *, current_hp=10, max_hp=10):
        self.container = container
        self.current_hp = current_hp
        self.max_hp = max_hp
        self.wound_stage = None


class _FakeMedicalState:
    def __init__(self, organs):
        # organs: {name: _FakeOrgan}
        self.organs = organs
        self.vital_signs_updated = False

    def update_vital_signs(self):
        self.vital_signs_updated = True


class _FakeItem:
    """Stub worn / wielded item; records relocation target."""

    def __init__(self, key):
        self.key = key
        self.moved_to = None

    def move_to(self, destination, quiet=False):
        self.moved_to = destination


class _FakeCharacter:
    def __init__(self, *, longdesc=None, organs=None, worn_items=None,
                 hands=None, gender="male", key="Bob", species="human"):
        self.longdesc = dict(longdesc or {})
        self.worn_items = {
            loc: list(items) for loc, items in (worn_items or {}).items()
        }
        self.hands = dict(hands or {"left": None, "right": None})
        self.gender = gender
        self.key = key
        self.medical_state = _FakeMedicalState(organs or {})
        self._saved = False

    def save_medical_state(self):
        self._saved = True


def _wound(location, organ, *, injury_type="cut", severity="Severe",
           max_hp=10):
    """Build a get_character_wounds-shaped dict."""
    return {
        "injury_type": injury_type,
        "location": location,
        "severity": severity,
        "stage": "fresh",
        "organ": organ,
        "organ_obj": _FakeOrgan(location, current_hp=0, max_hp=max_hp),
    }


# ---------------------------------------------------------------------
# apply_living_sever_overlay
# ---------------------------------------------------------------------


class ApplyLivingSeverOverlayTests(TestCase):
    """Pure copy: live character data → severed appendage db."""

    def test_single_location_longdesc_copied(self):
        appendage = _FakeAppendage()
        apply_living_sever_overlay(
            appendage,
            longdescs={
                "left_arm": "a freckled forearm",
                "chest": "a broad chest",
            },
            wounds=[],
            locations=("left_arm",),
        )
        self.assertEqual(
            appendage.db.longdesc_data, {"left_arm": "a freckled forearm"}
        )

    def test_wounds_at_location_carried_in_corpse_shape(self):
        appendage = _FakeAppendage()
        apply_living_sever_overlay(
            appendage,
            longdescs={},
            wounds=[
                _wound("left_arm", "left_humerus", max_hp=12),
                _wound("chest", "heart"),  # not carried
            ],
            locations=("left_arm",),
        )
        self.assertEqual(len(appendage.db.wounds_at_death), 1)
        carried = appendage.db.wounds_at_death[0]
        self.assertEqual(carried["location"], "left_arm")
        self.assertEqual(carried["organ"], "left_humerus")
        self.assertEqual(carried["injury_type"], "cut")
        # Rendered at the preserved-wound stage like corpse-severed parts.
        self.assertEqual(carried["stage"], "old")
        self.assertEqual(carried["organ_damage"]["container"], "left_arm")
        self.assertEqual(carried["organ_damage"]["current_hp"], 0)
        self.assertEqual(carried["organ_damage"]["max_hp"], 12)

    def test_carried_organ_hp_preserves_live_value(self):
        # Parity with the corpse-side death snapshot, which captures
        # ``organ_obj.current_hp`` at the instant of death rather than
        # zeroing it.  Severing a still-healthy arm should carry the
        # arm's organs onto the appendage at their live HP, not at 0.
        appendage = _FakeAppendage()
        healthy_wound = {
            "injury_type": "cut",
            "location": "left_arm",
            "severity": "Moderate",
            "stage": "fresh",
            "organ": "left_humerus",
            "organ_obj": _FakeOrgan("left_arm", current_hp=8, max_hp=12),
        }
        apply_living_sever_overlay(
            appendage,
            longdescs={},
            wounds=[healthy_wound],
            locations=("left_arm",),
        )
        carried = appendage.db.wounds_at_death[0]
        self.assertEqual(carried["organ_damage"]["current_hp"], 8)
        self.assertEqual(carried["organ_damage"]["max_hp"], 12)

    def test_empty_text_longdesc_skipped(self):
        appendage = _FakeAppendage()
        apply_living_sever_overlay(
            appendage,
            longdescs={"left_arm": ""},
            wounds=[],
            locations=("left_arm",),
        )
        self.assertEqual(appendage.db.longdesc_data, {})

    def test_none_inputs_treated_as_empty(self):
        appendage = _FakeAppendage()
        apply_living_sever_overlay(
            appendage, longdescs=None, wounds=None, locations=("left_arm",)
        )
        self.assertEqual(appendage.db.longdesc_data, {})
        self.assertEqual(appendage.db.wounds_at_death, [])

    def test_wound_without_organ_obj_defaults_max_hp_zero(self):
        appendage = _FakeAppendage()
        wound = {
            "injury_type": "cut",
            "location": "right_hand",
            "severity": "Moderate",
            "organ": "right_metacarpals",
            "organ_obj": None,
        }
        apply_living_sever_overlay(
            appendage, longdescs={}, wounds=[wound],
            locations=("right_hand",),
        )
        self.assertEqual(
            appendage.db.wounds_at_death[0]["organ_damage"]["max_hp"], 0
        )


# ---------------------------------------------------------------------
# sever_character_body
# ---------------------------------------------------------------------


class SeverCharacterBodyTests(TestCase):
    """Character-side mutation: drop prose, mark organs severed."""

    def test_longdesc_for_location_removed(self):
        char = _FakeCharacter(longdesc={
            "left_arm": "a freckled forearm",
            "chest": "a broad chest",
        })
        sever_character_body(char, "left_arm")
        self.assertNotIn("left_arm", char.longdesc)
        self.assertIn("chest", char.longdesc)

    def test_organs_in_container_marked_severed(self):
        organs = {
            "left_humerus": _FakeOrgan("left_arm"),
            "left_radius": _FakeOrgan("left_arm"),
            "heart": _FakeOrgan("chest"),
        }
        char = _FakeCharacter(organs=organs)
        sever_character_body(char, "left_arm")
        self.assertEqual(organs["left_humerus"].current_hp, 0)
        self.assertEqual(organs["left_humerus"].wound_stage, "severed")
        self.assertEqual(organs["left_radius"].current_hp, 0)
        self.assertEqual(organs["left_radius"].wound_stage, "severed")
        # Unrelated organ untouched.
        self.assertEqual(organs["heart"].current_hp, 10)
        self.assertIsNone(organs["heart"].wound_stage)

    def test_missing_location_longdesc_is_noop(self):
        char = _FakeCharacter(longdesc={"chest": "a broad chest"})
        # Should not raise even though left_arm has no prose.
        sever_character_body(char, "left_arm")
        self.assertEqual(char.longdesc, {"chest": "a broad chest"})


# ---------------------------------------------------------------------
# detach_items_to_appendage
# ---------------------------------------------------------------------


class DetachItemsToAppendageTests(TestCase):
    """Worn-coverage containment rule + wielded-weapon follow."""

    def test_glove_fully_contained_moves_with_hand(self):
        glove = _FakeItem("glove")
        char = _FakeCharacter(worn_items={"left_hand": [glove]})
        appendage = _FakeAppendage()
        moved = detach_items_to_appendage(char, appendage, "left_hand")
        self.assertIn(glove, moved)
        self.assertEqual(glove.moved_to, appendage)
        self.assertNotIn("left_hand", char.worn_items)

    def test_jacket_spanning_multiple_locations_stays(self):
        jacket = _FakeItem("jacket")
        char = _FakeCharacter(worn_items={
            "left_arm": [jacket],
            "right_arm": [jacket],
            "chest": [jacket],
        })
        appendage = _FakeAppendage()
        moved = detach_items_to_appendage(char, appendage, "left_arm")
        self.assertNotIn(jacket, moved)
        self.assertIsNone(jacket.moved_to)
        # Jacket still worn at all original locations.
        self.assertIn(jacket, char.worn_items["left_arm"])
        self.assertIn(jacket, char.worn_items["chest"])

    def test_wielded_weapon_drops_to_room_when_hand_severed(self):
        """PR-H0: weapon held in severed hand drops to the character's
        location rather than travelling onto the appendage."""
        knife = _FakeItem("knife")
        room = SimpleNamespace()
        char = _FakeCharacter(hands={"left": None, "right": knife})
        char.location = room
        appendage = _FakeAppendage()
        with patch("commands.combat.jump.drop_to_room") as mock_drop:
            moved = detach_items_to_appendage(
                char, appendage, "right_hand"
            )
        # Weapon dropped to the room, not relocated onto the appendage.
        mock_drop.assert_called_once_with(knife, room)
        # Weapon is NOT in the moved list (moved tracks items that
        # travel WITH the appendage).
        self.assertNotIn(knife, moved)
        # Hand slot cleared.
        self.assertIsNone(char.hands["right"])

    def test_wielded_weapon_drops_to_room_when_arm_severed(self):
        """Same drop-to-room rule when severance happens upstream of
        the hand container (whole arm severed)."""
        knife = _FakeItem("knife")
        room = SimpleNamespace()
        char = _FakeCharacter(hands={"left": None, "right": knife})
        char.location = room
        appendage = _FakeAppendage()
        with patch("commands.combat.jump.drop_to_room") as mock_drop:
            moved = detach_items_to_appendage(
                char, appendage, "right_arm"
            )
        mock_drop.assert_called_once_with(knife, room)
        self.assertNotIn(knife, moved)
        self.assertIsNone(char.hands["right"])

    def test_wielded_weapon_falls_back_to_appendage_without_location(self):
        """Defensive: if the character has no location (orphaned test
        stub, edge case), fall back to the legacy appendage-relocate
        path so the weapon isn't lost."""
        knife = _FakeItem("knife")
        char = _FakeCharacter(hands={"left": None, "right": knife})
        # No location attribute set on this character stub.
        appendage = _FakeAppendage()
        moved = detach_items_to_appendage(char, appendage, "right_hand")
        # Legacy behaviour: weapon relocates to appendage.
        self.assertEqual(knife.moved_to, appendage)
        self.assertIsNone(char.hands["right"])

    def test_wielded_weapon_in_other_hand_unaffected(self):
        knife = _FakeItem("knife")
        char = _FakeCharacter(hands={"left": knife, "right": None})
        appendage = _FakeAppendage()
        moved = detach_items_to_appendage(char, appendage, "right_hand")
        self.assertNotIn(knife, moved)
        self.assertEqual(char.hands["left"], knife)

    def test_legless_container_pulls_no_weapon(self):
        # A severed thigh has no hand → no wielded-weapon follow.
        boot = _FakeItem("boot")
        knife = _FakeItem("knife")
        char = _FakeCharacter(
            worn_items={"left_thigh": [boot]},
            hands={"left": knife, "right": None},
        )
        appendage = _FakeAppendage()
        moved = detach_items_to_appendage(char, appendage, "left_thigh")
        self.assertIn(boot, moved)
        self.assertNotIn(knife, moved)
        self.assertEqual(char.hands["left"], knife)

    def test_worn_follows_limb_wielded_drops_to_room(self):
        """PR-H0: combined case — worn glove travels with the
        severed hand; wielded knife falls to the ground.  ``moved``
        only contains the worn item; the knife is dispatched to
        ``drop_to_room`` instead."""
        glove = _FakeItem("glove")
        knife = _FakeItem("knife")
        room = SimpleNamespace()
        char = _FakeCharacter(
            worn_items={"right_hand": [glove]},
            hands={"left": None, "right": knife},
        )
        char.location = room
        appendage = _FakeAppendage()
        with patch("commands.combat.jump.drop_to_room") as mock_drop:
            moved = detach_items_to_appendage(
                char, appendage, "right_hand"
            )
        self.assertEqual(set(moved), {glove})
        mock_drop.assert_called_once_with(knife, room)


# ---------------------------------------------------------------------
# SEVER_HAND_BY_CONTAINER
# ---------------------------------------------------------------------


class SeverHandByContainerTests(TestCase):
    def test_arm_and_hand_map_to_correct_side(self):
        self.assertEqual(SEVER_HAND_BY_CONTAINER["left_arm"], "left")
        self.assertEqual(SEVER_HAND_BY_CONTAINER["left_hand"], "left")
        self.assertEqual(SEVER_HAND_BY_CONTAINER["right_arm"], "right")
        self.assertEqual(SEVER_HAND_BY_CONTAINER["right_hand"], "right")

    def test_legs_absent(self):
        for loc in ("left_thigh", "right_thigh", "left_shin",
                    "right_shin", "left_foot", "right_foot"):
            self.assertNotIn(loc, SEVER_HAND_BY_CONTAINER)
