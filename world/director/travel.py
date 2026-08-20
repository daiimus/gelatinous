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
    route = find_path_exits(npc.location, destination, traverser=npc)
    if route is None:
        if on_fail:
            on_fail(npc)
        return False
    npc.ndb.director_travel = {
        "destination": destination,
        "on_arrive": on_arrive,
        "on_fail": on_fail,
        "step_delay": step_delay or TRAVEL_STEP_DELAY,
        "steps": 0,
        # the route is computed ONCE and walked; a step that doesn't
        # land where the route expects re-pathfinds (A* measured at
        # ~18ms/path — per-step re-pathing saturates the reactor at
        # commute scale, souls hardening spec §1.5)
        "route": list(route),
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


#: ticks a walker will wait on a car before giving up and stalling
LIFT_PATIENCE = 15


def _await_lift(npc: Any, state: dict, nxt: Any, route: list,
                destination: Any) -> bool:
    """True when this tick was spent working an elevator rather than
    walking. Presses the real buttons; the ride itself is the wait."""
    try:
        from typeclasses.elevator import (
            ElevatorCarExit, ElevatorDoorExit, car_docked)
    except Exception:  # noqa: BLE001 — no elevators, no special case
        return False

    waited = state.get("lift_wait", 0)
    if waited > LIFT_PATIENCE:
        return False                      # give up; normal stall path

    if isinstance(nxt, ElevatorDoorExit):
        # at a landing: the car has to be here before the door gives
        if car_docked(nxt.destination, npc.location):
            state["lift_wait"] = 0
            return False
        if not waited:
            npc.execute_cmd("call")
        state["lift_wait"] = waited + 1
        return True

    if isinstance(nxt, ElevatorCarExit):
        # in the car: ride to the landing the route actually wants
        car = npc.location
        want = route[1].location if len(route) > 1 else destination
        if getattr(car, "is_docked_at", None) and car.is_docked_at(want):
            state["lift_wait"] = 0
            return False
        idx = car.floor_index(want) if hasattr(car, "floor_index") else None
        if idx is None:
            return False                  # not our shaft; walk it normally
        if not waited:
            label = (car.db.floors or [])[idx][1]
            npc.execute_cmd(f"press {label}")
        state["lift_wait"] = waited + 1
        return True

    return False


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
    # Walk the cached route; re-pathfind only when reality disagrees
    # with it (a bounced exit, a lock change, the npc moved by force).
    route = state.get("route") or []
    if not (route and route[0].location == npc.location):
        route = find_path_exits(npc.location, destination, traverser=npc)
        if not route:
            _finish(npc, state, "on_fail")
            return
        state["route"] = list(route)
        route = state["route"]
    # An elevator is a room that moves: the door only gives while the car
    # is docked here, so a walker that just tries the exit bounces until
    # its stall counter fires (souls were stranded for hours inside the
    # Constabulary and the Brackett). Summon and select through the REAL
    # verbs — `call` at the landing, `press <floor>` in the car — and
    # wait on the ride without burning stall strikes.
    nxt = route[0]
    if _await_lift(npc, state, nxt, route, destination):
        delay(state["step_delay"], _travel_step, npc)
        return

    # Walk through the next exit via its real command (locks, messages, etc.).
    nxt = route.pop(0)
    came_from = npc.location
    try:
        # A closed door on the route: open it first, through the REAL
        # verb (grant checks, reader flashes, room messages all apply).
        # The pathfinder only routes through doors this traverser can
        # open, so a bounce here means the world changed mid-walk — the
        # next tick re-pathfinds around it.
        is_open = getattr(nxt, "is_open", None)
        if callable(is_open) and not is_open():
            npc.execute_cmd(f"open {nxt.key}")
    except Exception:  # noqa: BLE001 — an odd exit never stalls travel
        pass
    npc.execute_cmd(nxt.key)
    # stall detection: an exit that exists but bounces (an elevator car
    # on another floor, a lock the pathfinder mispredicted) would loop
    # silently forever — three consecutive no-progress steps FAIL the
    # travel loudly instead
    if npc.location == came_from:
        state["stall"] = state.get("stall", 0) + 1
        if state["stall"] >= 3:
            _finish(npc, state, "on_fail")
            return
    else:
        state["stall"] = 0
    # a soul nobody can see walks at half cadence — same route, fewer
    # reactor slices (LOD is set by the souls heartbeat; non-soul NPCs
    # have no soul_lod and keep full pace)
    scale = 2.0 if getattr(npc.ndb, "soul_lod", None) == "cold" else 1.0
    delay(state["step_delay"] * scale, _travel_step, npc)
