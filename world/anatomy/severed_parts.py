"""Severed body-part default descriptions (PR #204).

Sibling table to :data:`world.anatomy.organs.ORGAN_DISPLAY`, but
keyed by species and severable body-location.  Consumed by
:meth:`typeclasses.items.Appendage.configure_from_sever` (and via
super-call by :class:`typeclasses.items.SeveredHead`) to seed
``self.db.desc`` at sever-time so the standard Evennia renderer
slots the prose into the look output naturally.

Design notes
============

* **Separate file from** :mod:`world.anatomy.species` — that module
  owns the structural species registry (location names, decay
  templates).  Prose belongs in its own file so the structural data
  stays scannable and the prose-heavy block stays easy to translate
  or rewrite in isolation (mirrors the
  :data:`world.anatomy.organs.ORGAN_DISPLAY` separation from
  :data:`world.medical.constants.ORGANS`).

* **Species-keyed** so non-humans (when they exist) can register
  their own anatomy prose without crowding the human entries.
  Unknown species fall back to ``"human"`` via
  :func:`get_severed_part_description`.

* **Three conditions only** — ``pristine`` / ``damaged`` / ``putrid``,
  matching the :data:`world.combat.constants.ORGAN_CONDITION_BY_DECAY`
  map.  The ``refuse`` condition (skeletal-stage corpses) is
  intentionally absent: skeletal corpses refuse severance at the
  command gate, so no Appendage instance ever reaches that condition.

* **Same vocabulary register as** :data:`world.anatomy.organs.ORGAN_DISPLAY`
  — short, clinical, physically anchored, single sentence.  Anchors
  the player's senses without depending on a custom ``db.desc``
  ever being set by a staff member.
"""

from __future__ import annotations


#: Severed-part description registry.  Keys: species identifier (lower-case)
#: → location identifier → condition → prose.  Locations match
#: :data:`world.combat.constants.SEVERABLE_CONTAINERS`.
SEVERED_PART_DESCRIPTIONS = {
    "human": {
        "head": {
            "pristine": (
                "A severed human head, the features still composed and "
                "the stump-cut at the neck clean and weeping a thin "
                "rim of blood."
            ),
            "damaged": (
                "A discoloured severed head, the skin gone waxy and "
                "the stump-cut at the neck dried into a dark, "
                "leathery rim."
            ),
            "putrid": (
                "A bloated severed head, the features distorted and "
                "the flesh sloughing in soft, fetid patches."
            ),
        },
        "left_arm": {
            "pristine": (
                "A severed left arm, the muscle firm and the shoulder "
                "stump cut cleanly through cartilage and bone."
            ),
            "damaged": (
                "A discoloured left arm, the skin mottled and the "
                "shoulder stump dried into a dark, ragged crust."
            ),
            "putrid": (
                "A bloated left arm, the flesh sloughing from the bone "
                "and the shoulder stump weeping a foul dark fluid."
            ),
        },
        "right_arm": {
            "pristine": (
                "A severed right arm, the muscle firm and the shoulder "
                "stump cut cleanly through cartilage and bone."
            ),
            "damaged": (
                "A discoloured right arm, the skin mottled and the "
                "shoulder stump dried into a dark, ragged crust."
            ),
            "putrid": (
                "A bloated right arm, the flesh sloughing from the bone "
                "and the shoulder stump weeping a foul dark fluid."
            ),
        },
        "left_hand": {
            "pristine": (
                "A severed left hand, the fingers still loosely curled "
                "and the wrist-cut clean across the carpal bones."
            ),
            "damaged": (
                "A discoloured left hand, the fingers stiffened into a "
                "claw and the wrist-cut dried into a dark rim."
            ),
            "putrid": (
                "A bloated left hand, the skin sloughing from the "
                "fingers and the wrist-cut weeping a foul dark fluid."
            ),
        },
        "right_hand": {
            "pristine": (
                "A severed right hand, the fingers still loosely curled "
                "and the wrist-cut clean across the carpal bones."
            ),
            "damaged": (
                "A discoloured right hand, the fingers stiffened into a "
                "claw and the wrist-cut dried into a dark rim."
            ),
            "putrid": (
                "A bloated right hand, the skin sloughing from the "
                "fingers and the wrist-cut weeping a foul dark fluid."
            ),
        },
        "left_thigh": {
            "pristine": (
                "A severed left thigh, the heavy muscle firm and the "
                "hip-cut clean through the femoral head."
            ),
            "damaged": (
                "A discoloured left thigh, the skin gone mottled and the "
                "hip-cut dried into a dark, crusted rim."
            ),
            "putrid": (
                "A bloated left thigh, the flesh sloughing from the femur "
                "and the hip-cut weeping a foul dark fluid."
            ),
        },
        "right_thigh": {
            "pristine": (
                "A severed right thigh, the heavy muscle firm and the "
                "hip-cut clean through the femoral head."
            ),
            "damaged": (
                "A discoloured right thigh, the skin gone mottled and the "
                "hip-cut dried into a dark, crusted rim."
            ),
            "putrid": (
                "A bloated right thigh, the flesh sloughing from the femur "
                "and the hip-cut weeping a foul dark fluid."
            ),
        },
        "left_shin": {
            "pristine": (
                "A severed left shin, the calf muscle firm and the "
                "knee-cut clean across the joint surfaces."
            ),
            "damaged": (
                "A discoloured left shin, the skin gone leathery and the "
                "knee-cut dried into a dark rim."
            ),
            "putrid": (
                "A bloated left shin, the flesh sloughing from the tibia "
                "and the knee-cut weeping a foul dark fluid."
            ),
        },
        "right_shin": {
            "pristine": (
                "A severed right shin, the calf muscle firm and the "
                "knee-cut clean across the joint surfaces."
            ),
            "damaged": (
                "A discoloured right shin, the skin gone leathery and the "
                "knee-cut dried into a dark rim."
            ),
            "putrid": (
                "A bloated right shin, the flesh sloughing from the tibia "
                "and the knee-cut weeping a foul dark fluid."
            ),
        },
        "left_foot": {
            "pristine": (
                "A severed left foot, the toes still loosely splayed and "
                "the ankle-cut clean across the tarsal bones."
            ),
            "damaged": (
                "A discoloured left foot, the toes stiffened and the "
                "ankle-cut dried into a dark, crusted rim."
            ),
            "putrid": (
                "A bloated left foot, the skin sloughing from the toes and "
                "the ankle-cut weeping a foul dark fluid."
            ),
        },
        "right_foot": {
            "pristine": (
                "A severed right foot, the toes still loosely splayed and "
                "the ankle-cut clean across the tarsal bones."
            ),
            "damaged": (
                "A discoloured right foot, the toes stiffened and the "
                "ankle-cut dried into a dark, crusted rim."
            ),
            "putrid": (
                "A bloated right foot, the skin sloughing from the toes and "
                "the ankle-cut weeping a foul dark fluid."
            ),
        },
        # Humans grow tails only by augment (ANATOMY_AUGMENTS_SPEC,
        # #511) — the prose assumes the cybernetic article, which is
        # the only human tail that exists.
        "tail": {
            "pristine": (
                "A severed cybernetic tail, alloy vertebrae still "
                "articulating faintly and a torn mount plate trailing "
                "fine cabling at the cut."
            ),
            "damaged": (
                "A scuffed cybernetic tail, its segments seized at odd "
                "angles and the mount-end cabling frayed dark."
            ),
            "putrid": (
                "A grime-caked cybernetic tail, dead servos locked "
                "stiff and the flesh-interface ring at the mount gone "
                "soft and foul."
            ),
        },
    },
}


SEVERED_PART_DESCRIPTIONS.setdefault("rat", {
    "head": {
        "pristine": (
            "A severed rat's head, the snout still twitching as if "
            "ready to sniff and the cut at the neck weeping fresh "
            "blood."
        ),
        "damaged": (
            "A discoloured rat's head, the fur matted and the neck "
            "stump dried into a dark, leathery crust."
        ),
        "putrid": (
            "A bloated rat's head, the features distorted and the "
            "fur sliding off in soft, fetid patches."
        ),
    },
    "left_foreleg": {
        "pristine": (
            "A small severed foreleg, the fur still soft and the "
            "shoulder-cut weeping thin blood."
        ),
        "damaged": (
            "A withered severed foreleg, the fur sparse and the "
            "stump dark with dried matter."
        ),
        "putrid": (
            "A bloated severed foreleg, the flesh going soft and the "
            "fur sloughing in fetid clumps."
        ),
    },
    "right_foreleg": {
        "pristine": (
            "A small severed foreleg, the fur still soft and the "
            "shoulder-cut weeping thin blood."
        ),
        "damaged": (
            "A withered severed foreleg, the fur sparse and the "
            "stump dark with dried matter."
        ),
        "putrid": (
            "A bloated severed foreleg, the flesh going soft and the "
            "fur sloughing in fetid clumps."
        ),
    },
    "left_forepaw": {
        "pristine": (
            "A tiny severed forepaw, the claws still neatly arranged "
            "and the cut at the wrist edged with blood."
        ),
        "damaged": (
            "A shrivelled severed forepaw, the claws curled inward "
            "and the stump dried hard."
        ),
        "putrid": (
            "A swollen severed forepaw, the small pads loose and the "
            "claws coming free of the rotting flesh."
        ),
    },
    "right_forepaw": {
        "pristine": (
            "A tiny severed forepaw, the claws still neatly arranged "
            "and the cut at the wrist edged with blood."
        ),
        "damaged": (
            "A shrivelled severed forepaw, the claws curled inward "
            "and the stump dried hard."
        ),
        "putrid": (
            "A swollen severed forepaw, the small pads loose and the "
            "claws coming free of the rotting flesh."
        ),
    },
    "left_hindleg": {
        "pristine": (
            "A small severed hindleg, the long thigh muscle still "
            "twitching and the hip-cut weeping fresh blood."
        ),
        "damaged": (
            "A withered severed hindleg, the muscle gone slack and "
            "the cut dried dark."
        ),
        "putrid": (
            "A bloated severed hindleg, the flesh going soft and "
            "fetid where the cut once was."
        ),
    },
    "right_hindleg": {
        "pristine": (
            "A small severed hindleg, the long thigh muscle still "
            "twitching and the hip-cut weeping fresh blood."
        ),
        "damaged": (
            "A withered severed hindleg, the muscle gone slack and "
            "the cut dried dark."
        ),
        "putrid": (
            "A bloated severed hindleg, the flesh going soft and "
            "fetid where the cut once was."
        ),
    },
    "left_hindpaw": {
        "pristine": (
            "A tiny severed hindpaw, the long toes still spread and "
            "the cut at the ankle weeping."
        ),
        "damaged": (
            "A shrivelled severed hindpaw, the toes curled inward "
            "and the stump dried hard."
        ),
        "putrid": (
            "A swollen severed hindpaw, the small pads loose and the "
            "claws coming free of the rotting flesh."
        ),
    },
    "right_hindpaw": {
        "pristine": (
            "A tiny severed hindpaw, the long toes still spread and "
            "the cut at the ankle weeping."
        ),
        "damaged": (
            "A shrivelled severed hindpaw, the toes curled inward "
            "and the stump dried hard."
        ),
        "putrid": (
            "A swollen severed hindpaw, the small pads loose and the "
            "claws coming free of the rotting flesh."
        ),
    },
    "tail": {
        "pristine": (
            "A long, ringed rat tail, severed at the base and "
            "weeping a thin line of blood from the cut."
        ),
        "damaged": (
            "A dried-out rat tail, the rings gone leathery and the "
            "base-cut crusted hard."
        ),
        "putrid": (
            "A swollen rat tail, the rings discoloured and the "
            "flesh sloughing softly off the vertebrae."
        ),
    },
})


def get_severed_part_description(species, location, condition):
    """Return condition-keyed prose for a severed body part.

    Args:
        species: Species identifier (e.g. ``"human"``); ``None`` /
            unknown species fall back to ``"human"``.
        location: Canonical body-location identifier
            (e.g. ``"left_arm"``).
        condition: Freshness descriptor — ``"pristine"`` /
            ``"damaged"`` / ``"putrid"``.

    Returns:
        Prose string (single sentence, no trailing newline) or an
        empty string when the species / location / condition tuple
        isn't registered.  Callers should treat empty as "no default
        desc available, fall back to whatever Evennia does next"
        rather than asserting.
    """
    species_table = SEVERED_PART_DESCRIPTIONS.get(species)
    if species_table is None:
        species_table = SEVERED_PART_DESCRIPTIONS.get("human", {})
    location_table = species_table.get(location)
    if not location_table:
        return ""
    return location_table.get(condition, "")
