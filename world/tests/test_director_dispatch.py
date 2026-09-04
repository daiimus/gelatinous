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
        room_a = _Room("A")
        # the walker checks route[0].location to decide whether to
        # re-path, so a mock exit needs the room it hangs in
        ex = SimpleNamespace(key="north", destination=_Room("B"),
                             location=room_a)
        mock_fpe.return_value = [ex]
        npc = _npc(room_a)
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

    @patch("world.director.dispatch.hears_emergency_band", return_value=True)
    @patch("world.director.dispatch.path_length")
    @patch("world.director.dispatch._npcs_with_roles")
    def test_find_responders_ranked_nearest_first(self, mock_npcs, mock_pl, _hb):
        near = _npc(_Room("near"), "near")
        far = _npc(_Room("far"), "far")
        unreachable = _npc(_Room("unr"), "unr")
        mock_npcs.return_value = [far, near, unreachable]
        steps = {near.location: 2, far.location: 9, unreachable.location: None}
        mock_pl.side_effect = lambda start, goal, traverser=None: steps[start]

        ranked = find_responders(WorldEvent("assault", _Room("event")))
        self.assertEqual([npc for _s, npc in ranked], [near, far])  # unr dropped

    @patch("world.director.dispatch.hears_emergency_band")
    @patch("world.director.dispatch.path_length")
    @patch("world.director.dispatch._npcs_with_roles")
    def test_deafened_unit_is_unreachable(self, mock_npcs, mock_pl, mock_hb):
        # dispatch orders are radio traffic: shoot the ear and the unit
        # stands at post — never selected, never rolls
        hearing = _npc(_Room("h"), "hearing")
        deaf = _npc(_Room("d"), "deaf")
        mock_npcs.return_value = [deaf, hearing]
        mock_pl.side_effect = lambda start, goal, traverser=None: 1
        mock_hb.side_effect = lambda npc: npc is hearing
        ranked = find_responders(WorldEvent("assault", _Room("event")))
        self.assertEqual([npc for _s, npc in ranked], [hearing])

    @patch("world.director.dispatch._npcs_with_roles", return_value=[])
    def test_unknown_event_type_no_responders(self, _m):
        self.assertEqual(find_responders(WorldEvent("picnic", _Room("e"))), [])

    @patch("world.director.dispatch.hears_emergency_band", return_value=True)
    @patch("world.director.dispatch.path_length")
    @patch("world.director.dispatch._npcs_with_roles")
    def test_source_excluded(self, mock_npcs, mock_pl, _hb):
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


class TestEveryCrimeRollsSomebody(TestCase):
    """Every registered crime must reach a responder (#2781).

    `report_crime` types the event with the SPECIFIC crime
    ("shoplifting", "murder"), while `ROLE_RESPONDS_TO` was keyed on a
    different vocabulary — so seven of eight resolved to no role and
    `find_responders` returned `[]`. That is indistinguishable from
    "every unit is busy", which is why five idle units and an unanswered
    murder looked identical from the desk.

    Pinned as a JOIN over `CRIME_SEVERITY` rather than a list of types:
    a crime added there without a responder route fails here instead of
    silently never dispatching.
    """

    @patch("world.director.dispatch.hears_emergency_band", return_value=True)
    @patch("world.director.dispatch.path_length", return_value=3)
    @patch("world.director.dispatch._npcs_with_roles")
    def test_every_crime_type_finds_a_responder(self, mock_npcs, _pl, _hb):
        from world.director.crime import CRIME_SEVERITY
        unit = _npc(_Room("post"), "unit")
        mock_npcs.return_value = [unit]
        for crime in CRIME_SEVERITY:
            with self.subTest(crime=crime):
                ranked = find_responders(
                    WorldEvent(crime, _Room("scene")))
                self.assertEqual(
                    [n for _s, n in ranked], [unit],
                    f"{crime!r} dispatches nobody",
                )

    def test_severity_is_the_star_rating(self):
        """A bigger crime rolls more units — `dispatch` sends
        `max(1, severity)`, so the rating lives in CRIME_SEVERITY."""
        from world.director.crime import CRIME_SEVERITY
        self.assertEqual(CRIME_SEVERITY["shoplifting"], 1)
        self.assertEqual(CRIME_SEVERITY["assault"], 2)
        self.assertEqual(CRIME_SEVERITY["murder"], 3)


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

    def test_the_ack_rides_her_own_xmit(self):
        """The same verb a responding unit uses, and the same one a
        player would — no privileged path for the desk (#2228)."""
        from world.director.dispatch import _transmit_ack
        operator = MagicMock()
        operator.is_dead.return_value = False
        operator.is_unconscious.return_value = False
        with patch("world.director.population.get_dispatch_operator",
                   return_value=operator):
            _transmit_ack("Dispatch copies.")
        operator.execute_cmd.assert_called_once_with("xmit Dispatch copies.")

    def test_an_unattended_desk_acknowledges_nothing(self):
        """No automation voice. The colony is operated by its people,
        and an unmanned emergency line is the setting rather than a
        hole in it (owner ruling, 2026-08-22)."""
        from world.director.dispatch import _transmit_ack
        with patch("world.director.population.get_dispatch_operator",
                   return_value=None), \
                patch("world.radio.transmit") as tx:
            _transmit_ack("Dispatch copies.")
        tx.assert_not_called()

    def test_a_downed_operator_says_nothing(self):
        """Dragged off the desk between the event and the ack."""
        from world.director.dispatch import _transmit_ack
        operator = MagicMock()
        operator.is_dead.return_value = True
        with patch("world.director.population.get_dispatch_operator",
                   return_value=operator):
            _transmit_ack("Dispatch copies.")
        operator.execute_cmd.assert_not_called()

    def test_a_wrecked_console_still_silences_her(self):
        """The sabotage seam survives the move, but it is the COMMAND
        that enforces it now: no console under her means no transmit
        device, and `xmit` refuses exactly as it would for a player.
        One rule instead of a second explicit check."""
        from world.radio import active_transmit_radio
        operator = MagicMock()
        operator.get_worn_items = lambda: []
        operator.hands = {}
        operator.contents = []
        operator.db.furniture = None          # not at any board
        self.assertIsNone(active_transmit_radio(operator))


class TestTheDeskDiscipline(TestCase):
    """What a dispatcher cannot say, whatever the model wrote.

    These two are playtest scars, not theory (2026-07-11). They used to
    live in `DispatchConsole._clean_reply`, back when the furniture did
    the talking; they belong to the JOB, so they moved with it and now
    guard whoever holds the chair (#2228).
    """

    def test_phantom_units_are_struck(self):
        from world.director.dispatch import DESK_FALLBACK_LINES, desk_discipline
        line = desk_discipline("Copy. Units rolling to Recyc.",
                               units_moved=False)
        self.assertIn(line, DESK_FALLBACK_LINES)

    def test_a_true_units_claim_becomes_the_plain_copy(self):
        """Units DID roll — but announcing them is theirs to do."""
        from world.director.dispatch import DESK_REPORT_ACK, desk_discipline
        self.assertEqual(
            desk_discipline("Copy, two units responding to Volta.",
                            units_moved=True),
            DESK_REPORT_ACK)

    def test_promising_to_leave_the_desk_is_struck(self):
        from world.director.dispatch import DESK_FALLBACK_LINES, desk_discipline
        for promise in ("I'll be there in a minute.",
                        "On my way, caller.",
                        "I'll come by after my shift."):
            self.assertIn(desk_discipline(promise), DESK_FALLBACK_LINES,
                          promise)

    def test_an_ordinary_line_is_untouched(self):
        from world.director.dispatch import desk_discipline
        good = "Copy, shots fired on Volta. Keep your head down out there."
        self.assertEqual(desk_discipline(good), good)

    def test_no_units_available_is_not_a_units_claim(self):
        """Saying she has nobody to send is the honest opposite."""
        from world.director.dispatch import desk_discipline
        line = "Copy, docks. No units available."
        self.assertEqual(desk_discipline(line), line)

    def test_nothing_in_nothing_out(self):
        from world.director.dispatch import desk_discipline
        self.assertIsNone(desk_discipline(""))
        self.assertIsNone(desk_discipline(None))


class TestTheReportLaneNeedsAnOperator(TestCase):
    """No operator, no dispatch (#2228).

    `consider_radio_report` used to hang off the console's
    `at_msg_receive`, so an unattended desk kept classifying calls and
    rolling the colony's security force with nobody in the chair —
    automation quietly doing the job we had just given an employee. The
    weakness is the setting; it should be structural, not a check.
    """

    def _speaker(self):
        s = MagicMock()
        s.db = SimpleNamespace(is_npc=None, llm_driven=None,
                               is_base_station=None)
        return s

    def test_no_operator_declines(self):
        from world.director.radio_report import consider_radio_report
        with patch("world.director.radio_report.apply_verdict") as applied:
            took = consider_radio_report(None, self._speaker(),
                                         "shots fired on Volta Street")
        self.assertFalse(took)
        applied.assert_not_called()

    def test_an_operator_dispatches(self):
        from world.director.radio_report import consider_radio_report
        with patch("world.director.radio_report.apply_verdict",
                   return_value=[]) as applied:
            took = consider_radio_report(MagicMock(), self._speaker(),
                                         "shots fired on Volta Street")
        self.assertTrue(took)
        applied.assert_called_once()

    def test_npc_traffic_still_never_dispatches(self):
        """The loop guard outranks everything: a witness's own report
        already carries its dispatch."""
        from world.director.radio_report import consider_radio_report
        npc = self._speaker()
        npc.db.is_npc = True
        with patch("world.director.radio_report.apply_verdict") as applied:
            took = consider_radio_report(MagicMock(), npc,
                                         "shots fired on Volta Street")
        self.assertFalse(took)
        applied.assert_not_called()



class TestHearsEmergencyBand(TestCase):
    """The reachability gate: comms organ or powered carried radio on
    the dispatch band."""

    def test_organ_on_band(self):
        from world import radio
        char = SimpleNamespace(contents=[])
        with patch.object(radio, "comms_organ_frequency",
                          return_value="911MHz"):
            self.assertTrue(radio.hears_emergency_band(char))

    def test_powered_carried_radio_on_band(self):
        from world import radio
        walkie = MagicMock()
        walkie.db.is_radio = True
        walkie.db.radio_on = True
        walkie.db.frequency = "911mhz"     # case-insensitive band match
        char = SimpleNamespace(contents=[walkie])
        with patch.object(radio, "comms_organ_frequency",
                          return_value=None):
            self.assertTrue(radio.hears_emergency_band(char))

    def test_deaf_unit_unreachable(self):
        from world import radio
        off = MagicMock()
        off.db.is_radio = True
        off.db.radio_on = False           # dead set doesn't count
        off.db.frequency = "911MHz"
        wrong = MagicMock()
        wrong.db.is_radio = True
        wrong.db.radio_on = True
        wrong.db.frequency = "88.8MHz"    # house band isn't dispatch
        char = SimpleNamespace(contents=[off, wrong])
        with patch.object(radio, "comms_organ_frequency",
                          return_value=None):
            self.assertFalse(radio.hears_emergency_band(char))
