"""
Tests for condition-driven appearance symptoms
(CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC §7.3).

A character's medical state tints their rendered skintone — sick looks sick.
Symptoms come from capacities/vitals (cyanosis, pallor) and from any condition
exposing ``appearance_symptom()`` (the cross-cutting hook). The dominant one
(by clinical priority) wins.

Run via::

    evennia test --keepdb world.tests.test_condition_appearance
"""

from types import SimpleNamespace
from unittest import TestCase

from world.medical.appearance import (
    SYMPTOM_TINTS,
    get_active_symptom,
    get_appearance_tint,
)


class _Cond:
    def __init__(self, symptom):
        self._symptom = symptom

    def appearance_symptom(self):
        return self._symptom


def _char(breathing=1.0, blood=100.0, conditions=(), medical=True):
    if not medical:
        return SimpleNamespace(medical_state=None)
    state = SimpleNamespace(
        calculate_body_capacity=lambda n: breathing if n == "breathing" else 1.0,
        blood_level=blood,
        conditions=list(conditions),
    )
    return SimpleNamespace(medical_state=state)


class CapacityDrivenSymptomTests(TestCase):
    def test_healthy_no_symptom(self):
        self.assertIsNone(get_active_symptom(_char()))
        self.assertIsNone(get_appearance_tint(_char()))

    def test_failing_breathing_is_cyanosis(self):
        ch = _char(breathing=0.3)
        self.assertEqual(get_active_symptom(ch), "cyanosis")
        self.assertEqual(get_appearance_tint(ch), SYMPTOM_TINTS["cyanosis"])

    def test_blood_loss_is_pallor(self):
        ch = _char(blood=90.0)
        self.assertEqual(get_active_symptom(ch), "pallor")

    def test_one_lung_boundary(self):
        # Exactly at threshold is NOT cyanotic (strict less-than).
        self.assertIsNone(get_active_symptom(_char(breathing=0.5)))
        self.assertEqual(get_active_symptom(_char(breathing=0.49)), "cyanosis")


class ConditionDrivenSymptomTests(TestCase):
    def test_condition_supplies_symptom(self):
        ch = _char(conditions=[_Cond("uremic")])
        self.assertEqual(get_active_symptom(ch), "uremic")
        self.assertEqual(get_appearance_tint(ch), SYMPTOM_TINTS["uremic"])

    def test_unranked_condition_symptom_still_shows(self):
        ch = _char(conditions=[_Cond("jaundice")])
        self.assertEqual(get_active_symptom(ch), "jaundice")

    def test_condition_without_hook_ignored(self):
        ch = _char(conditions=[SimpleNamespace()])  # no appearance_symptom
        self.assertIsNone(get_active_symptom(ch))


class PriorityTests(TestCase):
    def test_cyanosis_beats_pallor(self):
        ch = _char(breathing=0.3, blood=90.0)  # both present
        self.assertEqual(get_active_symptom(ch), "cyanosis")

    def test_pallor_beats_uremic(self):
        ch = _char(blood=90.0, conditions=[_Cond("uremic")])
        self.assertEqual(get_active_symptom(ch), "pallor")


class FailOpenTests(TestCase):
    def test_no_medical_model(self):
        self.assertIsNone(get_appearance_tint(_char(medical=False)))

    def test_broken_state_does_not_raise(self):
        class _Boom:
            @property
            def conditions(self):
                raise RuntimeError("boom")
        ch = SimpleNamespace(medical_state=_Boom())
        # get_appearance_tint swallows errors → no tint, never raises.
        self.assertIsNone(get_appearance_tint(ch))
