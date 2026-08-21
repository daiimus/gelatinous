"""Build 104 — Nonna keeps hours like everyone else (#2146).

Giving her the day slot was only half a fix: she had no soul, so she
had no schedule, no home, and nowhere to be. She stood at her counter
at every hour of the day and night, which is why the yard looked open
when it wasn't, and why she was still there at 14:00 holding a shift
that ended at 14:00.

This is the population merge applied to one person — and she is the
clearest argument for it. An authored NPC without a soul is furniture
with a face: it cannot go home, cannot get hungry, cannot be missed.

She gets a cube through the real kiosk like every other resident, the
day shift she has presumably worked for thirty years, and the wage her
own till pays. She is also marked Essential, so a woman with a creed
burned into her counter cannot be deleted by an ordinary bad night.

Idempotent.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/104_ensoul_nonna.py
"""

from evennia.utils.search import search_object

from world import rental
from world.souls import engine

COUNTER = "#8119"
OWNER = "#8120"
KIOSK = "#5640"

counter = next(iter(search_object(COUNTER)), None)
nonna = next(iter(search_object(OWNER)), None)
kiosk = next(iter(search_object(KIOSK)), None)

if counter is None or nonna is None:
    print("BUILD 104: counter or proprietor missing; aborted")
elif nonna.tags.get(engine.SOUL_TAG[0], category=engine.SOUL_TAG[1]):
    print("BUILD 104: Nonna already has a soul; skipped")
else:
    home = rental.residence_of(nonna)
    if home is None and kiosk is not None:
        try:
            rental.assign_cube(nonna, kiosk)
            home = rental.residence_of(nonna)
        except Exception as err:      # noqa: BLE001 — housed or not, she works
            print(f"BUILD 104: no cube for her ({err})")

    nonna.db.is_npc = True
    nonna.db.essential = True         # authored, and not disposable
    engine.ensoul(nonna, role="snailer", home=home,
                  post=counter.location, schedule="day",
                  wage_rate=0.02, venue=counter)

    slots = dict(counter.db.post_slots or {})
    slots["day"] = {"keeper": nonna, "vacant_since": None}
    counter.db.post_slots = slots
    counter.db.post_keeper = nonna

    print(f"BUILD 104: {nonna.key} ensouled — day shift at "
          f"{counter.location.key}, home {home.key if home else 'none'}; "
          f"she can go home now")
