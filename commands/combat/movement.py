"""
Movement Combat Commands Module

Contains commands related to movement and positioning in combat:
- CmdFlee: Attempt to flee from combat or aiming
- CmdRetreat: Disengage from melee proximity within the same room
- CmdAdvance: Close distance with a target
- CmdCharge: Recklessly charge at a target

CmdJump and apply_gravity_to_items have been extracted to
commands/combat/jump.py and are re-exported here for backward compatibility.
"""

from evennia import Command
from random import choice
from evennia.comms.models import ChannelDB

from world.combat.constants import (
    MSG_NOTHING_TO_FLEE, MSG_FLEE_NO_EXITS, MSG_FLEE_PINNED_BY_AIM, MSG_FLEE_TRAPPED_IN_COMBAT,
    MSG_FLEE_ALL_EXITS_COVERED, MSG_FLEE_BREAK_FREE_AIM, MSG_FLEE_FAILED_BREAK_AIM,
    MSG_RETREAT_NOT_IN_COMBAT, MSG_RETREAT_COMBAT_DATA_MISSING, MSG_RETREAT_PROXIMITY_UNCLEAR,
    MSG_RETREAT_NO_PROXIMITY, MSG_CANNOT_WHILE_GRAPPLED_RETREAT,
    MSG_ADVANCE_NOT_IN_COMBAT, MSG_ADVANCE_COMBAT_DATA_MISSING, MSG_ADVANCE_NO_TARGET, MSG_ADVANCE_SELF_TARGET,
    MSG_CHARGE_NOT_IN_COMBAT, MSG_CHARGE_COMBAT_DATA_MISSING, MSG_CHARGE_NO_TARGET, MSG_CHARGE_SELF_TARGET,
    DEBUG_PREFIX_FLEE, DEBUG_PREFIX_RETREAT, DEBUG_PREFIX_ADVANCE, DEBUG_PREFIX_CHARGE,
    DEBUG_FAIL, DEBUG_ERROR,
    NDB_COMBAT_HANDLER, NDB_AIMING_AT, NDB_AIMED_AT_BY, NDB_PROXIMITY, NDB_SKIP_ROUND,
    SPLATTERCAST_CHANNEL,
    COMBAT_ACTION_RETREAT, MSG_RETREAT_PREPARE,
    COMBAT_ACTION_ADVANCE, MSG_ADVANCE_PREPARE,
    COMBAT_ACTION_CHARGE, MSG_CHARGE_PREPARE,
)

# Re-export CmdJump and apply_gravity_to_items for backward compatibility.
# Canonical location: commands.combat.jump
from commands.combat.jump import CmdJump, apply_gravity_to_items  # noqa: F401
from world.combat.utils import (
    get_highest_opponent_stat, get_numeric_stat, filter_valid_opponents,
    standard_roll, clear_aim_state,
)


class CmdFlee(Command):
    """
    Attempt to flee from an aimer or combat.

    Usage:
      flee

    If someone is aiming at you, you will first attempt to break their aim.
    If successful, or if no one was aiming at you and you are in combat,
    you will attempt to escape the current combat and leave the room.
    You cannot flee into a room where an opponent is already targeting
    you with a ranged weapon.
    
    Flee occurs instantly but consumes your combat action. You can only
    attempt to flee once per combat round to prevent spam.
    
    If you fail any step, you remain in place and skip your next combat turn.
    Cannot be used if you are currently grappled in combat.
    If you disengage from local attackers but cannot find a safe exit, you remain in combat.
    """

    key = "flee"
    locks = "cmd:all()"
    help_category = "Combat"

    def func(self):
        caller = self.caller
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        
        # Check if player has already attempted to flee this combat round
        if hasattr(caller.ndb, "flee_attempted_this_round") and caller.ndb.flee_attempted_this_round:
            caller.msg("|rYou have already attempted to flee this combat round! Wait for the next round.|n")
            splattercast.msg(f"{DEBUG_PREFIX_FLEE}_COOLDOWN: {caller.key} attempted to flee but already tried this round.")
            return
        
        original_handler_at_flee_start = getattr(caller.ndb, NDB_COMBAT_HANDLER, None)
        # This is the specific character who has an NDB-level aim lock on the caller.
        # This aimer could be in the same room or an adjacent one.
        ndb_aimer_locking_caller = getattr(caller.ndb, NDB_AIMED_AT_BY, None) 

        splattercast.msg(f"{DEBUG_PREFIX_FLEE}_DEBUG ({caller.key}): Initial Handler='{original_handler_at_flee_start.key if original_handler_at_flee_start else None}', NDB Aimer='{ndb_aimer_locking_caller.key if ndb_aimer_locking_caller else None}'")

        # Set flee attempt flag to prevent spam within the same round
        caller.ndb.flee_attempted_this_round = True
        splattercast.msg(f"{DEBUG_PREFIX_FLEE}_ATTEMPT: {caller.key} marked as having attempted flee this round.")

        # --- PRE-FLEE SAFETY CHECK: PINNED BY RANGED TARGETERS IN ADJACENT ROOMS ---
        # Filter out sky rooms - can't flee into the air!
        all_exits = [ex for ex in caller.location.exits if ex.access(caller, 'traverse')]
        available_exits = [
            ex for ex in all_exits 
            if ex.destination and not ex.destination.db.is_sky_room
        ]
        
        # Debug log if sky rooms were filtered out
        sky_exits_filtered = len(all_exits) - len(available_exits)
        if sky_exits_filtered > 0:
            splattercast.msg(f"{DEBUG_PREFIX_FLEE}_SKY_FILTER: {caller.key} - filtered out {sky_exits_filtered} sky room exits from {len(all_exits)} total exits.")
        
        if not available_exits:
            # No exits at all.
            if ndb_aimer_locking_caller:
                caller.msg(MSG_FLEE_PINNED_BY_AIM.format(aimer=ndb_aimer_locking_caller.get_display_name(caller)))
            elif original_handler_at_flee_start:
                caller.msg(MSG_FLEE_TRAPPED_IN_COMBAT)
            else:
                # This case (no exits, not aimed at, not in combat) might be caught by the later "nothing to flee from"
                # but if it reaches here, it means flee was typed with no actual threat and no exits.
                caller.msg(MSG_FLEE_NO_EXITS)
            splattercast.msg(f"{DEBUG_PREFIX_FLEE}_ABORT_NO_EXITS: {caller.key} has no exits. NDB Aimer: {ndb_aimer_locking_caller.key if ndb_aimer_locking_caller else 'None'}, Handler: {original_handler_at_flee_start.key if original_handler_at_flee_start else 'None'}.")
            return
        else:
            # Exits exist, check if they ALL lead to ranged targeters.
            all_exits_lead_to_ranged_targeters = True 
            for potential_exit in available_exits:
                destination_room = potential_exit.destination
                is_this_exit_safe_from_ranged_targeters = True # Assume safe until proven otherwise
                if destination_room:
                    for char_in_dest in destination_room.contents:
                        if char_in_dest == caller or not hasattr(char_in_dest, "ndb"): continue
                        
                        # Check if char_in_dest is in combat, targeting caller, with a ranged weapon
                        other_h = getattr(char_in_dest.ndb, NDB_COMBAT_HANDLER, None)
                        if other_h and other_h.db.combat_is_running and other_h.db.combatants:
                            other_entry = next((e for e in other_h.db.combatants if e["char"] == char_in_dest), None)
                            if other_entry and other_h.get_target_obj(other_entry) == caller:
                                other_hands = getattr(char_in_dest, "hands", {})
                                other_weapon_obj = next((item for hand, item in other_hands.items() if item), None)
                                other_is_ranged = other_weapon_obj and other_weapon_obj.db.is_ranged
                                if other_is_ranged:
                                    is_this_exit_safe_from_ranged_targeters = False
                                    splattercast.msg(f"{DEBUG_PREFIX_FLEE}_PRE_CHECK_UNSAFE_EXIT: {caller.key} - exit {potential_exit.key} to {destination_room.key} is unsafe. Reason: {char_in_dest.key} is a ranged targeter in combat handler {other_h.key}.")
                                    break # This destination is unsafe due to this char_in_dest
                
                if is_this_exit_safe_from_ranged_targeters:
                    all_exits_lead_to_ranged_targeters = False # Found at least one safe exit
                    splattercast.msg(f"{DEBUG_PREFIX_FLEE}_PRE_CHECK_SAFE_EXIT_FOUND: {caller.key} found safe exit {potential_exit.key}.")
                    break # No need to check other exits if one safe one is found

            if all_exits_lead_to_ranged_targeters:
                caller.msg(MSG_FLEE_ALL_EXITS_COVERED)
                splattercast.msg(f"{DEBUG_PREFIX_FLEE}_ABORT_ALL_EXITS_TO_RANGED_TARGETERS: {caller.key}. Flee aborted.")
                return
        # --- END PRE-FLEE SAFETY CHECK ---

        # If the pre-flee safety check didn't abort, now check if there's anything to flee *from*.
        if not original_handler_at_flee_start and not ndb_aimer_locking_caller:
            caller.msg(MSG_NOTHING_TO_FLEE)
            splattercast.msg(f"{DEBUG_PREFIX_FLEE}_DEBUG ({caller.key}): 'Nothing to flee from' condition met (post-safety-check).")
            return

        # --- Part 1: Attempt to break an NDB-level aim lock ---
        # `current_aimer_for_break_attempt` is used locally for this part.
        # It starts as the NDB aimer and can be set to None if the aim is broken.
        current_aimer_for_break_attempt = ndb_aimer_locking_caller
        aim_successfully_broken = False

        if current_aimer_for_break_attempt:
            # Stale/Invalid Aim Check
            if not current_aimer_for_break_attempt.location or \
               current_aimer_for_break_attempt.location != caller.location or \
               getattr(current_aimer_for_break_attempt.ndb, NDB_AIMING_AT, None) != caller:
                caller.msg(f"The one aiming at you ({current_aimer_for_break_attempt.get_display_name(caller)}) seems to have stopped or departed; you are no longer locked by their aim.")
                if hasattr(caller.ndb, NDB_AIMED_AT_BY): del caller.ndb.aimed_at_by
                if hasattr(current_aimer_for_break_attempt.ndb, NDB_AIMING_AT) and current_aimer_for_break_attempt.ndb.aiming_at == caller:
                    del current_aimer_for_break_attempt.ndb.aiming_at
                splattercast.msg(f"{DEBUG_PREFIX_FLEE}_CMD (AIM_BREAK_PHASE): NDB Aim lock on {caller.key} by {current_aimer_for_break_attempt.key} was stale/invalid. Lock broken.")
                current_aimer_for_break_attempt = None 
                aim_successfully_broken = True 
            else:
                # Active Aim Lock - Attempt to Break
                splattercast.msg(f"{DEBUG_PREFIX_FLEE}_CMD (AIM_BREAK_PHASE): {caller.key} is attempting to break NDB aim lock by {current_aimer_for_break_attempt.key}.")
                aimer_motorics_to_resist = get_numeric_stat(current_aimer_for_break_attempt, "motorics")
                caller_motorics = get_numeric_stat(caller, "motorics")
                flee_roll, _, _ = standard_roll(caller_motorics)
                resist_roll, _, _ = standard_roll(aimer_motorics_to_resist)
                splattercast.msg(f"{DEBUG_PREFIX_FLEE}_AIM_ROLL: {caller.key}(motorics:{flee_roll}) vs {current_aimer_for_break_attempt.key}(motorics:{resist_roll})")

                if flee_roll > resist_roll:
                    caller.msg(MSG_FLEE_BREAK_FREE_AIM.format(aimer=current_aimer_for_break_attempt.get_display_name(caller)))
                    if current_aimer_for_break_attempt.access(caller, "view"): 
                        current_aimer_for_break_attempt.msg(f"|y{caller.get_display_name(current_aimer_for_break_attempt)} breaks free from your aim!|n")
                    
                    if hasattr(current_aimer_for_break_attempt, "clear_aim_state"):
                        current_aimer_for_break_attempt.clear_aim_state(reason_for_clearing=f"as {caller.key} breaks free")
                    else: # Fallback if clear_aim_state is missing on aimer
                        if hasattr(current_aimer_for_break_attempt.ndb, NDB_AIMING_AT): 
                            del current_aimer_for_break_attempt.ndb.aiming_at
                        # Clear override_place and handle mutual showdown cleanup
                        self._clear_aim_override_place_on_flee(current_aimer_for_break_attempt, caller)
                    
                    if hasattr(caller.ndb, NDB_AIMED_AT_BY): del caller.ndb.aimed_at_by # Clear on caller too
                    
                    splattercast.msg(f"{DEBUG_PREFIX_FLEE}_AIM_SUCCESS: {caller.key} broke free from {current_aimer_for_break_attempt.key}'s NDB aim.")
                    current_aimer_for_break_attempt = None # Successfully broke this aim
                    aim_successfully_broken = True
                else: # Failed to break NDB aim - AIMER ATTACKS!
                    caller_msg_flee_fail = MSG_FLEE_FAILED_BREAK_AIM.format(aimer=current_aimer_for_break_attempt.get_display_name(caller))
                    aimer_msg_flee_fail = ""
                    if current_aimer_for_break_attempt.access(caller, "view"):
                        aimer_msg_flee_fail = f"{caller.get_display_name(current_aimer_for_break_attempt)} tries to break your aim, but you maintain focus."
                    
                    splattercast.msg(f"{DEBUG_PREFIX_FLEE}_AIM_FAIL: {caller.key} failed to break {current_aimer_for_break_attempt.key}'s NDB aim. {current_aimer_for_break_attempt.key} initiates an attack.")
                    
                    # Aimer gets an immediate attack on the failed flee attempt
                    # Import and execute the attack command from the aimer's perspective
                    from commands.combat.core_actions import CmdAttack
                    
                    # Create a temporary attack command instance for the aimer
                    attack_cmd = CmdAttack()
                    attack_cmd.caller = current_aimer_for_break_attempt
                    attack_cmd.args = caller.key  # Target is the caller who failed to flee
                    attack_cmd.cmdstring = "attack"
                    
                    # Display messages about the aimer's opportunity attack
                    caller.msg(caller_msg_flee_fail)
                    if current_aimer_for_break_attempt.access(caller, "view"):
                        current_aimer_for_break_attempt.msg(aimer_msg_flee_fail)
                    
                    # Execute the attack
                    attack_cmd.func()
                    
                    return # Flee attempt ends here, aimer gets an attack.

        # --- Part 2: Combat Disengagement and Movement ---
        # If we reach here, any aim locks have been handled. Now attempt to flee from combat.
        splattercast.msg(f"{DEBUG_PREFIX_FLEE}_COMBAT_PHASE: {caller.key} attempting to disengage from combat.")
        
        # If we successfully broke an aim but have no combat handler, just move to safety
        if aim_successfully_broken and not original_handler_at_flee_start:
            chosen_exit = choice(available_exits)
            destination = chosen_exit.destination
            
            # Move to the chosen exit
            caller.move_to(destination, quiet=True)
            
            # Check for rigged grenades after successful movement
            from commands.explosion_utils import check_rigged_grenade, check_auto_defuse
            check_rigged_grenade(caller, chosen_exit)
            
            # Check for auto-defuse opportunities after fleeing to new room
            check_auto_defuse(caller)
            
            # Messages
            caller.msg(f"|gYou successfully flee {chosen_exit.key} to {destination.key}!|n")
            caller.location.msg_contents(f"|y{caller.get_display_name(caller.location)} has arrived, fleeing from an aimer.|n", exclude=[caller])
            
            # Message the room they left
            if hasattr(caller, 'previous_location') and caller.previous_location:
                caller.previous_location.msg_contents(f"|y{caller.get_display_name(caller.previous_location)} flees {chosen_exit.key}!|n")
            
            splattercast.msg(f"{DEBUG_PREFIX_FLEE}_SUCCESS: {caller.key} successfully fled after breaking aim via {chosen_exit.key} to {destination.key}.")
            return
        
        if original_handler_at_flee_start:
            # Character is in combat - attempt to disengage
            caller_entry = next((e for e in original_handler_at_flee_start.db.combatants if e["char"] == caller), None)
            if not caller_entry:
                # This shouldn't happen if ndb.combat_handler is properly managed
                caller.msg("Your combat state seems confused. Moving freely.")
                splattercast.msg(f"{DEBUG_PREFIX_FLEE}_ERROR: {caller.key} has combat handler but no entry.")
                destination = choice(available_exits).destination
                caller.move_to(destination)
                return
                
            # Check if grappled - can't flee while grappled
            grappled_by_char = original_handler_at_flee_start.get_grappled_by_obj(caller_entry)
            if grappled_by_char:
                caller.msg(f"|rYou cannot flee while {grappled_by_char.get_display_name(caller)} is grappling you! Try to escape the grapple first.|n")
                splattercast.msg(f"{DEBUG_PREFIX_FLEE}_BLOCKED: {caller.key} cannot flee while grappled by {grappled_by_char.key}.")
                return
                
            # Attempt to disengage from combat
            # Get all opponents targeting the caller
            opponents_targeting_caller = []
            combatants_list = original_handler_at_flee_start.db.combatants or []
            if combatants_list:
                for entry in combatants_list:
                    if entry["char"] != caller:
                        target_obj = original_handler_at_flee_start.get_target_obj(entry)
                        if target_obj == caller:
                            opponents_targeting_caller.append(entry["char"])
            
            # Opposed roll to disengage
            if opponents_targeting_caller:
                valid_opponents = filter_valid_opponents(opponents_targeting_caller)
                highest_opponent_motorics, blocking_opponent = get_highest_opponent_stat(valid_opponents, "motorics")
                caller_motorics = get_numeric_stat(caller, "motorics")
                
                flee_roll, _, _ = standard_roll(caller_motorics)
                block_roll, _, _ = standard_roll(highest_opponent_motorics)
                
                splattercast.msg(f"{DEBUG_PREFIX_FLEE}_DISENGAGE_ROLL: {caller.key} (motorics:{caller_motorics}, roll:{flee_roll}) vs opponents (highest:{highest_opponent_motorics}, blocker:{blocking_opponent.key if blocking_opponent else 'None'}, roll:{block_roll})")
                
                if flee_roll <= block_roll:
                    # Failed to disengage
                    caller.msg(f"|rYou try to flee but {blocking_opponent.get_display_name(caller) if blocking_opponent else 'your opponents'} block your escape!|n")
                    if blocking_opponent:
                        blocking_opponent.msg(f"|gYou successfully block {caller.get_display_name(blocking_opponent)}'s attempt to flee!|n")
                    caller.location.msg_contents(
                        f"|y{caller.get_display_name(caller.location)} tries to flee but is blocked by their opponents!|n",
                        exclude=[caller] + opponents_targeting_caller
                    )
                    splattercast.msg(f"{DEBUG_PREFIX_FLEE}_DISENGAGE_FAIL: {caller.key} failed to disengage from combat.")
                    
                    # Apply flee failure penalty (skip next turn)
                    setattr(caller.ndb, NDB_SKIP_ROUND, True)
                    caller.msg("|rYour failed escape attempt leaves you vulnerable!|n")
                    return
            
            # Successfully disengaged (or no opponents targeting) - choose exit and move
            safe_exits = []
            for exit_obj in available_exits:
                destination = exit_obj.destination
                if destination:
                    # Check if this exit leads away from ranged targeters (already done in pre-check, but double-check)
                    is_safe = True
                    for char_in_dest in destination.contents:
                        if char_in_dest == caller or not hasattr(char_in_dest, "ndb"):
                            continue
                        other_handler = getattr(char_in_dest.ndb, NDB_COMBAT_HANDLER, None)
                        if other_handler and other_handler.db.combat_is_running:
                            other_entry = next((e for e in (other_handler.db.combatants or []) if e["char"] == char_in_dest), None)
                            if other_entry and original_handler_at_flee_start.get_target_obj(other_entry) == caller:
                                other_hands = getattr(char_in_dest, "hands", {})
                                other_weapon = next((item for hand, item in other_hands.items() if item), None)
                                if other_weapon and other_weapon.db.is_ranged:
                                    is_safe = False
                                    break
                    if is_safe:
                        safe_exits.append(exit_obj)
            
            if not safe_exits:
                safe_exits = available_exits  # Fallback to any exit if none are "safe"
                
            chosen_exit = choice(safe_exits)
            destination = chosen_exit.destination
            
            # Remove from combat before moving (this also clears proximity)
            original_handler_at_flee_start.remove_combatant(caller)
            
            # Clear aim states before moving (consistent with traversal)
            if hasattr(caller, "clear_aim_state"):
                caller.clear_aim_state(reason_for_clearing="as you flee")
            else:
                clear_aim_state(caller)
            
            # Capture old location before moving for departure message
            old_location = caller.location
            
            # Move to the chosen exit
            caller.move_to(destination, quiet=True)
            
            # Check for rigged grenades after successful movement
            from commands.explosion_utils import check_rigged_grenade, check_auto_defuse
            check_rigged_grenade(caller, chosen_exit)
            
            # Check for auto-defuse opportunities after fleeing to new room
            check_auto_defuse(caller)
            
            # Messages
            caller.msg(f"|gYou successfully flee {chosen_exit.key} to {destination.key}!|n")
            caller.location.msg_contents(f"|y{caller.get_display_name(caller.location)} has arrived, fleeing from combat.|n", exclude=[caller])
            
            # Message the room they left
            if old_location and old_location != destination:
                old_location.msg_contents(f"|y{caller.get_display_name(old_location)} flees {chosen_exit.key}!|n")
            
            splattercast.msg(f"{DEBUG_PREFIX_FLEE}_SUCCESS: {caller.key} successfully fled via {chosen_exit.key} to {destination.key}.")
            
        else:
            # No combat handler and no aim was broken - this means nothing to flee from
            caller.msg("You have nothing to flee from.")
            splattercast.msg(f"{DEBUG_PREFIX_FLEE}_ERROR: {caller.key} reached flee movement phase with no combat handler and no aim broken.")

        # Ensure combat handler is updated if it still exists
        if original_handler_at_flee_start and hasattr(original_handler_at_flee_start, 'is_active'):
            if not original_handler_at_flee_start.is_active:
                original_handler_at_flee_start.start()

    def _clear_aim_override_place_on_flee(self, aimer, target):
        """
        Clear override_place for aiming when someone flees and breaks aim, handling mutual showdown cleanup.
        
        Args:
            aimer: The character who was aiming (their aim is being broken)
            target: The character who fled and broke the aim
        """
        # Check if they were in a mutual showdown
        if (hasattr(aimer, 'override_place') and hasattr(target, 'override_place') and
            aimer.override_place == "locked in a deadly showdown." and 
            target.override_place == "locked in a deadly showdown."):
            # They were in a showdown - clear aimer's place, check if target should revert to normal aiming
            aimer.override_place = ""
            
            # If target is still aiming at aimer, revert them to normal aiming
            target_still_aiming = getattr(target.ndb, NDB_AIMING_AT, None)
            if target_still_aiming == aimer:
                target.override_place = f"aiming carefully at {aimer.key}."
            else:
                # Target isn't aiming at anyone, clear their place too
                target.override_place = ""
        else:
            # Normal aiming cleanup
            if hasattr(aimer, 'override_place'):
                aimer.override_place = ""


class CmdRetreat(Command):
    """
    Attempt to disengage from melee proximity.

    Usage:
      retreat

    If you are in melee proximity with one or more opponents, you will
    attempt to break away, creating distance within the same room.
    Success depends on an opposed roll against those in proximity.
    Failure means you remain engaged.
    """
    key = "retreat"
    aliases = ["disengage"]
    locks = "cmd:all()"
    help_category = "Combat"

    def func(self):
        caller = self.caller
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        handler = getattr(caller.ndb, NDB_COMBAT_HANDLER, None)

        if not handler:
            caller.msg(MSG_RETREAT_NOT_IN_COMBAT)
            return

        caller_entry = next((e for e in handler.db.combatants if e["char"] == caller), None)
        if not caller_entry:
            caller.msg(MSG_RETREAT_COMBAT_DATA_MISSING)
            splattercast.msg(f"{DEBUG_PREFIX_RETREAT}_{DEBUG_ERROR}: {caller.key} has handler but no combat entry.")
            return

        # --- Check if caller is being grappled ---
        grappler_obj = handler.get_grappled_by_obj(caller_entry)
        if grappler_obj:
            caller.msg(MSG_CANNOT_WHILE_GRAPPLED_RETREAT.format(grappler=grappler_obj.get_display_name(caller) if grappler_obj else 'someone'))
            splattercast.msg(f"{DEBUG_PREFIX_RETREAT}_{DEBUG_FAIL}: {caller.key} attempted to retreat while grappled by {grappler_obj.key if grappler_obj else 'Unknown'}.")
            return

        if not hasattr(caller.ndb, NDB_PROXIMITY) or not isinstance(caller.ndb.in_proximity_with, set):
            caller.msg(MSG_RETREAT_PROXIMITY_UNCLEAR)
            splattercast.msg(f"{DEBUG_PREFIX_RETREAT}_{DEBUG_ERROR}: {caller.key} ndb.in_proximity_with missing or not a set.")
            # Initialize it as a failsafe, though it should be set by handler
            caller.ndb.in_proximity_with = set()
            return

        if not caller.ndb.in_proximity_with:
            caller.msg(MSG_RETREAT_NO_PROXIMITY)
            splattercast.msg(f"{DEBUG_PREFIX_RETREAT}_INFO: {caller.key} tried to retreat but not in proximity with anyone.")
            return

        # Set retreat action to be processed on caller's next turn
        caller_entry["combat_action"] = COMBAT_ACTION_RETREAT
        caller.msg(MSG_RETREAT_PREPARE)
        splattercast.msg(f"{DEBUG_PREFIX_RETREAT}: {caller.key} queued retreat action for next turn.")

        # Ensure the combat handler is running
        if handler and not handler.is_active:
            handler.start()


class CmdAdvance(Command):
    """
    Attempt to close distance and engage a target in melee.

    Usage:
      advance [target]

    If no target is specified, attempts to advance on your current
    combat target.
    If the target is in the same room but not in melee proximity,
    you will attempt to close the distance and enter melee.
    If the target is in an adjacent, managed combat room, you will
    attempt to move to that room. Engaging in melee proximity
    will require a subsequent action.
    Success depends on an opposed roll. Failure means you do not
    close the distance or fail to enter the room effectively.
    """
    key = "advance"
    aliases = ["engage", "close"]
    locks = "cmd:all()"
    help_category = "Combat"

    def func(self):
        caller = self.caller
        args = self.args.strip()
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        
        # Use robust handler validation to catch merge-related issues
        from world.combat.utils import validate_character_handler_reference
        is_valid, handler, error_msg = validate_character_handler_reference(caller)
        
        if not is_valid:
            splattercast.msg(f"{DEBUG_PREFIX_ADVANCE}_{DEBUG_ERROR}: {caller.key} handler validation failed: {error_msg}")
            caller.msg(MSG_ADVANCE_NOT_IN_COMBAT)
            return

        caller_entry = next((e for e in handler.db.combatants if e["char"] == caller), None)
        if not caller_entry:
            caller.msg(MSG_ADVANCE_COMBAT_DATA_MISSING)
            splattercast.msg(f"{DEBUG_PREFIX_ADVANCE}_{DEBUG_ERROR}: {caller.key} has handler but no combat entry.")
            return

        # Check if being grappled
        grappled_by_char_obj = handler.get_grappled_by_obj(caller_entry)
        if grappled_by_char_obj:
            caller.msg(f"You cannot advance while {grappled_by_char_obj.get_display_name(caller) if grappled_by_char_obj else 'someone'} is grappling you. Try 'escape' first.")
            splattercast.msg(f"{DEBUG_PREFIX_ADVANCE}_{DEBUG_FAIL}: {caller.key} attempted to advance while grappled by {grappled_by_char_obj.key if grappled_by_char_obj else 'Unknown'}.")
            return

        # Determine target
        target = None
        if args:
            target = caller.search(args, location=caller.location, quiet=True)
            # Handle case where search returns a list
            if isinstance(target, list):
                if len(target) == 1:
                    target = target[0]
                elif len(target) > 1:
                    caller.msg(f"Multiple targets match '{args}'. Please be more specific.")
                    return
                else:
                    target = None
                    
            if not target:
                # Try searching in adjacent combat rooms
                managed_rooms = handler.db.managed_rooms or []
                for room in managed_rooms:
                    if room != caller.location:
                        potential_target = caller.search(args, location=room, quiet=True)
                        # Handle list results for adjacent rooms too
                        if isinstance(potential_target, list):
                            if len(potential_target) == 1:
                                target = potential_target[0]
                                break
                            elif len(potential_target) > 1:
                                caller.msg(f"Multiple targets match '{args}' in {room.key}. Please be more specific.")
                                return
                        elif potential_target:
                            target = potential_target
                            break
                            
            if not target:
                caller.msg(f"You cannot find '{args}' to advance on.")
                return
                
            if target == caller:
                caller.msg(MSG_ADVANCE_SELF_TARGET)
                return
        else:
            # Use current combat target
            target = handler.get_target_obj(caller_entry)
            if not target:
                caller.msg(MSG_ADVANCE_NO_TARGET)
                return

        # Check if target is valid
        target_entry = next((e for e in handler.db.combatants if e["char"] == target), None)
        if not target_entry:
            caller.msg(f"{target.get_display_name(caller)} is not in combat.")
            return

        # Check if already in proximity
        if hasattr(caller.ndb, NDB_PROXIMITY) and caller.ndb.in_proximity_with and target in caller.ndb.in_proximity_with:
            caller.msg(f"You are already in melee proximity with {target.get_display_name(caller)}.")
            return

        # Set advance action to be processed on caller's next turn
        caller_entry["combat_action"] = COMBAT_ACTION_ADVANCE
        caller_entry["combat_action_target"] = target  # Store target for handler processing
        caller.msg(MSG_ADVANCE_PREPARE.format(target=target.get_display_name(caller)))
        splattercast.msg(f"{DEBUG_PREFIX_ADVANCE}: {caller.key} queued advance action on {target.key} for next turn.")

        # Ensure combat handler is active
        if handler and not handler.is_active:
            handler.start()


class CmdCharge(Command):
    """
    Charge recklessly at a target to engage in melee.

    Usage:
      charge [target]

    If no target is specified, attempts to charge your current
    combat target.
    A more aggressive, but potentially more dangerous, way to close
    distance with a target in the same room or an adjacent one.
    Success may grant a bonus on your next attack, but failure or
    the act of charging might leave you vulnerable.
    Charge always attempts to establish melee proximity on success.
    """
    key = "charge"
    aliases = ["rush"]
    locks = "cmd:all()"
    help_category = "Combat"

    def func(self):
        caller = self.caller
        args = self.args.strip()
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        handler = getattr(caller.ndb, NDB_COMBAT_HANDLER, None)

        if not handler:
            caller.msg(MSG_CHARGE_NOT_IN_COMBAT)
            return

        caller_entry = next((e for e in handler.db.combatants if e["char"] == caller), None)
        if not caller_entry:
            caller.msg(MSG_CHARGE_COMBAT_DATA_MISSING)
            splattercast.msg(f"{DEBUG_PREFIX_CHARGE}_{DEBUG_ERROR}: {caller.key} has handler but no combat entry.")
            return

        # Check if being grappled
        grappled_by_char_obj = handler.get_grappled_by_obj(caller_entry)
        if grappled_by_char_obj:
            caller.msg(f"You cannot charge while {grappled_by_char_obj.get_display_name(caller) if grappled_by_char_obj else 'someone'} is grappling you. Try 'escape' first.")
            splattercast.msg(f"{DEBUG_PREFIX_CHARGE}_{DEBUG_FAIL}: {caller.key} attempted to charge while grappled by {grappled_by_char_obj.key if grappled_by_char_obj else 'Unknown'}.")
            return

        # Check if caller is grappling someone
        grappling_victim_obj = handler.get_grappling_obj(caller_entry)
        if grappling_victim_obj:
            if args:
                # Caller specified a target while grappling
                target_search = caller.search(args, location=caller.location, quiet=True)
                # Handle case where search returns a list
                if isinstance(target_search, list):
                    if len(target_search) == 1:
                        target_search = target_search[0]
                    elif len(target_search) > 1:
                        caller.msg(f"Multiple targets match '{args}'. Please be more specific.")
                        return
                    else:
                        target_search = None
                        
                if not target_search:
                    # Try searching in adjacent combat rooms
                    managed_rooms = handler.db.managed_rooms or []
                    for room in managed_rooms:
                        if room != caller.location:
                            potential_target = caller.search(args, location=room, quiet=True)
                            # Handle list results for adjacent rooms too
                            if isinstance(potential_target, list):
                                if len(potential_target) == 1:
                                    target_search = potential_target[0]
                                    break
                                elif len(potential_target) > 1:
                                    caller.msg(f"Multiple targets match '{args}' in {room.key}. Please be more specific.")
                                    return
                            elif potential_target:
                                target_search = potential_target
                                break
                
                if target_search == grappling_victim_obj:
                    # Trying to charge the person they're grappling
                    caller.msg(f"You cannot charge {grappling_victim_obj.get_display_name(caller)} while you are grappling them! Release the grapple first or choose a different target.")
                    splattercast.msg(f"{DEBUG_PREFIX_CHARGE}_{DEBUG_FAIL}: {caller.key} attempted to charge their grapple victim {grappling_victim_obj.key}.")
                    return
                elif target_search:
                    # Charging someone else - prepare to potentially release grapple on successful charge
                    # (Grapple release will be handled by combat handler only on successful charge)
                    caller.msg(f"|yYou prepare to release your grapple on {grappling_victim_obj.get_display_name(caller)} and charge {target_search.get_display_name(caller)}!|n")
                    splattercast.msg(f"{DEBUG_PREFIX_CHARGE}_GRAPPLE_CHARGE: {caller.key} preparing to charge {target_search.key} while grappling {grappling_victim_obj.key}.")
                    # Continue with normal charge logic using target_search
                else:
                    caller.msg(f"You cannot find '{args}' to charge at.")
                    return
            else:
                # No target specified while grappling - require explicit target
                caller.msg(f"You are currently grappling {grappling_victim_obj.get_display_name(caller)}. You must specify a target to charge, or use 'escape' to release the grapple first.")
                splattercast.msg(f"{DEBUG_PREFIX_CHARGE}_{DEBUG_FAIL}: {caller.key} attempted to charge with no target while grappling {grappling_victim_obj.key}.")
                return

        # Determine target
        target = None
        if args:
            target = caller.search(args, location=caller.location, quiet=True)
            # Handle case where search returns a list
            if isinstance(target, list):
                if len(target) == 1:
                    target = target[0]
                elif len(target) > 1:
                    caller.msg(f"Multiple targets match '{args}'. Please be more specific.")
                    return
                else:
                    target = None
                    
            if not target:
                # Try searching in adjacent combat rooms
                managed_rooms = handler.db.managed_rooms or []
                for room in managed_rooms:
                    if room != caller.location:
                        potential_target = caller.search(args, location=room, quiet=True)
                        # Handle list results for adjacent rooms too
                        if isinstance(potential_target, list):
                            if len(potential_target) == 1:
                                target = potential_target[0]
                                break
                            elif len(potential_target) > 1:
                                caller.msg(f"Multiple targets match '{args}' in {room.key}. Please be more specific.")
                                return
                        elif potential_target:
                            target = potential_target
                            break
                            
            if not target:
                caller.msg(f"You cannot find '{args}' to charge.")
                return
                
            if target == caller:
                caller.msg(MSG_CHARGE_SELF_TARGET)
                return
        else:
            # Use current combat target
            target = handler.get_target_obj(caller_entry)
            if not target:
                caller.msg(MSG_CHARGE_NO_TARGET)
                return

        # Check if target is valid
        target_entry = next((e for e in handler.db.combatants if e["char"] == target), None)
        if not target_entry:
            caller.msg(f"{target.get_display_name(caller)} is not in combat.")
            return

        # Check if already in proximity
        if hasattr(caller.ndb, NDB_PROXIMITY) and caller.ndb.in_proximity_with and target in caller.ndb.in_proximity_with:
            caller.msg(f"You are already in melee proximity with {target.get_display_name(caller)}.")
            return

        # Set charge action to be processed on caller's next turn
        caller_entry["combat_action"] = COMBAT_ACTION_CHARGE
        caller_entry["combat_action_target"] = target  # Store target for handler processing
        caller.msg(MSG_CHARGE_PREPARE.format(target=target.get_display_name(caller)))
        splattercast.msg(f"{DEBUG_PREFIX_CHARGE}: {caller.key} queued charge action on {target.key} for next turn.")

        # Ensure combat handler is active
        if handler and not handler.is_active:
            handler.start()

