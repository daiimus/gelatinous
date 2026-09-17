"""A travelling NPC in mid-air waits; it does not re-route (B2, #3579).

``_travel_step`` walks a route that was computed ONCE (A* is ~18ms a
path; per-step re-pathing saturates the reactor at commute scale --
SOULS_SCALE_HARDENING_SPEC Law 8). It re-pathfinds only when reality
disagrees with the cached route, which is exactly what being airborne
looks like from the router's point of view: the NPC is in a room the
route never mentions.

So a tick that fires mid-fall, with the airborne check BELOW the route
reconciliation, does three bad things in a row:

1. re-pathfinds *from an air cell* -- which has one exit, ``down``, and
   no route to anywhere the walker wanted, so the travel FAULTS and the
   run is abandoned while the body is still in the air;
2. or, worse, finds a route and caches it, so the walk resumes from a
   plan drawn for a room the NPC is about to leave; and
3. pops the real route's head on the way past, so even a walker that
   survives the fall resumes one exit further along than it actually
   walked.

The fix is ordering: the guard sits ABOVE the reconciliation. Falling is
not a routing problem. The tick re-arms itself and nothing else happens
until the body is back on a floor.

Three states count as airborne, because a walker can be in any of them
before ``db.falling`` exists: a live fall record, an unspent leap token
(the tick between the roof and the far perch), and simply standing in a
room flagged ``is_sky_room``.

Driven the way the other travel tests drive it (test_doors.py:346-378):
a stub NPC carrying a real ``director_travel`` state, straight into
``_travel_step``.
"""

from __future__ import annotations

from types import SimpleNamespace as NS
from unittest import TestCase, mock

from world.director import travel as tmod


def _room(key="Somewhere", sky=None):
    return NS(db=NS(is_sky_room=sky), key=key)


def _npc(*, falling=None, token=None, sky=False, route=None):
    """A walker mid-journey. ``db``/``ndb`` are real namespaces rather
    than MagicMock attributes on purpose: a MagicMock answers every
    attribute with a truthy child, so ``npc.db.falling`` would read as a
    live fall on EVERY case and the control could not fail."""
    npc = mock.MagicMock()
    npc.db = NS(falling=falling)
    ndb = NS(director_travel={
        "destination": _room("Destination"),
        "steps": 0,
        "step_delay": 2.0,
        "on_arrive": None,
        "on_fail": None,
        "route": list(route) if route is not None else [],
    })
    if token is not None:
        ndb.airborne_token = token
    npc.ndb = ndb
    npc.location = _room("In the Air" if sky else "A Street",
                         sky=True if sky else None)
    return npc


def _stale_route():
    """A cached route whose head starts in a room the NPC is NOT in --
    the shape that makes the reconciliation re-pathfind. If the guard
    ever slips below it, this is what fires."""
    head = mock.MagicMock()
    head.key = "north"
    head.location = _room("Some Other Room")
    return [head]


class _StepCase(TestCase):
    def step(self, npc, route_result=None):
        with mock.patch.object(tmod, "find_path_exits",
                               return_value=route_result or []) as finder, \
             mock.patch.object(tmod, "delay") as delayed:
            tmod._travel_step(npc)
        return finder, delayed

    def state(self, npc):
        return npc.ndb.director_travel


class TestAFallingWalkerIsNotARoutingProblem(_StepCase):
    def test_the_tick_re_arms_itself(self):
        npc = _npc(falling={"cells": 2}, route=_stale_route())
        _finder, delayed = self.step(npc)
        delayed.assert_called_once_with(2.0, tmod._travel_step, npc)

    def test_it_does_not_re_pathfind(self):
        npc = _npc(falling={"cells": 2}, route=_stale_route())
        finder, _delayed = self.step(npc)
        finder.assert_not_called()

    def test_the_cached_route_is_untouched(self):
        route = _stale_route()
        npc = _npc(falling={"cells": 2}, route=route)
        before = list(self.state(npc)["route"])
        self.step(npc)
        self.assertEqual(self.state(npc)["route"], before)
        self.assertEqual(len(self.state(npc)["route"]), 1)

    def test_it_does_not_walk_anywhere(self):
        npc = _npc(falling={"cells": 2}, route=_stale_route())
        self.step(npc)
        npc.execute_cmd.assert_not_called()

    def test_the_travel_is_not_finished_or_faulted(self):
        npc = _npc(falling={"cells": 2}, route=_stale_route())
        self.step(npc)
        self.assertTrue(self.state(npc), "the travel state was torn down")

    def test_a_leaper_mid_token_waits_too(self):
        """The tick between the roof and the far perch: no fall record
        yet, and there may never be one."""
        npc = _npc(token=1, route=_stale_route())
        finder, delayed = self.step(npc)
        finder.assert_not_called()
        delayed.assert_called_once_with(2.0, tmod._travel_step, npc)

    def test_a_spent_token_is_not_airborne(self):
        """``airborne_token`` is zeroed, not deleted, when it is spent --
        a truthiness read would keep the walker parked for ever."""
        npc = _npc(token=0)
        finder, _delayed = self.step(npc)
        finder.assert_called_once()

    def test_standing_in_an_air_cell_is_airborne(self):
        """Arrived in the cell, record not yet written, or parked there
        by the impasse: either way, not a route to recompute."""
        npc = _npc(sky=True, route=_stale_route())
        finder, delayed = self.step(npc)
        finder.assert_not_called()
        delayed.assert_called_once_with(2.0, tmod._travel_step, npc)

    def test_a_truthy_sky_flag_is_not_the_flag(self):
        """``is True``, so an attribute that merely answered yes cannot
        park a walker."""
        npc = _npc()
        npc.location = NS(db=NS(is_sky_room=1), key="Not Really Air")
        finder, _delayed = self.step(npc)
        finder.assert_called_once()

    def test_the_step_counter_still_advances(self):
        """The anti-runaway cap has to keep counting, or a walker stuck
        above a bottomless column ticks for ever."""
        npc = _npc(falling={"cells": 1})
        self.step(npc)
        self.assertEqual(self.state(npc)["steps"], 1)


class TestTheGuardSitsAboveTheReconciliation(_StepCase):
    """The ordering pin. A stale route is what triggers re-pathfinding,
    so these two cases differ ONLY in whether the walker is airborne --
    if the guard slipped below the reconciliation, the first would
    re-pathfind exactly like the second."""

    def test_on_the_ground_a_stale_route_IS_re_pathfound(self):
        walk = mock.MagicMock()
        walk.key = "north"
        walk.location = None
        npc = _npc(route=_stale_route())
        finder, _delayed = self.step(npc, route_result=[walk])
        finder.assert_called_once()

    def test_in_the_air_the_same_stale_route_is_left_alone(self):
        npc = _npc(falling={"cells": 1}, route=_stale_route())
        finder, _delayed = self.step(npc)
        finder.assert_not_called()

    def test_a_grounded_walker_with_no_route_faults_as_before(self):
        """Control that the reconciliation still works at all: no route
        and none findable is a fault, not a wait."""
        npc = _npc(route=_stale_route())
        with mock.patch.object(tmod, "find_path_exits", return_value=[]), \
             mock.patch.object(tmod, "delay") as delayed:
            tmod._travel_step(npc)
        self.assertIsNone(npc.ndb.director_travel)
        delayed.assert_not_called()

    def test_an_airborne_walker_with_no_route_does_NOT_fault(self):
        """The reported blocker, stated as the outcome a player sees:
        the courier jumps a gap and her run is abandoned in mid-air."""
        npc = _npc(falling={"cells": 1}, route=[])
        with mock.patch.object(tmod, "find_path_exits", return_value=[]), \
             mock.patch.object(tmod, "delay") as delayed:
            tmod._travel_step(npc)
        self.assertTrue(npc.ndb.director_travel,
                        "the fall faulted the travel")
        delayed.assert_called_once_with(2.0, tmod._travel_step, npc)


class TestAGroundedWalkerIsUnaffected(_StepCase):
    """None of this may cost an ordinary walk a step."""

    def test_it_walks_its_route(self):
        walk = mock.MagicMock(spec=["key", "location"])
        walk.key = "north"
        npc = _npc()
        walk.location = npc.location
        self.state(npc)["route"] = [walk]
        with mock.patch.object(tmod, "find_path_exits") as finder, \
             mock.patch.object(tmod, "delay"):
            tmod._travel_step(npc)
        finder.assert_not_called()            # the cached route was good
        self.assertEqual([c.args[0] for c in npc.execute_cmd.call_args_list],
                         ["north"])

    def test_arrival_still_finishes_the_travel(self):
        npc = _npc()
        self.state(npc)["destination"] = npc.location
        with mock.patch.object(tmod, "delay"):
            tmod._travel_step(npc)
        self.assertIsNone(npc.ndb.director_travel)
