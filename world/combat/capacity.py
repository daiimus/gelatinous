"""
Combat capacity consumers (CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC §9 layer 1).

Body capacities (``world/medical/core.py`` ``calculate_body_capacity``) are
computed from organ health but, historically, only the *lethal* ones gated
anything.  This module is the first **consumer** of a performance capacity:
``sight`` multiplies a character's combat hit math.

The model (spec §1, decided):

* **Multiplicative** — the capacity scales the GRIM-derived result, it does
  not add/subtract a flat modifier.  Here that means the attacker's motorics
  skill term is multiplied by a 0.0–1.0 factor before it joins the d20.
* **Hybrid curve** — graduated falloff with redundancy protection: losing one
  of a redundant pair (one eye) costs little; losing the whole capacity (blind)
  falls off a cliff.  Encoded as a transparent piecewise-linear curve through
  the anchor points the spec calls out, so it is trivially tunable.
* **Suppressible named-effect** — a condition (the integration seam for chrome
  / biotech, e.g. a cyber sense-enhancer or a "blindsight" effect) can suppress
  the penalty entirely, restoring the capacity to full.  Riding the condition
  system means one augment is coherent across every consumer at once.

``sight`` is whole-body (you do not *wield* eyes), so it is the clean first
slice and dodges the per-effector resolver (spec §6) that manipulation/moving
will need.

Fail-open: anything without a readable medical state (many mobs, test stubs)
takes no penalty.  Absence of the medical model must never blind a combatant.
"""

from __future__ import annotations

# The condition_type that, when present on a combatant, suppresses the sight
# penalty and treats sight as fully present (spec §3 augment hook).  Nothing
# adds this condition yet — the cyber sense-enhancer augment is a later layer —
# but the consumer honours the seam now so the augment is pure content when it
# lands.
SIGHT_OVERRIDE_CONDITION = "sight_override"

# Piecewise-linear curves mapping raw ``sight`` capacity (0.0–1.0) to a hit
# multiplier.  Anchors are (raw_capacity, factor), ascending by capacity.
# Magnitudes are illustrative/tunable (spec §11) — the *shape* is the contract.
#
# Ranged (the big one): steep falloff with redundancy protection.  Two eyes =
# no penalty; one eye ≈ 0.65 (depth perception gone, but you can still aim);
# blind ≈ a near-useless 0.05 floor (point-blank-or-nothing).
SIGHT_CURVE_RANGED = ((0.0, 0.05), (0.5, 0.65), (1.0, 1.0))

# Melee (light): you can grab and swing by feel.  One eye costs nothing; only
# full blindness imposes a modest penalty.
SIGHT_CURVE_MELEE = ((0.0, 0.70), (0.5, 1.0), (1.0, 1.0))


def _piecewise(raw: float, anchors) -> float:
    """Linear-interpolate *raw* (clamped 0–1) through ascending *anchors*."""
    raw = max(0.0, min(1.0, raw))
    lo_x, lo_y = anchors[0]
    if raw <= lo_x:
        return lo_y
    for hi_x, hi_y in anchors[1:]:
        if raw <= hi_x:
            span = hi_x - lo_x
            if span <= 0:
                return hi_y
            t = (raw - lo_x) / span
            return lo_y + t * (hi_y - lo_y)
        lo_x, lo_y = hi_x, hi_y
    return anchors[-1][1]


def _read_capacity(character, name: str):
    """Return raw body capacity *name* (0.0–1.0), or ``None`` if unreadable.

    ``None`` signals "no medical model" — the caller fails open.
    """
    state = getattr(character, "medical_state", None)
    if state is None:
        return None
    calc = getattr(state, "calculate_body_capacity", None)
    if not callable(calc):
        return None
    try:
        return calc(name)
    except Exception:
        return None


def _has_override(character, condition_type: str) -> bool:
    """True if a condition suppresses a capacity penalty (chrome/biotech seam)."""
    state = getattr(character, "medical_state", None)
    getter = getattr(state, "get_conditions_by_type", None)
    if not callable(getter):
        return False
    try:
        return bool(getter(condition_type))
    except Exception:
        return False


def sight_hit_factor(character, is_ranged: bool) -> float:
    """Multiplier applied to *character*'s motorics skill term when attacking.

    Args:
        character: the attacker.
        is_ranged: True for ranged attacks (steep curve), False for melee
            (light curve — sight only matters when fully blind).

    Returns:
        A factor in ``[0.0, 1.0]``.  ``1.0`` means no sight penalty (full
        sight, no medical model, or an active suppressor).
    """
    if _has_override(character, SIGHT_OVERRIDE_CONDITION):
        return 1.0

    raw = _read_capacity(character, "sight")
    if raw is None:
        return 1.0  # fail-open: no medical model, no penalty

    curve = SIGHT_CURVE_RANGED if is_ranged else SIGHT_CURVE_MELEE
    return _piecewise(raw, curve)


# --------------------------------------------------------------------------
# Moving → dodge (CAPACITY_CONSUMERS spec §6.2/§6.3 — defensive half)
# --------------------------------------------------------------------------
# Unlike manipulation, ``moving`` is whole-body and already species-normalized
# (``calculate_body_capacity`` weights leg organs per anatomy: a human losing
# one of two legs ≫ a rat losing one of four). It drives the defensive side of
# the combat stack — dodge/evasion = motorics × moving.
#
# Hard floor at the species table's 0.15 incapacitation_threshold: below it you
# can't locomote (drag yourself), so evasion collapses to a flail. Graceful
# above. Magnitudes tunable (spec §11).
MOVING_INCAPACITATION_THRESHOLD = 0.15
MOVING_CURVE_DODGE = ((0.0, 0.10), (0.15, 0.25), (1.0, 1.0))

# The chrome-legs seam — a cyber locomotion augment suppresses the dodge
# penalty. Nothing sets it yet; honoured now so the augment is pure content.
MOVING_OVERRIDE_CONDITION = "moving_override"


def moving_dodge_factor(character) -> float:
    """Multiplier applied to *character*'s motorics when dodging/evading.

    Returns a factor in ``[0.0, 1.0]``; ``1.0`` means no penalty (full
    locomotion, no medical model, or an active suppressor).
    """
    if _has_override(character, MOVING_OVERRIDE_CONDITION):
        return 1.0

    raw = _read_capacity(character, "moving")
    if raw is None:
        return 1.0  # fail-open

    return _piecewise(raw, MOVING_CURVE_DODGE)


# --------------------------------------------------------------------------
# Manipulation → hit (CAPACITY_CONSUMERS spec §6.1/§6.3 — offensive half)
# --------------------------------------------------------------------------
# Unlike sight/moving, manipulation is NOT body-wide: weapon handling depends on
# the *specific hand(s) gripping the weapon*, not a body average (§6.1 Q1). A
# one-armed character with a pistol in their good hand fights at FULL accuracy —
# the missing arm is irrelevant to that weapon. So we scope the capacity to the
# gripping hand's limb chain via MedicalState.calculate_capacity_scoped.
#
# Breadth from surplus arms (Q2: initiative / disarm-resist / loadout) is a
# separate output and a future combat revision — not modelled here.
MANIPULATION_CURVE = ((0.0, 0.20), (0.5, 0.65), (1.0, 1.0))
MANIPULATION_OVERRIDE_CONDITION = "manipulation_override"


def _gripping_slots(attacker, weapon):
    """The grasping slots currently holding *weapon* (e.g. ``["left_hand"]``)."""
    hands = getattr(attacker, "hands", None) or {}
    try:
        return [slot for slot, item in hands.items() if item is weapon]
    except Exception:
        return []


def _limb_ancestors(attacker, slot):
    """Containers whose organs power *slot* — the slot + its upstream chain.

    Inverts the species ``limb_downstream_chain``: every container whose
    downstream set includes *slot* (e.g. ``left_hand`` → ``{left_arm,
    left_hand}``), so both the hand bones and the arm bones count.
    """
    species = getattr(getattr(attacker, "db", None), "species", None)
    try:
        from world.anatomy import get_species_limb_downstream_chain
        chain = get_species_limb_downstream_chain(species) or {}
    except Exception:
        chain = {}
    ancestors = {c for c, downstream in chain.items() if slot in downstream}
    ancestors.add(slot)  # a grasping container may itself hold organs (e.g. tail)
    return ancestors


def manipulation_hit_factor(attacker, weapon) -> float:
    """Multiplier on *attacker*'s motorics from the hand(s) gripping *weapon*.

    Per-effector (§6.1): scoped to the gripping hand's limb chain, not body-wide.
    When two hands grip one weapon, the weaker hand drags it (``min`` for now;
    exact min-vs-blend is TBD, spec §10). Falls back to body-wide manipulation
    for unarmed / natural-weapon / undeterminable grips. Fail-open to ``1.0``.
    """
    if _has_override(attacker, MANIPULATION_OVERRIDE_CONDITION):
        return 1.0

    state = getattr(attacker, "medical_state", None)
    scoped = getattr(state, "calculate_capacity_scoped", None)

    gripping = _gripping_slots(attacker, weapon) if weapon is not None else []
    if not gripping or not callable(scoped):
        # Unarmed, natural weapon, or no scoped model — body-wide manipulation.
        raw = _read_capacity(attacker, "manipulation")
        if raw is None:
            return 1.0
        return _piecewise(raw, MANIPULATION_CURVE)

    caps = []
    for slot in gripping:
        try:
            caps.append(scoped("manipulation", _limb_ancestors(attacker, slot)))
        except Exception:
            return 1.0  # fail-open on any anatomy lookup failure
    if not caps:
        return 1.0
    return _piecewise(min(caps), MANIPULATION_CURVE)
