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

    @patch("world.director.assignment.assign", return_value=True)
    @patch("world.director.assignment.is_assigned", return_value=False)
    @patch("world.director.dispatch.find_responders")
    def test_dispatch_sends_severity_count_nearest(self, mock_fr, _ia, mock_assign):
        a, b, c = _npc(_Room("a")), _npc(_Room("b")), _npc(_Room("c"))
        mock_fr.return_value = [(1, a), (2, b), (3, c)]
        sent = dispatch(WorldEvent("assault", _Room("e"), severity=2))
        self.assertEqual(sent, [a, b])  # nearest 2
        self.assertEqual(mock_assign.call_count, 2)

    @patch("world.director.assignment.assign", return_value=True)
    @patch("world.director.assignment.is_assigned")
    @patch("world.director.dispatch.find_responders")
    def test_dispatch_skips_committed_responders(self, mock_fr, mock_ia, _assign):
        a, b, c = _npc(_Room("a")), _npc(_Room("b")), _npc(_Room("c"))
        mock_fr.return_value = [(1, a), (2, b), (3, c)]
        mock_ia.side_effect = lambda npc: npc is a  # nearest is busy
        sent = dispatch(WorldEvent("assault", _Room("e"), severity=2))
        self.assertEqual(sent, [b, c])  # skips the committed one

    @patch("world.director.dispatch.find_responders", return_value=[])
    def test_dispatch_no_responders(self, _fr):
        self.assertEqual(dispatch(WorldEvent("assault", _Room("e"))), [])


class TestDispatchWiring(TestCase):
    def test_dispatch_command_registered(self):
        from commands.default_cmdsets import CharacterCmdSet
        cs = CharacterCmdSet()
        cs.at_cmdset_creation()
        self.assertIn("@dispatch", [c.key for c in cs.commands])


class TestDispatcherAck(TestCase):
    """The dispatcher's voice: deterministic template acks on 911MHz via
    the base's REAL console — no console = no voice (the physical gate)."""

    def _event(self, etype="assault", where="Cobb Street"):
        ev = MagicMock()
        ev.type = etype
        ev.location = MagicMock()
        ev.location.key = where
        return ev

    @patch("evennia.utils.delay")
    def test_units_answer_in_their_own_voices(self, mock_delay):
        from world.director.dispatch import _ack_on_air, _unit_ack
        a, b = MagicMock(), MagicMock()
        a.id, b.id = 3258, 3298
        _ack_on_air(self._event(), [a, b])
        # one staggered ack per unit, each through ITS comms, no console echo
        self.assertEqual(mock_delay.call_count, 2)
        calls = mock_delay.call_args_list
        self.assertEqual([c.args[1] for c in calls], [_unit_ack, _unit_ack])
        self.assertEqual(calls[0].args[2], a)
        self.assertIn("Unit 3258 responding — Cobb Street.", calls[0].args[3])
        self.assertIn("Unit 3298 responding — Cobb Street.", calls[1].args[3])
        self.assertLess(calls[0].args[0], calls[1].args[0])   # net discipline

    def test_unit_ack_rides_the_real_verb(self):
        from world.director.dispatch import _unit_ack
        npc = MagicMock()
        npc.is_dead.return_value = False
        npc.is_unconscious.return_value = False
        _unit_ack(npc, "Unit 1 responding — Cobb Street.")
        npc.execute_cmd.assert_called_once_with(
            "xmit Unit 1 responding — Cobb Street.")

    def test_downed_unit_stays_silent(self):
        from world.director.dispatch import _unit_ack
        npc = MagicMock()
        npc.is_dead.return_value = True
        _unit_ack(npc, "Unit 1 responding — Cobb Street.")
        npc.execute_cmd.assert_not_called()

    @patch("evennia.utils.delay")
    def test_drained_pool_is_announced(self, mock_delay):
        # 'No units available' on a scanner = the finite pool made audible.
        from world.director.dispatch import _ack_on_air
        _ack_on_air(self._event("disturbance"), [])
        line = mock_delay.call_args.args[2]
        self.assertIn("No units available", line)

    def test_transmit_rides_the_real_console(self):
        from world.director.dispatch import _transmit_ack
        station = MagicMock()
        with patch("world.director.population.get_base_station",
                   return_value=station), \
                patch("world.director.population.get_dispatch_operator",
                      return_value=None), \
                patch("world.radio.transmit") as tx:
            _transmit_ack("Dispatch copies.")
        tx.assert_called_once_with(station, "Dispatch copies.", station,
                                   overt=True)

    def test_ack_is_the_operators_voice_when_present(self):
        # The same words in a smoky rasp: acks attribute to the human at
        # the desk; her absence is audible (automation voice).
        from world.director.dispatch import _transmit_ack
        station, vess = MagicMock(), MagicMock()
        with patch("world.director.population.get_base_station",
                   return_value=station), \
                patch("world.director.population.get_dispatch_operator",
                      return_value=vess), \
                patch("world.radio.transmit") as tx:
            _transmit_ack("Dispatch copies.")
        tx.assert_called_once_with(vess, "Dispatch copies.", station,
                                   overt=True)


    def test_no_console_no_voice(self):
        # Sabotage seam: console gone/off = dispatch has no voice.
        from world.director.dispatch import _transmit_ack
        with patch("world.director.population.get_base_station",
                   return_value=None), \
                patch("world.radio.transmit") as tx:
            _transmit_ack("Dispatch copies.")
        tx.assert_not_called()


class TestDispatchConsoleAnswers(TestCase):
    """The console's answering brain: names-dispatch traffic from players
    gets a civic-LLM line (template fallback structural); NPC traffic and
    unaddressed squawks never do."""

    def _console(self):
        from typeclasses.items import DispatchConsole
        from types import SimpleNamespace
        c = MagicMock(spec=DispatchConsole)
        c.ndb = SimpleNamespace(last_answer=None)
        c.db = SimpleNamespace(is_base_station=True, radio_on=True)
        for m in ("_maybe_answer",):
            setattr(c, m, DispatchConsole._maybe_answer.__get__(
                c, DispatchConsole))
        c.ANSWER_COOLDOWN = DispatchConsole.ANSWER_COOLDOWN
        c.INSTRUCTIONS = DispatchConsole.INSTRUCTIONS
        c.FALLBACK_LINE = DispatchConsole.FALLBACK_LINE
        c._units_available = lambda: 2
        c._clean_reply = lambda text, heard=None: text   # sanitizer has its own suite
        c._operator = lambda: None                       # automation by default
        c.OPERATOR_INSTRUCTIONS = DispatchConsole.OPERATOR_INSTRUCTIONS
        return c

    def _player(self):
        p = MagicMock()
        p.db = SimpleNamespace(is_npc=None, llm_driven=None,
                               is_base_station=None)
        return p

    def _kwargs(self, speech):
        return {"type": "radio", "speech": speech,
                "radio_frequency": "911MHz"}

    def test_addressed_player_traffic_gets_a_civic_line(self):
        c = self._console()
        with patch("world.llm.client.civic_enabled", return_value=True), \
                patch("world.llm.client.request_civic_line") as req, \
                patch("world.radio.radio_voice_handle",
                      return_value="a husky voice"):
            c._maybe_answer(self._player(), self._kwargs(
                "Dispatch, do you copy?"))
        req.assert_called_once()
        prompt = req.call_args.args[1]
        self.assertIn("Units available: 2", prompt)
        self.assertIn("a husky voice", prompt)
        # the reply callback keys the console
        req.call_args.kwargs["on_reply"]("Dispatch copies. Go ahead.")
        c._answer.assert_called_once_with("Dispatch copies. Go ahead.",
                                          speaker=None)

    def test_civic_disabled_falls_back_to_template(self):
        c = self._console()
        with patch("world.llm.client.civic_enabled", return_value=False):
            c._maybe_answer(self._player(), self._kwargs(
                "Dispatch, anyone there?"))
        c._answer.assert_called_once_with(c.FALLBACK_LINE, speaker=None)

    def test_failure_falls_back_to_template(self):
        c = self._console()
        with patch("world.llm.client.civic_enabled", return_value=True), \
                patch("world.llm.client.request_civic_line") as req, \
                patch("world.radio.radio_voice_handle",
                      return_value="a voice"):
            c._maybe_answer(self._player(), self._kwargs("Dispatch?"))
        req.call_args.kwargs["on_fail"]()
        c._answer.assert_called_once_with(c.FALLBACK_LINE, speaker=None)

    def test_npc_traffic_is_never_answered(self):
        # Loop guard: the witness's report names no answer; unit chatter
        # and our own acks likewise.
        c = self._console()
        npc = self._player()
        npc.db.is_npc = True
        with patch("world.llm.client.civic_enabled", return_value=True), \
                patch("world.llm.client.request_civic_line") as req:
            c._maybe_answer(npc, self._kwargs(
                "Someone call it in — trouble near dispatch!"))
        req.assert_not_called()
        c._answer.assert_not_called()

    def test_all_band_traffic_is_answered_even_chatter(self):
        # It's the EMERGENCY band: everything on it is dispatch's traffic.
        # Idle chatter gets channel discipline (register-level), not silence.
        c = self._console()
        with patch("world.llm.client.civic_enabled", return_value=True), \
                patch("world.llm.client.request_civic_line") as req, \
                patch("world.radio.radio_voice_handle",
                      return_value="a voice"):
            c._maybe_answer(self._player(), self._kwargs("Hey there."))
        req.assert_called_once()
        self.assertIn("Hey there.", req.call_args.args[1])

    def test_operator_present_uses_her_register_and_voice(self):
        c = self._console()
        vess = MagicMock()
        c._operator = lambda: vess
        with patch("world.llm.client.civic_enabled", return_value=True), \
                patch("world.llm.client.request_civic_line") as req, \
                patch("world.radio.radio_voice_handle",
                      return_value="a voice"):
            c._maybe_answer(self._player(), self._kwargs(
                "Dispatch, do you copy?"))
        self.assertIs(req.call_args.args[0], c.OPERATOR_INSTRUCTIONS)
        req.call_args.kwargs["on_reply"]("Dispatch. Go ahead.")
        c._answer.assert_called_once_with("Dispatch. Go ahead.",
                                          speaker=vess)

    def test_cooldown_gates_repeat_answers(self):
        c = self._console()
        with patch("world.llm.client.civic_enabled", return_value=False):
            c._maybe_answer(self._player(), self._kwargs("Dispatch, copy?"))
            c._maybe_answer(self._player(), self._kwargs("Dispatch, copy?!"))
        self.assertEqual(c._answer.call_count, 1)   # second inside cooldown


class TestConsoleReplySanitation(TestCase):
    """The civic lane's reply guards (the GM lane's practices, scaled
    down): scaffolding echoes, stage directions, and caller-parroting all
    degrade to the template fallback — never onto the air."""

    def _console(self):
        from typeclasses.items import DispatchConsole
        return DispatchConsole.__new__(DispatchConsole)

    def test_scaffolding_echo_rejected(self):
        # The literal 19:15 misfire, on tape in the radio log.
        c = self._console()
        bad = ('Units available: 5. Radio traffic from an unfamiliar '
               'voice: "How\'s your day going?" [Radio traffic is dead.]')
        self.assertEqual(c._clean_reply(bad, heard="How's your day going?"),
                         c.FALLBACK_LINE)

    def test_caller_parrot_rejected(self):
        c = self._console()
        self.assertEqual(
            c._clean_reply("Copy, how's your day going?",
                           heard="How's your day going?"),
            c.FALLBACK_LINE)

    def test_legitimate_restatement_passes(self):
        c = self._console()
        good = "Copy, shots fired on Volta Street. Units responding."
        self.assertEqual(
            c._clean_reply(good, heard="Dispatch, shots fired on Volta Street!"),
            good)

    def test_stage_directions_and_labels_stripped(self):
        c = self._console()
        self.assertEqual(
            c._clean_reply('Dispatch: "Copy. Go ahead." [static]',
                           heard="hello dispatch"),
            "Copy. Go ahead.")

    def test_empty_or_overlong_falls_back(self):
        c = self._console()
        self.assertEqual(c._clean_reply("", heard="x"), c.FALLBACK_LINE)
        self.assertEqual(c._clean_reply("y" * 300, heard="x"),
                         c.FALLBACK_LINE)
