"""Build 056 — Greenhaus Cistern No. 1: the western connector.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/056_greenhaus_cisterns.py
    then a foreground reload.

FINAL FORM (after 057-061 iterations, owner-settled): ONE cistern — the
squat No. 1 at (5,-19,1) over the corner off Braddock — with a straight
east crossing at z1 into the farm:

    Shipbreaker's avionics stalls (6,-19,0) --ladder--> C1 lid (5,-19,1)
      --east gap--> air (6,-19,1) --> South Platform (Level 1)
      --ne gap-->   air (6,-18,1) --> North Platform (Level 1)
    (the stall ladder is slated to become HIDDEN later)

Cistern No. 2 was built and then retired the same day (its numeral
returns elsewhere later); No. 3 stands as a landmark at (13,-15). Gap
exits carry the three-part wiring (destination=air for descents,
gap_destination=the far perch, sky_room=the air) — build 060's law.
Re-run-safe.
"""
from evennia import create_object
from evennia.objects.models import ObjectDB
from world.spatial import get_xyz

ROOM_TC = "typeclasses.rooms.Room"
SKY_TC = "typeclasses.rooms.SkyRoom"
EXIT_TC = "typeclasses.exits.Exit"

C1_TOP = (5, -19, 1)

DESC = ("The lid of Greenhaus Cistern No. 1 — the sole survivor of the "
        "numbered set on this block, a squat riveted drum on splayed legs "
        "over the corner off Braddock. The deck plate is dished with age "
        "and slick where the fill valve weeps; the numeral is repainted "
        "annually by someone who clearly hates ladders. The ladder drops "
        "among the avionics stalls at the alley's south end. East and "
        "northeast, across the lane's air, the Fungary's first-level "
        "rails wait for the committed.")


def at(xyz):
    return next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
                 if r.destination is None and get_xyz(r) == xyz), None)


def by_key(key):
    return next((r for r in ObjectDB.objects.filter(db_key=key)
                 if r.destination is None), None)


def link(loc, dest, key, alias, edge=None):
    if loc is None or dest is None or any(e.key == key for e in loc.exits):
        return 0
    e = create_object(EXIT_TC, key=key, aliases=[alias],
                      location=loc, destination=dest)
    if edge is not None:
        e.db.is_edge = True
        e.db.edge_difficulty = edge
        e.db.is_gap = True
        e.db.gap_difficulty = edge
    return 1


made = exits = 0
c1 = at(C1_TOP)
if c1 is None:
    c1 = create_object(ROOM_TC, key="Greenhaus Cistern No. 1 - Tank Top")
    c1.db.xyz = C1_TOP
    made += 1
c1.key = "Greenhaus Cistern No. 1 - Tank Top"
c1.db.desc = DESC
c1.db.type = "cistern"
c1.db.atlas_skin = "cistern_solo"
c1.db.outside = True

air = at((6, -19, 1))
if air is None:
    air = create_object(SKY_TC, key="In the Air")
    air.db.xyz = (6, -19, 1)
    made += 1
air.db.type = "sky"
air.db.is_sky_room = True
air.db.outside = True
air.db.desc = ("Open air over Shipbreaker Alley, on the straight line "
               "between Cistern No. 1's lid and the Fungary's first-level "
               "rail. The lane's awnings sag below.")

stalls = at((6, -19, 0))          # Shipbreaker's avionics-stall south end
plat_s1 = by_key("The Fungary - South Platform (Level 1)")
plat_n1 = by_key("The Fungary - North Platform (Level 1)")
air_ne = at((6, -18, 1))
if air_ne is None:
    air_ne = create_object(SKY_TC, key="In the Air")
    air_ne.db.xyz = (6, -18, 1)
    made += 1
air_ne.db.type = "sky"
air_ne.db.is_sky_room = True
air_ne.db.outside = True
air_ne.db.desc = ("Open air over Shipbreaker Alley's bend, on the long "
                  "diagonal between Cistern No. 1's lid and the Fungary's "
                  "north rail. The avionics tarps ripple below.")
exits += link(stalls, c1, "up", "u")
exits += link(c1, stalls, "down", "d")
exits += link(c1, air, "east", "e", edge=7)
exits += link(plat_s1, air, "west", "w", edge=7)
exits += link(c1, air_ne, "northeast", "ne", edge=7)
exits += link(plat_n1, air_ne, "southwest", "sw", edge=7)
for room, key, far, sky in ((c1, "east", plat_s1, air),
                            (plat_s1, "west", c1, air),
                            (c1, "northeast", plat_n1, air_ne),
                            (plat_n1, "southwest", c1, air_ne)):
    for e in room.exits:
        if e.key == key and e.db.is_gap:
            e.db.gap_destination = far.id
            e.db.sky_room = sky.id

print(f"BUILD 056: Cistern No. 1 — {made} rooms, {exits} exits. "
      f"Route: Braddock ladder -> C1 -> east over the alley -> South Platform L1.")
