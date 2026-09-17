"""A fall is a walk down the column, not a teleport (#3579).

Owner ruling: *"They should traverse the air rooms falling ... if I'm
flying in a room or in a flying vehicle in one of the sky rooms, I'd see
someone fall past me."* So the body makes a REAL move per air cell, one
tick apart, and every cell it passes gets a line. The defects pinned:

* **The old walk teleported to a configured landing room.** An edge
  carried ``sky_room`` / ``fall_distance`` and the body appeared at the
  bottom; nobody in between saw anything, and a column whose shape had
  changed since the edge was authored landed you in the wrong place.
* **The ``down`` exit is re-resolved every tick.** The crane rebuilds
  its column on every trip, so a route cached at takeoff is stale
  before the second cell.
* **A cell with no ``down`` is a parked impasse (#3581), not a crash and
  not a strand.** 81 of the colony's 155 sky rooms are exitless. The
  body stops cleanly where it is, the record is cleared, and it is told
  why -- it must never be left with a live ``db.falling`` nothing will
  ever step.
* **Two states refuse a hooked move and have to be broken first**:
  escorting (``usher_escortee`` refuses at the sky block) and
  channeling (``at_pre_move`` refuses outright). Either one would park
  a falling body in mid-air.

``delay`` never fires under ``evennia test`` -- no reactor -- so it is
patched to run its callback INLINE, which turns the whole chain into one
synchronous call while still counting the ticks that were scheduled.
``msg_room_identity`` is patched because its session gate means a parked
test observer never hears it; the assertions are on template + location.
"""

from __future__ import annotations

from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

import world.gravity as gravity


def _inline(mocked):
    """Run every scheduled callback at once, but keep counting."""
    mocked.side_effect = lambda _seconds, callback, *a, **kw: callback(*a, **kw)
    return mocked


class _ColumnCase(EvenniaTest):
    """roof -> air1 -> ... -> airN -> street, each cell one-way down."""

    CELLS = 3

    def setUp(self):
        super().setUp()
        self.roof = self.room1
        self.roof.key = "Test Roof"
        self.street = self.room2
        self.street.key = "Test Street"
        self.cells = [
            create_object("typeclasses.rooms.SkyRoom", key="In the Air")
            for _ in range(self.CELLS)
        ]
        for index, cell in enumerate(self.cells):
            below = (self.cells[index + 1] if index + 1 < len(self.cells)
                     else self.street)
            create_object("typeclasses.exits.Exit", key="down",
                          location=cell, destination=below,
                          aliases=["d"])
        self.char1.location = self.roof
        self.said = []
        self.char1.msg = lambda text=None, **kw: self.said.append(str(text))
        self.broadcasts = []

    def _record_broadcast(self, location=None, template="", char_refs=None,
                          exclude=None, **kwargs):
        self.broadcasts.append((location, template))

    def fall_from_the_roof(self, mover=None):
        """The real door: a hooked move into the top cell."""
        mover = mover or self.char1
        with mock.patch.object(gravity, "delay") as delayed, \
             mock.patch.object(gravity, "msg_room_identity",
                               side_effect=self._record_broadcast):
            _inline(delayed)
            mover.move_to(self.cells[0], quiet=True)
        return delayed

    def start_in_the_air(self, mover=None, **kwargs):
        """Already in the top cell (``.location`` fires no hook), then
        gravity is asked directly -- the shape the boot sweep uses."""
        mover = mover or self.char1
        mover.location = self.cells[0]
        with mock.patch.object(gravity, "delay") as delayed, \
             mock.patch.object(gravity, "msg_room_identity",
                               side_effect=self._record_broadcast):
            _inline(delayed)
            gravity.start_fall(mover, **kwargs)
        return delayed


class TestABodyReachesTheGround(_ColumnCase):
    def test_it_lands_in_the_street(self):
        self.fall_from_the_roof()
        self.assertIs(self.char1.location, self.street)

    def test_the_record_is_gone(self):
        self.fall_from_the_roof()
        self.assertFalse(self.char1.db.falling)

    def test_no_chain_marker_is_left_behind(self):
        self.fall_from_the_roof()
        self.assertIsNone(getattr(self.char1.ndb, "fall_active", None))

    def test_one_tick_per_cell(self):
        delayed = self.fall_from_the_roof()
        self.assertEqual(delayed.call_count, self.CELLS)

    def test_every_tick_is_a_fall_step(self):
        delayed = self.fall_from_the_roof()
        for call in delayed.call_args_list:
            self.assertIs(call[0][1], gravity._fall_step)

    def test_it_paid_for_three_storeys(self):
        self.fall_from_the_roof()
        said = " ".join(self.said)
        self.assertIn("3 storeys", said)

    def test_the_cell_it_left_is_told(self):
        self.fall_from_the_roof()
        away = [t for loc, t in self.broadcasts
                if loc is self.cells[0] and "drops away" in t]
        self.assertTrue(away, self.broadcasts)

    def test_a_cell_it_passes_through_is_told(self):
        self.fall_from_the_roof()
        past = [t for loc, t in self.broadcasts
                if loc is self.cells[1] and "falls past you" in t]
        self.assertTrue(past, self.broadcasts)

    def test_the_landing_room_is_told(self):
        self.fall_from_the_roof()
        landed = [t for loc, t in self.broadcasts if loc is self.street]
        self.assertTrue(landed, self.broadcasts)


class TestAColumnOfOneCell(_ColumnCase):
    CELLS = 1

    def test_one_tick_lands_it(self):
        delayed = self.fall_from_the_roof()
        self.assertEqual(delayed.call_count, 1)
        self.assertIs(self.char1.location, self.street)

    def test_the_prose_counts_one_storey(self):
        self.fall_from_the_roof()
        self.assertIn("1 storey", " ".join(self.said))


class TestAColumnOfSixCells(_ColumnCase):
    CELLS = 6

    def test_six_ticks_six_cells(self):
        delayed = self.fall_from_the_roof()
        self.assertEqual(delayed.call_count, 6)
        self.assertIs(self.char1.location, self.street)


class TestACellWithNothingBeneath(_ColumnCase):
    """The parked impasse (#3581): the column simply ends."""

    CELLS = 1

    def setUp(self):
        super().setUp()
        for ex in list(self.cells[0].exits):
            ex.delete()

    def test_the_body_stops_where_it_is(self):
        self.fall_from_the_roof()
        self.assertIs(self.char1.location, self.cells[0])

    def test_the_record_is_cleared_not_left_live(self):
        """A live record nothing will ever step is the wedge."""
        self.fall_from_the_roof()
        self.assertFalse(self.char1.db.falling)

    def test_it_only_tried_once(self):
        delayed = self.fall_from_the_roof()
        self.assertEqual(delayed.call_count, 1)

    def test_they_are_told_why(self):
        self.fall_from_the_roof()
        self.assertIn("nothing beneath", " ".join(self.said))

    def test_the_cell_is_told_too(self):
        self.fall_from_the_roof()
        hangs = [t for loc, t in self.broadcasts
                 if loc is self.cells[0] and "hangs in the open air" in t]
        self.assertTrue(hangs, self.broadcasts)

    def test_no_damage_for_a_fall_that_did_not_happen(self):
        before = self.char1.medical_state.organs[
            "right_metatarsals"].current_hp
        self.fall_from_the_roof()
        self.assertEqual(
            self.char1.medical_state.organs["right_metatarsals"].current_hp,
            before)


class TestTheStatesThatRefuseAMove(_ColumnCase):
    """Escorting and channeling both veto a hooked move; a fall breaks
    them rather than parking the body in mid-air.

    The escort half is easy to test WRONGLY. Put the escortee somewhere
    the walker cannot take them and ``usher_escortee`` dissolves the
    link on its own, so the fall lands whether or not gravity ever
    cleared it -- deleting ``_clear_escort`` outright still passes. The
    veto itself is what has to be held open: ``usher_escortee`` is
    patched to REFUSE every move, which is the state
    ``Character.at_pre_move`` hands it, and the fall has to land anyway.
    """

    def _refusing_escort(self):
        return mock.patch("world.movement_coupling.usher_escortee",
                          return_value=False)

    def test_the_control_that_veto_really_does_refuse_a_move(self):
        """Without this the two pins below would pass against a patch
        that never fired."""
        self.char1.location = self.cells[0]
        self.char1.db.escorting = self.char2
        with self._refusing_escort():
            moved = self.char1.move_to(self.street, quiet=True)
        self.assertFalse(moved)
        self.assertIs(self.char1.location, self.cells[0])

    def test_starting_a_fall_clears_the_escort_link(self):
        """The direct pin on ``_clear_escort``: a body in free fall is
        escorting nobody."""
        self.char1.location = self.cells[0]
        self.char1.db.escorting = self.char2
        with mock.patch.object(gravity, "delay"), \
             mock.patch.object(gravity, "msg_room_identity"):
            gravity.start_fall(self.char1)
        self.assertIsNone(self.char1.db.escorting)

    def test_an_escorting_body_still_reaches_the_ground(self):
        self.char1.location = self.cells[0]
        self.char1.db.escorting = self.char2
        with self._refusing_escort(), \
             mock.patch.object(gravity, "delay") as delayed, \
             mock.patch.object(gravity, "msg_room_identity"):
            _inline(delayed)
            gravity.start_fall(self.char1)
        self.assertIs(self.char1.location, self.street)

    def test_it_is_not_stranded_half_way_down(self):
        """The failure mode the veto produces: the first step's move is
        refused and the body parks in the column."""
        self.char1.location = self.cells[0]
        self.char1.db.escorting = self.char2
        with self._refusing_escort(), \
             mock.patch.object(gravity, "delay") as delayed, \
             mock.patch.object(gravity, "msg_room_identity"):
            _inline(delayed)
            gravity.start_fall(self.char1)
        self.assertNotIn("hang in the open air", " ".join(self.said))
        self.assertFalse(self.char1.db.falling)

    def test_the_channel_break_is_asked_for(self):
        self.char1.location = self.cells[0]
        with mock.patch.object(gravity, "delay") as delayed, \
             mock.patch.object(gravity, "msg_room_identity"), \
             mock.patch.object(gravity, "_interrupt") as interrupt:
            _inline(delayed)
            gravity.start_fall(self.char1)
        self.assertIn(self.char1, [c[0][0] for c in interrupt.call_args_list])

    def test_a_channeling_body_still_reaches_the_ground(self):
        from world.channeled import begin_channel, channel_of
        self.char1.location = self.cells[0]
        with mock.patch("world.channeled.delay"):
            begin_channel(self.char1, 30, "welding a plate",
                          on_complete=lambda: None,
                          on_interrupt=lambda fraction: None,
                          key="welding")
        self.assertIsNotNone(channel_of(self.char1), "premise: channeling")
        with mock.patch.object(gravity, "delay") as delayed, \
             mock.patch.object(gravity, "msg_room_identity"):
            _inline(delayed)
            gravity.start_fall(self.char1)
        self.assertIsNone(channel_of(self.char1))
        self.assertIs(self.char1.location, self.street)


class TestADraggedCompanionRidesTheSameFall(_ColumnCase):
    """The victim goes in hookless and rides the LEADER's record -- their
    own arrival must never start a chain of its own."""

    def _drag(self):
        self.char2.location = self.cells[0]
        return self.start_in_the_air(companion=self.char2)

    def test_the_victim_arrives_in_the_same_room(self):
        self._drag()
        self.assertIs(self.char2.location, self.street)

    def test_only_one_chain_ever_ran(self):
        delayed = self._drag()
        self.assertEqual(delayed.call_count, self.CELLS)

    def test_the_victim_carries_only_a_marker_record(self):
        self.char1.location = self.cells[0]
        self.char2.location = self.cells[0]
        with mock.patch.object(gravity, "delay"), \
             mock.patch.object(gravity, "msg_room_identity"):
            gravity.start_fall(self.char1, companion=self.char2)
        self.assertEqual(self.char2.db.falling, {"led_by": self.char1})

    def test_both_records_are_cleared_at_the_bottom(self):
        self._drag()
        self.assertFalse(self.char1.db.falling)
        self.assertFalse(self.char2.db.falling)

    def test_a_companion_who_is_not_in_the_cell_is_dropped(self):
        self.char2.location = self.roof
        with mock.patch.object(gravity, "delay"), \
             mock.patch.object(gravity, "msg_room_identity"):
            self.char1.location = self.cells[0]
            gravity.start_fall(self.char1, companion=self.char2)
        self.assertIsNone(self.char1.db.falling["companion"])
        self.assertFalse(self.char2.db.falling)


class TestAThingFallsTheSameColumn(_ColumnCase):
    def _item(self):
        return create_object("typeclasses.items.Item", key="a steel shiv",
                             location=self.roof)

    def test_it_lands_in_the_street(self):
        item = self._item()
        self.fall_from_the_roof(mover=item)
        self.assertIs(item.location, self.street)

    def test_one_tick_per_cell_for_a_thing_too(self):
        item = self._item()
        delayed = self.fall_from_the_roof(mover=item)
        self.assertEqual(delayed.call_count, self.CELLS)

    def test_it_lands_with_the_item_line(self):
        item = self._item()
        self.fall_from_the_roof(mover=item)
        clatter = [t for loc, t in self.broadcasts
                   if loc is self.street and "clatter" in t]
        self.assertTrue(clatter, self.broadcasts)

    def test_a_thing_tumbles_where_a_body_falls(self):
        item = self._item()
        self.fall_from_the_roof(mover=item)
        self.assertTrue([t for loc, t in self.broadcasts
                         if loc is self.cells[0] and "tumbles away" in t])

    def test_the_record_is_gone(self):
        item = self._item()
        self.fall_from_the_roof(mover=item)
        self.assertFalse(item.db.falling)


class TestAFallThatLeavesTheAirByAnotherDoor(_ColumnCase):
    """Someone @tel'd out mid-fall: the next step finds a body that is
    not in air any more and drops the record instead of moving it."""

    def test_the_record_is_dropped(self):
        self.char1.location = self.cells[0]
        with mock.patch.object(gravity, "delay"), \
             mock.patch.object(gravity, "msg_room_identity"):
            gravity.start_fall(self.char1)
        self.char1.location = self.street
        with mock.patch.object(gravity, "msg_room_identity"):
            gravity._fall_step(self.char1)
        self.assertFalse(self.char1.db.falling)
        self.assertIs(self.char1.location, self.street)


class TestAFallerWhoLoggedOut(_ColumnCase):
    """No location at all: the record is KEPT so the reconnect hook can
    resume it, but the live chain marker is dropped."""

    def test_the_record_survives(self):
        self.char1.location = self.cells[0]
        with mock.patch.object(gravity, "delay"), \
             mock.patch.object(gravity, "msg_room_identity"):
            gravity.start_fall(self.char1)
        self.char1.location = None
        with mock.patch.object(gravity, "delay") as delayed, \
             mock.patch.object(gravity, "msg_room_identity"):
            gravity._fall_step(self.char1)
        self.assertTrue(self.char1.db.falling)
        self.assertEqual(delayed.call_count, 0)
        self.assertIsNone(getattr(self.char1.ndb, "fall_active", None))


class TestAStrandSaysWhichStrandItIs(_ColumnCase):
    """Four different things stop a fall, and only ONE of them means
    there is nothing below.

    ``no_down`` is the parked impasse: the column genuinely ends, and
    "nothing beneath you here -- no ledge, no street" is the truth.
    ``limit`` (a runaway column past FALL_MAX_CELLS), ``refused`` (the
    move was vetoed) and ``fault`` (the step raised) all stop a body
    that has a perfectly good street under it. Telling those three that
    there is nothing beneath them is a lie the player cannot check, and
    it sends them looking for a build error that is not there.
    """

    CELLS = 3

    def _strand_with(self, reason):
        self.char1.location = self.cells[0]
        record = {"cells": 1, "origin": self.cells[0], "roll": False,
                  "companion": None}
        with mock.patch.object(gravity, "msg_room_identity",
                               side_effect=self._record_broadcast):
            gravity._strand(self.char1, record, self.cells[0], reason=reason)
        return " ".join(self.said)

    def test_the_impasse_says_there_is_nothing_beneath(self):
        self.assertIn("nothing beneath", self._strand_with("no_down"))

    def test_the_runaway_guard_does_not(self):
        self.assertNotIn("nothing beneath", self._strand_with("limit"))

    def test_a_refused_move_does_not(self):
        self.assertNotIn("nothing beneath", self._strand_with("refused"))

    def test_a_faulted_step_does_not(self):
        self.assertNotIn("nothing beneath", self._strand_with("fault"))

    def test_the_guards_still_say_something(self):
        """Silence would be its own bug -- the body has stopped and the
        player is owed an explanation."""
        for reason in ("limit", "refused", "fault"):
            self.said.clear()
            self.assertIn("open air", self._strand_with(reason), reason)

    def test_the_room_line_matches_the_reason(self):
        self.broadcasts.clear()
        self._strand_with("no_down")
        self.assertTrue([t for _l, t in self.broadcasts
                         if "nothing beneath" in t])
        self.broadcasts.clear()
        self._strand_with("refused")
        self.assertFalse([t for _l, t in self.broadcasts
                          if "nothing beneath" in t])


class TestTheReasonIsPlumbedThroughFromTheStep(_ColumnCase):
    """Not just ``_strand``'s own branch: the caller has to pass the
    reason that actually applies."""

    CELLS = 3

    def _live_record(self):
        self.char1.location = self.cells[0]
        with mock.patch.object(gravity, "delay"), \
             mock.patch.object(gravity, "msg_room_identity"):
            gravity.start_fall(self.char1)

    def test_a_refused_move_mid_column_is_not_an_impasse(self):
        self._live_record()
        self.said.clear()
        with mock.patch.object(gravity, "delay"), \
             mock.patch.object(gravity, "msg_room_identity"), \
             mock.patch.object(type(self.char1), "move_to",
                               return_value=False):
            gravity._fall_step(self.char1)
        said = " ".join(self.said)
        self.assertIn("open air", said)
        self.assertNotIn("nothing beneath", said)
        self.assertFalse(self.char1.db.falling)
        self.assertIs(self.char1.location, self.cells[0])

    def test_the_runaway_cap_is_not_an_impasse_either(self):
        from world.combat.constants import FALL_MAX_CELLS
        self._live_record()
        record = dict(self.char1.db.falling)
        record["cells"] = FALL_MAX_CELLS
        self.char1.db.falling = record
        self.said.clear()
        with mock.patch.object(gravity, "delay"), \
             mock.patch.object(gravity, "msg_room_identity"):
            gravity._fall_step(self.char1)
        said = " ".join(self.said)
        self.assertIn("open air", said)
        self.assertNotIn("nothing beneath", said)
        self.assertFalse(self.char1.db.falling)

    def test_the_bare_cell_IS_an_impasse(self):
        """The control on the three above: the reason that DOES mean
        nothing below still says so through the same door."""
        for ex in list(self.cells[0].exits):
            ex.delete()
        self._live_record()
        self.said.clear()
        with mock.patch.object(gravity, "delay"), \
             mock.patch.object(gravity, "msg_room_identity"):
            gravity._fall_step(self.char1)
        self.assertIn("nothing beneath", " ".join(self.said))
