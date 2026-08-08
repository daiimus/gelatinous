"""Build 010 — the upper tower gets doors and leases (audit fix).

    evennia shell < scripts/builds/010_brackett_upper_leases.py
    then foreground reload (idmapper — data build).

The audit found the whole tower above floor 6 doorless and unrentable:
floors 7-15 units were built structurally but never given the DoorExit
lease pattern the lower floors have (plain open exits, no locks, not on
the kiosk). Owner: wire it all.

This build:
  1. Converts the two dead-end halls on floors 12-15 into units E (north
     face, ex-North Hall) and F (south face, ex-South Hall) — filling
     the empty walls the narrowing left, six units a floor in the 3x3.
  2. Gives EVERY unit on floors 7-15 a proper spring-latch DoorExit pair
     (hall-side keyed by unit number, autolocking), cloned from the
     floor-5 lease door, fixing the stray 11A-style keys on 12-15 as a
     side effect.
  3. Wires cube_door + residence + kiosk entry for all of them.

Result: the Brackett rents top to bottom, ~60 -> ~134 leases.
"""
from evennia import create_object
from evennia.objects.models import ObjectDB

B = "The Brackett Arms"
DOOR_TC = "typeclasses.doors.DoorExit"
ABBR = {"north": "n", "south": "s", "east": "e", "west": "w",
        "northeast": "ne", "northwest": "nw",
        "southeast": "se", "southwest": "sw"}
OPP = {"north": "south", "south": "north", "east": "west", "west": "east",
       "northeast": "southwest", "southwest": "northeast",
       "northwest": "southeast", "southeast": "northwest"}


def d_name(fr, to):
    dy, dx = to[1] - fr[1], to[0] - fr[0]
    ns = "north" if dy > 0 else "south" if dy < 0 else ""
    ew = "east" if dx > 0 else "west" if dx < 0 else ""
    return ns + ew


# ---- exemplar lease door (floor 5 Unit A hall-side) ------------------
landing5 = ObjectDB.objects.filter(db_key=f"{B} - Floor 5 Landing").first()
exemplar = next((e for e in landing5.exits if e.key == "5A"), None)
assert exemplar, "no floor-5 lease-door exemplar"
EX_LOCKS = str(exemplar.locks)
EX_DESC = exemplar.db.desc
DOOR_ATTRS = ("is_door", "door_closed", "door_locked", "door_autolock",
              "door_broken")
EX_ATTRS = {a.key: a.value for a in exemplar.attributes.all()
            if a.key in DOOR_ATTRS}


def make_door(loc, dest, key, twin_key, aliases):
    d = create_object(DOOR_TC, key=key, aliases=aliases, location=loc,
                      destination=dest)
    for k, v in EX_ATTRS.items():
        d.attributes.add(k, v)
    d.db.access_grants = []
    d.db.door_twin = twin_key
    d.db.desc = EX_DESC
    d.locks.add(EX_LOCKS)
    return d


# ---- 1. convert the dead halls to units E / F (floors 12-15) ---------
ORD = {12: "twelfth", 13: "thirteenth", 14: "fourteenth", 15: "fifteenth"}
converted = 0
for n in (12, 13, 14, 15):
    for suffix, letter, face in (
            ("North Hall", "E",
             f"A hab in the narrowed crown, the tower's one north-facing "
             f"apartment over Kaspar Street — the stair and elevator "
             f"cores stand to either side of it. Colonization-era "
             f"fittings and {ORD[n]}-floor light, the north blocks' "
             f"roofscape fallen away beneath the sill."),
            ("South Hall", "F",
             f"A hab on the south face of the crown, over Braddock "
             f"Avenue, set between the two south corners. Fold-down "
             f"berth, galley wall, wet cell — and a long {ORD[n]}-floor "
             f"look south toward the crater wall.")):
        old = ObjectDB.objects.filter(db_key=f"{B} - Floor {n} {suffix}").first()
        if old is None:
            continue                     # re-run safe (already converted)
        old.key = f"{B} - Unit {n}{letter}"
        old.db.type = None
        old.db.desc = face
        if old.attributes.has("sense_descs"):
            old.attributes.remove("sense_descs")
        converted += 1

# ---- 2 & 3. doors + rental for every unit on floors 7-15 -------------
kiosk = ObjectDB.objects.filter(id=5640).first()
assert kiosk, "kiosk #5640 missing"
cubes = list(kiosk.db.cubes or [])
cube_ids = {c.id for c in cubes if c is not None and getattr(c, "pk", None)}

wired = made_doors = 0
for r in ObjectDB.objects.filter(db_key__startswith=f"{B} - Unit "):
    xyz = r.attributes.get("xyz")
    if not (xyz and 7 <= xyz[2] <= 15):
        continue
    upos = (xyz[0], xyz[1])
    # the circulation neighbour + the unit-side exit to it
    egress = next((e for e in r.exits if e.destination is not None and
                   ("Hall" in e.destination.key or
                    "Landing" in e.destination.key)), None)
    if egress is None:
        print("WARN: no circulation exit from", r.key)
        continue
    hall = egress.destination
    hxyz = hall.attributes.get("xyz")
    hpos = (hxyz[0], hxyz[1])
    label = r.key.replace(f"{B} - Unit ", "")
    d_uh = egress.key if egress.key in OPP else d_name(upos, hpos)
    d_hu = OPP[d_uh]
    entrance = next((e for e in hall.exits if e.destination == r), None)

    hall_is_door = entrance is not None and \
        entrance.typeclass_path.endswith("DoorExit")
    unit_is_door = egress.typeclass_path.endswith("DoorExit")
    if not (hall_is_door and unit_is_door):
        if entrance is not None:
            entrance.delete()
        egress.delete()
        hall_side = make_door(hall, r, label, d_uh,
                             ["door", d_hu, ABBR[d_hu]])
        make_door(r, hall, d_uh, label, [ABBR[d_uh]])
        made_doors += 2
    else:
        hall_side = entrance

    r.db.cube_door = hall_side
    r.db.residence_building = B
    r.db.residence_origin = "Bhavani Corridor"
    if r.id not in cube_ids:
        cubes.append(r)
        cube_ids.add(r.id)
    wired += 1

kiosk.db.cubes = cubes
print(f"BUILD 010: {converted} halls->units, {made_doors} door leaves, "
      f"{wired} units wired, kiosk now {len(cubes)} cubes.")
