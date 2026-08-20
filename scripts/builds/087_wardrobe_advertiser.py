"""Build 087 — the issue dispenser advertises Wardrobe (#2104).

A soul standing anywhere undressed needs somewhere to go. The
Thawn-Harrison dispenser is the colony's free issue, so it is the
advertiser the wardrobe planner walks to. (Buying real clothes at a
shop is the obvious second source and is deliberately not wired yet.)

Idempotent.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/087_wardrobe_advertiser.py
"""

from evennia.utils.search import search_object

room = next(iter(search_object("#1989")), None)
disp = next((o for o in (room.contents if room else ())
             if o.is_typeclass("typeclasses.terminals.SleeveDispenser",
                               exact=False)), None)
if disp is None:
    print("BUILD 087: dispenser not found; aborted")
else:
    ads = dict(disp.db.advertises or {})
    ads["wardrobe"] = 0.9
    disp.db.advertises = ads
    disp.tags.add("advertiser", category="souls")
    print(f"BUILD 087: {disp.key} #{disp.id} advertises wardrobe")
