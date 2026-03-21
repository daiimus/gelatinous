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
from evennia.comms.models import ChannelDB
from .constants import (
    DEFAULT_MOTORICS, MIN_DICE_VALUE, SPLATTERCAST_CHANNEL,
    DEBUG_TEMPLATE, NDB_PROXIMITY, COLOR_NORMAL,
    DB_COMBAT_ACTION, DB_COMBAT_ACTION_TARGET, DB_INITIATIVE,
    WEAPON_TYPE_UNARMED, DB_CHAR, DB_TARGET_DBREF, DB_IS_YIELDING
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
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        if splattercast:
            formatted_msg = f"{prefix}_{status}: {message}"
            splattercast.msg(formatted_msg)
    except Exception:
        # Fail silently if channel not available
        pass


class _NullChannel:
    """No-op channel stand-in when Splattercast is unavailable."""

    def msg(self, *args, **kwargs):
        pass


def get_splattercast():
    """
    Safely retrieve the Splattercast debug channel.

    Returns:
        The channel object, or a no-op stand-in if unavailable.
    """
    channel = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
    return channel if channel else _NullChannel()


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
        if weapon and hasattr(weapon, 'db') and weapon.db.is_ranged:
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
    
    damage = weapon.db.damage if weapon.db.damage is not None else default
    
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
    from .constants import (
        SPLATTERCAST_CHANNEL, DB_COMBATANTS, DB_CHAR, DB_TARGET_DBREF,
        DB_GRAPPLING_DBREF, DB_GRAPPLED_BY_DBREF, DB_IS_YIELDING, 
        NDB_PROXIMITY, NDB_COMBAT_HANDLER, DB_COMBAT_RUNNING
    )
    from random import randint
    
    splattercast = get_splattercast()
    
    # Debug: Show what parameters were passed
    splattercast.msg(f"ADD_COMBATANT_PARAMS: char={char.key if char else None}, target={target.key if target else None}")
    
    # Prevent self-targeting
    if target and char == target:
        splattercast.msg(f"ADD_COMBATANT_ERROR: {char.key} cannot target themselves! Setting target to None.")
        target = None
    
    # Check if already in combat
    combatants = handler.db.combatants or []
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
        DB_INITIATIVE: randint(1, 20) + get_numeric_stat(char, "motorics", 0),
        DB_TARGET_DBREF: target_dbref,
        DB_GRAPPLING_DBREF: get_character_dbref(initial_grappling),
        DB_GRAPPLED_BY_DBREF: get_character_dbref(initial_grappled_by),
        DB_IS_YIELDING: initial_is_yielding,
        DB_COMBAT_ACTION: None
    }
    
    splattercast.msg(f"ADD_COMBATANT_ENTRY: {char.key} -> target_dbref={target_dbref}, initiative={entry[DB_INITIATIVE]}")
    
    combatants.append(entry)
    handler.db.combatants = combatants
    
    # Set the character's handler reference
    setattr(char.ndb, NDB_COMBAT_HANDLER, handler)
    
    # Set combat override_place (only if not already set to something more specific)
    if not hasattr(char, 'override_place') or not char.override_place or char.override_place == "":
        char.override_place = "locked in combat."
        splattercast.msg(f"ADD_COMB: Set {char.key} override_place to 'locked in combat.'")
    else:
        splattercast.msg(f"ADD_COMB: {char.key} already has override_place: '{char.override_place}' - not overriding")
    
    splattercast.msg(f"ADD_COMB: {char.key} added to combat in {handler.key} with initiative {entry[DB_INITIATIVE]}.")
    
    # Establish proximity for grappled pairs when adding to new handler
    from .proximity import establish_proximity
    if initial_grappling:
        establish_proximity(char, initial_grappling)
        splattercast.msg(f"ADD_COMB: Established proximity between {char.key} and grappled victim {initial_grappling.key}.")
    if initial_grappled_by:
        establish_proximity(char, initial_grappled_by)
        splattercast.msg(f"ADD_COMB: Established proximity between {char.key} and grappler {initial_grappled_by.key}.")
    
    # Start combat if not already running
    if not handler.db.combat_is_running:
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
    from .constants import (
        DB_COMBATANTS, DB_CHAR, DB_TARGET_DBREF
    )
    
    splattercast = get_splattercast()
    
    # Use the active working list if available (during round processing), otherwise use database
    active_list = getattr(handler, '_active_combatants_list', None)
    if active_list:
        combatants = active_list
        splattercast.msg(f"RMV_COMB: Using active working list with {len(combatants)} entries")
    else:
        combatants = handler.db.combatants or []
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
            other_char = other_entry.get(DB_CHAR)
            if not other_char:
                continue
            splattercast.msg(f"RMV_COMB: Cleared {other_char.key}'s target_dbref (was {char.key})")
            
            # Attempt smart auto-retargeting: find someone who is actively attacking this character
            # For melee weapons, prioritize targets in proximity; for ranged weapons, any attacker is fine
            other_char_weapon = get_wielded_weapon(other_char)
            other_char_is_ranged = other_char_weapon and hasattr(other_char_weapon, "db") and other_char_weapon.db.is_ranged
            
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
                    except Exception:
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
                other_char_entry_working = next((e for e in combatants if e.get(DB_CHAR) == other_char), None)
                if other_char_entry_working:
                    other_char_entry_working[DB_TARGET_DBREF] = get_character_dbref(new_target)
                    other_char_entry_working[DB_COMBAT_ACTION] = None
                    other_char_entry_working[DB_COMBAT_ACTION_TARGET] = None 
                    other_char_entry_working[DB_IS_YIELDING] = False
                    splattercast.msg(f"RMV_COMB: Updated working list for {other_char.key} -> target_dbref={other_char_entry_working[DB_TARGET_DBREF]}")
                
                # Also update database to ensure persistence (same as attack command)
                combatants_copy = handler.db.combatants or []
                other_char_entry_copy = next((e for e in combatants_copy if e.get(DB_CHAR) == other_char), None)
                if other_char_entry_copy:
                    other_char_entry_copy[DB_TARGET_DBREF] = get_character_dbref(new_target)
                    other_char_entry_copy[DB_COMBAT_ACTION] = None
                    other_char_entry_copy[DB_COMBAT_ACTION_TARGET] = None 
                    other_char_entry_copy[DB_IS_YIELDING] = False
                    
                    # Save the modified combatants list back (same as attack command)
                    handler.db.combatants = combatants_copy
                    splattercast.msg(f"RMV_COMB: Updated database using attack command pattern for {other_char.key}")
                
                # Get weapon info for initiate message
                from .messages import get_combat_message
                weapon_obj = get_wielded_weapon(other_char)
                weapon_type = WEAPON_TYPE_UNARMED
                if weapon_obj and hasattr(weapon_obj, 'db') and weapon_obj.db.weapon_type is not None:
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
    
    # Remove from combatants list using in-place mutation so the active
    # working list (handler._active_combatants_list) stays in sync.
    combatants[:] = [e for e in combatants if e.get(DB_CHAR) != char]
    
    # Always persist to database
    handler.db.combatants = combatants
    if active_list:
        splattercast.msg(f"RMV_COMB: Mutated active list in-place and synced to database")
    else:
        splattercast.msg(f"RMV_COMB: Updated database directly")
    
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
    
    # Clear aim state (aiming_at, aimed_at_by, aiming_direction)
    clear_aim_state(char)
    
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
    
    # Clear combat-related override_place values.
    # Combat sets several variants: "locked in combat.", "locked in a deadly showdown.",
    # "aiming carefully at {name}.", "aiming carefully to the {direction}."
    # We must NOT clear non-combat overrides like "unconscious and motionless." or
    # "lying motionless and deceased." which belong to the medical/death systems.
    combat_override_prefixes = ("locked in combat", "locked in a deadly showdown", "aiming carefully")
    if (hasattr(char, 'override_place') and 
        char.override_place and
        any(char.override_place.startswith(prefix) for prefix in combat_override_prefixes)):
        splattercast = get_splattercast()
        splattercast.msg(f"CLEANUP_COMB: Cleared combat override_place '{char.override_place}' for {char.key}")
        char.override_place = ""
    
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
    from .constants import DB_COMBATANTS, DB_CHAR, DEBUG_PREFIX_HANDLER, DEBUG_CLEANUP
    
    splattercast = get_splattercast()
    combatants = handler.db.combatants or []
    
    for entry in combatants:
        char = entry.get(DB_CHAR)
        if char:
            cleanup_combatant_state(char, entry, handler)
    
    # Clear the combatants list
    handler.db.combatants = []
    splattercast.msg(f"{DEBUG_PREFIX_HANDLER}_{DEBUG_CLEANUP}: All combatants cleaned up for {handler.key}.")


# ===================================================================
# COMBATANT UTILITY FUNCTIONS
# ===================================================================

def get_combatant_target(entry, handler):
    """Get the target object for a combatant entry."""
    target_dbref = entry.get(DB_TARGET_DBREF)
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
    from .constants import DB_COMBATANTS, DB_CHAR, NDB_COMBAT_HANDLER
    
    splattercast = get_splattercast()
    combatants = handler.db.combatants or []
    
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
        if not hasattr(handler, 'db') or handler.db.combatants is None:
            return False, None, "Handler missing required attributes"
        
        # Check if character is actually in the handler's combatants list
        combatants = handler.db.combatants or []
        char_in_handler = any(entry.get(DB_CHAR) == char for entry in combatants)
        
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


def get_combatants_safe(handler):
    """
    Safely retrieve the combatants list from a handler, ensuring it's never None.
    
    This handles edge cases where DB_COMBATANTS might be explicitly set to None
    rather than just missing, which can cause 'NoneType' object is not iterable errors.
    
    Args:
        handler: The combat handler instance
        
    Returns:
        list: The combatants list, or an empty list if None/missing
    """
    from .constants import DB_COMBATANTS, DEBUG_PREFIX_HANDLER
    
    combatants = handler.db.combatants
    if combatants is None:
        splattercast = get_splattercast()
        splattercast.msg(f"{DEBUG_PREFIX_HANDLER}_WARNING: {DB_COMBATANTS} was None for handler {handler.key}, initializing to empty list.")
        combatants = []
        # Only set the attribute if the handler has been saved to the database
        # Otherwise we get "needs to have a value for field 'id'" errors
        if hasattr(handler, 'id') and handler.id:
            handler.db.combatants = combatants
        else:
            splattercast.msg(f"{DEBUG_PREFIX_HANDLER}_WARNING: Handler {handler.key} not yet saved to DB, cannot set {DB_COMBATANTS}.")
    return combatants


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
    from .constants import (
        DB_COMBATANTS, DB_CHAR, DB_TARGET_DBREF,
        DB_GRAPPLING_DBREF, DB_GRAPPLED_BY_DBREF, DB_IS_YIELDING
    )
    
    splattercast = get_splattercast()
    combatants = handler.db.combatants or []
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
    from .constants import DB_COMBATANTS, DB_CHAR
    
    splattercast = get_splattercast()
    
    # Find the attacker's combat entry
    combatants_list = handler.db.combatants or []
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
    from .constants import DB_CHAR, DB_GRAPPLING_DBREF, DB_COMBATANTS, NDB_COMBAT_HANDLER
    
    splattercast = get_splattercast()
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
    combatants_list = combat_handler.db.combatants or []
    
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


# ===================================================================
# STICKY GRENADE HELPERS
# ===================================================================

def calculate_stick_chance(grenade, armor):
    """
    Calculate the chance that a sticky grenade will adhere to armor.
    
    Stick Criteria:
    1. Check armor base metal/magnetic levels
    2. If armor is a plate carrier, check installed plates for highest values
    3. Threshold check: magnetic_level >= (grenade_strength - 3) AND 
                       metal_level >= (grenade_strength - 5)
    4. If threshold met: chance = 40 + (metal_level * 5) + (magnetic_level * 5)
    5. Maximum 95% chance (always 5% chance to fail)
    
    Args:
        grenade: The sticky grenade object with magnetic_strength attribute
        armor: The armor Item with metal_level and magnetic_level attributes
    
    Returns:
        int: Percentage chance to stick (0-95), or 0 if thresholds not met
        
    Example:
        # Steel plate (metal=10, magnetic=10) vs medium grenade (strength=5)
        # Thresholds: magnetic >= 2, metal >= 0 (both pass)
        # Chance: 40 + (10*5) + (10*5) = 140 -> capped at 95%
        
        # Cloth vest (metal=0, magnetic=0) vs any grenade
        # Thresholds: fail -> 0% chance
        
        # Plate carrier with steel plate installed
        # Checks both carrier properties AND installed plate properties
    """
    from typeclasses.items import Item
    
    # Validate inputs
    if not grenade or not armor:
        return 0
    
    # Get grenade magnetic strength (default 5 if not set)
    magnetic_strength = grenade.db.magnetic_strength if grenade.db.magnetic_strength is not None else 5
    
    # Get armor base properties (default 0 if not set)
    metal_level = armor.db.metal_level if armor.db.metal_level is not None else 0
    magnetic_level = armor.db.magnetic_level if armor.db.magnetic_level is not None else 0
    
    # PLATE CARRIER CHECK: If this is a plate carrier, check installed plates
    is_plate_carrier = armor.db.is_plate_carrier
    if is_plate_carrier:
        installed_plates = armor.db.installed_plates or {}
        
        # Check all installed plates and use highest metal/magnetic values
        for slot, plate_ref in installed_plates.items():
            if plate_ref:
                # Get plate properties
                plate_metal = plate_ref.db.metal_level if plate_ref.db.metal_level is not None else 0
                plate_magnetic = plate_ref.db.magnetic_level if plate_ref.db.magnetic_level is not None else 0
                
                # Use highest values between carrier and plates
                metal_level = max(metal_level, plate_metal)
                magnetic_level = max(magnetic_level, plate_magnetic)
                
                debug_broadcast(
                    f"Plate carrier check: {armor.key} slot {slot} has {plate_ref.key} "
                    f"(metal={plate_metal}, magnetic={plate_magnetic})",
                    prefix="STICKY_GRENADE",
                    status="PLATE_CHECK"
                )
        
        debug_broadcast(
            f"Plate carrier final values: metal={metal_level}, magnetic={magnetic_level}",
            prefix="STICKY_GRENADE",
            status="PLATE_FINAL"
        )
    
    # Calculate thresholds
    magnetic_threshold = magnetic_strength - 3
    metal_threshold = magnetic_strength - 5
    
    # Check if thresholds are met
    if magnetic_level < magnetic_threshold or metal_level < metal_threshold:
        debug_broadcast(
            f"Stick failed threshold: {grenade.key} vs {armor.key} "
            f"(magnetic {magnetic_level}/{magnetic_threshold}, "
            f"metal {metal_level}/{metal_threshold})",
            prefix="STICKY_GRENADE",
            status="THRESHOLD_FAIL"
        )
        return 0
    
    # Calculate base chance
    chance = 40 + (metal_level * 5) + (magnetic_level * 5)
    
    # Cap at 95% (always 5% failure chance)
    chance = min(chance, 95)
    
    debug_broadcast(
        f"Stick chance: {grenade.key} vs {armor.key} = {chance}% "
        f"(metal={metal_level}, magnetic={magnetic_level}, strength={magnetic_strength})",
        prefix="STICKY_GRENADE",
        status="CALC"
    )
    
    return chance


def get_explosion_room(grenade):
    """
    Get the room where a grenade will explode, handling armor hierarchy.
    
    This traverses the location hierarchy to find the room:
    - grenade.location = armor -> armor.location = character/room
    - grenade.location = character -> character.location = room
    - grenade.location = room -> room itself
    
    Args:
        grenade: The grenade object
    
    Returns:
        Room object or None if grenade has no valid explosion location
        
    Example:
        # Stuck to worn armor: grenade -> armor -> character -> room
        room = get_explosion_room(grenade)  # Returns room
        
        # On ground: grenade -> room
        room = get_explosion_room(grenade)  # Returns room
    """
    from typeclasses.characters import Character
    from typeclasses.rooms import Room
    from typeclasses.items import Item
    
    if not grenade or not grenade.location:
        debug_broadcast(
            f"Explosion room lookup failed: grenade has no location",
            prefix="STICKY_GRENADE",
            status="ERROR"
        )
        return None
    
    location = grenade.location
    
    # If grenade is in/on an Item (armor), go up one level
    if isinstance(location, Item):
        debug_broadcast(
            f"Grenade {grenade.key} stuck to armor {location.key}, checking armor location",
            prefix="STICKY_GRENADE",
            status="HIERARCHY"
        )
        location = location.location
    
    # If we're now at a Character, go up one more level to room
    if isinstance(location, Character):
        debug_broadcast(
            f"Grenade on character {location.key}, getting their room",
            prefix="STICKY_GRENADE",
            status="HIERARCHY"
        )
        location = location.location
    
    # Validate we have a room
    if isinstance(location, Room):
        debug_broadcast(
            f"Explosion room for {grenade.key}: {location.key}",
            prefix="STICKY_GRENADE",
            status="SUCCESS"
        )
        return location
    
    debug_broadcast(
        f"Explosion room lookup failed: final location is {type(location).__name__}",
        prefix="STICKY_GRENADE",
        status="ERROR"
    )
    return None


def establish_stick(grenade, armor, hit_location):
    """
    Establish bidirectional sticky grenade relationship.
    
    Sets up the magnetic bond between grenade and armor:
    - grenade.location = armor (physical containment)
    - grenade.db.stuck_to_armor = armor (reference)
    - grenade.db.stuck_to_location = hit_location (body part)
    - armor.db.stuck_grenade = grenade (bidirectional reference)
    
    Args:
        grenade: The sticky grenade object
        armor: The armor Item object
        hit_location: String indicating body location (e.g., "chest", "head")
    
    Returns:
        bool: True if stick established successfully
        
    Example:
        if establish_stick(grenade, steel_vest, "chest"):
            # Grenade is now magnetically bonded to vest
            # Will move with vest when removed
    """
    from typeclasses.items import Item
    
    # Validate inputs
    if not grenade or not armor or not isinstance(armor, Item):
        debug_broadcast(
            f"Stick establishment failed: invalid inputs",
            prefix="STICKY_GRENADE",
            status="ERROR"
        )
        return False
    
    # Break any existing stick first
    if grenade.db.stuck_to_armor:
        old_armor = grenade.db.stuck_to_armor
        if old_armor and old_armor.db.stuck_grenade is not None:
            old_armor.db.stuck_grenade = None
    
    # Establish new stick - grenade moves to armor
    grenade.location = armor
    
    # Set grenade attributes
    grenade.db.stuck_to_armor = armor
    grenade.db.stuck_to_location = hit_location
    
    # Set armor attribute (bidirectional reference)
    armor.db.stuck_grenade = grenade
    
    debug_broadcast(
        f"Stick established: {grenade.key} -> {armor.key} at {hit_location}",
        prefix="STICKY_GRENADE",
        status="SUCCESS"
    )
    
    return True


def get_stuck_grenades_on_character(character):
    """
    Get all sticky grenades currently stuck to a character's armor.
    
    Searches all worn items for stuck grenades.
    
    Args:
        character: The Character object to check
    
    Returns:
        list: List of tuples (grenade, armor, location) for each stuck grenade
        
    Example:
        stuck = get_stuck_grenades_on_character(bob)
        for grenade, armor, location in stuck:
            print(f"{grenade.key} stuck to {armor.key} at {location}")
    """
    from typeclasses.characters import Character
    from typeclasses.items import Item
    
    if not isinstance(character, Character):
        return []
    
    stuck_grenades = []
    
    # Check all items in character's inventory
    for item in character.contents:
        if not isinstance(item, Item):
            continue
        
        # Check if this item has a stuck grenade
        if item.db.stuck_grenade:
            grenade = item.db.stuck_grenade
            location = grenade.db.stuck_to_location if grenade.db.stuck_to_location is not None else 'unknown'
            stuck_grenades.append((grenade, item, location))
            
            debug_broadcast(
                f"Found stuck grenade: {grenade.key} on {item.key} ({location})",
                prefix="STICKY_GRENADE",
                status="FOUND"
            )
    
    return stuck_grenades


def get_outermost_armor_at_location(character, hit_location):
    """
    Get the outermost armor piece at a specific body location.
    
    Searches worn items for highest layer number at the hit location.
    
    Args:
        character: The Character object
        hit_location: Body location string (e.g., "chest", "head", "left_arm")
    
    Returns:
        Item: The outermost armor at that location, or None if no armor
        
    Example:
        # Character wearing shirt (layer 1) and vest (layer 3) on chest
        armor = get_outermost_armor_at_location(bob, "chest")
        # Returns vest (higher layer)
    """
    from typeclasses.characters import Character
    from typeclasses.items import Item
    
    if not isinstance(character, Character):
        return None
    
    outermost_armor = None
    highest_layer = -1
    
    # Check all worn items
    for item in character.contents:
        if not isinstance(item, Item):
            continue
        
        # Check if item covers this location
        coverage = item.db.coverage or []
        if not coverage or hit_location not in coverage:
            continue
        
        # Check layer
        layer = item.db.layer if item.db.layer is not None else 0
        if layer > highest_layer:
            highest_layer = layer
            outermost_armor = item
    
    if outermost_armor:
        debug_broadcast(
            f"Outermost armor at {hit_location}: {outermost_armor.key} (layer {highest_layer})",
            prefix="STICKY_GRENADE",
            status="FOUND"
        )
    else:
        debug_broadcast(
            f"No armor found at {hit_location}",
            prefix="STICKY_GRENADE",
            status="NOT_FOUND"
        )
    
    return outermost_armor


def break_stick(grenade):
    """
    Break the magnetic bond between grenade and armor.
    
    Cleans up all bidirectional references. Grenade location is NOT changed
    (caller must handle that separately if needed).
    
    Args:
        grenade: The sticky grenade object
    
    Returns:
        bool: True if stick was broken, False if no stick existed
        
    Example:
        if break_stick(grenade):
            # Magnetic bond broken
            grenade.location = room  # Move to room
    """
    if not grenade:
        return False
    
    # Check if grenade is stuck
    if not grenade.db.stuck_to_armor:
        return False
    
    armor = grenade.db.stuck_to_armor
    location = grenade.db.stuck_to_location if grenade.db.stuck_to_location is not None else 'unknown'
    
    # Clear armor's reference to grenade
    if armor and armor.db.stuck_grenade is not None:
        armor.db.stuck_grenade = None
    
    # Clear grenade's references
    grenade.db.stuck_to_armor = None
    grenade.db.stuck_to_location = None
    
    debug_broadcast(
        f"Stick broken: {grenade.key} from {armor.key if armor else 'unknown'} at {location}",
        prefix="STICKY_GRENADE",
        status="BREAK"
    )
    
    return True
