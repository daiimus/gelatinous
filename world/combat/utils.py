"""
Combat System Utilities

Shared utility functions used throughout the combat system.
Organised following Python best practices while maintaining
Evennia conventions and backward compatibility.

Functions remaining in this module:
    - Character state management (proximity, aim)
    - Weapon & item helpers
    - Message formatting
    - Validation helpers
    - Stat management helpers
    - Combatant management (add, remove, cleanup)

Functions extracted to dedicated modules (re-exported here for
backward compatibility):
    - ``debug``  — debug_broadcast, get_splattercast, log_debug,
      log_combat_action, _NullChannel
    - ``dice``   — get_character_stat, roll_stat, opposed_roll,
      roll_with_advantage, roll_with_disadvantage, standard_roll
    - ``explosives`` — check_grenade_human_shield,
      send_grenade_shield_messages, calculate_stick_chance,
      get_explosion_room, establish_stick,
      get_stuck_grenades_on_character, get_outermost_armor_at_location,
      break_stick
"""

from __future__ import annotations

from random import randint

from .constants import (
    COLOR_NORMAL,
    DB_CHAR,
    DB_COMBAT_ACTION,
    DB_COMBAT_ACTION_TARGET,
    DB_INITIATIVE,
    DB_IS_YIELDING,
    DB_TARGET_DBREF,
    DEFAULT_MOTORICS,
    NDB_PROXIMITY,
    WEAPON_TYPE_UNARMED,
)
from .debug import get_splattercast, log_debug


# ===================================================================
# BACKWARD-COMPATIBLE RE-EXPORTS
#
# External consumers (commands/, typeclasses/, world/medical/, …)
# import these symbols from ``world.combat.utils``.  The canonical
# definitions now live in their own modules, but we re-export them
# here so every ``from world.combat.utils import X`` keeps working.
# ===================================================================

from .debug import (  # noqa: F401 — re-export
    _NullChannel,
    debug_broadcast,
    get_splattercast,
    log_combat_action,
    log_debug,
)
from .dice import (  # noqa: F401 — re-export
    get_character_stat,
    opposed_roll,
    roll_stat,
    roll_with_advantage,
    roll_with_disadvantage,
    standard_roll,
)
from .explosives import (  # noqa: F401 — re-export
    break_stick,
    calculate_stick_chance,
    check_grenade_human_shield,
    establish_stick,
    get_explosion_room,
    get_outermost_armor_at_location,
    get_stuck_grenades_on_character,
    send_grenade_shield_messages,
)


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
        log_debug("PROXIMITY", "CLEAR", "Cleared all proximity", character)


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
    
    log_debug("AIM", "CLEAR", "Cleared aim state", character)


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
        splattercast.msg("RMV_COMB: Mutated active list in-place and synced to database")
    else:
        splattercast.msg("RMV_COMB: Updated database directly")
    
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
