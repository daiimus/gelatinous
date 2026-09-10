"""Build 164 — stamp the sleeves #3033's backfill never reached (#2669).

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/164_backfill_the_last_sleeves.py

DEFAULTS TO A CENSUS. Set STAMP = True to write.

Owner ruling (2026-09-08): players get a manifest. `ensure_manifest` is
now on every creation path, and 57 of 65 player-owned bodies carry a
designation. The remaining 8 are older sleeves that predate it.

**GROUPED BY STACK, and that is the whole reason this is a script rather
than a loop.** A designation is a service record and belongs to the
PERSON, not the body — `ensure_manifest`'s own docstring says so:
"otherwise one player's thirty-three sleeves would carry thirty-three
different careers." Three of the eight share a `stack_id` and NONE of
that stack has a designation, so calling `ensure_manifest` on each in
turn would find nothing to inherit and roll three times. One roll per
stack, applied to every sleeve in it.

Re-run-safe: `ensure_manifest` leaves a character who already has a
designation exactly alone, and this only ever adds.
"""
from collections import defaultdict

from evennia.objects.models import ObjectDB

from world.manifest import designation_line, ensure_manifest, seed_skills
from world.ownership import is_player_owned

STAMP = False          # flip to True to write

bodies = [o for o in ObjectDB.objects.all()
          if o.pk and "characters.Character" in (o.typeclass_path or "")
          and is_player_owned(o)]
missing = [o for o in bodies if not o.db.designation]
print(f"player-owned bodies: {len(bodies)}   without a designation: "
      f"{len(missing)}")

stacks = defaultdict(list)
loners = []
for body in missing:
    stack = body.db.stack_id
    (stacks[stack] if stack else loners).append(body)

for stack, members in stacks.items():
    print(f"    stack {stack}: {[f'#{m.id} {m.key}' for m in members]}")
for body in loners:
    print(f"    no stack:  #{body.id} {body.key!r}")

if not missing:
    print("\nNothing to stamp.")
elif STAMP:
    print()
    for stack, members in stacks.items():
        first = members[0]
        ensure_manifest(first)
        for other in members[1:]:
            other.db.designation = dict(first.db.designation)
            skills = first.db.skills
            other.db.skills = dict(skills) if skills else seed_skills(
                other.db.designation)
        print(f"    stack {stack}: {designation_line(first)}")
        for m in members:
            print(f"        #{m.id} {m.key}")
    for body in loners:
        ensure_manifest(body)
        print(f"    #{body.id} {body.key}: {designation_line(body)}")
    left = [o for o in bodies if not o.db.designation]
    print(f"\nstill without a designation: {len(left)}")
else:
    print("\nCENSUS ONLY — set STAMP = True to write.")
