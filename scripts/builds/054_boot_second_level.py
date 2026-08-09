"""Build 054 — bring Hammett's Boot's second level into the one building.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/054_boot_second_level.py
    then a foreground reload.

The Boot renders like any horizontal building now: full hull cubes that
tile. This skins the z1 cells (the old walkable decks + the sealed caps)
as the SAME hull cube, so they read as the second storey of one solid
mass instead of a disconnected rooftop. Atlas skins only; rooms/exits
untouched (the decks stay walkable). Re-run-safe.
"""
from evennia.objects.models import ObjectDB
from world.spatial import get_xyz

# every z1 Boot cell — walkable decks and sealed caps alike
Z1 = [(-7, -18, 1), (-3, -18, 1), (-3, -19, 1),
      (-6, -18, 1), (-5, -18, 1), (-4, -18, 1), (-3, -17, 1)]


def at(xyz):
    return next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
                 if r.destination is None and get_xyz(r) == xyz), None)


n = 0
for xyz in Z1:
    r = at(xyz)
    if r is not None:
        r.db.atlas_skin = "boot_flank"       # blank hull cube = the upper storey
        n += 1

print(f"BUILD 054: {n} Boot second-level cells re-skinned to the hull cube.")
