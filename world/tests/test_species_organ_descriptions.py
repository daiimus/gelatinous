"""Tests for species-aware organ descriptions (robot / synth) and synth
organ names — a harvested "power core" / "synthetic heart" reads in its
own register, not as a glistening muscle.
"""

from __future__ import annotations

from unittest import TestCase

from world.anatomy import get_species_organ_name
from world.anatomy.organs import (
    ORGAN_DISPLAY,
    get_organ_default_description,
    get_organ_display_name,
)


def _organs_with_desc():
    return {
        k: list((v.get("default_descriptions") or {}).keys())
        for k, v in ORGAN_DISPLAY.items()
        if v.get("default_descriptions")
    }


class TestSpeciesOrganDescriptions(TestCase):
    def test_robot_covers_every_organic_description(self):
        for organ, conds in _organs_with_desc().items():
            for c in conds:
                self.assertTrue(
                    get_organ_default_description(organ, c, "robot"),
                    f"robot missing description for {organ}/{c}")

    def test_synth_covers_every_organic_description(self):
        for organ, conds in _organs_with_desc().items():
            for c in conds:
                self.assertTrue(
                    get_organ_default_description(
                        organ, c, "synthetic_humanoid"),
                    f"synth missing description for {organ}/{c}")

    def test_robot_descriptions_are_mechanical(self):
        d = get_organ_default_description("heart", "pristine", "robot")
        self.assertIn("power core", d.lower())
        self.assertNotIn("muscle", d.lower())
        # paired side substitution worked
        self.assertIn("left", get_organ_default_description(
            "left_eye", "pristine", "robot").lower())

    def test_synth_descriptions_are_synthetic(self):
        d = get_organ_default_description("heart", "pristine", "synthetic_humanoid")
        self.assertIn("synthetic", d.lower())
        self.assertIn("cobalt", get_organ_default_description(
            "liver", "damaged", "synthetic_humanoid").lower())

    def test_human_and_none_unchanged(self):
        organic = get_organ_default_description("heart", "pristine")
        self.assertTrue(organic)
        self.assertEqual(
            get_organ_default_description("heart", "pristine", "human"), organic)


class TestSynthOrganNames(TestCase):
    def test_synth_organ_display_names(self):
        self.assertEqual(
            get_organ_display_name("heart", "synthetic_humanoid"),
            "vat-heart")   # wetware register
        self.assertEqual(
            get_organ_display_name("left_eye", "synthetic_humanoid"),
            "synthetic left eye")

    def test_synth_severed_name_no_double_synth(self):
        name = get_species_organ_name("synthetic_humanoid", "heart", "fresh")
        self.assertEqual(name, "vat-heart")
        self.assertNotIn("synth synthetic", name)

    def test_synth_severed_decay_tiers(self):
        self.assertEqual(
            get_species_organ_name("synthetic_humanoid", "brain", "advanced"),
            "inert wetcore")
        self.assertEqual(
            get_species_organ_name("synthetic_humanoid", "brain", "skeletal"),
            "desiccated wetcore")
