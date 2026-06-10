"""Substance registry and effect pipeline (issue #458).

Substances *declare* their effects; the existing medical condition
system *applies and ticks* them.  No new runtime infrastructure —
``apply_substance`` translates declarations into mutations on the
consumer's :class:`~world.medical.core.MedicalState` and lets the
medical script's 12-second tick handle decay/recovery from there.

Effect vocabulary (v1) — deliberately limited to what the medical
system supports today:

* ``pain_relief`` — shaves severity off existing ``PainCondition``
  entries.  A smoke takes the edge off; an opiate (later) takes a
  lot more off.  No-op when the consumer isn't in pain.
* ``sedation`` — adds or stacks a
  :class:`~world.medical.conditions.ConsciousnessSuppressionCondition`
  with ``suppression_type="sedative"``.  Stacking is capped by the
  effect's ``max_stack`` so chain-smoking can't knock a character
  unconscious unboundedly — the cap is the substance's ceiling on
  total sedative severity from any source.

Future vocabulary (tolerance, addiction, stimulation, euphoria,
organ damage) lands in follow-up PRs per
``specs/SUBSTANCES_AND_DELIVERY_SPEC.md`` §5.

Dose tracking: every successful ``apply_substance`` increments
``consumer.db.substance_doses[substance_id]``.  Nothing consumes
this yet — it's the substrate hook for the future tolerance /
addiction system, recorded now so the data exists when that system
arrives.  One descriptor write per dose is a meaningful-event
write, consistent with the storage-patterns guidance.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------
# Declaration dataclasses
# ---------------------------------------------------------------------


@dataclass(frozen=True)
class SubstanceEffect:
    """One declared per-dose effect.

    Attributes:
        kind: Effect vocabulary entry — ``"pain_relief"`` or
            ``"sedation"`` in v1.
        magnitude: Severity points applied per dose.
        max_stack: For stacking effects (sedation), the cap on the
            consumer's *total* severity from this effect kind.
            Ignored for non-stacking effects (pain_relief shaves
            and bottoms out at zero naturally).
    """

    kind: str
    magnitude: int
    max_stack: int = 0


@dataclass(frozen=True)
class Substance:
    """A registered substance.

    Attributes:
        id: Registry key.  Items reference this via ``db.substance``.
        display_name: Human-readable name for messages / inspection.
        effects: Per-dose effects, applied in order.
        flavor_bank_key: Which flavor bank the delivery command's
            message picker uses (see ``world/smoke.py:SMOKE_MESSAGES``
            for the smoke banks).
    """

    id: str
    display_name: str
    effects: tuple[SubstanceEffect, ...]
    flavor_bank_key: str


# ---------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------

SUBSTANCES: dict[str, Substance] = {
    "tobacco_neutral": Substance(
        id="tobacco_neutral",
        display_name="tobacco",
        effects=(
            # A smoke takes the edge off — one point of pain relief
            # per puff.  Pure no-op on a pain-free consumer.
            SubstanceEffect(kind="pain_relief", magnitude=1),
        ),
        flavor_bank_key="tobacco_neutral",
    ),
    "tobacco_noir": Substance(
        id="tobacco_noir",
        display_name="Noir tobacco",
        effects=(
            SubstanceEffect(kind="pain_relief", magnitude=1),
            # "Smells of something older than tobacco."  Mild
            # sedative bite, capped at 2 total severity (0.30
            # consciousness penalty) — woozy, never blackout.
            SubstanceEffect(kind="sedation", magnitude=1, max_stack=2),
        ),
        flavor_bank_key="tobacco_noir",
    ),
}


def get_substance_entry(substance_id: str | None) -> Optional[Substance]:
    """Return the registry entry for ``substance_id``, or ``None``.

    Unknown / missing ids are not an error — items with no (or an
    unregistered) substance simply have no pharmacology.  Flavor
    banks have their own fallback path in the message pickers.
    """
    if not substance_id:
        return None
    return SUBSTANCES.get(substance_id)


# ---------------------------------------------------------------------
# Player-facing feedback per effect kind
# ---------------------------------------------------------------------
#
# Rendered by the delivery command when an effect actually landed
# (magnitude > 0 after caps).  Deliberately subtle — the flavor
# message carries the scene; this line carries the mechanics.

EFFECT_FEEDBACK: dict[str, str] = {
    "pain_relief": "The ache dulls a little.",
    "sedation": "A slow heaviness settles behind your eyes.",
}


# ---------------------------------------------------------------------
# Effect pipeline
# ---------------------------------------------------------------------


def _apply_pain_relief(medical_state, magnitude: int) -> int:
    """Shave up to ``magnitude`` severity off existing pain.

    Walks the consumer's ``PainCondition`` entries in list order,
    reducing each until the budget is spent.  Conditions that hit
    zero are left for the medical script's ``should_end`` sweep to
    remove on its next tick.

    Returns:
        Total severity actually relieved (0 when pain-free).
    """
    relieved = 0
    budget = magnitude
    for condition in getattr(medical_state, "conditions", []) or []:
        if budget <= 0:
            break
        if getattr(condition, "condition_type", None) != "pain":
            continue
        severity = int(getattr(condition, "severity", 0) or 0)
        if severity <= 0:
            continue
        shave = min(budget, severity)
        condition.severity = severity - shave
        budget -= shave
        relieved += shave
    return relieved


def _apply_sedation(medical_state, magnitude: int, max_stack: int) -> int:
    """Add or stack sedative consciousness suppression, capped.

    The cap applies to the consumer's **total** severity across
    sedative-typed suppression conditions — so two different
    sedative substances share one ceiling rather than each getting
    their own.  Conservative by design; per-substance source
    attribution can come with the tolerance work.

    Returns:
        Severity actually added after the cap (0 when at cap).
    """
    from world.medical.conditions import ConsciousnessSuppressionCondition

    existing = [
        c for c in (getattr(medical_state, "conditions", []) or [])
        if getattr(c, "condition_type", None) == "consciousness_suppression"
        and getattr(c, "suppression_type", None) == "sedative"
    ]
    current_total = sum(int(getattr(c, "severity", 0) or 0) for c in existing)
    headroom = max(0, max_stack - current_total)
    add = min(magnitude, headroom)
    if add <= 0:
        return 0

    if existing:
        condition = existing[0]
        condition.severity = int(condition.severity) + add
        # Keep the cached penalty in sync — the constructor formula
        # (0.15 per severity point, capped at 1.0).
        condition.consciousness_penalty = min(
            1.0, condition.severity * 0.15,
        )
    else:
        condition = ConsciousnessSuppressionCondition(
            add, suppression_type="sedative",
        )
        medical_state.add_condition(condition)
    return add


def apply_substance(consumer, substance_id: str | None, *, doses: int = 1) -> dict:
    """Apply ``doses`` of a substance to ``consumer``.

    The single entry point delivery commands call after their own
    validation (item in hand, lit, etc.).  Translates the
    substance's declared effects into medical-state mutations,
    records the dose, refreshes vitals, and flushes.

    Args:
        consumer: Character receiving the substance.  Must expose
            ``medical_state``; consumers without one (objects,
            corpses) no-op safely.
        substance_id: Registry key, usually from the item's
            ``db.substance``.  Unknown ids no-op (flavor-only
            items are legitimate).
        doses: Number of doses to apply (default one — one puff,
            one sip, one pill).

    Returns:
        Summary dict::

            {
                "substance": <id or None>,
                "known": bool,          # id resolved in registry
                "applied": {kind: total_magnitude, ...},
                "feedback": [str, ...], # player-facing lines for
                                        # effects that landed
            }
    """
    result = {
        "substance": substance_id,
        "known": False,
        "applied": {},
        "feedback": [],
    }
    entry = get_substance_entry(substance_id)
    if entry is None:
        return result
    result["known"] = True

    medical_state = getattr(consumer, "medical_state", None)
    if medical_state is None:
        return result

    for _ in range(max(1, int(doses))):
        for effect in entry.effects:
            if effect.kind == "pain_relief":
                landed = _apply_pain_relief(medical_state, effect.magnitude)
            elif effect.kind == "sedation":
                landed = _apply_sedation(
                    medical_state, effect.magnitude, effect.max_stack,
                )
            else:
                # Unknown effect kind — declared ahead of its
                # implementation.  Skip rather than crash so the
                # registry can grow ahead of the pipeline.
                continue
            if landed > 0:
                result["applied"][effect.kind] = (
                    result["applied"].get(effect.kind, 0) + landed
                )

    # Player-facing feedback for effects that actually landed.
    for kind in result["applied"]:
        line = EFFECT_FEEDBACK.get(kind)
        if line:
            result["feedback"].append(line)

    # Dose bookkeeping — substrate for future tolerance/addiction.
    db = getattr(consumer, "db", None)
    if db is not None:
        doses_map = getattr(db, "substance_doses", None)
        if doses_map is None:
            db.substance_doses = {substance_id: int(doses)}
        else:
            doses_map[substance_id] = (
                int(doses_map.get(substance_id, 0)) + int(doses)
            )

    # Refresh vitals so consciousness reflects new penalties
    # immediately, then flush — dose application is a meaningful
    # event per the storage-patterns guidance.
    update_vitals = getattr(medical_state, "update_vital_signs", None)
    if callable(update_vitals):
        update_vitals()
    save = getattr(consumer, "save_medical_state", None)
    if callable(save):
        save()

    return result
