"""Stepping off an edge always succeeds; the ROOM decides the rest.

**The history.** #2441 filed the original defect: `handle_edge_descent`'s
fallback branch -- taken when an `is_edge` exit had no `db.sky_room` --
moved the jumper to the exit's `destination`, applied landing damage and
said "you land safely". Correct for the nine such exits whose
destination is a street; catastrophic for the one whose destination was
an air cell, because 81 of the colony's 155 sky rooms are exitless and a
character put there was unrecoverable by anything but `@tel`. The fix at
the time was a REFUSAL on the roof.

**#3579 removed the reason for the refusal.** Gravity is now a property
of the room: an air cell takes anything that arrives in it down its own
`down` chain, one cell per tick, and a cell with nothing beneath stops
the body cleanly where it is (#3581). There is no longer anything to
configure and nothing to strand, so the edge no longer refuses -- it
steps off, and the cell takes over. The old `sky_room` attribute is not
read by anything.

Three things must stay true, and this file is what holds them:

1. an edge into air MOVES the jumper and starts a fall (the record is
   written and exactly one tick is scheduled);
2. the nine street-destination edges still work exactly as before,
   "land safely" and all -- a direct drop, one storey, no column;
3. a REFUSED move narrates nothing and costs nothing (#3353). The
   branch checks its own `move_to` return value, and the bug it guards
   is announcing a leap that never happened.
"""
from contextlib import ExitStack
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

import world.gravity as gravity


class _EdgeCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.jumper = self.char1
        self.roof = self.room1
        self.jumper.location = self.roof
        self.said = []
        self.jumper.msg = lambda text=None, **kw: self.said.append(str(text))
        self.street = create_object("typeclasses.rooms.Room",
                                    key="Test Street")

    def descend(self, *, dest_is_sky, refuse_move=False):
        """`handle_edge_descent(self)` takes no arguments -- it reads the
        direction off the command and resolves the exit itself, so the
        fixture configures the real exit rather than passing one in."""
        from commands.combat.jump import CmdJump

        exit_obj = self.exit                 # room1 -> room2, from EvenniaTest
        exit_obj.key = "south"
        exit_obj.db.is_edge = True
        exit_obj.destination.db.is_sky_room = dest_is_sky
        if dest_is_sky:
            exit_obj.destination.key = "In the Air"
            create_object("typeclasses.exits.Exit", key="down",
                          location=exit_obj.destination,
                          destination=self.street, aliases=["d"])

        cmd = CmdJump()
        cmd.caller = self.jumper
        cmd.direction = "south"

        with ExitStack() as stack:
            for target in ("commands.combat.jump.clear_aim_state",
                           "commands.combat.jump.msg_room_identity",
                           "commands.explosion_utils.check_rigged_grenade",
                           "commands.explosion_utils.check_auto_defuse"):
                stack.enter_context(mock.patch(target))
            stack.enter_context(mock.patch.object(
                type(cmd), "find_edge_exit", return_value=exit_obj))
            stack.enter_context(mock.patch.object(
                gravity, "msg_room_identity"))
            self.delayed = stack.enter_context(
                mock.patch.object(gravity, "delay"))
            if refuse_move:
                stack.enter_context(mock.patch.object(
                    type(self.jumper), "move_to", return_value=False))
            cmd.handle_edge_descent()
        return " ".join(self.said)

    def hurt(self):
        return sum(o.max_hp - o.current_hp
                   for o in self.jumper.medical_state.organs.values())


class TestAnEdgeIntoAirStepsOffAndFalls(_EdgeCase):
    """The branch that used to refuse. There is nothing to configure any
    more: the air cell is the flight plan."""

    def test_the_jumper_leaves_the_roof(self):
        self.descend(dest_is_sky=True)
        self.assertIsNot(self.jumper.location, self.roof)

    def test_they_are_in_the_air_cell(self):
        self.descend(dest_is_sky=True)
        self.assertIs(self.jumper.location, self.exit.destination)

    def test_a_fall_record_is_written(self):
        self.descend(dest_is_sky=True)
        self.assertTrue(self.jumper.db.falling)

    def test_exactly_one_tick_is_scheduled(self):
        self.descend(dest_is_sky=True)
        self.assertEqual(self.delayed.call_count, 1)
        self.assertIs(self.delayed.call_args[0][1], gravity._fall_step)

    def test_the_fall_will_roll_to_land(self):
        """They chose to step off, so the landing is theirs to make."""
        self.descend(dest_is_sky=True)
        self.assertTrue(self.jumper.db.falling["roll"])

    def test_they_are_told_they_are_falling_not_that_they_landed(self):
        said = self.descend(dest_is_sky=True)
        self.assertIn("falling through the air", said)
        self.assertNotIn("land safely", said)

    def test_no_damage_is_charged_at_takeoff(self):
        """The column charges once, at the bottom."""
        self.descend(dest_is_sky=True)
        self.assertEqual(self.hurt(), 0)


class TestTheStreetDestinationEdgeIsUnchanged(_EdgeCase):
    """Nine `is_edge` exits target a STREET. A direct drop: one storey,
    no roll, no column, and the line they have always printed."""

    def test_a_street_destination_still_lands_you(self):
        self.descend(dest_is_sky=False)
        self.assertIs(self.jumper.location, self.room2)

    def test_and_says_so(self):
        self.assertIn("land safely", self.descend(dest_is_sky=False))

    def test_and_starts_no_fall(self):
        self.descend(dest_is_sky=False)
        self.assertFalse(self.jumper.db.falling)
        self.assertEqual(self.delayed.call_count, 0)

    def test_and_costs_one_storey(self):
        from world.combat.constants import FALL_DAMAGE_PER_STORY
        self.descend(dest_is_sky=False)
        self.assertEqual(self.hurt(), FALL_DAMAGE_PER_STORY)


class TestARefusedMoveNarratesNothing(_EdgeCase):
    """#3353. Both branches check their own `move_to` return value; the
    bug is announcing a leap that the world refused."""

    def test_a_refused_direct_drop_says_nothing_at_all(self):
        said = self.descend(dest_is_sky=False, refuse_move=True)
        self.assertEqual(said, "")

    def test_a_refused_direct_drop_costs_nothing(self):
        self.descend(dest_is_sky=False, refuse_move=True)
        self.assertEqual(self.hurt(), 0)

    def test_a_refused_direct_drop_leaves_them_on_the_roof(self):
        self.descend(dest_is_sky=False, refuse_move=True)
        self.assertIs(self.jumper.location, self.roof)

    def test_a_refused_transit_says_nothing_at_all(self):
        said = self.descend(dest_is_sky=True, refuse_move=True)
        self.assertEqual(said, "")

    def test_a_refused_transit_starts_no_fall(self):
        self.descend(dest_is_sky=True, refuse_move=True)
        self.assertFalse(self.jumper.db.falling)
        self.assertEqual(self.delayed.call_count, 0)

    def test_a_refused_transit_leaves_no_flight_plan_behind(self):
        """A leftover `fall_intent` would roll the NEXT arrival in air
        against this edge's difficulty."""
        self.descend(dest_is_sky=True, refuse_move=True)
        self.assertIsNone(getattr(self.jumper.ndb, "fall_intent", None))
