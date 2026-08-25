"""Build 129 — Wren, the rabbit (#2258).

`route_taste` has been built and set on nobody since it landed. Its
own docstring names who it was for -- "the courier, the runner, the
burglar" -- and the colony had none of them, so every soul walked the
pavement like an accountant and the whole vertical city was decoration
as far as NPCs were concerned.

Wren is the first traverser with a taste for the awkward way. She runs
packages out of Kaspar Pawn & Salvage to whoever is standing a counter
somewhere else, collects a token on delivery, and comes back to wait.

Deliberate settings:

* `route_taste = 0.2` -- a rooftop costs her 1.2 against a street's
  1.0, so she prefers pavement by a whisker and takes the roofs freely.
  Note the pathfinder clamps at `max(DEFAULT_COST, ...)`: taste can
  never make a roof CHEAPER than the street, only comparable.
* `soul_post` is the room, not a fixture -- Kaspar has a counter but
  nobody keeps it, and her post is the depot rather than the till.
* Day shift only for now. One rabbit, observable, one set of routes to
  watch before there are three.

Idempotent.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/129_the_rabbit.py
"""

from evennia.utils.search import search_object

from world.npcs.blueprints import build_npc
from world.souls import posts as posts_mod

DEPOT = "#5157"          # Kaspar Pawn & Salvage
BP = "rabbit_wren"

depot = next(iter(search_object(DEPOT)), None)
if depot is None:
    print("BUILD 129: the depot is gone; aborted")
    raise SystemExit

existing = posts_mod._living_body(BP)
if existing is not None:
    wren = existing
    print(f"BUILD 129: {wren.key} #{wren.id} already runs")
else:
    wren = build_npc(BP, depot)
    if wren is None:
        print("BUILD 129: could not build the rabbit")
        raise SystemExit
    print(f"BUILD 129: {wren.key} #{wren.id} hired at {depot.key}")

# ENSOUL her, do not hand-set the attributes.
#
# The first version of this build wrote soul_role, soul_post and the
# rest directly -- and left her without the `soul` tag, which is how
# the heartbeat ENUMERATES souls. So she stood at the depot with a
# role, a schedule, a post and a perch, and never thought once. Every
# behaviour written for her was correct code that could not run.
#
# Which is precisely the bug this whole NPC exists to fix: something
# built and never wired. `ensoul` is the seam; use the seam (#2305).
from world.souls.engine import ensoul

ensoul(wren, role="courier", home=wren.db.soul_home or depot, post=depot,
       schedule="day", wage_rate=0.0)   # paid per delivery, not per hour
wren.db.route_taste = 0.2

print(f"BUILD 129: role={wren.db.soul_role} post={wren.db.soul_post.key} "
      f"taste={wren.db.route_taste} shift={wren.db.soul_schedule}")
from world.souls.engine import SOUL_TAG, get_souls
print(f"BUILD 129: ensouled="
      f"{bool(wren.tags.get(SOUL_TAG[0], category=SOUL_TAG[1]))} "
      f"| in the heartbeat roster={wren in get_souls()} "
      f"(without this she never thinks at all)")

# Prove the two things that decide whether she can work at all.
from world.director import courier
from world.spatial.pathfind import _route_cost
dests = courier.runnable_destinations(wren)
print(f"BUILD 129: runs available now: {len(dests)}")
for room, counter, keeper in dests:
    print(f"BUILD 129:   {room.key[:32]:32} till="
          f"{counter.attributes.get('register')} -> {keeper.key}")

class _Roof:
    db = type("d", (), {"type": "rooftop"})()
print(f"BUILD 129: a roof costs her {_route_cost(_Roof(), wren)} "
      f"(an ordinary colonist: {_route_cost(_Roof(), None)})")
