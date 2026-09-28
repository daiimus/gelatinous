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

    def test_a_harvested_organ_is_beyond_repair_even_when_it_is_a_bone(self):
        # The harvest check is what stops a harvested chrome strut (a bone
        # by its flags) from being splinted back into existence.
        state = MedicalState()
        organ = state.organs["left_femur"]
        organ.current_hp = 5
        organ.injury_type = "harvested"
        self.assertTrue(organ_is_bone(organ))
        self.assertTrue(state.organ_beyond_repair("left_femur"))

    def test_the_pelvis_and_jaw_are_bones(self):
        state = MedicalState()
        for name in ("pelvis", "jaw"):
            state.organs[name].current_hp = 0
            self.assertTrue(organ_is_bone(state.organs[name]), name)
            self.assertFalse(state.organ_beyond_repair(name), name)

    def test_a_body_saved_before_the_flag_still_knows_its_spine_is_a_bone(self):
        # Every saved body carries its own organ spec (#513); a flag added to
        # the species table must reach them through the organ's NAME.
        import copy
        state = MedicalState()
        snap = copy.deepcopy(state.to_dict())     # never mutate the live table through a shared dict
        for name in ("cervical_spine", "thoracolumbar_spine", "pelvis", "jaw"):
            snap["organs"][name]["data"].pop("bone_type", None)
            snap["organs"][name]["data"].pop("fracture_vulnerable", None)
            snap["organs"][name]["current_hp"] = 0
        old = MedicalState.from_dict(snap)
        for name in ("cervical_spine", "thoracolumbar_spine", "pelvis", "jaw"):
            self.assertTrue(organ_is_bone(old.organs[name]), name)
            self.assertFalse(old.organ_beyond_repair(name), f"{name} read as destroyed soft tissue on a legacy body")

    def test_a_failed_head_spawn_is_still_a_decapitation(self):
        # The blow sets decapitation_pending before the head is spawned;
        # if the spawn fails the spine sits at 0 unmarked.
        state = MedicalState()
        state.organs["cervical_spine"].current_hp = 0
        class _Char:
            class db: decapitation_pending = True
        state.character = _Char()
        self.assertTrue(state.organ_beyond_repair("cervical_spine"))

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

    def test_heal_mends_a_broken_bone_and_moves_it_off_destroyed(self):
        state = MedicalState()
        femur = state.organs["left_femur"]
        femur.current_hp = 0
        femur.wound_stage = "destroyed"
        self.assertGreater(femur.heal(5), 0)
        self.assertGreater(femur.current_hp, 0)
        self.assertEqual(femur.wound_stage, "treated", "a knitting bone still rendered as destroyed")

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

    def _gauze(self):
        item = create_object("typeclasses.items.Item", key="gauze", location=self.char1)
        item.db.medical_type = "wound_care"
        item.db.effectiveness = {"wound_healing": 8, "bleeding": 7}
        return item

    def test_a_dressing_holds_and_closes_a_site_that_cannot_heal(self):
        # The dressing still does its job -- the bleed stops -- but nothing
        # there will heal, so the site is closed: no regrowth rate, the
        # bleed condition removed (a held bleed on an organ that never
        # heals to full would otherwise tick the script forever), and a
        # second dressing here is not refused as "already stabilized".
        from world.medical.conditions import BleedingCondition
        liver = self.state.organs["liver"]
        liver.current_hp = 0
        liver.stabilized = False
        self.state.add_condition(BleedingCondition(8, location="abdomen"))
        result = T.apply_wound_care(self.char1, self.char2, self._gauze(), "abdomen")
        self.assertIsNone(result.get("no_op_reason"))
        self.assertTrue(liver.stabilized)
        self.assertEqual(getattr(liver, "dressing_rate", 0), 0)
        self.assertNotIn(liver, _healing_organs(self.state))
        self.assertEqual([c for c in self.state.conditions if isinstance(c, BleedingCondition)], [],
                         "the bleed at a closed site was left to tick forever")
        again = T.apply_wound_care(self.char1, self.char2, self._gauze(), "abdomen")
        self.assertIsNone(again.get("no_op_reason"), again["messages"])

    def test_control_a_mixed_site_keeps_its_hold_for_the_healable_organ(self):
        from world.medical.conditions import BleedingCondition
        self.state.organs["liver"].current_hp = 0
        self.state.organs["stomach"].current_hp = 3
        self.state.add_condition(BleedingCondition(8, location="abdomen"))
        T.apply_wound_care(self.char1, self.char2, self._gauze(), "abdomen")
        self.assertTrue(self.state.organs["stomach"].stabilized)
        self.assertGreater(self.state.organs["stomach"].dressing_rate, 0)
        self.assertTrue([c for c in self.state.conditions if isinstance(c, BleedingCondition)],
                        "the stomach's held bleed was removed")
        again = T.apply_wound_care(self.char1, self.char2, self._gauze(), "abdomen")
        self.assertEqual(again.get("no_op_reason"), "already_stabilized")

    def test_a_new_wound_reopens_a_site_a_destroyed_organ_kept_flagged(self):
        from world.medical.conditions import BleedingCondition
        liver = self.state.organs["liver"]
        liver.current_hp = 0
        T.apply_wound_care(self.char1, self.char2, self._gauze(), "abdomen")
        self.assertTrue(liver.stabilized)
        # later: a stab to the stomach, same container
        self.state.take_organ_damage("stomach", 12, "stab")
        self.assertFalse(liver.stabilized, "the stale flag would have held the new bleed")
        bleeds = [c for c in self.state.conditions if isinstance(c, BleedingCondition)]
        self.assertTrue(bleeds)
        self.assertFalse(bleeds[0]._location_stabilized(self.state))

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
        femur.stabilized = False
        msg = self.splint()
        self.assertEqual(femur.current_hp, 0)
        self.assertFalse(femur.stabilized, "the splint dressed a severed stump")
        self.assertEqual(getattr(femur, "dressing_rate", 0), 0)
        self.assertIn("severed", str(msg))

    def _splint_item(self):
        item = create_object("typeclasses.items.Item", key="a splint", location=self.char1)
        item.tags.add("medical_item", category="item_type")
        item.attributes.add("medical_type", "fracture_treatment")
        item.attributes.add("uses_left", 5)
        item.attributes.add("effectiveness", {"fracture": 8})
        return item

    def test_the_splint_goes_where_the_player_said(self):
        from world.medical.utils import apply_medical_effects
        state = self.char2.medical_state
        state.organs["left_femur"].current_hp = 0            # the worst bone anywhere
        state.organs["left_humerus"].current_hp = state.organs["left_humerus"].max_hp - 5
        apply_medical_effects(self._splint_item(), self.char1, self.char2, body_location="left_arm")
        self.assertEqual(state.organs["left_femur"].current_hp, 0, "the splint wandered to the leg")
        self.assertEqual(state.organs["left_humerus"].current_hp, state.organs["left_humerus"].max_hp)

    def test_the_splint_takes_a_bone_name_or_a_face(self):
        from world.medical.utils import apply_medical_effects
        state = self.char2.medical_state
        state.organs["left_femur"].current_hp = 0
        state.organs["left_humerus"].current_hp = state.organs["left_humerus"].max_hp - 5
        apply_medical_effects(self._splint_item(), self.char1, self.char2, body_location="left_humerus")
        self.assertEqual(state.organs["left_humerus"].current_hp, state.organs["left_humerus"].max_hp)
        state.organs["jaw"].current_hp = 0
        apply_medical_effects(self._splint_item(), self.char1, self.char2, body_location="face")
        self.assertGreater(state.organs["jaw"].current_hp, 0, "the jaw shows at the face and was not found there")

    def test_nothing_at_the_named_place_means_nothing_is_consumed(self):
        from commands.CmdConsumption import CmdApply
        state = self.char2.medical_state
        state.organs["left_femur"].current_hp = 0
        gate = CmdApply()._check_treatment_possible
        self.assertTrue(gate(self.char2, "fracture_treatment"))
        self.assertTrue(gate(self.char2, "fracture_treatment", body_location="left_thigh"))
        self.assertFalse(gate(self.char2, "fracture_treatment", body_location="left_arm"),
                         "a splint aimed at a whole arm would be spent on nothing")


class TheInstall(EvenniaTest):

    def test_a_replacement_starts_without_the_slots_old_care_flags(self):
        from world.medical import procedures as P
        state = self.char2.medical_state
        liver = state.organs["liver"]
        liver.current_hp = 0
        liver.stabilized = True
        liver.dressing_rate = 8
        self.char2.db.surgical_state = {"incisions": {"abdomen": True}, "active_procedure": None}
        self.char1.msg = lambda text=None, **kw: None
        # No organ_spec on the donor: this is the branch that REUSES the
        # slot's Organ object (a spec-carrying donor builds a fresh one,
        # whose defaults are already clean).
        item = create_object("typeclasses.items.Organ", key="a liver", location=self.char1)
        item.db.organ_name = "liver"
        item.db.condition = "pristine"
        with mock.patch("world.medical.procedures.roll_procedure",
                        return_value={"outcome": "success", "margin": 9}):
            P._resolve_install(self.char1, self.char2, organ_item=item, location="abdomen")
        new = state.organs["liver"]
        self.assertGreater(new.current_hp, 0)
        self.assertFalse(new.stabilized)
        self.assertEqual(getattr(new, "dressing_rate", 0), 0)
