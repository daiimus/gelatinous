"""Build 065 — Cistern No. 1's rooms match No. 3, plus the Leg Platform.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/065_cistern_one_stature_rooms.py
    then a foreground reload.

Owner: with the art at full stature, the rooms follow No. 3's pattern —
ladder column, tank top, belly — but No. 1 keeps its signature: the
newbie jump deck stays at z1 as the LEG PLATFORM, a slatted service
deck braced between the legs, carrying both Level-1 crossings exactly
as wired. The chain:

    #5110 stalls --ladder--> Leg Platform (5,-19,1)   [was the Tank Top;
        same room object, so the east/ne gap wiring survives untouched]
      --up--> Ladder Cage (5,-19,2)
      --up--> Tank Top (5,-19,3)  [rails, hatch wheel, beacon overhead]
      --in--> Inside the Tank     [same interior; 'out' retargeted]

z2/z3 cells carry no atlas skin — the full-stature cistern_solo sprite
on the z1 anchor cell draws the whole tank. Re-run-safe.
"""
from evennia import create_object
from evennia.objects.models import ObjectDB
from world.spatial import get_xyz

ROOM_TC = "typeclasses.rooms.Room"
EXIT_TC = "typeclasses.exits.Exit"
ALIAS = {"up": ["u"], "down": ["d"], "in": ["hatch", "enter"],
         "out": ["o", "exit"]}


def by_key(key):
    return next((r for r in ObjectDB.objects.filter(db_key=key)
                 if r.destination is None), None)


def at(xyz):
    return next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
                 if r.destination is None and get_xyz(r) == xyz), None)


def link(loc, dest, key):
    if loc is None or dest is None or any(e.key == key for e in loc.exits):
        return 0
    create_object(EXIT_TC, key=key, aliases=ALIAS.get(key, []),
                  location=loc, destination=dest)
    return 1


# 1. the old lid becomes the Leg Platform (same object; wiring survives)
plat = (by_key("Greenhaus Cistern No. 1 - Tank Top")
        if at((5, -19, 3)) is None else by_key(
            "Greenhaus Cistern No. 1 - Leg Platform"))
if plat is None:
    plat = by_key("Greenhaus Cistern No. 1 - Leg Platform")
if get_xyz(plat) != (5, -19, 1):
    raise SystemExit(f"unexpected platform location: {get_xyz(plat)}")
plat.key = "Greenhaus Cistern No. 1 - Leg Platform"
plat.db.desc = (
    "A slatted service deck braced between Cistern No. 1's legs, a "
    "storey off the corner lot — the tank's riveted belly hangs close "
    "overhead, and the ladder cage runs on up through a cut in the "
    "plate. The deck's outer rail is worn bright in two places, "
    "exactly where you'd vault it: east and northeast, across the "
    "lane's air, the Fungary's first-level rails wait for the "
    "committed. The stall ladder drops away below.")

# the platform's old hatch exit moves to the new top
removed = 0
inside = by_key("Greenhaus Cistern No. 1 - Inside the Tank")
for e in list(plat.exits):
    if e.key == "in":
        e.delete()
        removed += 1

# 2. the ladder cage and the new tank top
made = exits = 0
cage = at((5, -19, 2))
if cage is None:
    cage = create_object(ROOM_TC,
                         key="Greenhaus Cistern No. 1 - Ladder Cage")
    cage.db.xyz = (5, -19, 2)
    made += 1
cage.key = "Greenhaus Cistern No. 1 - Ladder Cage"
cage.db.type = "cistern"
cage.db.outside = True
cage.attributes.remove("atlas_skin")
cage.db.desc = (
    "The rung cage up Cistern No. 1's flank, level with the tank's "
    "waist — the Greenhaus band curves away on both sides, older and "
    "greener than its siblings', the numeral's fresh paint the only "
    "bright thing on it. The catwalk ring's bulb string buzzes at "
    "knee height. Below, the leg platform's deck; above, the lid's "
    "rail against the sky.")

top = at((5, -19, 3))
if top is None:
    top = create_object(ROOM_TC, key="Greenhaus Cistern No. 1 - Tank Top")
    top.db.xyz = (5, -19, 3)
    made += 1
top.key = "Greenhaus Cistern No. 1 - Tank Top"
top.db.type = "cistern"
top.db.outside = True
top.attributes.remove("atlas_skin")
top.db.desc = (
    "The lid of Greenhaus Cistern No. 1 — a riveted deck behind a rail, "
    "the red air-hazard beacon ticking overhead, the deck plate dished "
    "with age and slick where the fill valve weeps. A service hatch "
    "sits off-centre, its wheel stiff with verdigris. From up here the "
    "runt finally has the view it always deserved: the Fungary's "
    "grow-bands burning to the east, Braddock's crawl below, and its "
    "tall twin standing sentinel far off on the Spillane.")

exits += link(plat, cage, "up")
exits += link(cage, plat, "down")
exits += link(cage, top, "up")
exits += link(top, cage, "down")
exits += link(top, inside, "in")
# retarget the interior's way out to the new top
for e in inside.exits:
    if e.key == "out" and e.destination != top:
        e.destination = top

print(f"BUILD 065: No. 1 room-matched to No. 3 + Leg Platform — {made} new "
      f"rooms, {exits} exits, {removed} moved hatch. Jump wiring untouched "
      f"at z1.")
