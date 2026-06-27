"""Tests for the director's dispatch core — travel state machine,
responder ranking, and severity-scaled dispatch."""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

from world.director import WorldEvent, dispatch, find_responders, travel_to
from world.director.dispatch import ROLE_RESPONDS_TO


class _Room:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name


def _npc(location, name="npc", source=False):
    return SimpleNamespace(location=location, name=name,
                           ndb=SimpleNamespace(), execute_cmd=MagicMock())


# --- travel state machine -----------------------------------------------

class TestTravel(TestCase):
    def test_already_there_fires_arrive(self):
        room = _Room("A")
        on_arrive = MagicMock()
        npc = _npc(room)
        self.assertTrue(travel_to(npc, room, on_arrive=on_arrive))
        on_arrive.assert_called_once_with(npc)
        # no travel state left behind
        self.assertIsNone(getattr(npc.ndb, "director_travel", None))

    @patch("world.director.travel.find_path_exits", return_value=None)
    def test_unreachable_fires_fail(self, _fpe):
        on_fail = MagicMock()
        npc = _npc(_Room("A"))
        self.assertFalse(travel_to(npc, _Room("Z"), on_fail=on_fail))
        on_fail.assert_called_once_with(npc)

    @patch("world.director.travel.delay")
    @patch("world.director.travel.find_path_exits")
    def test_starts_and_walks_first_exit(self, mock_fpe, mock_delay):
        ex = SimpleNamespace(key="north", destination=_Room("B"))
        mock_fpe.return_value = [ex]
        npc = _npc(_Room("A"))
        started = travel_to(npc, _Room("Z"))
        self.assertTrue(started)
        npc.execute_cmd.assert_called_once_with("north")
        self.assertIsNotNone(getattr(npc.ndb, "director_travel", None))
        mock_delay.assert_called_once()  # next step scheduled


# --- responder ranking + dispatch ---------------------------------------

class TestDispatch(TestCase):
    def test_role_table_shape(self):
        self.assertIn("assault", ROLE_RESPONDS_TO)
        self.assertIn("security", ROLE_RESPONDS_TO["assault"])

    @patch("world.director.dispatch.path_length")
    @patch("world.director.dispatch._npcs_with_roles")
    def test_find_responders_ranked_nearest_first(self, mock_npcs, mock_pl):
        near = _npc(_Room("near"), "near")
        far = _npc(_Room("far"), "far")
        unreachable = _npc(_Room("unr"), "unr")
        mock_npcs.return_value = [far, near, unreachable]
        steps = {near.location: 2, far.location: 9, unreachable.location: None}
        mock_pl.side_effect = lambda start, goal, traverser=None: steps[start]

        ranked = find_responders(WorldEvent("assault", _Room("event")))
        self.assertEqual([npc for _s, npc in ranked], [near, far])  # unr dropped

    @patch("world.director.dispatch._npcs_with_roles", return_value=[])
    def test_unknown_event_type_no_responders(self, _m):
        self.assertEqual(find_responders(WorldEvent("picnic", _Room("e"))), [])

    @patch("world.director.dispatch.path_length")
    @patch("world.director.dispatch._npcs_with_roles")
    def test_source_excluded(self, mock_npcs, mock_pl):
        src = _npc(_Room("s"), "src")
        other = _npc(_Room("o"), "other")
        mock_npcs.return_value = [src, other]
        mock_pl.side_effect = lambda start, goal, traverser=None: 1
        ev = WorldEvent("assault", _Room("e"), source=src)
        ranked = find_responders(ev)
        self.assertEqual([npc for _s, npc in ranked], [other])

    @patch("world.director.dispatch.travel_to", return_value=True)
    @patch("world.director.dispatch.find_responders")
    def test_dispatch_sends_severity_count_nearest(self, mock_fr, mock_travel):
        a, b, c = _npc(_Room("a")), _npc(_Room("b")), _npc(_Room("c"))
        mock_fr.return_value = [(1, a), (2, b), (3, c)]
        sent = dispatch(WorldEvent("assault", _Room("e"), severity=2))
        self.assertEqual(sent, [a, b])  # nearest 2
        self.assertEqual(mock_travel.call_count, 2)

    @patch("world.director.dispatch.travel_to", return_value=True)
    @patch("world.director.dispatch.find_responders", return_value=[])
    def test_dispatch_no_responders(self, _fr, _travel):
        self.assertEqual(dispatch(WorldEvent("assault", _Room("e"))), [])


class TestDispatchWiring(TestCase):
    def test_dispatch_command_registered(self):
        from commands.default_cmdsets import CharacterCmdSet
        cs = CharacterCmdSet()
        cs.at_cmdset_creation()
        self.assertIn("@dispatch", [c.key for c in cs.commands])
