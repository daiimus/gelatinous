"""Build 045 — The Midden's bespoke atlas skins.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/045_midden_skins.py
    then a foreground reload.

Point each of the twelve yard cells at its OWN sprite — no shared tiles,
so the yard never reads as a repeat pattern. (Build 042 staged shared
names; this replaces the doubled ones with unique per-cell sprites now
that they're baked.) Data-only, re-run-safe.
"""
from evennia.objects.models import ObjectDB
from world.spatial import get_xyz

SKINS = {
    (-11, -13): "scrap_nw", (-10, -13): "scrap_n1", (-9, -13): "scrap_n2",
    (-8, -13): "scrap_ne", (-11, -14): "scrap_w", (-10, -14): "scrap_heap",
    (-9, -14): "scrap_mid", (-8, -14): "scrap_hull", (-11, -15): "scrap_sw",
    (-10, -15): "scrap_gate", (-9, -15): "scrap_weigh", (-8, -15): "scrap_se",
}


def at(xyz):
    return next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
                 if r.destination is None and get_xyz(r) == xyz), None)


n = 0
for (x, y), skin in SKINS.items():
    r = at((x, y, 0))
    if r is not None:
        r.db.atlas_skin = skin
        n += 1

print(f"BUILD 045: {n} Midden cells reskinned to unique sprites.")
