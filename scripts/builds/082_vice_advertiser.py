"""Build 082 — Cinder & Leaf advertises vice (#2076).

The craving loop's market: souls with an overdue habit (or a grim
enough mood) plan a vice run to the nearest vice advertiser and buy
the cheapest ware carrying their substance, through the same buy/drink
verbs and keeper-hours gate players face. Cinder & Leaf already stocks
the whole shelf; this just hangs the sign the planner can see.

Idempotent: re-runs re-mirror the same values.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/082_vice_advertiser.py
"""

from evennia.utils.search import search_object

COUNTER_ID = "#5484"           # the shop counter, Cinder & Leaf

counter = next(iter(search_object(COUNTER_ID)), None)
if counter is None or not counter.pk:
    print("BUILD 082: Cinder & Leaf counter not found; aborted")
else:
    ads = dict(counter.db.advertises or {})
    ads["vice"] = 0.9
    counter.db.advertises = ads
    counter.tags.add("advertiser", category="souls")
    print(f"BUILD 082: {counter.key} #{counter.id} advertises vice "
          f"({counter.location.key}); wares stand ready")
