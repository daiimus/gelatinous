"""Security intel — per-bot sightings and the force-wide wanted record.

Crime slice 4 (``NPC_DISPATCH_AND_SIMULATION_SPEC`` §5.1): intel is
**hybrid and syncs at base**. When a responder confirms a high-confidence
identification on scene, that knowledge is **local to the bot**
(``db.local_sightings``) — other units don't know your face yet. Only
when the bot **returns to its post** does its local intel merge into the
**force-wide wanted record** (persistent, ServerConfig-backed). The gap
between the sighting and the sync is the exploitable latency window; a
downed bot never syncs at all (the no-trace seam).

The wanted record is keyed by ``apparent_uid`` — a *presentation*, not a
person. Re-sleeving or a real disguise change yields a fresh UID and a
clean face (§5.2: a clean face costs something). Repeat offenders
accumulate ``count`` — the substrate future heat/priority reads.
"""

from __future__ import annotations

import time
from typing import Any

from evennia.server.models import ServerConfig

#: ServerConfig key for the persistent force-wide record.
WANTED_KEY = "director_wanted_record"


# --------------------------------------------------------------------------
# Force-wide wanted record (persistent)
# --------------------------------------------------------------------------

def get_wanted_record() -> dict:
    """The force-wide record: ``{apparent_uid: {count, last_crime,
    last_synced}}``. Empty dict when nothing is on file."""
    return ServerConfig.objects.conf(WANTED_KEY) or {}


def is_wanted(uid: str | None) -> dict | None:
    """The record entry for *uid*, or ``None`` if not on file."""
    if not uid:
        return None
    return get_wanted_record().get(uid)


def clear_wanted_record() -> None:
    """Wipe the force-wide record (builder/diagnostic use)."""
    ServerConfig.objects.conf(WANTED_KEY, delete=True)


def _save(record: dict) -> None:
    ServerConfig.objects.conf(WANTED_KEY, record)


# --------------------------------------------------------------------------
# Per-bot local sightings (the pre-sync knowledge)
# --------------------------------------------------------------------------

def log_local_sighting(bot: Any, uid: str | None, crime_type: str) -> None:
    """A confirmed on-scene identification, known only to *bot* until it
    syncs at its post."""
    if not uid or bot is None:
        return
    local = dict(getattr(bot.db, "local_sightings", None) or {})
    entry = dict(local.get(uid) or {"count": 0})
    entry["count"] = int(entry.get("count", 0)) + 1
    entry["last_crime"] = crime_type
    entry["seen_at"] = time.time()
    local[uid] = entry
    bot.db.local_sightings = local


def sync_bot_intel(bot: Any) -> int:
    """The bot is back at base: merge its local sightings into the
    force-wide record and clear them. Returns how many identifications
    were synced. A bot that never makes it back never syncs."""
    local = dict(getattr(bot.db, "local_sightings", None) or {})
    if not local:
        return 0
    record = dict(get_wanted_record())
    for uid, sighting in local.items():
        entry = dict(record.get(uid) or {"count": 0})
        entry["count"] = int(entry.get("count", 0)) + int(sighting.get("count", 1))
        entry["last_crime"] = sighting.get("last_crime")
        entry["last_synced"] = time.time()
        record[uid] = entry
    _save(record)
    bot.db.local_sightings = {}
    return len(local)
