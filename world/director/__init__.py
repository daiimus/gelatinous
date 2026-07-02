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
    resolve,
)
from world.director.dispatch import (
    ROLE_RESPONDS_TO,
    WorldEvent,
    dispatch,
    find_responders,
    raise_event,
)
from world.director.travel import (
    is_travelling,
    stop_travel,
    travel_to,
)

__all__ = [
    "Assignment",
    "ROLE_RESPONDS_TO",
    "WorldEvent",
    "active_assignments",
    "assign",
    "clear_assignment",
    "dispatch",
    "find_responders",
    "get_assignment",
    "is_assigned",
    "is_travelling",
    "raise_event",
    "register_arrival_handler",
    "resolve",
    "stop_travel",
    "travel_to",
]
