"""Tests for the spatial coordinate substrate (Phase 1): direction
parsing, coordinate read/write, distance/bearing, and the seeding walk
with contradiction + warp handling.
"""

from __future__ import annotations

from unittest import TestCase
from unittest.mock import MagicMock, patch

from world.spatial import (
    DIRECTION_DELTAS,
    bearing,
    distance,
    exit_direction,
    get_xyz,
    is_warp_exit,
    normalize_direction,
    rooms_within,
    seed_coordinates,
    set_xyz,
)


# --- lightweight fakes (no Evennia boot) --------------------------------

class _Aliases:
    def __init__(self, items=()):
        self._items = list(items)

    def all(self):
        return list(self._items)


class _Tags:
    def __init__(self, tags=()):
        self._tags = set(tags)  # set of (key, category)

    def has(self, key, category=None):
        return (key, category) in self._tags


class _Exit:
    def __init__(self, key, destination, aliases=(), warp=False):
        self.key = key
        self.destination = destination
        self.aliases = _Aliases(aliases)
        self.tags = _Tags({("warp", "exit_type")} if warp else set())


class _DB:
    def __init__(self):
        self.xyz = None


class _Room:
    def __init__(self, name):
        self.name = name
        self.db = _DB()
        self.exits = []

    def __repr__(self):
        return f"<{self.name}>"


def _link(a, b, direction, warp=False):
    a.exits.append(_Exit(direction, b, warp=warp))


# --- direction system ---------------------------------------------------

class TestDirections(TestCase):
    def test_all_deltas_unit(self):
        for d, (dx, dy, dz) in DIRECTION_DELTAS.items():
            self.assertTrue(all(v in (-1, 0, 1) for v in (dx, dy, dz)), d)
        self.assertEqual(DIRECTION_DELTAS["north"], (0, 1, 0))
        self.assertEqual(DIRECTION_DELTAS["east"], (1, 0, 0))
        self.assertEqual(DIRECTION_DELTAS["up"], (0, 0, 1))
        self.assertEqual(DIRECTION_DELTAS["down"], (0, 0, -1))

    def test_normalize(self):
        self.assertEqual(normalize_direction("north"), "north")
        self.assertEqual(normalize_direction("N"), "north")
        self.assertEqual(normalize_direction("ne"), "northeast")
        self.assertIsNone(normalize_direction("enter"))
        self.assertIsNone(normalize_direction(None))

    def test_exit_direction_key_then_alias(self):
        self.assertEqual(exit_direction(_Exit("north", None)), "north")
        self.assertEqual(exit_direction(_Exit("n", None)), "north")
        self.assertEqual(
            exit_direction(_Exit("doorway", None, aliases=["s"])), "south")
        self.assertIsNone(exit_direction(_Exit("enter bar", None)))

    def test_is_warp(self):
        self.assertTrue(is_warp_exit(_Exit("up", None, warp=True)))
        self.assertFalse(is_warp_exit(_Exit("up", None)))


# --- coordinate read / write + queries ----------------------------------

class TestCoordinateMath(TestCase):
    def test_set_get(self):
        r = _Room("r")
        self.assertIsNone(get_xyz(r))
        set_xyz(r, 3, -4, 1)
        self.assertEqual(get_xyz(r), (3, -4, 1))

    def test_distance(self):
        a, b = _Room("a"), _Room("b")
        set_xyz(a, 0, 0, 0)
        set_xyz(b, 3, 4, 0)
        self.assertEqual(distance(a, b), 5.0)
        # off-grid → None
        self.assertIsNone(distance(a, _Room("c")))

    def test_bearing(self):
        a = _Room("a")
        set_xyz(a, 0, 0, 0)

        def to(x, y, z):
            r = _Room("t")
            set_xyz(r, x, y, z)
            return bearing(a, r)

        self.assertEqual(to(1, 0, 0), "east")
        self.assertEqual(to(0, 1, 0), "north")
        self.assertEqual(to(1, 1, 0), "northeast")
        self.assertEqual(to(0, 0, 1), "up")
        self.assertEqual(to(1, 0, 1), "east and up")
        self.assertEqual(to(0, 0, 0), "here")

    def test_rooms_within(self):
        center = _Room("c")
        near = _Room("near")
        far = _Room("far")
        set_xyz(center, 0, 0, 0)
        set_xyz(near, 2, 0, 0)
        set_xyz(far, 10, 0, 0)
        with patch("world.spatial.coordinates.all_coordinate_rooms",
                   return_value=[center, near, far]):
            got = rooms_within(center, 3)
        self.assertIn(near, got)
        self.assertNotIn(far, got)
        self.assertNotIn(center, got)


# --- seeding walk -------------------------------------------------------

class TestSeeding(TestCase):
    def _grid(self):
        # A(0,0,0) -E-> B(1,0,0), A -N-> C(0,1,0),
        # B -N-> D(1,1,0), C -E-> D, plus reverse exits.
        A, B, C, D = (_Room(n) for n in "ABCD")
        _link(A, B, "east"); _link(B, A, "west")
        _link(A, C, "north"); _link(C, A, "south")
        _link(B, D, "north"); _link(D, B, "south")
        _link(C, D, "east"); _link(D, C, "west")
        return A, B, C, D

    def test_consistent_grid(self):
        A, B, C, D = self._grid()
        assignments, contradictions = seed_coordinates(A)
        self.assertEqual(assignments[A], (0, 0, 0))
        self.assertEqual(assignments[B], (1, 0, 0))
        self.assertEqual(assignments[C], (0, 1, 0))
        self.assertEqual(assignments[D], (1, 1, 0))
        self.assertEqual(contradictions, [])

    def test_contradiction_detected(self):
        A, B, C, D = self._grid()
        # Add a bogus A -up-> D. D is now reachable two ways with different
        # coords — a geometry contradiction (whichever path reaches it first
        # wins the assignment; the others are flagged).
        _link(A, D, "up")
        assignments, contradictions = seed_coordinates(A)
        self.assertTrue(contradictions)
        for c in contradictions:
            self.assertNotEqual(c["existing"], c["expected"])

    def test_warp_exit_skipped(self):
        A = _Room("A")
        warp_dest = _Room("warp_dest")
        _link(A, warp_dest, "east", warp=True)
        assignments, _ = seed_coordinates(A)
        self.assertNotIn(warp_dest, assignments)  # not reached through a warp

    def test_non_cardinal_skipped(self):
        A = _Room("A")
        bar = _Room("bar")
        A.exits.append(_Exit("enter bar", bar))
        assignments, _ = seed_coordinates(A)
        self.assertNotIn(bar, assignments)


class TestWiring(TestCase):
    def test_coordseed_registered_in_character_cmdset(self):
        from commands.default_cmdsets import CharacterCmdSet
        cs = CharacterCmdSet()
        cs.at_cmdset_creation()
        self.assertIn("@coordseed", [c.key for c in cs.commands])

    def test_room_has_xyz_property(self):
        from typeclasses.rooms import Room
        self.assertIsInstance(Room.__dict__.get("xyz"), property)


class TestSlopedExits(TestCase):
    """Split-level geometry: sloped exits derive their z-step."""

    def _world(self):
        from types import SimpleNamespace

        class Tags:
            def __init__(self, *names):
                self._names = set(names)

            def has(self, name, category=None):
                return name in self._names

        class _Room:                    # identity-hashable (dict key)
            def __init__(self, key):
                self.key = key
                self.exits = []

        def room(key):
            return _Room(key)

        def link(a, b, direction, back, a_tags=(), b_tags=()):
            a.exits.append(SimpleNamespace(
                key=direction, destination=b, aliases=None,
                tags=Tags(*a_tags)))
            b.exits.append(SimpleNamespace(
                key=back, destination=a, aliases=None, tags=Tags(*b_tags)))

        return room, link

    def test_sloped_south_steps_down(self):
        from world.spatial.coordinates import seed_coordinates
        room, link = self._world()
        rack, cube = room("rack"), room("cube")
        link(rack, cube, "south", "north",
             a_tags=("slope_down",), b_tags=("slope_up",))
        assigns, contras = seed_coordinates(rack)
        self.assertEqual(assigns[cube], (0, -1, -1))
        self.assertEqual(contras, [])

    def test_mismatched_return_slope_contradicts(self):
        from world.spatial.coordinates import seed_coordinates
        room, link = self._world()
        rack, cube = room("rack"), room("cube")
        link(rack, cube, "south", "north", a_tags=("slope_down",))
        assigns, contras = seed_coordinates(rack)
        self.assertEqual(len(contras), 1)   # north back reads level: bug

    def test_level_exits_unchanged(self):
        from world.spatial.coordinates import seed_coordinates
        room, link = self._world()
        a, b = room("a"), room("b")
        link(a, b, "east", "west")
        assigns, contras = seed_coordinates(a)
        self.assertEqual(assigns[b], (1, 0, 0))
        self.assertEqual(contras, [])

    def test_warp_still_excluded(self):
        from world.spatial.coordinates import seed_coordinates
        room, link = self._world()
        a, b = room("a"), room("b")
        link(a, b, "east", "west", a_tags=("warp",), b_tags=("warp",))
        assigns, _ = seed_coordinates(a)
        self.assertNotIn(b, assigns)


class TestOriginPin(TestCase):
    """@coordseed anchors at the pinned origin, never the caller."""

    def _cmd(self, switches=(), args=""):
        from commands.CmdCoordSeed import CmdCoordSeed
        cmd = CmdCoordSeed()
        cmd.switches = list(switches)
        cmd.args = args
        cmd.caller = MagicMock()
        return cmd

    def test_unpinned_seed_refuses(self):
        cmd = self._cmd()
        with patch("commands.CmdCoordSeed.pinned_origin",
                   return_value=None), \
             patch("commands.CmdCoordSeed.seed_coordinates") as seed:
            cmd.func()
        seed.assert_not_called()
        self.assertIn("No origin is pinned",
                      cmd.caller.msg.call_args.args[0])

    def test_seed_uses_pinned_origin_not_caller(self):
        origin = MagicMock()
        cmd = self._cmd(switches=("check",))
        with patch("commands.CmdCoordSeed.pinned_origin",
                   return_value=origin), \
             patch("commands.CmdCoordSeed.seed_coordinates",
                   return_value=({}, [])) as seed:
            cmd.func()
        seed.assert_called_once_with(origin)

    def test_origin_switch_pins_current_room(self):
        cmd = self._cmd(switches=("origin",))
        here = cmd.caller.location
        with patch("commands.CmdCoordSeed.pinned_origin",
                   return_value=None):
            cmd.func()
        here.tags.add.assert_called_once_with(
            "coordseed_origin", category="spatial")

    def test_repin_moves_the_tag(self):
        cmd = self._cmd(switches=("origin",))
        old = MagicMock()
        with patch("commands.CmdCoordSeed.pinned_origin",
                   return_value=old):
            cmd.func()
        old.tags.remove.assert_called_once_with(
            "coordseed_origin", category="spatial")
        cmd.caller.location.tags.add.assert_called_once()
