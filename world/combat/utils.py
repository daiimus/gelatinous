"""
Combat System Utilities

Shared utility functions used throughout the combat system.
Extracted from repeated patterns in the codebase to improve
maintainability and consistency.

Functions:
- Dice rolling and stat validation
- Debug logging helpers
- Character attribute access
- NDB state management
- Proximity validation
- Message formatting
"""

from random import randint
from .constants import (
    DEFAULT_MOTORICS, MIN_DICE_VALUE, SPLATTERCAST_CHANNEL,
    DEBUG_TEMPLATE, NDB_PROXIMITY, COLOR_NORMAL
)


# ===================================================================
# DEBUG & LOGGING
# ===================================================================

def debug_broadcast(message, prefix="DEBUG", status="INFO"):
    """
    Broadcast debug message to Splattercast channel.
    
    Args:
        message (str): Debug message to broadcast
        prefix (str): Prefix for the debug message
        status (str): Status level (INFO, SUCCESS, ERROR, etc.)
    """
    try:
        from evennia.comms.models import ChannelDB
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        if splattercast:
            formatted_msg = f"{prefix}_{status}: {message}"
            splattercast.msg(formatted_msg)
    except Exception:
        # Fail silently if channel not available
        pass


# ===================================================================
# DICE & STATS
# ===================================================================

def get_character_stat(character, stat_name, default=1):
    """
    Safely get a character's stat value with fallback to default.
    
    Args:
        character: The character object
        stat_name (str): Name of the stat (e.g., 'motorics', 'grit')
        default (int): Default value if stat is missing or invalid
        
    Returns:
        int: The stat value, guaranteed to be a positive integer
    """
    stat_value = getattr(character, stat_name, default)
    
    # Ensure it's a valid number
    if not isinstance(stat_value, (int, float)) or stat_value < 1:
        return default
    
    return int(stat_value)


def roll_stat(character, stat_name, default=DEFAULT_MOTORICS):
    """
    Roll a die based on a character's stat value.
    
    Args:
        character: The character object
        stat_name (str): Name of the stat to roll against
        default (int): Default stat value if missing
        
    Returns:
        int: Random value from 1 to stat_value
    """
    stat_value = get_character_stat(character, stat_name, default)
    return randint(MIN_DICE_VALUE, max(MIN_DICE_VALUE, stat_value))


def opposed_roll(char1, char2, stat1="motorics", stat2="motorics"):
    """
    Perform an opposed roll between two characters.
    
    Args:
        char1: First character
        char2: Second character  
        stat1 (str): Stat name for first character
        stat2 (str): Stat name for second character
        
    Returns:
        tuple: (char1_roll, char2_roll, char1_wins)
    """
    roll1 = roll_stat(char1, stat1)
    roll2 = roll_stat(char2, stat2)
    
    return roll1, roll2, roll1 > roll2


def roll_with_advantage(stat_value):
    """
    Roll with advantage: roll twice, take the higher result.
    
    Args:
        stat_value (int): The stat value to roll against
        
    Returns:
        tuple: (final_roll, roll1, roll2) for debugging
    """
    roll1 = randint(1, max(1, stat_value))
    roll2 = randint(1, max(1, stat_value))
    final_roll = max(roll1, roll2)
    return final_roll, roll1, roll2


def roll_with_disadvantage(stat_value):
    """
    Roll with disadvantage: roll twice, take the lower result.
    
    Args:
        stat_value (int): The stat value to roll against
        
    Returns:
        tuple: (final_roll, roll1, roll2) for debugging
    """
    roll1 = randint(1, max(1, stat_value))
    roll2 = randint(1, max(1, stat_value))
    final_roll = min(roll1, roll2)
    return final_roll, roll1, roll2


def standard_roll(stat_value):
    """
    Standard single roll.
    
    Args:
        stat_value (int): The stat value to roll against
        
    Returns:
        tuple: (final_roll, roll, roll) for consistent interface
    """
    roll = randint(1, max(1, stat_value))
    return roll, roll, roll


# ===================================================================
# DEBUG LOGGING
# ===================================================================

def log_debug(prefix, action, message, character=None):
    """
    Send a standardized debug message to Splattercast.
    
    Args:
        prefix (str): Debug prefix (e.g., DEBUG_PREFIX_ATTACK)
        action (str): Action type (e.g., DEBUG_SUCCESS)
        message (str): The debug message
        character: Optional character for context
    """
    try:
        from evennia.comms.models import ChannelDB
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        if splattercast:
            char_context = f" ({character.key})" if character else ""
            full_message = f"{prefix}_{action}: {message}{char_context}"
            splattercast.msg(full_message)
    except Exception:
        # Fail silently if channel doesn't exist
        pass


def log_combat_action(character, action_type, target=None, success=True, details=""):
    """
    Log a combat action with standardized format.
    
    Args:
        character: The character performing the action
        action_type (str): Type of action (attack, flee, etc.)
        target: Optional target character
        success (bool): Whether the action succeeded
        details (str): Additional details
    """
    prefix = f"{action_type.upper()}_CMD"
    action = "SUCCESS" if success else "FAIL"
    
    target_info = f" on {target.key}" if target else ""
    details_info = f" - {details}" if details else ""
    
    message = f"{character.key}{target_info}{details_info}"
    log_debug(prefix, action, message)


# ===================================================================
# CHARACTER STATE MANAGEMENT
# ===================================================================

def initialize_proximity_ndb(character):
    """
    Initialize a character's proximity NDB if missing or invalid.
    
    Args:
        character: The character to initialize
        
    Returns:
        bool: True if initialization was needed
    """
    if not hasattr(character.ndb, NDB_PROXIMITY) or not isinstance(character.ndb.in_proximity_with, set):
        character.ndb.in_proximity_with = set()
        log_debug("PROXIMITY", "FAILSAFE", f"Initialized {NDB_PROXIMITY}", character)
        return True
    return False


def clear_character_proximity(character):
    """
    Clear all proximity relationships for a character.
    
    Args:
        character: The character to clear proximity for
    """
    if hasattr(character.ndb, NDB_PROXIMITY) and character.ndb.in_proximity_with:
        # Clear this character from others' proximity
        for other_char in list(character.ndb.in_proximity_with):
            if hasattr(other_char.ndb, NDB_PROXIMITY) and isinstance(other_char.ndb.in_proximity_with, set):
                other_char.ndb.in_proximity_with.discard(character)
        
        # Clear this character's proximity
        character.ndb.in_proximity_with.clear()
        log_debug("PROXIMITY", "CLEAR", f"Cleared all proximity", character)


# ===================================================================
# WEAPON & ITEM HELPERS
# ===================================================================

def get_wielded_weapon(character):
    """
    Get the first weapon found in character's hands.
    
    Args:
        character: The character to check
        
    Returns:
        The weapon object, or None if no weapon is wielded
    """
    hands = getattr(character, "hands", {})
    return next((item for hand, item in hands.items() if item), None)


def is_wielding_ranged_weapon(character):
    """
    Check if a character is wielding a ranged weapon.
    
    Args:
        character: The character to check
        
    Returns:
        bool: True if wielding a ranged weapon, False otherwise
    """
    # Use the same hands detection logic as core_actions.py
    hands = getattr(character, "hands", {})
    for hand, weapon in hands.items():
        if weapon and hasattr(weapon, 'db') and getattr(weapon.db, 'is_ranged', False):
            return True
    
    return False


def get_wielded_weapons(character):
    """
    Get all weapons a character is currently wielding.
    
    Args:
        character: The character to check
        
    Returns:
        list: List of wielded weapon objects
    """
    weapons = []
    hands = getattr(character, "hands", {})
    
    for hand, weapon in hands.items():
        if weapon:
            weapons.append(weapon)
    
    return weapons


def get_weapon_damage(weapon, default=0):
    """
    Safely get weapon damage with fallback to default.
    
    Args:
        weapon: The weapon object
        default (int): Default damage if weapon has no damage or damage is None
        
    Returns:
        int: Weapon damage value, guaranteed to be a non-negative integer
    """
    if not weapon or not hasattr(weapon, 'db'):
        return default
    
    damage = getattr(weapon.db, "damage", default)
    
    # Handle None explicitly since some weapons might have damage=None
    if damage is None:
        return default
    
    # Ensure it's numeric and non-negative
    if not isinstance(damage, (int, float)) or damage < 0:
        return default
    
    return int(damage)


# ===================================================================
# MESSAGE FORMATTING
# ===================================================================

def format_combat_message(template, **kwargs):
    """
    Format a combat message template with color codes preserved.
    
    Args:
        template (str): Message template with {placeholders}
        **kwargs: Values to substitute
        
    Returns:
        str: Formatted message with proper color code termination
    """
    message = template.format(**kwargs)
    
    # Ensure message ends with color normal if it contains color codes
    if "|" in message and not message.endswith(COLOR_NORMAL):
        message += COLOR_NORMAL
    
    return message


def get_display_name_safe(character, observer=None):
    """
    Safely get a character's display name with fallback.
    
    Args:
        character: The character object
        observer: Optional observer for context
        
    Returns:
        str: Character's display name or fallback
    """
    if not character:
        return "someone"
    
    try:
        if observer and hasattr(character, "get_display_name"):
            return character.get_display_name(observer)
        return character.key if hasattr(character, "key") else str(character)
    except Exception:
        return "someone"


# ===================================================================
# VALIDATION HELPERS
# ===================================================================

def validate_combat_target(caller, target, allow_self=False):
    """
    Validate a combat target is appropriate.
    
    Args:
        caller: The character initiating combat
        target: The target character
        allow_self (bool): Whether self-targeting is allowed
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not target:
        return False, "Target not found."
    
    if not allow_self and target == caller:
        return False, "You can't target yourself."
    
    if not hasattr(target, "location") or not target.location:
        return False, "Target is not in a valid location."
    
    # Check if target is dead or unconscious
    if hasattr(target, 'is_dead') and target.is_dead():
        return False, f"{target.key} is dead and cannot be targeted."
    
    if hasattr(target, 'is_unconscious') and target.is_unconscious():
        return False, f"{target.key} is unconscious and cannot be targeted."
    
    return True, ""


def validate_in_same_room(char1, char2):
    """
    Check if two characters are in the same room.
    
    Args:
        char1: First character
        char2: Second character
        
    Returns:
        bool: True if in same room
    """
    return (hasattr(char1, "location") and hasattr(char2, "location") and 
            char1.location and char2.location and 
            char1.location == char2.location)


# ===================================================================
# STAT MANAGEMENT HELPERS
# ===================================================================

def get_highest_opponent_stat(opponents, stat_name="motorics", default=1):
    """
    Get the highest stat value among a list of opponents.
    
    Args:
        opponents (list): List of character objects
        stat_name (str): Name of the stat to check
        default (int): Default value if stat is missing or invalid
        
    Returns:
        tuple: (highest_value, character_with_highest_value)
    """
    if not opponents:
        return default, None
        
    highest_value = default
    highest_char = None
    
    for opponent in opponents:
        if not opponent or not hasattr(opponent, stat_name):
            continue
            
        stat_value = getattr(opponent, stat_name, default)
        numeric_value = stat_value if isinstance(stat_value, (int, float)) else default
        
        if numeric_value > highest_value:
            highest_value = numeric_value
            highest_char = opponent
            
    return highest_value, highest_char


def get_numeric_stat(character, stat_name, default=1):
    """
    Get a numeric stat value from a character, with fallback to default.
    
    Args:
        character: Character object
        stat_name (str): Name of the stat to retrieve
        default (int): Default value if stat is missing or invalid
        
    Returns:
        int: Numeric stat value
    """
    if not character or not hasattr(character, stat_name):
        return default
        
    stat_value = getattr(character, stat_name, default)
    return stat_value if isinstance(stat_value, (int, float)) else default


def filter_valid_opponents(opponents):
    """
    Filter a list to only include valid opponent characters.
    
    Args:
        opponents (list): List of potential opponent objects
        
    Returns:
        list: Filtered list of valid characters
    """
    return [
        opp for opp in opponents 
        if opp and hasattr(opp, "motorics")  # Basic character validation
    ]


# ===================================================================
# AIM STATE MANAGEMENT HELPERS
# ===================================================================

def clear_aim_state(character):
    """
    Clear all aim-related state from a character.
    
    Args:
        character: The character to clear aim state from
    """
    # Clear aiming target
    if hasattr(character.ndb, "aiming_at"):
        del character.ndb.aiming_at
    
    # Clear aiming direction  
    if hasattr(character.ndb, "aiming_direction"):
        del character.ndb.aiming_direction
    
    # Clear being aimed at by others
    if hasattr(character.ndb, "aimed_at_by"):
        del character.ndb.aimed_at_by
    
    log_debug("AIM", "CLEAR", f"Cleared aim state", character)


def clear_mutual_aim(char1, char2):
    """
    Clear any mutual aiming relationships between two characters.
    
    Args:
        char1: First character
        char2: Second character
    """
    # Clear char1 aiming at char2
    if hasattr(char1.ndb, "aiming_at") and char1.ndb.aiming_at == char2:
        del char1.ndb.aiming_at
        if hasattr(char1.ndb, "aiming_direction"):
            del char1.ndb.aiming_direction
    
    # Clear char2 aiming at char1
    if hasattr(char2.ndb, "aiming_at") and char2.ndb.aiming_at == char1:
        del char2.ndb.aiming_at
        if hasattr(char2.ndb, "aiming_direction"):
            del char2.ndb.aiming_direction
    
    # Clear being aimed at relationships
    if hasattr(char1.ndb, "aimed_at_by") and char1.ndb.aimed_at_by == char2:
        del char1.ndb.aimed_at_by
    
    if hasattr(char2.ndb, "aimed_at_by") and char2.ndb.aimed_at_by == char1:
        del char2.ndb.aimed_at_by


# ===================================================================
# COMBATANT MANAGEMENT (moved from handler.py)
# ===================================================================

def add_combatant(handler, char, target=None, initial_grappling=None, initial_grappled_by=None, initial_is_yielding=False):
    """
    Add a character to combat.
    
    Args:
        handler: The combat handler instance
        char: The character to add
        target: Optional initial target
        initial_grappling: Optional character being grappled initially
        initial_grappled_by: Optional character grappling this char initially
        initial_is_yielding: Whether the character starts yielding
    """
    from evennia.comms.models import ChannelDB
    from .constants import (
        SPLATTERCAST_CHANNEL, DB_COMBATANTS, DB_CHAR, DB_TARGET_DBREF,
        DB_GRAPPLING_DBREF, DB_GRAPPLED_BY_DBREF, DB_IS_YIELDING, 
        NDB_PROXIMITY, NDB_COMBAT_HANDLER, DB_COMBAT_RUNNING
    )
    from random import randint
    
    splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
    
    # Debug: Show what parameters were passed
    splattercast.msg(f"ADD_COMBATANT_PARAMS: char={char.key if char else None}, target={target.key if target else None}")
    
    # Prevent self-targeting
    if target and char == target:
        splattercast.msg(f"ADD_COMBATANT_ERROR: {char.key} cannot target themselves! Setting target to None.")
        target = None
    
    # Check if already in combat
    combatants = getattr(handler.db, DB_COMBATANTS, [])
    for entry in combatants:
        if entry.get(DB_CHAR) == char:
            splattercast.msg(f"ADD_COMB: {char.key} is already in combat.")
            return
    
    # Initialize proximity NDB if it doesn't exist or is not a set
    if not hasattr(char.ndb, NDB_PROXIMITY) or not isinstance(getattr(char.ndb, NDB_PROXIMITY), set):
        setattr(char.ndb, NDB_PROXIMITY, set())
        splattercast.msg(f"ADD_COMB: Initialized char.ndb.{NDB_PROXIMITY} as a new set for {char.key}.")
    
    # Create combat entry
    target_dbref = get_character_dbref(target)
    entry = {
        DB_CHAR: char,
        "initiative": randint(1, 20) + get_numeric_stat(char, "motorics", 0),
        DB_TARGET_DBREF: target_dbref,
        DB_GRAPPLING_DBREF: get_character_dbref(initial_grappling),
        DB_GRAPPLED_BY_DBREF: get_character_dbref(initial_grappled_by),
        DB_IS_YIELDING: initial_is_yielding,
        "combat_action": None
    }
    
    splattercast.msg(f"ADD_COMBATANT_ENTRY: {char.key} -> target_dbref={target_dbref}, initiative={entry['initiative']}")
    
    combatants.append(entry)
    setattr(handler.db, DB_COMBATANTS, combatants)
    
    # Set the character's handler reference
    setattr(char.ndb, NDB_COMBAT_HANDLER, handler)
    
    # Set combat override_place (only if not already set to something more specific)
    if not hasattr(char, 'override_place') or not char.override_place or char.override_place == "":
        char.override_place = "locked in combat."
        splattercast.msg(f"ADD_COMB: Set {char.key} override_place to 'locked in combat.'")
    else:
        splattercast.msg(f"ADD_COMB: {char.key} already has override_place: '{char.override_place}' - not overriding")
    
    splattercast.msg(f"ADD_COMB: {char.key} added to combat in {handler.key} with initiative {entry['initiative']}.")
    
    # Establish proximity for grappled pairs when adding to new handler
    from .proximity import establish_proximity
    if initial_grappling:
        establish_proximity(char, initial_grappling)
        splattercast.msg(f"ADD_COMB: Established proximity between {char.key} and grappled victim {initial_grappling.key}.")
    if initial_grappled_by:
        establish_proximity(char, initial_grappled_by)
        splattercast.msg(f"ADD_COMB: Established proximity between {char.key} and grappler {initial_grappled_by.key}.")
    
    # Start combat if not already running
    if not getattr(handler.db, DB_COMBAT_RUNNING, False):
        handler.start()
    
    # Validate grapple state after adding new combatant
    from .grappling import validate_and_cleanup_grapple_state
    validate_and_cleanup_grapple_state(handler)


def remove_combatant(handler, char):
    """
    Remove a character from combat and clean up their state.
    
    Args:
        handler: The combat handler instance
        char: The character to remove from combat
    """
    from evennia.comms.models import ChannelDB
    from .constants import (
        SPLATTERCAST_CHANNEL, DB_COMBATANTS, DB_CHAR, DB_TARGET_DBREF, 
        NDB_COMBAT_HANDLER
    )
    
    splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
    
    # Use the active working list if available (during round processing), otherwise use database
    active_list = getattr(handler, '_active_combatants_list', None)
    if active_list:
        combatants = active_list
        splattercast.msg(f"RMV_COMB: Using active working list with {len(combatants)} entries")
    else:
        combatants = getattr(handler.db, DB_COMBATANTS, [])
        splattercast.msg(f"RMV_COMB: Using database list with {len(combatants)} entries")
        
    entry = next((e for e in combatants if e.get(DB_CHAR) == char), None)
    
    if not entry:
        splattercast.msg(f"RMV_COMB: {char.key} not found in combat.")
        return
    
    # Clean up the character's state
    cleanup_combatant_state(char, entry, handler)
    
    # Remove references to this character from other combatants and attempt auto-retargeting
    for other_entry in combatants:
        if other_entry.get(DB_TARGET_DBREF) == get_character_dbref(char):
            other_entry[DB_TARGET_DBREF] = None
            other_char = other_entry[DB_CHAR]
            splattercast.msg(f"RMV_COMB: Cleared {other_char.key}'s target_dbref (was {char.key})")
            
            # Attempt smart auto-retargeting: find someone who is actively attacking this character
            # For melee weapons, prioritize targets in proximity; for ranged weapons, any attacker is fine
            other_char_weapon = get_wielded_weapon(other_char)
            other_char_is_ranged = other_char_weapon and hasattr(other_char_weapon, "db") and getattr(other_char_weapon.db, "is_ranged", False)
            
            new_target = None
            proximity_attackers = []  # Attackers in proximity (for melee priority)
            ranged_attackers = []     # All attackers (fallback)
            
            for potential_target_entry in combatants:
                potential_target_char = potential_target_entry.get(DB_CHAR)
                potential_target_dbref = potential_target_entry.get(DB_TARGET_DBREF)
                
                # Skip self and the character being removed
                if potential_target_char == other_char or potential_target_char == char:
                    continue
                
                # Skip dead or unconscious characters - they can't be valid retarget options
                if (hasattr(potential_target_char, 'is_dead') and potential_target_char.is_dead()) or \
                   (hasattr(potential_target_char, 'is_unconscious') and potential_target_char.is_unconscious()):
                    splattercast.msg(f"RMV_COMB: Skipping {potential_target_char.key} for auto-retarget - dead/unconscious")
                    continue
                
                # FRIENDLY FIRE PREVENTION: Only consider characters actively attacking other_char
                # This prevents auto-retargeting to teammates or neutral parties in combat
                if potential_target_dbref == get_character_dbref(other_char):
                    splattercast.msg(f"RMV_COMB: {potential_target_char.key} is actively attacking {other_char.key} - valid retarget candidate")
                elif potential_target_dbref:
                    target_name = "unknown"
                    try:
                        target_obj = next((e.get(DB_CHAR) for e in combatants if get_character_dbref(e.get(DB_CHAR)) == potential_target_dbref), None)
                        target_name = target_obj.key if target_obj else f"dbref#{potential_target_dbref}"
                    except:
                        target_name = f"dbref#{potential_target_dbref}"
                    splattercast.msg(f"RMV_COMB: Skipping {potential_target_char.key} for auto-retarget - attacking {target_name}, not {other_char.key} (friendly fire prevention)")
                    continue
                else:
                    splattercast.msg(f"RMV_COMB: Skipping {potential_target_char.key} for auto-retarget - not targeting anyone")
                    continue
                
                # This character is actively attacking other_char - valid candidate
                if potential_target_dbref == get_character_dbref(other_char):
                    ranged_attackers.append(potential_target_char)
                    
                    # Check if they're also in proximity for melee priority
                    if hasattr(other_char.ndb, "in_proximity_with") and potential_target_char in other_char.ndb.in_proximity_with:
                        proximity_attackers.append(potential_target_char)
            
            # Smart targeting logic based on weapon type
            if other_char_is_ranged:
                # Ranged weapon - any attacker is fine, pick first available
                new_target = ranged_attackers[0] if ranged_attackers else None
                retarget_reason = "ranged weapon - any attacker"
            else:
                # Melee weapon - prioritize proximity attackers, fallback to any attacker
                if proximity_attackers:
                    new_target = proximity_attackers[0]
                    retarget_reason = "melee weapon - proximity attacker"
                elif ranged_attackers:
                    new_target = ranged_attackers[0]
                    retarget_reason = "melee weapon - distant attacker (no proximity available)"
                else:
                    new_target = None
                    retarget_reason = "no valid attackers found"
            
            splattercast.msg(f"RMV_COMB: Auto-retarget analysis for {other_char.key}: weapon_ranged={other_char_is_ranged}, proximity_attackers={len(proximity_attackers)}, total_attackers={len(ranged_attackers)}, reason='{retarget_reason}'")
            
            if new_target:
                # Auto-retarget found - simulate the same flow as attack/kill command
                splattercast.msg(f"RMV_COMB: Auto-retargeting {other_char.key} to {new_target.key} ({retarget_reason}) - simulating attack command")
                
                # Use the same pattern as attack command: set_target + update both working list and database
                handler.set_target(other_char, new_target)
                
                # CRITICAL: Update the working list (combatants parameter) if we're using it
                other_char_entry_working = next((e for e in combatants if e.get("char") == other_char), None)
                if other_char_entry_working:
                    other_char_entry_working["target_dbref"] = get_character_dbref(new_target)
                    other_char_entry_working["combat_action"] = None
                    other_char_entry_working["combat_action_target"] = None 
                    other_char_entry_working["is_yielding"] = False
                    splattercast.msg(f"RMV_COMB: Updated working list for {other_char.key} -> target_dbref={other_char_entry_working['target_dbref']}")
                
                # Also update database to ensure persistence (same as attack command)
                combatants_copy = getattr(handler.db, "combatants", [])
                other_char_entry_copy = next((e for e in combatants_copy if e.get("char") == other_char), None)
                if other_char_entry_copy:
                    other_char_entry_copy["target_dbref"] = get_character_dbref(new_target)
                    other_char_entry_copy["combat_action"] = None
                    other_char_entry_copy["combat_action_target"] = None 
                    other_char_entry_copy["is_yielding"] = False
                    
                    # Save the modified combatants list back (same as attack command)
                    setattr(handler.db, "combatants", combatants_copy)
                    splattercast.msg(f"RMV_COMB: Updated database using attack command pattern for {other_char.key}")
                
                # Get weapon info for initiate message
                from .messages import get_combat_message
                weapon_obj = get_wielded_weapon(other_char)
                weapon_type = "unarmed"
                if weapon_obj and hasattr(weapon_obj, 'db') and hasattr(weapon_obj.db, 'weapon_type'):
                    weapon_type = weapon_obj.db.weapon_type
                
                # Send initiate messages (same as attack command)
                try:
                    initiate_msg_obj = get_combat_message(weapon_type, "initiate", 
                                                        attacker=other_char, target=new_target, item=weapon_obj)
                    
                    if isinstance(initiate_msg_obj, dict):
                        attacker_msg = initiate_msg_obj.get("attacker_msg", f"You turn your attention to {new_target.key}!")
                        victim_msg = initiate_msg_obj.get("victim_msg", f"{other_char.key} turns their attention to you!")
                        observer_msg = initiate_msg_obj.get("observer_msg", f"{other_char.key} turns their attention to {new_target.key}!")
                    else:
                        # Fallback messages
                        attacker_msg = f"|yYour target has left combat, but you quickly turn your attention to {new_target.get_display_name(other_char)}!|n"
                        victim_msg = f"|y{other_char.get_display_name(new_target)} turns their attention to you!|n"
                        observer_msg = f"|y{other_char.key} turns their attention to {new_target.key}!|n"
                    
                    # Send messages
                    other_char.msg(attacker_msg)
                    new_target.msg(victim_msg)
                    
                    # Send observer message to location  
                    if hasattr(other_char, 'location') and other_char.location:
                        other_char.location.msg_contents(observer_msg, exclude=[other_char, new_target])
                        
                except Exception as e:
                    splattercast.msg(f"RMV_COMB_ERROR: Failed to send auto-retarget messages for {other_char.key}: {e}")
                    # Fallback message
                    other_char.msg(f"|yYour target has left combat, but you quickly turn your attention to {new_target.get_display_name(other_char)}!|n")
            else:
                # No auto-retarget found - send original message
                if hasattr(other_char, 'msg'):
                    other_char.msg(f"|yYour target {char.get_display_name(other_char) if hasattr(char, 'get_display_name') else char.key} has left combat. Choose a new target if you wish to continue fighting.|n")
    
    # Remove from combatants list
    combatants = [e for e in combatants if e.get(DB_CHAR) != char]
    
    # Update the appropriate list(s)
    if active_list:
        # Working with active list - it will be saved back at end of round
        # But also update database in case something else queries it
        setattr(handler.db, DB_COMBATANTS, combatants)
        splattercast.msg(f"RMV_COMB: Updated both active list and database (active list will be saved at round end)")
    else:
        # Working with database directly
        setattr(handler.db, DB_COMBATANTS, combatants)
        splattercast.msg(f"RMV_COMB: Updated database directly")
    
    # Remove handler reference
    if hasattr(char.ndb, NDB_COMBAT_HANDLER) and getattr(char.ndb, NDB_COMBAT_HANDLER) == handler:
        delattr(char.ndb, NDB_COMBAT_HANDLER)
    
    splattercast.msg(f"{char.key} removed from combat.")
    # TODO: Add narrative combat exit message (weapon lowering, stepping back, etc.)
    
    # Stop combat if no combatants remain
    if len(combatants) == 0:
        splattercast.msg(f"RMV_COMB: No combatants remain in handler {handler.key}. Stopping.")
        handler.stop_combat_logic()


def cleanup_combatant_state(char, entry, handler):
    """
    Clean up all combat-related state for a character.
    
    Args:
        char: The character to clean up
        entry: The character's combat entry
        handler: The combat handler instance
    """
    from .proximity import clear_all_proximity
    from .grappling import break_grapple
    from .constants import NDB_PROXIMITY, NDB_SKIP_ROUND
    
    # Clear proximity relationships
    clear_all_proximity(char)
    
    # Break grapples
    grappling = get_combatant_grappling_target(entry, handler)
    grappled_by = get_combatant_grappled_by(entry, handler)
    
    if grappling:
        break_grapple(handler, grappler=char, victim=grappling)
    if grappled_by:
        break_grapple(handler, grappler=grappled_by, victim=char)
    
    # Clear NDB attributes
    from .constants import NDB_CHARGE_BONUS, NDB_CHARGE_VULNERABILITY
    ndb_attrs = [NDB_PROXIMITY, NDB_SKIP_ROUND, NDB_CHARGE_VULNERABILITY, 
                NDB_CHARGE_BONUS, "skip_combat_round"]
    for attr in ndb_attrs:
        if hasattr(char.ndb, attr):
            delattr(char.ndb, attr)
    
    # Clear combat handler reference to prevent stale references
    from .constants import NDB_COMBAT_HANDLER
    if hasattr(char.ndb, NDB_COMBAT_HANDLER):
        delattr(char.ndb, NDB_COMBAT_HANDLER)
    
    # Clear combat override_place (only if it's the generic combat state)
    if (hasattr(char, 'override_place') and 
        char.override_place == "locked in combat."):
        char.override_place = ""
        from evennia.comms.models import ChannelDB
        from .constants import SPLATTERCAST_CHANNEL
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        splattercast.msg(f"CLEANUP_COMB: Cleared combat override_place for {char.key}")
    
    # No need to set charge flags to False after deletion - this was causing race conditions
    # The delattr above already removed them, setting them to False recreates them


def cleanup_all_combatants(handler):
    """
    Clean up all combatant state and remove them from the handler.
    
    This function clears all proximity relationships, breaks grapples,
    and removes combat-related NDB attributes from all combatants.
    
    Args:
        handler: The combat handler instance
    """
    from evennia.comms.models import ChannelDB
    from .constants import SPLATTERCAST_CHANNEL, DB_COMBATANTS, DB_CHAR, DEBUG_PREFIX_HANDLER, DEBUG_CLEANUP
    
    splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
    combatants = getattr(handler.db, DB_COMBATANTS, [])
    
    for entry in combatants:
        char = entry.get(DB_CHAR)
        if char:
            cleanup_combatant_state(char, entry, handler)
    
    # Clear the combatants list
    setattr(handler.db, DB_COMBATANTS, [])
    splattercast.msg(f"{DEBUG_PREFIX_HANDLER}_{DEBUG_CLEANUP}: All combatants cleaned up for {handler.key}.")


# ===================================================================
# COMBATANT UTILITY FUNCTIONS
# ===================================================================

def get_combatant_target(entry, handler):
    """Get the target object for a combatant entry."""
    target_dbref = entry.get("target_dbref")
    return get_character_by_dbref(target_dbref)


def get_combatant_grappling_target(entry, handler):
    """Get the character that this combatant is grappling."""
    grappling_dbref = entry.get("grappling_dbref")
    return get_character_by_dbref(grappling_dbref)


def get_combatant_grappled_by(entry, handler):
    """Get the character that is grappling this combatant."""
    grappled_by_dbref = entry.get("grappled_by_dbref")
    return get_character_by_dbref(grappled_by_dbref)


def update_all_combatant_handler_references(handler):
    """
    Update all combatants' NDB combat_handler references to point to the given handler.
    
    This is critical after handler merges to ensure all combatants have correct references.
    
    Args:
        handler: The combat handler instance all combatants should reference
    """
    from evennia.comms.models import ChannelDB
    from .constants import SPLATTERCAST_CHANNEL, DB_COMBATANTS, DB_CHAR, NDB_COMBAT_HANDLER
    
    splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
    combatants = getattr(handler.db, DB_COMBATANTS, [])
    
    updated_count = 0
    for entry in combatants:
        char = entry.get(DB_CHAR)
        if char:
            setattr(char.ndb, NDB_COMBAT_HANDLER, handler)
            updated_count += 1
    
    splattercast.msg(f"HANDLER_REFERENCE_UPDATE: Updated {updated_count} combatants' handler references to {handler.key}.")


def validate_character_handler_reference(char):
    """
    Validate that a character's combat_handler reference points to a valid, active handler.
    
    Args:
        char: The character to validate
        
    Returns:
        tuple: (is_valid, handler_or_none, error_message)
    """
    from .constants import NDB_COMBAT_HANDLER
    
    # Check if character has a handler reference
    handler = getattr(char.ndb, NDB_COMBAT_HANDLER, None)
    if not handler:
        return False, None, "No combat_handler reference"
    
    # Check if handler still exists and is valid
    try:
        # Try to access handler attributes to verify it's still valid
        if not hasattr(handler, 'db') or not hasattr(handler.db, 'combatants'):
            return False, None, "Handler missing required attributes"
        
        # Check if character is actually in the handler's combatants list
        combatants = getattr(handler.db, 'combatants', [])
        char_in_handler = any(entry.get('char') == char for entry in combatants)
        
        if not char_in_handler:
            return False, handler, "Character not found in handler's combatants list"
        
        return True, handler, "Valid handler reference"
        
    except Exception as e:
        return False, None, f"Handler validation error: {e}"


def get_character_dbref(char):
    """
    Get DBREF for a character object.
    
    Args:
        char: The character object
        
    Returns:
        int or None: The character's DBREF
    """
    return char.id if char else None


def get_character_by_dbref(dbref):
    """
    Get character object by DBREF.
    
    Args:
        dbref: The database reference number
        
    Returns:
        Character object or None
    """
    if dbref is None:
        return None
    try:
        from evennia import search_object
        return search_object(f"#{dbref}")[0]
    except (IndexError, ValueError):
        return None


def detect_and_remove_orphaned_combatants(handler):
    """
    Detect and remove combatants who are orphaned (no valid combat relationships).
    
    An orphaned combatant is one who:
    - Has no target (target_dbref is None)
    - Is not grappling anyone (grappling_dbref is None)
    - Is not being grappled (grappled_by_dbref is None)
    - Is not being targeted by anyone else
    
    Note: Yielding status is NOT considered a valid combat relationship.
    A single yielding character with no other relationships is effectively
    orphaned since they have no one to interact with.
    
    This prevents handlers from running indefinitely when game mechanics
    create valid but inactive combat states (e.g., grapple target switching + flee).
    
    Args:
        handler: The combat handler instance
        
    Returns:
        list: List of orphaned combatants that were removed
    """
    from evennia.comms.models import ChannelDB
    from .constants import (
        SPLATTERCAST_CHANNEL, DB_COMBATANTS, DB_CHAR, DB_TARGET_DBREF,
        DB_GRAPPLING_DBREF, DB_GRAPPLED_BY_DBREF, DB_IS_YIELDING
    )
    
    splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
    combatants = getattr(handler.db, DB_COMBATANTS, [])
    orphaned_chars = []
    
    if not combatants:
        return orphaned_chars
    
    # Build a set of all character DBREFs that are being targeted
    targeted_dbrefs = set()
    for entry in combatants:
        target_dbref = entry.get(DB_TARGET_DBREF)
        if target_dbref is not None:
            targeted_dbrefs.add(target_dbref)
    
    # Check each combatant for orphan status
    for entry in combatants:
        char = entry.get(DB_CHAR)
        if not char:
            continue
            
        char_dbref = get_character_dbref(char)
        
        # Check all orphan conditions (excluding yielding status)
        has_target = entry.get(DB_TARGET_DBREF) is not None
        is_grappling = entry.get(DB_GRAPPLING_DBREF) is not None
        is_grappled = entry.get(DB_GRAPPLED_BY_DBREF) is not None
        is_targeted = char_dbref in targeted_dbrefs
        
        # Yielding status for context logging (but not considered in orphan check)
        is_yielding = entry.get(DB_IS_YIELDING, False)
        
        # If combatant has no combat relationships, they are orphaned
        if not (has_target or is_grappling or is_grappled or is_targeted):
            yield_context = " (yielding)" if is_yielding else " (not yielding)"
            splattercast.msg(f"ORPHAN_DETECT: {char.key} is orphaned{yield_context} - no target, not grappling, not grappled, not targeted")
            orphaned_chars.append(char)
    
    # Remove all orphaned combatants
    for orphaned_char in orphaned_chars:
        splattercast.msg(f"ORPHAN_REMOVE: Removing {orphaned_char.key} from combat (orphaned state)")
        remove_combatant(handler, orphaned_char)
    
    if orphaned_chars:
        char_names = [char.key for char in orphaned_chars]
        splattercast.msg(f"ORPHAN_CLEANUP: Removed {len(orphaned_chars)} orphaned combatants: {', '.join(char_names)}")
    
    return orphaned_chars


def resolve_bonus_attack(handler, attacker, target):
    """
    Resolve a bonus attack triggered by specific combat events.
    
    This is used when a character with a ranged weapon gets a bonus attack
    opportunity from failed advance or charge attempts.
    
    Args:
        handler: The combat handler instance
        attacker: The character making the bonus attack
        target: The target of the bonus attack
    """
    from evennia.comms.models import ChannelDB
    from .constants import SPLATTERCAST_CHANNEL, DB_COMBATANTS, DB_CHAR
    
    splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
    
    # Find the attacker's combat entry
    combatants_list = getattr(handler.db, DB_COMBATANTS, [])
    attacker_entry = next((e for e in combatants_list if e.get(DB_CHAR) == attacker), None)
    
    if not attacker_entry:
        splattercast.msg(f"BONUS_ATTACK_ERROR: {attacker.key} not found in combat for bonus attack.")
        return
        
    # Process the bonus attack using the same logic as regular attacks
    handler._process_attack(attacker, target, attacker_entry, combatants_list)
    
    # Log the bonus attack
    splattercast.msg(f"BONUS_ATTACK: {attacker.key} made bonus attack against {target.key}.")


# ===================================================================
# DAMAGE SYSTEM
# ===================================================================

def check_grenade_human_shield(proximity_list, combat_handler=None):
    """
    Check for human shield mechanics in grenade explosions.
    
    For characters in the proximity list who are grappling someone,
    implement simplified human shield mechanics:
    - Grappler automatically uses victim as blast shield
    - Grappler takes no damage 
    - Victim takes double damage
    
    Args:
        proximity_list: List of characters in blast radius
        combat_handler: Optional combat handler for grapple state checking
        
    Returns:
        dict: Modified damage assignments {char: damage_multiplier}
             where damage_multiplier is 0.0 for grapplers, 2.0 for victims
    """
    from evennia.comms.models import ChannelDB
    from .constants import SPLATTERCAST_CHANNEL, DB_CHAR, DB_GRAPPLING_DBREF, DB_COMBATANTS, NDB_COMBAT_HANDLER
    
    splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
    damage_modifiers = {}
    
    # If no combat handler provided, try to find one from the characters
    if not combat_handler and proximity_list:
        for char in proximity_list:
            if hasattr(char.ndb, NDB_COMBAT_HANDLER):
                combat_handler = getattr(char.ndb, NDB_COMBAT_HANDLER)
                break
    
    if not combat_handler:
        splattercast.msg("GRENADE_SHIELD: No combat handler found, skipping human shield checks")
        return damage_modifiers
    
    # Get current combatants list for grapple state checking
    combatants_list = getattr(combat_handler.db, DB_COMBATANTS, [])
    
    for char in proximity_list:
        # Find this character's combat entry
        char_entry = next((e for e in combatants_list if e.get(DB_CHAR) == char), None)
        if not char_entry:
            continue
            
        # Check if this character is grappling someone
        grappling_dbref = char_entry.get(DB_GRAPPLING_DBREF)
        if grappling_dbref:
            victim = get_character_by_dbref(grappling_dbref)
            if victim and victim in proximity_list:
                # Both grappler and victim are in blast radius - apply shield mechanics
                damage_modifiers[char] = 0.0  # Grappler takes no damage
                damage_modifiers[victim] = 2.0  # Victim takes double damage
                
                # Send human shield messages
                send_grenade_shield_messages(char, victim)
                
                splattercast.msg(f"GRENADE_SHIELD: {char.key} using {victim.key} as blast shield")
    
    return damage_modifiers


def send_grenade_shield_messages(grappler, victim):
    """
    Send human shield messages specific to grenade explosions.
    
    Args:
        grappler: The character using victim as shield
        victim: The character being used as shield
    """
    # Grenade-specific shield messages
    grappler_msg = f"|yYou instinctively position {get_display_name_safe(victim)} between yourself and the explosion!|n"
    victim_msg = f"|RYou are forced to absorb the full blast as {get_display_name_safe(grappler)} uses you as a shield!|n"
    observer_msg = f"|y{get_display_name_safe(grappler)} uses {get_display_name_safe(victim)} as a human shield against the explosion!|n"
    
    # Send messages
    grappler.msg(grappler_msg)
    victim.msg(victim_msg)
    
    # Send to observers in the same location (exclude the two participants)
    if grappler.location:
        grappler.location.msg_contents(observer_msg, exclude=[grappler, victim])
