"""Build 134 — tag the crane so nothing has to hunt for it (#2323).

`courier._crane_car()` answers "is this soul standing at the crane?" on
EVERY travel step for EVERY soul. The first version answered it by
walking `ObjectDB.objects.all()` -- a full table scan, thirty-odd times
a beat, to return "no" almost every time.

Now it is an indexed tag lookup cached for a minute, the same shape
advertisers use (hardening spec law #3). New containers tag themselves
at creation; this tags the one already standing at the Marlowe Lot.

Idempotent.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/134_tag_the_crane.py
"""

from evennia.objects.models import ObjectDB

from world.director.courier import CRANE_TAG, _crane_cache, _the_crane

cars = [o for o in ObjectDB.objects.all()
        if "CraneContainer" in o.typeclass_path]
if not cars:
    print("BUILD 134: no crane container found; aborted")
    raise SystemExit

for car in cars:
    if car.tags.get(CRANE_TAG[0], category=CRANE_TAG[1]):
        print(f"BUILD 134: {car.key} #{car.id} already tagged")
    else:
        car.tags.add(CRANE_TAG[0], category=CRANE_TAG[1])
        print(f"BUILD 134: {car.key} #{car.id} tagged")

_crane_cache["at"] = 0.0            # force a fresh read
car, dock = _the_crane()
print(f"BUILD 134: lookup returns {car} docking at "
      f"{dock.key if dock else 'NOWHERE'}")
