"""Death parks the gun; a limb cut off a corpse takes it (#3486, #3487).

Retracting an integrated weapon parks its object off-grid, and the living
sever path carries parked hardware onto the Appendage. Death ran neither:
the corpse factory swept the character's contents into the corpse and
blanked the hands, so a character who died with an arm-shotgun DEPLOYED
left a `get:false/drop:false` gun loose inside a corpse that never
self-deletes, with `deployed` still True in the death snapshot (#3486).
And `spawn_severed_part_from_corpse` -- both corpse sever doors -- did
create → configure → record → apply and nothing else, so a cyber arm cut
off a corpse stranded its module (#3487).

Owner ruling 2026-09-14: chrome stays on your corpse. The gun folds back
inside the arm at death and leaves with the arm.
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest, EvenniaTest

from typeclasses.characters import Character
from typeclasses.death_progression import DeathProgressionScript
from typeclasses.items import spawn_severed_part_from_corpse
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


class _ChromeDeath(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.patient = create_object(Character, key="Chrome", location=self.room1)
        self.organ = _gun_arm_organ(self.patient.medical_state)
        self.gun = create_object("typeclasses.items.Item", key="arm shotgun", location=None)
        self.gun.db.integrated = True
        self.gun.locks.add("get:false();drop:false()")
        self.organ.ability_state = {"shotgun": {"weapon_dbref": self.gun.dbref}}

    def _deploy(self):
        toggle_ability(self.patient, "shotgun")
        organ, _ = find_ability(self.patient, "shotgun")
        assert _ability_state(organ, "shotgun").get("deployed"), "precondition: could not deploy"
        assert self.gun.location == self.patient, "precondition: deployed gun is not on the body"

    def _die(self):
        return DeathProgressionScript()._create_corpse_from_character(self.patient)

    def _snapshot_state(self, holder):
        organs = holder.get_medical_snapshot()["organs"]
        return organs["cybernetic_humerus"]["ability_state"]["shotgun"]


class DyingWithTheGunOutParksItTest(_ChromeDeath):

    def test_the_gun_is_not_loose_inside_the_corpse(self):
        self._deploy()
        corpse = self._die()
        self.assertNotIn(self.gun, corpse.contents, "a locked, undroppable gun landed in the corpse")
        self.assertIsNone(self.gun.location, "the gun was not folded back inside the arm")

    def test_the_snapshot_records_it_retracted_and_keeps_the_link(self):
        self._deploy()
        corpse = self._die()
        state = self._snapshot_state(corpse)
        self.assertFalse(state.get("deployed"))
        self.assertEqual(state.get("weapon_dbref"), self.gun.dbref)

    def test_dying_retracted_changes_nothing(self):
        corpse = self._die()
        self.assertIsNone(self.gun.location)
        self.assertEqual(self._snapshot_state(corpse).get("weapon_dbref"), self.gun.dbref)


class ALimbCutOffACorpseTakesItsHardwareTest(_ChromeDeath):

    def test_the_parked_gun_leaves_with_the_arm(self):
        self._deploy()
        corpse = self._die()
        arm = spawn_severed_part_from_corpse(corpse, "right_arm")
        self.assertIsNotNone(arm, "fixture: the arm did not come off")
        self.assertEqual(self.gun.location, arm, "the module stayed behind at %r" % self.gun.location)
        self.assertFalse(self._snapshot_state(arm).get("deployed"))

    def test_a_pre_fix_corpse_with_the_gun_loose_inside_still_hands_it_over(self):
        """A corpse that died before #3486: gun in its contents, deployed True."""
        corpse = self._die()
        self.gun.location = corpse
        snap = corpse.get_medical_snapshot()
        snap["organs"]["cybernetic_humerus"]["ability_state"]["shotgun"]["deployed"] = True
        corpse.db.medical_state_at_death = snap
        arm = spawn_severed_part_from_corpse(corpse, "right_arm")
        self.assertEqual(self.gun.location, arm)
        self.assertFalse(self._snapshot_state(arm).get("deployed"))

    def test_another_limb_leaves_the_gun_where_it_is(self):
        self._deploy()
        corpse = self._die()
        leg = spawn_severed_part_from_corpse(corpse, "left_thigh")
        self.assertIsNotNone(leg)
        self.assertIsNone(self.gun.location)


class TheTypedSeverVerbIsTheSameDoorTest(EvenniaCommandTest):
    """Play caught this (2026-09-14): the helper carried the gun, the typed
    `sever` verb -- which builds its own Appendage inline -- did not. The
    carry now lives in `configure_from_sever`, where every door lands.

    Driven with ``EvenniaCommandTest.call`` -- ``execute_cmd`` is inert
    under ``evennia test`` (no reactor)."""

    def setUp(self):
        super().setUp()
        self.patient = create_object(Character, key="Chrome", location=self.room1)
        self.organ = _gun_arm_organ(self.patient.medical_state)
        self.gun = create_object("typeclasses.items.Item", key="arm shotgun", location=None)
        self.gun.db.integrated = True
        self.gun.locks.add("get:false();drop:false()")
        self.organ.ability_state = {"shotgun": {"weapon_dbref": self.gun.dbref}}

    def _typed_sever(self, corpse, what):
        from commands import forensics as cmd_module
        blade = create_object("typeclasses.items.Item", key="cleaver", location=self.char1)
        blade.db.can_sever = True

        def _immediate(seconds, callback, *args, **kwargs):
            callback(*args, **kwargs)

        def _roll(char, stat, *args, **kwargs):
            return {"intellect": 9, "motorics": 9}.get(stat, 9)

        with mock.patch.object(cmd_module, "get_wielded_weapon", return_value=blade), \
             mock.patch.object(cmd_module.utils, "delay", side_effect=_immediate), \
             mock.patch.object(cmd_module, "roll_stat", side_effect=_roll):
            self.said = self.call(cmd_module.CmdSever(), f"{what} from {corpse.key}", caller=self.char1)
        return [o for o in self.char1.contents if o.typeclass_path.endswith("Appendage")]

    def test_the_typed_verb_hands_the_gun_to_the_limb(self):
        toggle_ability(self.patient, "shotgun")
        assert self.gun.location == self.patient, "precondition: deployed gun is not on the body"
        corpse = DeathProgressionScript()._create_corpse_from_character(self.patient)
        arms = self._typed_sever(corpse, "right arm")
        self.assertEqual(len(arms), 1, "fixture: the typed verb did not produce an arm; it said %r" % self.said)
        self.assertEqual(self.gun.location, arms[0], "the module stayed behind at %r" % self.gun.location)
        self.assertIn("right_arm", list(corpse.db.severed_locations or []))
