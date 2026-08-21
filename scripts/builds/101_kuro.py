"""Build 101 — the free pot at the Escallier Snailery (#2142).

Owner's call, and the gate was already making the argument: ESCARGOT
FOR ALL, on a plank repainted so many times the letters stand proud
of the wood. The yard now serves kuro — a black shell stock made from
the trimmings, the shells and the ones too small to sell, given away
because it costs them nothing to make.

It fixes the money half of the food problem: 71% of the colony is
broke, and until now every calorie in the world had a price. It is
deliberately THIN — enough to get somebody through a night, not
enough to stop them being hungry and poor in the morning.

The yard also goes 24/7 on three eight-hour shifts, consistent with
the standing rule that carts keep hours while static locales don't.
That is three more jobs in a colony with twenty vacant ones and
nobody to take them.

Idempotent.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/101_kuro.py
"""

from evennia.utils.search import search_object

from world.souls.posts import register_post

COUNTER = "#8119"        # the shell counter, Escallier Snailery - Yard

counter = next(iter(search_object(COUNTER)), None)
if counter is None or not counter.pk:
    print("BUILD 101: shell counter not found; aborted")
else:
    inv = dict(counter.db.prototype_inventory or {})
    inv["snail_kuro"] = 0                # free, and bottomless by design
    counter.db.prototype_inventory = inv
    counter.db.is_infinite = True        # the pot is never off the heat

    # three eight-hour shifts, so the yard is open whenever somebody is
    # hungry rather than only when the street is awake
    keeper = (counter.db.post_slots or {}).get("day", {}).get("keeper")
    register_post(counter, role="snailer", schedule="day", wage_rate=0.02,
                  policy="successor", keeper=keeper,
                  shifts=("day", "swing", "night"))

    slots = {sh: (sl.get("keeper").key if sl.get("keeper") else "—")
             for sh, sl in (counter.db.post_slots or {}).items()}
    print(f"BUILD 101: {counter.key} serves kuro (free, thin, bottomless); "
          f"shifts {slots}")
