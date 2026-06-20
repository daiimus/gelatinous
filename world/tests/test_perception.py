"""
Tests for perception gating (CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC §5).

``world/perception.py`` reports which sense categories a looker can receive,
from their ``sight`` / ``hearing`` capacities. The weather and crowd ambient
renderers consume it to drop content the looker can't perceive.

Run via::

    evennia test --keepdb world.tests.test_perception
"""

from unittest import TestCase

from world.perception import (
    AUDITORY_SENSE,
    OLFACTORY_SENSE,
    VISUAL_SENSE,
    blocked_senses,
    can_perceive_sense,
    filter_sensory_keys,
    has_reduced_perception,
)


class _MedState:
    def __init__(self, sight=1.0, hearing=1.0, smell=1.0):
        self._caps = {"sight": sight, "hearing": hearing, "smell": smell}

    def calculate_body_capacity(self, name):
        return self._caps.get(name, 1.0)

    def get_conditions_by_type(self, condition_type):
        return []


class _Looker:
    def __init__(self, sight=1.0, hearing=1.0, smell=1.0, medical=True):
        self.medical_state = (
            _MedState(sight, hearing, smell) if medical else None
        )


ALL_SENSES = ["visual", "auditory", "olfactory", "tactile", "atmospheric"]


class BlockedSensesTests(TestCase):
    def test_full_senses_block_nothing(self):
        self.assertEqual(blocked_senses(_Looker()), set())

    def test_blind_blocks_visual_only(self):
        self.assertEqual(blocked_senses(_Looker(sight=0.0)), {VISUAL_SENSE})

    def test_deaf_blocks_auditory_only(self):
        self.assertEqual(blocked_senses(_Looker(hearing=0.0)), {AUDITORY_SENSE})

    def test_blind_and_deaf_blocks_both(self):
        self.assertEqual(
            blocked_senses(_Looker(sight=0.0, hearing=0.0)),
            {VISUAL_SENSE, AUDITORY_SENSE},
        )

    def test_one_eye_one_ear_block_nothing(self):
        self.assertEqual(blocked_senses(_Looker(sight=0.5, hearing=0.5)), set())

    def test_no_nose_blocks_olfactory_only(self):
        self.assertEqual(blocked_senses(_Looker(smell=0.0)), {OLFACTORY_SENSE})

    def test_blind_and_anosmic_blocks_both(self):
        self.assertEqual(
            blocked_senses(_Looker(sight=0.0, smell=0.0)),
            {VISUAL_SENSE, OLFACTORY_SENSE},
        )

    def test_none_looker_blocks_nothing(self):
        self.assertEqual(blocked_senses(None), set())

    def test_no_medical_model_fails_open(self):
        self.assertEqual(blocked_senses(_Looker(medical=False)), set())


class CanPerceiveSenseTests(TestCase):
    def test_blind_cannot_perceive_visual_but_others_ok(self):
        looker = _Looker(sight=0.0)
        self.assertFalse(can_perceive_sense(looker, "visual"))
        self.assertTrue(can_perceive_sense(looker, "auditory"))
        self.assertTrue(can_perceive_sense(looker, "olfactory"))
        self.assertTrue(can_perceive_sense(looker, "atmospheric"))

    def test_deaf_cannot_perceive_auditory(self):
        looker = _Looker(hearing=0.0)
        self.assertFalse(can_perceive_sense(looker, "auditory"))
        self.assertTrue(can_perceive_sense(looker, "visual"))

    def test_anosmic_cannot_perceive_olfactory_but_others_ok(self):
        looker = _Looker(smell=0.0)
        self.assertFalse(can_perceive_sense(looker, "olfactory"))
        self.assertTrue(can_perceive_sense(looker, "visual"))
        self.assertTrue(can_perceive_sense(looker, "tactile"))


class FilterSensoryKeysTests(TestCase):
    def test_blind_drops_visual_key(self):
        looker = _Looker(sight=0.0)
        self.assertEqual(
            filter_sensory_keys(looker, ALL_SENSES),
            ["auditory", "olfactory", "tactile", "atmospheric"],
        )

    def test_full_senses_keep_everything(self):
        self.assertEqual(filter_sensory_keys(_Looker(), ALL_SENSES), ALL_SENSES)

    def test_blind_deaf_keeps_unaffected_senses(self):
        looker = _Looker(sight=0.0, hearing=0.0)
        self.assertEqual(
            filter_sensory_keys(looker, ALL_SENSES),
            ["olfactory", "tactile", "atmospheric"],
        )


class HasReducedPerceptionTests(TestCase):
    def test_full_senses_not_reduced(self):
        self.assertFalse(has_reduced_perception(_Looker()))

    def test_missing_sense_is_reduced(self):
        self.assertTrue(has_reduced_perception(_Looker(sight=0.0)))
        self.assertTrue(has_reduced_perception(_Looker(hearing=0.0)))
