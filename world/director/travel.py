"""Pathfinder-driven NPC travel — walk an NPC to a room, one step per
tick, over the real exit graph.

The movement primitive every director behaviour rests on (routines and
dispatch both). The NPC walks by **executing the real exit command**
(``execute_cmd(exit.key)``) — the same way a player moves — so locks,
messages, and proximity cleanup all apply, and the LLM-NPC mandate (NPCs
act through real commands) is honoured for deterministic NPCs too.

The route is re-pathed every step, so a changed graph (a blown-open wall,
a locked door) is handled automatically.
"""

from __future__ import annotations

from typing import Any

from evennia.utils import delay

from world.spatial import find_path_exits

#: Seconds between room steps (walking pace).
TRAVEL_STEP_DELAY = 2.0
#: Hard cap on steps before giving up (anti-runaway).
TRAVEL_MAX_STEPS = 200
#: ndb key holding the in-flight travel state.
_NDB_KEY = "director_travel"


def is_travelling(npc: Any) -> bool:
    """True if *npc* has an active director travel in progress."""
    ndb = getattr(npc, "ndb", None)
    return bool(getattr(ndb, _NDB_KEY, None)) if ndb is not None else False


def stop_travel(npc: Any) -> None:
    """Cancel any in-flight travel for *npc*."""
    if npc is not None and getattr(npc, "ndb", None) is not None:
        setattr(npc.ndb, _NDB_KEY, None)


def travel_to(npc: Any, destination: Any, on_arrive=None, on_fail=None,
              step_delay: float | None = None) -> bool:
    """Walk *npc* to *destination* over the exit graph.

    Returns ``True`` if travel started (or the NPC is already there),
    ``False`` if *destination* is unreachable. ``on_arrive(npc)`` /
    ``on_fail(npc)`` fire on completion. Starting a new travel cancels any
    previous one.
    """
    if npc is None or destination is None:
        return False
    if npc.location == destination:
        if on_arrive:
            on_arrive(npc)
        return True
    if find_path_exits(npc.location, destination, traverser=npc) is None:
        if on_fail:
            on_fail(npc)
        return False
    npc.ndb.director_travel = {
        "destination": destination,
        "on_arrive": on_arrive,
        "on_fail": on_fail,
        "step_delay": step_delay or TRAVEL_STEP_DELAY,
        "steps": 0,
    }
    _travel_step(npc)
    return True


def _finish(npc: Any, state: dict, key: str) -> None:
    npc.ndb.director_travel = None
    cb = state.get(key)
    if cb:
        try:
            cb(npc)
        except Exception:  # noqa: BLE001 — a bad callback must not break the tick
            pass


def _travel_step(npc: Any) -> None:
    state = getattr(getattr(npc, "ndb", None), _NDB_KEY, None)
    if not state:
        return  # cancelled
    destination = state["destination"]
    if npc.location == destination:
        _finish(npc, state, "on_arrive")
        return
    state["steps"] += 1
    if state["steps"] > TRAVEL_MAX_STEPS:
        _finish(npc, state, "on_fail")
        return
    exits = find_path_exits(npc.location, destination, traverser=npc)
    if not exits:
        _finish(npc, state, "on_fail")
        return
    # Walk through the next exit via its real command (locks, messages, etc.).
    npc.execute_cmd(exits[0].key)
    delay(state["step_delay"], _travel_step, npc)
