"""Build 116 — the crane cab's chair is the crane job too (#2227).

Consistency, which is the point: a post worked from a seat declares
that seat, and then it works the same way everywhere. Build 115 marked
the dispatch chair and reported the operator's chair in the Boiler Run
cab as the only other seat sitting beside a base station.

Ossie doesn't strictly need it — the crane console is its own transmit
device, so the hoist answers whether he's standing or sitting. But the
chair is how you hold a post, and a keeper who is visibly seated at his
board can key up in his own voice off his own device like anyone else.
Same rule in both cabs, and whoever takes either chair inherits it.

Idempotent.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/116_the_cab_has_a_chair.py
"""

from evennia.objects.models import ObjectDB

from typeclasses.furniture import Seating

CAB_CHAIR = 7400

chair = ObjectDB.objects.filter(id=CAB_CHAIR).first()
if chair is None:
    print("BUILD 116: the cab chair is gone; aborted")
elif not isinstance(chair, Seating):
    print(f"BUILD 116: #{CAB_CHAIR} is {chair.typeclass_path}, not seating; "
          f"aborted")
elif chair.db.post_work_seat is True:
    print(f"BUILD 116: {chair.key} #{chair.id} already the work seat")
else:
    chair.db.post_work_seat = True
    print(f"BUILD 116: {chair.key} #{chair.id} -> post_work_seat "
          f"(in {chair.location.key if chair.location else None})")

# Every seat now declared, so the rule is auditable in one place.
print("BUILD 116: declared work seats --")
for obj in ObjectDB.objects.filter(
        db_attributes__db_key="post_work_seat").distinct():
    if obj.db.post_work_seat is True:
        print(f"  {obj.key} #{obj.id} in "
              f"{obj.location.key if obj.location else None}")
