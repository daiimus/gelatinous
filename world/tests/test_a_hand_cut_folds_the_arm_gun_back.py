"""A chrome hand cut off a surviving gun arm folds the deployed gun back
inside the arm (#3697). Before: ``detach_items_to_appendage`` dropped the
integrated gun to the floor as an item no verb could move, and the forearm
module kept reading deployed, so the next toggle was a retract of a gun
lying somewhere on a floor.

Controls: an ARM cut still hands the gun to the limb (the carry's old
promise, now from the body instead of via the floor), and a plain knife in
the cut hand still clatters to the ground.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import Character
from typeclasses.items import apply_sever_to_character
from world.medical.augments import _ability_state, find_ability, toggle_ability
from world.medical.core import Organ


def _gun_arm_organ(state):
    organ = Organ("cybernetic_humerus", organ_data={
        "container": "right_arm", "max_hp": 30, "hit_weight": "common",
        "bone_type": "actuator_column", "inorganic": True, "prosthetic_frame": True,
        "abilities": {"shotgun": {"type": "integrated_weapon", "slot": "right_hand",
                                  "weapon_prototype": "SHOTGUN_ARM_GUN"}},
    })
    organ.medical_state = state
    state.organs["cybernetic_humerus"] = organ
    return organ


class _GunArm(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.patient = create_object(Character, key="Chrome", location=self.room1)
        self.patient.db.species = "human"
        self.organ = _gun_arm_organ(self.patient.medical_state)
        self.gun = create_object("typeclasses.items.Item", key="arm shotgun", location=None)
        self.gun.db.integrated = True
        self.gun.locks.add("get:false();drop:false()")
        self.organ.ability_state = {"shotgun": {"weapon_dbref": self.gun.dbref}}
        self.patient.save_medical_state()

    def _deploy(self):
        toggle_ability(self.patient, "shotgun")
        organ, _ = find_ability(self.patient, "shotgun")
        assert _ability_state(organ, "shotgun").get("deployed"), "precondition: could not deploy"
        assert self.gun.location == self.patient, "precondition: deployed gun is not on the body"

    def _state(self):
        organ, _ = find_ability(self.patient, "shotgun")
        return _ability_state(organ, "shotgun")

    def _appendages(self):
        return [o for o in self.room1.contents if o.is_typeclass("typeclasses.items.Appendage", exact=False)]


class TheHandCutFoldsTheGunBack(_GunArm):

    def test_the_gun_is_parked_and_retracted_not_on_the_floor(self):
        self._deploy()
        apply_sever_to_character(self.patient, "right_hand")
        self.assertIsNone(self.gun.location)
        self.assertFalse(self._state().get("deployed"))
        self.assertEqual(self._state().get("weapon_dbref"), self.gun.dbref)
        self.assertNotIn(self.gun, self.room1.contents)
        for part in self._appendages():
            self.assertNotIn(self.gun, part.contents)
        self.assertNotIn(self.gun, (self.patient.held_items or {}).values())

    def test_the_next_toggle_is_a_deploy_attempt_not_a_retract(self):
        self._deploy()
        apply_sever_to_character(self.patient, "right_hand")
        line = toggle_ability(self.patient, "shotgun")
        # The hand is gone, so the deploy is refused on the slot; a retract
        # would have spoken folding prose and left deployed False by accident.
        self.assertIn("isn't there", line)
        self.assertFalse(self._state().get("deployed"))
        self.assertIsNone(self.gun.location)


class TheControlsStillHold(_GunArm):

    def test_an_arm_cut_still_hands_the_gun_to_the_limb(self):
        self._deploy()
        apply_sever_to_character(self.patient, "right_arm")
        parts = self._appendages()
        self.assertEqual(len(parts), 1, parts)
        self.assertEqual(self.gun.location, parts[0])
        self.assertNotIn(self.gun, self.room1.contents)
        # The ability left with the arm: the body no longer hosts it.
        self.assertIsNone(find_ability(self.patient, "shotgun")[0])

    def test_a_plain_knife_in_the_cut_hand_still_drops(self):
        knife = create_object("typeclasses.items.Item", key="knife", location=self.patient)
        self.patient.wield_item(knife, "right_hand")
        apply_sever_to_character(self.patient, "right_hand")
        self.assertEqual(knife.location, self.room1)
