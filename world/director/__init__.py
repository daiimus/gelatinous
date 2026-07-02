"""The director — the deterministic world-simulation engine that moves
NPCs around and dispatches them to world events.

See ``specs/proposals/NPC_DISPATCH_AND_SIMULATION_SPEC.md``.

This first slice is the **dispatch core**: pathfinder-driven NPC travel
(``travel``) plus event → responder routing (``dispatch``), built directly
on the spatial substrate (``world/spatial``). Population LOD, routines, the
deterministic interaction vocabulary, and the LLM escalation gate are
later layers.
"""

from world.director.assignment import (
    Assignment,
    active_assignments,
    assign,
    clear_assignment,
    get_assignment,
    is_assigned,
    register_arrival_handler,
    register_completion_handler,
    resolve,
)
from world.director.intel import (
    clear_wanted_record,
    get_wanted_record,
    is_wanted,
    sync_bot_intel,
)
from world.director.dispatch import (
    ROLE_RESPONDS_TO,
    WorldEvent,
    dispatch,
    find_responders,
    raise_event,
)
from world.director.crime import (
    CRIME_SEVERITY,
    report_crime,
)
from world.director.security import (
    build_bolo,
    match_bolo,
)
from world.director.witness import (
    can_report,
    spawn_witness,
    witness_chance,
    witness_report,
)
from world.director.travel import (
    is_travelling,
    stop_travel,
    travel_to,
)

__all__ = [
    "Assignment",
    "CRIME_SEVERITY",
    "ROLE_RESPONDS_TO",
    "WorldEvent",
    "active_assignments",
    "assign",
    "build_bolo",
    "can_report",
    "clear_assignment",
    "clear_wanted_record",
    "dispatch",
    "find_responders",
    "get_assignment",
    "get_wanted_record",
    "is_assigned",
    "is_travelling",
    "is_wanted",
    "match_bolo",
    "raise_event",
    "register_arrival_handler",
    "register_completion_handler",
    "report_crime",
    "resolve",
    "spawn_witness",
    "stop_travel",
    "sync_bot_intel",
    "travel_to",
    "witness_chance",
    "witness_report",
]
