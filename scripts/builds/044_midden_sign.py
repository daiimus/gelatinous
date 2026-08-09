"""Build 044 — the gate board reads RECLAMATION PIT.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/044_midden_sign.py
    then a foreground reload.

Owner: drop 'WE BUY / WE DON'T ASK'; the board's second line is just
'RECLAMATION PIT'. Idempotent.
"""
from evennia.objects.models import ObjectDB

gate = ObjectDB.objects.filter(db_key="The Midden - Gate").first()
assert gate is not None, "The Midden - Gate not found"
d = gate.db.desc or ""
d = d.replace("WE BUY / WE DON'T ASK", "RECLAMATION PIT")
gate.db.desc = d
print(f"BUILD 044: gate board -> {'RECLAMATION PIT' in d}")
