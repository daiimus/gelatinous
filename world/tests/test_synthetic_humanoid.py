"""Tests for the Synthetic Humanoid species (replicant/Synth).

Derived from human via deepcopy + targeted overrides: human MECHANICS
(organs, capacities, severability, death model all inherit) with a
synthetic PRESENTATION — a touch more durable, and a body that goes
inert rather than rotting. Appendage names stay humanoid.
"""

from __future__ import annotations

from unittest import TestCase

from world.anatomy import (
    get_species_corpse_description,
    get_species_corpse_name,
)
from world.anatomy.species import SPECIES_DEFINITIONS
from world.combat.constants import SKINTONE_PALETTE, VALID_SKINTONES

HUMAN = SPECIES_DEFINITIONS["human"]
SYNTH = SPECIES_DEFINITIONS["synthetic_humanoid"]


class TestSyntheticHumanoid(TestCase):
    def test_registered_with_display_name(self):
        self.assertIn("synthetic_humanoid", SPECIES_DEFINITIONS)
        self.assertEqual(SYNTH["display_name"], "synthetic humanoid")

    def test_inherits_human_mechanics(self):
        # Same organ keys, severability, and capacity wiring → the
        # capacity-derived death model behaves identically to human.
        self.assertEqual(set(SYNTH["organs"]), set(HUMAN["organs"]))
        self.assertEqual(SYNTH["severable_containers"],
                         HUMAN["severable_containers"])
        self.assertEqual(SYNTH["body_capacities"], HUMAN["body_capacities"])
        self.assertEqual(SYNTH["grasping_containers"],
                         HUMAN["grasping_containers"])
        self.assertEqual(SYNTH["limb_downstream_chain"],
                         HUMAN["limb_downstream_chain"])

    def test_appendages_keep_humanoid_names(self):
        self.assertEqual(SYNTH["location_display"]["left_hand"], "left hand")
        self.assertEqual(SYNTH["severed_chain_display"]["left_thigh"], "left leg")

    def test_organs_are_more_durable(self):
        for key, organ in SYNTH["organs"].items():
            self.assertGreater(organ["max_hp"], HUMAN["organs"][key]["max_hp"],
                               f"{key} should be tougher than human")
        self.assertEqual(SYNTH["organs"]["heart"]["max_hp"], 19)  # round(15*1.25)

    def test_corpse_does_not_rot(self):
        self.assertEqual(
            get_species_corpse_name("synthetic_humanoid", "fresh"),
            "deactivated synthetic")
        self.assertEqual(
            get_species_corpse_name("synthetic_humanoid", "skeletal"),
            "stripped synthetic frame")
        for stage in ("moderate", "advanced", "skeletal"):
            name = get_species_corpse_name("synthetic_humanoid", stage)
            self.assertNotIn("rotting", name)
            self.assertNotIn("skeletal remains", name)

    def test_corpse_description_is_synthetic_and_non_decaying(self):
        fresh = get_species_corpse_description(
            "synthetic_humanoid", "fresh", "It wore a grey coat.")
        self.assertIn("synthetic", fresh.lower())
        self.assertIn("It wore a grey coat.", fresh)
        moderate = get_species_corpse_description("synthetic_humanoid", "moderate")
        self.assertNotIn("decompos", moderate.lower())
        self.assertIn("does not rot", moderate.lower())

    def test_derivation_does_not_mutate_human(self):
        # deepcopy → the human definition is untouched by the overrides.
        self.assertEqual(HUMAN["organs"]["heart"]["max_hp"], 15)
        self.assertEqual(get_species_corpse_name("human", "skeletal"),
                         "skeletal remains")

    def test_alien_skintones_registered(self):
        for tone in ("alabaster", "ashen", "slate", "jade", "cobalt", "chrome"):
            self.assertIn(tone, SKINTONE_PALETTE)
            self.assertIn(tone, VALID_SKINTONES)
        self.assertIn("tan", SKINTONE_PALETTE)  # human tones still present
