"""Device comms verbs — ``transmit`` / ``tune`` / ``toggle`` (RADIO_COMMS_SPEC
Phase 1). Device-general on purpose: radio is the first consumer, but the
verbs resolve any duck-typed device (``db.is_radio`` today) so future gear
reuses them. Receiving is command-less — a powered, tuned radio echoes
matching traffic to its holder (see ``world/radio.py``)."""

from evennia import Command

from world.radio import (
    SCAN, active_transmit_radio, frequency_of, is_powered, is_radio,
    is_scanning, transmit,
)


def _resolve_device(caller, phrase, *, require_radio=True):
    """A device the caller can see. ``require_radio`` filters to comm gear."""
    obj = caller.search(phrase)
    if obj is None:
        return None
    if require_radio and not is_radio(obj):
        caller.msg(f"{obj.get_display_name(caller)} isn't a comm device.")
        return None
    return obj


class CmdTransmit(Command):
    """
    Speak over a radio (or other comm device).

    Usage:
        transmit <message>
        transmit <message> on <device>
        xmit <message>            (alias: xm)

    Sends your words over the air on the device's tuned frequency — everyone
    with a powered radio on that band hears you, recognised by voice (a
    modulator hides you). With no device named, it uses a radio you're
    WEARING first, then one in your HAND; you can't transmit through a radio
    that's only in your pocket. Seated at a dispatch board, the console
    itself carries your voice — whoever holds the chair holds the desk.

    You transmit LOW — people around you must catch what you mutter into
    the handset (a sharp ear might). To speak into the radio openly so the
    whole room hears, address it instead: ``to <radio>, <message>``.
    """

    key = "transmit"
    aliases = ["xmit", "xm"]
    locks = "cmd:all()"
    help_category = "Social"

    def parse(self):
        raw = (self.args or "").strip()
        self.raw_message = raw
        self.message = self.device_phrase = ""
        # "<message> on <device>" — split on the LAST " on " as a CANDIDATE.
        # The split is only honored if the trailing phrase resolves to a
        # carried radio (func) — otherwise the " on " belonged to the message
        # ("there's trouble on Cobb Street") and the whole line transmits.
        # This grammar ambiguity silently ate every witness report (#1049).
        low = raw.lower()
        idx = low.rfind(" on ")
        if idx != -1:
            self.message = raw[:idx].strip()
            self.device_phrase = raw[idx + 4:].strip()
        else:
            self.message = raw

    def _carried_radio_named(self, caller, phrase):
        """The carried radio *phrase* names, or None — resolved QUIETLY (no
        error spam: a failed match just means the words were message, not a
        device clause)."""
        try:
            matches = caller.search(phrase, candidates=list(caller.contents),
                                    quiet=True)
        except Exception:  # noqa: BLE001
            return None
        if not matches:
            return None
        matches = matches if isinstance(matches, list) else [matches]
        for obj in matches:
            if is_radio(obj):
                return obj
        return None

    def func(self):
        from world.channeled import refuse_if_channeling
        if refuse_if_channeling(self.caller):
            return  # BLOCKED (CHANNELED_ACTIONS_SPEC §2.2): device work is hands-work
        caller = self.caller
        if not self.raw_message:
            caller.msg("Transmit what?")
            return
        device = None
        if self.device_phrase:
            device = self._carried_radio_named(caller, self.device_phrase)
            if device is None:
                # No carried radio by that name — the " on " was part of the
                # message itself. Transmit the whole line on the default.
                self.message = self.raw_message
        if device is None:
            device = active_transmit_radio(caller)
            if device is None:
                # Built-in comms organ fallback (a security unit's ear module,
                # or any future implanted transceiver): same command, no
                # handheld required. world.radio.transmit_organ gates on the
                # organ being intact.
                from world.radio import comms_organ_frequency, transmit_organ
                if comms_organ_frequency(caller):
                    transmit_organ(caller, self.message)
                    return
                caller.msg("You have no radio worn or in hand to transmit "
                           "with.")
                return
        transmit(caller, self.message, device)


class CmdTune(Command):
    """
    Tune a radio to a frequency — or set it sweeping.

    Usage:
        tune <device> to <frequency>
        tune <device> <frequency>
        tune <device> to scan

    A frequency is any band number. ``scan`` sets the radio sweeping every
    band — it echoes whatever it catches, tagged with the frequency it caught
    it on, so you can note the number and tune to it. A sweeping radio can't
    transmit; tune it to a band first.
    """

    key = "tune"
    locks = "cmd:all()"
    help_category = "General"

    def parse(self):
        raw = (self.args or "").strip()
        self.device_phrase = self.freq = ""
        if " to " in raw:
            dev, _, freq = raw.partition(" to ")
            self.device_phrase, self.freq = dev.strip(), freq.strip()
        else:
            parts = raw.rsplit(None, 1)
            if len(parts) == 2:
                self.device_phrase, self.freq = parts[0].strip(), parts[1].strip()
            else:
                self.device_phrase = raw

    def func(self):
        from world.channeled import refuse_if_channeling
        if refuse_if_channeling(self.caller):
            return  # BLOCKED (CHANNELED_ACTIONS_SPEC §2.2): device work is hands-work
        caller = self.caller
        if not self.device_phrase or not self.freq:
            caller.msg("Usage: tune <device> to <frequency>")
            return
        device = _resolve_device(caller, self.device_phrase)
        if device is None:
            return
        freq = self.freq.strip()
        if freq.lower() == SCAN:
            device.db.frequency = SCAN
            caller.msg(f"You set {device.get_display_name(caller)} sweeping "
                       f"the bands.")
            return
        # The dial reads megahertz, not prose: a band is a NUMBER in the
        # tunable range, stored canonically ('912' -> 912MHz) so every
        # radio tuned to the same number lands on the same channel.
        from world.radio import BAND_MAX, BAND_MIN, normalize_band
        band = normalize_band(freq)
        if band is None:
            caller.msg(f"The dial reads megahertz — a number from "
                       f"{int(BAND_MIN)} to {BAND_MAX} (or 'scan'). "
                       f"'{freq}' isn't a frequency.")
            return
        device.db.frequency = band
        state = "" if is_powered(device) else " (it's switched off)"
        caller.msg(f"You tune {device.get_display_name(caller)} to "
                   f"{band}{state}.")


class CmdToggle(Command):
    """
    Switch a device on or off.

    Usage:
        toggle <device>            (flips it)
        toggle <device> on
        toggle <device> off

    A radio must be on to hear traffic or transmit. A powered radio is also
    audible — worth remembering if you're trying not to be found.
    """

    key = "toggle"
    locks = "cmd:all()"
    help_category = "General"

    def parse(self):
        raw = (self.args or "").strip()
        self.device_phrase, self.state = raw, None
        parts = raw.rsplit(None, 1)
        if len(parts) == 2 and parts[1].lower() in ("on", "off"):
            self.device_phrase, self.state = parts[0].strip(), parts[1].lower()

    def func(self):
        from world.channeled import refuse_if_channeling
        if refuse_if_channeling(self.caller):
            return  # BLOCKED (CHANNELED_ACTIONS_SPEC §2.2): device work is hands-work
        caller = self.caller
        if not self.device_phrase:
            caller.msg("Toggle what?")
            return
        device = _resolve_device(caller, self.device_phrase, require_radio=False)
        if device is None:
            return
        if not hasattr(device.db, "radio_on") and not is_radio(device):
            caller.msg(f"{device.get_display_name(caller)} has nothing to "
                       f"switch.")
            return
        want_on = (not is_powered(device)) if self.state is None \
            else (self.state == "on")
        device.db.radio_on = want_on
        caller.msg(f"You switch {device.get_display_name(caller)} "
                   f"{'on' if want_on else 'off'}.")
