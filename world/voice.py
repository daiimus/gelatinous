"""
Voice identity — the parallel-to-visual identity axis
(CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC §4).

The visual identity stack (``world/identity.py``) answers *"who do I see?"* via
sdesc → apparent-UID → recognition memory. Voice is the same machine on a second
axis — *"who do I hear?"* — so a known voice attributes a speaker even when the
listener can't see them (blind, dark, around a corner).

This module is the **data + composition** layer (slice 2a):

* A **curated vocabulary** (bounded, like visual keywords — not free text) for
  the two voice slots a player sets: a **description** (the colour/timbre:
  "gravelly", "silken") and an **ending** (the delivery cap: "drawl", "rasp").
* Read/compose helpers that turn that pair into the speech-flavour phrase
  rendered in ``say`` (``*speaking Common, in a gravelly drawl*``).
* The **talking** capacity gate (§4.7): a wrecked jaw/tongue garbles voice
  production, so a low-``talking`` speaker has no usable signature — their
  voice renders as broken regardless of what they set. This is the first
  consumer of the ``talking`` capacity (otherwise blocked on the social system).

Voice *recognition* (the memory/UID parallel) and the sight/hearing resolution
chain are later slices (2b/2c); this layer is their prerequisite — you cannot
recognise a voice that does not yet exist.

Vocabularies are illustrative/tunable (spec §11) and config-overridable, exactly
like the visual-keyword sets.
"""

from __future__ import annotations

import hashlib
from typing import Any

# Voice-UID digest size — matches the visual Apparent-UID convention
# (``world.identity._APPARENT_UID_DIGEST_BYTES``) so the two axes read alike.
_VOICE_UID_DIGEST_BYTES = 8

# --------------------------------------------------------------------------
# Curated vocabulary
# --------------------------------------------------------------------------
# The colour of the voice — timbre / texture / register. A single curated word
# (a future slice may add a second register slot; the example "gravelly baritone
# drawl" folds register into description for now).
DEFAULT_VOICE_DESCRIPTIONS = frozenset({
    "gravelly", "smoky", "silken", "gritty", "honeyed", "nasal", "breathy",
    "resonant", "raspy", "velvety", "brassy", "reedy", "hoarse", "mellow",
    "clipped", "booming", "husky", "flinty", "icy", "warm", "sandy", "wiry",
})

# The delivery cap — manner / cadence. Rendered as "in a <description> <ending>".
DEFAULT_VOICE_ENDINGS = frozenset({
    "drawl", "rasp", "lilt", "growl", "purr", "murmur", "snarl", "croon",
    "monotone", "burr", "twang", "cadence", "hum", "baritone", "tenor", "alto",
    "warble", "hiss",
})

# Below this ``talking`` capacity the speaker's voice is garbled — no usable
# signature (§4.7). Tunable.
VOICE_GARBLE_THRESHOLD = 0.35

# How often a *visible* speaker's voice flavour is sprinkled into their speech.
# The §4.6 rendering heuristic's "can see the speaker → sporadic, low-frequency
# flavour" branch — the only branch reachable until the sight/hearing resolution
# chain (slice 2c) can produce unseen speakers. Keeps voices alive for everyone
# without spamming. Garble bypasses this and always renders. Tunable.
VOICE_FLAVOR_SPRINKLE_CHANCE = 0.25


def _read_conf_set(conf_key: str, default: frozenset[str]) -> frozenset[str]:
    """Return a config-overridable vocabulary set, falling back to *default*.

    Mirrors ``world.identity._read_keyword_set`` — server config may extend or
    replace the starter vocabulary without a code change.
    """
    try:
        from django.conf import settings
        value = getattr(settings, conf_key, None)
    except Exception:
        value = None
    if not value:
        return default
    return frozenset(str(v).strip().lower() for v in value if str(v).strip())


def get_voice_descriptions() -> frozenset[str]:
    """The approved vocal-description vocabulary."""
    return _read_conf_set("VOICE_DESCRIPTIONS", DEFAULT_VOICE_DESCRIPTIONS)


def get_voice_endings() -> frozenset[str]:
    """The approved voice-ending vocabulary."""
    return _read_conf_set("VOICE_ENDINGS", DEFAULT_VOICE_ENDINGS)


def is_valid_voice_description(word: str) -> bool:
    return bool(word) and word.strip().lower() in get_voice_descriptions()


def is_valid_voice_ending(word: str) -> bool:
    return bool(word) and word.strip().lower() in get_voice_endings()


# --------------------------------------------------------------------------
# Stored signature accessors
# --------------------------------------------------------------------------
def get_voice_description(char: Any) -> str | None:
    db = getattr(char, "db", None)
    return getattr(db, "voice_description", None) if db is not None else None


def get_voice_ending(char: Any) -> str | None:
    db = getattr(char, "db", None)
    return getattr(db, "voice_ending", None) if db is not None else None


def has_voice_signature(char: Any) -> bool:
    """True if the character has set any voice flavour at all."""
    return bool(get_voice_description(char) or get_voice_ending(char))


# --------------------------------------------------------------------------
# The talking-capacity gate (§4.7)
# --------------------------------------------------------------------------
def _read_talking_capacity(char: Any) -> float | None:
    """Raw ``talking`` capacity (0.0–1.0), or ``None`` if unreadable.

    ``None`` → fail open (no medical model means no garble).
    """
    state = getattr(char, "medical_state", None)
    calc = getattr(state, "calculate_body_capacity", None)
    if not callable(calc):
        return None
    try:
        value = calc("talking")
    except Exception:
        return None
    # Only a real number gates garble; anything else (e.g. a test mock) fails
    # open, mirroring ``world.combat.dice.get_character_stat``.
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    return value


def is_voice_garbled(char: Any) -> bool:
    """True when a wrecked ``talking`` capacity ruins voice production."""
    talking = _read_talking_capacity(char)
    if talking is None:
        return False
    return talking < VOICE_GARBLE_THRESHOLD


# --------------------------------------------------------------------------
# Composition (what ``say`` renders)
# --------------------------------------------------------------------------
def garbled_voice_phrase(char: Any, language: str = "Common") -> str | None:
    """The flavour phrase for a speaker whose voice is garbled, else ``None``.

    Garble always renders (a ruined voice is conspicuous every time) — the
    caller does not sprinkle it.
    """
    if not is_voice_garbled(char):
        return None
    return f"speaking {language}, in a slurred, broken voice"


def voice_phrase(char: Any, language: str = "Common") -> str | None:
    """The descriptive voice-flavour phrase from the speaker's signature.

    Returns ``None`` when the speaker has set no voice flavour (graceful — no
    empty ``*speaking Common*`` noise). Ignores the talking gate; callers check
    :func:`garbled_voice_phrase` first.
    """
    desc = get_voice_description(char)
    ending = get_voice_ending(char)
    if desc and ending:
        body = f"in a {desc} {ending}"
    elif desc:
        body = f"in a {desc} voice"
    elif ending:
        body = f"in a {ending}"
    else:
        return None
    return f"speaking {language}, {body}"


# --------------------------------------------------------------------------
# Voice recognition — the apparent-UID / recognition-memory parallel (§4.2)
# --------------------------------------------------------------------------
# Voice recognition is the visual recognition machine on a second axis. The
# signature is salted on the speaker's real ``sleeve_uid`` (so everyone has a
# stable, recognisable voice even before they curate flavour — the description /
# ending are presentation, exactly as the visual sdesc keyword is) plus the
# presentation slots and the modulator state. A voice modulator changes the UID,
# defeating recognition the way a mask defeats the visual channel.
#
# Garble (a wrecked ``talking`` capacity) is NOT a signature input — it does not
# change *who* the voice belongs to, it transiently prevents production. The
# resolution chain (slice 2c) skips the voice channel for a currently-garbled
# speaker; the stored UID stays stable across the injury.

def is_voice_modulated(char: Any) -> bool:
    """True if a voice modulator is masking this character's voice.

    The cyber-disguise parallel to a visual mask (§4.2). No augment sets this
    yet; the flag is honoured now so the modulator is pure content later.
    """
    db = getattr(char, "db", None)
    return bool(getattr(db, "voice_modulator_active", False)) if db is not None else False


def get_voice_signature(char: Any) -> tuple:
    """The voice signature tuple — input to :func:`get_apparent_voice_uid`.

    Mirrors ``world.identity.get_identity_signature``: real ``sleeve_uid`` as a
    per-character salt, plus the curated presentation slots and modulator state.

    Returns:
        ``(sleeve_uid, voice_description, voice_ending, modulator_active)``.
    """
    return (
        getattr(char, "sleeve_uid", None),
        get_voice_description(char),
        get_voice_ending(char),
        is_voice_modulated(char),
    )


def get_apparent_voice_uid(char: Any) -> str | None:
    """Deterministic voice UID for a character's current voice presentation.

    ``None`` when there is no real ``sleeve_uid`` (pre-chargen shell) — callers
    MUST treat ``None`` as "no voice recognition possible", exactly as the
    visual pipeline treats a ``None`` Apparent UID.
    """
    signature = get_voice_signature(char)
    if signature[0] is None:
        return None
    signature_bytes = repr(signature).encode("utf-8")
    return hashlib.blake2b(
        signature_bytes, digest_size=_VOICE_UID_DIGEST_BYTES
    ).hexdigest()


def get_assigned_voice_name(observer: Any, target: Any) -> str | None:
    """Return *observer*'s assigned name for *target*'s current voice.

    Resolves *target*'s current voice UID and looks up the matching
    ``voice_memory`` entry on *observer*. The voice parallel to
    ``world.identity.get_assigned_name``. Returns the non-empty assigned name,
    or ``None`` when the observer has not named this voice (including when the
    target has no voice UID, or the voice is modulated into an unknown UID).
    """
    voice_uid = get_apparent_voice_uid(target)
    if voice_uid is None:
        return None
    memory = getattr(observer, "voice_memory", None)
    if not memory or voice_uid not in memory:
        return None
    assigned = memory[voice_uid].get("assigned_name") or ""
    return assigned or None


def remember_voice(observer: Any, target: Any, name: str) -> bool:
    """Record *name* for *target*'s current voice in *observer*'s voice memory.

    The voice parallel to the recognition-memory writer in ``CmdRemember``.
    Keyed on the target's current voice UID, so a modulated voice gets its own
    entry (you can know someone's real voice and not their disguised one).

    Returns ``True`` if an entry was written, ``False`` when the target has no
    usable voice UID (nothing to remember).
    """
    voice_uid = get_apparent_voice_uid(target)
    if voice_uid is None:
        return False

    memory = getattr(observer, "voice_memory", None)
    if memory is None:
        memory = {}

    entry = memory.get(voice_uid, {})
    entry["assigned_name"] = name
    entry["voice_phrase_at_encounter"] = voice_phrase(target)
    entry["real_sleeve_uid"] = getattr(target, "sleeve_uid", None)
    memory[voice_uid] = entry
    # Reassign through the attribute so the AttributeProperty persists the
    # mutated dict (mirrors how CmdRemember writes recognition_memory).
    observer.voice_memory = memory
    return True


def forget_voice(observer: Any, target: Any) -> bool:
    """Clear *observer*'s assigned name for *target*'s current voice.

    Returns ``True`` if an entry was cleared, ``False`` otherwise.
    """
    voice_uid = get_apparent_voice_uid(target)
    if voice_uid is None:
        return False
    memory = getattr(observer, "voice_memory", None)
    if not memory or voice_uid not in memory:
        return False
    memory[voice_uid]["assigned_name"] = ""
    observer.voice_memory = memory
    return True
