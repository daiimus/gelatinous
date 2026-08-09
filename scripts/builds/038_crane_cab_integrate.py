"""Build 038 — integrate the crane console and operator's chair.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/038_crane_cab_integrate.py
    then a foreground reload.

Both were created bolted-down but still listed as loose objects in the
cab. Mark them integrate=True with an integration_desc so they read as
part of the room (the base-station + fixture convention), not clutter.
Data-only, re-run-safe.
"""
from evennia.objects.models import ObjectDB
from world.spatial import get_xyz


def at(xyz):
    return next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
                 if r.destination is None and get_xyz(r) == xyz), None)


cab = at((-1, -19, 17))
assert cab is not None, "operator's cab missing at (-1,-19,17)"


def find(key):
    return next((o for o in cab.contents if o.key == key), None)


n = 0
console = find("Boiler Run crane console")
if console is not None:
    console.db.integrate = True
    console.db.integration_desc = (
        "A bolted-down |cBoiler Run crane console|n fills the front of the "
        "cab — a bank of levers worn to bare metal and a fixed transceiver "
        "glowing a steady 27.0, the voice that runs the container.")
    n += 1

chair = find("operator's chair")
if chair is not None:
    chair.db.integrate = True
    chair.db.integration_desc = (
        "A cracked vinyl |coperator's chair|n is bolted to the cab floor "
        "before the levers, worn into the shape of whoever works them.")
    n += 1

print(f"BUILD 038: integrated {n} cab fixtures "
      f"(console #{console.id if console else '?'}, "
      f"chair #{chair.id if chair else '?'}).")
