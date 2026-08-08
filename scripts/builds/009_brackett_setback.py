"""Build 009 — the setback tower + roof deck (owner-designed).

    evennia shell < scripts/builds/009_brackett_setback.py
    then foreground reload (idmapper — data build).

Owner rulings (2026-08-07): the tower steps in from the full plate to
the 3x3 core at floor 12 and runs as plain apartment floors 12-15,
then a roof deck at 16. No stash rooms, no cargo spine — the elevator
is KEPT and extended to serve 12-15; the stairs continue past it to
the roof. The only outside element in the whole build is the roof
deck.

Layout per apartment floor (the floor-11 core, wings shaved off):
        x=-11          x=-10          x=-9
 y=-17  Stairwell      North Hall     Elevator Shaft
 y=-18  Unit A         Landing        Unit B
 y=-19  Unit C         South Hall     Unit D
Four corner units, each dooring onto a hall; the elevator lobby is
the Landing. Fire escape continues up the east iron for egress.

Roof deck = the strip model (3 rooms tiling the 3x3 at x=-10),
outside/rooftop, reached by the stairs. Flat and walkable now; jump
edges and the westward bridge to the wall are a later arc.
"""
from evennia import create_object
from evennia.objects.models import ObjectDB

ROOM_TC = "typeclasses.rooms.Room"
EXIT_TC = "typeclasses.exits.Exit"
B = "The Brackett Arms"
CORE = [(-11, -17), (-10, -17), (-9, -17),
        (-11, -18), (-10, -18), (-9, -18),
        (-11, -19), (-10, -19), (-9, -19)]


def by_key(key):
    r = ObjectDB.objects.filter(db_key=key).first()
    assert r, f"missing: {key}"
    return r


def has_exit(room, key):
    return any(e.key == key for e in room.exits)


def mk_exit(loc, dest, key, aliases=None):
    if has_exit(loc, key):
        return 0
    create_object(EXIT_TC, key=key, aliases=aliases or [], location=loc,
                  destination=dest)
    return 1


made_rooms = made_exits = 0

# ---- 1. floor-11 core as the template --------------------------------
T = {}
for r in ObjectDB.objects.filter(db_key__contains=B):
    xyz = r.attributes.get("xyz")
    if xyz and xyz[2] == 11 and (xyz[0], xyz[1]) in CORE:
        T[(xyz[0], xyz[1])] = r
assert len(T) == 9, f"core template incomplete: {len(T)}"
T_KEY = {pos: r.key for pos, r in T.items()}
T_TYPE = {pos: r.attributes.get("type") for pos, r in T.items()}
core_ids = {r.id for r in T.values()}
pos_of = {r.id: pos for pos, r in T.items()}
T_EXITS = []                            # intra-core horizontal only
for pos, r in T.items():
    for e in r.exits:
        d = e.destination
        if d is not None and d.id in core_ids:
            T_EXITS.append((pos, e.key, list(e.aliases.all()), pos_of[d.id]))


def floor_key(tkey, n):
    return tkey.replace("11", str(n))


# ---- 2. the apartment floors 12-15 -----------------------------------
floors = {}
for n in (12, 13, 14, 15):
    rooms = {}
    for pos in CORE:
        key_n = floor_key(T_KEY[pos], n)
        existing = ObjectDB.objects.filter(db_key=key_n).first()
        if existing:
            rooms[pos] = existing
            continue
        r = create_object(ROOM_TC, key=key_n)
        r.db.xyz = (pos[0], pos[1], n)
        r.db.type = T_TYPE[pos]
        r.db.outside = False
        made_rooms += 1
        rooms[pos] = r
    for f_pos, ekey, aliases, t_pos in T_EXITS:
        made_exits += mk_exit(rooms[f_pos], rooms[t_pos], ekey, aliases)
    floors[n] = rooms

# stairwell chain 11 -> 12 -> ... -> 15
prev = by_key(f"{B} - Stairwell (Floor 11)")
for n in (12, 13, 14, 15):
    cur = floors[n][(-11, -17)]
    made_exits += mk_exit(prev, cur, "up", ["u"]) + mk_exit(cur, prev, "down", ["d"])
    prev = cur

# ---- 3. the elevator is kept, extended to 15 -------------------------
car = by_key(f"{B} Elevator Car")
exemplar = None
for o in by_key(f"{B} - Floor 5 Landing").contents:
    if o.key == "call button":
        exemplar = o
assert exemplar, "no call-button exemplar"
stops = list(car.db.floors or [])
have = {lbl for _, lbl in stops}
for n in (12, 13, 14, 15):
    land = floors[n][(-10, -18)]
    if str(n) not in have:
        stops.append((land, str(n)))
    made_exits += mk_exit(land, car, "elevator", ["in"])
    if not any(o.key == "call button" for o in land.contents):
        btn = create_object(exemplar.typeclass_path, key="call button",
                            location=land)
        for a in exemplar.attributes.all():
            btn.attributes.add(a.key, a.value)
car.db.floors = stops

# ---- 4. the fire escape continues (egress) ---------------------------
FLOORNAME = {12: "Twelfth", 13: "Thirteenth", 14: "Fourteenth",
             15: "Fifteenth"}
prev_landing = by_key(f"{B} - Fire Escape (Eleventh Floor)")
for n in (12, 13, 14, 15):
    key = f"{B} - Fire Escape ({FLOORNAME[n]} Floor)"
    landing = ObjectDB.objects.filter(db_key=key).first()
    if not landing:
        landing = create_object(ROOM_TC, key=key)
        landing.db.xyz = (-8, -18, n)
        landing.db.type = "fire escape"
        landing.db.outside = True
        landing.db.is_ground = True
        landing.db.is_sky_room = False
        made_rooms += 1
    made_exits += mk_exit(prev_landing, landing, "up", ["u"])
    made_exits += mk_exit(landing, prev_landing, "down", ["d"])
    made_exits += mk_exit(floors[n][(-10, -18)], landing, "window")
    prev_landing = landing

# ---- 5. the roof deck at 16 (strip model, outside) -------------------
ROOF = {
    (-10, -17): f"{B} - Roof Deck (North)",
    (-10, -18): f"{B} - Roof Deck",
    (-10, -19): f"{B} - Roof Deck (South)",
}
roof = {}
for pos, key in ROOF.items():
    r = ObjectDB.objects.filter(db_key=key).first()
    if not r:
        r = create_object(ROOM_TC, key=key)
        r.db.xyz = (pos[0], pos[1], 16)
        r.db.type = "rooftop"
        r.db.outside = True
        r.db.is_ground = True
        made_rooms += 1
    roof[pos] = r
made_exits += mk_exit(roof[(-10, -17)], roof[(-10, -18)], "south", ["s"])
made_exits += mk_exit(roof[(-10, -18)], roof[(-10, -17)], "north", ["n"])
made_exits += mk_exit(roof[(-10, -18)], roof[(-10, -19)], "south", ["s"])
made_exits += mk_exit(roof[(-10, -19)], roof[(-10, -18)], "north", ["n"])
# the stairs top out onto the deck (elevator stops at 15)
st15 = floors[15][(-11, -17)]
made_exits += mk_exit(st15, roof[(-10, -17)], "up", ["u"])
made_exits += mk_exit(roof[(-10, -17)], st15, "down", ["d"])

# ---- 6. prose --------------------------------------------------------
ORD = {12: "twelfth", 13: "thirteenth", 14: "fourteenth", 15: "fifteenth"}
UNIT = {
    (-11, -18): ("west over Bhavani Corridor",
                 "windows west, the rooftops of the lower blocks fallen "
                 "away beneath the sill"),
    (-9, -18): ("east over the fire escape",
                "windows east onto the iron and, past it, the dead hull "
                "of the Boot"),
    (-11, -19): ("the southwest corner",
                 "corner-set, windows west and south, Braddock Avenue a "
                 "long drop below"),
    (-9, -19): ("the southeast corner",
                "corner-set, windows east and south, the wind finding "
                "every seam up here"),
}
LETTER = {(-11, -18): "A", (-9, -18): "B", (-11, -19): "C", (-9, -19): "D"}
written = 0


def put(room, desc, senses=None):
    global written
    if not room.db.desc:
        room.db.desc = desc
        if senses:
            room.db.sense_descs = senses
        written += 1


for n in (12, 13, 14, 15):
    rooms = floors[n]
    put(rooms[(-10, -18)],
        f"The floor-{n} landing, up in the setback tower where the plate "
        f"steps in to its narrow core — the wings are storeys below you "
        f"now. The elevator's doors, the halls north and south, and a "
        f"quiet the packed lower floors never hold.",
        {"auditory": "Wind worrying the window frames; the shaft "
                     "breathing far down.",
         "olfactory": "Cold air and cooking, thinner than below.",
         "tactile": "The floor has a faint sway you'd swear you imagined.",
         "atmospheric": "The crown of the old tower — as high as the "
                        "elevator climbs, and quiet with it."})
    put(rooms[(-10, -17)],
        f"The north hall on floor {n}: the stairwell one way, the "
        f"elevator the other, and the narrowed core's short run of "
        f"doors. Nothing cantilevers out here — the tower keeps its "
        f"weight tucked in above the twelfth-floor setback.")
    put(rooms[(-10, -19)],
        f"The south hall on floor {n}, serving the two southern corners. "
        f"The glass holds Braddock Avenue a long way down and the "
        f"colony's roofscape running off toward the crater wall.")
    put(rooms[(-11, -17)],
        f"The fire stairs at floor {n}, still climbing past where the "
        f"elevator's traffic thinned — welded-plate treads, the rebuild's "
        f"numbering, the last stretch before the roof.")
    put(rooms[(-9, -17)],
        f"The shaft at floor {n}: cable in the dark, counterweight "
        f"grease, the car's light passing like weather.")
    for pos, letter in LETTER.items():
        where, glass = UNIT[pos]
        put(rooms[pos],
            f"A hab in the narrowed crown of the tower, {where}: "
            f"{glass}. The colonization-era fittings — fold-down berth, "
            f"galley wall, wet cell — but {ORD[n]}-floor air and a view "
            f"the lower leases would pay for.")

put(roof[(-10, -17)],
    "The north end of the Brackett roof deck, where the stairs let out "
    "under open sky. The colony falls away on every side — lower "
    "rooftops, the amber grid of the streets, the crater wall standing "
    "off to the west with its dark unbuilt reaches.",
    {"auditory": "Wind, and the far wash of the colony three hundred "
                 "feet down.",
     "olfactory": "Cold and ozone and the faint tar of the deck.",
     "tactile": "The wind up here has real weight; the parapet is the "
                "only thing between you and the drop.",
     "atmospheric": "The crown of the tower. From here the only way "
                    "higher is the wall itself."})
put(roof[(-10, -18)],
    "The heart of the roof deck: flat plated tar, a low parapet, the "
    "stubbed head of the elevator machinery and the stairwell bulkhead "
    "the only structures breaking the open sky. Laundry lines and a "
    "few salvaged planters say someone has claimed the view.")
put(roof[(-10, -19)],
    "The south lip of the roof deck, over Braddock Avenue and facing "
    "the long roofscape toward the crater wall. The obvious place a "
    "future span would leave from — for now, just the parapet and the "
    "wind and a very long look down.")

print(f"BUILD 009: {made_rooms} rooms, {made_exits} exits, {written} "
      f"descs; elevator now tops at "
      f"{[l for _,l in car.db.floors][-1]}, roof deck at 16.")
