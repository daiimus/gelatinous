"""Tests for patrol routines — posts, beats, the heartbeat tick, and the
Patrol→Detect waypoint sweep."""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

from world.director import routines as rmod
from world.director.routines import at_waypoint, get_beat, tick_npc


class _Room:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name


class _Npc:
    def __init__(self, location, role="security", post=None, beat=None):
        self.location = location
        self.db = SimpleNamespace(role=role, post=post, patrol_beat=beat)
        self.ndb = SimpleNamespace()
        self.execute_cmd = MagicMock()


class TestBeat(TestCase):
    def test_post_anchors_the_cycle(self):
        base, a, b = _Room("base"), _Room("a"), _Room("b")
        npc = _Npc(base, post=base, beat=[a, b])
        self.assertEqual(get_beat(npc), [base, a, b])

    def test_post_not_duplicated(self):
        base, a = _Room("base"), _Room("a")
        npc = _Npc(base, post=base, beat=[base, a])
        self.assertEqual(get_beat(npc), [base, a])

    def test_no_beat_no_cycle(self):
        npc = _Npc(_Room("x"))
        self.assertEqual(get_beat(npc), [])


@patch("world.director.routines._in_combat", return_value=False)
@patch("world.director.routines.is_travelling", return_value=False)
@patch("world.director.routines.is_assigned", return_value=False)
class TestTick(TestCase):
    def test_no_beat_none(self, *_m):
        self.assertEqual(tick_npc(_Npc(_Room("x"))), "none")

    def test_busy_skips(self, mock_assigned, *_m):
        base, a = _Room("base"), _Room("a")
        npc = _Npc(base, post=base, beat=[a])
        mock_assigned.return_value = True
        self.assertEqual(tick_npc(npc), "skip")

    @patch("world.director.routines.travel_to")
    def test_walks_to_next_waypoint(self, mock_travel, *_m):
        base, a = _Room("base"), _Room("a")
        npc = _Npc(a, post=base, beat=[a])   # cycle [base, a]; idx 0 -> base
        npc.ndb.patrol_idx = 0               # pin (fresh NPCs stagger randomly)
        self.assertEqual(tick_npc(npc), "travel")
        self.assertEqual(mock_travel.call_args.args[1], base)

    @patch("world.director.routines.at_waypoint")
    def test_arrival_advances_and_sweeps(self, mock_hook, *_m):
        base, a = _Room("base"), _Room("a")
        npc = _Npc(base, post=base, beat=[a])  # at waypoint 0 (base)
        npc.ndb.patrol_idx = 0                 # pin (fresh NPCs stagger randomly)
        self.assertEqual(tick_npc(npc), "waypoint")
        self.assertEqual(npc.ndb.patrol_idx, 1)
        mock_hook.assert_called_once_with(npc)


class TestWaypointSweep(TestCase):
    @patch("world.director.security._scan_wanted")
    @patch("world.director.dispatch.raise_event")
    def test_wanted_face_raises_disturbance(self, mock_raise, mock_scan):
        felon = MagicMock(name="felon")
        mock_scan.return_value = ("UID", felon, {"count": 1})
        npc = _Npc(_Room("corner"), role="security")
        at_waypoint(npc)
        event = mock_raise.call_args.args[0]
        self.assertEqual(event.type, "disturbance")
        self.assertIs(event.source, felon)
        self.assertEqual(event.location, npc.location)

    @patch("world.director.security._scan_wanted",
           return_value=(None, None, None))
    @patch("world.director.dispatch.raise_event")
    def test_clean_sweep_just_emotes(self, mock_raise, _scan):
        npc = _Npc(_Room("corner"), role="security")
        at_waypoint(npc)
        mock_raise.assert_not_called()
        npc.execute_cmd.assert_called_once()

    def test_non_security_no_sweep(self):
        npc = _Npc(_Room("corner"), role="miner")
        at_waypoint(npc)
        npc.execute_cmd.assert_not_called()


class TestPostedAssignments(TestCase):
    @patch("world.director.assignment.travel_to", return_value=True)
    def test_assignment_returns_to_the_base_not_the_spot(self, _t):
        from world.director import assignment as amod
        from world.director.assignment import assign, get_assignment

        class _Char:
            def __init__(self):
                self.location = _Room("street corner")
                self.db = SimpleNamespace(post=_Room("precinct"), role="security")
                self.ndb = SimpleNamespace()

        amod._ACTIVE.clear()
        npc = _Char()
        event = SimpleNamespace(location=_Room("scene"), type="assault",
                                payload={})
        self.assertTrue(assign(npc, event))
        self.assertEqual(get_assignment(npc).post.name, "precinct")
        amod._ACTIVE.clear()


class TestWiring(TestCase):
    def test_patrol_command_registered(self):
        from commands.default_cmdsets import CharacterCmdSet
        cs = CharacterCmdSet()
        cs.at_cmdset_creation()
        self.assertIn("@patrol", [c.key for c in cs.commands])
