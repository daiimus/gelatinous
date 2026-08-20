"""Build 084 — the Rook's biome advertises only inward (#2096).

The chair (social 0.8) and nutrient line (hunger 0.9) were summoning
the whole colony to a sealed room — souls planned social/hunger runs
at fixtures behind no door and faulted 'no path'. advertise_scope =
'room' scopes both to souls standing in (or homed to) the studio.

Idempotent. Run: docker exec -i gelatinous bash -lc \
    'cd /usr/src/game && evennia shell' < scripts/builds/084_biome_scope.py
"""

from evennia.utils.search import search_object

for dbref in ("#6035", "#8352"):        # broadcast chair, nutrient line
    obj = next(iter(search_object(dbref)), None)
    if obj is None or not obj.pk:
        print(f"BUILD 084: {dbref} missing; skipped")
        continue
    obj.db.advertise_scope = "room"
    print(f"BUILD 084: {obj.key} #{obj.id} now advertises room-only")
