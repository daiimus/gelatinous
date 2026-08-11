"""Build 057 — move Cistern No. 1 one cell south, off the alley.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/057_cistern_one_south.py
    then a foreground reload.

Owner catch: No. 1 at (5,-18,1) stood directly over the WALKABLE
Shipbreaker Alley cell. Move it to (5,-19,1) — over the empty block
corner south of the alley — and make the hop to No. 2's catwalk the
true diagonal it always wanted to be (northeast, ne). The alley ladder
stays: the tank's north leg is the one you climb from the lane.
056 is corrected to match for fresh-world replays. Re-run-safe.
"""
from evennia import create_object
from evennia.objects.models import ObjectDB
from world.spatial import get_xyz

EXIT_TC = "typeclasses.exits.Exit"


def by_key(key):
    return next((r for r in ObjectDB.objects.filter(db_key=key)
                 if r.destination is None), None)


c1 = by_key("Greenhaus Cistern No. 1 - Tank Top")
walk = by_key("Greenhaus Cistern No. 2 - Service Catwalk")

# 1. the move
if get_xyz(c1) != (5, -19, 1):
    c1.db.xyz = (5, -19, 1)
c1.db.desc = ("The lid of Greenhaus Cistern No. 1 — the runt of the numbered "
              "set, a squat riveted drum on splayed legs over the waste "
              "corner south of Shipbreaker's bend. The deck plate is dished "
              "with age and slick where the fill valve weeps; the Greenhaus "
              "band has gone verdigris except where the numeral is "
              "repainted, annually, by someone who clearly hates ladders. "
              "The ladder rides the north leg down to the alley. Northeast, "
              "its taller sibling's catwalk hangs a committed leap away.")

# 2. rewire the gap: cardinal east/west out, true diagonal in
removed = 0
for room, key in ((c1, "east"), (walk, "west")):
    for e in list(room.exits):
        if e.key == key and e.db.is_edge:
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


added = edge(c1, walk, "northeast", "ne", 7)
added += edge(walk, c1, "southwest", "sw", 7)

print(f"BUILD 057: Cistern No. 1 -> {get_xyz(c1)}; {removed} cardinal edges "
      f"removed, {added} diagonal edges added. Ladder untouched.")
