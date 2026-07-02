"""Dispatch assignments — the lifecycle of a responder, from dispatch to
return-to-post.

Completes the dispatcher's monitor/resolve half
(``NPC_DISPATCH_AND_SIMULATION_SPEC`` §5 steps 4–5): a dispatched NPC is
*assigned* to an event; on arrival a **role-keyed arrival handler** runs
(the seam the crime layer's scan-and-match plugs into); after a linger the
assignment **resolves** and the NPC travels back to its post. A
module-level registry tracks who is committed where — the finite-pool
bookkeeping that makes "overwhelm the force" a real tactic.

Assignment state lives on ``ndb`` + an in-memory registry (same
volatility tier as travel state): a reload clears in-flight assignments,
and NPCs simply resume their routine. Off-screen authority arrives with
the population/LOD layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from evennia.utils import delay

from world.director.travel import stop_travel, travel_to

#: Seconds a responder investigates on scene before resolving.
LINGER_SECONDS = 30.0
#: ndb key holding the NPC's active assignment.
_NDB_KEY = "director_assignment"

#: Active assignments, npc -> Assignment. In-memory (cleared on reload).
_ACTIVE: dict = {}

#: role -> callable(npc, assignment) run when the responder arrives on
#: scene. The seam the crime layer (scan/match/challenge) plugs into.
ARRIVAL_HANDLERS: dict[str, Callable] = {}


@dataclass
class Assignment:
    """One responder's commitment to one event."""

    npc: Any
    event: Any                    # the WorldEvent
    post: Any                     # room to return to when resolved
    state: str = "en_route"       # en_route | on_scene | returning | done
    payload: dict = field(default_factory=dict)


def register_arrival_handler(role: str, handler: Callable) -> None:
    """Register *handler(npc, assignment)* to run when a responder with
    ``db.role == role`` arrives on scene."""
    ARRIVAL_HANDLERS[role] = handler


def get_assignment(npc: Any):
    """The NPC's active :class:`Assignment`, or ``None``."""
    return _ACTIVE.get(npc)


def active_assignments() -> list:
    """Every in-flight assignment (the committed slice of the pool)."""
    return list(_ACTIVE.values())


def is_assigned(npc: Any) -> bool:
    return npc in _ACTIVE


def assign(npc: Any, event: Any) -> bool:
    """Commit *npc* to *event*: record the assignment (posting it back to
    its current room) and start travel. Returns ``False`` if travel could
    not start (unreachable). Reassignment cancels the previous assignment.
    """
    if npc is None or event is None or getattr(event, "location", None) is None:
        return False
    clear_assignment(npc)
    assignment = Assignment(npc=npc, event=event, post=npc.location)
    _ACTIVE[npc] = assignment
    if npc.ndb is not None:
        setattr(npc.ndb, _NDB_KEY, assignment)
    started = travel_to(npc, event.location,
                        on_arrive=_on_scene, on_fail=_on_travel_fail)
    if not started:
        clear_assignment(npc)
        return False
    return True


def clear_assignment(npc: Any) -> None:
    """Drop any assignment state for *npc* and halt its travel (does not
    move it — the NPC stands down wherever it is)."""
    _ACTIVE.pop(npc, None)
    stop_travel(npc)
    if getattr(npc, "ndb", None) is not None:
        setattr(npc.ndb, _NDB_KEY, None)


def resolve(npc: Any) -> None:
    """Finish the on-scene phase: send the responder back to its post."""
    assignment = _ACTIVE.get(npc)
    if assignment is None:
        return
    assignment.state = "returning"
    post = assignment.post
    if post is None or npc.location == post:
        _done(npc)
        return
    if not travel_to(npc, post, on_arrive=_done, on_fail=_done):
        _done(npc)


# --- internal lifecycle steps --------------------------------------------

def _on_scene(npc: Any) -> None:
    assignment = _ACTIVE.get(npc)
    if assignment is None:
        return
    assignment.state = "on_scene"
    role = getattr(getattr(npc, "db", None), "role", None)
    handler = ARRIVAL_HANDLERS.get(role, default_arrival)
    try:
        handler(npc, assignment)
    except Exception:  # noqa: BLE001 — a bad handler must not strand the NPC
        resolve(npc)


def _on_travel_fail(npc: Any) -> None:
    # Couldn't reach the scene — stand down where it is.
    clear_assignment(npc)


def _done(npc: Any) -> None:
    assignment = _ACTIVE.get(npc)
    if assignment is not None:
        assignment.state = "done"
    clear_assignment(npc)


def default_arrival(npc: Any, assignment: Any) -> None:
    """Default on-scene behavior: visibly investigate (via a real command),
    linger, then resolve. Role handlers (the crime layer's scan-and-match)
    replace this per role."""
    try:
        npc.execute_cmd("emote sweeps the area, taking stock of the scene.")
    except Exception:  # noqa: BLE001
        pass
    delay(LINGER_SECONDS, resolve, npc)
