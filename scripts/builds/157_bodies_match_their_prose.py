"""Build 157 — re-roll longdesc slots whose prose contradicts the body.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/157_bodies_match_their_prose.py
    then a foreground reload.

The human catalogue's `chest` and `abdomen` slots were flat lists, so
`_eligible` (which filters on BUILD only) offered sex-specific prose to
every body. Two male NPCs carry a C-section scar and one female NPC
carries chest hair (#2731).

The catalogue is now sex-keyed and the resolver additive, which stops
NEW bodies drawing wrong. It cannot fix a description already written
down -- these three were rolled once and stored.

    #4597  Jerry Lee-Kim   male     abdomen   C-section scar
    #4795  Jason McIntyre  male     abdomen   C-section scar
    #9180  Pia             female   chest     chest hair

Re-rolls ONLY the offending slot, from the now-correct pool, leaving
every other slot on the body untouched -- these are named cast and their
other prose was authored or rolled deliberately.

TWO READ TRAPS, both worth knowing before re-running this:
  * `longdesc` needs its CATEGORY -- `o.attributes.get("longdesc")`
    without `category="appearance"` returns None and reports a false
    clean.
  * `sex` is a PROPERTY. `o.db.sex` is also None.

Re-run-safe: a body whose slot no longer contradicts its sex is skipped.
"""
from evennia.objects.models import ObjectDB

from world.mob_flavor import random_longdesc

MARKERS = {"abdomen": ("c-section", "female"),
           "chest": ("chest hair", "male")}

FIXED = 0
SKIPPED = 0

for obj in ObjectDB.objects.all():
    longdesc = obj.attributes.get("longdesc", category="appearance")
    if not longdesc:
        continue
    sex = getattr(obj, "sex", None)
    if not sex:
        continue
    changed = False
    for slot, (needle, belongs_to) in MARKERS.items():
        text = str((longdesc or {}).get(slot) or "")
        if needle not in text.lower() or sex == belongs_to:
            continue
        species = getattr(obj.db, "species", None) or "human"
        build = getattr(obj, "build", None)
        replacement = None
        for _try in range(12):
            candidate = random_longdesc(slot, species=species,
                                        sex=sex, build=build)
            if candidate and needle not in str(candidate).lower():
                replacement = candidate
                break
        if replacement is None:
            print(f"  #{obj.id} {obj.key!r}: no clean {slot} line found — left alone")
            continue
        print(f"  #{obj.id} {obj.key!r} ({sex}) {slot}:")
        print(f"      was: {text[:66]}")
        print(f"      now: {str(replacement)[:66]}")
        longdesc[slot] = replacement
        changed = True
        FIXED += 1
    if changed:
        obj.attributes.add("longdesc", longdesc, category="appearance")
    else:
        SKIPPED += 1

print(f"\nslots re-rolled: {FIXED}   bodies untouched: {SKIPPED}")
