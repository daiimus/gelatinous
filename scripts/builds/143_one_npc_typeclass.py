"""Build 143 — one NPC typeclass (#2378).

The collapse the last week of work was for. `Bartender`, `Shopkeeper`,
`Doctor` and `Butcher` no longer hold anything: serving, selling and
treating live in the job registry keyed by `post_role`; aliases, the
scripted fallback, the archetype and the tools ride the job; receiving a
corpse is the job's `on_receive` hook. What was left on those classes
was a creation hook, a fixture lookup and a handful of delegates.

So the bodies become what every other NPC in the colony is: `LLMNpc` —
a Character with the voice mixin, whose capabilities come from the post
it stands and the soul it carries. The typeclass says what a body IS and
never what it can do (NPC_PLATFORM_SPEC §3, law 5).

Swapped WITHOUT start hooks. A Character's creation hook rebuilds a
body, and these twelve have lived in theirs — the same care build 137
took. Attributes, tags, posts, souls, personas and memories are all
untouched by a swap; only the class pointer moves.

Idempotent, and refuses to touch anything a player owns.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/143_one_npc_typeclass.py
"""

from evennia.objects.models import ObjectDB

from world.ownership import is_player_owned

TARGET = "typeclasses.llm_npc.LLMNpc"
DOOMED_CLASSES = (
    "typeclasses.bar.Bartender",
    "typeclasses.shopkeeper.Shopkeeper",
    "typeclasses.clinic.Doctor",
    "typeclasses.butcher.Butcher",
)

moved = refused = 0
for path in DOOMED_CLASSES:
    for obj in list(ObjectDB.objects.filter(db_typeclass_path=path)):
        if is_player_owned(obj):
            print(f"BUILD 143: {obj.db_key} REFUSED — a player owns this body")
            refused += 1
            continue
        before = obj.db_typeclass_path.split(".")[-1]
        obj.swap_typeclass(TARGET, clean_attributes=False,
                           run_start_hooks=None)
        # The voice mixin's own marker, normally set by a creation hook we
        # are deliberately not running.
        obj.db.is_npc = True
        print(f"BUILD 143: {obj.db_key[:24]:24} {before:11} -> LLMNpc")
        moved += 1

print(f"BUILD 143: moved={moved} refused={refused}")

left = {p: ObjectDB.objects.filter(db_typeclass_path=p).count()
        for p in DOOMED_CLASSES}
print(f"BUILD 143: bodies still on a role class: {left}")
print("BUILD 143: done")
