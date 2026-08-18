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


def add_thought(soul, key, valence, note=""):
    """Record a thought; feed the RAG memory when it's significant.
    Same-key entries are capped at STACK_CAP (newest kept), so a
    condition that persists — broke and hungry for six hours — reads
    as ONE sustained misery, not twenty, and can't flood every other
    memory out of the log."""
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
                recs = deserialize(soul.db.llm_memories) or []
                recs.append(mem.make_record(text, vec, subject=""))
                soul.db.llm_memories = mem.prune(recs)
            except Exception:   # noqa: BLE001 — memory is best-effort
                pass

        request_embedding(text, on_done=_save, on_fail=lambda *a: None)
    except Exception:           # noqa: BLE001 — never let a feeling crash a beat
        pass


def decayed(soul, now=None):
    """[(age_weighted_valence, key, note, age_seconds)] for the log."""
    now = now if now is not None else time.time()
    out = []
    for stamp, key, valence, note in (soul.db.soul_thoughts or []):
        weight = 0.5 ** (max(0.0, now - stamp) / HALFLIFE_SECONDS)
        out.append((valence * weight, key, note, now - stamp))
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
