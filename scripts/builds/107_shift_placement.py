"""Build 107 — you can see who's actually working (#2148).

Now that nobody is described by their trade, the room needs another
way to tell you who is behind the counter and who is merely standing
near it. Their placement line does it: a post authors how its keeper
stands while holding the shift, the work step puts it on, and the
shift release takes it off.

So the yard reads "a wiry woman is behind the shell counter, sleeves
turned back" while she's working, and just "a wiry woman is here"
when she isn't — which is exactly the difference a customer needs to
know, without anyone being labelled.

Idempotent. Only sets lines for posts that don't have one.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/107_shift_placement.py
"""

from evennia.utils.search import search_object

PLACEMENTS = {
    "#8119": "is behind the shell counter, sleeves turned back",
    "#7530": "is working the noodle cart, ladle in hand",
    "#5221": "is working the cart, cleaver within reach",
    "#5484": "is behind the shop counter, stock at their elbow",
    "#5160": "is behind the steel counter, appraising something",
    "#2705": "is working the hull-slab bar",
    "#3069": "is working the backlit bar",
    "#5150": "is working the chain-hoist bar",
}

set_lines = 0
for ref, line in PLACEMENTS.items():
    fixture = next(iter(search_object(ref)), None)
    if fixture is None or not fixture.pk:
        continue
    if fixture.db.post_work_place:
        continue
    fixture.db.post_work_place = line
    set_lines += 1
    print(f"BUILD 107: {fixture.key} — \"{line}\"")

print(f"BUILD 107: {set_lines} posts now show their keeper at work")
