"""Build 001 — Old Town roof skeleton, phase 1 (Head Builder arc).

Skeleton only: room names, coordinates, exits/edges. NO descriptions —
the prose pass comes later. Run inside the container:

    evennia shell < scripts/builds/001_old_town_roof_skeleton.py

then `evennia reload` (foreground) so the running server's idmapper
sees the new rooms.

Work items (from the wiring audit, 2026-08-05):
  A. WITHDRAWN — the terrace/roof separation is the unit's security.
  B. Queen of Cups Lobby Roof: edges only (doctrine-complete: N/NE/NW
     onto Pessoa) — the
     stairway stays unconnected BY DESIGN; the roof is a prize.
  C. WITHDRAWN — Shipbreaker Alley is an open-air yard (outside=True);
     roofing it violated weather truth. new_roof() now refuses such.
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


DIRS8 = {"north": (0, 1), "south": (0, -1), "east": (1, 0), "west": (-1, 0),
         "northeast": (1, 1), "northwest": (-1, 1),
         "southeast": (1, -1), "southwest": (-1, -1)}


def wire_edges(roof, exemplar_attrs):
    """Doctrine-complete parapet pass: EVERY direction, diagonals
    included, that faces a street at ground level gets an edge exit.
    (Learned 2026-08-05: a single hand-picked edge misses the law.)"""
    x, y, z = roof.attributes.get("xyz")
    made = 0
    for name, (dx, dy) in DIRS8.items():
        if has_exit(roof, name):
            continue
        n = room_at(x + dx, y + dy, 0)
        if not n or (n.attributes.get("type") or "") not in (
                "street", "alley", "bridge"):
            continue
        ex = create_object(EXIT_TC, key=name, aliases=AL.get(name),
                           location=roof, destination=n)
        for k, v in exemplar_attrs.items():
            ex.attributes.add(k, v)
        ex.db.fall_room = n.id   # dbref int, per convention
        made += 1
    return made


def new_roof(key, x, y, z):
    r = ObjectDB.objects.filter(db_key=key).first()
    if r:
        return r, 0
    below = room_at(x, y, z - 1)
    assert below is not None, f"no room under proposed roof {key}"
    assert not below.attributes.get("outside"), (
        f"REFUSING roof over OUTSIDE room {below.key} — open sky below "
        "means no roof above (weather truth; learned at Shipbreaker)")
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

# -- A. (WITHDRAWN) the Brackett z6 "join" ------------------------------
# Unit 6A Terrace is the tenant's PRIVATE balcony — it opens into their
# bedroom. Joining it to the public roof plate bypasses the unit's
# biometric door (roof -> terrace -> bedroom). The separation the audit
# flagged as a gap WAS the security design. Withdrawn 2026-08-05
# (owner review). Pattern for the future: private terraces are not roof
# fabric; unit security perimeter includes the balcony.

# -- B. the Queen of Cups Lobby Roof ------------------------------------
# NO stairway access, ON PURPOSE (owner, 2026-08-05): the roof is a
# prize — you get there some other way, some other era. But its rims
# are real: edges only. One street borders it (Pessoa, north).
lobby_roof = by_key("Queen of Cups - Lobby Roof")
made_exits += wire_edges(lobby_roof, edge_attrs)

# -- C. (WITHDRAWN) Shipbreaker Alley "rooftop" -------------------------
# The audit called it an unroofed building because its type is
# "market" — but the NAME says Alley and every cell is outside=True:
# it is an open-air shipbreaking yard with sky overhead. A rooftop
# above an outside room is a weather-truth contradiction. Demolished
# 2026-08-05 (owner review). If the yard ever earns vertical texture,
# it will be crane gantries — its own thing, not a rooftop.

# -- D. the first water tower ------------------------------------------
kaspar_n = by_key("Kaspar Urgent Care - Rooftop (North)")
tower, n3 = new_roof("Kaspar Urgent Care - Water Tower", -2, -17, 2)
made_rooms += n3
made_exits += link(kaspar_n, tower, "up")                 # the leg ladder

print(f"BUILD 001 complete: {made_rooms} rooms, {made_exits} exits.")
print("Rooms are SKELETON ONLY — no descriptions yet, by design.")
