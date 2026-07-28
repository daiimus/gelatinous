"""The colony map export (COLONY_MAPPING_SPEC §M1).

One canonical, deterministic, READ-ONLY walk of the coordinate substrate:
``export_map()`` returns cells (every coord-seeded room) and links (every
exit between two seeded rooms), with edge flight-plans and door state
riding along. Everything that draws a map — the atlas, the portrait
plates, someday the decking layer's wayfinding files — is a consumer of
this one structure. The exporter stamps nothing (no timestamps, no
randomness): callers date their own editions.
"""

from evennia.objects.models import ObjectDB

from world.spatial import get_xyz


def _flags(room):
    flags = []
    db = room.db
    if db.outside is True:
        flags.append("outside")
    if db.is_sky_room is True:
        flags.append("sky")
    if db.is_ground is True:
        flags.append("ground")
    return flags


def _link_kind(ex, src):
    db = ex.db
    if db.is_door is True:
        return "door"
    if db.is_edge is True:
        return "edge"
    if db.is_gap is True:
        return "gap"
    if src.db.is_sky_room is True and ex.key in ("down", "d"):
        return "fall"
    return "walk"


def export_map():
    """The whole seeded world as one deterministic structure."""
    rooms = {}
    for obj in ObjectDB.objects.filter(
            db_attributes__db_key="xyz").distinct():
        if obj.destination is not None:
            continue                      # exits never carry cells
        xyz = get_xyz(obj)
        if xyz is None:
            continue
        rooms[obj.id] = (obj, xyz)

    cells = []
    for _, (room, xyz) in rooms.items():
        cells.append({
            "dbref": f"#{room.id}",
            "key": room.key,
            "xyz": list(xyz),
            "type": str(room.db.type or ""),
            "flags": _flags(room),
            "crowd": int(room.db.crowd_base_level or 0),
        })
    cells.sort(key=lambda c: (c["xyz"], c["dbref"]))

    links = []
    for ex in ObjectDB.objects.exclude(db_destination=None):
        src, dst = ex.location, ex.destination
        if src is None or src.id not in rooms or dst.id not in rooms:
            continue                      # off-grid ends are absent by design
        kind = _link_kind(ex, src)
        entry = {"from": f"#{src.id}", "to": f"#{dst.id}",
                 "key": ex.key, "kind": kind}
        if kind in ("edge", "gap"):
            edge = {}
            for attr in ("sky_room", "fall_room", "fall_distance",
                         "fall_damage", "edge_difficulty",
                         "gap_destination"):
                val = ex.attributes.get(attr)
                if val is not None:
                    edge[attr] = int(val) if not isinstance(val, str) \
                        else val
            entry["edge"] = edge
        elif kind == "door":
            entry["door"] = {"locked": ex.db.door_locked is True}
        links.append(entry)
    links.sort(key=lambda l: (l["from"], l["to"], l["key"]))

    return {"cells": cells, "links": links}
