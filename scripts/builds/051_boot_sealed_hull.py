"""Build 051 — seal the gaps in Hammett's Boot's hull-top.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/051_boot_sealed_hull.py
    then a foreground reload.

Owner: the Boot's exits are final; the sprite should say so. The hull-top
is three walkable decks (Shin Plate, Instep, Rand) with blank gaps between
and at the toe. Cap those four empty cells with inaccessible sealed-hull
filler — no exits, welded shut — so the derelict reads as one continuous
hull with the three decks as its only footing. The heel cells at x-8 stay
untouched: they're live 'In the Air' parkour cells, not dead map. The arch
at street level stays open too (it's the boot's shape). Rollback = delete
these four rooms. Re-run-safe.
"""
from evennia import create_object
from evennia.objects.models import ObjectDB
from world.spatial import get_xyz

ROOM_TC = "typeclasses.rooms.Room"
# the sole-top cells that are NOT one of the three walkable decks
SEAL = [(-6, -18, 1), (-5, -18, 1), (-4, -18, 1), (-3, -17, 1)]

DESC = ("A welded-over section of Hammett's Boot's hull — riveted plate and "
        "cross-welded hatches, sealed for good. No deck, no way up: just the "
        "curve of the old derelict, closed to the world.")


def at(xyz):
    return next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
                 if r.destination is None and get_xyz(r) == xyz), None)


made = 0
for xyz in SEAL:
    r = at(xyz)
    if r is None:
        r = create_object(ROOM_TC, key="Hammett's Boot - Sealed Hull")
        r.db.xyz = xyz
        r.db.outside = True
        r.db.desc = DESC
        made += 1
    r.key = "Hammett's Boot - Sealed Hull"
    r.db.type = "rooftop"
    r.db.atlas_skin = "sealed_hull"      # skin wins in cls(); no exits = inaccessible

print(f"BUILD 051: sealed {len(SEAL)} boot hull-top cells (+{made} new), "
      f"skin=sealed_hull, no exits.")
