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

from .constants import NDB_PROXIMITY, NDB_PROXIMITY_UNIVERSAL
from .debug import log_debug

# NOTE (#2487): there are no `hasattr(char.ndb, ...)` guards in this
# module, on purpose. `obj.ndb` is a `DbHolder` whose `__getattribute__`
# returns the handler's `get()` -- None for a missing key -- rather than
# raising, so `hasattr` is True for EVERY name and gates nothing. The
# real test is `isinstance(..., set)`, which is what each read does. Two
# call sites elsewhere trusted the hasattr with no isinstance behind it
# and raised `TypeError: argument of type 'NoneType' is not iterable`
# inside the combat round tick.


def initialize_proximity(character):
    """
    Initialize proximity NDB for a character if missing or invalid.
    
    Args:
        character: Character to initialize
        
    Returns:
        bool: True if initialization was needed
    """
    if not isinstance(getattr(character.ndb, NDB_PROXIMITY), set):
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
    

    DOES NOT CHECK GEOMETRY. Identity is the only guard here — callers
    are responsible for the two being in the same room. Every live
    caller is an advance / charge / grapple-drag path that has just
    established co-location, which is why the guard lives at the call
    sites rather than here; the one caller that did NOT was the
    post-reload sweep, and it now filters on location (#2748).

    If a future caller cannot guarantee co-location, put the test there
    rather than assuming this will catch it.
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
    if isinstance(getattr(char1.ndb, NDB_PROXIMITY), set):
        getattr(char1.ndb, NDB_PROXIMITY).discard(char2)
    
    if isinstance(getattr(char2.ndb, NDB_PROXIMITY), set):
        getattr(char2.ndb, NDB_PROXIMITY).discard(char1)
    
    log_debug("PROXIMITY", "BREAK", f"{char1.key} <-> {char2.key}")


def clear_all_proximity(character):
    """
    Clear all proximity relationships for a character.
    
    Args:
        character: Character to clear proximity for
    """
    proximity_set = getattr(character.ndb, NDB_PROXIMITY)
    if not isinstance(proximity_set, set):
        return
    
    # Remove this character from all others' proximity
    for other_char in list(proximity_set):
        if isinstance(getattr(other_char.ndb, NDB_PROXIMITY), set):
            getattr(other_char.ndb, NDB_PROXIMITY).discard(character)
    
    # Clear this character's proximity
    proximity_set.clear()
    log_debug("PROXIMITY", "CLEAR_ALL", f"Cleared for {character.key}")


def clear_proximity_on_room_change(character):
    """Drop every proximity link when a character changes room by a path
    that is not an exit traversal (#2490).

    `Exit.at_traverse` is the ONLY place this cleanup lived, and combat
    does not traverse exits — `advance`, a cross-room `charge` and a
    grapple drag all call `char.move_to(target_room)` directly.

    Those paths hand-roll the traversal side effects and got three of
    four: both `_do_advance_move` and `_resolve_charge_cross_room`
    re-implement aim clearing, the rigged-grenade check and auto-defuse,
    and neither clears proximity. An incomplete compensation list rather
    than an oversight — somebody enumerated what traversal does and
    missed an item.

    The residue is a cross-room proximity ghost: A and B fighting in the
    bar, A advances to the back room, and A keeps a live proximity link
    to B in a room A is no longer in.

    Clears both sets, on both sides, the way `at_traverse` does:
    `NDB_PROXIMITY` (melee) and `NDB_PROXIMITY_UNIVERSAL` (grenades and
    other room-anchored hazards).
    """
    clear_all_proximity(character)

    universal = getattr(character.ndb, NDB_PROXIMITY_UNIVERSAL, None)
    if not isinstance(universal, list) or not universal:
        return
    for obj in list(universal):
        other = getattr(getattr(obj, "ndb", None), NDB_PROXIMITY_UNIVERSAL, None)
        if isinstance(other, list) and character in other:
            other.remove(character)
    setattr(character.ndb, NDB_PROXIMITY_UNIVERSAL, [])
    log_debug("PROXIMITY", "CLEAR_ON_MOVE", f"Cleared for {character.key}")


def get_proximity_list(character):
    """
    Get list of characters in proximity with given character.
    
    Args:
        character: Character to check
        
    Returns:
        list: List of characters in proximity
    """
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
    
    # Remove invalid characters -- from BOTH sides.
    #
    # This discarded from `character`'s set only, leaving `character`
    # sitting in the partner's. That is not a repair, it is a new
    # asymmetry: one of them has forgotten the other and the other has
    # not, which is the exact desync this helper exists to clean up
    # (#2485). `break_proximity` is the module's working primitive and
    # already removes each from the other.
    for invalid_char in invalid_chars:
        if invalid_char is None:
            proximity_set.discard(invalid_char)
            continue
        break_proximity(character, invalid_char)
        log_debug("PROXIMITY", "CLEANUP", f"Removed invalid {invalid_char} from {character.key}")


def sync_proximity_bidirectional(character):
    """
    Ensure proximity relationships are bidirectional and consistent.
    
    Args:
        character: Character to sync proximity for
    """
    proximity_set = getattr(character.ndb, NDB_PROXIMITY)
    if not isinstance(proximity_set, set):
        return
    
    for other_char in list(proximity_set):
        if is_in_proximity(other_char, character):
            continue                      # already symmetric
        # A ONE-SIDED entry is ambiguous: it can mean the partner
        # dropped us, or that our own side is stale. This used to
        # resolve it by ADDING -- treating `character`'s set as
        # authoritative and forcing the partner to match -- so a stale
        # cross-room entry was PROPAGATED rather than repaired, and the
        # sibling helper above repairs the very same desync by
        # REMOVING. Two repairs pulling in opposite directions (#2485).
        #
        # Validity decides which way. A pair that should not be in
        # proximity at all is broken on both sides; only a genuinely
        # valid pair is completed.
        valid = (
            getattr(other_char, "location", None) is not None
            and getattr(character, "location", None) is not None
            and other_char.location == character.location
        )
        if not valid:
            break_proximity(character, other_char)
            log_debug("PROXIMITY", "SYNC",
                      f"Broke stale {character.key} <-> {other_char.key}")
            continue
        initialize_proximity(other_char)
        getattr(other_char.ndb, NDB_PROXIMITY).add(character)
        log_debug("PROXIMITY", "SYNC", f"Added {character.key} to {other_char.key}'s proximity")
