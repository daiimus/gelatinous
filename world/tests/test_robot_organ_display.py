"""Tests for species-aware organ display names — a living robot's organs
read mechanically (processor core, power core, optical sensors) via the
per-species ``organ_display`` override on ``get_organ_display_name``.
"""

from __future__ import annotations

from unittest import TestCase

from world.anatomy.organs import get_organ_display_name
from world.anatomy.species import SPECIES_DEFINITIONS

ROBOT = SPECIES_DEFINITIONS["robot"]


class TestRobotOrganDisplay(TestCase):
    def test_species_override_renames_components(self):
        self.assertEqual(get_organ_display_name("brain", "robot"), "processor core")
        self.assertEqual(get_organ_display_name("heart", "robot"), "power core")
        self.assertEqual(get_organ_display_name("left_eye", "robot"), "left optical sensor")
        self.assertEqual(get_organ_display_name("right_ear", "robot"), "right audio sensor")
        self.assertEqual(get_organ_display_name("left_femur", "robot"), "left thigh strut")

    def test_override_covers_every_robot_organ(self):
        # No living robot organ should fall back to an organic name.
        override = ROBOT["organ_display"]
        for organ_name in ROBOT["organs"]:
            self.assertIn(organ_name, override, f"{organ_name} has no mechanical name")

    def test_human_and_none_fall_back_to_organic(self):
        self.assertEqual(get_organ_display_name("brain", "human"), "brain")
        self.assertEqual(get_organ_display_name("brain"), "brain")
        self.assertEqual(get_organ_display_name("left_eye", None), "left eye")

    def test_synth_unaffected(self):
        # Synth has no organ_display override → still organic names.
        self.assertEqual(get_organ_display_name("brain", "synthetic_humanoid"), "brain")

    def test_unmapped_organ_defensive_fallback(self):
        # Unknown organ on a robot falls back to the stripped key.
        self.assertEqual(
            get_organ_display_name("nonexistent_organ", "robot"), "nonexistent organ")
