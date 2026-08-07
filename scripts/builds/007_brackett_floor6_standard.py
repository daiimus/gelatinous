"""Build 007 — floor 6 standardizes (owner ruling 2026-08-07).

    evennia shell < scripts/builds/007_brackett_floor6_standard.py
    then foreground reload (idmapper — the atlas lesson).

The penthouse experiment ends. Floor 6 becomes the template floor:
the old suites dissolve into single habs, the center column returns
to circulation (North Hall / Landing / South Hall), the wing rooms
door off halls like every other floor, and the stairwell keeps its
one standard doorway. The premium-suite idea moves to Phase B's
leaning tier, where irregular rooms are native. Also fixes the
Build-005A defect where cloned door exits on floors 7-11 kept their
floor-5 keys (a floor-9 tenant would have typed 5E).

Verified before running: all four floor-6 leases vacant, no contents.
"""
import re

from evennia import create_object
from evennia.objects.models import ObjectDB

B = "The Brackett Arms"


def by_key(key):
    r = ObjectDB.objects.filter(db_key=key).first()
    assert r, f"missing: {key}"
    return r


# ---- 1. the floor-5 template, captured whole -------------------------
FLOOR5 = {}
for r in ObjectDB.objects.filter(db_key__contains=B):
    xyz = r.attributes.get("xyz")
    if xyz and xyz[2] == 5 and -11 <= xyz[0] <= -9 and -20 <= xyz[1] <= -16:
        FLOOR5[(xyz[0], xyz[1])] = r
assert len(FLOOR5) == 15, f"floor-5 template incomplete: {len(FLOOR5)}"
pos_of = {r.id: pos for pos, r in FLOOR5.items()}


def renumber(text, n):
    """5A -> {n}A wherever a floor-5 unit token appears."""
    return re.sub(r"5([A-J])\b", lambda m: f"{n}{m.group(1)}", text or "")


# ---- 2. renames: the suites dissolve ---------------------------------
RENAMES = [  # ordered so no step collides with a name still in use
    ("Unit 6C", "Floor 6 South Hall"),
    ("Unit 6D", "Floor 6 North Hall"),
    ("Floor 6 Hall", "Floor 6 Landing"),
    ("Unit 6A (Parlor)", "Unit 6A"),
    ("Unit 6B (Parlor)", "Unit 6B"),
    ("Unit 6A (Bedroom)", "Unit 6C"),
    ("Unit 6B (Bedroom)", "Unit 6D"),
    ("Unit 6A (Loggia)", "Unit 6H"),
    ("Unit 6C (Back Room)", "Unit 6I"),
    ("Unit 6B (Store Room)", "Unit 6J"),
]
renamed = 0
for old, new in RENAMES:
    r = ObjectDB.objects.filter(db_key=f"{B} - {old}").first()
    if r is None:
        continue                       # re-run safe
    r.key = f"{B} - {new}"
    renamed += 1

FLOOR6 = {}
for pos, r5 in FLOOR5.items():
    key6 = r5.key.replace("5", "6")
    FLOOR6[pos] = by_key(key6)
ids6 = {r.id for r in FLOOR6.values()}

# types match the template; the terrace-suite mark comes off
for pos, r in FLOOR6.items():
    r.db.type = FLOOR5[pos].attributes.get("type")

# ---- 3. the exit graph rebuilds from the template --------------------
killed = 0
for r in FLOOR6.values():
    for e in list(r.exits):
        if e.destination is not None and e.destination.id in ids6:
            e.delete()
            killed += 1

made = 0
for pos, r5 in FLOOR5.items():
    for e in r5.exits:
        d = e.destination
        if d is None or d.id not in pos_of:
            continue                   # window/elevator/stairs: floor 6 has its own
        loc, dest = FLOOR6[pos], FLOOR6[pos_of[d.id]]
        key = renumber(e.key, 6)
        if any(x.key == key for x in loc.exits):
            continue                   # re-run safe
        new = create_object(e.typeclass_path, key=key,
                            aliases=[renumber(a, 6) for a in e.aliases.all()],
                            location=loc, destination=dest)
        for a in e.attributes.all():
            val = a.value
            if isinstance(val, str):
                val = renumber(val, 6)
            new.attributes.add(a.key, val)
        new.locks.add(str(e.locks))
        made += 1

# ---- 4. rental wiring: ten leases, like floors 1-5 -------------------
wired = 0
for pos, r in FLOOR6.items():
    r5 = FLOOR5[pos]
    if r5.attributes.get("cube_door") is None:
        continue                       # not a unit cell
    hall6 = None
    for hall in FLOOR6.values():
        for e in hall.exits:
            if e.destination == r and e.key.startswith("6"):
                hall6 = e
    assert hall6, f"no lease door found for {r.key}"
    r.db.cube_door = hall6
    r.db.residence_building = B
    r.db.residence_origin = "Bhavani Corridor"
    wired += 1

kiosk = ObjectDB.objects.filter(id=5640).first()
assert kiosk, "kiosk #5640 missing"
cubes = list(kiosk.db.cubes or [])
cubes = [c for c in cubes
         if c is not None and getattr(c, "pk", None)
         and c.id not in ids6]         # drop stale floor-6 entries (halls now)
for pos, r in FLOOR6.items():
    if r.attributes.get("cube_door") is not None:
        cubes.append(r)
kiosk.db.cubes = cubes

# ---- 5. prose: the seam floor ----------------------------------------
FACADE = {
    -11: "The window faces west over Bhavani Corridor",
    -9: "The window faces east across the fire escape's iron toward the "
        "Boot's dead hull",
}
WING = {
    -16: "set over Kaspar Street where the wing roof used to be, the old "
         "tar line still ghosting the floor at the plate seam",
    -20: "set over Braddock Avenue on the enclosed south wing, a strip "
         "of weathered terrace tile surviving under the window",
}
LETTER_POS = {"A": (-11, -18), "B": (-9, -18), "C": (-11, -19),
              "D": (-9, -19), "E": (-11, -16), "F": (-10, -16),
              "G": (-9, -16), "H": (-11, -20), "I": (-10, -20),
              "J": (-9, -20)}
BODY = ("A single-room hab in the colonization-era standard: fold-down "
        "berth, galley wall, a wet cell behind a concertina door. Floor "
        "six is the top of the old pour — the ceiling here carries the "
        "rebuild's whole weight, and does it quietly.")


def unit_desc(letter, x, y):
    if y in WING:
        return f"A wing unit {WING[y]}. {BODY}"
    return f"{BODY} {FACADE.get(x, 'The window faces the shaftway')}."


prose = 0
DESCS = {
    "Floor 6 Landing": (
        "The floor-6 landing: the elevator's brushed-steel doors, the "
        "stencil of the floor number in the colonization-era typeface — "
        "the last floor that got one — and the halls running north and "
        "south. Above this the tower is younger and louder about it.",
        {"auditory": "Cable-song in the shaft; the stair door swings on "
                     "its original hinges.",
         "olfactory": "Cooking oil and old varnish — the fifth floor's "
                      "smell, one flight later.",
         "tactile": "The tile here has the old floors' gentle sag "
                    "underfoot.",
         "atmospheric": "The seam floor: everything below is settled, "
                        "everything above is still deciding."}),
    "Floor 6 North Hall": (
        "The north hall on floor six, running onto the Kaspar "
        "cantilever: plated decking, unit doors in the original prefab "
        "panels, and at the far end the wing rooms the enclosure added "
        "when the tower rose.", None),
    "Floor 6 South Hall": (
        "The south hall on floor six, over Braddock Avenue: quieter "
        "than the north face, the ceiling carrying the rebuild's load "
        "without comment. Unit doors run the row.", None),
    "Stairwell (Floor 6)": (
        "Ferrocrete and caged light at floor six, the climb metered in "
        "stenciled numerals — the last flight in the original pour "
        "before the treads turn to welded plate above.", None),
    "Elevator Shaft (Floor 6)": (
        "The shaft at floor six: counterweight grease, cable in the "
        "dark, the car's light passing like weather.", None),
}
for suffix, (desc, senses) in DESCS.items():
    r = by_key(f"{B} - {suffix}")
    r.db.desc = desc
    if senses:
        r.db.sense_descs = senses
    else:
        r.attributes.remove("sense_descs") if r.attributes.has("sense_descs") else None
    prose += 1
for letter, (x, y) in LETTER_POS.items():
    r = by_key(f"{B} - Unit 6{letter}")
    r.db.desc = unit_desc(letter, x, y)
    r.attributes.remove("sense_descs") if r.attributes.has("sense_descs") else None
    prose += 1

# ---- 6. floors 7-11: door keys renumber (the 005A defect) ------------
rekeyed = 0
for n in (7, 8, 9, 10, 11):
    for r in ObjectDB.objects.filter(db_key__contains=B):
        xyz = r.attributes.get("xyz")
        if not (xyz and xyz[2] == n and -11 <= xyz[0] <= -9
                and -20 <= xyz[1] <= -16):
            continue
        for e in r.exits:
            fixed = renumber(e.key, n)
            if fixed != e.key:
                e.key = fixed
                rekeyed += 1

print(f"BUILD 007: {renamed} renamed, {killed} exits removed, {made} "
      f"rebuilt, {wired} leases wired, kiosk now {len(cubes)} cubes, "
      f"{prose} descs, {rekeyed} door keys renumbered on 7-11.")
