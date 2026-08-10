"""Build 056 — Greenhaus Cisterns No. 1 and No. 2: the western connectors.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/056_greenhaus_cisterns.py
    then a foreground reload.

INTENT (playbook §0): the Verticals' water supply, and the western
approach that turns the farm towers from an island into a line. Two
riveted Greenhaus cisterns stand over Shipbreaker Alley's diagonal —
No. 1 squat at (5,-18), No. 2 taller at (6,-18) — feeding the Fungary's
riser. The parkour diagonal: alley ladder → No. 1 tank top (z1) → gap
east → No. 2 service catwalk (z1) → ladder → No. 2 tank top (z2) → gap
east through the riser hatch into the Fungary Stair Core (Level 2).
Every jump is same-level and cardinal; every climb is a ladder.
(Greenhaus Cistern No. 3 already stands at (13,-15) as a landmark —
this completes the numbered set.)

Re-run-safe. Rollback: delete the three rooms keyed "Greenhaus Cistern
No. 1/No. 2 - …" plus the alley's up exit and the core hatch edge.
"""
from evennia import create_object
from evennia.objects.models import ObjectDB
from world.spatial import get_xyz

ROOM_TC = "typeclasses.rooms.Room"
EXIT_TC = "typeclasses.exits.Exit"
ALIAS = {"north": ["n"], "south": ["s"], "east": ["e"], "west": ["w"],
         "up": ["u"], "down": ["d"]}

C1_TOP = (5, -18, 1)
C2_WALK = (6, -18, 1)
C2_TOP = (6, -18, 2)

DESCS = {
    C1_TOP: ("The lid of Greenhaus Cistern No. 1 — the runt of the numbered "
             "set, a squat riveted drum on splayed legs over Shipbreaker's "
             "bend. The deck plate is dished with age and slick where the "
             "fill valve weeps; the Greenhaus band has gone verdigris "
             "except where the numeral is repainted, annually, by someone "
             "who clearly hates ladders. East, its taller sibling's "
             "catwalk hangs a committed leap away."),
    C2_WALK: ("Cistern No. 2's service catwalk — a mesh ring around the "
              "drum's waist, bolted to legs that straddle the alley below. "
              "Feed pipes as thick as thighs leave the tank eastward, "
              "shouldering through a junction collar toward the farm "
              "towers. The ladder to the lid is cold, wet, and "
              "load-rated for exactly one honest person."),
    C2_TOP: ("The lid of Greenhaus Cistern No. 2 — a wide riveted deck "
             "behind a rail that stops meaning it halfway round. The "
             "Greenhaus band below is fresh, the level gauge ticking "
             "green; the whole drum thrums faintly as the risers drink. "
             "East, flush in the Fungary's concrete flank, a service "
             "hatch stencilled GH-RISER 01 stands a hard jump away."),
}


def at(xyz):
    return next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
                 if r.destination is None and get_xyz(r) == xyz), None)


def by_key(key):
    return next((r for r in ObjectDB.objects.filter(db_key=key)
                 if r.destination is None), None)


def has_exit(loc, key):
    return any(e.key == key for e in loc.exits)


def link(loc, dest, key, edge=None, gap=None):
    if loc is None or dest is None or has_exit(loc, key):
        return 0
    e = create_object(EXIT_TC, key=key, aliases=ALIAS.get(key, []),
                      location=loc, destination=dest)
    if edge is not None:
        e.db.is_edge = True
        e.db.edge_difficulty = edge
    if gap is not None:
        e.db.is_gap = True
        e.db.gap_difficulty = gap
    return 1


made = exits = 0
rooms = {}
SPEC = {C1_TOP: ("Greenhaus Cistern No. 1 - Tank Top", "cistern_solo"),
        C2_WALK: ("Greenhaus Cistern No. 2 - Service Catwalk", "cistern_walk"),
        C2_TOP: ("Greenhaus Cistern No. 2 - Tank Top", "cistern_top")}
for xyz, (key, skin) in SPEC.items():
    r = at(xyz)
    if r is None:
        r = create_object(ROOM_TC, key=key)
        r.db.xyz = xyz
        made += 1
    r.key = key
    r.db.desc = DESCS[xyz]
    r.db.type = "cistern"
    r.db.atlas_skin = skin
    r.db.outside = True
    rooms[xyz] = r

alley = at((5, -18, 0))
core2 = by_key("The Fungary - Stair Core (Level 2)")

# the ladder up No. 1 from the alley (public climb, both ways)
exits += link(alley, rooms[C1_TOP], "up")
exits += link(rooms[C1_TOP], alley, "down")
# the diagonal: No.1 top <-> No.2 catwalk (same-z gap over the alley bend)
exits += link(rooms[C1_TOP], rooms[C2_WALK], "east", edge=7, gap=7)
exits += link(rooms[C2_WALK], rooms[C1_TOP], "west", edge=7, gap=7)
# No. 2's own ladder, catwalk to lid
exits += link(rooms[C2_WALK], rooms[C2_TOP], "up")
exits += link(rooms[C2_TOP], rooms[C2_WALK], "down")
# the riser hatch: No.2 lid <-> Fungary Stair Core (Level 2)
exits += link(rooms[C2_TOP], core2, "east", edge=8, gap=8)
exits += link(core2, rooms[C2_TOP], "west", edge=8, gap=8)

print(f"BUILD 056: Greenhaus Cisterns No. 1 & 2 — {made} rooms, "
      f"{exits} exits. Route: Shipbreaker ladder → C1 → C2 → Fungary core L2.")
