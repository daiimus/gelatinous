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


class TestAResponderIsNotRetiredByAFailedWalk(_Base):
    """The souls door onto `assign()` writes a `respond` job and returns
    -- no `on_fail`, no timeout -- while the legacy door it replaced has
    two failure exits. And `fault()` sets `soul_job = None` without
    touching this module, so the Assignment stayed in the registry
    marked `en_route` for the life of the process.

    That permanently removed the unit from a FINITE pool:
    `find_responders` and `units_available` both skip assigned units, so
    the desk under-reported its strength and eventually reported none
    available while idle robots stood at post. Travel failure is not
    exotic -- it is the most common job fault in the game, 1,885 in the
    retained log, one soul failing the same route 273 times (#2715).

    Checked on read rather than pushed from `fault()`: the souls layer
    is the driver and the director is a source of work, so jobs.py
    importing this module would invert that.
    """

    def _souled(self, location, goal="respond"):
        npc = _npc(location)
        npc.tags = MagicMock()
        npc.tags.get.return_value = True          # `_has_soul`
        npc.db.soul_job = {"goal": goal, "at": 0, "steps": []} if goal else None
        return npc

    def test_a_soul_running_the_respond_job_is_assigned(self):
        """The pin: a unit actually rolling must stay committed, or the
        desk double-books it."""
        npc = self._souled(_Room("A"))
        amod._ACTIVE[npc] = object()
        self.assertTrue(is_assigned(npc))

    def test_a_soul_whose_job_died_is_released(self):
        """`fault()` sets soul_job to None and tells nobody."""
        npc = self._souled(_Room("A"), goal=None)
        amod._ACTIVE[npc] = object()
        self.assertFalse(is_assigned(npc),
                         "the unit stayed committed to a dead job")

    def test_a_soul_that_moved_on_to_other_work_is_released(self):
        """`respond` is never re-planned -- it has no arm in goal
        arbitration -- so a soul that faults falls back to patrol or
        duty and looks entirely healthy while the director still
        believes it is committed."""
        npc = self._souled(_Room("A"), goal="duty")
        amod._ACTIVE[npc] = object()
        self.assertFalse(is_assigned(npc))

    def test_the_release_clears_the_registry(self):
        """Self-healing: an entry already orphaned is dropped the next
        time anybody asks."""
        npc = self._souled(_Room("A"), goal=None)
        amod._ACTIVE[npc] = object()
        is_assigned(npc)
        self.assertNotIn(npc, amod._ACTIVE)

    def test_an_unassigned_npc_is_still_unassigned(self):
        self.assertFalse(is_assigned(self._souled(_Room("A"))))

    def test_an_unsouled_responder_is_taken_at_its_word(self):
        """The legacy path has its own failure exits, so there is no job
        to inspect and nothing to second-guess."""
        npc = _npc(_Room("A"))
        npc.tags = MagicMock()
        npc.tags.get.return_value = None          # not souled
        amod._ACTIVE[npc] = object()
        self.assertTrue(is_assigned(npc))
