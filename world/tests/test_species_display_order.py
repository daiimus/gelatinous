"""Tests for species-keyed display order and default longdesc surfaces
(issue #356 Phase 3).
"""

from __future__ import annotations

from unittest import TestCase

from world.anatomy import (
    get_species_anatomical_display_order,
    get_species_anatomical_regions,
    get_species_default_longdesc_locations,
)
from world.anatomy.species import SPECIES_DEFINITIONS
from world.combat.constants import (
    ANATOMICAL_DISPLAY_ORDER,
    ANATOMICAL_REGIONS,
    DEFAULT_LONGDESC_LOCATIONS,
)


class HumanTablesMatchLegacyGlobals(TestCase):

    def test_anatomical_display_order_matches(self):
        self.assertEqual(
            get_species_anatomical_display_order("human"),
            ANATOMICAL_DISPLAY_ORDER,
        )

    def test_anatomical_regions_matches(self):
        self.assertEqual(
            get_species_anatomical_regions("human"),
            ANATOMICAL_REGIONS,
        )

    def test_default_longdesc_locations_matches(self):
        self.assertEqual(
            get_species_default_longdesc_locations("human"),
            DEFAULT_LONGDESC_LOCATIONS,
        )


class FallbackToHumanOnUnknown(TestCase):

    def test_unknown_species_falls_back(self):
        self.assertEqual(
            get_species_anatomical_display_order("alien_xyz"),
            get_species_anatomical_display_order("human"),
        )


class NoAliasingOnReturnedData(TestCase):

    def test_display_order_mutation_isolated(self):
        order = get_species_anatomical_display_order("human")
        order.append("test_loc")
        self.assertNotIn(
            "test_loc",
            get_species_anatomical_display_order("human"),
        )

    def test_regions_mutation_isolated(self):
        regions = get_species_anatomical_regions("human")
        regions["test_region"] = ["test_loc"]
        self.assertNotIn(
            "test_region",
            get_species_anatomical_regions("human"),
        )

    def test_default_longdesc_mutation_isolated(self):
        defaults = get_species_default_longdesc_locations("human")
        defaults["test_loc"] = "test"
        self.assertNotIn(
            "test_loc",
            get_species_default_longdesc_locations("human"),
        )


class AdHocRatStubProducesDifferentTables(TestCase):
    """A rat declares a tail at the end of display order, snout/fur in
    place of face/hair, and a smaller longdesc default set."""

    def setUp(self):
        SPECIES_DEFINITIONS["_test_rat"] = {
            "display_name": "test rat",
            "location_display": {},
            "decay_part_prefixes": {},
            "decay_organ_prefixes": {},
            "decay_corpse_names": {},
            "decay_corpse_descriptions": {},
            "pair_keys": {},
            "anatomical_display_order": [
                "fur", "left_eye", "right_eye", "head", "snout",
                "left_ear", "right_ear", "neck",
                "chest", "abdomen",
                "left_foreleg", "right_foreleg",
                "left_forepaw", "right_forepaw",
                "left_hindleg", "right_hindleg",
                "left_hindpaw", "right_hindpaw",
                "tail",
            ],
            "anatomical_regions": {
                "head_region": ["fur", "left_eye", "right_eye", "head",
                                "snout", "left_ear", "right_ear", "neck"],
                "torso_region": ["chest", "abdomen"],
                "foreleg_region": ["left_foreleg", "right_foreleg",
                                   "left_forepaw", "right_forepaw"],
                "hindleg_region": ["left_hindleg", "right_hindleg",
                                   "left_hindpaw", "right_hindpaw"],
                "tail_region": ["tail"],
            },
            "default_longdesc_locations": {
                loc: None for loc in (
                    "fur", "left_eye", "right_eye", "snout", "neck",
                    "chest", "abdomen",
                    "left_foreleg", "right_foreleg",
                    "left_hindleg", "right_hindleg",
                    "tail",
                )
            },
        }

    def tearDown(self):
        del SPECIES_DEFINITIONS["_test_rat"]

    def test_rat_tail_at_end_of_display_order(self):
        order = get_species_anatomical_display_order("_test_rat")
        self.assertEqual(order[-1], "tail")

    def test_rat_uses_snout_not_face_in_display(self):
        order = get_species_anatomical_display_order("_test_rat")
        self.assertIn("snout", order)
        self.assertIn("fur", order)
        self.assertNotIn("face", order)
        self.assertNotIn("hair", order)

    def test_rat_regions_drop_humanoid_arm_leg(self):
        regions = get_species_anatomical_regions("_test_rat")
        # Rat-specific regions present.
        self.assertIn("foreleg_region", regions)
        self.assertIn("hindleg_region", regions)
        self.assertIn("tail_region", regions)
        # Humanoid-specific regions absent.
        self.assertNotIn("arm_region", regions)
        self.assertNotIn("leg_region", regions)

    def test_rat_default_longdesc_has_tail(self):
        defaults = get_species_default_longdesc_locations("_test_rat")
        self.assertIn("tail", defaults)
        self.assertNotIn("left_arm", defaults)
        self.assertNotIn("face", defaults)
