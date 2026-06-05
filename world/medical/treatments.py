"""Wound-care treatment dispatch (#307, PR-B stabilization channel).

Single entry point: :func:`apply_wound_care`.  Called by ``CmdApply``
when a player applies a ``wound_care``-typed item at a location on a
target.  Resolves stabilization (always) and per-category effect
rolls in parallel (bleeding / infection / pain), then consumes one
use of the item.

The substance-tolerance principle settled in the design pass means
the system accepts any wound_care item on any wound.  The item's
``effectiveness`` ratings, combined with the wound's severity and
depth, determine what the application actually does — anywhere from
"slowed the worst of it but they need a surgeon" (failure) to
"stopped the bleeding, closed the infection, dulled the pain" (full
success across all categories).

Channels intentionally NOT handled here:

* ``wound_healing`` — slow-tick organ HP recovery via the medical
  script (PR-C).
* ``organ_repair`` — instant HP refund on surgical-grade items
  applied during an open procedure (PR-D).

Both ride the same application path eventually, just gated on
later infrastructure that doesn't exist yet.
"""

from __future__ import annotations

import random
from typing import Optional

from world.medical.constants import (
    WOUND_CARE_BASE_DIFFICULTY,
    WOUND_CARE_BLEEDING_REDUCTION,
    WOUND_CARE_DEPTH_MODIFIER,
    WOUND_CARE_INFECTION_REDUCTION,
    WOUND_CARE_PAIN_REDUCTION,
    WOUND_CARE_PARALLEL_CATEGORIES,
    WOUND_CARE_PARTIAL_THRESHOLD,
    WOUND_CARE_SEVERITY_MODIFIERS,
    WOUND_CARE_SUCCESS_THRESHOLD,
)


# ---------------------------------------------------------------------
# Outcome literals — strings rather than enums to keep test stubs
# inspectable without an import.
# ---------------------------------------------------------------------

SUCCESS = "success"
PARTIAL = "partial"
FAILURE = "failure"


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def calculate_treatment_skill(actor) -> float:
    """G.R.I.M. medical effectiveness for treatment rolls.

    Same formula as the procedure verbs: intellect-weighted, with
    motorics contributing for steady hands.  Matches the formula at
    HEALTH_AND_SUBSTANCE_SYSTEM_SPEC line 1434.
    """
    intellect = getattr(actor, "intellect", 0) or 0
    motorics = getattr(actor, "motorics", 0) or 0
    return (intellect * 0.75) + (motorics * 0.25)


def calculate_treatment_difficulty(
    wound_severity: str,
    item_internal_effective: bool,
    is_internal_wound: bool,
) -> int:
    """Compose the treatment-roll target.

    Args:
        wound_severity: One of the keys in
            :data:`WOUND_CARE_SEVERITY_MODIFIERS` (string severity
            from wound rendering).  Unknown → treated as Moderate.
        item_internal_effective: Whether the item's effectiveness
            includes a non-zero ``organ_repair`` rating (i.e. it's
            a deep-treatment item designed for open procedures).
        is_internal_wound: Whether the wound sits at an internal-
            cavity container (head / chest / abdomen / etc. — the
            ``core.py`` ``internal_containers`` distinction).

    Adds:
        + severity modifier from the ladder
        + depth modifier when the wound is internal AND the item
          isn't internal-effective
    """
    target = WOUND_CARE_BASE_DIFFICULTY
    target += WOUND_CARE_SEVERITY_MODIFIERS.get(
        wound_severity, WOUND_CARE_SEVERITY_MODIFIERS["Moderate"]
    )
    if is_internal_wound and not item_internal_effective:
        target += WOUND_CARE_DEPTH_MODIFIER
    return target


def roll_treatment(actor, target_difficulty: int, item_rating: int) -> dict:
    """3d6 + skill + item rating vs target.

    Returns a dict with ``roll`` (the 3d6 sum), ``total`` (after
    bonuses), ``target`` (the difficulty), and ``outcome``
    (success / partial / failure based on the threshold ladder).
    """
    roll = sum(random.randint(1, 6) for _ in range(3))
    skill = calculate_treatment_skill(actor)
    total = roll + int(skill) + int(item_rating)
    if total >= WOUND_CARE_SUCCESS_THRESHOLD:
        outcome = SUCCESS
    elif total >= WOUND_CARE_PARTIAL_THRESHOLD:
        outcome = PARTIAL
    else:
        outcome = FAILURE
    return {
        "roll": roll,
        "skill": skill,
        "item_rating": item_rating,
        "total": total,
        "target": target_difficulty,
        "outcome": outcome,
    }


def damaged_organs_at_location(target, location: str) -> list:
    """Return the live ``Organ`` instances at ``location`` that have
    HP loss.  Matches by ``container`` or ``display_location`` so the
    surface-organ rule lines up with the access rule from PR-A.
    """
    state = getattr(target, "medical_state", None)
    if state is None or not hasattr(state, "organs"):
        return []
    out = []
    for organ in state.organs.values():
        if organ.current_hp >= organ.max_hp:
            continue  # Healthy — no wound to stabilize.
        container = getattr(organ, "container", None)
        display = getattr(organ, "display_location", None)
        if location in (container, display):
            out.append(organ)
    return out


def _wound_severity_from_organ(organ) -> str:
    """Map an organ's HP-loss tier to the wound severity ladder.

    Mirrors ``_determine_severity_from_damage`` in wound rendering
    closely enough for the difficulty math.  The full renderer
    accounts for organ-specific maxes; here we use the percentage of
    HP lost.
    """
    if organ.max_hp <= 0:
        return "Moderate"
    pct_lost = (organ.max_hp - organ.current_hp) / organ.max_hp
    if pct_lost >= 0.75:
        return "Critical"
    if pct_lost >= 0.5:
        return "Severe"
    if pct_lost >= 0.25:
        return "Moderate"
    return "Minor"


def _is_internal_container(container: str) -> bool:
    """Whether ``container`` is an internal body cavity.

    Uses the duck-typed match: anything not in the limb set is
    treated as internal.  Same distinction ``world/medical/core.py``
    makes for the destruction-vs-severance pipeline.
    """
    limb_containers = {
        "left_arm", "right_arm", "left_hand", "right_hand",
        "left_thigh", "right_thigh", "left_shin", "right_shin",
        "left_foot", "right_foot", "tail", "left_wing", "right_wing",
    }
    if container is None:
        return False
    if container in limb_containers:
        return False
    if "tentacle_" in container or "_leg_" in container or "_arm_" in container:
        return False
    return True


def _conditions_at_location(
    medical_state, location: str, condition_cls
) -> list:
    """Return conditions of ``condition_cls`` at ``location`` (or at
    the same location resolved via the organ's display vs container).
    """
    out = []
    for condition in getattr(medical_state, "conditions", []):
        if not isinstance(condition, condition_cls):
            continue
        if condition.location == location:
            out.append(condition)
    return out


# ---------------------------------------------------------------------
# Main dispatch
# ---------------------------------------------------------------------


def apply_wound_care(actor, target, item, location: str) -> dict:
    """Apply a wound_care item at ``location`` on ``target``.

    Returns a result dict with ``stabilized`` (bool), ``rolls``
    (per-category result dicts), ``messages`` (list of user-facing
    strings the caller can msg), and ``no_op_reason`` when nothing
    happens (already stabilized, no wound at location, etc.).

    Side effects:
        * Marks any damaged organs at the location as stabilized.
        * Reduces BleedingCondition / InfectionCondition /
          PainCondition severities at the location per the per-
          category roll outcome.
        * Consumes one use of ``item`` (decrements ``uses_left``).
    """
    result = {
        "stabilized": False,
        "rolls": {},
        "messages": [],
        "no_op_reason": None,
    }

    wounded_organs = damaged_organs_at_location(target, location)
    if not wounded_organs:
        result["no_op_reason"] = "no_wound"
        result["messages"].append(
            f"There's no wound at "
            f"{location.replace('_', ' ')} to treat."
        )
        return result

    # If any wounded organ at this location is already stabilized,
    # the location as a whole is being held — re-applying does
    # nothing useful.  Triage hint to the caller.
    if any(getattr(o, "stabilized", False) for o in wounded_organs):
        result["no_op_reason"] = "already_stabilized"
        result["messages"].append(
            f"The wound at {location.replace('_', ' ')} is already "
            f"stabilized — they need a surgeon now, not more dressing."
        )
        return result

    # Determine the difficulty floor for the rolls.  We use the worst
    # (highest-severity) wound at the location as the target driver,
    # so stabilizing a critically damaged organ is harder than a
    # minor one even if both share the location.
    worst_severity = max(
        (_wound_severity_from_organ(o) for o in wounded_organs),
        key=lambda s: WOUND_CARE_SEVERITY_MODIFIERS.get(s, 0),
    )
    container = wounded_organs[0].container
    is_internal_wound = _is_internal_container(container)

    effectiveness = _item_effectiveness(item)
    item_internal_effective = bool(effectiveness.get("organ_repair", 0))

    difficulty = calculate_treatment_difficulty(
        wound_severity=worst_severity,
        item_internal_effective=item_internal_effective,
        is_internal_wound=is_internal_wound,
    )

    # Resolve each category in parallel.  Each gets its own roll
    # against the same difficulty target, using the item's per-
    # category effectiveness rating as the modifier.
    for category in WOUND_CARE_PARALLEL_CATEGORIES:
        rating = int(effectiveness.get(category, 0))
        roll_result = roll_treatment(actor, difficulty, rating)
        result["rolls"][category] = roll_result
        _apply_category_outcome(
            target, location, category, roll_result["outcome"], result,
        )

    # Stabilization is unconditional on any application.  Even a
    # failed roll across all categories still pins the wound at its
    # current state — the act of dressing a wound stops it from
    # getting worse, even if the surgeon will need to redo the
    # work later.
    #
    # PR-C: also register the dressing's wound_healing rating on
    # each stabilized organ so the medical script's healing tick
    # can restore HP over time.  Rate is stored on the organ as a
    # number (not an item reference) so item depletion doesn't
    # affect ongoing recovery.
    wound_healing_rating = int(effectiveness.get("wound_healing", 0) or 0)
    for organ in wounded_organs:
        organ.stabilized = True
        organ.dressing_rate = wound_healing_rating
    result["stabilized"] = True
    result["messages"].append(
        f"The wound at {location.replace('_', ' ')} is stabilized."
    )

    # PR-C: ensure the medical script is running so the healing
    # tick can fire.  Idempotent — returns the existing script if
    # one is already present.  Skips on test stubs that don't have
    # the ``scripts`` accessor.
    if wound_healing_rating > 0 and hasattr(target, "scripts"):
        try:
            from world.medical.script import start_medical_script
            start_medical_script(target)
        except Exception:
            # Don't let script-start failures break the treatment
            # outcome — the stabilization landed regardless.
            pass

    # Consume one use of the item.
    _consume_use(item)

    return result


def _apply_category_outcome(
    target, location: str, category: str, outcome: str, result: dict
) -> None:
    """Side-effect: mutate the relevant condition at ``location`` per
    the per-category outcome.  Appends a user-facing line to
    ``result["messages"]``.
    """
    from world.medical.conditions import (
        BleedingCondition,
        InfectionCondition,
        PainCondition,
    )

    medical_state = getattr(target, "medical_state", None)
    if medical_state is None:
        return

    if category == "bleeding":
        conditions = _conditions_at_location(
            medical_state, location, BleedingCondition,
        )
        reduction = _category_reduction("bleeding", outcome)
        for cond in conditions:
            cond.severity = max(0, cond.severity - reduction)
        if conditions and reduction > 0:
            result["messages"].append(
                f"Bleeding at {location.replace('_', ' ')} "
                f"reduced by {reduction}."
            )

    elif category == "infection":
        conditions = _conditions_at_location(
            medical_state, location, InfectionCondition,
        )
        reduction = _category_reduction("infection", outcome)
        for cond in conditions:
            cond.severity = max(0, cond.severity - reduction)
        if conditions and reduction > 0:
            result["messages"].append(
                f"Infection at {location.replace('_', ' ')} "
                f"reduced by {reduction}."
            )

    elif category == "pain":
        conditions = _conditions_at_location(
            medical_state, location, PainCondition,
        )
        reduction = _category_reduction("pain", outcome)
        for cond in conditions:
            cond.severity = max(0, cond.severity - reduction)
        if conditions and reduction > 0:
            result["messages"].append(
                f"Pain at {location.replace('_', ' ')} "
                f"reduced by {reduction}."
            )


def _category_reduction(category: str, outcome: str) -> int:
    """Effect amount for a category given its roll outcome.

    Full effect on success, half (rounded down) on partial, zero on
    failure — the stabilization channel still fires on failure but
    no per-category reduction lands.
    """
    base = {
        "bleeding": WOUND_CARE_BLEEDING_REDUCTION,
        "infection": WOUND_CARE_INFECTION_REDUCTION,
        "pain": WOUND_CARE_PAIN_REDUCTION,
    }.get(category, 0)
    if outcome == SUCCESS:
        return base
    if outcome == PARTIAL:
        return base // 2
    return 0


def _item_effectiveness(item) -> dict:
    """Return the item's ``effectiveness`` dict, or empty when absent.

    Items declare effectiveness as an AttributeProperty / db attr;
    we read defensively because some test stubs use plain dicts.
    """
    attrs = getattr(item, "attributes", None)
    if attrs is None:
        # Direct attribute access for plain test stubs.
        return getattr(item, "effectiveness", {}) or {}
    if hasattr(attrs, "get"):
        return attrs.get("effectiveness") or {}
    return {}


def _consume_use(item) -> None:
    """Decrement ``uses_left`` on the item.  Items without
    ``uses_left`` (single-use disposables relying on deletion, or
    legacy items) are left alone — the caller is responsible for
    those cases."""
    attrs = getattr(item, "attributes", None)
    if attrs is None or not hasattr(attrs, "get"):
        return
    uses = attrs.get("uses_left")
    if isinstance(uses, int) and uses > 0:
        attrs.add("uses_left", uses - 1)
