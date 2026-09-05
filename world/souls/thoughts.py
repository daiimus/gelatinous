"""Thoughts & mood (spec §11) — the soul notices its own life.

A thought is a small record emitted when something happens TO the soul
— never on a timer. Mood is the clamped, half-life-decayed sum of the
log, DERIVED on read; no mood attribute exists (the zero-write law
survives the feelings layer).

Significant thoughts on llm_driven souls also become general-subject
episodic records through the existing embed path, so conversation
retrieval surfaces them organically — the thought decided nothing;
the voice narrates a state the engine produced.
"""

import time

THOUGHT_CAP = 20
STACK_CAP = 3                        # same-key thoughts held at once — a
                                     # persisting condition refreshes its
                                     # thought, it doesn't flood the log
HALFLIFE_SECONDS = 6 * 3600          # a thought fades by half in ~6h
RAG_THRESHOLD = 0.2                  # |valence| worth remembering aloud

MOOD_BANDS = (                       # (floor, label) — first match wins
    (0.25, "bright"),
    (-0.10, "level"),
    (-0.40, "low"),
    (-10.0, "grim"),
)


#: A wound fades in days rather than hours. Acting against your own
#: nature is meant to follow you around a while (NPC_TRAITS_SPEC §4).
WOUND_HALFLIFE = 3 * 24 * 3600

#: Keys recorded as wounds. Kept as data so the set can grow (grief,
#: betrayal) without touching the decay maths.
WOUND_KEYS = {"against_my_nature"}

#: Where a soul's OWN wound keys live. `WOUND_KEYS` above is the shared
#: baseline; anything recorded with `wound=True` is added here, on the
#: soul, so it survives a reload. It used to be added to the module set
#: instead — which died with the process, silently dropping a grudge from
#: a three-day half-life to six hours, and which was shared, so the first
#: soul to record a key made it a wound for everyone (#2783).
_WOUND_ATTR = "soul_wound_keys"


def _wound_keys(soul):
    """The keys that decay slowly FOR THIS SOUL."""
    try:
        own = set(getattr(soul.db, _WOUND_ATTR, None) or ())
    except Exception:  # noqa: BLE001 — an unreadable body has no wounds
        own = set()
    return WOUND_KEYS | own


def _mark_wound(soul, key):
    try:
        own = set(getattr(soul.db, _WOUND_ATTR, None) or ())
        if key not in own:
            own.add(key)
            setattr(soul.db, _WOUND_ATTR, sorted(own))
    except Exception:  # noqa: BLE001 — never block a feeling on bookkeeping
        pass


def add_thought(soul, key, valence, note="", wound=False):
    """Record a thought; feed the RAG memory when it's significant.
    Same-key entries are capped at STACK_CAP (newest kept), so a
    condition that persists — broke and hungry for six hours — reads
    as ONE sustained misery, not twenty, and can't flood every other
    memory out of the log."""
    if wound:
        _mark_wound(soul, key)
    log = list(soul.db.soul_thoughts or [])
    log.append((time.time(), key, float(valence), note))
    same = [t for t in log if t[1] == key]
    if len(same) > STACK_CAP:
        for stale in same[:-STACK_CAP]:
            log.remove(stale)
    soul.db.soul_thoughts = log[-THOUGHT_CAP:]
    if abs(valence) >= RAG_THRESHOLD and soul.db.llm_driven and note:
        _feed_rag(soul, note)


def _feed_rag(soul, note):
    """Write the thought as a general-subject episodic record via the
    existing embed->make_record->prune path (fire-and-forget; the
    memory module surfaces empty-subject records in any scoped
    conversation when they're semantically relevant)."""
    try:
        from evennia.utils.dbserialize import deserialize
        from world.llm import memory as mem
        from world.llm.client import llm_enabled, request_embedding

        if not llm_enabled():
            return
        text = f"I remember: {note}."

        def _save(vec):
            try:
                # THROUGH `remember`, not around it. This called
                # `make_record` and `prune` — the two helpers `remember`
                # wraps — and skipped the DEDUPLICATION in the middle,
                # so every thought was appended as a new record whether
                # or not that exact sentence was already stored.
                #
                # Not merely wasted rows: `prune` enforces a per-subject
                # cap, so duplicates EVICT real memories. A soul that
                # keeps having the same thought spends its whole
                # recollection budget on one sentence and genuinely
                # forgets everything else — which is precisely the
                # damage build 118 was written to repair, and it had
                # fully returned: 79% of 2,170 live records were
                # duplicates (#2707, #2242).
                #
                # `remember` also bumps last_seen/uses on a repeat,
                # which is what `salience` rewards — so a repeated
                # experience becomes a STRONG memory instead of a crowd
                # of weak identical ones.
                recs = deserialize(soul.db.llm_memories) or []
                soul.db.llm_memories = mem.remember(recs, text, vec,
                                                    subject="")
            except Exception:   # noqa: BLE001 — memory is best-effort
                pass

        request_embedding(text, on_done=_save, on_fail=lambda *a: None)
    except Exception:           # noqa: BLE001 — never let a feeling crash a beat
        pass


def _weight(key, age, soul=None):
    """How much a thought of this key still counts after `age` seconds.

    The ONE decay rule. Mood and opinion both read it, so a wound fades
    slowly in both or in neither — two half-lives for the same feeling
    would be two doors onto one decision."""
    keys = _wound_keys(soul) if soul is not None else WOUND_KEYS
    half = WOUND_HALFLIFE if key in keys else HALFLIFE_SECONDS
    return 0.5 ** (max(0.0, age) / half)


def decayed(soul, now=None):
    """[(age_weighted_valence, key, note, age_seconds)] for the log."""
    now = now if now is not None else time.time()
    out = []
    for stamp, key, valence, note in (soul.db.soul_thoughts or []):
        age = now - stamp
        out.append((valence * _weight(key, age, soul), key, note, age))
    return out


def mood(soul, now=None):
    """Clamped sum of decayed valences. Pure read."""
    total = sum(v for v, *_ in decayed(soul, now))
    return max(-1.0, min(1.0, total))


def mood_band(value):
    for floor, label in MOOD_BANDS:
        if value >= floor:
            return label
    return "grim"


# ---------------------------------------------------------------------------
# Opinion — the same feeling, pointed at a PERSON
# ---------------------------------------------------------------------------
#
# Mood is what a soul thinks of its life; opinion is what it thinks of YOU.
# Both are the decayed sum of things that happened, derived on read, and both
# run through `_weight` so a grudge and a bad mood age at one rate.
#
# It lives in its own attribute rather than sharing `soul_thoughts` because
# that log is capped at 20 for the soul's OWN life. A bartender who meets a
# dozen patrons in a night would evict her own payday and hunger to make room
# for acquaintances — sociability would quietly degrade mood. Per-person
# storage also lets two people both be "generous" without the stack cap
# treating them as the same thought.
#
# NOTHING GATES ON THIS YET, deliberately. Opinion is something souls HAVE
# before it is something that decides anything: no system in the colony has
# been balance-tuned, and refusing service or moving prices off an untuned
# score is how you get a colony that hates everyone. See NPC_TRAITS_SPEC §12.

OPINION_STACK_CAP = 3        # same key about the same person
OPINION_CAP = 6              # entries kept per person
ACQUAINTANCE_CAP = 24        # people tracked at once; least-recent evicted
MOOD_SHARE = 0.35            # how much of a personal event also colours the day

OPINION_BANDS = (            # (floor, label) — first match wins
    (0.40, "warm"),
    (0.10, "friendly"),
    (-0.10, "neutral"),
    (-0.40, "wary"),
    (-10.0, "hostile"),
)


def _opinions(soul):
    from evennia.utils.dbserialize import deserialize
    return deserialize(soul.db.soul_opinions) or {}


def add_opinion(soul, uid, key, valence, note="", wound=False,
                mood_share=MOOD_SHARE):
    """Record that `uid` did something that moves this soul's read on them.

    Also nudges the general mood at `mood_share` of the weight (owner
    ruling 2026-08-29): being robbed at knifepoint should dent your day,
    not merely your opinion of the robber. Pass ``mood_share=0`` for
    something that is genuinely only about that person.
    """
    uid = str(uid or "").strip()
    if not uid or not valence:
        return
    if wound:
        _mark_wound(soul, key)
    book = _opinions(soul)
    entries = [tuple(e) for e in (book.get(uid) or [])]
    entries.append((time.time(), key, float(valence), note))

    # dedupe within this person only — A being generous must not evict B
    same = [e for e in entries if e[1] == key]
    for stale in same[:-OPINION_STACK_CAP]:
        entries.remove(stale)
    book[uid] = entries[-OPINION_CAP:]

    if len(book) > ACQUAINTANCE_CAP:
        # forget the least recently FELT-ABOUT person, not the oldest
        # acquaintance: someone seen daily stays known, someone met once a
        # year ago does not.
        def _last(item):
            return max((e[0] for e in item[1]), default=0.0)
        for uid_out, _ in sorted(book.items(), key=_last)[
                :len(book) - ACQUAINTANCE_CAP]:
            book.pop(uid_out, None)
    soul.db.soul_opinions = book

    if mood_share:
        add_thought(soul, key, float(valence) * mood_share, note, wound=wound)


def opinion_of(soul, uid, now=None):
    """Clamped, decayed sum of what `uid` has done to this soul. Pure read —
    no attribute holds it, exactly as with mood."""
    uid = str(uid or "").strip()
    if not uid:
        return 0.0
    now = now if now is not None else time.time()
    entries = _opinions(soul).get(uid) or []
    total = sum(float(v) * _weight(k, now - t, soul) for t, k, v, _n in
                (tuple(e) for e in entries))
    return max(-1.0, min(1.0, total))


def opinion_band(value):
    for floor, label in OPINION_BANDS:
        if value >= floor:
            return label
    return "hostile"


def opinion_note(soul, uid, now=None):
    """The strongest surviving reason behind the current opinion, for a
    voice to cite. Returns '' when there is nothing worth saying."""
    uid = str(uid or "").strip()
    if not uid:
        return ""
    now = now if now is not None else time.time()
    best, best_note = 0.0, ""
    for e in (_opinions(soul).get(uid) or []):
        stamp, key, valence, note = tuple(e)
        weighted = abs(float(valence) * _weight(key, now - stamp, soul))
        if note and weighted > best:
            best, best_note = weighted, note
    return best_note
