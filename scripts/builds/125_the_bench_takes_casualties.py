"""Build 125 — the bench takes casualties, not just services (#2262).

Units gained a `health` need shaped `clinic`, so a damaged one now
self-delivers the way the walking wounded do. It needs a door: the
`clinic` shape looks for whatever advertises this species' service, and
for a machine that is `repair`.

Before this, a secbot could take a shotgun blast, keep patrolling on a
wrecked chassis, and turn up a week later when the WEAR timer bit. A
timer is not an injury.

The bench advertises both now:

* `maintenance` — scheduled wear, satisfied by dwelling (the service)
* `repair`      — damage, satisfied by the treat step (the casualty)

Both stay STAFFED: no keeper, no repair, and the vacancy is felt
exactly when nobody is standing there.

Idempotent.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/125_the_bench_takes_casualties.py
"""

from evennia.utils.search import search_object

bench = next(iter(search_object("#8986")), None)
if bench is None:
    print("BUILD 125: the service bench is gone; aborted")
    raise SystemExit

ads = dict(bench.db.advertises or {})
if ads.get("repair"):
    print(f"BUILD 125: {bench.key} already takes casualties")
else:
    ads["repair"] = 0.9
    bench.db.advertises = ads
    print(f"BUILD 125: {bench.key} now advertises {ads}")

bench.db.advertise_staffed = True
bench.tags.add("advertiser", category="souls")

print(f"BUILD 125: staffed={bench.db.advertise_staffed} "
      f"tagged={bool(bench.tags.get('advertiser', category='souls'))}")

# Prove a damaged unit can now find it.
from evennia.objects.models import ObjectDB
from world.souls import actions, needs as needs_mod
actions._ad_cache["at"] = 0
bot = next((o for o in ObjectDB.objects.filter(
    db_attributes__db_key="role").distinct() if o.db.role == "security"), None)
if bot is not None:
    service = needs_mod.clinic_service(bot)
    found = actions._advertisers(bot, service)
    print(f"BUILD 125: a damaged unit looks for {service!r} and finds "
          f"{found[0][1].key if found else 'NOTHING'}")
    print(f"BUILD 125: its needs are {sorted(needs_mod.profile_of(bot))}")
