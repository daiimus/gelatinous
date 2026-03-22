"""
Explosion Utility Functions

Shared explosion mechanics used by multiple systems including:
- Rigged grenade checks on room entry
- Auto-defuse pipeline for live grenades
- Standalone grenade explosion resolution
- Countdown ticker system
- Explosion proximity merging
- Adjacent room notifications

These functions were extracted from CmdThrow.py to reduce its size
and make the explosion pipeline reusable without importing the full
throw command module.

Part of the G.R.I.M. Combat System.
"""

import random
from evennia import utils
from evennia.comms.models import ChannelDB
from world.combat.constants import (
    DEBUG_PREFIX_THROW,
    NDB_PROXIMITY_UNIVERSAL,
    NDB_PROXIMITY,
    NDB_COUNTDOWN_REMAINING,
    NDB_GRENADE_TIMER,
    NDB_COMBAT_HANDLER,
    DB_CHAR,
    DB_GRAPPLED_BY_DBREF,
    DB_GRAPPLING_DBREF,
    SPLATTERCAST_CHANNEL,
    MSG_GRENADE_EXPLODE_ROOM,
    MSG_GRENADE_EXPLODE_ADJACENT,
    MSG_GRENADE_DAMAGE,
    MSG_GRENADE_DAMAGE_ROOM,
    MSG_GRENADE_DUD_ROOM,
    MSG_GRENADE_CHAIN_TRIGGER,
    MSG_RIG_TRIGGERED,
    MSG_RIG_TRIGGERED_ROOM,
)


def notify_adjacent_rooms_of_explosion(explosion_room):
    """Send explosion sound notifications to all adjacent rooms."""
    if not explosion_room:
        return

    # Get all exits from the explosion room
    exits = explosion_room.exits

    for exit_obj in exits:
        # Get the destination room
        destination = exit_obj.destination
        if destination and destination != explosion_room:
            # Find the reverse direction for the message
            # Check if there's a return exit to determine direction
            return_exits = destination.exits
            direction = None

            for return_exit in return_exits:
                if return_exit.destination == explosion_room:
                    direction = return_exit.key
                    break

            # If no return exit found, use the original exit's opposite direction
            if not direction:
                # Simple direction mapping
                direction_map = {
                    'north': 'south', 'south': 'north',
                    'east': 'west', 'west': 'east',
                    'up': 'down', 'down': 'up',
                    'northeast': 'southwest', 'southwest': 'northeast',
                    'northwest': 'southeast', 'southeast': 'northwest'
                }
                direction = direction_map.get(exit_obj.key, exit_obj.key)

            # Send the message to the adjacent room
            destination.msg_contents(MSG_GRENADE_EXPLODE_ADJACENT.format(direction=direction))


def check_rigged_grenade(character, exit_obj):
    """Check if character triggers a rigged grenade. Character should already be at destination."""
    # Initialize Splattercast for debug logging
    splattercast = ChannelDB.objects.get_channel("Splattercast")

    # Check if there's a rigged grenade on this exit
    rigged_grenade = exit_obj.db.rigged_grenade

    if not rigged_grenade:
        return False

    # Check if this character is the rigger (immunity)
    rigger = rigged_grenade.db.rigged_by

    if rigger and character == rigger:
        return False  # Rigger is immune to their own trap

    # Trigger the rigged grenade
    character.msg(MSG_RIG_TRIGGERED.format(object=rigged_grenade.key))
    character.location.msg_contents(
        MSG_RIG_TRIGGERED_ROOM.format(object=rigged_grenade.key, victim=character.key),
        exclude=character
    )

    # Pull the pin and start countdown timer when triggered
    rigged_grenade.db.pin_pulled = True
    fuse_time = 1  # Rigged grenades explode almost immediately
    setattr(rigged_grenade.ndb, NDB_COUNTDOWN_REMAINING, fuse_time)

    # Move grenade to the character's location quietly (no movement announcements)
    rigged_grenade.move_to(character.location, quiet=True)

    # FOR STICKY GRENADES: Find most magnetic target and attempt to stick
    # FOR REGULAR GRENADES: Just establish proximity with trigger character
    is_sticky = bool(rigged_grenade.db.is_sticky)
    sticky_target = None

    if is_sticky:
        # Use CmdThrow's magnetic targeting logic (lazy import to avoid circular)
        from commands.CmdThrow import CmdThrow
        cmd = CmdThrow()
        cmd.caller = character  # Set caller for context
        sticky_target = cmd.select_most_magnetic_target_in_room(character.location, rigged_grenade)

        if sticky_target:
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_RIGGED_STICKY: Selected {sticky_target.key} as magnetic target")
            # Use existing resolve_weapon_hit logic to handle stick attempt
            cmd.resolve_weapon_hit(rigged_grenade, sticky_target, character)
        else:
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_RIGGED_STICKY: No viable magnetic targets, treating as regular grenade")

    # Establish proximity for auto-defuse system (rigged grenades need this!)
    proximity_list = getattr(rigged_grenade.ndb, NDB_PROXIMITY_UNIVERSAL, None)
    if not proximity_list:
        setattr(rigged_grenade.ndb, NDB_PROXIMITY_UNIVERSAL, [])
        proximity_list = getattr(rigged_grenade.ndb, NDB_PROXIMITY_UNIVERSAL)

    # For sticky grenades that stuck: proximity is whoever it stuck to
    # For regular grenades or failed sticks: proximity is the trigger character
    if is_sticky and sticky_target:
        # Sticky grenade dictates its own proximity via establish_stick()
        # Just verify the target is in the list
        if sticky_target not in proximity_list:
            proximity_list.append(sticky_target)
    else:
        # Regular grenade - add trigger character
        if character not in proximity_list:
            proximity_list.append(character)

    splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
    splattercast.msg(f"{DEBUG_PREFIX_THROW}_RIGGED: Established proximity for {rigged_grenade.key}: {[char.key for char in proximity_list]}")

    # Start countdown timer
    # Create a closure to handle explosion
    def explode_rigged_grenade():
        """Handle rigged grenade explosion after timer."""
        try:
            # Check dud chance
            dud_chance = rigged_grenade.db.dud_chance if rigged_grenade.db.dud_chance is not None else 0.0
            if random.random() < dud_chance:
                if rigged_grenade.location:
                    rigged_grenade.location.msg_contents(MSG_GRENADE_DUD_ROOM.format(grenade=rigged_grenade.key))
                return

            # Get blast damage
            blast_damage = rigged_grenade.db.blast_damage if rigged_grenade.db.blast_damage is not None else 10

            # Room explosion
            if rigged_grenade.location:
                rigged_grenade.location.msg_contents(MSG_GRENADE_EXPLODE_ROOM.format(grenade=rigged_grenade.key))
                # Notify adjacent rooms
                notify_adjacent_rooms_of_explosion(rigged_grenade.location)

            # Get unified proximity list (includes current grappling relationships)
            proximity_list = get_unified_explosion_proximity(rigged_grenade)

            # Check for human shield mechanics
            from world.combat.utils import check_grenade_human_shield
            damage_modifiers = check_grenade_human_shield(proximity_list)

            # Apply damage to all in proximity (trigger character only if they're in proximity)
            for other_character in proximity_list:
                if hasattr(other_character, 'msg'):
                    # Apply damage modifier (0.0 for grapplers, 2.0 for victims, 1.0 for others)
                    modifier = damage_modifiers.get(other_character, 1.0)
                    final_damage = int(blast_damage * modifier)

                    if final_damage > 0:
                        damage_type = rigged_grenade.db.damage_type if rigged_grenade.db.damage_type is not None else 'blast'
                        other_character.take_damage(final_damage, location="chest", injury_type=damage_type)
                        other_character.msg(MSG_GRENADE_DAMAGE.format(grenade=rigged_grenade.key))
                        if other_character.location:
                            other_character.location.msg_contents(
                                MSG_GRENADE_DAMAGE_ROOM.format(victim=other_character.key, grenade=rigged_grenade.key),
                                exclude=other_character
                            )
                    # Note: Characters with 0.0 modifier (grapplers) take no damage and get no damage messages

            # Handle chain reactions if enabled
            if rigged_grenade.db.chain_trigger:
                for obj in proximity_list:
                    if (hasattr(obj, 'db') and
                        obj.db.is_explosive and
                        obj != rigged_grenade):

                        # Trigger chain explosion
                        if rigged_grenade.location:
                            rigged_grenade.location.msg_contents(
                                MSG_GRENADE_CHAIN_TRIGGER.format(grenade=obj.key))

                        # Start immediate explosion timer with new ticker system
                        obj.db.pin_pulled = True
                        setattr(obj.ndb, NDB_COUNTDOWN_REMAINING, 1)
                        start_standalone_grenade_ticker(obj)

            # Delete the rigged grenade
            rigged_grenade.delete()

        except Exception as e:
            splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_ERROR: Error in explode_rigged_grenade: {e}")

    # Start the timer
    start_standalone_grenade_ticker(rigged_grenade, explode_rigged_grenade)

    # Clean up rigging from both exits
    exit_obj.db.rigged_grenade = None

    # Find and clean up return exit too
    original_exit = rigged_grenade.db.rigged_to_exit
    if original_exit and original_exit.destination:
        destination_room = original_exit.destination
        character_room = character.location

        # Look for return exit that might also be rigged
        for obj in destination_room.contents:
            if (hasattr(obj, 'destination') and
                obj.destination == character_room and
                obj.db.rigged_grenade == rigged_grenade):
                obj.db.rigged_grenade = None
                splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
                splattercast.msg(f"{DEBUG_PREFIX_THROW}_SUCCESS: Cleaned up return exit rigging on {obj}")
                break

    # Announce timer start
    character.location.msg_contents(f"The {rigged_grenade.key} starts counting down! {fuse_time} seconds!")

    splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
    splattercast.msg(f"{DEBUG_PREFIX_THROW}_RIGGED: {character.key} triggered rigged {rigged_grenade.key} on {exit_obj.key}, timer: {fuse_time}s")

    # Return True to indicate explosion timer started
    return True


def start_standalone_grenade_ticker(grenade, explosion_callback=None):
    """Start a countdown ticker for grenades outside of CmdPull context."""
    def tick():
        try:
            # Check if grenade still exists and has countdown
            if not grenade or not hasattr(grenade, 'ndb'):
                return  # Grenade was deleted or lost state

            remaining = getattr(grenade.ndb, NDB_COUNTDOWN_REMAINING, 0)

            # Debug output
            splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
            if splattercast:
                splattercast.msg(f"{DEBUG_PREFIX_THROW}_TICKER: {grenade.key} countdown: {remaining}s remaining")

            if remaining > 1:
                # Continue countdown
                remaining -= 1
                setattr(grenade.ndb, NDB_COUNTDOWN_REMAINING, remaining)

                # Schedule next tick
                timer = utils.delay(1, tick)
                setattr(grenade.ndb, NDB_GRENADE_TIMER, timer)

                if splattercast:
                    splattercast.msg(f"{DEBUG_PREFIX_THROW}_TICKER: {grenade.key} scheduled next tick, {remaining}s remaining")

            elif remaining == 1:
                # Final countdown - explode next tick
                setattr(grenade.ndb, NDB_COUNTDOWN_REMAINING, 0)
                if explosion_callback:
                    timer = utils.delay(1, explosion_callback)
                else:
                    # Use default explosion for non-rigged grenades
                    timer = utils.delay(1, lambda: explode_standalone_grenade(grenade))
                setattr(grenade.ndb, NDB_GRENADE_TIMER, timer)

                if splattercast:
                    splattercast.msg(f"{DEBUG_PREFIX_THROW}_TICKER: {grenade.key} final countdown - explosion scheduled")

            else:
                # Should not reach here - explosion should have been triggered
                if splattercast:
                    splattercast.msg(f"{DEBUG_PREFIX_THROW}_TICKER_ERROR: {grenade.key} reached 0 without explosion - triggering now")
                if explosion_callback:
                    explosion_callback()
                else:
                    explode_standalone_grenade(grenade)

        except Exception as e:
            # Failsafe - if ticker fails, explode immediately to avoid duds
            splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
            if splattercast:
                splattercast.msg(f"{DEBUG_PREFIX_THROW}_TICKER_ERROR: Ticker error for {grenade.key}: {e} - triggering explosion")
            try:
                if explosion_callback:
                    explosion_callback()
                else:
                    explode_standalone_grenade(grenade)
            except Exception:
                pass  # If even explosion fails, give up gracefully

    # Start the ticker
    tick()


def get_unified_explosion_proximity(grenade):
    """
    Get unified proximity list for explosions by combining object proximity
    with current character proximity relationships (grappling, etc.).

    This ensures human shield mechanics work regardless of when grappling
    relationships were established relative to grenade placement.
    """
    try:
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)

        # Start with grenade's existing proximity list
        proximity_list = getattr(grenade.ndb, NDB_PROXIMITY_UNIVERSAL, [])
        if proximity_list is None:
            proximity_list = []

        # Make a copy to avoid modifying the original
        unified_list = list(proximity_list)

        splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: get_unified_explosion_proximity - initial list: {[char.key if hasattr(char, 'key') else str(char) for char in unified_list]}")

        # For each character already in proximity, add their current proximity relationships
        for character in list(proximity_list):  # Use list() to avoid modification during iteration
            if not hasattr(character, 'ndb'):
                continue

            # Check character proximity system (grappling relationships)
            character_proximity = getattr(character.ndb, NDB_PROXIMITY, None)
            if character_proximity:
                # Convert set to list for consistent handling
                character_list = list(character_proximity) if hasattr(character_proximity, '__iter__') else []
                for related_char in character_list:
                    if related_char and related_char not in unified_list:
                        unified_list.append(related_char)
                        splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Added {related_char.key if hasattr(related_char, 'key') else str(related_char)} from {character.key}'s character proximity")

        splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: get_unified_explosion_proximity - final list: {[char.key if hasattr(char, 'key') else str(char) for char in unified_list]}")
        return unified_list

    except Exception as e:
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        splattercast.msg(f"{DEBUG_PREFIX_THROW}_ERROR: Error in get_unified_explosion_proximity: {e}")
        # Return original proximity list as fallback
        return getattr(grenade.ndb, NDB_PROXIMITY_UNIVERSAL, [])


def explode_standalone_grenade(grenade):
    """Handle explosion for grenades outside of CmdPull context (like chain reactions)."""
    try:
        # Note: Using character.take_damage() for medical system integration

        # Debug: Confirm this function is being called
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: explode_standalone_grenade called for {grenade}")

        # Debug: Check dud chance
        dud_chance = grenade.db.dud_chance if grenade.db.dud_chance is not None else 0.0
        splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Dud chance: {dud_chance}")
        if random.random() < dud_chance:
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Grenade {grenade} is a dud")
            if grenade.location:
                grenade.location.msg_contents(MSG_GRENADE_DUD_ROOM.format(grenade=grenade.key))
            return

        splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Grenade {grenade} is not a dud, proceeding with explosion")

        splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Grenade {grenade} is not a dud, proceeding with explosion")

        # Get blast damage
        blast_damage = grenade.db.blast_damage if grenade.db.blast_damage is not None else 10
        splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Blast damage: {blast_damage}")

        # Check if grenade is in someone's inventory when it explodes
        # STICKY GRENADE: Check armor hierarchy first (grenade -> armor -> character)
        # Use typeclass check to distinguish characters (PCs and NPCs) from rooms
        holder = None
        stuck_to_armor = None  # Track if grenade is stuck to armor

        if grenade.location:
            from typeclasses.characters import Character
            from typeclasses.items import Item
            from world.combat.utils import get_explosion_room

            # FIRST: Check if grenade is stuck to armor (sticky grenade system)
            if isinstance(grenade.location, Item):
                stuck_to_armor = grenade.location
                splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Grenade stuck to armor: {stuck_to_armor.key}")

                # Check if armor is worn by someone
                if stuck_to_armor.location and isinstance(stuck_to_armor.location, Character):
                    holder = stuck_to_armor.location
                    splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Stuck armor worn by: {holder.key}")
                else:
                    # Armor is on ground - get room for explosion
                    room = get_explosion_room(grenade)
                    splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Stuck armor on ground in: {room.key if room else 'unknown'}")

            # SECOND: Check if grenade is directly in character inventory
            elif isinstance(grenade.location, Character):
                # Grenade is in a character's inventory - they're holding it!
                # This works for both PCs and NPCs, regardless of hands/account status
                holder = grenade.location
                splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Grenade in character inventory: {holder.key}")

        splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Holder check - location: {grenade.location}, holder: {holder}, stuck_to_armor: {stuck_to_armor}")
        splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Location is Character: {isinstance(grenade.location, Character) if grenade.location else 'No location'}")
        splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Location typeclass: {type(grenade.location).__name__ if grenade.location else 'No location'}")

        # Get unified proximity list (includes current grappling relationships)
        proximity_list = get_unified_explosion_proximity(grenade)

        splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Unified proximity list: {[char.key if hasattr(char, 'key') else str(char) for char in proximity_list]}")

        # Handle explosion in someone's hands (much more dangerous!)
        if holder:
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Handling explosion in holder's hands: {holder}")
            # Explosion in hands - double damage and guaranteed hit
            holder_damage = blast_damage * 2
            damage_type = grenade.db.damage_type if grenade.db.damage_type is not None else 'blast'  # Explosive damage type
            holder.take_damage(holder_damage, location="chest", injury_type=damage_type)

            # Different messages for sticky vs normal grenades
            if stuck_to_armor:
                # Sticky grenade stuck to armor they're wearing
                stuck_location = grenade.db.stuck_to_location or 'body'
                holder.msg(f"|R*** CATASTROPHIC EXPLOSION! ***|n\nThe {grenade.key} magnetically clamped to your {stuck_to_armor.key} DETONATES against your {stuck_location}!\nYou take {holder_damage} damage!")

                # Announce to the room
                if holder.location:
                    holder.location.msg_contents(
                        f"|R{holder.key}'s {grenade.key}, magnetically clamped to their {stuck_to_armor.key}, EXPLODES in a devastating blast!|n",
                        exclude=holder
                    )
            else:
                # Normal grenade in hands
                holder.msg(f"|rThe {grenade.key} EXPLODES IN YOUR HANDS!|n You take {holder_damage} damage!")

                # Announce to the room
                if holder.location:
                    holder.location.msg_contents(
                        f"|r{holder.key}'s {grenade.key} explodes in their hands!|n",
                        exclude=holder
                    )

            # Still damage others in proximity, but less (shielded by holder's body)
            for character in proximity_list:
                if character != holder and hasattr(character, 'msg'):
                    reduced_damage = blast_damage // 2  # Half damage due to body shielding
                    damage_type = grenade.db.damage_type if grenade.db.damage_type is not None else 'blast'
                    character.take_damage(reduced_damage, location="chest", injury_type=damage_type)
                    character.msg(MSG_GRENADE_DAMAGE.format(grenade=grenade.key))

        else:
            # Normal room explosion
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Handling normal room explosion")
            splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
            if grenade.location:
                explosion_msg = MSG_GRENADE_EXPLODE_ROOM.format(grenade=grenade.key)
                splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Standalone explosion sending message to room {grenade.location}: {explosion_msg}")

                # Debug: Show room occupants (characters only, both PCs and NPCs)
                from typeclasses.characters import Character
                room_characters = [char.key for char in grenade.location.contents if isinstance(char, Character)]
                splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Room occupants: {room_characters}")

                grenade.location.msg_contents(explosion_msg)
                # Notify adjacent rooms
                notify_adjacent_rooms_of_explosion(grenade.location)
                splattercast.msg(f"{DEBUG_PREFIX_THROW}_SUCCESS: Standalone explosion message sent to {grenade.location}")
            else:
                splattercast.msg(f"{DEBUG_PREFIX_THROW}_ERROR: Standalone explosion - grenade has no location")

            # Check for human shield mechanics
            from world.combat.utils import check_grenade_human_shield
            damage_modifiers = check_grenade_human_shield(proximity_list)

            # Apply damage to all in proximity with human shield modifiers
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Standalone explosion processing proximity list: {[char.key if hasattr(char, 'key') else str(char) for char in proximity_list]}")
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

        # Handle chain reactions
        if grenade.db.chain_trigger:
            for obj in proximity_list:
                if (hasattr(obj, 'db') and
                    obj.db.is_explosive and
                    obj != grenade):

                    # Trigger chain explosion
                    if grenade.location:
                        grenade.location.msg_contents(
                            MSG_GRENADE_CHAIN_TRIGGER.format(grenade=obj.key))

                    # Start chain reaction with new ticker system
                    obj.db.pin_pulled = True
                    setattr(obj.ndb, NDB_COUNTDOWN_REMAINING, 1)
                    start_standalone_grenade_ticker(obj)

        # Clean up
        grenade.delete()

    except Exception as e:
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        splattercast.msg(f"{DEBUG_PREFIX_THROW}_ERROR: Error in explode_standalone_grenade: {e}")


def check_auto_defuse(character):
    """Check for auto-defuse opportunities when character enters a room with live grenades."""
    try:
        # Find live grenades in the room that have the character in proximity
        live_grenades = []

        for obj in character.location.contents:
            # Check if object is an explosive
            if not obj.db.is_explosive:
                continue

            # Check if grenade is live (pin pulled and timer active)
            pin_pulled = obj.db.pin_pulled
            if not pin_pulled:
                continue

            # Check if grenade has time remaining
            remaining_time = getattr(obj.ndb, NDB_COUNTDOWN_REMAINING, 0)
            if remaining_time is None or remaining_time <= 0:
                continue

            # Check if character is in this grenade's proximity
            obj_proximity = getattr(obj.ndb, NDB_PROXIMITY_UNIVERSAL, [])
            if obj_proximity and character in obj_proximity:
                # Check if character has already attempted to defuse this grenade
                attempted_by = getattr(obj.ndb, 'defuse_attempted_by', [])
                if attempted_by is None:
                    attempted_by = []

                if character not in attempted_by:
                    live_grenades.append(obj)

        if not live_grenades:
            return

        # Auto-defuse attempt for each grenade (like D&D trap detection)
        for grenade in live_grenades:
            attempt_auto_defuse(character, grenade)

    except Exception as e:
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        splattercast.msg(f"AUTO_DEFUSE_ERROR: Error in check_auto_defuse for {character.key}: {e}")


def attempt_auto_defuse(character, grenade):
    """Attempt automatic defuse when entering proximity of live grenade."""
    try:
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)

        # Mark attempt to prevent spam (same as manual defuse)
        attempted_by = getattr(grenade.ndb, 'defuse_attempted_by', [])
        if attempted_by is None:
            attempted_by = []
        attempted_by.append(character)
        setattr(grenade.ndb, 'defuse_attempted_by', attempted_by)

        # Get remaining time for pressure calculation
        remaining_time = getattr(grenade.ndb, NDB_COUNTDOWN_REMAINING, 0)

        # Calculate difficulty (same as manual defuse)
        base_difficulty = 15  # Base difficulty
        time_pressure = max(0, 10 - remaining_time)  # Gets harder as time runs out
        total_difficulty = base_difficulty + time_pressure

        # Auto-defuse uses same skill system as manual defuse
        from world.combat.utils import roll_stat

        # Simulate combined stat roll (Intellect + Motorics)
        intellect_roll = roll_stat(character, 'intellect')
        motorics_roll = roll_stat(character, 'motorics')
        combined_roll = intellect_roll + motorics_roll

        # Determine success
        success = combined_roll >= total_difficulty

        # Announce auto-defuse attempt (more subtle than manual)
        character.msg(f"You notice the live {grenade.key} and instinctively attempt to defuse it...")
        character.location.msg_contents(
            f"{character.key} quickly works on defusing the {grenade.key}.",
            exclude=character
        )

        # Debug output
        splattercast.msg(f"AUTO_DEFUSE: {character.key} rolled {combined_roll} vs difficulty {total_difficulty} "
                       f"(base {base_difficulty} + pressure {time_pressure}, {remaining_time}s left) - "
                       f"{'SUCCESS' if success else 'FAILURE'}")

        if success:
            handle_auto_defuse_success(character, grenade)
        else:
            handle_auto_defuse_failure(character, grenade)

    except Exception as e:
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        splattercast.msg(f"AUTO_DEFUSE_ERROR: Error in attempt_auto_defuse for {character.key} and {grenade.key}: {e}")


def handle_auto_defuse_success(character, grenade):
    """Handle successful auto-defuse attempt."""
    try:
        # Cancel countdown timer
        timer = getattr(grenade.ndb, NDB_GRENADE_TIMER, None)
        if timer:
            timer.cancel()
            delattr(grenade.ndb, NDB_GRENADE_TIMER)

        # Clear countdown state
        setattr(grenade.ndb, NDB_COUNTDOWN_REMAINING, 0)
        grenade.db.pin_pulled = False  # Grenade is now safe

        # Success messages (more dramatic than manual defuse)
        character.msg(f"SUCCESS! You instinctively defuse the {grenade.key} just in time!")
        character.location.msg_contents(
            f"{character.key} quickly defuses the {grenade.key}!",
            exclude=character
        )

        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        splattercast.msg(f"AUTO_DEFUSE_SUCCESS: {character.key} auto-defused {grenade.key}")

    except Exception as e:
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        splattercast.msg(f"AUTO_DEFUSE_ERROR: Error in handle_auto_defuse_success: {e}")


def handle_auto_defuse_failure(character, grenade):
    """Handle failed auto-defuse attempt (less severe than manual defuse failure)."""
    try:
        # Auto-defuse failures have lower chance of early detonation (10% vs 30%)
        early_detonation_chance = 0.1

        if random.random() < early_detonation_chance:
            # Early detonation triggered
            character.msg(f"Your hasty defuse attempt accidentally triggers the {grenade.key}!")
            character.location.msg_contents(
                f"{character.key}'s defuse attempt accidentally triggers the {grenade.key}!",
                exclude=character
            )

            # Trigger immediate explosion (same as manual defuse)
            timer = getattr(grenade.ndb, NDB_GRENADE_TIMER, None)
            if timer:
                timer.cancel()

            # Set very short timer for dramatic effect
            setattr(grenade.ndb, NDB_COUNTDOWN_REMAINING, 1)
            utils.delay(1, trigger_auto_defuse_explosion, grenade)

            splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
            splattercast.msg(f"AUTO_DEFUSE_FAILURE: {character.key} triggered early detonation of {grenade.key}")

        else:
            # Failed but no early detonation (more subtle failure message)
            character.msg(f"You notice the {grenade.key} but can't defuse it in time.")
            character.location.msg_contents(
                f"{character.key} notices the {grenade.key} but can't defuse it.",
                exclude=character
            )

            splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
            splattercast.msg(f"AUTO_DEFUSE_FAILURE: {character.key} failed to auto-defuse {grenade.key} (no early detonation)")

    except Exception as e:
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        splattercast.msg(f"AUTO_DEFUSE_ERROR: Error in handle_auto_defuse_failure: {e}")


def trigger_auto_defuse_explosion(grenade):
    """Trigger early explosion from failed auto-defuse attempt (reuses manual defuse logic)."""
    # Reuse the explosion logic from manual defuse
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
                    utils.delay(0.5, trigger_auto_defuse_explosion, obj)

        # Clean up
        grenade.delete()

    except Exception as e:
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        splattercast.msg(f"AUTO_DEFUSE_ERROR: Error in trigger_auto_defuse_explosion: {e}")
