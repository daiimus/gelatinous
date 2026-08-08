"""Build 011 — the crown: mast, roof gardens, the sealed south terrace.

    evennia shell < scripts/builds/011_brackett_crown.py
    then foreground reload.

Owner-designed:
  * The AWE Sentinel-9 mast (orphaned inside Floor 7's hallway when the
    tower rose) relocates to a climbable industrial antenna rising three
    stories above the roof deck to a platform near rim height. The
    basement head-end cabinet references it by name, so coverage follows
    to the new height — dispatch survives.
  * The roof deck + the north setback shelf become tended communal roof
    GARDENS (solarpunk roof-farming), green on the atlas via atlas_skin.
  * The south setback shelf is EMBRACED as sealed: no ordinary exits, a
    semi-abandoned terrace reachable only by the future air/climb layer,
    with a dead untuned repeater humming to itself as the payoff.
"""
import math

from evennia import create_object
from evennia.objects.models import ObjectDB
from evennia.prototypes.spawner import spawn

from world import prototypes as P

ROOM_TC = "typeclasses.rooms.Room"
EXIT_TC = "typeclasses.exits.Exit"
B = "The Brackett Arms"


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


def room_at(key, xyz, rtype, outside=True, skin=None, ground=True):
    global made_rooms
    r = ObjectDB.objects.filter(db_key=key).first()
    if r is None:
        r = create_object(ROOM_TC, key=key)
        r.db.xyz = xyz
        made_rooms += 1
    r.db.type = rtype
    r.db.outside = outside
    if ground:
        r.db.is_ground = True
    if skin:
        r.db.atlas_skin = skin
    return r

# ---- 1. the mast climb + relocation ----------------------------------
deck = by_key(f"{B} - Roof Deck")                     # (-10,-18,16)
MAST = {17: "The Brackett Arms - Antenna Mast (Lower)",
        18: "The Brackett Arms - Antenna Mast (Upper)",
        19: "The Brackett Arms - Antenna Platform"}
mast_rooms = {}
for z, key in MAST.items():
    mast_rooms[z] = room_at(key, (-10, -18, z), "rooftop", skin="machine")
# ladder chain: deck -> 17 -> 18 -> 19
chain = [deck, mast_rooms[17], mast_rooms[18], mast_rooms[19]]
for lower, upper in zip(chain, chain[1:]):
    made_exits += mk_exit(lower, upper, "up", ["u"])
    made_exits += mk_exit(upper, lower, "down", ["d"])
# relocate the Sentinel to the platform (coverage follows the object)
mast = ObjectDB.objects.filter(id=5641).first()
if mast is not None:
    mast.move_to(mast_rooms[19], quiet=True, move_hooks=False)

mast_rooms[17].db.desc = (
    "The base of the Brackett's antenna mast, bolted to the roof deck: "
    "a caged maintenance ladder climbs the lattice steel into the wind. "
    "The city is already small below the grating.")
mast_rooms[18].db.desc = (
    "Halfway up the mast. The ladder cage rattles; guy-wires sing off "
    "into the dark. Only the crater wall still stands taller than you "
    "from here.")
mast_rooms[19].db.desc = (
    "The antenna platform at the mast's head — the highest walkable "
    "point of the Brackett, near the height of the crater rim itself. "
    "The AWE Sentinel-9 relays from the steel overhead; the whole "
    "colony lies spread and glittering, and the wall is close enough to "
    "read its unbuilt reaches.")
mast_rooms[19].db.sense_descs = {
    "auditory": "Wind, guy-wire hum, and the mast's faint electrical tick.",
    "olfactory": "Cold ozone; nothing of the streets reaches up here.",
    "tactile": "The platform trembles in the gusts; the rail is the only "
               "argument against a very long fall.",
    "atmospheric": "The roof of the tower's world. The rim, and whatever "
                   "waits on it, has never looked so reachable."}

# ---- 2. the north communal garden ------------------------------------
north = room_at(f"{B} - Roof Garden (North)", (-11, -16, 12),
                "rooftop", skin="garden")
north.db.desc = (
    "The north roof garden, stepped out onto the old wing's roof where "
    "the tower narrows: raised beds of greens and climbing beans on a "
    "tarred deck, a water butt fed off the aquaponics line, and Kaspar "
    "Street's roofscape running off below the parapet. The building's "
    "tenants keep it; the smell of green is a shock this high up.")
north.db.sense_descs = {
    "auditory": "Bees at the beans, wind in the trellis, the city a "
                "rumor below.",
    "olfactory": "Wet soil and tomato leaf — impossibly green up here.",
    "tactile": "Warm bed-frames, cool wind; grit and potting mix "
               "underfoot.",
    "atmospheric": "The colony's roof-farming habit, made a garden — "
                   "communal, tended, and rented-into like everything "
                   "else in the Brackett."}
st12 = by_key(f"{B} - Stairwell (Floor 12)")
made_exits += mk_exit(st12, north, "north", ["n"])
made_exits += mk_exit(north, st12, "south", ["s"])

# ---- 3. the sealed south terrace + untuned repeater ------------------
south = room_at(f"{B} - Roof Garden (South, Derelict)", (-11, -20, 12),
                "rooftop", skin="garden")
south.db.desc = (
    "What was once the south wing's roof garden, gone to seed: beds "
    "burst with volunteer growth and dead stalks, a collapsed trellis, "
    "planters cracked by frost. No stair reaches here and no ladder is "
    "let down — the only ways up are the ones you bring or improvise. In "
    "the middle of the ruin a squat repeater hums to itself, tuned to "
    "nothing, patient.")
south.db.sense_descs = {
    "auditory": "The repeater's dead carrier hum, and wind through "
                "rank growth. Nothing human.",
    "olfactory": "Rot and green and cold metal.",
    "tactile": "Everything up here is either overgrown or coming apart.",
    "atmospheric": "Sealed and forgotten — a rooftop the building turned "
                   "its back on, waiting for whoever can reach it."}
# NO exits by design (owner: air/climb only, future)

# the untuned repeater: a dormant node, a future decking prize
if not any(o.key for o in south.contents if "repeater" in o.key.lower()):
    try:
        made = spawn(P.REPEATER_MAST)
        rep = made[0]
        rep.move_to(south, quiet=True, move_hooks=False)
        rep.db.frequency = "000.0MHz"
        rep.db.is_base_station = False
        rep.db.integrate = True
        rep.db.integration_desc = (
            "A squat |cderelict repeater|n hunches among the dead beds, "
            "power light amber, |ctuned to nothing|n — it hums a dead "
            "carrier and relays not one word.")
    except Exception as exc:  # noqa: BLE001
        print("REPEATER spawn failed:", exc)

# ---- 4. the roof deck becomes the communal farm ----------------------
by_key(f"{B} - Roof Deck").db.atlas_skin = "garden"
by_key(f"{B} - Roof Deck (North)").db.atlas_skin = "garden"
by_key(f"{B} - Roof Deck (South)").db.atlas_skin = "garden"
by_key(f"{B} - Roof Deck").db.desc = (
    "The heart of the roof deck, given over to the tenants' rooftop "
    "farm: raised grow-beds and cane rows on the plated tar, water "
    "reclaimed off the aquaponics line, the stairwell bulkhead and the "
    "foot of the antenna mast the only hard structures. Laundry lines "
    "run between the beans; the whole colony farms its roofs, and this "
    "is the Brackett's plot.")

print(f"BUILD 011: {made_rooms} rooms, {made_exits} exits; mast relocated "
      f"to {mast.location.key if mast else '??'}; south terrace sealed.")
