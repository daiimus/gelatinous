"""Build 162 — take off the manifest anyone who never sailed (#2670).

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/162_strike_the_robot_from_the_manifest.py

DEFAULTS TO A CENSUS. Set STRIKE = True to clear the designations.

Build 100 backfilled the slowboat manifest and spelled its exclusion
`startswith("synth")`, so a security robot walked through a filter
written to keep non-people off it. `#3258` is on record as a
Specialist, Logistics & Stores aboard SBL-0117 — a berth on the
crossing, which is a thing only a person can have held. It renders on
`@soul` and on the character's own record.

The rule now lives in `world/manifest.travelled_as_crew`, which this
script asks rather than re-deriving. That is the point: a second copy
of the predicate is how the first one drifted.

Re-run-safe: it clears only designations held by bodies the rule says
never sailed, so a second run finds nothing.
"""
from world.manifest import NEVER_ON_THE_MANIFEST, travelled_as_crew
from world.souls.engine import get_souls

STRIKE = False          # flip to True to clear them

souls = [s for s in get_souls() if s.pk]
print(f"souls: {len(souls)}   (rule excludes {list(NEVER_ON_THE_MANIFEST)})")
if not souls:
    print("NOTHING TO SCAN. `SOUL_TAG` is a (key, CATEGORY) pair and a tag "
          "read without its category returns nothing.")
else:
    held = [s for s in souls if s.db.designation]
    wrong = [s for s in held if not travelled_as_crew(s)]
    print(f"holding a designation: {len(held)}")
    print(f"...who never sailed:   {len(wrong)}")
    for s in wrong:
        d = dict(s.db.designation or {})
        print(f"    #{s.id:<6} {s.key:<34} species={s.db.species!r}")
        print(f"           {d}")
    if not wrong:
        print("\nNothing to strike. Before believing that, confirm the "
              "count above is non-zero.")
    elif STRIKE:
        for s in wrong:
            s.attributes.remove("designation")
        left = [s for s in souls if s.db.designation
                and not travelled_as_crew(s)]
        print(f"\nstruck {len(wrong)}; still wrong: {len(left)}")
    else:
        print("\nCENSUS ONLY — set STRIKE = True to clear them.")
