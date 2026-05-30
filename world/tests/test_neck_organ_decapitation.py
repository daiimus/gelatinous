"""Tests for the neck organ + decapitation death model (combat-sever Phase A, #243).

Covers:

* schema presence of the ``cervical_spine`` organ and the
  ``neck_integrity`` body capacity;
* hit-location routing — ``neck`` resolves to ``cervical_spine``;
* the death wiring — destroying ``cervical_spine`` drives
  ``MedicalState.is_dead()`` True via ``neck_integrity`` at 0.0;
* the pre-migration safety net — a medical state that lacks the organ
  lazily reads a healthy neck (not decapitated) thanks to
  ``get_organ`` lazy creation.
"""

from __future__ import annotations

from unittest import TestCase

from world.medical.constants import BODY_CAPACITIES, ORGANS
from world.medical.core import MedicalState
from world.medical.utils import (
    get_organ_by_body_location,
    select_target_organ,
)


class TestNeckOrganSchema(TestCase):
    """The neck organ and its capacity must be registered in the schema."""

    def test_cervical_spine_registered(self):
        self.assertIn("cervical_spine", ORGANS)
        organ = ORGANS["cervical_spine"]
        self.assertEqual(organ["container"], "neck")
        self.assertTrue(organ.get("vital"))
        self.assertEqual(organ.get("capacity"), "neck_integrity")
        self.assertEqual(organ.get("contribution"), "total")

    def test_cervical_spine_is_destroyable(self):
        # Unlike the thoracic/lumbar ``spine`` in the ``back`` container,
        # the cervical spine must be destroyable (it is the decapitation
        # locus).
        self.assertTrue(ORGANS["cervical_spine"].get("can_be_destroyed"))
        self.assertNotIn("cannot_be_destroyed", ORGANS["cervical_spine"])

    def test_neck_integrity_capacity_registered(self):
        self.assertIn("neck_integrity", BODY_CAPACITIES)
        cap = BODY_CAPACITIES["neck_integrity"]
        self.assertEqual(cap["organs"], ["cervical_spine"])
        self.assertTrue(cap.get("directly_fatal"))


class TestNeckHitRouting(TestCase):
    """Combat damage aimed at the neck must resolve to the cervical spine."""

    def test_neck_location_contains_cervical_spine(self):
        organs = get_organ_by_body_location("neck")
        self.assertIn("cervical_spine", organs)

    def test_select_target_organ_neck(self):
        # The neck has a single organ, so selection is deterministic.
        organ = select_target_organ("neck", precision_roll=10, attacker_skill=5)
        self.assertEqual(organ, "cervical_spine")


class TestDecapitationDeath(TestCase):
    """Destroying the cervical spine is immediately fatal."""

    def test_healthy_neck_is_full_and_alive(self):
        state = MedicalState()
        self.assertAlmostEqual(
            state.calculate_body_capacity("neck_integrity"), 1.0
        )
        self.assertFalse(state.is_dead())

    def test_destroyed_cervical_spine_is_fatal(self):
        state = MedicalState()
        organ = state.get_organ("cervical_spine")
        state.take_organ_damage("cervical_spine", organ.max_hp + 5, "cut")
        self.assertTrue(state.get_organ("cervical_spine").is_destroyed())
        self.assertEqual(
            state.calculate_body_capacity("neck_integrity"), 0.0
        )
        self.assertTrue(state.is_dead())

    def test_missing_organ_lazily_reads_healthy(self):
        # Simulates a pre-migration character whose persisted organ set
        # lacks ``cervical_spine``.  ``get_organ`` lazily creates a full-HP
        # organ, so the character must NOT read as decapitated.
        state = MedicalState()
        state.organs.pop("cervical_spine", None)
        self.assertAlmostEqual(
            state.calculate_body_capacity("neck_integrity"), 1.0
        )
        self.assertFalse(state.is_dead())
