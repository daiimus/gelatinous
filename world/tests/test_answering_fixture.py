"""Radio-duty stations answer on one standard (#2216).

The competence lives on the FIXTURE; the voice belongs to whoever
holds the chair. `world/radio.py` already states that as law —
"whoever holds the chair holds the voice" — and `DispatchConsole`
implemented it. The crane did not: its parsing lived on Ossie's
typeclass, so the crane answered him and nobody else, forever.

`AnsweringFixture` is that shape extracted, so the crane is the second
INSTANCE rather than the second DESIGN.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaCommandTest

from typeclasses.items import AnsweringFixture


class ProbeStation(AnsweringFixture):
    """A bare station that records what it was asked to handle.

    Not underscore-prefixed: a typeclass is a Django model proxy and
    the name cannot start with one (models.E023).
    """

    def _handle(self, speech, speaker, kwargs):
        self.db.heard = speech


class TestTheStandardGates(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.station = self.obj1
        self.station.swap_typeclass(
            "world.tests.test_answering_fixture.ProbeStation",
            clean_attributes=False, run_start_hooks=None)
        self.station.db.heard = None

    def _hear(self, speech, speaker=None, **kw):
        payload = {"type": "radio", "speech": speech}
        payload.update(kw)
        self.station.at_msg_receive(from_obj=speaker or self.char1, **payload)
        return self.station.db.heard

    def test_a_transmission_reaches_the_handler(self):
        self.assertEqual(self._hear("bring her down"), "bring her down")

    def test_non_radio_traffic_is_ignored(self):
        self.station.at_msg_receive(text="hello", from_obj=self.char1)
        self.assertIsNone(self.station.db.heard)

    def test_silence_is_ignored(self):
        """A static-drowned listener catches no words — nothing to answer."""
        self.assertIsNone(self._hear(None))

    def test_it_never_answers_a_machine(self):
        """Players talk, stations answer. Otherwise the band fills with
        machines replying to each other."""
        for flag in ("is_npc", "llm_driven", "is_base_station"):
            self.station.db.heard = None
            self.char2.attributes.add(flag, True)
            self.assertIsNone(self._hear("bring her down", self.char2), flag)
            self.char2.attributes.remove(flag)

    def test_it_never_answers_itself(self):
        self.assertIsNone(self._hear("echo", self.station))

    def test_a_handler_that_raises_never_breaks_delivery(self):
        with mock.patch.object(ProbeStation, "_handle",
                               side_effect=RuntimeError("boom")):
            self.assertTrue(
                self.station.at_msg_receive(
                    type="radio", speech="x", from_obj=self.char1))


class TestCooldown(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.station = self.obj1
        self.station.swap_typeclass(
            "world.tests.test_answering_fixture.ProbeStation",
            clean_attributes=False, run_start_hooks=None)

    def test_the_first_answer_passes(self):
        self.assertTrue(self.station._cooled_down(now=1000.0))

    def test_a_second_answer_too_soon_is_refused(self):
        self.station._cooled_down(now=1000.0)
        self.assertFalse(self.station._cooled_down(now=1001.0))

    def test_it_reopens_after_the_window(self):
        self.station._cooled_down(now=1000.0)
        later = 1000.0 + AnsweringFixture.ANSWER_COOLDOWN + 0.1
        self.assertTrue(self.station._cooled_down(now=later))


class TestTheVoiceBelongsToTheChair(EvenniaCommandTest):
    """`_answer` re-checks everything at SEND time — the gap between
    hearing and answering is where the interesting failures live."""

    def setUp(self):
        super().setUp()
        self.station = self.obj1
        self.station.swap_typeclass(
            "world.tests.test_answering_fixture.ProbeStation",
            clean_attributes=False, run_start_hooks=None)

    def _sent(self, **patches):
        with mock.patch("world.radio.is_powered", return_value=True), \
             mock.patch("world.radio.transmit") as tx:
            for target, value in patches.items():
                setattr(self.station.db, target, value)
            self.station._answer("copy", speaker=self.char2)
            return tx

    def test_the_operator_is_the_speaker(self):
        tx = self._sent()
        self.assertTrue(tx.called)
        self.assertIs(tx.call_args[0][0], self.char2)

    def test_an_unpowered_station_is_silent(self):
        with mock.patch("world.radio.is_powered", return_value=False), \
             mock.patch("world.radio.transmit") as tx:
            self.station._answer("copy", speaker=self.char2)
        self.assertFalse(tx.called)

    def test_a_wrecked_antenna_is_silent(self):
        """The sabotage seam: no carrier, honestly."""
        antenna = self.obj2
        antenna.db.intact = False
        with mock.patch("world.radio.is_powered", return_value=True), \
             mock.patch("world.radio.transmit") as tx:
            self.station.db.antenna = antenna
            self.station._answer("copy", speaker=self.char2)
        self.assertFalse(tx.called)

    def test_an_operator_downed_mid_reply_does_not_speak(self):
        """Shot between the copy and the answer: the station speaks in
        its own voice, not hers."""
        with mock.patch.object(type(self.char2), "is_dead",
                               return_value=True), \
             mock.patch("world.radio.is_powered", return_value=True), \
             mock.patch("world.radio.transmit") as tx:
            self.station._answer("copy", speaker=self.char2)
        self.assertTrue(tx.called)
        self.assertIs(tx.call_args[0][0], self.station)

    def test_an_empty_chair_speaks_in_the_station_voice(self):
        with mock.patch("world.radio.is_powered", return_value=True), \
             mock.patch("world.radio.transmit") as tx:
            self.station._answer("copy")          # no speaker, no operator
        self.assertIs(tx.call_args[0][0], self.station)
