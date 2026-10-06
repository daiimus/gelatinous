"""A reattached cyber limb keeps the weapon object it took when cut.

Severance moves a limb's integrated hardware onto the severed appendage
(decision 7: the limb takes its gear). Reattachment used to DELETE the
object at the limb's recorded dbref and reset the toggle state, so the
hand came back empty and respawned a new gun on the next deploy -- and,
under the old shared-claw model, it deleted the other hand's claws too
(#3571). Owner 2026-10-05: "I concur. Keep it."

Now the resolver reclaims an object that lies ON the appendage being
reattached: parked back in the body, dbref kept, retracted. An object
that is NOT on this appendage is simply unlinked, never deleted.
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import Character
from typeclasses.items import apply_sever_to_character
from world.medical import procedures as P
from world.medical.augments import _ability_state, find_ability, toggle_ability
from world.medical.core import Organ


class _AnArmOffAndBackOn(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.surgeon = self.char1
        self.patient = create_object(Character, key="Chrome", location=self.room1)
        self.patient.db.species = "human"
        state = self.patient.medical_state
        organ = Organ("cybernetic_humerus", organ_data={
            "container": "right_arm", "max_hp": 30, "hit_weight": "common",
            "bone_type": "actuator_column", "inorganic": True, "prosthetic_frame": True,
            "abilities": {"shotgun": {"type": "integrated_weapon", "slot": "right_hand",
                                      "weapon_prototype": "SHOTGUN_ARM_GUN"}},
        })
        organ.medical_state = state
        state.organs["cybernetic_humerus"] = organ
        self.gun = create_object("typeclasses.items.Item", key="arm shotgun", location=None)
        self.gun.db.integrated = True
        organ.ability_state = {"shotgun": {"weapon_dbref": self.gun.dbref}}
        self.patient.save_medical_state()
        self.told = []
        self.surgeon.msg = lambda text=None, **kw: self.told.append(str(text))

    def sever(self):
        apply_sever_to_character(self.patient, "right_arm")
        arm = next((o for o in self.room1.contents
                    if o.is_typeclass("typeclasses.items.Appendage", exact=False)), None)
        self.assertIsNotNone(arm, "fixture: the arm did not come off")
        return arm

    def reattach(self, arm):
        with mock.patch("world.medical.procedures.roll_procedure",
                        return_value={"outcome": "success"}):
            P._resolve_install_limb(self.surgeon, self.patient, organ_item=arm, location="right_arm")
        organ, _ = find_ability(self.patient, "shotgun")
        self.assertIsNotNone(organ, f"the arm did not reattach: {self.told}")
        return _ability_state(organ, "shotgun")


class TheWeaponComesBackWithTheArm(_AnArmOffAndBackOn):

    def test_the_gun_on_the_appendage_is_reclaimed_not_deleted(self):
        arm = self.sever()
        self.assertEqual(self.gun.location, arm, "fixture: the limb did not take its gear")
        state = self.reattach(arm)
        self.assertTrue(self.gun.pk, "the gun was deleted")
        self.assertIsNone(self.gun.location, "the gun was not parked back in the body")
        self.assertEqual(state.get("weapon_dbref"), self.gun.dbref)
        self.assertFalse(state.get("deployed"))

    def test_and_deploys_again_as_the_same_object(self):
        arm = self.sever()
        self.reattach(arm)
        toggle_ability(self.patient, "shotgun")
        self.assertEqual(self.gun.location, self.patient)
        self.assertIn(self.gun, self.patient.hands.values())

    def test_an_object_parked_in_the_body_is_not_stolen(self):
        # The case §9 names: a legacy shared reference to the other hand's
        # claws, parked off-grid (location None). The reattached limb must
        # not claim it; it is unlinked and stays where it is.
        arm = self.sever()
        self.gun.location = None
        state = self.reattach(arm)
        self.assertTrue(self.gun.pk)
        self.assertIsNone(self.gun.location)
        self.assertNotIn("weapon_dbref", state)

    def test_an_object_not_on_the_appendage_is_unlinked_and_left_alone(self):
        # A reference to something elsewhere (the other hand's shared
        # claws under the old model, or a gun someone carried off) must
        # not be stolen or deleted: the hand simply respawns on deploy.
        arm = self.sever()
        self.gun.location = self.room2
        state = self.reattach(arm)
        self.assertTrue(self.gun.pk)
        self.assertEqual(self.gun.location, self.room2)
        self.assertNotIn("weapon_dbref", state)
        self.assertFalse(state.get("deployed"))
