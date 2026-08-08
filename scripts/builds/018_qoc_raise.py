"""Build 018 — raise the Queen of Cups to z12, level with the Halcyon.

    evennia shell < scripts/builds/018_qoc_raise.py
    then foreground reload.

Owner: level the Queen with the Halcyon (roof z12) for the skyline and
a future fallen-antenna parkour line. Extend the cube rack seven
levels: convert the z5 prize-roof cells into Rack 5, stack fresh Racks
6-11, cap with a new roof at z12. Each level = an aisle + 5 capsule
cubes + a stairwell tread. +35 cubes (25 -> 60), wired like the
existing racks (direction-keyed DoorExits, Pessoa Street origin, on
the #5068 terminal). The antenna mast #5081 + repeater cabinet #5082
sit on the old roof (now a stairwell) — relocated to the new z12 roof
so 88.8MHz coverage follows up (and it's in place for the fallen-
antenna bridge later).
"""
from evennia import create_object
from evennia.objects.models import ObjectDB

ROOM_TC = "typeclasses.rooms.Room"
EXIT_TC = "typeclasses.exits.Exit"
DOOR_TC = "typeclasses.doors.DoorExit"
Q = "Queen of Cups"
AISLE = (-2, -15)
STAIR = (-2, -14)
ORD = {5: "Fifth", 6: "Sixth", 7: "Seventh", 8: "Eighth", 9: "Ninth",
       10: "Tenth", 11: "Eleventh"}
# (dx, dy from aisle, suffix, aisle-side dir, cube-side dir)
CUBES = [(-1, 0, "01", "west", "east"),
         (-1, -1, "02", "southwest", "northeast"),
         (0, -1, "03", "south", "north"),
         (1, -1, "04", "southeast", "northwest"),
         (1, 0, "05", "east", "west")]
ABBR = {"north": "n", "south": "s", "east": "e", "west": "w",
        "northeast": "ne", "northwest": "nw",
        "southeast": "se", "southwest": "sw"}


def at_xyz(xyz):
    return next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
                 if r.db.xyz == xyz and r.destination is None), None)


def has_exit(room, key):
    return any(e.key == key for e in room.exits)


def mk_exit(loc, dest, key, aliases=None):
    if has_exit(loc, key):
        return
    create_object(EXIT_TC, key=key, aliases=aliases or [], location=loc,
                  destination=dest)


# door exemplar: Rack 1 aisle's "west" lease door
_a1 = at_xyz((-2, -15, 1))
ex = next(e for e in _a1.exits if e.key == "west")
EX_LOCKS, EX_DESC = str(ex.locks), ex.db.desc
D_ATTRS = {a.key: a.value for a in ex.attributes.all()
           if a.key in ("is_door", "door_closed", "door_locked",
                        "door_autolock", "door_broken")}


def make_door(loc, dest, key, twin):
    d = create_object(DOOR_TC, key=key, aliases=[ABBR[key]], location=loc,
                      destination=dest)
    for k, v in D_ATTRS.items():
        d.attributes.add(k, v)
    d.db.access_grants = []
    d.db.door_twin = twin
    d.db.desc = EX_DESC
    d.locks.add(EX_LOCKS)
    return d


new_cubes = []


def build_level(z, convert=False):
    """One rack level: aisle + stairwell + 5 cube capsules, wired."""
    ax, ay = AISLE
    if convert:
        aisle = at_xyz((ax, ay, z))
        st = at_xyz((STAIR[0], STAIR[1], z))
        for r in (aisle, st):
            r.attributes.remove("is_ground") if r.attributes.has("is_ground") else None
            r.db.outside = False
        # drop the aisle's old roof-grid exits (the stairwell keeps its
        # down/south, which are the vertical link + aisle link)
        for e in list(aisle.exits):
            e.delete()
        aisle.key = f"{Q} - Rack {z}"
        aisle.db.type = "cube hotel"
        st.key = f"{Q} - {ORD[z]} Level"
        st.db.type = "stairwell"
    else:
        aisle = ObjectDB.objects.filter(db_key=f"{Q} - Rack {z}").first() or \
            create_object(ROOM_TC, key=f"{Q} - Rack {z}")
        aisle.db.xyz = (ax, ay, z)
        aisle.db.type = "cube hotel"
        st = ObjectDB.objects.filter(db_key=f"{Q} - {ORD[z]} Level").first() or \
            create_object(ROOM_TC, key=f"{Q} - {ORD[z]} Level")
        st.db.xyz = (STAIR[0], STAIR[1], z)
        st.db.type = "stairwell"
    aisle.db.atlas_skin = "hotel"
    st.db.atlas_skin = "hotel"
    # aisle <-> stairwell
    mk_exit(aisle, st, "north", ["n"])
    mk_exit(st, aisle, "south", ["s"])
    # cubes
    for dx, dy, suf, adir, cdir in CUBES:
        cx, cy = ax + dx, ay + dy
        key = f"R{z}-{suf}"
        if convert:
            cube = at_xyz((cx, cy, z))
            cube.attributes.remove("is_ground") if cube.attributes.has("is_ground") else None
            cube.db.outside = False
            cube.key = key
        else:
            cube = ObjectDB.objects.filter(db_key=key).first() or \
                create_object(ROOM_TC, key=key)
            cube.db.xyz = (cx, cy, z)
        cube.db.type = "cube hotel"
        cube.db.atlas_skin = "hotel"
        cube.db.residence_building = Q
        cube.db.residence_origin = "Pessoa Street"
        # clear any converted-roof exits, then wire the lease pair
        for e in list(cube.exits):
            e.delete()
        for e in [x for x in aisle.exits if x.destination == cube]:
            e.delete()
        hall = make_door(aisle, cube, adir, cdir)
        make_door(cube, aisle, cdir, adir)
        cube.db.cube_door = hall
        new_cubes.append(cube)
    return aisle, st


# ---- move the antenna off the old roof cell first --------------------
mast = ObjectDB.objects.filter(id=5081).first()
cab = ObjectDB.objects.filter(id=5082).first()
old_roof_ids = {r.id for r in ObjectDB.objects.filter(db_key__startswith=f"{Q} - Rack Roof")}
old_rooftop = ObjectDB.objects.filter(db_key=f"{Q} - Rooftop").first()

# ---- rack 5 (convert the old roof) + racks 6-11 ----------------------
for z in range(5, 12):
    build_level(z, convert=(z == 5))

# stairwell chain: Fourth Level (z4) up through Eleventh (z11)
prev = at_xyz((STAIR[0], STAIR[1], 4))
for z in range(5, 12):
    cur = ObjectDB.objects.filter(db_key=f"{Q} - {ORD[z]} Level").first()
    mk_exit(prev, cur, "up", ["u"])
    mk_exit(cur, prev, "down", ["d"])
    prev = cur

# ---- new roof at z12 (same 7-cell prize-roof pattern) ----------------
ROOF = {(-3, -16): "Rack Roof Southwest", (-3, -15): "Rack Roof Northwest",
        (-2, -16): "Rack Roof South", (-2, -15): "Rack Roof North",
        (-1, -16): "Rack Roof Southeast", (-1, -15): "Rack Roof Northeast",
        (-2, -14): "Rooftop"}
roof = {}
for (x, y), name in ROOF.items():
    r = ObjectDB.objects.filter(db_key=f"{Q} - {name}").first()
    if r is None or r.db.xyz[2] != 12:
        r = create_object(ROOM_TC, key=f"{Q} - {name}")
    r.db.xyz = (x, y, 12)
    r.db.type = "rooftop"
    r.db.outside = True
    r.db.is_ground = True
    roof[(x, y)] = r
# cardinal roof grid
for (x, y), r in roof.items():
    for (dx, dy, d) in ((0, 1, "north"), (0, -1, "south"),
                        (1, 0, "east"), (-1, 0, "west")):
        nb = roof.get((x + dx, y + dy))
        if nb is not None:
            mk_exit(r, nb, d, [ABBR[d]])
# stairs top out onto the Rooftop cell
top_st = ObjectDB.objects.filter(db_key=f"{Q} - Eleventh Level").first()
mk_exit(top_st, roof[(-2, -14)], "up", ["u"])
mk_exit(roof[(-2, -14)], top_st, "down", ["d"])

# ---- relocate the antenna + cabinet to the new roof ------------------
if mast is not None:
    mast.move_to(roof[(-2, -14)], quiet=True, move_hooks=False)
if cab is not None:
    cab.move_to(roof[(-2, -14)], quiet=True, move_hooks=False)

# ---- terminal: add the 35 new cubes ----------------------------------
kiosk = ObjectDB.objects.filter(id=5068).first()
cubes = list(kiosk.db.cubes or [])
ids = {c.id for c in cubes if c is not None and getattr(c, "pk", None)}
for c in new_cubes:
    if c.id not in ids:
        cubes.append(c)
kiosk.db.cubes = cubes

print(f"BUILD 018: QoC raised to z12; {len(new_cubes)} new cubes wired; "
      f"terminal now {len(cubes)}; antenna at "
      f"{mast.location.db.xyz if mast else '?'}.")
