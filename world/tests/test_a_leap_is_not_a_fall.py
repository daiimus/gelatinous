"""A made leap crosses the gap; a missed one is just a fall (#3579).

Gravity is a property of the room, so a leap has to survive being inside
an air cell for a tick without the cell taking it down the column. The
mechanism is a one-tick ``ndb.airborne_token``, and the defects it
guards:

* **The token must be spent ON ARRIVAL, not on landing.** A far perch
  that is itself air would otherwise re-grant the token on every
  arrival and the leaper would drift across the sky for ever.
* **A gap whose far perch no longer exists is refused ON THE ROOF
  (#3559).** The old code silently substituted the exit's own
  destination -- the air cell -- so a deleted perch turned a jump into
  an unannounced fall. A raw dbref that no longer resolves is a build
  error, and the honest answer is "that doesn't go anywhere".
* **The roof must see them go.** The move is ``quiet=True``, so without
  an explicit broadcast the room they leapt from saw a character
  vanish (#2424).
* **A failed leap is an ordinary fall**: no token, no landing roll
  (they did not choose to descend), and the cell's gravity takes over.

``delay`` is patched to QUEUE its callbacks and drain them after the
command returns, which reproduces the production order (the command
finishes, then the reactor fires the tick) while still counting every
tick that was scheduled.

The verb's post-move guards read ``if not moved:`` and deliberately do
NOT re-check ``self.caller.location``: the cell's hook may already have
carried the body onward, and that is not a refusal. An earlier version
of this file ran the ticks inline and caught exactly that -- the leap
landed on the far perch inside ``move_to``, the location check fired,
and the roof never heard the departure line (#2424 all over again).
``TestTheHookMayLandThemBeforeTheVerbFinishes`` below holds the fix.
"""

from __future__ import annotations

from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

import world.gravity as gravity
from world.combat.constants import NDB_AIRBORNE_TOKEN


def _queue(mocked):
    """Collect scheduled callbacks instead of running them; returns the
    pending list, which nested schedules append to."""
    pending = []
    mocked.side_effect = (
        lambda _seconds, callback, *a, **kw: pending.append((callback, a, kw)))
    return pending


def _drain(pending, limit=40):
    """Fire the queue in order, the way a reactor would."""
    fired = 0
    while pending and fired < limit:
        callback, args, kwargs = pending.pop(0)
        callback(*args, **kwargs)
        fired += 1
    return fired


class _GapCase(EvenniaTest):
    """roof --east(gap)--> air1 -> air2 -> street, with a far roof."""

    def setUp(self):
        super().setUp()
        self.roof, self.street = self.room1, self.room2
        self.roof.key = "Near Roof"
        self.street.key = "Test Street"
        self.far = create_object("typeclasses.rooms.Room", key="Far Roof")
        self.air1 = create_object("typeclasses.rooms.SkyRoom",
                                  key="In the Air")
        self.air2 = create_object("typeclasses.rooms.SkyRoom",
                                  key="In the Air")
        create_object("typeclasses.exits.Exit", key="down",
                      location=self.air1, destination=self.air2,
                      aliases=["d"])
        create_object("typeclasses.exits.Exit", key="down",
                      location=self.air2, destination=self.street,
                      aliases=["d"])
        self.gap = create_object("typeclasses.exits.Exit", key="east",
                                 location=self.roof, destination=self.air1)
        self.gap.db.is_gap = True
        self.gap.db.is_edge = True
        self.gap.db.gap_destination = self.far
        self.char1.location = self.roof
        self.said = []
        self.char1.msg = lambda text=None, **kw: self.said.append(str(text))
        self.broadcasts = []

    def _record(self, location=None, template="", char_refs=None,
                exclude=None, **kwargs):
        self.broadcasts.append((location, template))

    def leap(self, *, rolled, settle=True):
        from commands.combat.jump import CmdJump
        cmd = CmdJump()
        cmd.caller = self.char1
        cmd.direction = "east"
        with mock.patch.object(gravity, "delay") as delayed, \
             mock.patch.object(gravity, "msg_room_identity"), \
             mock.patch("commands.combat.jump.msg_room_identity",
                        side_effect=self._record), \
             mock.patch("commands.combat.jump.standard_roll",
                        return_value=(rolled, rolled, rolled)), \
             mock.patch("commands.combat.jump.clear_aim_state"), \
             mock.patch("commands.explosion_utils.check_rigged_grenade"), \
             mock.patch("commands.explosion_utils.check_auto_defuse"), \
             mock.patch.object(type(cmd), "find_edge_exit",
                               return_value=self.gap):
            pending = _queue(delayed)
            cmd.handle_gap_jump()
            if settle:
                _drain(pending)
        return delayed

    def said_text(self):
        return " ".join(self.said)

    def hurt(self):
        return sum(o.max_hp - o.current_hp
                   for o in self.char1.medical_state.organs.values())


class TestAMadeLeapReachesTheFarPerch(_GapCase):
    def test_it_ends_on_the_far_roof(self):
        self.leap(rolled=999)
        self.assertIs(self.char1.location, self.far)

    def test_it_passes_through_the_air_cell_on_the_way(self):
        """The tick in the air is real -- that is what makes a leaper
        visible to anyone flying in the cell."""
        delayed = self.leap(rolled=999)
        self.assertEqual(delayed.call_count, 1)
        self.assertIs(delayed.call_args[0][1], gravity._continue_leap)

    def test_it_costs_nothing(self):
        self.leap(rolled=999)
        self.assertEqual(self.hurt(), 0)

    def test_no_fall_record_is_ever_written(self):
        self.leap(rolled=999)
        self.assertFalse(self.char1.db.falling)

    def test_the_token_is_spent(self):
        self.leap(rolled=999)
        self.assertFalse(gravity.has_airborne_token(self.char1))
        self.assertIsNone(getattr(self.char1.ndb, "leap", None))

    def test_the_roof_they_left_hears_them_go(self):
        self.leap(rolled=999)
        departures = [t for loc, t in self.broadcasts
                      if loc is self.roof and "leaps across the east gap" in t]
        self.assertTrue(departures, self.broadcasts)

    def test_the_far_roof_hears_them_arrive(self):
        self.leap(rolled=999)
        arrivals = [t for loc, t in self.broadcasts
                    if loc is self.far and "spectacular leap" in t]
        self.assertTrue(arrivals, self.broadcasts)

    def test_they_are_told_they_made_it(self):
        self.leap(rolled=999)
        self.assertIn("land safely", self.said_text())


class TestAMissedLeapFallsTheColumn(_GapCase):
    def test_it_ends_in_the_street(self):
        self.leap(rolled=1)
        self.assertIs(self.char1.location, self.street)

    def test_it_walks_every_cell(self):
        delayed = self.leap(rolled=1)
        self.assertEqual(delayed.call_count, 2)
        for call in delayed.call_args_list:
            self.assertIs(call[0][1], gravity._fall_step)

    def test_it_costs_two_storeys(self):
        from world.combat.constants import FALL_DAMAGE_PER_STORY
        self.leap(rolled=1)
        self.assertEqual(self.hurt(), FALL_DAMAGE_PER_STORY * 2)

    def test_a_missed_leap_does_not_roll_to_land(self):
        """They did not choose to descend, so there is nothing to land
        well from -- the record says ``roll: False``."""
        from commands.combat.jump import CmdJump
        cmd = CmdJump()
        cmd.caller = self.char1
        cmd.direction = "east"
        with mock.patch.object(gravity, "delay"), \
             mock.patch.object(gravity, "msg_room_identity"), \
             mock.patch("commands.combat.jump.msg_room_identity"), \
             mock.patch("commands.combat.jump.standard_roll",
                        return_value=(1, 1, 1)), \
             mock.patch("commands.combat.jump.clear_aim_state"), \
             mock.patch("commands.explosion_utils.check_auto_defuse"), \
             mock.patch.object(type(cmd), "find_edge_exit",
                               return_value=self.gap):
            cmd.handle_gap_jump()
        self.assertFalse(self.char1.db.falling["roll"])

    def test_no_token_was_ever_granted(self):
        self.leap(rolled=1)
        self.assertFalse(
            (getattr(self.char1.ndb, NDB_AIRBORNE_TOKEN, None) or 0) > 0)

    def test_the_roof_hears_them_fall_short(self):
        self.leap(rolled=1)
        short = [t for loc, t in self.broadcasts
                 if loc is self.roof and "falls short" in t]
        self.assertTrue(short, self.broadcasts)


class TestAGapWithNoPerchIsRefusedOnTheRoof(_GapCase):
    """#3559: a raw dbref that no longer resolves is a build error, not
    a licence to drop someone into the air cell."""

    def test_a_dead_dbref_refuses(self):
        self.gap.db.gap_destination = "999999999"
        self.leap(rolled=999)
        self.assertIn("doesn't lead anywhere safe", self.said_text())

    def test_and_leaves_them_standing_on_the_roof(self):
        self.gap.db.gap_destination = "999999999"
        self.leap(rolled=999)
        self.assertIs(self.char1.location, self.roof)

    def test_and_starts_no_fall(self):
        self.gap.db.gap_destination = "999999999"
        delayed = self.leap(rolled=999)
        self.assertEqual(delayed.call_count, 0)
        self.assertFalse(self.char1.db.falling)

    def test_a_perch_that_is_itself_air_is_refused_too(self):
        """The old silent substitution put you in exactly this room."""
        self.gap.db.gap_destination = self.air2
        self.leap(rolled=999)
        self.assertIs(self.char1.location, self.roof)
        self.assertIn("doesn't lead anywhere safe", self.said_text())

    def test_a_bare_gap_with_no_gap_destination_falls_back_to_the_exit(self):
        """Control: the refusal is scoped to an UNUSABLE perch. A gap
        whose exit already points at a solid room still works."""
        self.gap.db.gap_destination = None
        self.gap.destination = self.far
        self.leap(rolled=999)
        self.assertIs(self.char1.location, self.far)


class TestALeapOntoAirDoesNotLoopForever(_GapCase):
    """Gravity's own contract, below the verb: even if something hands
    ``_continue_leap`` a perch that is itself an air cell, the token has
    already been spent, so the arrival falls instead of re-leaping."""

    def _enter_the_air_mid_leap(self, perch):
        self.char1.ndb.airborne_token = 1
        self.char1.ndb.leap = {"destination": perch, "finish": None}
        with mock.patch.object(gravity, "delay") as delayed, \
             mock.patch.object(gravity, "msg_room_identity"):
            pending = _queue(delayed)
            self.char1.move_to(self.air1, quiet=True)
            _drain(pending)
        return delayed

    def test_the_chain_terminates_in_the_street(self):
        delayed = self._enter_the_air_mid_leap(self.air2)
        self.assertIs(self.char1.location, self.street)
        self.assertLessEqual(delayed.call_count, 4)
        self.assertFalse(self.char1.db.falling)

    def test_a_leap_with_no_perch_at_all_just_falls(self):
        delayed = self._enter_the_air_mid_leap(None)
        self.assertIs(self.char1.location, self.street)
        self.assertLessEqual(delayed.call_count, 4)


class TestTheHookMayLandThemBeforeTheVerbFinishes(_GapCase):
    """The post-move guard is ``if not moved:`` and nothing more.

    A guard that also asked "are they still in the air cell?" reads a
    completed, hook-driven onward move as a refused one, and bails out
    before the departure broadcast and the combat/aim cleanup. Under
    real timing the tick is a second away so it never fires -- which is
    exactly the kind of bug that ships. Here the ticks run INLINE, so
    the hook has already put the leaper on the far perch by the time
    ``move_to`` returns, and the verb must still finish its work.
    """

    def leap_inline(self, *, rolled):
        from commands.combat.jump import CmdJump
        cmd = CmdJump()
        cmd.caller = self.char1
        cmd.direction = "east"
        with mock.patch.object(gravity, "delay") as delayed, \
             mock.patch.object(gravity, "msg_room_identity"), \
             mock.patch("commands.combat.jump.msg_room_identity",
                        side_effect=self._record), \
             mock.patch("commands.combat.jump.standard_roll",
                        return_value=(rolled, rolled, rolled)), \
             mock.patch("commands.combat.jump.clear_aim_state") as aim, \
             mock.patch("commands.explosion_utils.check_rigged_grenade"), \
             mock.patch("commands.explosion_utils.check_auto_defuse"), \
             mock.patch.object(type(cmd), "find_edge_exit",
                               return_value=self.gap):
            delayed.side_effect = (
                lambda _s, callback, *a, **kw: callback(*a, **kw))
            cmd.handle_gap_jump()
        return aim

    def test_the_roof_still_hears_a_made_leap_depart(self):
        self.leap_inline(rolled=999)
        self.assertTrue([t for loc, t in self.broadcasts
                         if loc is self.roof and "leaps across" in t],
                        self.broadcasts)

    def test_the_roof_still_hears_a_missed_leap_fall_short(self):
        self.leap_inline(rolled=1)
        self.assertTrue([t for loc, t in self.broadcasts
                         if loc is self.roof and "falls short" in t],
                        self.broadcasts)

    def test_the_aim_state_is_still_cleared(self):
        """The other half of the work that sat below the guard."""
        aim = self.leap_inline(rolled=1)
        aim.assert_called()

    def test_the_body_still_ends_up_where_it_belongs(self):
        self.leap_inline(rolled=999)
        self.assertIs(self.char1.location, self.far)
