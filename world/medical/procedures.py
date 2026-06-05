"""Surgical procedure pipeline (#307 follow-up).

Centralises the engine that backs ``incise`` / ``harvest`` / ``install`` /
``suture`` and the location-aware ``apply`` upgrades.  Commands are
thin wrappers; the heavy lifting (target accessor, state mutations,
skill rolls, time delays, failure consequences) lives here.

Design contract
================

* **Procedures act on bodies and body-derived containers.**  Living
  characters, corpses, severed heads, and severed limbs all expose an
  organ snapshot via :func:`get_organ_snapshot`.  Same dispatch path
  for every target type.
* **Two-phase resolution.**  Each verb opens a procedure: the
  attempt is staged on ``target.db.surgical_state["active_procedure"]``
  with a delay duration; resolution fires when the delay elapses,
  rolling skill and applying outcome.  Interruptions during the
  window route through :func:`interrupt_procedure`.
* **Anesthesia is condition-driven, not a verb.**  Unconscious
  patients (via ``character.is_unconscious()`` or absence of an
  account on a sedated target) get bonuses and skip pain seeding.
  Conscious patients add a difficulty modifier and accumulate pain
  while procedures run on them.
* **Failure modes are placeholders** (#307 design pass):
  - Botched incise → mild organ damage at the cut location.
  - Botched harvest → organ comes out one condition worse.
  - Botched install → organ doesn't take, infection seeded.
  - Botched treat / suture → infection seeded at location.
"""

from __future__ import annotations

import random
import time
from typing import Optional

from evennia.utils import delay as evennia_delay

# ---------------------------------------------------------------------
# Constants — placeholders subject to balance pass (#307)
# ---------------------------------------------------------------------

#: Base difficulty for procedure rolls (spec line 704 / 1466 reference).
PROCEDURE_BASE_DIFFICULTY = 12

#: Difficulty bump for operating on a conscious patient (no anesthesia).
CONSCIOUS_PATIENT_DIFFICULTY = 5

#: Difficulty discount for operating on an unconscious / anesthetised
#: patient — they don't resist and the surgeon can work with full focus.
ANESTHETIZED_DIFFICULTY_BONUS = 3

#: Tick durations (in seconds) per verb.  Short enough to feel
#: interactive; long enough that mid-combat surgery is genuinely
#: tense.  Balance numbers — adjust freely.
PROCEDURE_DURATIONS = {
    "incise": 6,
    "harvest": 18,
    "install": 18,
    "suture": 9,
}

#: Pain severity seeded on a conscious patient when a procedure
#: completes on them (per verb).  Unconscious patients skip this.
CONSCIOUS_PAIN_SEVERITY = {
    "incise": 3,
    "harvest": 5,
    "install": 4,
    "suture": 2,
}

#: Infection severity seeded as a failure consequence.  Caller passes
#: the body location; the resulting condition is location-bound.
FAILURE_INFECTION_SEVERITY = 2


# ---------------------------------------------------------------------
# Target accessor — works on every container type
# ---------------------------------------------------------------------


def get_organ_snapshot(target) -> dict:
    """Return the organ snapshot for any procedure target.

    Unifies the four supported target types behind one accessor so the
    dispatch never branches on ``isinstance``:

    * **Living character** → reads from ``target.medical_state`` (live
      ``Organ`` objects).
    * **Corpse / SeveredHead / Appendage** → reads from
      ``target.get_medical_snapshot()`` (death-time dict snapshot).

    Returns an empty dict when no snapshot is available (target
    predates the medical pipeline or isn't a body container).
    """
    # Living: medical_state attribute with live organs.
    medical_state = getattr(target, "medical_state", None)
    if medical_state is not None and hasattr(medical_state, "organs"):
        return {
            "organs": {
                name: organ.to_dict()
                for name, organ in medical_state.organs.items()
            },
        }

    # Item / corpse: get_medical_snapshot() returns the snapshot dict.
    accessor = getattr(target, "get_medical_snapshot", None)
    if callable(accessor):
        return accessor() or {}

    return {}


def organs_at_location(target, location: str) -> list[tuple[str, dict]]:
    """Return ``(organ_name, organ_data)`` pairs at ``location``.

    Matches against either the organ's ``container`` or
    ``display_location`` (the latter handles sensory organs like the
    eyes that surface at a more specific render location than their
    bulk container).
    """
    snapshot = get_organ_snapshot(target)
    organs = snapshot.get("organs") or {}
    out = []
    for name, data in organs.items():
        if not isinstance(data, dict):
            continue
        container = data.get("container")
        display = data.get("display_location")
        if location in (container, display):
            out.append((name, data))
    return out


# ---------------------------------------------------------------------
# Surgical state on the target
# ---------------------------------------------------------------------


def _state(target) -> dict:
    """Lazy-init and return ``target.db.surgical_state``."""
    if target.db.surgical_state is None:
        target.db.surgical_state = {
            "incisions": {},
            "active_procedure": None,
        }
    return target.db.surgical_state


def has_incision(target, location: str) -> bool:
    """True when ``location`` is currently incised on ``target``."""
    state = _state(target)
    return location in state["incisions"]


def open_incision(target, location: str, surgeon, tool=None) -> None:
    """Record a new incision at ``location``.

    Multiple simultaneous incisions are allowed — useful for
    thoracoabdominal procedures and other multi-cavity work.
    """
    state = _state(target)
    state["incisions"][location] = {
        "opened_at": time.time(),
        "opened_by": getattr(surgeon, "dbref", None),
        "tool": getattr(tool, "dbref", None),
    }
    # Persist back so AttributeProperty fires.
    target.db.surgical_state = state


def close_incision(target, location: str) -> bool:
    """Remove an incision at ``location``.  Returns True if one was
    actually closed, False if no incision existed there.
    """
    state = _state(target)
    if location not in state["incisions"]:
        return False
    del state["incisions"][location]
    target.db.surgical_state = state
    return True


def close_all_incisions(target) -> list[str]:
    """Close every open incision; return the list of closed locations."""
    state = _state(target)
    closed = list(state["incisions"].keys())
    state["incisions"] = {}
    target.db.surgical_state = state
    return closed


def open_incision_locations(target) -> list[str]:
    """Return the locations currently incised on ``target``."""
    return list(_state(target)["incisions"].keys())


# ---------------------------------------------------------------------
# Active procedure tracking (time delays)
# ---------------------------------------------------------------------


def is_procedure_active(target) -> bool:
    """True when ``target`` has a procedure in-flight."""
    state = _state(target)
    return state.get("active_procedure") is not None


def start_procedure(target, *, verb: str, actor, **kwargs) -> dict:
    """Stage an active procedure on ``target``.

    Schedules :func:`_resolve_procedure_callback` to fire after the
    verb's duration via ``evennia.utils.delay``.  The actor / target
    can still be interrupted in the meantime (combat damage,
    physical separation, target dies); see
    :func:`interrupt_procedure`.

    Stores enough context on ``target.db.surgical_state`` that the
    resolution callback can re-fetch the actor / tool / target_organ
    without closures over Python objects that may not survive a
    process restart.
    """
    duration = PROCEDURE_DURATIONS.get(verb, 6)
    record = {
        "verb": verb,
        "actor_dbref": getattr(actor, "dbref", None),
        "started_at": time.time(),
        "duration_s": duration,
        "kwargs": dict(kwargs),
    }
    state = _state(target)
    state["active_procedure"] = record
    target.db.surgical_state = state

    evennia_delay(
        duration,
        _resolve_procedure_callback,
        target,
        persistent=False,
    )
    return record


def interrupt_procedure(target, reason: str = "interrupted") -> Optional[dict]:
    """Clear the active procedure without resolving it.

    Used by combat / movement / death hooks.  Returns the cleared
    record so callers can render an interruption message.
    """
    state = _state(target)
    record = state.get("active_procedure")
    state["active_procedure"] = None
    target.db.surgical_state = state
    return record


def _resolve_procedure_callback(target) -> None:
    """Fire when a staged procedure's delay elapses.

    Re-reads the active procedure off ``target.db.surgical_state``,
    confirms it's still valid (target alive enough / actor reachable),
    and dispatches to the verb-specific resolver.  Resolution is
    intentionally idempotent: if the active_procedure was cleared in
    the meantime (interrupted, manually cancelled), we no-op.
    """
    state = _state(target)
    record = state.get("active_procedure")
    if record is None:
        return  # interrupted / already resolved
    # Clear the slot first so a resolver-triggered side effect can't
    # re-enter.
    state["active_procedure"] = None
    target.db.surgical_state = state

    from evennia.objects.models import ObjectDB
    actor_dbref = record.get("actor_dbref")
    if actor_dbref:
        try:
            actor = ObjectDB.objects.get(id=int(actor_dbref.lstrip("#")))
        except (ObjectDB.DoesNotExist, ValueError):
            actor = None
    else:
        actor = None

    if actor is None:
        # Actor has gone away (logged out, deleted).  Per design (E):
        # leave the patient as-is; the incision stays open and bleeds.
        return

    verb = record["verb"]
    kwargs = record.get("kwargs") or {}
    resolver = _VERB_RESOLVERS.get(verb)
    if resolver is None:
        return
    resolver(actor, target, **kwargs)


# ---------------------------------------------------------------------
# Skill rolls — spec line 1434
# ---------------------------------------------------------------------


def calculate_procedure_skill(actor) -> float:
    """Return the actor's medical-procedure skill.

    Per spec line 1434:
    ``medical_effectiveness = (intellect * 0.75) + (motorics * 0.25)``
    """
    intellect = getattr(actor, "intellect", 1) or 1
    motorics = getattr(actor, "motorics", 1) or 1
    return (intellect * 0.75) + (motorics * 0.25)


def calculate_procedure_difficulty(target, *, conscious_modifier: bool = True) -> int:
    """Return the difficulty target for a procedure on ``target``.

    ``conscious_modifier``: when True (default), apply the +5
    difficulty for conscious unanesthetised patients and the −3
    bonus for unconscious / anesthetized ones.  Corpses are treated
    as unconscious (full bonus) since there's no resistance to deal
    with.
    """
    difficulty = PROCEDURE_BASE_DIFFICULTY
    if not conscious_modifier:
        return difficulty

    # Corpses: max bonus (no resistance).
    from typeclasses.corpse import Corpse
    if isinstance(target, Corpse):
        return difficulty - ANESTHETIZED_DIFFICULTY_BONUS

    # Severed items: same — no resistance.
    try:
        from typeclasses.items import Appendage, SeveredHead, Organ
        if isinstance(target, (Appendage, SeveredHead, Organ)):
            return difficulty - ANESTHETIZED_DIFFICULTY_BONUS
    except ImportError:
        pass

    # Living character: depends on consciousness.
    is_unconscious = False
    checker = getattr(target, "is_unconscious", None)
    if callable(checker):
        try:
            is_unconscious = bool(checker())
        except Exception:
            is_unconscious = False
    if is_unconscious:
        return difficulty - ANESTHETIZED_DIFFICULTY_BONUS
    return difficulty + CONSCIOUS_PATIENT_DIFFICULTY


def roll_procedure(actor, target, *, conscious_modifier: bool = True) -> dict:
    """Roll a procedure check.

    Returns a dict with ``roll``, ``skill``, ``total``, ``difficulty``,
    ``outcome`` (``"success"`` / ``"partial"`` / ``"failure"``).  Uses
    3d6 + skill vs difficulty matching the existing
    ``calculate_treatment_success`` shape so existing UX prose
    integrates cleanly.
    """
    skill = calculate_procedure_skill(actor)
    difficulty = calculate_procedure_difficulty(
        target, conscious_modifier=conscious_modifier,
    )
    roll = sum(random.randint(1, 6) for _ in range(3))
    total = roll + skill

    if total >= difficulty + 5:
        outcome = "success"
    elif total >= difficulty:
        outcome = "partial"
    else:
        outcome = "failure"

    return {
        "roll": roll,
        "skill": skill,
        "total": total,
        "difficulty": difficulty,
        "outcome": outcome,
    }


# ---------------------------------------------------------------------
# Failure-consequence helpers
# ---------------------------------------------------------------------


def seed_infection(target, location: str, severity: int = FAILURE_INFECTION_SEVERITY) -> None:
    """Add a location-bound infection condition to ``target``.

    Used as a placeholder failure consequence for botched procedures
    (#307 design pass: refine when the deeper treatment mechanics
    land).  Only applies to living targets that have a
    ``medical_state.conditions`` list; corpses and severed items are
    no-ops.
    """
    state = getattr(target, "medical_state", None)
    if state is None or not hasattr(state, "conditions"):
        return
    try:
        from world.medical.conditions import InfectionCondition
    except ImportError:
        return
    state.conditions.append(InfectionCondition(severity, location))


def seed_pain(target, location: Optional[str], severity: int) -> None:
    """Add a pain condition to a conscious living target.

    Skips the seed when the target is unconscious / anesthetized (no
    pain perceived) or isn't a living character (no medical_state).
    """
    state = getattr(target, "medical_state", None)
    if state is None or not hasattr(state, "conditions"):
        return
    is_unconscious = False
    checker = getattr(target, "is_unconscious", None)
    if callable(checker):
        try:
            is_unconscious = bool(checker())
        except Exception:
            is_unconscious = False
    if is_unconscious:
        return
    try:
        from world.medical.conditions import PainCondition
    except ImportError:
        return
    state.conditions.append(PainCondition(severity, location))


# ---------------------------------------------------------------------
# Verb resolvers — invoked by ``_resolve_procedure_callback`` after the
# delay elapses.  Each resolver reads its kwargs from the staged
# procedure record, rolls the skill check, applies the outcome, and
# messages the actor + target + room.
# ---------------------------------------------------------------------


def _resolve_incise(actor, target, *, location: str, **_) -> None:
    """Resolve an ``incise`` attempt at ``location``.

    Outcomes:
    * **success** — incision opens cleanly.
    * **partial** — incision opens but with extra damage to an organ
      at the location (placeholder failure detail).
    * **failure** — no incision; minor organ damage seeded.
    """
    from world.identity_utils import msg_room_identity

    result = roll_procedure(actor, target)
    outcome = result["outcome"]

    if outcome in ("success", "partial"):
        open_incision(target, location, surgeon=actor)
        seed_pain(target, location, CONSCIOUS_PAIN_SEVERITY["incise"])

    if outcome == "success":
        actor.msg(
            f"You cut a clean incision through {_possessive(target)} "
            f"{location.replace('_', ' ')}."
        )
        if hasattr(target, "msg") and target is not actor:
            target.msg(
                f"{actor.key}'s blade opens a clean incision through "
                f"your {location.replace('_', ' ')}."
            )
        if actor.location is not None:
            msg_room_identity(
                location=actor.location,
                template=(
                    f"{{actor}} cuts a clean incision through "
                    f"{{patient}}'s {location.replace('_', ' ')}."
                ),
                char_refs={"actor": actor, "patient": target},
                exclude=[actor, target] if target is not actor else [actor],
            )
    elif outcome == "partial":
        _apply_collateral_damage(target, location, amount=2)
        actor.msg(
            f"You open {_possessive(target)} {location.replace('_', ' ')} "
            f"— but the cut runs deeper than you meant."
        )
    else:  # failure
        _apply_collateral_damage(target, location, amount=3)
        seed_infection(target, location)
        actor.msg(
            f"The blade slips. {_possessive(target).capitalize()} "
            f"{location.replace('_', ' ')} is gashed but not properly "
            f"opened."
        )


def _resolve_harvest(actor, target, *, organ_name: str, location: str,
                     **_) -> None:
    """Resolve a ``harvest`` attempt for ``organ_name`` at ``location``."""
    from evennia import create_object
    from world.identity_utils import msg_room_identity
    from world.combat.constants import ORGAN_CONDITION_BY_DECAY

    result = roll_procedure(actor, target)
    outcome = result["outcome"]

    # Fetch the source organ data from the snapshot.
    snapshot_organs = get_organ_snapshot(target).get("organs", {}) or {}
    organ_data = snapshot_organs.get(organ_name) or {}

    # Decay tier → harvested condition.
    decay_stage = "fresh"
    stage_getter = getattr(target, "get_decay_stage", None)
    if callable(stage_getter):
        try:
            decay_stage = stage_getter() or "fresh"
        except Exception:
            decay_stage = "fresh"
    condition = ORGAN_CONDITION_BY_DECAY.get(decay_stage, "pristine")

    # Outcome → condition fidelity.  Botched living-harvest produces
    # damaged organs even from a fresh body (placeholder failure rule
    # per design D: organ damage risk when harvesting from a conscious
    # patient).
    if outcome == "partial" and condition == "pristine":
        condition = "damaged"
    elif outcome == "failure":
        condition = "damaged" if condition == "pristine" else "putrid"
        seed_infection(target, location)
        seed_pain(target, location, CONSCIOUS_PAIN_SEVERITY["harvest"])
        actor.msg(
            f"Your hands slip mid-extraction. The {organ_name.replace('_', ' ')} "
            f"comes out badly mangled."
        )
        # Even failed harvest tears the organ out — mark it removed
        # on the source so the player knows the procedure happened.
        _mark_organ_removed(target, organ_name)
        return

    # Success / partial: spawn the harvested item.
    from typeclasses.items import Organ as HarvestedOrgan
    room = actor.location
    harvested = create_object(
        typeclass=HarvestedOrgan,
        key=organ_name,
        location=actor,
    )
    # Reuse the existing harvest configuration path so identity /
    # decay / prose are all set the same way as corpse-harvest.
    # ``configure_from_harvest`` expects a corpse-shaped source for
    # signature / decay; for living targets we adapt via a thin shim.
    _configure_harvested_item(
        harvested, organ_name=organ_name, condition=condition,
        source=target, organ_data=organ_data,
    )

    # Mark the organ removed on the source so repeat harvests can't
    # spawn duplicates.
    _mark_organ_removed(target, organ_name)

    seed_pain(target, location, CONSCIOUS_PAIN_SEVERITY["harvest"])

    actor.msg(
        f"You extract the {organ_name.replace('_', ' ')} from "
        f"{target.get_display_name(actor)}'s {location.replace('_', ' ')}."
    )
    if room is not None:
        msg_room_identity(
            location=room,
            template=(
                f"{{actor}} extracts the {organ_name.replace('_', ' ')} "
                f"from {{patient}}'s {location.replace('_', ' ')}."
            ),
            char_refs={"actor": actor, "patient": target},
            exclude=[actor, target] if target is not actor else [actor],
        )


def _resolve_install(actor, target, *, organ_item, location: str,
                     **_) -> None:
    """Resolve an ``install`` attempt: slot ``organ_item`` into
    ``target`` at ``location``."""
    from world.identity_utils import msg_room_identity

    result = roll_procedure(actor, target)
    outcome = result["outcome"]

    if outcome == "failure":
        # Botched install: organ doesn't take, infection seeded.
        seed_infection(target, location)
        seed_pain(target, location, CONSCIOUS_PAIN_SEVERITY["install"])
        actor.msg(
            f"The graft won't take. The {organ_item.key} stays loose "
            f"in your hands."
        )
        return

    # Success / partial: organ installs.  Living target: restore HP and
    # attach any organ-bound conditions from the harvested item to the
    # corresponding organ on the recipient.
    state = getattr(target, "medical_state", None)
    if state is not None:
        organ = state.organs.get(organ_item.db.organ_name)
        if organ is not None:
            # Reset HP based on harvested condition.
            condition_hp = {
                "pristine": organ.max_hp,
                "damaged": int(organ.max_hp * 0.6),
                "putrid": int(organ.max_hp * 0.3),
            }
            organ.current_hp = condition_hp.get(
                organ_item.db.condition or "pristine", organ.max_hp,
            )
            organ.wound_stage = None if organ.current_hp == organ.max_hp else "fresh"
            # Attach organ-bound conditions from the harvested item.
            for condition_dict in (organ_item.db.organ_conditions or []):
                try:
                    from world.medical.conditions import deserialize_condition
                    organ.conditions.append(deserialize_condition(condition_dict))
                except Exception:
                    pass

    seed_pain(target, location, CONSCIOUS_PAIN_SEVERITY["install"])

    if outcome == "partial":
        # Partial: success but with infection seed.
        seed_infection(target, location)
        actor.msg(
            f"You install the {organ_item.key} — but the graft is "
            f"sloppy. Time will tell."
        )
    else:
        actor.msg(
            f"You install the {organ_item.key} into "
            f"{target.get_display_name(actor)}'s "
            f"{location.replace('_', ' ')}."
        )

    if actor.location is not None:
        msg_room_identity(
            location=actor.location,
            template=(
                f"{{actor}} installs a {organ_item.key} into "
                f"{{patient}}'s {location.replace('_', ' ')}."
            ),
            char_refs={"actor": actor, "patient": target},
            exclude=[actor, target] if target is not actor else [actor],
        )

    # Consume the harvested item.
    try:
        organ_item.delete()
    except Exception:
        pass


def _resolve_suture(actor, target, *, location: Optional[str] = None,
                    **_) -> None:
    """Resolve a ``suture`` attempt.  ``location=None`` closes all
    open incisions; a specific location closes just one."""
    from world.identity_utils import msg_room_identity

    result = roll_procedure(actor, target)
    outcome = result["outcome"]

    if location is None:
        closed = close_all_incisions(target)
    else:
        closed = [location] if close_incision(target, location) else []

    if not closed:
        actor.msg(
            f"There's nothing to suture on "
            f"{target.get_display_name(actor)}."
        )
        return

    seed_pain(target, closed[0], CONSCIOUS_PAIN_SEVERITY["suture"])

    if outcome == "failure":
        # Botched close: infection seeded at the location.
        for loc in closed:
            seed_infection(target, loc)
        actor.msg(
            f"You close the wound — but the stitches are uneven and "
            f"the seam pulls dirty."
        )
    elif outcome == "partial":
        actor.msg(
            f"You suture the incision shut. The line is rough but "
            f"will hold."
        )
    else:
        actor.msg(
            f"You suture the incision shut with neat, even stitches."
        )

    if actor.location is not None:
        location_str = ", ".join(loc.replace("_", " ") for loc in closed)
        msg_room_identity(
            location=actor.location,
            template=(
                f"{{actor}} sutures {{patient}}'s "
                f"{location_str} closed."
            ),
            char_refs={"actor": actor, "patient": target},
            exclude=[actor, target] if target is not actor else [actor],
        )


# Mapping consumed by ``_resolve_procedure_callback``.
_VERB_RESOLVERS = {
    "incise": _resolve_incise,
    "harvest": _resolve_harvest,
    "install": _resolve_install,
    "suture": _resolve_suture,
}


# ---------------------------------------------------------------------
# Supporting helpers
# ---------------------------------------------------------------------


def _possessive(target) -> str:
    """Cheap possessive — ``"the rat's"`` / ``"Bob's"``."""
    name = getattr(target, "key", "the patient")
    return f"{name}'s"


def _apply_collateral_damage(target, location: str, amount: int) -> None:
    """Damage organs at ``location`` (placeholder failure detail)."""
    state = getattr(target, "medical_state", None)
    if state is None or not hasattr(state, "organs"):
        return
    for organ in state.organs.values():
        if organ.container == location or organ.display_location == location:
            organ.current_hp = max(0, organ.current_hp - amount)
            if organ.wound_stage is None:
                organ.wound_stage = "fresh"


def _mark_organ_removed(target, organ_name: str) -> None:
    """Mark ``organ_name`` as removed from ``target``.

    Three persistence paths covered:

    1. ``removed_organs`` list — gates repeat-harvest on the same source.
    2. Live ``medical_state`` organ HP — zero / ``severed`` so downstream
       rendering and capacity math reflect the absence on living targets.
    3. Death-time snapshot organ HP — same zero / ``severed`` mutation so
       autopsy and repeat-harvest agree on corpse-shaped sources.
    4. ``wounds_at_death`` ``harvested`` wound entry — feeds autopsy
       narrative and PR #200's sever-overlay carry-forward (when the
       organ's container location is later severed, the wound rides
       along onto the severed item).  Only synthesised when the target
       carries the ``wounds_at_death`` attribute (corpses / severed
       parts); living targets get the live-organ mutation instead.
    """
    removed = getattr(target.db, "removed_organs", None) or []
    if organ_name not in removed:
        removed = list(removed) + [organ_name]
        target.db.removed_organs = removed

    state = getattr(target, "medical_state", None)
    if state is not None and hasattr(state, "organs"):
        organ = state.organs.get(organ_name)
        if organ is not None:
            organ.current_hp = 0
            organ.wound_stage = "severed"

    snapshot = None
    accessor = getattr(target, "get_medical_snapshot", None)
    if callable(accessor):
        try:
            snapshot = accessor()
        except Exception:
            snapshot = None
    container = organ_name
    if snapshot:
        organs = snapshot.get("organs") or {}
        entry = organs.get(organ_name)
        if isinstance(entry, dict):
            entry["current_hp"] = 0
            entry["wound_stage"] = "severed"
            container = entry.get("container") or organ_name

    # Corpse-shaped sources (Corpse, SeveredHead, SeveredAppendage) carry
    # ``medical_state_at_death`` — use that as the duck check rather than
    # isinstance-ing every concrete class.  Living targets don't have a
    # death snapshot and don't need a wound-at-death entry.
    target_db = getattr(target, "db", None)
    if target_db is not None and getattr(target_db, "medical_state_at_death", None) is not None:
        wounds = list(getattr(target_db, "wounds_at_death", None) or ())
        wounds.append({
            "injury_type": "harvested",
            "location": container,
            "severity": "Critical",
            "stage": "old",
            "organ": organ_name,
            "organ_damage": {
                "current_hp": 0,
                "max_hp": 0,
                "container": container,
            },
        })
        target_db.wounds_at_death = wounds
        if snapshot:
            target_db.medical_state_at_death = snapshot


def _configure_harvested_item(item, *, organ_name: str, condition: str,
                              source, organ_data: dict) -> None:
    """Set the harvested ``item``'s db fields without relying on the
    corpse-shaped ``configure_from_harvest`` flow.

    The legacy ``Organ.configure_from_harvest`` assumes a corpse with
    identity-signature and decay-stage attributes; living targets and
    severed items don't fit that contract uniformly.  We populate
    fields directly here so harvest works against any source.
    """
    from world.anatomy import (
        get_organ_default_description,
        get_species_organ_name,
    )

    item.db.organ_name = organ_name
    item.db.condition = condition
    item.db.source_corpse_dbref = getattr(source, "dbref", None)

    # Identity provenance — copy from the source when present.
    source_db = getattr(source, "db", None)
    item.db.source_signature = (
        getattr(source_db, "signature_at_death", None)
        if source_db is not None else None
    )
    item.db.source_apparent_uid = (
        getattr(source_db, "apparent_uid_at_death", None)
        if source_db is not None else None
    )

    # Species + decay-aware display key.
    species = getattr(source_db, "species", None) or "human"
    item.db.source_species = species

    stage_getter = getattr(source, "get_decay_stage", None)
    if callable(stage_getter):
        try:
            decay_stage = stage_getter() or "fresh"
        except Exception:
            decay_stage = "fresh"
    else:
        decay_stage = "fresh"

    item.key = get_species_organ_name(species, organ_name, decay_stage)

    prose = get_organ_default_description(organ_name, condition)
    if prose:
        item.db.desc = prose

    # Organ-bound conditions travel with the organ (#307 follow-up).
    item.db.organ_conditions = list(organ_data.get("conditions") or [])
