"""The hunt — deterministic NPC search behaviour off the awareness meter.

STEALTH_AND_DETECTION_SPEC §5: the MGS/Hitman/Thief loop, **no LLM**. A
security NPC's awareness records (accrued exactly like a player's — passive
checks on room entry, hide-time contests, unseen whispers) drive a state
machine the director heartbeat ticks:

    Unaware ──(detect)──▶ Suspicious ──(commit)──▶ Searching ──(reacquire)──▶ Alert
       ▲                      │                        │                        │
       └──(decay/give up)─────┴──────(budget out)──────┘                   (engage)

* **Suspicious** — break routine, orient (a visible tell: the bot snapping
  alert is the player's cue to move), commit to the hunt.
* **Searching** — travel to the target's LAST-KNOWN room (stamped on the
  awareness record), sweep it with the REAL ``search`` command, then fan
  outward through adjacent rooms on a bounded budget.
* **Reacquire → engage** — challenge, raise a ``disturbance`` (the existing
  dispatch/challenge machinery takes over), and PROPAGATE: every other
  security unit is seeded to Searching at the sighting room.
* **Give up** — budget exhausted or the record decayed: drop it, one
  give-up beat, and the patrol routine resumes on the next tick.

Everything the hunter does goes through real commands (`search`, `say`,
`emote`) and director travel (real exits) — the same world the players get.
"""

from __future__ import annotations

from typing import Any, Optional

#: Rooms a hunter will sweep (last-known + adjacents) before giving up.
SEARCH_BUDGET = 4

ORIENT_EMOTE = ("snaps alert, optics sweeping for something it "
                "half-caught.")
GIVEUP_EMOTE = "abandons its sweep and resumes its rounds."
CHALLENGE_LINE = "Halt, Colonist. Remain where you are."


def _room_by_id(room_id) -> Optional[Any]:
    if room_id is None:
        return None
    try:
        from evennia.objects.models import ObjectDB
        return ObjectDB.objects.get(id=int(room_id))
    except Exception:  # noqa: BLE001 — a demolished room is just gone
        return None


def _present_target(npc, target_key) -> Optional[Any]:
    """The hunted target, if perceivably HERE (reacquired)."""
    from world.perception import can_perceive
    from world.stealth import _target_key
    room = npc.location
    for obj in (room.contents if room else []):
        if obj is npc or not hasattr(obj, "get_sdesc"):
            continue
        try:
            if _target_key(obj) == target_key and can_perceive(npc, obj):
                return obj
        except Exception:  # noqa: BLE001
            continue
    return None


def is_hunting(npc) -> bool:
    return bool(getattr(getattr(npc, "ndb", None), "hunt", None))


def _give_up(npc, target_key) -> None:
    from world.stealth import UNAWARE, seed_awareness
    npc.ndb.hunt = None
    seed_awareness(npc, target_key, UNAWARE)
    try:
        npc.execute_cmd(f"emote {GIVEUP_EMOTE}")
    except Exception:  # noqa: BLE001
        pass


def _has_cause(npc, record) -> bool:
    """A hunt requires CAUSE (user-decided 2026-07-03), from either axis:

    * **Status** — the presence's apparent-uid is on the wanted record
      (silent check).
    * **Situation** — an UNRESOLVED incident (sourceless disturbance: an
      explosion, an anonymous crime) is hot in/adjacent to where the
      presence was sensed, or where the bot stands. Reasonable
      suspicion: near a fresh blast, a hidden person IS the lead.

    Without either, the presence is ignored — an innocent hider is
    clocked (the nervous-face render) but never hunted or rousted."""
    from world.director.dispatch import incident_context
    from world.director.intel import is_wanted
    key, _level, last_room_id, _t = record
    if is_wanted(key):
        return True
    if incident_context(npc.location):
        return True
    return incident_context(_room_by_id(last_room_id))


def _with_cause(npc, records) -> list:
    return [rec for rec in records if _has_cause(npc, rec)]


def _engage(npc, target) -> None:
    """Reacquired a target WITH CAUSE: challenge, hand off to dispatch,
    propagate. Defensive re-check — a pardon mid-hunt stands the bot
    down silently (no message; there was never a public incident)."""
    from world.director.dispatch import incident_context
    from world.director.intel import is_wanted
    from world.stealth import (
        ALERT, UNAWARE, _target_key, set_awareness,
    )
    key = _target_key(target)
    if not is_wanted(key) and not incident_context(npc.location):
        npc.ndb.hunt = None
        set_awareness(npc, target, UNAWARE, roll_stamp=True)
        return
    set_awareness(npc, target, ALERT)
    npc.ndb.hunt = None
    try:
        npc.execute_cmd(f"say {CHALLENGE_LINE}")
    except Exception:  # noqa: BLE001
        pass
    # Backup request rides the REAL air (comms organ via xmit's fallback) —
    # audible to anyone on 911MHz. Flavour only; the raise stays authoritative.
    try:
        where = getattr(npc.location, "key", "position")
        npc.execute_cmd(f"xmit Unit engaging — backup to {where}.")
    except Exception:  # noqa: BLE001 — a mute unit still raises
        pass
    try:
        from world.director.dispatch import WorldEvent, raise_event
        raise_event(WorldEvent("disturbance", npc.location, severity=2,
                               source=target))
    except Exception:  # noqa: BLE001 — dispatch down ≠ hunt crash
        pass
    propagate_alert(npc, _target_key(target),
                    getattr(npc.location, "id", None))


def propagate_alert(npc, target_key, room_id) -> int:
    """Seed every OTHER security unit to Searching at the sighting room —
    alert propagation (spec §5). Returns how many were seeded."""
    from evennia.objects.models import ObjectDB
    from world.stealth import SEARCHING, seed_awareness
    seeded = 0
    try:
        candidates = ObjectDB.objects.filter(
            db_attributes__db_key="role").distinct()
    except Exception:  # noqa: BLE001
        return 0
    for other in candidates:
        if other == npc or getattr(other.db, "role", None) != "security":
            continue
        try:
            seed_awareness(other, target_key, SEARCHING, room_id)
            seeded += 1
        except Exception:  # noqa: BLE001
            continue
    return seeded


def _next_sweep_room(npc, state) -> Optional[Any]:
    """Where to sweep next: the last-known room first, then unswept
    adjacents of it (the bounded fan-out)."""
    swept = state.get("swept") or []
    last_room = _room_by_id(state.get("last_room"))
    if last_room is not None and last_room.id not in swept:
        return last_room
    anchor = last_room or npc.location
    if anchor is None:
        return None
    for exit_obj in getattr(anchor, "exits", []) or []:
        dest = getattr(exit_obj, "destination", None)
        if dest is not None and dest.id not in swept:
            return dest
    return None


def tick_hunt(npc) -> bool:
    """One heartbeat of hunt behaviour. True = the hunt owns this NPC's
    turn (the patrol routine stays out); False = nothing to hunt."""
    from world.director.travel import is_travelling, travel_to
    from world.stealth import ALERT, SEARCHING, SUSPICIOUS, hunt_records

    state = getattr(npc.ndb, "hunt", None)
    if is_travelling(npc):
        return bool(state)          # en route to a sweep — stay committed

    records = _with_cause(npc, hunt_records(npc))
    best = records[0] if records else None
    if best is None:
        if state:
            _give_up(npc, state.get("key", ""))
        return False
    key, level, last_room_id, _t = best

    # Reacquired in this very room → engage.
    target = _present_target(npc, key)
    if target is not None and level >= ALERT:
        _engage(npc, target)
        return True

    if state is None:
        if level < SUSPICIOUS:
            return False
        # Commit: the orient beat is the player's audible cue to move.
        try:
            npc.execute_cmd(f"emote {ORIENT_EMOTE}")
        except Exception:  # noqa: BLE001
            pass
        npc.ndb.hunt = {"key": key, "budget": SEARCH_BUDGET,
                        "swept": [], "last_room": last_room_id}
        return True
    if state.get("key") != key:
        # A stronger scent supersedes the old hunt.
        state = {"key": key, "budget": SEARCH_BUDGET,
                 "swept": [], "last_room": last_room_id}
        npc.ndb.hunt = state

    dest = _next_sweep_room(npc, state)
    if dest is None or state.get("budget", 0) <= 0:
        _give_up(npc, key)
        return True

    if npc.location == dest:
        # Sweep HERE with the real command — the same contest players get.
        state["swept"] = list(state.get("swept") or []) + [dest.id]
        state["budget"] = int(state.get("budget", 0)) - 1
        npc.ndb.hunt = state
        try:
            npc.execute_cmd("search")
        except Exception:  # noqa: BLE001
            pass
        found = _present_target(npc, key)
        if found is not None:
            _engage(npc, found)
        return True

    travel_to(npc, dest)
    return True
