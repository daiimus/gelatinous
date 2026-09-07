"""Release seats held by bodies that are off the grid (#2579).

`at_post_unpuppet` pulls the body off the grid with a direct
`self.location = None`, so `at_post_move` never fires and the posture it
owns is never cleared. A logged-out character kept `db.posture` and
`db.furniture`, so the seat stayed occupied — the capacity guard counts
them, and `is_restrained()` (a free-action path in the consent gate)
reads `db.furniture`.

**Only characters that are OFF THE GRID.** A seated NPC with no session
is not a bug: the Rook has to be in the broadcast chair to transmit, and
is deliberately left alone.
"""
from evennia.objects.models import ObjectDB

from typeclasses.characters import Character

fixed = 0
skipped = []
for obj in ObjectDB.objects.all():
    if not isinstance(obj, Character):
        continue
    holding = obj.db.furniture is not None or (
        obj.db.posture and obj.db.posture != "standing")
    if not holding:
        continue
    if obj.location is not None:
        skipped.append((obj.id, str(obj.key),
                        str(getattr(obj.db.furniture, "key", None))))
        continue
    seat = getattr(obj.db.furniture, "key", None)
    obj._clear_posture()
    fixed += 1
    print(f"  stood up: {obj.key} (was {obj.db.posture!r} on {seat!r})")

print(f"released: {fixed}")
for row in skipped:
    print(f"  left seated (on-grid, deliberate): {row}")
