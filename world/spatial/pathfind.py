"""A* pathfinding over the real exit graph (Phase 2).

See ``specs/proposals/SPATIAL_COORDINATE_SYSTEM_SPEC.md`` §5.

The search traverses the **actual exit network** (rooms = nodes, exits =
edges), so locked doors, ``warp`` links, and any future destruction are
honoured automatically — connectivity always reflects the world as it
really is. The seeded coordinates supply only the **heuristic** (the
estimated remaining steps), which makes A* fast and directed; rooms
without coordinates degrade gracefully to a heuristic of 0 (i.e. plain
Dijkstra) so the search stays correct off-grid.

Edge weight is no longer flat: a room costs what a person's willingness
to walk through it costs (``ROUTE_COST``, keyed on the ``db.type`` the
world already carries). Streets are cheap, rooftops are dear, and a
traverser can declare a taste for the awkward ones. Cost is never below
1.0, so the coordinate heuristic stays admissible and A* stays optimal.

Distance and cost are different questions and the module answers both:
``path_length`` counts STEPS (it is what "nearest unit" means to
dispatch), while the search itself minimises COST. ``max_steps`` is a
budget in steps.

Consumers: the NPC dispatch director (route an NPC toward a target),
auto-walk, and "is B reachable from A, and how far by travel?" queries.
This answers *travel* distance; ``coordinates.distance`` answers
*line-of-sight* distance — they are different and both needed.
"""

from __future__ import annotations

import heapq
import itertools
from typing import Any

from world.spatial.coordinates import get_xyz


def _heuristic(room: Any, goal: Any) -> int:
    """Estimated remaining steps from *room* to *goal* using coordinates.

    Movement model: a step changes one axis (cardinal / vertical) or two
    axes at once in the XY plane (a diagonal). So the tightest admissible
    estimate is ``max(|dx|, |dy|) + |dz|``. Off-grid either end → 0, which
    turns A* into Dijkstra (still correct, just unguided).
    """
    a, b = get_xyz(room), get_xyz(goal)
    if a is None or b is None:
        return 0
    dx, dy, dz = abs(a[0] - b[0]), abs(a[1] - b[1]), abs(a[2] - b[2])
    return max(dx, dy) + dz


#: What a room costs to route THROUGH, keyed on the `db.type` the world
#: already carries. Not distance — willingness. A step is a step, but a
#: person walking to work goes round on the street rather than over three
#: roofs to save one, and the flat cost said otherwise: the rooftops are
#: a genuinely connected shortcut between buildings, so A* used them, and
#: ordinary colonists were commuting across the skyline (#2231).
#:
#: Unlisted types cost STREET_COST — the common case is ordinary ground.
ROUTE_COST = {
    "street": 1.0,
    "market": 1.0,
    "shop": 1.0,
    "interior": 1.0,
    "stairwell": 1.2,      # the honest way up, mildly tedious
    "shaft": 1.5,
    "fire escape": 4.0,    # legal, unpleasant, and not a commute
    "hull": 4.0,
    "rooftop": 6.0,        # normal people do not walk along rooftops
}
DEFAULT_COST = 1.0

#: Multiplier a traverser applies to the awkward routes. `db.route_taste`
#: of 0.2 means a roof costs a fifth — the courier, the runner, the
#: burglar. Absent (the overwhelming majority) means 1.0: an ordinary
#: person with an ordinary preference for the pavement. Deliberately a
#: number on the traverser rather than a new system; when roles or traits
#: want to set it, they set it.
def _route_cost(room: Any, traverser: Any) -> float:
    kind = getattr(getattr(room, "db", None), "type", None)
    cost = ROUTE_COST.get(kind, DEFAULT_COST)
    if cost <= DEFAULT_COST or traverser is None:
        return cost
    try:
        taste = getattr(traverser.db, "route_taste", None)
        if taste is not None:
            cost = max(DEFAULT_COST, cost * float(taste))
    except Exception:  # noqa: BLE001 — taste never breaks routing
        pass
    return cost


def _car_exit(room: Any):
    """The `out` exit of an elevator car, or None if this isn't one."""
    if not (getattr(getattr(room, "db", None), "floors", None)
            and hasattr(room, "floor_index")):
        return None
    try:
        from typeclasses.elevator import ElevatorCarExit
    except Exception:  # noqa: BLE001 — no elevators, no special case
        return None
    for ex in (getattr(room, "exits", None) or []):
        if isinstance(ex, ElevatorCarExit):
            return ex
    return None


def _neighbors(room: Any, traverser: Any):
    """Yield ``(destination, exit)`` for every usable exit out of *room*.

    When *traverser* is given, exits it cannot pass (locked doors, access
    locks) are skipped — so dispatch routes around what the NPC can't open.
    With no traverser the search uses pure connectivity (every exit).
    """
    # An elevator CAR reaches every floor its rider may press — not just
    # the one it happens to be parked at.
    #
    # The car is a moving room whose `out` exit is re-pointed on arrival,
    # so the raw graph said corridor -> car and car -> lobby but never
    # lobby -> corridor: riding is a button press, not an exit. Anything
    # behind a lift was therefore unreachable whenever the car rested
    # elsewhere, which is why the dispatch operator could never plan a
    # route to her own desk and the emergency board was never manned
    # (#2231). `travel._await_lift` has always known how to call a car
    # and press a floor; it was never handed a route that asked it to.
    #
    # `_floor_permitted` is the same predicate the button uses, so a
    # secured floor routes for a granted sleeve and for nobody else —
    # one rule, not a second copy of the lock.
    car_out = _car_exit(room)
    if car_out is not None:
        for idx, entry in enumerate(getattr(room.db, "floors", None) or []):
            landing = entry[0] if entry else None
            if landing is None:
                continue
            if traverser is not None:
                allowed = getattr(room, "_floor_permitted", None)
                try:
                    if callable(allowed) and not allowed(idx, traverser):
                        continue
                except Exception:  # noqa: BLE001 — a locked panel is a no
                    continue
            yield landing, car_out
        return

    for ex in (getattr(room, "exits", None) or []):
        dest = getattr(ex, "destination", None)
        if dest is None:
            continue
        # An EDGE or a GAP is not a walk. `Exit.at_traverse` refuses
        # normal traversal outright — for players too — and hands you
        # off to the `jump` command, because the thing on the other side
        # is a storey of air. Routing over them produced ten souls
        # standing on a clinic roof, re-trying a parapet every three
        # minutes, because the route said "walk north" and the parapet
        # said no (#2227). A walking route may not contain a jump; the
        # souls `flee` step already knew this and the graph did not.
        db = getattr(ex, "db", None)
        if getattr(db, "is_edge", None) or getattr(db, "is_gap", None):
            continue
        if traverser is not None:
            try:
                if not ex.access(traverser, "traverse"):
                    continue
            except Exception:  # noqa: BLE001 — never break routing over a lock
                pass
            # verticality §2.1: a locked door the traverser's sleeve can't
            # answer is a blocked edge — dispatch routes around it
            blocks = getattr(ex, "door_blocks", None)
            if callable(blocks):
                try:
                    if blocks(traverser):
                        continue
                except Exception:  # noqa: BLE001
                    pass
        yield dest, ex


def _search(start: Any, goal: Any, traverser: Any,
            max_steps: int | None) -> dict | None:
    """Run A* from *start* to *goal*. Returns the ``came_from`` map
    (``room -> (prev_room, exit)``) when *goal* is reached, else ``None``.
    """
    counter = itertools.count()  # stable tie-breaker (never compare rooms)
    open_heap = [(_heuristic(start, goal), 0.0, next(counter), start, 0)]
    came_from: dict = {}
    g_score: dict = {start: 0.0}
    closed: set = set()

    while open_heap:
        _f, g, _c, current, steps = heapq.heappop(open_heap)
        if current == goal:
            return came_from
        if current in closed:
            continue
        closed.add(current)
        # `max_steps` is a budget in STEPS, and stays one now that `g`
        # carries route cost — otherwise an expensive route would be
        # pruned as though it were a long one.
        if max_steps is not None and steps >= max_steps:
            continue
        for dest, ex in _neighbors(current, traverser):
            if dest in closed:
                continue
            tentative = g + _route_cost(dest, traverser)
            if tentative < g_score.get(dest, float("inf")):
                came_from[dest] = (current, ex)
                g_score[dest] = tentative
                heapq.heappush(
                    open_heap,
                    (tentative + _heuristic(dest, goal), tentative,
                     next(counter), dest, steps + 1),
                )
    return None


def _walk_back(came_from: dict, start: Any, goal: Any):
    """Rebuild the chain from goal to start as ``[(prev, exit, room), ...]``
    in forward order (start-exclusive)."""
    chain = []
    cur = goal
    while cur != start:
        prev, ex = came_from[cur]
        chain.append((prev, ex, cur))
        cur = prev
    chain.reverse()
    return chain


def find_path(start: Any, goal: Any, traverser: Any = None,
              max_steps: int | None = None) -> list | None:
    """Shortest room path ``[start, …, goal]`` (inclusive), or ``None`` if
    *goal* is unreachable (within *max_steps*, if given)."""
    if start is goal or start == goal:
        return [start]
    came_from = _search(start, goal, traverser, max_steps)
    if came_from is None:
        return None
    return [start] + [room for (_p, _e, room) in _walk_back(came_from, start, goal)]


def find_path_exits(start: Any, goal: Any, traverser: Any = None,
                    max_steps: int | None = None) -> list | None:
    """The ordered list of **exits** to traverse from *start* to *goal*
    (for auto-walk / step-by-step movement), or ``None`` if unreachable.
    Empty list when ``start == goal``."""
    if start is goal or start == goal:
        return []
    came_from = _search(start, goal, traverser, max_steps)
    if came_from is None:
        return None
    return [ex for (_p, ex, _r) in _walk_back(came_from, start, goal)]


def path_length(start: Any, goal: Any, traverser: Any = None,
                max_steps: int | None = None) -> int | None:
    """Number of travel steps from *start* to *goal*, or ``None`` if
    unreachable. ``0`` when ``start == goal``."""
    path = find_path(start, goal, traverser, max_steps)
    return None if path is None else len(path) - 1


def is_reachable(start: Any, goal: Any, traverser: Any = None,
                 max_steps: int | None = None) -> bool:
    """True if *goal* is reachable from *start* over the exit graph."""
    if start is goal or start == goal:
        return True
    return _search(start, goal, traverser, max_steps) is not None
