"""Build 114 — the dispatcher's own voice on the band (#2223).

The console used to answer for her. It doesn't any more: the desk keeps
the competence (classify the call, roll the steel) and she keeps the
voice, answering through the real `xmit` command from whatever radio
she is actually holding.

Her stored persona seed still says ``archetype: colonist``, which is
what the prompt builder reads — so without this she'd take the band in
a civilian's register with no radio tool and no channel discipline.
This retunes the live seed to the new ``dispatcher`` archetype.

Idempotent. Touches only the operator's persona seed.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/114_dispatcher_speaks_for_herself.py
"""

from evennia.objects.models import ObjectDB
from evennia.utils.dbserialize import deserialize

ARCHETYPE = "dispatcher"

operators = [
    obj for obj in ObjectDB.objects.filter(
        db_attributes__db_key="dispatch_operator")
    if getattr(obj.db, "dispatch_operator", None) is True
]

if not operators:
    print("BUILD 114: no dispatch operator found; nothing to retune")

for who in operators:
    seed = deserialize(who.db.llm_persona) or {}
    if not seed:
        print(f"BUILD 114: {who.key} #{who.id} has no persona seed; skipped")
        continue
    was = seed.get("archetype")
    if was == ARCHETYPE:
        print(f"BUILD 114: {who.key} #{who.id} already a {ARCHETYPE}")
    else:
        seed["archetype"] = ARCHETYPE
        who.db.llm_persona = seed
        print(f"BUILD 114: {who.key} #{who.id} {was!r} -> {ARCHETYPE!r}")

    # Report what she can actually reach the air with — no device, no
    # voice, and that is the design (an unstaffed desk is silent).
    try:
        from world.radio import active_transmit_radio, frequency_of
        device = active_transmit_radio(who)
        print(f"BUILD 114: {who.key} transmits on "
              f"{frequency_of(device) if device else None!r} "
              f"via {getattr(device, 'key', None)!r}")
    except Exception as err:  # noqa: BLE001
        print(f"BUILD 114: could not read her transmit device: {err}")

    try:
        from world.llm.prompt import tool_names
        print(f"BUILD 114: tools = {tool_names({'persona_seed': seed})}")
    except Exception as err:  # noqa: BLE001
        print(f"BUILD 114: could not resolve tools: {err}")
