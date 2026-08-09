"""Build 035 — the crane's hoist cable, hanging dynamically.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/035_crane_cable_shaft.py
    then a foreground reload.

The container hung with nothing connecting it to the jib. Fill the
container's shaft column (-1,-17) z2..z16 with "In the Air" SkyRooms so
there are cells to dress, then let the car's own _skin_column paint the
cable: hoist line in the cells ABOVE the car, open air at and below it.
Re-running move_to_level does the initial paint; it re-paints on every
future lift, so the chain follows the box. Re-run-safe.
"""
from evennia import create_object
from evennia.objects.models import ObjectDB
from world.spatial import get_xyz

SKY_TC = "typeclasses.rooms.SkyRoom"
COL = (-1, -17)


def at(xyz):
    return next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
                 if r.destination is None and get_xyz(r) == xyz), None)


made = 0
# z2..z16: the shaft the container rides (z1 is the dock — the car lives
# there when parked, so no separate air cell needed).
for z in range(2, 17):
    if at((COL[0], COL[1], z)) is not None:
        continue
    r = create_object(SKY_TC, key="In the Air")
    r.db.xyz = (COL[0], COL[1], z)
    r.db.type = "sky"
    r.db.is_sky_room = True
    r.db.outside = True
    r.db.desc = ("Open air in the crane's shaft over the Marlowe Lot — the "
                 "hoist cable sings somewhere above or below, and the dig "
                 "waits at the bottom.")
    made += 1

# paint the cable off the car's current level
car = ObjectDB.objects.filter(
    db_typeclass_path="typeclasses.rooms.CraneContainer").first()
if car is not None:
    car.move_to_level(car.db.level or 1, announce=False)
    chained = [get_xyz(r)[2] for r in ObjectDB.objects.filter(
                   db_typeclass_path=SKY_TC)
               if (get_xyz(r) or (0, 0, 0))[:2] == COL
               and r.db.atlas_skin == "crane_chain"]
    print(f"BUILD 035: +{made} shaft cells; car@z{car.db.level}; "
          f"cable at z{sorted(chained)}.")
else:
    print(f"BUILD 035: +{made} shaft cells; NO CAR FOUND.")
