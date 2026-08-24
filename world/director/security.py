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

from world.director.assignment import (
    register_arrival_handler,
    register_completion_handler,
    resolve,
)
from world.director.intel import is_wanted, log_local_sighting, sync_bot_intel
from world.identity import get_apparent_uid
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

#: How a description reached the people acting on it. A BOLO is a
#: CLAIM — what somebody said — and what it is worth depends entirely
#: on how they came to say it (#2247).
#:
#: `machine` is the only channel that may carry a `uid`, because a uid
#: is a 16-character presentation hash and nobody says one out loud. A
#: security unit that saw something itself is passing DATA to the net;
#: this is the precursor to the photo/video record that will feed cases
#: and decking. Everyone else describes.
BOLO_CHANNELS = ("machine", "witness", "radio")


def build_bolo(perp: Any, *, via: str = "witness", by: Any = None) -> dict | None:
    """Snapshot what an observer on channel *via* could honestly pass on.

    ``height``/``build`` are the silhouette anyone can describe. ``uid``
    is the exact presentation and is included ONLY for ``machine`` —
    a bystander cannot recite a hash, and until now every crime handed
    responders one anyway, so a civilian's glimpse identified people as
    positively as a camera would.

    ``None`` when there is nothing worth passing on.
    """
    if perp is None:
        return None
    height = getattr(perp, "height", None)
    build = getattr(perp, "build", None)
    uid = get_apparent_uid(perp) if via == "machine" else None
    if uid is None and not (height or build):
        return None
    return {"uid": uid, "height": height, "build": build,
            "via": via if via in BOLO_CHANNELS else "radio",
            "by": getattr(by, "key", None)}


def is_the_right_person(event: Any, candidate: Any) -> bool | None:
    """Did they actually get the one who did it?

    The GAME's question, never the robot's. A BOLO is what somebody
    claimed and can be vague, mistaken or a lie; `event.source` is who
    really did it. Keeping those apart is the whole point — a unit acts
    on a possibly-false account while the system still knows the truth,
    so wrong-person outcomes are legible to us and invisible to them.

    ``None`` when the event names no instigator (an anonymous fire, a
    sourceless disturbance): unknowable rather than wrong.
    """
    source = getattr(event, "source", None)
    if source is None or candidate is None:
        return None
    return getattr(source, "id", None) == getattr(candidate, "id", None)


def match_bolo(bolo: dict | None, candidate: Any) -> str | None:
    """Match *candidate*'s **current** presentation against *bolo*.

    Returns ``"high"`` (presentation hash matches), ``"low"`` (only the
    height+build silhouette matches), or ``None``.
    """
    if not bolo or candidate is None:
        return None
    uid = bolo.get("uid")
    # A positive identification has to have come from something that
    # could actually record one. A uid arriving by any other channel is
    # a bug or a forgery, and forgery is meant to be the attack surface
    # rather than an accident (#2247).
    if uid and bolo.get("via") == "machine" \
            and get_apparent_uid(candidate) == uid:
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


def _target_token(suspect: Any) -> str:
    """A string the identity-aware combat resolver will actually match
    for *suspect*: their current **sdesc**, which substring-matches
    itself. Real keys are builder-gated by the recognition system —
    ``attack Elizabeth von Fischer`` resolves nothing for an NPC. The
    unit targets what it perceives, exactly like a player typing
    ``attack stout woman``."""
    try:
        sdesc = suspect.get_sdesc()
        if sdesc:
            return sdesc
    except Exception:  # noqa: BLE001
        pass
    return str(getattr(suspect, "key", suspect))


def _aim_lock(npc: Any, suspect: Any) -> None:
    """The innocuous detainment rung: hold the suspect at aim (the aim
    lock pins them in place; a flee contest is their counterplay). A real
    command — the same aim any player uses."""
    _cmd(npc, f"aim {_target_token(suspect)}")


def _release_aim(npc: Any) -> None:
    """Lower the weapon when standing down (only if actually aiming)."""
    if getattr(getattr(npc, "ndb", None), "aiming_at", None) is not None:
        _cmd(npc, "aim stop")


def _in_combat(char: Any) -> bool:
    """Is *char* currently in an active combat handler?

    Liveness-checked: a stale ndb ref (handler deleted, char no longer
    in its entries) would otherwise read as in-combat FOREVER — wedging
    the soul engine and patrols out of the character's life. A stale
    ref is cleared on detection."""
    try:
        from world.combat.constants import NDB_COMBAT_HANDLER
        handler = getattr(getattr(char, "ndb", None), NDB_COMBAT_HANDLER,
                          None)
        if handler is None:
            return False
        from world.combat.utils import validate_character_handler_reference
        valid, _handler, _err = validate_character_handler_reference(char)
        if not valid:
            setattr(char.ndb, NDB_COMBAT_HANDLER, None)
            return False
        return True
    except Exception:  # noqa: BLE001
        return False


def _engage(npc: Any, assignment: Any, suspect: Any) -> None:
    """The Engage rung: violence in progress in front of the unit
    authorizes force. Deploy the arm gun and attack — real commands; the
    combat handler owns the fight from here. Fires once per assignment."""
    if assignment.payload.get("engaged"):
        return
    assignment.payload["engaged"] = True
    _cmd(npc, "say Cease, Colonist. Violence in progress: "
              "force is authorized.")
    _cmd(npc, "/shotgun")   # deploy the integrated riot gun
    _cmd(npc, f"attack {_target_token(suspect)}")


def _scan_wanted(npc: Any):
    """First perceivable character whose *current* presentation is on the
    force-wide wanted record: ``(uid, char, entry)`` or ``(None,)*3``.
    Per-bot perception still gates — the force knowing a face doesn't let
    a bot that can't see act on it."""
    if not can_see(npc) or npc.location is None:
        return None, None, None
    for obj in getattr(npc.location, "contents", None) or []:
        if obj is npc:
            continue
        if not (hasattr(obj, "is_typeclass")
                and obj.is_typeclass("typeclasses.characters.Character",
                                     exact=False)):
            continue
        uid = get_apparent_uid(obj)
        entry = is_wanted(uid)
        if entry:
            return uid, obj, entry
    return None, None, None


def security_arrival(npc: Any, assignment: Any) -> None:
    """On-scene behavior for ``role == "security"``: scan, match, act.

    Priority: the event's BOLO (this incident) beats the wanted record
    (old business) — but a face on file gets challenged even when it has
    nothing to do with *this* call."""
    _cmd(npc, "emote sweeps the scene with a slow sensor pass.")
    event = assignment.event
    bolo = (getattr(event, "payload", None) or {}).get("bolo")
    confidence, suspect = _scan(npc, bolo)
    if confidence == "high":
        # Confirmed identification — known to THIS bot only until it
        # returns to post and syncs (the §5.1 latency window).
        log_local_sighting(npc, bolo.get("uid"),
                           getattr(event, "type", "crime"))
        if _in_combat(suspect):
            # Crime IN PROGRESS in front of the unit — skip detainment,
            # escalate straight to the Engage rung.
            _engage(npc, assignment, suspect)
        else:
            _cmd(npc, "say Colonist. Hold your position. "
                      "You match an active report.")
            _aim_lock(npc, suspect)
        assignment.payload["watch_rounds"] = WATCH_ROUNDS
        delay(WATCH_SECONDS, _watch_tick, npc)
        return
    # No hit on this incident — but is anyone here already on file?
    wanted_uid, flagged, entry = _scan_wanted(npc)
    if flagged is not None:
        log_local_sighting(npc, wanted_uid,
                           entry.get("last_crime") or "wanted")
        if _in_combat(flagged):
            _engage(npc, assignment, flagged)
        else:
            _cmd(npc, "say Colonist. You're flagged in the system. "
                      "Hold your position.")
            _aim_lock(npc, flagged)
        assignment.payload["watch_rounds"] = WATCH_ROUNDS
        delay(WATCH_SECONDS, _watch_tick, npc)
    elif confidence == "low":
        _cmd(npc, "say You there, Colonist. You fit a description. "
                  "State your business here.")
        delay(INVESTIGATE_SECONDS, resolve, npc)
    else:
        _cmd(npc, "emote finds nothing that matches its report and "
                  "logs the scene.")
        delay(INVESTIGATE_SECONDS, resolve, npc)


def _watch_tick(npc: Any) -> None:
    """Re-scan while holding a suspect (event-BOLO match *or* a face on
    the wanted record); give up after ``WATCH_ROUNDS`` cycles or when no
    subject holds. A unit in combat never walks home mid-fight, and a held
    suspect who turns violent gets the Engage rung."""
    from world.director.assignment import get_assignment
    assignment = get_assignment(npc)
    if assignment is None:
        return  # stood down meanwhile
    if _in_combat(npc):
        # The fight owns the unit; keep monitoring without burning rounds.
        delay(WATCH_SECONDS, _watch_tick, npc)
        return
    bolo = (getattr(assignment.event, "payload", None) or {}).get("bolo")
    confidence, suspect = _scan(npc, bolo)
    holding = confidence == "high"
    if not holding:
        _uid, suspect, _entry = _scan_wanted(npc)
        holding = suspect is not None
    if holding and _in_combat(suspect):
        # The held suspect started (or resumed) violence under watch.
        _engage(npc, assignment, suspect)
        delay(WATCH_SECONDS, _watch_tick, npc)
        return
    rounds = assignment.payload.get("watch_rounds", 0) - 1
    assignment.payload["watch_rounds"] = rounds
    if not holding or rounds <= 0:
        if holding:
            _cmd(npc, "emote logs the subject's presence and stands down.")
        _release_aim(npc)   # lower the weapon before walking home
        resolve(npc)
        return
    _cmd(npc, "emote holds position, optics locked on its subject.")
    delay(WATCH_SECONDS, _watch_tick, npc)


def security_completion(npc: Any, assignment: Any) -> None:
    """Back at post: sync local sightings into the force-wide wanted
    record (§5.1 — intel goes force-wide only *here*; the walk home is
    the latency window, and a bot that never makes it back never syncs)."""
    if sync_bot_intel(npc):
        _cmd(npc, "emote docks at its post and uplinks patrol data.")


register_arrival_handler("security", security_arrival)
register_completion_handler("security", security_completion)
