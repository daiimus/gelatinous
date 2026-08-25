"""Build 128 — designate the junkyard (#2284).

    destroyed → remains taken to the constabulary
              → weapon arm module removed
              → disposed of in the junkyard

The spec assumed a junkyard already existed ("Kaspar Salvage / the
scrap yards"). It half did. Kaspar Pawn & Salvage is an INDOOR SHOP --
"a deep, narrow shop... racked here behind scuffed polycarb" -- which
is somewhere you sell a handset, not somewhere you dump a chassis.

The Midden's Middle Yard is the actual place: "Open trodden ground in
the middle of the yard, ringed by heaps taller than a person. A
shopping cart on its side, a car door, and the flat smell of wet iron
over everything." Wet iron is exactly right.

Tag-driven, so this is a builder decision that can move later without
touching code.

Idempotent.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/128_the_midden_takes_the_wrecks.py
"""

from evennia.utils.search import search_object

from world.director.disposal import ARMAMENT, SCRAPYARD_TAG, scrapyard

YARD = "#7487"          # The Midden - Middle Yard

room = next(iter(search_object(YARD)), None)
if room is None:
    print("BUILD 128: the Middle Yard is gone; aborted")
    raise SystemExit

if room.tags.get(SCRAPYARD_TAG[0], category=SCRAPYARD_TAG[1]):
    print(f"BUILD 128: {room.key} is already the junkyard")
else:
    room.tags.add(SCRAPYARD_TAG[0], category=SCRAPYARD_TAG[1])
    print(f"BUILD 128: {room.key} #{room.id} designated the junkyard")

found = scrapyard()
print(f"BUILD 128: a stripped chassis would go to "
      f"{found.key if found else 'NOWHERE'}")

# And confirm the armament this all exists to recover is really an
# organ on a real unit, not an assumption.
from evennia.objects.models import ObjectDB
from world.medical.procedures import get_organ_snapshot
unit = next((o for o in ObjectDB.objects.filter(
    db_attributes__db_key="role").distinct() if o.db.role == "security"), None)
if unit is not None:
    organs = get_organ_snapshot(unit).get("organs") or {}
    seat = (organs.get(ARMAMENT) or {}).get("container")
    print(f"BUILD 128: live units carry {ARMAMENT!r} in the {seat}")
