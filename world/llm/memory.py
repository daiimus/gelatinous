"""Long-term NPC memory (LLM Gamemaster Phase 2) — portable core.

Per-NPC semantic memory: short text records, each carrying an embedding vector
(produced by the sidecar's embedder). Retrieval is **exact cosine top-k** at this
scale — a handful of NPCs, hundreds–thousands of records each — so there's no ANN
index, just a scan over the NPC's own records. Storage/IO and the embed round-trip
live in the game layer (records are an Evennia attribute; embeddings come from the
sidecar); this module is pure functions over record dicts + query vectors, so it's
testable with no model and no Evennia.

A record is a plain JSON/Attribute-safe dict::

    {"text": str, "embedding": [float], "subject": str,
     "created": float, "last_seen": float, "uses": int}

``subject`` scopes a memory to an interlocutor (e.g. their stable uid/key); an
empty subject is a general memory available to everyone.
"""

import math
import time

#: Recency half-life for salience (seconds) — a memory not recalled for this long
#: is worth half as much when pruning. One week of game/real time by default.
RECENCY_HALFLIFE = 7 * 24 * 3600.0

#: Default per-subject cap; forgetting drops the least-salient beyond this.
DEFAULT_CAP_PER_SUBJECT = 30


def make_record(text, embedding, subject="", now=None):
    """Build a fresh memory record (plain dict)."""
    now = time.time() if now is None else now
    return {
        "text": text,
        "embedding": list(embedding or []),
        "subject": subject or "",
        "created": now,
        "last_seen": now,
        "uses": 0,
    }


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _norm(a):
    return math.sqrt(sum(x * x for x in a)) or 1.0


def cosine(a, b):
    """Cosine similarity of two equal-length vectors; 0 for empty/missing."""
    if not a or not b:
        return 0.0
    return _dot(a, b) / (_norm(a) * _norm(b))


def salience(record, now=None):
    """A record's keep-worthiness: recency decay + a small use-count bonus."""
    now = time.time() if now is None else now
    age = max(0.0, now - record.get("last_seen", record.get("created", now)))
    recency = 0.5 ** (age / RECENCY_HALFLIFE)
    return recency + 0.1 * record.get("uses", 0)


def retrieve(query_vec, records, k=3, subject=None, now=None):
    """Return the ``k`` records most similar to ``query_vec`` (cosine).

    When ``subject`` is given, only that subject's records + general (empty-
    subject) records are considered, so "what I recall about *this* person"
    ranks above unrelated chatter. Records with non-positive similarity are
    dropped. The returned records are bumped (``last_seen``/``uses``) so recall
    feeds salience — frequently-relevant memories survive pruning.
    """
    now = time.time() if now is None else now
    pool = [r for r in records
            if subject is None or not r.get("subject") or r.get("subject") == subject]
    scored = [(cosine(query_vec, r.get("embedding") or []), r) for r in pool]
    scored.sort(key=lambda sr: sr[0], reverse=True)
    hits = [r for sim, r in scored[:k] if sim > 0.0]
    for r in hits:
        r["last_seen"] = now
        r["uses"] = r.get("uses", 0) + 1
    return hits


def prune(records, cap_per_subject=DEFAULT_CAP_PER_SUBJECT, now=None):
    """Forgetting: keep the most-salient ``cap_per_subject`` records per subject."""
    now = time.time() if now is None else now
    by_subject = {}
    for r in records:
        by_subject.setdefault(r.get("subject", ""), []).append(r)
    kept = []
    for recs in by_subject.values():
        recs.sort(key=lambda r: salience(r, now), reverse=True)
        kept.extend(recs[:cap_per_subject])
    return kept


def memory_texts(records):
    """The text lines of a record list, for prompt injection."""
    return [r["text"] for r in records if r.get("text")]
