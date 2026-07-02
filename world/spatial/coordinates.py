"""Coordinate read/write helpers, the direction system, and the seeding
walk for the spatial substrate (Phase 1).

See ``specs/proposals/SPATIAL_COORDINATE_SYSTEM_SPEC.md``.

Axes: ``+X`` east / ``+Y`` north / ``+Z`` up. Origin ``(0, 0, 0)`` at the
central ground room; the Drifts (mines/sewers) are ``Z < 0``, upper levels ``Z > 0``.
One unit = one room step along a cardinal exit.
"""

from __future__ import annotations

from collections import deque
from typing import Any

# --------------------------------------------------------------------------
# Direction system
# --------------------------------------------------------------------------

#: Canonical cardinal/diagonal/vertical direction → unit coordinate delta.
DIRECTION_DELTAS: dict[str, tuple[int, int, int]] = {
    "north": (0, 1, 0),
    "south": (0, -1, 0),
    "east": (1, 0, 0),
    "west": (-1, 0, 0),
    "up": (0, 0, 1),
    "down": (0, 0, -1),
    "northeast": (1, 1, 0),
    "northwest": (-1, 1, 0),
    "southeast": (1, -1, 0),
    "southwest": (-1, -1, 0),
}

#: Abbreviation → canonical direction (mirrors the exit alias convention).
DIRECTION_ALIASES: dict[str, str] = {
    "n": "north", "s": "south", "e": "east", "w": "west",
    "u": "up", "d": "down",
    "ne": "northeast", "nw": "northwest",
    "se": "southeast", "sw": "southwest",
}

#: Tag marking an exit as a deliberate non-Euclidean link (elevator,
#: teleporter, maglev). Excluded from coordinate propagation; still a
#: normal, walkable exit.
WARP_TAG = "warp"
WARP_TAG_CATEGORY = "exit_type"


def normalize_direction(token: Any) -> str | None:
    """Return the canonical direction for *token* (a key or alias), or
    ``None`` if it isn't a recognised cardinal/diagonal/vertical step."""
    if not token:
        return None
    token = str(token).lower().strip()
    if token in DIRECTION_DELTAS:
        return token
    return DIRECTION_ALIASES.get(token)


def exit_direction(exit_obj: Any) -> str | None:
    """Resolve an exit's canonical direction from its key, then aliases.

    Returns ``None`` for non-cardinal exits (``enter bar``, ``out``,
    ``climb`` …), which the seeder skips.
    """
    direction = normalize_direction(getattr(exit_obj, "key", None))
    if direction:
        return direction
    aliases = getattr(exit_obj, "aliases", None)
    if aliases is not None:
        try:
            for alias in aliases.all():
                direction = normalize_direction(alias)
                if direction:
                    return direction
        except Exception:  # noqa: BLE001 — never break seeding over aliases
            pass
    return None


def is_warp_exit(exit_obj: Any) -> bool:
    """True if the exit is tagged as a warp (excluded from geometry)."""
    tags = getattr(exit_obj, "tags", None)
    if tags is None:
        return False
    try:
        return bool(tags.has(WARP_TAG, category=WARP_TAG_CATEGORY))
    except Exception:  # noqa: BLE001
        return False


# --------------------------------------------------------------------------
# Coordinate read / write
# --------------------------------------------------------------------------

def get_xyz(room: Any) -> tuple[int, int, int] | None:
    """Return *room*'s ``(x, y, z)`` tuple, or ``None`` if off-grid."""
    if room is None:
        return None
    db = getattr(room, "db", None)
    coord = getattr(db, "xyz", None) if db is not None else None
    if coord is None:
        return None
    try:
        x, y, z = coord
        return (int(x), int(y), int(z))
    except (TypeError, ValueError):
        return None


def set_xyz(room: Any, x: int, y: int, z: int) -> None:
    """Assign *room*'s coordinates."""
    room.db.xyz = (int(x), int(y), int(z))


def clear_xyz(room: Any) -> None:
    """Remove *room*'s coordinates (return it to off-grid)."""
    if getattr(room, "db", None) is not None:
        room.db.xyz = None


# --------------------------------------------------------------------------
# Spatial queries (linear scan for Phase 1; spatial-hash escalation later)
# --------------------------------------------------------------------------

def distance(room_a: Any, room_b: Any) -> float | None:
    """Straight-line distance between two rooms in the coordinate volume.

    ``None`` if either room is off-grid. This is line-of-sight / signal
    distance, *not* travel distance (that's the pathfinder, Phase 2).
    """
    a, b = get_xyz(room_a), get_xyz(room_b)
    if a is None or b is None:
        return None
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5


def all_coordinate_rooms() -> list:
    """Every on-grid object (rooms carry the coordinates). A targeted
    attribute query — not ``Room.objects.all()``, which returns only the
    exact ``Room`` typeclass and would miss ``StreetRoom`` / ``IndoorRoom``
    / ``BridgeRoom`` subclasses. The query is the seam a spatial hash slots
    behind later."""
    from evennia.objects.models import ObjectDB
    rooms = ObjectDB.objects.filter(db_attributes__db_key="xyz").distinct()
    return [r for r in rooms if get_xyz(r) is not None]


def rooms_within(room: Any, n: float) -> list:
    """On-grid rooms within straight-line distance *n* of *room* (excluding
    *room* itself). Empty when *room* is off-grid."""
    if get_xyz(room) is None:
        return []
    out = []
    for other in all_coordinate_rooms():
        if other == room:
            continue
        d = distance(room, other)
        if d is not None and d <= n:
            out.append(other)
    return out


#: Compass labels for the eight horizontal octants, plus pure vertical.
_BEARINGS = [
    "east", "northeast", "north", "northwest",
    "west", "southwest", "south", "southeast",
]


def bearing(room_a: Any, room_b: Any) -> str | None:
    """Rough compass+altitude bearing from *a* to *b* (for radar / dispatch
    facing). ``None`` if off-grid; ``"here"`` if co-located."""
    import math
    a, b = get_xyz(room_a), get_xyz(room_b)
    if a is None or b is None:
        return None
    dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    horiz = None
    if dx or dy:
        octant = int(round(math.atan2(dy, dx) / (math.pi / 4))) % 8
        horiz = _BEARINGS[octant]
    vert = "up" if dz > 0 else "down" if dz < 0 else None
    if horiz and vert:
        return f"{horiz} and {vert}"
    return horiz or vert or "here"


# --------------------------------------------------------------------------
# Seeding walk
# --------------------------------------------------------------------------

def seed_coordinates(origin: Any) -> tuple[dict, list]:
    """Breadth-first assign coordinates outward from *origin* (= ``(0,0,0)``)
    over cardinal exits.

    **Authoritative**: a room reached twice with conflicting coordinates is
    a geometry bug (a direction that doesn't reverse). It is recorded in the
    contradiction list and *not* overwritten — coordinates are never
    silently averaged. ``warp``-tagged and non-cardinal exits are skipped.

    Pure traversal — assigns nothing to the DB. The caller (``@coordseed``)
    writes ``assignments`` and reports ``contradictions``.

    Returns ``(assignments, contradictions)`` where ``assignments`` maps
    ``room -> (x, y, z)`` and each contradiction is a dict describing the
    clash.
    """
    assignments: dict = {origin: (0, 0, 0)}
    contradictions: list = []
    queue: deque = deque([origin])

    while queue:
        room = queue.popleft()
        x, y, z = assignments[room]
        for ex in (getattr(room, "exits", None) or []):
            if is_warp_exit(ex):
                continue
            direction = exit_direction(ex)
            if direction is None:
                continue
            dest = getattr(ex, "destination", None)
            if dest is None:
                continue
            dx, dy, dz = DIRECTION_DELTAS[direction]
            expected = (x + dx, y + dy, z + dz)
            if dest in assignments:
                if assignments[dest] != expected:
                    contradictions.append({
                        "from_room": room,
                        "exit": ex,
                        "direction": direction,
                        "dest": dest,
                        "existing": assignments[dest],
                        "expected": expected,
                    })
                continue
            assignments[dest] = expected
            queue.append(dest)

    return assignments, contradictions
