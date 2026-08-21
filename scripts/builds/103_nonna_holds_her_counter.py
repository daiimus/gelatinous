"""Build 103 — the proprietor holds her own counter (#2146).

Nonna Escallier was authored as the owner of the Escallier yard: the
creed is burned into her counter's edge, and the shop's own purchase
message says she hands the food over. But the souls succession system
did not know she existed, saw an unheld day slot, and hired Jordan
Esparza into it — so with Nonna standing at her counter the shop
answered "the hand's off shift" and refused to sell.

The rule this settles: a shop's AUTHORED OWNER holds its post. She
takes the day slot she has presumably worked for thirty years; swing
and night stay open for the help she'd hire for the hours she doesn't
work. Jordan is released to take one of the twenty genuinely vacant
shifts elsewhere.

Idempotent.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/103_nonna_holds_her_counter.py
"""

from evennia.utils.search import search_object

COUNTER = "#8119"        # the shell counter
OWNER = "#8120"          # Nonna Escallier

counter = next(iter(search_object(COUNTER)), None)
nonna = next(iter(search_object(OWNER)), None)
if counter is None or nonna is None:
    print("BUILD 103: counter or proprietor missing; aborted")
else:
    slots = dict(counter.db.post_slots or {})
    displaced = (slots.get("day") or {}).get("keeper")
    slots["day"] = {"keeper": nonna, "vacant_since": None}
    counter.db.post_slots = slots
    counter.db.post_keeper = nonna          # legacy mirror + shop messages
    counter.db.owner = nonna

    # whoever was hired into her shift goes back on the market; there are
    # twenty real vacancies and one of them is genuinely his
    if displaced is not None and displaced != nonna and displaced.pk:
        if displaced.db.soul_post == counter.location:
            displaced.db.soul_post = None
            displaced.db.soul_venue = None
        print(f"BUILD 103: released {displaced.key} from a counter that was "
              f"never vacant")

    print(f"BUILD 103: {nonna.key} holds the day slot at {counter.key}; "
          f"swing and night stay open for hired help")
