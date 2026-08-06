"""Build 006 — the Brackett rise fit-out (owner walk findings).

    evennia shell < scripts/builds/006_brackett_rise_fitout.py
    then foreground reload.

Findings addressed:
  1. Call buttons: floors 7-11 landings get ElevatorCallButton objects
     cloned from the floor-5 exemplar (stops and doors existed; the
     summons did not).
  2. Prose: every new/converted room receives its description in the
     building's own register (colonization-era standard below, the
     fortified rebuild above — newer steel on old bones), plus sense
     layers on the communal rooms.
The z6 south row remains suite rooms BY the flagged design.
"""
from evennia import create_object
from evennia.objects.models import ObjectDB

B = "The Brackett Arms"


def by_key(key):
    r = ObjectDB.objects.filter(db_key=key).first()
    assert r, f"missing: {key}"
    return r


# ---- 1. the call buttons ---------------------------------------------
exemplar = None
for o in by_key(f"{B} - Floor 5 Landing").contents:
    if o.key == "call button":
        exemplar = o
assert exemplar, "no call-button exemplar on floor 5"
btn_tc = exemplar.typeclass_path
made_buttons = 0
for n in (7, 8, 9, 10, 11):
    land = by_key(f"{B} - Floor {n} Landing")
    if any(o.key == "call button" for o in land.contents):
        continue
    btn = create_object(btn_tc, key="call button", location=land)
    for a in exemplar.attributes.all():
        if a.key != "desc":
            btn.attributes.add(a.key, a.value)
    btn.db.desc = exemplar.db.desc
    made_buttons += 1

# ---- 2. the prose ----------------------------------------------------
ORD = {6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven"}
REBUILD_NOTES = {
    7: "At the ceiling joint the old tower ends and the rebuild begins — "
       "two pours of ferrocrete that never quite agreed.",
    8: "The rebuild's plating shows its salvage: no two wall panels from "
       "the same donor, all of them holding.",
    9: "Halfway up the graft. The bolts here are torqued to a standard "
       "the lower floors never saw.",
    10: "The corridor lights run off the rebuild's own circuit and burn "
        "a shade whiter than the tower below.",
    11: "Top of the official tower. Above this the paint stops, and the "
        "colony's permission stops with it.",
}
FACADE = {
    -11: "The window faces west over Bhavani Corridor",
    -9: "The window faces east across the fire escape's iron toward the "
        "Boot's dead hull",
}
WING = {
    -16: "hung out over Kaspar Street on the cantilever trusses, nothing "
         "under the floor plates but air and the street",
    -20: "riding the south face over Braddock Avenue, the ceiling "
         "carrying the faint load-groan of whatever the tower holds up "
         "there",
}
UNIT_BODIES = [
    "A single-room hab in the rebuild standard: fold-down berth, galley "
    "wall, a wet cell behind a concertina door, the fixtures "
    "salvage-grade but square.",
    "A one-room hab on the rebuilt floors — berth, galley wall, wet "
    "cell — the colonization-era layout copied in newer, rougher "
    "materials.",
    "A standard hab whose bones are the old tower's and whose skin is "
    "the rebuild's: plated walls, a re-tapped vent line, everything "
    "holding by intent rather than habit.",
]


def unit_desc(n, letter, x, y):
    body = UNIT_BODIES[(n + ord(letter)) % len(UNIT_BODIES)]
    if y in WING:
        return (f"A wing unit {WING[y]}. " + body)
    facade = FACADE.get(x, "The window faces the shaftway's grey light")
    return f"{body} {facade}, {ORD[n]} storeys up."


def put(key, desc, senses=None):
    r = ObjectDB.objects.filter(db_key=key).first()
    if not r:
        return 0
    if not r.db.desc:
        r.db.desc = desc
        if senses:
            r.db.sense_descs = senses
        return 1
    return 0


written = 0
LETTER_POS = {"A": (-11, -18), "B": (-9, -18), "C": (-11, -19),
              "D": (-9, -19), "E": (-11, -16), "F": (-10, -16),
              "G": (-9, -16), "H": (-11, -20), "I": (-10, -20),
              "J": (-9, -20)}
for n in (7, 8, 9, 10, 11):
    written += put(
        f"{B} - Floor {n} Landing",
        f"The floor-{n} landing: elevator doors in newer steel than the "
        f"frame around them, the floor number hand-stenciled where the "
        f"colonization-era typeface ran out, halls running north and "
        f"south into the rebuild's straighter lines. {REBUILD_NOTES[n]}",
        {"auditory": "Cable-song in the shaft; the car passing is the "
                     "floor's own weather.",
         "olfactory": "Cooking oil and cut-metal solvent, the rebuild's "
                      "perfume.",
         "tactile": "The new tile is dead level — your boots notice "
                    "after the old floors' sag.",
         "atmospheric": "The graft holds. Everyone who lives here has "
                        "decided to believe that."})
    written += put(
        f"{B} - Floor {n} North Hall",
        f"The north hall on floor {n}, running onto the Kaspar "
        f"cantilever: plated decking with {ORD[n]} storeys of air below, "
        f"unit doors in salvage-matched panels, no two hinges alike.")
    written += put(
        f"{B} - Floor {n} South Hall",
        f"The south hall on floor {n}, over Braddock Avenue. The rebuild "
        f"runs quieter on this face — heavier plate, fewer windows, and "
        f"overhead the first hints of the damaged tier's mass.")
    written += put(
        f"{B} - Stairwell (Floor {n})",
        f"The fire stairs at floor {n}: ferrocrete giving way to "
        f"welded-plate treads, the climb metered in two generations of "
        f"stenciled numbering.")
    written += put(
        f"{B} - Elevator Shaft (Floor {n})",
        f"The shaft at floor {n}: counterweight grease, cable in the "
        f"dark, the car's light passing like weather.")
    for letter, (x, y) in LETTER_POS.items():
        written += put(f"{B} - Unit {n}{letter}", unit_desc(n, letter, x, y))

# z6 conversions
written += put(f"{B} - Unit 6E",
               "A wing flat entered through the railroad chain off the "
               "stairwell — the enclosure's compromise. Berth against the "
               "old parapet line, the roofline's former edge now a window "
               "sill over Kaspar Street.")
written += put(f"{B} - Unit 6F",
               "The middle flat of the enclosed north wing: a hab built "
               "where a roof used to be, tar-line still ghosting the floor "
               "at the old plate seam, the cantilever's air on two sides.")
written += put(f"{B} - Unit 6G",
               "The end flat of the railroad chain, farthest from the "
               "stairs and quietest for it. The east window looks down the "
               "fire escape's iron toward the Boot.")
written += put(f"{B} - Unit 6A (Loggia)",
               "Unit 6A's loggia: the old terrace glassed and roofed when "
               "the tower rose, its tile still weathered where the rain "
               "used to reach. The best room in the building that the "
               "building pretends not to know about.")
written += put(f"{B} - Unit 6C (Back Room)",
               "6C's back room, taken from the south wing roof in the "
               "enclosure: shelving on the old parapet line, one thick "
               "window over Braddock, the wing's former open air still "
               "somehow in the smell of it.")
written += put(f"{B} - Unit 6B (Store Room)",
               "6B's store room — the southeast roof enclosed and put to "
               "work. Crates where the wind used to be, and a bolted hatch "
               "in the ceiling nobody discusses.")

print(f"BUILD 006: {made_buttons} call buttons, {written} descriptions.")
