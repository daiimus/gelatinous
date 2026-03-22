"""
Movement Resolution Module

Standalone functions for resolving movement-related combat actions
(retreat, advance, charge) within the combat handler.

Extracted from CombatHandler to reduce handler.py size and improve
modularity.

All functions take ``handler`` as their first parameter (the CombatHandler
script instance) instead of operating as methods on the class.
"""

from random import randint

from evennia.comms.models import ChannelDB

from .constants import (
    SPLATTERCAST_CHANNEL,
    DEBUG_PREFIX_HANDLER,
    DB_CHAR, DB_COMBAT_ACTION, DB_COMBAT_ACTION_TARGET,
    DB_IS_YIELDING, DB_GRAPPLING_DBREF, DB_GRAPPLED_BY_DBREF,
    NDB_PROXIMITY_UNIVERSAL,
)
from .dice import roll_with_disadvantage, standard_roll
from .utils import (
    get_numeric_stat, initialize_proximity_ndb,
    is_wielding_ranged_weapon, clear_aim_state,
    get_character_by_dbref,
)
from .proximity import (
    establish_proximity, break_proximity, is_in_proximity,
)


def resolve_retreat(handler, char, entry):
    """
    Resolve a retreat action for a character in combat.

    The retreating character makes a motorics roll against the highest
    motorics among their nearby opponents (excluding any grappled victim).
    On success, proximity is broken with all opponents (but maintained
    with any grappled victim).

    Args:
        handler: The CombatHandler script instance.
        char: The character attempting to retreat.
        entry: The character's combat entry dict.
    """
    splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)

    splattercast.msg(
        f"{DEBUG_PREFIX_HANDLER}_RETREAT: {char.key} executing retreat "
        f"action."
    )

    # Check if in proximity with anyone (combat proximity)
    initialize_proximity_ndb(char)
    combat_proximity_list = getattr(
        char.ndb, "in_proximity_with", set()
    )

    # Also check grenade proximity
    grenade_proximity_list = getattr(
        char.ndb, NDB_PROXIMITY_UNIVERSAL, []
    )
    if not isinstance(grenade_proximity_list, list):
        grenade_proximity_list = []

    # Combine both proximity systems to get all nearby entities
    all_proximity = set(combat_proximity_list) | set(grenade_proximity_list)
    all_proximity.discard(char)  # Remove self

    if not all_proximity:
        char.msg(
            "|yYou are not in melee with anyone to retreat from.|n"
        )
        return

    # Check if currently grappling someone
    grappled_victim = None
    grappled_victim_dbref = entry.get(DB_GRAPPLING_DBREF)
    if grappled_victim_dbref:
        grappled_victim = get_character_by_dbref(grappled_victim_dbref)

    # Get valid opponents (exclude grappled victim from motorics contest)
    opponents = []
    for entity in all_proximity:
        if (
            entity != char
            and entity.location == char.location
            and entity != grappled_victim
        ):
            opponents.append(entity)

    # Special case: If only in proximity with grappled victim, retreat fails
    if (
        grappled_victim
        and len(all_proximity) == 1
        and grappled_victim in all_proximity
    ):
        char.msg(
            "|rYou cannot retreat while grappling your only opponent! "
            "You are physically latched together.|n"
        )
        splattercast.msg(
            f"{DEBUG_PREFIX_HANDLER}_RETREAT: {char.key} cannot retreat "
            f"— only in proximity with grappled victim "
            f"{grappled_victim.key}."
        )
        return

    # If no valid opponents for contest (safety check)
    if not opponents:
        char.msg(
            "|yYou are not in melee with anyone to retreat from.|n"
        )
        return

    # Find the highest opponent stat for retreat difficulty
    highest_opponent_stat = 0
    for opponent in opponents:
        opponent_stat = get_numeric_stat(opponent, "motorics")
        if opponent_stat > highest_opponent_stat:
            highest_opponent_stat = opponent_stat

    # Make opposed roll
    char_motorics = get_numeric_stat(char, "motorics")
    char_roll = randint(1, max(1, char_motorics))
    opponent_roll = randint(1, max(1, highest_opponent_stat))

    splattercast.msg(
        f"{DEBUG_PREFIX_HANDLER}_RETREAT: {char.key} "
        f"(motorics:{char_motorics}, roll:{char_roll}) vs highest "
        f"opponent (motorics:{highest_opponent_stat}, "
        f"roll:{opponent_roll})"
    )

    if char_roll > opponent_roll:
        # Success — break proximity with opponents but maintain with
        # grappled victim
        # NOTE: Strict > means ties favor the opponent (defender).
        # This is intentional.
        for opponent in opponents:
            if is_in_proximity(char, opponent):
                break_proximity(char, opponent)

        # Always ensure proximity is maintained with grappled victim
        if grappled_victim:
            if not is_in_proximity(char, grappled_victim):
                establish_proximity(char, grappled_victim)
            splattercast.msg(
                f"{DEBUG_PREFIX_HANDLER}_RETREAT: Maintained proximity "
                f"with grappled victim {grappled_victim.key} during "
                f"retreat."
            )

        char.msg(
            "|gYou successfully retreat from melee combat.|n"
        )
        char.location.msg_contents(
            f"|y{char.key} retreats from melee combat.|n",
            exclude=[char],
        )
        splattercast.msg(
            f"{DEBUG_PREFIX_HANDLER}_RETREAT: {char.key} successfully "
            f"retreated from melee."
        )
    else:
        # Failure — remain in proximity
        char.msg(
            "|rYour retreat fails! You remain locked in melee.|n"
        )
        char.location.msg_contents(
            f"|y{char.key} tries to retreat but remains engaged.|n",
            exclude=[char],
        )
        splattercast.msg(
            f"{DEBUG_PREFIX_HANDLER}_RETREAT: {char.key} failed to "
            f"retreat from melee."
        )


def resolve_advance(handler, char, entry):
    """
    Resolve an advance action for a character in combat.

    Same-room advance establishes melee proximity. Cross-room advance
    moves the character to the target's room (with optional grapple
    dragging).

    Args:
        handler: The CombatHandler script instance.
        char: The character attempting to advance.
        entry: The character's combat entry dict.
    """
    splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
    target = entry.get(DB_COMBAT_ACTION_TARGET)

    if not target:
        char.msg("|rNo target specified for advance action.|n")
        return

    # Check if target is still in combat
    combatants_list = handler.db.combatants or []
    if not any(e.get(DB_CHAR) == target for e in combatants_list):
        char.msg(f"|r{target.key} is no longer in combat.|n")
        return

    splattercast.msg(
        f"{DEBUG_PREFIX_HANDLER}_ADVANCE: {char.key} executing advance "
        f"action on {target.key}."
    )

    # Check if target is in the same room
    if target.location == char.location:
        _resolve_advance_same_room(handler, char, target, splattercast)
    else:
        _resolve_advance_cross_room(
            handler, char, target, entry, combatants_list, splattercast,
        )


def _resolve_advance_same_room(handler, char, target, splattercast):
    """
    Handle same-room advance: establish melee proximity via opposed roll.

    Args:
        handler: The CombatHandler script instance.
        char: The advancing character.
        target: The target character.
        splattercast: The Splattercast channel object.
    """
    initialize_proximity_ndb(char)
    initialize_proximity_ndb(target)

    if is_in_proximity(char, target):
        char.msg(
            f"|yYou are already in melee proximity with {target.key}.|n"
        )
        return

    # Make opposed roll for proximity
    char_motorics = get_numeric_stat(char, "motorics")
    target_motorics = get_numeric_stat(target, "motorics")
    char_roll = randint(1, max(1, char_motorics))
    target_roll = randint(1, max(1, target_motorics))

    splattercast.msg(
        f"{DEBUG_PREFIX_HANDLER}_ADVANCE: {char.key} "
        f"(motorics:{char_motorics}, roll:{char_roll}) vs {target.key} "
        f"(motorics:{target_motorics}, roll:{target_roll})"
    )

    if char_roll > target_roll:
        # Success — establish proximity
        # NOTE: Strict > means ties favor the target (defender).
        # This is intentional.
        establish_proximity(char, target)

        char.msg(
            f"|gYou successfully advance to melee range with "
            f"{target.key}.|n"
        )
        target.msg(
            f"|y{char.key} advances to melee range with you.|n"
        )
        char.location.msg_contents(
            f"|y{char.key} advances to melee range with "
            f"{target.key}.|n",
            exclude=[char, target],
        )
        splattercast.msg(
            f"{DEBUG_PREFIX_HANDLER}_ADVANCE: {char.key} successfully "
            f"advanced to melee with {target.key}."
        )
    else:
        # Failure — no proximity established
        char.msg(
            f"|rYour advance on {target.key} fails! They keep their "
            f"distance.|n"
        )
        target.msg(
            f"|g{char.key} tries to advance on you but you keep your "
            f"distance.|n"
        )
        char.location.msg_contents(
            f"|y{char.key} tries to advance on {target.key} but fails "
            f"to close the distance.|n",
            exclude=[char, target],
        )
        splattercast.msg(
            f"{DEBUG_PREFIX_HANDLER}_ADVANCE: {char.key} failed to "
            f"advance on {target.key}."
        )


def _resolve_advance_cross_room(
    handler, char, target, entry, combatants_list, splattercast
):
    """
    Handle cross-room advance: move character to target's room (with
    optional grapple dragging).

    Args:
        handler: The CombatHandler script instance.
        char: The advancing character.
        target: The target character in another room.
        entry: The character's combat entry dict.
        combatants_list: List of all combat entry dicts.
        splattercast: The Splattercast channel object.
    """
    managed_rooms = handler.db.managed_rooms or []
    target_room = target.location

    if target_room not in managed_rooms:
        char.msg(
            f"|r{target.key} is no longer in a combat area you can "
            f"reach.|n"
        )
        return

    # Check if advancing character is grappling someone and should drag them
    grappled_victim = handler.get_grappling_obj(entry)
    should_drag_victim = False

    if grappled_victim:
        # Check drag conditions: yielding and not targeted by others
        is_yielding = entry.get(DB_IS_YIELDING, False)

        is_targeted_by_others_not_victim = False
        for e in combatants_list:
            other_char = e.get(DB_CHAR)
            if not other_char:
                continue
            if (
                other_char != char
                and other_char != grappled_victim
                and other_char != target
                and other_char.location == char.location
            ):
                if handler.get_target_obj(e) == char:
                    is_targeted_by_others_not_victim = True
                    break

        if is_yielding and not is_targeted_by_others_not_victim:
            should_drag_victim = True
            splattercast.msg(
                f"{DEBUG_PREFIX_HANDLER}_ADVANCE_DRAG: {char.key} meets "
                f"drag conditions — will attempt to drag "
                f"{grappled_victim.key}."
            )
        else:
            char.msg(
                f"|rYou cannot advance to another room while actively "
                f"grappling {grappled_victim.key} — others are targeting "
                f"you or you're being aggressive.|n"
            )
            splattercast.msg(
                f"{DEBUG_PREFIX_HANDLER}_ADVANCE_DRAG_BLOCKED: "
                f"{char.key} cannot drag {grappled_victim.key} — "
                f"yielding:{is_yielding}, "
                f"targeted_by_others:"
                f"{is_targeted_by_others_not_victim}"
            )
            return

    # Find exit from current room to target room
    exit_to_target = None
    for exit_obj in char.location.exits:
        if exit_obj.destination == target_room:
            exit_to_target = exit_obj
            break

    if not exit_to_target:
        char.msg(
            f"|rYou cannot find a way to {target.key}'s location.|n"
        )
        return

    # Make opposed roll for movement
    char_motorics = get_numeric_stat(char, "motorics")
    target_motorics = get_numeric_stat(target, "motorics")
    char_roll = randint(1, max(1, char_motorics))
    target_roll = randint(1, max(1, target_motorics))

    splattercast.msg(
        f"{DEBUG_PREFIX_HANDLER}_ADVANCE_MOVE: {char.key} "
        f"(motorics:{char_motorics}, roll:{char_roll}) vs {target.key} "
        f"(motorics:{target_motorics}, roll:{target_roll})"
    )

    if char_roll > target_roll:
        # Success — move to target's room
        # NOTE: Strict > means ties favor the target (defender).
        # This is intentional.
        _do_advance_move(
            handler, char, target, target_room, exit_to_target,
            grappled_victim, should_drag_victim, splattercast,
        )
    else:
        # Failure — no movement
        char.msg(
            f"|rYour advance toward {target.key} fails! You cannot "
            f"reach their position.|n"
        )
        target.msg(
            f"|g{char.key} tries to advance toward your position but "
            f"fails to reach you.|n"
        )
        char.location.msg_contents(
            f"|y{char.key} attempts to advance toward {target.key} but "
            f"fails to reach them.|n",
            exclude=[char],
        )
        splattercast.msg(
            f"{DEBUG_PREFIX_HANDLER}_ADVANCE_MOVE: {char.key} failed to "
            f"move to {target.key}."
        )

        # Check if target has ranged weapon for bonus attack
        if is_wielding_ranged_weapon(target):
            target.msg(
                f"|gYour ranged weapon gives you a clear shot as "
                f"{char.key} fails to reach you!|n"
            )
            char.msg(
                f"|r{target.key} takes advantage of your failed advance "
                f"to attack from range!|n"
            )
            splattercast.msg(
                f"{DEBUG_PREFIX_HANDLER}_ADVANCE_MOVE_BONUS: "
                f"{target.key} gets bonus attack vs {char.key} for "
                f"failed cross-room advance."
            )
            handler.resolve_bonus_attack(target, char)


def _do_advance_move(
    handler, char, target, target_room, exit_to_target,
    grappled_victim, should_drag_victim, splattercast,
):
    """
    Execute the actual cross-room advance movement after a successful roll.

    Args:
        handler: The CombatHandler script instance.
        char: The advancing character.
        target: The target character.
        target_room: The room the character is moving to.
        exit_to_target: The exit object used for traversal.
        grappled_victim: The character being grappled (or ``None``).
        should_drag_victim: Whether to drag the grappled victim along.
        splattercast: The Splattercast channel object.
    """
    old_location = char.location

    # Clear aim states before moving (consistent with traversal)
    if hasattr(char, "clear_aim_state"):
        char.clear_aim_state(reason_for_clearing="as you advance")
    else:
        clear_aim_state(char)

    # Handle grapple victim dragging if needed
    if should_drag_victim and grappled_victim:
        # Announce dragging
        char.msg(
            f"|gYou drag {grappled_victim.key} with you as you advance "
            f"to {target_room.key}.|n"
        )
        grappled_victim.msg(
            f"|r{char.key} drags you along as they advance to "
            f"{target_room.key}!|n"
        )
        old_location.msg_contents(
            f"|y{char.key} drags {grappled_victim.key} along as they "
            f"advance toward {target_room.key}.|n",
            exclude=[char, grappled_victim],
        )
        splattercast.msg(
            f"{DEBUG_PREFIX_HANDLER}_ADVANCE_DRAG: {char.key} is "
            f"dragging {grappled_victim.key} from {old_location.key} to "
            f"{target_room.key}."
        )

        # Move both characters
        char.move_to(target_room)
        grappled_victim.move_to(
            target_room, quiet=True, move_hooks=False
        )

        # Re-establish proximity between grappler and victim after drag
        establish_proximity(char, grappled_victim)
        splattercast.msg(
            f"{DEBUG_PREFIX_HANDLER}_ADVANCE_DRAG: Re-established "
            f"proximity between {char.key} and dragged victim "
            f"{grappled_victim.key} in {target_room.key}."
        )

        # Announce arrival in new location
        target_room.msg_contents(
            f"|y{char.key} arrives dragging {grappled_victim.key}.|n",
            exclude=[char, grappled_victim],
        )
    else:
        # Normal single character movement
        char.move_to(target_room)

    # Check for rigged grenades after successful movement
    from commands.CmdThrow import check_rigged_grenade, check_auto_defuse

    check_rigged_grenade(char, exit_to_target)

    # Check for auto-defuse opportunities after advancing to new room
    check_auto_defuse(char)

    if should_drag_victim and grappled_victim:
        char.msg(
            f"|gYou successfully advance to {target_room.key} with "
            f"{grappled_victim.key} in tow to engage {target.key}.|n"
        )
        target.msg(
            f"|y{char.key} advances into the room dragging "
            f"{grappled_victim.key} to engage you!|n"
        )
        splattercast.msg(
            f"{DEBUG_PREFIX_HANDLER}_ADVANCE_MOVE: {char.key} "
            f"successfully moved to {target_room.key} with "
            f"{grappled_victim.key} to engage {target.key}."
        )
    else:
        char.msg(
            f"|gYou successfully advance to {target_room.key} to engage "
            f"{target.key}.|n"
        )
        target.msg(
            f"|y{char.key} advances into the room to engage you!|n"
        )
        old_location.msg_contents(
            f"|y{char.key} advances toward {target_room.key} to engage "
            f"{target.key}.|n",
            exclude=[char],
        )
        target_room.msg_contents(
            f"|y{char.key} advances into the room to engage "
            f"{target.key}!|n",
            exclude=[char, target],
        )
        splattercast.msg(
            f"{DEBUG_PREFIX_HANDLER}_ADVANCE_MOVE: {char.key} "
            f"successfully moved to {target_room.key} to engage "
            f"{target.key}."
        )


def resolve_charge(handler, char, entry, combatants_list):
    """
    Resolve a charge action for a character in combat.

    Charge uses disadvantage on the motorics roll. On success it
    establishes proximity and grants a +2 attack bonus. On failure the
    charger may suffer a bonus attack from ranged defenders. Also handles
    grapple release when charging and cross-room movement.

    Args:
        handler: The CombatHandler script instance.
        char: The character attempting to charge.
        entry: The character's combat entry dict.
        combatants_list: List of all combat entry dicts.
    """
    splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
    target = entry.get(DB_COMBAT_ACTION_TARGET)

    if not target:
        char.msg("|rNo target specified for charge action.|n")
        return

    # Validate target is still in combat
    if not any(e[DB_CHAR] == target for e in combatants_list):
        char.msg(f"|r{target.key} is no longer in combat.|n")
        return

    splattercast.msg(
        f"{DEBUG_PREFIX_HANDLER}_CHARGE: {char.key} executing charge "
        f"action on {target.key}."
    )

    # Initialize proximity for both characters
    initialize_proximity_ndb(char)
    initialize_proximity_ndb(target)

    # Check if already in proximity
    if is_in_proximity(char, target):
        char.msg(
            f"|yYou are already in melee proximity with {target.key}.|n"
        )
        # Clear the charge action since it's not needed
        charge_combatants = list(handler.db.combatants)
        for combat_entry in charge_combatants:
            if combat_entry[DB_CHAR] == char:
                combat_entry[DB_COMBAT_ACTION] = None
                combat_entry[DB_COMBAT_ACTION_TARGET] = None
                break
        handler.db.combatants = charge_combatants

        # Instead of waiting for normal attack phase, make an immediate
        # bonus attack
        splattercast.msg(
            f"{DEBUG_PREFIX_HANDLER}_CHARGE: {char.key} already in "
            f"proximity with {target.key}, making immediate bonus "
            f"attack."
        )
        handler.resolve_bonus_attack(char, target)
        return

    # Handle same room vs different room charge
    if target.location == char.location:
        _resolve_charge_same_room(
            handler, char, target, entry, combatants_list, splattercast,
        )
    else:
        _resolve_charge_cross_room(
            handler, char, target, entry, combatants_list, splattercast,
        )


def _release_grapple_for_charge(
    handler, char, entry, combatants_list, splattercast, cross_room=False
):
    """
    Release grapple hold when a character charges, if applicable.

    Args:
        handler: The CombatHandler script instance.
        char: The charging character.
        entry: The character's combat entry dict.
        combatants_list: List of all combat entry dicts.
        splattercast: The Splattercast channel object.
        cross_room: Whether this is a cross-room charge.
    """
    if not entry.get(DB_GRAPPLING_DBREF):
        return

    grappled_victim = handler.get_grappling_obj(entry)
    if not grappled_victim:
        return

    # Release the grapple — update the actual combatants list
    for combatant_entry in combatants_list:
        if combatant_entry.get(DB_CHAR) == char:
            combatant_entry[DB_GRAPPLING_DBREF] = None
        elif combatant_entry.get(DB_CHAR) == grappled_victim:
            combatant_entry[DB_GRAPPLED_BY_DBREF] = None

    target = entry.get(DB_COMBAT_ACTION_TARGET)

    if cross_room:
        # Cross-room: victim might be in different room now
        char.msg(
            f"|yYou release your grapple on "
            f"{grappled_victim.get_display_name(char)} as you charge "
            f"away!|n"
        )
        if grappled_victim.access(char, "view"):
            grappled_victim.msg(
                f"|y{char.get_display_name(grappled_victim)} releases "
                f"their grapple on you and charges away!|n"
            )
    else:
        char.msg(
            f"|yYou release your grapple on "
            f"{grappled_victim.get_display_name(char)} as you charge "
            f"{target.key}!|n"
        )
        if grappled_victim.access(char, "view"):
            grappled_victim.msg(
                f"|y{char.get_display_name(grappled_victim)} releases "
                f"their grapple on you to charge "
                f"{target.get_display_name(grappled_victim)}!|n"
            )

    label = "cross-room " if cross_room else ""
    splattercast.msg(
        f"{DEBUG_PREFIX_HANDLER}_CHARGE_GRAPPLE_RELEASE: {char.key} "
        f"released grapple on {grappled_victim.key} due to successful "
        f"{label}charge."
    )


def _resolve_charge_same_room(
    handler, char, target, entry, combatants_list, splattercast
):
    """
    Handle same-room charge with disadvantage.

    Args:
        handler: The CombatHandler script instance.
        char: The charging character.
        target: The target character.
        entry: The character's combat entry dict.
        combatants_list: List of all combat entry dicts.
        splattercast: The Splattercast channel object.
    """
    char_motorics = get_numeric_stat(char, "motorics")
    target_motorics = get_numeric_stat(target, "motorics")

    charge_roll, roll1, roll2 = roll_with_disadvantage(char_motorics)
    resist_roll, r_roll1, r_roll2 = standard_roll(target_motorics)

    splattercast.msg(
        f"{DEBUG_PREFIX_HANDLER}_CHARGE_SAME_ROOM: {char.key} "
        f"(motorics:{char_motorics}, "
        f"disadvantage:{roll1},{roll2}>>{charge_roll}) vs {target.key} "
        f"(motorics:{target_motorics}, roll:{resist_roll})"
    )

    if charge_roll > resist_roll:
        # Success — establish proximity and charge bonus
        # NOTE: Strict > means ties favor the target (defender).
        # This is intentional.

        # Release grapple if holding someone
        _release_grapple_for_charge(
            handler, char, entry, combatants_list, splattercast,
        )

        establish_proximity(char, target)

        # Clear aim states
        clear_aim_state(char)

        # Update target on successful charge
        handler.set_target(char, target)

        # Set charge bonus
        char.ndb.charge_attack_bonus_active = True
        splattercast.msg(
            f"{DEBUG_PREFIX_HANDLER}_CHARGE: {char.key} "
            f"charge_attack_bonus_active set to True by successful "
            f"charge."
        )

        char.msg(
            f"|gYou charge {target.key} and slam into melee range! "
            f"Your next attack will have a bonus.|n"
        )
        target.msg(
            f"|r{char.key} charges at you and crashes into melee "
            f"range!|n"
        )
        char.location.msg_contents(
            f"|y{char.key} charges at {target.key} with reckless "
            f"abandon!|n",
            exclude=[char, target],
        )
        splattercast.msg(
            f"{DEBUG_PREFIX_HANDLER}_CHARGE: {char.key} successfully "
            f"charged {target.key}."
        )
    else:
        # Failure — charge penalty
        char.msg(
            f"|rYour reckless charge at {target.key} fails "
            f"spectacularly!|n"
        )
        target.msg(
            f"|y{char.key} charges at you but you dodge, leaving them "
            f"off-balance!|n"
        )
        char.location.msg_contents(
            f"|y{char.key} charges recklessly at {target.key} but "
            f"misses and stumbles!|n",
            exclude=[char, target],
        )

        # Check if target has ranged weapon for bonus attack
        if is_wielding_ranged_weapon(target):
            handler.resolve_bonus_attack(target, char)
            splattercast.msg(
                f"{DEBUG_PREFIX_HANDLER}_CHARGE: {char.key} failed "
                f"charge against ranged weapon user {target.key}, bonus "
                f"attack triggered."
            )

        # Apply charge failure penalty
        # TODO: charge_penalty is set but never read — implement penalty
        # mechanic (e.g., reduced dodge or accuracy next round) or remove
        char.ndb.charge_penalty = True
        char.msg("|rYour failed charge leaves you off-balance!|n")
        splattercast.msg(
            f"{DEBUG_PREFIX_HANDLER}_CHARGE: {char.key} failed charge on "
            f"{target.key}, penalty applied."
        )


def _resolve_charge_cross_room(
    handler, char, target, entry, combatants_list, splattercast
):
    """
    Handle cross-room charge: move to target's room with disadvantage.

    Args:
        handler: The CombatHandler script instance.
        char: The charging character.
        target: The target character in another room.
        entry: The character's combat entry dict.
        combatants_list: List of all combat entry dicts.
        splattercast: The Splattercast channel object.
    """
    managed_rooms = handler.db.managed_rooms or []
    if target.location not in managed_rooms:
        char.msg(
            f"|r{target.key} is not in a room you can charge to.|n"
        )
        return

    # Check for valid path
    target_room = target.location
    exits_to_target = [
        ex for ex in char.location.exits if ex.destination == target_room
    ]

    if not exits_to_target:
        char.msg(
            f"|rThere is no clear path to charge at {target.key}.|n"
        )
        return

    # Check if target has ranged weapon
    target_has_ranged = is_wielding_ranged_weapon(target)

    # Charge uses disadvantage for cross-room
    char_motorics = get_numeric_stat(char, "motorics")
    target_motorics = get_numeric_stat(target, "motorics")

    charge_roll, roll1, roll2 = roll_with_disadvantage(char_motorics)
    resist_roll, r_roll1, r_roll2 = standard_roll(target_motorics)

    splattercast.msg(
        f"{DEBUG_PREFIX_HANDLER}_CHARGE_CROSS_ROOM: {char.key} "
        f"(motorics:{char_motorics}, "
        f"disadvantage:{roll1},{roll2}>>{charge_roll}) vs {target.key} "
        f"(motorics:{target_motorics}, roll:{resist_roll})"
    )

    if charge_roll > resist_roll:
        # Success — move and establish proximity
        # NOTE: Strict > means ties favor the target (defender).
        # This is intentional.
        exit_to_use = exits_to_target[0]
        char.move_to(target_room)

        # Release grapple if holding someone
        _release_grapple_for_charge(
            handler, char, entry, combatants_list, splattercast,
            cross_room=True,
        )

        # Check for rigged grenades after successful movement
        from commands.CmdThrow import (
            check_rigged_grenade, check_auto_defuse,
        )

        check_rigged_grenade(char, exit_to_use)

        # Check for auto-defuse opportunities after charging to new room
        check_auto_defuse(char)

        clear_aim_state(char)
        establish_proximity(char, target)

        # Update target on successful charge
        handler.set_target(char, target)

        # Set charge bonus
        char.ndb.charge_attack_bonus_active = True
        splattercast.msg(
            f"{DEBUG_PREFIX_HANDLER}_CHARGE: {char.key} "
            f"charge_attack_bonus_active set to True by successful "
            f"cross-room charge."
        )

        char.msg(
            f"|gYou charge recklessly through the {exit_to_use.key} and "
            f"crash into melee with {target.key}! Your next attack will "
            f"have a bonus.|n"
        )
        target.msg(
            f"|r{char.key} charges recklessly through the "
            f"{exit_to_use.key} and crashes into melee with you!|n"
        )
        return_exit = exit_to_use.get_return_exit()
        from_label = (
            return_exit.key if return_exit else "elsewhere"
        )
        char.location.msg_contents(
            f"|y{char.key} charges recklessly from {from_label} and "
            f"crashes into melee!|n",
            exclude=[char, target],
        )
        splattercast.msg(
            f"{DEBUG_PREFIX_HANDLER}_CHARGE: {char.key} successfully "
            f"charged cross-room and engaged {target.key} in melee."
        )
    else:
        # Failure — charge penalty and potential ranged attack
        clear_aim_state(char)

        if target_has_ranged:
            char.msg(
                f"|r{target.key} stops your reckless charge with "
                f"covering fire!|n"
            )
            target.msg(
                f"|gYou stop {char.key}'s reckless charge with your "
                f"ranged weapon!|n"
            )

            # Trigger bonus attack
            handler.resolve_bonus_attack(target, char)
            splattercast.msg(
                f"{DEBUG_PREFIX_HANDLER}_CHARGE: {char.key} failed "
                f"cross-room charge against ranged weapon user "
                f"{target.key}, bonus attack triggered."
            )
        else:
            char.msg(
                f"|rYour reckless charge at {target.key} fails as you "
                f"stumble at the entrance!|n"
            )
            target.msg(
                f"|y{char.key} attempts to charge at you but stumbles "
                f"at the entrance!|n"
            )
            splattercast.msg(
                f"{DEBUG_PREFIX_HANDLER}_CHARGE: {char.key} failed "
                f"cross-room charge on {target.key}."
            )

        # Apply charge failure penalty
        # TODO: charge_penalty is set but never read — implement penalty
        # mechanic (e.g., reduced dodge or accuracy next round) or remove
        char.ndb.charge_penalty = True
        char.msg("|rYour failed charge leaves you off-balance!|n")
