"""Tests for damage → condition creation (issue #495).

Pins the trigger vocabulary so ghost damage types can't silently
disable a condition again — the old infection gate listed
'blade'/'pierce', which no caller ever sends, leaving only bullets
able to infect.

Run via::

    evennia test --settings settings.py world.tests.test_condition_creation
"""

from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

from world.medical.conditions import create_condition_from_damage


def _types(conditions):
    return [c.condition_type for c in conditions]


class TestInfectionTrigger(TestCase):
    @patch("world.medical.conditions.random.randint", return_value=1)
    def test_heavy_penetrating_wounds_can_infect(self, _r):
        """All real penetrating types infect on a heavy hit (interim
        random model; future model is circumstantial — treatment
        quality, environment, retained foreign bodies)."""
        for dtype in ("bullet", "cut", "stab", "laceration"):
            conditions = create_condition_from_damage(10, dtype, "chest")
            self.assertIn("infection", _types(conditions), dtype)

    @patch("world.medical.conditions.random.randint", return_value=1)
    def test_blunt_does_not_infect(self, _r):
        """Closed trauma doesn't break skin — no infection path."""
        conditions = create_condition_from_damage(10, "blunt", "chest")
        self.assertNotIn("infection", _types(conditions))

    @patch("world.medical.conditions.random.randint", return_value=1)
    def test_light_wounds_do_not_infect(self, _r):
        conditions = create_condition_from_damage(5, "cut", "chest")
        self.assertNotIn("infection", _types(conditions))

    @patch("world.medical.conditions.random.randint", return_value=100)
    def test_infection_is_chance_based(self, _r):
        """Roll of 100 > 25 → heavy cut, no infection this time."""
        conditions = create_condition_from_damage(10, "cut", "chest")
        self.assertNotIn("infection", _types(conditions))


class TestBaselineConditions(TestCase):
    @patch("world.medical.conditions.random.randint", return_value=100)
    def test_any_damage_produces_pain(self, _r):
        conditions = create_condition_from_damage(3, "blunt", "left_arm")
        self.assertIn("pain", _types(conditions))

    @patch("world.medical.conditions.random.randint", return_value=100)
    def test_heavy_damage_produces_bleeding(self, _r):
        conditions = create_condition_from_damage(10, "cut", "left_arm")
        self.assertIn("minor_bleeding", _types(conditions))
