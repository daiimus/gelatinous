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
* ``pain_inflict`` — the first harmful kind (#498): adds a
  :class:`~world.medical.conditions.PainCondition` of ``magnitude``
  severity.  Rides the existing pain machinery — it decays on the
  medical tick, feeds the consciousness cliff, and shows in
  ``diagnose`` like any wound pain.

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

import random
import time
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
class ToleranceSpec:
    """Per-substance tolerance curve (issue #485).

    Each dose adds one tolerance point; points decay lazily by
    wall-clock hours since the last update (no tick — computed in
    ``apply_substance``).  Each full ``points_per_level`` of
    standing points is one tolerance level, and each level shaves
    one point of per-dose effect magnitude (floor 0).
    """

    points_per_level: int
    decay_per_hour: float
    max_level: int


@dataclass(frozen=True)
class AddictionSpec:
    """Per-substance addiction parameters (issue #485, flavor-first).

    Crossing ``threshold_doses`` lifetime doses adds a persistent
    :class:`~world.medical.conditions.AddictionCondition`.  Dormant
    while fed; ``craving_after`` seconds without a dose surfaces
    periodic craving prose (``prose_key`` bank) and a mild ache.
    """

    threshold_doses: int
    craving_after: int
    prose_key: str


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
    tolerance: Optional[ToleranceSpec] = None
    addiction: Optional[AddictionSpec] = None


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
        tolerance=ToleranceSpec(
            points_per_level=15, decay_per_hour=0.5, max_level=1,
        ),
        addiction=AddictionSpec(
            threshold_doses=30, craving_after=7200, prose_key="tobacco",
        ),
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
        tolerance=ToleranceSpec(
            points_per_level=15, decay_per_hour=0.5, max_level=1,
        ),
        addiction=AddictionSpec(
            threshold_doses=25, craving_after=7200, prose_key="tobacco",
        ),
    ),
    "cannabis": Substance(
        id="cannabis",
        display_name="cannabis",
        effects=(
            # Mellow analgesic drift — kinder than tobacco on the
            # pain, heavier on the eyelids.
            SubstanceEffect(kind="pain_relief", magnitude=1),
            SubstanceEffect(kind="sedation", magnitude=1, max_stack=2),
        ),
        flavor_bank_key="cannabis",
        tolerance=ToleranceSpec(
            points_per_level=10, decay_per_hour=1.0, max_level=1,
        ),
        addiction=AddictionSpec(
            threshold_doses=60, craving_after=14400, prose_key="cannabis",
        ),
    ),
    "alcohol": Substance(
        id="alcohol",
        display_name="alcohol",
        effects=(
            # Numbs more than it heals; the cap of 4 (0.60
            # consciousness penalty) is properly drunk — heavily
            # impaired, still standing.  Blackout stays out of v1.
            SubstanceEffect(kind="pain_relief", magnitude=1),
            SubstanceEffect(kind="sedation", magnitude=1, max_stack=4),
        ),
        flavor_bank_key="alcohol",
        tolerance=ToleranceSpec(
            points_per_level=12, decay_per_hour=0.75, max_level=1,
        ),
        addiction=AddictionSpec(
            threshold_doses=40, craving_after=10800, prose_key="alcohol",
        ),
    ),
    "guttervenom": Substance(
        id="guttervenom",
        display_name="guttervenom",
        effects=(
            # A weapon, not a habit: searing systemic pain plus a
            # woozy dimming as the body fights it.  No tolerance, no
            # addiction — nobody chases this.
            SubstanceEffect(kind="pain_inflict", magnitude=3),
            SubstanceEffect(kind="sedation", magnitude=1, max_stack=3),
        ),
        flavor_bank_key="guttervenom",
    ),
    "opium": Substance(
        id="opium",
        display_name="opium",
        effects=(
            # The serious analgesic — three points of pain relief per
            # dose, and a sedative pull that can take a chasing user
            # to the nod (cap 5 = 0.75 consciousness penalty: barely
            # present, not unconscious).  Its danger is its identity.
            SubstanceEffect(kind="pain_relief", magnitude=3),
            SubstanceEffect(kind="sedation", magnitude=2, max_stack=5),
        ),
        flavor_bank_key="opium",
        tolerance=ToleranceSpec(
            points_per_level=8, decay_per_hour=0.25, max_level=2,
        ),
        addiction=AddictionSpec(
            threshold_doses=10, craving_after=5400, prose_key="opium",
        ),
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
    "pain_inflict": "Fire spreads outward from the injection site.",
}

#: Shown once per application when tolerance zeroed out an effect
#: that would otherwise have landed.
TOLERANCE_FEEDBACK = "It doesn't hit like it used to."

#: pain_inflict's landed-effect line (harmful effects get their own
#: voice — EFFECT_FEEDBACK below covers the beneficial kinds).

#: Shown once, the moment an addiction condition first forms.
ADDICTION_ONSET_FEEDBACK = (
    "Somewhere along the line, this stopped being optional."
)

#: Craving prose banks, keyed by ``AddictionSpec.prose_key``.  Read
#: by ``AddictionCondition.tick_effect`` via ``pick_craving_line``.
CRAVING_PROSE: dict[str, list[str]] = {
    "generic": [
        "A want with no name works its way up from somewhere below "
        "your ribs.",
        "Your hands keep looking for something to do. You know "
        "exactly what.",
    ],
    "cannabis": [
        "The world has corners again. You remember when it didn't.",
        "Everything is slightly too loud and nothing is funny. This "
        "feels correctable.",
        "Your thoughts keep arriving on time. You miss when they "
        "wandered in late, smiling.",
    ],
    "alcohol": [
        "Your mouth is dry in a way water has repeatedly failed to "
        "fix.",
        "There's a glass-shaped absence in your hand. It has opinions.",
        "Sobriety is a fluorescent light. You remember somewhere "
        "dimmer, warmer.",
        "Your hands have a fine grammar of tremors this morning, "
        "spelling out a familiar request.",
    ],
    "opium": [
        "The pain isn't worse. The world is just made of it again.",
        "Somewhere under your skin, a tide has gone out, and "
        "everything the water covered is bare and aching.",
        "You can feel your whole skeleton. No one should feel their "
        "whole skeleton.",
        "The smoke knew your name. Everything since has been "
        "introductions.",
    ],
    "tobacco": [
        "Your fingers miss the weight of a cigarette. They make the "
        "shape of one anyway.",
        "Someone, somewhere, is smoking. You can't smell it. You can "
        "feel it.",
        "The space between your index and middle finger aches with "
        "vacancy.",
        "You catch yourself inhaling slow through pursed lips. "
        "Nothing arrives.",
    ],
}


def pick_craving_line(prose_key: str) -> str | None:
    """Return a random craving line for ``prose_key`` (falls back to
    the generic bank; None only if both banks are missing)."""
    bank = CRAVING_PROSE.get(prose_key) or CRAVING_PROSE.get("generic")
    return random.choice(bank) if bank else None


# ---------------------------------------------------------------------
# Tolerance bookkeeping (lazy decay — no tick)
# ---------------------------------------------------------------------


def _tolerance_level(consumer, substance_id: str, spec: ToleranceSpec) -> int:
    """Return the consumer's current tolerance level for a substance.

    Decays standing points by wall-clock hours since the last update,
    writes the decayed value back, and converts points to a level.
    """
    db = getattr(consumer, "db", None)
    if db is None:
        return 0
    store = getattr(db, "substance_tolerance", None)
    if store is None:
        return 0
    entry = store.get(substance_id)
    if not entry:
        return 0
    now = time.time()
    elapsed_hours = max(0.0, (now - entry.get("updated", now)) / 3600.0)
    points = max(0.0, entry.get("points", 0.0) - elapsed_hours * spec.decay_per_hour)
    entry["points"] = points
    entry["updated"] = now
    return min(spec.max_level, int(points // spec.points_per_level))


def _record_tolerance_dose(consumer, substance_id: str) -> None:
    """Add one tolerance point for this dose."""
    db = getattr(consumer, "db", None)
    if db is None:
        return
    store = getattr(db, "substance_tolerance", None)
    if store is None:
        db.substance_tolerance = {
            substance_id: {"points": 1.0, "updated": time.time()},
        }
        return
    entry = store.get(substance_id)
    if entry is None:
        store[substance_id] = {"points": 1.0, "updated": time.time()}
    else:
        entry["points"] = entry.get("points", 0.0) + 1.0
        entry["updated"] = time.time()


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


def _apply_pain_inflict(medical_state, magnitude: int) -> int:
    """Add a PainCondition of ``magnitude`` severity (#498).

    The harmful mirror of ``pain_relief`` — a new pain condition
    rides the existing machinery: medical-tick decay, consciousness
    penalty above the pain threshold, diagnose visibility.

    Returns:
        Severity actually inflicted.
    """
    from world.medical.conditions import PainCondition

    if magnitude <= 0:
        return 0
    medical_state.add_condition(PainCondition(magnitude, location=None))
    return magnitude


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

    # Tolerance (#485): standing level shaves per-dose magnitude.
    tolerance_level = 0
    if entry.tolerance is not None:
        tolerance_level = _tolerance_level(consumer, substance_id, entry.tolerance)

    tolerance_blunted = False
    for _ in range(max(1, int(doses))):
        for effect in entry.effects:
            magnitude = max(0, effect.magnitude - tolerance_level)
            if magnitude <= 0 < effect.magnitude:
                tolerance_blunted = True
                continue
            if effect.kind == "pain_relief":
                landed = _apply_pain_relief(medical_state, magnitude)
            elif effect.kind == "sedation":
                landed = _apply_sedation(
                    medical_state, magnitude, effect.max_stack,
                )
            elif effect.kind == "pain_inflict":
                landed = _apply_pain_inflict(medical_state, magnitude)
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
    if tolerance_blunted:
        result["feedback"].append(TOLERANCE_FEEDBACK)

    # Dose bookkeeping — lifetime history feeding tolerance/addiction.
    lifetime_doses = int(doses)
    db = getattr(consumer, "db", None)
    if db is not None:
        doses_map = getattr(db, "substance_doses", None)
        if doses_map is None:
            db.substance_doses = {substance_id: int(doses)}
        else:
            doses_map[substance_id] = (
                int(doses_map.get(substance_id, 0)) + int(doses)
            )
            lifetime_doses = int(doses_map[substance_id])

    # Tolerance accrues per application (#485).
    if entry.tolerance is not None:
        for _ in range(max(1, int(doses))):
            _record_tolerance_dose(consumer, substance_id)

    # Addiction (#485, flavor-first): feed an existing habit, or form
    # one once the lifetime threshold is crossed.
    if entry.addiction is not None:
        existing = [
            c for c in (getattr(medical_state, "conditions", []) or [])
            if getattr(c, "condition_type", None) == "addiction"
            and getattr(c, "substance_id", None) == substance_id
        ]
        if existing:
            existing[0].record_dose()
        elif lifetime_doses >= entry.addiction.threshold_doses:
            from world.medical.conditions import AddictionCondition
            condition = AddictionCondition(
                substance_id,
                prose_key=entry.addiction.prose_key,
                craving_after=entry.addiction.craving_after,
            )
            # add_condition starts the condition ticker itself when
            # the state has a character reference.
            medical_state.add_condition(condition)
            result["feedback"].append(ADDICTION_ONSET_FEEDBACK)

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
