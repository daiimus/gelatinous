"""Spatial coordinate substrate — a signed integer (x, y, z) volume laid
over the hand-built world.

Phase 1 of ``specs/proposals/SPATIAL_COORDINATE_SYSTEM_SPEC.md``: the
coordinate data + read helpers + the ``@coordseed`` seeding walk. Pure
Python, no scipy. Coordinates are stored as ``room.db.xyz`` (a signed
``(x, y, z)`` int tuple, or ``None`` for off-grid rooms).

This package adds no behaviour to existing rooms until they are seeded —
an unseeded room's ``xyz`` is ``None`` and every helper fails open.
"""

from world.spatial.coordinates import (
    DIRECTION_ALIASES,
    DIRECTION_DELTAS,
    all_coordinate_rooms,
    bearing,
    clear_xyz,
    distance,
    exit_direction,
    get_xyz,
    is_warp_exit,
    slope_delta,
    normalize_direction,
    rooms_within,
    seed_coordinates,
    set_xyz,
)
from world.spatial.pathfind import (
    find_path,
    find_path_exits,
    is_reachable,
    path_length,
)

__all__ = [
    "DIRECTION_ALIASES",
    "DIRECTION_DELTAS",
    "all_coordinate_rooms",
    "bearing",
    "clear_xyz",
    "distance",
    "exit_direction",
    "find_path",
    "find_path_exits",
    "get_xyz",
    "is_reachable",
    "is_warp_exit",
    "slope_delta",
    "normalize_direction",
    "path_length",
    "rooms_within",
    "seed_coordinates",
    "set_xyz",
]
