"""Build 005 — the Brackett rise, Phase A (owner-designed, collab test).

    evennia shell < scripts/builds/005_brackett_rise.py
    then foreground reload.

Owner rulings (2026-08-06): full-footprint extension including the
fire escape; floors inhabited; elevator serves through 11; letters
continue; the cargo spine (Phase B) gets its own vertical run; phase
order A then B with a walk between.

Phase A scope:
  z6  — the wings enclose. North row becomes railroad flats off the
        stairwell (6E-6F-6G). South row CANNOT take lettered units
        without breaking the security law (no public circulation
        touches it), so the suites extend instead: the 6A Terrace
        encloses as 6A's Loggia, South Wing Roof West becomes Unit
        6C's Back Room, South Wing Roof East becomes Unit 6B's Store
        Room. FLAGGED for the owner's walk as the one taste deviation.
  z7  — the roof crown rebuilds as Floor 7 (full template) plus the
        six perimeter cells the crown never had.
  z8-11 — four new full floors cloned from floor 5's REAL rooms and
        exit graph (names, types, wiring — extracted, not guessed).
  Iron — fire escape landings 7-11, window per floor landing, ladders
        both ways; the z7 air cell is consumed with inbound repoints.

Converted rooms get their descs/senses CLEARED (roof prose on
interior rooms would lie); the prose pass follows the walk.
"""
from evennia import create_object
from evennia.objects.models import ObjectDB

EXIT_TC = "typeclasses.exits.Exit"
ROOM_TC = "typeclasses.rooms.Room"
B = "The Brackett Arms"


def by_key(key):
    r = ObjectDB.objects.filter(db_key=key).first()
    assert r, f"missing: {key}"
    return r


def room_at(x, y, z):
    for r in ObjectDB.objects.filter(db_attributes__db_key="xyz"):
        if r.attributes.get("xyz") == (x, y, z):
            return r
    return None


def has_exit(room, name):
    return any(e.key == name for e in room.exits)


def mk_exit(loc, dest, key, aliases=None):
    if has_exit(loc, key):
        return 0
    create_object(EXIT_TC, key=key, aliases=aliases or [], location=loc,
                  destination=dest)
    return 1


made_rooms = conv_rooms = made_exits = killed_exits = repointed = 0

# ---- 1. extract floor 5 as the living template -----------------------
FLOOR5 = {}
for r in ObjectDB.objects.filter(db_key__contains=B):
    xyz = r.attributes.get("xyz")
    if xyz and xyz[2] == 5 and -11 <= xyz[0] <= -9 and -20 <= xyz[1] <= -16:
        FLOOR5[(xyz[0], xyz[1])] = r
assert len(FLOOR5) == 15, f"floor-5 template incomplete: {len(FLOOR5)}"
T_KEY = {pos: r.key for pos, r in FLOOR5.items()}
T_TYPE = {pos: r.attributes.get("type") for pos, r in FLOOR5.items()}
T_EXITS = []          # (from_pos, key, aliases, to_pos) intra-floor only
pos_of = {r.id: pos for pos, r in FLOOR5.items()}
for pos, r in FLOOR5.items():
    for e in r.exits:
        d = e.destination
        if d and d.id in pos_of:
            T_EXITS.append((pos, e.key, list(e.aliases.all()), pos_of[d.id]))


def floor_key(template_key, n):
    return template_key.replace("5", str(n))


def strip_surface(room):
    """Roof -> interior: clear surface attrs, prose, and outdoor wiring."""
    global killed_exits
    room.attributes.remove("desc") if room.attributes.has("desc") else None
    room.attributes.remove("sense_descs") if room.attributes.has("sense_descs") else None
    room.db.outside = False
    if room.attributes.has("is_ground"):
        room.attributes.remove("is_ground")
    for e in list(room.exits):
        e.delete()
        killed_exits += 1


# ---- 2. z6: the wings enclose ----------------------------------------
Z6 = {
    (-11, -16): ("North Wing Roof West", f"{B} - Unit 6E"),
    (-10, -16): ("North Wing Roof", f"{B} - Unit 6F"),
    (-9, -16):  ("North Wing Roof East", f"{B} - Unit 6G"),
    (-11, -20): ("Unit 6A Terrace", f"{B} - Unit 6A (Loggia)"),
    (-10, -20): ("South Wing Roof West", f"{B} - Unit 6C (Back Room)"),
    (-9, -20):  ("South Wing Roof East", f"{B} - Unit 6B (Store Room)"),
}
for pos, (old_suffix, new_key) in Z6.items():
    if ObjectDB.objects.filter(db_key=new_key).first():
        continue                       # re-run safe: already converted
    r = by_key(f"{B} - {old_suffix}")
    strip_surface(r)
    r.key = new_key
    r.db.type = None
    conv_rooms += 1
# north row: railroad flats off the stairwell
st6 = by_key(f"{B} - Stairwell (Floor 6)")
u6e, u6f, u6g = (by_key(f"{B} - Unit 6{c}") for c in "EFG")
made_exits += mk_exit(st6, u6e, "east", ["e"]) + mk_exit(u6e, st6, "west", ["w"])
made_exits += mk_exit(u6e, u6f, "east", ["e"]) + mk_exit(u6f, u6e, "west", ["w"])
made_exits += mk_exit(u6f, u6g, "east", ["e"]) + mk_exit(u6g, u6f, "west", ["w"])
# south row: suite extensions
made_exits += mk_exit(by_key(f"{B} - Unit 6A (Bedroom)"),
                      by_key(f"{B} - Unit 6A (Loggia)"), "south", ["s"])
made_exits += mk_exit(by_key(f"{B} - Unit 6A (Loggia)"),
                      by_key(f"{B} - Unit 6A (Bedroom)"), "north", ["n"])
made_exits += mk_exit(by_key(f"{B} - Unit 6C"),
                      by_key(f"{B} - Unit 6C (Back Room)"), "south", ["s"])
made_exits += mk_exit(by_key(f"{B} - Unit 6C (Back Room)"),
                      by_key(f"{B} - Unit 6C"), "north", ["n"])
made_exits += mk_exit(by_key(f"{B} - Unit 6B (Bedroom)"),
                      by_key(f"{B} - Unit 6B (Store Room)"), "south", ["s"])
made_exits += mk_exit(by_key(f"{B} - Unit 6B (Store Room)"),
                      by_key(f"{B} - Unit 6B (Bedroom)"), "north", ["n"])

# ---- 3. z7..z11: the rise --------------------------------------------
CONVERT_Z7 = {
    (-11, -19): "Southwest Roof", (-10, -19): "South Roof",
    (-9, -19): "Southeast Roof", (-11, -18): "West Roof",
    (-10, -18): "Roof Deck", (-9, -18): "East Roof",
    (-11, -17): "Northwest Roof", (-10, -17): "North Roof",
}
floors = {}
for n in (7, 8, 9, 10, 11):
    rooms = {}
    for pos in FLOOR5:
        x, y = pos
        key_n = floor_key(T_KEY[pos], n)
        existing = ObjectDB.objects.filter(db_key=key_n).first()
        if existing:
            rooms[pos] = existing
            continue
        if n == 7 and pos in CONVERT_Z7:
            r = by_key(f"{B} - {CONVERT_Z7[pos]}")
            # keep the Roof Deck's elevator link; strip everything else
            saved = [e for e in r.exits if e.key == "elevator"]
            for e in list(r.exits):
                if e not in saved:
                    e.delete(); globals()['killed_exits'] += 1
            if r.attributes.has("desc"): r.attributes.remove("desc")
            if r.attributes.has("sense_descs"): r.attributes.remove("sense_descs")
            r.db.outside = False
            if r.attributes.has("is_ground"): r.attributes.remove("is_ground")
            r.key = key_n
            r.db.type = T_TYPE[pos]
            conv_rooms += 1
        else:
            old_air = room_at(x, y, n)
            if old_air is not None and old_air.attributes.get("is_sky_room"):
                for ex in ObjectDB.objects.filter(db_destination=old_air):
                    ex.delete(); globals()['killed_exits'] += 1
                old_air.delete()
            r = create_object(ROOM_TC, key=key_n)
            r.db.xyz = (x, y, n)
            r.db.type = T_TYPE[pos]
            r.db.outside = False
            made_rooms += 1
        rooms[pos] = r
    # intra-floor wiring from the extracted graph
    for f_pos, ekey, aliases, t_pos in T_EXITS:
        made_exits += mk_exit(rooms[f_pos], rooms[t_pos], ekey, aliases)
    floors[n] = rooms

# stairwell chain 6..11 (6->7 may already exist via the old roof stair)
prev = by_key(f"{B} - Stairwell (Floor 6)")
for n in (7, 8, 9, 10, 11):
    cur = floors[n][(-11, -17)]
    made_exits += mk_exit(prev, cur, "up", ["u"]) + mk_exit(cur, prev, "down", ["d"])
    prev = cur

# ---- 4. the iron extends ---------------------------------------------
FLOORNAME = {7: "Seventh", 8: "Eighth", 9: "Ninth", 10: "Tenth", 11: "Eleventh"}
prev_landing = by_key(f"{B} - Fire Escape (Sixth Floor)")
for n in (7, 8, 9, 10, 11):
    key = f"{B} - Fire Escape ({FLOORNAME[n]} Floor)"
    landing = ObjectDB.objects.filter(db_key=key).first()
    if not landing:
        old_air = room_at(-8, -18, n)
        landing = create_object(ROOM_TC, key=key)
        landing.db.xyz = (-8, -18, n)
        landing.db.type = "fire escape"
        landing.db.outside = True
        landing.db.is_ground = True
        landing.db.is_sky_room = False
        made_rooms += 1
        if old_air is not None and old_air.attributes.get("is_sky_room"):
            for ex in ObjectDB.objects.filter(db_destination=old_air):
                ex.destination = landing
                ex.save()
                repointed += 1
            old_air.delete()
    made_exits += mk_exit(prev_landing, landing, "up", ["u"])
    made_exits += mk_exit(landing, prev_landing, "down", ["d"])
    made_exits += mk_exit(floors[n][(-10, -18)], landing, "window")
    prev_landing = landing

print(f"BUILD 005A: {made_rooms} new rooms, {conv_rooms} converted, "
      f"{made_exits} exits made, {killed_exits} removed, {repointed} repointed.")
print("Converted rooms have CLEARED descs (prose follows the walk).")
print("FLAGGED: z6 south row = suite extensions, not lettered units "
      "(security law — no public circulation touches that row).")
