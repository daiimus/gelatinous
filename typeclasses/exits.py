"""
Exits

Exits are connectors between Rooms. An exit always has a destination property
set and has a single command defined on itself with the same name as its key,
for allowing Characters to traverse the exit to its destination.

"""

from evennia.objects.objects import DefaultExit
from evennia.comms.models import ChannelDB
from world.combat.handler import get_or_create_combat 
from world.combat.constants import SPLATTERCAST_CHANNEL, DB_CHAR, NDB_PROXIMITY_UNIVERSAL 


from .objects import ObjectParent

class Exit(DefaultExit):
    """
    Exits are connectors between rooms. Exits are normal Objects except
    they define the `destination` property and override some hooks
    and methods to represent the exits.
    """

    def at_object_creation(self):
        super().at_object_creation()
        # Add abbreviation aliases for cardinal directions
        cardinal_aliases = {
            "north": "n",
            "south": "s",
            "east": "e",
            "west": "w",
            "northeast": "ne",
            "northwest": "nw",
            "southeast": "se",
            "southwest": "sw",
            "up": "u",
            "down": "d",
            "in": "in",
            "out": "out"
        }
        alias = cardinal_aliases.get(self.key.lower())
        if alias and alias not in self.aliases.all():
            self.aliases.add(alias)

    def return_appearance(self, looker, **kwargs):
        """
        This is called when someone does 'look w' - show the sophisticated exit examination.
        Uses our own get_display_desc method which includes weather, crowd, and character integration.
        """
        return self.get_display_desc(looker, **kwargs)

    def at_traverse(self, traversing_object, target_location):
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        
        # --- SKY ROOM RESTRICTION CHECK ---
        # Block normal traversal to/from sky rooms - these are transit-only spaces
        # Exception: Allow jump command system to use sky rooms for aerial transit
        current_room_is_sky = traversing_object.location.db.is_sky_room
        target_room_is_sky = target_location.db.is_sky_room
        is_jump_movement = getattr(traversing_object.ndb, "jump_movement_allowed", False)
        
        if (current_room_is_sky or target_room_is_sky) and not is_jump_movement:
            if current_room_is_sky and target_room_is_sky:
                traversing_object.msg(f"|rYou cannot traverse between sky rooms! Sky rooms are transit-only spaces.|n")
            elif current_room_is_sky:
                traversing_object.msg(f"|rYou cannot leave sky rooms through normal movement! You are falling - wait for gravity to take effect.|n")
            elif target_room_is_sky:
                traversing_object.msg(f"|rYou cannot enter sky rooms through normal movement! Use jump commands to access aerial transit.|n")
            
            splattercast.msg(f"SKY_ROOM_BLOCK: {traversing_object.key} attempted normal traversal from {traversing_object.location.key} (sky={current_room_is_sky}) to {target_location.key} (sky={target_room_is_sky}). Blocked.")
            return  # Block traversal
        # --- END SKY ROOM RESTRICTION CHECK ---
        
        # --- EDGE/GAP RESTRICTION CHECK ---
        # Block normal traversal of edge and gap exits - these require jump command
        is_edge = self.db.is_edge
        is_gap = self.db.is_gap
        
        if is_edge or is_gap:
            if is_edge and is_gap:
                traversing_object.msg(f"|rYou cannot simply walk to the {self.key} - it's an edge with a gap! Use 'jump off {self.key} edge' or 'jump across {self.key} edge' instead.|n")
            elif is_edge:
                traversing_object.msg(f"|rYou cannot simply walk to the {self.key} - it's an edge! Use 'jump off {self.key} edge' to descend.|n")
            elif is_gap:
                traversing_object.msg(f"|rYou cannot simply walk to the {self.key} - it's a gap! Use 'jump across {self.key} edge' to leap across.|n")
            
            splattercast.msg(f"EDGE_GAP_BLOCK: {traversing_object.key} attempted normal traversal of {self.key} (is_edge={is_edge}, is_gap={is_gap}). Blocked.")
            return  # Block traversal
        # --- END EDGE/GAP RESTRICTION CHECK ---
        
        # --- SACRIFICE RESTRICTION CHECK ---
        # Check if traversing character is performing sacrifice
        if getattr(traversing_object.ndb, "performing_sacrifice", False):
            traversing_object.msg("|rYou cannot move while performing a heroic sacrifice!|n")
            splattercast.msg(f"SACRIFICE BLOCK: {traversing_object.key} attempted to traverse {self.key} while performing sacrifice.")
            return
        # --- END SACRIFICE RESTRICTION CHECK ---
        
        # --- AIMING LOCK CHECK ---
        aimer = getattr(traversing_object.ndb, "aimed_at_by", None)
        if aimer:
            # Check if the aimer is still valid and in the same location
            if not aimer.location or aimer.location != traversing_object.location:
                # Aimer is gone or no longer in the same room, clear the lock
                splattercast.msg(f"AIM LOCK: {traversing_object.key} was aimed at by {aimer.key if aimer else 'Unknown'}, but aimer is no longer present/valid. Clearing lock.")
                del traversing_object.ndb.aimed_at_by
                if hasattr(aimer, "ndb") and getattr(aimer.ndb, "aiming_at", None) == traversing_object:
                    del aimer.ndb.aiming_at
            else:
                traversing_object.msg(f"|r{aimer.key} is aiming at you, locking you in place! You cannot move.|n")
                aimer.msg(f"|yYour target, {traversing_object.key}, tries to move but is locked by your aim!|n")
                splattercast.msg(f"AIM LOCK: {traversing_object.key} attempted to traverse {self.key} but is locked by {aimer.key}'s aim.")
                return # Block traversal
        # --- END AIMING LOCK CHECK ---

        # --- CLEAR TRAVERSER'S OWN AIM STATE UPON MOVING ---
        if hasattr(traversing_object, "clear_aim_state"):
            # This will only send messages if an aim state was actually cleared.
            traversing_object.clear_aim_state(reason_for_clearing="as you move")
        else:
            # Fallback - manually clear aim state if the method isn't on the object
            aim_cleared = False
            
            # Clear target aiming
            old_aim_target = getattr(traversing_object.ndb, "aiming_at", None)
            if old_aim_target:
                del traversing_object.ndb.aiming_at
                if hasattr(old_aim_target, "ndb") and getattr(old_aim_target.ndb, "aimed_at_by", None) == traversing_object:
                    del old_aim_target.ndb.aimed_at_by
                    old_aim_target.msg(f"{traversing_object.key} stops aiming at you as they move.")
                
                # Get weapon name for better messaging
                hands = getattr(traversing_object, "hands", {})
                weapon = next((item for hand, item in hands.items() if item), None)
                weapon_name = weapon.key if weapon else "weapon"
                
                traversing_object.msg(f"You stop aiming at {old_aim_target.key} and lower your {weapon_name} as you move.")
                
                # Clear override_place and handle mutual showdown cleanup
                self._clear_aim_override_place_on_move(traversing_object, old_aim_target)
                aim_cleared = True
            
            # Clear direction aiming  
            old_aim_direction = getattr(traversing_object.ndb, "aiming_direction", None)
            if old_aim_direction:
                del traversing_object.ndb.aiming_direction
                
                # Get weapon name for better messaging
                hands = getattr(traversing_object, "hands", {})
                weapon = next((item for hand, item in hands.items() if item), None)
                weapon_name = weapon.key if weapon else "weapon"
                
                # Try to get the actual exit name from the direction
                exit_obj = traversing_object.location.search(old_aim_direction, quiet=True)
                if exit_obj and hasattr(exit_obj[0], 'destination') and exit_obj[0].destination:
                    exit_name = exit_obj[0].key
                else:
                    # Fallback to direction mapping for non-exit directions
                    direction_map = {
                        "n": "north", "s": "south", "e": "east", "w": "west",
                        "ne": "northeast", "nw": "northwest", "se": "southeast", "sw": "southwest",
                        "u": "up", "d": "down", "in": "in", "out": "out"
                    }
                    exit_name = direction_map.get(old_aim_direction.lower(), old_aim_direction)
                
                traversing_object.msg(f"You stop aiming to the {exit_name} and lower your {weapon_name} as you move.")
                
                # Clear directional aim override_place
                traversing_object.override_place = ""
                aim_cleared = True
            
            if not aim_cleared:
                splattercast.msg(f"AIM_CLEAR_ON_MOVE_FAIL: {traversing_object.key} lacks clear_aim_state method during traversal of {self.key}.")
        # --- END CLEAR TRAVERSER'S OWN AIM STATE ---

        # --- PROXIMITY CLEANUP ON ROOM CHANGE ---
        # Clear proximity relationships when moving between rooms (except during combat dragging)
        handler = getattr(traversing_object.ndb, "combat_handler", None)
        is_being_dragged = False
        if handler:
            combatants = handler.db.combatants
            if combatants:
                try:
                    is_being_dragged = any(e.get(DB_CHAR) == traversing_object and 
                                         handler.get_grappled_by_obj(e) for e in combatants)
                except (TypeError, AttributeError) as ex:
                    # Log the error but don't crash traversal
                    splattercast.msg(f"TRAVERSE_ERROR: Error checking grapple status for {traversing_object.key}: {ex}")
                    is_being_dragged = False
        
        if not is_being_dragged and hasattr(traversing_object.ndb, "in_proximity_with"):
            if isinstance(traversing_object.ndb.in_proximity_with, set) and traversing_object.ndb.in_proximity_with:
                splattercast.msg(f"PROXIMITY_CLEANUP_ON_MOVE: {traversing_object.key} moving from {traversing_object.location.key} to {target_location.key}. Clearing proximity with: {[o.key for o in traversing_object.ndb.in_proximity_with]}")
                
                # Remove traversing_object from others' proximity sets
                for other_char in list(traversing_object.ndb.in_proximity_with):
                    if hasattr(other_char.ndb, "in_proximity_with") and isinstance(other_char.ndb.in_proximity_with, set):
                        other_char.ndb.in_proximity_with.discard(traversing_object)
                        splattercast.msg(f"PROXIMITY_CLEANUP_ON_MOVE: Removed {traversing_object.key} from {other_char.key}'s proximity list.")
                
                # Clear traversing_object's proximity set
                traversing_object.ndb.in_proximity_with.clear()
        
        # --- UNIVERSAL PROXIMITY CLEANUP ON ROOM CHANGE ---
        # Clear universal proximity relationships (grenades, etc.) when moving between rooms
        if not is_being_dragged and hasattr(traversing_object.ndb, NDB_PROXIMITY_UNIVERSAL):
            universal_proximity = getattr(traversing_object.ndb, NDB_PROXIMITY_UNIVERSAL, [])
            if isinstance(universal_proximity, list) and universal_proximity:
                splattercast.msg(f"UNIVERSAL_PROXIMITY_CLEANUP_ON_MOVE: {traversing_object.key} moving rooms. Clearing universal proximity with: {[o.key if hasattr(o, 'key') else str(o) for o in universal_proximity]}")
                
                # Remove traversing_object from others' universal proximity lists
                for obj in list(universal_proximity):
                    if hasattr(obj, 'ndb'):
                        obj_proximity = getattr(obj.ndb, NDB_PROXIMITY_UNIVERSAL, [])
                        if isinstance(obj_proximity, list) and traversing_object in obj_proximity:
                            obj_proximity.remove(traversing_object)
                            splattercast.msg(f"UNIVERSAL_PROXIMITY_CLEANUP_ON_MOVE: Removed {traversing_object.key} from {obj.key if hasattr(obj, 'key') else str(obj)}'s universal proximity list.")
                
                # Clear traversing_object's universal proximity list
                setattr(traversing_object.ndb, NDB_PROXIMITY_UNIVERSAL, [])
        # --- END UNIVERSAL PROXIMITY CLEANUP ---

        handler = getattr(traversing_object.ndb, "combat_handler", None)

        if handler:
            # Character is in combat - check if handler is still valid
            combatants_list = handler.db.combatants
            if combatants_list is None:
                # Handler has been cleaned up but character still has reference
                splattercast.msg(f"TRAVERSAL: {traversing_object.key} has stale combat_handler reference. Clearing and allowing move.")
                setattr(traversing_object.ndb, "combat_handler", None)
                super().at_traverse(traversing_object, target_location)
                return
                
            char_entry_in_handler = next((e for e in combatants_list if e["char"] == traversing_object), None)

            if not char_entry_in_handler:
                # This case should ideally not be reached if ndb.combat_handler is properly managed.
                splattercast.msg(f"ERROR: {traversing_object.key} has ndb.combat_handler but no entry in handler {handler.key}. Allowing move as non-combatant.")
                super().at_traverse(traversing_object, target_location)
                return

            # Check drag conditions
            grappled_victim_obj = handler.get_grappling_obj(char_entry_in_handler)
            is_yielding = char_entry_in_handler.get("is_yielding")
            
            is_targeted_by_others_not_victim = False
            if combatants_list:
                for entry in combatants_list:
                    # Check if this entry is targeting the traversing_object
                    if handler.get_target_obj(entry) == traversing_object:
                        # And this entry is not the traversing_object itself
                        if entry["char"] != traversing_object:
                            # AND this entry is not the person being grappled by the traversing_object
                            if entry["char"] != grappled_victim_obj:
                                is_targeted_by_others_not_victim = True
                                break # Found someone else targeting, no need to check further
            
            # Drag conditions: grappling someone, yielding, and not targeted by anyone *else* (other than the victim)
            if grappled_victim_obj and is_yielding and not is_targeted_by_others_not_victim:
                # Conditions for dragging are met
                victim_entry_in_handler = next((e for e in combatants_list if e["char"] == grappled_victim_obj), None)
                if not victim_entry_in_handler:
                    splattercast.msg(f"ERROR: {traversing_object.key} is grappling {grappled_victim_obj.key if grappled_victim_obj else 'Unknown'}, but victim not in handler. Blocking drag.")
                    traversing_object.msg("|rYour grapple target seems to have vanished from combat. You can't drag them.|n")
                    return

                # --- Immediate resistance check ---
                from random import randint
                victim_grit = getattr(grappled_victim_obj, "grit", 1)
                grappler_grit = getattr(traversing_object, "grit", 1)
                resist_roll = randint(1, max(1, victim_grit))
                drag_roll = randint(1, max(1, grappler_grit))
                splattercast.msg(f"DRAG RESIST: {grappled_victim_obj.key} rolls {resist_roll} vs {drag_roll} ({traversing_object.key})")

                if resist_roll > drag_roll:
                    traversing_object.msg(f"|r{grappled_victim_obj.key} resists your attempt to drag them!|n")
                    grappled_victim_obj.msg(f"|gYou resist {traversing_object.key}'s attempt to drag you!|n")
                    splattercast.msg(f"{grappled_victim_obj.key} successfully resisted being dragged by {traversing_object.key}.")

                    # --- Break the grapple on successful resistance ---
                    # Find both entries in the handler
                    grappler_entry = next((e for e in combatants_list if e["char"] == traversing_object), None)
                    victim_entry = next((e for e in combatants_list if e["char"] == grappled_victim_obj), None)
                    if grappler_entry:
                        grappler_entry["grappling_dbref"] = None
                    if victim_entry:
                        victim_entry["grappled_by_dbref"] = None
                    msg = f"{grappled_victim_obj.key} breaks free from {traversing_object.key}'s grapple!"
                    traversing_object.location.msg_contents(f"|g{msg}|n")
                    splattercast.msg(f"GRAPPLE BROKEN: {msg}")

                    return

                # Proceed with drag if resistance fails
                traversing_object.msg(f"|g{grappled_victim_obj.key} struggles but fails to resist.|n")
                grappled_victim_obj.msg(f"|rYou struggle but fail to resist {traversing_object.key}'s attempt to drag you.|n")
                splattercast.msg(f"{grappled_victim_obj.key} failed to resist being dragged by {traversing_object.key}.")

                old_handler = handler
                old_location = traversing_object.location

                # Announce dragging
                msg_drag_self = f"|gYou drag {grappled_victim_obj.key} with you through the {self.key} exit...|n"
                msg_drag_victim = f"|r{traversing_object.key} drags you through the {self.key} exit!|n"
                msg_drag_room = f"{traversing_object.key} drags {grappled_victim_obj.key} away through the {self.key} exit."
                
                traversing_object.msg(msg_drag_self)
                grappled_victim_obj.msg(msg_drag_victim)
                old_location.msg_contents(msg_drag_room, exclude=[traversing_object, grappled_victim_obj])
                splattercast.msg(f"DRAG: {traversing_object.key} is dragging {grappled_victim_obj.key} from {old_location.key} to {target_location.key} via {self.key}.")

                # Perform moves: grappler first, then victim quietly
                super().at_traverse(traversing_object, target_location) 
                grappled_victim_obj.move_to(target_location, quiet=True, move_hooks=False)

                # Check for rigged grenades after drag movement (same as normal traversal)
                from commands.CmdThrow import check_rigged_grenade, check_auto_defuse
                check_rigged_grenade(traversing_object, self)

                # Check for auto-defuse opportunities for both characters after drag
                check_auto_defuse(traversing_object)
                check_auto_defuse(grappled_victim_obj)

                # Announce arrival in new location
                msg_arrive_room = f"{traversing_object.key} arrives, dragging {grappled_victim_obj.key}."
                target_location.msg_contents(msg_arrive_room, exclude=[traversing_object, grappled_victim_obj])

                # --- Transfer combat state to the new location ---
                # 1. Before removing, determine if victim is yielding
                victim_entry_in_handler = next((e for e in combatants_list if e["char"] == grappled_victim_obj), None)
                victim_is_yielding = victim_entry_in_handler.get("is_yielding", False) if victim_entry_in_handler else False

                # 2. Remove combatants from the old handler.
                old_handler.remove_combatant(traversing_object)
                old_handler.remove_combatant(grappled_victim_obj)

                # 3. Get or create a combat handler in the new location.
                new_handler = get_or_create_combat(target_location)

                # 4. Add combatants to the new handler with their transferred state.
                new_handler.add_combatant(
                    traversing_object, 
                    target=None, # Grappler is always yielding when dragging
                    initial_grappling=grappled_victim_obj, 
                    initial_grappled_by=None, 
                    initial_is_yielding=True
                )
                new_handler.add_combatant(
                    grappled_victim_obj, 
                    target=None,  # Victim never has an offensive target immediately after being dragged
                    initial_grappling=None, 
                    initial_grappled_by=traversing_object, 
                    initial_is_yielding=victim_is_yielding # Preserve their yielding state from before the drag
                )
                
                splattercast.msg(f"DRAG: Combatants re-added to new handler {new_handler.key} with transferred grapple state.")

                # No longer need to manually find and update entries here, as add_combatant handles it.
                
                new_handler_combatants = new_handler.db.combatants
                if new_handler_combatants and len(new_handler_combatants) > 1 and not new_handler.is_active:
                    splattercast.msg(f"DRAG: New handler {new_handler.key} has {len(new_handler_combatants)} combatants, ensuring it starts if not already active.")
                    new_handler.start()

                return  # Movement and combat transfer handled successfully

            else:
                # In combat, but conditions for dragging are not met
                traversing_object.msg("|rYou can't leave while in combat! Try to flee instead.|n")
                splattercast.msg(f"{traversing_object.key} tried to move via exit '{self.key}' while in combat. Drag conditions not met (grappling: {bool(grappled_victim_obj)}, yielding: {is_yielding}, targeted_by_others_not_victim: {is_targeted_by_others_not_victim}).")
                return  # Block movement

        # Not in combat, standard traversal
        super().at_traverse(traversing_object, target_location)
        
        # Clear temporary character placement on room change
        if hasattr(traversing_object, 'temp_place'):
            traversing_object.temp_place = ""
        
        # Check for rigged grenades after successful movement
        from commands.CmdThrow import check_rigged_grenade, check_auto_defuse
        check_rigged_grenade(traversing_object, self)
        
        # Check for auto-defuse opportunities after entering new room
        check_auto_defuse(traversing_object)

    def get_display_desc(self, looker, **kwargs):
        """
        Enhanced exit description system providing atmospheric descriptions 
        instead of generic "This is an exit." message.
        
        Analyzes exit properties and destination context to generate immersive
        descriptions that complement the directional looking system.
        
        Args:
            looker: Character examining the exit
            **kwargs: Additional parameters
            
        Returns:
            str: Formatted exit description with atmospheric context and character display
        """
        # Check aiming restrictions - aiming characters cannot examine exits (focus limitation)
        if hasattr(looker, 'ndb') and getattr(looker.ndb, "aiming_at", None):
            looker.msg("You cannot see any further.")
            return ""
        
        if hasattr(looker, 'ndb') and getattr(looker.ndb, "aiming_direction", None):
            looker.msg("You cannot see any further.")
            return ""
        
        # Build description components
        description_parts = []
        
        # Start with custom description if set (priority over atmospheric defaults)
        custom_desc = self.db.desc
        if custom_desc:
            description_parts.append(custom_desc.strip())
        
        # Generate atmospheric description based on exit analysis
        atmospheric_desc = self._get_atmospheric_description(looker)
        if atmospheric_desc:
            description_parts.append(atmospheric_desc)
        
        # Combine descriptions
        if not description_parts:
            # Fallback to prevent empty description
            description_parts.append("A passageway leading elsewhere.")
        
        base_description = " ".join(description_parts)
        
        # Add character display from current room (following standard appearance patterns)
        character_display = self._get_exit_character_display(looker)
        
        # Combine all components
        full_description = base_description
        if character_display:
            full_description += f" {character_display}"
            
        return full_description
        
    def _get_atmospheric_description(self, looker):
        """
        Generate atmospheric description based on exit properties and destination analysis.
        Includes weather integration for enhanced atmospheric context.
        
        Args:
            looker: Character examining the exit
            
        Returns:
            str: Atmospheric description or empty string
        """
        # Check for edge/gap exits first (specialized descriptions)
        is_edge = self.db.is_edge
        is_gap = self.db.is_gap
        
        if is_edge and is_gap:
            return "A jagged gap torn in reality, requiring a leap of faith to cross."
        elif is_edge:
            return "A precarious edge where solid ground gives way to open space below."
        elif is_gap:
            return "A treacherous gap that demands careful timing to traverse safely."
            
        # Check for sky room destinations
        destination = self.destination
        if destination and getattr(destination, 'is_sky_room', False):
            return "The opening leads into open air, where gravity makes the rules."
        
        # Analyze destination for street context (with weather integration)
        street_context = self._analyze_street_context()
        if street_context:
            return street_context
            
        # Generate directional atmospheric defaults (with weather integration)
        directional_desc = self._get_directional_atmospheric(looker)
        if directional_desc:
            return directional_desc
            
        # Fallback atmospheric description
        return "The passage stretches into shadows and uncertainty."
        
    def _analyze_street_context(self):
        """
        Analyze destination room type and exit count for street-specific descriptions.
        Includes weather integration for enhanced atmospheric context.
        
        Returns:
            str: Street context description or empty string
        """
        destination = self.destination
        if not destination:
            return ""
            
        # Check if destination is a street-type room
        dest_type = getattr(destination, 'type', None)
        if dest_type != 'street':
            return ""
            
        # Analyze destination exit count to determine street type
        dest_exits = destination.exits
        if not dest_exits:
            return ""
            
        # Count street exits to determine intersection type
        street_exit_count = sum(1 for e in dest_exits 
                              if e.destination and hasattr(e.destination, 'type') 
                              and e.destination.type == 'street')
        
        direction = self.key.lower()
        
        # Get weather context for enhanced descriptions
        weather_context = self._get_weather_context()
        
        if street_exit_count <= 1:
            # Dead-end street
            base_desc = f"The street {direction}ward leads to a dead-end, where urban decay reaches its terminus."
        elif street_exit_count == 2:
            # Continuing street (matches spec example)
            base_desc = f"The street stretches {direction}ward through the urban canyon, where scattered streetlight illuminates the continuing path between deteriorating storefronts."
        else:
            # Intersection
            base_desc = f"The street {direction}ward opens into a bustling intersection, where multiple paths converge in the city's concrete maze."
        
        # Integrate weather context if available
        if weather_context:
            return f"{weather_context}, {base_desc.lower()}"
        else:
            return base_desc
            
    def _get_weather_context(self):
        """
        Get weather context for exit descriptions.
        Integrates with the existing weather system if available.
        
        Returns:
            str: Weather context string or empty string
        """
        try:
            # Check if current room is outside (weather affects exits to outside areas)
            current_room = self.location
            destination = self.destination
            
            # Only add weather context if going to/from outside areas
            room_is_outside = getattr(current_room, 'outside', False) if current_room else False
            dest_is_outside = getattr(destination, 'outside', False) if destination else False
            
            if not (room_is_outside or dest_is_outside):
                return ""
                
            # Use the same weather system as rooms
            from world.weather import weather_system
            
            # Get weather contributions for the current room or destination
            weather_room = current_room if room_is_outside else destination
            if not weather_room:
                return ""
                
            # Get current weather status
            current_weather = weather_system.get_current_weather()
            
            # Simple weather context phrases for exit descriptions
            weather_contexts = {
                # Clear/mild weather
                'clear': "",  # No weather context needed for clear conditions
                
                # Rain variants
                'rain': "Through the steady rain",
                'light_rain': "Through the gentle rain", 
                'torrential_rain': "Through the torrential downpour",
                'foggy_rain': "Through the misty rain",
                'rainy_thunderstorm': "Through the thunderous downpour",
                'tox_rain': "Through the toxic rainfall",
                
                # Fog variants
                'fog': "Through the thick fog",
                'heavy_fog': "Through the impenetrable fog",
                'blind_fog': "Through the blinding fog",
                
                # Snow variants
                'soft_snow': "Through the gentle snowfall",
                'hard_snow': "Through the driving snow",
                'blizzard': "Through the raging blizzard",
                
                # Storm variants
                'dry_thunderstorm': "Under the ominous storm clouds",
                'flashstorm': "Through the violent storm",
                'sandstorm': "Through the swirling sand",
                
                # Atmospheric conditions
                'overcast': "Under the overcast sky",
                'windy': "Against the strong wind",
                'gray_pall': "Through the gray pall"
            }
            
            return weather_contexts.get(current_weather, "")
            
        except ImportError as e:
            # Weather system not available
            return ""
        except Exception as e:
            # Any other error - fail gracefully
            return ""
        
    def _get_directional_atmospheric(self, looker):
        """
        Generate atmospheric descriptions based on cardinal direction.
        Provides noir-aesthetic defaults matching the game's atmosphere.
        
        Args:
            looker: Character examining the exit
            
        Returns:
            str: Directional atmospheric description
        """
        direction = self.key.lower()
        
        # Directional atmospheric themes (noir/urban decay aesthetic)
        directional_themes = {
            'north': "Northward lies deeper shadow, where the city's forgotten corners harbor their secrets.",
            'south': "To the south, urban decay spreads like a stain across crumbling infrastructure.",
            'east': "Eastward, the passage leads through crumbling architecture toward distant uncertainty.",
            'west': "The western route disappears into ruins and the weight of abandoned dreams.",
            'northeast': "The northeastern path winds through industrial decay and forgotten machinery.",
            'northwest': "Northwest leads through deteriorating structures toward darker territories.",
            'southeast': "The southeastern route stretches through urban blight and weathered concrete.",
            'southwest': "Southwest lies a passage through rust-stained metal and cracked pavement.",
            'up': "The upward path climbs through layers of the city's vertical labyrinth.",
            'down': "Downward leads deeper into the city's underground arteries and hidden spaces.",
            'in': "The entrance leads inward to sheltered spaces away from the street's harsh realities.",
            'out': "The exit leads outward to where the open street awaits with all its dangers."
        }
        
        return directional_themes.get(direction, "")
        
    def _get_exit_character_display(self, looker):
        """
        Get character display from destination room (where the exit leads to).
        Shows characters in the destination location following standard appearance patterns.
        Uses crowd-aware formatting for more immersive descriptions.
        
        Args:
            looker: Character examining the exit
            
        Returns:
            str: Character display string or empty string
        """
        destination_room = self.destination
        if not destination_room:
            return ""
            
        # Get characters in destination room (excluding looker if they're somehow there)
        destination_characters = [char for char in destination_room.contents 
                                if char.is_typeclass("typeclasses.characters.Character") 
                                and char != looker]
                          
        if not destination_characters:
            return ""
            
        # Format character names
        char_names = [char.get_display_name(looker) for char in destination_characters]
        
        # Get crowd level from destination room for contextual descriptions
        try:
            from world.crowd import crowd_system
            crowd_level = crowd_system.calculate_crowd_level(destination_room)
        except (ImportError, AttributeError):
            crowd_level = 0
        
        # Get directional context for the description
        direction = self.key.lower()
        direction_phrase = f"To the {direction}" if direction in ['north', 'south', 'east', 'west'] else f"{direction.capitalize()}"
        
        # Format character display based on crowd level and character count
        if crowd_level >= 3:  # heavy/packed crowd
            if len(char_names) == 1:
                return f"{direction_phrase} you can see a bustling crowd of people going about their business, amidst them {char_names[0]}."
            elif len(char_names) == 2:
                return f"{direction_phrase} you can see a bustling crowd of people going about their business, amidst them {char_names[0]} and {char_names[1]}."
            else:
                all_but_last = ", ".join(char_names[:-1])
                return f"{direction_phrase} you can see a bustling crowd of people going about their business, amidst them {all_but_last}, and {char_names[-1]}."
        
        elif crowd_level >= 2:  # moderate crowd
            if len(char_names) == 1:
                return f"{direction_phrase} you see figures moving through the urban maze, among them {char_names[0]}."
            elif len(char_names) == 2:
                return f"{direction_phrase} you see figures moving through the urban maze, among them {char_names[0]} and {char_names[1]}."
            else:
                all_but_last = ", ".join(char_names[:-1])
                return f"{direction_phrase} you see figures moving through the urban maze, among them {all_but_last}, and {char_names[-1]}."
        
        elif crowd_level >= 1:  # sparse crowd
            if len(char_names) == 1:
                return f"{direction_phrase} you catch glimpses of movement in the shadows, including {char_names[0]}."
            elif len(char_names) == 2:
                return f"{direction_phrase} you catch glimpses of movement in the shadows, including {char_names[0]} and {char_names[1]}."
            else:
                all_but_last = ", ".join(char_names[:-1])
                return f"{direction_phrase} you catch glimpses of movement in the shadows, including {all_but_last}, and {char_names[-1]}."
        
        else:  # no crowd (level 0)
            if len(char_names) == 1:
                return f"{direction_phrase} you see {char_names[0]}."
            elif len(char_names) == 2:
                return f"{direction_phrase} you see {char_names[0]} and {char_names[1]}."
            else:
                all_but_last = ", ".join(char_names[:-1])
                return f"{direction_phrase} you see {all_but_last}, and {char_names[-1]}."

    def _clear_aim_override_place_on_move(self, mover, target):
        """
        Clear override_place for aiming when someone moves, handling mutual showdown cleanup.
        
        Args:
            mover: The character who is moving (and stopping their aim)
            target: The character they were aiming at
        """
        # Check if they were in a mutual showdown
        if (hasattr(mover, 'override_place') and hasattr(target, 'override_place') and
            mover.override_place == "locked in a deadly showdown." and 
            target.override_place == "locked in a deadly showdown."):
            # They were in a showdown - clear mover's place, check if target should revert to normal aiming
            mover.override_place = ""
            
            # If target is still aiming at mover, revert them to normal aiming
            target_still_aiming = getattr(target.ndb, "aiming_at", None)
            if target_still_aiming == mover:
                target.override_place = f"aiming carefully at {mover.key}."
            else:
                # Target isn't aiming at anyone, clear their place too
                target.override_place = ""
        else:
            # Normal aiming cleanup
            if hasattr(mover, 'override_place'):
                mover.override_place = ""
