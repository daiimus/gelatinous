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

from typing import Any

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
        return calc("talking")
    except Exception:
        return None


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
