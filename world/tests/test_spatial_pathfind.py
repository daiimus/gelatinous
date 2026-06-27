"""Tests for the A* exit-graph pathfinder (Phase 2)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase

from world.spatial import (
    find_path,
    find_path_exits,
    is_reachable,
    path_length,
    set_xyz,
)


class _Exit:
    def __init__(self, key, destination, locked=False):
        self.key = key
        self.destination = destination
        self._locked = locked

    def access(self, who, access_type):
        return not self._locked


class _Room:
    def __init__(self, name):
        self.name = name
        self.db = SimpleNamespace(xyz=None)
        self.exits = []

    def __repr__(self):
        return self.name


def _link(a, b, direction, locked=False):
    a.exits.append(_Exit(direction, b, locked=locked))


class TestPathfind(TestCase):
    def _diamond(self):
        # A -E-> B -E-> D  (2 steps)   and   A -N-> X -N-> Y -E-> D (3 steps)
        A, B, D, X, Y = (_Room(n) for n in ("A", "B", "D", "X", "Y"))
        set_xyz(A, 0, 0, 0); set_xyz(B, 1, 0, 0); set_xyz(D, 2, 0, 0)
        set_xyz(X, 0, 1, 0); set_xyz(Y, 0, 2, 0)
        _link(A, B, "east"); _link(B, D, "east")
        _link(A, X, "north"); _link(X, Y, "north"); _link(Y, D, "east")
        return A, B, D, X, Y

    def test_finds_shortest_path(self):
        A, B, D, X, Y = self._diamond()
        path = find_path(A, D)
        self.assertEqual(path, [A, B, D])  # the 2-step branch, not the 3-step
        self.assertEqual(path_length(A, D), 2)

    def test_path_exits_and_directions(self):
        A, B, D, X, Y = self._diamond()
        exits = find_path_exits(A, D)
        self.assertEqual([e.key for e in exits], ["east", "east"])
        self.assertEqual([e.destination for e in exits], [B, D])

    def test_same_room(self):
        A = _Room("A")
        self.assertEqual(find_path(A, A), [A])
        self.assertEqual(find_path_exits(A, A), [])
        self.assertEqual(path_length(A, A), 0)
        self.assertTrue(is_reachable(A, A))

    def test_unreachable(self):
        A, B = _Room("A"), _Room("B")  # no exits between them
        self.assertIsNone(find_path(A, B))
        self.assertIsNone(path_length(A, B))
        self.assertFalse(is_reachable(A, B))

    def test_traverser_routes_around_locked_exit(self):
        # A -E(locked)-> B ; A -N-> C -E-> B. A traverser must detour.
        A, B, C = (_Room(n) for n in "ABC")
        set_xyz(A, 0, 0, 0); set_xyz(B, 1, 0, 0); set_xyz(C, 0, 1, 0)
        _link(A, B, "east", locked=True)
        _link(A, C, "north"); _link(C, B, "east")
        npc = SimpleNamespace(name="npc")
        # No traverser → takes the direct (locked) edge.
        self.assertEqual(find_path(A, B), [A, B])
        # With a traverser the locked edge is skipped → the detour.
        self.assertEqual(find_path(A, B, traverser=npc), [A, C, B])

    def test_off_grid_still_routes(self):
        # No coordinates anywhere → heuristic 0 → Dijkstra, still correct.
        A, B, C = (_Room(n) for n in "ABC")
        _link(A, B, "east"); _link(B, C, "east")
        self.assertEqual(find_path(A, C), [A, B, C])

    def test_max_steps_cutoff(self):
        A, B, C, D = (_Room(n) for n in "ABCD")
        _link(A, B, "east"); _link(B, C, "east"); _link(C, D, "east")
        self.assertIsNone(find_path(A, D, max_steps=2))
        self.assertEqual(find_path(A, D, max_steps=3), [A, B, C, D])


class TestPathWiring(TestCase):
    def test_path_command_registered(self):
        from commands.default_cmdsets import CharacterCmdSet
        cs = CharacterCmdSet()
        cs.at_cmdset_creation()
        self.assertIn("@path", [c.key for c in cs.commands])
