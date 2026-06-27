"""Tests for the Robot species (a fully mechanical humanoid chassis).

Derived from human via deepcopy + targeted overrides: human MECHANICS
(organs, capacities, severability, capacity-derived death model all
inherit — destroy the brain-slot processor or the heart-slot power core
and the unit deactivates) with a MECHANICAL presentation — tougher frame,
no biological infection, a body that is deactivated and stripped for
parts rather than rotting, and a distinct hydraulic fluid. Appendage
names stay humanoid (it is a humanoid robot).

The deeper "mechanical presentation" layer (per-organ inorganic prose,
component organ-name divergence, pruning breathing/blood_filtration) is a
deliberate follow-up, the same layer the synthetic species also defers.
"""

from __future__ import annotations

from unittest import TestCase

from world.anatomy import (
    get_species_blood_color,
    get_species_corpse_description,
    get_species_corpse_name,
    get_species_infection_immune,
)
from world.anatomy.species import SPECIES_DEFINITIONS
from world.medical.medical_messages import (
    get_bleeding_room_message, get_death_cause_template,
)

HUMAN = SPECIES_DEFINITIONS["human"]
ROBOT = SPECIES_DEFINITIONS["robot"]


class TestRobotSpecies(TestCase):
    def test_registered_with_display_name(self):
        self.assertIn("robot", SPECIES_DEFINITIONS)
        self.assertEqual(ROBOT["display_name"], "robot")

    def test_inherits_human_mechanics(self):
        # Same organ keys, severability, and capacity wiring → the
        # capacity-derived death model behaves identically to human
        # (processor core = brain slot; power core = heart slot).
        self.assertEqual(set(ROBOT["organs"]), set(HUMAN["organs"]))
        self.assertEqual(ROBOT["severable_containers"],
                         HUMAN["severable_containers"])
        self.assertEqual(ROBOT["body_capacities"], HUMAN["body_capacities"])
        self.assertEqual(ROBOT["grasping_containers"],
                         HUMAN["grasping_containers"])
        self.assertEqual(ROBOT["limb_downstream_chain"],
                         HUMAN["limb_downstream_chain"])

    def test_appendages_keep_humanoid_names(self):
        # A humanoid robot — arms/hands/legs, not "actuators" (yet).
        self.assertEqual(ROBOT["location_display"]["left_hand"], "left hand")
        self.assertEqual(ROBOT["severed_chain_display"]["left_thigh"], "left leg")

    def test_components_are_more_durable(self):
        for key, organ in ROBOT["organs"].items():
            self.assertGreater(organ["max_hp"], HUMAN["organs"][key]["max_hp"],
                               f"{key} should be tougher than human")
        # heart slot (power core): round(15 * 1.5) == 22
        self.assertEqual(ROBOT["organs"]["heart"]["max_hp"], 22)
        # brain slot (processor): round(10 * 1.5) == 15
        self.assertEqual(ROBOT["organs"]["brain"]["max_hp"], 15)

    def test_chassis_does_not_rot(self):
        self.assertEqual(
            get_species_corpse_name("robot", "fresh"), "deactivated robot")
        self.assertEqual(
            get_species_corpse_name("robot", "skeletal"), "stripped robot frame")
        for stage in ("moderate", "advanced", "skeletal"):
            name = get_species_corpse_name("robot", stage)
            self.assertNotIn("rotting", name)
            self.assertNotIn("skeletal remains", name)

    def test_corpse_description_is_mechanical_and_non_decaying(self):
        fresh = get_species_corpse_description(
            "robot", "fresh", "It wore a security vest.")
        self.assertIn("chassis", fresh.lower())
        self.assertIn("It wore a security vest.", fresh)
        moderate = get_species_corpse_description("robot", "moderate")
        self.assertNotIn("decompos", moderate.lower())
        self.assertIn("does not rot", moderate.lower())

    def test_derivation_does_not_mutate_human(self):
        # deepcopy → the human definition is untouched by the overrides.
        self.assertEqual(HUMAN["organs"]["heart"]["max_hp"], 15)
        self.assertEqual(get_species_corpse_name("human", "skeletal"),
                         "skeletal remains")


class TestRobotFluid(TestCase):
    def test_species_blood_color_is_amber(self):
        robot = get_species_blood_color("robot")
        self.assertEqual(robot["name"], "amber")
        self.assertEqual(robot["code"], "|y")
        # other species unaffected; unknown falls back to human crimson.
        self.assertEqual(get_species_blood_color("human")["name"], "crimson")
        self.assertEqual(get_species_blood_color(None)["name"], "crimson")

    def test_leak_prose_is_amber_not_crimson(self):
        msg = get_bleeding_room_message(10, "robot")
        self.assertIn("amber", msg.lower())
        self.assertNotIn("crimson", msg.lower())
        self.assertIn("crimson", get_bleeding_room_message(10, "human").lower())

    def test_death_prose_is_amber(self):
        self.assertIn(
            "amber",
            get_death_cause_template("blood loss", "robot").lower())


class TestRobotInfectionImmunity(TestCase):
    def test_species_flag(self):
        self.assertTrue(get_species_infection_immune("robot"))
        self.assertFalse(get_species_infection_immune("human"))
        self.assertFalse(get_species_infection_immune(None))
