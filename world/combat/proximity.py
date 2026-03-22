"""
Combat Proximity Management

Handles all proximity-related logic for the combat system.
Extracted from combathandler.py and CmdCombat.py to improve
organization and maintainability.

Functions:
- Proximity establishment and clearing
- Bidirectional proximity management
- Room-based proximity validation
- Proximity cleanup on movement
"""

from .constants import NDB_PROXIMITY
from .debug import log_debug


def initialize_proximity(character):
    """
    Initialize proximity NDB for a character if missing or invalid.
    
    Args:
        character: Character to initialize
        
    Returns:
        bool: True if initialization was needed
    """
    if not hasattr(character.ndb, NDB_PROXIMITY) or not isinstance(getattr(character.ndb, NDB_PROXIMITY), set):
        setattr(character.ndb, NDB_PROXIMITY, set())
        log_debug("PROXIMITY", "INIT", f"Initialized for {character.key}")
        return True
    return False


def establish_proximity(char1, char2):
    """
    Establish bidirectional proximity between two characters.
    
    Args:
        char1: First character
        char2: Second character
    """
    if char1 == char2:
        return
    
    # Initialize if needed
    initialize_proximity(char1)
    initialize_proximity(char2)
    
    # Get proximity sets
    char1_proximity = getattr(char1.ndb, NDB_PROXIMITY)
    char2_proximity = getattr(char2.ndb, NDB_PROXIMITY)
    
    # Establish bidirectional proximity
    char1_proximity.add(char2)
    char2_proximity.add(char1)
    
    log_debug("PROXIMITY", "ESTABLISH", f"{char1.key} <-> {char2.key}")


def break_proximity(char1, char2):
    """
    Break proximity between two specific characters.
    
    Args:
        char1: First character
        char2: Second character
    """
    if char1 == char2:
        return
    
    # Remove from each other's proximity sets
    if hasattr(char1.ndb, NDB_PROXIMITY) and isinstance(getattr(char1.ndb, NDB_PROXIMITY), set):
        getattr(char1.ndb, NDB_PROXIMITY).discard(char2)
    
    if hasattr(char2.ndb, NDB_PROXIMITY) and isinstance(getattr(char2.ndb, NDB_PROXIMITY), set):
        getattr(char2.ndb, NDB_PROXIMITY).discard(char1)
    
    log_debug("PROXIMITY", "BREAK", f"{char1.key} <-> {char2.key}")


def clear_all_proximity(character):
    """
    Clear all proximity relationships for a character.
    
    Args:
        character: Character to clear proximity for
    """
    if not hasattr(character.ndb, NDB_PROXIMITY):
        return
    
    proximity_set = getattr(character.ndb, NDB_PROXIMITY)
    if not isinstance(proximity_set, set):
        return
    
    # Remove this character from all others' proximity
    for other_char in list(proximity_set):
        if hasattr(other_char.ndb, NDB_PROXIMITY) and isinstance(getattr(other_char.ndb, NDB_PROXIMITY), set):
            getattr(other_char.ndb, NDB_PROXIMITY).discard(character)
    
    # Clear this character's proximity
    proximity_set.clear()
    log_debug("PROXIMITY", "CLEAR_ALL", f"Cleared for {character.key}")


def get_proximity_list(character):
    """
    Get list of characters in proximity with given character.
    
    Args:
        character: Character to check
        
    Returns:
        list: List of characters in proximity
    """
    if not hasattr(character.ndb, NDB_PROXIMITY):
        return []
    
    proximity_set = getattr(character.ndb, NDB_PROXIMITY)
    if not isinstance(proximity_set, set):
        return []
    
    return list(proximity_set)


def is_in_proximity(char1, char2):
    """
    Check if two characters are in proximity.
    
    Args:
        char1: First character
        char2: Second character
        
    Returns:
        bool: True if characters are in proximity
    """
    if char1 == char2:
        return False
    
    if not hasattr(char1.ndb, NDB_PROXIMITY):
        return False
    
    proximity_set = getattr(char1.ndb, NDB_PROXIMITY)
    if not isinstance(proximity_set, set):
        return False
    
    return char2 in proximity_set


def proximity_opposed_roll(character, stat_name="motorics"):
    """
    Get the highest opposing roll from characters in proximity.
    
    Args:
        character: Character attempting the action
        stat_name (str): Stat to roll against
        
    Returns:
        tuple: (highest_roll, highest_opponent, all_rolls)
    """
    from .dice import roll_stat
    
    proximity_list = get_proximity_list(character)
    if not proximity_list:
        return 0, None, []
    
    # Get rolls from all opponents in proximity
    rolls = []
    for opponent in proximity_list:
        if hasattr(opponent, stat_name):
            roll = roll_stat(opponent, stat_name)
            rolls.append((opponent, roll))
    
    if not rolls:
        return 0, None, []
    
    # Find highest roll
    highest_opponent, highest_roll = max(rolls, key=lambda x: x[1])
    
    return highest_roll, highest_opponent, rolls


def cleanup_invalid_proximity(character):
    """
    Clean up proximity relationships with invalid characters.
    
    Args:
        character: Character to clean up proximity for
    """
    if not hasattr(character.ndb, NDB_PROXIMITY):
        return
    
    proximity_set = getattr(character.ndb, NDB_PROXIMITY)
    if not isinstance(proximity_set, set):
        return
    
    # Find invalid characters (deleted, no location, etc.)
    invalid_chars = []
    for other_char in proximity_set:
        if not other_char or not hasattr(other_char, 'location') or not other_char.location:
            invalid_chars.append(other_char)
        elif hasattr(character, 'location') and character.location != other_char.location:
            # Different rooms - should not be in proximity
            invalid_chars.append(other_char)
    
    # Remove invalid characters
    for invalid_char in invalid_chars:
        proximity_set.discard(invalid_char)
        log_debug("PROXIMITY", "CLEANUP", f"Removed invalid {invalid_char} from {character.key}")


def sync_proximity_bidirectional(character):
    """
    Ensure proximity relationships are bidirectional and consistent.
    
    Args:
        character: Character to sync proximity for
    """
    if not hasattr(character.ndb, NDB_PROXIMITY):
        return
    
    proximity_set = getattr(character.ndb, NDB_PROXIMITY)
    if not isinstance(proximity_set, set):
        return
    
    for other_char in list(proximity_set):
        # Ensure other character has us in their proximity too
        if not is_in_proximity(other_char, character):
            initialize_proximity(other_char)
            getattr(other_char.ndb, NDB_PROXIMITY).add(character)
            log_debug("PROXIMITY", "SYNC", f"Added {character.key} to {other_char.key}'s proximity")
