"""Phase 1 test contract for AUGMENT_ABILITIES_SPEC (issue #516).

Pins the toggled-cyberware ability layer:

* ability lookup reads organs (severed organs drop out);
* integrated_weapon deploy fills the hand slot with the weapon item
  (held-is-wielded: combat resolution follows for free) and
  auto-drops whatever the hand held;
* retract restores the empty hand and parks the weapon off-grid;
* ability_state round-trips with the organ;
* severance carries retracted hardware onto the appendage.

Run via::

    evennia test --settings settings.py world.tests.test_augment_abilities
"""

from __future__ import annotations

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import Character
from world.medical.augments import (
    CYBERWARE_COMMAND_PREFIX,
    carry_hardware_to_appendage,
    find_ability,
    list_abilities,
    toggle_ability,
)
from world.medical.core import Organ


def _gun_arm_organ(state, deployed_weapon_dbref=None):
    """A cybernetic arm organ carrying the shotgun ability — the
    spec shape the SHOTGUN_ARM item will declare.  Built with a
    bespoke organ_data copy (never mutate species-table specs)."""
    organ = Organ("cybernetic_humerus", organ_data={
        "container": "right_arm", "max_hp": 30, "hit_weight": "common",
        "bone_type": "actuator_column",
        "abilities": {
            "shotgun": {
                "type": "integrated_weapon",
                "slot": "right_hand",
                "weapon_prototype": "SHOTGUN_ARM_GUN",
            },
        },
    })
    organ.medical_state = state
    state.organs["cybernetic_humerus"] = organ
    if deployed_weapon_dbref:
        organ.ability_state = {
            "shotgun": {"weapon_dbref": deployed_weapon_dbref},
        }
    return organ


class TestAbilityLayer(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char = create_object(Character, key="Chrome", location=self.room1)
        self.organ = _gun_arm_organ(self.char.medical_state)
        # Pre-seed the integrated weapon so tests don't depend on the
        # Phase 2 prototype.
        self.gun = create_object(
            "typeclasses.items.Item", key="arm shotgun", location=None,
        )
        self.gun.db.integrated = True
        self.gun.locks.add("get:false();drop:false();give:false()")
        self.organ.ability_state = {
            "shotgun": {"weapon_dbref": self.gun.dbref},
        }

    def test_find_ability_reads_organs(self):
        organ, spec = find_ability(self.char, "shotgun")
        self.assertIs(organ, self.organ)
        self.assertEqual(spec["slot"], "right_hand")

    def test_severed_organ_loses_the_ability(self):
        self.organ.wound_stage = "severed"
        organ, spec = find_ability(self.char, "shotgun")
        self.assertIsNone(organ)
        self.assertIn("no cyberware", toggle_ability(self.char, "shotgun"))

    def test_unknown_ability_lists_what_you_have(self):
        msg = toggle_ability(self.char, "lasereyes")
        self.assertIn(f"{CYBERWARE_COMMAND_PREFIX}shotgun", msg)

    def test_deploy_fills_the_slot(self):
        toggle_ability(self.char, "shotgun")
        self.assertIs(self.char.hands["right_hand"], self.gun)
        self.assertIs(self.gun.location, self.char)
        self.assertTrue(
            self.organ.ability_state["shotgun"]["deployed"]
        )
        # Held-is-wielded: combat resolves the deployed gun.
        from world.combat.utils import get_wielded_weapon
        self.assertIs(get_wielded_weapon(self.char), self.gun)

    def test_deploy_auto_drops_held_item(self):
        knife = create_object(
            "typeclasses.items.Item", key="knife", location=self.char,
        )
        self.char.hands = {"right_hand": knife}
        toggle_ability(self.char, "shotgun")
        self.assertIs(knife.location, self.room1)
        self.assertIs(self.char.hands["right_hand"], self.gun)

    def test_retract_restores_the_hand(self):
        toggle_ability(self.char, "shotgun")
        toggle_ability(self.char, "shotgun")
        self.assertIsNone(self.char.hands["right_hand"])
        self.assertIsNone(self.gun.location)
        self.assertFalse(
            self.organ.ability_state["shotgun"]["deployed"]
        )

    def test_listing_shows_state(self):
        self.assertIn("retracted", list_abilities(self.char))
        toggle_ability(self.char, "shotgun")
        self.assertIn("deployed", list_abilities(self.char))

    def test_ability_state_round_trips(self):
        toggle_ability(self.char, "shotgun")
        restored = Organ.from_dict(self.organ.to_dict())
        self.assertTrue(restored.ability_state["shotgun"]["deployed"])
        self.assertEqual(
            restored.ability_state["shotgun"]["weapon_dbref"],
            self.gun.dbref,
        )
        self.assertIn("abilities", restored.data)

    def test_severance_carries_retracted_hardware(self):
        """Retracted = folded inside the arm; the severed arm takes
        it (spec decision 7)."""
        appendage = create_object(
            "typeclasses.items.Item", key="severed arm", location=self.room1,
        )
        carry_hardware_to_appendage(
            self.char, ("right_arm", "right_hand"), appendage,
        )
        self.assertIs(self.gun.location, appendage)
        self.assertFalse(
            self.organ.ability_state["shotgun"].get("deployed", False)
        )

    def test_integrated_weapon_refuses_drop(self):
        toggle_ability(self.char, "shotgun")
        self.assertFalse(self.gun.access(self.char, "drop"))
        self.assertFalse(self.gun.access(self.char, "get"))
