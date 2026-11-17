"""
Voice identity — the parallel-to-visual identity axis
(CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC §4).

The visual identity stack (``world/identity.py``) answers *"who do I see?"* via
sdesc → apparent-UID → recognition memory. Voice is the same machine on a second
axis — *"who do I hear?"* — so a known voice attributes a speaker even when the
listener can't see them (blind, dark, around a corner).

This module is the whole voice layer — data and composition (slice 2a),
recognition (2b) and the resolution chain (2c). It described itself as
2a only for three slices after the other two shipped INSIDE it, while
inline comments a few lines down referred to 2c in the present tense
(#2645):

* A **curated vocabulary** (bounded, like visual keywords — not free text) for
  the two voice slots a player sets: a **description** (the colour/timbre:
  "gravelly", "silken") and an **ending** (the delivery cap: "drawl", "rasp").
* Read/compose helpers that turn that pair into the speech-flavour phrase
  rendered in ``say`` (``*speaking Common, in a gravelly drawl*``).
* The **talking** capacity gate (§4.7): a wrecked jaw/tongue garbles voice
  production, so a low-``talking`` speaker has no usable signature — their
  voice renders as broken regardless of what they set. This is the first
  consumer of the ``talking`` capacity (otherwise blocked on the social system).
* **Recognition** (slice 2b): `get_apparent_voice_uid`, `remember_voice`
  and the voice half of recognition memory — the memory/UID parallel to
  the visual channel. Composition is its prerequisite: you cannot
  recognise a voice that does not exist.
* **The resolution chain** (slice 2c): `attempt_voice_discern` and the
  sight/hearing arbitration that lets a listener place a speaker they
  cannot see.

Vocabularies are illustrative/tunable (spec §11) and config-overridable, exactly
like the visual-keyword sets.
"""

from __future__ import annotations

import hashlib
from typing import Any

# Per-sense capability checks live in world.perception (the perception module);
# voice's speech-attribution chain consumes them.
from world.perception import (
    _read_capacity,
    can_hear,
    can_see,
    hearing_multiplier,
)

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

    Mirrors ``world.identity._read_keyword_set`` — and now actually does.
    It read ``django.conf.settings``, a module loaded at startup, while
    the function it named as its model reads ``ServerConfig``, which is
    runtime-editable and has staff commands behind it. Different backing
    store, different lifecycle, and "without a code change" was false:
    editing settings.py IS a code change, and it needs a restart. The
    voice vocabularies were effectively hardcoded while the identity
    vocabulary they were modelled on was live-editable (#2809).
    """
    try:
        from evennia.server.models import ServerConfig
        stored = ServerConfig.objects.conf(conf_key)
    except Exception:  # noqa: BLE001 — no DB yet (import time, a bare test)
        stored = None
    if not stored:
        return default
    return frozenset(str(v).strip().lower() for v in stored if str(v).strip())


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
def is_voice_garbled(char: Any) -> bool:
    """True when a wrecked ``talking`` capacity ruins voice production."""
    talking = _read_capacity(char, "talking")
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
    from world.grammar import with_article
    if desc and ending:
        body = f"in {with_article(f'{desc} {ending}')}"
    elif desc:
        body = f"in {with_article(f'{desc} voice')}"
    elif ending:
        body = f"in {with_article(ending)}"
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

    The cyber-disguise parallel to a visual mask (§4.2). Derived from the
    jaw module itself: ``VOICE_MODULATOR`` seats a ``voice_modulator``
    ability into a cyber jaw, and ``/modulate`` deploys it.

    Read off the organ rather than a ``character.db`` flag, because a
    flag has to be cleared by everything that can take the module away —
    and a module destroyed in place clears nothing, which welded the
    disguise on permanently (#2484). A destroyed organ simply stops
    matching here.
    """
    from world.medical.augments import has_deployed_ability
    return has_deployed_ability(char, "voice_modulator")


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


def remember_voice(observer: Any, target: Any, name: str,
                   look_uid: str | None = None) -> bool:
    """Record *name* for *target*'s current voice in *observer*'s voice memory.

    The voice parallel to the recognition-memory writer in ``CmdRemember``.
    Keyed on the target's current voice UID, so a modulated voice gets its own
    entry (you can know someone's real voice and not their disguised one).

    Returns ``True`` if an entry was written, ``False`` when the target has no
    usable voice UID (nothing to remember) or *observer* cannot hear.

    The gate lives HERE rather than at each caller. `CmdRemember` reasoned
    "you are co-located, so you hear them" and checked only whether the
    SPEAKER's voice was garbled — which is sound for a hearing listener
    and is exactly the assumption deafness breaks, so a deaf character
    who remembered someone they could see acquired a voice they cannot
    hear (#2809).
    """
    if not can_hear(observer):
        return False
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
    # The look this voice was named together with (#3825). `forget`
    # erases a voice by the look the observer learned it with. Not by
    # its name: papers can rename the face and leave the voice as it
    # was, and two different people can end up under one name. It is
    # overwritten when the same voice is named again under another
    # look, so the voice goes with the look it was last named with.
    entry["named_with"] = look_uid
    # Familiarity: how many times this voice has been remembered, feeding the
    # discernment determination (mirrors recognition ``times_seen``).
    entry["times_heard"] = int(entry.get("times_heard", 0) or 0) + 1
    memory[voice_uid] = entry
    # Reassign through the attribute so the AttributeProperty persists the
    # mutated dict (mirrors how CmdRemember writes recognition_memory).
    observer.voice_memory = memory
    return True


def won_voice_verdicts(observer: Any) -> set:
    """The won voice verdicts *observer* holds, as their keys:
    ``(body dbref, voice uid)`` for every stored attempt to tell whose
    voice it was hearing that succeeded (``voice_discern_cache``,
    written by :func:`attempt_voice_discern`). A failed attempt is not
    one.

    :func:`world.identity.erase_look` reads this before and after it
    erases a name, to tell which verdicts went with it (#3861). The
    keys are compared and not the voice uids: a verdict made on a body
    object that no longer exists is never erased, and a new body of
    the same person can sound the same.
    """
    cache = observer.db.voice_discern_cache
    if not cache:
        return set()
    return {key for key in list(cache)
            if isinstance(key, tuple) and len(key) == 2 and cache[key]}


def _won_voice_verdicts_standing_on(observer: Any, uids: Any) -> list:
    """The voices *observer* placed BY WAY OF the entries *uids*.

    Mirror of :func:`world.identity._won_verdicts_standing_on`. A won
    verdict stands on the entry :func:`attempt_voice_discern` read the
    name from: the heard voice's own entry when it has a name, else the
    first named voice the observer holds for that body. Lost verdicts
    are never returned (#3817).
    """
    cache = getattr(getattr(observer, "db", None), "voice_discern_cache", None)
    memory = getattr(observer, "voice_memory", None) or {}
    if not cache:
        return []
    from evennia.utils.search import search_object

    uids = set(uids)
    standing = []
    for key in list(cache):
        if not (isinstance(key, tuple) and len(key) == 2 and cache[key]):
            continue
        dbref, voice_uid = key
        if (memory.get(voice_uid) or {}).get("assigned_name"):
            stands_on = voice_uid
        else:
            found = search_object(dbref) if isinstance(dbref, str) else []
            sleeve = next((getattr(obj, "sleeve_uid", None) for obj in found
                           if getattr(obj, "sleeve_uid", None)), None)
            named = [uid for uid, entry
                     in find_voice_entries_by_real_sleeve_uid(observer, sleeve)
                     if entry.get("assigned_name")]
            stands_on = named[0] if named else None
        if stands_on in uids:
            standing.append(key)
    return standing


def _older_entry_is_theirs(entry: Any, wanted: str,
                           real_sleeve_uid: str | None) -> bool:
    """Whether a voice entry with no ``named_with`` was named together
    with the face called *wanted* on the body *real_sleeve_uid*.

    Such an entry was written before the look was recorded, by the same
    ``remember`` that named the face, so it carried the face's name and
    the face's body tag. The name has to match. The body tag is read to
    tell two people under one name apart, and it is strict in one
    direction: a voice whose body is known is NOT theirs when the
    face's body is unknown. A face with no body tag was never named in
    person (papers made it), so no voice was named with it; treating
    "unknown" as a match there took a stranger's voice.
    """
    if not wanted:
        return False
    if str((entry or {}).get("assigned_name") or "").strip().lower() != wanted:
        return False
    theirs = (entry or {}).get("real_sleeve_uid")
    return not theirs or (bool(real_sleeve_uid) and theirs == real_sleeve_uid)


def settle_older_voices(observer: Any) -> int:
    """Write, on older voice entries, the look each was named with.

    A voice entry from before ``named_with`` was recorded was written by
    the same ``remember`` that named a face: it carried that face's
    name and that face's body tag. While it still matches exactly ONE
    face entry by both, that face is the look it was named with, and
    this writes it down. Run at the start of every ``remember`` and
    ``forget`` (#3825), before anything is written.

    It has to be settled early because the match does not last.
    Naming in person renames the face always and the voice only when
    it is heard; papers rename a face and never its voice; and papers
    can put a second face under a name already in use. After any of
    those, name and body no longer say which look a voice belongs
    with. Marking at each of those moments was tried and got it wrong
    by lending a papers-made face the body of whoever stood there
    (review round four). Settled beforehand, none of them can move it.

    A voice that matches no face, or more than one, is left as it is,
    and `forget` falls back to :func:`_older_entry_is_theirs` for it.
    Every named voice in the live world on 2026-11-14 matched exactly
    one. Returns the number of entries marked.
    """
    voices = getattr(observer, "voice_memory", None)
    faces = getattr(observer, "recognition_memory", None)
    if not voices or not faces:
        return 0
    marked = 0
    for entry in voices.values():
        if not entry or entry.get("named_with"):
            continue
        wanted = str(entry.get("assigned_name") or "").strip().lower()
        body = entry.get("real_sleeve_uid")
        if not wanted or not body:
            continue
        matches = [uid for uid, face in faces.items()
                   if (face or {}).get("real_sleeve_uid") == body
                   and str((face or {}).get("assigned_name") or "").strip().lower()
                   == wanted]
        if len(matches) == 1:
            entry["named_with"] = matches[0]
            marked += 1
    if marked:
        observer.voice_memory = voices
    return marked


def erase_voices_named(observer: Any, name: str, *,
                       look_uid: str | None = None,
                       real_sleeve_uid: str | None = None) -> int:
    """Erase the voice entries *observer* learned together with one look.

    The voice half of forgetting (#3825), called by
    :func:`world.identity.erase_look`. A voice is given a name in one
    place only, ``remember <somebody in front of you> as <name>``, and
    :func:`remember_voice` records the look it was named with
    (``named_with``). That record is the observer's own connection,
    and it is what is matched: a voice named with the look being
    forgotten goes, whatever either is called by now.

    Not by name alone. Papers can rename a face and leave its voice
    under the old name, so matching names missed the voice of the very
    person being forgotten (#2652 again); and two different people can
    carry one name, so matching names took a stranger's voice.

    An entry written before the look was recorded has no
    ``named_with``. For those the name is all there is to go on, and
    the true body is read only to tell two people under one name apart
    (:func:`_older_entry_is_theirs`). Every named voice in the live
    world on 2026-11-14 was such an entry, and each matched a face of
    the same body by name, and :func:`settle_older_voices` writes the
    look on them while that is still so.

    The entries go, not just their names, and so do the voices placed
    by way of them; a failed attempt to place a voice stays (#3817).
    A voice can have a won verdict and no entry here: the observer
    worked out whose it was and never named it.
    :func:`world.identity.erase_look` tells the observer about such a
    voice as well (#3861, :func:`won_voice_verdicts`).

    It used to be done by true body: forgetting somebody by name
    blanked every named voice of the same body, whatever the observer
    had called it, and forgetting somebody present blanked their
    current voice whatever it was called.

    Returns the number of entries erased.
    """
    wanted = str(name or "").strip().lower()
    memory = getattr(observer, "voice_memory", None)
    if not memory or not (wanted or look_uid):
        return 0
    doomed = []
    for uid, entry in memory.items():
        entry = entry or {}
        learned_with = entry.get("named_with")
        if learned_with:
            if look_uid and learned_with == look_uid:
                doomed.append(uid)
            continue
        if _older_entry_is_theirs(entry, wanted, real_sleeve_uid):
            doomed.append(uid)
    if not doomed:
        return 0
    verdicts = _won_voice_verdicts_standing_on(observer, doomed)
    for uid in doomed:
        del memory[uid]
    observer.voice_memory = memory
    if verdicts:
        cache = observer.db.voice_discern_cache
        for key in verdicts:
            if key in cache:
                del cache[key]
        observer.db.voice_discern_cache = cache
    return len(doomed)


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


def named_voice_entry(observer: Any, target: Any) -> tuple:
    """``(voice uid, entry)``: the named voice entry *observer* would
    place *target*'s current voice by, or ``(None, None)``.

    The heard voice's own entry when it has a name. Otherwise the first
    named voice the observer holds for that body: they know the natural
    voice, and it is disguised now. :func:`attempt_voice_discern` reads
    the name from this entry; whether the observer DOES place the voice
    is that function's roll, not this one's.
    """
    voice_uid = get_apparent_voice_uid(target)
    real_sleeve = getattr(target, "sleeve_uid", None)
    if voice_uid is None or not real_sleeve:
        return None, None
    named = [
        (uid, entry)
        for uid, entry in find_voice_entries_by_real_sleeve_uid(observer, real_sleeve)
        if (entry.get("assigned_name") or "")
    ]
    if not named:
        return None, None
    return next((pair for pair in named if pair[0] == voice_uid), named[0])


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
    # Have we named this person's voice under any presentation? The
    # entry for the *current* presentation first; otherwise any named
    # one (you know their natural voice, they are modulated now).
    _source, bare_entry = named_voice_entry(observer, target)
    if bare_entry is None:
        return None
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
    # Hearing weights the observer's side — the capacity consumer. Read it
    # through the same door as the ``can_hear`` gate three lines up the call
    # chain: ``_read_capacity`` reports the organ, which is 0.0 for destroyed
    # ears whether or not chrome ones replaced them. Multiplying by that raw
    # 0.0 meant a character who passed the gate on their cyber ears could
    # then never place a voice, however well they knew it.
    hearing = hearing_multiplier(observer)
    success = (obs_roll + familiarity) * hearing > (tgt_roll + penalty)

    if cacheable:
        cache[key] = success
        observer.db.voice_discern_cache = cache

    return assigned_name if success else None


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
    if can_see(observer) and not _speaker_concealed(speaker, observer):
        return speaker.get_display_name(observer)
    if can_hear(observer):
        return attempt_voice_discern(observer, speaker) or GENERIC_UNSEEN_SPEAKER
    return GENERIC_UNSEEN_SPEAKER


def _speaker_concealed(speaker, observer) -> bool:
    """Stealth gates the VISUAL attribution channel: a speaker hidden from
    this observer can't be identified by sight, so attribution falls
    through to the voice determination — you can hide your body, not a
    voice someone knows (a modulator handles that). Best-effort: no
    stealth state means not concealed."""
    try:
        from world.stealth import is_hidden_from
        return is_hidden_from(speaker, observer)
    except Exception:  # noqa: BLE001
        return False
