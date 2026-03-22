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
        if obj.db.is_throwing_weapon:
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
                combatants_list = handler.db.combatants or []
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
                blast_damage = obj.db.blast_damage if obj.db.blast_damage is not None else 10
                damage_type = obj.db.damage_type if obj.db.damage_type is not None else 'blast'  # Changed to 'blast' for explosive damage
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
            if hasattr(self, 'obj_to_throw') and self.obj_to_throw.db.is_sticky:
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
                    if hasattr(self, 'obj_to_throw') and self.obj_to_throw.db.is_sticky:
                        target = self.select_most_magnetic_target_in_room(destination, self.obj_to_throw)
                        if not target:  # No viable magnetic targets, select random
                            target = self.select_random_target_in_room(destination)
                    else:
                        target = self.select_random_target_in_room(destination)
                    return destination, target
            
            # Fallback to current room
            # For sticky grenades in current room, prefer most magnetic character, fallback to random
            if hasattr(self, 'obj_to_throw') and self.obj_to_throw.db.is_sticky:
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
        magnetic_strength = grenade.db.magnetic_strength if grenade.db.magnetic_strength is not None else 5
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
            metal_level = armor.db.metal_level or 0
            magnetic_level = armor.db.magnetic_level or 0
            
            # Check if plate carrier - use installed plates' values
            is_plate_carrier = bool(armor.db.is_plate_carrier)
            if is_plate_carrier:
                installed_plates = armor.db.installed_plates or {}
                for slot, plate_ref in installed_plates.items():
                    if plate_ref:
                        plate_metal = plate_ref.db.metal_level or 0
                        plate_magnetic = plate_ref.db.magnetic_level or 0
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
        return bool(obj.db.is_throwing_weapon)
    
    def is_explosive(self, obj):
        """Check if object is explosive."""
        return bool(obj.db.is_explosive)
    
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
                        except Exception:
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
            except Exception:
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
            elif target and not is_weapon and obj.db.is_sticky:
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
                is_sticky = bool(weapon.db.is_sticky)
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
                base_damage = weapon.db.damage if weapon.db.damage is not None else 1
                total_damage = random.randint(1, 6) + base_damage
                damage_type = weapon.db.damage_type if weapon.db.damage_type is not None else 'blunt'  # Get weapon damage type
                
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
            if grenade.db.impact_detonation:
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
                    combatants_list = handler.db.combatants or []
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
            weapon_bonus = melee_weapon.db.deflection_bonus if melee_weapon.db.deflection_bonus is not None else 0.0  # Optional weapon property
            
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
        is_ranged = bool(obj.db.is_ranged)
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
        if not grenade.db.is_explosive:
            self.caller.msg(MSG_PULL_NOT_EXPLOSIVE.format(object=grenade.key))
            return
        
        # Check if requires pin
        requires_pin = grenade.db.requires_pin if grenade.db.requires_pin is not None else True
        if not requires_pin:
            self.caller.msg(MSG_PULL_NO_PIN_REQUIRED.format(object=grenade.key))
            return
        
        # Check if already pulled
        if grenade.db.pin_pulled:
            self.caller.msg(MSG_PULL_ALREADY_PULLED.format(object=grenade.key))
            return
        
        # Pull pin and start timer
        self.pull_pin(grenade)
    
    def pull_pin(self, grenade):
        """Pull the pin and start countdown."""
        # Set pin pulled flag
        grenade.db.pin_pulled = True
        
        # Get fuse time
        fuse_time = grenade.db.fuse_time if grenade.db.fuse_time is not None else 8
        
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
                    is_stuck = isinstance(grenade.location, Item) and grenade.db.stuck_to_armor is not None
                    
                    if is_stuck:
                        # Grenade stuck to armor - send dramatic warnings
                        armor = grenade.location
                        stuck_location = grenade.db.stuck_to_location or 'unknown'
                        
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
                except Exception:
                    pass  # If even explosion fails, give up gracefully
        
        # Start the ticker
        tick()
    
    def explode_grenade(self, grenade):
        """Handle grenade explosion."""
        try:
            # Check dud chance
            dud_chance = grenade.db.dud_chance if grenade.db.dud_chance is not None else 0.0
            if random.random() < dud_chance:
                self.handle_dud(grenade)
                return
            
            # Get blast damage
            blast_damage = grenade.db.blast_damage if grenade.db.blast_damage is not None else 10
            
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
                damage_type = grenade.db.damage_type if grenade.db.damage_type is not None else 'blast'  # Explosive damage type
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
                        damage_type = grenade.db.damage_type if grenade.db.damage_type is not None else 'blast'
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
        if not exploding_grenade.db.chain_trigger:
            return
        
        # Find other explosives in proximity
        proximity_list = getattr(exploding_grenade.ndb, NDB_PROXIMITY_UNIVERSAL, [])
        if proximity_list is None:
            proximity_list = []
        
        for obj in proximity_list:
            if (hasattr(obj, 'db') and 
                obj.db.is_explosive and 
                obj != exploding_grenade):
                
                        # Trigger chain explosion with new ticker system
                        if exploding_grenade.location:
                            exploding_grenade.location.msg_contents(
                                MSG_GRENADE_CHAIN_TRIGGER.format(grenade=obj.key))
                        
                        # Set short timer and start ticker
                        obj.db.pin_pulled = True
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


# ---------------------------------------------------------------------------
# Backward-compatible re-exports
# ---------------------------------------------------------------------------
# These names were originally defined here but have been extracted to focused
# modules.  Re-exporting them keeps existing ``from commands.CmdThrow import …``
# statements working while consumers are gradually migrated.

from commands.CmdExplosives import (  # noqa: F401 – re-export
    CmdRig,
    CmdDefuse,
    CmdScan,
    CmdDetonate,
    CmdDetonateList,
    CmdClearDetonator,
)

from commands.explosion_utils import (  # noqa: F401 – re-export
    notify_adjacent_rooms_of_explosion,
    check_rigged_grenade,
    start_standalone_grenade_ticker,
    get_unified_explosion_proximity,
    explode_standalone_grenade,
    check_auto_defuse,
    attempt_auto_defuse,
    handle_auto_defuse_success,
    handle_auto_defuse_failure,
    trigger_auto_defuse_explosion,
)
