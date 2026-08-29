"""Build 139 — Vesper takes her shift (#2362).

The last of the population merge, and the one that was ruled on twice.

`NPC_NEEDS_AND_GOALS_SPEC` §12 excluded Companions from ensoulment:
"Vesper's agentic tool loop is its own driver." The owner reversed that
— *"Vesper/Companions can be shift workers too"* — and the spec was
amended (2026-08-28) to say so. The reasoning in the original was wrong
about the shape of the thing: an agentic tool loop is not a driver, it
is a voice that happens to have hands. The precedence law is combat >
director > souls, and the LLM appears nowhere in it.

The exclusion left a workaround behind. `posts._slot_held` carries a
branch letting an UNSOULED cast member hold a post by presence, so the
vacancy watcher would not resleeve a second Vesper while the first stood
there (#2132). She is the only body that branch was ever for. It goes in
the same change that removes the need for it.

She is bound through `do_claim`, the same path a soul walking in off the
street uses, so her post, role, schedule, wage rate and till all derive
from the post rather than from anything typed here.

Idempotent.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/139_vesper_takes_the_shift.py
"""

from evennia.objects.models import ObjectDB

from world.souls import engine, posts as posts_mod

VESPER_ID = 3109
CHAISE_ID = 5278
SHIFT = "swing"

vesper = ObjectDB.objects.get(id=VESPER_ID)
chaise = ObjectDB.objects.get(id=CHAISE_ID)

if vesper.tags.get(engine.SOUL_TAG[0], category=engine.SOUL_TAG[1]):
    print(f"BUILD 139: {vesper.key} already ensouled — nothing to do.")
else:
    # Her needs come from the `synth` profile (species synthetic_humanoid),
    # which carries the full human set. HOME is the VIP room she already
    # lives and works in — a Companion at a lounge is resident there, and
    # `rest` with no home returns None from the planner and faults nightly.
    room = chaise.location if chaise.location is not None else chaise
    engine.ensoul(vesper, role="companion", home=room, post=None,
                  schedule=SHIFT, wage_rate=0.02)
    # Bind through the REAL claim, so post/role/schedule/wage/till are
    # derived from the post exactly as they would be for anyone else.
    posts_mod.do_claim(vesper, chaise, shift=SHIFT)
    print(f"BUILD 139: {vesper.key} ensouled and bound to "
          f"{chaise.key} ({SHIFT})")
    print(f"BUILD 139:   role={vesper.db.soul_role} "
          f"post={vesper.db.soul_post} home={vesper.db.soul_home}")
    print(f"BUILD 139:   profile={__import__('world.souls.needs', fromlist=['x']).profile_name(vesper)}")

slots = {k: (s.get("keeper").key if s.get("keeper") else None)
         for k, s in (chaise.db.post_slots or {}).items()}
print(f"BUILD 139: chaise slots now {slots}")
print("BUILD 139: done")
