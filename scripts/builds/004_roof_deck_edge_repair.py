"""Build 004 — Roof Deck stale edge flags (owner review finding).

    evennia shell < scripts/builds/004_roof_deck_edge_repair.py

The Brackett Roof Deck's east and west exits point correctly at the
East Roof and West Roof plates — same level, plain walks — but carried
is_edge=True from an earlier wiring pass, so walking between roof
plates behaved like jumping off a rim. The diagonal exits into the air
ARE edges and stay. This clears every edge/gap attribute from the two
plate-to-plate walks. (Applied live 2026-08-05; this script is the
idempotent record.)
"""
from evennia.objects.models import ObjectDB

CLEAR = ("is_edge", "edge_difficulty", "fall_room", "fall_damage",
         "fall_distance", "sky_room", "is_gap", "gap_difficulty",
         "gap_destination", "gap_width")

deck = ObjectDB.objects.filter(db_key="The Brackett Arms - Roof Deck").first()
assert deck, "Roof Deck missing"
fixed = 0
for e in deck.exits:
    dest = e.destination
    if dest and dest.key in ("The Brackett Arms - East Roof",
                             "The Brackett Arms - West Roof"):
        for attr in CLEAR:
            if e.attributes.has(attr):
                e.attributes.remove(attr)
                fixed += 1
print(f"BUILD 004: cleared {fixed} stale attrs; deck-to-plate exits are plain walks.")
