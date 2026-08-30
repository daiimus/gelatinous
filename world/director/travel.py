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
        # This path calls back DIRECTLY rather than through _finish, so
        # it has to set the reason itself -- otherwise the caller gets
        # "reason not recorded", which is honest but useless (#2321).
        npc.ndb.travel_fail_why = (
            f"no route from {getattr(npc.location, 'key', '?')} "
            f"at all")
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


def _finish(npc: Any, state: dict, key: str, why: str = "") -> None:
    """End a walk and tell the caller WHY.

    `on_fail` covers three different failures -- the route ran out of
    steps, the graph offered no route at all, and an exit bounced three
    times -- and for a long while every one of them was reported as
    "an exit that wouldn't give". That sent a debugging session after a
    door for an hour when the real answer was "no route" (#2321).

    The reason rides on ndb so the callback can read it without
    changing every caller's signature; it is cleared with the state.
    """
    npc.ndb.director_travel = None
    npc.ndb.travel_fail_why = why or None
    cb = state.get(key)
    if cb:
        try:
            cb(npc)
        except Exception:  # noqa: BLE001 — a bad callback must not break the tick
            pass


#: ticks a walker will wait on a car before giving up and stalling
#: Fallback only. Real patience is derived per shaft by `_lift_patience` —
#: a flat tick count cannot serve both a 2-floor lift and a 16-floor one.
LIFT_PATIENCE = 15


def _lift_patience(car: Any, step_delay: float) -> int:
    """How many ticks to wait on THIS car, from how long its shaft can take.

    The flat 15 ticks was 30 seconds at the default step delay, while the
    Brackett's 16-floor shaft needs 3 + 6×15 = 93 seconds end to end. Any ride
    of five floors or more therefore ran out of patience, fell through to the
    ordinary walk, bounced off a door with no car behind it three times and
    faulted — which is what stranded souls mid-errand (#2412).

    Worst case for the shaft plus a margin, so a short lift stays brisk and a
    tall one gets the time it actually needs.
    """
    try:
        from typeclasses.elevator import DOOR_SECONDS, RIDE_SECONDS_PER_FLOOR
        floors = len((getattr(car, "db", None) and car.db.floors) or [])
        if floors < 2:
            # Cannot read the shaft. Deriving from nothing would produce a
            # confidently-wrong SHORT patience, which is the failure mode this
            # function exists to remove — take the documented flat cap.
            return LIFT_PATIENCE
        worst = DOOR_SECONDS * 2 + RIDE_SECONDS_PER_FLOOR * max(1, floors - 1)
        return int(worst / max(0.5, float(step_delay))) + 4
    except Exception:  # noqa: BLE001 — an odd car falls back to the flat cap
        return LIFT_PATIENCE


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

    if isinstance(nxt, ElevatorDoorExit):
        # at a landing: the car has to be here before the door gives
        if car_docked(nxt.destination, npc.location):
            state["lift_wait"] = 0
            return False
        if waited > _lift_patience(nxt.destination, state["step_delay"]):
            return False                  # give up; normal stall path
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
        if waited > _lift_patience(car, state["step_delay"]):
            return False                  # give up; normal stall path
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
        _finish(npc, state, "on_fail",
                f"gave up after {TRAVEL_MAX_STEPS} steps")
        return
    # Walk the cached route; re-pathfind only when reality disagrees
    # with it (a bounced exit, a lock change, the npc moved by force).
    route = state.get("route") or []
    if not (route and route[0].location == npc.location):
        route = find_path_exits(npc.location, destination, traverser=npc)
        if not route:
            _finish(npc, state, "on_fail",
                    f"no route from {getattr(npc.location, 'key', '?')}")
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
    # A GAP is not a walk. `Exit.at_traverse` refuses the exit name
    # outright -- for players too -- and hands you to the jump command,
    # so typing "north" at a parapet does nothing forever. The
    # pathfinder only offers these hops to a traverser with a
    # `route_taste`, and this is the verb that makes such a route
    # actually walkable (#2303).
    #
    # It can fail. She misjudges it, falls, and the run faults like any
    # other broken step -- the intended consequence, not an edge case
    # to smooth over.
    #
    # A fall does NOT drop what she is carrying (owner, 2026-08-24):
    # falling is not fumbling. But she can die of it, and then the
    # parcel is on the body like everything else she owned -- which is
    # a perfectly good way for a consignment to go missing.
    # `is True` rather than truthiness: these flags are authored as
    # literal True everywhere they are set (rooms.py, CmdBuildTools),
    # and an identity check will not mistake a door for a parapet just
    # because something answered yes to an attribute it had never heard
    # of.
    # `jump across` is for a GAP. An edge without a gap is a drop and
    # takes `jump off` -- issuing the crossing verb at one just earns
    # "the breach exit is not a gap you can jump across", forever
    # (#2335). The pathfinder no longer offers drops at all, so this
    # only has to handle the crossing case.
    ndb = getattr(nxt, "db", None)
    if getattr(ndb, "is_gap", None) is True:
        npc.execute_cmd(f"jump across {nxt.key} edge")
    else:
        npc.execute_cmd(nxt.key)
    # stall detection: an exit that exists but bounces (an elevator car
    # on another floor, a lock the pathfinder mispredicted) would loop
    # silently forever — three consecutive no-progress steps FAIL the
    # travel loudly instead
    if npc.location == came_from:
        state["stall"] = state.get("stall", 0) + 1
        if state["stall"] >= 3:
            _finish(npc, state, "on_fail",
                    f"{nxt.key} out of "
                    f"{getattr(came_from, 'key', '?')} "
                    f"bounced three times")
            return
    else:
        state["stall"] = 0
    # a soul nobody can see walks at half cadence — same route, fewer
    # reactor slices (LOD is set by the souls heartbeat; non-soul NPCs
    # have no soul_lod and keep full pace)
    scale = 2.0 if getattr(npc.ndb, "soul_lod", None) == "cold" else 1.0
    delay(state["step_delay"] * scale, _travel_step, npc)
