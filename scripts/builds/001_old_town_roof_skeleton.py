"""Build 001 — Old Town roof skeleton, phase 1 (Head Builder arc).

Skeleton only: room names, coordinates, exits/edges. NO descriptions —
the prose pass comes later. Run inside the container:

    evennia shell < scripts/builds/001_old_town_roof_skeleton.py

then `evennia reload` (foreground) so the running server's idmapper
sees the new rooms.

Work items (from the wiring audit, 2026-08-05):
  A. Wire the Brackett z6 gap: Unit 6A Terrace <-> South Wing Roof West.
  B. WITHDRAWN — Queen of Cups Lobby Roof is sealed BY DESIGN.
  C. Roof Shipbreaker Alley (the south grid's one unroofed building):
     two strip rooms at z1, a hatch up from the yard, parapet edges.
  D. The colony's first furniture: a water tower platform above the
     Kaspar Urgent Care rooftop (F2 — ladder up, vantage, +1).
"""
from evennia import create_object
from evennia.objects.models import ObjectDB

EXIT_TC = "typeclasses.exits.Exit"
ROOM_TC = "typeclasses.rooms.Room"

# GRID COMPASS (game space): north = +y, EAST = +x.
# (The atlas RENDER is horizontally mirrored — screen-east is -x there.
#  Exits always use game space. Verified against South Wing Roof East.)
OPP = {"north": "south", "south": "north", "east": "west", "west": "east",
       "up": "down", "down": "up",
       "northeast": "southwest", "southwest": "northeast",
       "northwest": "southeast", "southeast": "northwest"}
AL = {"north": ["n"], "south": ["s"], "east": ["e"], "west": ["w"],
      "up": ["u"], "down": ["d"],
      "northeast": ["ne"], "southwest": ["sw"],
      "northwest": ["nw"], "southeast": ["se"]}


def room_at(x, y, z):
    for r in ObjectDB.objects.filter(db_attributes__db_key="xyz"):
        if r.attributes.get("xyz") == (x, y, z):
            return r
    return None


def by_key(key):
    r = ObjectDB.objects.filter(db_key=key).first()
    assert r, f"missing room: {key}"
    return r


def has_exit(room, direction):
    return any(e.key == direction for e in room.exits)


def link(a, b, direction, one_way=False):
    made = 0
    if not has_exit(a, direction):
        create_object(EXIT_TC, key=direction, aliases=AL.get(direction),
                      location=a, destination=b)
        made += 1
    if not one_way and not has_exit(b, OPP[direction]):
        create_object(EXIT_TC, key=OPP[direction], aliases=AL.get(OPP[direction]),
                      location=b, destination=a)
        made += 1
    return made


def edge_down(roof, direction, street, exemplar_attrs):
    """A parapet edge: jumpable drop from a roof to the street below."""
    if has_exit(roof, direction):
        return 0
    ex = create_object(EXIT_TC, key=direction, aliases=AL.get(direction),
                       location=roof, destination=street)
    for k, v in exemplar_attrs.items():
        ex.attributes.add(k, v)
    ex.db.fall_room = street.id   # dbref int, per convention (export int()s it)
    return 1


def new_roof(key, x, y, z):
    r = ObjectDB.objects.filter(db_key=key).first()
    if r:
        return r, 0
    r = create_object(ROOM_TC, key=key)
    r.db.xyz = (x, y, z)
    r.db.type = "rooftop"
    r.db.outside = True
    r.db.is_ground = True
    r.db.is_sky_room = False
    return r, 1


made_rooms = made_exits = 0

# -- exemplar edge attrs: copy the Kaspar rooftop's street edge ---------
kaspar_roof = by_key("Kaspar Urgent Care - Rooftop")
edge_attrs = {}
for e in kaspar_roof.exits:
    if e.attributes.get("is_edge"):
        for k in ("is_edge", "edge_difficulty", "fall_damage", "fall_distance"):
            v = e.attributes.get(k)
            if v is not None:
                edge_attrs[k] = v
        break
assert edge_attrs.get("is_edge"), "no edge exemplar found on Kaspar rooftop"

# -- A. Brackett z6 join ------------------------------------------------
# terrace (-11,-20,6) -> roof (-10,-20,6): x+1 is EAST (game compass)
t6a = by_key("The Brackett Arms - Unit 6A Terrace")
sww = by_key("The Brackett Arms - South Wing Roof West")
made_exits += link(t6a, sww, "east")

# -- B. (WITHDRAWN) the Queen of Cups "orphan" --------------------------
# The Lobby Roof is exitless ON PURPOSE (owner, 2026-08-05): it is not
# supposed to be reachable from the stairway. Leave it sealed — it is a
# prize roof for a future traversal era, not a defect. Do not wire it.

# -- C. Shipbreaker Alley rooftop --------------------------------------
# footprint x5..6 (x6 = the eastern column; game east = +x), y-17..-19;
# two strip rooms tile it, anchored (5,-17) west and (6,-18) east
def is_street_room(r):
    return r is not None and (r.attributes.get("type") or "") in (
        "street", "bridge", "alley")

sb_ground = room_at(5, -17, 0)
assert sb_ground and "Shipbreaker" in sb_ground.key, "Shipbreaker yard not at (5,-17)"
west_strip, n1 = new_roof("Shipbreaker Alley - Rooftop (West)", 5, -17, 1)
east_strip, n2 = new_roof("Shipbreaker Alley - Rooftop (East)", 6, -18, 1)
made_rooms += n1 + n2
made_exits += link(sb_ground, west_strip, "up")           # yard hatch
made_exits += link(west_strip, east_strip, "southeast")   # strip join
w_lot = room_at(4, -17, 0)
if is_street_room(w_lot):
    made_exits += edge_down(west_strip, "west", w_lot, edge_attrs)
e_street = room_at(7, -18, 0)
if is_street_room(e_street):
    made_exits += edge_down(east_strip, "east", e_street, edge_attrs)

# -- D. the first water tower ------------------------------------------
kaspar_n = by_key("Kaspar Urgent Care - Rooftop (North)")
tower, n3 = new_roof("Kaspar Urgent Care - Water Tower", -2, -17, 2)
made_rooms += n3
made_exits += link(kaspar_n, tower, "up")                 # the leg ladder

print(f"BUILD 001 complete: {made_rooms} rooms, {made_exits} exits.")
print("Rooms are SKELETON ONLY — no descriptions yet, by design.")
