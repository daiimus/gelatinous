"""The weapon's to-hit term reaches the roll (MULTI_WEAPON_COMBAT_SPEC §5).

`process_attack` adds `choice.hit_bonus` beside the charge bonus: an akimbo
profile's +1 lands on the d20, a plain weapon's 0 changes nothing. Pinned
on the splattercast roll line with the dice held still.
"""
import re
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.combat import attack as A
from world.combat.constants import NDB_LAST_WEAPON_SLOT, NDB_PROXIMITY
from world.combat.weapon_choice import WeaponChoice


class TheHitBonusLandsOnTheRoll(EvenniaTest):

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
        self.claws = create_object("typeclasses.items.Item", key="carbide blades", location=None)

    def _swing(self, hit_bonus):
        choice = WeaponChoice(items=(self.claws,), slots=(), lead_slot="left_hand", damage=0,
                              hit_bonus=hit_bonus, damage_type="cut", weapon_type="nailz_akimbo",
                              is_ranged=False, natural=True)
        spl = mock.MagicMock()
        with mock.patch.object(A, "choose_weapon", return_value=choice), \
             mock.patch.object(A, "randint", return_value=10), \
             mock.patch.object(A, "get_splattercast", return_value=spl):
            A.process_attack(self.handler, self.char1, self.char2, self.entry, self.handler.db.combatants)
        lines = [str(c.args[0]) for c in spl.msg.call_args_list if c.args]
        roll = next((m.group(1) for line in lines
                     for m in [re.search(r"^ATTACK: .* \(roll ([0-9.]+)\) vs", line)] if m), None)
        self.assertIsNotNone(roll, lines)
        return float(roll), lines

    def test_a_pair_profile_adds_its_bonus(self):
        plain, _ = self._swing(0)
        boosted, lines = self._swing(1)
        self.assertAlmostEqual(boosted, plain + 1)
        self.assertTrue(any("+1 from nailz_akimbo" in line for line in lines), lines)

    def test_a_plain_weapon_announces_nothing(self):
        _, lines = self._swing(0)
        self.assertFalse(any("from nailz_akimbo" in line for line in lines), lines)


class TheWheelTurnsOnlyOnARealSwing(TheHitBonusLandsOnTheRoll):
    """§6: the cursor moves once the reach gates pass, and never on a
    refused swing."""

    def test_a_swing_that_lands_turns_the_wheel(self):
        self._swing(0)
        self.assertEqual(getattr(self.char1.ndb, NDB_LAST_WEAPON_SLOT, None), "left_hand")

    def test_a_refused_melee_swing_leaves_the_cursor_alone(self):
        setattr(self.char1.ndb, NDB_PROXIMITY, set())            # not closed to melee
        if getattr(self.char1.ndb, NDB_LAST_WEAPON_SLOT, None) is not None:
            delattr(self.char1.ndb, NDB_LAST_WEAPON_SLOT)
        choice = WeaponChoice(items=(self.claws,), slots=("left_hand",), lead_slot="left_hand", damage=0,
                              hit_bonus=0, damage_type="cut", weapon_type="nailz", is_ranged=False, natural=True)
        with mock.patch.object(A, "choose_weapon", return_value=choice), \
             mock.patch.object(A, "get_splattercast", return_value=mock.MagicMock()):
            A.process_attack(self.handler, self.char1, self.char2, self.entry, self.handler.db.combatants)
        self.assertIsNone(getattr(self.char1.ndb, NDB_LAST_WEAPON_SLOT, None), "a refused swing turned the wheel")
