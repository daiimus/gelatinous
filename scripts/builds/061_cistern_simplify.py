"""Build 061 — retire Cistern No. 2 (for now); No. 1 to the 5 slot.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/061_cistern_simplify.py
    then a foreground reload.

Owner call: Cistern No. 2 comes down entirely — the numeral returns
elsewhere later — and No. 1 moves to (5,-19,1), where the crossing
becomes one straight EAST line at z1:

    Braddock (5,-20) --ladder--> C1 lid (5,-19,1)
      --east gap--> In the Air over the alley (6,-19,1)
      --lands--> The Fungary - South Platform (Level 1) (7,-19,1)

Demolition manifest: both No. 2 rooms (occupants relocated to Braddock
first), the North Platform (Level 2) west edge into them, the old
crossing air at (5,-18,1), and C1's old ladder/edges. Re-run-safe.
"""
from evennia import create_object
from evennia.objects.models import ObjectDB
from world.spatial import get_xyz

EXIT_TC = "typeclasses.exits.Exit"
SKY_TC = "typeclasses.rooms.SkyRoom"


def by_key(key):
    return next((r for r in ObjectDB.objects.filter(db_key=key)
                 if r.destination is None), None)


def at(xyz):
    return next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
                 if r.destination is None and get_xyz(r) == xyz), None)


c1 = by_key("Greenhaus Cistern No. 1 - Tank Top")
walk = by_key("Greenhaus Cistern No. 2 - Service Catwalk")
top = by_key("Greenhaus Cistern No. 2 - Tank Top")
plat_n2 = by_key("The Fungary - North Platform (Level 2)")
plat_s1 = by_key("The Fungary - South Platform (Level 1)")
braddock_old = at((4, -20, 0))
braddock_new = at((5, -20, 0))

# 0. evacuate the doomed rooms
moved = 0
for room in (walk, top):
    if room is None:
        continue
    for o in list(room.contents):
        if o.destination is None and not o.db_typeclass_path.endswith("Exit"):
            if "character" in (o.db_typeclass_path or "").lower():
                o.move_to(braddock_new, quiet=True)
                o.msg("|yGreenhaus crews wave you off the tank — the whole "
                      "drum is coming down for relocation. You climb clear "
                      "to Braddock.|n")
                moved += 1

# 1. demolition
removed = 0
if plat_n2 is not None:
    for e in list(plat_n2.exits):
        if e.key == "west" and e.destination in (walk, top):
            e.delete()
            removed += 1
old_air = at((5, -18, 1))
for room in (walk, top, old_air):
    if room is not None:
        room.delete()
        removed += 1

# 2. C1 to the 5 slot; strip its stale exits
if c1 is not None and get_xyz(c1) != (5, -19, 1):
    c1.db.xyz = (5, -19, 1)
for e in list(c1.exits):
    e.delete()
    removed += 1
if braddock_old is not None:
    for e in list(braddock_old.exits):
        if e.destination == c1:
            e.delete()
            removed += 1
c1.db.desc = ("The lid of Greenhaus Cistern No. 1 — the sole survivor of "
              "the numbered set on this block, a squat riveted drum on "
              "splayed legs over the corner off Braddock. The deck plate "
              "is dished with age and slick where the fill valve weeps; "
              "the numeral is repainted annually by someone who clearly "
              "hates ladders. The ladder rides the south leg down to the "
              "avenue. East, across the alley's air, the Fungary's "
              "first-level platform rail waits for the committed.")

# 3. the straight east crossing
air = at((6, -19, 1))
if air is None:
    air = create_object(SKY_TC, key="In the Air")
    air.db.xyz = (6, -19, 1)
air.key = "In the Air"
air.db.type = "sky"
air.db.is_sky_room = True
air.db.outside = True
air.db.desc = ("Open air over Shipbreaker Alley, on the straight line "
               "between Cistern No. 1's lid and the Fungary's first-level "
               "rail. The lane's awnings sag below.")


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


def wire(room, key, far, sky):
    for e in room.exits:
        if e.key == key and e.db.is_gap:
            e.db.gap_destination = far.id
            e.db.sky_room = sky.id


added = link(braddock_new, c1, "up", "u")
added += link(c1, braddock_new, "down", "d")
added += link(c1, air, "east", "e", edge=7)
added += link(plat_s1, air, "west", "w", edge=7)
wire(c1, "east", plat_s1, air)
wire(plat_s1, "west", c1, air)

print(f"BUILD 061: No. 2 demolished, No. 1 -> {get_xyz(c1)}; {moved} occupants "
      f"evacuated, {removed} pieces removed, {added} exits laid. "
      f"Route: Braddock ladder -> C1 -> east over the alley -> South Platform L1.")
