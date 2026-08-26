"""Build 135 — the colony can eat after dark (#2325).

The souls audit log counted it: 26 souls pinned at maximum hunger, and
`no_plan_satisfies_'hunger'` faulting every beat. The cause was not
code:

    Lin's noodle cart   INFINITE stock   staffed: day only
    the shell counter   INFINITE stock   staffed: day only
    Ottilie's cart      FINITE, EMPTY    staffed: swing only

Both stocked counters were day-only, so for sixteen hours out of
twenty-four the only open food in the colony was a butcher's cart with
nothing in it. Nobody starves visibly, so it went unnoticed until
something counted.

The shell counter even HAD its swing and night slots declared -- with
`post_blueprints` empty, so the vacancy watcher could never fill them.
Structure built, never wired.

Four keepers, same pattern as the dispatch desk, the bench and Kaspar:
blueprints in the registry, installed into slots the posts declare.
Lin's cart needs its swing and night slots created first; it only ever
had day.

Deliberately NOT touching Ottilie. Her cart is finite-stock by design
-- carcasses in, dishes out -- and an empty butcher's counter is the
gig loop being quiet, not a staffing bug.

Idempotent.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/135_the_colony_eats_after_dark.py
"""

from evennia.objects.models import ObjectDB

from world.npcs.blueprints import build_npc
from world.souls import posts as posts_mod

PLAN = (
    ("the shell counter", (("swing", "snailer_pia"),
                           ("night", "snailer_tobias"))),
    ("Lin's noodle cart", (("swing", "vendor_marek"),
                           ("night", "vendor_sunniva"))),
)

for counter_key, shifts in PLAN:
    found = [o for o in ObjectDB.objects.all() if o.key == counter_key]
    if not found:
        print(f"BUILD 135: {counter_key} is gone; skipped")
        continue
    counter = found[0]
    room = counter.location

    slots = dict(counter.db.post_slots or {})
    plans = dict(counter.db.post_blueprints or {})
    for shift, bp_key in shifts:
        slots.setdefault(shift, {"keeper": None, "vacant_since": 1.0})
        plans[shift] = bp_key
    counter.db.post_slots = slots
    counter.db.post_blueprints = plans

    for shift, bp_key in shifts:
        slot = (counter.db.post_slots or {}).get(shift) or {}
        keeper = slot.get("keeper")
        if keeper is not None and keeper.pk:
            print(f"BUILD 135: {counter_key} {shift} already held by "
                  f"{keeper.key}")
            continue
        walking = posts_mod._living_body(bp_key)
        if walking is not None:
            s = dict(counter.db.post_slots or {})
            s[shift] = {"keeper": walking, "vacant_since": None}
            counter.db.post_slots = s
            print(f"BUILD 135: {walking.key} re-bound to {counter_key} "
                  f"{shift}")
            continue
        npc = build_npc(bp_key, room)
        if npc is None:
            print(f"BUILD 135: could not build {bp_key}")
            continue
        posts_mod._install_keeper(npc, counter, room, shift)
        print(f"BUILD 135: {npc.key} #{npc.id} on {counter_key} {shift}")

    print(f"BUILD 135: {counter_key} now reads --")
    for shift, slot in sorted((counter.db.post_slots or {}).items()):
        who = (slot or {}).get("keeper")
        print(f"   {shift:6} {who.key if who else '(vacant)'}")

# The question this build exists to answer: can a hungry soul eat now?
from world.souls.engine import get_souls
from world.souls import needs as needs_mod, actions
hungry = [s for s in get_souls()
          if needs_mod.pressures(s).get("hunger", 0) >= 1.0]
fed = sum(1 for s in hungry if actions.plan_for(s, "hunger"))
print(f"BUILD 135: souls at maximum hunger: {len(hungry)}; "
      f"able to form a plan now: {fed}")
