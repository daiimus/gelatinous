"""
Throw Command Implementation

Comprehensive throwing system supporting:
- Utility object transfer between rooms
- Combat weapon deployment with damage
- Grenade mechanics with proximity and timers
- Flight state management and room announcements
- Universal proximity system integration
- Grenade deflection with melee weapons

Part of the G.R.I.M. Combat System.
"""

import random
from evennia import Command, utils
from evennia.utils import search
from evennia.comms.models import ChannelDB
from world.combat.constants import *
# Note: apply_damage removed - using character.take_damage() for medical system integration
from world.combat.handler import get_or_create_combat


class CmdThrow(Command):
    """
    Throw objects at targets or in directions.
    
    Usage:
        throw <object>                    # Throw randomly in current room or aimed direction
        throw <object> at <target>        # Throw at specific target (requires aim for cross-room)
        throw <object> to <direction>     # Throw to adjacent room in specified direction
        throw <object> to here            # Throw randomly in current room
    
    Examples:
        throw knife at bob               # Target Bob in current room or aimed room
        throw grenade to north           # Throw grenade north to adjacent room
        throw keys to here               # Throw keys randomly in current room
        throw rock                       # Throw rock in aimed direction or current room
    
    The throw command serves dual purposes: utility object transfer and combat weapon
    deployment. Objects with the 'is_throwing_weapon' property will trigger combat
    mechanics, while utility objects transfer harmlessly between rooms.
    
    Thrown objects have a 2-second flight time and appear in room descriptions during
    flight. Landing creates proximity relationships for grenade mechanics and chain
    reactions.
    
    Special mechanics:
    - Grenades can be deflected by the TARGET if they're wielding a melee weapon (Motorics skill check)
    - Deflected grenades may bounce back to the thrower or ricochet in random directions  
    - Melee weapons with 'deflection_bonus' property modify the deflection difficulty threshold
    - Impact grenades (future feature) cannot be deflected
    """
    
    key = "throw"
    aliases = ["toss", "hurl"]
    locks = "cmd:all()"
    help_category = "Combat"
    
    def parse(self):
        """Parse throw command with intelligent syntax detection."""
        self.args = self.args.strip()
        
        # Initialize parsing results
        self.object_name = None
        self.target_name = None
        self.direction = None
        self.throw_type = None  # 'at_target', 'to_direction', 'to_here', 'fallback'
        
        if not self.args:
            return
        
        # Parse for "at" keyword - targeted throwing
        if " at " in self.args:
            parts = self.args.split(" at ", 1)
            if len(parts) == 2:
                self.object_name = parts[0].strip()
                target_part = parts[1].strip()
                
                # Handle "throw knife at here" -> convert to "throw knife to here"
                if target_part.lower() == "here":
                    self.throw_type = "to_here"
                else:
                    self.target_name = target_part
                    self.throw_type = "at_target"
                return
        
        # Parse for "to" keyword - directional or here throwing
        if " to " in self.args:
            parts = self.args.split(" to ", 1)
            if len(parts) == 2:
                self.object_name = parts[0].strip()
                target_part = parts[1].strip()
                
                if target_part.lower() == "here":
                    self.throw_type = "to_here"
                else:
                    # Check if it's a direction or character name
                    self.direction = target_part
                    self.throw_type = "to_direction"
                return
        
        # Fallback - single object name
        self.object_name = self.args
        self.throw_type = "fallback"
    
    def func(self):
        """Execute the throw command."""
        if not self.args:
            self.caller.msg("Throw what? Use 'throw <object>' or 'throw <object> at <target>'.")
            return
        
        # Validate and get the object to throw
        obj = self.get_object_to_throw()
        if not obj:
            return
        
        # Store object as instance variable for use in determine_destination
        self.obj_to_throw = obj
        
        # Check if this is a dedicated throwing weapon that should use attack command
        if getattr(obj.db, DB_IS_THROWING_WEAPON, False):
            # If targeting someone, invoke attack command instead
            if self.target_name:
                self.caller.msg(f"You ready your {obj.key} to attack...")
                # Execute the attack command with the target
                self.caller.execute_cmd(f"attack {self.target_name}")
            else:
                self.caller.msg("Throwing weapons are designed for combat. Use 'attack <target>' to fight, or 'throw <weapon> to <direction/here>' to discard it.")
            return
        
        # Determine destination and target based on throw type
        destination, target = self.determine_destination()
        if destination is None:
            return
        
        # Check if this is a weapon throw and handle combat
        is_weapon = self.is_throwing_weapon(obj)
        if is_weapon and target:
            if self.handle_weapon_throw(obj, target, destination):
                return  # Combat handled the throw
        
        # Handle utility throw or weapon miss
        self.handle_utility_throw(obj, destination, target)
    
    def get_object_to_throw(self):
        """Validate and return the object to throw."""
        if not self.object_name:
            self.caller.msg(MSG_THROW_NOTHING_WIELDED)
            return None
        
        # Check if caller has hands (AttributeProperty compatible)
        caller_hands = getattr(self.caller, 'hands', None)
        if caller_hands is None:
            self.caller.msg(MSG_THROW_NOTHING_WIELDED)
            return None
        
        # Check for empty hands dict (no hands at all)
        if not caller_hands:
            self.caller.msg(MSG_THROW_NO_HANDS)
            return None
        
        # Find object in hands
        obj = None
        hand_name = None
        for hand, wielded_obj in caller_hands.items():
            if wielded_obj and self.object_name.lower() in wielded_obj.key.lower():
                obj = wielded_obj
                hand_name = hand
                break
        
        if not obj:
            # Check if object exists but not wielded
            search_obj = self.caller.search(self.object_name, location=self.caller, quiet=True)
            if search_obj:
                self.caller.msg(MSG_THROW_OBJECT_NOT_WIELDED.format(object=self.object_name))
                return None
            else:
                self.caller.msg(MSG_THROW_OBJECT_NOT_FOUND.format(object=self.object_name))
                return None
        
        # Check for special grenade validation
        if self.is_explosive(obj):
            if not self.validate_grenade_throw(obj):
                return None
        
        # Check if caller is grappled
        if hasattr(self.caller, 'ndb') and hasattr(self.caller.ndb, NDB_COMBAT_HANDLER):
            handler = getattr(self.caller.ndb, NDB_COMBAT_HANDLER)
            if handler:
                combatants_list = getattr(handler.db, DB_COMBATANTS, [])
                combat_entry = next((e for e in combatants_list if e.get(DB_CHAR) == self.caller), None)
                if combat_entry and combat_entry.get(DB_GRAPPLED_BY_DBREF):
                    self.caller.msg(MSG_THROW_GRAPPLED)
                    return None
        
        return obj
    
    def validate_grenade_throw(self, obj):
        """Validate grenade-specific throwing requirements."""
        # Allow unpinned grenades to be thrown as inert objects
        # Players should be able to make tactical mistakes or intentional choices
        
        # Only check if grenade timer has expired (explosion in hands)
        if hasattr(obj.ndb, NDB_COUNTDOWN_REMAINING):
            remaining = getattr(obj.ndb, NDB_COUNTDOWN_REMAINING, 0)
            if remaining is not None and remaining <= 0:
                self.caller.msg(MSG_THROW_TIMER_EXPIRED)
                # Apply damage to caller using medical system
                blast_damage = getattr(obj.db, DB_BLAST_DAMAGE, 10)
                damage_type = getattr(obj.db, 'damage_type', 'blast')  # Changed to 'blast' for explosive damage
                self.caller.take_damage(blast_damage, location="chest", injury_type=damage_type)
                obj.delete()
                return False
        
        return True
    
    def determine_destination(self):
        """Determine destination room and target based on throw type."""
        if self.throw_type == "to_here":
            # Just throw in current room with no specific target
            return self.caller.location, None
        
        elif self.throw_type == "at_target":
            # Find target in current room or aimed room
            target = self.find_target()
            if not target:
                return None, None
            return target.location, target
        
        elif self.throw_type == "to_direction":
            # Validate direction and get destination room
            destination = self.get_destination_room(self.direction)
            if not destination:
                return None, None
            # For sticky grenades, prefer most magnetic character, fallback to random
            if hasattr(self, 'obj_to_throw') and getattr(self.obj_to_throw.db, 'is_sticky', False):
                target = self.select_most_magnetic_target_in_room(destination, self.obj_to_throw)
                if not target:  # No viable magnetic targets, select random
                    target = self.select_random_target_in_room(destination)
            else:
                target = self.select_random_target_in_room(destination)
            return destination, target
        
        elif self.throw_type == "fallback":
            # Use aim state or current room
            aim_direction = getattr(self.caller.ndb, NDB_AIMING_DIRECTION, None)
            if aim_direction:
                destination = self.get_destination_room(aim_direction)
                if destination:
                    # For sticky grenades, prefer most magnetic character, fallback to random
                    if hasattr(self, 'obj_to_throw') and getattr(self.obj_to_throw.db, 'is_sticky', False):
                        target = self.select_most_magnetic_target_in_room(destination, self.obj_to_throw)
                        if not target:  # No viable magnetic targets, select random
                            target = self.select_random_target_in_room(destination)
                    else:
                        target = self.select_random_target_in_room(destination)
                    return destination, target
            
            # Fallback to current room
            # For sticky grenades in current room, prefer most magnetic character, fallback to random
            if hasattr(self, 'obj_to_throw') and getattr(self.obj_to_throw.db, 'is_sticky', False):
                target = self.select_most_magnetic_target_in_room(self.caller.location, self.obj_to_throw)
                if not target:  # No viable magnetic targets, select random
                    target = self.select_random_target_in_room(self.caller.location)
            else:
                target = self.select_random_target_in_room(self.caller.location)
            return self.caller.location, target
        
        return None, None
    
    def find_target(self):
        """Find target for 'at' syntax throwing."""
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        
        if not self.target_name:
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_ERROR: find_target: No target_name provided")
            return None
        
        splattercast.msg(f"{DEBUG_PREFIX_THROW}_TEMPLATE: find_target: Looking for target '{self.target_name}' in {self.caller.location}(#{self.caller.location.id})")
        
        # First check current room
        target_search = self.caller.search(self.target_name, location=self.caller.location, quiet=True)
        target = target_search[0] if target_search else None
        target_hands = getattr(target, 'hands', None) if target else None
        splattercast.msg(f"{DEBUG_PREFIX_THROW}_TEMPLATE: find_target: search result = {target_search}, target = {target}, has_hands = {target_hands is not None}")
        
        if target and target_hands is not None:  # Is a character with hands attribute
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_SUCCESS: find_target: Found valid character target: {target}")
            return target
        
        # Check aimed room for cross-room targeting
        aim_direction = getattr(self.caller.ndb, NDB_AIMING_DIRECTION, None)
        splattercast.msg(f"{DEBUG_PREFIX_THROW}_TEMPLATE: find_target: aim_direction = {aim_direction}")
        
        if aim_direction:
            destination = self.get_destination_room(aim_direction)
            if destination:
                target_search = self.caller.search(self.target_name, location=destination, quiet=True)
                target = target_search[0] if target_search else None
                target_hands = getattr(target, 'hands', None) if target else None
                splattercast.msg(f"{DEBUG_PREFIX_THROW}_TEMPLATE: find_target: cross-room search result = {target_search}, target = {target}, has_hands = {target_hands is not None}")
                if target and target_hands is not None:
                    return target
        else:
            # No aim for cross-room targeting
            if not target:
                self.caller.msg(MSG_THROW_NO_AIM_CROSS_ROOM)
                return None
        
        splattercast.msg(f"{DEBUG_PREFIX_THROW}_FAIL: find_target: No valid target found for '{self.target_name}'")
        self.caller.msg(MSG_THROW_TARGET_NOT_FOUND.format(target=self.target_name))
        return None
    
    def get_destination_room(self, direction):
        """Get destination room for directional throwing."""
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        
        if not direction:
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_ERROR: get_destination_room: No direction provided")
            return None
        
        splattercast.msg(f"{DEBUG_PREFIX_THROW}_TEMPLATE: get_destination_room: Looking for exit '{direction}' in {self.caller.location}(#{self.caller.location.id})")
        
        # Find exit in current room using standard Evennia patterns
        exit_search = self.caller.search(direction, location=self.caller.location, quiet=True)
        
        splattercast.msg(f"{DEBUG_PREFIX_THROW}_TEMPLATE: get_destination_room: search result = {exit_search}")
        
        # Handle search result - could be list or single object
        exit_obj = exit_search[0] if exit_search else None
        
        splattercast.msg(f"{DEBUG_PREFIX_THROW}_TEMPLATE: get_destination_room: exit_obj = {exit_obj}")
        
        # Check if we got a valid exit with destination (standard Evennia way)
        if exit_obj and hasattr(exit_obj, 'destination') and exit_obj.destination:
            # Additional debug: check if destination is the same as current room
            current_room = self.caller.location
            destination_room = exit_obj.destination
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_TEMPLATE: get_destination_room: current_room = {current_room}(#{current_room.id}), destination_room = {destination_room}(#{destination_room.id})")
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_TEMPLATE: get_destination_room: rooms_are_same = {current_room == destination_room}")
            
            if current_room == destination_room:
                splattercast.msg(f"{DEBUG_PREFIX_THROW}_ERROR: get_destination_room: Exit {exit_obj} destination points back to same room!")
                self.caller.msg(f"The exit '{direction}' seems to loop back to this room. Cannot throw that way.")
                return None
            
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_SUCCESS: get_destination_room: Found valid exit {exit_obj} -> {exit_obj.destination}(#{exit_obj.destination.id})")
            return exit_obj.destination
        
        # Debug: log what we found if the exit is invalid
        if exit_obj:
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_TEMPLATE: get_destination_room: Found object type: {type(exit_obj)}, destination: {getattr(exit_obj, 'destination', 'NONE')}")
        
        # If not found or invalid, check if it might be a character name mistaken for direction
        if exit_obj:
            # Use typeclass check to distinguish characters from other objects
            from typeclasses.characters import Character
            is_character = isinstance(exit_obj, Character)
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_TEMPLATE: get_destination_room: Found object but no destination, is_character = {is_character}")
            
            if is_character:
                splattercast.msg(f"{DEBUG_PREFIX_THROW}_TEMPLATE: get_destination_room: '{direction}' is a character, suggesting 'at' syntax")
                self.caller.msg(MSG_THROW_SUGGEST_AT_SYNTAX.format(
                    object=self.object_name, target=direction))
                return None
        
        splattercast.msg(f"{DEBUG_PREFIX_THROW}_FAIL: get_destination_room: Invalid direction '{direction}'")
        self.caller.msg(MSG_THROW_INVALID_DIRECTION.format(direction=direction))
        return None
    
    def select_random_target_in_room(self, room):
        """Select random character in room for proximity assignment."""
        if not room:
            return None
        
        # Use typeclass check to distinguish characters (PCs and NPCs) from other objects
        from typeclasses.characters import Character
        characters = [obj for obj in room.contents if isinstance(obj, Character) and obj != self.caller]
        if characters:
            return random.choice(characters)
        return None
    
    def select_most_magnetic_target_in_room(self, room, grenade):
        """
        Select the most magnetic character in room for sticky grenade targeting.
        
        For sticky grenades thrown without a specific target, this finds the character
        with the highest magnetic armor to stick to.
        
        Args:
            room: The room to search
            grenade: The sticky grenade being thrown (for magnetic strength)
            
        Returns:
            Character with highest magnetic armor, or None if no valid targets
        """
        if not room:
            return None
        
        from typeclasses.characters import Character
        from typeclasses.items import Item
        from world.combat.utils import get_outermost_armor_at_location
        
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        
        # Get all characters except thrower
        characters = [obj for obj in room.contents if isinstance(obj, Character) and obj != self.caller]
        if not characters:
            return None
        
        # Get grenade magnetic strength for threshold checks
        magnetic_strength = getattr(grenade.db, 'magnetic_strength', 5)
        magnetic_threshold = magnetic_strength - 3
        metal_threshold = magnetic_strength - 5
        
        # Find character with highest magnetic armor that meets thresholds
        best_target = None
        best_magnetic_score = 0
        
        for char in characters:
            # Check armor at chest (primary target location)
            armor = get_outermost_armor_at_location(char, "chest")
            
            if not armor:
                continue
            
            # Get armor properties (including plate carrier check)
            metal_level = getattr(armor.db, 'metal_level', 0) or 0
            magnetic_level = getattr(armor.db, 'magnetic_level', 0) or 0
            
            # Check if plate carrier - use installed plates' values
            is_plate_carrier = getattr(armor.db, 'is_plate_carrier', False)
            if is_plate_carrier:
                installed_plates = getattr(armor.db, 'installed_plates', {})
                for slot, plate_ref in installed_plates.items():
                    if plate_ref:
                        plate_metal = getattr(plate_ref.db, 'metal_level', 0) or 0
                        plate_magnetic = getattr(plate_ref.db, 'magnetic_level', 0) or 0
                        metal_level = max(metal_level, plate_metal)
                        magnetic_level = max(magnetic_level, plate_magnetic)
            
            # Check if meets thresholds
            if magnetic_level >= magnetic_threshold and metal_level >= metal_threshold:
                # This target is viable - use magnetic level as score
                if magnetic_level > best_magnetic_score:
                    best_magnetic_score = magnetic_level
                    best_target = char
                    splattercast.msg(f"{DEBUG_PREFIX_THROW}_STICKY_TARGET: {char.key} viable with magnetic={magnetic_level}, metal={metal_level}")
        
        if best_target:
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_STICKY_TARGET: Selected {best_target.key} (magnetic={best_magnetic_score})")
        else:
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_STICKY_TARGET: No viable magnetic targets in {room.key}")
        
        return best_target
    
    def is_throwing_weapon(self, obj):
        """Check if object is a throwing weapon."""
        return getattr(obj.db, DB_IS_THROWING_WEAPON, False)
    
    def is_explosive(self, obj):
        """Check if object is explosive."""
        return getattr(obj.db, DB_IS_EXPLOSIVE, False)
    
    def handle_weapon_throw(self, obj, target, destination):
        """Handle throwing weapon combat mechanics."""
        # Enter combat if not already in combat
        handler = get_or_create_combat(self.caller.location)
        if not handler:
            splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_ERROR: Failed to get combat handler for weapon throw")
            return False
        
        # Add combatants to handler
        handler.add_combatant(self.caller)
        if target:
            handler.add_combatant(target)
        
        # Consume combat turn (skip turn mechanic)
        setattr(self.caller.ndb, NDB_SKIP_ROUND, True)
        
        # Remove object from hand before flight
        self.remove_from_hand(obj)
        
        # Start flight with combat resolution
        self.start_flight(obj, destination, target, is_weapon=True)
        return True
    
    def handle_utility_throw(self, obj, destination, target):
        """Handle utility object throwing."""
        # Remove object from hand
        self.remove_from_hand(obj)
        
        # Start flight
        self.start_flight(obj, destination, target, is_weapon=False)
    
    def remove_from_hand(self, obj):
        """Remove object from caller's hand."""
        caller_hands = getattr(self.caller, 'hands', {})
        for hand_name, wielded_obj in caller_hands.items():
            if wielded_obj == obj:
                caller_hands[hand_name] = None
                break
    
    def start_flight(self, obj, destination, target, is_weapon=False):
        """Start object flight with timer."""
        # Announce throw in origin room
        self.announce_throw_origin(obj, destination, target)
        
        # Add to room's flying objects - ensure we have a proper list
        flying_objects = getattr(self.caller.location.ndb, NDB_FLYING_OBJECTS, None)
        if not flying_objects:
            setattr(self.caller.location.ndb, NDB_FLYING_OBJECTS, [])
        
        flying_objects = getattr(self.caller.location.ndb, NDB_FLYING_OBJECTS)
        if flying_objects is None:
            flying_objects = []
            setattr(self.caller.location.ndb, NDB_FLYING_OBJECTS, flying_objects)
        
        flying_objects.append(obj)
        
        # Store flight data on object
        obj.ndb.flight_destination = destination
        obj.ndb.flight_target = target
        obj.ndb.flight_origin = self.caller.location
        obj.ndb.flight_is_weapon = is_weapon
        obj.ndb.flight_thrower = self.caller
        
        # Start flight timer and store reference for potential cancellation
        obj.ndb.flight_timer = utils.delay(THROW_FLIGHT_TIME, self.complete_flight, obj)
        
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        splattercast.msg(f"{DEBUG_PREFIX_THROW}_SUCCESS: {self.caller} started flight for {obj} to {destination}(#{destination.id})")
    
    def announce_throw_origin(self, obj, destination, target):
        """Announce throw in origin room."""
        caller_name = self.caller.key
        object_name = obj.key
        
        # Determine announcement based on throw type
        if self.throw_type == "to_direction":
            direction = self.direction
            message = MSG_THROW_ORIGIN_DIRECTIONAL.format(
                thrower=caller_name, object=object_name, direction=direction)
        
        elif self.throw_type == "at_target" and target and target.location == self.caller.location:
            target_name = target.key
            message = MSG_THROW_ORIGIN_TARGETED_SAME.format(
                thrower=caller_name, object=object_name, target=target_name)
        
        elif self.throw_type == "at_target" and target:
            # Cross-room targeting
            aim_direction = getattr(self.caller.ndb, NDB_AIMING_DIRECTION, "that direction")
            message = MSG_THROW_ORIGIN_TARGETED_CROSS.format(
                thrower=caller_name, object=object_name, direction=aim_direction)
        
        elif self.throw_type == "to_here":
            message = MSG_THROW_ORIGIN_HERE.format(
                thrower=caller_name, object=object_name)
        
        else:  # fallback
            aim_direction = getattr(self.caller.ndb, NDB_AIMING_DIRECTION, "nearby")
            if aim_direction == "nearby":
                message = MSG_THROW_ORIGIN_HERE.format(
                    thrower=caller_name, object=object_name)
            else:
                message = MSG_THROW_ORIGIN_FALLBACK.format(
                    thrower=caller_name, object=object_name, direction=aim_direction)
        
        # Broadcast to room
        self.caller.location.msg_contents(message, exclude=self.caller)
        self.caller.msg(f"You throw a {object_name}.")
    
    def complete_flight(self, obj):
        """Complete the flight and handle landing."""
        splattercast = None
        try:
            splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Starting complete_flight for {obj}")
            
            # Check if object is None or doesn't have ndb (deleted/caught)
            if not obj or not hasattr(obj, 'ndb') or obj.ndb is None:
                splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Object {obj} is None or missing ndb, skipping complete_flight")
                return
            
            # Check if object was caught (flight data cleaned up)
            if not hasattr(obj.ndb, 'flight_destination'):
                splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Object {obj} was caught, skipping complete_flight")
                return
            
            # Get flight data with defensive checks - wrap in try-catch to handle race conditions
            try:
                destination = getattr(obj.ndb, 'flight_destination', None)
                target = getattr(obj.ndb, 'flight_target', None)
                origin = getattr(obj.ndb, 'flight_origin', None)
                is_weapon = getattr(obj.ndb, 'flight_is_weapon', False)
                thrower = getattr(obj.ndb, 'flight_thrower', None)
            except (AttributeError, TypeError):
                # Race condition - object state changed between checks
                splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Race condition detected during flight data access, skipping complete_flight")
                return
            
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Flight data - destination: {destination}, target: {target}, origin: {origin}")
            
            # Clean up origin room flying objects with additional safety
            if origin and hasattr(origin, 'ndb') and origin.ndb is not None:
                try:
                    origin_flying_objects = getattr(origin.ndb, NDB_FLYING_OBJECTS, None)
                    if origin_flying_objects and obj in origin_flying_objects:
                        origin_flying_objects.remove(obj)
                        splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Removed {obj} from origin flying objects")
                except (AttributeError, TypeError, ValueError):
                    # Safe to ignore - object cleanup isn't critical
                    pass
            
            # Move object to destination
            if destination:
                try:
                    splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Moving {obj} to destination {destination}")
                    obj.move_to(destination, quiet=True)  # Use quiet=True to suppress auto-messages
                    
                    # Announce arrival based on room relationship
                    if destination != origin:
                        # Cross-room throw - announce arrival
                        arrival_dir = self.get_arrival_direction(origin, destination)
                        if target and target.location == destination:
                            # Send personal message to victim
                            target.msg(MSG_THROW_ARRIVAL_TARGETED_VICTIM.format(object=obj.key, direction=arrival_dir))
                            # Send observer message to everyone else
                            destination.msg_contents(
                                MSG_THROW_ARRIVAL_TARGETED.format(object=obj.key, direction=arrival_dir, target=target.key),
                                exclude=[target]
                            )
                        else:
                            destination.msg_contents(MSG_THROW_ARRIVAL.format(object=obj.key, direction=arrival_dir))
                        splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Cross-room arrival message sent")
                    else:
                        # Same-room throw - show flight message
                        if target:
                            # Send personal message to victim
                            target.msg(MSG_THROW_FLIGHT_SAMEROOM_TARGET_VICTIM.format(object=obj.key))
                            # Send observer message to everyone else (excluding thrower and victim)
                            destination.msg_contents(
                                MSG_THROW_FLIGHT_SAMEROOM_TARGET.format(object=obj.key, target=target.key),
                                exclude=[thrower, target]
                            )
                        else:
                            destination.msg_contents(MSG_THROW_FLIGHT_SAMEROOM_GENERAL.format(object=obj.key), exclude=[thrower])
                        splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Same-room flight message sent")
                    
                    # Check for grenade deflection before landing
                    if self.is_explosive(obj) and destination:
                        deflection_result = self.check_grenade_deflection(obj, destination, thrower)
                        if deflection_result:
                            splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Grenade was deflected, skipping normal landing")
                            return  # Deflection handled everything, don't continue with normal landing
                    
                    splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: About to call handle_landing")
                    # Handle landing and proximity
                    self.handle_landing(obj, destination, target, is_weapon, thrower)
                    splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Completed handle_landing")
                    
                    # Apply gravity if item landed in a sky room
                    from commands.combat.movement import apply_gravity_to_items
                    apply_gravity_to_items(destination)
                    splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Applied gravity check to destination {destination}")
                    
                except Exception as e:
                    splattercast.msg(f"{DEBUG_PREFIX_THROW}_ERROR: Error during object movement/landing: {e}")
                    # Try to move to origin as fallback
                    if origin:
                        try:
                            obj.move_to(origin)
                            splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Moved {obj} back to origin {origin} as fallback")
                        except:
                            pass  # If even fallback fails, give up gracefully
            
            # Clean up flight data with defensive checks
            try:
                if hasattr(obj, 'ndb') and obj.ndb is not None:
                    if hasattr(obj.ndb, 'flight_destination'):
                        del obj.ndb.flight_destination
                    if hasattr(obj.ndb, 'flight_target'):
                        del obj.ndb.flight_target
                    if hasattr(obj.ndb, 'flight_origin'):
                        del obj.ndb.flight_origin
                    if hasattr(obj.ndb, 'flight_is_weapon'):
                        del obj.ndb.flight_is_weapon
                    if hasattr(obj.ndb, 'flight_thrower'):
                        del obj.ndb.flight_thrower
                    if hasattr(obj.ndb, 'flight_timer'):
                        del obj.ndb.flight_timer
                    splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Cleaned up flight data for {obj}")
            except (AttributeError, TypeError):
                # Object state changed during cleanup - not critical
                pass
            
        except Exception as e:
            if splattercast:
                splattercast.msg(f"{DEBUG_PREFIX_THROW}_ERROR: Unexpected error in complete_flight: {e}")
            # Final failsafe - try to put object somewhere safe
            try:
                if obj and hasattr(obj, 'move_to'):
                    # Try to get origin from flight data if still available
                    flight_origin = None
                    if hasattr(obj, 'ndb') and obj.ndb and hasattr(obj.ndb, 'flight_origin'):
                        flight_origin = getattr(obj.ndb, 'flight_origin', None)
                    if flight_origin:
                        obj.move_to(flight_origin)
                        if splattercast:
                            splattercast.msg(f"{DEBUG_PREFIX_THROW}_ERROR: Emergency moved {obj} back to origin {flight_origin}")
            except:
                pass  # If all else fails, give up gracefully
    
    def get_arrival_direction(self, origin, destination):
        """Determine arrival direction for announcement."""
        # Simple implementation - would need room connection mapping for accuracy
        return "somewhere"
    
    def handle_landing(self, obj, destination, target, is_weapon, thrower):
        """Handle object landing and proximity assignment."""
        try:
            splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: handle_landing called - obj: {obj}, destination: {destination}, target: {target}, is_weapon: {is_weapon}")
            
            # Track whether we've shown a target interaction message
            showed_interaction = False
            
            # Weapon combat resolution
            if is_weapon and target:
                try:
                    splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Resolving weapon hit")
                    self.resolve_weapon_hit(obj, target, thrower)
                    showed_interaction = True  # Weapon hit/miss shows its own message
                    splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: resolve_weapon_hit completed")
                except Exception as e:
                    splattercast.msg(f"{DEBUG_PREFIX_THROW}_ERROR: Error in resolve_weapon_hit: {e}")
                    # Continue with landing even if weapon hit fails
            
            # Sticky grenade resolution (even for utility throws)
            elif target and not is_weapon and getattr(obj.db, 'is_sticky', False):
                try:
                    splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Sticky grenade utility throw - routing to weapon hit logic")
                    self.resolve_weapon_hit(obj, target, thrower)
                    showed_interaction = True  # Stick/bounce shows its own message
                    splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Sticky grenade resolution completed")
                except Exception as e:
                    splattercast.msg(f"{DEBUG_PREFIX_THROW}_ERROR: Error in sticky grenade resolution: {e}")
                    # Continue with landing even if stick check fails
            
            # Utility object bounce
            elif target and not is_weapon:
                try:
                    splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Utility object bounce")
                    # Send personal message to victim
                    target.msg(MSG_THROW_UTILITY_BOUNCE_VICTIM.format(object=obj.key))
                    # Send observer message to room
                    target.location.msg_contents(
                        MSG_THROW_UTILITY_BOUNCE.format(object=obj.key, target=target.key),
                        exclude=[target]
                    )
                    showed_interaction = True  # Bounce message already shown
                    splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Utility bounce message sent")
                except Exception as e:
                    splattercast.msg(f"{DEBUG_PREFIX_THROW}_ERROR: Error in utility bounce: {e}")
                    # Continue with landing even if bounce message fails
            
            # Assign proximity for universal proximity system
            try:
                splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Assigning landing proximity")
                self.assign_landing_proximity(obj, target, thrower)
                splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: assign_landing_proximity completed")
            except Exception as e:
                splattercast.msg(f"{DEBUG_PREFIX_THROW}_ERROR: Error in assign_landing_proximity: {e}")
                # Continue with landing even if proximity assignment fails
            
            # Handle grenade-specific landing
            if self.is_explosive(obj):
                try:
                    splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Handling grenade landing")
                    self.handle_grenade_landing(obj, target, thrower)
                    splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: handle_grenade_landing completed")
                except Exception as e:
                    splattercast.msg(f"{DEBUG_PREFIX_THROW}_ERROR: Error in handle_grenade_landing: {e}")
                    # Continue with landing even if grenade landing fails
            
            # General landing announcement - only if no target interaction was shown
            if not showed_interaction:
                try:
                    if target:
                        message = MSG_THROW_LANDING_PROXIMITY.format(object=obj.key, target=target.key)
                    else:
                        message = MSG_THROW_LANDING_ROOM.format(object=obj.key)
                    
                    splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Sending landing message: {message}")
                    destination.msg_contents(message)
                    splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Landing message sent successfully")
                except Exception as e:
                    splattercast.msg(f"{DEBUG_PREFIX_THROW}_ERROR: Error in landing message: {e}")
                    # Continue even if landing message fails
            else:
                splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Skipping landing message - interaction already shown")
            
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: handle_landing completed successfully")
            
        except Exception as e:
            splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_ERROR: Unexpected error in handle_landing: {e}")
            # Don't re-raise - let the object land even if there are issues
    
    def resolve_weapon_hit(self, weapon, target, thrower):
        """Resolve weapon throw hit/miss and damage."""
        try:
            # Simple hit resolution - could be enhanced with accuracy system
            hit_chance = 0.7  # 70% base hit chance
            
            if random.random() <= hit_chance:
                # STICKY GRENADE CHECK - Check for stick before damage
                # Import required for sticky grenade logic
                from world.combat.utils import (
                    calculate_stick_chance, establish_stick,
                    get_outermost_armor_at_location, debug_broadcast
                )
                
                # Check if this is a sticky grenade
                is_sticky = getattr(weapon.db, 'is_sticky', False)
                hit_location = "chest"  # Default hit location for throws
                
                if is_sticky:
                    splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
                    splattercast.msg(f"{DEBUG_PREFIX_THROW}_STICKY: Sticky grenade {weapon.key} hit {target.key}")
                    
                    # Get outermost armor at hit location
                    armor = get_outermost_armor_at_location(target, hit_location)
                    
                    if armor:
                        # Calculate stick chance
                        stick_chance = calculate_stick_chance(weapon, armor)
                        roll = random.randint(1, 100)
                        
                        if roll <= stick_chance:
                            # SUCCESS - Grenade sticks to armor
                            if establish_stick(weapon, armor, hit_location):
                                # Send stick messages - Spider-themed with telescoping legs
                                target.msg(f"|rThe {weapon.key}'s articulated legs extend with mechanical precision, their electromagnetic tips skittering across your {armor.key} before *CLAMPING* tight with magnetic fury!|n")
                                thrower.msg(f"Your {weapon.key}'s spider-legs deploy and latch onto {target.key}'s {armor.key} with a satisfying *CLACK-CLACK-CLACK* of magnetic adhesion!")
                                target.location.msg_contents(
                                    f"The {weapon.key}'s eight legs telescope outward in a blur of motion, seeking metal across {target.key}'s {armor.key} before *SNAPPING* into electromagnetic lock!",
                                    exclude=[thrower, target]
                                )
                                
                                splattercast.msg(f"{DEBUG_PREFIX_THROW}_STICKY_SUCCESS: {weapon.key} stuck to {armor.key} (roll {roll} <= {stick_chance})")
                                
                                # Skip normal landing - grenade is stuck to armor now
                                return
                            else:
                                splattercast.msg(f"{DEBUG_PREFIX_THROW}_STICKY_ERROR: establish_stick failed")
                        else:
                            # FAIL - Grenade bounces off
                            target.msg(f"The {weapon.key}'s legs extend and scrabble frantically across your {armor.key}, but the magnetic field is too weak - it bounces away with a frustrated clatter!")
                            thrower.msg(f"Your {weapon.key}'s spider-legs fail to find purchase on {target.key}'s {armor.key}, bouncing off ineffectively!")
                            target.location.msg_contents(
                                f"The {weapon.key}'s articulated legs scrape and skitter across {target.key}'s {armor.key} before losing grip and clattering away!",
                                exclude=[thrower, target]
                            )
                            
                            splattercast.msg(f"{DEBUG_PREFIX_THROW}_STICKY_FAIL: {weapon.key} bounce (roll {roll} > {stick_chance})")
                            # Continue to normal landing
                    else:
                        # No armor at hit location - bounce off
                        target.msg(f"The {weapon.key} strikes your {hit_location} and its legs extend desperately, seeking metal that isn't there - it bounces away with a frustrated whir of servos!")
                        thrower.msg(f"Your {weapon.key}'s electromagnetic sensors find no ferrous surface on {target.key}'s {hit_location} - the spider-legs retract as it falls away!")
                        target.location.msg_contents(
                            f"The {weapon.key}'s articulated legs extend and search frantically across {target.key}'s {hit_location} before retracting in defeat!",
                            exclude=[thrower, target]
                        )
                        
                        splattercast.msg(f"{DEBUG_PREFIX_THROW}_STICKY_FAIL: No armor at {hit_location}")
                        # Continue to normal landing
                
                # Hit - apply damage (only for non-sticky or failed-stick weapons)
                base_damage = getattr(weapon.db, 'damage', 1)
                total_damage = random.randint(1, 6) + base_damage
                damage_type = getattr(weapon.db, 'damage_type', 'blunt')  # Get weapon damage type
                
                target.take_damage(total_damage, location="chest", injury_type=damage_type)
                
                # Send personal message to victim
                target.msg(MSG_THROW_WEAPON_HIT_VICTIM.format(thrower=thrower.key, weapon=weapon.key))
                # Send personal message to thrower
                thrower.msg(MSG_THROW_WEAPON_HIT.format(weapon=weapon.key, target=target.key))
                # Observer message (everyone else in room)
                target.location.msg_contents(
                    f"{thrower.key}'s {weapon.key} strikes {target.key}!",
                    exclude=[thrower, target]
                )
                
                # Establish proximity if hit (safe pattern)
                proximity_list = getattr(target.ndb, NDB_PROXIMITY_UNIVERSAL, None)
                if not proximity_list:
                    setattr(target.ndb, NDB_PROXIMITY_UNIVERSAL, [])
                    proximity_list = getattr(target.ndb, NDB_PROXIMITY_UNIVERSAL, [])
                
                # Validate proximity_list is a list
                if not isinstance(proximity_list, list):
                    proximity_list = []
                    setattr(target.ndb, NDB_PROXIMITY_UNIVERSAL, proximity_list)
                
                if thrower and thrower not in proximity_list:
                    proximity_list.append(thrower)
            
            else:
                # Miss - send personal message to victim
                target.msg(MSG_THROW_WEAPON_MISS_VICTIM.format(thrower=thrower.key, weapon=weapon.key))
                # Send personal message to thrower
                thrower.msg(MSG_THROW_WEAPON_MISS.format(weapon=weapon.key, target=target.key))
                # Observer message (everyone else in room)
                target.location.msg_contents(
                    f"{thrower.key}'s {weapon.key} narrowly misses {target.key} and clatters to the ground.",
                    exclude=[thrower, target]
                )
                
        except Exception as e:
            splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_ERROR: Error in resolve_weapon_hit: {e}")
            # Don't re-raise - weapon hit failure shouldn't fail entire throw
    
    def assign_landing_proximity(self, obj, target, thrower=None):
        """Assign proximity for universal proximity system."""
        try:
            splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: assign_landing_proximity called - obj: {obj}, target: {target}, thrower: {thrower}")
            
            # Ensure object has proximity list (use same pattern as drop command)
            proximity_list = getattr(obj.ndb, NDB_PROXIMITY_UNIVERSAL, None)
            if not proximity_list:
                setattr(obj.ndb, NDB_PROXIMITY_UNIVERSAL, [])
                proximity_list = getattr(obj.ndb, NDB_PROXIMITY_UNIVERSAL, [])
            
            # Validate proximity_list is actually a list
            if not isinstance(proximity_list, list):
                proximity_list = []
                setattr(obj.ndb, NDB_PROXIMITY_UNIVERSAL, proximity_list)
            
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: obj proximity_list: {proximity_list}")
            
            if target:
                # Add target to object proximity
                if target not in proximity_list:
                    proximity_list.append(target)
                    splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Added target {target} to obj proximity")
                
                # Inherit target's existing proximity relationships, but exclude the thrower
                # Check both proximity systems:
                
                # 1. Object proximity system (NDB_PROXIMITY_UNIVERSAL)
                target_proximity = getattr(target.ndb, NDB_PROXIMITY_UNIVERSAL, None)
                splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: target_proximity (objects): {target_proximity}")
                if target_proximity and isinstance(target_proximity, list):
                    for character in target_proximity:
                        # Filter out the thrower - they shouldn't be in proximity to their own thrown object
                        if character and character not in proximity_list and character != thrower:
                            proximity_list.append(character)
                            splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Added {character} from target object proximity")
                        elif character == thrower:
                            splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Skipped thrower {character} from object proximity inheritance")
                
                # 2. Character proximity system (in_proximity_with)
                character_proximity = getattr(target.ndb, NDB_PROXIMITY, None)
                splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: target_proximity (characters): {character_proximity}")
                if character_proximity:
                    # Convert set to list for consistent handling
                    character_list = list(character_proximity) if hasattr(character_proximity, '__iter__') else []
                    for character in character_list:
                        # Filter out the thrower - they shouldn't be in proximity to their own thrown object
                        if character and character not in proximity_list and character != thrower:
                            proximity_list.append(character)
                            splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Added {character} from target character proximity")
                        elif character == thrower:
                            splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Skipped thrower {character} from character proximity inheritance")
            
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: assign_landing_proximity completed successfully")
            
        except Exception as e:
            splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_ERROR: Error in assign_landing_proximity: {e}")
            raise  # Re-raise to let handle_landing handle it
    
    def handle_grenade_landing(self, grenade, target, thrower=None):
        """Handle grenade-specific landing mechanics."""
        try:
            splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: handle_grenade_landing called - grenade: {grenade}, target: {target}, thrower: {thrower}")
            
            # If grenade lands near someone, everyone in their proximity gets added
            target_proximity = getattr(target.ndb, NDB_PROXIMITY_UNIVERSAL, None) if target else None
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: target_proximity: {target_proximity}")
            
            if target_proximity and isinstance(target_proximity, list):
                grenade_proximity = getattr(grenade.ndb, NDB_PROXIMITY_UNIVERSAL, [])
                if not isinstance(grenade_proximity, list):
                    grenade_proximity = []
                
                for character in target_proximity:
                    # Filter out the thrower - they shouldn't be in proximity to their own thrown grenade
                    if character and character not in grenade_proximity and character != thrower:
                        grenade_proximity.append(character)
                        splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Added {character} to grenade proximity")
                    elif character == thrower:
                        splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Skipped thrower {character} from grenade proximity inheritance")
                
                setattr(grenade.ndb, NDB_PROXIMITY_UNIVERSAL, grenade_proximity)
            
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_SUCCESS: Grenade {grenade} landed with proximity: {getattr(grenade.ndb, NDB_PROXIMITY_UNIVERSAL, [])}")
            
        except Exception as e:
            splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_ERROR: Error in handle_grenade_landing: {e}")
            # Don't re-raise here - grenade landing failure shouldn't fail entire throw
    
    def check_grenade_deflection(self, grenade, destination, thrower):
        """Check if the specific target can deflect the incoming grenade with a melee weapon."""
        try:
            import random
            splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: check_grenade_deflection called for {grenade} in {destination}")
            
            # Future-proofing: Skip deflection for impact grenades (explode on contact)
            if getattr(grenade.db, 'impact_detonation', False):
                splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Impact grenade {grenade} cannot be deflected")
                return False
            
            # Get the specific target from flight data
            target = getattr(grenade.ndb, 'flight_target', None)
            if not target:
                splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: No specific target for deflection check")
                return False
            
            # Check if target is in the destination room
            if target.location != destination:
                splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Target {target} not in destination {destination}")
                return False
            
            # Check if target is grappled or grappling (cannot deflect while restricted)
            if hasattr(target, 'ndb') and hasattr(target.ndb, NDB_COMBAT_HANDLER):
                handler = getattr(target.ndb, NDB_COMBAT_HANDLER)
                if handler:
                    combatants_list = getattr(handler.db, DB_COMBATANTS, [])
                    combat_entry = next((e for e in combatants_list if e.get(DB_CHAR) == target), None)
                    if combat_entry:
                        grappled_by = combat_entry.get(DB_GRAPPLED_BY_DBREF)
                        grappling = combat_entry.get(DB_GRAPPLING_DBREF)
                        if grappled_by or grappling:
                            splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Target {target} cannot deflect - grappled_by: {grappled_by}, grappling: {grappling}")
                            return False
            
            # Check if target has hands and a melee weapon
            target_hands = getattr(target, 'hands', None)
            if not target_hands:
                splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Target {target} has no hands")
                return False
            
            # Find melee weapon in target's hands
            melee_weapon = None
            for hand, wielded_obj in target_hands.items():
                if wielded_obj and self.is_melee_weapon(wielded_obj):
                    melee_weapon = wielded_obj
                    break
            
            if not melee_weapon:
                splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Target {target} has no melee weapon")
                return False
            
            # Perform Motorics skill check for deflection
            from world.combat.utils import roll_stat
            
            # Roll Motorics skill
            motorics_roll = roll_stat(target, 'motorics')
            
            # Base difficulty threshold (higher = easier)
            base_threshold = 10  # Moderate difficulty
            weapon_bonus = getattr(melee_weapon.db, 'deflection_bonus', 0.0)  # Optional weapon property
            
            # Convert weapon bonus to threshold modifier (0.30 bonus = +6 to threshold)
            threshold_modifier = int(weapon_bonus * 20)
            final_threshold = base_threshold + threshold_modifier
            
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: {target} Motorics deflection: rolled {motorics_roll} vs threshold {final_threshold}")
            
            if motorics_roll >= final_threshold:
                # Successful deflection!
                return self.perform_grenade_deflection(grenade, target, melee_weapon, thrower, destination)
            else:
                # Failed deflection attempt
                target.msg(f"You attempt to deflect the {grenade.key} with your {melee_weapon.key}, but your reflexes aren't quick enough!")
                destination.msg_contents(
                    f"{target.key} swings their {melee_weapon.key} at the incoming {grenade.key} but fails to connect!",
                    exclude=target
                )
                splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: {target} failed deflection attempt")
                return False
                
        except Exception as e:
            splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_ERROR: Error in check_grenade_deflection: {e}")
            return False
    
    def is_melee_weapon(self, obj):
        """Check if object is a melee weapon suitable for deflection."""
        # Melee weapons are those that are NOT ranged (default is melee)
        is_ranged = getattr(obj.db, 'is_ranged', False)
        return not is_ranged
    
    def perform_grenade_deflection(self, grenade, deflector, weapon, original_thrower, current_location):
        """Perform the actual grenade deflection."""
        try:
            import random
            splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: perform_grenade_deflection called")
            
            # Announce successful deflection
            deflector.msg(f"|yYou successfully bat the {grenade.key} away with your {weapon.key}!|n")
            current_location.msg_contents(
                f"|y{deflector.key} deflects the incoming {grenade.key} with their {weapon.key}!|n",
                exclude=deflector
            )
            
            # Determine deflection target and destination
            deflection_success = self.determine_deflection_target(grenade, deflector, original_thrower, current_location)
            
            if deflection_success:
                splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Grenade deflection successful, new flight initiated")
                return True
            else:
                # Deflection hit but grenade lands in same room
                splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Deflection hit but grenade stays in same room")
                self.handle_landing(grenade, current_location, None, False, original_thrower)
                return True
                
        except Exception as e:
            splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_ERROR: Error in perform_grenade_deflection: {e}")
            return False
    
    def determine_deflection_target(self, grenade, deflector, original_thrower, current_location):
        """Determine where the deflected grenade goes."""
        try:
            import random
            splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
            
            # Get grenade's original flight data
            origin = getattr(grenade.ndb, 'flight_origin', None)
            
            # 60% chance to deflect back toward origin/thrower if possible
            # 40% chance to deflect in random direction
            deflect_back_chance = 0.6
            
            if random.random() <= deflect_back_chance and origin and origin != current_location:
                # Try to deflect back to origin room
                new_destination = origin
                new_target = original_thrower if original_thrower and original_thrower.location == origin else None
                deflection_type = "back toward origin"
                
                splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Deflecting back to origin {origin}")
                
            else:
                # Deflect in random direction
                available_exits = [obj for obj in current_location.contents 
                                 if hasattr(obj, 'destination') and obj.destination 
                                 and obj.destination != current_location]
                
                if available_exits:
                    random_exit = random.choice(available_exits)
                    new_destination = random_exit.destination
                    new_target = self.select_random_target_in_room(new_destination)
                    deflection_type = f"toward {random_exit.key}"
                    
                    splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Deflecting to random direction {random_exit.key}")
                else:
                    # No exits available, grenade lands in current room
                    splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: No exits available for deflection")
                    return False
            
            # Announce deflection direction
            current_location.msg_contents(
                f"The {grenade.key} ricochets {deflection_type}!"
            )
            
            # Update flight data and restart flight
            grenade.ndb.flight_destination = new_destination
            grenade.ndb.flight_target = new_target
            grenade.ndb.flight_origin = current_location
            grenade.ndb.flight_thrower = deflector  # Deflector becomes new "thrower"
            
            # Start new flight with shorter timer (already partially through flight)
            reduced_flight_time = max(1, THROW_FLIGHT_TIME - 1)  # At least 1 second
            grenade.ndb.flight_timer = utils.delay(reduced_flight_time, self.complete_flight, grenade)
            
            # Add to current room's flying objects temporarily
            flying_objects = getattr(current_location.ndb, NDB_FLYING_OBJECTS, None)
            if not flying_objects:
                setattr(current_location.ndb, NDB_FLYING_OBJECTS, [])
                flying_objects = getattr(current_location.ndb, NDB_FLYING_OBJECTS)
            
            if grenade not in flying_objects:
                flying_objects.append(grenade)
            
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_SUCCESS: Deflected {grenade} from {deflector} to {new_destination}")
            return True
            
        except Exception as e:
            splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_ERROR: Error in determine_deflection_target: {e}")
            return False


class CmdPull(Command):
    """
    Pull pins on grenades to arm them.
    
    Usage:
        pull pin on <grenade>
    
    Examples:
        pull pin on grenade
        pull pin on flashbang
    
    Pulling the pin on a grenade starts its countdown timer. The grenade must be
    thrown or dropped before the timer expires, or it will explode in your hands.
    """
    
    key = "pull"
    locks = "cmd:all()"
    help_category = "Combat"
    
    def parse(self):
        """Parse pull command syntax."""
        self.args = self.args.strip()
        
        # Expected syntax: "pin on <grenade>"
        if self.args.startswith("pin on "):
            self.grenade_name = self.args[7:].strip()
        else:
            self.grenade_name = None
    
    def func(self):
        """Execute pull command."""
        if not self.args:
            self.caller.msg(MSG_PULL_WHAT)
            return
        
        if not self.grenade_name:
            self.caller.msg(MSG_PULL_INVALID_SYNTAX)
            return
        
        # Check for hands at all
        caller_hands = getattr(self.caller, 'hands', None)
        if caller_hands is None or not caller_hands:
            self.caller.msg(MSG_PULL_NO_HANDS)
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
                self.caller.msg(MSG_PULL_OBJECT_NOT_WIELDED.format(object=self.grenade_name))
                return
            else:
                self.caller.msg(MSG_PULL_OBJECT_NOT_FOUND.format(object=self.grenade_name))
                return
        
        # Validate explosive
        if not getattr(grenade.db, DB_IS_EXPLOSIVE, False):
            self.caller.msg(MSG_PULL_NOT_EXPLOSIVE.format(object=grenade.key))
            return
        
        # Check if requires pin
        if not getattr(grenade.db, DB_REQUIRES_PIN, True):
            self.caller.msg(MSG_PULL_NO_PIN_REQUIRED.format(object=grenade.key))
            return
        
        # Check if already pulled
        if getattr(grenade.db, DB_PIN_PULLED, False):
            self.caller.msg(MSG_PULL_ALREADY_PULLED.format(object=grenade.key))
            return
        
        # Pull pin and start timer
        self.pull_pin(grenade)
    
    def pull_pin(self, grenade):
        """Pull the pin and start countdown."""
        # Set pin pulled flag
        setattr(grenade.db, DB_PIN_PULLED, True)
        
        # Get fuse time
        fuse_time = getattr(grenade.db, DB_FUSE_TIME, 8)
        
        # Start countdown with robust ticker system
        setattr(grenade.ndb, NDB_COUNTDOWN_REMAINING, fuse_time)
        self.start_grenade_ticker(grenade)
        
        # Announce
        self.caller.msg(MSG_PULL_SUCCESS.format(object=grenade.key))
        self.caller.location.msg_contents(
            MSG_PULL_SUCCESS_ROOM.format(puller=self.caller.key, object=grenade.key),
            exclude=self.caller
        )
        
        # Timer warning
        self.caller.msg(MSG_PULL_TIMER_WARNING.format(object=grenade.key, time=fuse_time))
        
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        splattercast.msg(f"{DEBUG_PREFIX_THROW}_SUCCESS: {self.caller} pulled pin on {grenade}, timer: {fuse_time}s")
    
    def start_grenade_ticker(self, grenade):
        """Start a proper countdown ticker that decrements every second and survives deflections."""
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
                    
                    # STICKY GRENADE: Send appropriate countdown warnings
                    from typeclasses.items import Item
                    from typeclasses.characters import Character
                    
                    # Check if grenade is stuck to armor
                    is_stuck = isinstance(grenade.location, Item) and hasattr(grenade.db, 'stuck_to_armor')
                    
                    if is_stuck:
                        # Grenade stuck to armor - send dramatic warnings
                        armor = grenade.location
                        stuck_location = getattr(grenade.db, 'stuck_to_location', 'unknown')
                        
                        # Check if armor is worn
                        if armor.location and isinstance(armor.location, Character):
                            wearer = armor.location
                            # Warning to wearer
                            wearer.msg(f"|R*** {remaining} SECONDS ***|n {grenade.key} magnetically clamped to your {armor.key}!")
                            
                            # Warning to room
                            if wearer.location:
                                wearer.location.msg_contents(
                                    f"|y{wearer.key} has a live {grenade.key} magnetically stuck to their {armor.key}! {remaining} seconds remaining!|n",
                                    exclude=wearer
                                )
                        else:
                            # Armor on ground with stuck grenade
                            room = armor.location
                            if room:
                                room.msg_contents(
                                    f"|yA {grenade.key} magnetically stuck to a {armor.key} ticks down: {remaining} seconds!|n"
                                )
                    
                    # Schedule next tick
                    timer = utils.delay(1, tick)
                    setattr(grenade.ndb, NDB_GRENADE_TIMER, timer)
                    
                    if splattercast:
                        splattercast.msg(f"{DEBUG_PREFIX_THROW}_TICKER: {grenade.key} scheduled next tick, {remaining}s remaining, stuck={is_stuck}")
                
                elif remaining == 1:
                    # Final countdown - explode next tick
                    setattr(grenade.ndb, NDB_COUNTDOWN_REMAINING, 0)
                    
                    # Create a proper closure that captures the explosion function
                    def trigger_explosion():
                        try:
                            splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
                            splattercast.msg(f"{DEBUG_PREFIX_THROW}_TICKER: Triggering explosion for {grenade.key}")
                            explode_standalone_grenade(grenade)
                        except Exception as e:
                            splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
                            splattercast.msg(f"{DEBUG_PREFIX_THROW}_TICKER_ERROR: Error in trigger_explosion: {e}")
                    
                    timer = utils.delay(1, trigger_explosion)
                    setattr(grenade.ndb, NDB_GRENADE_TIMER, timer)
                    
                    if splattercast:
                        splattercast.msg(f"{DEBUG_PREFIX_THROW}_TICKER: {grenade.key} final countdown - explosion scheduled")
                
                else:
                    # Should not reach here - explosion should have been triggered
                    if splattercast:
                        splattercast.msg(f"{DEBUG_PREFIX_THROW}_TICKER_ERROR: {grenade.key} reached 0 without explosion - triggering now")
                    explode_standalone_grenade(grenade)
                    
            except Exception as e:
                # Failsafe - if ticker fails, explode immediately to avoid duds
                splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
                if splattercast:
                    splattercast.msg(f"{DEBUG_PREFIX_THROW}_TICKER_ERROR: Ticker error for {grenade.key}: {e} - triggering explosion")
                try:
                    explode_standalone_grenade(grenade)
                except:
                    pass  # If even explosion fails, give up gracefully
        
        # Start the ticker
        tick()
    
    def explode_grenade(self, grenade):
        """Handle grenade explosion."""
        try:
            # Check dud chance
            dud_chance = getattr(grenade.db, DB_DUD_CHANCE, 0.0)
            if random.random() < dud_chance:
                self.handle_dud(grenade)
                return
            
            # Get blast damage
            blast_damage = getattr(grenade.db, DB_BLAST_DAMAGE, 10)
            
            # Check if grenade is in someone's inventory when it explodes
            # Use typeclass check to distinguish characters (PCs and NPCs) from rooms
            holder = None
            if grenade.location:
                from typeclasses.characters import Character
                if isinstance(grenade.location, Character):
                    # Grenade is in a character's inventory - they're holding it!
                    # This works for both PCs and NPCs, regardless of hands/account status
                    holder = grenade.location
            
            # Get proximity list
            # Get unified proximity list (includes current grappling relationships)
            proximity_list = get_unified_explosion_proximity(grenade)
            
            # Handle explosion in someone's hands (much more dangerous!)
            if holder:
                # Explosion in hands - double damage and guaranteed hit
                holder_damage = blast_damage * 2
                damage_type = getattr(grenade.db, 'damage_type', 'blast')  # Explosive damage type
                holder.take_damage(holder_damage, location="chest", injury_type=damage_type)
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
                        damage_type = getattr(grenade.db, 'damage_type', 'blast')
                        character.take_damage(reduced_damage, location="chest", injury_type=damage_type)
                        character.msg(MSG_GRENADE_DAMAGE.format(grenade=grenade.key))
                        
            else:
                # Normal room explosion
                splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
                if grenade.location:
                    explosion_msg = MSG_GRENADE_EXPLODE_ROOM.format(grenade=grenade.key)
                    splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Sending explosion message to room {grenade.location}: {explosion_msg}")
                    grenade.location.msg_contents(explosion_msg)
                    # Notify adjacent rooms
                    notify_adjacent_rooms_of_explosion(grenade.location)
                    splattercast.msg(f"{DEBUG_PREFIX_THROW}_SUCCESS: Explosion message sent to {grenade.location}")
                else:
                    splattercast.msg(f"{DEBUG_PREFIX_THROW}_ERROR: Grenade has no location for explosion message")
                
                # Check for human shield mechanics
                from world.combat.utils import check_grenade_human_shield
                damage_modifiers = check_grenade_human_shield(proximity_list)
                
                # Apply damage to all in proximity with human shield modifiers
                splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Processing proximity list for damage: {[char.key if hasattr(char, 'key') else str(char) for char in proximity_list]}")
                for character in proximity_list:
                    if hasattr(character, 'msg'):  # Is a character
                        # Apply damage modifier (0.0 for grapplers, 2.0 for victims, 1.0 for others)
                        modifier = damage_modifiers.get(character, 1.0)
                        final_damage = int(blast_damage * modifier)
                        
                        if final_damage > 0:
                            damage_type = getattr(grenade.db, 'damage_type', 'blast')
                            character.take_damage(final_damage, location="chest", injury_type=damage_type)
                            character.msg(MSG_GRENADE_DAMAGE.format(grenade=grenade.key))
                            if character.location:
                                character.location.msg_contents(
                                    MSG_GRENADE_DAMAGE_ROOM.format(victim=character.key, grenade=grenade.key),
                                    exclude=character
                                )
                        # Note: Characters with 0.0 modifier (grapplers) take no damage and get no damage messages
            
            # Handle chain reactions
            self.handle_chain_reactions(grenade)
            
            # Clean up
            grenade.delete()
            
        except Exception as e:
            splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_ERROR: Error in explode_grenade: {e}")
    
    def handle_dud(self, grenade):
        """Handle grenade dud (failure to explode)."""
        if grenade.location:
            grenade.location.msg_contents(MSG_GRENADE_DUD_ROOM.format(grenade=grenade.key))
        
        # Clear timer state but keep grenade
        setattr(grenade.ndb, NDB_COUNTDOWN_REMAINING, 0)
        if hasattr(grenade.ndb, NDB_GRENADE_TIMER):
            delattr(grenade.ndb, NDB_GRENADE_TIMER)
    
    def handle_chain_reactions(self, exploding_grenade):
        """Handle chain reactions with other explosives."""
        if not getattr(exploding_grenade.db, DB_CHAIN_TRIGGER, False):
            return
        
        # Find other explosives in proximity
        proximity_list = getattr(exploding_grenade.ndb, NDB_PROXIMITY_UNIVERSAL, [])
        if proximity_list is None:
            proximity_list = []
        
        for obj in proximity_list:
            if (hasattr(obj, 'db') and 
                getattr(obj.db, DB_IS_EXPLOSIVE, False) and 
                obj != exploding_grenade):
                
                        # Trigger chain explosion with new ticker system
                        if exploding_grenade.location:
                            exploding_grenade.location.msg_contents(
                                MSG_GRENADE_CHAIN_TRIGGER.format(grenade=obj.key))
                        
                        # Set short timer and start ticker
                        setattr(obj.db, DB_PIN_PULLED, True)
                        setattr(obj.ndb, NDB_COUNTDOWN_REMAINING, 1)  # 1 second for chain reaction
                        self.start_grenade_ticker(obj)
class CmdCatch(Command):
    """
    Catch thrown objects out of the air.
    
    Usage:
        catch <object>
    
    Examples:
        catch grenade
        catch knife
    
    Attempt to catch objects that are currently flying through the air.
    Requires at least one free hand. Useful for catching and re-throwing
    live grenades or intercepting thrown weapons.
    """
    
    key = "catch"
    locks = "cmd:all()"
    help_category = "Combat"
    
    def func(self):
        """Execute catch command."""
        if not self.args:
            self.caller.msg(MSG_CATCH_WHAT)
            return
        
        object_name = self.args.strip()
        
        # Check for hands at all
        caller_hands = getattr(self.caller, 'hands', None)
        if caller_hands is None or not caller_hands:
            self.caller.msg(MSG_CATCH_NO_HANDS_AT_ALL)
            return
        
        # Check for free hands
        free_hand = None
        for hand_name, wielded_obj in caller_hands.items():
            if wielded_obj is None:
                free_hand = hand_name
                break
        
        if not free_hand:
            self.caller.msg(MSG_CATCH_NO_FREE_HANDS)
            return
        
        # Find flying object in current room with robust null safety
        flying_objects = getattr(self.caller.location.ndb, NDB_FLYING_OBJECTS, None)
        if not flying_objects or not isinstance(flying_objects, list):
            flying_objects = []
        
        target_obj = None
        for obj in flying_objects:
            if object_name.lower() in obj.key.lower():
                target_obj = obj
                break
        
        if not target_obj:
            self.caller.msg(MSG_CATCH_OBJECT_NOT_FOUND.format(object=object_name))
            return
        
        # Attempt catch (simple success/fail)
        catch_chance = 0.6  # 60% base catch chance
        
        if random.random() <= catch_chance:
            # Success - catch object
            self.catch_object(target_obj, free_hand)
        else:
            # Failure - object continues flight
            self.caller.msg(MSG_CATCH_FAILED.format(object=target_obj.key))
            self.caller.location.msg_contents(
                MSG_CATCH_FAILED_ROOM.format(catcher=self.caller.key, object=target_obj.key),
                exclude=self.caller
            )
    
    def catch_object(self, obj, hand_name):
        """Successfully catch the object."""
        # Remove from flying objects
        flying_objects = getattr(self.caller.location.ndb, NDB_FLYING_OBJECTS, [])
        if obj in flying_objects:
            flying_objects.remove(obj)
        
        # Cancel flight timer by moving to caller and wielding
        obj.move_to(self.caller)
        caller_hands = getattr(self.caller, 'hands', {})
        caller_hands[hand_name] = obj
        
        # Announce success
        self.caller.msg(MSG_CATCH_SUCCESS.format(object=obj.key))
        self.caller.location.msg_contents(
            MSG_CATCH_SUCCESS_ROOM.format(catcher=self.caller.key, object=obj.key),
            exclude=self.caller
        )
        
        # Clean up flight data
        if hasattr(obj.ndb, 'flight_destination'):
            del obj.ndb.flight_destination
        if hasattr(obj.ndb, 'flight_target'):
            del obj.ndb.flight_target
        if hasattr(obj.ndb, 'flight_origin'):
            del obj.ndb.flight_origin
        if hasattr(obj.ndb, 'flight_is_weapon'):
            del obj.ndb.flight_is_weapon
        if hasattr(obj.ndb, 'flight_thrower'):
            del obj.ndb.flight_thrower
        if hasattr(obj.ndb, 'flight_timer'):
            # Cancel the pending flight timer so the object doesn't
            # "arrive" or explode after being caught
            try:
                obj.ndb.flight_timer.cancel()
            except Exception:
                pass  # Timer may have already fired
            del obj.ndb.flight_timer
        
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        if splattercast:
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_SUCCESS: {self.caller} caught {obj} mid-flight")


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
        if not getattr(grenade.db, DB_IS_EXPLOSIVE, False):
            self.caller.msg(MSG_RIG_NOT_EXPLOSIVE.format(object=grenade.key))
            return
        
        # Check if pin is NOT pulled (should be unpinned for rigging)
        if getattr(grenade.db, DB_PIN_PULLED, False):
            self.caller.msg(MSG_RIG_ALREADY_PINNED)
            return
        
        # Find exit
        exit_search = self.caller.search(self.exit_name, location=self.caller.location, quiet=True)
        exit_obj = exit_search[0] if exit_search else None
        if not exit_obj or not hasattr(exit_obj, 'destination') or not exit_obj.destination:
            self.caller.msg(MSG_RIG_INVALID_EXIT.format(exit=self.exit_name))
            return
        
        # Check if exit already rigged
        existing_rigged = getattr(exit_obj.db, 'rigged_grenade', None)
        if existing_rigged:
            self.caller.msg(MSG_RIG_EXIT_ALREADY_RIGGED)
            return
        
        # Check if return exit is already rigged too
        return_exit = self.find_return_exit_for_check(exit_obj)
        if return_exit and getattr(return_exit.db, 'rigged_grenade', None):
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
        setattr(exit_obj.db, 'rigged_grenade', grenade)
        setattr(grenade.db, 'rigged_to_exit', exit_obj)
        setattr(grenade.db, 'rigged_by', self.caller)  # Store who rigged it for immunity
        
        # Add integration description for rigged grenade
        # Store original integration state if not already stored
        if not hasattr(grenade.db, 'original_integrate'):
            grenade.db.original_integrate = getattr(grenade.db, 'integrate', False)
        if not hasattr(grenade.db, 'original_integration_desc'):
            grenade.db.original_integration_desc = getattr(grenade.db, 'integration_desc', None)
        if not hasattr(grenade.db, 'original_integration_priority'):
            grenade.db.original_integration_priority = getattr(grenade.db, 'integration_priority', None)
        
        # Enable integration and set rigging description with priority
        grenade.db.integrate = True
        grenade.db.integration_desc = f"A |C{grenade.get_display_name(self.caller)}|n is rigged to the {exit_obj.key} exit with a barely visible trip wire."
        grenade.db.integration_priority = 3  # High priority for rigged grenades
        
        # Find and rig the return exit too
        return_exit = self.find_return_exit(exit_obj)
        if return_exit:
            setattr(return_exit.db, 'rigged_grenade', grenade)
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
    from evennia.comms.models import ChannelDB
    splattercast = ChannelDB.objects.get_channel("Splattercast")
    
    # Check if there's a rigged grenade on this exit
    rigged_grenade = getattr(exit_obj.db, 'rigged_grenade', None)
    
    if not rigged_grenade:
        return False
    
    # Check if this character is the rigger (immunity)
    rigger = getattr(rigged_grenade.db, 'rigged_by', None)
    
    if rigger and character == rigger:
        return False  # Rigger is immune to their own trap
    
    # Trigger the rigged grenade
    character.msg(MSG_RIG_TRIGGERED.format(object=rigged_grenade.key))
    character.location.msg_contents(
        MSG_RIG_TRIGGERED_ROOM.format(object=rigged_grenade.key, victim=character.key),
        exclude=character
    )
    
    # Pull the pin and start countdown timer when triggered
    setattr(rigged_grenade.db, DB_PIN_PULLED, True)
    fuse_time = 1  # Rigged grenades explode almost immediately
    setattr(rigged_grenade.ndb, NDB_COUNTDOWN_REMAINING, fuse_time)
    
    # Move grenade to the character's location quietly (no movement announcements)
    rigged_grenade.move_to(character.location, quiet=True)
    
    # FOR STICKY GRENADES: Find most magnetic target and attempt to stick
    # FOR REGULAR GRENADES: Just establish proximity with trigger character
    is_sticky = getattr(rigged_grenade.db, 'is_sticky', False)
    sticky_target = None
    
    if is_sticky:
        # Use the existing CmdThrow's magnetic targeting logic
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
            dud_chance = getattr(rigged_grenade.db, DB_DUD_CHANCE, 0.0)
            if random.random() < dud_chance:
                if rigged_grenade.location:
                    rigged_grenade.location.msg_contents(MSG_GRENADE_DUD_ROOM.format(grenade=rigged_grenade.key))
                return
            
            # Get blast damage
            blast_damage = getattr(rigged_grenade.db, DB_BLAST_DAMAGE, 10)
            
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
                        damage_type = getattr(rigged_grenade.db, 'damage_type', 'blast')
                        other_character.take_damage(final_damage, location="chest", injury_type=damage_type)
                        other_character.msg(MSG_GRENADE_DAMAGE.format(grenade=rigged_grenade.key))
                        if other_character.location:
                            other_character.location.msg_contents(
                                MSG_GRENADE_DAMAGE_ROOM.format(victim=other_character.key, grenade=rigged_grenade.key),
                                exclude=other_character
                            )
                    # Note: Characters with 0.0 modifier (grapplers) take no damage and get no damage messages
            
            # Handle chain reactions if enabled
            if getattr(rigged_grenade.db, DB_CHAIN_TRIGGER, False):
                for obj in proximity_list:
                    if (hasattr(obj, 'db') and 
                        getattr(obj.db, DB_IS_EXPLOSIVE, False) and 
                        obj != rigged_grenade):
                        
                        # Trigger chain explosion
                        if rigged_grenade.location:
                            rigged_grenade.location.msg_contents(
                                MSG_GRENADE_CHAIN_TRIGGER.format(grenade=obj.key))
                        
                        # Start immediate explosion timer with new ticker system
                        setattr(obj.db, DB_PIN_PULLED, True)
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
    delattr(exit_obj.db, 'rigged_grenade')
    
    # Find and clean up return exit too
    original_exit = getattr(rigged_grenade.db, 'rigged_to_exit', None)
    if original_exit and original_exit.destination:
        destination_room = original_exit.destination
        character_room = character.location
        
        # Look for return exit that might also be rigged
        for obj in destination_room.contents:
            if (hasattr(obj, 'destination') and 
                obj.destination == character_room and
                hasattr(obj.db, 'rigged_grenade') and
                getattr(obj.db, 'rigged_grenade') == rigged_grenade):
                delattr(obj.db, 'rigged_grenade')
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
            except:
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
        dud_chance = getattr(grenade.db, DB_DUD_CHANCE, 0.0)
        splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Dud chance: {dud_chance}")
        if random.random() < dud_chance:
            splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Grenade {grenade} is a dud")
            if grenade.location:
                grenade.location.msg_contents(MSG_GRENADE_DUD_ROOM.format(grenade=grenade.key))
            return
        
        splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Grenade {grenade} is not a dud, proceeding with explosion")
        
        splattercast.msg(f"{DEBUG_PREFIX_THROW}_DEBUG: Grenade {grenade} is not a dud, proceeding with explosion")
        
        # Get blast damage
        blast_damage = getattr(grenade.db, DB_BLAST_DAMAGE, 10)
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
            damage_type = getattr(grenade.db, 'damage_type', 'blast')  # Explosive damage type
            holder.take_damage(holder_damage, location="chest", injury_type=damage_type)
            
            # Different messages for sticky vs normal grenades
            if stuck_to_armor:
                # Sticky grenade stuck to armor they're wearing
                stuck_location = getattr(grenade.db, 'stuck_to_location', 'body')
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
                    damage_type = getattr(grenade.db, 'damage_type', 'blast')
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
                        damage_type = getattr(grenade.db, 'damage_type', 'blast')
                        character.take_damage(final_damage, location="chest", injury_type=damage_type)
                        character.msg(MSG_GRENADE_DAMAGE.format(grenade=grenade.key))
                        if character.location:
                            character.location.msg_contents(
                                MSG_GRENADE_DAMAGE_ROOM.format(victim=character.key, grenade=grenade.key),
                                exclude=character
                            )
                    # Note: Characters with 0.0 modifier (grapplers) take no damage and get no damage messages
        
        # Handle chain reactions
        if getattr(grenade.db, DB_CHAIN_TRIGGER, False):
            for obj in proximity_list:
                if (hasattr(obj, 'db') and 
                    getattr(obj.db, DB_IS_EXPLOSIVE, False) and 
                    obj != grenade):
                    
                    # Trigger chain explosion
                    if grenade.location:
                        grenade.location.msg_contents(
                            MSG_GRENADE_CHAIN_TRIGGER.format(grenade=obj.key))
                    
                    # Start chain reaction with new ticker system
                    setattr(obj.db, DB_PIN_PULLED, True)
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
            if not getattr(obj.db, DB_IS_EXPLOSIVE, False):
                continue
                
            # Check if grenade is live (pin pulled and timer active)
            pin_pulled = getattr(obj.db, DB_PIN_PULLED, False)
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
        setattr(grenade.db, DB_PIN_PULLED, False)  # Grenade is now safe
        
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
        dud_chance = getattr(grenade.db, DB_DUD_CHANCE, 0.0)
        if random.random() < dud_chance:
            if grenade.location:
                grenade.location.msg_contents(MSG_GRENADE_DUD_ROOM.format(grenade=grenade.key))
            return
        
        # Get blast damage
        blast_damage = getattr(grenade.db, DB_BLAST_DAMAGE, 10)
        
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
                    damage_type = getattr(grenade.db, 'damage_type', 'blast')
                    character.take_damage(final_damage, location="chest", injury_type=damage_type)
                    character.msg(MSG_GRENADE_DAMAGE.format(grenade=grenade.key))
                    if character.location:
                        character.location.msg_contents(
                            MSG_GRENADE_DAMAGE_ROOM.format(victim=character.key, grenade=grenade.key),
                            exclude=character
                        )
                # Note: Characters with 0.0 modifier (grapplers) take no damage and get no damage messages
        
        # Handle chain reactions if enabled
        if getattr(grenade.db, DB_CHAIN_TRIGGER, False):
            for obj in proximity_list:
                if (hasattr(obj, 'db') and 
                    getattr(obj.db, DB_IS_EXPLOSIVE, False) and 
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
                getattr(obj.db, DB_IS_EXPLOSIVE, False)):
                
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
                getattr(obj.db, DB_IS_EXPLOSIVE, False)):
                
                # Check if grenade is live (either pin pulled OR rigged to exit)
                pin_pulled = getattr(obj.db, DB_PIN_PULLED, False)
                is_rigged = getattr(obj.db, 'rigged_to_exit', None) is not None
                
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
        if not getattr(grenade.db, DB_IS_EXPLOSIVE, False):
            self.caller.msg(f"The {grenade.key} is not an explosive device.")
            return False
        
        # Must be live (pin pulled OR rigged)
        pin_pulled = getattr(grenade.db, DB_PIN_PULLED, False)
        is_rigged = getattr(grenade.db, 'rigged_to_exit', None) is not None
        
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
        is_rigged = getattr(grenade.db, 'rigged_to_exit', None) is not None
        
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
        setattr(grenade.db, DB_PIN_PULLED, False)  # Grenade is now safe
        
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
        rigged_to_exit = getattr(grenade.db, 'rigged_to_exit', None)
        if rigged_to_exit:
            splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
            
            # Clean up main exit
            if hasattr(rigged_to_exit.db, 'rigged_grenade'):
                delattr(rigged_to_exit.db, 'rigged_grenade')
                if splattercast:
                    splattercast.msg(f"DEFUSE_CLEANUP: Removed rigging from {rigged_to_exit}")
            
            # Find and clean up return exit
            if rigged_to_exit.destination:
                destination_room = rigged_to_exit.destination
                grenade_room = grenade.location if hasattr(grenade, 'location') else self.caller.location
                
                for obj in destination_room.contents:
                    if (hasattr(obj, 'destination') and 
                        obj.destination == grenade_room and
                        hasattr(obj.db, 'rigged_grenade') and
                        getattr(obj.db, 'rigged_grenade') == grenade):
                        delattr(obj.db, 'rigged_grenade')
                        if splattercast:
                            splattercast.msg(f"DEFUSE_CLEANUP: Removed rigging from return exit {obj}")
                        break
            
            # Clean up grenade's rigging reference
            delattr(grenade.db, 'rigged_to_exit')
            if hasattr(grenade.db, 'rigged_by'):
                delattr(grenade.db, 'rigged_by')
            
            # Restore original integration state
            if hasattr(grenade.db, 'original_integrate'):
                grenade.db.integrate = grenade.db.original_integrate
                delattr(grenade.db, 'original_integrate')
            else:
                # Default: disable integration for regular grenades
                grenade.db.integrate = False
                
            if hasattr(grenade.db, 'original_integration_desc'):
                if grenade.db.original_integration_desc is not None:
                    grenade.db.integration_desc = grenade.db.original_integration_desc
                else:
                    # Remove integration_desc if it wasn't set originally
                    if hasattr(grenade.db, 'integration_desc'):
                        delattr(grenade.db, 'integration_desc')
                delattr(grenade.db, 'original_integration_desc')
                
            if hasattr(grenade.db, 'original_integration_priority'):
                if grenade.db.original_integration_priority is not None:
                    grenade.db.integration_priority = grenade.db.original_integration_priority
                else:
                    # Remove integration_priority if it wasn't set originally
                    if hasattr(grenade.db, 'integration_priority'):
                        delattr(grenade.db, 'integration_priority')
                delattr(grenade.db, 'original_integration_priority')
            
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
            dud_chance = getattr(grenade.db, DB_DUD_CHANCE, 0.0)
            if random.random() < dud_chance:
                if grenade.location:
                    grenade.location.msg_contents(MSG_GRENADE_DUD_ROOM.format(grenade=grenade.key))
                return
            
            # Get blast damage
            blast_damage = getattr(grenade.db, DB_BLAST_DAMAGE, 10)
            
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
                        damage_type = getattr(grenade.db, 'damage_type', 'blast')
                        character.take_damage(final_damage, location="chest", injury_type=damage_type)
                        character.msg(MSG_GRENADE_DAMAGE.format(grenade=grenade.key))
                        if character.location:
                            character.location.msg_contents(
                                MSG_GRENADE_DAMAGE_ROOM.format(victim=character.key, grenade=grenade.key),
                                exclude=character
                            )
                    # Note: Characters with 0.0 modifier (grapplers) take no damage and get no damage messages
            
            # Handle chain reactions if enabled
            if getattr(grenade.db, DB_CHAIN_TRIGGER, False):
                for obj in proximity_list:
                    if (hasattr(obj, 'db') and 
                        getattr(obj.db, DB_IS_EXPLOSIVE, False) and 
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
        if not getattr(explosive.db, DB_IS_EXPLOSIVE, False):
            caller.msg(f"{explosive.key} is not an explosive device.")
            return
        
        # Find detonator
        detonator = caller.search(detonator_name, location=caller)
        if not detonator:
            return
        
        # Validate detonator type
        if not hasattr(detonator.db, 'device_type') or detonator.db.device_type != "remote_detonator":
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
        if not hasattr(detonator.db, 'device_type') or detonator.db.device_type != "remote_detonator":
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
        if getattr(explosive.db, DB_PIN_PULLED, False):
            caller.msg(f"|y{explosive.key} is already detonating!|n")
            return
        
        # Pull the pin remotely
        setattr(explosive.db, DB_PIN_PULLED, True)
        fuse_time = getattr(explosive.db, DB_FUSE_TIME, 8)
        setattr(explosive.ndb, NDB_COUNTDOWN_REMAINING, fuse_time)
        
        # Start countdown using CmdPull's grenade ticker system
        # Create temporary CmdPull instance to access start_grenade_ticker
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
            if getattr(explosive.db, DB_PIN_PULLED, False):
                already_active_count += 1
                continue
            
            # Pull the pin remotely
            setattr(explosive.db, DB_PIN_PULLED, True)
            fuse_time = getattr(explosive.db, DB_FUSE_TIME, 8)
            setattr(explosive.ndb, NDB_COUNTDOWN_REMAINING, fuse_time)
            
            # Start countdown
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
                    if (held_item and hasattr(held_item.db, 'device_type') and 
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
        if not hasattr(detonator.db, 'device_type') or detonator.db.device_type != "remote_detonator":
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
            if getattr(explosive.db, DB_PIN_PULLED, False):
                countdown = getattr(explosive.ndb, NDB_COUNTDOWN_REMAINING, 0)
                if getattr(explosive.db, 'stuck_to_armor', None):
                    status = f"|RSTUCK|n"
                else:
                    status = f"|YACTIVE|n"
                fuse_str = f"|R{countdown}s left!|n"
            elif getattr(explosive.db, 'rigged_to_exit', None) is not None:
                status = f"|yTRAP|n"
                fuse_time = getattr(explosive.db, DB_FUSE_TIME, 8)
                fuse_str = f"{fuse_time}s (trap)"
            else:
                status = f"|gREADY|n"
                fuse_time = getattr(explosive.db, DB_FUSE_TIME, 8)
                fuse_str = f"{fuse_time}s"
            
            # Get location
            if not explosive.location:
                loc_str = "|xVoid|n"
            elif explosive.location == caller:
                loc_str = "Your inventory"
            elif hasattr(explosive.location, 'key'):
                # Check if stuck to armor
                if getattr(explosive.db, 'stuck_to_armor', None):
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
                if (held_item and hasattr(held_item.db, 'device_type') and 
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
        if not hasattr(detonator.db, 'device_type') or detonator.db.device_type != "remote_detonator":
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
                if hasattr(explosive_obj.db, 'scanned_by_detonator'):
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
