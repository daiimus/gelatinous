"""World events and the dispatcher — match responders to an event by role
and travel distance, and route them to it.

This is the heart of the director's "both layers": the simulation (who
exists, where, with what role) meets the spatial system (how they get
there). Fully deterministic — no LLM. See
``NPC_DISPATCH_AND_SIMULATION_SPEC.md`` §5.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from world.director.travel import travel_to
from world.spatial import path_length


@dataclass
class WorldEvent:
    """A typed, located thing that happened in the world."""

    type: str
    location: Any                 # the room it happened in
    severity: int = 1             # drives how many responders are sent
    source: Any = None            # the instigator (a PC, an NPC, a system)
    payload: dict = field(default_factory=dict)


#: Event type → the NPC roles that respond to it. New roles/events: add
#: an entry. ``db.role`` on a Character names its role (e.g. "security").
ROLE_RESPONDS_TO: dict[str, tuple[str, ...]] = {
    "assault": ("security",),
    "disturbance": ("security",),
    "crime": ("security",),
    "fire": ("security",),
}


def _npcs_with_roles(roles) -> list:
    """Every Character whose ``db.role`` is one of *roles* (a targeted
    attribute query — not a full object scan)."""
    from evennia.objects.models import ObjectDB
    roles = set(roles)
    out = []
    for obj in ObjectDB.objects.filter(db_attributes__db_key="role").distinct():
        if not obj.is_typeclass("typeclasses.characters.Character", exact=False):
            continue
        if getattr(obj.db, "role", None) in roles:
            out.append(obj)
    return out


def find_responders(event: WorldEvent) -> list:
    """Candidate responders for *event*, **nearest-first by travel distance**.

    Returns ``[(steps, npc), …]`` sorted ascending; unreachable and
    locationless NPCs are dropped. Empty when no role responds to the type.
    """
    roles = ROLE_RESPONDS_TO.get(event.type)
    if not roles or event.location is None:
        return []
    ranked = []
    for npc in _npcs_with_roles(roles):
        if npc.location is None or npc is event.source:
            continue
        steps = path_length(npc.location, event.location, traverser=npc)
        if steps is None:
            continue  # can't get there
        ranked.append((steps, npc))
    ranked.sort(key=lambda t: t[0])
    return ranked


def dispatch(event: WorldEvent) -> list:
    """Send the nearest eligible responders to *event* (count scaled by
    ``severity``). Returns the list of dispatched NPCs."""
    ranked = find_responders(event)
    if not ranked:
        return []
    count = min(len(ranked), max(1, int(event.severity)))
    dispatched = []
    for _steps, npc in ranked[:count]:
        if travel_to(npc, event.location):
            dispatched.append(npc)
    return dispatched


def raise_event(event: WorldEvent) -> list:
    """Raise *event* onto the director. Currently routes straight to the
    dispatcher; the seam where a full event bus / monitor lands later."""
    return dispatch(event)
