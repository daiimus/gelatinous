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

import random
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
    one, then the DISPATCH BOARD the character is seated at (a powered base
    station in their room — desk work, see ``seated_base_station``). Returns
    None otherwise — a radio merely carried in a pocket can receive but not
    be spoken through (spec: 'unable to use the command unless it's worn or
    held')."""
    worn = _worn_radios(char)
    if worn:
        return worn[0]
    held = _held_radios(char)
    if held:
        return held[0]
    return seated_base_station(char)


def seated_base_station(char: Any) -> Optional[Any]:
    """The board the character is WORKING: a powered base station in their
    room while they sit at furniture there. Working a console is desk work —
    you take the chair; a standing visitor doesn't key the colony's dispatch
    voice by brushing past it. (Whoever holds the chair holds the voice: the
    attribution stays honestly THEIRS — a seized desk broadcasts the seizer,
    not the operator.)"""
    furniture = getattr(getattr(char, "db", None), "furniture", None)
    if furniture is None:
        return None
    room = getattr(char, "location", None)
    if room is None or getattr(furniture, "location", None) is not room:
        return None
    for obj in getattr(room, "contents", []) or []:
        if (getattr(getattr(obj, "db", None), "is_base_station", None) is True
                and is_radio(obj) and is_powered(obj)):
            return obj
    return None


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


def hears_emergency_band(char: Any) -> bool:
    """A working receiver on the dispatch band: the built-in comms organ
    (§2.1) or any powered carried radio tuned there. This is what makes
    a security unit REACHABLE — dispatch orders are radio traffic, so a
    deafened unit (shot ear, snatched or broken walkie) can't be raised,
    doesn't roll, and drops out of the availability count. The sabotage
    is the point: neutralize a unit without destroying it."""
    try:
        if same_band(comms_organ_frequency(char), EMERGENCY_BAND):
            return True
        for radio in carried_radios(char):
            try:
                if is_powered(radio) and same_band(
                        frequency_of(radio), EMERGENCY_BAND):
                    return True
            except Exception:  # noqa: BLE001 — one broken set never deafens
                continue
    except Exception:  # noqa: BLE001 — no medical model = no organ, keep checking nothing
        pass
    return False


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
    a grille you're merely standing near.

    The voice is described ONCE (playtest, 2026-07-10): a GENERIC handle —
    "A voice", or the name when the listener knows it — with the accent
    carried in italics before the words:

        A voice crackles over the radio: *speaking Common, in a smoky
        rasp* "Long day."

    (The descriptive handle + accent-suffix arrangement described the same
    voice twice. The NPC brain's buffer handle — ``radio_voice_handle`` —
    keeps the descriptor: prose for a reader, not a render.)"""
    from world.perception import can_hear
    from world.voice import attempt_voice_discern, voice_phrase
    band = f"[{frequency}] " if tagged else ""
    if not can_hear(listener):
        source = "Your radio" if own else "A radio nearby"
        return f"{band}{source} crackles, but you can't make out a word."
    who = attempt_voice_discern(listener, speaker) or "a voice"
    accent = voice_phrase(speaker)
    acc = f"|x*{accent}*|n " if accent else ""
    return (f'{band}{who[:1].upper()}{who[1:]} crackles over the radio: '
            f'{acc}"{message}"')


def transmit(speaker: Any, message: str, device: Any,
             overt: bool = False) -> bool:
    """Speaker transmits *message* over *device* on its tuned frequency.

    ``overt`` is HOW the words leave the mouth (decided 2026-07-07):
    ``xmit`` (overt=False) is keying the handset and speaking into it, LOW —
    bystanders must catch it (opposed hearing check, §_mutter_into);
    ``to <radio>, <message>`` (overt=True) is openly addressing the device —
    ordinary room speech everyone present hears.

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
    if overt:
        _speak_aloud(speaker, message, verb="says into the radio")
    else:
        _mutter_into(speaker, message)
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


#: The mutter-catch curve: an even roll hears half the letters; each point
#: of margin swings comprehension by this much. Below the floor the words
#: are just noise (the act-only line).
MUTTER_CLARITY_STEP = 0.15
MUTTER_CLARITY_FLOOR = 0.2

# --- Phase 2 range (RADIO_COMMS_SPEC, decided 2026-07-10) -----------------
#: Handheld / comms-organ transmit reach, in city grid cells.
RADIO_TX_RANGE = 12
#: A base station riding an intact mast: colony-wide.
MAST_TX_RANGE = 999
#: Inside this fraction of reach the signal is crisp.
RANGE_CLEAR_FRACTION = 0.7
#: Between full reach and this fraction: a static wash, existence only.
RANGE_STATIC_FRACTION = 1.15
#: Extra cells of reach per z-level of the transmit room (rooftops matter).
RANGE_ELEVATION_BONUS = 2


def _chebyshev(a, b):
    """Grid distance, matching the pathfinder heuristic."""
    return max(abs(a[0] - b[0]), abs(a[1] - b[1])) + abs(a[2] - b[2])


def _grid_room(obj):
    """The nearest containing room WITH coordinates (a held radio's
    room is its holder's room). None = off-grid (range fails open)."""
    from world.spatial import get_xyz
    node = obj
    for _ in range(3):
        if node is None:
            return None
        try:
            if get_xyz(node) is not None:
                return node
        except Exception:  # noqa: BLE001 — malformed coords read off-grid
            return None
        node = getattr(node, "location", None)
    return None


def _effective_tx_range(device, origin_xyz):
    """Transmit reach in cells. A base station rides its mast: intact
    (or none linked) = MAST_TX_RANGE, wrecked = handheld reach (the
    desk radio still keys, but only locally). Handhelds/organs use
    ``db.tx_range`` or the default. The transmit room's elevation adds
    reach."""
    base = None
    try:
        if device is not None:
            db = getattr(device, "db", None)
            explicit = getattr(db, "tx_range", None)
            if getattr(db, "is_base_station", None) is True:
                antenna = getattr(db, "antenna", None)
                if antenna is not None and getattr(
                        getattr(antenna, "db", None), "intact",
                        None) is not True:
                    base = RADIO_TX_RANGE
                else:
                    base = explicit or MAST_TX_RANGE
            elif explicit:
                base = float(explicit)
    except Exception:  # noqa: BLE001
        base = None
    if base is None:
        base = RADIO_TX_RANGE
    try:
        z = origin_xyz[2] if origin_xyz else 0
        return float(base) + RANGE_ELEVATION_BONUS * max(0, int(z))
    except Exception:  # noqa: BLE001
        return float(base)


def _relay_points(frequency, exclude_device, origin_xyz, origin_range):
    """(xyz, reach) per qualifying repeater: a powered base station on
    the band with an intact (or absent) mast, on-grid, and within the
    ORIGIN's reach — a repeater must hear you to repeat you. One hop;
    repeaters regenerate the signal clean."""
    from world.spatial import get_xyz
    out = []
    if origin_xyz is None:
        return out
    for radio in _all_powered_radios():
        try:
            if radio is exclude_device:
                continue
            if getattr(radio.db, "is_base_station", None) is not True:
                continue
            if not same_band(frequency_of(radio), frequency):
                continue
            antenna = getattr(radio.db, "antenna", None)
            if antenna is not None and getattr(
                    getattr(antenna, "db", None), "intact", None) is not True:
                continue
            room = _grid_room(radio)
            xyz = get_xyz(room) if room is not None else None
            if xyz is None:
                continue
            reach = _effective_tx_range(radio, xyz)
            # reciprocity: the mast HEARS at mast range too — a repeater
            # picks up any handheld its own big ears can reach
            if _chebyshev(origin_xyz, xyz) > max(origin_range, reach):
                continue
            out.append((xyz, reach))
        except Exception:  # noqa: BLE001 — one odd repeater never mutes a band
            continue
    return out


def _reception_fraction(origin_xyz, origin_range, relays, listener_obj):
    """Best-path distance/reach fraction for a receiver. The link is
    RECIPROCAL: a mast-backed station hears at mast range, so the
    effective reach of the direct path is max(transmit, receive) — a
    witness's handheld reaches dispatch from across the colony because
    the CONSOLE'S antenna is tall, not theirs. 0.0 (crisp) whenever
    anyone involved is off-grid — range NEVER silences rooms the
    coordinate grid doesn't cover."""
    from world.spatial import get_xyz
    if origin_xyz is None:
        return 0.0
    room = _grid_room(listener_obj)
    xyz = get_xyz(room) if room is not None else None
    if xyz is None:
        return 0.0
    rx_reach = _effective_tx_range(listener_obj, xyz)
    link = max(float(origin_range), float(rx_reach), 1.0)
    best = _chebyshev(origin_xyz, xyz) / link
    for rxyz, rrange in relays:
        frac = _chebyshev(rxyz, xyz) / max(float(rrange), 1.0)
        if frac < best:
            best = frac
    return best


def _clarity_for_fraction(fraction):
    """Map a range fraction to a reception grade:
    ('clear'|'fuzzy'|'static'|'gone', clarity). Fuzzy rides the same
    letter-drop renderer as the mutter machinery — the fringe of
    coverage sounds like fragments, not a cliff."""
    if fraction <= RANGE_CLEAR_FRACTION:
        return ("clear", 1.0)
    if fraction <= 1.0:
        span = ((fraction - RANGE_CLEAR_FRACTION)
                / (1.0 - RANGE_CLEAR_FRACTION))
        return ("fuzzy", max(MUTTER_CLARITY_FLOOR,
                             1.0 - span * (1.0 - MUTTER_CLARITY_FLOOR)))
    if fraction <= RANGE_STATIC_FRACTION:
        return ("static", 0.0)
    return ("gone", 0.0)


def _obscure_heard(message: str, clarity: float) -> str:
    """Drop letters the listener didn't catch: each letter survives with
    probability *clarity*, the rest render as ``-`` — fragments of a low
    voice ("c-ver the b-ck d--r"), spacing and punctuation intact so the
    SHAPE of the sentence stays audible."""
    drop = 1.0 - max(0.0, min(1.0, clarity))
    return "".join("-" if ch.isalpha() and random.random() < drop else ch
                   for ch in message)


def _mutter_into(speaker: Any, message: str) -> None:
    """The xmit register: a low voice into the handset. Each hearing
    bystander rolls to catch it — listener Intellect vs the speaker's
    Resonance (the voice-discern pairing) — and the MARGIN sets how much
    survives: a clean win hears every word, an even ear catches fragments
    ("c-ver the b-ck d--r"), a bad miss (or deafness) gets only the act.
    Sight-only observers see the act. The counter-play is the band: a
    same-room listener whose radio matches hears the CONTENT off their own
    handset regardless (perspective 4)."""
    location = getattr(speaker, "location", None)
    if location is None:
        return
    try:
        from world.combat.dice import opposed_roll
        from world.grammar import capitalize_first
        from world.perception import can_hear, can_see
        from world.speech import (
            render_speech_line, speech_payload, visible_voice_flavor,
        )
        from world.voice import resolve_speaker_attribution
        flavor = visible_voice_flavor(speaker)
        contents = getattr(location, "contents", None)
        if not isinstance(contents, (list, tuple)):
            return
        for observer in contents:
            if observer is speaker or not hasattr(observer, "msg"):
                continue
            heard = can_hear(observer)
            seen = can_see(observer)
            if not heard and not seen:
                continue
            clarity = 0.0
            if heard:
                try:
                    o_roll, s_roll, _ = opposed_roll(
                        observer, speaker, "intellect", "resonance")
                    clarity = max(0.0, min(1.0, 0.5 + (o_roll - s_roll)
                                           * MUTTER_CLARITY_STEP))
                except Exception:  # noqa: BLE001 — no dice, no eavesdrop
                    clarity = 0.0
            if clarity >= MUTTER_CLARITY_FLOOR:
                caught = (message if clarity >= 1.0
                          else _obscure_heard(message, clarity))
                text = render_speech_line(
                    speaker, observer, caught, flavor=flavor,
                    verb="mutters into the radio")
                # The payload carries exactly what THIS listener heard —
                # an NPC brain reacts to the fragments, not the secret.
                payload = speech_payload(observer, speaker, caught)
                observer.msg(text=text, type="say", from_obj=speaker,
                             **payload)
            else:
                who = capitalize_first(
                    resolve_speaker_attribution(speaker, observer))
                observer.msg(
                    f"{who} mutters something into the radio.",
                    type="say", from_obj=speaker)
    except Exception:  # noqa: BLE001 — room render never blocks the air
        pass


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
    receivers = []   # (listener, tagged, own, grade, clarity), order-stable
    seen = set()

    # Phase 2 range: where is this transmission coming from, how far
    # does it carry, and which repeaters regenerate it? Off-grid
    # origins fail open (everyone hears clean — Phase 1 behaviour).
    from world.spatial import get_xyz
    try:
        origin_room = _grid_room(speaker)
        origin_xyz = get_xyz(origin_room) if origin_room is not None else None
    except Exception:  # noqa: BLE001
        origin_xyz = None
    origin_range = _effective_tx_range(exclude_device, origin_xyz)
    relays = _relay_points(frequency, exclude_device, origin_xyz,
                           origin_range)

    def _collect(listener, *, tagged, own, grade, clarity):
        if listener is None or listener is speaker or id(listener) in seen:
            return
        if not hasattr(listener, "msg"):
            return
        # No same-room suppression (decided 2026-07-07): a matching radio
        # beside the speaker DOES echo — with xmit's low voice, your own
        # handset repeating the words is how you learn you share their band.
        seen.add(id(listener))
        receivers.append((listener, tagged, own, grade, clarity))

    for radio in _all_powered_radios():
        if radio is exclude_device:
            continue
        scanning = is_scanning(radio)
        if scanning or same_band(frequency_of(radio), frequency):
            # the receiving SET's position decides reception; everyone
            # at its grille hears the same grade
            grade, clarity = _clarity_for_fraction(
                _reception_fraction(origin_xyz, origin_range, relays, radio))
            if grade == "gone":
                continue
            # Perspective 4: a walkie has a GRILLE — the traffic is audible
            # to the whole room the radio is in, not just its holder (the
            # toggle help has promised this since P1). A carried radio fans
            # to the holder's room; one on the floor fans to its room.
            holder = radio.location
            for listener in _grille_audience(holder):
                _collect(listener, tagged=scanning, own=(listener is holder),
                         grade=grade, clarity=clarity)

    for bot in _comms_bots_on(frequency):
        # A comms ORGAN is internal — in the ear, not on a grille. Private
        # to the unit; the room hears nothing.
        grade, clarity = _clarity_for_fraction(
            _reception_fraction(origin_xyz, origin_range, relays, bot))
        if grade == "gone":
            continue
        _collect(bot, tagged=False, own=True, grade=grade, clarity=clarity)

    # Single-answerer election: deterministic (lowest dbref) among LLM-driven
    # receivers who actually got WORDS (a static-drowned unit can't answer).
    elected = None
    try:
        candidates = [l for l, _, _, grade, _ in receivers
                      if grade in ("clear", "fuzzy")
                      and getattr(getattr(l, "db", None), "llm_driven", False)
                      is True]
        if candidates:
            elected = min(candidates, key=lambda l: getattr(l, "id", 0) or 0)
    except Exception:  # noqa: BLE001 — election is best-effort flavour
        elected = None

    from world.perception import can_hear
    for listener, tagged, own, grade, clarity in receivers:
        try:
            band = f"[{frequency}] " if tagged else ""
            if grade == "static":
                # past the edge of coverage: existence, not content
                source = "Your radio" if own else "A radio nearby"
                listener.msg(
                    f"{band}{source} hisses — a voice buried somewhere "
                    f"in distant static.",
                    type="radio", from_obj=speaker,
                    radio_frequency=frequency, radio_elected=False)
                continue
            heard = message if clarity >= 1.0                 else _obscure_heard(message, clarity)
            payload = {}
            if can_hear(listener):
                payload["speech"] = heard   # the say-rails contract:
                # an NPC reacts to exactly the fragments it caught
            listener.msg(_render_radio_line(
                speaker, listener, heard, frequency, tagged=tagged,
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
