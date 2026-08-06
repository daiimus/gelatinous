"""Build 003 — the Brackett fire escape (rough draft, owner-designed).

    evennia shell < scripts/builds/003_brackett_fire_escape.py
    then foreground reload.

The design (owner, 2026-08-05):
  - Code-era iron serves floors 3-5; the 6th-floor conversion crowd,
    told to fend for themselves, bolted on their own landing.
  - A window on each floor — purposefully vague — leads OUT to its
    landing (one-way; climbing in is a future hidden-exit mechanic).
    Floors 3-5 exit from the east units; the 6th exits from the FLOOR
    HALLWAY, because the bolt-on is communal (narrative placement).
  - The iron itself works both ways, z3 through z6.
  - The bottom is a one-way drop onto Hammett's Boot - Shin Plate.
  - East Roof's edge into the column now falls ONE story onto the
    bolt-on landing instead of seven to the Heel.
  - Landings replace four air cells at (-8,-18) z3..z6; every exit
    that pointed at those air cells (including falls from above) is
    repointed to the landings, so the column still resolves.

Skeleton only: names, coordinates, exits. No descriptions.
"""
from evennia import create_object
from evennia.objects.models import ObjectDB

EXIT_TC = "typeclasses.exits.Exit"
ROOM_TC = "typeclasses.rooms.Room"
COL_X, COL_Y = -8, -18


def by_key(key):
    r = ObjectDB.objects.filter(db_key=key).first()
    assert r, f"missing: {key}"
    return r


def room_at(x, y, z):
    for r in ObjectDB.objects.filter(db_attributes__db_key="xyz"):
        if r.attributes.get("xyz") == (x, y, z):
            return r
    return None


def has_exit(room, name):
    return any(e.key == name for e in room.exits)


def window_alias(host):
    """The owner's '(w) NOT WEST' rule: alias w only where unambiguous."""
    for e in host.exits:
        if e.key == "west" or "w" in (e.aliases.all() or []):
            return ["win"]
    return ["w"]


shin = by_key("Hammett's Boot - Shin Plate")
hosts = {
    3: by_key("The Brackett Arms - Unit 3B"),
    4: by_key("The Brackett Arms - Unit 4B"),
    5: by_key("The Brackett Arms - Unit 5B"),
    6: by_key("The Brackett Arms - Floor 6 Hall"),
}
FLOOR = {3: "Third", 4: "Fourth", 5: "Fifth", 6: "Sixth"}

landings = {}
made_rooms = made_exits = repointed = 0
for z in (3, 4, 5, 6):
    name = f"The Brackett Arms - Fire Escape ({FLOOR[z]} Floor)"
    existing = ObjectDB.objects.filter(db_key=name).first()
    if existing:
        landings[z] = existing
        continue
    air = room_at(COL_X, COL_Y, z)
    assert air and air.attributes.get("is_sky_room"), \
        f"expected air cell at ({COL_X},{COL_Y},{z})"
    landing = create_object(ROOM_TC, key=name)
    landing.db.xyz = (COL_X, COL_Y, z)
    landing.db.type = "rooftop"
    landing.db.outside = True
    landing.db.is_ground = True
    landing.db.is_sky_room = False
    made_rooms += 1
    # every exit that pointed at the air cell now points at the iron —
    # including falls from the air above, which land on the escape
    for ex in ObjectDB.objects.filter(db_destination=air):
        ex.destination = landing
        ex.save()
        repointed += 1
    air.delete()
    landings[z] = landing

# the windows: one-way out, purposefully vague
for z, host in hosts.items():
    if not has_exit(host, "window"):
        create_object(EXIT_TC, key="window", aliases=window_alias(host),
                      location=host, destination=landings[z])
        made_exits += 1

# the iron works both ways, z3..z6
for lo, hi in ((3, 4), (4, 5), (5, 6)):
    if not has_exit(landings[lo], "up"):
        create_object(EXIT_TC, key="up", aliases=["u"],
                      location=landings[lo], destination=landings[hi])
        made_exits += 1
    if not has_exit(landings[hi], "down"):
        create_object(EXIT_TC, key="down", aliases=["d"],
                      location=landings[hi], destination=landings[lo])
        made_exits += 1

# the bottom: one-way drop onto the Boot's shin
if not has_exit(landings[3], "drop"):
    create_object(EXIT_TC, key="drop", aliases=["down", "d"],
                  location=landings[3], destination=shin)
    made_exits += 1

# East Roof's edge now falls one story onto the bolt-on landing
# (the z7 roofs use the older style: a plain walk into the air cell,
# with the air column's own down-chain doing the falling — which the
# repointing above already lands on the bolt-on. Make it explicit.)
east_roof = by_key("The Brackett Arms - East Roof")
edge_fixed = False
for ex in east_roof.exits:
    dest = ex.destination
    if dest and dest.attributes.get("xyz") == (COL_X, COL_Y, 7):
        ex.db.is_edge = True
        ex.db.edge_difficulty = 8
        ex.db.fall_room = landings[6].id
        ex.db.fall_distance = 1
        ex.db.fall_damage = 5
        edge_fixed = True
assert edge_fixed, "East Roof exit into the column not found — inspect by hand"

print(f"BUILD 003 complete: {made_rooms} landings, {made_exits} exits, "
      f"{repointed} exits repointed onto the iron, roof edge softened.")
