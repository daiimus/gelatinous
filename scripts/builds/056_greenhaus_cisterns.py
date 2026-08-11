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

DESC = ("A slatted service deck braced between Cistern No. 1's legs, a "
        "storey off the corner lot — the tank's riveted belly hangs close "
        "overhead, and the ladder cage runs on up through a cut in the "
        "plate. The deck's outer rail is worn bright in two places, "
        "exactly where you'd vault it: east and northeast, across the "
        "lane's air, the Fungary's first-level rails wait for the "
        "committed. The stall ladder drops away below.")

CAGE_DESC = (
    "The rung cage up Cistern No. 1's flank, level with the tank's "
    "waist — the Greenhaus band curves away on both sides, older and "
    "greener than its siblings', the numeral's fresh paint the only "
    "bright thing on it. The catwalk ring's bulb string buzzes at knee "
    "height. Below, the leg platform's deck; above, the lid's rail "
    "against the sky.")

TOP_DESC = (
    "The lid of Greenhaus Cistern No. 1 — a riveted deck behind a rail, "
    "the red air-hazard beacon ticking overhead, the deck plate dished "
    "with age and slick where the fill valve weeps. A service hatch "
    "sits off-centre, its wheel stiff with verdigris. From up here the "
    "runt finally has the view it always deserved: the Fungary's "
    "grow-bands burning to the east, Braddock's crawl below, and its "
    "tall twin standing sentinel far off on the Spillane.")

INTERIOR_DESC = (
    "Inside the runt. No. 1's drum is shallow and old — the hatch-light "
    "lands on maybe a hand's depth of standing water over a sediment the "
    "colour of tea, ring-marked up the walls where better years stood "
    "deeper. In the centre squats the pump housing, a cold iron toad of "
    "a machine, its breaker box shut, its gauge needle asleep on the pin. "
    "GH-1 is stencilled on the casing beside an inspection tally that "
    "stopped years ago. The rivets tick as the day's heat leaves.")


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
    c1 = create_object(ROOM_TC, key="Greenhaus Cistern No. 1 - Leg Platform")
    c1.db.xyz = C1_TOP
    made += 1
c1.key = "Greenhaus Cistern No. 1 - Leg Platform"
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

# the column above the platform: ladder cage (z2) and tank top (z3);
# no atlas skins — the full-stature cistern_solo sprite on the z1 cell
# draws the whole tank
cage = at((5, -19, 2))
if cage is None:
    cage = create_object(ROOM_TC, key="Greenhaus Cistern No. 1 - Ladder Cage")
    cage.db.xyz = (5, -19, 2)
    made += 1
cage.db.desc = CAGE_DESC
cage.db.type = "cistern"
cage.db.outside = True
top = at((5, -19, 3))
if top is None:
    top = create_object(ROOM_TC, key="Greenhaus Cistern No. 1 - Tank Top")
    top.db.xyz = (5, -19, 3)
    made += 1
top.db.desc = TOP_DESC
top.db.type = "cistern"
top.db.outside = True
exits += link(c1, cage, "up", "u")
exits += link(cage, c1, "down", "d")
exits += link(cage, top, "up", "u")
exits += link(top, cage, "down", "d")

# the belly (every cistern gets one: the future pump's socket)
inside = by_key("Greenhaus Cistern No. 1 - Inside the Tank")
if inside is None:
    inside = create_object(ROOM_TC,
                           key="Greenhaus Cistern No. 1 - Inside the Tank")
    made += 1
inside.db.desc = INTERIOR_DESC
inside.db.type = "interior"
inside.db.outside = False
exits += link(top, inside, "in", "hatch")
exits += link(inside, top, "out", "o")

print(f"BUILD 056: Cistern No. 1 — {made} rooms, {exits} exits. "
      f"Route: Braddock ladder -> C1 -> east over the alley -> South Platform L1.")
