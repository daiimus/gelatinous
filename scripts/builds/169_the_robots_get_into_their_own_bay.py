"""Build 169 — the robots get into their own bay (#2696).

The force's only `maintenance` advertiser is the Boiler Run service
bench in the Constabulary Secure Corridor (build 124), one floor up a
lift whose floor "2" is a biometric lock. The grant file on that floor
carried the dispatchers and the three mechanics; it never carried the
eight security robots the bench exists to service. The pathfinder
honours the lock (`_floor_permitted`), `_reachable_only` dropped the
bench, `plan_for(bot, "maintenance")` was None for every unit, and each
one logged a fault every goal cooldown from 2026-08-29 on — more fault
lines than every other unsatisfiable goal combined (#2696).

Owner, 2026-10-11: "Grant them access."

This issues a Colonial Constabulary floor-2 grant to every security
robot's sleeve — a body whose key says "security robot" and whose needs
profile is `robot`. Idempotent: a sleeve already on the file is skipped,
and the grant shape is `world.access.make_grant`, the same record the
mechanics carry.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/169_the_robots_get_into_their_own_bay.py
then `evennia reload`: the running server caches `db.floor_locks`, and an
external write reaches it only after one.
"""

from evennia.objects.models import ObjectDB
from evennia.utils.search import search_object

from world.access import is_granted, make_grant
from world.souls import needs as needs_mod

CAR = "#4969"           # Colonial Constabulary Elevator Car
FLOOR = "2"             # Colonial Constabulary Secure Corridor
ISSUER = "Colonial Constabulary"


def _is_security_robot(obj):
    if not obj.pk or "security robot" not in (obj.key or "").lower():
        return False
    try:
        return needs_mod.profile_name(obj) == "robot"
    except Exception:  # noqa: BLE001 — not a souled body: not a candidate
        return False


car = next(iter(search_object(CAR)), None)
if car is None:
    print("BUILD 169: the Constabulary car is gone; aborted")
    raise SystemExit
labels = [str(f[1]) for f in (car.db.floors or [])]
if FLOOR not in labels:
    print(f"BUILD 169: floor {FLOOR!r} is not on the car ({labels}); aborted")
    raise SystemExit

robots = sorted(
    (o for o in ObjectDB.objects.filter(db_key__icontains="security robot")
     if _is_security_robot(o)),
    key=lambda o: o.id)
print(f"BUILD 169: {len(robots)} security robots found")

locks = dict(car.db.floor_locks or {})
grants = list(locks.get(FLOOR) or [])
before = len(grants)
for bot in robots:
    if is_granted(bot, grants):
        print(f"BUILD 169: #{bot.id} {bot.key} already granted")
        continue
    grant = make_grant(bot, issued_by=ISSUER)
    if not grant["sleeve"]:
        print(f"BUILD 169: #{bot.id} {bot.key} has no sleeve uid; skipped")
        continue
    grants.append(grant)
    print(f"BUILD 169: #{bot.id} {bot.key} granted floor {FLOOR}")
locks[FLOOR] = grants
car.db.floor_locks = locks
print(f"BUILD 169: floor {FLOOR} grant file {before} -> {len(grants)} entries")

idx = labels.index(FLOOR)
for bot in robots:
    print(f"BUILD 169: floor {FLOOR} button lights for #{bot.id}: "
          f"{car._floor_permitted(idx, bot)}")
