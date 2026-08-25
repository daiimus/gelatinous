"""Build 127 — designate the recovery bay (#2282).

A recovery detail needs somewhere to take a casualty. The destination
is TAG-driven rather than hardcoded, so a builder can move the precinct
without editing code; this tags the room the force already works out
of.

The Secure Corridor is the right room and not an arbitrary one: the
charging cradles are there, the service bench is there, and Marisol,
Tuck and Halina stand their shifts at it. A unit dragged home arrives
exactly where the person who can rebuild it is standing.

Idempotent.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/127_somewhere_to_bring_it.py
"""

from evennia.utils.search import search_object

from world.souls.actions import RECOVERY_TAG, recovery_bay

BAY = "#4960"          # Colonial Constabulary Secure Corridor

room = next(iter(search_object(BAY)), None)
if room is None:
    print("BUILD 127: the secure corridor is gone; aborted")
    raise SystemExit

if room.tags.get(RECOVERY_TAG[0], category=RECOVERY_TAG[1]):
    print(f"BUILD 127: {room.key} is already the recovery bay")
else:
    room.tags.add(RECOVERY_TAG[0], category=RECOVERY_TAG[1])
    print(f"BUILD 127: {room.key} #{room.id} designated the recovery bay")

# Prove a unit would actually find it, rather than trusting the tag.
from evennia.objects.models import ObjectDB
unit = next((o for o in ObjectDB.objects.filter(
    db_attributes__db_key="role").distinct() if o.db.role == "security"), None)
if unit is not None:
    found = recovery_bay(unit)
    print(f"BUILD 127: a unit would deliver to "
          f"{found.key if found else 'NOWHERE'}")
    print(f"BUILD 127: the bench is in that room: "
          f"{any(getattr(o.db, 'is_service_bench', None) for o in (found.contents if found else []))}")
