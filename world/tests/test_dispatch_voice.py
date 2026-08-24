"""The voice on the emergency band is HERS (#2223).

The console used to answer for the dispatcher: it classified the
traffic, then ran its own civic-lane prompt and transmitted the reply
with her as the nominal speaker. Two brains were pointed at the same
call, and hers — the one with her memory, her mood, her twenty years —
was the one deliberately muted.

It is the other way round now. The DESK keeps the competence (classify
the call, roll the steel) because that belongs to the chair and any
operator who takes it. The VOICE is the operator's own: she hears the
transmission on her own device and answers through the real `xmit`
command, so an empty, dead or kidnapped desk is silent with nothing
anywhere having to check for it.

Owner ruling (2026-08-22): "I think it's her brain."
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaCommandTest

from typeclasses.llm_npc import LLMNpc


class _DeskCase(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.petra = self.char2
        self.petra.swap_typeclass("typeclasses.llm_npc.LLMNpc",
                                  clean_attributes=False,
                                  run_start_hooks=None)
        self.petra.db.llm_driven = True
        self.seated = True

    def _hear(self, speech, band="911MHz"):
        """Deliver radio traffic to her device and return the reply mock."""
        board = mock.MagicMock() if self.seated else None
        with mock.patch.object(LLMNpc, "_try_llm_reply") as replied, \
             mock.patch.object(LLMNpc, "_dispatch_board",
                               return_value=board), \
             mock.patch("typeclasses.llm_npc.llm_enabled",
                        return_value=True), \
             mock.patch("typeclasses.llm_npc.delay",
                        side_effect=lambda _t, fn, *a, **kw: fn(*a, **kw)):
            self.petra._hear_radio(speech, self.char1,
                                   {"radio_frequency": band})
        return replied


class TestSheTakesTheBand(_DeskCase):
    def test_hearing_does_not_answer_on_a_timer(self):
        """The reply is CAUSED by the verdict, not raced against it.

        It used to be scheduled here on a flat 1.5s beat, which was
        grounded only when the deterministic classifier happened to
        match; on the model path the verdict landed at ~4s, after the
        prompt was built, and she asked "are you reporting an assault?"
        with two units already rolling (#2238)."""
        replied = self._hear("shots fired on Volta Street")
        self.assertFalse(replied.called)

    def test_the_traffic_is_still_heard(self):
        """Observed either way — the band colours her next turn."""
        self._hear("shots fired on Volta Street")
        self.assertTrue(self.petra.ndb.action_buffer)

    def test_answering_takes_a_radio_turn(self):
        """What the souls layer calls once it knows what it did."""
        with mock.patch.object(LLMNpc, "_try_llm_reply") as replied, \
             mock.patch("typeclasses.llm_npc.delay",
                        side_effect=lambda _t, fn, *a, **kw: fn(*a, **kw)):
            self.petra.answer_traffic("shots fired", self.char1)
        self.assertTrue(replied.called)
        self.assertEqual(replied.call_args[0][2], "radio")

    def test_she_knows_what_she_did_before_she_speaks(self):
        """The regression that started this: whatever order the verdict
        arrives in, the board is stamped before she opens her mouth."""
        from world.souls import salience
        seen = {}
        self.petra.answer_traffic = lambda speech, speaker: seen.update(
            board=self.petra.ndb.dispatch_verdict)
        self.petra.ndb.soul_stimuli = [
            {"kind": "radio_traffic", "band": 2,
             "payload": {"speech": "shots fired", "speaker": self.char1,
                         "board": None}}]
        with mock.patch("world.director.radio_report.consider_radio_report",
                        return_value=False), \
             mock.patch("world.director.dispatch.units_available",
                        return_value=2):
            salience.work_stimuli(self.petra)
        self.assertIsNotNone(seen.get("board"))
        self.assertEqual(seen["board"]["units"], 2)

    def test_another_band_is_not_the_desk(self):
        """Off-shift, carrying a radio on the house band, she is just a
        person on a band — the desk branch must not claim it."""
        replied = self._hear("anyone there?", band="88.8")
        if replied.called:
            self.assertNotEqual(replied.call_args[0][2], "radio")

    def test_out_of_the_chair_she_is_not_the_desk(self):
        """No flag on anybody — the seat is the whole qualification, so
        a dispatcher who stood up falls back to the ordinary NPC rules
        and answers on a timer like everyone else."""
        self.seated = False
        replied = self._hear("shots fired on Volta Street")
        if replied.called:
            self.assertEqual(replied.call_args[0][2], "radio_ambient")

    def test_npc_traffic_never_starts_a_turn(self):
        """The loop guard outranks the desk: witness bots and unit
        chatter must not pull her brain, or the band ping-pongs."""
        self.char1.db.is_npc = True
        replied = self._hear("shots fired on Volta Street")
        self.assertFalse(replied.called)


class TestTheBoardGroundsHer(_DeskCase):
    """What the desk did reaches the model as narration, never as a
    decision — the units moved (or didn't) before she opens her mouth."""

    def _line(self, verdict, dispatched=0, units=3):
        self.petra.ndb.dispatch_verdict = {
            "units": units, "verdict": verdict, "dispatched": dispatched}
        return self.petra._dispatch_board_line()

    def test_units_rolling_forbids_announcing_them(self):
        line = self._line({"is_incident_report": True,
                           "incident_type": "assault",
                           "location_text": "Volta Street"}, dispatched=2)
        self.assertIn("2 unit(s) are already rolling", line)
        self.assertIn("Volta Street", line)
        self.assertIn("do NOT announce them", line)

    def test_nothing_sent_forbids_claiming_a_response(self):
        line = self._line({"is_incident_report": True,
                           "incident_type": "fire",
                           "location_text": ""}, dispatched=0)
        self.assertIn("no new units went out", line)
        self.assertIn("Do not claim anyone is responding", line)

    def test_chatter_grants_nothing(self):
        line = self._line(None)
        self.assertIn("not a report of anything", line)
        self.assertIn("nothing granted or fetched", line)

    def test_every_call_overwrites_the_last(self):
        """Stale grounding is worse than none. It is NOT cleared on read
        — the reply comes back after the prompt is built, and the desk
        discipline still needs to know whether the units claim she just
        wrote was true — so freshness rests on every call overwriting."""
        self._line({"is_incident_report": True, "incident_type": "assault",
                    "location_text": ""}, dispatched=1)
        line = self._line(None)
        self.assertIn("not a report of anything", line)

    def test_a_described_suspect_reaches_the_desk(self):
        """The caller said "a tall heavyset guy"; the units got the
        silhouette and the DESK was told "no description of anyone",
        because the board never carried it (#2249)."""
        self.petra.ndb.dispatch_verdict = {
            "units": 3, "dispatched": 2,
            "verdict": {"is_incident_report": True,
                        "incident_type": "assault",
                        "location_text": "The Kettle - Entrance"},
            "suspect": {"bolo": {"uid": None, "height": "tall",
                                 "build": "heavyset"},
                        "text": "a tall heavyset guy is stabbing someone",
                        "anonymous": False},
        }
        line = self.petra._dispatch_board_line()
        self.assertIn("tall heavyset guy", line)
        self.assertNotIn("no description", line)

    def test_an_anonymous_report_still_says_so(self):
        self.petra.ndb.dispatch_verdict = {
            "units": 3, "dispatched": 2,
            "verdict": {"is_incident_report": True,
                        "incident_type": "assault", "location_text": ""},
            "suspect": {"bolo": None, "text": "someone's stabbing a man",
                        "anonymous": True},
        }
        line = self.petra._dispatch_board_line()
        self.assertIn("described NOBODY", line)

    def test_no_verdict_is_no_line(self):
        self.petra.ndb.dispatch_verdict = None
        self.assertIsNone(self.petra._dispatch_board_line())


class TestHerRegister(EvenniaCommandTest):
    """The channel discipline that lived in the console's instruction
    block is a real archetype now, so it rides her persona."""

    def test_the_dispatcher_archetype_exists(self):
        from world.llm.prompt import ARCHETYPES
        self.assertIn("dispatcher", ARCHETYPES)

    def test_her_persona_uses_it(self):
        from world.llm.personas import DISPATCH_OPERATOR_PERSONA
        self.assertEqual(DISPATCH_OPERATOR_PERSONA["archetype"], "dispatcher")

    def test_she_is_granted_the_radio_tool(self):
        """Without it she has no way to reach the air at all."""
        from world.llm.prompt import tool_names
        from world.llm.personas import DISPATCH_OPERATOR_PERSONA
        self.assertIn("radio", tool_names(
            {"persona_seed": DISPATCH_OPERATOR_PERSONA}))

    def test_she_is_told_not_to_announce_units(self):
        """The single guard that mattered most in the old register: units
        announce themselves, the copy is hers."""
        from world.llm.prompt import ARCHETYPES
        duties = ARCHETYPES["dispatcher"]["duties"].lower()
        self.assertIn("never say units are rolling", duties)
        self.assertIn("never promise to go anywhere", duties)
