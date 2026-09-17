"""Tests for :func:`commands.combat.jump.drop_to_room` (#307, PR-H0).

The helper centralises the physical effects that happen when an item
ends up on a room's floor: the move, and the proximity init. It is
deliberately message-free -- each caller (CmdDrop, the sever pipeline,
throw / disarm cleanups) owns its own narrative prose.

**#3579 removed the third effect.** ``drop_to_room`` used to call an
``apply_gravity_to_items(room)`` sweep, which every drop site had to
remember to reach through this helper or lose. Gravity is now a property
of the ROOM: the move here is made with hooks ON, so
``Room.at_object_receive`` -> ``world.gravity.on_enter_air`` starts the
fall for free, by this door and by every other one. The old class of
tests patched a name that no longer exists, which under
``mock.patch`` is an ERROR at patch time rather than a quiet pass -- so
they are gone, and one real-object case stands in their place.

Run via::

    evennia test world.tests.test_drop_to_room
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

import world.gravity as gravity
from world.combat.constants import NDB_PROXIMITY_UNIVERSAL


def _stub_room():
    room = SimpleNamespace()
    room.db = SimpleNamespace(is_sky_room=False)
    room.contents = []
    room.key = "test room"
    return room


def _stub_item(key="test-item"):
    item = SimpleNamespace()
    item.key = key
    item.ndb = SimpleNamespace()
    item.moved_to = None

    def _move_to(destination, quiet=False):
        item.moved_to = destination

    item.move_to = _move_to
    return item


class DropToRoomMove(TestCase):
    """Item is physically relocated to the destination room."""

    def test_moves_item_to_room(self):
        from commands.combat.jump import drop_to_room
        item = _stub_item()
        room = _stub_room()
        drop_to_room(item, room)
        self.assertIs(item.moved_to, room)

    def test_uses_quiet_move(self):
        """Move-to is silent -- callers handle their own messaging."""
        from commands.combat.jump import drop_to_room
        item = _stub_item()
        room = _stub_room()
        moved_with = {}

        def capture_move(destination, quiet=False):
            moved_with["destination"] = destination
            moved_with["quiet"] = quiet

        item.move_to = capture_move
        drop_to_room(item, room)
        self.assertIs(moved_with["destination"], room)
        self.assertTrue(moved_with["quiet"])

    def test_the_move_keeps_its_hooks(self):
        """Hooks ON is the whole gravity contract: the destination's own
        ``at_object_receive`` is what starts a fall. A ``move_hooks=False``
        here would silently un-wire gravity for every drop site."""
        from commands.combat.jump import drop_to_room
        item = _stub_item()
        seen = {}

        def capture_move(destination, quiet=False, **kwargs):
            seen.update(kwargs)

        item.move_to = capture_move
        drop_to_room(item, _stub_room())
        self.assertNotIn("move_hooks", seen)


class DropToRoomProximity(TestCase):
    """Proximity list is initialised on the item's ndb."""

    def test_creates_empty_proximity_list_when_missing(self):
        from commands.combat.jump import drop_to_room
        item = _stub_item()
        drop_to_room(item, _stub_room())
        proximity = getattr(item.ndb, NDB_PROXIMITY_UNIVERSAL, None)
        self.assertIsInstance(proximity, list)
        self.assertEqual(proximity, [])

    def test_preserves_existing_proximity_list(self):
        """Re-dropping an item that already has proximity entries keeps
        them -- re-init only happens when the attribute is absent/None."""
        from commands.combat.jump import drop_to_room
        item = _stub_item()
        sentinel = SimpleNamespace()
        setattr(item.ndb, NDB_PROXIMITY_UNIVERSAL, [sentinel])
        drop_to_room(item, _stub_room())
        proximity = getattr(item.ndb, NDB_PROXIMITY_UNIVERSAL, [])
        self.assertIn(sentinel, proximity)

    def test_reinits_when_existing_is_none(self):
        """Defensive: an explicit ``None`` placeholder gets replaced."""
        from commands.combat.jump import drop_to_room
        item = _stub_item()
        setattr(item.ndb, NDB_PROXIMITY_UNIVERSAL, None)
        drop_to_room(item, _stub_room())
        proximity = getattr(item.ndb, NDB_PROXIMITY_UNIVERSAL, None)
        self.assertIsInstance(proximity, list)


class DropToRoomNoMessages(TestCase):
    """The helper does NOT emit player-facing messages.

    Callers own their own narrative. This pins the contract so nobody
    adds a sneaky ``msg`` call without surfacing the implication for the
    sever / disarm / throw scenarios that all have distinct prose.
    """

    def test_does_not_message_room_or_item(self):
        from commands.combat.jump import drop_to_room
        item = _stub_item()
        item.msg = lambda *a, **k: self.fail("item should not be messaged")
        room = _stub_room()
        room.msg_contents = lambda *a, **k: self.fail(
            "room should not be messaged"
        )
        drop_to_room(item, room)


def _queue(mocked):
    """Collect scheduled callbacks instead of running them."""
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


class DropToRoomIntoAnAirCell(EvenniaTest):
    """The replacement for the old gravity-dispatch class, with real
    objects: dropping something into air is a FALL, and nothing in
    ``drop_to_room`` had to know that.

    The tick is QUEUED and drained after ``drop_to_room`` returns rather
    than run inline. Inline, the whole fall would execute inside
    ``item.move_to`` -- so the helper's own remaining work (the
    proximity init) would run AFTER the item had already landed, which
    is the reverse of the production order and would let a defect in
    that ordering pass. Draining afterwards reproduces the real
    sequence: the helper finishes, then the reactor fires the step.
    """

    def setUp(self):
        super().setUp()
        self.street = self.room2
        self.air = create_object("typeclasses.rooms.SkyRoom",
                                 key="In the Air")
        self.mid = create_object("typeclasses.rooms.SkyRoom",
                                 key="In the Air")
        create_object("typeclasses.exits.Exit", key="down",
                      location=self.air, destination=self.mid, aliases=["d"])
        create_object("typeclasses.exits.Exit", key="down",
                      location=self.mid, destination=self.street,
                      aliases=["d"])
        self.item = create_object("typeclasses.items.Item",
                                  key="a steel shiv", location=self.room1)

    def drop(self, room, settle=True):
        from commands.combat.jump import drop_to_room
        with patch.object(gravity, "delay") as delayed, \
             patch.object(gravity, "msg_room_identity"):
            pending = _queue(delayed)
            drop_to_room(self.item, room)
            self.scheduled_before_return = delayed.call_count
            if settle:
                _drain(pending)
        return delayed

    def test_the_helper_only_schedules_the_first_tick(self):
        """Production order: ``drop_to_room`` returns with the fall
        merely armed, not finished."""
        self.drop(self.air, settle=False)
        self.assertEqual(self.scheduled_before_return, 1)
        self.assertIs(self.item.location, self.air)
        self.assertTrue(self.item.db.falling)

    def test_an_item_dropped_into_air_lands_in_the_room_below(self):
        self.drop(self.air)
        self.assertIs(self.item.location, self.street)
        self.assertFalse(self.item.db.falling)

    def test_it_walks_every_cell_of_the_column(self):
        delayed = self.drop(self.air)
        self.assertEqual(delayed.call_count, 2)

    def test_its_proximity_list_is_reset_where_it_lands(self):
        """Every cell is a new room, so the list the helper seeded on
        the roof is stale the moment the item leaves it. A thing that
        landed in the street still carrying the roof's proximity would
        be reachable from a room it is not in."""
        setattr(self.item.ndb, NDB_PROXIMITY_UNIVERSAL, [self.char1])
        self.drop(self.air)
        self.assertEqual(
            getattr(self.item.ndb, NDB_PROXIMITY_UNIVERSAL, None), [])

    def test_a_freshly_dropped_item_ends_with_an_empty_list_too(self):
        self.drop(self.air)
        proximity = getattr(self.item.ndb, NDB_PROXIMITY_UNIVERSAL, None)
        self.assertIsInstance(proximity, list)
        self.assertEqual(proximity, [])

    def test_dropping_onto_a_floor_starts_nothing(self):
        """Control: the helper does not pre-filter, and an ordinary room
        is simply an ordinary room."""
        delayed = self.drop(self.street)
        self.assertEqual(delayed.call_count, 0)
        self.assertIs(self.item.location, self.street)
        self.assertFalse(self.item.db.falling)
