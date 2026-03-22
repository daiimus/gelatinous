"""
Explosive Device Management Commands

Commands for managing explosive devices including:
- Rigging grenades to exits as traps
- Defusing live grenades with skill checks
- Remote detonator operations (scan, detonate, list, clear)

These commands were extracted from CmdThrow.py to separate explosive
device management from the core throwing mechanics.

Part of the G.R.I.M. Combat System.
"""

import random
from evennia import Command, utils
from evennia.comms.models import ChannelDB
from world.combat.constants import (
    DEBUG_PREFIX_THROW,
    NDB_PROXIMITY_UNIVERSAL,
    NDB_COUNTDOWN_REMAINING,
    NDB_GRENADE_TIMER,
    SPLATTERCAST_CHANNEL,
    MSG_RIG_WHAT,
    MSG_RIG_INVALID_SYNTAX,
    MSG_RIG_NO_HANDS,
    MSG_RIG_OBJECT_NOT_WIELDED,
    MSG_RIG_OBJECT_NOT_FOUND,
    MSG_RIG_NOT_EXPLOSIVE,
    MSG_RIG_ALREADY_PINNED,
    MSG_RIG_INVALID_EXIT,
    MSG_RIG_EXIT_ALREADY_RIGGED,
    MSG_RIG_SUCCESS,
    MSG_RIG_SUCCESS_ROOM,
    MSG_GRENADE_DUD_ROOM,
    MSG_GRENADE_EXPLODE_ROOM,
    MSG_GRENADE_DAMAGE,
    MSG_GRENADE_DAMAGE_ROOM,
    MSG_GRENADE_CHAIN_TRIGGER,
)
from commands.explosion_utils import (
    notify_adjacent_rooms_of_explosion,
    get_unified_explosion_proximity,
)


class CmdRig(Command):
    """
    Rig explosives to exits as traps.

    Usage:
        rig <grenade> to <exit>

    Examples:
        rig grenade to north
        rig flashbang to door

    Set up a grenade as a trap on an exit. The grenade will explode when
    someone tries to pass through that exit. The grenade must NOT have its
    pin pulled - the pin will be pulled automatically when triggered.
    """

    key = "rig"
    locks = "cmd:all()"
    help_category = "Combat"

    def parse(self):
        """Parse rig command syntax."""
        self.args = self.args.strip()

        # Expected syntax: "<grenade> to <exit>"
        if " to " in self.args:
            parts = self.args.split(" to ", 1)
            if len(parts) == 2:
                self.grenade_name = parts[0].strip()
                self.exit_name = parts[1].strip()
                return

        self.grenade_name = None
        self.exit_name = None

    def func(self):
        """Execute rig command."""
        if not self.args:
            self.caller.msg(MSG_RIG_WHAT)
            return

        if not self.grenade_name or not self.exit_name:
            self.caller.msg(MSG_RIG_INVALID_SYNTAX)
            return

        # Check for hands at all
        caller_hands = getattr(self.caller, 'hands', None)
        if caller_hands is None or not caller_hands:
            self.caller.msg(MSG_RIG_NO_HANDS)
            return

        # Find grenade in hands
        grenade = None
        for hand, wielded_obj in caller_hands.items():
            if wielded_obj and self.grenade_name.lower() in wielded_obj.key.lower():
                grenade = wielded_obj
                break

        if not grenade:
            # Check if exists but not wielded
            search_obj = self.caller.search(self.grenade_name, location=self.caller, quiet=True)
            if search_obj:
                self.caller.msg(MSG_RIG_OBJECT_NOT_WIELDED.format(object=self.grenade_name))
                return
            else:
                self.caller.msg(MSG_RIG_OBJECT_NOT_FOUND.format(object=self.grenade_name))
                return

        # Validate explosive
        if not grenade.db.is_explosive:
            self.caller.msg(MSG_RIG_NOT_EXPLOSIVE.format(object=grenade.key))
            return

        # Check if pin is NOT pulled (should be unpinned for rigging)
        if grenade.db.pin_pulled:
            self.caller.msg(MSG_RIG_ALREADY_PINNED)
            return

        # Find exit
        exit_search = self.caller.search(self.exit_name, location=self.caller.location, quiet=True)
        exit_obj = exit_search[0] if exit_search else None
        if not exit_obj or not hasattr(exit_obj, 'destination') or not exit_obj.destination:
            self.caller.msg(MSG_RIG_INVALID_EXIT.format(exit=self.exit_name))
            return

        # Check if exit already rigged
        existing_rigged = exit_obj.db.rigged_grenade
        if existing_rigged:
            self.caller.msg(MSG_RIG_EXIT_ALREADY_RIGGED)
            return

        # Check if return exit is already rigged too
        return_exit = self.find_return_exit_for_check(exit_obj)
        if return_exit and return_exit.db.rigged_grenade:
            self.caller.msg(MSG_RIG_EXIT_ALREADY_RIGGED)
            return

        # Rig the grenade
        self.rig_grenade(grenade, exit_obj)

    def find_return_exit_for_check(self, exit_obj):
        """Find the return exit for pre-rigging checks."""
        if not exit_obj.destination:
            return None

        destination_room = exit_obj.destination
        current_room = self.caller.location

        # Look for an exit in the destination room that leads back to current room
        for obj in destination_room.contents:
            if (hasattr(obj, 'destination') and
                obj.destination == current_room and
                obj != exit_obj):  # Don't check the same exit twice
                return obj

        return None

    def rig_grenade(self, grenade, exit_obj):
        """Rig the grenade to the exit and its return exit."""
        # Remove from hand
        caller_hands = getattr(self.caller, 'hands', {})
        for hand_name, wielded_obj in caller_hands.items():
            if wielded_obj == grenade:
                caller_hands[hand_name] = None
                break

        # Keep grenade in current room instead of moving to exit
        grenade.move_to(self.caller.location, quiet=True)

        # Set up rigging on the main exit
        exit_obj.db.rigged_grenade = grenade
        grenade.db.rigged_to_exit = exit_obj
        grenade.db.rigged_by = self.caller  # Store who rigged it for immunity

        # Add integration description for rigged grenade
        # Store original integration state if not already stored
        if grenade.db.original_integrate is None:
            grenade.db.original_integrate = grenade.db.integrate or False
        if grenade.db.original_integration_desc is None:
            grenade.db.original_integration_desc = grenade.db.integration_desc
        if grenade.db.original_integration_priority is None:
            grenade.db.original_integration_priority = grenade.db.integration_priority

        # Enable integration and set rigging description with priority
        grenade.db.integrate = True
        grenade.db.integration_desc = f"A |C{grenade.get_display_name(self.caller)}|n is rigged to the {exit_obj.key} exit with a barely visible trip wire."
        grenade.db.integration_priority = 3  # High priority for rigged grenades

        # Find and rig the return exit too
        return_exit = self.find_return_exit(exit_obj)
        if return_exit:
            return_exit.db.rigged_grenade = grenade
            splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_SUCCESS: Also rigged return exit {return_exit} in {return_exit.location}")

        # Cancel normal countdown and set up trigger
        if hasattr(grenade.ndb, NDB_GRENADE_TIMER):
            # Cancel existing timer
            delattr(grenade.ndb, NDB_GRENADE_TIMER)

        # Announce
        self.caller.msg(MSG_RIG_SUCCESS.format(object=grenade.key, exit_name=exit_obj.key))
        self.caller.location.msg_contents(
            MSG_RIG_SUCCESS_ROOM.format(rigger=self.caller.key, object=grenade.key, exit_name=exit_obj.key),
            exclude=self.caller
        )

        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        splattercast.msg(f"{DEBUG_PREFIX_THROW}_SUCCESS: {self.caller} rigged {grenade} to {exit_obj}")

    def find_return_exit(self, exit_obj):
        """Find the return exit that leads back to the current room."""
        if not exit_obj.destination:
            return None

        destination_room = exit_obj.destination
        current_room = self.caller.location

        # Look for an exit in the destination room that leads back to current room
        for obj in destination_room.contents:
            if (hasattr(obj, 'destination') and
                obj.destination == current_room and
                obj != exit_obj):  # Don't rig the same exit twice
                return obj

        return None


class CmdDefuse(Command):
    """
    Defuse live grenades and explosives.

    Usage:
        defuse <grenade>

    Examples:
        defuse grenade
        defuse flashbang

    Attempt to defuse a live grenade using technical skill and dexterity.
    Requires the grenade to be in proximity (within reach). Uses Intellect +
    Motorics skill check with time pressure - the less time remaining, the
    harder the defuse attempt becomes.

    WARNING: Failed defuse attempts may trigger early detonation!
    Each grenade can only be defused once per character to prevent spam.
    """

    key = "defuse"
    locks = "cmd:all()"
    help_category = "Combat"

    def func(self):
        """Execute defuse command."""
        if not self.args:
            self.caller.msg("Defuse what?")
            return

        grenade_name = self.args.strip()

        # Find grenade in proximity
        grenade = self.find_grenade_in_proximity(grenade_name)
        if not grenade:
            return

        # Validate grenade state
        if not self.validate_grenade_for_defuse(grenade):
            return

        # Check one-attempt-per-grenade limit
        if self.already_attempted_defuse(grenade):
            self.caller.msg(f"You have already attempted to defuse the {grenade.key}.")
            return

        # Execute defuse attempt
        self.attempt_defuse(grenade)

    def find_grenade_in_proximity(self, grenade_name):
        """Find grenade in proximity or establish proximity for nearby grenades."""
        # First check existing proximity relationships
        proximity_candidates = []

        # Check both room contents AND character inventory for proximity candidates
        all_candidates = list(self.caller.location.contents) + list(self.caller.contents)

        for obj in all_candidates:
            if (grenade_name.lower() in obj.key.lower() and
                obj.db.is_explosive):

                # Check if caller is already in this object's proximity
                obj_proximity = getattr(obj.ndb, NDB_PROXIMITY_UNIVERSAL, [])
                if obj_proximity and self.caller in obj_proximity:
                    proximity_candidates.append(obj)

        # If found in existing proximity, return it
        if proximity_candidates:
            if len(proximity_candidates) > 1:
                self.caller.msg(f"Multiple {grenade_name}s are within reach. Be more specific.")
                return None
            return proximity_candidates[0]

        # If not in proximity, check for physical presence and establish mutual proximity
        physical_candidates = []

        # Check both room contents AND character inventory for physical candidates
        for obj in all_candidates:
            if (grenade_name.lower() in obj.key.lower() and
                obj.db.is_explosive):

                # Check if grenade is live (either pin pulled OR rigged to exit)
                pin_pulled = obj.db.pin_pulled
                is_rigged = obj.db.rigged_to_exit is not None

                if pin_pulled or is_rigged:
                    physical_candidates.append(obj)

        if not physical_candidates:
            self.caller.msg(f"You don't see any armed '{grenade_name}' within reach to defuse.")
            return None

        if len(physical_candidates) > 1:
            self.caller.msg(f"Multiple {grenade_name}s are nearby. Be more specific.")
            return None

        # Establish mutual proximity and return the grenade
        grenade = physical_candidates[0]

        # Different message for held vs room grenades
        if grenade.location == self.caller:
            self.caller.msg(f"You examine the {grenade.key} in your hands, preparing to defuse it...")
        else:
            self.caller.msg(f"You move closer to the {grenade.key}, entering its blast radius...")
            self.establish_mutual_proximity(grenade)

        return grenade

    def establish_mutual_proximity(self, grenade):
        """Establish mutual proximity between character and grenade."""
        # Add character to grenade's proximity (enters blast radius)
        grenade_proximity = getattr(grenade.ndb, NDB_PROXIMITY_UNIVERSAL, [])
        if not isinstance(grenade_proximity, list):
            grenade_proximity = []

        if self.caller not in grenade_proximity:
            grenade_proximity.append(self.caller)

            # Also establish proximity with other characters already in the grenade's proximity
            for other_char in list(grenade_proximity):  # Use list() to avoid modification during iteration
                if (hasattr(other_char, 'ndb') and other_char != self.caller):
                    other_proximity = getattr(other_char.ndb, NDB_PROXIMITY_UNIVERSAL, [])
                    if not isinstance(other_proximity, list):
                        other_proximity = []
                        setattr(other_char.ndb, NDB_PROXIMITY_UNIVERSAL, other_proximity)

                    if self.caller not in other_proximity:
                        other_proximity.append(self.caller)

        setattr(grenade.ndb, NDB_PROXIMITY_UNIVERSAL, grenade_proximity)

        # Add grenade to character's proximity
        char_proximity = getattr(self.caller.ndb, NDB_PROXIMITY_UNIVERSAL, [])
        if not isinstance(char_proximity, list):
            char_proximity = []
            setattr(self.caller.ndb, NDB_PROXIMITY_UNIVERSAL, char_proximity)

        if grenade not in char_proximity:
            char_proximity.append(grenade)

            # Also add other characters in the grenade's proximity to this character's proximity
            for other_char in grenade_proximity:
                if (hasattr(other_char, 'ndb') and other_char != self.caller and
                    other_char not in char_proximity):
                    char_proximity.append(other_char)

        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        if splattercast:
            splattercast.msg(f"DEFUSE_PROXIMITY: {self.caller.key} established mutual proximity with {grenade.key} "
                           f"(grenade proximity: {[c.key if hasattr(c, 'key') else str(c) for c in grenade_proximity]})")

    def validate_grenade_for_defuse(self, grenade):
        """Validate that grenade can be defused."""
        # Must be explosive
        if not grenade.db.is_explosive:
            self.caller.msg(f"The {grenade.key} is not an explosive device.")
            return False

        # Must be live (pin pulled OR rigged)
        pin_pulled = grenade.db.pin_pulled
        is_rigged = grenade.db.rigged_to_exit is not None

        if not (pin_pulled or is_rigged):
            self.caller.msg(f"The {grenade.key} is not armed - no need to defuse it.")
            return False

        # For rigged grenades, no timer check needed (they're not counting down)
        if is_rigged:
            return True

        # For pin-pulled grenades, check timer
        remaining_time = getattr(grenade.ndb, NDB_COUNTDOWN_REMAINING, 0)
        if remaining_time is None or remaining_time <= 0:
            self.caller.msg(f"The {grenade.key} has already exploded or is about to explode!")
            return False

        return True

    def already_attempted_defuse(self, grenade):
        """Check if caller has already attempted to defuse this grenade."""
        attempted_by = getattr(grenade.ndb, 'defuse_attempted_by', [])
        if attempted_by is None:
            attempted_by = []
            setattr(grenade.ndb, 'defuse_attempted_by', attempted_by)

        return self.caller in attempted_by

    def attempt_defuse(self, grenade):
        """Execute the defuse attempt with skill checks."""
        # Mark attempt to prevent spam
        attempted_by = getattr(grenade.ndb, 'defuse_attempted_by', [])
        if attempted_by is None:
            attempted_by = []
        attempted_by.append(self.caller)
        setattr(grenade.ndb, 'defuse_attempted_by', attempted_by)

        # Check if this is a rigged grenade (different difficulty calculation)
        is_rigged = grenade.db.rigged_to_exit is not None

        if is_rigged:
            # Rigged grenades: base difficulty only (no time pressure)
            base_difficulty = 18  # Slightly harder base (trap disarmament)
            time_pressure = 0
            total_difficulty = base_difficulty
            remaining_time = "N/A"
        else:
            # Live grenades: time pressure difficulty
            remaining_time = getattr(grenade.ndb, NDB_COUNTDOWN_REMAINING, 0)
            base_difficulty = 15  # Base difficulty
            time_pressure = max(0, 10 - remaining_time)  # Gets harder as time runs out
            total_difficulty = base_difficulty + time_pressure

        # Get character stats (fallback to 1 if not found)
        intellect = getattr(self.caller, 'intellect', 1)
        motorics = getattr(self.caller, 'motorics', 1)

        # Roll Intellect + Motorics (using existing roll pattern)
        from world.combat.utils import roll_stat

        # Simulate combined stat roll (would need proper implementation)
        intellect_roll = roll_stat(self.caller, 'intellect')
        motorics_roll = roll_stat(self.caller, 'motorics')
        combined_roll = intellect_roll + motorics_roll

        # Determine success
        success = combined_roll >= total_difficulty

        # Announce attempt (different message for rigged vs live)
        if is_rigged:
            self.caller.msg(f"You carefully examine the rigged {grenade.key} and attempt to disarm the trap...")
            self.caller.location.msg_contents(
                f"{self.caller.key} carefully works on disarming the rigged {grenade.key}.",
                exclude=self.caller
            )
        else:
            self.caller.msg(f"You carefully examine the live {grenade.key} and attempt to defuse it...")
            self.caller.location.msg_contents(
                f"{self.caller.key} carefully works on defusing the {grenade.key}.",
                exclude=self.caller
            )

        # Debug output
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        if splattercast:
            grenade_type = "rigged" if is_rigged else "live"
            splattercast.msg(f"DEFUSE: {self.caller.key} rolled {combined_roll} vs difficulty {total_difficulty} "
                           f"(base {base_difficulty} + pressure {time_pressure}, {remaining_time}s left, {grenade_type}) - "
                           f"{'SUCCESS' if success else 'FAILURE'}")

        if success:
            self.handle_defuse_success(grenade)
        else:
            self.handle_defuse_failure(grenade)

    def handle_defuse_success(self, grenade):
        """Handle successful defuse attempt."""
        # Cancel countdown timer if active
        timer = getattr(grenade.ndb, NDB_GRENADE_TIMER, None)
        if timer:
            timer.cancel()
            delattr(grenade.ndb, NDB_GRENADE_TIMER)

        # Clear countdown state
        setattr(grenade.ndb, NDB_COUNTDOWN_REMAINING, 0)
        grenade.db.pin_pulled = False  # Grenade is now safe

        # Clean up rigging if this was a rigged grenade
        self.cleanup_rigging(grenade)

        # Clear proximity relationships (grenade is now safe)
        self.clear_grenade_proximity(grenade)

        # Success messages
        self.caller.msg(f"SUCCESS! You successfully defuse the {grenade.key}. It is now safe.")
        self.caller.location.msg_contents(
            f"{self.caller.key} successfully defuses the {grenade.key}!",
            exclude=self.caller
        )

        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        if splattercast:
            splattercast.msg(f"DEFUSE_SUCCESS: {self.caller.key} defused {grenade.key}")

    def clear_grenade_proximity(self, grenade):
        """Clear all proximity relationships for a defused grenade."""
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)

        # Get grenade's proximity list
        grenade_proximity = getattr(grenade.ndb, NDB_PROXIMITY_UNIVERSAL, [])
        if not isinstance(grenade_proximity, list):
            return

        # Remove grenade from all characters' proximity lists
        for character in list(grenade_proximity):
            if hasattr(character, 'ndb'):
                char_proximity = getattr(character.ndb, NDB_PROXIMITY_UNIVERSAL, [])
                if isinstance(char_proximity, list) and grenade in char_proximity:
                    char_proximity.remove(grenade)
                    if splattercast:
                        splattercast.msg(f"DEFUSE_PROXIMITY_CLEAR: Removed {grenade.key} from {character.key}'s proximity")

        # Clear grenade's proximity list
        setattr(grenade.ndb, NDB_PROXIMITY_UNIVERSAL, [])

        if splattercast:
            splattercast.msg(f"DEFUSE_PROXIMITY_CLEAR: Cleared all proximity for defused {grenade.key}")

    def cleanup_rigging(self, grenade):
        """Clean up rigging references when grenade is defused."""
        rigged_to_exit = grenade.db.rigged_to_exit
        if rigged_to_exit:
            splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)

            # Clean up main exit
            if rigged_to_exit.db.rigged_grenade is not None:
                rigged_to_exit.db.rigged_grenade = None
                if splattercast:
                    splattercast.msg(f"DEFUSE_CLEANUP: Removed rigging from {rigged_to_exit}")

            # Find and clean up return exit
            if rigged_to_exit.destination:
                destination_room = rigged_to_exit.destination
                grenade_room = grenade.location if hasattr(grenade, 'location') else self.caller.location

                for obj in destination_room.contents:
                    if (hasattr(obj, 'destination') and
                        obj.destination == grenade_room and
                        obj.db.rigged_grenade is not None and
                        obj.db.rigged_grenade == grenade):
                        obj.db.rigged_grenade = None
                        if splattercast:
                            splattercast.msg(f"DEFUSE_CLEANUP: Removed rigging from return exit {obj}")
                        break

            # Clean up grenade's rigging reference
            grenade.db.rigged_to_exit = None
            if grenade.db.rigged_by is not None:
                grenade.db.rigged_by = None

            # Restore original integration state
            if grenade.db.original_integrate is not None:
                grenade.db.integrate = grenade.db.original_integrate
                grenade.db.original_integrate = None
            else:
                # Default: disable integration for regular grenades
                grenade.db.integrate = False

            if grenade.db.original_integration_desc is not None:
                grenade.db.integration_desc = grenade.db.original_integration_desc
                grenade.db.original_integration_desc = None
            else:
                # Remove integration_desc if it wasn't set originally
                grenade.db.integration_desc = None

            if grenade.db.original_integration_priority is not None:
                grenade.db.integration_priority = grenade.db.original_integration_priority
                grenade.db.original_integration_priority = None
            else:
                # Remove integration_priority if it wasn't set originally
                grenade.db.integration_priority = None

            # Announce trap disarmament
            self.caller.msg("You also disarm the trap rigging mechanism.")
            self.caller.location.msg_contents(
                f"{self.caller.key} disarms the trap rigging on the {grenade.key}.",
                exclude=self.caller
            )

            if splattercast:
                splattercast.msg(f"DEFUSE_CLEANUP: Fully cleaned up rigging for {grenade.key}")

    def handle_defuse_failure(self, grenade):
        """Handle failed defuse attempt with potential early detonation."""
        # 30% chance of early detonation on failure
        early_detonation_chance = 0.3

        if random.random() < early_detonation_chance:
            # Early detonation triggered
            self.caller.msg(f"FAILURE! Your clumsy attempt triggers the {grenade.key} early!")
            self.caller.location.msg_contents(
                f"{self.caller.key}'s failed defuse attempt triggers the {grenade.key}!",
                exclude=self.caller
            )

            # Trigger immediate explosion (reuse existing explosion logic)
            timer = getattr(grenade.ndb, NDB_GRENADE_TIMER, None)
            if timer:
                timer.cancel()

            # Set very short timer for dramatic effect
            setattr(grenade.ndb, NDB_COUNTDOWN_REMAINING, 1)
            utils.delay(1, self.trigger_early_explosion, grenade)

            splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
            if splattercast:
                splattercast.msg(f"DEFUSE_FAILURE: {self.caller.key} triggered early detonation of {grenade.key}")

        else:
            # Failed but no early detonation
            self.caller.msg(f"FAILURE! You fail to defuse the {grenade.key}, but it continues ticking...")
            self.caller.location.msg_contents(
                f"{self.caller.key} fails to defuse the {grenade.key}.",
                exclude=self.caller
            )

            splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
            if splattercast:
                splattercast.msg(f"DEFUSE_FAILURE: {self.caller.key} failed to defuse {grenade.key} (no early detonation)")

    def trigger_early_explosion(self, grenade):
        """Trigger early explosion from failed defuse attempt."""
        # Reuse the explosion logic from CmdPull
        # Note: Using character.take_damage() for medical system integration

        try:
            # Check dud chance
            dud_chance = grenade.db.dud_chance if grenade.db.dud_chance is not None else 0.0
            if random.random() < dud_chance:
                if grenade.location:
                    grenade.location.msg_contents(MSG_GRENADE_DUD_ROOM.format(grenade=grenade.key))
                return

            # Get blast damage
            blast_damage = grenade.db.blast_damage if grenade.db.blast_damage is not None else 10

            # Room explosion
            if grenade.location:
                grenade.location.msg_contents(MSG_GRENADE_EXPLODE_ROOM.format(grenade=grenade.key))
                # Notify adjacent rooms
                notify_adjacent_rooms_of_explosion(grenade.location)

            # Get unified proximity list (includes current grappling relationships)
            proximity_list = get_unified_explosion_proximity(grenade)

            # Check for human shield mechanics
            from world.combat.utils import check_grenade_human_shield
            damage_modifiers = check_grenade_human_shield(proximity_list)

            # Apply damage to all in proximity with human shield modifiers
            for character in proximity_list:
                if hasattr(character, 'msg'):  # Is a character
                    # Apply damage modifier (0.0 for grapplers, 2.0 for victims, 1.0 for others)
                    modifier = damage_modifiers.get(character, 1.0)
                    final_damage = int(blast_damage * modifier)

                    if final_damage > 0:
                        damage_type = grenade.db.damage_type if grenade.db.damage_type is not None else 'blast'
                        character.take_damage(final_damage, location="chest", injury_type=damage_type)
                        character.msg(MSG_GRENADE_DAMAGE.format(grenade=grenade.key))
                        if character.location:
                            character.location.msg_contents(
                                MSG_GRENADE_DAMAGE_ROOM.format(victim=character.key, grenade=grenade.key),
                                exclude=character
                            )
                    # Note: Characters with 0.0 modifier (grapplers) take no damage and get no damage messages

            # Handle chain reactions if enabled
            if grenade.db.chain_trigger:
                for obj in proximity_list:
                    if (hasattr(obj, 'db') and
                        obj.db.is_explosive and
                        obj != grenade):

                        # Trigger chain explosion
                        if grenade.location:
                            grenade.location.msg_contents(
                                MSG_GRENADE_CHAIN_TRIGGER.format(grenade=obj.key))

                        # Start immediate explosion timer
                        utils.delay(0.5, self.trigger_early_explosion, obj)

            # Clean up
            grenade.delete()

        except Exception as e:
            splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_ERROR: Error in trigger_early_explosion: {e}")


# =============================================================================
# REMOTE DETONATOR COMMANDS
# =============================================================================

class CmdScan(Command):
    """
    Scan an explosive device with a remote detonator.

    Usage:
        scan <explosive> with <detonator>

    Examples:
        scan grenade with detonator
        scan spdr with remote

    Scans an explosive device into the detonator's memory for remote detonation.
    The detonator can store up to 20 explosive signatures. Each explosive can
    only be scanned by one detonator at a time - scanning with a new detonator
    will override the previous link.

    You must be wielding or holding the detonator to use it.
    """

    key = "scan"
    locks = "cmd:all()"
    help_category = "Combat"

    def func(self):
        caller = self.caller

        # Parse arguments
        if not self.args or " with " not in self.args:
            caller.msg("Usage: scan <explosive> with <detonator>")
            return

        parts = self.args.split(" with ", 1)
        if len(parts) != 2:
            caller.msg("Usage: scan <explosive> with <detonator>")
            return

        explosive_name = parts[0].strip()
        detonator_name = parts[1].strip()

        # Find explosive
        explosive = caller.search(explosive_name, location=caller)
        if not explosive:
            return

        # Validate explosive
        if not explosive.db.is_explosive:
            caller.msg(f"{explosive.key} is not an explosive device.")
            return

        # Find detonator
        detonator = caller.search(detonator_name, location=caller)
        if not detonator:
            return

        # Validate detonator type
        if not detonator.db.device_type or detonator.db.device_type != "remote_detonator":
            caller.msg(f"{detonator.key} is not a remote detonator.")
            return

        # Check if detonator is wielded/held
        if not hasattr(caller, 'hands') or not caller.hands:
            caller.msg("You need hands to use a detonator.")
            return

        is_wielded = any(held_item == detonator for held_item in caller.hands.values() if held_item)
        if not is_wielded:
            caller.msg(f"You must be wielding or holding {detonator.key} to use it.")
            return

        # Add explosive to detonator
        success, message = detonator.add_explosive(explosive)

        if success:
            # Success messaging
            caller.msg(f"|gYou scan {explosive.key} into {detonator.key}'s memory.|n")
            caller.msg(f"  Signature: e-{explosive.id}")
            caller.msg(f"  Capacity: {len(detonator.db.scanned_explosives)}/{detonator.db.max_capacity}")

            # Room messaging
            caller.location.msg_contents(
                f"{caller.key} points a device at {explosive.key}, which emits a soft beep.",
                exclude=[caller]
            )

            # Debug logging
            splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
            splattercast.msg(
                f"DETONATOR_SCAN: {caller.key} scanned e-{explosive.id} ({explosive.key}) "
                f"into detonator #{detonator.id}. Capacity: {len(detonator.db.scanned_explosives)}/{detonator.db.max_capacity}"
            )
        else:
            # Failure messaging
            caller.msg(f"|r{message}|n")


class CmdDetonate(Command):
    """
    Remotely detonate scanned explosives.

    Usage:
        detonate e-<dbref> with <detonator>
        detonate all with <detonator>

    Examples:
        detonate e-1234 with remote
        detonate all with detonator

    Remotely detonates scanned explosives by pulling their pins and starting
    their normal fuse countdowns. Each explosive type behaves as it normally
    would (sticky grenades seek/stick, rigged explosives use 1s fuse, etc.).

    Detonating "all" triggers every scanned explosive simultaneously with
    staggered countdowns based on their individual fuse times.

    You must be wielding or holding the detonator to use it.
    """

    key = "detonate"
    locks = "cmd:all()"
    help_category = "Combat"

    def func(self):
        caller = self.caller

        # Parse arguments
        if not self.args or " with " not in self.args:
            caller.msg("Usage: detonate e-<dbref> with <detonator> OR detonate all with <detonator>")
            return

        parts = self.args.split(" with ", 1)
        if len(parts) != 2:
            caller.msg("Usage: detonate e-<dbref> with <detonator> OR detonate all with <detonator>")
            return

        target_str = parts[0].strip()
        detonator_name = parts[1].strip()

        # Find detonator
        detonator = caller.search(detonator_name, location=caller)
        if not detonator:
            return

        # Validate detonator type
        if not detonator.db.device_type or detonator.db.device_type != "remote_detonator":
            caller.msg(f"{detonator.key} is not a remote detonator.")
            return

        # Check if detonator is wielded/held
        if not hasattr(caller, 'hands') or not caller.hands:
            caller.msg("You need hands to use a detonator.")
            return

        is_wielded = any(held_item == detonator for held_item in caller.hands.values() if held_item)
        if not is_wielded:
            caller.msg(f"You must be wielding or holding {detonator.key} to use it.")
            return

        # Check for empty list
        if not detonator.db.scanned_explosives:
            caller.msg(f"{detonator.key} has no scanned explosives.")
            return

        # Handle "all" detonation
        if target_str.lower() == "all":
            self.detonate_all(caller, detonator)
        # Handle single detonation
        elif target_str.startswith("e-"):
            try:
                explosive_dbref = int(target_str[2:])
                self.detonate_single(caller, detonator, explosive_dbref)
            except ValueError:
                caller.msg(f"Invalid explosive ID: {target_str}")
        else:
            caller.msg("Usage: detonate e-<dbref> with <detonator> OR detonate all with <detonator>")

    def detonate_single(self, caller, detonator, explosive_dbref):
        """Detonate a single explosive."""
        # Validate detonator has this explosive
        if explosive_dbref not in detonator.db.scanned_explosives:
            caller.msg(f"e-{explosive_dbref} is not in {detonator.key}'s memory.")
            return

        # Get explosive object
        from evennia.utils.search import search_object
        explosive = search_object(f"#{explosive_dbref}")

        if not explosive or len(explosive) == 0:
            caller.msg(f"|ye-{explosive_dbref} no longer exists.|n")
            # Auto-cleanup invalid explosive
            detonator.db.scanned_explosives.remove(explosive_dbref)
            return

        explosive = explosive[0]

        # Check if already detonating
        if explosive.db.pin_pulled:
            caller.msg(f"|y{explosive.key} is already detonating!|n")
            return

        # Pull the pin remotely
        explosive.db.pin_pulled = True
        fuse_time = explosive.db.fuse_time if explosive.db.fuse_time is not None else 8
        setattr(explosive.ndb, NDB_COUNTDOWN_REMAINING, fuse_time)

        # Start countdown using CmdPull's grenade ticker system
        # Create temporary CmdPull instance to access start_grenade_ticker
        from commands.CmdThrow import CmdPull
        pull_cmd = CmdPull()
        pull_cmd.caller = caller
        pull_cmd.start_grenade_ticker(explosive)

        # Operator messaging
        caller.msg(
            f"|rYou flip open the red safety cover on {detonator.key} and press the large button. "
            f"A distant beep echoes!|n"
        )

        # Operator's room messaging (button press)
        caller.location.msg_contents(
            f"{caller.key} flips open a red safety cover on their {detonator.key} and presses a large button.",
            exclude=[caller]
        )

        # Grenade's location messaging (activation)
        if explosive.location and explosive.location != caller.location:
            # Cross-room - grenade location sees activation
            explosive.location.msg_contents(
                f"|rAn {explosive.key} beeps and its light begins flashing!|n |y[{fuse_time} seconds]|n"
            )
        elif explosive.location == caller.location:
            # Same room - show activation to everyone
            caller.location.msg_contents(
                f"|rAn {explosive.key} beeps and its light begins flashing!|n |y[{fuse_time} seconds]|n",
                exclude=[caller]
            )
            caller.msg(f"|rThe {explosive.key} beeps and its light begins flashing!|n |y[{fuse_time} seconds]|n")

        # Debug logging
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        splattercast.msg(
            f"DETONATOR_SINGLE: {caller.key} remotely detonated e-{explosive_dbref} ({explosive.key}) "
            f"via detonator #{detonator.id}. Fuse: {fuse_time}s"
        )

    def detonate_all(self, caller, detonator):
        """Detonate all scanned explosives."""
        # Validate and clean list
        detonator.validate_scanned_list()

        if not detonator.db.scanned_explosives:
            caller.msg(f"{detonator.key} has no valid explosives to detonate.")
            return

        from evennia.utils.search import search_object

        detonated_count = 0
        already_active_count = 0

        # Track locations for messaging
        activation_locations = {}  # location: [explosive_names]

        for explosive_dbref in list(detonator.db.scanned_explosives):
            explosive = search_object(f"#{explosive_dbref}")
            if not explosive or len(explosive) == 0:
                continue

            explosive = explosive[0]

            # Skip if already detonating
            if explosive.db.pin_pulled:
                already_active_count += 1
                continue

            # Pull the pin remotely
            explosive.db.pin_pulled = True
            fuse_time = explosive.db.fuse_time if explosive.db.fuse_time is not None else 8
            setattr(explosive.ndb, NDB_COUNTDOWN_REMAINING, fuse_time)

            # Start countdown
            from commands.CmdThrow import CmdPull
            pull_cmd = CmdPull()
            pull_cmd.caller = caller
            pull_cmd.start_grenade_ticker(explosive)

            detonated_count += 1

            # Track for location messaging
            if explosive.location:
                if explosive.location not in activation_locations:
                    activation_locations[explosive.location] = []
                activation_locations[explosive.location].append((explosive.key, fuse_time))

        if detonated_count == 0:
            if already_active_count > 0:
                caller.msg(f"|yAll scanned explosives are already detonating.|n")
            else:
                caller.msg(f"|yNo valid explosives to detonate.|n")
            return

        # Operator messaging
        caller.msg(
            f"|rYou flip open the red safety cover on {detonator.key} and press the large button. "
            f"Multiple distant beeps echo from various locations!|n"
        )
        caller.msg(f"|gDetonated {detonated_count} explosive(s).|n")

        # Operator's room messaging
        caller.location.msg_contents(
            f"{caller.key} flips open a red safety cover on their {detonator.key} and presses a large button. "
            f"Multiple distant beeps echo from various locations!",
            exclude=[caller]
        )

        # Send activation messages to each location
        for location, explosives_list in activation_locations.items():
            if location == caller.location:
                # Same room - show to everyone including operator
                for exp_name, fuse in explosives_list:
                    location.msg_contents(
                        f"|rAn {exp_name} beeps and its light begins flashing!|n |y[{fuse} seconds]|n"
                    )
            else:
                # Different room - just show activation
                for exp_name, fuse in explosives_list:
                    location.msg_contents(
                        f"|rAn {exp_name} beeps and its light begins flashing!|n |y[{fuse} seconds]|n"
                    )

        # Debug logging
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        splattercast.msg(
            f"DETONATOR_ALL: {caller.key} remotely detonated {detonated_count} explosives "
            f"via detonator #{detonator.id}. Already active: {already_active_count}"
        )


class CmdDetonateList(Command):
    """
    List scanned explosives in remote detonator.

    Usage:
        detonate list with <detonator>
        detonator list (if wielded)

    Examples:
        detonate list with remote
        detonator list

    Displays a table of all scanned explosives showing their ID, type, status,
    fuse time, and current location. Automatically validates and removes invalid
    explosives from the list.

    You must be wielding or holding the detonator to use it.
    """

    key = "detonate list"
    aliases = ["detonator list"]
    locks = "cmd:all()"
    help_category = "Combat"

    def func(self):
        caller = self.caller

        # Parse arguments - handle both syntaxes
        detonator = None

        if self.cmdstring == "detonator list":
            # Find wielded detonator
            if hasattr(caller, 'hands') and caller.hands:
                for held_item in caller.hands.values():
                    if (held_item and held_item.db.device_type and
                        held_item.db.device_type == "remote_detonator"):
                        detonator = held_item
                        break

            if not detonator:
                caller.msg("You must be wielding a remote detonator to use this command.")
                return
        else:
            # Parse "detonate list with <detonator>"
            if not self.args or " with " not in self.args:
                caller.msg("Usage: detonate list with <detonator>")
                return

            parts = self.args.split(" with ", 1)
            if len(parts) != 2:
                caller.msg("Usage: detonate list with <detonator>")
                return

            detonator_name = parts[1].strip()
            detonator = caller.search(detonator_name, location=caller)
            if not detonator:
                return

        # Validate detonator type
        if not detonator.db.device_type or detonator.db.device_type != "remote_detonator":
            caller.msg(f"{detonator.key} is not a remote detonator.")
            return

        # Check if detonator is wielded/held
        if not hasattr(caller, 'hands') or not caller.hands:
            caller.msg("You need hands to use a detonator.")
            return

        is_wielded = any(held_item == detonator for held_item in caller.hands.values() if held_item)
        if not is_wielded:
            caller.msg(f"You must be wielding or holding {detonator.key} to use it.")
            return

        # Validate list
        detonator.validate_scanned_list()

        if not detonator.db.scanned_explosives:
            caller.msg(f"{detonator.key} has no scanned explosives.")
            return

        # Build table
        from evennia.utils.evtable import EvTable
        from evennia.utils.search import search_object

        table = EvTable(
            "|wID|n", "|wDevice|n", "|wStatus|n", "|wFuse|n", "|wLocation|n",
            border="cells",
            width=78
        )

        for explosive_dbref in detonator.db.scanned_explosives:
            explosive = search_object(f"#{explosive_dbref}")
            if not explosive or len(explosive) == 0:
                continue

            explosive = explosive[0]

            # Get status
            if explosive.db.pin_pulled:
                countdown = getattr(explosive.ndb, NDB_COUNTDOWN_REMAINING, 0)
                if explosive.db.stuck_to_armor is not None:
                    status = f"|RSTUCK|n"
                else:
                    status = f"|YACTIVE|n"
                fuse_str = f"|R{countdown}s left!|n"
            elif explosive.db.rigged_to_exit is not None:
                status = f"|yTRAP|n"
                fuse_time = explosive.db.fuse_time if explosive.db.fuse_time is not None else 8
                fuse_str = f"{fuse_time}s (trap)"
            else:
                status = f"|gREADY|n"
                fuse_time = explosive.db.fuse_time if explosive.db.fuse_time is not None else 8
                fuse_str = f"{fuse_time}s"

            # Get location
            if not explosive.location:
                loc_str = "|xVoid|n"
            elif explosive.location == caller:
                loc_str = "Your inventory"
            elif hasattr(explosive.location, 'key'):
                # Check if stuck to armor
                if explosive.db.stuck_to_armor is not None:
                    stuck_to = explosive.db.stuck_to_armor
                    if hasattr(stuck_to, 'location') and hasattr(stuck_to.location, 'key'):
                        loc_str = f"On {stuck_to.location.key}"
                    else:
                        loc_str = "Stuck to armor"
                else:
                    loc_str = explosive.location.key
            else:
                loc_str = "|xUnknown|n"

            table.add_row(
                f"e-{explosive_dbref}",
                explosive.key[:18],  # Truncate long names
                status,
                fuse_str,
                loc_str[:16]  # Truncate long location names
            )

        # Display
        caller.msg(f"\n|w{'='*78}|n")
        caller.msg(f"|w  REMOTE DETONATOR - SCANNED DEVICES|n")
        caller.msg(f"|w  Capacity: {len(detonator.db.scanned_explosives)}/{detonator.db.max_capacity}|n")
        caller.msg(f"|w{'='*78}|n")
        caller.msg(str(table))
        caller.msg(f"|w{'='*78}|n")
        caller.msg("\nStatus Legend:")
        caller.msg("  |gREADY|n  - Armed and ready for remote detonation")
        caller.msg("  |YACTIVE|n - Currently counting down (pin already pulled)")
        caller.msg("  |RSTUCK|n  - Sticky grenade adhered to target")
        caller.msg("  |yTRAP|n   - Rigged explosive waiting for trigger")


class CmdClearDetonator(Command):
    """
    Clear explosives from remote detonator memory.

    Usage:
        clear e-<dbref> from <detonator>
        clear all from <detonator>
        detonator clear (if wielded)

    Examples:
        clear e-1234 from remote
        clear all from detonator
        detonator clear

    Removes explosive signatures from the detonator's memory, breaking the
    bidirectional link. Cleared explosives can no longer be remotely detonated
    until they are scanned again.

    You must be wielding or holding the detonator to use it.
    """

    key = "clear"
    aliases = ["detonator clear"]
    locks = "cmd:all()"
    help_category = "Combat"

    def func(self):
        caller = self.caller

        # Handle "detonator clear" syntax
        if self.cmdstring == "detonator clear":
            # Find wielded detonator and clear all
            if not hasattr(caller, 'hands') or not caller.hands:
                caller.msg("You need hands to use a detonator.")
                return

            detonator = None
            for held_item in caller.hands.values():
                if (held_item and held_item.db.device_type and
                    held_item.db.device_type == "remote_detonator"):
                    detonator = held_item
                    break

            if not detonator:
                caller.msg("You must be wielding a remote detonator to use this command.")
                return

            self.clear_all(caller, detonator)
            return

        # Parse "clear <target> from <detonator>" syntax
        if not self.args or " from " not in self.args:
            caller.msg("Usage: clear e-<dbref> from <detonator> OR clear all from <detonator>")
            return

        parts = self.args.split(" from ", 1)
        if len(parts) != 2:
            caller.msg("Usage: clear e-<dbref> from <detonator> OR clear all from <detonator>")
            return

        target_str = parts[0].strip()
        detonator_name = parts[1].strip()

        # Find detonator
        detonator = caller.search(detonator_name, location=caller)
        if not detonator:
            return

        # Validate detonator type
        if not detonator.db.device_type or detonator.db.device_type != "remote_detonator":
            caller.msg(f"{detonator.key} is not a remote detonator.")
            return

        # Check if detonator is wielded/held
        if not hasattr(caller, 'hands') or not caller.hands:
            caller.msg("You need hands to use a detonator.")
            return

        is_wielded = any(held_item == detonator for held_item in caller.hands.values() if held_item)
        if not is_wielded:
            caller.msg(f"You must be wielding or holding {detonator.key} to use it.")
            return

        # Handle "all" clear
        if target_str.lower() == "all":
            self.clear_all(caller, detonator)
        # Handle single clear
        elif target_str.startswith("e-"):
            try:
                explosive_dbref = int(target_str[2:])
                self.clear_single(caller, detonator, explosive_dbref)
            except ValueError:
                caller.msg(f"Invalid explosive ID: {target_str}")
        else:
            caller.msg("Usage: clear e-<dbref> from <detonator> OR clear all from <detonator>")

    def clear_single(self, caller, detonator, explosive_dbref):
        """Clear a single explosive from detonator."""
        # Check if explosive is in list
        if explosive_dbref not in detonator.db.scanned_explosives:
            caller.msg(f"e-{explosive_dbref} is not in {detonator.key}'s memory.")
            return

        # Get explosive name if it still exists
        from evennia.utils.search import search_object
        explosive = search_object(f"#{explosive_dbref}")
        explosive_name = explosive[0].key if explosive and len(explosive) > 0 else f"e-{explosive_dbref}"

        # Remove from detonator
        success = detonator.remove_explosive(explosive_dbref)

        if success:
            caller.msg(f"|gYou clear e-{explosive_dbref} ({explosive_name}) from {detonator.key}'s memory.|n")

            # Room messaging
            caller.location.msg_contents(
                f"{caller.key} presses several buttons on their {detonator.key}.",
                exclude=[caller]
            )

            # Debug logging
            splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
            splattercast.msg(
                f"DETONATOR_CLEAR_SINGLE: {caller.key} cleared e-{explosive_dbref} from detonator #{detonator.id}"
            )
        else:
            caller.msg(f"|rFailed to clear e-{explosive_dbref} from {detonator.key}.|n")

    def clear_all(self, caller, detonator):
        """Clear all explosives from detonator."""
        if not detonator.db.scanned_explosives:
            caller.msg(f"{detonator.key} has no scanned explosives to clear.")
            return

        count = len(detonator.db.scanned_explosives)

        # Clear bidirectional references
        from evennia.utils.search import search_object
        for explosive_dbref in list(detonator.db.scanned_explosives):
            explosive = search_object(f"#{explosive_dbref}")
            if explosive and len(explosive) > 0:
                explosive_obj = explosive[0]
                if explosive_obj.db.scanned_by_detonator is not None:
                    explosive_obj.db.scanned_by_detonator = None

        # Clear detonator list
        detonator.db.scanned_explosives = []

        caller.msg(f"|gYou clear all {count} explosive signature(s) from {detonator.key}'s memory.|n")

        # Room messaging
        caller.location.msg_contents(
            f"{caller.key} holds down a button on their {detonator.key}, which emits a series of beeps before going silent.",
            exclude=[caller]
        )

        # Debug logging
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        splattercast.msg(
            f"DETONATOR_CLEAR_ALL: {caller.key} cleared {count} explosives from detonator #{detonator.id}"
        )
