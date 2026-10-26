"""#2585: every refusal `xmit` gives carries ``type="refusal"`` — the line a
player reads, the line an NPC's receive hook hears. A transmission that goes
out carries no such tag. Command-side; the brain side is in test_llm_npc.
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from commands.CmdRadio import CmdTransmit
from world.radio import REFUSAL, transmit, transmit_organ


def _radio(on=True, freq="447"):
    r = MagicMock()
    r.db.is_radio = True
    r.db.radio_on = on
    r.db.frequency = freq
    r.get_display_name = lambda looker=None, **k: "the handset"
    return r


def _char(worn=None, hands=None):
    c = MagicMock()
    c.get_worn_items = lambda: (worn or [])
    c.hands = hands or {}
    c.contents = list(worn or []) + list((hands or {}).values())
    c.medical_state = None
    c.location = None
    return c


def _refusals(char):
    return [(call.args[0] if call.args else call.kwargs.get("text"))
            for call in char.msg.call_args_list
            if call.kwargs.get("type") == REFUSAL]


def _xmit(char, line):
    cmd = CmdTransmit()
    cmd.caller = char
    cmd.args = line
    cmd.parse()
    with patch("commands.CmdRadio.refuse_if_channeling", return_value=False, create=True), \
            patch("world.channeled.refuse_if_channeling", return_value=False):
        cmd.func()
    return cmd


class TestTheCommandTagsItsRefusals(TestCase):
    def test_no_radio_worn_or_in_hand(self):
        c = _char()
        _xmit(c, "hello")
        self.assertEqual(len(_refusals(c)), 1)
        self.assertIn("no radio worn or in hand", _refusals(c)[0])

    def test_nothing_to_transmit(self):
        c = _char(worn=[_radio()])
        _xmit(c, "")
        self.assertEqual(_refusals(c), ["Transmit what?"])

    def test_switched_off(self):
        dev = _radio(on=False)
        c = _char(worn=[dev])
        self.assertFalse(transmit(c, "hello", dev))
        self.assertIn("switched off", _refusals(c)[0])

    def test_sweeping(self):
        dev = _radio(freq="scan")
        c = _char(worn=[dev])
        self.assertFalse(transmit(c, "hello", dev))
        self.assertIn("sweeping", _refusals(c)[0])

    def test_not_tuned(self):
        dev = _radio(freq=None)
        c = _char(worn=[dev])
        self.assertFalse(transmit(c, "hello", dev))
        self.assertIn("isn't tuned", _refusals(c)[0])

    def test_no_working_comms_organ(self):
        c = _char()
        self.assertFalse(transmit_organ(c, "hello"))
        self.assertIn("no working comms module", _refusals(c)[0])


class TestAWorkingTransmitIsNotARefusal(TestCase):
    def test_the_echo_carries_no_tag(self):
        dev = _radio()
        c = _char(worn=[dev])
        with patch("world.radio._log_to_channel"), \
                patch("world.radio._mutter_into"), \
                patch("world.radio._deliver"):
            self.assertTrue(transmit(c, "hello", dev))
        self.assertEqual(_refusals(c), [])
        texts = [call.args[0] for call in c.msg.call_args_list if call.args]
        self.assertTrue(any("You transmit on" in t for t in texts))
