"""
Perception gating — which sensory channels a looker currently receives
(CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC §5).

The LOOK Sensory Category Framework (``LOOK_COMMAND_SPEC.md``) already tags
ambient content (weather, crowd) by sense — visual / auditory / olfactory /
tactile / atmospheric — and was built to "show reduced content" to players with
sensory limitations. This module supplies the missing input: it reads a looker's
``sight`` / ``hearing`` capacities (via the voice-layer perception primitives,
which already honour the chrome-eye / cyber-ear override seams) and reports which
sense categories are *blocked*.

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

from world.voice import can_hear, can_see, can_smell

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
