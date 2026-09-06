"""Build 150 — rebrand the packs that shipped the wrong tobacco (#2430).

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/150_rebrand_the_cigarette_packs.py
    then a foreground reload.

#2430 fixed the CAUSE: `at_object_creation` runs before the spawner
applies prototype attributes, so `_fill_with_cigarettes` read the
defensive defaults and every pack shipped neutral cigarettes. It repairs
itself in `return_appearance`.

That is not enough on its own. Repair-on-look only fires when somebody
looks, and nobody had: 9 of the 10 live packs were still holding
`tobacco_neutral` behind a Noir label after the fix shipped. The PR said
"repairs on the next interaction, no migration", which was true and did
no work. This is the migration.

Calls the same `_ensure_correct_fill()` the look path uses, so there is
one implementation rather than a second one written for the build.

Cigarettes already taken OUT of a pack are somebody's property and are
untouched — only what is still inside is replaced.

Re-run-safe: a correctly branded pack is skipped.
"""
from evennia.objects.models import ObjectDB


def main():
    packs = [o for o in ObjectDB.objects.all()
             if o.attributes.get("cigarette_prototype")]
    print(f"BUILD 150: {len(packs)} packs")

    fixed = clean = failed = 0
    for pack in packs:
        want = str(pack.db.substance or "").lower()
        before = [str(c.db.substance or "").lower() for c in pack.contents]
        if not before or all(s == want for s in before):
            clean += 1
            continue
        ensure = getattr(pack, "_ensure_correct_fill", None)
        if not callable(ensure):
            print(f"BUILD 150:   #{pack.id} has no _ensure_correct_fill; "
                  f"is the fix deployed?")
            failed += 1
            continue
        ensure()
        after = [str(c.db.substance or "").lower() for c in pack.contents]
        ok = bool(after) and all(s == want for s in after)
        fixed += 1 if ok else 0
        failed += 0 if ok else 1
        print(f"BUILD 150:   #{pack.id} {pack.key[:26]:26} "
              f"{len(before)} x {before[0] if before else '-'} -> "
              f"{len(after)} x {after[0] if after else '-'}"
              f"{'' if ok else '   STILL WRONG'}")

    print(f"BUILD 150: {fixed} rebranded, {clean} already correct, "
          f"{failed} failed")

    still = 0
    for pack in ObjectDB.objects.all():
        if not pack.attributes.get("cigarette_prototype"):
            continue
        want = str(pack.db.substance or "").lower()
        kids = [str(c.db.substance or "").lower() for c in pack.contents]
        if kids and not all(s == want for s in kids):
            still += 1
    print(f"BUILD 150: packs still misbranded: {still}")


main()
