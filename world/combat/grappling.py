"""
Combat Grappling System

Handles all grappling-related logic for the combat system.
Extracted from combathandler.py and CmdCombat.py to improve
organization and maintainability.

Functions:
- Grapple establishment and breaking
- Grapple state validation
- Grapple relationship management
- Integration with proximity system
"""

from .constants import (
    DB_GRAPPLING_DBREF, DB_GRAPPLED_BY_DBREF, 
    MSG_CANNOT_WHILE_GRAPPLED, MSG_CANNOT_GRAPPLE_SELF, MSG_ALREADY_GRAPPLING,
    MSG_GRAPPLE_AUTO_YIELD
)
from .utils import log_debug, get_display_name_safe
from .proximity import establish_proximity, is_in_proximity


def get_character_by_dbref(dbref):
    """
    Helper to get character by dbref with error handling.
    
    Args:
        dbref: Database reference number
        
    Returns:
        Character or None
    """
    if not dbref:
        return None
    
    try:
        from evennia import search_object
        results = search_object(f"#{dbref}")
        return results[0] if results else None
    except (ValueError, TypeError, ImportError):
        return None


def get_grappling_target(combat_handler, combatant_entry):
    """
    Get the character that this combatant is grappling.
    
    Args:
        combat_handler: The combat handler script
        combatant_entry (dict): The combatant's entry in the handler
        
    Returns:
        Character or None: The grappled character
    """
    grappling_dbref = combatant_entry.get(DB_GRAPPLING_DBREF)
    return get_character_by_dbref(grappling_dbref)


def get_grappled_by(combat_handler, combatant_entry):
    """
    Get the character that is grappling this combatant.
    
    Args:
        combat_handler: The combat handler script
        combatant_entry (dict): The combatant's entry in the handler
        
    Returns:
        Character or None: The grappling character
    """
    grappled_by_dbref = combatant_entry.get(DB_GRAPPLED_BY_DBREF)
    return get_character_by_dbref(grappled_by_dbref)


def establish_grapple(combat_handler, grappler, victim):
    """
    Establish a grapple between two characters.
    
    Args:
        combat_handler: The combat handler script
        grappler: Character doing the grappling
        victim: Character being grappled
        
    Returns:
        tuple: (success, message)
    """
    if grappler == victim:
        return False, MSG_CANNOT_GRAPPLE_SELF
    
    # Get combatant entries
    grappler_entry = None
    victim_entry = None
    
    combatants_list = list(combat_handler.db.combatants)
    for entry in combatants_list:
        if entry.get("char") == grappler:
            grappler_entry = entry
        elif entry.get("char") == victim:
            victim_entry = entry
    
    if not grappler_entry or not victim_entry:
        return False, "Combat entries not found."
    
    # Check if grappler is already grappling someone
    if grappler_entry.get(DB_GRAPPLING_DBREF):
        current_target = get_grappling_target(combat_handler, grappler_entry)
        if current_target:
            return False, MSG_ALREADY_GRAPPLING.format(target=get_display_name_safe(current_target, grappler))
    
    # Check if victim is already being grappled
    if victim_entry.get(DB_GRAPPLED_BY_DBREF):
        current_grappler = get_grappled_by(combat_handler, victim_entry)
        if current_grappler:
            return False, f"{get_display_name_safe(victim, grappler)} is already being grappled by {get_display_name_safe(current_grappler, grappler)}."
    
    # Establish the grapple
    for i, entry in enumerate(combatants_list):
        if entry.get("char") == grappler:
            combatants_list[i][DB_GRAPPLING_DBREF] = victim.id
            # Grappler starts in restraint mode (yielding)
            combatants_list[i]["is_yielding"] = True
        elif entry.get("char") == victim:
            combatants_list[i][DB_GRAPPLED_BY_DBREF] = grappler.id
            # Victim automatically yields when grappled (restraint mode)
            combatants_list[i]["is_yielding"] = True
    
    # Save the updated list
    combat_handler.db.combatants = combatants_list
    
    # Ensure proximity (grappling requires proximity)
    establish_proximity(grappler, victim)
    
    # Notify victim they're auto-yielding
    victim.msg(MSG_GRAPPLE_AUTO_YIELD)
    
    log_debug("GRAPPLE", "ESTABLISH", f"{grappler.key} grapples {victim.key}")
    
    return True, f"You successfully grapple {get_display_name_safe(victim, grappler)}!"


def break_grapple(combat_handler, grappler=None, victim=None):
    """
    Break a grapple relationship.
    
    Args:
        combat_handler: The combat handler script
        grappler: Character doing the grappling (optional if victim provided)
        victim: Character being grappled (optional if grappler provided)
        
    Returns:
        tuple: (success, message)
    """
    if not grappler and not victim:
        return False, "Must specify either grappler or victim."
    
    combatants_list = list(combat_handler.db.combatants)
    grapple_broken = False
    
    # Find and break the grapple
    for i, entry in enumerate(combatants_list):
        char = entry.get("char")
        
        if grappler and char == grappler:
            if entry.get(DB_GRAPPLING_DBREF):
                combatants_list[i][DB_GRAPPLING_DBREF] = None
                grapple_broken = True
        
        if victim and char == victim:
            if entry.get(DB_GRAPPLED_BY_DBREF):
                combatants_list[i][DB_GRAPPLED_BY_DBREF] = None
                grapple_broken = True
    
    if grapple_broken:
        # Save the updated list
        combat_handler.db.combatants = combatants_list
        
        grappler_name = get_display_name_safe(grappler) if grappler else "someone"
        victim_name = get_display_name_safe(victim) if victim else "someone"
        
        log_debug("GRAPPLE", "BREAK", f"{grappler_name} -> {victim_name}")
        
        return True, "Grapple broken."
    
    return False, "No grapple found to break."


def is_grappling(combat_handler, character):
    """
    Check if a character is grappling someone.
    
    Args:
        combat_handler: The combat handler script
        character: Character to check
        
    Returns:
        bool: True if character is grappling someone
    """
    for entry in combat_handler.db.combatants:
        if entry.get("char") == character:
            return bool(entry.get(DB_GRAPPLING_DBREF))
    return False


def is_grappled(combat_handler, character):
    """
    Check if a character is being grappled.
    
    Args:
        combat_handler: The combat handler script
        character: Character to check
        
    Returns:
        bool: True if character is being grappled
    """
    for entry in combat_handler.db.combatants:
        if entry.get("char") == character:
            return bool(entry.get(DB_GRAPPLED_BY_DBREF))
    return False


def validate_grapple_action(combat_handler, character, action_name):
    """
    Validate if a character can perform an action while grappled/grappling.
    
    Args:
        combat_handler: The combat handler script
        character: Character attempting the action
        action_name (str): Name of the action being attempted
        
    Returns:
        tuple: (can_perform, error_message)
    """
    # Check if being grappled
    for entry in combat_handler.db.combatants:
        if entry.get("char") == character:
            grappled_by_dbref = entry.get(DB_GRAPPLED_BY_DBREF)
            if grappled_by_dbref:
                grappler = get_grappled_by(combat_handler, entry)
                if grappler:
                    grappler_name = get_display_name_safe(grappler, character)
                    message = MSG_CANNOT_WHILE_GRAPPLED.format(
                        action=action_name,
                        grappler=grappler_name
                    )
                    return False, message
    
    return True, ""


def cleanup_invalid_grapples(combat_handler):
    """
    Clean up grapple relationships with invalid characters.
    
    Args:
        combat_handler: The combat handler script
    """
    combatants_list = list(combat_handler.db.combatants)
    cleaned = False
    
    for i, entry in enumerate(combatants_list):
        char = entry.get("char")
        if not char:
            continue
        
        # Check grappling target
        grappling_dbref = entry.get(DB_GRAPPLING_DBREF)
        if grappling_dbref:
            target = get_grappling_target(combat_handler, entry)
            if not target or not hasattr(target, 'location') or target.location != char.location:
                combatants_list[i][DB_GRAPPLING_DBREF] = None
                cleaned = True
                log_debug("GRAPPLE", "CLEANUP", f"Removed invalid grappling target from {char.key}")
        
        # Check grappled by
        grappled_by_dbref = entry.get(DB_GRAPPLED_BY_DBREF)
        if grappled_by_dbref:
            grappler = get_grappled_by(combat_handler, entry)
            if not grappler or not hasattr(grappler, 'location') or grappler.location != char.location:
                combatants_list[i][DB_GRAPPLED_BY_DBREF] = None
                cleaned = True
                log_debug("GRAPPLE", "CLEANUP", f"Removed invalid grappler from {char.key}")
    
    if cleaned:
        combat_handler.db.combatants = combatants_list


# ===================================================================
# GRAPPLE ACTION RESOLVERS (moved from handler.py)
# ===================================================================

def resolve_grapple_initiate(char_entry, combatants_list, handler):
    """
    Resolve a grapple initiate action.
    
    Args:
        char_entry: The character's combat entry
        combatants_list: List of all combatants
        handler: The combat handler instance
    """
    from evennia.comms.models import ChannelDB
    from .constants import (
        SPLATTERCAST_CHANNEL, NDB_PROXIMITY, DB_CHAR, DB_TARGET_DBREF,
        DB_GRAPPLING_DBREF, DB_GRAPPLED_BY_DBREF, DB_IS_YIELDING
    )
    from .utils import get_numeric_stat
    from random import randint
    
    splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
    char = char_entry.get(DB_CHAR)
    
    # Find who they're trying to grapple
    target = handler.get_target_obj(char_entry)
    if not target:
        char.msg("You have no target to grapple.")
        return
    
    # Check if target is in combat
    target_entry = next((e for e in combatants_list if e.get(DB_CHAR) == target), None)
    if not target_entry:
        char.msg(f"{target.key} is not in combat.")
        return
    
    # Check proximity
    if not hasattr(char.ndb, NDB_PROXIMITY):
        setattr(char.ndb, NDB_PROXIMITY, set())
    if target not in getattr(char.ndb, NDB_PROXIMITY):
        char.msg(f"You need to be in melee proximity with {target.key} to grapple them.")
        return
    
    # Roll for grapple
    attacker_roll = randint(1, max(1, get_numeric_stat(char, "motorics", 1)))
    defender_roll = randint(1, max(1, get_numeric_stat(target, "motorics", 1)))
    
    if attacker_roll > defender_roll:
        # Success
        char_entry[DB_GRAPPLING_DBREF] = get_character_dbref(target)
        target_entry[DB_GRAPPLED_BY_DBREF] = get_character_dbref(char)
        
        # Set victim's target to the grappler for potential retaliation after escape/release
        target_entry[DB_TARGET_DBREF] = get_character_dbref(char)
        
        # Auto-yield only the grappler (restraint intent)
        # The victim remains non-yielding so they auto-resist each turn
        char_entry[DB_IS_YIELDING] = True
        # target_entry[DB_IS_YIELDING] = False  # Keep victim non-yielding for auto-resistance
        
        char.msg(f"|gYou successfully grapple {target.key}!|n")
        target.msg(f"|g{char.key} grapples you!|n")
        # Note: No auto-yield message for victim since they remain non-yielding to auto-resist
        
        if char.location:
            char.location.msg_contents(
                f"|g{char.key} grapples {target.key}!|n",
                exclude=[char, target]
            )
        
        splattercast.msg(f"GRAPPLE_SUCCESS: {char.key} grappled {target.key}.")
    else:
        # Failure
        char.msg(f"|yYou fail to grapple {target.key}.|n")
        target.msg(f"|y{char.key} fails to grapple you.|n")
        
        # Check if grappler initiated combat - if so, they should become yielding on failure
        initiated_combat = char_entry.get("initiated_combat_this_action", False)
        if initiated_combat:
            char_entry[DB_IS_YIELDING] = True
            char.msg("|gYour failed grapple attempt leaves you non-aggressive.|n")
            splattercast.msg(f"GRAPPLE_FAIL_YIELD: {char.key} initiated combat with grapple but failed, setting to yielding.")
            
            # Also set the target to yielding since the grapple was a non-violent initiation
            target_entry[DB_IS_YIELDING] = True
            target.msg("|gAfter the failed grapple attempt, you also stand down from aggression.|n")
            splattercast.msg(f"GRAPPLE_FAIL_YIELD: {target.key} also set to yielding after failed grapple initiation.")
        
        if char.location:
            char.location.msg_contents(
                f"|y{char.key} fails to grapple {target.key}.|n",
                exclude=[char, target]
            )
        
        splattercast.msg(f"GRAPPLE_FAIL: {char.key} failed to grapple {target.key}.")


def resolve_grapple_join(char_entry, combatants_list, handler):
    """
    Resolve a grapple join action - contest between new grappler and current grappler.
    
    Args:
        char_entry: The character's combat entry
        combatants_list: List of all combatants
        handler: The combat handler instance
    """
    from evennia.comms.models import ChannelDB
    from .constants import (
        SPLATTERCAST_CHANNEL, NDB_PROXIMITY, DB_CHAR,
        DB_GRAPPLING_DBREF, DB_GRAPPLED_BY_DBREF, DB_IS_YIELDING
    )
    from .utils import get_numeric_stat
    from random import randint
    
    splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
    char = char_entry.get(DB_CHAR)
    
    # Find existing grapple to contest
    target = handler.get_target_obj(char_entry)
    if not target:
        char.msg("You have no target to contest for grappling.")
        return
    
    # Check if target is already grappled
    target_entry = next((e for e in combatants_list if e.get(DB_CHAR) == target), None)
    if not target_entry or not target_entry.get(DB_GRAPPLED_BY_DBREF):
        char.msg(f"{target.key} is not currently being grappled.")
        return
    
    # Find the original grappler
    current_grappler = handler.get_grappled_by_obj(target_entry)
    if not current_grappler:
        char.msg("Unable to find the original grappler.")
        return
    
    # Get the current grappler's combat entry
    current_grappler_entry = next((e for e in combatants_list if e.get(DB_CHAR) == current_grappler), None)
    if not current_grappler_entry:
        char.msg(f"{current_grappler.key} is not properly registered in combat.")
        return
    
    # Check proximity
    if not hasattr(char.ndb, NDB_PROXIMITY):
        setattr(char.ndb, NDB_PROXIMITY, set())
    if target not in getattr(char.ndb, NDB_PROXIMITY):
        char.msg(f"You need to be in melee proximity with {target.key} to contest the grapple.")
        return
    
    # Contest: new grappler vs current grappler (both using motorics)
    new_grappler_roll = randint(1, max(1, get_numeric_stat(char, "motorics", 1)))
    current_grappler_roll = randint(1, max(1, get_numeric_stat(current_grappler, "motorics", 1)))
    
    splattercast.msg(f"GRAPPLE_CONTEST: {char.key} ({new_grappler_roll}) vs {current_grappler.key} ({current_grappler_roll}) for {target.key}")
    
    if new_grappler_roll > current_grappler_roll:
        # New grappler wins - they take over the grapple
        char_entry[DB_GRAPPLING_DBREF] = get_character_dbref(target)
        char_entry[DB_IS_YIELDING] = True
        
        # Clear the old grappler's hold
        current_grappler_entry[DB_GRAPPLING_DBREF] = None
        
        # Target is now grappled by the new grappler
        target_entry[DB_GRAPPLED_BY_DBREF] = get_character_dbref(char)
        
        # Success messages
        char.msg(f"|gYou successfully wrestle {target.key} away from {current_grappler.key}!|n")
        current_grappler.msg(f"|r{char.key} wrestles {target.key} away from your grasp!|n")
        target.msg(f"|y{char.key} takes over grappling you from {current_grappler.key}!|n")
        
        if char.location:
            char.location.msg_contents(
                f"|g{char.key} wrestles {target.key} away from {current_grappler.key}!|n",
                exclude=[char, target, current_grappler]
            )
        
        splattercast.msg(f"GRAPPLE_TAKEOVER: {char.key} took {target.key} from {current_grappler.key}.")
        
    else:
        # Current grappler maintains control
        char.msg(f"|yYou fail to wrestle {target.key} away from {current_grappler.key}!|n")
        current_grappler.msg(f"|gYou maintain your grip on {target.key} despite {char.key}'s attempt!|n")
        target.msg(f"|y{char.key} tries to take you from {current_grappler.key} but fails!|n")
        
        if char.location:
            char.location.msg_contents(
                f"|y{char.key} fails to wrestle {target.key} away from {current_grappler.key}!|n",
                exclude=[char, target, current_grappler]
            )
        
        splattercast.msg(f"GRAPPLE_CONTEST_FAIL: {char.key} failed to take {target.key} from {current_grappler.key}.")
        
        # Check if the failed grappler initiated combat - if so, they should become yielding
        initiated_combat = char_entry.get("initiated_combat_this_action", False)
        if initiated_combat:
            char_entry[DB_IS_YIELDING] = True
            char.msg("|gYour failed grapple attempt leaves you non-aggressive.|n")
            splattercast.msg(f"GRAPPLE_CONTEST_FAIL_YIELD: {char.key} initiated combat but failed contest, setting to yielding.")


def resolve_release_grapple(char_entry, combatants_list, handler):
    """
    Resolve a release grapple action.
    
    Args:
        char_entry: The character's combat entry
        combatants_list: List of all combatants
        handler: The combat handler instance
    """
    from evennia.comms.models import ChannelDB
    from .constants import (
        SPLATTERCAST_CHANNEL, DB_CHAR, DB_GRAPPLING_DBREF, DB_GRAPPLED_BY_DBREF
    )
    
    splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
    char = char_entry.get(DB_CHAR)
    
    # Find who they're grappling
    grappling_target = handler.get_grappling_obj(char_entry)
    if not grappling_target:
        char.msg("You are not grappling anyone.")
        return
    
    # Find the target's entry
    target_entry = next((e for e in combatants_list if e.get(DB_CHAR) == grappling_target), None)
    if not target_entry:
        char.msg(f"{grappling_target.key} is not in combat.")
        return
    
    # Clear the grapple
    char_entry[DB_GRAPPLING_DBREF] = None
    target_entry[DB_GRAPPLED_BY_DBREF] = None
    
    # Preserve existing yielding states - don't force any changes
    # The yielding state reflects the original intent when combat/grapple was initiated
    # If they want to become violent again, they need to explicitly take a hostile action
    
    # Check if target is still grappled by someone else for validation
    still_grappled = any(
        e.get(DB_GRAPPLING_DBREF) == get_character_dbref(grappling_target)
        for e in combatants_list
        if e.get(DB_CHAR) != char
    )
    
    char.msg(f"|gYou release your grapple on {grappling_target.key}.|n")
    grappling_target.msg(f"|g{char.key} releases their grapple on you.|n")
    
    if char.location:
        char.location.msg_contents(
            f"|g{char.key} releases their grapple on {grappling_target.key}.|n",
            exclude=[char, grappling_target]
        )
    
    splattercast.msg(f"GRAPPLE_RELEASE: {char.key} released {grappling_target.key}.")


def validate_and_cleanup_grapple_state(handler):
    """
    Validate and clean up stale grapple references in the combat handler.
    
    This function checks for and fixes:
    - Stale DBREFs to characters no longer in the database
    - Invalid cross-references (A grappling B but B not grappled by A)
    - Self-grappling references
    - References to characters no longer in combat
    - Orphaned grapple states
    
    Called periodically during combat to maintain data integrity.
    
    Args:
        handler: The combat handler instance
    """
    from evennia.comms.models import ChannelDB
    from .constants import (
        SPLATTERCAST_CHANNEL, DB_CHAR, DB_GRAPPLING_DBREF, DB_GRAPPLED_BY_DBREF
    )
    
    splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
    combatants_list = list(getattr(handler.db, "combatants", []))
    cleanup_needed = False
    
    splattercast.msg(f"GRAPPLE_VALIDATE: Starting grapple state validation for handler {handler.key}")
    
    # Get list of all valid character DBREFs in combat for reference checking
    valid_combat_dbrefs = set()
    valid_combat_chars = set()
    for entry in combatants_list:
        char = entry.get(DB_CHAR)
        if char:
            valid_combat_dbrefs.add(get_character_dbref(char))
            valid_combat_chars.add(char)
    
    for i, entry in enumerate(combatants_list):
        char = entry.get(DB_CHAR)
        if not char:
            continue
            
        grappling_dbref = entry.get(DB_GRAPPLING_DBREF)
        grappled_by_dbref = entry.get(DB_GRAPPLED_BY_DBREF)
        
        # Check grappling_dbref (who this character is grappling)
        if grappling_dbref is not None:
            # Try to resolve the grappling target
            grappling_target = get_character_by_dbref(grappling_dbref)
            
            if not grappling_target:
                # Stale DBREF - character no longer exists
                splattercast.msg(f"GRAPPLE_CLEANUP: {char.key} has stale grappling_dbref {grappling_dbref} (character doesn't exist). Clearing.")
                combatants_list[i] = dict(entry)
                combatants_list[i][DB_GRAPPLING_DBREF] = None
                cleanup_needed = True
            elif grappling_target == char:
                # Self-grappling
                splattercast.msg(f"GRAPPLE_CLEANUP: {char.key} is grappling themselves! Clearing self-grapple.")
                combatants_list[i] = dict(entry)
                combatants_list[i][DB_GRAPPLING_DBREF] = None
                cleanup_needed = True
            elif grappling_target not in valid_combat_chars:
                # Target not in combat
                splattercast.msg(f"GRAPPLE_CLEANUP: {char.key} is grappling {grappling_target.key} who is not in combat. Clearing.")
                combatants_list[i] = dict(entry)
                combatants_list[i][DB_GRAPPLING_DBREF] = None
                cleanup_needed = True
            else:
                # Valid target - check cross-reference
                target_entry = next((e for e in combatants_list if e.get(DB_CHAR) == grappling_target), None)
                if target_entry:
                    target_grappled_by_dbref = target_entry.get(DB_GRAPPLED_BY_DBREF)
                    expected_dbref = get_character_dbref(char)
                    
                    if target_grappled_by_dbref != expected_dbref:
                        # Broken cross-reference
                        splattercast.msg(f"GRAPPLE_CLEANUP: {char.key} claims to grapple {grappling_target.key}, but {grappling_target.key} doesn't have matching grappled_by reference. Fixing cross-reference.")
                        # Fix the target's grappled_by reference
                        target_index = next(j for j, e in enumerate(combatants_list) if e.get(DB_CHAR) == grappling_target)
                        combatants_list[target_index] = dict(combatants_list[target_index])
                        combatants_list[target_index][DB_GRAPPLED_BY_DBREF] = expected_dbref
                        cleanup_needed = True
        
        # Check grappled_by_dbref (who is grappling this character)
        if grappled_by_dbref is not None:
            # Try to resolve the grappler
            grappler = get_character_by_dbref(grappled_by_dbref)
            
            if not grappler:
                # Stale DBREF - grappler no longer exists
                splattercast.msg(f"GRAPPLE_CLEANUP: {char.key} has stale grappled_by_dbref {grappled_by_dbref} (character doesn't exist). Clearing.")
                combatants_list[i] = dict(entry)
                combatants_list[i][DB_GRAPPLED_BY_DBREF] = None
                cleanup_needed = True
            elif grappler == char:
                # Self-grappling
                splattercast.msg(f"GRAPPLE_CLEANUP: {char.key} is grappled by themselves! Clearing self-grapple.")
                combatants_list[i] = dict(entry)
                combatants_list[i][DB_GRAPPLED_BY_DBREF] = None
                cleanup_needed = True
            elif grappler not in valid_combat_chars:
                # Grappler not in combat
                splattercast.msg(f"GRAPPLE_CLEANUP: {char.key} is grappled by {grappler.key} who is not in combat. Clearing.")
                combatants_list[i] = dict(entry)
                combatants_list[i][DB_GRAPPLED_BY_DBREF] = None
                cleanup_needed = True
            else:
                # Valid grappler - check cross-reference
                grappler_entry = next((e for e in combatants_list if e.get(DB_CHAR) == grappler), None)
                if grappler_entry:
                    grappler_grappling_dbref = grappler_entry.get(DB_GRAPPLING_DBREF)
                    expected_dbref = get_character_dbref(char)
                    
                    if grappler_grappling_dbref != expected_dbref:
                        # Broken cross-reference
                        splattercast.msg(f"GRAPPLE_CLEANUP: {char.key} claims to be grappled by {grappler.key}, but {grappler.key} doesn't have matching grappling reference. Fixing cross-reference.")
                        # Fix the grappler's grappling reference
                        grappler_index = next(j for j, e in enumerate(combatants_list) if e.get(DB_CHAR) == grappler)
                        combatants_list[grappler_index] = dict(combatants_list[grappler_index])
                        combatants_list[grappler_index][DB_GRAPPLING_DBREF] = expected_dbref
                        cleanup_needed = True
    
    # Save changes if any cleanup was needed
    if cleanup_needed:
        setattr(handler.db, "combatants", combatants_list)
        splattercast.msg(f"GRAPPLE_CLEANUP: Grapple state cleanup completed for handler {handler.key}. Changes saved.")
    else:
        splattercast.msg(f"GRAPPLE_VALIDATE: All grapple states valid for handler {handler.key}.")


def get_character_dbref(char):
    """
    Get DBREF for a character object.
    
    Args:
        char: The character object
        
    Returns:
        int or None: The character's DBREF
    """
    return char.id if char else None
