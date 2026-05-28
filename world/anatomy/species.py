"""Species anatomy overlay (PR #202 / PR-G).

A minimal data + helpers layer that names body parts, corpses, and
locations by species and decay stage.  Designed as a *minimal overlay*
rather than a full anatomical refactor: humans are the assumed default,
and the only species shipped at the time of writing; non-humans will
register here when they exist, and severed items / organs / corpses
will pick up the new vocabulary automatically because every rendering
path consults these helpers.

Design notes
============

* **Decay-tier vocabulary** (per the PR-G design discussion):

    +-----------+----------------------------------------+
    | Stage     | Display                                |
    +===========+========================================+
    | fresh     | ``{species} {part}`` / ``{species} corpse`` |
    | early     | ``{species} {part}`` / ``{species} corpse`` |
    | moderate  | ``rotting {part}`` / ``rotting corpse`` |
    | advanced  | ``rotting {part}`` / ``rotting corpse`` |
    | skeletal  | ``skeletal {part}`` / ``skeletal remains`` |
    +-----------+----------------------------------------+

  Fresh/early stages reveal species cleanly; moderate/advanced
  obfuscate ("rotting" alone, no species clue); skeletal abandons
  species for the universal "skeletal" tag.  Players who want more
  precision than these glance-level tags must ``look`` for the full
  description (which still carries decay prose) or ``autopsy`` (which
  rolls Intellect for forensic recovery).

  Harvested **organs** follow the same shape via
  :data:`decay_organ_prefixes`, but the skeletal-tier tag is
  ``desiccated`` rather than ``skeletal`` — a heart or kidney doesn't
  skeletonize, it dries out.  See :func:`get_species_organ_name`.

* **No species in skeletal/rotting stages**: deliberate gameplay
  signal — late decay obscures species at a glance.  Once a body has
  rotted past recognition or reduced to bone, the casual observer
  can't tell a human from a synth without close examination.

* **Per-character override hook**: characters (or any object with a
  ``db.species`` attribute) consult this registry through their
  species key.  Unknown species fall back to the ``human`` definition
  rather than crashing — this keeps the system robust as new species
  are added incrementally.

* **No state stored on the helpers**: every call is a pure lookup
  against :data:`SPECIES_DEFINITIONS`.  This lets rendering code call
  the helpers on every ``get_display_name`` / ``return_appearance``
  invocation without performance concerns and lets decay drift propagate
  naturally as time passes (the source data — ``get_decay_stage()`` —
  is what changes, not the registry).
"""

from __future__ import annotations

#: Species registry.  Keys are stable species identifiers (lowercase,
#: underscore-separated for multi-word species like ``"glitch_synth"``);
#: values are dicts whose schema is documented inline below.
SPECIES_DEFINITIONS = {
    "human": {
        # Glance-level species tag, used in fresh/early-stage display
        # ("a human corpse", "a human left arm").  Omitted from moderate/
        # advanced/skeletal stages by the decay-prefix template.
        "display_name": "human",

        # Per-location display strings.  Keys are canonical body-
        # location identifiers (matching ``container`` values in
        # ``world.medical.constants.ORGANS`` and the ``location`` field
        # of wound records).  Values are the player-facing strings —
        # underscored canonical keys (``"left_arm"``) become spaced
        # display strings (``"left arm"``).
        "location_display": {
            "head": "head",
            "face": "face",
            "neck": "neck",
            "chest": "chest",
            "abdomen": "abdomen",
            "back": "back",
            "groin": "groin",
            "left_arm": "left arm",
            "right_arm": "right arm",
            "left_hand": "left hand",
            "right_hand": "right hand",
            "left_thigh": "left thigh",
            "right_thigh": "right thigh",
            "left_shin": "left shin",
            "right_shin": "right shin",
            "left_foot": "left foot",
            "right_foot": "right foot",
            "left_eye": "left eye",
            "right_eye": "right eye",
            "left_ear": "left ear",
            "right_ear": "right ear",
        },

        # Decay-tier prefix templates for severed body parts.  Rendered
        # by :func:`get_species_part_name` with ``{species}`` and
        # ``{part}`` substitution.  Note "rotting" and "skeletal" drop
        # the species token deliberately (see module docstring).
        "decay_part_prefixes": {
            "fresh":    "{species} {part}",
            "early":    "{species} {part}",
            "moderate": "rotting {part}",
            "advanced": "rotting {part}",
            "skeletal": "skeletal {part}",
        },

        # Decay-tier prefix templates for harvested organs.  Same shape
        # as ``decay_part_prefixes`` but the skeletal tier uses
        # ``desiccated`` — soft tissue dries out rather than
        # skeletonizing.  Rendered by :func:`get_species_organ_name`.
        "decay_organ_prefixes": {
            "fresh":    "{species} {organ}",
            "early":    "{species} {organ}",
            "moderate": "rotting {organ}",
            "advanced": "rotting {organ}",
            "skeletal": "desiccated {organ}",
        },

        # Decay-tier corpse-name templates.  Rendered by
        # :func:`get_species_corpse_name`.  Skeletal abandons "corpse"
        # for "remains" — a fully skeletonized body isn't a corpse in
        # the colloquial sense and the change in vocabulary signals
        # the irreversibility of that decay tier.
        "decay_corpse_names": {
            "fresh":    "human corpse",
            "early":    "human corpse",
            "moderate": "rotting corpse",
            "advanced": "rotting corpse",
            "skeletal": "skeletal remains",
        },
    },
}


def _resolve_species(species: str | None) -> dict:
    """Return the species definition, falling back to ``human``.

    Centralized so every helper degrades gracefully on unknown / None
    species inputs without scattering ``.get(..., SPECIES_DEFINITIONS["human"])``
    boilerplate.
    """
    if not species:
        return SPECIES_DEFINITIONS["human"]
    return SPECIES_DEFINITIONS.get(species, SPECIES_DEFINITIONS["human"])


def get_species_location_display(species: str | None, location: str) -> str:
    """Return the display string for a body location under a species.

    Unmapped locations fall back to the raw token with underscores
    replaced by spaces — robust against ad-hoc anatomy keys that
    haven't been added to the registry yet (e.g. a future ``"tail"``
    or ``"third_arm"``).

    Args:
        species: Species identifier (e.g. ``"human"``); ``None`` /
            unknown species fall back to ``"human"``.
        location: Canonical body-location identifier
            (e.g. ``"left_arm"``).

    Returns:
        Display string suitable for embedding in player-facing prose.
    """
    spec = _resolve_species(species)
    mapping = spec.get("location_display") or {}
    if location in mapping:
        return mapping[location]
    return (location or "").replace("_", " ")


def get_species_part_name(
    species: str | None, location: str, decay_stage: str
) -> str:
    """Return the decay-modulated display name for a severed body part.

    Used by :class:`typeclasses.items.Appendage`,
    :class:`typeclasses.items.SeveredHead`, and any other detached
    body-part typeclass to render decay-aware glance names like
    ``"human left arm"`` (fresh) → ``"rotting left arm"`` (moderate)
    → ``"skeletal left arm"`` (skeletal).

    The output deliberately omits any article — callers compose with
    ``"a "`` / ``"the "`` per their context.

    Args:
        species: Species identifier; unknown / None → human.
        location: Canonical body-location identifier.
        decay_stage: One of ``fresh`` / ``early`` / ``moderate`` /
            ``advanced`` / ``skeletal``.  Unknown stages fall back to
            the ``fresh`` template.

    Returns:
        Display string ready for use as ``self.key`` or in look output.
    """
    spec = _resolve_species(species)
    prefixes = spec.get("decay_part_prefixes") or {}
    template = prefixes.get(decay_stage) or prefixes.get("fresh") or "{part}"
    part = get_species_location_display(species, location)
    species_display = spec.get("display_name", "")
    return template.format(species=species_display, part=part)


def get_species_corpse_name(
    species: str | None, decay_stage: str
) -> str:
    """Return the decay-modulated display name for a whole corpse.

    Used by :class:`typeclasses.corpse.Corpse` to render decay-aware
    glance names like ``"human corpse"`` → ``"rotting corpse"`` →
    ``"skeletal remains"``.

    Args:
        species: Species identifier; unknown / None → human.
        decay_stage: One of ``fresh`` / ``early`` / ``moderate`` /
            ``advanced`` / ``skeletal``.  Unknown stages fall back to
            the ``fresh`` template.

    Returns:
        Display string ready for use as ``corpse.key``.
    """
    spec = _resolve_species(species)
    names = spec.get("decay_corpse_names") or {}
    if decay_stage in names:
        return names[decay_stage]
    return names.get("fresh", "corpse")


def get_species_organ_name(
    species: str | None,
    organ_name: str,
    decay_stage: str | None = None,
) -> str:
    """Return the decay-modulated display name for a harvested organ.

    Used by :class:`typeclasses.items.Organ` to render decay-aware
    glance names like ``"human heart"`` (fresh) → ``"rotting heart"``
    (moderate) → ``"desiccated heart"`` (skeletal).  The skeletal tier
    deliberately reads ``desiccated`` rather than ``skeletal`` — soft
    tissue dries out rather than skeletonizing.

    Mirrors the contract of :func:`get_species_part_name`: fresh/early
    surface species cleanly, moderate/advanced obscure it ("rotting"
    only), and the skeletal tier abandons species entirely.  Players
    wanting more precision must ``look`` (which shows condition-keyed
    prose) or use forensic commands.

    Args:
        species: Species identifier; unknown / None → human (the
            defensive fallback contract documented in
            ``specs/IDENTITY_RECOGNITION_SPEC.md``).
        organ_name: Canonical organ identifier from
            :data:`world.medical.constants.ORGANS`.  Unregistered
            organs fall back to their underscore-stripped key.
        decay_stage: One of ``fresh`` / ``early`` / ``moderate`` /
            ``advanced`` / ``skeletal``.  ``None`` or unknown stages
            fall back to the ``fresh`` template.

    Returns:
        Display string ready for use as ``self.key`` or in look output.
    """
    from .organs import get_organ_display_name

    spec = _resolve_species(species)
    prefixes = spec.get("decay_organ_prefixes") or {}
    template = (
        prefixes.get(decay_stage)
        or prefixes.get("fresh")
        or "{organ}"
    )
    organ_display = get_organ_display_name(organ_name)
    species_display = spec.get("display_name", "")
    return template.format(species=species_display, organ=organ_display)
