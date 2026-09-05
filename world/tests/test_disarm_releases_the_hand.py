"""A disarmed weapon leaves the hand it was in (#2421).

`Character.hands` is a DERIVED view, rebuilt on every read from the
`held_items` AttributeProperty. Mutating the dict it returns changes
nothing. Two call sites mutate the throwaway and never write back:

    world/combat/actions.py     resolve_disarm
    commands/CmdExplosives.py   rig_grenade

The stale comment at `actions.py:88` is the likely cause -- it still says
"hands is an AttributeProperty on Character", which stopped being true at
the PR-H2 migration. Every other consumer snapshots and writes back and
says so; these two were missed.

The reported symptom was two copies of one weapon in play: on the floor
for anyone to pick up, AND still wielded, with the "disarmed" character
attacking at full weapon damage.

Nothing exercised `resolve_disarm` -- `grep resolve_disarm world/tests/`
returned nothing -- which is why the suite stayed green over it. That
absence is most of what this file is for: it pins the OUTCOME (the hand
is empty, the weapon is on the floor, and there is exactly one of it),
not the mechanism, so it holds whichever layer ends up doing the work.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaTest

from world.combat.actions import resolve_disarm
from world.combat.constants import (
    DB_CHAR,
    DB_COMBAT_ACTION_TARGET,
    NDB_PROXIMITY,
)


class _DisarmCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.attacker = self.char1
        self.victim = self.char2
        self.attacker.location = self.room1
        self.victim.location = self.room1

        self.weapon = self.obj1
        self.weapon.key = "a rust-pitted machete"
        self.weapon.tags.add("weapon", category="type")
        self.weapon.location = self.victim
        self.victim.held_items = {"right_hand": self.weapon}

        # in melee, and both in the same fight
        setattr(self.attacker.ndb, NDB_PROXIMITY, {self.victim})
        setattr(self.victim.ndb, NDB_PROXIMITY, {self.attacker})
        self.handler = mock.MagicMock()
        self.handler.db.combatants = [{DB_CHAR: self.victim},
                                      {DB_CHAR: self.attacker}]
        self.entry = {DB_COMBAT_ACTION_TARGET: self.victim}

    def disarm(self, win=True):
        """Drive the real resolver with the opposed roll decided."""
        rolls = [10, 1] if win else [1, 10]
        with mock.patch("world.combat.actions.roll_stat",
                        side_effect=rolls):
            resolve_disarm(self.handler, self.attacker, self.entry)

    def held(self):
        return dict(self.victim.held_items or {})


class TestASuccessfulDisarmEmptiesTheHand(_DisarmCase):
    def test_the_hand_is_empty_afterwards(self):
        self.disarm()
        self.assertNotIn(self.weapon, self.held().values())

    def test_the_derived_view_agrees(self):
        """`hands` is what `get_wielded_weapon` and `inventory` read. It
        reported the weapon as still wielded while it lay on the floor."""
        self.disarm()
        self.assertIsNone(self.victim.hands.get("right_hand"))

    def test_the_weapon_is_on_the_floor(self):
        self.disarm()
        self.assertIs(self.weapon.location, self.room1)

    def test_there_is_only_one_of_it(self):
        """The whole complaint: on the floor for a third party to pick
        up AND still in the victim's hand."""
        self.disarm()
        on_floor = self.weapon.location is self.room1
        in_hand = self.weapon in self.held().values()
        self.assertTrue(on_floor)
        self.assertFalse(in_hand)


class TestAFailedDisarmChangesNothing(_DisarmCase):
    def test_the_weapon_stays_in_the_hand(self):
        self.disarm(win=False)
        self.assertIs(self.held().get("right_hand"), self.weapon)

    def test_the_weapon_stays_on_the_body(self):
        self.disarm(win=False)
        self.assertIs(self.weapon.location, self.victim)


class TestOtherHandsAreUntouched(_DisarmCase):
    def test_the_off_hand_keeps_what_it_held(self):
        other = self.obj2
        other.location = self.victim
        self.victim.held_items = {"right_hand": self.weapon,
                                  "left_hand": other}
        self.disarm()
        self.assertIs(self.held().get("left_hand"), other)


class TestRiggingAGrenadeReleasesTheHand(_DisarmCase):
    """`rig_grenade` had the identical shape, with a live explosive:
    wielded AND rigged to the exit at the same time (#2421)."""

    def setUp(self):
        super().setUp()
        from commands.CmdExplosives import CmdRig
        self.grenade = self.obj2
        self.grenade.key = "a dented frag grenade"
        self.grenade.location = self.attacker
        self.attacker.held_items = {"right_hand": self.grenade}
        self.cmd = CmdRig()
        self.cmd.caller = self.attacker
        # self.exit is room1 -> room2, from EvenniaTest

    def rig(self):
        self.cmd.rig_grenade(self.grenade, self.exit)

    def test_the_hand_is_empty_afterwards(self):
        self.rig()
        self.assertNotIn(self.grenade,
                         dict(self.attacker.held_items or {}).values())

    def test_the_grenade_is_rigged_to_the_exit(self):
        self.rig()
        self.assertIs(self.exit.db.rigged_grenade, self.grenade)

    def test_it_is_not_wielded_and_rigged_at_once(self):
        self.rig()
        wielded = self.grenade in dict(self.attacker.held_items or {}).values()
        self.assertFalse(wielded)
        self.assertIs(self.exit.db.rigged_grenade, self.grenade)
