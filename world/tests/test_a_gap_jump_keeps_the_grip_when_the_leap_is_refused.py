"""The gap jump keeps its grip when the leap cannot happen (#3684).

`jump across <gap>` while grappling released the hold and spoke the
`release_jump` beat as soon as the price of leaving was paid -- before
the roll and before the jumper's own move. A jumper whose hooked move
`at_pre_move` refuses (a channel, a live escort) was then refused with
the victim already freed and told, and the jumper still on the roof
having announced a leap they never made.

Now the hold is let go only once the leap is real: after a move that
happened (the beat spoken to the roof they left) or on a slip in place,
which is an attempt made. What refuses a jumper's move is the whole
walk of hooks and exits, and nothing predicts it exactly, so nothing
tries: a refused move keeps the hold and says only what the gate says.

Controls: a free jumper still releases the hold for the leap and the
victim still hears it; a slip in place still lets go.
"""
from contextlib import ExitStack
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

import world.gravity as gravity
from world.channeled import begin_channel, channel_of
from world.combat.constants import (
    DB_GRAPPLED_BY_DBREF, DB_GRAPPLING_DBREF, NDB_COMBAT_HANDLER,
)
from world.combat.utils import get_character_dbref
from world.consent import grant_trust
from world.gravity import NDB_FALL_INTENT, NDB_LEAP


class _AGapWithAHold(EvenniaTest):
    """jumper (char1) holds victim (char2) on the roof (room1); `east` is a
    gap with no air beneath (room2 is solid) onto the far roof."""

    def setUp(self):
        super().setUp()
        self.jumper, self.victim = self.char1, self.char2
        self.roof = self.room1
        self.victim.location = self.roof
        self.said, self.heard = [], []
        self.jumper.msg = lambda text=None, **kw: self.said.append(str(text))
        self.victim.msg = lambda text=None, **kw: self.heard.append(str(text))
        self.far = create_object("typeclasses.rooms.Room", key="Far Roof")
        self.gap = self.exit
        self.gap.key = "east"
        self.gap.db.is_gap = True
        self.gap.db.gap_destination = self.far
        self.handler = mock.MagicMock()
        self.handler.db.combatants = [
            {"char": self.jumper, DB_GRAPPLING_DBREF: get_character_dbref(self.victim)},
            {"char": self.victim, DB_GRAPPLED_BY_DBREF: get_character_dbref(self.jumper)},
        ]
        setattr(self.jumper.ndb, NDB_COMBAT_HANDLER, self.handler)

    def channeling(self, who):
        ok = begin_channel(who, 30, "spraying a wall",
                           on_complete=lambda: None, on_interrupt=lambda f: None,
                           key="spraying")
        self.assertTrue(ok, "fixture: the channel did not start")

    def leap(self, *, rolled):
        from commands.combat.jump import CmdJump
        cmd = CmdJump()
        cmd.caller = self.jumper
        cmd.direction = "east"
        with ExitStack() as stack:
            for target in ("commands.combat.jump.clear_aim_state",
                           "commands.combat.jump.msg_room_identity",
                           "commands.explosion_utils.check_rigged_grenade",
                           "commands.explosion_utils.check_auto_defuse"):
                stack.enter_context(mock.patch(target))
            stack.enter_context(mock.patch("commands.combat.jump.standard_roll",
                                           return_value=(rolled, rolled, rolled)))
            stack.enter_context(mock.patch.object(type(cmd), "find_edge_exit", return_value=self.gap))
            stack.enter_context(mock.patch.object(type(cmd), "pay_the_price_of_leaving", return_value=True))
            stack.enter_context(mock.patch.object(gravity, "msg_room_identity"))
            stack.enter_context(mock.patch.object(gravity, "delay"))
            self.room_beat = stack.enter_context(mock.patch("world.combat.grappling.msg_room_identity"))
            cmd.handle_gap_jump()

    def grip(self):
        entries = self.handler.db.combatants
        return (entries[0].get(DB_GRAPPLING_DBREF), entries[1].get(DB_GRAPPLED_BY_DBREF))

    def held(self):
        return (get_character_dbref(self.victim), get_character_dbref(self.jumper))

    def released_line(self, lines):
        return any("turn" in t or "run at the gap" in t or "grip on" in t for t in lines)


class TheGripIsKept(_AGapWithAHold):

    def test_control_a_free_jumper_lets_go_for_the_leap(self):
        self.leap(rolled=999)
        self.assertIs(self.jumper.location, self.far)
        self.assertEqual(self.grip(), (None, None))
        self.assertTrue(self.released_line(self.heard), self.heard)
        self.assertTrue(self.room_beat.called)

    def test_a_channeling_jumper_is_refused_and_keeps_the_hold(self):
        self.channeling(self.jumper)
        self.leap(rolled=999)
        self.assertIs(self.jumper.location, self.roof)
        self.assertEqual(self.grip(), self.held(), "the hold was released for a leap that never happened")
        self.assertFalse(self.released_line(self.heard), self.heard)
        self.assertFalse(self.room_beat.called, "the roof heard a hold end that did not")
        self.assertTrue(any("busy" in t for t in self.said), self.said)
        self.assertTrue(channel_of(self.jumper))

    def test_control_a_slip_in_place_still_lets_go(self):
        # A miss with no air beneath is a slip where you stand: an attempt
        # made, so the grip opens for it as it always did. (That a
        # channeling jumper gets to attempt at all is #3685's subject.)
        self.channeling(self.jumper)
        self.leap(rolled=-999)
        self.assertIs(self.jumper.location, self.roof)
        self.assertEqual(self.grip(), (None, None))
        self.assertTrue(self.released_line(self.heard), self.heard)
        self.assertEqual(self.room_beat.call_args.kwargs["location"], self.roof)

    def test_a_channeling_jumper_who_misses_over_air_is_refused_and_keeps_the_hold(self):
        # The fourth let-go site: a missed leap over air is a move into
        # the cell, which the gate refuses; nothing is let go, nothing
        # left behind.
        air = create_object("typeclasses.rooms.SkyRoom", key="In the Air")
        self.gap.destination = air
        self.channeling(self.jumper)
        self.leap(rolled=-999)
        self.assertIs(self.jumper.location, self.roof)
        self.assertEqual(self.grip(), self.held())
        self.assertFalse(self.released_line(self.heard), self.heard)
        self.assertFalse(self.room_beat.called)
        self.assertIsNone(getattr(self.jumper.ndb, NDB_FALL_INTENT, None))
        self.assertTrue(any("busy" in t for t in self.said), self.said)

    def marching_the_victim(self):
        # `escort` needs no consent from a restrained escortee, so the
        # jumper can be escorting the very person they hold. The mock
        # handler is invisible to `is_restrained`, so the victim here
        # reads as free; trust stands in for the restraint, or the usher
        # would release the march on its own and the pin would not bite.
        # The gap takes the usual shape (its own destination IS the
        # perch), so the usher has an exit to walk the victim at -- the
        # gap exit, which refuses a walker. A clear that ran AFTER the
        # move would leave that walk in place and the jumper refused.
        self.gap.db.gap_destination = None
        self.gap.destination = self.far
        grant_trust(self.victim, self.jumper, "escort")
        self.jumper.db.escorting = self.victim

    def test_a_jumper_marching_their_own_victim_still_leaps_and_the_march_ends(self):
        # The march stood on the hold; it ends before the move, or the
        # usher would walk the victim at the gap and refuse the jumper --
        # which the hold-first order never did.
        self.marching_the_victim()
        self.leap(rolled=999)
        self.assertIs(self.jumper.location, self.far)
        self.assertIs(self.victim.location, self.roof)
        self.assertFalse(self.jumper.db.escorting)
        self.assertEqual(self.grip(), (None, None))
        self.assertTrue(any("stop leading" in t for t in self.said), self.said)
        self.assertTrue(any("stops leading you" in t for t in self.heard), self.heard)
        self.assertTrue(self.released_line(self.heard), self.heard)

    def test_a_channeling_marcher_is_refused_with_the_march_and_the_hold_intact(self):
        # The channel gate refuses before the usher is ever asked, so the
        # march was not what stood in the way: nothing ends, nothing is
        # said but what the gate says.
        self.marching_the_victim()
        self.channeling(self.jumper)
        self.leap(rolled=999)
        self.assertIs(self.jumper.location, self.roof)
        self.assertIs(self.jumper.db.escorting, self.victim)
        self.assertEqual(self.grip(), self.held())
        self.assertEqual(self.heard, [], self.heard)
        self.assertEqual(self.said, ["You're busy spraying — 'stop' first."], self.said)

    def test_the_roof_hears_the_grip_open_after_the_leap(self):
        # The beat is spoken once the jumper has gone: its room line lands
        # on the roof they left, not the perch they reached.
        self.leap(rolled=999)
        self.assertIs(self.jumper.location, self.far)
        self.assertEqual(self.room_beat.call_args.kwargs["location"], self.roof)

    def escorted_by_jumper(self):
        other = create_object("typeclasses.characters.Character", key="Other", location=self.roof)
        self.told_other = []
        other.msg = lambda text=None, **kw: self.told_other.append(str(text))
        grant_trust(other, self.jumper, "escort")
        self.jumper.db.escorting = other
        return other

    def test_a_jumper_with_a_live_escort_over_air_is_refused_and_keeps_the_hold(self):
        # The usher walks the escortee at the gap exit, which refuses a
        # walker, so the jumper is refused by the real gate.
        air = create_object("typeclasses.rooms.SkyRoom", key="In the Air")
        self.gap.destination = air
        other = self.escorted_by_jumper()
        self.leap(rolled=999)
        self.assertIs(self.jumper.location, self.roof)
        self.assertIs(other.location, self.roof)
        self.assertEqual(self.grip(), self.held())
        self.assertFalse(self.released_line(self.heard), self.heard)
        self.assertTrue(any("cannot" in t for t in self.told_other), self.told_other)

    def test_control_a_live_escort_with_no_exit_to_the_perch_does_not_refuse(self):
        # This fixture's gap lands on a perch no exit leads to (the exit
        # goes to the solid room below; `gap_destination` names the far
        # roof), so the usher steps aside and the leader moves on: the
        # leap happens and the grip opens for it. Predicting a refusal
        # here would keep a hold for a leap that DID happen.
        other = self.escorted_by_jumper()
        self.leap(rolled=999)
        self.assertIs(self.jumper.location, self.far)
        self.assertEqual(self.grip(), (None, None))
        self.assertTrue(self.released_line(self.heard), self.heard)

    def test_a_live_escort_on_the_usual_direct_step_is_refused_and_keeps_the_hold(self):
        # The usual direct-step gap: the exit's own destination IS the
        # perch, so the usher walks the escortee at the gap exit, which
        # refuses a walker, and the jumper is refused by the real gate.
        self.gap.db.gap_destination = None
        self.gap.destination = self.far
        other = self.escorted_by_jumper()
        self.leap(rolled=999)
        self.assertIs(self.jumper.location, self.roof)
        self.assertIs(other.location, self.roof)
        self.assertEqual(self.grip(), self.held())
        self.assertFalse(self.released_line(self.heard), self.heard)
        self.assertTrue(any("cannot" in t for t in self.told_other), self.told_other)

    def test_control_a_plain_door_to_the_perch_is_walked_and_the_grip_opens(self):
        # A plank beside the gap: the usher walks the escortee across it
        # and the leader moves on, so the leap happens and the hold opens
        # for it. Counting any exit as a refusal would keep the hold for
        # a leap that DID happen and then break it without a word.
        create_object("typeclasses.exits.Exit", key="plank", location=self.roof, destination=self.far)
        other = self.escorted_by_jumper()
        self.leap(rolled=999)
        self.assertIs(self.jumper.location, self.far)
        self.assertIs(other.location, self.far)
        self.assertEqual(self.grip(), (None, None))
        self.assertTrue(self.released_line(self.heard), self.heard)

    def test_a_channeling_jumper_over_air_is_refused_with_nothing_left_behind(self):
        air = create_object("typeclasses.rooms.SkyRoom", key="In the Air")
        self.gap.destination = air
        self.channeling(self.jumper)
        self.leap(rolled=999)
        self.assertIs(self.jumper.location, self.roof)
        self.assertEqual(self.grip(), self.held())
        self.assertFalse(self.released_line(self.heard), self.heard)
        self.assertIsNone(getattr(self.jumper.ndb, NDB_LEAP, None))
