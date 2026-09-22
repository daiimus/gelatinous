"""Build 166 — the crane keeps its doors, and the shaft is wired (#3560).

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \\
        < scripts/builds/166_the_crane_keeps_its_doors.py
    then a foreground reload.

Owner ruling (2026-09-21): "the exit should always exist as an edge working
for jump off and only sometimes work for jump across." `CraneContainer`
no longer deletes and rebuilds its exits on every ride; it keeps four
permanent doors (the car's west and north, the Urgent Care roof's east,
the Queen's roof's south) and points each at what lies beyond it per
level. This script converts the live car:

  1. The shaft's dock-level air cell (-1,-17,1), which build 035 skipped
     because the car parks there. The car already coexists with a shaft
     cell at every other level; the Urgent Care roof's east door needs
     this one to be an edge while the car is aloft.
  2. Down exits along the shaft, z16 -> ... -> z1 -> the Foundation at z0
     (the dig). The cells were built for the atlas cable and had no
     exits at all, so a body falling into the shaft hung in open air
     (the parked impasse, #3581) instead of going "down the cable into
     the dig" as the car's own docstring promises. Never stomps an
     authored exit.
  3. The car's churned exits (`db.crane_exits`, raw ids) are deleted and
     the ledger retired; `move_to_level` at the current level creates the
     four persistent doors and sets them.

The transit cell over the Queen's roof (-1,-16,13) is left as it is: it
has no `down`, and wiring it is a design question about where a failed
leap falls, not this build's.

Re-run-safe: every step finds before it creates.
"""
from evennia import create_object, search_tag
from evennia.objects.models import ObjectDB
from world.spatial import get_xyz, set_xyz

SKY_TC = "typeclasses.rooms.SkyRoom"
EXIT_TC = "typeclasses.exits.Exit"
COL = (-1, -17)
TOP = 16


def sky_at(xyz):
    return next((r for r in ObjectDB.objects.filter(db_typeclass_path=SKY_TC)
                 if get_xyz(r) == xyz), None)


def room_at(xyz):
    """A non-air, non-car room at *xyz* (the Foundation at z0)."""
    return next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
                 if r.destination is None and get_xyz(r) == xyz
                 and r.db_typeclass_path != SKY_TC
                 and r.db_typeclass_path != "typeclasses.rooms.CraneContainer"), None)


def down_of(cell):
    for ex in cell.exits:
        if ex.key.lower() in ("down", "d") or "d" in [a.lower() for a in ex.aliases.all()]:
            return ex
    return None


# ---- 1. the dock-level shaft cell ---------------------------------------
made_cells = 0
foot = (COL[0], COL[1], 1)
if sky_at(foot) is None:
    r = create_object(SKY_TC, key="In the Air")
    set_xyz(r, *foot)
    r.db.type = "sky"
    r.db.is_sky_room = True
    r.db.outside = True
    r.db.desc = ("Open air at the foot of the crane's shaft, level with the "
                 "Urgent Care roof — the container's berth when it's docked, "
                 "and a one-storey drop to the rebar dig when it isn't.")
    made_cells += 1

# ---- 2. wire the shaft downward ------------------------------------------
made_exits = 0
foundation = room_at((COL[0], COL[1], 0))
assert foundation is not None, "no Foundation room at the shaft's foot"
for z in range(TOP, 0, -1):
    cell = sky_at((COL[0], COL[1], z))
    if cell is None:
        print(f"BUILD 166: no shaft cell at z{z}, skipped")
        continue
    below = sky_at((COL[0], COL[1], z - 1)) if z > 1 else foundation
    if below is None:
        print(f"BUILD 166: nothing below z{z}, skipped")
        continue
    if down_of(cell) is None:
        create_object(EXIT_TC, key="down", aliases=["d"], location=cell, destination=below)
        made_exits += 1

# ---- 3. the car: retire the churned exits, raise the permanent doors ----
car = search_tag("crane_car", category="machines")
car = car[0] if car else None
assert car is not None, "no crane car tagged crane_car"
retired = 0
for eid in list(car.attributes.get("crane_exits") or []):
    ex = ObjectDB.objects.filter(id=eid).first()
    if ex is not None:
        ex.delete()
        retired += 1
if car.attributes.has("crane_exits"):
    car.attributes.remove("crane_exits")
level = car.db.level or car.MIN_Z
car.move_to_level(level, announce=False)

doors = []
for room, key in ((car, "west"), (car, "north")):
    ex = next((e for e in room.exits if e.key == key), None)
    doors.append(f"car.{key}=#{ex.id if ex else '-'}")
for xyz, key in ((car.UC_ROOF, "east"), (car.QOC_ROOF, "south")):
    room = room_at(xyz)
    ex = next((e for e in room.exits if e.key == key), None) if room else None
    doors.append(f"{key}@{xyz}=#{ex.id if ex else '-'}")
print(f"BUILD 166: +{made_cells} shaft cell, +{made_exits} down exits, "
      f"{retired} churned exits retired; car #{car.id} at z{level}; doors: {', '.join(doors)}")
