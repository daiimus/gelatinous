"""Build 015 — the Mimi <-> Brackett jump edge (parkour).

    evennia shell < scripts/builds/015_mimi_brackett_jump.py
    then foreground reload.

The first inter-building parkour edge. Hotel Mimi's Sun Deck
(-8,-15,12) leaps southwest across the Kaspar gap to the Brackett's
Roof Garden North Corner #6963 (-9,-16,12) — equal roofs, a single
diagonal hop. Wired both ways off the known-good edge pattern
(is_edge + is_gap, sky_room transit, fall_room below, gap_destination
= the far roof). Fail the roll and it's twelve decks down to Kaspar
Street.
"""
from evennia import create_object
from evennia.objects.models import ObjectDB

ROOM_TC = "typeclasses.rooms.Room"
EXIT_TC = "typeclasses.exits.Exit"

sun = ObjectDB.objects.filter(db_key="Hotel Mimi - Sun Deck").first()
garden = ObjectDB.objects.filter(id=6963).first()      # Brackett North Corner
assert sun and garden, "missing endpoints"

# the ground you hit if you miss: Kaspar Street under the gap
fall = next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
             if r.db.xyz == (-8, -16, 0) and r.destination is None), None)
assert fall, "no Kaspar Street fall room at (-8,-16,0)"

# the transit air the leap crosses (over Kaspar, twelve decks up)
sky = ObjectDB.objects.filter(db_key="Kaspar Gap (Mimi–Brackett)").first()
if sky is None:
    sky = create_object(ROOM_TC, key="Kaspar Gap (Mimi–Brackett)")
    sky.db.xyz = (-8, -16, 12)
    sky.db.is_sky_room = True
    sky.db.outside = True
    sky.db.is_ground = False
    sky.db.type = "sky"
    sky.db.desc = ("Open air over Kaspar Street, twelve decks up — the "
                   "gap between the Mimi's sun deck and the Brackett's "
                   "roof garden. Nothing under you but the drop.")
    sky.db.sense_descs = {
        "olfactory": "Cold wind, and the street's exhaust rising thin.",
        "tactile": "Nothing. That's the point.",
        "atmospheric": "The half-second a leap lives in."}


def edge(loc, direction, alias, gap_dest):
    if any(e.key == direction for e in loc.exits):
        return 0
    e = create_object(EXIT_TC, key=direction, aliases=[alias],
                      location=loc, destination=sky)
    e.db.is_edge = True
    e.db.is_gap = True
    e.db.edge_difficulty = 14          # high jump, hard
    e.db.gap_difficulty = 12
    e.db.gap_width = "medium"
    e.db.fall_distance = 12
    e.db.fall_damage = 10              # per storey -> lethal from z12
    e.db.sky_room = sky.id             # dbref ints (export_map convention)
    e.db.fall_room = fall.id
    e.db.gap_destination = gap_dest.id
    return 1


made = edge(sun, "southwest", "sw", garden)          # Mimi -> Brackett
made += edge(garden, "northeast", "ne", sun)         # Brackett -> Mimi

print(f"BUILD 015: sky {sky.id}, fall {fall.id}, {made} jump edges "
      f"(Sun Deck <-> #6963, both ways).")
