"""Build 156 — stamp `filled_once` on every existing cigarette pack.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/156_packs_remember_they_were_filled.py
    then a foreground reload.

`_ensure_correct_fill` used to refill ANY empty pack on a look, because
"empty" cannot tell "never filled" -- the #2935 migration case -- from
"a player smoked them all". A pack emptied without firing the crush
hook refilled itself every time somebody looked at it.

The fix remembers the fill in `db.filled_once`. Packs made before that
carry no marker, so each would still be handed one free refill.

The migration #2935 exists for has demonstrably finished: a sweep of
all 10 live packs found ZERO holding mis-branded cigarettes. So every
pack in the world today has been filled, and can say so.

Pack #4667 is the one this actually matters for -- it sits at 0/10, so
without this build the next person to look at it is given ten
cigarettes.

Re-run-safe: a pack already marked is not written.
"""
from evennia.objects.models import ObjectDB

from typeclasses.smoke import CigarettePack

MARKED = 0
SKIPPED = 0

for obj in ObjectDB.objects.all():
    if not isinstance(obj, CigarettePack):
        continue
    if obj.db.filled_once:
        SKIPPED += 1
        continue
    held = len(obj.contents)
    cap = int(obj.db.capacity or 0)
    print(f"  #{obj.id} {obj.key!r} holding {held}/{cap} -> marked filled")
    obj.db.filled_once = True
    MARKED += 1

print(f"\npacks marked: {MARKED}   already marked: {SKIPPED}")
