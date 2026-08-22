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
    def test_ordinary_traffic_is_her_traffic(self):
        """No address gate on 911: everything said on it is dispatch's.
        Un-addressed traffic used to fall to the ambient volunteer, which
        answers rarely and at random — not a dispatcher."""
        replied = self._hear("shots fired on Volta Street")
        self.assertTrue(replied.called)
        self.assertEqual(replied.call_args[0][2], "radio")

    def test_a_hail_is_her_traffic_too(self):
        replied = self._hear("anyone there?")
        self.assertTrue(replied.called)
        self.assertEqual(replied.call_args[0][2], "radio")

    def test_another_band_is_not_the_desk(self):
        """Off-shift, carrying a radio on the house band, she is just a
        person on a band — the desk branch must not claim it."""
        replied = self._hear("anyone there?", band="88.8")
        if replied.called:
            self.assertNotEqual(replied.call_args[0][2], "radio")

    def test_out_of_the_chair_she_is_not_the_desk(self):
        """No flag on anybody — the seat is the whole qualification, so
        a dispatcher who stood up answers like anybody else."""
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
