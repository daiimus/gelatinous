"""Build 115 — the dispatch chair is the dispatch job (#2225).

`seated_base_station` has always said whoever holds the chair holds the
voice, but nothing in the souls layer ever sat anybody down. Placement
was cosmetic: the operator "at her console" was standing beside it, so
`active_transmit_radio` found nothing and she could not key up at all.
Invisible for as long as the console did the talking; the moment the
voice became hers (#2223) it was the whole feature.

`post_work_seat` marks the chair a post is worked FROM. This stamps it
on the dispatch chair and reports every other post that owns furniture
nobody sits in, so the owner can say which of those are desk jobs.

Idempotent.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/115_the_desk_has_a_chair.py
"""

from evennia.objects.models import ObjectDB

from typeclasses.furniture import Seating

DISPATCH_CHAIR = 4956

chair = ObjectDB.objects.filter(id=DISPATCH_CHAIR).first()
if chair is None:
    print("BUILD 115: the dispatch chair is gone; aborted")
elif chair.db.post_work_seat is True:
    print(f"BUILD 115: {chair.key} #{chair.id} already the work seat")
else:
    chair.db.post_work_seat = True
    print(f"BUILD 115: {chair.key} #{chair.id} -> post_work_seat")

# Every OTHER post that owns a seat nobody is bound to — candidates the
# owner may want to call desk work, reported rather than flagged.
print("BUILD 115: other posts with unclaimed furniture --")
posts = {
    who.db.soul_post
    for who in ObjectDB.objects.filter(db_attributes__db_key="soul_post")
    if who.db.soul_post is not None
}
for room in sorted(posts, key=lambda r: r.key):
    seats = [o for o in room.contents
             if isinstance(o, Seating) and o.db.post_work_seat is not True]
    if not seats:
        continue
    station = any(getattr(o.db, "is_base_station", None) is True
                  for o in room.contents)
    print(f"  {room.key} #{room.id}"
          f"{'  [HAS A BASE STATION]' if station else ''}")
    for seat in seats:
        print(f"      {seat.key} #{seat.id} "
              f"({seat.typeclass_path.rsplit('.', 1)[-1]})")
