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
    ``severity``) as tracked **assignments** (en route → on scene → linger
    → return to post; see ``world/director/assignment.py``). Already-
    assigned responders are committed elsewhere and skipped — the finite
    pool is real, which is what makes overwhelming it a tactic. Returns
    the list of dispatched NPCs."""
    from world.director.assignment import assign, is_assigned
    ranked = find_responders(event)
    if not ranked:
        return []
    count = max(1, int(event.severity))
    dispatched = []
    for _steps, npc in ranked:
        if len(dispatched) >= count:
            break
        if is_assigned(npc):
            continue  # committed to another incident
        if assign(npc, event):
            dispatched.append(npc)
    return dispatched


#: How long an incident scene stays HOT (situational cause for the hunt).
INCIDENT_WINDOW = 600.0
_INCIDENT_KEY = "director_incidents"


def _log_incident(event: WorldEvent) -> None:
    """Roll the incident log (ServerConfig, capped): every raised event
    marks its room; entries expire after INCIDENT_WINDOW."""
    if event.location is None:
        return
    import time
    from evennia.server.models import ServerConfig
    now = time.time()
    log = [entry for entry in (ServerConfig.objects.conf(_INCIDENT_KEY) or [])
           if now - float(entry.get("t", 0)) < INCIDENT_WINDOW]
    log.append({"room": getattr(event.location, "id", None), "t": now,
                "type": event.type,
                "known_source": event.source is not None})
    ServerConfig.objects.conf(_INCIDENT_KEY, log[-50:])


def incident_context(room, *, window: float = INCIDENT_WINDOW) -> bool:
    """Reasonable suspicion (stealth spec, user-decided 2026-07-03): an
    UNRESOLVED incident (no known instigator) is hot in or adjacent to
    *room*. Context, not status: near a fresh sourceless disturbance —
    an explosion, an anonymous crime — a hidden presence IS cause."""
    if room is None:
        return False
    import time
    from evennia.server.models import ServerConfig
    ids = {getattr(room, "id", None)}
    for exit_obj in getattr(room, "exits", []) or []:
        dest = getattr(exit_obj, "destination", None)
        if dest is not None:
            ids.add(dest.id)
    now = time.time()
    for entry in ServerConfig.objects.conf(_INCIDENT_KEY) or []:
        if entry.get("known_source"):
            continue  # a known perp is hunted by uid, not by vicinity
        if now - float(entry.get("t", 0)) >= window:
            continue
        if entry.get("room") in ids:
            return True
    return False


def raise_event(event: WorldEvent) -> list:
    """Raise *event* onto the director. Logs the incident (situational
    cause for the hunt), then routes to the dispatcher; the seam where a
    full event bus / monitor lands later."""
    try:
        _log_incident(event)
    except Exception:  # noqa: BLE001 — logging must not block dispatch
        pass
    return dispatch(event)
