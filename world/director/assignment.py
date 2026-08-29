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

#: role -> callable(npc, assignment) run when the assignment completes
#: (the responder is back at its post). The seam base-intel-sync plugs
#: into: what a bot learned on scene goes force-wide only *here*.
COMPLETION_HANDLERS: dict[str, Callable] = {}
#: role -> handler(npc, assignment) for a responder that dies
#: still holding one (#2255).
DEATH_HANDLERS: dict = {}
#: role -> callable(npc) -> bool, run once per BEAT while a responder is
#: on scene. True keeps it there. This is what lets an assignment be
#: WORK the souls engine does rather than a body the director seizes
#: (NPC_PLATFORM_SPEC §7): a hold that re-arms its own timer can only
#: ever be driven by that timer.
WATCH_HANDLERS: dict[str, Callable] = {}


@dataclass
class Assignment:
    """One responder's commitment to one event."""

    npc: Any
    event: Any                    # the WorldEvent
    post: Any                     # room to return to when resolved
    state: str = "en_route"       # en_route | on_scene | returning | done
    payload: dict = field(default_factory=dict)


def register_watch_handler(role: str, handler: Callable) -> None:
    """Register *handler(npc) -> bool*, ticked once a beat on scene."""
    WATCH_HANDLERS[role] = handler


def run_arrival(npc: Any) -> None:
    """Run the on-scene handler for whoever this is. Shared by the old
    travel callback and the souls `respond` step, so both doors cannot
    drift."""
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


def run_watch(npc: Any) -> bool:
    """One on-scene beat. False when the responder is done holding."""
    assignment = _ACTIVE.get(npc)
    if assignment is None:
        return False
    role = getattr(getattr(npc, "db", None), "role", None)
    handler = WATCH_HANDLERS.get(role)
    if handler is None:
        return False          # no watch for this role: arriving IS the job
    try:
        return bool(handler(npc))
    except Exception:  # noqa: BLE001 — a bad watch must not strand the NPC
        return False


def register_arrival_handler(role: str, handler: Callable) -> None:
    """Register *handler(npc, assignment)* to run when a responder with
    ``db.role == role`` arrives on scene."""
    ARRIVAL_HANDLERS[role] = handler


def register_completion_handler(role: str, handler: Callable) -> None:
    """Register *handler(npc, assignment)* to run when a responder with
    ``db.role == role`` finishes its assignment back at its post."""
    COMPLETION_HANDLERS[role] = handler


def register_death_handler(role: str, handler: Callable) -> None:
    """Register *handler(npc, assignment)* to run when a responder with
    ``db.role == role`` dies while still holding an assignment."""
    DEATH_HANDLERS[role] = handler


def release_on_death(npc: Any) -> None:
    """Settle and drop a dead responder's assignment.

    Nothing used to clear an assignment on death, and the consequences
    compounded (#2255):

    * the call it came from stayed open in the ledger forever, with no
      outcome and nothing to answer for
    * the wreck kept its errand, so it read as still working
    * and because :func:`world.souls.engine.think` returns early for
      any assigned soul, the unit's soul stayed **permanently asleep**
      -- even after being repaired, it would never think again

    That last one is the quiet one: the precedence law that correctly
    stops a live unit walking off a scene also bricks a dead one.

    Fail-soft throughout. Dying must never raise.
    """
    assignment = _ACTIVE.get(npc)
    if assignment is None:
        return
    role = getattr(getattr(npc, "db", None), "role", None)
    handler = DEATH_HANDLERS.get(role)
    if handler is not None:
        try:
            handler(npc, assignment)
        except Exception:  # noqa: BLE001 — settling must not block release
            pass
    clear_assignment(npc)


def get_assignment(npc: Any):
    """The NPC's active :class:`Assignment`, or ``None``."""
    return _ACTIVE.get(npc)


def active_assignments() -> list:
    """Every in-flight assignment (the committed slice of the pool)."""
    return list(_ACTIVE.values())


def is_assigned(npc: Any) -> bool:
    return npc in _ACTIVE


def assign(npc: Any, event: Any) -> bool:
    """Commit *npc* to *event*: record the assignment and start travel.
    The return point is the NPC's **base** (``db.post``) when one is set
    — a posted responder goes home to the precinct, not to wherever it
    happened to be standing — else its current room. Returns ``False`` if
    travel could not start (unreachable). Reassignment cancels the
    previous assignment."""
    if npc is None or event is None or getattr(event, "location", None) is None:
        return False
    clear_assignment(npc)
    post = getattr(getattr(npc, "db", None), "post", None) or npc.location
    assignment = Assignment(npc=npc, event=event, post=post)
    _ACTIVE[npc] = assignment
    if npc.ndb is not None:
        setattr(npc.ndb, _NDB_KEY, assignment)
    # HAND THE SOUL THE WORK rather than seizing the body (#2384). Band 0
    # outranks everything, so the unit still does not wander off a call —
    # which is what the old `is_assigned` silence switch was protecting —
    # but it is ARBITRATED now instead of switched off, so a band-0
    # safety need can still reach it and a dead unit's job clears like
    # any other. That switch had already cost once: nothing cleared it on
    # death, and a wrecked unit's soul stayed asleep permanently, even
    # after repair (#2255).
    if _has_soul(npc):
        npc.db.soul_job = {
            "goal": "respond", "band": 0, "at": 0, "steps": [
                {"do": "travel", "room": event.location.id},
                {"do": "respond"},
                {"do": "travel", "room": post.id},
                {"do": "stand_down"},
            ],
        }
        return True
    # An unsouled responder — nothing in the colony currently is — still
    # gets driven the old way rather than standing there.
    started = travel_to(npc, event.location,
                        on_arrive=_on_scene, on_fail=_on_travel_fail)
    if not started:
        clear_assignment(npc)
        return False
    return True


def _has_soul(npc: Any) -> bool:
    try:
        from world.souls.engine import SOUL_TAG
        return bool(npc.tags.get(SOUL_TAG[0], category=SOUL_TAG[1]))
    except Exception:  # noqa: BLE001 — no tag handler is no soul
        return False


def finish(npc: Any) -> None:
    """Settle a completed assignment (the souls `stand_down` step)."""
    _done(npc)


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
    run_arrival(npc)


def _on_travel_fail(npc: Any) -> None:
    # Couldn't reach the scene — stand down where it is.
    clear_assignment(npc)


def _done(npc: Any) -> None:
    assignment = _ACTIVE.get(npc)
    if assignment is not None:
        assignment.state = "done"
        role = getattr(getattr(npc, "db", None), "role", None)
        handler = COMPLETION_HANDLERS.get(role)
        if handler is not None:
            try:
                handler(npc, assignment)
            except Exception:  # noqa: BLE001 — completion flavour must not strand
                pass
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
