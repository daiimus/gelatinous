"""Death records — the OOC tombstone (DEATH_AND_SLEEVE_LIFECYCLE_SPEC §9).

A sleeve's permanent memorial: **who the sleeve was, born, died.** Engraved on
the OWNING ACCOUNT (``account.db.death_records``) the moment the sleeve is
archived, so it survives everything the mortal loop later does to the body
(cleanup gigs, corpse removal) and everything the sleeve loop does to the
husk. Deliberately minimal — no cause, no location (that's actionable
intelligence and belongs in-game): a name and two dates, everything a
headstone says and everything it doesn't.

Scope: EVERY archived sleeve gets a record (death or manual retirement —
``died`` is simply the archive moment). NPCs get no tombstone: no account,
no player to reminisce. The web "Manage Sleeves" view reads this list;
``corpse_dbref`` is an internal key only, never surfaced, and goes stale
by design once the world removes the body.
"""

from __future__ import annotations

import time
from typing import Any, Optional


def get_records(account: Any) -> list:
    """The account's tombstones (a copy — mutate via the helpers)."""
    return list(getattr(getattr(account, "db", None), "death_records", None) or [])


def _sleeve_born(character: Any) -> Optional[float]:
    """The sleeve's decant moment: ``current_sleeve_birth`` when charcreate
    stamped it, else the object's creation timestamp (true for every sleeve
    ever made — covers pre-charcreate legacy sleeves)."""
    born = getattr(getattr(character, "db", None), "current_sleeve_birth", None)
    if born is not None:
        return born
    created = getattr(character, "date_created", None)
    try:
        return created.timestamp() if created else None
    except (AttributeError, OSError, OverflowError, ValueError):
        return None


def add_record(character: Any, account: Any = None,
               died: Optional[float] = None) -> Optional[dict]:
    """Engrave a tombstone for *character* on its owning account.

    Idempotent per sleeve — re-archiving can never double-engrave. Returns
    the record, or None when there's no account (an NPC: by design, no
    tombstone). ``account`` may be passed explicitly for callers that
    captured it before an unpuppet."""
    account = account or getattr(character, "account", None)
    if account is None:
        return None
    dbref = getattr(character, "dbref", None)
    records = get_records(account)
    for rec in records:
        if rec.get("sleeve_dbref") == dbref:
            return rec
    record = {
        "sleeve_dbref": dbref,
        "name": getattr(character, "key", None),
        "born": _sleeve_born(character),
        "died": died if died is not None else time.time(),
        "corpse_dbref": None,
    }
    records.append(record)
    account.db.death_records = records
    return record


def stamp_corpse(character: Any, corpse: Any, account: Any = None) -> bool:
    """Link the sleeve's tombstone to its body (internal key only). The link
    goes stale once a cleanup gig removes the corpse — by design; the record
    itself never depends on it."""
    account = account or getattr(character, "account", None)
    if account is None or corpse is None:
        return False
    dbref = getattr(character, "dbref", None)
    records = get_records(account)
    for rec in records:
        if rec.get("sleeve_dbref") == dbref:
            rec["corpse_dbref"] = getattr(corpse, "dbref", None)
            account.db.death_records = records
            return True
    return False
