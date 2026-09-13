"""Surgery stows the hardware at the cut, and nobody toggles mid-procedure (#3360).

`toggle_ability` implemented two of the spec's three gates (anatomy;
dead/unconscious) and no busy gate, so a patient on the table could
`deploy` an integrated weapon in the hand being cut on -- auto-dropping
what the hand held, with a room message, mid-incision.

Owner ruling 2026-09-13:
  * the FIRST element of any procedure restores the hardware at the
    location being cut to its default, undeployed state (hardware
    elsewhere on the body is left alone);
  * no toggles while a procedure is active on the body;
  * NO channeled-act gate -- a shotgun arm must deploy when combat
    starts, and sensory hardware is used whenever.
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import Character
from world.medical import procedures as P
from world.medical.augments import toggle_ability, find_ability, _ability_state
from world.medical.core import Organ


def _gun_arm_organ(state):
    organ = Organ("cybernetic_humerus", organ_data={
        "container": "right_arm", "max_hp": 30, "hit_weight": "common",
        "bone_type": "actuator_column",
        "abilities": {"shotgun": {"type": "integrated_weapon", "slot": "right_hand",
                                  "weapon_prototype": "SHOTGUN_ARM_GUN"}},
    })
    organ.medical_state = state
    state.organs["cybernetic_humerus"] = organ
    return organ


class SurgeryStowsHardwareTest(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.patient = create_object(Character, key="Chrome", location=self.room1)
        self.organ = _gun_arm_organ(self.patient.medical_state)
        self.gun = create_object("typeclasses.items.Item", key="arm shotgun", location=None)
        self.gun.db.integrated = True
        self.organ.ability_state = {"shotgun": {"weapon_dbref": self.gun.dbref}}
        # surgeon = char1 with a kit
        self.kit = create_object("typeclasses.items.Item", key="a surgical kit", location=self.char1)
        self.kit.tags.add("surgical_kit", category="item_type")
        pk = mock.patch("world.medical.utils.find_surgical_kit", return_value=self.kit); pk.start(); self.addCleanup(pk.stop)
        P._PROCEDURE_COMPLETE_HOOKS.clear(); self.addCleanup(P._PROCEDURE_COMPLETE_HOOKS.clear)

    def _deployed(self):
        organ, _ = find_ability(self.patient, "shotgun")
        return bool(_ability_state(organ, "shotgun").get("deployed"))

    def _deploy(self):
        toggle_ability(self.patient, "shotgun")
        assert self._deployed(), "precondition: could not deploy"

    # --- ruling (2): first element of a procedure at the cut stows it ------

    def test_procedure_at_the_cut_stows_the_weapon(self):
        self._deploy()
        P.start_procedure(self.patient, verb="incise", actor=self.char1, location="right_arm")
        self.assertFalse(self._deployed(), "shotgun still deployed after surgery began on that arm")

    def test_procedure_elsewhere_leaves_it_deployed(self):
        self._deploy()
        P.start_procedure(self.patient, verb="incise", actor=self.char1, location="left_shin")
        self.assertTrue(self._deployed(), "a leg operation stowed the arm shotgun")

    # --- ruling (1): the busy gate ----------------------------------------

    def test_toggle_refused_while_a_procedure_is_active(self):
        P.start_procedure(self.patient, verb="incise", actor=self.char1, location="left_shin")
        assert P.is_procedure_active(self.patient)
        msg = toggle_ability(self.patient, "shotgun")
        self.assertFalse(self._deployed(), "patient deployed a weapon mid-procedure")
        self.assertIn("procedure", msg.lower())

    # --- controls -----------------------------------------------------------

    def test_toggle_works_when_no_procedure(self):
        self.assertFalse(self._deployed())
        toggle_ability(self.patient, "shotgun"); self.assertTrue(self._deployed())
        toggle_ability(self.patient, "shotgun"); self.assertFalse(self._deployed())

    def test_channeling_does_not_gate_toggles(self):
        # Ruling (3): no channeled-act gate. Simulate "mid-channel" the way
        # the house gate reads it and confirm deploy still succeeds.
        try:
            from world import channeled
            with mock.patch.object(channeled, "is_channeling", return_value=True, create=True):
                toggle_ability(self.patient, "shotgun")
        except ImportError:
            toggle_ability(self.patient, "shotgun")
        self.assertTrue(self._deployed(), "a channeled act blocked the deploy; ruling says it must not")
