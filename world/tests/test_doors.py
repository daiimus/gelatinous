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

    def test_closed_door_refuses_until_opened(self):
        # the door is a state machine: walking never opens it (user
        # call 2026-07-10) — passage requires the open command first
        door = _door_factory(closed=True)
        walker = MagicMock()
        self.assertFalse(door._traverse_gate(walker))
        self.assertTrue(door.db.door_closed)           # untouched
        self.assertIn("closed", walker.msg.call_args.args[0])
        self.assertIn("open it", walker.msg.call_args.args[0])

    def test_locked_refuses_everyone_even_granted(self):
        alice = _sleeve("uid-alice")
        door = _door_factory(closed=True, locked=True,
                             grants=[make_grant(alice)])
        for walker in (alice, _sleeve("uid-mallory")):
            self.assertFalse(door._traverse_gate(walker))
            self.assertIn("sealed", walker.msg.call_args.args[0])
        self.assertTrue(door.db.door_locked)           # unchanged
        self.assertTrue(door.db.door_closed)

    def test_broken_door_never_blocks(self):
        door = _door_factory(closed=True, locked=True, broken=True)
        walker = _sleeve("uid-anyone")
        self.assertTrue(door._traverse_gate(walker))
        self.assertFalse(door.door_blocks(walker))

    def test_locked_door_blocks_only_ungranted(self):
        # travel opens doors en route now: closed-unlocked passes,
        # locked passes only a granted sleeve
        alice = _sleeve("uid-alice")
        locked = _door_factory(closed=True, locked=True,
                               grants=[make_grant(alice)])
        self.assertFalse(locked.door_blocks(alice))
        stranger = _sleeve("uid-stranger")
        self.assertTrue(locked.door_blocks(stranger))
        open_door = _door_factory(closed=False)
        self.assertFalse(open_door.door_blocks(alice))


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
        self.assertIn("blinks |rred|n", mallory.msg.call_args.args[0])

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


class TestAutolock(TestCase):
    """The spring latch: closing an autolock door seals it — anyone may
    restore security; only granted sleeves may remove it."""

    def _closer(self, autolock=True, open_=True):
        from commands.CmdDoors import CmdCloseDoor
        door = _door_factory(closed=not open_, locked=False)
        door.db.door_autolock = autolock
        _bind(door, dmod.DoorExit, "is_open")
        cmd = CmdCloseDoor()
        cmd.args = "door"
        cmd.caller = MagicMock()
        with patch("commands.CmdDoors.find_door", return_value=door):
            cmd.func()
        return door, cmd.caller

    def test_stranger_closing_reseals_the_lock(self):
        door, caller = self._closer(autolock=True)
        self.assertTrue(door.db.door_closed)
        self.assertTrue(door.db.door_locked)           # spring latch
        self.assertIn("re-engages", caller.msg.call_args.args[0])

    def test_plain_doors_just_close(self):
        door, caller = self._closer(autolock=False)
        self.assertTrue(door.db.door_closed)
        self.assertFalse(door.db.door_locked)


class TestDoorBlocksForTravel(TestCase):
    """Pathfinder edges: doors pass for those who could open them."""

    def _door(self, closed=True, locked=False, grants=()):
        door = MagicMock()
        door.db = SimpleNamespace(door_closed=closed, door_locked=locked,
                                  door_broken=False,
                                  access_grants=list(grants))
        door.is_open = dmod.DoorExit.is_open.__get__(door, dmod.DoorExit)
        door.door_blocks = dmod.DoorExit.door_blocks.__get__(
            door, dmod.DoorExit)
        return door

    def test_open_passes(self):
        self.assertFalse(self._door(closed=False).door_blocks(MagicMock()))

    def test_closed_unlocked_passes_anyone(self):
        # travel opens it en route with the real verb
        self.assertFalse(self._door(closed=True).door_blocks(MagicMock()))

    def test_locked_blocks_ungranted(self):
        door = self._door(closed=True, locked=True)
        with patch("world.access.is_granted", return_value=False):
            self.assertTrue(door.door_blocks(MagicMock()))

    def test_locked_passes_granted(self):
        door = self._door(closed=True, locked=True)
        with patch("world.access.is_granted", return_value=True):
            self.assertFalse(door.door_blocks(MagicMock()))


class TestTravelOpensDoors(TestCase):
    def test_step_opens_closed_door_then_walks(self):
        from types import SimpleNamespace as NS
        from world.director import travel as tmod
        npc = MagicMock()
        door_exit = MagicMock()
        door_exit.key = "west"
        door_exit.is_open = lambda: False
        npc.ndb = NS(director_travel={
            "destination": MagicMock(), "steps": 0, "step_delay": 1,
            "on_arrive": None, "on_fail": None})
        with patch.object(tmod, "find_path_exits",
                          return_value=[door_exit]), \
             patch.object(tmod, "delay"):
            tmod._travel_step(npc)
        self.assertEqual(
            [c.args[0] for c in npc.execute_cmd.call_args_list],
            ["open west", "west"])

    def test_step_walks_plain_exits_directly(self):
        from types import SimpleNamespace as NS
        from world.director import travel as tmod
        npc = MagicMock()
        ex = MagicMock(spec=["key"])
        ex.key = "north"
        npc.ndb = NS(director_travel={
            "destination": MagicMock(), "steps": 0, "step_delay": 1,
            "on_arrive": None, "on_fail": None})
        with patch.object(tmod, "find_path_exits", return_value=[ex]), \
             patch.object(tmod, "delay"):
            tmod._travel_step(npc)
        self.assertEqual(
            [c.args[0] for c in npc.execute_cmd.call_args_list], ["north"])
