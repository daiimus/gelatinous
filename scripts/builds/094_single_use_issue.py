"""Build 094 — the issue is single-use (#2120).

Thawn-Harrison issue clothing is paper-thin and heat-welded: it gets
somebody from a table to a door once. Taking it off tears it, and a
dropped suit is refuse before it lands — so the colony never grows a
stockpile of free jumpsuits.

Marks the already-spawned issue garments; any lying loose in the world
(shed at the thrift before this landed) are cleared out.

Idempotent.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/094_single_use_issue.py
"""

from evennia.objects.models import ObjectDB

marked = swept = 0
for obj in ObjectDB.objects.filter(db_key__icontains="Thawn-Harrison"):
    if not obj.attributes.get("coverage"):
        continue                      # the dispenser itself, not a garment
    if not obj.attributes.get("single_use"):
        obj.attributes.add("single_use", True)
        marked += 1
    # loose on a floor or in a bin: refuse, by its own nature
    holder = obj.location
    if holder is not None and holder.is_typeclass(
            "typeclasses.rooms.Room", exact=False):
        obj.delete()
        swept += 1

print(f"BUILD 094: {marked} issue garments marked single-use; "
      f"{swept} discarded suits swept from the floor")
