"""
Perception gating — which sensory channels a looker currently receives
(CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC §5).

The LOOK Sensory Category Framework (``LOOK_COMMAND_SPEC.md``) already tags
ambient content (weather, crowd) by sense — visual / auditory / olfactory /
tactile / atmospheric — and was built to "show reduced content" to players with
sensory limitations. This module supplies the missing input: its ``can_see`` /
``can_hear`` / ``can_smell`` primitives read a looker's ``sight`` / ``hearing`` /
``smell`` capacities (honouring the chrome-eye / cyber-ear / cyber-nose override
seams) and ``blocked_senses`` reports which sense categories are *blocked*.
(``world.voice`` consumes the same primitives for its speech-attribution chain.)

Scope (decided, spec §5): this gates the *additive* sensory pools. The single-
blob base room description stays valid as the visual layer — full base-desc
sense decomposition is a future authoring lift, not a prerequisite.

``sight`` → visual, ``hearing`` → auditory, ``smell`` → olfactory (the nose
organ). Tactile / gustatory / atmospheric are never gated here: ambient touch is
whole-body sensation that survives losing a hand (a future *examine-by-touch* of
an object would gate on hands instead), and atmospheric is the multi-sense mood
catch-all. Fails open: a looker with no readable capacities perceives everything.
"""

from __future__ import annotations

from typing import Any

from world.combat.capacity import SIGHT_OVERRIDE_CONDITION


# --------------------------------------------------------------------------
# Capacity / condition reads (low-level helpers, shared with world.voice)
# --------------------------------------------------------------------------
def _read_capacity(char: Any, name: str) -> float | None:
    """Raw body capacity *name* (0.0–1.0) for *char*, or ``None`` if unreadable.

    ``None`` signals "no medical model" — callers fail open. Only a real number
    is returned; anything else (e.g. a test mock) yields ``None``, mirroring
    ``world.combat.dice.get_character_stat``.
    """
    state = getattr(char, "medical_state", None)
    calc = getattr(state, "calculate_body_capacity", None)
    if not callable(calc):
        return None
    try:
        value = calc(name)
    except Exception:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    return value


def _has_condition(char: Any, condition_type: str) -> bool:
    """True if *char* carries an active condition of *condition_type*."""
    state = getattr(char, "medical_state", None)
    getter = getattr(state, "get_conditions_by_type", None)
    if not callable(getter):
        return False
    try:
        return bool(getter(condition_type))
    except Exception:
        return False


# --------------------------------------------------------------------------
# Per-sense capability checks — can this character see / hear / smell?
# --------------------------------------------------------------------------
# Below these capacities the character has effectively lost the sense (blind /
# deaf / anosmic). One eye / one ear (0.5) still perceives; total loss (0.0)
# does not. Tunable. Each is restorable by a chrome override condition (cyber
# eyes / ears / nose); reuse the combat sight-override so one augment is
# coherent everywhere.
SIGHT_PERCEPTION_THRESHOLD = 0.15
HEARING_PERCEPTION_THRESHOLD = 0.15
SMELL_PERCEPTION_THRESHOLD = 0.15
HEARING_OVERRIDE_CONDITION = "hearing_override"
SMELL_OVERRIDE_CONDITION = "smell_override"


def can_see(char: Any) -> bool:
    """True if *char* can see (enough ``sight`` to visually identify others).

    Fails open with no medical model. A sight-override condition (chrome eyes)
    restores sight regardless of organ state.
    """
    if _has_condition(char, SIGHT_OVERRIDE_CONDITION):
        return True
    sight = _read_capacity(char, "sight")
    if sight is None:
        return True
    return sight >= SIGHT_PERCEPTION_THRESHOLD


def can_hear(char: Any) -> bool:
    """True if *char* can hear (enough ``hearing`` to receive a voice).

    Fails open with no medical model. A hearing-override condition (cyber ears)
    restores hearing regardless of organ state.
    """
    if _has_condition(char, HEARING_OVERRIDE_CONDITION):
        return True
    hearing = _read_capacity(char, "hearing")
    if hearing is None:
        return True
    return hearing >= HEARING_PERCEPTION_THRESHOLD


def can_smell(char: Any) -> bool:
    """True if *char* can smell (enough ``smell`` for olfactory perception).

    Fails open with no medical model. A smell-override condition (a cyber nose)
    restores smell regardless of organ state.
    """
    if _has_condition(char, SMELL_OVERRIDE_CONDITION):
        return True
    smell = _read_capacity(char, "smell")
    if smell is None:
        return True
    return smell >= SMELL_PERCEPTION_THRESHOLD


#: Sense category gated by ``sight``.
VISUAL_SENSE = "visual"
#: Sense category gated by ``hearing``.
AUDITORY_SENSE = "auditory"
#: Sense category gated by ``smell`` (the nose organ).
OLFACTORY_SENSE = "olfactory"


def blocked_senses(looker: Any) -> set[str]:
    """Return the sense categories *looker* cannot currently perceive.

    Empty when the looker perceives everything (full senses, no medical model,
    or restored by a chrome override). Only the sight/hearing/smell-gated
    categories can appear here; every other sense passes through.
    """
    blocked: set[str] = set()
    if looker is None:
        return blocked
    if not can_see(looker):
        blocked.add(VISUAL_SENSE)
    if not can_hear(looker):
        blocked.add(AUDITORY_SENSE)
    if not can_smell(looker):
        blocked.add(OLFACTORY_SENSE)
    return blocked


def can_perceive_sense(looker: Any, sense: str) -> bool:
    """True if *looker* can perceive content tagged with *sense*."""
    return sense not in blocked_senses(looker)


def filter_sensory_keys(looker: Any, senses):
    """Yield the sense keys from *senses* that *looker* can perceive.

    Convenience for ambient renderers that hold a dict/list of sense-tagged
    content: ``[s for s in senses if can_perceive_sense(looker, s)]``.
    """
    blocked = blocked_senses(looker)
    return [s for s in senses if s not in blocked]


def has_reduced_perception(looker: Any) -> bool:
    """True if *looker* is missing at least one gated sense.

    Drives compensatory enrichment (spec §5): a looker who has lost a sense
    gets a little more texture from the senses that remain.
    """
    return bool(blocked_senses(looker))


# ---------------------------------------------------------------------------
# The presence gate (STEALTH_AND_DETECTION_SPEC §7 / PHASE_LAYER_SPEC §3)
# ---------------------------------------------------------------------------

def can_perceive(looker, target) -> bool:
    """THE presence gate: whether *looker* passively perceives *target* as
    present at all. Today this is stealth's graded clause (an Unaware /
    Suspicious looker doesn't perceive a hidden target); the phase layer's
    binary clause slots in here when it lands. Deliberate bypasses (AoE,
    area sound, active `search`) must NOT route through this — hidden is
    concealment, never invulnerability."""
    try:
        from world.stealth import is_hidden_from
        return not is_hidden_from(target, looker)
    except Exception:  # noqa: BLE001 — fail-open: perception over paranoia
        return True


def filter_present(looker, entities):
    """The single enumeration choke (leak-completeness discipline): every
    path that lists 'who is here' for a looker filters through this."""
    return [e for e in entities if can_perceive(looker, e)]
