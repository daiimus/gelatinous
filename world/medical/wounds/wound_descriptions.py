"""
Wound Description Logic

Core functions for generating wound descriptions and integrating them
with character longdesc. Follows the combat message pattern with
multiple description variants.
"""

import random
from .constants import (
    WOUND_STAGES, INJURY_SEVERITY_MAP, get_location_display_name,
    WOUND_TRANSITION_DAYS, MAX_WOUND_DESCRIPTIONS, MEDICAL_COLORS
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
    
    # Get descriptions for this stage
    stage_descriptions = wound_messages.get(stage, wound_messages.get("fresh", []))
    
    if not stage_descriptions:
        location_display = get_location_display_name(location, character)
        return f"a {severity.lower()} {injury_type} wound on the {location_display}"
    
    # Select random description from available options
    description_data = random.choice(stage_descriptions)
    
    # Build format variables
    location_display = get_location_display_name(location, character)
    format_vars = {
        'severity': INJURY_SEVERITY_MAP.get(severity, severity.lower()),
        'location': location_display,
        'organ': organ or "",
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
    
    # Format with parameters
    formatted_description = description_data.format(**format_vars)
    
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
    
    # Check all organs in the character's medical state for damage
    for organ_name, organ in medical_state.organs.items():
        if organ.current_hp < organ.max_hp:  # Organ is damaged
            location = organ.container
            
            # Only include if wound location is visible (not concealed by clothing)
            if _is_wound_visible(character, location):
                # Determine injury type and stage based on organ condition
                injury_type = _determine_injury_type_from_organ(organ)
                stage = _determine_wound_stage_from_organ(organ)
                severity = _determine_severity_from_damage(organ)
                
                wound_data = {
                    'injury_type': injury_type,
                    'location': location,
                    'severity': severity,
                    'stage': stage,
                    'organ': organ_name,
                    'organ_obj': organ
                }
                wounds.append(wound_data)
    
    return wounds


def update_character_wounds(character):
    """
    Update character's longdesc with current wound descriptions.
    
    Args:
        character: Character object to update
        
    Returns:
        bool: True if longdesc was updated, False otherwise
    """
    wounds = get_character_wounds(character)
    
    if not wounds:
        # No wounds - remove any existing wound descriptions
        return _remove_wound_descriptions(character)
    
    # Limit to most significant wounds
    significant_wounds = _prioritize_wounds(wounds)[:MAX_WOUND_DESCRIPTIONS]
    
    # Generate wound descriptions
    wound_descriptions = []
    for wound in significant_wounds:
        description = get_wound_description(
            injury_type=wound['injury_type'],
            location=wound['location'], 
            severity=wound['severity'],
            stage=wound['stage'],
            organ=wound.get('organ')
        )
        wound_descriptions.append(description)
    
    # Update longdesc with wound descriptions
    return _update_longdesc_with_wounds(character, wound_descriptions)


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
    # First check if the organ has stored injury type from when damage was applied
    if hasattr(organ, 'injury_type') and organ.injury_type != "generic":
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


def _determine_injury_type_from_condition(condition):
    """
    Determine injury type from medical condition.
    
    Args:
        condition: Medical condition object
        
    Returns:
        str: Injury type (bullet, cut, blunt, etc.)
    """
    # Map condition types to injury types
    condition_to_injury = {
        "bleeding": "cut",      # Generic bleeding becomes cut
        "laceration": "cut",    # Laceration is cutting injury
        "puncture": "stab",     # Puncture is stabbing injury  
        "fracture": "blunt",    # Fractures are blunt trauma
    }
    
    condition_type = condition.condition_type if hasattr(condition, 'condition_type') else "unknown"
    return condition_to_injury.get(condition_type, "trauma")


def _determine_wound_stage(condition):
    """
    Determine wound healing stage from condition data.
    
    Args:
        condition: Medical condition object
        
    Returns:
        str: Wound stage (fresh, treated, healing, scarred)
    """
    # For now, return fresh - this will be enhanced with time/treatment tracking
    if hasattr(condition, 'treated') and condition.treated:
        return "treated"
    
    # Could add time-based healing here based on when condition was created
    return "fresh"


def _prioritize_wounds(wounds):
    """
    Sort wounds by significance for display.
    
    Args:
        wounds (list): List of wound data dictionaries
        
    Returns:
        list: Sorted wounds (most significant first)
    """
    severity_order = {"Critical": 4, "Severe": 3, "Moderate": 2, "Light": 1}
    stage_order = {"fresh": 4, "treated": 3, "healing": 2, "scarred": 1}
    
    def wound_priority(wound):
        severity_score = severity_order.get(wound['severity'], 0)
        stage_score = stage_order.get(wound['stage'], 0) 
        return (severity_score, stage_score)
    
    return sorted(wounds, key=wound_priority, reverse=True)


def _update_longdesc_with_wounds(character, wound_descriptions):
    """
    Update character longdesc with wound descriptions.
    
    Args:
        character: Character object
        wound_descriptions (list): List of wound description strings
        
    Returns:
        bool: True if updated successfully
    """
    # For now, this is a placeholder
    # Will integrate with actual longdesc system
    
    # TODO: Implement longdesc integration
    # - Add wounds to appropriate body locations in longdesc
    # - Handle wound description formatting
    # - Preserve existing longdesc content
    
    return True


def _remove_wound_descriptions(character):
    """
    Remove wound descriptions from character longdesc.
    
    Args:
        character: Character object
        
    Returns:
        bool: True if removed successfully
    """
    # Placeholder for wound removal logic
    # TODO: Implement wound description removal from longdesc
    return True
