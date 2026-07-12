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

    def test_synth_has_its_own_names(self):
        # Synth now carries "synthetic <organ>" names (a distinct register
        # from the robot's mechanical components).
        self.assertEqual(
            get_organ_display_name("brain", "synthetic_humanoid"),
            "wetcore")   # the wetware register (2026-07-12)

    def test_unmapped_organ_defensive_fallback(self):
        # Unknown organ on a robot falls back to the stripped key.
        self.assertEqual(
            get_organ_display_name("nonexistent_organ", "robot"), "nonexistent organ")


class TestSynthWetwareRegister(TestCase):
    """The wetware register (2026-07-12): the synth's soft core reads as
    engineered tissue; bones, senses, and the form stay 'synthetic X';
    humans are untouched."""

    def test_soft_core_is_wetware(self):
        from world.anatomy.organs import get_organ_display_name
        s = "synthetic_humanoid"
        self.assertEqual(get_organ_display_name("brain", s), "wetcore")
        self.assertEqual(get_organ_display_name("heart", s), "vat-heart")
        self.assertEqual(get_organ_display_name("left_lung", s),
                         "left culture-lung")
        self.assertEqual(get_organ_display_name("liver", s), "filter gland")
        self.assertEqual(get_organ_display_name("right_kidney", s),
                         "right flush gland")
        self.assertEqual(get_organ_display_name("stomach", s), "culture gut")

    def test_form_visible_organs_stay_synthetic_prefixed(self):
        from world.anatomy.organs import get_organ_display_name
        s = "synthetic_humanoid"
        self.assertEqual(get_organ_display_name("left_eye", s),
                         "synthetic left eye")
        self.assertEqual(get_organ_display_name("jaw", s), "synthetic jaw")
        self.assertEqual(get_organ_display_name("left_femur", s),
                         "synthetic left femur")

    def test_humans_untouched(self):
        from world.anatomy.organs import get_organ_display_name
        self.assertEqual(get_organ_display_name("brain", "human"), "brain")
        self.assertEqual(get_organ_display_name("heart", "human"), "heart")

    def test_nothing_industrial_leaked(self):
        # the register guidance: engineered tissue, never machinery
        from world.anatomy.species import _SYNTH_WETWARE
        forbidden = ("pump", "processor", "unit", "module", "core ",
                     "engine", "motor", "filter unit")
        for noun in _SYNTH_WETWARE.values():
            for bad in forbidden:
                self.assertNotIn(bad, noun, noun)
