"""Build 062 — Cistern No. 1: ne crossing + entrance via the avionics stalls.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/062_cistern_ne_and_entrance.py
    then a foreground reload.

Owner: the lid gets a SECOND jump line — northeast over the alley's
bend into the Fungary NORTH Platform (Level 1) — and the ladder moves
off Braddock to #5110, Shipbreaker Alley's avionics-stall south end
(6,-19,0), one diagonal step from the tank (to be made hidden later).

    #5110 --ladder--> C1 lid (5,-19,1)
      --east gap--> air (6,-19,1) --> South Platform (Level 1)   [existing]
      --ne gap-->   air (6,-18,1) --> North Platform (Level 1)   [new]

Both lines collinear; three-part gap wiring throughout. Re-run-safe.
"""
from evennia import create_object
from evennia.objects.models import ObjectDB
from evennia.utils.search import search_object
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
plat_n1 = by_key("The Fungary - North Platform (Level 1)")
braddock = at((5, -20, 0))
stalls = search_object("#5110")[0]

# 1. move the entrance: Braddock ladder out, avionics-stall ladder in
removed = 0
for room, key in ((braddock, "up"), (c1, "down")):
    if room is None:
        continue
    for e in list(room.exits):
        if e.key == key and e.destination in (c1, braddock):
            e.delete()
            removed += 1


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


added = link(stalls, c1, "up", "u")
added += link(c1, stalls, "down", "d")

# 2. the northeast line and its air
air_ne = at((6, -18, 1))
if air_ne is None:
    air_ne = create_object(SKY_TC, key="In the Air")
    air_ne.db.xyz = (6, -18, 1)
air_ne.key = "In the Air"
air_ne.db.type = "sky"
air_ne.db.is_sky_room = True
air_ne.db.outside = True
air_ne.db.desc = ("Open air over Shipbreaker Alley's bend, on the long "
                  "diagonal between Cistern No. 1's lid and the Fungary's "
                  "north rail. The avionics tarps ripple below.")

added += link(c1, air_ne, "northeast", "ne", edge=7)
added += link(plat_n1, air_ne, "southwest", "sw", edge=7)
for room, key, far in ((c1, "northeast", plat_n1), (plat_n1, "southwest", c1)):
    for e in room.exits:
        if e.key == key and e.db.is_gap:
            e.db.gap_destination = far.id
            e.db.sky_room = air_ne.id

# 3. desc: the lid now names both lines and the stall ladder
c1.db.desc = ("The lid of Greenhaus Cistern No. 1 — the sole survivor of "
              "the numbered set on this block, a squat riveted drum on "
              "splayed legs over the corner off Braddock. The deck plate "
              "is dished with age and slick where the fill valve weeps; "
              "the numeral is repainted annually by someone who clearly "
              "hates ladders. The ladder drops among the avionics stalls "
              "at the alley's south end. East and northeast, across the "
              "lane's air, the Fungary's first-level rails wait for the "
              "committed.")

print(f"BUILD 062: entrance -> #5110 (avionics stalls); ne line laid to the "
      f"North Platform. {removed} old pieces removed, {added} exits added.")
