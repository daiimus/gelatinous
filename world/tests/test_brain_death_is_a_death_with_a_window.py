"""Brain death is a death with a window (#3248, owner ruling 2026-09-26).

Two variables, kept apart: ``consciousness`` is the awake axis and never
gates death ("Conscious capacity 0 should not be death"); the brain's
DEATH is the structural capacity ``brain_integrity``, the twin of
``neck_integrity``. A destroyed brain reads dead on the blow, and a brain
installed during the death progression restores the capacity, so the
existing revival gate (exactly ``not is_dead()``) brings the body back.

Controls: a knockout with an intact brain is not a death; a brain at one
hit point is not a death; the vital-location set is unchanged.
"""
from unittest import mock

from django.test import TestCase
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.anatomy import get_species_body_capacities
from world.anatomy.species import SPECIES_DEFINITIONS
from world.medical.constants import BODY_CAPACITIES, LETHAL_CAPACITY_NAMES
from world.medical.core import MedicalState


class TheSchema(TestCase):

    def test_every_species_has_the_capacity_on_the_brain(self):
        for species in SPECIES_DEFINITIONS:
            caps = get_species_body_capacities(species)
            self.assertIn("brain_integrity", caps, species)
            self.assertEqual(caps["brain_integrity"]["organs"], ["brain"], species)
            self.assertTrue(caps["brain_integrity"].get("directly_fatal"), species)
        self.assertIn("brain_integrity", BODY_CAPACITIES)

    def test_the_lethal_set_names_the_brain_and_not_the_awake_axis(self):
        self.assertIn("brain_integrity", LETHAL_CAPACITY_NAMES)
        self.assertNotIn("consciousness", LETHAL_CAPACITY_NAMES)


class BrainDeath(TestCase):

    def test_a_destroyed_brain_is_dead_on_the_blow(self):
        state = MedicalState()
        brain = state.get_organ("brain")
        state.take_organ_damage("brain", brain.max_hp + 5, "blunt")
        self.assertTrue(state.get_organ("brain").is_destroyed())
        self.assertEqual(state.calculate_body_capacity("brain_integrity"), 0.0)
        self.assertTrue(state.is_dead())

    def test_control_a_brain_with_a_point_left_is_alive(self):
        state = MedicalState()
        brain = state.get_organ("brain")
        state.take_organ_damage("brain", brain.max_hp - 1, "blunt")
        self.assertGreater(state.calculate_body_capacity("brain_integrity"), 0.0)
        self.assertFalse(state.is_dead())

    def test_control_a_knockout_is_not_a_death(self):
        # The awake axis at zero with an intact brain: unconscious, alive.
        state = MedicalState()
        state.consciousness = 0.0
        self.assertTrue(state.is_unconscious())
        self.assertEqual(state.calculate_body_capacity("brain_integrity"), 1.0)
        self.assertFalse(state.is_dead())

    def test_a_missing_brain_reads_healthy_like_a_missing_spine(self):
        # A pre-migration organ set lazily gets a full-HP organ (the neck
        # test pins the same for the cervical spine).
        state = MedicalState()
        state.organs.pop("brain", None)
        self.assertEqual(state.calculate_body_capacity("brain_integrity"), 1.0)
        self.assertFalse(state.is_dead())

    def test_a_head_infection_at_ten_is_a_brain_death(self):
        # Capacities read organ FUNCTION, so a severity-10 infection at the
        # head zeroes the brain the way a chest one already zeroes the
        # heart. The owner accepted infection reaching internal organs
        # being fatal (2026-09-26).
        from world.medical.conditions import InfectionCondition
        state = MedicalState()
        state.add_condition(InfectionCondition(10, location="head"))
        self.assertEqual(state.calculate_body_capacity("brain_integrity"), 0.0)
        self.assertTrue(state.is_dead())


class TheWindow(EvenniaTest):
    """Dying of a destroyed brain, then a brain installed on the table."""

    def setUp(self):
        super().setUp()
        self.char2.location = self.room1
        kit = create_object("typeclasses.items.Item", key="a surgical kit",
                            location=self.char1)
        mock.patch("world.medical.utils.find_surgical_kit",
                   return_value=kit).start()
        self.addCleanup(mock.patch.stopall)
        self.char2.db.surgical_state = {"incisions": {"head": True},
                                        "active_procedure": None}
        self.char1.msg = lambda text=None, **kw: None

    def dying(self):
        state = self.char2.medical_state
        state.organs["brain"].current_hp = 0
        self.char2.save_medical_state()
        self.assertTrue(state.is_dead(), "fixture: a destroyed brain should read dead")
        return state

    def replacement(self):
        state = self.char2.medical_state
        item = create_object("typeclasses.items.Organ", key="a brain",
                             location=self.char1)
        item.db.organ_name = "brain"
        item.db.condition = "pristine"
        item.db.organ_spec = dict(state.organs["brain"].data)
        return item

    def install(self):
        from world.medical import procedures as P
        with mock.patch("world.medical.procedures.roll_procedure",
                        return_value={"outcome": "success", "margin": 9}):
            P._resolve_install(self.char1, self.char2,
                               organ_item=self.replacement(), location="head")

    def test_the_cause_is_brain_death(self):
        self.dying()
        self.assertEqual(self.char2.get_death_cause(), "brain death")

    def test_the_revival_gate_refuses_while_the_brain_is_gone(self):
        from typeclasses.death_progression import DeathProgressionScript
        self.dying()
        self.assertFalse(
            DeathProgressionScript._check_medical_revival_conditions(None, self.char2))

    def test_a_brain_installed_in_the_window_revives(self):
        from typeclasses.death_progression import DeathProgressionScript
        state = self.dying()
        self.install()
        self.assertEqual(state.calculate_body_capacity("brain_integrity"), 1.0)
        self.assertFalse(state.is_dead(), "the new brain did not bring them back")
        self.assertTrue(
            DeathProgressionScript._check_medical_revival_conditions(None, self.char2))

    def test_control_a_new_brain_on_a_body_dead_of_its_heart_does_not_revive(self):
        from typeclasses.death_progression import DeathProgressionScript
        state = self.dying()
        state.organs["heart"].current_hp = 0
        self.char2.save_medical_state()
        self.install()
        self.assertTrue(state.is_dead(), "a brain is not a heart")
        self.assertFalse(
            DeathProgressionScript._check_medical_revival_conditions(None, self.char2))


class TheNeckHasAName(EvenniaTest):

    def test_a_severed_spine_reads_as_a_broken_neck(self):
        state = self.char2.medical_state
        state.organs["cervical_spine"].current_hp = 0
        self.char2.save_medical_state()
        self.assertTrue(state.is_dead())
        self.assertEqual(self.char2.get_death_cause(), "a broken neck")

    def test_every_species_renders_both_new_causes(self):
        from world.medical.medical_messages import (_GENERIC_DEATH_BY_SPECIES,
                                                    get_death_cause_template)
        for species in SPECIES_DEFINITIONS:
            generic = (_GENERIC_DEATH_BY_SPECIES.get(species)
                       or _GENERIC_DEATH_BY_SPECIES["human"])
            for cause in ("brain death", "a broken neck"):
                line = get_death_cause_template(cause, species)
                self.assertNotEqual(line, generic, f"{species}/{cause} fell to generic")
