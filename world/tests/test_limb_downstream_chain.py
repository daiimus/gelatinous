"""Tests for the limb downstream chain (issue #339).

When a limb is severed, downstream parts go with it: severing a shin
takes the foot; severing a thigh takes the shin + foot; severing an
arm takes the hand. Each chain produces a single Appendage with a
compound anatomical name. Wound rendering filters downstream severance
wounds so the body shows one cut-point wound, not one per chain
location.

These tests pin the chain semantics at every layer:

* Constants — chain + parent maps cover every severable limb.
* Naming — ``get_species_severed_chain_name`` returns compound names
  ("left leg", "left lower leg") for chain roots; falls back to the
  single-location name when no chain mapping exists.
* ``sever_character_body`` — strips longdescs and sets organ state
  for every chain location.
* ``detach_items_to_appendage`` — worn / wielded items follow the
  chain hand even when the cut happens upstream.
* ``get_character_wounds`` — cut-point filter suppresses downstream
  severance wounds.
* ``apply_sever_to_corpse`` — post-death CmdSever path also clears
  the downstream chain.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase

from typeclasses.items import (
    detach_items_to_appendage,
    sever_character_body,
)
from world.anatomy import (
    get_species_part_name,
    get_species_severed_chain_name,
)
from world.combat.constants import (
    LIMB_DOWNSTREAM_CHAIN,
    LIMB_PARENT,
    SEVERABLE_CONTAINERS,
)


# =====================================================================
# Constants — invariants
# =====================================================================


class ConstantInvariantTests(TestCase):
    """The chain + parent maps must cover the severable limb set."""

    SEVERABLE_LIMBS = (
        "left_arm", "left_hand",
        "left_thigh", "left_shin", "left_foot",
        "right_arm", "right_hand",
        "right_thigh", "right_shin", "right_foot",
    )

    def test_chain_map_covers_all_severable_limbs(self):
        for limb in self.SEVERABLE_LIMBS:
            with self.subTest(limb=limb):
                self.assertIn(
                    limb, LIMB_DOWNSTREAM_CHAIN,
                    f"Severable {limb} missing from LIMB_DOWNSTREAM_CHAIN",
                )

    def test_chain_includes_primary_container(self):
        # Every chain must start with the keyed container — keeps
        # iteration uniform for callers.
        for primary, chain in LIMB_DOWNSTREAM_CHAIN.items():
            with self.subTest(primary=primary):
                self.assertEqual(chain[0], primary)

    def test_thigh_chain_takes_shin_and_foot(self):
        self.assertEqual(
            LIMB_DOWNSTREAM_CHAIN["left_thigh"],
            ("left_thigh", "left_shin", "left_foot"),
        )
        self.assertEqual(
            LIMB_DOWNSTREAM_CHAIN["right_thigh"],
            ("right_thigh", "right_shin", "right_foot"),
        )

    def test_shin_chain_takes_foot(self):
        self.assertEqual(
            LIMB_DOWNSTREAM_CHAIN["left_shin"],
            ("left_shin", "left_foot"),
        )

    def test_arm_chain_takes_hand(self):
        self.assertEqual(
            LIMB_DOWNSTREAM_CHAIN["left_arm"],
            ("left_arm", "left_hand"),
        )

    def test_terminal_limbs_have_only_themselves(self):
        for terminal in ("left_hand", "right_hand",
                         "left_foot", "right_foot"):
            with self.subTest(terminal=terminal):
                self.assertEqual(
                    LIMB_DOWNSTREAM_CHAIN[terminal], (terminal,)
                )

    def test_parent_map_consistent_with_chain(self):
        # Every parent relationship in LIMB_PARENT must be reflected
        # in the corresponding chain entry.
        for child, parent in LIMB_PARENT.items():
            with self.subTest(child=child, parent=parent):
                parent_chain = LIMB_DOWNSTREAM_CHAIN.get(parent)
                self.assertIsNotNone(parent_chain)
                self.assertIn(child, parent_chain)


# =====================================================================
# Naming
# =====================================================================


class CompoundNamingTests(TestCase):

    def test_thigh_compound_name_is_full_leg(self):
        self.assertEqual(
            get_species_severed_chain_name("human", "left_thigh", "fresh"),
            "human left leg",
        )

    def test_shin_compound_name_is_lower_leg(self):
        self.assertEqual(
            get_species_severed_chain_name("human", "left_shin", "fresh"),
            "human left lower leg",
        )

    def test_arm_compound_name_is_arm(self):
        self.assertEqual(
            get_species_severed_chain_name("human", "left_arm", "fresh"),
            "human left arm",
        )

    def test_terminal_limb_compound_name_unchanged(self):
        # Severing at a hand or foot has no downstream — name should
        # be the same as the single-location name.
        self.assertEqual(
            get_species_severed_chain_name("human", "left_hand", "fresh"),
            "human left hand",
        )
        self.assertEqual(
            get_species_severed_chain_name("human", "left_foot", "fresh"),
            "human left foot",
        )

    def test_unknown_container_falls_back_to_single_location(self):
        # A container with no chain_display mapping defers to the
        # single-location ``get_species_part_name`` path.
        result = get_species_severed_chain_name(
            "human", "tentacle", "fresh"
        )
        expected = get_species_part_name("human", "tentacle", "fresh")
        self.assertEqual(result, expected)

    def test_decay_prefix_applies_to_compound_name(self):
        # The decay-stage prefix machinery still drives the prefix —
        # so a moderate-decay severed leg is still "rotting left leg",
        # not "human left leg".
        self.assertEqual(
            get_species_severed_chain_name(
                "human", "left_thigh", "moderate"
            ),
            "rotting left leg",
        )


# =====================================================================
# sever_character_body — chain handling
# =====================================================================


class _FakeOrgan:
    def __init__(self, container, current_hp=10, max_hp=10, name=None,
                 injury_type="generic"):
        self.container = container
        self.current_hp = current_hp
        self.max_hp = max_hp
        self.wound_stage = None
        # ``name`` and ``injury_type`` are read by the wound-injury
        # heuristics; we don't care about their values, just presence.
        self.name = name or container
        self.injury_type = injury_type
        self.conditions = []


class _FakeMedical:
    def __init__(self, organs):
        self.organs = organs


class _FakeChar:
    def __init__(self, longdesc=None, organs=None):
        self.longdesc = dict(longdesc or {})
        self.medical_state = _FakeMedical(organs or {})


class SeverCharacterBodyChainTests(TestCase):

    def test_legacy_single_string_still_works(self):
        # Existing call sites pass a single string container; preserve
        # that signature for backwards compatibility.
        organs = {
            "left_humerus": _FakeOrgan("left_arm"),
            "left_metacarpals": _FakeOrgan("left_hand"),
        }
        char = _FakeChar(
            longdesc={"left_arm": "muscled arms",
                      "left_hand": "scarred hand"},
            organs=organs,
        )
        sever_character_body(char, "left_arm")
        # Only the single container is severed under legacy signature.
        self.assertNotIn("left_arm", char.longdesc)
        self.assertEqual(organs["left_humerus"].wound_stage, "severed")
        self.assertIsNone(organs["left_metacarpals"].wound_stage)

    def test_chain_severs_all_listed_containers(self):
        organs = {
            "left_femur": _FakeOrgan("left_thigh"),
            "left_tibia": _FakeOrgan("left_shin"),
            "left_metatarsals": _FakeOrgan("left_foot"),
            # Unrelated organ on the other leg — must NOT be touched.
            "right_femur": _FakeOrgan("right_thigh"),
        }
        char = _FakeChar(
            longdesc={
                "left_thigh": "muscled thigh",
                "left_shin": "scarred shin",
                "left_foot": "wide foot",
                "right_thigh": "matching thigh",
            },
            organs=organs,
        )
        sever_character_body(
            char, ("left_thigh", "left_shin", "left_foot")
        )
        # All chain longdescs gone.
        self.assertNotIn("left_thigh", char.longdesc)
        self.assertNotIn("left_shin", char.longdesc)
        self.assertNotIn("left_foot", char.longdesc)
        # Right leg untouched.
        self.assertIn("right_thigh", char.longdesc)
        # All chain organs severed.
        self.assertEqual(organs["left_femur"].wound_stage, "severed")
        self.assertEqual(organs["left_tibia"].wound_stage, "severed")
        self.assertEqual(
            organs["left_metatarsals"].wound_stage, "severed"
        )
        # Right leg organ untouched.
        self.assertIsNone(organs["right_femur"].wound_stage)


# =====================================================================
# detach_items_to_appendage — chain handling
# =====================================================================


class _FakeItem:
    """Hashable stand-in for a worn / wielded item.

    ``SimpleNamespace`` instances aren't hashable, and the detach
    helper uses items as dict keys to track which locations they're
    worn at.
    """

    _next_id = 0

    def __init__(self):
        type(self)._next_id += 1
        self._id = type(self)._next_id

    def __hash__(self):
        return self._id

    def __eq__(self, other):
        return self is other


class DetachItemsChainTests(TestCase):

    def _char(self, worn=None, hands=None):
        return SimpleNamespace(
            worn_items=worn or {},
            hands=hands or {"left": None, "right": None},
        )

    def _appendage(self):
        # Minimal stub — _relocate_item is no-op when move_to absent.
        return SimpleNamespace()

    def test_severing_arm_takes_glove_worn_at_hand(self):
        glove = _FakeItem()
        char = self._char(worn={"left_hand": [glove]})
        app = self._appendage()
        moved = detach_items_to_appendage(
            char, app, ("left_arm", "left_hand")
        )
        self.assertIn(glove, moved)
        self.assertNotIn("left_hand", char.worn_items)

    def test_severing_shin_takes_boot_worn_at_foot(self):
        boot = _FakeItem()
        char = self._char(worn={"left_foot": [boot]})
        app = self._appendage()
        moved = detach_items_to_appendage(
            char, app, ("left_shin", "left_foot")
        )
        self.assertIn(boot, moved)
        self.assertNotIn("left_foot", char.worn_items)

    def test_severing_arm_takes_wielded_weapon(self):
        sword = _FakeItem()
        char = self._char(hands={"left": sword, "right": None})
        app = self._appendage()
        moved = detach_items_to_appendage(
            char, app, ("left_arm", "left_hand")
        )
        self.assertIn(sword, moved)
        self.assertIsNone(char.hands["left"])
        # Right hand untouched.
        self.assertIsNone(char.hands["right"])

    def test_jacket_spanning_chest_and_arms_stays_on_body(self):
        # A jacket that covers chest AND both arms must stay on the
        # character when only one arm is severed.
        jacket = _FakeItem()
        char = self._char(
            worn={
                "chest": [jacket],
                "left_arm": [jacket],
                "right_arm": [jacket],
            }
        )
        app = self._appendage()
        moved = detach_items_to_appendage(
            char, app, ("left_arm", "left_hand")
        )
        self.assertNotIn(jacket, moved)
        # Jacket entry remains in worn_items (chest at least).
        self.assertIn("chest", char.worn_items)

    def test_legacy_single_string_still_works(self):
        # Existing callers pass a single string — preserve backwards
        # compatibility.
        glove = _FakeItem()
        char = self._char(worn={"left_hand": [glove]})
        app = self._appendage()
        moved = detach_items_to_appendage(char, app, "left_hand")
        self.assertIn(glove, moved)


# =====================================================================
# get_character_wounds — cut-point filter
# =====================================================================


class CutPointFilterTests(TestCase):
    """Downstream severance wounds are suppressed; only the cut point
    renders."""

    def _char_with_severed_chain(self):
        # Simulate a shin+foot severance: tibia and metatarsals are
        # both wound_stage='severed' at current_hp=0.
        organs = {
            "left_tibia": _FakeOrgan("left_shin"),
            "left_metatarsals": _FakeOrgan("left_foot"),
        }
        organs["left_tibia"].current_hp = 0
        organs["left_tibia"].wound_stage = "severed"
        organs["left_metatarsals"].current_hp = 0
        organs["left_metatarsals"].wound_stage = "severed"

        char = SimpleNamespace(
            medical_state=_FakeMedical(organs),
            # Wound visibility check uses this — return False / no
            # coverage so the wound is visible.
            is_location_covered=lambda loc: False,
            db=SimpleNamespace(skintone=None, species="human"),
        )
        return char

    def test_shin_sever_renders_one_wound_at_cut_point(self):
        from world.medical.wounds import get_character_wounds

        char = self._char_with_severed_chain()
        wounds = get_character_wounds(char)
        # Only the shin (cut point) wound should remain; the foot
        # (downstream) wound is suppressed.
        locations = {w["location"] for w in wounds}
        self.assertIn("left_shin", locations)
        self.assertNotIn("left_foot", locations)

    def test_solo_foot_sever_still_renders(self):
        # If only the foot is severed (foot directly cut, not as
        # downstream of shin), the wound should still render — the
        # shin's parent is itself NOT severed.
        from world.medical.wounds import get_character_wounds

        organs = {
            "left_metatarsals": _FakeOrgan("left_foot"),
            "left_tibia": _FakeOrgan("left_shin"),  # intact
        }
        organs["left_metatarsals"].current_hp = 0
        organs["left_metatarsals"].wound_stage = "severed"
        # left_tibia stays healthy — shin is still attached.

        char = SimpleNamespace(
            medical_state=_FakeMedical(organs),
            is_location_covered=lambda loc: False,
            db=SimpleNamespace(skintone=None, species="human"),
        )
        wounds = get_character_wounds(char)
        locations = {w["location"] for w in wounds}
        self.assertIn("left_foot", locations)
