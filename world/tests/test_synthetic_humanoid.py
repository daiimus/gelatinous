"""Tests for the Synthetic Humanoid species (replicant/Synth).

Derived from human via deepcopy + targeted overrides: human MECHANICS
(organs, capacities, severability, death model all inherit) with a
synthetic PRESENTATION — a touch more durable, and a body that goes
inert rather than rotting. Appendage names stay humanoid.
"""

from __future__ import annotations

from unittest import TestCase

from unittest.mock import MagicMock

from world.anatomy import (
    get_species_blood_color,
    get_species_corpse_description,
    get_species_corpse_name,
    get_species_infection_immune,
)
from world.anatomy.species import SPECIES_DEFINITIONS
from world.combat.constants import SKINTONE_PALETTE, VALID_SKINTONES
from world.medical.medical_messages import (
    get_bleeding_room_message, get_death_cause_template,
)

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
        # Glance tokens use the short "synth" (decided over "synthetic humanoid").
        self.assertEqual(
            get_species_corpse_name("synthetic_humanoid", "fresh"),
            "deactivated synth")
        self.assertEqual(
            get_species_corpse_name("synthetic_humanoid", "skeletal"),
            "stripped synth frame")
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


class TestSyntheticBlood(TestCase):
    def test_species_blood_color(self):
        synth = get_species_blood_color("synthetic_humanoid")
        self.assertEqual(synth["name"], "cobalt")
        self.assertEqual(synth["code"], "|B")
        self.assertEqual(get_species_blood_color("human")["name"], "crimson")
        # field-less / unknown species fall back to human crimson.
        self.assertEqual(get_species_blood_color("rat")["name"], "crimson")
        self.assertEqual(get_species_blood_color(None)["name"], "crimson")

    def test_bleeding_prose_is_cobalt_not_crimson(self):
        msg = get_bleeding_room_message(10, "synthetic_humanoid")
        self.assertIn("cobalt", msg.lower())
        self.assertNotIn("crimson", msg.lower())
        # human is unaffected
        self.assertIn("crimson", get_bleeding_room_message(10, "human").lower())

    def test_death_prose_is_cobalt(self):
        self.assertIn("cobalt",
                      get_death_cause_template("blood loss",
                                               "synthetic_humanoid").lower())


class TestBloodPoolMixture(TestCase):
    """The pool renderer (no Evennia boot — bind methods to a stand-in)."""

    def _pool_with(self, *colors):
        from typeclasses.objects import BloodPool

        class _DB:
            pass

        pool = MagicMock()
        pool.db = _DB()
        pool.db.bleeding_incidents = [
            {"blood_color": c, "severity": 5, "timestamp": 0} for c in colors
        ]
        pool._DEFAULT_BLOOD_COLOR = BloodPool._DEFAULT_BLOOD_COLOR
        for m in ("_blood_colors", "_stain_word"):
            setattr(pool, m, getattr(BloodPool, m).__get__(pool, type(pool)))
        return pool

    def test_single_colour(self):
        pool = self._pool_with(get_species_blood_color("synthetic_humanoid"))
        self.assertEqual(pool._stain_word(), "|Bcobalt|n")

    def test_mixed_pool_is_visually_distinguishable(self):
        pool = self._pool_with(get_species_blood_color("human"),
                               get_species_blood_color("synthetic_humanoid"))
        word = pool._stain_word()
        self.assertIn("|Rcrimson|n", word)
        self.assertIn("|Bcobalt|n", word)
        self.assertIn(" and ", word)

    def test_same_species_not_double_counted(self):
        pool = self._pool_with(get_species_blood_color("human"),
                               get_species_blood_color("human"))
        self.assertEqual(pool._stain_word(), "|Rcrimson|n")

    def test_legacy_incident_defaults_to_crimson(self):
        pool = self._pool_with(None)
        self.assertEqual(pool._stain_word(), "|Rcrimson|n")
        self.assertEqual(pool._stain_word(aged=True), "|Rrust-brown|n")


class TestSyntheticInfectionImmunity(TestCase):
    def test_species_flag(self):
        self.assertTrue(get_species_infection_immune("synthetic_humanoid"))
        self.assertFalse(get_species_infection_immune("human"))
        self.assertFalse(get_species_infection_immune("rat"))
        self.assertFalse(get_species_infection_immune(None))

    def test_infection_condition_type_matches_guard(self):
        # the add_condition gate keys on condition_type == "infection".
        from world.medical.conditions import InfectionCondition
        self.assertEqual(InfectionCondition(2, "chest").condition_type,
                         "infection")

    def test_seed_infection_skips_immune_target(self):
        from world.medical.procedures import seed_infection
        state = MagicMock()
        state.conditions = []
        state.is_infection_immune.return_value = True
        seed_infection(MagicMock(medical_state=state), "chest", 3)
        self.assertEqual(state.conditions, [])  # no infection seeded

    def test_seed_infection_applies_to_non_immune(self):
        from world.medical.procedures import seed_infection
        state = MagicMock()
        state.conditions = []
        state.is_infection_immune.return_value = False
        seed_infection(MagicMock(medical_state=state), "chest", 3)
        self.assertEqual(len(state.conditions), 1)
