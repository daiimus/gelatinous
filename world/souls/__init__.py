"""Souls — deterministic NPC needs, goals, and jobs (NPC_NEEDS_AND_GOALS_SPEC).

The two-brain law: this package DECIDES; the LLM only ever voices.
Souls act exclusively through real commands (`execute_cmd`) and the
director's `travel_to` — no teleports, no db pokes into the economy.

Ensouling is opt-in per NPC:

    from world.souls import ensoul, desoul
    ensoul(npc, role="resident", home=cube, post=room, schedule="day")

State lives on the NPC under plain db attributes (`soul_*`); the global
`SoulsHeartbeat` script (engine.py) ticks decay and thinking at
LOD-scaled rates and survives reloads the same way patrols do.
"""

from world.souls.engine import ensoul, desoul, get_souls  # noqa: F401
