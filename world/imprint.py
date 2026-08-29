"""The imprint — what a person is, as of their last backup.

ONE implementation, used by every resleeve path. NPC post-holders
(`world/souls/posts.py`) and player flash clones
(`commands/charcreate.py`) capture and restore through exactly these
functions, so the two can never drift into different rules about what
survives a death.

That sameness is the point. When backups become something a character
DOES at a terminal (`specs/proposals/BACKUPS_AND_MEMORY_FORGERY_SPEC`),
the only change is *when* `capture()` runs and *where* the record is
stored. Nothing about what a record contains, or how a body is
rehydrated from one, has to be touched — and it will land for players
and NPCs simultaneously, because there is only one path.

The record:

    version      schema marker
    name         who this is
    sleeve_uid   the BODY — recognition resolves through it, and a
                 clone inherits it (IDENTITY_RECOGNITION_SPEC §Sleeve)
    died_at      when the body stopped
    taken_at     what the backup HELD — THE field restore keys on
    memories     episodic (LLM cast only)
    dossiers     conclusions about people (LLM cast only)
    thoughts     interiority (souls only)
    opinions     what they made of PEOPLE (souls only) — the per-person
                 half of the same feeling `thoughts` holds. A record
                 written before the opinion layer (#2388) simply has
                 none, which restores correctly.
    recognition  who they knew by FACE
    voice        who they knew by VOICE

`taken_at` is derived from `GAP` today. It is a stored field rather
than a recomputation precisely so that an on-demand backup can set it
to the moment somebody pressed the button, and no restore logic
changes.
"""

import time
from datetime import datetime

#: How much never made the backup. Today a constant; later, the
#: distance between a death and the last time that person bothered.
GAP = 5400


def capture(character, now=None):
    """The imprint of *character*, as of their last backup."""
    from evennia.utils.dbserialize import deserialize

    now = time.time() if now is None else float(now)

    def _prop(name, default):
        """AttributeProperty — categorised, so `.db.x` would miss it."""
        try:
            return deserialize(getattr(character, name, None)) or default
        except Exception:  # noqa: BLE001 — a partial imprint beats none
            return default

    def _db(name, default):
        try:
            return deserialize(getattr(character.db, name, None)) or default
        except Exception:  # noqa: BLE001
            return default

    return {
        "version": 1,
        "name": character.key,
        "sleeve_uid": getattr(character, "sleeve_uid", None),
        "died_at": now,
        "taken_at": now - GAP,
        "memories": _db("llm_memories", []),
        "dossiers": _db("llm_dossiers", {}),
        "thoughts": _db("soul_thoughts", []),
        "opinions": _db("soul_opinions", {}),
        "recognition": _prop("recognition_memory", {}),
        "voice": _prop("voice_memory", {}),
    }


def remembered_before(entries, cutoff):
    """Acquaintances that existed as of the backup.

    Recognition and voice entries are keyed by Apparent UID and carry
    an ISO ``first_seen``. Somebody first met INSIDE the gap was never
    written to the backup, so they come back a stranger — the gap
    applied to people instead of episodes. That stranger may well be
    why you died, which is the interesting part.

    An entry with no readable ``first_seen`` is KEPT: losing a
    relationship to a malformed field costs more than it protects.
    """
    out = {}
    for uid, entry in (entries or {}).items():
        if not isinstance(entry, dict):
            continue
        try:
            met = datetime.fromisoformat(str(entry.get("first_seen"))).timestamp()
        except (TypeError, ValueError):
            out[uid] = entry
            continue
        if met < cutoff:
            out[uid] = entry
    return out


def cutoff_of(snap, fallback_now=None):
    """When the backup was taken. Records written before ``taken_at``
    existed derive it the old way, so nothing on disk breaks."""
    taken = (snap or {}).get("taken_at")
    if taken is not None:
        return float(taken)
    died = (snap or {}).get("died_at")
    if died is None:
        died = time.time() if fallback_now is None else float(fallback_now)
    return float(died) - GAP


def restore(body, snap, now=None):
    """Rehydrate *body* from an imprint record.

    Applies only what the record holds, so a player (no episodic brain)
    and a soul (episodic brain, dossiers, interiority) both come
    through this one function and each gets what applies to them.
    """
    if not snap:
        return False
    cutoff = cutoff_of(snap, now)

    # The body comes back as the same sleeve, so the people who knew
    # that face still know it. A rebuild that mints a fresh uid returns
    # a stranger wearing its own name.
    uid = snap.get("sleeve_uid")
    if uid and getattr(body, "sleeve_uid", None) != uid:
        body.sleeve_uid = uid

    if snap.get("memories"):
        body.db.llm_memories = [
            r for r in snap["memories"]
            if float(r.get("created", 0) or 0) < cutoff]
    if snap.get("dossiers"):
        body.db.llm_dossiers = dict(snap["dossiers"])
    if snap.get("thoughts"):
        body.db.soul_thoughts = [
            t for t in snap["thoughts"] if float(t[0]) < cutoff]
    if snap.get("opinions"):
        # Same cutoff as thoughts, per person: what you had already
        # concluded about someone survives; what they did to you inside
        # the backup gap is gone with the rest of that stretch. A person
        # who has nothing left is dropped rather than kept as an empty
        # acquaintance.
        kept = {}
        for uid, entries in (snap["opinions"] or {}).items():
            fresh = [tuple(e) for e in entries
                     if float(tuple(e)[0]) < cutoff]
            if fresh:
                kept[uid] = fresh
        body.db.soul_opinions = kept

    # ...and who they knew, by face and by voice, on the same terms.
    body.recognition_memory = remembered_before(
        snap.get("recognition") or {}, cutoff)
    body.voice_memory = remembered_before(snap.get("voice") or {}, cutoff)
    return True
