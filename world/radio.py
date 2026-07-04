"""Radio — the colony's primary comms (RADIO_COMMS_SPEC Phase 1).

Radio is PHYSICAL and DEVICE-GATED (Option A): a transmission reaches every
powered walkie tuned to its frequency (the network is assumed present until
Phase 2 makes range/antennae geography). No device — snatched, off, wrong
band — no signal.

**Backend (§6.1): one channel, the walkie sorts it out.** A single staff-
locked Evennia Channel ("Radio") carries ALL traffic tagged with frequency —
the admin's whole-grid monitor and single chronological log. Players never
subscribe: a tuned, powered walkie **echoes** matching traffic to its holder,
re-rendered through the voice rails (voice recognition on the air; a modulator
defeats it; hearing-gated; attributed by VOICE only — you can't see who's on
the far end).

Devices are duck-typed (`db.is_radio`), so the transmit/tune/toggle verbs
generalise to any future comm gear.
"""

from __future__ import annotations

from typing import Any, Optional

RADIO_CHANNEL_KEY = "Radio"
#: The special "frequency" that receives every band (scanner sweep mode).
SCAN = "scan"


# --------------------------------------------------------------------------
# Device predicates & state
# --------------------------------------------------------------------------

def is_radio(obj: Any) -> bool:
    """Duck-typed: a comm device that transmits/receives on a frequency.
    Strict ``is True`` — the flag is only ever written as a literal, so a
    non-radio's absent/mock attribute never reads as one."""
    return getattr(getattr(obj, "db", None), "is_radio", False) is True


def is_powered(device: Any) -> bool:
    return getattr(getattr(device, "db", None), "radio_on", False) is True


def frequency_of(device: Any) -> Optional[str]:
    return getattr(getattr(device, "db", None), "frequency", None)


def is_scanning(device: Any) -> bool:
    return frequency_of(device) == SCAN


# --------------------------------------------------------------------------
# Which device a character uses (worn first, then held)
# --------------------------------------------------------------------------

def _worn_radios(char: Any) -> list:
    get_worn = getattr(char, "get_worn_items", None)
    worn = get_worn() if callable(get_worn) else []
    return [i for i in (worn or []) if is_radio(i)]


def _held_radios(char: Any) -> list:
    hands = getattr(char, "hands", None) or {}
    seen, out = set(), []
    for item in hands.values():
        if is_radio(item) and id(item) not in seen:
            seen.add(id(item))
            out.append(item)
    return out


def active_transmit_radio(char: Any) -> Optional[Any]:
    """The device a ``transmit`` defaults to: a WORN radio first, then a HELD
    one. Returns None if the character has neither worn nor held — a radio
    merely carried in a pocket can receive but not be spoken through
    (spec: 'unable to use the command unless it's worn or held')."""
    worn = _worn_radios(char)
    if worn:
        return worn[0]
    held = _held_radios(char)
    return held[0] if held else None


def carried_radios(char: Any) -> list:
    """Every radio in the character's possession (worn, held, or pocketed) —
    all of them receive, so a captured second walkie on another band is a
    listening post for free."""
    out, seen = [], set()
    for item in getattr(char, "contents", []) or []:
        if is_radio(item) and id(item) not in seen:
            seen.add(id(item))
            out.append(item)
    return out


# --------------------------------------------------------------------------
# The channel (staff monitor + log)
# --------------------------------------------------------------------------

def get_radio_channel() -> Optional[Any]:
    """The single staff-locked channel carrying all traffic. Created on first
    use; players never subscribe (they hear via a walkie echo)."""
    try:
        from evennia.comms.models import ChannelDB
        from evennia import create_channel
        chan = ChannelDB.objects.get_channel(RADIO_CHANNEL_KEY)
        if not chan:
            chan = create_channel(
                RADIO_CHANNEL_KEY,
                locks=("control:perm(Admin);listen:perm(Builder);"
                       "send:false()"),
                desc="Colony radio grid — all frequencies (staff monitor).",
            )
        return chan
    except Exception:  # noqa: BLE001 — the log is a convenience, never load-bearing
        return None


def _log_to_channel(speaker: Any, message: str, frequency: str) -> None:
    chan = get_radio_channel()
    if chan is None:
        return
    try:
        from world.voice import get_voice_description
        voice = get_voice_description(speaker) or "unknown voice"
        name = getattr(speaker, "key", "?")
        chan.msg(f"[{frequency}] {name} ({voice}): \"{message}\"")
    except Exception:  # noqa: BLE001
        pass


# --------------------------------------------------------------------------
# Transmit + echo
# --------------------------------------------------------------------------

def _all_powered_radios():
    """Every powered radio in the world (attribute-scoped query). Range is
    abstracted in P1, so a transmission reaches all of them on-band."""
    from evennia.objects.models import ObjectDB
    return [o for o in ObjectDB.objects.filter(
        db_attributes__db_key="is_radio").distinct()
        if is_radio(o) and is_powered(o)]


def _render_radio_line(speaker: Any, listener: Any, message: str,
                       frequency: str, *, tagged: bool) -> str:
    """A received transmission, VOICE-attributed (never sight — you can't see
    the far end) and hearing-gated. ``tagged`` prefixes the frequency (scanner
    sweep mode caught it off-band)."""
    from world.perception import can_hear
    from world.voice import (
        attempt_voice_discern, get_voice_description, voice_phrase,
    )
    band = f"[{frequency}] " if tagged else ""
    if not can_hear(listener):
        return f"{band}Your radio crackles, but you can't make out a word."
    # Attribution: a known voice names them; else the voice descriptor; else
    # a bare "someone". Mirrors resolve_speaker_attribution's voice branch.
    known = attempt_voice_discern(listener, speaker)
    if known:
        who = known
    else:
        desc = get_voice_description(speaker)
        who = f"a {desc} voice" if desc else "an unfamiliar voice"
    flavour = voice_phrase(speaker)
    flav = f" |x*{flavour}*|n" if flavour else ""
    return (f'{band}{who[:1].upper()}{who[1:]} crackles over the radio{flav}: '
            f'"{message}"')


def transmit(speaker: Any, message: str, device: Any) -> bool:
    """Speaker transmits *message* over *device* on its tuned frequency.

    Returns False (with the speaker messaged) if the device can't send —
    off, or in scan mode (sweeping, not parked on a band). Otherwise posts to
    the staff channel and echoes to every powered radio tuned to that
    frequency (plus any radio in scan mode, which catches all bands)."""
    if not is_powered(device):
        speaker.msg(f"{device.get_display_name(speaker)} is switched off.")
        return False
    if is_scanning(device):
        speaker.msg(f"{device.get_display_name(speaker)} is sweeping — "
                    f"tune it to a frequency before you transmit.")
        return False
    frequency = frequency_of(device)
    if not frequency:
        speaker.msg(f"{device.get_display_name(speaker)} isn't tuned to "
                    f"anything.")
        return False

    speaker.msg(f'You transmit on {frequency}: "{message}"')
    _log_to_channel(speaker, message, frequency)

    for radio in _all_powered_radios():
        if radio is device:
            continue
        scanning = is_scanning(radio)
        if not scanning and frequency_of(radio) != frequency:
            continue
        holder = radio.location
        if holder is None or not hasattr(holder, "msg"):
            continue  # a radio on the ground squawks to nobody in P1
        if holder is speaker:
            continue
        try:
            holder.msg(_render_radio_line(
                speaker, holder, message, frequency, tagged=scanning),
                type="radio", from_obj=speaker)
        except Exception:  # noqa: BLE001 — one bad listener never stops the net
            continue
    return True
