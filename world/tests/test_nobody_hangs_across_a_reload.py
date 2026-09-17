"""A fall survives the reload that kills its timer (#3579, #505 shape).

The live chain is a ``delay`` -- an ephemeral twisted call that dies with
the process. The record, ``db.falling``, is persistent. Without a boot
sweep the two halves part company and a body hangs in an air cell for
ever, holding a record nothing will ever step; that is exactly the wedge
#505 fixed for grenade fuses and #2450 for the death curtain.

What is pinned here:

* **The sweep is actually wired into ``at_server_start``.** A sweep
  nobody calls is the same as no sweep.
* **A live step re-arms at its TRUE remaining time**, read from the
  persisted ``next_step_at`` epoch, so a body one tick from the ground
  does not get a fresh full second.
* **An OVERDUE step waits a beat** (2.0s) instead of firing during boot,
  when the world is still loading.
* **One bad row never stops the sweep.** It walks every falling object
  in the database; a single broken one must not strand all the others.
* **A record whose body is no longer in air is CLEARED**, not resumed --
  someone was @tel'd out, or the cell was rebuilt under them.
* **A logged-out faller is skipped, not cleared.** They have no
  location; the reconnect path resumes them from the record, which is
  why the record must still be there.

``ObjectDB`` is imported inside ``sweep_airborne``, so the mock goes on
``evennia.objects.models.ObjectDB`` -- the pattern from
test_grenade_fuse_persistence.py.
"""

from __future__ import annotations

import inspect
import time
from types import SimpleNamespace
from unittest import TestCase, mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

import world.gravity as gravity


class _DB(SimpleNamespace):
    """A ``db`` handler: answers None for anything unset."""

    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        return None


def _room(sky=True):
    return SimpleNamespace(db=_DB(is_sky_room=True if sky else None),
                           key="In the Air", contents=[])


def _faller(record, location):
    obj = mock.MagicMock()
    obj.key = "Faller"
    obj.db = _DB(falling=record)
    obj.ndb = SimpleNamespace()
    obj.location = location
    return obj


class _Cursed:
    """A row that explodes the moment the sweep touches it."""

    key = "cursed"

    @property
    def db(self):
        raise RuntimeError("this row is broken")


class TestTheSweepIsWiredIntoBoot(TestCase):
    def test_at_server_start_calls_it(self):
        from server.conf import at_server_startstop

        source = inspect.getsource(at_server_startstop)
        start = source.index("def at_server_start(")
        stop = source.index("def at_server_stop(")
        self.assertIn("sweep_airborne", source[start:stop],
                      "world.gravity.sweep_airborne is never called at boot")

    def test_it_is_not_merely_mentioned_in_the_stop_hook(self):
        """Control: a name that only appears AFTER at_server_stop would
        pass a whole-module search and resume nothing."""
        from server.conf import at_server_startstop

        source = inspect.getsource(at_server_startstop)
        stop = source.index("def at_server_stop(")
        self.assertNotIn("sweep_airborne", source[stop:])


class TestResumingTheFallsTheReloadDropped(TestCase):
    """The warm half, with the database mocked out."""

    def sweep(self, rows, rooms=()):
        def _filter(**kwargs):
            if "db_attributes__db_key" in kwargs:
                return SimpleNamespace(distinct=lambda: list(rows))
            return list(rooms)

        with mock.patch("evennia.objects.models.ObjectDB") as db, \
                mock.patch.object(gravity, "delay") as delayed:
            db.objects.filter.side_effect = _filter
            result = gravity.sweep_airborne()
        return result, delayed

    def _record(self, due_in):
        return {"cells": 2, "roll": True, "edge_difficulty": 8,
                "next_step_at": time.time() + due_in}

    def test_a_future_step_rearms_at_its_true_remaining_time(self):
        row = _faller(self._record(8), _room())
        (resumed, started), delayed = self.sweep([row])
        self.assertEqual((resumed, started), (1, 0))
        seconds = delayed.call_args[0][0]
        self.assertGreater(seconds, 6.5)
        self.assertLessEqual(seconds, 8.0)

    def test_and_schedules_the_fall_step_for_that_object(self):
        row = _faller(self._record(8), _room())
        _result, delayed = self.sweep([row])
        self.assertIs(delayed.call_args[0][1], gravity._fall_step)
        self.assertIs(delayed.call_args[0][2], row)

    def test_and_marks_the_chain_live_again(self):
        row = _faller(self._record(8), _room())
        self.sweep([row])
        self.assertTrue(getattr(row.ndb, "fall_active", False))

    def test_an_overdue_step_waits_a_beat(self):
        row = _faller(self._record(-30), _room())
        (resumed, _started), delayed = self.sweep([row])
        self.assertEqual(resumed, 1)
        self.assertEqual(delayed.call_args[0][0], 2.0)

    def test_a_step_due_right_now_also_waits_a_beat(self):
        row = _faller(self._record(0), _room())
        _result, delayed = self.sweep([row])
        self.assertEqual(delayed.call_args[0][0], 2.0)

    def test_a_record_with_no_epoch_at_all_waits_a_beat(self):
        row = _faller({"cells": 1}, _room())
        (resumed, _started), delayed = self.sweep([row])
        self.assertEqual(resumed, 1)
        self.assertEqual(delayed.call_args[0][0], 2.0)

    def test_a_body_no_longer_in_air_is_cleared(self):
        row = _faller(self._record(4), _room(sky=False))
        (resumed, _started), delayed = self.sweep([row])
        self.assertEqual(resumed, 0)
        row.attributes.remove.assert_called_once_with("falling")
        delayed.assert_not_called()

    def test_a_logged_out_faller_is_skipped_not_cleared(self):
        """No location: the reconnect hook resumes them from the record,
        so clearing it here would lose the fall entirely."""
        row = _faller(self._record(4), None)
        (resumed, _started), delayed = self.sweep([row])
        self.assertEqual(resumed, 0)
        row.attributes.remove.assert_not_called()
        delayed.assert_not_called()

    def test_a_dragged_companion_is_left_to_its_leader(self):
        """A LIVE marker: the leader is still falling and their step is
        what moves this body."""
        leader = _faller(self._record(4), _room())
        row = _faller({"led_by": leader}, _room())
        (resumed, _started), delayed = self.sweep([leader, row])
        self.assertEqual(resumed, 1)               # the leader only
        delayed.assert_called_once()
        row.attributes.remove.assert_not_called()

    def test_a_stale_companion_marker_is_collected(self):
        """The marker is what makes the cell's hook IGNORE this body, so
        one left behind by a leader who is no longer falling is a
        permanent no-fall flag -- they would hang in air for ever and no
        later sweep would start them either, because ``is_falling`` reads
        True off the marker."""
        leader = _faller(None, _room())            # leader not falling
        row = _faller({"led_by": leader}, _room())
        (resumed, _started), delayed = self.sweep([row])
        self.assertEqual(resumed, 0)
        row.attributes.remove.assert_called_once_with("falling")
        delayed.assert_not_called()

    def test_a_marker_whose_leader_is_gone_is_collected(self):
        """The leader was deleted outright: no pk, no fall, no rescue."""
        dead = mock.MagicMock()
        dead.pk = None
        row = _faller({"led_by": dead}, _room())
        self.sweep([row])
        row.attributes.remove.assert_called_once_with("falling")

    def test_a_marker_with_no_leader_at_all_is_collected(self):
        row = _faller({"led_by": None}, _room())
        self.sweep([row])
        row.attributes.remove.assert_called_once_with("falling")

    def test_an_empty_record_is_ignored(self):
        row = _faller({}, _room())
        (resumed, _started), delayed = self.sweep([row])
        self.assertEqual(resumed, 0)
        delayed.assert_not_called()

    def test_one_bad_row_never_stops_the_sweep(self):
        good = _faller(self._record(5), _room())
        (resumed, _started), delayed = self.sweep([_Cursed(), good, _Cursed()])
        self.assertEqual(resumed, 1)
        delayed.assert_called_once()

    def test_several_falls_all_resume(self):
        rows = [_faller(self._record(3), _room()) for _ in range(4)]
        (resumed, _started), delayed = self.sweep(rows)
        self.assertEqual(resumed, 4)
        self.assertEqual(delayed.call_count, 4)

    def test_nothing_falling_is_a_quiet_no_op(self):
        (resumed, started), delayed = self.sweep([])
        self.assertEqual((resumed, started), (0, 0))
        delayed.assert_not_called()


class TestStartingTheFallsNobodyRecorded(EvenniaTest):
    """The cold half: anything found hanging in an air cell with no
    record at all -- built there, @tel'd there, or left by a version of
    the game that had no gravity layer. Real typeclasses and a real
    wired column, because ``is_stranded_aloft`` is an isinstance gate
    AND now requires somewhere to fall to.

    The warm-half class above passes ``rooms=()``, so every ``started``
    it asserts is vacuously zero. These are the cases that actually
    exercise the second loop.
    """

    def setUp(self):
        super().setUp()
        self.street = self.room2
        self.air = create_object("typeclasses.rooms.SkyRoom",
                                 key="In the Air")
        create_object("typeclasses.exits.Exit", key="down",
                      location=self.air, destination=self.street,
                      aliases=["d"])
        self.bare = create_object("typeclasses.rooms.SkyRoom",
                                  key="In the Air")

    def sweep(self, rooms=None):
        rooms = [self.air, self.bare, self.room1] if rooms is None else rooms

        def _filter(**kwargs):
            if "db_attributes__db_key" in kwargs:
                return SimpleNamespace(distinct=list)
            return list(rooms)

        with mock.patch("evennia.objects.models.ObjectDB") as db, \
                mock.patch.object(gravity, "delay") as delayed, \
                mock.patch.object(gravity, "msg_room_identity"):
            db.objects.filter.side_effect = _filter
            result = gravity.sweep_airborne()
        return result, delayed

    def test_a_body_hanging_in_a_wired_cell_is_started(self):
        self.char1.location = self.air
        (_resumed, started), delayed = self.sweep()
        self.assertEqual(started, 1)
        self.assertTrue(self.char1.db.falling)
        self.assertEqual(delayed.call_count, 1)
        self.assertIs(delayed.call_args[0][1], gravity._fall_step)

    def test_the_started_record_starts_from_scratch(self):
        self.char1.location = self.air
        self.sweep()
        record = self.char1.db.falling
        self.assertEqual(record["cells"], 0)
        self.assertFalse(record["roll"])
        self.assertIs(record["origin"], self.air)

    def test_a_body_parked_in_a_BARE_cell_is_not_started(self):
        """The impasse already stopped them there (#3581). Starting them
        again would re-strand and re-message on every single boot."""
        self.char1.location = self.bare
        (_resumed, started), delayed = self.sweep()
        self.assertEqual(started, 0)
        self.assertFalse(self.char1.db.falling)
        self.assertEqual(delayed.call_count, 0)

    def test_a_thing_hanging_in_a_wired_cell_is_started(self):
        item = create_object("typeclasses.items.Item", key="a shiv",
                             location=self.room1)
        item.location = self.air
        (_resumed, started), _delayed = self.sweep()
        self.assertEqual(started, 1)
        self.assertTrue(item.db.falling)

    def test_two_bodies_in_one_cell_are_both_started(self):
        self.char1.location = self.air
        self.char2.location = self.air
        (_resumed, started), _delayed = self.sweep()
        self.assertEqual(started, 2)

    def test_the_columns_own_exits_are_left_alone(self):
        (_resumed, started), _delayed = self.sweep()
        self.assertEqual(started, 0)

    def test_a_body_that_stays_aloft_is_left_where_it_is(self):
        self.char1.location = self.air
        self.char1.db.stays_aloft = True
        (_resumed, started), _delayed = self.sweep()
        self.assertEqual(started, 0)
        self.assertFalse(self.char1.db.falling)

    def test_a_body_already_carrying_a_record_is_not_started_twice(self):
        self.char1.location = self.air
        self.char1.db.falling = {"cells": 1, "origin": self.air}
        (_resumed, started), _delayed = self.sweep()
        self.assertEqual(started, 0)
        self.assertEqual(self.char1.db.falling["cells"], 1)

    def test_a_body_on_the_ground_is_not_touched(self):
        self.char1.location = self.room1
        (_resumed, started), _delayed = self.sweep()
        self.assertEqual(started, 0)
        self.assertFalse(self.char1.db.falling)

    def test_a_broken_room_never_stops_the_cold_half(self):
        """One room whose contents explode must not cost every other
        cell its sweep."""
        cursed = mock.MagicMock()
        type(cursed).contents = mock.PropertyMock(
            side_effect=RuntimeError("bad room"))
        cursed.db = _DB(is_sky_room=True)
        self.char1.location = self.air
        (_resumed, started), _delayed = self.sweep(
            rooms=[cursed, self.air])
        self.assertEqual(started, 1)
