"""
Longdesc Integration for Wound Descriptions

Handles integration between wound system and character longdesc,
including proper formatting for multiple wounds and clothing concealment.
"""

from .wound_descriptions import get_character_wounds, get_wound_description
from .constants import MAX_WOUND_DESCRIPTIONS


def get_character_wound_display(character):
    """
    Get formatted wound descriptions for character's longdesc.
    
    Args:
        character: Character object
        
    Returns:
        str: Formatted wound descriptions ready for longdesc integration
    """
    wounds = get_character_wounds(character)
    
    if not wounds:
        return ""
    
    # Limit to most significant wounds to prevent description spam
    significant_wounds = _prioritize_wounds_for_display(wounds)[:MAX_WOUND_DESCRIPTIONS]
    
    # Group wounds by location for better formatting
    wounds_by_location = _group_wounds_by_location(significant_wounds)
    
    # Generate descriptions
    wound_descriptions = []
    for location, location_wounds in wounds_by_location.items():
        if len(location_wounds) == 1:
            # Single wound at this location
            wound = location_wounds[0]
            description = get_wound_description(
                injury_type=wound['injury_type'],
                location=wound['location'],
                severity=wound['severity'],
                stage=wound['stage'],
                organ=wound.get('organ')
            )
            wound_descriptions.append(description)
        else:
            # Multiple wounds at same location - use compound description
            compound_desc = _create_compound_wound_description(location, location_wounds)
            wound_descriptions.append(compound_desc)
    
    # Format for longdesc integration
    if len(wound_descriptions) == 1:
        return f" {wound_descriptions[0]}."
    elif len(wound_descriptions) == 2:
        return f" {wound_descriptions[0]} and {wound_descriptions[1]}."
    else:
        # Three or more wounds
        formatted = ", ".join(wound_descriptions[:-1])
        return f" {formatted}, and {wound_descriptions[-1]}."


def _prioritize_wounds_for_display(wounds):
    """
    Sort wounds by display priority for longdesc.
    
    Args:
        wounds (list): List of wound data dictionaries
        
    Returns:
        list: Sorted wounds (most significant first)
    """
    severity_order = {"Critical": 4, "Severe": 3, "Moderate": 2, "Light": 1}
    stage_order = {
        "fresh": 6, "treated": 5, "healing": 4,
        "destroyed": 3, "severed": 2, "scarred": 1,
    }
    
    # Dynamic location priority - visible areas get higher priority
    # Face and head are typically most visible, then exposed areas
    def get_location_priority(location):
        """Get priority for location (higher = more visible)"""
        location = location.lower()
        
        # Primary visibility tiers
        if 'face' in location or 'head' in location:
            return 10
        elif 'neck' in location:
            return 9
        elif 'chest' in location or 'torso' in location:
            return 8
        elif 'arm' in location or 'hand' in location:
            return 7
        elif 'abdomen' in location or 'stomach' in location:
            return 6
        elif 'leg' in location or 'thigh' in location:
            return 5
        elif 'back' in location:
            return 4
        elif 'foot' in location or 'feet' in location:
            return 3
        else:
            # Unknown location gets medium priority
            return 5
    
    def wound_priority(wound):
        severity_score = severity_order.get(wound['severity'], 0)
        stage_score = stage_order.get(wound['stage'], 0)
        location_score = get_location_priority(wound['location'])
        return (severity_score, stage_score, location_score)
    
    return sorted(wounds, key=wound_priority, reverse=True)


def _group_wounds_by_location(wounds):
    """
    Group wounds by body location for compound descriptions.
    
    Args:
        wounds (list): List of wound data dictionaries
        
    Returns:
        dict: Wounds grouped by location
    """
    grouped = {}
    for wound in wounds:
        location = wound['location']
        if location not in grouped:
            grouped[location] = []
        grouped[location].append(wound)
    
    return grouped


def _create_compound_wound_description(location, wounds):
    """
    Create a description for multiple wounds at the same location.
    
    Args:
        location (str): Body location
        wounds (list): List of wound data for this location
        
    Returns:
        str: Compound wound description
    """
    from .constants import get_location_display_name, INJURY_SEVERITY_MAP
    
    # Sort wounds by severity for compound description
    _severity_rank = {"Light": 0, "Moderate": 1, "Severe": 2, "Critical": 3}
    wounds = sorted(wounds, key=lambda w: _severity_rank.get(w['severity'], 0))
    
    # Find the most severe wound to base description on
    primary_wound = wounds[-1]  # Most severe
    
    # Count wounds by stage
    fresh_count = len([w for w in wounds if w['stage'] == 'fresh'])
    treated_count = len([w for w in wounds if w['stage'] == 'treated'])
    healing_count = len([w for w in wounds if w['stage'] == 'healing'])
    scarred_count = len([w for w in wounds if w['stage'] == 'scarred'])
    
    location_display = get_location_display_name(location)
    severity_display = INJURY_SEVERITY_MAP.get(primary_wound['severity'], primary_wound['severity'].lower())
    
    # Create compound description based on wound mix
    if fresh_count > 1:
        if primary_wound['stage'] == 'fresh':
            return f"|Rmultiple {severity_display} wounds on the {location_display}|n"
        else:
            return f"multiple wounds on the {location_display}, including |Ra {severity_display} fresh injury|n"
    elif fresh_count == 1 and (treated_count + healing_count + scarred_count) > 0:
        return f"|Ra fresh {severity_display} wound|n among older injuries on the {location_display}"
    else:
        # No fresh wounds, describe the mix
        if scarred_count > 1:
            return f"multiple old wound scars on the {location_display}"
        elif healing_count > 1:
            return f"multiple healing wounds on the {location_display}"
        else:
            return f"multiple {severity_display} injuries on the {location_display}"


def update_character_longdesc_with_wounds(character):
    """
    Update character's longdesc to include current wound descriptions.
    This integrates with the existing longdesc system.
    
    Args:
        character: Character object to update
        
    Returns:
        bool: True if longdesc was updated successfully
    """
    # Get current wound display
    wound_display = get_character_wound_display(character)
    
    # TODO: Integrate with actual longdesc system
    # This would need to:
    # 1. Parse existing longdesc for wound markers
    # 2. Remove old wound descriptions
    # 3. Insert new wound descriptions at appropriate points
    # 4. Handle clothing coverage changes
    # 5. Preserve other longdesc content
    
    # For now, store wound display for testing
    character.db.wound_display = wound_display
    
    return True


def remove_all_wound_descriptions(character):
    """
    Remove all wound descriptions from character's longdesc.
    Used when character is fully healed or for cleanup.
    
    Args:
        character: Character object
        
    Returns:
        bool: True if removed successfully
    """
    # TODO: Implement wound description removal from longdesc
    # This would remove all wound-related text from the longdesc
    
    # For now, clear stored wound display
    character.db.wound_display = ""
    
    return True
