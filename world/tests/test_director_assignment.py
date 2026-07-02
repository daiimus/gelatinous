"""Tests for the dispatch assignment lifecycle — en route → on scene
(role-keyed arrival handler) → linger → return to post → done."""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

from world.director import WorldEvent
from world.director import assignment as amod
from world.director.assignment import (
    ARRIVAL_HANDLERS,
    active_assignments,
    assign,
    clear_assignment,
    get_assignment,
    is_assigned,
    register_arrival_handler,
    resolve,
)


class _Room:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name


class _Npc:
    """Hashable NPC stand-in (SimpleNamespace is unhashable and the
    assignment registry keys on the NPC object, as real typeclasses do)."""

    def __init__(self, location, role="security"):
        self.location = location
        self.ndb = SimpleNamespace()
        self.db = SimpleNamespace(role=role)
        self.execute_cmd = MagicMock()


def _npc(location, role="security"):
    return _Npc(location, role=role)


class _Base(TestCase):
    def setUp(self):
        amod._ACTIVE.clear()
        self._saved_handlers = dict(ARRIVAL_HANDLERS)
        ARRIVAL_HANDLERS.clear()

    def tearDown(self):
        amod._ACTIVE.clear()
        ARRIVAL_HANDLERS.clear()
        ARRIVAL_HANDLERS.update(self._saved_handlers)


class TestAssignmentLifecycle(_Base):
    @patch("world.director.assignment.travel_to", return_value=True)
    def test_assign_records_post_and_travels(self, mock_travel):
        post = _Room("post")
        scene = _Room("scene")
        npc = _npc(post)
        self.assertTrue(assign(npc, WorldEvent("assault", scene)))
        a = get_assignment(npc)
        self.assertIsNotNone(a)
        self.assertEqual(a.post, post)
        self.assertEqual(a.state, "en_route")
        self.assertTrue(is_assigned(npc))
        self.assertEqual(len(active_assignments()), 1)
        mock_travel.assert_called_once()
        self.assertEqual(mock_travel.call_args.args[1], scene)

    @patch("world.director.assignment.travel_to", return_value=False)
    def test_unreachable_clears_assignment(self, _t):
        npc = _npc(_Room("post"))
        self.assertFalse(assign(npc, WorldEvent("assault", _Room("scene"))))
        self.assertFalse(is_assigned(npc))

    @patch("world.director.assignment.delay")
    @patch("world.director.assignment.travel_to", return_value=True)
    def test_arrival_runs_default_handler_and_schedules_resolve(
            self, mock_travel, mock_delay):
        npc = _npc(_Room("post"))
        assign(npc, WorldEvent("assault", _Room("scene")))
        on_arrive = mock_travel.call_args.kwargs["on_arrive"]
        on_arrive(npc)  # simulate arrival
        self.assertEqual(get_assignment(npc).state, "on_scene")
        npc.execute_cmd.assert_called_once()          # visible investigate
        mock_delay.assert_called_once()               # linger → resolve

    @patch("world.director.assignment.travel_to", return_value=True)
    def test_arrival_uses_role_handler(self, mock_travel):
        handler = MagicMock()
        register_arrival_handler("security", handler)
        npc = _npc(_Room("post"), role="security")
        assign(npc, WorldEvent("assault", _Room("scene")))
        mock_travel.call_args.kwargs["on_arrive"](npc)
        handler.assert_called_once()
        self.assertEqual(handler.call_args.args[0], npc)

    @patch("world.director.assignment.travel_to", return_value=True)
    def test_broken_handler_still_resolves(self, mock_travel):
        register_arrival_handler("security", MagicMock(side_effect=RuntimeError))
        post = _Room("post")
        npc = _npc(post, role="security")
        assign(npc, WorldEvent("assault", _Room("scene")))
        npc.location = _Room("scene")
        mock_travel.reset_mock()
        # arrival: handler explodes -> resolve() -> travel back to post
        amod._on_scene(npc)
        self.assertEqual(mock_travel.call_args.args[1], post)

    @patch("world.director.assignment.travel_to", return_value=True)
    def test_resolve_travels_back_to_post_then_done(self, mock_travel):
        post = _Room("post")
        npc = _npc(post)
        assign(npc, WorldEvent("assault", _Room("scene")))
        npc.location = _Room("scene")            # it walked there
        mock_travel.reset_mock()
        resolve(npc)
        self.assertEqual(get_assignment(npc).state, "returning")
        self.assertEqual(mock_travel.call_args.args[1], post)
        # simulate arrival back at post
        mock_travel.call_args.kwargs["on_arrive"](npc)
        self.assertFalse(is_assigned(npc))

    @patch("world.director.assignment.travel_to", return_value=True)
    def test_resolve_already_at_post_finishes_immediately(self, mock_travel):
        post = _Room("post")
        npc = _npc(post)
        assign(npc, WorldEvent("assault", _Room("scene")))
        mock_travel.reset_mock()
        resolve(npc)                              # still at post (never left)
        self.assertFalse(is_assigned(npc))
        mock_travel.assert_not_called()

    @patch("world.director.assignment.travel_to", return_value=True)
    def test_reassignment_replaces_previous(self, _t):
        npc = _npc(_Room("post"))
        assign(npc, WorldEvent("assault", _Room("s1")))
        first = get_assignment(npc)
        assign(npc, WorldEvent("fire", _Room("s2")))
        self.assertIsNot(get_assignment(npc), first)
        self.assertEqual(get_assignment(npc).event.type, "fire")
        self.assertEqual(len(active_assignments()), 1)

    @patch("world.director.assignment.travel_to", return_value=True)
    def test_clear_assignment_stands_down(self, _t):
        npc = _npc(_Room("post"))
        assign(npc, WorldEvent("assault", _Room("scene")))
        clear_assignment(npc)
        self.assertFalse(is_assigned(npc))
        self.assertEqual(active_assignments(), [])
