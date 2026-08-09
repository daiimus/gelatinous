"""Build 034 — move the crane gap into the real leap path.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/034_crane_gap_relocate.py
    then a foreground reload.

The transit sky room was mistakenly parked at (0,-17,12) — over South
Marlowe Street, EAST of the container — while the container's leap
actually goes NORTH to the Queen of Cups rack roof, across the airspace
over Kaspar Street. Relocate it to (-1,-16,13): north of the car, at the
Queen's roofline, the apex of the hop. Matches CraneContainer.SKY. The
container re-reads SKY by coordinate on every move, so once it lives
here the next lift wires the honest arc. Re-run-safe.
"""
from evennia.objects.models import ObjectDB
from world.spatial import get_xyz, set_xyz


def at(xyz):
    return next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
                 if r.destination is None and get_xyz(r) == xyz), None)


NEW = (-1, -16, 13)
sky = at((0, -17, 12)) or at(NEW)
assert sky is not None, "crane gap sky room not found"
set_xyz(sky, *NEW)
sky.key = "Crane Gap (over Kaspar Street)"
sky.db.desc = (
    "Open air north of the crane, level with the Queen of Cups' rack roof "
    "— the half-second the leap from the container lives in, out over "
    "Kaspar Street with the dig waiting far below.")
sky.db.sense_descs = {
    "olfactory": "Cold updraft off the street, diesel and wet concrete.",
    "tactile": "Nothing under you. That's the whole problem.",
    "atmospheric": "The gap between a swinging box and a solid roof."}

# nudge the car through a rewire so any live edge re-reads the new gap
car = ObjectDB.objects.filter(
    db_typeclass_path="typeclasses.rooms.CraneContainer").first()
if car is not None:
    car.move_to_level(car.db.level or 1, announce=False)

print(f"BUILD 034: crane gap #{sky.id} -> {get_xyz(sky)} {sky.key!r}; "
      f"car level={car.db.level if car else '?'} SKY={type(car).SKY if car else '?'}")
