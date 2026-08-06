"""Build 003 — the Brackett fire escape (rough draft, owner-designed).

    evennia shell < scripts/builds/003_brackett_fire_escape.py
    then foreground reload.

The design (owner, 2026-08-05):
  - Code-era iron serves floors 3-5; the 6th-floor conversion crowd,
    told to fend for themselves, bolted on their own landing.
  - A window on each floor — purposefully vague — leads OUT to its
    landing (one-way; climbing in is a future hidden-exit mechanic).
    Every floor exits from its COMMUNAL landing/hall — the window at
    the end of the landing (owner ruling: private-unit windows are
    invisible inside locked rentals). Key "window", no aliases.
  - The iron itself works both ways, z3 through z6.
  - The bottom is a one-way drop onto Hammett's Boot - Shin Plate.
  - East Roof's edge into the column now falls ONE story onto the
    bolt-on landing instead of seven to the Heel.
  - Landings replace four air cells at (-8,-18) z3..z6; every exit
    that pointed at those air cells (including falls from above) is
    repointed to the landings, so the column still resolves.

Prose pass applied 2026-08-06 (owner go): descs + sense layers
ship with the landings on creation; re-runs never stomp live edits.
"""
from evennia import create_object
from evennia.objects.models import ObjectDB

EXIT_TC = "typeclasses.exits.Exit"
ROOM_TC = "typeclasses.rooms.Room"
COL_X, COL_Y = -8, -18


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


shin = by_key("Hammett's Boot - Shin Plate")
# windows are COMMUNAL on every floor (owner ruling after live test:
# unit-hosted windows are invisible inside locked rentals): each
# floor's landing/hall gets the window, key "window", NO aliases.
hosts = {
    3: by_key("The Brackett Arms - Floor 3 Landing"),
    4: by_key("The Brackett Arms - Floor 4 Landing"),
    5: by_key("The Brackett Arms - Floor 5 Landing"),
    6: by_key("The Brackett Arms - Floor 6 Hall"),
}
FLOOR = {3: "Third", 4: "Fourth", 5: "Fifth", 6: "Sixth"}

DESCS = {
    3: ("The bottom of the old iron: a grated landing bolted to the "
        "tenement's east wall, paint gone to scale, rivets bleeding rust "
        "down the brick. The counterweighted ladder hangs below the floor "
        "hatch, chained short so it stops above the Boot's shin — close "
        "enough to drop, too far to climb back. Someone has scratched "
        "tally marks into the rail, dozens of them, meaning unknown.",
        {"auditory": "The Boot's hull ticks with temperature below; the "
                     "whole run of iron telegraphs any footstep above.",
         "olfactory": "Rust, chain grease, and the dead-ship smell rising "
                      "off the hull beneath — cold metal and old bilge.",
         "tactile": "The grating gives a half-inch under weight, spring "
                    "and complaint; the chain runs greasy through its eye.",
         "atmospheric": "Everything below this landing is one-way — the "
                        "iron ends here, and the ship begins."}),
    4: ("A landing like a held breath between ladders — four bolts, a "
        "rail, and the long view of brick running both directions. The "
        "fourth-floor window is painted into its frame except for the one "
        "pane that isn't. Cigarette ends collect where the grating meets "
        "the wall, all of them the same brand.",
        {"auditory": "Ladder rungs ring above and below at the smallest "
                     "shift — nobody arrives here unannounced.",
         "olfactory": "Stale smoke has soaked into the brick; rain never "
                      "quite rinses this corner.",
         "tactile": "The rail wobbles a knuckle's width where one anchor "
                    "has pulled from the mortar.",
         "atmospheric": "A between-place — the kind of spot the "
                        "building's stories pass through and never stop."}),
    5: ("The top of the code-era run, where the original iron ends in a "
        "squared-off rail and the view opens: the toe quarter laid out "
        "roof by roof, the Boot's hull below, the arcade lights of Kaspar "
        "Street, the crater rim beyond all of it. The fifth-floor window "
        "sits at chest height, its sill worn smooth by decades of "
        "climbing through. Above, newer iron continues — different welds, "
        "different mind.",
        {"auditory": "Wind first — everything else arrives underneath it, "
                     "thinned by five stories.",
         "olfactory": "Clean height: dust and processor ozone, the "
                      "street's grease burned off by distance.",
         "tactile": "The updraft finds every seam in your clothes; the "
                    "rail runs cold even in heat.",
         "atmospheric": "The highest place boots alone can reach — "
                        "everything above wants rope, or nerve."}),
    6: ("The bolt-on: salvage iron in three different greens, welded by "
        "someone who cared about holding, not looks. It hangs off the "
        "building a full story above the old escape's end, a scavenged "
        "ladder lashed across the gap to the code-era run below. The hall "
        "window behind it has a blanket for a curtain and a jar of "
        "cigarette ends on the sill. The roofline waits one story up — "
        "close enough to hear, too far to touch.",
        {"auditory": "Sixth-floor life bleeds through the window — a "
                     "radio, a cough, a kettle: the floor that officially "
                     "isn't.",
         "olfactory": "Weld scale and fresh rust — this iron is decades "
                      "younger than the run it hangs from.",
         "tactile": "The bolt-on flexes more than the old iron: a longer "
                    "sway, a newer fear.",
         "atmospheric": "Built by the people it serves, and it feels like "
                        "it — half fire escape, half statement."}),
}

landings = {}
made_rooms = made_exits = repointed = 0
for z in (3, 4, 5, 6):
    name = f"The Brackett Arms - Fire Escape ({FLOOR[z]} Floor)"
    existing = ObjectDB.objects.filter(db_key=name).first()
    if existing:
        landings[z] = existing
        continue
    air = room_at(COL_X, COL_Y, z)
    assert air and air.attributes.get("is_sky_room"), \
        f"expected air cell at ({COL_X},{COL_Y},{z})"
    landing = create_object(ROOM_TC, key=name)
    landing.db.xyz = (COL_X, COL_Y, z)
    landing.db.type = "fire escape"
    landing.db.outside = True
    landing.db.is_ground = True
    landing.db.is_sky_room = False
    desc, senses = DESCS[z]
    landing.db.desc = desc
    landing.db.sense_descs = senses
    made_rooms += 1
    # every exit that pointed at the air cell now points at the iron —
    # including falls from the air above, which land on the escape
    for ex in ObjectDB.objects.filter(db_destination=air):
        ex.destination = landing
        ex.save()
        repointed += 1
    air.delete()
    landings[z] = landing

# the windows: one-way out, purposefully vague
for z, host in hosts.items():
    if not has_exit(host, "window"):
        create_object(EXIT_TC, key="window",
                      location=host, destination=landings[z])
        made_exits += 1

# the iron works both ways, z3..z6
for lo, hi in ((3, 4), (4, 5), (5, 6)):
    if not has_exit(landings[lo], "up"):
        create_object(EXIT_TC, key="up", aliases=["u"],
                      location=landings[lo], destination=landings[hi])
        made_exits += 1
    if not has_exit(landings[hi], "down"):
        create_object(EXIT_TC, key="down", aliases=["d"],
                      location=landings[hi], destination=landings[lo])
        made_exits += 1

# the bottom: one-way drop onto the Boot's shin
if not has_exit(landings[3], "drop"):
    create_object(EXIT_TC, key="drop", aliases=["down", "d"],
                  location=landings[3], destination=shin)
    made_exits += 1

# East Roof's edge now falls one story onto the bolt-on landing
# (the z7 roofs use the older style: a plain walk into the air cell,
# with the air column's own down-chain doing the falling — which the
# repointing above already lands on the bolt-on. Make it explicit.)
east_roof = by_key("The Brackett Arms - East Roof")
edge_fixed = False
for ex in east_roof.exits:
    dest = ex.destination
    if dest and dest.attributes.get("xyz") == (COL_X, COL_Y, 7):
        ex.db.is_edge = True
        ex.db.edge_difficulty = 8
        ex.db.sky_room = dest.id      # REQUIRED: without it the jump
        ex.db.fall_room = landings[6].id   # degrades to a plain walk
        ex.db.fall_distance = 1
        ex.db.fall_damage = 5
        edge_fixed = True
assert edge_fixed, "East Roof exit into the column not found — inspect by hand"

print(f"BUILD 003 complete: {made_rooms} landings, {made_exits} exits, "
      f"{repointed} exits repointed onto the iron, roof edge softened.")
