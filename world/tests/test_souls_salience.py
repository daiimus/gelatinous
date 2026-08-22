"""The world can interrupt a soul (#2228, SOULS_SALIENCE_SPEC).

Every goal a soul could form was derived from its own internal state —
needs, the clock, whether it held a post. `_desired_goal` is a pure
function of the soul, so nothing in the world could put anything in
front of one. And thinking is LOD-gated: a soul with no player nearby
thinks every sixth 30s beat, about three minutes.

Fine for deciding whether you're hungry. Fatal for work whose trigger
arrives from elsewhere — a distress call reaches the dispatcher by
radio from someone who is, by definition, not standing next to her, and
being alone at her desk is exactly what makes her cold.

F.E.A.R., RimWorld and The Sims all draw the same line: the tick is
cost control for ROUTINE decisions, and salient events bypass it.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaCommandTest

from world.souls import salience


class _SoulCase(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.soul = self.char1
        self.soul.tags.add("soul", category="npc_role")


class TestTheInbox(_SoulCase):
    def test_noticing_something_wakes_the_soul(self):
        with mock.patch.object(salience, "delay") as woken:
            self.assertTrue(salience.notice(self.soul, "radio_traffic"))
        woken.assert_called_once()
        self.assertEqual(woken.call_args[0][0], 0)   # next reactor turn

    def test_it_is_not_thought_inline(self):
        """A stimulus raised during radio delivery must not re-enter the
        delivery loop it came from."""
        with mock.patch.object(salience, "delay"), \
             mock.patch.object(salience, "_think_now") as thought:
            salience.notice(self.soul, "radio_traffic")
        thought.assert_not_called()

    def test_pending_reads_without_consuming(self):
        with mock.patch.object(salience, "delay"):
            salience.notice(self.soul, "radio_traffic")
        self.assertEqual(len(salience.pending(self.soul)), 1)
        self.assertEqual(len(salience.pending(self.soul)), 1)

    def test_draining_consumes(self):
        with mock.patch.object(salience, "delay"):
            salience.notice(self.soul, "radio_traffic")
        self.assertEqual(len(salience.drain(self.soul)), 1)
        self.assertEqual(salience.pending(self.soul), [])

    def test_draining_one_kind_leaves_the_rest(self):
        with mock.patch.object(salience, "delay"):
            salience.notice(self.soul, "radio_traffic")
            salience.notice(self.soul, "casualty")
        self.assertEqual(len(salience.drain(self.soul, "radio_traffic")), 1)
        self.assertEqual([s["kind"] for s in salience.pending(self.soul)],
                         ["casualty"])

    def test_the_inbox_is_bounded(self):
        """A soul beside a busy radio must not accumulate forever — and
        the OLDEST goes, because the newest call is the live one."""
        with mock.patch.object(salience, "delay"):
            for i in range(salience.MAX_STIMULI + 5):
                salience.notice(self.soul, "radio_traffic",
                                payload={"n": i})
        items = salience.pending(self.soul)
        self.assertEqual(len(items), salience.MAX_STIMULI)
        self.assertEqual(items[-1]["payload"]["n"],
                         salience.MAX_STIMULI + 4)

    def test_top_band_is_the_most_urgent(self):
        with mock.patch.object(salience, "delay"):
            salience.notice(self.soul, "chatter", band=4)
            salience.notice(self.soul, "gunfire", band=1)
        self.assertEqual(salience.top_band(self.soul), 1)

    def test_an_empty_inbox_has_no_band(self):
        self.assertIsNone(salience.top_band(self.soul))

    def test_a_dead_soul_notices_nothing(self):
        self.assertFalse(salience.notice(None, "radio_traffic"))

    def test_a_burst_costs_one_wake(self):
        """The emergency band is open and somebody will hold the key
        down. A think per transmission would put the reactor budget in
        a stranger's hands; one wake drains the whole inbox."""
        with mock.patch.object(salience, "delay") as woken:
            for _ in range(6):
                salience.notice(self.soul, "radio_traffic")
        woken.assert_called_once()
        self.assertEqual(len(salience.pending(self.soul)), 6)

    def test_the_next_burst_wakes_again(self):
        with mock.patch.object(salience, "delay") as woken:
            salience.notice(self.soul, "radio_traffic")
            salience._think_now(self.soul)          # the wake fires
            salience.notice(self.soul, "radio_traffic")
        self.assertEqual(woken.call_count, 2)


class TestSensingTheRadio(_SoulCase):
    """Only the person SITTING at the board is working it. That is what
    makes an unmanned desk do nothing — not a check for emptiness, just
    nobody there to hear it."""

    def _board(self, band="911MHz"):
        board = self.obj1
        board.location = self.room1
        board.db.is_radio = True
        board.db.is_base_station = True
        board.db.radio_on = True
        board.db.frequency = band
        chair = self.obj2
        chair.location = self.room1
        self.soul.location = self.room1
        self.soul.db.furniture = chair
        return board

    def _sense(self, band="911MHz", speech="shots fired on Volta Street"):
        with mock.patch.object(salience, "delay"):
            return salience.sense_radio(self.soul, speech, self.char2, band)

    def test_seated_at_the_board_she_senses_the_call(self):
        self._board()
        self.assertTrue(self._sense())
        self.assertEqual(salience.pending(self.soul)[0]["kind"],
                         "radio_traffic")

    def test_standing_up_ends_the_shift(self):
        self._board()
        self.soul.db.furniture = None
        self.assertFalse(self._sense())
        self.assertEqual(salience.pending(self.soul), [])

    def test_another_band_is_not_her_board(self):
        self._board(band="88.8")
        self.assertFalse(self._sense(band="911MHz"))

    def test_npc_traffic_is_never_work(self):
        """The witness's own report already carries its dispatch —
        classifying it again double-rolls the same incident."""
        self._board()
        self.char2.db.is_npc = True
        self.assertFalse(self._sense())

    def test_a_player_at_the_desk_holds_the_post(self):
        """The chair is the whole qualification. A player who takes
        dispatch long-term IS the dispatcher — same devices, same
        commands, same job. There is no NPC path and no player path
        (owner ruling, 2026-08-22)."""
        self._board()
        self.soul.tags.remove("soul", category="npc_role")
        self.assertTrue(self._sense())
        self.assertEqual(salience.pending(self.soul)[0]["kind"],
                         "radio_traffic")

    def test_she_senses_the_words_she_caught(self):
        """Degraded traffic dispatches on the fragments that arrived,
        not on what was said."""
        self._board()
        self._sense(speech="…ots fired on V…")
        self.assertEqual(
            salience.pending(self.soul)[0]["payload"]["speech"],
            "…ots fired on V…")


class TestDoingTheWork(_SoulCase):
    def test_the_work_step_judges_the_call(self):
        with mock.patch.object(salience, "delay"):
            salience.notice(self.soul, "radio_traffic",
                            payload={"speech": "shots fired",
                                     "speaker": self.char2, "board": None})
        with mock.patch("world.director.radio_report.consider_radio_report",
                        return_value=True) as considered:
            self.assertEqual(salience.work_stimuli(self.soul), 1)
        considered.assert_called_once()
        self.assertEqual(considered.call_args[0][0], self.soul)  # SHE judges

    def test_the_call_is_consumed(self):
        with mock.patch.object(salience, "delay"):
            salience.notice(self.soul, "radio_traffic", payload={})
        with mock.patch("world.director.radio_report.consider_radio_report",
                        return_value=False):
            salience.work_stimuli(self.soul)
        self.assertEqual(salience.pending(self.soul), [])

    def test_the_outcome_is_stashed_for_the_voice(self):
        """Deterministic first: the units have already moved (or been
        declined) before anything is said about them."""
        with mock.patch.object(salience, "delay"):
            salience.notice(self.soul, "radio_traffic",
                            payload={"speech": "shots fired",
                                     "speaker": self.char2, "board": None})
        with mock.patch("world.director.radio_report.consider_radio_report",
                        return_value=False), \
             mock.patch("world.director.dispatch.units_available",
                        return_value=3):
            salience.work_stimuli(self.soul)
        self.assertEqual(self.soul.ndb.dispatch_verdict["units"], 3)

    def test_a_crashing_call_does_not_end_the_shift(self):
        with mock.patch.object(salience, "delay"):
            salience.notice(self.soul, "radio_traffic", payload={})
        with mock.patch("world.director.radio_report.consider_radio_report",
                        side_effect=RuntimeError("boom")):
            self.assertEqual(salience.work_stimuli(self.soul), 0)

    def test_a_player_does_the_work_without_a_souls_job(self):
        """A player has no `step_job` to drain the inbox, so the wake
        must do the work itself — otherwise the desk would only work
        for NPCs, which is the fork this design refuses."""
        self.soul.tags.remove("soul", category="npc_role")
        with mock.patch.object(salience, "delay"):
            salience.notice(self.soul, "radio_traffic",
                            payload={"speech": "shots fired",
                                     "speaker": self.char2, "board": None})
        with mock.patch("world.director.radio_report.consider_radio_report",
                        return_value=True) as considered:
            salience._think_now(self.soul)
        considered.assert_called_once()
        self.assertEqual(salience.pending(self.soul), [])

    def test_a_player_wake_does_not_run_the_souls_engine(self):
        """Goal arbitration is the souls engine's business; a player
        decides what to do next by deciding."""
        self.soul.tags.remove("soul", category="npc_role")
        with mock.patch.object(salience, "delay"):
            salience.notice(self.soul, "radio_traffic", payload={})
        with mock.patch("world.souls.engine.think") as thought, \
             mock.patch("world.director.radio_report.consider_radio_report",
                        return_value=False):
            salience._think_now(self.soul)
        thought.assert_not_called()

    def test_other_kinds_are_left_for_their_own_handlers(self):
        with mock.patch.object(salience, "delay"):
            salience.notice(self.soul, "casualty")
        salience.work_stimuli(self.soul)
        self.assertEqual(len(salience.pending(self.soul)), 1)
