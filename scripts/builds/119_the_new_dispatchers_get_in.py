"""Build 119 — issue the dispatch floor to the keepers who work there.

Build 117 hired Kiro and Ines and never gave them the building.

The constabulary's dispatch floor is biometrically locked: the lift's
`db.floor_locks["2"]` is a grant file of `{"sleeve", "until",
"issued_by"}` entries, and `world.access.is_granted` reads the
presenter's `sleeve_uid` against it. Petra's sleeve was in there; the
two new keepers' were not.

The effect was total rather than partial. `_floor_permitted` refuses,
so the lift stops being a routable edge for them, so their own post is
unreachable, so `plan_for("duty")` finds no plan and they never go to
work. The emergency board read as staffed on all three shifts while
two of its three keepers were physically unable to reach the desk —
and the fault log said so all along: "no path to Colonial Constabulary
Dispatch Operations".

Grants persist correctly across a resleeve without any help: the
sleeve uid IS the body, flash clones inherit it, and `imprint.restore`
writes it back — the same fact that keeps people recognising you.

Idempotent. Issues only what is missing, and reports the resulting
grant file so the door policy is auditable in one place.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/119_the_new_dispatchers_get_in.py
"""

from evennia.utils.search import search_object

from world.access import is_granted, make_grant, sleeve_uid_of

CAR = "#4969"                 # Colonial Constabulary Elevator Car
FLOOR = "2"                   # the dispatch floor
ISSUER = "Colonial Constabulary"
KEEPERS = ("#8827", "#8833")  # Kiro (swing), Ines (night)

car = next(iter(search_object(CAR)), None)
if car is None:
    print("BUILD 119: the constabulary lift is gone; aborted")
    raise SystemExit

locks = dict(car.db.floor_locks or {})
grants = list(locks.get(FLOOR) or [])

for ref in KEEPERS:
    who = next(iter(search_object(ref)), None)
    if who is None or not who.pk:
        print(f"BUILD 119: {ref} not found; skipped")
        continue
    uid = sleeve_uid_of(who)
    if not uid:
        print(f"BUILD 119: {who.key} has no sleeve uid; skipped")
        continue
    if is_granted(who, grants):
        print(f"BUILD 119: {who.key} already reads in")
        continue
    grants.append(make_grant(who, issued_by=ISSUER))
    print(f"BUILD 119: {who.key} #{who.id} granted floor {FLOOR} "
          f"(sleeve {uid[:8]}…)")

locks[FLOOR] = grants
car.db.floor_locks = locks

print(f"BUILD 119: floor {FLOOR} grant file now --")
for entry in grants:
    print(f"   {str(entry.get('sleeve'))[:8]}…  issued_by="
          f"{entry.get('issued_by')!r}  until={entry.get('until')}")

# Prove it the way the lift will ask.
print("BUILD 119: can they reach the desk now? --")
from world.spatial.pathfind import is_reachable
post = next(iter(search_object("#4963")), None)
for ref in KEEPERS:
    who = next(iter(search_object(ref)), None)
    if who is None or post is None:
        continue
    print(f"   {who.key:<6} permitted={car._floor_permitted(1, who)} "
          f"post_reachable={is_reachable(who.location, post, traverser=who)}")
