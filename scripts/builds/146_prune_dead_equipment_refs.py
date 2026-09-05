"""Build 146 — prune dead references out of held_items / worn_items (#2467).

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/146_prune_dead_equipment_refs.py
    then a foreground reload.

#2468 gave `Character` the invariant it never had: anything leaving a body
now releases its hand and clothing slots, whether it moves, is deleted, or
goes out through a `move_hooks=False` path that releases by hand. That stops
NEW drift.

It does not clear the drift already banked. `release_slots` prunes empty
slots as it goes, so a body repairs itself the next time ANYTHING leaves it
-- but a body whose only bad slot is a dead reference may never be touched
again. That is the gap this build closes, and it is why the fix alone was
not the whole of #2467.

WHAT THIS DOES. Calls `release_slots` on every character with a sentinel
they cannot be holding, which prunes slots holding nothing without
disturbing live ones. Deliberately the same code path #2468 tests rather
than a second walker over packed tuples: a bespoke prune here would be one
more door onto the decision, and this one has tests.

Dead references are invisible to a plain read -- `deserialize` renders them
as `None`, which is why they read as free hands and why two earlier sweeps
for them returned zero. The count below is taken by walking the packed
`__packed_dbobj__` tuples against the live id set, which is the only method
that sees them.

Re-run-safe: a body with nothing to prune is not written.
"""
from evennia.objects.models import ObjectDB
from evennia.typeclasses.models import Attribute

_NEVER_HELD = object()


def _dead_ref_count():
    """Dead object references under the two equipment ledgers."""
    live = set(ObjectDB.objects.values_list("id", flat=True))
    found = 0

    def walk(value):
        nonlocal found
        if isinstance(value, tuple) and len(value) > 3 and value[0] == "__packed_dbobj__":
            if value[3] not in live:
                found += 1
        elif isinstance(value, (list, tuple)):
            for item in value:
                walk(item)
        elif isinstance(value, dict):
            for item in value.values():
                walk(item)

    for attr in Attribute.objects.filter(db_key__in=("held_items", "worn_items")):
        try:
            walk(attr.db_value)
        except Exception:  # noqa: BLE001 — a malformed row is not a reason to stop
            continue
    return found


def main():
    before = _dead_ref_count()
    print(f"BUILD 146: dead equipment references before: {before}")

    touched = 0
    for obj in ObjectDB.objects.all():
        release = getattr(obj, "release_slots", None)
        if not callable(release):
            continue
        held_was = dict(obj.held_items or {})
        worn_was = dict(obj.worn_items or {})
        release(_NEVER_HELD)
        if dict(obj.held_items or {}) != held_was or dict(obj.worn_items or {}) != worn_was:
            touched += 1
            print(f"BUILD 146:   pruned {obj.id} {obj.key[:28]}")

    after = _dead_ref_count()
    print(f"BUILD 146: bodies repaired: {touched}")
    print(f"BUILD 146: dead equipment references after: {after}")


main()
