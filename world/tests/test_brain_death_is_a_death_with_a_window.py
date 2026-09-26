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
from evennia import create_object, create_script
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
        # KNOWN GAP, pinned so a change is deliberate: an organ ABSENT from
        # the dict (not destroyed, not harvested — a harvest zeroes HP in
        # place) is skipped by calculate_body_capacity, which then fails
        # open to 1.0, exactly as it does for the cervical spine. Only the
        # augment and limb installs call remove_organ, and no head augment
        # exists, so nothing reaches this today (#3248 comment 2026-09-26).
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


class TheReviewsFindings(EvenniaTest):
    """Pins for what the adversarial review of #3676 found."""

    def _infection(self, severity, location="head"):
        from world.medical.conditions import InfectionCondition
        cond = InfectionCondition(severity, location=location)
        self.char2.medical_state.add_condition(cond)
        return cond

    def test_an_infection_that_reaches_ten_on_its_tick_kills_on_that_tick(self):
        # The tick mutates severity in place; the cached verdict must not
        # outlive it. Control first: the stale cache is real.
        cond = self._infection(9)
        state = self.char2.medical_state
        self.assertFalse(state.is_dead())                 # caches False
        cond.severity = 10                                # a bare in-place write
        self.assertFalse(state.is_dead(), "control: the cache should still say alive")
        cond.severity = 9
        state._invalidate_derived_state()
        self.assertFalse(state.is_dead())
        with mock.patch("world.medical.conditions.hazard_fires", return_value=True):
            cond.tick_effect(self.char2, elapsed_minutes=1.0)
        self.assertEqual(cond.severity, 10)
        self.assertTrue(state.is_dead(), "the tick's own severity change did not reach the verdict")

    def test_a_decapitation_is_named_as_one_not_as_brain_death(self):
        # The head cluster goes with the head: the sever zeroes the brain too.
        state = self.char2.medical_state
        for name in ("cervical_spine", "brain"):
            state.organs[name].current_hp = 0
            state.organs[name].wound_stage = "severed"
        self.char2.save_medical_state()
        self.assertTrue(state.is_dead())
        self.assertEqual(self.char2.get_death_cause(), "decapitation")

    def test_a_septic_spine_is_not_a_broken_neck(self):
        state = self.char2.medical_state
        self._infection(10, location="neck")
        self.assertTrue(state.is_dead())
        self.assertGreater(state.organs["cervical_spine"].current_hp, 0)
        self.assertEqual(self.char2.get_death_cause(), "organ failure")

    def test_every_species_renders_a_decapitation_in_its_own_register(self):
        from world.medical.medical_messages import get_death_cause_template
        self.assertIn("|B", get_death_cause_template("brain death", "synthetic_humanoid"))
        self.assertIn("|B", get_death_cause_template("a broken neck", "synthetic_humanoid"))
        for species in SPECIES_DEFINITIONS:
            line = get_death_cause_template("decapitation from a slash to the neck", species)
            self.assertIn("head", line, f"{species}: {line}")
            self.assertNotIn("lolls", line, f"{species} got the broken-neck line for a decapitation")

    def test_the_splattercast_readout_names_a_brain_death(self):
        state = self.char2.medical_state
        state.organs["brain"].current_hp = 0
        self.char2.save_medical_state()
        report = self.char2.debug_death_analysis()
        self.assertIn("BRAIN DEATH", report)
        self.assertIn("Overall Status: DEAD", report)

    def test_an_interrupt_with_nothing_in_flight_leaves_the_chart_alone(self):
        from world.medical.procedures import interrupt_procedure
        self.char2.db.surgical_state = {"incisions": {}, "active_procedure": None}
        self.char2.db.medical_chart = {"status": "running",
                                       "steps": [{"id": 1, "verb": "harvest", "status": "running"}]}
        interrupt_procedure(self.char2, reason="the patient died")
        self.assertEqual(self.char2.db.medical_chart["steps"][0]["status"], "running")
        self.assertEqual(self.char2.db.medical_chart["status"], "running")

    def test_a_procedure_does_not_resolve_onto_an_archived_husk(self):
        from world.medical import procedures as P
        self.char2.db.surgical_state = {
            "incisions": {"head": True},
            "active_procedure": {"verb": "install", "token": "t1",
                                 "actor_dbref": self.char1.dbref, "kwargs": {}}}
        self.char2.db.archived = True
        self.char2.tags.add("archived", category="sleeve")
        told = []
        self.char1.msg = lambda text=None, **kw: told.append(str(text))
        with mock.patch.dict(P._VERB_RESOLVERS, {"install": mock.Mock(side_effect=AssertionError("resolved onto a husk"))}):
            P._resolve_procedure_callback(self.char2, token="t1")
        self.assertTrue(any("beyond reach" in t for t in told), told)
        self.assertIsNone(self.char2.db.surgical_state["active_procedure"])

    def test_control_a_dying_body_is_still_a_patient(self):
        # death_processed with the progression still running is the window,
        # not "gone".
        from world.medical import procedures as P
        self.char2.db.death_processed = True
        create_script("evennia.scripts.scripts.DefaultScript",
                      key="death_progression", obj=self.char2, autostart=False)
        self.assertFalse(P._patient_is_gone(self.char2))
        self.char2.scripts.get("death_progression")[0].delete()
        self.assertTrue(P._patient_is_gone(self.char2))

