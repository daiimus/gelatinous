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
# Capacity reads
# --------------------------------------------------------------------------
def _read_capacity(char: Any, name: str) -> float | None:
    """Raw body capacity *name* (0.0–1.0) for *char*, or ``None`` if unreadable.

    ``None`` signals "no medical model" — callers fail open. Only a real number
    is returned; anything else (e.g. a test mock) yields ``None``, mirroring
    ``world.combat.dice.get_character_stat``.
    """
    state = getattr(char, "medical_state", None)
    calc = getattr(state, "calculate_body_capacity", None)
    if not callable(calc):
        return None
    try:
        value = calc(name)
    except Exception:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    return value


def _has_condition(char: Any, condition_type: str) -> bool:
    """True if *char* carries an active condition of *condition_type*."""
    state = getattr(char, "medical_state", None)
    getter = getattr(state, "get_conditions_by_type", None)
    if not callable(getter):
        return False
    try:
        return bool(getter(condition_type))
    except Exception:
        return False


# --------------------------------------------------------------------------
# The talking-capacity gate (§4.7)
# --------------------------------------------------------------------------
def is_voice_garbled(char: Any) -> bool:
    """True when a wrecked ``talking`` capacity ruins voice production."""
    talking = _read_capacity(char, "talking")
    if talking is None:
        return False
    return talking < VOICE_GARBLE_THRESHOLD


# --------------------------------------------------------------------------
# Perception primitives — can the observer see / hear the speaker (§4.5)
# --------------------------------------------------------------------------
# Below these capacities the observer has effectively lost the sense (blind /
# deaf). One eye / one ear (0.5) still perceives; total loss (0.0) does not.
# These live here for the resolution chain; layer 3 (perception render) may
# promote them to a shared perception module. Tunable.
SIGHT_PERCEPTION_THRESHOLD = 0.15
HEARING_PERCEPTION_THRESHOLD = 0.15

# Condition seams that restore a lost sense (chrome eyes / cyber ears). Reuse
# the combat sight-override constant so one augment is coherent everywhere.
from world.combat.capacity import SIGHT_OVERRIDE_CONDITION  # noqa: E402
HEARING_OVERRIDE_CONDITION = "hearing_override"


def can_see(char: Any) -> bool:
    """True if *char* can see (enough ``sight`` to visually identify others).

    Fails open with no medical model. A sight-override condition (chrome eyes)
    restores sight regardless of organ state.
    """
    if _has_condition(char, SIGHT_OVERRIDE_CONDITION):
        return True
    sight = _read_capacity(char, "sight")
    if sight is None:
        return True
    return sight >= SIGHT_PERCEPTION_THRESHOLD


def can_hear(char: Any) -> bool:
    """True if *char* can hear (enough ``hearing`` to receive a voice).

    Fails open with no medical model. A hearing-override condition (cyber ears)
    restores hearing regardless of organ state.
    """
    if _has_condition(char, HEARING_OVERRIDE_CONDITION):
        return True
    hearing = _read_capacity(char, "hearing")
    if hearing is None:
        return True
    return hearing >= HEARING_PERCEPTION_THRESHOLD


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
    # Familiarity: how many times this voice has been remembered, feeding the
    # discernment determination (mirrors recognition ``times_seen``).
    entry["times_heard"] = int(entry.get("times_heard", 0) or 0) + 1
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
    invalidate_voice_discern_cache_for_sleeve(
        observer, getattr(target, "sleeve_uid", None)
    )
    return True


def find_voice_entries_by_real_sleeve_uid(observer, real_sleeve_uid):
    """All *observer* voice-memory ``(voice_uid, entry)`` for a given sleeve.

    Voice parallel to ``world.identity.find_entries_by_real_sleeve_uid`` — lets
    discernment find "have I named this person's voice under *any* presentation?"
    (e.g. their natural voice, when they are now modulated).
    """
    if not real_sleeve_uid:
        return []
    memory = getattr(observer, "voice_memory", None) or {}
    return [
        (uid, entry)
        for uid, entry in memory.items()
        if entry.get("real_sleeve_uid") == real_sleeve_uid
    ]


# --------------------------------------------------------------------------
# Voice discernment — the determination (mirrors disguise piercing, §4.5)
# --------------------------------------------------------------------------
# Discerning a voice is ALWAYS a determination, never a free lookup: a face you
# can stare at, a voice you must place, and audio-only is an inherently less
# certain channel. The mechanic mirrors ``world.identity.attempt_disguise_pierce``
# exactly — opposed Intellect (observer) vs Resonance (target), familiarity
# buff, a "disguise" penalty (here the voice modulator), permanently cached per
# presentation so one determination sticks (no per-utterance flicker). What
# voice adds is the ``hearing`` capacity multiplier on the observer's side — the
# consumer that makes this layer earn its name (deaf cannot discern, one ear is
# impaired). Magnitudes mirror the visual side and are tunable (spec §11).

VOICE_DISCERN_FAMILIARITY_CAP = 5
VOICE_DISCERN_MODULATION_PENALTY = 3

#: What an unseen, undiscerned speaker is rendered as. The voice descriptor as a
#: stand-in identity ("a gravelly drawl says…") is deferred — for now an
#: unrecognised voice simply isn't attributed (decided).
GENERIC_UNSEEN_SPEAKER = "someone"


def attempt_voice_discern(observer: Any, target: Any) -> str | None:
    """Resolve (and cache) whether *observer* places *target*'s voice by name.

    Returns the assigned voice name on success, ``None`` otherwise (never
    heard/named this voice, garbled production, failed determination). The
    caller renders ``None`` as :data:`GENERIC_UNSEEN_SPEAKER`.
    """
    if observer is target:
        return None
    # A garbled voice carries no usable signature to place.
    if is_voice_garbled(target):
        return None

    voice_uid = get_apparent_voice_uid(target)
    real_sleeve = getattr(target, "sleeve_uid", None)
    if voice_uid is None or not real_sleeve:
        return None

    # Have we named this person's voice under any presentation?
    named = [
        (uid, entry)
        for uid, entry in find_voice_entries_by_real_sleeve_uid(observer, real_sleeve)
        if (entry.get("assigned_name") or "")
    ]
    if not named:
        return None
    # Prefer the entry for the *current* voice presentation; otherwise any named
    # presentation (you know their natural voice, they are modulated now).
    bare_entry = next(
        (entry for uid, entry in named if uid == voice_uid), named[0][1]
    )
    assigned_name = bare_entry["assigned_name"]

    observer_dbref = getattr(observer, "dbref", None)
    target_dbref = getattr(target, "dbref", None)
    cacheable = (
        observer_dbref is not None
        and target_dbref is not None
        and bool(voice_uid)
    )
    if cacheable:
        cache = observer.db.voice_discern_cache
        if cache is None:
            cache = {}
        key = (target_dbref, voice_uid)
        if key in cache:
            return assigned_name if cache[key] else None
    else:
        cache = None
        key = None

    from world.combat.dice import opposed_roll

    obs_roll, tgt_roll, _ = opposed_roll(
        observer, target, "intellect", "resonance"
    )
    familiarity = min(
        int(bare_entry.get("times_heard", 0) or 0),
        VOICE_DISCERN_FAMILIARITY_CAP,
    )
    penalty = VOICE_DISCERN_MODULATION_PENALTY if is_voice_modulated(target) else 0
    # Hearing weights the observer's side — the capacity consumer. Fail open
    # (full hearing) with no medical model.
    hearing = _read_capacity(observer, "hearing")
    if hearing is None:
        hearing = 1.0
    success = (obs_roll + familiarity) * hearing > (tgt_roll + penalty)

    if cacheable:
        cache[key] = success
        observer.db.voice_discern_cache = cache

    return assigned_name if success else None


def invalidate_voice_discern_cache_for_sleeve(observer, real_sleeve_uid):
    """Drop cached voice-discern verdicts for every presentation of a sleeve.

    Voice parallel to ``world.identity.invalidate_pierce_cache_for_sleeve`` —
    called on forget so the cognitive act of forgetting a person also discards
    every cached discernment for any voice presentation they have used.
    """
    if not real_sleeve_uid:
        return 0
    db = getattr(observer, "db", None)
    cache = getattr(db, "voice_discern_cache", None) if db is not None else None
    if not cache:
        return 0
    uids = {
        uid for uid, _ in find_voice_entries_by_real_sleeve_uid(observer, real_sleeve_uid)
    }
    if not uids:
        return 0
    removed = 0
    for key in list(cache.keys()):
        # key == (target_dbref, voice_uid)
        if isinstance(key, tuple) and len(key) == 2 and key[1] in uids:
            del cache[key]
            removed += 1
    if removed:
        observer.db.voice_discern_cache = cache
    return removed


# --------------------------------------------------------------------------
# The resolution chain — who said it, per listener (§4.5)
# --------------------------------------------------------------------------
def resolve_speaker_attribution(speaker: Any, observer: Any) -> str:
    """How *observer* hears *speaker* attributed in speech.

    The see → hear → neither chain, gated on the *observer's* capacities:

    1. **Can see** → the normal visual display name (recognition / disguise
       pierce / sdesc) — unchanged from the sighted path.
    2. **Can't see, can hear** → the voice discernment determination: the
       assigned voice name on success, else :data:`GENERIC_UNSEEN_SPEAKER`.
    3. **Neither** (blind + deaf) → :data:`GENERIC_UNSEEN_SPEAKER`.
    """
    if observer is speaker:
        return getattr(speaker, "key", GENERIC_UNSEEN_SPEAKER)
    if can_see(observer):
        return speaker.get_display_name(observer)
    if can_hear(observer):
        return attempt_voice_discern(observer, speaker) or GENERIC_UNSEEN_SPEAKER
    return GENERIC_UNSEEN_SPEAKER
