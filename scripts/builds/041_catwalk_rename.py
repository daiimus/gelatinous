"""Build 041 — the catwalk belongs to the Brackett.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/041_catwalk_rename.py
    then a foreground reload.

Owner: rename "Kaspar Catwalk" -> "The Brackett Arms - Catwalk". It hangs
off the Brackett's roof garden; the name should say so. Found by
coordinate (-8,-16,12); atlas skin and exits key off id/skin, not the
name, so the rename is cosmetic. Re-run-safe.
"""
from evennia.objects.models import ObjectDB
from world.spatial import get_xyz

cw = next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
           if r.destination is None and get_xyz(r) == (-8, -16, 12)), None)
assert cw is not None, "catwalk not found at (-8,-16,12)"
cw.key = "The Brackett Arms - Catwalk"
print(f"BUILD 041: #{cw.id} -> {cw.key!r}")
