"""Build 158 — re-roll look_places that name scenery the room may not have.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/158_flavour_that_travels.py
    then a foreground reload.

The catalogues carried `look_place` lines naming interior scenery --
ceilings, doorways, "the room", baseboards -- and a `look_place` travels
with the PERSON. Six NPCs standing on streets were described as lying on
the floor staring at the ceiling (#2733).

The catalogues are fixed, which governs new draws. A line already
written onto a body stays until re-rolled.

Also re-rolls any body whose stored abdomen prose claims a starved
abdomen while the body is heavyset or stocky -- the untagged line from
the same issue.

METHOD TRAP, recorded because it cost the original probe a false clean:
`look_place` and `longdesc` live under CATEGORIES (`description` and
`appearance`). Reading either without its category returns None.

Re-run-safe: a body whose stored prose is already clean is skipped.
"""
import re

from evennia.objects.models import ObjectDB

from world.mob_flavor import random_longdesc, random_look_place

INTERIOR = re.compile(r"\b(ceiling|ceilings|doorway|doorways|baseboard|"
                      r"baseboards)\b|\bthe room\b", re.I)
STARVED = "concave enough to suggest several missed meals"
FULL_BUILDS = {"heavyset", "stocky"}

PLACES = 0
BELLIES = 0

for obj in ObjectDB.objects.all():
    species = getattr(obj.db, "species", None) or "human"

    place = obj.attributes.get("look_place", category="description")
    if isinstance(place, str) and INTERIOR.search(place):
        for _try in range(12):
            candidate = random_look_place(species=species)
            if candidate and not INTERIOR.search(candidate):
                print(f"  #{obj.id} {obj.key!r} look_place:")
                print(f"      was: {place[:64]}")
                print(f"      now: {candidate[:64]}")
                obj.attributes.add("look_place", candidate,
                                   category="description")
                PLACES += 1
                break

    longdesc = obj.attributes.get("longdesc", category="appearance")
    build = getattr(obj, "build", None)
    if longdesc and build in FULL_BUILDS:
        belly = str((longdesc or {}).get("abdomen") or "")
        if STARVED in belly:
            for _try in range(12):
                candidate = random_longdesc("abdomen", species=species,
                                            sex=getattr(obj, "sex", None),
                                            build=build)
                if candidate and STARVED not in str(candidate):
                    print(f"  #{obj.id} {obj.key!r} ({build}) abdomen:")
                    print(f"      was: {belly[:64]}")
                    print(f"      now: {str(candidate)[:64]}")
                    longdesc["abdomen"] = candidate
                    obj.attributes.add("longdesc", longdesc,
                                       category="appearance")
                    BELLIES += 1
                    break

print(f"\nlook_places re-rolled: {PLACES}   abdomens re-rolled: {BELLIES}")
