"""A two-handed weapon wants your other hand free (GRIP_ENFORCEMENT_SPEC;
owner rulings 2026-10-06, verbatim in its §6).

The grip is implicit: the weapon sits in one hand and a free grasping slot
is the second hand. Full or gone, the swing is under-gripped and the roll
pays the placeholder factor. Natural and integrated weapons never pay.
"""
import re
from types import SimpleNamespace
from unittest import TestCase, mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest, EvenniaTest

from world.combat import attack as A
from world.combat.capacity import grip_hit_factor
from world.combat.constants import NDB_PROXIMITY
from world.combat.weapon_choice import WeaponChoice, choose_weapon


def _choice(hands_required, slots=("left_hand",), natural=False, integrated=False):
    item = SimpleNamespace(key="rifle", db=SimpleNamespace(integrated=integrated))
    return WeaponChoice(items=(item,), slots=tuple(slots), lead_slot=slots[0] if slots else "",
                        hands_required=hands_required, damage=5, hit_bonus=0, damage_type="bullet",
                        weapon_type="bolt-action_rifle", is_ranged=True, natural=natural)


class TheFactor(TestCase):

    def test_a_free_second_hand_is_a_full_grip(self):
        self.assertEqual(grip_hit_factor(_choice(2), free_slots=1), 1.0)

    def test_no_free_hand_is_an_under_grip(self):
        self.assertAlmostEqual(grip_hit_factor(_choice(2), free_slots=0), 0.6)

    def test_two_of_three_hands(self):
        self.assertAlmostEqual(grip_hit_factor(_choice(3), free_slots=1), 0.8)

    def test_a_one_handed_weapon_never_pays(self):
        self.assertEqual(grip_hit_factor(_choice(1), free_slots=0), 1.0)

    def test_natural_and_integrated_weapons_never_pay(self):
        self.assertEqual(grip_hit_factor(_choice(2, natural=True), free_slots=0), 1.0)
        self.assertEqual(grip_hit_factor(_choice(2, integrated=True), free_slots=0), 1.0)

    def test_unarmed_pays_nothing(self):
        self.assertEqual(grip_hit_factor(None, free_slots=0), 1.0)


class TheRollPays(EvenniaTest):
    """process_attack multiplies the grip factor beside manipulation."""

    def setUp(self):
        super().setUp()
        self.char2.location = self.room1
        setattr(self.char1.ndb, NDB_PROXIMITY, {self.char2})
        setattr(self.char2.ndb, NDB_PROXIMITY, {self.char1})
        self.handler = mock.MagicMock()
        self.entry = {"char": self.char1}
        self.handler.db.combatants = [self.entry, {"char": self.char2}]
        self.char1.msg = lambda text=None, **kw: None
        self.char2.msg = lambda text=None, **kw: None
        self.char2.take_damage = mock.MagicMock(return_value=(False, 3))
        self.rifle = create_object("typeclasses.items.Item", key="bolt-action rifle", location=self.char1)
        self.rifle.db.hands_required = 2
        self.rifle.db.is_ranged = True
        self.rifle.tags.add("weapon", category="type")

    def _roll(self):
        choice = WeaponChoice(items=(self.rifle,), slots=("left_hand",), lead_slot="left_hand", hands_required=2,
                              damage=0, hit_bonus=0, damage_type="bullet", weapon_type="bolt-action_rifle",
                              is_ranged=True, natural=False)
        spl = mock.MagicMock()
        with mock.patch.object(A, "choose_weapon", return_value=choice), \
             mock.patch.object(A, "randint", return_value=10), \
             mock.patch.object(A, "get_splattercast", return_value=spl):
            A.process_attack(self.handler, self.char1, self.char2, self.entry, self.handler.db.combatants)
        lines = [str(c.args[0]) for c in spl.msg.call_args_list if c.args]
        roll = next(float(m.group(1)) for line in lines for m in [re.search(r"^ATTACK: .* \(roll ([0-9.]+)\) vs", line)] if m)
        return roll, lines

    def test_a_free_hand_costs_nothing(self):
        self.char1.hands = {"left_hand": self.rifle}
        roll, lines = self._roll()
        self.assertFalse(any("grip 0." in line for line in lines), lines)

    def test_a_full_other_hand_pays(self):
        self.char1.hands = {"left_hand": self.rifle}
        full, _ = self._roll()
        bottle = create_object("typeclasses.items.Item", key="bottle", location=self.char1)
        self.char1.hands = {"right_hand": bottle}
        under, lines = self._roll()
        self.assertLess(under, full)
        self.assertTrue(any("grip 0.60" in line for line in lines), lines)


class ThePlayerIsTold(EvenniaCommandTest):

    def _rifle(self, where):
        rifle = create_object("typeclasses.items.Item", key="bolt-action rifle", location=where)
        rifle.db.hands_required = 2
        rifle.tags.add("weapon", category="type")
        return rifle

    def test_inventory_marks_a_two_handed_weapon(self):
        from commands.CmdInventory import CmdInventory
        self.char1.db.species = "human"
        self.char1.hands = {"left_hand": self._rifle(self.char1)}
        out = self.call(CmdInventory(), "", caller=self.char1)
        self.assertIn("(two-handed)", out)

    def test_filling_the_other_hand_says_the_rifle_hangs_one_handed(self):
        self.char1.db.species = "human"
        rifle = self._rifle(self.char1)
        self.assertNotIn("hangs", self.char1.wield_item(rifle, "left_hand"))
        bottle = create_object("typeclasses.items.Item", key="bottle", location=self.char1)
        said = self.char1.wield_item(bottle, "right_hand")
        self.assertIn("bolt-action rifle hangs one-handed", said)

    def test_taking_a_two_hander_with_the_other_hand_full_says_it_wants_both(self):
        self.char1.db.species = "human"
        bottle = create_object("typeclasses.items.Item", key="bottle", location=self.char1)
        self.char1.wield_item(bottle, "right_hand")
        said = self.char1.wield_item(self._rifle(self.char1), "left_hand")
        self.assertIn("It wants both hands.", said)

    def test_get_with_both_hands_full_says_only_that_the_taken_two_hander_wants_both(self):
        # The swap frees nothing and fills nothing for the other hand, so a
        # two-hander already hanging there stays unmentioned.
        from commands.CmdInventory import CmdGet
        self.char1.db.species = "human"
        bat = create_object("typeclasses.items.Item", key="baseball bat", location=self.char1)
        bat.db.hands_required = 2
        self.char1.wield_item(create_object("typeclasses.items.Item", key="bottle", location=self.char1), "left_hand")
        self.char1.wield_item(bat, "right_hand")
        self._rifle(self.room1)
        out = self.call(CmdGet(), "rifle", caller=self.char1)
        self.assertIn("Your hands are full.", out)
        self.assertIn("It wants both hands.", out)
        self.assertNotIn("baseball bat hangs", out)

    def test_a_weapon_filling_the_slots_it_wants_is_not_hanging(self):
        # One object stored in two slots (the broken-hand path) is one
        # weapon with both hands: no note, and never two notes.
        self.char1.db.species = "human"
        rifle = self._rifle(self.char1)
        self.char1.held_items = {"left_hand": rifle, "right_hand": rifle}
        self.assertEqual(self.char1.grip_notes(), "")

    def test_the_taken_weapon_speaks_first_and_each_weapon_once(self):
        self.char1.db.species = "human"
        bat = create_object("typeclasses.items.Item", key="baseball bat", location=self.char1)
        bat.db.hands_required = 2
        self.char1.wield_item(bat, "left_hand")
        said = self.char1.wield_item(self._rifle(self.char1), "right_hand")
        self.assertTrue(said.endswith(" It wants both hands. The baseball bat hangs one-handed."), said)

    def test_get_tells_the_same(self):
        from commands.CmdInventory import CmdGet
        self.char1.db.species = "human"
        self.char1.wield_item(self._rifle(self.char1), "left_hand")
        create_object("typeclasses.items.Item", key="bottle", location=self.room1)
        out = self.call(CmdGet(), "bottle", caller=self.char1)
        self.assertIn("hangs one-handed", out)


class TheDataSaysSo(TestCase):

    def test_bat_staff_and_chainsaw_want_two_hands(self):
        from world import prototypes as P
        for proto in (P.BASEBALL_BAT, P.STAFF, P.CHAINSAW):
            self.assertEqual(proto.get("hands_required"), 2, proto["key"])

    def test_the_racket_lost_its_stray_key(self):
        from world import prototypes as P
        self.assertNotIn("hands", P.TENNIS_RACKET)

    def test_the_door_reads_the_requirement(self):
        rifle = SimpleNamespace(key="rifle", tags=SimpleNamespace(has=lambda k, category=None: True),
                                db=SimpleNamespace(is_ranged=True, damage=5, weapon_type="bolt-action_rifle",
                                                   damage_type=None, hit_bonus=None, akimbo_family=None,
                                                   akimbo_profiles=None, hands_required=2, integrated=False))
        char = SimpleNamespace(hands={"left_hand": rifle, "right_hand": None}, location=object(),
                               ndb=SimpleNamespace(), slot_order=lambda names: sorted(names))
        with mock.patch("world.medical.augments.get_active_natural_weapons", return_value=[]):
            self.assertEqual(choose_weapon(char).hands_required, 2)


class TheCutLeavesNoGhost(EvenniaTest):
    """detach_items_to_appendage re-reads the store after the drop (§3)."""

    def test_an_object_in_two_slots_leaves_both_when_one_hand_is_cut(self):
        from typeclasses.items import apply_sever_to_character
        self.char1.db.species = "human"
        knife = create_object("typeclasses.items.Item", key="knife", location=self.char1)
        self.char1.held_items = {"left_hand": knife, "right_hand": knife}
        apply_sever_to_character(self.char1, "left_arm")
        self.assertEqual(knife.location, self.room1, "the knife did not drop")
        self.assertIsNone((self.char1.held_items or {}).get("right_hand"),
                          "the surviving slot still points at a knife on the floor")
