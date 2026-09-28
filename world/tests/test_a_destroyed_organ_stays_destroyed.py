"""A destroyed organ stays destroyed; a broken bone heals (#3253).

Owner ruling 2026-09-28: soft tissue at 0 HP is destroyed and stays so
until a donor or cybernetic install; a bone at 0 HP is broken and heals
(the cervical spine is a bone, so a broken neck can be set inside the
death window; severed, it is a decapitation and one-way); anything
severed stays severed; sealant and dressings follow that; staff `@heal`
keeps its override.

One question, `MedicalState.organ_beyond_repair`, folds in the harvest
marker (`organ_is_gone`, #3651); `Organ.heal` refuses on it, so every
in-play healer is covered at one door, and the callers ask first so
their messages are honest. Controls: a damaged (not destroyed) organ
still heals by every path; a broken bone heals; `full_heal` restores.
"""
from unittest import mock

from django.test import TestCase
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.anatomy import get_species_body_capacities, get_species_organs
from world.anatomy.species import SPECIES_DEFINITIONS
from world.medical import treatments as T
from world.medical.core import MedicalState, organ_is_bone
from world.medical.script import _healing_organs


class TheQuestion(TestCase):

    def test_a_destroyed_soft_organ_is_beyond_repair(self):
        state = MedicalState()
        state.organs["liver"].current_hp = 0
        self.assertTrue(state.organ_beyond_repair("liver"))

    def test_control_a_damaged_soft_organ_is_not(self):
        state = MedicalState()
        state.organs["liver"].current_hp = 1
        self.assertFalse(state.organ_beyond_repair("liver"))

    def test_a_broken_bone_is_not_beyond_repair(self):
        state = MedicalState()
        state.organs["left_femur"].current_hp = 0
        self.assertTrue(organ_is_bone(state.organs["left_femur"]))
        self.assertFalse(state.organ_beyond_repair("left_femur"))

    def test_a_broken_neck_is_a_broken_bone(self):
        state = MedicalState()
        state.organs["cervical_spine"].current_hp = 0
        self.assertTrue(organ_is_bone(state.organs["cervical_spine"]))
        self.assertFalse(state.organ_beyond_repair("cervical_spine"))
        self.assertTrue(state.is_dead(), "a broken neck is still a death")

    def test_a_severed_bone_is_beyond_repair(self):
        # decapitation: the spine goes with the head
        state = MedicalState()
        spine = state.organs["cervical_spine"]
        spine.current_hp = 0
        spine.wound_stage = "severed"
        self.assertTrue(state.organ_beyond_repair("cervical_spine"))

    def test_a_harvested_organ_is_beyond_repair(self):
        state = MedicalState()
        organ = state.organs["left_kidney"]
        organ.current_hp = 0
        organ.injury_type = "harvested"
        self.assertTrue(state.organ_beyond_repair("left_kidney"))

    def test_every_species_spine_is_a_bone_and_no_brain_carries_can_heal(self):
        for species in SPECIES_DEFINITIONS:
            organs = get_species_organs(species)
            for name in ("cervical_spine", "thoracolumbar_spine"):
                if name in organs:
                    self.assertTrue(organs[name].get("bone_type"), f"{species}/{name}")
            if "brain" in organs:
                self.assertNotIn("can_heal", organs["brain"], species)


class TheDoor(TestCase):
    """`Organ.heal` is where every in-play healer ends up."""

    def test_heal_refuses_a_destroyed_soft_organ(self):
        state = MedicalState()
        liver = state.organs["liver"]
        liver.current_hp = 0
        self.assertEqual(liver.heal(5), 0)
        self.assertEqual(liver.current_hp, 0)

    def test_control_heal_mends_a_damaged_soft_organ(self):
        state = MedicalState()
        liver = state.organs["liver"]
        liver.current_hp = 2
        self.assertGreater(liver.heal(5), 0)

    def test_heal_mends_a_broken_bone(self):
        state = MedicalState()
        femur = state.organs["left_femur"]
        femur.current_hp = 0
        self.assertGreater(femur.heal(5), 0)
        self.assertGreater(femur.current_hp, 0)

    def test_heal_refuses_a_severed_part(self):
        state = MedicalState()
        femur = state.organs["left_femur"]
        femur.current_hp = 0
        femur.wound_stage = "severed"
        self.assertEqual(femur.heal(5), 0)

    def test_control_full_heal_still_restores_a_destroyed_organ(self):
        # The staff override writes HP directly and bypasses the door.
        state = MedicalState()
        state.organs["liver"].current_hp = 0
        state.full_heal()
        self.assertEqual(state.organs["liver"].current_hp, state.organs["liver"].max_hp)


class TheHealers(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.state = self.char2.medical_state
        self.char2.db.surgical_state = {"incisions": {"abdomen": True, "neck": True},
                                        "active_procedure": None}

    def sealant(self, location):
        result = {"messages": [], "rolls": {"organ_repair": {"item_rating": 8}}}
        T._apply_organ_repair_outcome(self.char2, location, "success", result)
        return result

    def test_sealant_does_not_raise_a_destroyed_liver_and_says_so(self):
        self.state.organs["liver"].current_hp = 0
        result = self.sealant("abdomen")
        self.assertEqual(self.state.organs["liver"].current_hp, 0)
        self.assertTrue(any("beyond repair" in m for m in result["messages"]), result["messages"])

    def test_control_sealant_mends_a_damaged_liver(self):
        self.state.organs["liver"].current_hp = 3
        self.sealant("abdomen")
        self.assertGreater(self.state.organs["liver"].current_hp, 3)

    def test_sealant_sets_a_broken_neck_and_the_window_pays(self):
        from typeclasses.death_progression import DeathProgressionScript
        self.state.organs["cervical_spine"].current_hp = 0
        self.char2.save_medical_state()
        self.assertTrue(self.state.is_dead())
        self.sealant("neck")
        self.assertGreater(self.state.organs["cervical_spine"].current_hp, 0)
        self.assertFalse(self.state.is_dead())
        self.assertTrue(DeathProgressionScript._check_medical_revival_conditions(None, self.char2))

    def test_sealant_does_not_revive_a_brain_death(self):
        self.char2.db.surgical_state["incisions"]["head"] = True
        self.state.organs["brain"].current_hp = 0
        self.char2.save_medical_state()
        self.assertTrue(self.state.is_dead())
        self.sealant("head")
        self.assertEqual(self.state.organs["brain"].current_hp, 0)
        self.assertTrue(self.state.is_dead(), "sealant revived a brain death")

    def test_a_dressing_stabilises_a_destroyed_organ_but_sets_no_regrowth(self):
        liver = self.state.organs["liver"]
        liver.current_hp = 0
        liver.stabilized = False
        item = create_object("typeclasses.items.Item", key="gauze", location=self.char1)
        item.db.medical_type = "wound_care"
        item.db.effectiveness = {"wound_healing": 8, "bleeding": 7}
        T.apply_wound_care(self.char1, self.char2, item, "abdomen")
        self.assertTrue(liver.stabilized)
        self.assertEqual(getattr(liver, "dressing_rate", 0), 0)
        self.assertNotIn(liver, _healing_organs(self.state))

    def test_control_a_dressing_regrows_a_broken_bone(self):
        femur = self.state.organs["left_femur"]
        femur.current_hp = 0
        femur.stabilized = True
        femur.dressing_rate = 8
        self.assertIn(femur, _healing_organs(self.state))
        liver = self.state.organs["liver"]
        liver.current_hp = 0
        liver.stabilized = True
        liver.dressing_rate = 8
        self.assertNotIn(liver, _healing_organs(self.state))


class TheSplint(EvenniaTest):

    def splint(self):
        from world.medical.utils import apply_medical_effects
        item = create_object("typeclasses.items.Item", key="a splint", location=self.char1)
        item.tags.add("medical_item", category="item_type")
        item.attributes.add("medical_type", "fracture_treatment")
        item.attributes.add("uses_left", 5)
        item.attributes.add("effectiveness", {"fracture": 8})
        return apply_medical_effects(item, self.char1, self.char2)

    def test_a_shattered_bone_is_splintable(self):
        femur = self.char2.medical_state.organs["left_femur"]
        femur.current_hp = 0
        self.splint()
        self.assertGreater(femur.current_hp, 0, "the splint refused a broken bone")

    def test_a_severed_bone_is_not(self):
        femur = self.char2.medical_state.organs["left_femur"]
        femur.current_hp = 0
        femur.wound_stage = "severed"
        self.splint()
        self.assertEqual(femur.current_hp, 0)
