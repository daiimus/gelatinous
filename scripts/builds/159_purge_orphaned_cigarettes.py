"""Build 159 — purge the cigarettes a deleted pack orphaned into Limbo.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/159_purge_orphaned_cigarettes.py

DEFAULTS TO A CENSUS. It prints what it would remove and removes
nothing. Set PURGE = True to delete.

The leak is closed in `typeclasses/smoke.py` (#2635): a deleted pack now
takes its cigarettes with it. What is left behind is the banked damage --
cigarettes moved to their HOME by `clear_contents()` on every pack
deleted before that fix. A spawned cigarette has no home, so home is
`#2`, and they went to Limbo in exact runs of ten, none ever smoked.

Deliberately narrow. A cigarette is removed only if ALL of:

  * "cigarette" in its key,
  * it sits directly in `#2` -- not in anyone's hands,
  * it has never been smoked (`uses_left` still 6),
  * its home is `#2` too, which is the leak's own signature: a cigarette
    that ARRIVED in Limbo some other way would have a real home.

Anything else in Limbo is reported and left alone. PC sleeve husks in
particular live there BY DESIGN; the Character filter never matches them
and the key filter would not either.

METHOD TRAP, recorded because the first version of this script reported
a clean zero: cigarettes are `typeclasses.items.Item`, NOT a class under
`typeclasses/smoke.py`. Filtering on the typeclass path -- the obvious
move, given the file the bug lives in -- matches nothing at all and
reads exactly like "already cleaned up".
"""
from collections import Counter

from evennia.objects.models import ObjectDB

PURGE = False          # flip to True to delete

limbo = ObjectDB.objects.filter(id=2).first()
if not limbo:
    print("no #2 — nothing to do")
else:
    contents = limbo.contents
    print(f"#2 holds {len(contents)} objects")

    cigs, odd = [], []
    for obj in contents:
        if "cigarette" in (obj.key or "").lower():
            uses = obj.attributes.get("uses_left")
            home_is_limbo = getattr(obj.home, "id", None) == 2
            if uses == 6 and home_is_limbo:
                cigs.append(obj)
            else:
                odd.append((obj, uses, getattr(obj.home, "key", None)))

    print(f"\norphaned, never smoked, homed in #2: {len(cigs)}")
    for key, n in sorted(Counter(c.key for c in cigs).items()):
        print(f"    {n:>4}  {key}")
    print(f"other cigarettes in #2 (LEFT ALONE): {len(odd)}")
    for obj, uses, home in odd[:10]:
        print(f"    #{obj.id} {obj.key!r} uses_left={uses} home={home}")

    if not cigs:
        print("\nNOTHING MATCHED. Before believing that, check the "
              "predicate against a cigarette you know exists — see the "
              "method trap in this file's docstring.")
    elif PURGE:
        for c in cigs:
            c.delete()
        print(f"\ndeleted {len(cigs)}; #2 now holds {len(limbo.contents)}")
    else:
        print("\nCENSUS ONLY — set PURGE = True to delete.")
