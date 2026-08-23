"""Build 117 — the emergency board runs three shifts (#2233).

The dispatch post carried one keeper. `swing` and `night` both read
`vacant_since: 1.0` — never filled, not once — so the colony's distress
line answered eight hours in twenty-four and was dark for sixteen.

This builds Kiro Balázs (swing) and Ines Havlicek (night) from their
blueprints and installs them into their slots the same way any keeper
is installed: `_install_keeper` gives them housing off the Brackett
kiosk, ensouls them onto the post with their shift, and records the
slot. No ad-hoc spawning, no hand-set attributes.

It also registers their blueprint keys on the post, so the vacancy
watcher and the resleeve insurance know whose shift each one is — a
blueprint names a PERSON, and without this a dead night keeper would
be replaced by whoever the post could find.

Idempotent, and self-repairing: a keeper who already walks is not
rebuilt, only re-bound if its slot record is wrong.

The post of record is resolved by its TAG, not guessed. Dispatch
registers the ROOM as its post while the crane registers the FIXTURE —
two models — and a first run of this script took the console for the
post and wrote a second, rival set of slots onto it. That is a
split-brain the vacancy watcher would read from whichever object it
happened to be handed, so the script now also scrubs post bookkeeping
off anything that isn't the tagged post.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/117_the_desk_runs_three_shifts.py
"""

from evennia.utils.search import search_object

from world.npcs.blueprints import build_npc
from world.souls import posts as posts_mod

CONSOLE = "#4931"
SHIFTS = (("swing", "dispatch_kiro"), ("night", "dispatch_ines"))

console = next(iter(search_object(CONSOLE)), None)
if console is None:
    print("BUILD 117: the dispatch console is gone; aborted")
    raise SystemExit

# The POST is whatever carries the post tag — never assumed. The console
# is equipment that happens to stand in it.
room = posts_mod._post_room(console)
post = next((p for p in posts_mod.get_posts() if p is room), None)
if post is None:
    print(f"BUILD 117: {room.key} #{room.id} is not a tagged post; aborted")
    raise SystemExit
print(f"BUILD 117: post = {post.key} #{post.id} "
      f"({post.typeclass_path.rsplit('.', 1)[-1]})")

# scrub any rival bookkeeping off the equipment
for attr in ("post_slots", "post_blueprints", "post_keeper", "post_role"):
    if getattr(console.db, attr, None) is not None:
        setattr(console.db, attr, None)
        print(f"BUILD 117: cleared stray {attr} off {console.key}")

# whose shift is whose — the vacancy watcher and the resleeve insurance
# both read this, and a blueprint names a person rather than a role
plans = dict(post.db.post_blueprints or {})
for shift, bp_key in SHIFTS:
    if plans.get(shift) != bp_key:
        plans[shift] = bp_key
        print(f"BUILD 117: {shift} shift -> blueprint {bp_key!r}")
post.db.post_blueprints = plans

for shift, bp_key in SHIFTS:
    slot = (post.db.post_slots or {}).get(shift) or {}
    keeper = slot.get("keeper")
    if keeper is not None and keeper.pk:
        print(f"BUILD 117: {shift} already held by {keeper.key}; skipped")
        continue
    walking = posts_mod._living_body(bp_key)
    if walking is not None:
        # built by an earlier run whose slots went to the wrong object:
        # rebind the record, don't build a twin or re-issue housing
        slots = dict(post.db.post_slots or {})
        slots[shift] = {"keeper": walking, "vacant_since": None}
        post.db.post_slots = slots
        walking.db.soul_post = room
        walking.db.soul_schedule = shift
        print(f"BUILD 117: {walking.key} #{walking.id} already walks — "
              f"re-bound to {shift} on the real post")
        continue

    npc = build_npc(bp_key, room)
    if npc is None:
        print(f"BUILD 117: could not build {bp_key}; skipped")
        continue
    posts_mod._install_keeper(npc, post, room, shift)
    print(f"BUILD 117: {npc.key} #{npc.id} installed on {shift} "
          f"(home {npc.db.soul_home}, schedule {npc.db.soul_schedule})")

print("BUILD 117: the board now reads --")
for shift, slot in sorted((post.db.post_slots or {}).items()):
    who = slot.get("keeper")
    print(f"   {shift:6} {who.key if who is not None else '(vacant)'}")
