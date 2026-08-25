"""Build 130 — Kaspar answers around the clock (#2297).

The steel counter was a post with one shift filled: Ezra on days, swing
and night vacant since the beginning. That was invisible until the
rabbit arrived, because a shop with nobody in it just looks shut.

It stopped being invisible the moment custody became a chain (#2295).
A depot cannot consign a parcel with nobody behind the counter, so
Wren's shift was silently gated on Ezra's — and any swing or night
rabbit would have stood in an empty shop all night with nothing to
carry.

Two more pawnbrokers, same pattern as the dispatch desk (#2233) and the
service bench (#2261): blueprints in the registry, installed into the
slots the post already declared.

Idempotent.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/130_kaspar_around_the_clock.py
"""

from evennia.utils.search import search_object

from world.npcs.blueprints import build_npc
from world.souls import posts as posts_mod

COUNTER = "#5160"        # the steel counter at Kaspar Pawn & Salvage
SHIFTS = (("swing", "pawn_hollis"), ("night", "pawn_sunny"))

counter = next(iter(search_object(COUNTER)), None)
if counter is None:
    print("BUILD 130: the counter is gone; aborted")
    raise SystemExit
room = counter.location

plans = dict(counter.db.post_blueprints or {})
plans.setdefault("day", "merchant_ezra")
for shift, key in SHIFTS:
    plans[shift] = key
counter.db.post_blueprints = plans

for shift, bp_key in SHIFTS:
    slot = (counter.db.post_slots or {}).get(shift) or {}
    keeper = slot.get("keeper")
    if keeper is not None and keeper.pk:
        print(f"BUILD 130: {shift} already held by {keeper.key}")
        continue
    walking = posts_mod._living_body(bp_key)
    if walking is not None:
        slots = dict(counter.db.post_slots or {})
        slots[shift] = {"keeper": walking, "vacant_since": None}
        counter.db.post_slots = slots
        print(f"BUILD 130: {walking.key} re-bound to {shift}")
        continue
    npc = build_npc(bp_key, room)
    if npc is None:
        print(f"BUILD 130: could not build {bp_key}")
        continue
    posts_mod._install_keeper(npc, counter, room, shift)
    print(f"BUILD 130: {npc.key} #{npc.id} on {shift}")

print("BUILD 130: the counter now reads --")
for shift, slot in sorted((counter.db.post_slots or {}).items()):
    who = slot.get("keeper")
    print(f"   {shift:6} {who.key if who else '(vacant)'}")

# The thing this build exists to unblock: can a consignment be signed
# out right now, whatever the hour?
from world.director import courier
clerk = courier._keeper_in(room)
print(f"BUILD 130: on duty at the counter now: "
      f"{clerk.key if clerk else 'NOBODY'}")
