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
#: The colony's distress channel — witnesses call it in here, security
#: monitors it. No band plan yet, so a real-world emergency band stands in.
EMERGENCY_BAND = "911MHz"


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
    freq = frequency_of(device)
    return isinstance(freq, str) and freq.strip().lower() == SCAN


#: The handheld's tunable range, in megahertz — a bounded spectrum makes
#: scanning/guessing/jamming meaningful (a band plan exists to be searched).
BAND_MIN, BAND_MAX = 1.0, 999.9


def normalize_band(raw: Any) -> Optional[str]:
    """Canonicalize a dialed frequency: a NUMBER (optional one decimal),
    optional ``MHz`` suffix any case, within the tunable range — rendered
    as ``911MHz`` / ``101.5MHz``. Returns None for anything a dial can't
    say (``banana`` is not a frequency). ``scan`` is not a band; callers
    handle it before this."""
    if raw is None:
        return None
    text = str(raw).strip().lower()
    if text.endswith("mhz"):
        text = text[:-3].strip()
    if not text:
        return None
    try:
        value = float(text)
    except (TypeError, ValueError):
        return None
    if not (BAND_MIN <= value <= BAND_MAX):
        return None
    value = round(value, 1)
    shown = str(int(value)) if value == int(value) else f"{value:.1f}"
    return f"{shown}MHz"


def same_band(a: Any, b: Any) -> bool:
    """Two frequencies are the same band. Both sides normalize through the
    canonical dial format first — so a legacy loose value (``912``) matches
    its canonical form (``912MHz``), and case never matters. Non-numeric
    values fall back to a case-insensitive string compare (future named
    bands); None never matches (an untuned radio is on no band)."""
    if a is None or b is None:
        return False
    na, nb = normalize_band(a), normalize_band(b)
    if na is not None and nb is not None:
        return na == nb
    return str(a).strip().lower() == str(b).strip().lower()


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


def comms_organ_frequency(char: Any) -> Optional[str]:
    """The band a character's BUILT-IN comms organ is tuned to, if it has a
    functional one (a security bot's ear/antenna module — §2.1). None when
    the organ is absent or destroyed (the EMP/shoot-the-ear mute seam falls
    out of the medical hit-location system for free)."""
    state = getattr(char, "medical_state", None)
    if state is None:
        return None
    for organ in (getattr(state, "organs", None) or {}).values():
        try:
            freq = (getattr(organ, "data", None) or {}).get("radio_frequency")
            if freq and not organ.is_destroyed():
                return freq
        except Exception:  # noqa: BLE001 — a broken organ record just doesn't hear
            continue
    return None


def _comms_bots_on(frequency: str) -> list:
    """Security units whose built-in comms organ is tuned to *frequency* and
    intact — role-scoped so it's a bounded query, not a full character scan."""
    from evennia.objects.models import ObjectDB
    out = []
    for char in ObjectDB.objects.filter(
            db_attributes__db_key="role").distinct():
        if getattr(char.db, "role", None) != "security":
            continue
        if same_band(comms_organ_frequency(char), frequency):
            out.append(char)
    return out


def radio_voice_handle(speaker: Any, listener: Any) -> str:
    """How *listener* knows the voice on the air: a recognised voice names
    them (voice memory; a modulator defeats it), else the voice descriptor,
    else "an unfamiliar voice". Attribution is VOICE-ONLY — you can't see the
    far end. Shared by the echo render and the NPC brain (§7.1)."""
    from world.voice import attempt_voice_discern, get_voice_description
    known = attempt_voice_discern(listener, speaker)
    if known:
        return known
    desc = get_voice_description(speaker)
    return f"a {desc} voice" if desc else "an unfamiliar voice"


def _render_radio_line(speaker: Any, listener: Any, message: str,
                       frequency: str, *, tagged: bool, own: bool = True) -> str:
    """A received transmission, VOICE-attributed (never sight — you can't see
    the far end) and hearing-gated. ``tagged`` prefixes the frequency (scanner
    sweep mode caught it off-band); ``own`` distinguishes your handset from
    a grille you're merely standing near."""
    from world.perception import can_hear
    from world.voice import voice_phrase
    band = f"[{frequency}] " if tagged else ""
    if not can_hear(listener):
        source = "Your radio" if own else "A radio nearby"
        return f"{band}{source} crackles, but you can't make out a word."
    who = radio_voice_handle(speaker, listener)
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
    _speak_aloud(speaker, message, verb="says into the radio")
    _deliver(speaker, message, frequency, device)
    return True


def _speak_aloud(speaker: Any, message: str, verb: str) -> None:
    """Perspective 3 (§2.4 — radio is PHYSICAL): transmitting is talking,
    out loud, in a room. The spoken line rides the say rails so bystanders
    get per-observer attribution, hearing gating, garble, and stealth for
    free — the witness calling in your assault is audible to the person
    standing next to them."""
    location = getattr(speaker, "location", None)
    if location is None:
        return
    try:
        from world.speech import broadcast_speech
        broadcast_speech(speaker, message, location, verb=verb)
    except Exception:  # noqa: BLE001 — room render never blocks the air
        pass


def transmit_organ(speaker: Any, message: str) -> bool:
    """Key up a BUILT-IN comms organ — the transceiver a security unit wears
    in its ear (§2.1). No handheld needed; the organ's intactness is the
    physical gate (destroyed ear = mute, same as deaf). Same air, same log,
    same delivery as a walkie. ``transmit``'s no-device fallback routes here,
    so a bot keys up through the identical player command."""
    frequency = comms_organ_frequency(speaker)
    if not frequency:
        speaker.msg("You have no working comms module to transmit with.")
        return False
    speaker.msg(f'You transmit on {frequency}: "{message}"')
    _log_to_channel(speaker, message, frequency)
    _speak_aloud(speaker, message, verb="says over comms")
    _deliver(speaker, message, frequency, None)
    return True


def _deliver(speaker: Any, message: str, frequency: str,
             exclude_device: Any) -> None:
    """Echo a transmission to every receiver on *frequency*: powered walkies
    (tuned or scanning) held by a character, and security units with a live
    built-in comms organ. Deduped per receiver so a bot holding a walkie AND
    wearing a comms organ hears it once.

    Each hearing listener also gets the STRUCTURED speech payload the say
    rails use (``speech=<words>``, world.speech) plus radio kwargs — so an NPC
    brain reads one shape regardless of the carrying verb (§7.1). A deaf
    listener gets the static line and no words. One listener among the
    LLM-driven receivers is ELECTED (``radio_elected=True``) — the §7.2
    single-answerer for "all units"-style broadcasts, so a band-wide call
    can't raise a chorus."""
    receivers = []          # (listener, tagged, own), deduped, order-stable
    seen = set()
    speaker_room = getattr(speaker, "location", None)

    def _collect(listener, *, tagged, own):
        if listener is None or listener is speaker or id(listener) in seen:
            return
        if not hasattr(listener, "msg"):
            return
        # Same-room suppression: whoever stands WITH the speaker already
        # heard the words live (perspective 3, the say rails) — their radio
        # echoing it back would be double render, not physics worth keeping.
        if (speaker_room is not None
                and getattr(listener, "location", None) is speaker_room):
            return
        seen.add(id(listener))
        receivers.append((listener, tagged, own))

    for radio in _all_powered_radios():
        if radio is exclude_device:
            continue
        scanning = is_scanning(radio)
        if scanning or same_band(frequency_of(radio), frequency):
            # Perspective 4: a walkie has a GRILLE — the traffic is audible
            # to the whole room the radio is in, not just its holder (the
            # toggle help has promised this since P1). A carried radio fans
            # to the holder's room; one on the floor fans to its room.
            holder = radio.location
            for listener in _grille_audience(holder):
                _collect(listener, tagged=scanning, own=(listener is holder))

    for bot in _comms_bots_on(frequency):
        # A comms ORGAN is internal — in the ear, not on a grille. Private
        # to the unit; the room hears nothing.
        _collect(bot, tagged=False, own=True)

    # Single-answerer election: deterministic (lowest dbref) among LLM-driven
    # receivers. Range is abstracted in P1, so "nearest" has no meaning yet.
    elected = None
    try:
        candidates = [l for l, _, _ in receivers
                      if getattr(getattr(l, "db", None), "llm_driven", False)
                      is True]
        if candidates:
            elected = min(candidates, key=lambda l: getattr(l, "id", 0) or 0)
    except Exception:  # noqa: BLE001 — election is best-effort flavour
        elected = None

    from world.perception import can_hear
    for listener, tagged, own in receivers:
        try:
            payload = {}
            if can_hear(listener):
                payload["speech"] = message   # the say-rails contract
            listener.msg(_render_radio_line(
                speaker, listener, message, frequency, tagged=tagged,
                own=own),
                type="radio", from_obj=speaker,
                radio_frequency=frequency,
                radio_elected=(listener is elected),
                **payload)
        except Exception:  # noqa: BLE001 — one bad listener never stops the net
            pass


def _grille_audience(holder: Any) -> list:
    """Who hears a receiving walkie's grille. A radio carried by someone
    fans to their whole room (holder included); one lying in a room fans to
    that room's contents. Strictly typed (isinstance list) so a mock or
    malformed location degrades to holder-only, never to silence."""
    if holder is None:
        return []
    room = getattr(holder, "location", None)
    contents = getattr(room, "contents", None) if room is not None else None
    if isinstance(contents, (list, tuple)):          # carried: holder's room
        audience = list(contents)
        if holder not in audience:
            audience.append(holder)
        return audience
    contents = getattr(holder, "contents", None)
    if (isinstance(contents, (list, tuple))
            and not hasattr(holder, "hands")):       # on the floor of a room
        return list(contents)
    return [holder]                                   # fallback: holder only
