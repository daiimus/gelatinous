"""Build 155 — drop stale names from living bodies' `removed_organs`.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/155_refilled_slots_are_not_removed_slots.py
    then a foreground reload.

`db.removed_organs` was append-only: harvest added a name and nothing
took one off. `MedicalState.full_heal` reads it as "this slot is empty
now" (#3047), so once a surgeon installed a replacement the new organ
could never be healed by any path through `full_heal`.

The install resolvers now clear the name as they seat the organ, which
stops NEW drift. It does not clear what is already banked -- the same
shape as build 146 for #2467 and build 154 for #3087.

Measured before this ran:

    Laszlo XLIV       #2017  left_eye   10/10
    Laszlo XLIV       #2017  right_eye  10/10
    Jericho Black III #2967  heart      19/20   <- could not be healed

CORPSES ARE LEFT ALONE. A corpse's `removed_organs` is a HISTORICAL
record of what was taken out of it -- that is exactly what forensics
(`world/forensics.py`) and the repeat-harvest gate read it for, and it
is correct there. Only a LIVING body's list doubles as a claim about
current anatomy.

WHAT THIS DOES. For each living body, drops any name whose organ is
present in the medical state and is not itself flagged
`injury_type="harvested"`. An organ that really was harvested and never
replaced keeps its entry, so #3047's guard is untouched.

Re-run-safe: a body with nothing stale is not written.
"""
from evennia.objects.models import ObjectDB

from typeclasses.corpse import Corpse

CHANGED = 0
BODIES = 0

for obj in ObjectDB.objects.all():
    removed = list(getattr(obj.db, "removed_organs", None) or ())
    if not removed or isinstance(obj, Corpse):
        continue
    state = getattr(obj, "medical_state", None)
    organs = getattr(state, "organs", None) if state is not None else None
    if not organs:
        continue
    keep = []
    dropped = []
    for name in removed:
        organ = organs.get(name)
        if organ is not None and getattr(organ, "injury_type", None) != "harvested":
            dropped.append(name)
        else:
            keep.append(name)
    if not dropped:
        continue
    BODIES += 1
    CHANGED += len(dropped)
    print(f"  #{obj.id} {obj.key!r}: dropping {dropped} (keeping {keep})")
    obj.db.removed_organs = keep
    try:
        obj.save_medical_state()
    except Exception:  # noqa: BLE001 — the list is the record; state is a courtesy
        pass

print(f"\nbodies repaired: {BODIES}   stale names dropped: {CHANGED}")
