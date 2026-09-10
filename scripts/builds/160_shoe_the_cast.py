"""Build 160 — put shoes on the cast that shipped without any (#2705).

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/160_shoe_the_cast.py

DEFAULTS TO A CENSUS. Set DRESS = True to actually dress them.

`OUTFIT_SLOTS` — a torso piece, a leg piece, footwear — was declared in
`world/souls/population.py` and read by the generated-arrival dresser
alone. Blueprints never consulted it, so the rule governed procedural
residents and not the named cast. That is fixed in code; this is the
banked damage, which a code fix cannot reach.

METHOD TRAP, recorded because it cost the original probe its first
answer: worn state lives in the `worn_items` AttributeProperty on the
CHARACTER, keyed by body location. There is no per-item `db.worn` flag
— zero such rows exist in the database — and a probe that read one
reported all 78 souls as naked.

Robots are bare on purpose and are skipped, which is most of the
difference between the 20 uncovered souls and the 12 that matter.
"""
from world.souls.engine import get_souls
from world.souls.population import (
    OUTFIT_SLOTS, ensure_outfit_complete, missing_outfit_slots,
)

DRESS = False          # flip to True to dress them

# `get_souls()`, not a tag read of my own. `SOUL_TAG` is a
# (key, CATEGORY) pair and a tag read without its category returns
# nothing — the first run of this script reported "souls: 0", which
# reads exactly like a clean world.
souls = [o for o in get_souls() if o.pk]
print(f"souls: {len(souls)}")

short = [(o, missing_outfit_slots(o)) for o in souls]
short = [(o, m) for o, m in short if m]
print(f"short at least one slot (robots already excluded): {len(short)}")
for o, m in short:
    print(f"    #{o.id:<6} {o.key:<24} missing {[s for s, _p in m]}")

if not short:
    print("\nNOTHING MATCHED. Before believing that, confirm the "
          "soul count above is non-zero and that the probe reads "
          "`worn_items` on the CHARACTER — see the method trap in this "
          "file's docstring.")
elif DRESS:
    print()
    for o, _m in short:
        filled = ensure_outfit_complete(o)
        worn = sorted(o.worn_items or {})
        print(f"    #{o.id:<6} {o.key:<24} filled {filled}")
    still = [(o, m) for o in souls if (m := missing_outfit_slots(o))]
    print(f"\nstill short after the pass: {len(still)}")
    for o, m in still:
        print(f"    #{o.id} {o.key} {[s for s, _p in m]}")
else:
    print(f"\nCENSUS ONLY — set DRESS = True. Slots checked: "
          f"{[s for s, _p in OUTFIT_SLOTS]}")
