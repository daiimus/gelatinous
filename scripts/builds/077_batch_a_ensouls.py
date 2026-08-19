"""Build 077 — the Full Soul Count, Batch A: the counter-keepers.

Ottilie, Ezra, and Bellows join the economy (souls spec P2 "named
NPCs, carefully" — batch A is the pre-blessed tier: vendors keeping
honest hours is exactly why the keeper-gate exists). Each gets their
counter as an administrative post (keeper-bound: the shop CLOSES when
they walk away), their registry blueprint attached as data (policy
stays successor pending the owner's insurance roster), a real cube
off the kiosk board, and a soul on a working schedule. Their personas
already exist; the STATE line keeps the voice honest off-post.

Idempotent: skips any keeper already ensouled.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/077_batch_a_ensouls.py
"""

from evennia.utils.search import search_object

from world import rental
from world.souls import engine, ensoul
from world.souls.posts import register_post

DAY = 24 * 3600
BATCH = [
    # (npc dbref, counter dbref, role, schedule, blueprint)
    ("#5222", "#5221", "butcher", "vendor", "butcher_ottilie"),
    ("#5161", "#5160", "pawnbroker", "day", "merchant_ezra"),
    ("#5624", "#5484", "tobacconist", "vendor", "tobacconist_bellows"),
]

kiosk = next(iter(search_object("#5640")), None)
souled = {s.id for s in engine.get_souls() if s.pk}

for npc_ref, counter_ref, role, schedule, blueprint in BATCH:
    npc = next(iter(search_object(npc_ref)), None)
    counter = next(iter(search_object(counter_ref)), None)
    if npc is None or counter is None:
        print(f"  {npc_ref}: MISSING pieces; skipped")
        continue
    if npc.id in souled:
        print(f"  {npc.key}: already ensouled; skipped")
        continue
    register_post(counter, role=role, schedule=schedule, wage_rate=0.02,
                  policy="successor", delay=3 * DAY, keeper=npc)
    counter.db.post_blueprint = blueprint
    counter.db.post_keeper = npc          # the shop keeps their hours now
    if not npc.tokens:
        npc.tokens = 10
    ok, msg = rental.assign_cube(npc, kiosk)
    home = rental.residence_of(npc)
    ensoul(npc, role=role, home=home, post=counter.location,
           schedule=schedule, wage_rate=0.02, venue=counter)
    print(f"  {npc.key} (#{npc.id}) role:{role} sched:{schedule} "
          f"till:{counter.db.register} home:"
          f"{home.key if home else 'NONE'} "
          f"kiosk:{'ok' if ok else 'FAILED — ' + msg}")

print("BUILD 077: batch A ensouled")
print(f"  souls now: {[(s.key, s.db.soul_role) for s in engine.get_souls() if s.pk]}")
