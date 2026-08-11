"""Build 058 — move Cistern No. 2 off the alley to (6,-17); rewire the line.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/058_cistern_two_north.py
    then a foreground reload.

Owner catch (same mistake as No. 1): No. 2's column stood over the
WALKABLE Shipbreaker Alley cell at (6,-18). Move catwalk and lid to the
empty block corner at (6,-17,1..2). The new line:

  C1 lid (5,-19,1) --ne edge--> In the Air over the alley bend (6,-18,1)
                                 <--south edge-- C2 catwalk (6,-17,1)
  C2 catwalk --up--> C2 lid (6,-17,2) --east edge--> Fungary North
  Platform (Level 2) (7,-17,2)   [replaces the old core hatch]

Air over a walkable street is established idiom (the Kaspar connector);
only structures must keep off walkable cells. 056 corrected to match.
Re-run-safe.
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
core2 = by_key("The Fungary - Stair Core (Level 2)")
plat2 = by_key("The Fungary - North Platform (Level 2)")

# 1. the move
if get_xyz(walk) != (6, -17, 1):
    walk.db.xyz = (6, -17, 1)
if get_xyz(top) != (6, -17, 2):
    top.db.xyz = (6, -17, 2)
top.db.desc = ("The lid of Greenhaus Cistern No. 2 — a wide riveted deck "
               "behind a rail that stops meaning it halfway round. The "
               "Greenhaus band below is fresh, the level gauge ticking "
               "green; the whole drum thrums faintly as the risers drink. "
               "East, the Fungary's second-level platform rail stands a "
               "hard jump away; southwest, the runt's lid shows past the "
               "alley's bend.")
walk.db.desc = ("Cistern No. 2's service catwalk — a mesh ring around the "
                "drum's waist, bolted to legs that straddle the waste "
                "corner north of Shipbreaker's bend. Feed pipes as thick "
                "as thighs leave the tank eastward for the farm towers. "
                "South, open air hangs over the alley's dogleg; the ladder "
                "to the lid is cold, wet, and load-rated for exactly one "
                "honest person.")
c1.db.desc = ("The lid of Greenhaus Cistern No. 1 — the runt of the "
              "numbered set, a squat riveted drum on splayed legs over the "
              "waste corner south of Shipbreaker's bend. The deck plate is "
              "dished with age and slick where the fill valve weeps; the "
              "numeral is repainted annually by someone who clearly hates "
              "ladders. The ladder rides the north leg down to the alley. "
              "Northeast, a flying leap over the lane's dogleg reaches its "
              "taller sibling's catwalk.")

# 2. the air over the alley bend
air = at((6, -18, 1))
if air is None:
    air = create_object(SKY_TC, key="In the Air")
    air.db.xyz = (6, -18, 1)
air.key = "In the Air"
air.db.type = "sky"
air.db.is_sky_room = True
air.db.outside = True
air.db.desc = ("Open air over Shipbreaker Alley's dogleg, between the two "
               "Greenhaus cisterns. The lane's awnings sag below; tank "
               "rails wait on either side.")

# 3. rewire: tear out the stale geometry, lay the honest line
removed = 0
for room, keys in ((c1, ("northeast",)), (walk, ("southwest", "west")),
                   (top, ("east",)), (core2, ("west",))):
    for e in list(room.exits):
        if e.key in keys and (e.db.is_edge or e.db.is_gap):
            e.delete()
            removed += 1


def edge(loc, dest, key, alias, diff):
    if any(e.key == key for e in loc.exits):
        return 0
    e = create_object(EXIT_TC, key=key, aliases=[alias],
                      location=loc, destination=dest)
    e.db.is_edge = True
    e.db.edge_difficulty = diff
    e.db.is_gap = True
    e.db.gap_difficulty = diff
    return 1


added = edge(c1, air, "northeast", "ne", 7)
added += edge(walk, air, "south", "s", 7)
added += edge(top, plat2, "east", "e", 8)
added += edge(plat2, top, "west", "w", 8)

print(f"BUILD 058: C2 -> {get_xyz(walk)}/{get_xyz(top)}; air over the bend "
      f"@(6,-18,1); {removed} stale edges removed, {added} laid. "
      f"Entry now lands on the North Platform (Level 2).")
