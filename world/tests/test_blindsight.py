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

from world.combat.capacity import sight_hit_factor, _blindsight_active
from world.perception import can_see
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
        self.db = SimpleNamespace()
        self.medical_state = _Med(sight)
        self.organ = _Organ("blindsight", "blindsight")
        self.medical_state.organs = {"suite": self.organ}
        if blindsight:
            _toggle_blindsight(self, self.organ, "blindsight", {})


class _Organ:
    """A living host organ. `iter_abilities` needs `current_hp`,
    `data["abilities"]` and `ability_state` — a bare object with only
    `ability_state` looks like a body with no cyberware at all now that
    the effect is derived from the organ (#2484)."""

    def __init__(self, ability, ability_type, hp=10):
        self.current_hp = hp
        self.container = "head"
        self.data = {"abilities": {ability: {"type": ability_type}}}
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
    def test_toggle_engages_and_disengages(self):
        ch = _Char()
        organ = ch.organ
        self.assertFalse(_blindsight_active(ch))

        _toggle_blindsight(ch, organ, "blindsight", {})
        self.assertTrue(_blindsight_active(ch))
        self.assertTrue(organ.ability_state["blindsight"]["deployed"])

        _toggle_blindsight(ch, organ, "blindsight", {})
        self.assertFalse(_blindsight_active(ch))
        self.assertFalse(organ.ability_state["blindsight"]["deployed"])

    def test_a_destroyed_module_stops_driving_it(self):
        """No teardown hook runs when the module is simply shot out, so
        derivation is the only thing that ends the effect (#2484)."""
        ch = _Char()
        _toggle_blindsight(ch, ch.organ, "blindsight", {})
        self.assertTrue(_blindsight_active(ch))
        ch.organ.current_hp = 0
        self.assertFalse(_blindsight_active(ch))
        self.assertAlmostEqual(sight_hit_factor(ch, is_ranged=True), 1.0)

    def test_custom_messages(self):
        ch = _Char()
        organ = ch.organ
        spec = {"deploy_msg": "ON", "retract_msg": "OFF"}
        self.assertEqual(_toggle_blindsight(ch, organ, "blindsight", spec), "ON")
        self.assertEqual(_toggle_blindsight(ch, organ, "blindsight", spec), "OFF")
