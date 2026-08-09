"""Build 033 — dress the Marlowe Lot on the atlas (P4).

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/033_crane_atlas_skins.py
    then a foreground reload.

Skins the crane rooms with the new sprite family: the fenced dig at
street level, the Boiler Run mast climbing to the cab, and the Longhaul
container (which renders at whatever floor it's currently hung — the
room really moves, so the map stays honest for free). Data-only,
re-run-safe.
"""
from evennia.objects.models import ObjectDB
from world.spatial import get_xyz


def at(xyz):
    return next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
                 if r.destination is None and get_xyz(r) == xyz), None)


n = 0

# ground: hoarding / crane base / rebar dig
GROUND = {(-1, -19, 0): "crane_lot", (-1, -18, 0): "crane_base",
          (-1, -17, 0): "crane_dig"}
for xyz, skin in GROUND.items():
    r = at(xyz)
    if r is not None:
        r.db.atlas_skin = skin
        n += 1

# the mast: z1..z16 lattice, z17 the cab
for z in range(1, 17):
    r = at((-1, -18, z))
    if r is not None:
        r.db.atlas_skin = "crane_mast"
        n += 1
cab = at((-1, -18, 17))
if cab is not None:
    cab.db.atlas_skin = "crane_cab"
    n += 1

# the container: skin the movable car itself (renders at its live z)
car = ObjectDB.objects.filter(
    db_typeclass_path="typeclasses.rooms.CraneContainer").first()
if car is not None:
    car.db.atlas_skin = "crane_container"
    n += 1

print(f"BUILD 033: {n} crane cells skinned "
      f"(car #{car.id if car else '?'} @ {get_xyz(car) if car else '?'}).")
