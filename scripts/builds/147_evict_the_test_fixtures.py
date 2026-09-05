"""Build 147 — evict the test fixtures living in production (#2432).

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/147_evict_the_test_fixtures.py
    then a foreground reload.

Eight complete `BaseEvenniaTest` sets -- Room, Room2, Obj, Obj2, Char,
Char2 -- plus the butcher suite's "test cart", created at eight distinct
moments on 2026-08-28 and 2026-08-29. Nothing real is attached to any of
them and no account owns one, but a test suite that can reach production
at all is the actual finding.

THE SET IS BIGGER THAN IT LOOKS. The issue counted 48. The closure is
**80**: each cart holds two "plate of grilled rat chops" (16), and each
Room holds an "out" exit into its Room2 (8). Those are fixture debris
too, and they are the reason the order below matters.

ORDER MATTERS, AND THIS IS WHY. `DefaultObject.delete()` calls
`clear_contents()`, which moves whatever is inside to its HOME -- not to
oblivion. **40 of these 80 are homed to Limbo (#2).** Deleting a cart
before the plates inside it would deposit those plates in Limbo, which is
precisely how Limbo acquired 634 orphans earlier in this project's
history. So this deletes leaves first: plates, then the objects that held
them, then exits, then rooms. By the time a container is deleted it is
already empty and `clear_contents` has nothing to relocate.

The Limbo population is counted before and after and the run ABORTS if it
moves. A cleanup that grows Limbo has failed, whatever else it achieved.

HOW THEY GOT THERE -- narrowed, not solved. `evennia test` is safe: this
session ran the suite over twenty times against this container and
created ZERO fixtures (verified by `db_date_created`; newest fixture is
still 2026-08-29 20:46). That rules out the normal path empirically
rather than by reading the runner class. What does write to production is
`evennia shell`, and 166 test modules use a bare `unittest.TestCase` with
no Django DB isolation -- so importing or driving one from a shell lands
straight in the live database. Consistent with the evidence; not proven
for these particular rows.

Re-run-safe: finds nothing and exits.
"""
from evennia.objects.models import ObjectDB

FIXTURE_KEYS = {"Room", "Room2", "Obj", "Obj2", "Char", "Char2", "test cart"}
LIMBO_ID = 2


def _closure():
    core = [o for o in ObjectDB.objects.all() if o.key in FIXTURE_KEYS]
    ids = {o.id for o in core}
    debris = [
        o for o in ObjectDB.objects.all()
        if o.id not in ids
        and ((o.location and o.location.id in ids)
             or (o.destination and o.destination.id in ids))
    ]
    found = {o.id: o for o in core}
    for o in debris:
        found[o.id] = o
    return found


def _limbo_count():
    limbo = ObjectDB.objects.filter(id=LIMBO_ID).first()
    return len(limbo.contents) if limbo else None


def main():
    found = _closure()
    if not found:
        print("BUILD 147: no test fixtures present; nothing to do.")
        return
    print(f"BUILD 147: {len(found)} fixture objects in the closure")

    # Refuse if anything real has attached itself since the audit.
    attached = [
        (o.id, o.key) for o in ObjectDB.objects.all()
        if o.id not in found
        and ((o.location and o.location.id in found)
             or (o.home and o.home.id in found)
             or (o.destination and o.destination.id in found))
    ]
    if attached:
        print(f"BUILD 147: ABORT — real objects attached: {attached}")
        return
    owned = [(o.id, o.key) for o in found.values() if o.db_account]
    if owned:
        print(f"BUILD 147: ABORT — an account owns one of these: {owned}")
        return

    before = _limbo_count()
    print(f"BUILD 147: Limbo holds {before} before")

    # Leaves first. Anything still holding something is deferred to a
    # later pass, so no delete ever has contents to relocate.
    remaining = dict(found)
    deleted = 0
    failed = []
    while remaining:
        leaves = [o for o in remaining.values()
                  if not [c for c in o.contents if c.id in remaining]]
        if not leaves:
            print(f"BUILD 147: ABORT — {len(remaining)} left in a "
                  f"containment cycle: {sorted(remaining)}")
            return
        for obj in leaves:
            oid, key = obj.id, obj.key
            del remaining[oid]
            try:
                obj.delete()
            except Exception as err:  # noqa: BLE001
                # REPORTED, never swallowed. The first live run of this
                # stopped after 48 of 80 and a second run finished the
                # job -- re-run safety covered it, but only because the
                # output was being filtered did the stop go unnoticed at
                # the time. A partial pass has to be loud.
                failed.append((oid, key, f"{type(err).__name__}: {err}"))
                print(f"BUILD 147:   FAILED #{oid} {key}: {err}")
                continue
            deleted += 1
            print(f"BUILD 147:   deleted #{oid} {key}")

    after = _limbo_count()
    print(f"BUILD 147: deleted {deleted}; Limbo holds {after} after")
    still = _closure()
    if still or failed:
        print(f"BUILD 147: INCOMPLETE — {len(still)} still present, "
              f"{len(failed)} failed to delete: {failed}")
        print("BUILD 147: re-run; this build is idempotent.")
    if before != after:
        print("BUILD 147: WARNING — Limbo population MOVED. Investigate; "
              "contents were relocated rather than removed.")
    else:
        print("BUILD 147: Limbo unchanged, as required.")


main()
