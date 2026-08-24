"""Build 123 — the security force joins the colony (Phase 2, #2251).

Six security units, and only one had a soul. They ran entirely on the
director's assignment machinery: told where to go, told what to do on
arrival, invisible to the system every other body in the colony lives
in. No needs, no faults, no thoughts, nothing to interrupt.

Almost all of the machinery for this was already written and had never
run:

* `PROFILES["robot"]` — `charge` (~12h to critical) and `maintenance`
  (~1 week) in place of hunger and rest.
* `_wear_and_tear` — a unit left too long between services acquires a
  DEFECT, and logs a fault saying why.
* `traits.DEFECTS` — the vocabulary of them. `ghost_contact`: "sees
  threats that aren't there… turns sharply toward nothing and holds
  there", with dials that genuinely shift its safety threshold.
* `registry_for` — already routes machines to DEFECTS and people to
  TRAITS.

So a neglected secbot was always DESIGNED to become a paranoid one.
None of it fired, because nothing was souled.

Schedule is `always` — a machine does not clock off. What takes a unit
out of service is a flat battery or a fault, not the end of a shift.

Wage is zero: they are property. That needed the falsy-zero fix first,
because `rate or 0.02` read a rate of nothing as "unset" and paid the
default.

Post is each unit's existing base (`db.post`) — where it returns when
it has nothing else to do. Assignments still outrank souls entirely
(`think` returns early for an assigned NPC), so answering a call is
unaffected.

Expect maintenance to fault: it is advertised NOWHERE on purpose, so
that servicing a unit stays a person's job (owner ruling). The faults
are the vacancy.

Idempotent.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/123_the_units_get_souls.py
"""

from evennia.objects.models import ObjectDB

from world.souls import engine, needs as needs_mod

units = [o for o in ObjectDB.objects.filter(
    db_attributes__db_key="role").distinct()
    if o.pk and o.db.role == "security"]
print(f"BUILD 123: {len(units)} security units")

for unit in units:
    base = unit.db.post or unit.location
    souled = bool(unit.tags.get(engine.SOUL_TAG[0],
                                category=engine.SOUL_TAG[1]))
    already = souled and unit.db.soul_post is base \
        and unit.db.soul_schedule == "always"
    if already:
        print(f"BUILD 123: {unit.key} #{unit.id} already enlisted")
        continue

    engine.ensoul(unit, role="security", home=None, post=base,
                  schedule="always", wage_rate=0.0, profile="robot")
    print(f"BUILD 123: {unit.key} #{unit.id} enlisted "
          f"(base {getattr(base, 'key', None)})")

print("BUILD 123: the force now reads --")
for unit in units:
    pressures = {k: round(v, 2)
                 for k, v in needs_mod.pressures(unit).items() if v}
    print(f"   {unit.key:<32} #{unit.id} "
          f"profile={needs_mod.profile_name(unit)} "
          f"wage={unit.db.soul_wage_rate} needs={pressures}")

print("BUILD 123: charge advertisers reachable? --")
from world.souls import actions
for unit in units[:3]:
    ads = actions._advertisers(unit, "charge")
    print(f"   {unit.key} #{unit.id}: "
          f"{ads[0][1].key if ads else 'NO CHARGE POINT IN RANGE'}")
print("BUILD 123: maintenance advertisers (expected: none — it is a job)")
for unit in units[:1]:
    ads = actions._advertisers(unit, "maintenance")
    print(f"   {unit.key}: {ads[0][1].key if ads else 'none, by design'}")
