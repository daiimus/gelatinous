"""Radio range, Phase 2 (RADIO_COMMS_SPEC, decided 2026-07-10).

Distance from live coordinates; falloff rendered through the mutter
letter-drop machinery (crisp → fragments → static wash → silence);
base stations with intact masts are one-hop repeaters; elevation adds
reach; anything off-grid fails open.
"""

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

import world.radio as radio
from world.radio import (
    MAST_TX_RANGE, RADIO_TX_RANGE, RANGE_ELEVATION_BONUS,
    _chebyshev, _clarity_for_fraction, _effective_tx_range,
    _reception_fraction,
)


def _room(x, y, z=0):
    room = MagicMock()
    room.db = SimpleNamespace(xyz=(x, y, z))
    room.location = None
    return room


def _radio_at(room, base_station=False, antenna=None, tx_range=None,
              freq="911MHz"):
    r = MagicMock()
    r.db = SimpleNamespace(is_radio=True, radio_on=True, frequency=freq,
                           is_base_station=base_station, antenna=antenna,
                           tx_range=tx_range)
    r.location = room
    return r


def _mast(intact=True):
    m = MagicMock()
    m.db = SimpleNamespace(intact=intact)
    return m


class TestRangeMath(TestCase):
    def test_chebyshev_matches_the_pathfinder(self):
        self.assertEqual(_chebyshev((0, 0, 0), (3, 1, 0)), 3)
        self.assertEqual(_chebyshev((0, 0, 0), (3, 1, 2)), 5)  # z is stairs

    def test_effective_range_defaults_and_elevation(self):
        self.assertEqual(_effective_tx_range(None, (0, 0, 0)),
                         RADIO_TX_RANGE)
        # a rooftop transmitter reaches farther
        self.assertEqual(_effective_tx_range(None, (0, 0, 2)),
                         RADIO_TX_RANGE + 2 * RANGE_ELEVATION_BONUS)

    def test_base_station_rides_its_mast(self):
        room = _room(0, 0)
        intact = _radio_at(room, base_station=True, antenna=_mast(True))
        wrecked = _radio_at(room, base_station=True, antenna=_mast(False))
        unlinked = _radio_at(room, base_station=True, antenna=None)
        self.assertEqual(_effective_tx_range(intact, (0, 0, 0)),
                         MAST_TX_RANGE)
        self.assertEqual(_effective_tx_range(wrecked, (0, 0, 0)),
                         RADIO_TX_RANGE)          # desk radio only
        self.assertEqual(_effective_tx_range(unlinked, (0, 0, 0)),
                         MAST_TX_RANGE)

    def test_clarity_bands(self):
        self.assertEqual(_clarity_for_fraction(0.5), ("clear", 1.0))
        grade, clarity = _clarity_for_fraction(0.9)
        self.assertEqual(grade, "fuzzy")
        self.assertTrue(0.2 <= clarity < 1.0)
        self.assertEqual(_clarity_for_fraction(1.1)[0], "static")
        self.assertEqual(_clarity_for_fraction(1.3)[0], "gone")


class TestReception(TestCase):
    def test_direct_reception_by_distance(self):
        near = _radio_at(_room(5, 0))
        far = _radio_at(_room(30, 0))
        self.assertAlmostEqual(
            _reception_fraction((0, 0, 0), 12, [], near), 5 / 12)
        self.assertGreater(
            _reception_fraction((0, 0, 0), 12, [], far), 2.0)

    def test_relay_saves_the_distant_listener(self):
        far = _radio_at(_room(30, 0))
        relay = ((10, 0, 0), MAST_TX_RANGE)   # heard the origin, colony reach
        frac = _reception_fraction((0, 0, 0), 12, [relay], far)
        self.assertLess(frac, 0.1)            # crisp via the repeater

    def test_off_grid_fails_open(self):
        no_coords = MagicMock()
        no_coords.db = SimpleNamespace(xyz=None)
        no_coords.location = None
        set_ = _radio_at(no_coords)
        self.assertEqual(
            _reception_fraction((0, 0, 0), 12, [], set_), 0.0)
        near = _radio_at(_room(5, 0))
        self.assertEqual(_reception_fraction(None, 12, [], near), 0.0)


class TestDeliveryByRange(TestCase):
    def _world(self, radios):
        return patch.object(radio, "_all_powered_radios",
                            return_value=radios)

    def _speaker_at(self, room):
        c = MagicMock()
        c.get_worn_items = lambda: []
        c.hands = {}
        c.contents = []
        c.location = room
        return c

    def _held_by_char_at(self, room, freq="447"):
        r = _radio_at(None, freq=freq)
        holder = MagicMock()
        holder.db = SimpleNamespace(llm_driven=False)
        holder.location = room
        r.location = holder
        return r, holder

    def test_far_set_gets_static_farther_gets_nothing(self):
        origin = _room(0, 0)
        speaker = self._speaker_at(origin)
        dev = _radio_at(None, freq="447"); dev.location = speaker
        static_r, static_holder = self._held_by_char_at(_room(13, 0))
        gone_r, gone_holder = self._held_by_char_at(_room(30, 0))
        with self._world([dev, static_r, gone_r]), \
                patch.object(radio, "_comms_bots_on", return_value=[]), \
                patch.object(radio, "_log_to_channel"), \
                patch("world.perception.can_hear", return_value=True), \
                patch("world.voice.attempt_voice_discern",
                      return_value=None), \
                patch("world.voice.voice_phrase", return_value=None):
            radio.transmit(speaker, "meet at the pad", dev)
        static_kwargs = static_holder.msg.call_args.kwargs
        self.assertNotIn("speech", static_kwargs)       # existence only
        self.assertIn("static", static_holder.msg.call_args.args[0])
        gone_holder.msg.assert_not_called()             # out of the world

    def test_fringe_set_hears_fragments(self):
        origin = _room(0, 0)
        speaker = self._speaker_at(origin)
        dev = _radio_at(None, freq="447"); dev.location = speaker
        fringe_r, fringe_holder = self._held_by_char_at(_room(11, 0))
        with self._world([dev, fringe_r]), \
                patch.object(radio, "_comms_bots_on", return_value=[]), \
                patch.object(radio, "_log_to_channel"), \
                patch("world.perception.can_hear", return_value=True), \
                patch("world.voice.attempt_voice_discern",
                      return_value=None), \
                patch("world.voice.voice_phrase", return_value=None):
            radio.transmit(speaker, "cover the back door before they run",
                           dev)
        heard = fringe_holder.msg.call_args.kwargs.get("speech", "")
        self.assertEqual(len(heard),
                         len("cover the back door before they run"))
        self.assertIn("-", heard)                       # letter-dropped

    def test_repeater_carries_the_band_colony_wide(self):
        origin = _room(0, 0)
        speaker = self._speaker_at(origin)
        dev = _radio_at(None, freq="911MHz"); dev.location = speaker
        console = _radio_at(_room(8, 0), base_station=True,
                            antenna=_mast(True), freq="911MHz")
        console.location.contents = []                  # empty dispatch room
        far_r, far_holder = self._held_by_char_at(_room(30, 0),
                                                  freq="911MHz")
        with self._world([dev, console, far_r]), \
                patch.object(radio, "_comms_bots_on", return_value=[]), \
                patch.object(radio, "_log_to_channel"), \
                patch("world.perception.can_hear", return_value=True), \
                patch("world.voice.attempt_voice_discern",
                      return_value=None), \
                patch("world.voice.voice_phrase", return_value=None):
            radio.transmit(speaker, "officer down on the far side", dev)
        heard = far_holder.msg.call_args.kwargs.get("speech", "")
        self.assertEqual(heard, "officer down on the far side")  # clean

    def test_wrecked_mast_collapses_coverage(self):
        origin = _room(0, 0)
        speaker = self._speaker_at(origin)
        dev = _radio_at(None, freq="911MHz"); dev.location = speaker
        console = _radio_at(_room(8, 0), base_station=True,
                            antenna=_mast(False), freq="911MHz")
        console.location.contents = []
        far_r, far_holder = self._held_by_char_at(_room(30, 0),
                                                  freq="911MHz")
        with self._world([dev, console, far_r]), \
                patch.object(radio, "_comms_bots_on", return_value=[]), \
                patch.object(radio, "_log_to_channel"), \
                patch("world.perception.can_hear", return_value=True), \
                patch("world.voice.attempt_voice_discern",
                      return_value=None), \
                patch("world.voice.voice_phrase", return_value=None):
            radio.transmit(speaker, "anyone copy?", dev)
        far_holder.msg.assert_not_called()   # the relay is dead steel now


class TestReciprocity(TestCase):
    """The mast hears at mast range: a distant handheld reaches a
    mast-backed console (the witness→dispatch chain survives range),
    and a repeater picks up anything its own ears cover."""

    def test_console_hears_the_distant_witness(self):
        console = _radio_at(_room(0, 0), base_station=True,
                            antenna=_mast(True))
        frac = _reception_fraction((30, 0, 0), RADIO_TX_RANGE, [], console)
        self.assertLess(frac, 0.1)                     # clear at the desk

    def test_wrecked_mast_deafens_the_console_too(self):
        console = _radio_at(_room(0, 0), base_station=True,
                            antenna=_mast(False))
        frac = _reception_fraction((30, 0, 0), RADIO_TX_RANGE, [], console)
        self.assertGreater(frac, 1.15)                 # gone

    def test_relay_qualifies_by_its_own_ears(self):
        from world.radio import _relay_points
        from unittest.mock import patch
        console = _radio_at(_room(0, 0), base_station=True,
                            antenna=_mast(True), freq="911MHz")
        with patch.object(radio, "_all_powered_radios",
                          return_value=[console]):
            relays = radio._relay_points("911MHz", None, (30, 0, 0),
                                         RADIO_TX_RANGE)
        self.assertEqual(len(relays), 1)               # heard the far call


class TestOrderReach(TestCase):
    """Orders ARE radio traffic: a wrecked mast collapses command reach
    to walkie range; a switched-off console commands nothing."""

    def _unit_at(self, x, y, z=0):
        unit = MagicMock()
        unit.db = SimpleNamespace(tx_range=None, is_base_station=None)
        unit.location = _room(x, y, z)
        return unit

    def _console(self, intact=True, on=True, x=0, y=0):
        c = _radio_at(_room(x, y), base_station=True,
                      antenna=_mast(intact))
        c.db.radio_on = on
        return c

    def test_intact_mast_commands_the_colony(self):
        from world.radio import order_reaches
        with patch.object(radio, "_all_powered_radios", return_value=[]):
            self.assertTrue(order_reaches(self._unit_at(200, 200),
                                          console=self._console()))

    def test_wrecked_mast_collapses_to_walkie_range(self):
        from world.radio import order_reaches
        console = self._console(intact=False)
        with patch.object(radio, "_all_powered_radios", return_value=[]):
            self.assertTrue(order_reaches(self._unit_at(5, 5),
                                          console=console))
            self.assertFalse(order_reaches(self._unit_at(40, 40),
                                           console=console))

    def test_switched_off_console_commands_nothing(self):
        from world.radio import order_reaches
        console = self._console(on=False)
        self.assertFalse(order_reaches(self._unit_at(1, 1),
                                       console=console))

    def test_no_console_is_a_pre_radio_world(self):
        from world.radio import order_reaches
        with patch("world.director.population.get_base_station",
                   return_value=None):
            self.assertTrue(order_reaches(self._unit_at(40, 40)))

    def test_off_grid_unit_fails_open(self):
        from world.radio import order_reaches
        unit = MagicMock()
        unit.db = SimpleNamespace(tx_range=None, is_base_station=None)
        unit.location = None
        with patch.object(radio, "_all_powered_radios", return_value=[]):
            self.assertTrue(order_reaches(unit,
                                          console=self._console(False)))

    def test_repeater_extends_a_wrecked_masts_orders(self):
        from world.radio import order_reaches
        console = self._console(intact=False)     # walkie-range command
        repeater = _radio_at(_room(8, 8, 5), base_station=True,
                             antenna=_mast(True))
        with patch.object(radio, "_all_powered_radios",
                          return_value=[repeater]):
            self.assertTrue(order_reaches(self._unit_at(40, 40),
                                          console=console))
