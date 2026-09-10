"""Build 161 — clear the garments a stuck wardrobe loop bought (#3169).

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/161_clear_the_trouser_pile.py

DEFAULTS TO A CENSUS. Set PURGE = True to delete.

`#6106 Sam Fukuda` was carrying 628 unworn pairs of trousers, one bought
per planning cycle, none of which could ever go on: his blueprint gives
him layer-5 rubber waders that stop at the thigh, so `groin` stayed
bare, `wardrobe_pressure` sat at 1.0 for good, and the planner — which
refuses to PICK a garment it cannot wear — fell through to the shop
branch every time and bought another.

The loop is closed in code. This is the banked damage.

Deliberately narrow. A garment is removed only if ALL of:

  * its holder is a soul,
  * it is NOT worn,
  * it is wearable (so tools, food and parcels are never touched),
  * its holder carries MORE THAN `KEEP` others with the same key.

`KEEP` copies of each key survive, so a soul who legitimately owns a
spare keeps one. Nothing is deleted from a player.

Re-run-safe: the predicate is a census, so an interrupted run simply
leaves fewer to find next time.

NOT touched: `#5161 Ezra Vantomme`'s 69 undelivered courier parcels.
That is a different unbounded accumulation with a different cause, and
deleting a courier's cargo without understanding why it piled up would
destroy the evidence for it.
"""
import time
from collections import Counter, defaultdict

from django.db.utils import OperationalError

from world.souls.engine import get_souls

PURGE = False          # flip to True to delete
KEEP = 1               # copies of each key a soul may keep


def _surplus(soul):
    """Unworn wearable duplicates beyond `KEEP` of each key."""
    by_key = defaultdict(list)
    for obj in soul.contents:
        check = getattr(obj, "is_wearable", None)
        if not callable(check) or not check():
            continue
        if soul.is_item_worn(obj):
            continue
        by_key[obj.key].append(obj)
    out = []
    for _key, items in by_key.items():
        if len(items) > KEEP:
            out.extend(sorted(items, key=lambda o: o.id)[KEEP:])
    return out


souls = [s for s in get_souls() if s.pk]
print(f"souls: {len(souls)}")
if not souls:
    print("NOTHING TO SCAN. `SOUL_TAG` is a (key, CATEGORY) pair — a tag "
          "read without its category returns nothing and reads exactly "
          "like a clean world.")
else:
    total = 0
    for soul in souls:
        surplus = _surplus(soul)
        if not surplus:
            continue
        total += len(surplus)
        counts = Counter(o.key for o in surplus).most_common(4)
        print(f"    #{soul.id:<6} {soul.key:<22} {len(surplus):>4} surplus "
              f"{counts}")
        if PURGE:
            for obj in surplus:
                # RETRY. Deleting hundreds of rows from a separate
                # process while the server is live hits "database is
                # locked" partway through — the first run of this
                # script died after 366 of 627. Re-running is safe
                # (the predicate is a census), but a run that finishes
                # is better than three that do not.
                for attempt in range(6):
                    try:
                        obj.delete()
                        break
                    except OperationalError:
                        time.sleep(0.4 * (attempt + 1))
    print(f"\nsurplus garments: {total}")
    if PURGE:
        left = sum(len(_surplus(s)) for s in souls)
        print(f"deleted {total}; remaining surplus: {left}")
    else:
        print(f"CENSUS ONLY — set PURGE = True. Keeping {KEEP} of each key.")
