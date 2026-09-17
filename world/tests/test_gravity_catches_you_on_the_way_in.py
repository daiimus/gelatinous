"""Arriving in air is what starts a fall -- by any door (#3579).

``Room.at_object_receive`` calls ``world.gravity.on_enter_air`` for every
arrival, so a jump, a throw, a drop, a shove, a teleport and a reconnect
all reach the same decision. The defects pinned here:

* **The FLAG is the truth, not the typeclass.** The colony's highest
  crossings are plain ``Room``s flagged ``is_sky_room`` in place, and one
  ``SkyRoom`` was flipped into a walkable catwalk by clearing the flag. A
  gate written on ``isinstance(room, SkyRoom)`` gets both backwards.
* **A running chain must not start a second fall.** ``_fall_step`` moves
  the body with hooks ON -- that is deliberate, it is how the next cell
  continues the fall -- so the arrival hook sees a body that is already
  falling on every single step. ``ndb.fall_active`` is what tells it
  apart from a body whose chain died with the process.
* **Exits are created INSIDE air cells.** ``@airfill`` builds the column
  by creating a ``down`` exit in each cell, and Evennia fires the receive
  hook from ``at_first_save``. A gravity layer that tried to make an
  exit fall would break every column build.
* **A raise here undoes a completed move.** ``objects.py:1318-1325``:
  an exception out of ``at_object_receive`` makes ``move_to`` return
  ``False`` even though the object HAS moved -- so every caller that
  checks the return value narrates a refusal that did not happen.

``delay`` never fires under ``evennia test`` (there is no reactor), so it
is patched with a plain Mock and the assertion is on what was SCHEDULED.
"""

from __future__ import annotations

from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

import world.gravity as gravity


class _AirCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.sky = create_object("typeclasses.rooms.SkyRoom",
                                 key="In the Air")
        self.plain_air = create_object("typeclasses.rooms.Room",
                                       key="Above the Boot")
        self.plain_air.db.is_sky_room = True
        self.walkable_sky = create_object("typeclasses.rooms.SkyRoom",
                                          key="A Catwalk")
        self.walkable_sky.db.is_sky_room = False
        self.char1.location = self.room1

    def arrive(self, room, mover=None):
        """Move with hooks ON (assigning ``.location`` fires nothing) and
        report ``(move_to returned, delay call count)``."""
        mover = mover or self.char1
        with mock.patch.object(gravity, "delay") as delayed:
            moved = mover.move_to(room, quiet=True)
        self.delayed = delayed
        return moved, delayed.call_count


class TestArrivingInAirStartsOneFall(_AirCase):
    def test_a_skyroom_schedules_exactly_one_step(self):
        moved, scheduled = self.arrive(self.sky)
        self.assertTrue(moved)
        self.assertIs(self.char1.location, self.sky)
        self.assertEqual(scheduled, 1)

    def test_and_writes_the_record(self):
        self.arrive(self.sky)
        record = self.char1.db.falling
        self.assertTrue(record)
        self.assertEqual(record["cells"], 0)
        self.assertIs(record["origin"], self.sky)

    def test_the_step_it_scheduled_is_the_fall_step(self):
        self.arrive(self.sky)
        args = self.delayed.call_args[0]
        self.assertIs(args[1], gravity._fall_step)
        self.assertIs(args[2], self.char1)

    def test_a_plain_room_flagged_in_place_schedules_one_too(self):
        """The flag, never the typeclass."""
        _moved, scheduled = self.arrive(self.plain_air)
        self.assertEqual(scheduled, 1)
        self.assertTrue(self.char1.db.falling)

    def test_an_item_falls_as_readily_as_a_body(self):
        item = create_object("typeclasses.items.Item", key="a shiv",
                             location=self.room1)
        _moved, scheduled = self.arrive(self.sky, mover=item)
        self.assertEqual(scheduled, 1)
        self.assertTrue(item.db.falling)


class TestWhatDoesNotFall(_AirCase):
    def test_a_walkable_room_schedules_nothing(self):
        """A SkyRoom whose flag was cleared is a catwalk, not air."""
        moved, scheduled = self.arrive(self.walkable_sky)
        self.assertTrue(moved)
        self.assertEqual(scheduled, 0)
        self.assertFalse(self.char1.db.falling)

    def test_an_ordinary_room_schedules_nothing(self):
        _moved, scheduled = self.arrive(self.room2)
        self.assertEqual(scheduled, 0)

    def test_a_body_that_stays_aloft_schedules_nothing(self):
        self.char1.db.stays_aloft = True
        moved, scheduled = self.arrive(self.sky)
        self.assertTrue(moved)
        self.assertEqual(scheduled, 0)
        self.assertFalse(self.char1.db.falling)

    def test_a_truthy_stays_aloft_is_not_the_flag(self):
        """Control on the strict read: ``1`` still falls."""
        self.char1.db.stays_aloft = 1
        _moved, scheduled = self.arrive(self.sky)
        self.assertEqual(scheduled, 1)

    def test_a_running_chain_is_not_a_new_fall(self):
        """This is the state on EVERY step of a fall: the step's own
        ``move_to`` re-enters this hook."""
        self.char1.db.falling = {"cells": 3, "origin": self.sky,
                                 "roll": False}
        self.char1.ndb.fall_active = True
        _moved, scheduled = self.arrive(self.sky)
        self.assertEqual(scheduled, 0)
        self.assertEqual(self.char1.db.falling["cells"], 3)

    def test_a_dragged_companion_is_not_a_new_fall(self):
        """A ``led_by`` marker means the leader's step moves them."""
        self.char2.db.falling = {"led_by": self.char1}
        _moved, scheduled = self.arrive(self.sky, mover=self.char2)
        self.assertEqual(scheduled, 0)

    def test_an_exit_born_in_an_air_cell_schedules_nothing(self):
        """@airfill creates the column's own ``down`` exits in the air."""
        with mock.patch.object(gravity, "delay") as delayed:
            ex = create_object("typeclasses.exits.Exit", key="down",
                               location=self.sky, destination=self.room2)
        self.assertEqual(delayed.call_count, 0)
        self.assertIsNotNone(ex.pk)
        self.assertFalse(ex.db.falling)


class TestAChainThatDiedWithTheProcessResumes(_AirCase):
    """A record with NO ``fall_active`` is a reload or a reconnect: the
    persistent half survived, the ephemeral chain did not."""

    def test_a_record_with_no_live_chain_reschedules(self):
        self.char1.db.falling = {"cells": 2, "origin": self.sky,
                                 "roll": False}
        _moved, scheduled = self.arrive(self.sky)
        self.assertEqual(scheduled, 1)

    def test_and_keeps_the_cells_already_fallen(self):
        self.char1.db.falling = {"cells": 2, "origin": self.sky,
                                 "roll": False}
        self.arrive(self.sky)
        self.assertEqual(self.char1.db.falling["cells"], 2)


class TestALeapIsCarriedNotDropped(_AirCase):
    def test_a_token_schedules_the_leap_not_a_fall(self):
        self.char1.ndb.airborne_token = 1
        self.char1.ndb.leap = {"destination": self.room2, "finish": None}
        _moved, scheduled = self.arrive(self.sky)
        self.assertEqual(scheduled, 1)
        self.assertIs(self.delayed.call_args[0][1], gravity._continue_leap)
        self.assertFalse(self.char1.db.falling)

    def test_the_token_is_spent_on_arrival(self):
        """Or a far perch that is itself air re-grants it forever."""
        self.char1.ndb.airborne_token = 1
        self.char1.ndb.leap = {"destination": self.room2, "finish": None}
        self.arrive(self.sky)
        self.assertFalse(gravity.has_airborne_token(self.char1))


class TestTheVerbsFlightPlan(_AirCase):
    """``ndb.fall_intent`` is how ``jump`` hands the cell the edge's
    difficulty and whether the landing rolls."""

    def test_the_intent_reaches_the_record(self):
        self.char1.ndb.fall_intent = {"edge_difficulty": 14, "roll": True}
        self.arrive(self.sky)
        record = self.char1.db.falling
        self.assertEqual(record["edge_difficulty"], 14)
        self.assertTrue(record["roll"])

    def test_the_intent_is_consumed(self):
        """A leftover intent would roll the NEXT fall off a kerb."""
        self.char1.ndb.fall_intent = {"edge_difficulty": 14, "roll": True}
        self.arrive(self.sky)
        self.assertIsNone(getattr(self.char1.ndb, "fall_intent", None))

    def test_a_stale_intent_is_consumed_even_when_nothing_falls(self):
        """The intent is dropped on EVERY branch, not only the one that
        starts a fall. A plan left on a body that arrived already
        falling -- or that can stay aloft -- would be read by whatever
        air cell they entered next, rolling a later landing against an
        edge they jumped off ten minutes ago."""
        self.char1.db.stays_aloft = True
        self.char1.ndb.fall_intent = {"edge_difficulty": 30, "roll": True}
        _moved, scheduled = self.arrive(self.sky)
        self.assertEqual(scheduled, 0)
        self.assertIsNone(getattr(self.char1.ndb, "fall_intent", None))

    def test_a_running_chain_consumes_a_stale_intent_too(self):
        self.char1.db.falling = {"cells": 1, "origin": self.sky,
                                 "roll": False}
        self.char1.ndb.fall_active = True
        self.char1.ndb.fall_intent = {"edge_difficulty": 30, "roll": True}
        self.arrive(self.sky)
        self.assertIsNone(getattr(self.char1.ndb, "fall_intent", None))

    def test_a_companion_can_ride_in_on_the_intent(self):
        """The verb hands the victim over through the flight plan; the
        leader's record is what names them."""
        self.char2.location = self.sky
        self.char2.db.falling = {"led_by": self.char1}
        self.char1.ndb.fall_intent = {"edge_difficulty": 8, "roll": True,
                                      "companion": self.char2}
        self.arrive(self.sky)
        self.assertIs(self.char1.db.falling["companion"], self.char2)

    def test_no_intent_means_no_roll_and_the_default_difficulty(self):
        from world.combat.constants import FALL_EDGE_DIFFICULTY_DEFAULT
        self.arrive(self.sky)
        record = self.char1.db.falling
        self.assertFalse(record["roll"])
        self.assertEqual(record["edge_difficulty"],
                         FALL_EDGE_DIFFICULTY_DEFAULT)


class TestABrokenFallNeverUndoesAMove(_AirCase):
    """objects.py:1318-1325 -- a raise out of ``at_object_receive``
    makes a COMPLETED move report failure, and every caller that checks
    the return value then narrates a refusal that did not happen."""

    def test_move_to_still_reports_success(self):
        with mock.patch.object(gravity, "start_fall",
                               side_effect=RuntimeError("gravity is broken")):
            moved = self.char1.move_to(self.sky, quiet=True)
        self.assertTrue(moved)

    def test_and_the_body_really_is_in_the_air(self):
        with mock.patch.object(gravity, "start_fall",
                               side_effect=RuntimeError("gravity is broken")):
            self.char1.move_to(self.sky, quiet=True)
        self.assertIs(self.char1.location, self.sky)

    def test_a_broken_predicate_is_survived_too(self):
        with mock.patch.object(gravity, "is_sky",
                               side_effect=RuntimeError("boom")):
            moved = self.char1.move_to(self.sky, quiet=True)
        self.assertTrue(moved)
        self.assertIs(self.char1.location, self.sky)
