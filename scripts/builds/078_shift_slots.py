"""Build 078 — the tripartite clock: 24/7 venues, 8-hour shifts.

Owner rulings 2026-08-20: venues never close (a global playerbase
must never find shops shut) and shifts run eight hours — day (06-14),
swing (14-22), night (22-06). Every registered venue converts to the
slot model: its current keeper takes the shift that fits their life,
their blueprint attaches to THEIR slot, and the remaining slots open
VACANT with grace served — the succession watcher and the population
keeper will staff the colony's ~dozen new night and swing jobs one
arrival at a time. The employment boom is the plan: open jobs pull
arrivals, arrivals earn wages, wages lower the poverty index, and the
shuttle starts sending seekers instead of knives.

Idempotent: slot conversion re-mirrors; schedules re-assert.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/078_shift_slots.py
"""

from evennia.utils.search import search_object

ALL_SHIFTS = ("day", "swing", "night")

#: fixture ref -> (keeper's shift, keeper dbref, blueprint, open shifts)
#: STREET FOOD keeps hours (owner 2026-08-20: the culinary mosaic IS
#: the content — Lin's morning noodles, Ottilie's evening cuts, future
#: carts claiming other hours); STATIC LOCALES run 24/7.
CONVERSIONS = [
    ("#7530", "day", "#8284", "vendor_lin", ("day",)),          # Lin's cart
    ("#5221", "swing", "#5222", "butcher_ottilie", ("swing",)), # Ottilie
    ("#5484", "day", "#5624", "tobacconist_bellows", ALL_SHIFTS),  # Bellows
    ("#5160", "day", "#5161", "merchant_ezra", ALL_SHIFTS),     # Ezra
    ("#8119", "day", None, None, ALL_SHIFTS),                   # shell counter
    ("#8287", "day", "#8288", None, ALL_SHIFTS),                # 24/7 EMS
]

for fix_ref, shift, keeper_ref, blueprint, shifts in CONVERSIONS:
    fixture = next(iter(search_object(fix_ref)), None)
    if fixture is None:
        print(f"  {fix_ref}: MISSING; skipped")
        continue
    keeper = (next(iter(search_object(keeper_ref)), None)
              if keeper_ref else fixture.db.post_keeper)
    if keeper is not None and not keeper.pk:
        keeper = None
    slots = {}
    for s in shifts:
        slots[s] = {"keeper": None, "vacant_since": 1.0}   # grace served
    if keeper is not None:
        slots[shift] = {"keeper": keeper, "vacant_since": None}
        keeper.db.soul_schedule = shift
        fixture.db.post_keeper = keeper
    fixture.db.post_slots = slots
    if blueprint:
        bps = dict(fixture.db.post_blueprints or {})
        bps[shift] = blueprint
        fixture.db.post_blueprints = bps
    manned = [s for s, sl in slots.items() if sl["keeper"]]
    print(f"  {fixture.key}: slots={list(slots)} manned={manned} "
          f"keeper={keeper.key if keeper else None} shift={shift}")

# roomed single-shift posts: re-assert schedules onto the new clock
for npc_ref, shift in (("#8130", "day"),      # Martha, caretaker
                       ("#8261", "day"),      # Noel, kettle day station
                       ("#8286", "day")):     # Jordan follows the counter
    npc = next(iter(search_object(npc_ref)), None)
    if npc is not None and npc.pk:
        npc.db.soul_schedule = shift

# the Kettle hall's night slot (Eli's old post) converts too
hall = next((r for r in search_object("The Kettle - Bath Hall")
             if r.pk and not r.destination), None)
if hall is not None and hall.db.post_role:
    hall.db.post_slots = {"night": {"keeper": None, "vacant_since": 1.0}}
    print(f"  {hall.key}: night slot open (Eli's old shift)")

print("BUILD 078: the tripartite clock is live — open slots will staff "
      "themselves")
