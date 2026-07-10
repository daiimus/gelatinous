"""NPC radio comprehension (RADIO_COMMS_SPEC §7).

Radio reaches the LLM brain as heard-over-the-air words (say-rails speech
payload), gated like room speech: named → answer; "all units" → only the
elected unit; NPC-sourced → observe-only (the loop guard); chatter → buffer +
rare volunteer. Transmit rides the real ``xmit`` command, with the built-in
comms organ as the command's own no-handheld fallback.
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

import typeclasses.llm_npc as llmnpc
import world.radio as radio
from world.radio import transmit, transmit_organ


def _bind(b, name):
    setattr(b, name,
            getattr(llmnpc.LLMNpcMixin, name).__get__(b, llmnpc.LLMNpcMixin))


def _radio(on=True, freq="447", holder=None, holder_id=1):
    r = MagicMock()
    r.db.is_radio = True
    r.db.radio_on = on
    r.db.frequency = freq
    listener = MagicMock()
    listener.id = holder_id
    listener.db.llm_driven = False
    r.location = holder if holder is not None else listener
    return r


def _speaker():
    c = MagicMock()
    c.get_worn_items = lambda: []
    c.hands = {}
    c.contents = []
    return c


class TestDeliveryPayload(TestCase):
    def _tx(self, listeners_radios, message="unit 7, report in"):
        speaker = _speaker()
        dev = _radio(freq="447")
        dev.location = speaker
        with patch.object(radio, "_all_powered_radios",
                          return_value=[dev] + listeners_radios), \
                patch.object(radio, "_comms_bots_on", return_value=[]), \
                patch.object(radio, "_log_to_channel"), \
                patch("world.perception.can_hear", return_value=True), \
                patch("world.voice.attempt_voice_discern", return_value=None), \
                patch("world.voice.get_voice_description", return_value="flat"), \
                patch("world.voice.voice_phrase", return_value=None):
            transmit(speaker, message, dev)

    def test_hearing_listener_gets_speech_payload(self):
        heard = _radio(freq="447")
        self._tx([heard], "rendezvous at the docks")
        kwargs = heard.location.msg.call_args.kwargs
        self.assertEqual(kwargs["speech"], "rendezvous at the docks")
        self.assertEqual(kwargs["type"], "radio")
        self.assertEqual(kwargs["radio_frequency"], "447")

    def test_deaf_listener_gets_no_words(self):
        speaker = _speaker()
        dev = _radio(freq="447"); dev.location = speaker
        heard = _radio(freq="447")
        with patch.object(radio, "_all_powered_radios",
                          return_value=[dev, heard]), \
                patch.object(radio, "_comms_bots_on", return_value=[]), \
                patch.object(radio, "_log_to_channel"), \
                patch("world.perception.can_hear", return_value=False):
            transmit(speaker, "secret", dev)
        kwargs = heard.location.msg.call_args.kwargs
        self.assertNotIn("speech", kwargs)   # static, no content to react to

    def test_exactly_one_llm_listener_is_elected(self):
        a, b = _radio(freq="447", holder_id=10), _radio(freq="447", holder_id=20)
        a.location.db.llm_driven = True
        b.location.db.llm_driven = True
        self._tx([a, b])
        elected = [r.location.msg.call_args.kwargs["radio_elected"]
                   for r in (a, b)]
        self.assertEqual(sorted(elected), [False, True])
        # deterministic: the lowest id answers
        self.assertTrue(a.location.msg.call_args.kwargs["radio_elected"])


class TestTransmitOrgan(TestCase):
    def test_intact_organ_transmits(self):
        bot = _speaker()
        with patch.object(radio, "comms_organ_frequency",
                          return_value="911MHz"), \
                patch.object(radio, "_log_to_channel"), \
                patch.object(radio, "_deliver") as deliver:
            self.assertTrue(transmit_organ(bot, "unit responding"))
        deliver.assert_called_once_with(bot, "unit responding", "911MHz", None)

    def test_no_organ_refuses(self):
        char = _speaker()
        with patch.object(radio, "comms_organ_frequency", return_value=None):
            self.assertFalse(transmit_organ(char, "hello?"))
        self.assertIn("no working comms", char.msg.call_args.args[0])

    def test_xmit_command_falls_back_to_organ(self):
        from commands.CmdRadio import CmdTransmit
        cmd = CmdTransmit()
        caller = MagicMock()
        caller.get_worn_items = lambda: []
        caller.hands = {}
        cmd.caller = caller
        cmd.args = "unit responding, en route"
        cmd.parse()
        with patch("world.radio.comms_organ_frequency",
                   return_value="911MHz"), \
                patch("world.radio.transmit_organ") as org:
            cmd.func()
        org.assert_called_once_with(caller, "unit responding, en route")


class TestHearRadio(TestCase):
    def _npc(self, elected=False, llm=True):
        b = MagicMock()
        b.key = "Unit 7"
        b.sdesc_keyword = None
        b.db.llm_driven = llm
        b.ndb.action_buffer = None
        b._is_npc_speaker = lambda s: False
        b._radio_voice_handle = lambda s: "a flat voice"
        b._name_aliases = lambda: []
        # class constant — a bare MagicMock would swallow it into a Mock
        b._RADIO_BROADCAST_PHRASES = llmnpc.LLMNpcMixin._RADIO_BROADCAST_PHRASES
        for m in ("_hear_radio", "_observe_action", "_mentions_self"):
            _bind(b, m)
        return b

    def _kwargs(self, elected=False):
        return {"type": "radio", "radio_frequency": "911MHz",
                "radio_elected": elected}

    def test_named_directly_answers(self):
        b = self._npc()
        with patch.object(llmnpc, "llm_enabled", return_value=True), \
                patch.object(llmnpc, "delay") as d:
            b._hear_radio("Unit 7, report in.", MagicMock(), self._kwargs())
        d.assert_called_once()
        self.assertIn("radio", d.call_args.args)      # directed radio mode

    def test_broadcast_only_elected_answers(self):
        with patch.object(llmnpc, "llm_enabled", return_value=True), \
                patch.object(llmnpc, "delay") as d:
            self._npc()._hear_radio("all units, check in.", MagicMock(),
                                    self._kwargs(elected=True))
        d.assert_called_once()
        with patch.object(llmnpc, "llm_enabled", return_value=True), \
                patch.object(llmnpc, "delay") as d2:
            b2 = self._npc()
            b2._hear_radio("all units, check in.", MagicMock(),
                           self._kwargs(elected=False))
        d2.assert_not_called()                         # someone else's call
        self.assertTrue(b2.ndb.action_buffer)          # ...but still heard

    def test_npc_sourced_is_observed_never_answered(self):
        b = self._npc()
        b._is_npc_speaker = lambda s: True             # witness / bot chatter
        with patch.object(llmnpc, "llm_enabled", return_value=True), \
                patch.object(llmnpc, "delay") as d:
            b._hear_radio("Unit 7, trouble on Cobb Street!", MagicMock(),
                          self._kwargs(elected=True))
        d.assert_not_called()                          # the loop guard holds
        self.assertIn('a flat voice said: "Unit 7, trouble on Cobb Street!"',
                      b.ndb.action_buffer[0])

    def test_chatter_buffers_and_volunteers_ambient(self):
        b = self._npc()
        with patch.object(llmnpc, "llm_enabled", return_value=True), \
                patch.object(llmnpc, "delay") as d:
            b._hear_radio("quiet night out there.", MagicMock(),
                          self._kwargs())
        self.assertTrue(b.ndb.action_buffer)           # colours the next turn
        d.assert_called_once()
        self.assertIn("radio_ambient", d.call_args.args)

    def test_deaf_or_brainless_hears_nothing(self):
        b = self._npc()
        with patch.object(llmnpc, "delay") as d:
            b._hear_radio(None, MagicMock(), self._kwargs())   # deaf: no words
        d.assert_not_called()
        self.assertFalse(b.ndb.action_buffer)
        b2 = self._npc(llm=False)
        with patch.object(llmnpc, "delay") as d2:
            b2._hear_radio("hello?", MagicMock(), self._kwargs())
        d2.assert_not_called()

    def test_at_msg_receive_routes_radio(self):
        b = self._npc()
        b._hear_radio = MagicMock()
        _bind(b, "at_msg_receive")
        b.at_msg_receive(text="[447] A flat voice crackles...",
                         from_obj=MagicMock(), type="radio",
                         speech="come in", radio_frequency="447")
        b._hear_radio.assert_called_once()


class TestRadioTool(TestCase):
    def test_registered_and_granted_to_security(self):
        from world.llm.prompt import ARCHETYPES, TOOLS
        self.assertIn("radio", TOOLS)
        self.assertEqual(TOOLS["radio"]["kind"], "action")
        self.assertIn("radio", ARCHETYPES["security"]["tools"])
        self.assertNotIn("radio", ARCHETYPES["colonist"]["tools"])

    def test_tool_routes_to_real_xmit_command(self):
        b = MagicMock()
        _bind(b, "_handle_action_tool")
        b._handle_action_tool("radio", '"Unit responding, en route."',
                              MagicMock())
        b.execute_cmd.assert_called_once_with(
            "xmit Unit responding, en route.")

    def test_radio_turn_framing_is_unambiguous(self):
        from world.llm.prompt import build_messages
        msgs = build_messages({}, "a flat voice", "report in", "radio")
        turn = msgs[-1]["content"]
        self.assertIn("Over your radio", turn)
        self.assertIn("not in the room", turn)
        msgs2 = build_messages({}, "a flat voice", "quiet night",
                               "radio_ambient")
        self.assertIn("Radio chatter", msgs2[-1]["content"])


class TestOperatorObservesNeverReplies(TestCase):
    """The dispatch operator's own brain never radio-replies (the console
    is her radio voice) — but the traffic lands in her buffer, so her
    face-to-face turns know what's been on the band."""

    def test_operator_named_on_air_observes_only(self):
        b = MagicMock()
        b.key = "Vess"
        b.sdesc_keyword = None
        b.db.llm_driven = True
        b.db.dispatch_operator = True
        b.ndb.action_buffer = None
        b._is_npc_speaker = lambda s: False
        b._radio_voice_handle = lambda s: "a husky voice"
        b._name_aliases = lambda: []
        b._RADIO_BROADCAST_PHRASES = llmnpc.LLMNpcMixin._RADIO_BROADCAST_PHRASES
        for m in ("_hear_radio", "_observe_action", "_mentions_self"):
            _bind(b, m)
        with patch.object(llmnpc, "llm_enabled", return_value=True), \
                patch.object(llmnpc, "delay") as d:
            b._hear_radio("Vess, you there?", MagicMock(),
                          {"type": "radio", "radio_frequency": "911MHz",
                           "radio_elected": True})
        d.assert_not_called()                    # no second brain on the air
        self.assertTrue(b.ndb.action_buffer)     # ...but she heard it
        self.assertIn("Vess, you there?", b.ndb.action_buffer[0])
