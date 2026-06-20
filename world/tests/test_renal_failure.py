"""
Tests for the RenalFailure chronic condition
(CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC §7.2).

Total kidney loss → chronic uremia: spawned/cleared from blood_filtration,
obtunds (consciousness penalty), slowly kills (uremic decline via the existing
blood-loss death floor), and shows a uremic skin tint (§7.3 hook). The
spawn/clear decision is unit-tested against a fake state (the live path needs a
full Character + ticker); the condition's own behaviour is tested directly.

Run via::

    evennia test --keepdb world.tests.test_renal_failure
"""

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import world.medical.conditions as C
from world.medical.conditions import (
    RENAL_FAILURE_DECLINE_PER_TICK,
    RENAL_FAILURE_LETHAL_SEVERITY,
    RENAL_FAILURE_MAX_CONSCIOUSNESS_PENALTY,
    RenalFailureCondition,
    deserialize_condition,
)
from world.medical.core import MedicalState
from world.medical.appearance import SYMPTOM_TINTS, get_appearance_tint


class RenalFailureBehaviourTests(TestCase):
    def test_consciousness_penalty_scales_and_caps(self):
        self.assertAlmostEqual(RenalFailureCondition(severity=1).get_consciousness_penalty(), 0.06)
        self.assertAlmostEqual(RenalFailureCondition(severity=5).get_consciousness_penalty(), 0.30)
        self.assertAlmostEqual(
            RenalFailureCondition(severity=10).get_consciousness_penalty(),
            RENAL_FAILURE_MAX_CONSCIOUSNESS_PENALTY,
        )

    def test_blood_loss_only_when_terminal(self):
        self.assertEqual(
            RenalFailureCondition(severity=RENAL_FAILURE_LETHAL_SEVERITY - 1).get_blood_loss_rate(),
            0.0,
        )
        self.assertAlmostEqual(
            RenalFailureCondition(severity=RENAL_FAILURE_LETHAL_SEVERITY).get_blood_loss_rate(),
            RENAL_FAILURE_DECLINE_PER_TICK,
        )

    def test_appearance_symptom_is_uremic(self):
        self.assertEqual(RenalFailureCondition().appearance_symptom(), "uremic")

    def test_does_not_self_resolve(self):
        self.assertFalse(RenalFailureCondition(severity=1).should_end())

    def test_tick_ramps_severity(self):
        cond = RenalFailureCondition(severity=3)
        with patch.object(C, "hazard_fires", return_value=True):
            cond.tick_effect(SimpleNamespace(key="P"), elapsed_minutes=1.0)
        self.assertEqual(cond.severity, 4)

    def test_round_trips_through_factory(self):
        cond = RenalFailureCondition(severity=6)
        restored = deserialize_condition(cond.to_dict())
        self.assertIsInstance(restored, RenalFailureCondition)
        self.assertEqual(restored.severity, 6)
        self.assertEqual(restored.condition_type, "renal_failure")


class _FakeState:
    """Minimal stand-in exposing what _update_renal_failure touches."""
    def __init__(self, filtration, existing=()):
        self._filtration = filtration
        self._existing = list(existing)
        self.added = []
        self.removed = []

    def calculate_body_capacity(self, name):
        return self._filtration

    def get_conditions_by_type(self, condition_type):
        return list(self._existing) if condition_type == "renal_failure" else []

    def add_condition(self, condition):
        self.added.append(condition)

    def remove_condition(self, condition):
        self.removed.append(condition)


class RenalFailureSpawnLogicTests(TestCase):
    def _run(self, filtration, existing=()):
        st = _FakeState(filtration, existing)
        MedicalState._update_renal_failure(st)
        return st

    def test_onset_when_both_kidneys_gone(self):
        st = self._run(0.0)
        self.assertEqual(len(st.added), 1)
        self.assertIsInstance(st.added[0], RenalFailureCondition)
        self.assertEqual(st.removed, [])

    def test_idempotent_when_already_present(self):
        st = self._run(0.0, existing=[RenalFailureCondition()])
        self.assertEqual(st.added, [])

    def test_one_kidney_does_not_onset(self):
        st = self._run(0.5)
        self.assertEqual(st.added, [])

    def test_recovery_clears_when_filtration_restored(self):
        cond = RenalFailureCondition(severity=5)
        st = self._run(0.5, existing=[cond])
        self.assertEqual(st.removed, [cond])

    def test_hysteresis_dead_zone_neither_spawns_nor_clears(self):
        # Between onset (0.05) and recovery (0.4): leave the condition alone.
        cond = RenalFailureCondition(severity=5)
        st = self._run(0.2, existing=[cond])
        self.assertEqual(st.added, [])
        self.assertEqual(st.removed, [])


class RenalFailureAppearanceTests(TestCase):
    def test_renal_failure_tints_uremic(self):
        char = SimpleNamespace(medical_state=SimpleNamespace(
            calculate_body_capacity=lambda n: 1.0,
            blood_level=100.0,
            conditions=[RenalFailureCondition(severity=3)],
        ))
        self.assertEqual(get_appearance_tint(char), SYMPTOM_TINTS["uremic"])
