"""Build 052 — fill the ground-level gaps around Hammett's Boot.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/052_boot_hull_mass.py
    then a foreground reload.

The real gaps were at STREET level: the market sole is one lit strip with
nine dead empty cells around it (above at y-17, below at y-19, behind the
heel), reading as black holes. None of the Boot's exits touch them (they're
pure negative space), so cap them all with full-height inaccessible
hull-mass filler — the boot becomes one solid derelict hull with the market
carved into it. The toe (Spur/Toe/Lug) is already solid. Rollback = delete
these rooms. Re-run-safe.
"""
from evennia import create_object
from evennia.objects.models import ObjectDB
from world.spatial import get_xyz

ROOM_TC = "typeclasses.rooms.Room"
# every dead ground cell ringing the Boot's sole (verified: no exits into them)
FILL = [(-9, -18, 0), (-8, -19, 0),
        (-7, -17, 0), (-6, -17, 0), (-5, -17, 0),
        (-7, -19, 0), (-6, -19, 0), (-5, -19, 0), (-4, -19, 0)]

DESC = ("The riveted flank of Hammett's Boot's hull — rust-streaked plate "
        "welded shut, the derelict's solid outside. No door, no seam that "
        "opens. Just the old ship, closed to the world.")


def at(xyz):
    return next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
                 if r.destination is None and get_xyz(r) == xyz), None)


made = 0
for xyz in FILL:
    r = at(xyz)
    if r is None:
        r = create_object(ROOM_TC, key="Hammett's Boot - Hull")
        r.db.xyz = xyz
        r.db.outside = True
        r.db.desc = DESC
        made += 1
    r.key = "Hammett's Boot - Hull"
    r.db.type = "hull"
    r.db.atlas_skin = "hull_mass"        # skin wins in cls(); no exits = inaccessible

print(f"BUILD 052: filled {len(FILL)} boot-ground gaps (+{made} new), "
      f"skin=hull_mass, no exits.")
