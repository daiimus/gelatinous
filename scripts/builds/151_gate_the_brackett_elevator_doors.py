"""Retypeclass the eight ungated Brackett elevator doors (#2610).

The doors-are-shut rule lives in `ElevatorDoorExit.at_traverse`. The
Brackett Arms landings for floors 8-15 carried plain
`typeclasses.exits.Exit` objects whose destination is the car, so
walking `elevator` from any of them put the player inside the car
wherever it happened to be. Verified live across all 14 floors: floors
2-7 gated, 8-15 not.

The build script that made them (`009_brackett_setback.py`) used the
generic `EXIT_TC`; the earlier floors were fixed afterwards and these
were missed.

Idempotent: only exits whose destination is an `ElevatorCar` and whose
typeclass is not already `ElevatorDoorExit` are touched. Aliases are
re-asserted afterwards because `at_object_creation` — which adds `in` —
does not re-run on a swap.
"""
from evennia.objects.models import ObjectDB

from typeclasses.elevator import ElevatorCar, ElevatorDoorExit

TARGET = "typeclasses.elevator.ElevatorDoorExit"

cars = [o for o in ObjectDB.objects.all() if isinstance(o, ElevatorCar)]
print(f"cars: {len(cars)}")

converted = 0
for obj in ObjectDB.objects.all():
    dest = getattr(obj, "destination", None)
    if dest is None or not any(dest == car for car in cars):
        continue
    if isinstance(obj, ElevatorDoorExit):
        continue
    where = getattr(obj.location, "key", "?")
    obj.swap_typeclass(TARGET, clean_attributes=False,
                       run_start_hooks=None)
    if "in" not in [str(a) for a in obj.aliases.all()]:
        obj.aliases.add("in")
    converted += 1
    print(f"  gated: {where} / {obj.key}")

print(f"converted: {converted}")

# Verify: no ungated door into any car remains.
remaining = [
    o for o in ObjectDB.objects.all()
    if getattr(o, "destination", None) is not None
    and any(o.destination == car for car in cars)
    and not isinstance(o, ElevatorDoorExit)
]
print(f"ungated remaining: {len(remaining)}")
