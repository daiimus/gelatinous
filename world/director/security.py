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
    register_death_handler,
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
    worn = _worn_signature(perp)
    if uid is None and not (height or build or worn):
        return None
    return {"uid": uid, "height": height, "build": build, "worn": worn,
            "via": via if via in BOLO_CHANNELS else "radio",
            "by": getattr(by, "key", None)}


def _worn_signature(perp: Any) -> set:
    """What the person is visibly WEARING, as colour+garment pairs.

    The thing every witness actually leads with — "a guy in a black
    trenchcoat" — and the thing a BOLO had nowhere to put, so the most
    useful sentence anybody says was thrown away (#2250).

    Deliberately coarse: colour and garment noun, not the item. Two
    different black coats read the same to a stranger across a street,
    which is exactly the fidelity a description deserves.
    """
    out = set()
    try:
        for item in (perp.get_worn_items() or []):
            noun = str(getattr(item, "key", "")).split()[-1].lower()
            colour = str(getattr(item, "color", "") or "").lower().strip()
            if noun:
                out.add((colour, noun))
    except Exception:  # noqa: BLE001 — an unreadable wardrobe describes nothing
        pass
    return out


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
    seen_h = getattr(candidate, "height", None)
    seen_b = getattr(candidate, "build", None)
    if height and build:
        if seen_h == height and seen_b == build:
            return "low"
        return None

    # HALF a silhouette plus what they were wearing. "A svelte lady in a
    # black trenchcoat" gives one axis and a coat — useless before,
    # because both axes were required, so the most recognisable thing
    # about somebody counted for nothing (#2250).
    #
    # Clothes come off, which is the point: this is the description that
    # a change of coat defeats, and it should be.
    worn = bolo.get("worn")
    if worn and (height or build):
        axis_ok = ((height is None or seen_h == height)
                   and (build is None or seen_b == build))
        if axis_ok and (worn & _worn_signature(candidate)):
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


def close_call_for(assignment: Any, outcome: str, npc: Any = None) -> None:
    """Settle the CALL this assignment came from, and say so on the air.

    The half that never existed. A unit finding nothing had nowhere to
    report it, so a false report cost the colony two units and left no
    trace — nothing to answer for, nothing to hold against a caller,
    nothing for a dispatcher to know an hour later.

    Only PHONED-IN incidents carry a call id; a witnessed crime is not
    a call, and closing one would be inventing a caller who never rang.
    """
    event = getattr(assignment, "event", None)
    call_id = (getattr(event, "payload", None) or {}).get("call_id")
    if not call_id:
        return
    try:
        from world.director.calls import close_call
        if close_call(call_id, outcome, by=npc) is None:
            return
    except Exception:  # noqa: BLE001 — the ledger never breaks a scene
        return
    # The play-by-play: units already announce themselves when they
    # roll, so they announce the finding too. Deterministic, in the
    # unit's own voice, through the real verb — the same discipline as
    # the responding ack.
    line = _CALL_OUTCOME_LINES.get(outcome)
    if line and npc is not None:
        where = getattr(getattr(event, "location", None), "key", "the scene")
        _cmd(npc, f"xmit Unit {getattr(npc, 'id', 0) or 0} — {where}. "
                  f"{line}")


#: What a unit says when it settles a call. Flat, procedural, and short
#: enough not to clog a band people are trying to shout for help on.
_CALL_OUTCOME_LINES = {
    "unfounded": "Nothing here matching the report. Scene logged, "
                 "clearing.",
    "detained": "Subject held. Matches the report.",
    "checked": "Subject checked, no match. Clearing.",
}


#: What a unit says once when its own chassis goes critical mid-call.
#: Short: it is shouting over a band people use to call for help, and
#: it is not asking permission to leave.
_MAYDAY_LINE = ("Chassis compromised, hydraulic loss. Still on scene.")


def _mayday(npc: Any, assignment: Any) -> None:
    """Transmit ONCE when a responding unit is critically damaged.

    A unit on a call never abandons it -- `think()` returns early for
    any assigned soul, so the souls layer (and its band tree) is asleep
    for the whole call, and that is the correct behaviour: you do not
    walk off a scene because you are hurt.

    But it left the damage mute. This force communicates entirely by
    voice, and the one thing a unit never transmitted was its own
    condition, so dispatch knew where every unit went and nothing about
    what state it was in. Now it calls its own damage in and holds the
    scene, and the board can roll somebody else (#2272).

    Fires once per assignment, like `_engage`.
    """
    if assignment.payload.get("mayday"):
        return
    try:
        from world.souls import needs as _needs
        if _needs.pressure(npc, "health") < _needs.critical_for(npc, "health"):
            return
    except Exception:  # noqa: BLE001 — an unreadable body stays quiet
        return
    assignment.payload["mayday"] = True
    where = getattr(getattr(assignment, "event", None), "location", None)
    _cmd(npc, f"xmit Unit {getattr(npc, 'id', 0) or 0} — "
              f"{getattr(where, 'key', 'the scene')}. {_MAYDAY_LINE}")


def security_arrival(npc: Any, assignment: Any) -> None:
    """On-scene behavior for ``role == "security"``: scan, match, act.

    Priority: the event's BOLO (this incident) beats the wanted record
    (old business) — but a face on file gets challenged even when it has
    nothing to do with *this* call."""
    _mayday(npc, assignment)
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
        close_call_for(assignment, "detained", npc)
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
        close_call_for(assignment, "checked", npc)
        delay(INVESTIGATE_SECONDS, resolve, npc)
    else:
        _cmd(npc, "emote finds nothing that matches its report and "
                  "logs the scene.")
        # UNFOUNDED — the first consequence a false report has ever had.
        close_call_for(assignment, "unfounded", npc)
        delay(INVESTIGATE_SECONDS, resolve, npc)


def watch_once(npc: Any) -> bool:
    """One cycle of holding a suspect. True = keep watching.

    Split out of the delay-chained `_watch_tick` so something else can
    drive it — a souls job, once dispatch stops seizing the body
    (NPC_PLATFORM_SPEC §7, #2383). The behaviour is unchanged; only who
    calls it, and how often, moves.

    Returning False means the watch is over and the unit should stand
    down. It deliberately does NOT call `resolve` itself: deciding to
    stop and walking home are different acts, and conflating them is why
    this could only ever be driven by a timer.
    """
    from world.director.assignment import get_assignment
    assignment = get_assignment(npc)
    if assignment is None:
        return False  # stood down meanwhile
    _mayday(npc, assignment)
    if _in_combat(npc):
        # The fight owns the unit; keep monitoring without burning rounds.
        return True
    bolo = (getattr(assignment.event, "payload", None) or {}).get("bolo")
    confidence, suspect = _scan(npc, bolo)
    holding = confidence == "high"
    if not holding:
        _uid, suspect, _entry = _scan_wanted(npc)
        holding = suspect is not None
    if holding and _in_combat(suspect):
        # The held suspect started (or resumed) violence under watch.
        _engage(npc, assignment, suspect)
        return True
    rounds = assignment.payload.get("watch_rounds", 0) - 1
    assignment.payload["watch_rounds"] = rounds
    if not holding or rounds <= 0:
        if holding:
            _cmd(npc, "emote logs the subject's presence and stands down.")
        _release_aim(npc)   # lower the weapon before walking home
        return False
    _cmd(npc, "emote holds position, optics locked on its subject.")
    return True


def _watch_tick(npc: Any) -> None:
    """The timer-driven watch: tick once, then re-arm or stand down."""
    from world.director.assignment import get_assignment
    if watch_once(npc):
        delay(WATCH_SECONDS, _watch_tick, npc)
        return
    if get_assignment(npc) is not None:
        resolve(npc)


def security_completion(npc: Any, assignment: Any) -> None:
    """Back at post: sync local sightings into the force-wide wanted
    record (§5.1 — intel goes force-wide only *here*; the walk home is
    the latency window, and a bot that never makes it back never syncs)."""
    if sync_bot_intel(npc):
        _cmd(npc, "emote docks at its post and uplinks patrol data.")


register_arrival_handler("security", security_arrival)
def security_death(npc: Any, assignment: Any) -> None:
    """A responder destroyed on a call. Settle the call it was holding.

    The unit says nothing -- `unit_lost` has no line in
    `_CALL_OUTCOME_LINES` on purpose. A destroyed unit does not
    transmit, and its going silent mid-call IS the signal. The ledger
    still records how the call ended, so a false report that got a unit
    killed leaves a trace (#2255).
    """
    close_call_for(assignment, "unit_lost", npc)


register_completion_handler("security", security_completion)
register_death_handler("security", security_death)
