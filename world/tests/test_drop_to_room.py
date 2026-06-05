"""Tests for :func:`commands.combat.jump.drop_to_room` (#307, PR-H0).

The helper centralises the three physical effects that happen when
an item lands on a room's floor — move + gravity + proximity init.
It is deliberately message-free; each caller (CmdDrop, sever pipeline,
future throw / disarm cleanups) owns its own narrative prose.

Run via::

    evennia test world.tests.test_drop_to_room
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from world.combat.constants import NDB_PROXIMITY_UNIVERSAL


def _stub_room(is_sky=False):
    """Minimal room stub with the surfaces apply_gravity_to_items reads."""
    room = SimpleNamespace()
    room.db = SimpleNamespace(is_sky_room=is_sky)
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
        # Patch gravity — its real implementation logs to a channel
        # that doesn't exist in the test environment.  We test
        # gravity dispatch separately in DropToRoomGravity.
        with patch("commands.combat.jump.apply_gravity_to_items"):
            drop_to_room(item, room)
        self.assertIs(item.moved_to, room)

    def test_uses_quiet_move(self):
        """Move-to is silent — callers handle their own messaging."""
        from commands.combat.jump import drop_to_room
        item = _stub_item()
        room = _stub_room()
        moved_with = {}

        def capture_move(destination, quiet=False):
            moved_with["destination"] = destination
            moved_with["quiet"] = quiet

        item.move_to = capture_move
        with patch("commands.combat.jump.apply_gravity_to_items"):
            drop_to_room(item, room)
        self.assertIs(moved_with["destination"], room)
        self.assertTrue(moved_with["quiet"])


class DropToRoomGravity(TestCase):
    """Gravity hook fires on the destination room."""

    def test_apply_gravity_called_with_room(self):
        with patch("commands.combat.jump.apply_gravity_to_items") as mock_gravity:
            from commands.combat.jump import drop_to_room
            item = _stub_item()
            room = _stub_room(is_sky=True)
            drop_to_room(item, room)
        mock_gravity.assert_called_once_with(room)

    def test_apply_gravity_called_for_ground_rooms_too(self):
        """The gravity helper internally no-ops for non-sky rooms,
        but the dispatch shouldn't pre-filter — keeps the contract
        simple and lets gravity logic centralise."""
        with patch("commands.combat.jump.apply_gravity_to_items") as mock_gravity:
            from commands.combat.jump import drop_to_room
            item = _stub_item()
            room = _stub_room(is_sky=False)
            drop_to_room(item, room)
        mock_gravity.assert_called_once_with(room)


class DropToRoomProximity(TestCase):
    """Proximity list is initialised on the item's ndb."""

    def test_creates_empty_proximity_list_when_missing(self):
        from commands.combat.jump import drop_to_room
        item = _stub_item()
        room = _stub_room()
        with patch("commands.combat.jump.apply_gravity_to_items"):
            drop_to_room(item, room)
        proximity = getattr(item.ndb, NDB_PROXIMITY_UNIVERSAL, None)
        self.assertIsInstance(proximity, list)
        self.assertEqual(proximity, [])

    def test_preserves_existing_proximity_list(self):
        """Re-dropping an item that already has proximity entries
        keeps them — re-init only happens when the attribute is
        absent / None."""
        from commands.combat.jump import drop_to_room
        item = _stub_item()
        sentinel = SimpleNamespace()  # Pre-existing proximity entry
        setattr(item.ndb, NDB_PROXIMITY_UNIVERSAL, [sentinel])
        room = _stub_room()
        with patch("commands.combat.jump.apply_gravity_to_items"):
            drop_to_room(item, room)
        proximity = getattr(item.ndb, NDB_PROXIMITY_UNIVERSAL, [])
        self.assertIn(sentinel, proximity)

    def test_reinits_when_existing_is_none(self):
        """Defensive: an explicit ``None`` placeholder gets replaced
        with a fresh list."""
        from commands.combat.jump import drop_to_room
        item = _stub_item()
        setattr(item.ndb, NDB_PROXIMITY_UNIVERSAL, None)
        room = _stub_room()
        with patch("commands.combat.jump.apply_gravity_to_items"):
            drop_to_room(item, room)
        proximity = getattr(item.ndb, NDB_PROXIMITY_UNIVERSAL, None)
        self.assertIsInstance(proximity, list)


class DropToRoomNoMessages(TestCase):
    """The helper does NOT emit player-facing messages.

    Callers own their own narrative.  This pins the contract so
    nobody adds a sneaky ``msg`` call without surfacing the
    implication for sever / disarm / throw scenarios that all
    have distinct prose.
    """

    def test_does_not_message_room_or_item(self):
        from commands.combat.jump import drop_to_room
        item = _stub_item()
        item.msg = lambda *a, **k: self.fail("item should not be messaged")
        room = _stub_room()
        room.msg_contents = lambda *a, **k: self.fail(
            "room should not be messaged"
        )
        with patch("commands.combat.jump.apply_gravity_to_items"):
            drop_to_room(item, room)
