"""Build 113 — the crane console answers, not the operator (#2216).

Swaps the live objects onto the standard:

* the crane console  -> ``typeclasses.crane.CraneConsole``
* Ossie              -> ``typeclasses.llm_npc.LLMNpc``

The competence moves from the person to the fixture. Ossie keeps his
voice — he is the speaker whenever he is in the chair — but he is no
longer the *reason* the crane works, so the day shift can be held by
somebody else without the hoist going deaf.

Attributes are preserved on both swaps (`clean_attributes=False`): his
soul, home, post binding and persona all survive, as does the
console's band, power state and post registration.

Idempotent.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/113_crane_console_answers.py
"""

from evennia.utils.search import search_object

CONSOLE_PATH = "typeclasses.crane.CraneConsole"
NPC_PATH = "typeclasses.llm_npc.LLMNpc"
OSSIE = "#7401"

ossie = next(iter(search_object(OSSIE)), None)
if ossie is None or not ossie.pk:
    print("BUILD 113: Ossie not found; aborted")
else:
    cab = ossie.location
    console = next(
        (o for o in (cab.contents if cab else [])
         if getattr(o.db, "is_base_station", None) is True), None)

    if console is None:
        print("BUILD 113: crane console not found; aborted")
    else:
        if console.typeclass_path != CONSOLE_PATH:
            console.swap_typeclass(CONSOLE_PATH, clean_attributes=False,
                                   run_start_hooks=None)
            print(f"BUILD 113: {console.key} -> CraneConsole")
        else:
            print("BUILD 113: console already a CraneConsole")

        if ossie.typeclass_path != NPC_PATH:
            ossie.swap_typeclass(NPC_PATH, clean_attributes=False,
                                 run_start_hooks=None)
            print(f"BUILD 113: {ossie.key} -> LLMNpc (the crane no longer "
                  f"lives inside him)")
        else:
            print("BUILD 113: Ossie already a plain LLMNpc")

        # the console IS the post, so it can ask itself who is on shift
        print(f"BUILD 113: post_role={console.db.post_role!r} "
              f"slots={sorted(console.db.post_slots or {})}")
        print(f"BUILD 113: soul_post still {ossie.db.soul_post}, "
              f"schedule {ossie.db.soul_schedule!r}")
