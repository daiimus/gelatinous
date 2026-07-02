"""Patrol routines — the director's heartbeat walking NPCs on beats.

Dispatch-spec Phase 2 (roles & routines), first consumer: security bots
with a **base of operations**. Three ideas:

* **Post** (``db.post``) — the NPC's base room. A posted NPC's dispatch
  assignments return it *there* (not wherever it happened to stand), so
  "returns to base and syncs intel" becomes literal geography.
* **Beat** (``db.patrol_beat``) — an ordered list of rooms the NPC walks
  in a loop, base included implicitly at the top of every cycle.
  Builder-authored (``@patrol/beat``) or coordinate-sampled
  (``@patrol/auto``).
* **The heartbeat** — a persistent Evennia script ticks every
  ``HEARTBEAT_SECONDS`` and *nudges* idle patrollers one step: not at the
  next waypoint → travel there (director ``travel_to``, real exits);
  arrived → run the waypoint hook, advance the index. No delay-chains to
  die on reload: the script survives restarts and simply resumes nudging.

**Patrol→Detect composition:** on waypoint arrival a security NPC runs
the wanted-scan; a flagged face raises a ``disturbance`` event on the
spot — dispatch assigns (usually the patroller itself, distance 0) and
the existing challenge/aim/watch machinery takes over. Detect costs no
new behavior code.

Anything urgent always preempts: an assigned, travelling, or fighting
NPC is skipped by the heartbeat until it is free again.
"""

from __future__ import annotations

from typing import Any

from evennia import DefaultScript

from world.director.assignment import is_assigned
from world.director.travel import is_travelling, travel_to

#: Seconds between heartbeat ticks (also the linger at each waypoint).
HEARTBEAT_SECONDS = 45
#: Global script key.
SCRIPT_KEY = "director_routines"


# --------------------------------------------------------------------------
# Beat state helpers
# --------------------------------------------------------------------------

def get_beat(npc: Any) -> list:
    """The NPC's patrol cycle: ``[post] + beat rooms`` (post-anchored so
    every loop passes through base). Empty when it has no beat."""
    beat = list(getattr(npc.db, "patrol_beat", None) or [])
    if not beat:
        return []
    post = getattr(npc.db, "post", None)
    if post is not None and post not in beat:
        beat.insert(0, post)
    return [room for room in beat if room is not None]


def _in_combat(npc: Any) -> bool:
    from world.director.security import _in_combat as check
    return check(npc)


def is_patrol_idle(npc: Any) -> bool:
    """Free to take a patrol step: not assigned, not mid-travel, not
    fighting, and actually somewhere."""
    return (npc.location is not None
            and not is_assigned(npc)
            and not is_travelling(npc)
            and not _in_combat(npc))


# --------------------------------------------------------------------------
# The tick
# --------------------------------------------------------------------------

def tick_npc(npc: Any) -> str:
    """Advance one NPC's patrol by one nudge. Returns what happened
    (for diagnostics): ``skip`` / ``travel`` / ``waypoint`` / ``none``."""
    beat = get_beat(npc)
    if not beat:
        return "none"
    if not is_patrol_idle(npc):
        return "skip"
    idx = int(getattr(npc.ndb, "patrol_idx", None) or 0) % len(beat)
    waypoint = beat[idx]
    if npc.location != waypoint:
        travel_to(npc, waypoint)
        return "travel"
    # Arrived: run the waypoint hook, then aim for the next stop.
    npc.ndb.patrol_idx = (idx + 1) % len(beat)
    at_waypoint(npc)
    return "waypoint"


def at_waypoint(npc: Any) -> None:
    """Waypoint hook. Security: sweep for wanted faces — a hit raises a
    ``disturbance`` on the spot and the dispatch/challenge machinery
    (usually assigning this very patroller) takes it from there."""
    if getattr(getattr(npc, "db", None), "role", None) != "security":
        return
    try:
        from world.director.dispatch import WorldEvent, raise_event
        from world.director.security import _scan_wanted
        _uid, flagged, _entry = _scan_wanted(npc)
        if flagged is not None:
            raise_event(WorldEvent("disturbance", npc.location,
                                   severity=1, source=flagged))
        else:
            npc.execute_cmd("emote pans a slow sensor sweep across the "
                            "street and moves on.")
    except Exception:  # noqa: BLE001 — a bad sweep must not stall the beat
        pass


def tick_all() -> dict:
    """One heartbeat over every NPC with a beat. Returns counts by
    outcome (diagnostics)."""
    from evennia.objects.models import ObjectDB
    counts: dict = {}
    for npc in ObjectDB.objects.filter(
            db_attributes__db_key="patrol_beat").distinct():
        try:
            outcome = tick_npc(npc)
        except Exception:  # noqa: BLE001 — one broken bot must not stall all
            outcome = "error"
        counts[outcome] = counts.get(outcome, 0) + 1
    return counts


# --------------------------------------------------------------------------
# The heartbeat script
# --------------------------------------------------------------------------

class DirectorRoutineScript(DefaultScript):
    """Persistent global heartbeat driving all patrol beats."""

    def at_script_creation(self):
        self.key = SCRIPT_KEY
        self.desc = "Director heartbeat: walks NPCs on their patrol beats."
        self.interval = HEARTBEAT_SECONDS
        self.persistent = True

    def at_repeat(self):
        tick_all()
        try:
            from world.director.population import maintain_security_complement
            maintain_security_complement()
        except Exception:  # noqa: BLE001 — respawn must not stall the beats
            pass


def ensure_heartbeat() -> Any:
    """Get-or-create the global heartbeat script (idempotent; called by
    ``@patrol`` so the first beat ever set starts the engine)."""
    from evennia import create_script
    from evennia.scripts.models import ScriptDB
    existing = ScriptDB.objects.filter(db_key=SCRIPT_KEY).first()
    if existing:
        if not existing.is_active:
            existing.start()
        return existing
    return create_script(
        "world.director.routines.DirectorRoutineScript",
        key=SCRIPT_KEY, persistent=True, autostart=True)
