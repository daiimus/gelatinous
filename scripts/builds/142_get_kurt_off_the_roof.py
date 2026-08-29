"""Build 142 — get Kurt off the roof (#2375).

Build 138 ensouled the ambient crowd wherever each body happened to be
standing. One of them, Kurt Ivanov, was on the Queen of Cups lobby roof.

Every exit from that roof is `is_edge` — a drop. The pathfinder refuses
to route a fall ("a drop is never a route"), and Kurt has no
`route_taste`, the dial that lets a courier take awkward ground. So he
was correctly unable to walk anywhere, and just as correctly kept
deciding to go home, because nothing told him not to: a job that faulted
mid-flight did not cool its goal down.

He produced 75 of 120 faults in one window — a soul re-deciding to walk
home every thirty seconds and failing every time.

The loop is fixed in code. This is the one body already in the hole. He
steps off the roof the only way anyone leaves it, into the street the
drops lead to, and re-enters the world walkable.

The rule is NOT relaxed. A soul with no parkour should not fall off a
building; the mistake was ensouling someone up there without checking
they could leave, not the pathfinder refusing to throw them off.

Idempotent: only moves a soul with no walkable exit.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/142_get_kurt_off_the_roof.py
"""

from world.souls.engine import get_souls


def _walkable(room):
    """Exits an ordinary soul may actually use."""
    return [e for e in room.exits
            if not e.db.is_edge and not e.db.is_gap
            and not (e.destination is not None
                     and e.destination.db.is_sky_room is True)]


moved = 0
for soul in get_souls():
    room = soul.location
    if room is None or soul.db.route_taste is not None:
        continue
    if _walkable(room):
        continue
    # Where do the drops lead? That is where they would end up anyway,
    # minus the fall.
    down = next((e.destination for e in room.exits
                 if e.destination is not None), None)
    if down is None:
        print(f"BUILD 142: {soul.key} is stranded in {room.key} with "
              f"nowhere to put them — left alone, needs a builder")
        continue
    soul.move_to(down, quiet=True, move_hooks=False)
    soul.db.soul_job = None
    print(f"BUILD 142: {soul.key} moved off {room.key} -> {down.key}")
    moved += 1

print(f"BUILD 142: moved={moved}")
print("BUILD 142: done")
