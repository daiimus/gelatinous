"""Build 163 — clear the parcels that piled up on the consignor (#3192).

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/163_clear_the_consignors_pile.py

DEFAULTS TO A CENSUS. Set PURGE = True to delete.

The stale-parcel sweep looked in the COURIER's hands; `_spawn_package`
puts the parcel in the CLERK's. A run that never got as far as
collecting left it there and nothing swept the clerk, so one arrived per
failed run and none was ever removed — 72 on `#5161 Ezra Vantomme`.

The leak is closed in `world/souls/salience.py`. This is the banked
damage.

Deliberately narrow: only objects carrying `courier_package`, and only
those held by somebody who is NOT the courier — a courier legitimately
carries the one she is delivering right now. The disposal rule is the
one the sweep already states: a parcel ends delivered and destroyed, or
stolen and fenced and destroyed; an undelivered one has no third ending
yet.

Re-run-safe: the predicate is a census.
"""
from collections import Counter

from evennia.objects.models import ObjectDB
from world.souls.engine import get_souls

PURGE = False          # flip to True to delete

couriers = {s.id for s in get_souls()
            if s.pk and s.db.soul_runs_made is not None}
print(f"couriers: {sorted(couriers) or 'none found'}")

stranded = []
for obj in ObjectDB.objects.all():
    if not obj.attributes.has("courier_package"):
        continue
    holder = obj.location
    if holder is None or getattr(holder, "id", None) in couriers:
        continue
    stranded.append(obj)

by_holder = Counter(f"{getattr(o.location, 'key', None)}"
                    f"#{getattr(o.location, 'id', None)}" for o in stranded)
print(f"parcels held by a non-courier: {len(stranded)}")
for who, count in by_holder.most_common():
    print(f"    {count:>4}  {who}")

if not stranded:
    print("\nNOTHING MATCHED. Before believing that, confirm the courier "
          "list above is not accidentally everybody.")
elif PURGE:
    ids = sorted(o.id for o in stranded)
    for obj in stranded:
        obj.delete()
    print(f"\ndeleted {len(ids)} (ids {ids[0]}..{ids[-1]})")
else:
    print("\nCENSUS ONLY — set PURGE = True to delete.")
