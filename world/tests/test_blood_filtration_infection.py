"""
Tests for blood_filtration → infection course
(CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC §7.1).

Failing kidneys can't help fight an infection you already have: it worsens
faster and clears slower. blood_filtration slots in as a multiplier parallel
to ``InfectionCondition.environmental_modifier``. These tests capture the
hazard actually handed to ``hazard_fires`` so the scaling is verified
deterministically (no reliance on the random roll).

Run via::

    evennia test --keepdb world.tests.test_blood_filtration_infection
"""

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

import world.medical.conditions as C
from world.medical.conditions import (
    BLOOD_FILTRATION_HEAL_FLOOR,
    InfectionCondition,
    read_blood_filtration,
)
from world.medical.constants import (
    INFECTION_IMPROVE_HAZARD_PER_MINUTE,
    INFECTION_WORSEN_HAZARD_PER_MINUTE,
)


def _char(filtration=1.0, medical=True):
    state = None
    if medical:
        state = SimpleNamespace(
            calculate_body_capacity=lambda n: (
                filtration if n == "blood_filtration" else 1.0
            )
        )
    return SimpleNamespace(key="Patient", medical_state=state)


def _captured_hazard(condition, character):
    """Run one tick with hazard_fires stubbed to record (and not fire)."""
    recorded = []
    with patch.object(
        C, "hazard_fires", side_effect=lambda p, t: recorded.append(p) or False
    ), patch("world.combat.debug.get_splattercast", return_value=MagicMock()):
        condition.tick_effect(character, elapsed_minutes=1.0)
    return recorded[0]


class ReadBloodFiltrationTests(TestCase):
    def test_returns_value(self):
        self.assertEqual(read_blood_filtration(_char(0.5)), 0.5)

    def test_no_medical_model_none(self):
        self.assertIsNone(read_blood_filtration(_char(medical=False)))

    def test_non_numeric_fails_open(self):
        # A MagicMock capacity (test stub) must not be treated as a number.
        ch = SimpleNamespace(medical_state=MagicMock())
        self.assertIsNone(read_blood_filtration(ch))


class WorsenScalingTests(TestCase):
    def _worsen(self, filtration, medical=True):
        cond = InfectionCondition(severity=3)
        cond.treated = False
        return _captured_hazard(cond, _char(filtration, medical))

    def test_healthy_filtration_no_change(self):
        self.assertAlmostEqual(self._worsen(1.0), INFECTION_WORSEN_HAZARD_PER_MINUTE)

    def test_one_kidney_worsens_50pct_faster(self):
        self.assertAlmostEqual(
            self._worsen(0.5), INFECTION_WORSEN_HAZARD_PER_MINUTE * 1.5
        )

    def test_no_kidneys_worsens_double(self):
        self.assertAlmostEqual(
            self._worsen(0.0), INFECTION_WORSEN_HAZARD_PER_MINUTE * 2.0
        )

    def test_no_medical_model_unscaled(self):
        self.assertAlmostEqual(
            self._worsen(0.0, medical=False), INFECTION_WORSEN_HAZARD_PER_MINUTE
        )

    def test_environmental_modifier_still_applies(self):
        cond = InfectionCondition(severity=3)
        cond.treated = False
        cond.set_environmental_modifier(3.0)  # sewers
        hazard = _captured_hazard(cond, _char(0.5))
        self.assertAlmostEqual(
            hazard, INFECTION_WORSEN_HAZARD_PER_MINUTE * 3.0 * 1.5
        )


class HealScalingTests(TestCase):
    def _heal(self, filtration, medical=True):
        cond = InfectionCondition(severity=3)
        cond.treated = True
        return _captured_hazard(cond, _char(filtration, medical))

    def test_healthy_filtration_full_heal(self):
        self.assertAlmostEqual(self._heal(1.0), INFECTION_IMPROVE_HAZARD_PER_MINUTE)

    def test_one_kidney_heals_slower(self):
        self.assertAlmostEqual(
            self._heal(0.5), INFECTION_IMPROVE_HAZARD_PER_MINUTE * 0.5
        )

    def test_clearance_floor(self):
        # Even near-zero filtration never stalls below the floor.
        self.assertAlmostEqual(
            self._heal(0.0),
            INFECTION_IMPROVE_HAZARD_PER_MINUTE * BLOOD_FILTRATION_HEAL_FLOOR,
        )

    def test_no_medical_model_unscaled(self):
        self.assertAlmostEqual(
            self._heal(0.0, medical=False), INFECTION_IMPROVE_HAZARD_PER_MINUTE
        )
