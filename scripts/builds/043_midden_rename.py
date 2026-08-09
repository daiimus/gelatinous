"""Build 043 — Rust Acre becomes The Midden.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/043_midden_rename.py
    then a foreground reload.

Owner renamed the scrapyard. Swap the name in the twelve room keys and on
the gate board; the cell prose never carried it, so nothing else changes.
Idempotent.
"""
from evennia.objects.models import ObjectDB

n = 0
for r in ObjectDB.objects.filter(db_key__startswith="Rust Acre"):
    if r.destination is not None:
        continue
    r.key = r.key.replace("Rust Acre", "The Midden")
    n += 1

# the gate board
gate = ObjectDB.objects.filter(db_key="The Midden - Gate").first()
if gate and gate.db.desc:
    gate.db.desc = gate.db.desc.replace("RUST ACRE", "THE MIDDEN")

print(f"BUILD 043: renamed {n} cells Rust Acre -> The Midden; gate board updated.")
