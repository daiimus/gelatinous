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

Idempotent: a slot with a living keeper is left alone.

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

room = posts_mod._post_room(console)
print(f"BUILD 117: post = {room.key} #{room.id}")

# whose shift is whose — the vacancy watcher and the resleeve insurance
# both read this, and a blueprint names a person rather than a role
plans = dict(console.db.post_blueprints or {})
for shift, bp_key in SHIFTS:
    if plans.get(shift) != bp_key:
        plans[shift] = bp_key
        print(f"BUILD 117: {shift} shift -> blueprint {bp_key!r}")
console.db.post_blueprints = plans

for shift, bp_key in SHIFTS:
    slot = (console.db.post_slots or {}).get(shift) or {}
    keeper = slot.get("keeper")
    if keeper is not None and keeper.pk:
        print(f"BUILD 117: {shift} already held by {keeper.key}; skipped")
        continue
    if posts_mod._living_body(bp_key) is not None:
        print(f"BUILD 117: {bp_key} already walks; skipped")
        continue

    npc = build_npc(bp_key, room)
    if npc is None:
        print(f"BUILD 117: could not build {bp_key}; skipped")
        continue
    posts_mod._install_keeper(npc, console, room, shift)
    print(f"BUILD 117: {npc.key} #{npc.id} installed on {shift} "
          f"(home {npc.db.soul_home}, schedule {npc.db.soul_schedule})")

print("BUILD 117: the board now reads --")
for shift, slot in sorted((console.db.post_slots or {}).items()):
    who = slot.get("keeper")
    print(f"   {shift:6} {who.key if who is not None else '(vacant)'}")
