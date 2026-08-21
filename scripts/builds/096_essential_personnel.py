"""Build 096 — mark the cast as Essential Personnel (#2128).

Essential Personnel are archived at death rather than deleted: they
wait in Limbo exactly as dead PC sleeves already do, and a resleeve
restores the PERSON instead of rebuilding a copy from their blueprint.
Generated residents keep deleting — they are what that branch was
written to stop accumulating.

Stamps everyone currently in the world who was built from a blueprint,
plus the handful rebuilt by hand before the flag existed.

Idempotent.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/096_essential_personnel.py
"""

from world.npcs.blueprints import BLUEPRINTS
from world.souls import engine

BY_NAME = {bp["name"]: key for key, bp in BLUEPRINTS.items()
           if not bp.get("fixture")}

marked = []
for soul in engine.get_souls():
    if not soul.pk:
        continue
    bp_key = soul.db.blueprint_key or BY_NAME.get(soul.key)
    if not bp_key:
        continue
    soul.db.essential = True
    soul.db.blueprint_key = bp_key
    marked.append(f"{soul.key} ({bp_key})")

print(f"BUILD 096: {len(marked)} Essential Personnel marked")
for line in sorted(marked):
    print(f"    {line}")
