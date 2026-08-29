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


def remember(records, text, embedding, subject="", now=None):
    """Add *text* to *records* — or, if it is already remembered, remember
    it HARDER.

    The same thing happening twice is one memory recalled twice, not two
    memories. Appending blindly made an NPC's recollection into a tally:
    a dispatcher stuck in a travel fault accumulated 29 identical copies
    of "nothing to eat I could reach or afford", which is `cap_per_subject`
    minus one — so prune spent almost the whole budget on one sentence and
    genuinely forgot everything else to keep it (#2242).

    Recall bumps `last_seen`/`uses`, which is exactly what `salience`
    rewards, so a thing that keeps happening becomes a strong memory
    rather than a crowd of weak identical ones.
    """
    now = time.time() if now is None else now
    key = " ".join(str(text or "").split())
    subject = subject or ""
    for rec in records:
        if (rec.get("subject", "") == subject
                and " ".join(str(rec.get("text") or "").split()) == key):
            rec["last_seen"] = now
            rec["uses"] = rec.get("uses", 0) + 1
            return prune(records, now=now)
    records.append(make_record(text, embedding, subject=subject, now=now))
    return prune(records, now=now)


def is_retrievable(record):
    """Can this record ever come back? Only if it carries a vector.

    A record written while the embedder was unreachable has none, so
    `cosine` scores it 0 and `retrieve` drops it. It is kept for its
    TEXT — an NPC's mind should not be empty just because the sidecar
    was down when they lived through something (#2360) — but it cannot
    contribute to a reply until it is backfilled."""
    return bool(record.get("embedding"))


def prune(records, cap_per_subject=DEFAULT_CAP_PER_SUBJECT, now=None):
    """Forgetting: keep the most-salient ``cap_per_subject`` per subject.

    Retrievable records outrank unretrievable ones regardless of age. A
    vectorless record is recent, and recency is most of salience, so
    ranking on salience alone would have a spell of embedder downtime
    quietly evict everything an NPC could actually recall and replace it
    with records that can never surface."""
    now = time.time() if now is None else now
    by_subject = {}
    for r in records:
        by_subject.setdefault(r.get("subject", ""), []).append(r)
    kept = []
    for recs in by_subject.values():
        recs.sort(key=lambda r: (is_retrievable(r), salience(r, now)),
                  reverse=True)
        kept.extend(recs[:cap_per_subject])
    return kept


def memory_texts(records):
    """The text lines of a record list, for prompt injection."""
    return [r["text"] for r in records if r.get("text")]
