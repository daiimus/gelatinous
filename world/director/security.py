"""Security response — BOLOs and the on-scene scan-and-match.

Crime slice 1 (``NPC_DISPATCH_AND_SIMULATION_SPEC`` §5.1): the responder
is a **perceiver, not an oracle**. A crime event never hands security the
perpetrator object — it carries a **BOLO**: a snapshot of what the perp
*looked like* (their ``apparent_uid`` presentation hash, plus the coarse
height/build silhouette). On scene, the responder scans who it can
*currently perceive* and matches against the BOLO with **tiered
confidence**:

* **high** — the candidate's current ``apparent_uid`` equals the BOLO's
  (same presentation): challenge and *watch* (stay on scene, re-scan).
* **low** — only the coarse silhouette matches (same height + build):
  question — which can put an innocent lookalike in the hot seat.
  Mistaken identity is intended (§5.2).
* none — no match: investigate and move on.

Everything §5.1 promises falls out: flee the scene (not perceived),
change presentation (UID no longer matches), look generic (coarse
matches are shared), blind the bot (it can't scan at all).
"""

from __future__ import annotations

from typing import Any

from evennia.utils import delay

from world.director.assignment import register_arrival_handler, resolve
from world.identity import get_apparent_uid, get_short_sdesc
from world.perception import can_see

#: Seconds between watch re-scans when a high-confidence suspect is held.
WATCH_SECONDS = 15.0
#: How many watch cycles before the responder gives up and resolves.
WATCH_ROUNDS = 4
#: Seconds an unmatched investigation lingers before resolving.
INVESTIGATE_SECONDS = 30.0


# --------------------------------------------------------------------------
# BOLO — build & match
# --------------------------------------------------------------------------

def build_bolo(perp: Any) -> dict | None:
    """Snapshot *perp*'s current presentation as a BOLO dict.

    ``uid`` is the precise presentation hash; ``height``/``build`` are the
    coarse silhouette fallback. ``None`` when there is nothing to describe.
    """
    if perp is None:
        return None
    uid = get_apparent_uid(perp)
    height = getattr(perp, "height", None)
    build = getattr(perp, "build", None)
    if uid is None and not (height or build):
        return None
    return {"uid": uid, "height": height, "build": build}


def match_bolo(bolo: dict | None, candidate: Any) -> str | None:
    """Match *candidate*'s **current** presentation against *bolo*.

    Returns ``"high"`` (presentation hash matches), ``"low"`` (only the
    height+build silhouette matches), or ``None``.
    """
    if not bolo or candidate is None:
        return None
    uid = bolo.get("uid")
    if uid and get_apparent_uid(candidate) == uid:
        return "high"
    height, build = bolo.get("height"), bolo.get("build")
    if height and build:
        if (getattr(candidate, "height", None) == height
                and getattr(candidate, "build", None) == build):
            return "low"
    return None


# --------------------------------------------------------------------------
# The security arrival handler
# --------------------------------------------------------------------------

def _scan(npc: Any, bolo: dict | None):
    """Best (confidence, suspect) among characters *npc* can perceive at
    its location — ``(None, None)`` when nothing matches or it can't see."""
    if not can_see(npc):
        return None, None  # a blinded responder scans nothing
    location = npc.location
    if location is None:
        return None, None
    best = (None, None)
    for obj in getattr(location, "contents", None) or []:
        if obj is npc:
            continue
        if not (hasattr(obj, "is_typeclass")
                and obj.is_typeclass("typeclasses.characters.Character",
                                     exact=False)):
            continue
        confidence = match_bolo(bolo, obj)
        if confidence == "high":
            return "high", obj
        if confidence == "low" and best[0] is None:
            best = ("low", obj)
    return best


def _cmd(npc: Any, command: str) -> None:
    try:
        npc.execute_cmd(command)
    except Exception:  # noqa: BLE001 — flavour must never strand the responder
        pass


def security_arrival(npc: Any, assignment: Any) -> None:
    """On-scene behavior for ``role == "security"``: scan, match, act."""
    _cmd(npc, "emote sweeps the scene with a slow sensor pass.")
    bolo = (getattr(assignment.event, "payload", None) or {}).get("bolo")
    confidence, suspect = _scan(npc, bolo)
    if confidence == "high":
        handle = get_short_sdesc(suspect)
        _cmd(npc, f"say You — {handle}. Hold your position. "
                  f"You match an active report.")
        assignment.payload["watch_rounds"] = WATCH_ROUNDS
        delay(WATCH_SECONDS, _watch_tick, npc)
    elif confidence == "low":
        handle = get_short_sdesc(suspect)
        _cmd(npc, f"say You there — {handle}. You fit a description. "
                  f"State your business here.")
        delay(INVESTIGATE_SECONDS, resolve, npc)
    else:
        _cmd(npc, "emote finds nothing that matches its report and "
                  "logs the scene.")
        delay(INVESTIGATE_SECONDS, resolve, npc)


def _watch_tick(npc: Any) -> None:
    """Re-scan while holding a high-confidence suspect; give up after
    ``WATCH_ROUNDS`` cycles or when the suspect no longer matches."""
    from world.director.assignment import get_assignment
    assignment = get_assignment(npc)
    if assignment is None:
        return  # stood down meanwhile
    bolo = (getattr(assignment.event, "payload", None) or {}).get("bolo")
    confidence, suspect = _scan(npc, bolo)
    rounds = assignment.payload.get("watch_rounds", 0) - 1
    assignment.payload["watch_rounds"] = rounds
    if confidence != "high" or rounds <= 0:
        if confidence == "high":
            _cmd(npc, "emote logs the subject's presence and stands down.")
        resolve(npc)
        return
    _cmd(npc, "emote holds position, optics locked on its subject.")
    delay(WATCH_SECONDS, _watch_tick, npc)


register_arrival_handler("security", security_arrival)
