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

#: Patrol-sweep locale by room type (user note 2026-07-10: the hardcoded
#: "across the street" read wrong indoors). Unknown types stay ambiguous.
_SWEEP_LOCALES = {
    "street": "across the street",
    "intersection": "across the crossing",
    "alley": "down the alley",
    "corridor": "down the corridor",
    "bridge": "along the span",
    "sky": "across the open air",
    "interior": "across the room",
    "constabulary": "across the floor",
    "shaft": "up the shaft",
}


def _sweep_locale(room) -> str:
    """The right patch of world for a sensor sweep to pan across."""
    rtype = str(getattr(getattr(room, "db", None), "type", "") or "").lower()
    return _SWEEP_LOCALES.get(rtype, "across its surroundings")
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


def _is_conversing(npc: Any) -> bool:
    """Mid-conversation with a player (the LLM engagement hold): the NPC
    defers its routine until the model calls ``release`` or the hold's
    inactivity window lapses — nobody walks out of an exchange because a
    heartbeat said so."""
    from time import monotonic
    until = getattr(getattr(npc, "ndb", None), "llm_engaged_until", None)
    return bool(until and until > monotonic())


def is_patrol_idle(npc: Any) -> bool:
    """Free to take a patrol step: not assigned, not mid-travel, not
    fighting, not mid-conversation, no active soul job, and actually
    somewhere. Patrol is the IDLE filler — the full precedence order is
    combat > dispatch assignment > souls > patrol (souls spec §12), so
    a unit recharging on its cradle is not yanked back onto the beat."""
    return (npc.location is not None
            and not is_assigned(npc)
            and not is_travelling(npc)
            and not _in_combat(npc)
            and not _is_conversing(npc)
            and not getattr(npc.db, "soul_job", None))


# --------------------------------------------------------------------------
# The tick
# --------------------------------------------------------------------------

def tick_npc(npc: Any) -> str:
    """Advance one NPC's patrol by one nudge. Returns what happened
    (for diagnostics): ``skip`` / ``wait`` / ``travel`` / ``waypoint`` /
    ``souls`` / ``hunt`` / ``none``.

    A SOULED body returns ``souls`` rather than being WALKED here: it
    takes its beat through the souls engine now (#2373). The hunt still
    runs first and still drives the body, because a hunt is a security
    RESPONSE rather than idle drift — it is the last thing this tick
    moves, and the last piece of criterion 9. The walking fallback below
    is for an unsouled body, which nothing in the colony currently is.

    * **Cadence** (``db.patrol_cadence``, default 1): act only every Nth
      tick — civilians drift at a stroll while security marches. Now
      consulted by the souls band tree too, through `cadence_ready`.
    * **Stagger**: a fresh/reloaded NPC starts at a *random* beat index,
      so multiple units on the same loop spread out instead of walking
      in lockstep. Lives in `next_waypoint`, shared by both.
    """
    beat = get_beat(npc)
    if not beat:
        return "none"
    if not is_patrol_idle(npc):
        return "skip"
    # The hunt owns an idle security unit before the beat does (stealth
    # spec §5): awareness records of hidden presences turn the patroller
    # into a hunter until it reacquires or gives up.
    if getattr(npc.db, "role", None) == "security":
        try:
            from world.director.hunt import tick_hunt
            if tick_hunt(npc):
                return "hunt"
        except Exception:  # noqa: BLE001 — a broken hunt must not stall beats
            pass
    # THE FEET MOVED. Walking the beat is a souls goal now (band 4, the
    # idle filler this always described itself as) — see
    # `actions._patrol_plan`. This module still owns what a beat IS, the
    # stagger, the cadence and what happens at a stop; it just no longer
    # drives the body, because after the population merge every patrolled
    # body was ALSO a soul and two schedulers were walking the same 46
    # people, coordinating by reading each other's attributes (#2373).
    #
    # An UNSOULED body on a beat would go nowhere, so it still walks
    # here. Nothing in the colony is in that state today; this is the
    # honest fallback rather than a silent assumption.
    if _is_souled(npc):
        return "souls"
    if not cadence_ready(npc):
        return "wait"
    waypoint, idx = next_waypoint(npc)
    if waypoint is None:
        return "none"
    if npc.location != waypoint:
        npc.ndb.patrol_idx = idx            # keep aiming here
        travel_to(npc, waypoint)
        return "travel"
    advance_waypoint(npc)
    at_waypoint(npc)
    return "waypoint"


def _is_souled(npc: Any) -> bool:
    """Does the souls engine own this body's feet?

    Defensive: a body with no tag handler is not a soul. Fails toward
    "the director still walks it", so a body nothing else drives keeps
    moving rather than freezing in the street.
    """
    from world.souls.engine import SOUL_TAG
    tags = getattr(npc, "tags", None)
    if tags is None:
        return False
    try:
        return bool(tags.get(SOUL_TAG[0], category=SOUL_TAG[1]))
    except Exception:  # noqa: BLE001 — an unreadable tag is not a soul
        return False


def next_waypoint(npc: Any):
    """The waypoint this NPC is currently walking to, and its index.

    Extracted so the souls planner and this module cannot disagree about
    where somebody is headed. The stagger (a random starting index) is
    preserved: multiple units on one loop must not walk in lockstep.
    """
    from random import randrange
    beat = get_beat(npc)
    if not beat:
        return None, None
    idx = getattr(npc.ndb, "patrol_idx", None)
    if idx is None:
        idx = randrange(len(beat))
    idx = int(idx) % len(beat)
    return beat[idx], idx


def advance_waypoint(npc: Any) -> None:
    """Aim at the next stop on the loop."""
    beat = get_beat(npc)
    if not beat:
        return
    idx = getattr(npc.ndb, "patrol_idx", None) or 0
    npc.ndb.patrol_idx = (int(idx) + 1) % len(beat)


def cadence_ready(npc: Any) -> bool:
    """Is this NPC due to move this beat?

    Civilians drift at a stroll and security marches, which is what
    `patrol_cadence` expresses. Consulted by the souls band tree rather
    than by a second walker, so the pacing survives the driver moving.
    """
    cadence = int(getattr(npc.db, "patrol_cadence", None) or 1)
    if cadence <= 1:
        return True
    waited = int(getattr(npc.ndb, "patrol_wait", None) or 0) + 1
    if waited < cadence:
        npc.ndb.patrol_wait = waited
        return False
    npc.ndb.patrol_wait = 0
    return True


def at_waypoint(npc: Any) -> None:
    """Waypoint hook, by role. Security: sweep for wanted faces — a hit
    raises a ``disturbance`` on the spot and the dispatch/challenge
    machinery (usually assigning this very patroller) takes it from
    there. Civilians: a role-flavored ambient beat (the seed of the §6
    deterministic interaction vocabulary)."""
    role = getattr(getattr(npc, "db", None), "role", None)
    if role == "security":
        try:
            from world.director.dispatch import WorldEvent, raise_event
            from world.director.security import _scan_wanted
            _uid, flagged, _entry = _scan_wanted(npc)
            if flagged is not None:
                # Call it in over the REAL air first (the unit's comms
                # organ; xmit's no-handheld fallback) — anyone tuned to
                # 911MHz hears the net light up. Best-effort flavour; the
                # deterministic raise below is what dispatch acts on.
                try:
                    where = getattr(npc.location, "key", "position")
                    npc.execute_cmd(
                        f"xmit Dispatch — flagged match on {where}, "
                        f"moving to challenge.")
                except Exception:  # noqa: BLE001 — a mute unit still raises
                    pass
                raise_event(WorldEvent("disturbance", npc.location,
                                       severity=1, source=flagged))
            else:
                npc.execute_cmd("emote pans a slow sensor sweep "
                                f"{_sweep_locale(npc.location)} and moves on.")
        except Exception:  # noqa: BLE001 — a bad sweep must not stall the beat
            pass
        return
    # Civilian ambience: one flavored idle beat per arrival.
    try:
        from world.director.civilians import ambient_beat
        line = ambient_beat(npc)
        if line:
            npc.execute_cmd(f"emote {line}")
    except Exception:  # noqa: BLE001 — ambience must not stall the drift
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

    def at_start(self):
        """Once per server start/reload: upkeep that must be true of the
        standing population, applied in-process (never via external shell —
        idmapper). Today: factory-fit the comms module into any security
        unit spawned before the transceiver existed (#1009). Idempotent."""
        try:
            from world.director.population import (
                ensure_base_station, ensure_comms_fitted,
                ensure_dispatch_operator,
            )
            ensure_comms_fitted()
            ensure_base_station()
            ensure_dispatch_operator()
        except Exception:  # noqa: BLE001 — upkeep must not stall the beats
            pass

    def at_repeat(self):
        counts = tick_all()
        try:
            from world.director.population import maintain_security_complement
            maintain_security_complement()
        except Exception:  # noqa: BLE001
            pass
        try:
            # Civilians drain over time; top the pool up one per beat.
            from world.director.population import maintain_civilian_population
            maintain_civilian_population()
        except Exception:  # noqa: BLE001 — respawn must not stall the beats
            pass
        try:
            from world.director.broadcasts import maintain_broadcasts
            maintain_broadcasts()
        except Exception:  # noqa: BLE001 — the station must not stall the beats
            pass
        # The flash-temp backstop: a witness despawns on a Twisted delay,
        # which a reload inside the window loses — stranding them in the
        # street forever (#2367). State that must be true is cheaper to
        # check than an event that must be caught.
        try:
            from world.director.witness import sweep_stranded
            swept = sweep_stranded()
            if swept:
                from evennia.utils import logger
                logger.log_info(f"Witness sweep: {swept} stranded despawned.")
        except Exception:  # noqa: BLE001 — cleanup can't kill the heartbeat
            pass
        # Tick telemetry (DB-backed → visible cross-process; surfaced by
        # @patrol/status as "last tick Ns ago").
        import time
        self.db.last_tick = time.time()
        self.db.last_counts = counts


def ensure_heartbeat() -> Any:
    """The global heartbeat, via ``settings.GLOBAL_SCRIPTS`` — Evennia's
    canonical always-on-script container (the server creates, starts, and
    keeps it alive at every boot; a hand-created row from an external
    ``evennia shell`` never gets its timer armed, learned the hard way).
    Accessing the attribute triggers creation if it doesn't exist yet."""
    from evennia import GLOBAL_SCRIPTS
    return getattr(GLOBAL_SCRIPTS, SCRIPT_KEY, None)
