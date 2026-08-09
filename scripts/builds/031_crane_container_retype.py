"""Build 031 — the container becomes the moving crane car.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/031_crane_container_retype.py
    then a foreground reload.

Phase 2: retype the parked Longhaul container into CraneContainer and
let its own move_to_level() wire the 2nd-floor dock. Clears the static
boarding exits Build 030 hardcoded first, so there are no duplicates.
Re-run-safe.
"""
from evennia.objects.models import ObjectDB
from world.spatial import get_xyz


def at(xyz):
    return next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
                 if r.destination is None and get_xyz(r) == xyz), None)


car = at((-1, -17, 1))
assert car is not None, "container not found at (-1,-17,1)"
uc = at((-2, -17, 1))
assert uc is not None, "Urgent Care roof (north) missing"

# ---- drop the Build 030 static boarding exits both ways --------------
for room, keys in ((car, ("west", "east")), (uc, ("east", "west"))):
    for e in list(room.exits):
        if e.key in keys and e.destination in (car, uc):
            e.delete()
car.db.crane_exits = []

# ---- retype and let the car wire itself ------------------------------
if car.typeclass_path != "typeclasses.rooms.CraneContainer":
    car.swap_typeclass("typeclasses.rooms.CraneContainer",
                       run_start_hooks="all")
car.db.level = 1
car.move_to_level(1, announce=False)

print(f"BUILD 031: #{car.id} -> {car.typeclass_path}, level={car.db.level}, "
      f"xyz={get_xyz(car)}, exits={[e.key for e in car.exits]}, "
      f"crane_exits={car.db.crane_exits}")
