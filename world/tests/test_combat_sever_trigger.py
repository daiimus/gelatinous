"""Unit tests for the Phase C combat severance trigger (#245 follow-up).

Exercises the damage-driven severance decision logic added to
:class:`typeclasses.armor_mixin.ArmorMixin` against plain-Python stubs
(no Evennia typeclass / DB):

* :meth:`ArmorMixin._bone_freshly_destroyed` — reports a limb whose
  representative bone is at/below 0 HP and not yet cleanly amputated.
* :meth:`ArmorMixin._maybe_sever_from_damage` — gates on edged injury
  type, routes the neck to a deferred decapitation flag, and detaches
  any other severable limb immediately.

The :data:`world.combat.constants.SEVERING_INJURY_TYPES` membership
contract is also covered.

Run via::

    evennia test world.tests.test_combat_sever_trigger
"""

from __future__ import annotations

from unittest import TestCase

import typeclasses.items as items_module
from typeclasses.armor_mixin import ArmorMixin
from world.combat.constants import (
    SEVERABLE_CONTAINERS,
    SEVERING_INJURY_TYPES,
)


class _DB:
    """Bare attribute container — matches Evennia ``obj.db`` surface."""


class _FakeOrgan:
    def __init__(self, container, *, current_hp=10, max_hp=10,
                 wound_stage=None):
        self.container = container
        self.current_hp = current_hp
        self.max_hp = max_hp
        self.wound_stage = wound_stage


class _FakeMedicalState:
    def __init__(self, organs):
        self.organs = organs


class _FakeCharacter(ArmorMixin):
    """Minimal host exposing only what the trigger logic touches."""

    def __init__(self, organs):
        self.db = _DB()
        self.db.decapitation_pending = None
        self.medical_state = _FakeMedicalState(organs)


# ---------------------------------------------------------------------
# SEVERING_INJURY_TYPES
# ---------------------------------------------------------------------


class SeveringInjuryTypesTests(TestCase):
    def test_edged_types_present(self):
        self.assertIn("cut", SEVERING_INJURY_TYPES)
        self.assertIn("stab", SEVERING_INJURY_TYPES)
        self.assertIn("laceration", SEVERING_INJURY_TYPES)

    def test_non_edged_types_absent(self):
        for injury in ("blunt", "bullet", "burn", "generic"):
            self.assertNotIn(injury, SEVERING_INJURY_TYPES)


# ---------------------------------------------------------------------
# _bone_freshly_destroyed
# ---------------------------------------------------------------------


class BoneFreshlyDestroyedTests(TestCase):
    def test_destroyed_bone_is_fresh(self):
        char = _FakeCharacter({
            "left_humerus": _FakeOrgan(
                "left_arm", current_hp=0, wound_stage="destroyed"
            ),
        })
        self.assertTrue(char._bone_freshly_destroyed("left_arm"))

    def test_intact_bone_is_not_fresh(self):
        char = _FakeCharacter({
            "left_humerus": _FakeOrgan("left_arm", current_hp=10),
        })
        self.assertFalse(char._bone_freshly_destroyed("left_arm"))

    def test_already_severed_bone_is_not_fresh(self):
        # Idempotency guard: a re-hit on an amputated stump must not
        # re-sever it.
        char = _FakeCharacter({
            "left_humerus": _FakeOrgan(
                "left_arm", current_hp=0, wound_stage="severed"
            ),
        })
        self.assertFalse(char._bone_freshly_destroyed("left_arm"))

    def test_no_organ_in_location_is_not_fresh(self):
        char = _FakeCharacter({
            "heart": _FakeOrgan("chest", current_hp=0),
        })
        self.assertFalse(char._bone_freshly_destroyed("left_arm"))

    def test_all_organs_must_be_destroyed(self):
        # A container with a still-functional organ is not "lost".
        char = _FakeCharacter({
            "a": _FakeOrgan("left_arm", current_hp=0,
                            wound_stage="destroyed"),
            "b": _FakeOrgan("left_arm", current_hp=5),
        })
        self.assertFalse(char._bone_freshly_destroyed("left_arm"))


# ---------------------------------------------------------------------
# _maybe_sever_from_damage
# ---------------------------------------------------------------------


class MaybeSeverFromDamageTests(TestCase):
    def setUp(self):
        # Capture apply_sever_to_character calls without touching the DB.
        self._orig = items_module.apply_sever_to_character
        self.calls = []

        def _spy(character, container, *, injury_type="cut"):
            self.calls.append((character, container, injury_type))

        items_module.apply_sever_to_character = _spy

    def tearDown(self):
        items_module.apply_sever_to_character = self._orig

    def _destroyed(self, container):
        return _FakeCharacter({
            "bone": _FakeOrgan(container, current_hp=0,
                               wound_stage="destroyed"),
        })

    def test_edged_limb_hit_severs_immediately(self):
        char = self._destroyed("left_arm")
        char._maybe_sever_from_damage("left_arm", "cut")
        self.assertEqual(self.calls, [(char, "left_arm", "cut")])
        self.assertIsNone(char.db.decapitation_pending)

    def test_blunt_limb_hit_does_not_sever(self):
        char = self._destroyed("left_arm")
        char._maybe_sever_from_damage("left_arm", "blunt")
        self.assertEqual(self.calls, [])

    def test_edged_neck_hit_flags_decapitation(self):
        char = self._destroyed("neck")
        char._maybe_sever_from_damage("neck", "stab")
        # Neck routes through death → corpse, not a synchronous sever.
        self.assertEqual(self.calls, [])
        self.assertTrue(char.db.decapitation_pending)

    def test_blunt_neck_hit_does_not_flag(self):
        char = self._destroyed("neck")
        char._maybe_sever_from_damage("neck", "blunt")
        self.assertIsNone(char.db.decapitation_pending)

    def test_intact_limb_not_severed(self):
        char = _FakeCharacter({
            "bone": _FakeOrgan("right_arm", current_hp=8),
        })
        char._maybe_sever_from_damage("right_arm", "cut")
        self.assertEqual(self.calls, [])

    def test_already_severed_limb_not_re_severed(self):
        char = _FakeCharacter({
            "bone": _FakeOrgan("right_arm", current_hp=0,
                               wound_stage="severed"),
        })
        char._maybe_sever_from_damage("right_arm", "cut")
        self.assertEqual(self.calls, [])

    def test_head_location_excluded(self):
        # Head is severable-on-corpse only; living decapitation routes
        # through the neck path, so a direct head hit never severs here.
        char = self._destroyed("head")
        char._maybe_sever_from_damage("head", "cut")
        self.assertEqual(self.calls, [])
        self.assertIsNone(char.db.decapitation_pending)

    def test_non_severable_location_ignored(self):
        char = self._destroyed("chest")
        char._maybe_sever_from_damage("chest", "cut")
        self.assertEqual(self.calls, [])

    def test_every_living_severable_limb_routes(self):
        living_limbs = SEVERABLE_CONTAINERS - {"head"}
        for container in living_limbs:
            with self.subTest(container=container):
                self.calls.clear()
                char = self._destroyed(container)
                char._maybe_sever_from_damage(container, "laceration")
                self.assertEqual(
                    self.calls, [(char, container, "laceration")]
                )
