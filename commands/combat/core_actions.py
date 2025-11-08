"""
Core Combat Actions Module

Contains the fundamental combat commands that initiate or control combat flow:
- CmdAttack: Primary combat initiation command
- CmdStop: Stop attacking/aiming commands

These commands form the core of the combat system and are used most frequently
by players during combat encounters.
"""

from evennia import Command
from evennia.utils.utils import inherits_from
from random import randint, choice
from world.combat.handler import get_or_create_combat
from world.combat.constants import COMBAT_SCRIPT_KEY
from world.combat.messages import get_combat_message
from evennia.comms.models import ChannelDB
from evennia.utils import utils
from evennia.utils.evtable import EvTable

from world.combat.constants import (
    MSG_ATTACK_WHO, MSG_SELF_TARGET, MSG_NOT_IN_COMBAT, MSG_NO_COMBAT_DATA,
    MSG_STOP_WHAT, MSG_STOP_NOT_AIMING, MSG_STOP_AIM_ERROR, MSG_STOP_NOT_IN_COMBAT,
    MSG_STOP_NOT_REGISTERED, MSG_STOP_YIELDING, MSG_STOP_ALREADY_ACCEPTING_GRAPPLE,
    MSG_STOP_ALREADY_YIELDING, MSG_RESUME_ATTACKING, MSG_GRAPPLE_VIOLENT_SWITCH,
    DEBUG_PREFIX_ATTACK, DEBUG_FAILSAFE, DEBUG_SUCCESS, DEBUG_FAIL, DEBUG_ERROR,
    NDB_PROXIMITY, DEFAULT_WEAPON_TYPE, COLOR_SUCCESS, COLOR_FAILURE, COLOR_WARNING
)
from world.combat.utils import (
    initialize_proximity_ndb, get_wielded_weapon, roll_stat, opposed_roll,
    log_combat_action, get_display_name_safe, validate_combat_target
)
from world.combat.proximity import (
    establish_proximity, break_proximity, clear_all_proximity, 
    is_in_proximity, get_proximity_list, proximity_opposed_roll
)
from world.combat.grappling import (
    get_grappling_target, get_grappled_by, establish_grapple, break_grapple,
    is_grappling, is_grappled, validate_grapple_action
)


class CmdAttack(Command):
    """
    Attack a target in your current room or in the direction you are aiming.

    Usage:
        attack <target>
        kill <target>

    Initiates combat and adds you and your target to the CombatHandler.
    Attack validity depends on weapon type and proximity to target.
    """

    key = "attack"
    aliases = ["kill"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller
        args = self.args.strip()
        splattercast = ChannelDB.objects.get_channel("Splattercast")

        if not args:
            caller.msg(MSG_ATTACK_WHO)
            return

        # --- SELF-TARGET CHECK (early) ---
        # Check if player is trying to target themselves with "me", "self", or "myself"
        if args.lower() in ["me", "myself", "self"]:
            caller.msg(MSG_SELF_TARGET)
            return
        # --- END SELF-TARGET CHECK ---

        # --- WEAPON IDENTIFICATION (early) ---
        hands = getattr(caller, "hands", {})
        weapon_obj = next((item for hand, item in hands.items() if item), None)
        
        # Debug weapon detection
        splattercast.msg(f"WEAPON_DETECT: {caller.key} hands={hands}, weapon_obj={weapon_obj.key if weapon_obj else 'None'}")
        if weapon_obj:
            splattercast.msg(f"WEAPON_DETECT: {weapon_obj.key} has db={hasattr(weapon_obj, 'db')}, "
                           f"db.is_ranged={getattr(weapon_obj.db, 'is_ranged', 'MISSING') if hasattr(weapon_obj, 'db') else 'NO_DB'}, "
                           f"db.weapon_type={getattr(weapon_obj.db, 'weapon_type', 'MISSING') if hasattr(weapon_obj, 'db') else 'NO_DB'}")
        
        is_ranged_weapon = weapon_obj and hasattr(weapon_obj, "db") and getattr(weapon_obj.db, "is_ranged", False)
        weapon_name_for_msg = weapon_obj.key if weapon_obj else "your fists"
        weapon_type_for_msg = (str(weapon_obj.db.weapon_type).lower() if weapon_obj and hasattr(weapon_obj, "db") and hasattr(weapon_obj.db, "weapon_type") and weapon_obj.db.weapon_type else "unarmed")
        
        splattercast.msg(f"WEAPON_FINAL: {caller.key} is_ranged={is_ranged_weapon}, weapon_type={weapon_type_for_msg}")
        # --- END WEAPON IDENTIFICATION ---

        target_room = caller.location
        target_search_name = args

        # --- AIMING DIRECTION ATTACK ---
        aiming_direction = getattr(caller.ndb, "aiming_direction", None)
        if aiming_direction:
            splattercast.msg(f"{DEBUG_PREFIX_ATTACK}: {caller.key} is aiming {aiming_direction}, attempting remote attack on '{args}'.")
            
            aiming_direction_lower = aiming_direction.lower()
            exit_obj = None
            for ex in caller.location.exits:
                current_exit_aliases_lower = [alias.lower() for alias in (ex.aliases.all() if hasattr(ex.aliases, "all") else [])]
                if ex.key.lower() == aiming_direction_lower or aiming_direction_lower in current_exit_aliases_lower:
                    exit_obj = ex
                    break
            
            if not exit_obj or not exit_obj.destination:
                caller.msg(f"You are aiming {aiming_direction}, but there's no clear path to attack through.")
                return
            target_room = exit_obj.destination
            splattercast.msg(f"{DEBUG_PREFIX_ATTACK}: Remote attack target room is {target_room.key}.")
        # --- END AIMING DIRECTION ATTACK ---

        potential_targets = [
            obj for obj in target_room.contents
            if inherits_from(obj, "typeclasses.characters.Character") and
               (target_search_name.lower() in obj.key.lower() or
                any(target_search_name.lower() in alias.lower() for alias in (obj.aliases.all() if hasattr(obj.aliases, "all") else [])))
        ]
        if not potential_targets:
            caller.msg(f"You don't see '{target_search_name}' {(f'in the {aiming_direction} direction' if aiming_direction else 'here')}.")
            return
        target = potential_targets[0]

        if target == caller:
            caller.msg(MSG_SELF_TARGET)
            return

        # --- TARGET VALIDATION ---
        # Check if target can be attacked (holographic merchants, etc.)
        if hasattr(target, 'validate_attack_target'):
            validation_error = target.validate_attack_target()
            if validation_error:
                # Target is invalid - show glitch effect for holographic
                if getattr(target.db, 'is_holographic', False):
                    caller.msg(f"|yYour attack passes through {target.key}'s holographic form with a shimmer of static.|n")
                    target.location.msg_contents(
                        f"|y{caller.key}'s attack passes through {target.key}'s flickering projection.|n",
                        exclude=[caller, target]
                    )
                else:
                    # Generic validation failure
                    caller.msg(f"You cannot attack {target.key}.")
                return

        # --- GRAPPLE RESTRICTION CHECK ---
        # Check if caller is grappled and trying to attack their grappler
        caller_handler = getattr(caller.ndb, "combat_handler", None)
        if caller_handler:
            combatants_list = getattr(caller_handler.db, "combatants", None)
            if combatants_list:  # Add None check to prevent iteration errors
                caller_entry = next((e for e in combatants_list if e["char"] == caller), None)
                if caller_entry:
                    grappler_obj = caller_handler.get_grappled_by_obj(caller_entry)
                    if grappler_obj and grappler_obj == target:
                        caller.msg(f"You cannot attack {target.key} while they are grappling you! Use 'escape' to resist violently.")
                        return

        # --- PROXIMITY AND WEAPON VALIDATION ---
        # Initialize caller's proximity NDB if missing (failsafe)
        if initialize_proximity_ndb(caller):
            splattercast.msg(f"{DEBUG_PREFIX_ATTACK}_{DEBUG_FAILSAFE}: Initialized {NDB_PROXIMITY} for {caller.key}.")

        # --- COMBAT INITIATION PROXIMITY ESTABLISHMENT ---
        # For melee weapons in same room, establish proximity if this is NEW combat initiation
        if not aiming_direction and caller.location == target.location and not is_ranged_weapon:
            # Check if either character is already in combat (existing combat scenario)
            caller_existing_handler = getattr(caller.ndb, "combat_handler", None)
            target_existing_handler = getattr(target.ndb, "combat_handler", None)
            
            # If neither is in combat, this is NEW combat initiation - grant proximity to melee aggressor
            if not caller_existing_handler and not target_existing_handler:
                establish_proximity(caller, target)
                splattercast.msg(f"{DEBUG_PREFIX_ATTACK}_COMBAT_INITIATION: Established proximity between {caller.key} and {target.key} for melee combat initiation.")
            # If caller is not in combat but target is, this is JOINING existing combat - contested proximity roll
            elif not caller_existing_handler and target_existing_handler:
                splattercast.msg(f"{DEBUG_PREFIX_ATTACK}_COMBAT_JOIN: {caller.key} joins existing combat - rolling contested proximity.")
                
                # Perform contested proximity roll (same mechanics as advance command)
                from world.combat.utils import get_numeric_stat
                
                caller_motorics = get_numeric_stat(caller, "motorics")
                target_motorics = get_numeric_stat(target, "motorics")
                caller_roll = randint(1, max(1, caller_motorics))
                target_roll = randint(1, max(1, target_motorics))
                
                splattercast.msg(f"{DEBUG_PREFIX_ATTACK}_CONTESTED: {caller.key} (motorics:{caller_motorics}, roll:{caller_roll}) vs {target.key} (motorics:{target_motorics}, roll:{target_roll})")
                
                if caller_roll > target_roll:
                    # Success - establish proximity
                    establish_proximity(caller, target)
                    caller.msg(f"|gYou rush forward and close to melee range with {target.get_display_name(caller)}!|n")
                    target.msg(f"|y{caller.get_display_name(target)} rushes forward to melee range with you!|n")
                    caller.location.msg_contents(f"|y{caller.key} rushes forward to melee range with {target.key}!|n", exclude=[caller, target])
                    splattercast.msg(f"{DEBUG_PREFIX_ATTACK}_CONTESTED: {caller.key} successfully gained proximity to {target.key}.")
                else:
                    # Failure - no proximity established, but still joins combat
                    caller.msg(f"|rYou rush forward trying to reach {target.get_display_name(caller)}, but they keep their distance!|n")
                    target.msg(f"|g{caller.get_display_name(target)} rushes at you but you keep your distance!|n")
                    caller.location.msg_contents(f"|y{caller.key} rushes at {target.key} but fails to close the distance.|n", exclude=[caller, target])
                    splattercast.msg(f"{DEBUG_PREFIX_ATTACK}_CONTESTED: {caller.key} failed to gain proximity to {target.key}, but joins combat anyway.")
            else:
                splattercast.msg(f"{DEBUG_PREFIX_ATTACK}_EXISTING_COMBAT: Preserving existing proximity state. Caller handler: {caller_existing_handler.key if caller_existing_handler else 'None'}, Target handler: {target_existing_handler.key if target_existing_handler else 'None'}.")

        if not aiming_direction: # SAME ROOM ATTACK
            splattercast.msg(f"{DEBUG_PREFIX_ATTACK}: Validating same-room attack by {caller.key} on {target.key}.")
            is_in_melee_proximity = target in caller.ndb.in_proximity_with

            if is_in_melee_proximity: # Caller is in melee with target
                # Allow both ranged and melee attacks at melee range
                # Future: Could add penalties for ranged weapons at melee range here
                if is_ranged_weapon:
                    splattercast.msg(f"{DEBUG_PREFIX_ATTACK}_{DEBUG_SUCCESS}: {caller.key} attacking {target.key} with ranged weapon '{weapon_name_for_msg}' at melee range.")
                else:
                    splattercast.msg(f"{DEBUG_PREFIX_ATTACK}_{DEBUG_SUCCESS}: {caller.key} attacking {target.key} with non-ranged '{weapon_name_for_msg}' while in melee proximity.")
            else: # Caller is NOT in melee with target (at range in same room)
                if not is_ranged_weapon:
                    # Check if this is a "joining existing combat" scenario - allow those through
                    caller_existing_handler = getattr(caller.ndb, "combat_handler", None)
                    target_existing_handler = getattr(target.ndb, "combat_handler", None)
                    
                    if not caller_existing_handler and target_existing_handler:
                        # This is joining existing combat - proximity was handled above, allow through
                        splattercast.msg(f"{DEBUG_PREFIX_ATTACK}_JOINING: {caller.key} joining existing combat with melee weapon, proceeding to handler.")
                    else:
                        # Not joining existing combat - standard proximity failure
                        caller.msg(f"You are too far away to hit {target.get_display_name(caller)} with your {weapon_name_for_msg}. Try advancing or charging.")
                        splattercast.msg(f"{DEBUG_PREFIX_ATTACK}_{DEBUG_FAIL}: {caller.key} tried to use non-ranged weapon '{weapon_name_for_msg}' on {target.key} who is not in melee proximity. Attack aborted.")
                        return
                else:
                    splattercast.msg(f"{DEBUG_PREFIX_ATTACK}_{DEBUG_SUCCESS}: {caller.key} attacking {target.key} with ranged weapon '{weapon_name_for_msg}' from distance in same room.")
        else: # ADJACENT ROOM ATTACK (aiming_direction is set)
            splattercast.msg(f"{DEBUG_PREFIX_ATTACK}: Validating ranged attack into {target_room.key} by {caller.key} on {target.key}.")
            if not is_ranged_weapon:
                caller.msg(f"You need a ranged weapon to attack {target.get_display_name(caller)} in the {aiming_direction} direction.")
                splattercast.msg(f"{DEBUG_PREFIX_ATTACK}_{DEBUG_FAIL}: {caller.key} tried to attack into {aiming_direction} (target: {target.key}) without a ranged weapon ({weapon_name_for_msg}). Attack aborted.")
                return
            splattercast.msg(f"{DEBUG_PREFIX_ATTACK}_{DEBUG_SUCCESS}: {caller.key} attacking into {aiming_direction} with ranged weapon '{weapon_name_for_msg}'.")
        # --- END PROXIMITY AND WEAPON VALIDATION ---

        # --- Get/Create/Merge Combat Handlers ---
        caller_handler = get_or_create_combat(caller.location)
        target_handler = get_or_create_combat(target.location) # Might be the same if target_room is caller.location

        final_handler = caller_handler
        if caller_handler != target_handler:
            splattercast.msg(f"{DEBUG_PREFIX_ATTACK}: Cross-handler engagement! Caller's handler: {caller_handler.key} (on {caller_handler.obj.key}). Target's handler: {target_handler.key} (on {target_handler.obj.key}). Merging...")
            caller_handler.merge_handler(target_handler)
            splattercast.msg(f"{DEBUG_PREFIX_ATTACK}: Merge complete. Final handler is {final_handler.key}, now managing rooms: {[r.key for r in final_handler.db.managed_rooms]}.")
        else:
            splattercast.msg(f"{DEBUG_PREFIX_ATTACK}: Caller and target are (or will be) in the same handler zone: {final_handler.key} (on {final_handler.obj.key}).")
            final_handler.enroll_room(caller.location)
            final_handler.enroll_room(target.location)

        # --- CAPTURE PRE-ADDITION COMBAT STATE ---
        caller_was_in_final_handler = any(e["char"] == caller for e in final_handler.db.combatants)
        target_was_in_final_handler = any(e["char"] == target for e in final_handler.db.combatants)
        
        original_caller_target_in_handler = None
        if caller_was_in_final_handler:
            caller_entry_snapshot = next((e for e in final_handler.db.combatants if e["char"] == caller), None)
            if caller_entry_snapshot:
                original_caller_target_in_handler = final_handler.get_target_obj(caller_entry_snapshot)

        # --- Add combatants to the final_handler ---
        if not caller_was_in_final_handler:
            final_handler.add_combatant(caller, target=target)
        else: 
            caller_entry = next((e for e in final_handler.db.combatants if e["char"] == caller), None)
            if caller_entry: # Ensure entry exists
                final_handler.set_target(caller, target) # This command updates the target
                
                # Clear any existing combat action when attacking (prevents stuck charge actions)
                # Use copy-modify-save pattern to ensure changes persist
                combatants_copy = getattr(final_handler.db, "combatants", [])
                caller_entry_copy = next((e for e in combatants_copy if e.get("char") == caller), None)
                if caller_entry_copy:
                    caller_entry_copy["combat_action"] = None
                    caller_entry_copy["combat_action_target"] = None
                    
                    # Check if caller was yielding and provide appropriate messaging
                    was_yielding = caller_entry_copy.get("is_yielding", False)
                    caller_entry_copy["is_yielding"] = False
                    
                    # Save the modified combatants list back
                    setattr(final_handler.db, "combatants", combatants_copy)
                    
                    if was_yielding:
                        # Check if caller is grappled (being grappled by someone)
                        grappler_obj = final_handler.get_grappled_by_obj(caller_entry_copy)
                        if grappler_obj:
                            # Special message for switching to violent resistance while grappled
                            caller.msg(MSG_GRAPPLE_VIOLENT_SWITCH.format(grappler=grappler_obj.key))
                        else:
                            # General message for resuming attacking
                            caller.msg(MSG_RESUME_ATTACKING)

        if not target_was_in_final_handler:
            final_handler.add_combatant(target, target=caller) 
        else: 
            target_entry = next((e for e in final_handler.db.combatants if e["char"] == target), None)
            if target_entry: # Ensure entry exists
                if not final_handler.get_target_obj(target_entry): 
                     final_handler.set_target(target, caller)
                # Do not automatically un-yield target if they were already yielding.
                # target_entry["is_yielding"] = False

        # --- Messaging and Action ---
        if aiming_direction:
            # --- Attacking into an adjacent room ---
            splattercast.msg(f"{DEBUG_PREFIX_ATTACK}: Aiming direction attack by {caller.key} towards {aiming_direction} into {target_room.key}.")

            # --- ADDITIONAL AIMING DIRECTION LOGIC ---
            initiate_msg_obj = get_combat_message(weapon_type_for_msg, "initiate", attacker=caller, target=target, item=weapon_obj)
            
            std_attacker_initiate = ""
            std_victim_initiate = ""
            std_observer_initiate = ""

            if isinstance(initiate_msg_obj, dict):
                std_attacker_initiate = initiate_msg_obj.get("attacker_msg", f"You prepare to strike {target.key}!")
                std_victim_initiate = initiate_msg_obj.get("victim_msg", f"{caller.key} prepares to strike you!")
                std_observer_initiate = initiate_msg_obj.get("observer_msg", f"{caller.key} prepares to strike {target.key}!")
            elif isinstance(initiate_msg_obj, str): # Fallback if get_combat_message returns a single string for initiate
                splattercast.msg(f"CmdAttack (aiming): initiate_msg_obj for {weapon_type_for_msg} was a string. Using generic attacker/victim messages. String: {initiate_msg_obj}")
                std_observer_initiate = initiate_msg_obj
                std_attacker_initiate = f"You prepare to strike {target.key} with your {weapon_type_for_msg}!"
                std_victim_initiate = f"{caller.key} prepares to strike you with their {weapon_type_for_msg}!"
            else: # Unexpected type
                splattercast.msg(f"CmdAttack (aiming): Unexpected initiate_msg_obj type from get_combat_message for {weapon_type_for_msg}: {type(initiate_msg_obj)}. Content: {initiate_msg_obj}")
                std_attacker_initiate = f"You initiate an attack on {target.key}."
                std_victim_initiate = f"{caller.key} initiates an attack on you."
                std_observer_initiate = f"{caller.key} initiates an attack on {target.key}."

            # 2. Determine the direction from which the attack arrives in the target's room
            attacker_direction_from_target_perspective = "a nearby location" # Default
            exit_from_target_to_caller_room = None
            for ex_obj in target_room.exits:
                if ex_obj.destination == caller.location:
                    exit_from_target_to_caller_room = ex_obj
                    break
            if exit_from_target_to_caller_room:
                attacker_direction_from_target_perspective = exit_from_target_to_caller_room.key

            # 3. Construct and send messages (using |r for normal red)

            # Attacker's message
            prefix_attacker = f"|RAiming {aiming_direction} into {target_room.get_display_name(caller)}, "
            caller.msg(prefix_attacker + std_attacker_initiate)

            # Victim's message (in target_room)
            prefix_victim = f"|RSuddenly, you notice {caller.get_display_name(target)} to the {attacker_direction_from_target_perspective} aiming at you from {caller.location.get_display_name(target)}), "
            target.msg(prefix_victim + std_victim_initiate)

            # Observer message in caller's room (attacker's room)
            prefix_observer_caller_room = f"|R{caller.key} takes aim {aiming_direction} into {target_room.get_display_name(caller.location)}, "
            caller.location.msg_contents(prefix_observer_caller_room + std_observer_initiate, exclude=[caller])

            # Observer message in target's room
            prefix_observer_target_room = f"|RYour attention is drawn to the {attacker_direction_from_target_perspective} as {caller.key} aiming from {caller.location.get_display_name(target_room)}, "
            target_room.msg_contents(prefix_observer_target_room + std_observer_initiate, exclude=[target])
            
        else:
            # Standard local attack initiation message (use get_combat_message)
            initiate_msg_obj = get_combat_message(weapon_type_for_msg, "initiate", attacker=caller, target=target, item=weapon_obj)
            
            attacker_msg = ""
            victim_msg = ""
            observer_msg = ""
            
            if isinstance(initiate_msg_obj, dict):
                attacker_msg = initiate_msg_obj.get("attacker_msg", f"You prepare to strike {target.key}!")
                victim_msg = initiate_msg_obj.get("victim_msg", f"{caller.key} prepares to strike you!")
                observer_msg = initiate_msg_obj.get("observer_msg", f"{caller.key} prepares to strike {target.key}!")
            elif isinstance(initiate_msg_obj, str):
                # If it's just a string, use it as observer message and create first/second person versions
                observer_msg = initiate_msg_obj
                attacker_msg = f"You prepare to strike {target.key}!"
                victim_msg = f"{caller.key} prepares to strike you!"
            else:
                splattercast.msg(f"CmdAttack: Unexpected initiate_msg_obj type from get_combat_message for {weapon_type_for_msg}: {type(initiate_msg_obj)}. Content: {initiate_msg_obj}")
                attacker_msg = f"You initiate an attack on {target.key}."
                victim_msg = f"{caller.key} initiates an attack on you."
                observer_msg = f"{caller.key} initiates an attack on {target.key}."

            # Send personalized messages
            caller.msg(attacker_msg)
            target.msg(victim_msg)
            caller.location.msg_contents(observer_msg, exclude=[caller, target])

            # Check if target should also get an initiate message
            # Conditions: target wasn't already in combat OR target wasn't targeting anyone
            should_show_target_initiate = (
                not target_was_in_final_handler or 
                (target_was_in_final_handler and not final_handler.get_target_obj(next((e for e in final_handler.db.combatants if e["char"] == target), None)))
            )
            
            if should_show_target_initiate and target != caller:
                # Get target's weapon for their defensive initiate message
                target_weapon = get_wielded_weapon(target)
                target_weapon_type = "unarmed"
                if target_weapon and hasattr(target_weapon, 'db') and hasattr(target_weapon.db, 'weapon_type'):
                    target_weapon_type = target_weapon.db.weapon_type
                
                # Get target's initiate message (defensive reaction)
                target_initiate_msg_obj = get_combat_message(target_weapon_type, "initiate", attacker=target, target=caller, item=target_weapon)
                
                target_attacker_msg = ""
                target_victim_msg = ""
                target_observer_msg = ""
                
                if isinstance(target_initiate_msg_obj, dict):
                    target_attacker_msg = target_initiate_msg_obj.get("attacker_msg", f"{target.key} takes a defensive stance!")
                    target_victim_msg = target_initiate_msg_obj.get("victim_msg", f"{target.key} reacts defensively to your threat!")
                    target_observer_msg = target_initiate_msg_obj.get("observer_msg", f"{target.key} reacts defensively to {caller.key}'s threat.")
                elif isinstance(target_initiate_msg_obj, str):
                    target_observer_msg = target_initiate_msg_obj
                    target_attacker_msg = f"{target.key} takes a defensive stance!"
                    target_victim_msg = f"{target.key} reacts defensively to your threat!"
                else:
                    target_attacker_msg = f"{target.key} takes a defensive stance!"
                    target_victim_msg = f"{target.key} reacts defensively to your threat!"
                    target_observer_msg = f"{target.key} reacts defensively to {caller.key}'s threat."
                
                # Send target's defensive reaction messages
                target.msg(target_attacker_msg)  # Target sees their own defensive action
                caller.msg(target_victim_msg)   # Attacker sees target's reaction to them
                caller.location.msg_contents(target_observer_msg, exclude=[caller, target])  # Others see the reaction
                
                # Debug message (simplified to avoid f-string complexity)
                target_entry = next((e for e in final_handler.db.combatants if e["char"] == target), None)
                has_target = bool(final_handler.get_target_obj(target_entry)) if target_entry else False
                splattercast.msg(f"TARGET_INITIATE: {target.key} shown defensive initiate against {caller.key} (was_in_combat: {target_was_in_final_handler}, has_target: {has_target})")

        splattercast.msg(f"{DEBUG_PREFIX_ATTACK}: {caller.key} attacks {target.key if target else 'a direction'}. Combat managed by {final_handler.key}.")
        
        if not final_handler.is_active:
            final_handler.start()


class CmdStop(Command):
    """
    Stop attacking or aiming.

    Usage:
      stop aiming
      stop attacking

    Stops your current aggressive actions. 'stop aiming' clears any aim locks
    you have on targets or directions. 'stop attacking' makes you yield in
    combat (stop actively attacking but remain in combat).
    """

    key = "stop"
    locks = "cmd:all()"
    help_category = "Combat"

    def func(self):
        caller = self.caller
        args = self.args.strip().lower()
        
        if not args:
            caller.msg(MSG_STOP_WHAT)
            return

        if args == "aiming" or args == "aim":
            # Check if currently aiming at a target
            aiming_target = getattr(caller.ndb, "aiming_at", None)
            aiming_direction = getattr(caller.ndb, "aiming_direction", None)
            
            if not aiming_target and not aiming_direction:
                caller.msg(MSG_STOP_NOT_AIMING)
                return
                
            # Clear target aiming
            if aiming_target:
                delattr(caller.ndb, "aiming_at")
                if hasattr(aiming_target.ndb, "aimed_at_by") and getattr(aiming_target.ndb, "aimed_at_by") == caller:
                    delattr(aiming_target.ndb, "aimed_at_by")
                
                # Clear override_place and handle mutual showdown cleanup
                self._clear_aim_override_place_on_stop(caller, aiming_target)
                
                # Get weapon name for better messaging
                hands = getattr(caller, "hands", {})
                weapon = next((item for hand, item in hands.items() if item), None)
                weapon_name = weapon.key if weapon else "weapon"
                
                caller.msg(f"You stop aiming at {aiming_target.key} and lower your {weapon_name}.")
                aiming_target.msg(f"{caller.key} stops aiming at you.")
                
            # Clear direction aiming
            if aiming_direction:
                delattr(caller.ndb, "aiming_direction")
                
                # Clear directional aim override_place (but only if we weren't also target aiming)
                if not aiming_target:
                    caller.override_place = ""
                
                # Get weapon name for better messaging
                hands = getattr(caller, "hands", {})
                weapon = next((item for hand, item in hands.items() if item), None)
                weapon_name = weapon.key if weapon else "weapon"
                
                # Try to get the actual exit name from the direction
                exit_obj = caller.search(aiming_direction, location=caller.location, quiet=True)
                if exit_obj and hasattr(exit_obj[0], 'destination') and exit_obj[0].destination:
                    exit_name = exit_obj[0].key
                else:
                    # Fallback to direction mapping for non-exit directions
                    direction_map = {
                        "n": "north", "s": "south", "e": "east", "w": "west",
                        "ne": "northeast", "nw": "northwest", "se": "southeast", "sw": "southwest",
                        "u": "up", "d": "down", "in": "in", "out": "out"
                    }
                    exit_name = direction_map.get(aiming_direction.lower(), aiming_direction)
                
                caller.msg(f"You stop aiming to the {exit_name} and lower your {weapon_name}.")
                
        elif args == "attacking" or args == "attack":
            handler = getattr(caller.ndb, "combat_handler", None)
            
            if not handler:
                caller.msg(MSG_STOP_NOT_IN_COMBAT)
                return

            caller_entry = next((e for e in handler.db.combatants if e["char"] == caller), None)
            if not caller_entry:
                caller.msg(MSG_STOP_NOT_REGISTERED)
                return

            # Check if being grappled - different message in this case
            grappler_obj = handler.get_grappled_by_obj(caller_entry)
            if grappler_obj:
                if not caller_entry.get("is_yielding", False):
                    caller_entry["is_yielding"] = True
                    caller.msg(MSG_STOP_YIELDING)
                else:
                    caller.msg(MSG_STOP_ALREADY_ACCEPTING_GRAPPLE)
            else:
                if not caller_entry.get("is_yielding", False):
                    caller_entry["is_yielding"] = True
                    caller.msg(MSG_STOP_YIELDING)
                else:
                    caller.msg(MSG_STOP_ALREADY_YIELDING)
        else:
            caller.msg(MSG_STOP_WHAT)

    def _clear_aim_override_place_on_stop(self, aimer, target):
        """
        Clear override_place for aiming when stopping aim, handling mutual showdown cleanup.
        
        Args:
            aimer: The character stopping their aim
            target: The character they were aiming at
        """
        # Check if they were in a mutual showdown
        if (hasattr(aimer, 'override_place') and hasattr(target, 'override_place') and
            aimer.override_place == "locked in a deadly showdown." and 
            target.override_place == "locked in a deadly showdown."):
            # They were in a showdown - clear aimer's place, check if target should revert to normal aiming
            aimer.override_place = ""
            
            # If target is still aiming at aimer, revert them to normal aiming
            target_still_aiming = getattr(target.ndb, "aiming_at", None)
            if target_still_aiming == aimer:
                target.override_place = f"aiming carefully at {aimer.key}."
            else:
                # Target isn't aiming at anyone, clear their place too
                target.override_place = ""
        else:
            # Normal aiming cleanup
            if hasattr(aimer, 'override_place'):
                aimer.override_place = ""
