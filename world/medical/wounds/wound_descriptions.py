"""
Wound Description Logic

Core functions for generating wound descriptions and integrating them
with character longdesc. Follows the combat message pattern with
multiple description variants.
"""

import random
from .constants import (
    INJURY_SEVERITY_MAP, get_location_display_name, MEDICAL_COLORS
)

# Import wound message files (similar to combat messages)
from . import messages


def get_wound_description(injury_type, location, severity="Moderate", stage="fresh", organ=None, character=None):
    """
    Get a random wound description for the specified parameters.
    
    Args:
        injury_type (str): Type of injury (bullet, cut, blunt, etc.)
        location (str): Body location where wound is located
        severity (str): Injury severity (Light, Moderate, Severe, Critical) 
        stage (str): Healing stage (fresh, treated, healing, scarred)
        organ (str): Specific organ affected (optional, for detail)
        character: Character object (for skintone)
        
    Returns:
        str: Formatted wound description ready for longdesc integration
    """
    # Get the appropriate message module for this injury type
    try:
        message_module = getattr(messages, injury_type)
        wound_messages = message_module.WOUND_DESCRIPTIONS
    except AttributeError:
        # Fallback to generic wound descriptions
        message_module = messages.generic
        wound_messages = message_module.WOUND_DESCRIPTIONS

    # Issue #347: destroyed-stage overlay keyed by (injury_type, location).
    # Limb-vocabulary doesn't fit sensory destruction ("His left eye
    # has been mangled into ribbons of flesh" reads wrong) so each
    # injury-type module may declare a ``DESTROYED_BY_LOCATION`` dict
    # mapping high-specificity surfaces (eyes, ears, ...) to bespoke
    # prose. Falls through to the generic destroyed-stage list when no
    # overlay exists for this (injury_type, location) cell, so authoring
    # is incremental and a missing overlay never produces an unauthored
    # template.
    stage_descriptions = None
    if stage == "destroyed":
        overlay = getattr(message_module, "DESTROYED_BY_LOCATION", None)
        if overlay and location in overlay:
            stage_descriptions = overlay[location]

    if stage_descriptions is None:
        stage_descriptions = wound_messages.get(
            stage, wound_messages.get("fresh", [])
        )
    
    if not stage_descriptions:
        location_display = get_location_display_name(location, character)
        return f"a {severity.lower()} {injury_type} wound on the {location_display}"
    
    # Select random description from available options
    description_data = random.choice(stage_descriptions)
    
    # Build format variables
    location_display = get_location_display_name(location, character)
    # Humanize the organ token the same way location is humanized so
    # templates using {organ} render "left eye" instead of "left_eye".
    # Cheap str-level transform — organ-spec lookup is intentionally
    # avoided here to keep this renderer independent of the ORGANS
    # registry (the registry can grow species-specific entries in PR-G
    # without rippling into the wound-description pipeline).
    organ_display = (organ or "").replace("_", " ") if organ else ""
    format_vars = {
        'severity': INJURY_SEVERITY_MAP.get(severity, severity.lower()),
        'location': location_display,
        'organ': organ_display,
        'injury_type': injury_type
    }
    
    # Add skintone if character provided and stage requires it
    if character and stage in ["treated", "healing", "scarred"]:
        skintone = character.db.skintone
        if skintone:
            try:
                from world.combat.constants import SKINTONE_PALETTE
                color_code = SKINTONE_PALETTE.get(skintone, "")
                format_vars['skintone'] = color_code
            except ImportError:
                # Skintone system not available, use empty string
                format_vars['skintone'] = ""
        else:
            format_vars['skintone'] = ""
    else:
        format_vars['skintone'] = ""
    
    # Add medical color variables
    from .constants import MEDICAL_COLORS
    format_vars.update(MEDICAL_COLORS)
    
    # Format with parameters.  Issue #347: the destroyed-stage overlay
    # uses pronoun tokens (``{Their}``, ``{their}``) that aren't in
    # ``format_vars``; we use ``format_map`` with a fallback dict that
    # preserves unknown ``{key}`` tokens for the pronoun pass below
    # (a plain ``.format(**format_vars)`` would KeyError on them).
    class _PreserveMissing(dict):
        def __missing__(self, key):
            return "{" + key + "}"

    formatted_description = description_data.format_map(
        _PreserveMissing(format_vars)
    )

    # Issue #347: pronoun pass for templates that use ``{Their}`` /
    # ``{their}`` / ``{Them}`` etc.  Existing templates without
    # pronoun tokens are no-ops through this pass.
    if character is not None:
        try:
            from world.anatomy import substitute_pronoun_tokens
            gender = (
                getattr(character, "gender", None)
                or character.db.original_gender
            )
            formatted_description = substitute_pronoun_tokens(
                formatted_description,
                gender=gender,
                number="singular",
            )
        except (AttributeError, ImportError):
            # Character stub without gender / Evennia not importable —
            # leave tokens literal rather than crashing.
            pass

    # Apply grammar formatting (capitalization and punctuation)
    formatted_description = _format_wound_grammar(formatted_description)

    return formatted_description


def _format_wound_grammar(description):
    """
    Apply proper grammar formatting to wound descriptions.
    
    Handles capitalization and punctuation while preserving color codes.
    
    Args:
        description (str): Raw wound description with possible color codes
        
    Returns:
        str: Grammatically formatted description
    """
    if not description:
        return description
    
    # Find the first actual letter (skip color codes)
    import re
    
    # Pattern to match color codes like |R, {skintone}, etc.
    color_pattern = r'(\|[a-zA-Z0-9]|\{[^}]+\})'
    
    # Split into tokens (color codes and text)
    tokens = re.split(color_pattern, description)
    
    # Find first token that starts with a letter and capitalize it
    capitalized = False
    for i, token in enumerate(tokens):
        if not capitalized and token and not re.match(color_pattern, token):
            # This is regular text, capitalize first letter
            if token[0].isalpha():
                tokens[i] = token[0].upper() + token[1:]
                capitalized = True
                break
    
    # Rejoin the tokens
    result = ''.join(tokens)
    
    # Add period at the end if not already there, but before |n
    if result.endswith('|n'):
        if not result.endswith('.|n'):
            result = result[:-2] + '.|n'
    elif not result.endswith('.'):
        result += '.'
    
    return result


def get_character_wounds(character):
    """
    Analyze character's medical state and extract visible wounds.
    Only returns wounds that are not concealed by clothing/armor.
    Uses the flexible medical system to find actual damaged organs.

    Cut-point filter (issue #339): when a limb chain has been severed
    (e.g. shin + foot, thigh + shin + foot), the medical state has
    every chain organ flagged ``wound_stage='severed'``. To avoid
    rendering multiple severance wounds for what was a single cut, we
    suppress downstream severance wounds — only the cut point shows.
    A wound at ``left_foot`` is suppressed if ``left_shin`` (its parent
    container per :data:`world.combat.constants.LIMB_PARENT`) is also
    severed.

    Args:
        character: Character object with medical state

    Returns:
        list: List of wound data dictionaries for visible wounds
    """
    wounds = []

    # Get character's medical state
    try:
        medical_state = character.medical_state
    except AttributeError:
        return wounds

    # First pass: build the set of severed containers so the cut-point
    # filter knows whose parent is gone.
    severed_containers = set()
    for organ in medical_state.organs.values():
        if (getattr(organ, "wound_stage", None) == "severed"
                and organ.current_hp <= 0):
            severed_containers.add(organ.container)

    # Issue #356 Phase 2: species-aware limb-parent map.  Rats have
    # two-segment limbs (foreleg+forepaw, hindleg+hindpaw) so their
    # parent map differs from human's three-segment chain.
    species = getattr(character.db, "species", None) if hasattr(character, "db") else None
    try:
        from world.anatomy import get_species_limb_parent
        LIMB_PARENT = get_species_limb_parent(species)
    except ImportError:
        LIMB_PARENT = {}

    # Head-cluster cut-point: when the head has been severed off the
    # body (decapitation — combat- or chart-driven), every cluster
    # peer (face / neck / eyes / ears / hair-or-fur / snout, depending
    # on species) collapses into a single wound at the "head" cut
    # point.  The cluster forms a bundle, not a parent tree, so it
    # doesn't fit the limb-parent shape — handled separately here.
    # Detection: the brain sits in container="head" and gets zeroed
    # by ``sever_character_body`` during head severance, so its
    # presence in ``severed_containers`` is a reliable signal that
    # the cluster left the body.
    head_cluster_collapsed = "head" in severed_containers
    if head_cluster_collapsed:
        try:
            from world.anatomy import get_species_severed_head_locations
            head_cluster = get_species_severed_head_locations(species)
        except ImportError:
            head_cluster = frozenset()
    else:
        head_cluster = frozenset()

    # Check all organs in the character's medical state for damage
    for organ_name, organ in medical_state.organs.items():
        if organ.current_hp < organ.max_hp:  # Organ is damaged
            # Issue #346: file the wound at the organ's display surface,
            # not its bulk container. Most organs (heart, lungs, liver)
            # have ``display_location == container``; sensory organs
            # (left_eye, right_eye, left_ear, right_ear) route to a more
            # specific longdesc surface so the destruction reads at the
            # right anatomical line. Visibility / coverage checks still
            # consult the container — clothing covers the bulk region.
            location = getattr(organ, "display_location", None) or organ.container

            # Only include if wound location is visible (not concealed by clothing)
            if _is_wound_visible(character, organ.container):
                # Determine injury type and stage based on organ condition
                injury_type = _determine_injury_type_from_organ(organ)
                stage = _determine_wound_stage_from_organ(organ)
                severity = _determine_severity_from_damage(organ)

                # Head-cluster collapse — suppress every wound at any
                # cluster location (including peers like "left_eye" /
                # "neck" AND the head itself).  We emit one synthetic
                # cut-point wound after the loop, matching the corpse
                # path in ``apply_sever_to_corpse``.  Mirroring that
                # contract here means the live-body view and the
                # eventual corpse view render with the same prose
                # ("the head has been taken off the body") instead of
                # the live body listing every cluster organ's own
                # injury separately ("the brain is destroyed", "the
                # left eye is destroyed", …) — see preamble.
                if head_cluster_collapsed and location in head_cluster:
                    continue

                # Cut-point filter: suppress severance wounds that are
                # downstream of another severed container. Only the
                # cut point renders a stump wound; the rest of the
                # chain just went with it.
                if stage == "severed":
                    parent = LIMB_PARENT.get(location)
                    if parent and parent in severed_containers:
                        continue

                wound_data = {
                    'injury_type': injury_type,
                    'location': location,
                    'severity': severity,
                    'stage': stage,
                    'organ': organ_name,
                    'organ_obj': organ
                }
                wounds.append(wound_data)

    # Head-cluster collapse — emit the single synthetic cut-point
    # wound that ``apply_sever_to_corpse`` would have laid down on the
    # corpse-side path.  Same shape (injury_type="severed",
    # location="head", organ=None) so the renderer routes to the
    # severance prose ("the head has been taken off the body") rather
    # than the per-organ-destruction prose the live body would have
    # produced.  Visibility-gated on the head location so concealment
    # via headwear (theoretical edge case) still works.
    if head_cluster_collapsed and _is_wound_visible(character, "head"):
        wounds.append({
            "injury_type": "severed",
            "location": "head",
            "severity": "Critical",
            "stage": "old",
            "organ": None,
            "organ_obj": None,
        })

    return wounds


def _is_wound_visible(character, location):
    """
    Check if a wound at the specified location is visible (not concealed by clothing/armor).
    Leverages existing clothing system coverage logic.
    
    Args:
        character: Character object
        location (str): Body location to check
        
    Returns:
        bool: True if wound is visible, False if concealed by clothing
    """
    # Use existing clothing system method - much simpler!
    return not character.is_location_covered(location)


def _determine_injury_type_from_organ(organ):
    """
    Determine injury type from organ damage patterns.
    
    Args:
        organ: Organ object from medical system
        
    Returns:
        str: Injury type (bullet, cut, blunt, etc.)
    """
    # First check if the organ has stored injury type from when damage
    # was applied.  Guard against ``None`` — severed organs have their
    # current_hp set to 0 by ``sever_character_body`` without going
    # through ``take_damage``, so ``organ.injury_type`` is still its
    # init-time ``None``.  Without the guard, ``None != "generic"`` is
    # True and we return None, which downstream
    # ``getattr(messages, None)`` rejects with a TypeError.
    if (hasattr(organ, 'injury_type')
            and organ.injury_type
            and organ.injury_type != "generic"):
        return organ.injury_type
    
    # Check organ conditions for injury type clues
    organ_conditions = getattr(organ, 'conditions', [])
    
    for condition in organ_conditions:
        condition_type = getattr(condition, 'type', '')
        if 'bullet' in condition_type or 'gunshot' in condition_type:
            return 'bullet'
        elif 'cut' in condition_type or 'slash' in condition_type or 'laceration' in condition_type:
            return 'cut'
        elif 'stab' in condition_type or 'puncture' in condition_type:
            return 'stab'
        elif 'blunt' in condition_type or 'crush' in condition_type or 'fracture' in condition_type:
            return 'blunt'
    
    # Default based on organ type or damage pattern
    organ_name = organ.name.lower()
    if 'bone' in organ_name or 'femur' in organ_name or 'humerus' in organ_name:
        return 'blunt'  # Bone damage usually blunt
    elif 'eye' in organ_name or organ_name in ['brain', 'heart']:
        return 'generic'  # Delicate organs use generic descriptions (no 'trauma' module)
    
    return 'generic'


def _determine_wound_stage_from_organ(organ):
    """
    Determine wound healing stage from organ state.
    
    Args:
        organ: Organ object from medical system
        
    Returns:
        str: Wound stage (fresh, treated, healing, destroyed, severed, scarred)
    """
    # Use stored wound stage if available (new tracking system)
    if hasattr(organ, 'wound_stage') and organ.wound_stage:
        return organ.wound_stage
    
    # Fallback logic for organs without wound stage tracking
    if organ.current_hp <= 0:
        # Need to determine if this should be destroyed or severed
        # Default to destroyed for fallback (internal organs more common)
        return 'destroyed'
    
    # Default to fresh for any damaged organ without tracking
    return 'fresh'


def _determine_severity_from_damage(organ):
    """
    Determine wound severity from organ damage.
    
    Args:
        organ: Organ object from medical system
        
    Returns:
        str: Severity (Light, Moderate, Severe, Critical)
    """
    if organ.current_hp <= 0:
        return 'Critical'  # Destroyed organ
    
    damage_percent = organ.current_hp / organ.max_hp
    
    if damage_percent >= 0.75:
        return 'Light'
    elif damage_percent >= 0.5:
        return 'Moderate'
    elif damage_percent >= 0.25:
        return 'Severe'
    else:
        return 'Critical'
