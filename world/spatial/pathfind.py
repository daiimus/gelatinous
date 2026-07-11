"""A* pathfinding over the real exit graph (Phase 2).

See ``specs/proposals/SPATIAL_COORDINATE_SYSTEM_SPEC.md`` §5.

The search traverses the **actual exit network** (rooms = nodes, exits =
edges), so locked doors, ``warp`` links, and any future destruction are
honoured automatically — connectivity always reflects the world as it
really is. The seeded coordinates supply only the **heuristic** (the
estimated remaining steps), which makes A* fast and directed; rooms
without coordinates degrade gracefully to a heuristic of 0 (i.e. plain
Dijkstra) so the search stays correct off-grid.

Edge weight is a flat 1 step for Phase 2 — terrain cost / hazard
avoidance / traversal penalties are a reserved seam.

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


def _neighbors(room: Any, traverser: Any):
    """Yield ``(destination, exit)`` for every usable exit out of *room*.

    When *traverser* is given, exits it cannot pass (locked doors, access
    locks) are skipped — so dispatch routes around what the NPC can't open.
    With no traverser the search uses pure connectivity (every exit).
    """
    for ex in (getattr(room, "exits", None) or []):
        dest = getattr(ex, "destination", None)
        if dest is None:
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
    open_heap = [(_heuristic(start, goal), 0, next(counter), start)]
    came_from: dict = {}
    g_score: dict = {start: 0}
    closed: set = set()

    while open_heap:
        _f, g, _c, current = heapq.heappop(open_heap)
        if current == goal:
            return came_from
        if current in closed:
            continue
        closed.add(current)
        if max_steps is not None and g >= max_steps:
            continue
        for dest, ex in _neighbors(current, traverser):
            if dest in closed:
                continue
            tentative = g + 1
            if tentative < g_score.get(dest, float("inf")):
                came_from[dest] = (current, ex)
                g_score[dest] = tentative
                heapq.heappush(
                    open_heap,
                    (tentative + _heuristic(dest, goal), tentative,
                     next(counter), dest),
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
