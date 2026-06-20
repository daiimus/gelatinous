"""
Tests for combat blindsight — the targeting/sonar enhancer
(CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC enhancer seam; combat-only, decided
2026-06-20).

Restores combat AIM when the eyes are gone, but NOT perception — a blind
character with blindsight still can't see (rooms/faces stay dark). Toggled by
the targeting-processor augment ability.

Run via::

    evennia test --keepdb world.tests.test_blindsight
"""

from types import SimpleNamespace
from unittest import TestCase

from world.combat.capacity import sight_hit_factor, BLINDSIGHT_FLAG
from world.voice import can_see
from world.medical.augments import _toggle_blindsight


class _Med:
    def __init__(self, sight=1.0):
        self._sight = sight

    def calculate_body_capacity(self, name):
        return self._sight if name == "sight" else 1.0

    def get_conditions_by_type(self, condition_type):
        return []


class _Char:
    def __init__(self, sight=1.0, blindsight=False):
        self.key = "P"
        self.db = SimpleNamespace(blindsight_active=blindsight)
        self.medical_state = _Med(sight)


class _Organ:
    def __init__(self):
        self.ability_state = {}


class BlindsightRestoresAimTests(TestCase):
    def test_blind_without_blindsight_cannot_aim(self):
        self.assertLess(sight_hit_factor(_Char(sight=0.0), is_ranged=True), 0.1)

    def test_blind_with_blindsight_aims_full(self):
        ch = _Char(sight=0.0, blindsight=True)
        self.assertAlmostEqual(sight_hit_factor(ch, is_ranged=True), 1.0)
        self.assertAlmostEqual(sight_hit_factor(ch, is_ranged=False), 1.0)


class BlindsightIsCombatOnlyTests(TestCase):
    def test_blindsight_does_not_restore_perception(self):
        # The whole point: aim is restored, but the character still can't SEE.
        ch = _Char(sight=0.0, blindsight=True)
        self.assertAlmostEqual(sight_hit_factor(ch, is_ranged=True), 1.0)
        self.assertFalse(can_see(ch))  # rooms / faces stay dark


class BlindsightToggleTests(TestCase):
    def test_toggle_sets_and_clears_flag(self):
        ch, organ = _Char(), _Organ()
        self.assertFalse(getattr(ch.db, BLINDSIGHT_FLAG))

        _toggle_blindsight(ch, organ, "blindsight", {})
        self.assertTrue(getattr(ch.db, BLINDSIGHT_FLAG))
        self.assertTrue(organ.ability_state["blindsight"]["deployed"])

        _toggle_blindsight(ch, organ, "blindsight", {})
        self.assertFalse(getattr(ch.db, BLINDSIGHT_FLAG))
        self.assertFalse(organ.ability_state["blindsight"]["deployed"])

    def test_custom_messages(self):
        ch, organ = _Char(), _Organ()
        spec = {"deploy_msg": "ON", "retract_msg": "OFF"}
        self.assertEqual(_toggle_blindsight(ch, organ, "blindsight", spec), "ON")
        self.assertEqual(_toggle_blindsight(ch, organ, "blindsight", spec), "OFF")
