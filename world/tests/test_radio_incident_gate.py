"""Only an EMERGENCY board classifies incidents (#2773).

`sense_radio` gated on "is this board tuned to the band the transmission
came in on" and nothing else. Every band satisfies that, so whoever sat
at ANY base station became an incident classifier for their band.

Its sibling `filter_for_duty`, twenty-five lines below in the same file,
imports EMERGENCY_BAND and checks exactly this. Only one of the two ever
did.

What it cost: 88.8 is the pirate station and talking on it is the
FEATURE. The Rook holds that chair (#6027), is a soul, and so has his
inbox drained by the work loop -- which runs the full incident pipeline
(`describe_suspect`, `units_available`, `consider_radio_report`). A
player keying up to request a track had their words classified for
incident type and severity, and units rolled to wherever the classifier
decided they were. Ossie's crane console on 27.0 is the same shape and
arms the moment he takes the chair.

The loop guard above rejects NPC- and device-sourced traffic by SPEAKER,
so it never covered this: a player speaking is exactly what passes it.
"""
from unittest import TestCase, mock

from world.souls import salience


class _Board:
    def __init__(self, band):
        self.db = type("db", (), {"is_base_station": True})()
        self.band = band


class _Speaker:
    """A player: not an NPC, not llm_driven, not a device."""
    def __init__(self):
        self.db = type("db", (), {"is_npc": None, "llm_driven": None,
                                  "is_base_station": None})()


class TestOnlyTheEmergencyBoardRaisesWork(TestCase):
    def _sense(self, board_band, tx_band):
        board = _Board(board_band)
        with mock.patch("world.radio.seated_base_station",
                        return_value=board), \
             mock.patch("world.radio.frequency_of",
                        return_value=board_band), \
             mock.patch.object(salience, "notice",
                               return_value=True) as noticed:
            salience.sense_radio(object(), "there's a great track",
                                 _Speaker(), tx_band)
        return noticed.called

    def test_the_pirate_station_does_not_dispatch(self):
        """The reported case: the Rook's board on 88.8."""
        self.assertFalse(self._sense("88.8MHz", "88.8MHz"),
                         "a track request was classified as an incident")

    def test_the_crane_console_does_not_dispatch(self):
        """Same shape, arms when Ossie takes the chair."""
        self.assertFalse(self._sense("27.0MHz", "27.0MHz"))

    def test_the_emergency_board_still_dispatches(self):
        """The pin: this is the whole point of the mechanism (#2228) and
        must keep working."""
        self.assertTrue(self._sense("911MHz", "911MHz"),
                        "the dispatch desk stopped hearing emergencies")

    def test_a_board_on_a_different_band_than_the_transmission_is_deaf(self):
        """The original check, still enforced — an emergency board does
        not classify traffic from another band."""
        self.assertFalse(self._sense("911MHz", "88.8MHz"))


class TestTheSpeakerGuardIsUnchanged(TestCase):
    def _sense_from(self, **speaker_flags):
        board = _Board("911MHz")
        speaker = _Speaker()
        for k, v in speaker_flags.items():
            setattr(speaker.db, k, v)
        with mock.patch("world.radio.seated_base_station",
                        return_value=board), \
             mock.patch("world.radio.frequency_of", return_value="911MHz"), \
             mock.patch.object(salience, "notice",
                               return_value=True) as noticed:
            salience.sense_radio(object(), "a report", speaker, "911MHz")
        return noticed.called

    def test_npc_traffic_still_raises_nothing(self):
        self.assertFalse(self._sense_from(is_npc=True))

    def test_device_traffic_still_raises_nothing(self):
        self.assertFalse(self._sense_from(is_base_station=True))

    def test_a_player_on_the_emergency_band_still_raises_work(self):
        self.assertTrue(self._sense_from())
