"""Build 133 — the Community Thrift actually opens (#2314).

The room was written for a shop that has OPENED -- "the roll-shutter is
up for the first time in years", the TO LET card turned over and
marked TAKE WHAT YOU NEED -- behind a shutter that was still down. Both
exits carried `traverse:false()` and an authored refusal:

    "The roll-shutter is down and padlocked, a TO LET card yellowing
     behind the grille."

So the interior said open and the door said closed, and the door won.
Nobody but a superuser had ever been inside, which is why it went
unnoticed: quelled, it refuses; unquelled, it lets you straight in.

The stock is real -- a ShopContainer with infinite inventory at zero
markup, every garment priced 0 -- so souls that arrive actually get
clothed rather than failing one step later.

Consequence, recorded deliberately: this becomes the best AND free
clothing in the colony (0.95 against Ramirez's 0.8, which charges).
Wardrobe stops being an economic pressure. That is the owner's call
and is the point of a thrift.

Idempotent.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/133_the_thrift_opens.py
"""

from evennia.utils.search import search_object

DOORS = ("#5461", "#5462")      # Kaspar St -> Thrift, and back

for ref in DOORS:
    ex = next(iter(search_object(ref)), None)
    if ex is None:
        print(f"BUILD 133: {ref} is gone; skipped")
        continue
    if ex.locks.get("traverse") == "traverse:all()":
        print(f"BUILD 133: {ex.key} from {ex.location.key} already open")
    else:
        ex.locks.replace("traverse:all()")
        print(f"BUILD 133: {ex.key} from {ex.location.key} -> open")
    # the padlock line is now a lie; the shutter is up in the prose
    if ex.attributes.has("err_traverse"):
        ex.attributes.remove("err_traverse")
        print(f"BUILD 133:   removed the padlock refusal")

# Prove it for somebody who is NOT a superuser -- the whole reason this
# went unseen. Wren is an ordinary Character and answers honestly.
from world.souls import posts as posts_mod
from world.spatial.pathfind import find_path
from world.souls import actions
w = posts_mod._living_body("rabbit_wren")
thrift = next(iter(search_object("#5297")), None)
if w is not None and thrift is not None:
    ex = next(iter(search_object("#5461")), None)
    print(f"BUILD 133: ordinary character may traverse: "
          f"{ex.access(w, 'traverse')}")
    path = find_path(w.location, thrift, traverser=w)
    print(f"BUILD 133: a soul can now route there: "
          f"{len(path) if path else 'NO PATH'} rooms")
    opts = actions._advertisers(w, "wardrobe")
    if opts:
        score, fixture, room = opts[0]
        print(f"BUILD 133: best clothing in the colony is now "
              f"{room.key} ({fixture.key}) at {score:.3f}")
