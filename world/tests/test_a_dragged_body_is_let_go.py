"""A dragged body's marker record is released whenever the ride ends (B1).

Dragging someone off a roof puts a MARKER record on them --
``db.falling = {"led_by": <leader>}`` -- and that marker is what makes
the air cell's arrival hook ignore them: they are moved by the leader's
step, so their own arrival must not start a second chain of its own.

The marker is therefore a **no-fall flag**, and it is persistent. Every
way out of the ride has to remove it:

* they land together;
* they are separated mid-column (the victim is pulled out, teleported,
  or their own move is refused);
* the leader leaves the column, by any door;
* the fall is stranded by the impasse or by one of the guards;
* the process died and the boot sweep finds the marker with no live
  leader behind it.

Miss ANY of those and the body is left carrying a record that says "I am
falling" while nothing is stepping it. ``is_falling`` reads True off it,
so ``start_fall`` refuses, the arrival hook returns early, and
``is_stranded_aloft`` is False -- the boot sweep will not rescue them
either. That body can never fall again for the rest of the game: they
walk off a roof and stand in mid-air.

The victim is now moved with hooks ON (posture, follower links and
presence rosters all update the way they did before the gravity layer),
which is precisely why the marker has to be right: the hook sees them
arrive in every cell.
"""

from __future__ import annotations

from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

import world.gravity as gravity


def _queue(mocked):
    pending = []
    mocked.side_effect = (
        lambda _seconds, callback, *a, **kw: pending.append((callback, a, kw)))
    return pending


def _drain(pending, limit=40):
    fired = 0
    while pending and fired < limit:
        callback, args, kwargs = pending.pop(0)
        callback(*args, **kwargs)
        fired += 1
    return fired


def _step_once(pending):
    """Fire exactly one queued tick, leaving anything it schedules."""
    if not pending:
        return False
    callback, args, kwargs = pending.pop(0)
    callback(*args, **kwargs)
    return True


class _DragCase(EvenniaTest):
    """roof -> air1 -> air2 -> air3 -> street; leader drags char2."""

    CELLS = 3

    def setUp(self):
        super().setUp()
        self.roof, self.street = self.room1, self.room2
        self.street.key = "Test Street"
        self.elsewhere = create_object("typeclasses.rooms.Room",
                                       key="Somewhere Else")
        self.cells = [
            create_object("typeclasses.rooms.SkyRoom", key="In the Air")
            for _ in range(self.CELLS)
        ]
        for index, cell in enumerate(self.cells):
            below = (self.cells[index + 1] if index + 1 < len(self.cells)
                     else self.street)
            create_object("typeclasses.exits.Exit", key="down",
                          location=cell, destination=below, aliases=["d"])
        self.leader, self.victim = self.char1, self.char2
        for body in (self.leader, self.victim):
            body.msg = lambda text=None, **kw: None

    def begin_drag(self):
        """The shape the verb produces: the victim is already in the
        cell wearing the marker, and the leader's fall names them."""
        self.leader.location = self.cells[0]
        self.victim.location = self.cells[0]
        self.victim.db.falling = {"led_by": self.leader}
        patches = mock.patch.object(gravity, "msg_room_identity")
        self.addCleanup(patches.stop)
        patches.start()
        delayed = mock.patch.object(gravity, "delay")
        self.addCleanup(delayed.stop)
        self.delayed = delayed.start()
        self.pending = _queue(self.delayed)
        started = gravity.start_fall(self.leader, companion=self.victim)
        self.assertTrue(started, "premise: the fall began")
        return self.pending


class TestTheyLandTogether(_DragCase):
    def test_both_reach_the_street(self):
        _drain(self.begin_drag())
        self.assertIs(self.leader.location, self.street)
        self.assertIs(self.victim.location, self.street)

    def test_the_leaders_record_is_gone(self):
        _drain(self.begin_drag())
        self.assertFalse(self.leader.db.falling)

    def test_the_victims_marker_is_gone(self):
        _drain(self.begin_drag())
        self.assertFalse(self.victim.db.falling)

    def test_the_victim_can_fall_again_afterwards(self):
        """The whole point of releasing the marker."""
        _drain(self.begin_drag())
        self.victim.location = self.cells[0]
        with mock.patch.object(gravity, "delay"), \
             mock.patch.object(gravity, "msg_room_identity"):
            self.assertTrue(gravity.start_fall(self.victim))

    def test_one_chain_ran_not_two(self):
        pending = self.begin_drag()
        _drain(pending)
        self.assertEqual(self.delayed.call_count, self.CELLS)


class TestTheVictimIsPulledOutMidFall(_DragCase):
    """Separated on the way down -- someone grabs them off the leader, a
    staffer @tels them, the column forks. The leader keeps falling; the
    victim must be let go."""

    def _separate_after_one_step(self):
        pending = self.begin_drag()
        _step_once(pending)                       # cells[0] -> cells[1]
        self.assertIs(self.victim.location, self.cells[1],
                      "premise: they rode the first step together")
        self.victim.location = self.elsewhere
        _step_once(pending)                       # the step that notices
        return pending

    def test_the_marker_is_released(self):
        self._separate_after_one_step()
        self.assertFalse(self.victim.db.falling)

    def test_the_leaders_record_stops_naming_them(self):
        self._separate_after_one_step()
        record = self.leader.db.falling
        self.assertTrue(record, "premise: the leader is still falling")
        self.assertIsNone(record["companion"])

    def test_the_victim_stays_where_they_were_taken(self):
        self._separate_after_one_step()
        self.assertIs(self.victim.location, self.elsewhere)

    def test_the_leader_still_reaches_the_ground(self):
        pending = self._separate_after_one_step()
        _drain(pending)
        self.assertIs(self.leader.location, self.street)

    def test_the_released_victim_can_start_a_new_fall(self):
        """(d): the marker was the only thing stopping them, so with it
        gone a wired cell takes them down."""
        pending = self._separate_after_one_step()
        _drain(pending)
        self.victim.location = self.cells[0]
        with mock.patch.object(gravity, "delay"), \
             mock.patch.object(gravity, "msg_room_identity"):
            self.assertTrue(gravity.start_fall(self.victim))
        self.assertTrue(self.victim.db.falling)
        self.assertNotIn("led_by", self.victim.db.falling)

    def test_a_victim_whose_own_move_is_refused_is_released(self):
        """The other separation: they are still in the cell but the
        world will not let them leave it.

        The refusal is scoped to the VICTIM's instance. Patching
        ``Character.move_to`` wholesale refuses the leader's move too --
        the fall then strands for an unrelated reason and the test
        passes without ever exercising this branch."""
        pending = self.begin_drag()
        real_move = type(self.victim).move_to
        victim = self.victim

        def only_the_victim_is_refused(self_obj, *args, **kwargs):
            if self_obj is victim:
                return False
            return real_move(self_obj, *args, **kwargs)

        with mock.patch.object(type(self.victim), "move_to",
                               new=only_the_victim_is_refused):
            _step_once(pending)
        self.assertIs(self.leader.location, self.cells[1],
                      "premise: only the victim was refused")
        self.assertFalse(self.victim.db.falling)
        self.assertIs(self.victim.location, self.cells[0])
        self.assertIsNone(self.leader.db.falling["companion"])


class TestTheLeaderLeavesTheColumn(_DragCase):
    """(c) The leader is @tel'd out mid-fall. Their next step finds them
    somewhere that is not air and drops the record -- the victim's
    marker has to go with it, or the victim is flagged falling by a
    leader who is not."""

    def _teleport_the_leader_away(self):
        pending = self.begin_drag()
        _step_once(pending)
        self.leader.location = self.elsewhere
        _drain(pending)
        return pending

    def test_the_leaders_record_is_dropped(self):
        self._teleport_the_leader_away()
        self.assertFalse(self.leader.db.falling)

    def test_the_victims_marker_is_dropped_too(self):
        self._teleport_the_leader_away()
        self.assertFalse(self.victim.db.falling)

    def test_the_abandoned_victim_can_fall_again(self):
        self._teleport_the_leader_away()
        self.victim.location = self.cells[0]
        with mock.patch.object(gravity, "delay"), \
             mock.patch.object(gravity, "msg_room_identity"):
            self.assertTrue(gravity.start_fall(self.victim))


class TestAStrandLetsThemGoToo(_DragCase):
    """The impasse and the guards end the ride as surely as a landing."""

    CELLS = 2

    def test_the_impasse_releases_the_companion(self):
        for ex in list(self.cells[0].exits):
            ex.delete()
        pending = self.begin_drag()
        _drain(pending)
        self.assertFalse(self.leader.db.falling)
        self.assertFalse(self.victim.db.falling)

    def test_a_refused_step_releases_the_companion(self):
        pending = self.begin_drag()
        with mock.patch.object(type(self.leader), "move_to",
                               return_value=False):
            _step_once(pending)
        self.assertFalse(self.leader.db.falling)
        self.assertFalse(self.victim.db.falling)

    def test_and_the_victim_can_fall_again_after_a_strand(self):
        for ex in list(self.cells[0].exits):
            ex.delete()
        _drain(self.begin_drag())
        self.victim.location = self.cells[1]
        with mock.patch.object(gravity, "delay"), \
             mock.patch.object(gravity, "msg_room_identity"):
            self.assertTrue(gravity.start_fall(self.victim))


class TestTheMarkerStillDoesItsJobWhileTheRideRuns(_DragCase):
    """The control on all of the above: a marker that were released too
    EAGERLY would be just as broken -- the victim's own arrival would
    start a second, competing chain."""

    def test_the_victim_is_flagged_for_the_whole_descent(self):
        pending = self.begin_drag()
        _step_once(pending)
        self.assertEqual(self.victim.db.falling, {"led_by": self.leader})

    def test_the_victims_arrival_never_schedules_a_chain(self):
        pending = self.begin_drag()
        _drain(pending)
        # start_fall(1) + one tick per remaining cell -- and not one more
        self.assertEqual(self.delayed.call_count, self.CELLS)

    def test_the_victim_really_is_carried_by_hooked_moves(self):
        """Hooks ON is deliberate: posture, follower links and presence
        rosters all update. The marker, not a hookless move, is what
        keeps gravity's hands off them."""
        pending = self.begin_drag()
        _step_once(pending)
        self.assertIs(self.victim.location, self.cells[1])
