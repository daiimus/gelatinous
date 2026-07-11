"""Doors + biometric access (verticality §2, the door IS the exit).

A door is a mirrored DoorExit pair; locked traversal is answered by the
sleeve against the §2.2 grant file (world.access); the pathfinder treats
locked doors as blocked edges per traverser; the elevator's floor locks
consume the same grant model.
"""

import time
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

import typeclasses.doors as dmod
import typeclasses.elevator as emod
from world.access import is_granted, make_grant


def _bind(mock, cls, *names):
    for name in names:
        setattr(mock, name, getattr(cls, name).__get__(mock, cls))


def _sleeve(uid):
    char = MagicMock()
    char.sleeve_uid = uid
    return char


def _door_factory(closed=True, locked=False, grants=None, broken=False):
    door = MagicMock()
    door.db = SimpleNamespace(is_door=True, door_closed=closed,
                              door_locked=locked, door_broken=broken,
                              access_grants=grants or [], door_twin=None)
    _bind(door, dmod.DoorExit,
          "is_open", "is_locked_for", "door_blocks", "_traverse_gate",
          "_mirror", "_both_rooms_msg", "twin")
    door.destination.exits = []
    return door


class TestGrantFile(TestCase):
    def test_matching_live_grant_passes(self):
        alice = _sleeve("uid-alice")
        grants = [make_grant(alice, issued_by="Vess")]
        self.assertTrue(is_granted(alice, grants))
        self.assertFalse(is_granted(_sleeve("uid-mallory"), grants))

    def test_expired_grant_fails_closed(self):
        alice = _sleeve("uid-alice")
        stale = [make_grant(alice, until=time.time() - 10)]
        self.assertFalse(is_granted(alice, stale))
        live = [make_grant(alice, until=time.time() + 3600)]
        self.assertTrue(is_granted(alice, live))

    def test_no_sleeve_or_garbage_never_grants(self):
        self.assertFalse(is_granted(_sleeve(None), [{"sleeve": None}]))
        self.assertFalse(is_granted(_sleeve("u"), ["garbage", 42, {}]))
        self.assertFalse(is_granted(_sleeve("u"), None))


class TestDoorGate(TestCase):
    def test_open_door_passes_silently(self):
        door = _door_factory(closed=False)
        walker = MagicMock()
        self.assertTrue(door._traverse_gate(walker))
        walker.msg.assert_not_called()

    def test_closed_unlocked_auto_opens_both_sides(self):
        door = _door_factory(closed=True)
        twin = _door_factory(closed=True)
        door.db.door_twin = twin
        twin.pk = 1
        walker = MagicMock()
        self.assertTrue(door._traverse_gate(walker))
        self.assertFalse(door.db.door_closed)
        self.assertFalse(twin.db.door_closed)          # mirrored
        self.assertIn("push the door open", walker.msg.call_args.args[0])

    def test_locked_refuses_the_ungranted(self):
        door = _door_factory(closed=True, locked=True,
                     grants=[make_grant(_sleeve("uid-alice"))])
        mallory = _sleeve("uid-mallory")
        self.assertFalse(door._traverse_gate(mallory))
        self.assertTrue(door.db.door_locked)           # unchanged
        self.assertIn("blinks red", mallory.msg.call_args.args[0])

    def test_locked_admits_granted_momentarily(self):
        alice = _sleeve("uid-alice")
        door = _door_factory(closed=True, locked=True, grants=[make_grant(alice)])
        self.assertTrue(door._traverse_gate(alice))
        self.assertTrue(door.db.door_locked)           # seals again behind
        self.assertTrue(door.db.door_closed)
        self.assertIn("flashes green", alice.msg.call_args.args[0])

    def test_broken_door_never_blocks(self):
        door = _door_factory(closed=True, locked=True, broken=True)
        walker = _sleeve("uid-anyone")
        self.assertTrue(door._traverse_gate(walker))
        self.assertFalse(door.door_blocks(walker))


class TestClosedDoorBlocksSight(TestCase):
    """§2.1: sight through a closed door is NONE — looking at the door
    describes the door, never the far room's occupants."""

    def _door(self, closed=True, locked=False, desc=None):
        door = _door_base = _door_factory(closed=closed, locked=locked)
        door.db.desc = desc
        _bind(door, dmod.DoorExit, "return_appearance")
        return door

    def test_closed_door_shows_the_door_not_the_room(self):
        door = self._door(closed=True, locked=False)
        out = door.return_appearance(MagicMock())
        self.assertIn("closed", out)
        door.get_display_desc.assert_not_called()   # far-side view never built

    def test_locked_door_mentions_the_reader(self):
        door = self._door(closed=True, locked=True)
        out = door.return_appearance(MagicMock())
        self.assertIn("sealed", out)
        self.assertIn("reader", out)

    def test_authored_desc_is_kept(self):
        door = self._door(closed=True, desc="Brushed steel, knee-scarred.")
        self.assertIn("Brushed steel", door.return_appearance(MagicMock()))


class TestPathfinderEdges(TestCase):
    def _room_with(self, exits):
        room = MagicMock()
        room.exits = exits
        return room

    def _plain_exit(self):
        ex = MagicMock(spec=["destination", "access"])
        ex.access.return_value = True
        return ex

    def test_locked_door_is_a_blocked_edge(self):
        from world.spatial.pathfind import _neighbors
        alice = _sleeve("uid-alice")
        blocked = self._plain_exit()
        blocked.door_blocks = MagicMock(return_value=True)
        open_door = self._plain_exit()
        open_door.door_blocks = MagicMock(return_value=False)
        plain = self._plain_exit()
        room = self._room_with([blocked, open_door, plain])
        found = [ex for _, ex in _neighbors(room, alice)]
        self.assertNotIn(blocked, found)
        self.assertIn(open_door, found)
        self.assertIn(plain, found)

    def test_no_traverser_keeps_pure_connectivity(self):
        from world.spatial.pathfind import _neighbors
        blocked = self._plain_exit()
        blocked.door_blocks = MagicMock(return_value=True)
        room = self._room_with([blocked])
        self.assertEqual(len(list(_neighbors(room, None))), 1)


class TestElevatorFloorLock(TestCase):
    def _car(self, locks):
        car = MagicMock()
        landing1, landing2 = MagicMock(), MagicMock()
        car.db = SimpleNamespace(
            floors=[[landing1, "1"], [landing2, "2"]], current_floor=0,
            moving=False, target_floor=None, floor_locks=locks,
            shaft_xy=None)
        _bind(car, emod.ElevatorCar,
              "floor_index", "request_floor", "_floor_permitted",
              "_begin_move", "current_landing")
        return car

    def test_secured_floor_refuses_ungranted_sleeve(self):
        alice = _sleeve("uid-alice")
        car = self._car({"2": [make_grant(alice)]})
        mallory = _sleeve("uid-mallory")
        with patch.object(emod, "delay") as d:
            self.assertFalse(car.request_floor("2", mallory))
        d.assert_not_called()
        self.assertIn("blinks red", mallory.msg.call_args.args[0])

    def test_secured_floor_lights_for_granted_sleeve(self):
        alice = _sleeve("uid-alice")
        car = self._car({"2": [make_grant(alice)]})
        with patch.object(emod, "delay") as d:
            self.assertTrue(car.request_floor("2", alice))
        d.assert_called_once()

    def test_unsecured_floors_stay_free(self):
        car = self._car({"2": [make_grant(_sleeve("uid-alice"))]})
        car.db.current_floor = 1
        with patch.object(emod, "delay") as d:
            self.assertTrue(car.request_floor("1", _sleeve("uid-mallory")))
        d.assert_called_once()
