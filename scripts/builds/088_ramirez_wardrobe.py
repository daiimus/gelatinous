"""Build 088 — Ramirez sells clothes to the planner (#2106).

The wardrobe planner now has two sources: the free issue dispenser at
Cryogenics and any counter stocking wearable prototypes. Ramirez
Provisions is the colony's clothing shop, so it hangs the sign.

NOTE — prices left untouched on purpose: every ware on this counter is
currently priced 0 (free), which is a data gap the owner should rule
on rather than a builder inventing an economy. The branch works either
way; with 0 prices, souls simply get free clothes at Ramirez.

Idempotent.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/088_ramirez_wardrobe.py
"""

from evennia.utils.search import search_object

counter = next(iter(search_object("#738")), None)
if counter is None or not counter.pk:
    print("BUILD 088: Ramirez counter not found; aborted")
else:
    ads = dict(counter.db.advertises or {})
    ads["wardrobe"] = 0.8      # under the free issue's 0.9; distance decides
    counter.db.advertises = ads
    counter.tags.add("advertiser", category="souls")
    inv = counter.db.prototype_inventory or {}
    free = [k for k, v in inv.items() if not v]
    print(f"BUILD 088: {counter.key} #{counter.id} advertises wardrobe "
          f"({counter.location.key}); {len(inv)} wares, {len(free)} priced 0")
