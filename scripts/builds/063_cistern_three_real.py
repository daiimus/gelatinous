"""Build 063 — Cistern No. 3 becomes real: Overflow Alley + four rooms.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/063_cistern_three_real.py
    then a foreground reload.

The landmark at (13,-15) has been atlas scenery since it was raised;
the world now catches up. A dead-end spur — OVERFLOW ALLEY, named for
the fill-valve weep — runs east off Spillane beneath the tank's legs,
and the cistern gets four rooms: two ladder-cage rooms up the column,
the tank top, and a hatch that puts you INSIDE the drum.

    Spillane (12,-15,0) --east--> Overflow Alley (13,-15,0)
      --up--> Ladder Cage (Lower) (13,-15,1)
      --up--> Ladder Cage (Upper) (13,-15,2)
      --up--> Tank Top (13,-15,3)
      --in (hatch)--> Inside the Tank (off-grid interior)

The landmark's covers already claim this column (z0-4), so every room
slots beneath the existing art with no sprite work. The walkable alley
under the tank is fine by the overlap law: the law bars per-cell
STRUCTURE sprites capping walkable cells; a landmark on tall legs with
the lane dead-ending beneath them is the intended fiction. Re-run-safe.
"""
from evennia import create_object
from evennia.objects.models import ObjectDB
from world.spatial import get_xyz

ROOM_TC = "typeclasses.rooms.Room"
EXIT_TC = "typeclasses.exits.Exit"
ALIAS = {"east": ["e"], "west": ["w"], "up": ["u"], "down": ["d"],
         "in": ["hatch", "enter"], "out": ["o", "exit"]}

SPEC = [
    ((13, -15, 0), "Overflow Alley", "alley", True,
     "A dead-end spur off the Spillane, pinched between prefab flanks and "
     "roofed — eventually — by the riveted belly of Greenhaus Cistern "
     "No. 3, whose splayed legs straddle the lane. The fill valve high "
     "above weeps a permanent drip-line down the middle, feeding a green "
     "stripe of algae the width of a boot. Rung-cage bolts start at head "
     "height on the northern leg, stencilled GH-3 / AUTHORISED."),
    ((13, -15, 1), "Greenhaus Cistern No. 3 - Ladder Cage (Lower)",
     "cistern", True,
     "The rung cage up Cistern No. 3's northern leg — hoops of strap "
     "steel every metre, most of them true. Overflow Alley's drip-stripe "
     "glistens below; Spillane's steam drifts past at eye level. The "
     "rungs are wet. The rungs are always wet."),
    ((13, -15, 2), "Greenhaus Cistern No. 3 - Ladder Cage (Upper)",
     "cistern", True,
     "Higher in the cage, level with the tank's riveted waist. The "
     "Greenhaus band curves away on both sides, big as a road sign and "
     "fresher than anything else on the block. Wind finds the cage here; "
     "the whole leg hums when the risers drink. The corridor's yellow "
     "emergency lights make a runway of Spillane below."),
    ((13, -15, 3), "Greenhaus Cistern No. 3 - Tank Top",
     "cistern", True,
     "The lid of Greenhaus Cistern No. 3 — a wide riveted deck behind a "
     "rail, the red air-hazard beacon ticking overhead. The level gauge "
     "reads full-and-then-some; the deck thrums underfoot. A service "
     "hatch stands proud of the plate at the centre, its wheel polished "
     "bright by gloves. From here the whole eastern corridor lays itself "
     "out — the processor's steam north, the farm towers west."),
]

INTERIOR_DESC = (
    "Inside the tank. The hatch-light falls in one hard column onto black "
    "water that reaches to the knee and swallows sound whole — every drip "
    "off the crown rings twice. The walls curve away into a dark that the "
    "gauge lines phosphoresce faintly green. Stencilled at the waterline, "
    "upside down, someone has painted: DON'T DRINK IT EITHER. It is very "
    "cold, and impossibly loud when the risers drink.")


def at(xyz):
    return next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
                 if r.destination is None and get_xyz(r) == xyz), None)


def by_key(key):
    return next((r for r in ObjectDB.objects.filter(db_key=key)
                 if r.destination is None), None)


def link(loc, dest, key):
    if loc is None or dest is None or any(e.key == key for e in loc.exits):
        return 0
    create_object(EXIT_TC, key=key, aliases=ALIAS.get(key, []),
                  location=loc, destination=dest)
    return 1


made = exits = 0
rooms = {}
for xyz, key, rtype, outside, desc in SPEC:
    r = at(xyz)
    if r is None:
        r = create_object(ROOM_TC, key=key)
        r.db.xyz = xyz
        made += 1
    r.key = key
    r.db.desc = desc
    r.db.type = rtype
    r.db.outside = outside
    rooms[xyz] = r

inside = by_key("Greenhaus Cistern No. 3 - Inside the Tank")
if inside is None:
    inside = create_object(ROOM_TC,
                           key="Greenhaus Cistern No. 3 - Inside the Tank")
    made += 1
inside.db.desc = INTERIOR_DESC
inside.db.type = "interior"
inside.db.outside = False

spillane = at((12, -15, 0))
exits += link(spillane, rooms[(13, -15, 0)], "east")
exits += link(rooms[(13, -15, 0)], spillane, "west")
for z in range(0, 3):
    exits += link(rooms[(13, -15, z)], rooms[(13, -15, z + 1)], "up")
    exits += link(rooms[(13, -15, z + 1)], rooms[(13, -15, z)], "down")
exits += link(rooms[(13, -15, 3)], inside, "in")
exits += link(inside, rooms[(13, -15, 3)], "out")

print(f"BUILD 063: Cistern No. 3 made real — {made} rooms, {exits} exits. "
      f"Spillane -> Overflow Alley -> two ladder cages -> Tank Top -> "
      f"in the drum.")
