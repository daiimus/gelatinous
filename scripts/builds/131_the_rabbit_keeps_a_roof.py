"""Build 131 — Wren keeps a roof (#2299).

`off_duty` exists because "nobody stays at work for want of a reason to
leave" — the shopkeeper loitering behind her own counter for the seven
hours between the end of her day and the start of her sleep. For a
rabbit, the reason to leave is a roof.

So the perch needs no new goal, no timer and no randomness. She is up
there between clocking off and getting tired, and when rest finally
bites it is a band-2 schedule goal against off_duty's band 4 — the
tree sends her home to bed like everybody else.

The roof chosen is the Last Shift's, which is the point: it is a
rooftop she can only reach by being the kind of traverser who takes
rooftops. An ordinary colonist pays 6.0 to cross one; she pays 1.2.

Idempotent.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/131_the_rabbit_keeps_a_roof.py
"""

from evennia.utils.search import search_object

from world.souls import posts as posts_mod

PERCH = "#6043"          # The Last Shift - Rooftop

wren = posts_mod._living_body("rabbit_wren")
if wren is None:
    print("BUILD 131: no rabbit to give a roof to; aborted")
    raise SystemExit

roof = next(iter(search_object(PERCH)), None)
if roof is None:
    print("BUILD 131: that roof is gone; aborted")
    raise SystemExit

wren.db.soul_perch = roof
print(f"BUILD 131: {wren.key} keeps {roof.key} (#{roof.id})")

# Prove she can actually get there, and that it is the kind of trip
# only she would make.
from world.spatial.pathfind import find_path
from world.souls import actions
for who, label in ((wren, wren.key), (None, "an ordinary colonist")):
    try:
        path = find_path(wren.db.soul_post, roof, traverser=who)
        print(f"BUILD 131: route for {label}: "
              f"{len(path) if path else 'NO PATH'} rooms")
    except Exception as exc:
        print(f"BUILD 131: route for {label}: {type(exc).__name__}")

job = actions.plan_for(wren, "off_duty")
print(f"BUILD 131: off shift she heads for "
      f"{'the roof' if job and job['steps'][0]['room'] == roof.id else job}")
