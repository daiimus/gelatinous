"""Build 124 — three shifts of somebody with hands (#2261).

`maintenance` was advertised nowhere on purpose: the dwell step's
maintenance branch also CLEARS a logged defect, so any advertiser would
let a unit service itself by leaning on a wall fitting — deleting the
job a person is meant to hold. But "nowhere" left the force
accumulating faults nobody could ever clear.

A STAFFED advertiser is the middle. The bench offers repair only while
somebody is standing their shift at it; off shift the need has no plan
at all, and that absence is what a vacancy feels like.

This builds the bench and the three people:

* the bench in the Constabulary Secure Corridor, beside the charging
  rack — tagged `advertiser`/souls (advertisers are found by INDEXED
  TAG, never by the attribute — hardening spec law #3), advertising
  `maintenance` and marked `advertise_staffed`
* a post on it with day / swing / night slots
* Marisol, Tuck and Halina, from blueprints, installed the same way any
  keeper is

And it issues them the biometric floor grant, because they work behind
the same lock the dispatchers do. Build 117 hired two people into that
building and forgot this, and the fault log said "no path to Colonial
Constabulary Dispatch Operations" for hours before anyone read it
(#2244). Not making that one twice.

Idempotent.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/124_somebody_with_hands.py
"""

from evennia import create_object
from evennia.utils.search import search_object

from world.access import is_granted, make_grant
from world.npcs.blueprints import build_npc
from world.souls import posts as posts_mod

ROOM = "#4960"          # Constabulary Secure Corridor (floor 2)
CAR = "#4969"           # the lift, whose floor_locks gate this floor
FLOOR = "2"
SHIFTS = (("day", "mech_marisol"), ("swing", "mech_tuck"),
          ("night", "mech_halina"))

room = next(iter(search_object(ROOM)), None)
if room is None:
    print("BUILD 124: the secure corridor is gone; aborted")
    raise SystemExit

# --- the bench ---------------------------------------------------------
bench = next((o for o in room.contents
              if getattr(o.db, "is_service_bench", None) is True), None)
if bench is None:
    bench = create_object("typeclasses.items.Item",
                          key="a Boiler Run service bench", location=room)
    bench.aliases.add(["bench", "service bench"])
    bench.db.is_service_bench = True
    bench.db.desc = (
        "A steel bench bolted along the corridor wall opposite the "
        "cradles, its top scarred to a dull shine and its edge worn "
        "concave where forearms have rested on it for years. A rack of "
        "drivers hangs above in size order; a parts tray at the end "
        "holds screws sorted by somebody who clearly minds. The Boiler "
        "Run plate is polished where a thumb finds it."
    )
    bench.locks.add("get:false()")
    print(f"BUILD 124: {bench.key} #{bench.id} installed in {room.key}")
else:
    print(f"BUILD 124: bench #{bench.id} already here")

bench.db.advertises = {"maintenance": 0.9}
bench.db.advertise_staffed = True        # no keeper, no repair
bench.tags.add("advertiser", category="souls")
print(f"BUILD 124: bench advertises {dict(bench.db.advertises)} "
      f"staffed={bench.db.advertise_staffed}")

if not bench.db.post_role:
    posts_mod.register_post(bench, role="mechanic", schedule="day",
                            wage_rate=0.03, policy="successor",
                            shifts=("day", "swing", "night"))
    print("BUILD 124: bench registered as a post (day/swing/night)")

plans = dict(bench.db.post_blueprints or {})
for shift, key in SHIFTS:
    plans[shift] = key
bench.db.post_blueprints = plans

# --- the people --------------------------------------------------------
for shift, bp_key in SHIFTS:
    slot = (bench.db.post_slots or {}).get(shift) or {}
    keeper = slot.get("keeper")
    if keeper is not None and keeper.pk:
        print(f"BUILD 124: {shift} already held by {keeper.key}")
        continue
    walking = posts_mod._living_body(bp_key)
    if walking is not None:
        slots = dict(bench.db.post_slots or {})
        slots[shift] = {"keeper": walking, "vacant_since": None}
        bench.db.post_slots = slots
        print(f"BUILD 124: {walking.key} re-bound to {shift}")
        continue
    npc = build_npc(bp_key, room)
    if npc is None:
        print(f"BUILD 124: could not build {bp_key}")
        continue
    posts_mod._install_keeper(npc, bench, room, shift)
    print(f"BUILD 124: {npc.key} #{npc.id} on {shift} "
          f"(home {npc.db.soul_home})")

# --- the door ----------------------------------------------------------
car = next(iter(search_object(CAR)), None)
if car is not None:
    locks = dict(car.db.floor_locks or {})
    grants = list(locks.get(FLOOR) or [])
    for shift, _bp in SHIFTS:
        who = ((bench.db.post_slots or {}).get(shift) or {}).get("keeper")
        if who is None or not who.pk or is_granted(who, grants):
            continue
        grants.append(make_grant(who, issued_by="Colonial Constabulary"))
        print(f"BUILD 124: {who.key} granted floor {FLOOR}")
    locks[FLOOR] = grants
    car.db.floor_locks = locks

print("BUILD 124: the bench now reads --")
for shift, slot in sorted((bench.db.post_slots or {}).items()):
    who = slot.get("keeper")
    print(f"   {shift:6} {who.key if who else '(vacant)'}")
