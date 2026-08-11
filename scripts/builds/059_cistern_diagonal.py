"""Build 059 — straighten the cistern crossing into one true diagonal.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/059_cistern_diagonal.py
    then a foreground reload.

Owner catch: C1 at (5,-19) and C2 at (6,-17) sat a knight's move apart,
so the crossing bent mid-air — a jump's momentum goes straight, and the
exits didn't align with any straight line. Final geometry (owner pick):

    C1 lid (4,-19,1) --ne--> In the Air (5,-18,1) <--sw-- C2 catwalk
    (6,-17,1): ONE straight diagonal, parallel to the alley's own
    dogleg, tanks flanking the bend. Ladder now rides up from Braddock
    (4,-20,0). C2 lid -> Fungary North Platform (Level 2) unchanged.

The old air cell over (6,-18,1) is deleted. Re-run-safe.
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

# 1. the move
if get_xyz(c1) != (4, -19, 1):
    c1.db.xyz = (4, -19, 1)
c1.db.desc = ("The lid of Greenhaus Cistern No. 1 — the runt of the "
              "numbered set, a squat riveted drum on splayed legs over the "
              "block corner off Braddock. The deck plate is dished with age "
              "and slick where the fill valve weeps; the numeral is "
              "repainted annually by someone who clearly hates ladders. The "
              "ladder rides the south leg down to the avenue. Northeast, "
              "the long diagonal over Shipbreaker's dogleg ends at its "
              "taller sibling's catwalk.")
walk.db.desc = ("Cistern No. 2's service catwalk — a mesh ring around the "
                "drum's waist, bolted to legs that straddle the waste "
                "corner north of Shipbreaker's bend. Feed pipes as thick "
                "as thighs leave the tank eastward for the farm towers. "
                "Southwest, the long diagonal over the lane's dogleg runs "
                "back to the runt; the ladder to the lid is cold, wet, and "
                "load-rated for exactly one honest person.")

# 2. tear out the bent geometry
removed = 0
old_air = at((6, -18, 1))
alley = at((5, -18, 0))
for room, keys in ((c1, ("northeast", "down")), (walk, ("south",)),
                   ((alley or c1), ("up",))):
    for e in list(room.exits):
        if e.key in keys and (e.destination in (c1, old_air) or room is c1):
            e.delete()
            removed += 1
if old_air is not None and not any(True for _ in old_air.exits):
    old_air.delete()
    removed += 1

# 3. the straight diagonal's air, over the alley's own bend cell
air = at((5, -18, 1))
if air is None:
    air = create_object(SKY_TC, key="In the Air")
    air.db.xyz = (5, -18, 1)
air.key = "In the Air"
air.db.type = "sky"
air.db.is_sky_room = True
air.db.outside = True
air.db.desc = ("Open air over Shipbreaker Alley's dogleg, halfway along "
               "the cistern diagonal. The lane's awnings sag below; a tank "
               "rail waits at either end of the line.")


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


braddock = at((4, -20, 0))
added = link(braddock, c1, "up", "u")
added += link(c1, braddock, "down", "d")
added += link(c1, air, "northeast", "ne", edge=7)
added += link(walk, air, "southwest", "sw", edge=7)

print(f"BUILD 059: C1 -> {get_xyz(c1)}; air over the bend @(5,-18,1); "
      f"{removed} stale pieces removed, {added} laid. One straight diagonal.")
