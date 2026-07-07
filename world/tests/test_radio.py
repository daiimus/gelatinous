"""Radio Phase 1 (world/radio.py + commands/CmdRadio.py) — RADIO_COMMS_SPEC.

The device-gated echo: powered walkie tuned to a frequency hears matching
traffic, voice-attributed and hearing-gated; transmit defaults worn→held;
scan catches all bands; the `to`-retarget transmits.
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

import world.radio as radio
from world.radio import (
    SCAN, active_transmit_radio, is_radio, is_scanning, transmit,
)


def _radio(on=True, freq="447"):
    r = MagicMock()
    r.db.is_radio = True
    r.db.radio_on = on
    r.db.frequency = freq
    return r


def _char(worn=None, hands=None, contents=None):
    c = MagicMock()
    c.get_worn_items = lambda: (worn or [])
    c.hands = hands or {}
    c.contents = contents if contents is not None else []
    c.get_display_name = lambda looker=None, **k: "a lean man"
    return c


class TestDevicePredicates(TestCase):
    def test_is_radio(self):
        self.assertTrue(is_radio(_radio()))
        plain = MagicMock(); plain.db.is_radio = False
        self.assertFalse(is_radio(plain))

    def test_scan_mode(self):
        self.assertTrue(is_scanning(_radio(freq=SCAN)))
        self.assertFalse(is_scanning(_radio(freq="447")))
        self.assertTrue(is_scanning(_radio(freq="SCAN")))   # case-insensitive

    def test_same_band_is_case_insensitive(self):
        from world.radio import same_band
        self.assertTrue(same_band("911MHz", "911mhz"))   # tuned vs constant
        self.assertTrue(same_band(" 447 ", "447"))
        self.assertFalse(same_band("447", "891"))
        self.assertFalse(same_band(None, "447"))         # untuned = no band
        self.assertFalse(same_band("447", None))

    def test_same_band_normalizes_legacy_loose_values(self):
        from world.radio import same_band
        self.assertTrue(same_band("912", "912MHz"))      # pre-dial data
        self.assertTrue(same_band("101.5", "101.5mhz"))
        self.assertTrue(same_band("911.0", "911MHz"))    # trailing .0 folds

    def test_normalize_band_is_a_dial_not_prose(self):
        from world.radio import normalize_band
        self.assertEqual(normalize_band("912"), "912MHz")
        self.assertEqual(normalize_band("911mhz"), "911MHz")
        self.assertEqual(normalize_band(" 101.5 MHz".replace(" MHz", "MHz")),
                         "101.5MHz")
        self.assertEqual(normalize_band("101.54"), "101.5MHz")  # one decimal
        self.assertIsNone(normalize_band("banana"))      # not a frequency
        self.assertIsNone(normalize_band("0"))           # below the dial
        self.assertIsNone(normalize_band("1000"))        # above the dial
        self.assertIsNone(normalize_band(""))
        self.assertIsNone(normalize_band(None))

    def test_tune_rejects_prose_and_stores_canonical(self):
        from commands.CmdRadio import CmdTune
        dev = _radio()
        # prose refused
        cmd = CmdTune(); cmd.args = "walkie to banana"
        cmd.caller = MagicMock(); cmd.caller.ndb.channel = None
        cmd.caller.search.return_value = dev
        cmd.parse(); cmd.func()
        self.assertIn("isn't a frequency", cmd.caller.msg.call_args.args[0])
        self.assertNotEqual(dev.db.frequency, "banana")
        # loose number stored canonically
        cmd2 = CmdTune(); cmd2.args = "walkie to 912"
        cmd2.caller = MagicMock(); cmd2.caller.ndb.channel = None
        cmd2.caller.search.return_value = dev
        cmd2.parse(); cmd2.func()
        self.assertEqual(dev.db.frequency, "912MHz")

    def test_transmit_device_prefers_worn_then_held(self):
        worn, held = _radio(), _radio()
        c = _char(worn=[worn], hands={"r": held})
        self.assertIs(active_transmit_radio(c), worn)      # worn wins
        c2 = _char(worn=[], hands={"r": held})
        self.assertIs(active_transmit_radio(c2), held)     # else held
        c3 = _char(worn=[], hands={})
        self.assertIsNone(active_transmit_radio(c3))       # pocketed != usable


class TestTransmit(TestCase):
    def _world(self, listeners):
        return patch.object(radio, "_all_powered_radios",
                            return_value=listeners)

    def test_matching_frequency_hears_voice_attributed(self):
        speaker = _char()
        dev = _radio(freq="447")
        heard_radio = _radio(freq="447")
        listener = MagicMock()
        heard_radio.location = listener
        with self._world([dev, heard_radio]), \
                patch.object(radio, "_log_to_channel"), \
                patch("world.perception.can_hear", return_value=True), \
                patch("world.voice.attempt_voice_discern",
                      return_value=None), \
                patch("world.voice.get_voice_description",
                      return_value="gravelly"), \
                patch("world.voice.voice_phrase", return_value=None):
            ok = transmit(speaker, "rendezvous at the docks", dev)
        self.assertTrue(ok)
        line = listener.msg.call_args.args[0]
        self.assertIn("A gravelly voice crackles over the radio", line)
        self.assertIn("rendezvous at the docks", line)

    def test_known_voice_names_the_speaker(self):
        speaker = _char()
        dev, heard = _radio(freq="447"), _radio(freq="447")
        listener = MagicMock(); heard.location = listener
        with self._world([dev, heard]), \
                patch.object(radio, "_log_to_channel"), \
                patch("world.perception.can_hear", return_value=True), \
                patch("world.voice.attempt_voice_discern",
                      return_value="Roony"), \
                patch("world.voice.voice_phrase", return_value=None):
            transmit(speaker, "hi", dev)
        self.assertIn("Roony crackles over the radio",
                      listener.msg.call_args.args[0])

    def test_off_band_radio_does_not_hear(self):
        speaker = _char()
        dev, off_band = _radio(freq="447"), _radio(freq="891")
        listener = MagicMock(); off_band.location = listener
        with self._world([dev, off_band]), \
                patch.object(radio, "_log_to_channel"):
            transmit(speaker, "hi", dev)
        listener.msg.assert_not_called()

    def test_band_match_ignores_case(self):
        # Device tuned "911MHz" (constant) reaches a walkie the player tuned
        # as "911mhz" — the case-insensitivity that lets typed bands connect.
        speaker = _char()
        dev, heard = _radio(freq="911MHz"), _radio(freq="911mhz")
        listener = MagicMock(); heard.location = listener
        with self._world([dev, heard]), \
                patch.object(radio, "_log_to_channel"), \
                patch("world.perception.can_hear", return_value=True), \
                patch("world.voice.attempt_voice_discern", return_value=None), \
                patch("world.voice.get_voice_description", return_value="flat"), \
                patch("world.voice.voice_phrase", return_value=None):
            transmit(speaker, "unit down", dev)
        self.assertIn("unit down", listener.msg.call_args.args[0])

    def test_scanning_radio_catches_all_bands_tagged(self):
        speaker = _char()
        dev, scanner = _radio(freq="447"), _radio(freq=SCAN)
        listener = MagicMock(); scanner.location = listener
        with self._world([dev, scanner]), \
                patch.object(radio, "_log_to_channel"), \
                patch("world.perception.can_hear", return_value=True), \
                patch("world.voice.attempt_voice_discern", return_value=None), \
                patch("world.voice.get_voice_description",
                      return_value="flat"), \
                patch("world.voice.voice_phrase", return_value=None):
            transmit(speaker, "come in", dev)
        self.assertIn("[447]", listener.msg.call_args.args[0])   # freq-tagged

    def test_deaf_listener_gets_static(self):
        speaker = _char()
        dev, heard = _radio(freq="447"), _radio(freq="447")
        listener = MagicMock(); heard.location = listener
        with self._world([dev, heard]), \
                patch.object(radio, "_log_to_channel"), \
                patch("world.perception.can_hear", return_value=False):
            transmit(speaker, "secret", dev)
        line = listener.msg.call_args.args[0]
        self.assertIn("crackles", line)
        self.assertNotIn("secret", line)

    def test_xmit_mutters_discreetly_in_the_speakers_room(self):
        # xmit = keying the handset and speaking LOW: the room gets the
        # mutter render (opposed catch checks), never the open say line.
        speaker = _char()
        dev = _radio(freq="447")
        with self._world([dev]), \
                patch.object(radio, "_log_to_channel"), \
                patch.object(radio, "_mutter_into") as mut, \
                patch("world.speech.broadcast_speech") as bs:
            transmit(speaker, "cover the back door", dev)
        mut.assert_called_once_with(speaker, "cover the back door")
        bs.assert_not_called()

    def test_overt_transmit_speaks_openly(self):
        # `to <radio>, ...` = openly addressing the device: ordinary room
        # speech via the say rails, everyone present hears.
        speaker = _char()
        dev = _radio(freq="447")
        with self._world([dev]), \
                patch.object(radio, "_log_to_channel"), \
                patch("world.speech.broadcast_speech") as bs:
            transmit(speaker, "cover the back door", dev, overt=True)
        bs.assert_called_once()
        args, kwargs = bs.call_args
        self.assertEqual(args[1], "cover the back door")
        self.assertEqual(kwargs.get("verb"), "says into the radio")

    def test_mutter_clarity_grades_with_the_roll_margin(self):
        # Margin sets comprehension: a clean win hears every word, an even
        # ear catches fragments, a bad miss gets only the act.
        from types import SimpleNamespace
        speaker = MagicMock()
        sharp, even, dull = MagicMock(), MagicMock(), MagicMock()
        room = SimpleNamespace(contents=[sharp, even, dull])
        speaker.location = room
        rolls = {id(sharp): (10, 5),    # margin +5 -> clarity 1.0: verbatim
                 id(even): (5, 5),      # margin  0 -> clarity 0.5: fragments
                 id(dull): (2, 9)}      # margin -7 -> below floor: act only
        rendered = []
        def _render(spk, obs, msg, **kw):
            rendered.append((obs, msg))
            return f'X mutters into the radio, "{msg}"'
        with patch("world.combat.dice.opposed_roll",
                   side_effect=lambda o, s, *a: (*rolls[id(o)], None)), \
                patch("world.perception.can_hear", return_value=True), \
                patch("world.perception.can_see", return_value=True), \
                patch("world.speech.visible_voice_flavor", return_value=None), \
                patch("world.speech.render_speech_line",
                      side_effect=_render), \
                patch("world.voice.resolve_speaker_attribution",
                      return_value="a lean man"):
            radio._mutter_into(speaker, "cover the back door")
        by_obs = {id(o): m for o, m in rendered}
        self.assertEqual(by_obs[id(sharp)], "cover the back door")  # verbatim
        fragments = by_obs[id(even)]
        self.assertIn("-", fragments)                # some letters lost...
        self.assertNotEqual(fragments, "cover the back door")
        self.assertEqual(len(fragments), len("cover the back door"))
        self.assertTrue(any(c.isalpha() for c in fragments))  # ...not all
        dull_text = dull.msg.call_args.args[0]
        self.assertIn("mutters something into the radio", dull_text)
        self.assertNotIn("cover", dull_text)

    def test_obscure_heard_keeps_shape_loses_letters(self):
        from world.radio import _obscure_heard
        msg = "meet at the docks, nine."
        self.assertEqual(_obscure_heard(msg, 1.0), msg)      # perfect ear
        blanked = _obscure_heard(msg, 0.0)
        self.assertEqual(len(blanked), len(msg))             # shape intact
        self.assertNotIn("m", blanked)                       # letters gone
        self.assertIn(",", blanked)                          # punctuation stays
        self.assertIn(" ", blanked)

    def test_grille_fans_to_the_receiving_radios_room(self):
        # Perspective 4: a walkie has a grille — the whole room hears it,
        # not just the holder ('a powered radio is also audible').
        from types import SimpleNamespace
        speaker = _char()
        dev = _radio(freq="447")
        holder, bystander = MagicMock(), MagicMock()
        holder.db.llm_driven = False
        bystander.db.llm_driven = False
        room = SimpleNamespace(contents=[holder, bystander])
        holder.location = room
        bystander.location = room
        heard = _radio(freq="447")
        heard.location = holder
        with self._world([dev, heard]), \
                patch.object(radio, "_log_to_channel"), \
                patch("world.speech.broadcast_speech"), \
                patch("world.perception.can_hear", return_value=True), \
                patch("world.voice.attempt_voice_discern", return_value=None), \
                patch("world.voice.get_voice_description", return_value="flat"), \
                patch("world.voice.voice_phrase", return_value=None):
            transmit(speaker, "come in", dev)
        holder.msg.assert_called_once()
        bystander.msg.assert_called_once()      # the grille reached them
        self.assertIn("come in", bystander.msg.call_args.args[0])

    def test_same_room_matching_radio_echoes_the_mutter(self):
        # Decided 2026-07-07 (double render): xmit is a LOW voice — but a
        # same-room listener whose radio shares the band hears the CONTENT
        # off their own handset. The echo is how you learn you share a band.
        from types import SimpleNamespace
        speaker = _char()
        dev = _radio(freq="447")
        friend = MagicMock()
        friend.db.llm_driven = False
        room = SimpleNamespace(contents=[])
        speaker.location = room
        friend.location = room                   # standing with the speaker
        heard = _radio(freq="447")
        heard.location = friend
        with self._world([dev, heard]), \
                patch.object(radio, "_log_to_channel"), \
                patch.object(radio, "_mutter_into"), \
                patch("world.perception.can_hear", return_value=True), \
                patch("world.voice.attempt_voice_discern", return_value=None), \
                patch("world.voice.get_voice_description", return_value="flat"), \
                patch("world.voice.voice_phrase", return_value=None):
            transmit(speaker, "quiet now", dev)
        friend.msg.assert_called_once()          # the echo arrives
        self.assertIn("quiet now", friend.msg.call_args.args[0])

    def test_ground_radio_fans_to_its_room(self):
        # A walkie left on the floor squawks to whoever's in the room —
        # a planted/abandoned live radio is a real presence.
        from types import SimpleNamespace
        speaker = _char()
        dev = _radio(freq="447")
        visitor = MagicMock()
        visitor.db.llm_driven = False
        room = SimpleNamespace(contents=[visitor])   # no 'hands': a room
        ground_radio = _radio(freq="447")
        ground_radio.location = room
        with self._world([dev, ground_radio]), \
                patch.object(radio, "_log_to_channel"), \
                patch("world.speech.broadcast_speech"), \
                patch("world.perception.can_hear", return_value=True), \
                patch("world.voice.attempt_voice_discern", return_value=None), \
                patch("world.voice.get_voice_description", return_value="flat"), \
                patch("world.voice.voice_phrase", return_value=None):
            transmit(speaker, "anyone there?", dev)
        visitor.msg.assert_called_once()
        self.assertIn("anyone there?", visitor.msg.call_args.args[0])

    def test_off_device_refuses_transmit(self):
        speaker = _char()
        dev = _radio(on=False, freq="447")
        with patch.object(radio, "_all_powered_radios", return_value=[]):
            self.assertFalse(transmit(speaker, "hi", dev))
        self.assertIn("switched off", speaker.msg.call_args.args[0])

    def test_scanning_device_refuses_transmit(self):
        speaker = _char()
        dev = _radio(freq=SCAN)
        self.assertFalse(transmit(speaker, "hi", dev))
        self.assertIn("sweeping", speaker.msg.call_args.args[0])


class TestCommands(TestCase):
    def test_transmit_parses_on_device(self):
        from commands.CmdRadio import CmdTransmit
        cmd = CmdTransmit()
        cmd.args = "meet at the docks on the black handset"
        cmd.parse()
        self.assertEqual(cmd.message, "meet at the docks")
        self.assertEqual(cmd.device_phrase, "the black handset")

    def test_message_containing_on_transmits_whole_line(self):
        # THE witness bug (#1049): "there's trouble on Cobb Street" parsed
        # "Cobb Street..." as a device name and silently ate every report.
        # The on-split is only honored when it names a carried radio.
        from commands.CmdRadio import CmdTransmit
        dev = _radio(freq="911MHz")
        caller = _char(worn=[dev], contents=[dev])
        caller.search = lambda phrase, **kw: []   # no device by that name
        line = ("Someone call it in — there's trouble on Cobb Street, "
                "get a unit down here!")
        cmd = CmdTransmit(); cmd.caller = caller
        cmd.args = line
        cmd.parse()
        with patch("commands.CmdRadio.transmit") as tx:
            cmd.func()
        tx.assert_called_once_with(caller, line, dev)   # FULL line, default dev

    def test_on_split_still_honored_for_a_carried_radio(self):
        from commands.CmdRadio import CmdTransmit
        worn, named = _radio(freq="447"), _radio(freq="911MHz")
        caller = _char(worn=[worn], contents=[worn, named])
        caller.search = lambda phrase, **kw: [named]    # resolves the handset
        cmd = CmdTransmit(); cmd.caller = caller
        cmd.args = "meet at the docks on the black handset"
        cmd.parse()
        with patch("commands.CmdRadio.transmit") as tx:
            cmd.func()
        tx.assert_called_once_with(caller, "meet at the docks", named)

    def test_transmit_no_radio_worn_or_held(self):
        from commands.CmdRadio import CmdTransmit
        cmd = CmdTransmit()
        cmd.caller = _char(worn=[], hands={})
        cmd.args = "hello"
        cmd.parse()
        cmd.func()
        self.assertIn("no radio worn or in hand",
                      cmd.caller.msg.call_args.args[0])

    def test_tune_parses_to_and_bare(self):
        from commands.CmdRadio import CmdTune
        for args in ("walkie to 447", "walkie 447"):
            cmd = CmdTune(); cmd.args = args; cmd.parse()
            self.assertEqual(cmd.device_phrase, "walkie")
            self.assertEqual(cmd.freq, "447")

    def test_tune_to_scan(self):
        from commands.CmdRadio import CmdTune
        dev = _radio()
        cmd = CmdTune(); cmd.args = "walkie to scan"
        cmd.caller = MagicMock(); cmd.caller.search.return_value = dev
        cmd.parse(); cmd.func()
        self.assertEqual(dev.db.frequency, SCAN)

    def test_toggle_flip_and_explicit(self):
        from commands.CmdRadio import CmdToggle
        dev = _radio(on=False)
        cmd = CmdToggle(); cmd.args = "walkie"
        cmd.caller = MagicMock(); cmd.caller.search.return_value = dev
        cmd.parse(); cmd.func()
        self.assertTrue(dev.db.radio_on)          # flipped on
        cmd2 = CmdToggle(); cmd2.args = "walkie off"
        cmd2.caller = MagicMock(); cmd2.caller.search.return_value = dev
        cmd2.parse(); cmd2.func()
        self.assertFalse(dev.db.radio_on)         # explicit off

    def test_to_retarget_transmits(self):
        from commands.CmdCommunication import CmdTo
        dev = _radio(freq="447")
        caller = MagicMock()
        caller.location = MagicMock()
        caller.contents = [dev]
        caller.search.return_value = dev
        cmd = CmdTo(); cmd.caller = caller; cmd.args = "walkie, on my way"
        with patch("world.stealth.break_stealth"), \
                patch("world.radio.transmit") as tx:
            cmd.func()
        tx.assert_called_once_with(caller, "on my way", dev, overt=True)


class TestCommsOrgan(TestCase):
    """Security bots hear via a built-in comms organ (ear module), not a
    carried walkie — and go deaf when it's destroyed (the EMP/mute seam)."""

    def _bot(self, freq="911MHz", destroyed=False):
        bot = MagicMock()
        bot.db.role = "security"
        organ = MagicMock()
        organ.data = {"radio_frequency": freq}
        organ.is_destroyed = lambda: destroyed
        bot.medical_state.organs = {"comms_module": organ}
        return bot

    def test_intact_organ_reports_frequency(self):
        from world.radio import comms_organ_frequency
        self.assertEqual(comms_organ_frequency(self._bot()), "911MHz")

    def test_destroyed_organ_is_deaf(self):
        from world.radio import comms_organ_frequency
        self.assertIsNone(comms_organ_frequency(
            self._bot(destroyed=True)))

    def test_no_medical_state_is_deaf(self):
        from world.radio import comms_organ_frequency
        c = MagicMock(); c.medical_state = None
        self.assertIsNone(comms_organ_frequency(c))

    def test_bot_receives_emergency_transmission(self):
        from world.radio import EMERGENCY_BAND, transmit
        speaker = _char()
        dev = _radio(freq=EMERGENCY_BAND)
        bot = self._bot(freq=EMERGENCY_BAND)
        with patch.object(radio, "_all_powered_radios", return_value=[dev]), \
                patch.object(radio, "_comms_bots_on", return_value=[bot]), \
                patch.object(radio, "_log_to_channel"), \
                patch("world.perception.can_hear", return_value=True), \
                patch("world.voice.attempt_voice_discern", return_value=None), \
                patch("world.voice.get_voice_description", return_value="tinny"), \
                patch("world.voice.voice_phrase", return_value=None):
            transmit(speaker, "unit down", dev)
        bot.msg.assert_called_once()
        self.assertIn("unit down", bot.msg.call_args.args[0])


class TestWitnessGating(TestCase):
    def _witness(self, walkie=None):
        w = MagicMock()
        w.contents = [walkie] if walkie else []
        return w

    def test_walkie_present_and_tuned_gates_report_true(self):
        from world.director.witness import _witness_walkie
        from world.radio import EMERGENCY_BAND
        walkie = _radio(freq=EMERGENCY_BAND)
        self.assertIs(_witness_walkie(self._witness(walkie)), walkie)

    def test_snatched_walkie_no_report(self):
        from world.director.witness import _witness_walkie
        self.assertIsNone(_witness_walkie(self._witness(None)))

    def test_off_or_wrong_band_walkie_no_report(self):
        from world.director.witness import _witness_walkie
        off = _radio(on=False, freq="911MHz")
        self.assertIsNone(_witness_walkie(self._witness(off)))
        wrong = _radio(on=True, freq="447")
        self.assertIsNone(_witness_walkie(self._witness(wrong)))
