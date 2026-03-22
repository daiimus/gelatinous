"""
Room

Rooms are simple containers that has no location of their own.

"""

from evennia.objects.objects import DefaultRoom
from evennia.typeclasses.attributes import AttributeProperty
from world.combat.constants import NDB_FLYING_OBJECTS
from world.weather import weather_system
from world.crowd import crowd_system

from .objects import ObjectParent


class Room(ObjectParent, DefaultRoom):
    """
    Rooms are like any Object, except their location is None
    (which is default). They also use basetype_setup() to
    add locks so they cannot be puppeted or picked up.
    (to change that, use at_object_creation instead)

    See mygame/typeclasses/objects.py for a list of
    properties and methods available on all Objects.
    """
    
    # Room type for smart exit system
    type = AttributeProperty(default=None, autocreate=True)
    
    # Sky room flag for exit filtering
    is_sky_room = AttributeProperty(default=False, autocreate=True)
    
    # Outside room flag for weather system
    outside = AttributeProperty(default=False, autocreate=True)
    
    # Room description
    desc = AttributeProperty(default="", autocreate=True)
    
    # Crowd system base level
    crowd_base_level = AttributeProperty(default=0, autocreate=True)
    
    def at_object_creation(self):
        """
        Called when room is first created.
        Initialize room attributes for existing rooms.
        """
        super().at_object_creation()
        
        # Initialize attributes - AttributeProperty will handle new rooms,
        # but existing rooms need this to ensure attributes exist
        if not hasattr(self, 'type'):
            self.type = None
        if not hasattr(self, 'is_sky_room'):
            self.is_sky_room = False
        if not hasattr(self, 'outside'):
            self.outside = False
        if not hasattr(self, 'desc'):
            self.desc = ""
        if not hasattr(self, 'crowd_base_level'):
            self.crowd_base_level = 0
    
    def at_object_receive(self, moved_obj, source_location, **kwargs):
        """
        Called when an object enters this room.
        Check for fully decayed corpses and clean them up just-in-time.
        """
        super().at_object_receive(moved_obj, source_location, **kwargs)
        
        # When a character (PC or NPC) enters, check all corpses in room for decay
        from typeclasses.characters import Character
        if isinstance(moved_obj, Character):
            # Only run decay check when a character enters (not every object move)
            self._check_corpse_decay()
    
    def _check_corpse_decay(self):
        """Check all corpses in room and remove those that have fully decayed."""
        from typeclasses.corpse import Corpse
        
        # Get all corpses in this room
        corpses = [obj for obj in self.contents if isinstance(obj, Corpse)]
        
        for corpse in corpses:
            try:
                if corpse.check_complete_decay():
                    # Drop items to room
                    for item in list(corpse.contents):
                        try:
                            item.move_to(self, quiet=True)
                        except Exception:
                            pass
                    
                    # Log and delete
                    try:
                        from evennia.comms.models import ChannelDB
                        splattercast = ChannelDB.objects.get_channel("Splattercast")
                        splattercast.msg(f"CORPSE_DECAY_JIT: {corpse.key} decayed on room entry to {self.key}")
                    except Exception:
                        pass
                    
                    corpse.delete()
            except Exception:
                pass  # Corpse may have been deleted or be in invalid state
    
    # Override the appearance template to use our custom footer for exits
    # and custom things display to handle @integrate objects
    # This avoids duplicate display issues with exits while letting Evennia handle characters
    # See: https://www.evennia.com/docs/latest/Components/Objects.html#changing-an-objects-appearance
    appearance_template = """{header}|c{name}|n
{desc}
{things}
{characters}
{footer}"""

    def return_appearance(self, looker, **kwargs):
        """
        This formats a description. It is the hook a 'look' command
        should call.

        Enhanced to show flying objects during throw mechanics and 
        integrate @integrate objects and weather into the room description.
        
        Also supports aiming system: When looker is aiming in a direction,
        shows the complete appearance of the aimed room instead of current room.
        """
        # Check if looker is aiming in a direction - if so, show aimed room appearance
        aiming_direction = getattr(looker.ndb, "aiming_direction", None) if hasattr(looker, 'ndb') else None
        
        if aiming_direction:
            # Find the exit for the aimed direction
            exit_obj = None
            for ex in self.exits:
                current_exit_aliases_lower = [alias.lower() for alias in (ex.aliases.all() if hasattr(ex.aliases, "all") else [])]
                if ex.key.lower() == aiming_direction.lower() or aiming_direction.lower() in current_exit_aliases_lower:
                    exit_obj = ex
                    break
            
            # If we found the exit and it has a destination, return that room's appearance
            if exit_obj and exit_obj.destination:
                aimed_room = exit_obj.destination
                # Call the parent's return_appearance directly to avoid aiming recursion
                return super(Room, aimed_room).return_appearance(looker, **kwargs)
        
        # Normal room appearance (not aiming)
        # Get the base description from the parent class
        appearance = super().return_appearance(looker, **kwargs)
        
        # Process @integrate objects and flying objects - append to room description
        integrated_content = self.get_integrated_objects_content(looker)
        
        # Get weather contributions for outdoor rooms
        weather_desc = weather_system.get_weather_contributions(self, looker)
        
        # Combine integrated content and weather
        all_integrated_content = []
        if integrated_content:
            all_integrated_content.append(integrated_content)
        if weather_desc:
            all_integrated_content.append(weather_desc)
        
        if all_integrated_content:
            combined_content = " ".join(all_integrated_content)
            # Simple approach: find room description and append integrated content
            lines = appearance.split('\n')
            room_name_found = False
            
            for i, line in enumerate(lines):
                # Skip until we find the room name
                if not room_name_found and line.startswith('|c') and line.endswith('|n'):
                    room_name_found = True
                    continue
                
                # After room name, find first non-empty line (room description) and append
                if room_name_found and line.strip() and not line.startswith('Characters:') and not line.startswith('You see:') and not line.startswith('Exits:'):
                    lines[i] += f" {combined_content}"
                    break
            
            appearance = '\n'.join(lines)
        
        return appearance

    def search_for_target(self, looker, searchdata, return_candidates_only=False, **kwargs):
        """
        Enhanced search that respects aiming direction for world interpretation.
        
        When looker is aiming in a direction, creates a unified search space
        across both current room and aimed room. This allows ordinal numbers
        to work correctly across the combined space (e.g., "3rd sword" finds
        the 3rd sword across both rooms).
        
        Args:
            looker: The character performing the search
            searchdata: What to search for (string)
            return_candidates_only: If True, return just the candidate list 
                                  instead of performing the search
            **kwargs: Additional search parameters
            
        Returns:
            Search result object(s), None if not found, or candidate list if return_candidates_only=True
        """
        # Check if looker is aiming in a direction
        aiming_direction = getattr(looker.ndb, "aiming_direction", None) if hasattr(looker, 'ndb') else None
        
        if aiming_direction:
            # Find the exit for the aimed direction (same logic as return_appearance)
            exit_obj = None
            for ex in self.exits:
                current_exit_aliases_lower = [alias.lower() for alias in (ex.aliases.all() if hasattr(ex.aliases, "all") else [])]
                if ex.key.lower() == aiming_direction.lower() or aiming_direction.lower() in current_exit_aliases_lower:
                    exit_obj = ex
                    break
            
            # If we found the exit and it has a destination, create unified search space
            if exit_obj and exit_obj.destination:
                aimed_room = exit_obj.destination
                
                # Combine candidates from both rooms for unified ordinal numbering
                current_candidates = list(self.contents)
                aimed_candidates = list(aimed_room.contents)
                combined_candidates = current_candidates + aimed_candidates
                
                # Remove the looker from candidates (they shouldn't find themselves)
                if looker in combined_candidates:
                    combined_candidates.remove(looker)
                
                # Return just candidates if requested
                if return_candidates_only:
                    return combined_candidates
                
                # Search using combined candidate pool
                return looker.search(searchdata, candidates=combined_candidates, quiet=True, **kwargs)
        
        # Not aiming or invalid aim - use standard room search
        # Remove the looker from candidates
        candidates = [obj for obj in self.contents if obj != looker]
        
        # Return just candidates if requested
        if return_candidates_only:
            return candidates
            
        return looker.search(searchdata, candidates=candidates, quiet=True, **kwargs)
    
    def get_integrated_objects_content(self, looker):
        """
        Get content from all @integrate objects in this room.
        
        Objects with @integrate = True contribute to the room description
        instead of appearing in the traditional object list.
        
        Flying objects are automatically integrated regardless of @integrate status.
        
        Args:
            looker: Character looking at the room
            
        Returns:
            str: Combined integrated content from all @integrate objects and flying objects
        """
        # Find all @integrate objects in this room
        integrated_objects = []
        
        # Get flying objects list managed by CmdThrow
        flying_objects = getattr(self.ndb, NDB_FLYING_OBJECTS, [])
        if flying_objects is None:
            flying_objects = []
        
        # Add all flying objects first (they get highest priority)
        for obj in flying_objects:
            priority = 1  # High priority for flying objects
            integrated_objects.append((priority, obj, True))
        
        for obj in self.contents:
            # Check objects for integration - currently supports Items, GraffitiObjects, BloodPools, and ShopContainers
            # TODO: Consider expanding to other object types or using a more generic approach
            if not (obj.is_typeclass("typeclasses.items.Item") or 
                    obj.is_typeclass("typeclasses.objects.GraffitiObject") or 
                    obj.is_typeclass("typeclasses.objects.BloodPool") or
                    obj.is_typeclass("typeclasses.shopkeeper.ShopContainer")):
                continue
            
            # Skip if already added as flying object
            if obj in flying_objects:
                continue
            
            # Check if item should be integrated
            is_integrate = obj.db.integrate
            
            if is_integrate:
                # Regular @integrate objects use their configured priority
                priority = obj.db.integration_priority if obj.db.integration_priority is not None else 5
                # Safety check: ensure priority is not None
                if priority is None:
                    priority = 5
                integrated_objects.append((priority, obj, False))
        
        if not integrated_objects:
            return ""
        
        # Sort by priority (lower number = appears first)
        integrated_objects.sort(key=lambda x: x[0])
        
        # Collect integration content
        content_parts = []
        for priority, obj, is_flying in integrated_objects:
            if is_flying:
                # Use flying-specific description with teal item name
                content = f"A |c{obj.key}|n is flying through the air."
            else:
                # Use regular integration content
                content = self.get_object_integration_content(obj, looker)
            
            if content:
                content_parts.append(content)
        
        # Join all integration content
        if content_parts:
            return " ".join(content_parts)
        
        return ""
    
    def get_object_integration_content(self, obj, looker):
        """
        Get the integration content for a specific object.
        
        Uses sensory contributions as primary content source.
        Later this will be enhanced to check character sensory abilities.
        
        Args:
            obj: The object to get integration content for
            looker: Character looking at the room
            
        Returns:
            str: Integration content for this object
        """
        # Check for sensory contributions (primary content source)
        sensory_contributions = obj.db.sensory_contributions or {}
        
        if sensory_contributions:
            # Collect available sensory content
            # For now, use all available senses - later we'll filter by character abilities
            content_parts = []
            
            # Standard sensory order: visual, auditory, olfactory, tactile, etc.
            sensory_order = ["visual", "auditory", "olfactory", "tactile", "gustatory"]
            
            for sense in sensory_order:
                if sense in sensory_contributions:
                    content_parts.append(sensory_contributions[sense])
            
            # Add any other sensory contributions not in standard order
            for sense, content in sensory_contributions.items():
                if sense not in sensory_order:
                    content_parts.append(content)
            
            if content_parts:
                return " ".join(content_parts)
        
        # Fall back to basic integration description if no sensory data
        integration_desc = obj.db.integration_desc if obj.db.integration_desc is not None else ""
        if integration_desc:
            return integration_desc
        
        # Last resort: use the object's short_desc or key
        return obj.db.integration_fallback if obj.db.integration_fallback is not None else f"{obj.key} is here"
    
    def get_display_characters(self, looker, **kwargs):
        """
        Custom character display using placement descriptions.
        
        Uses @override_place, @temp_place, or @look_place attributes to create
        natural language character positioning instead of "Characters:" listing.
        Now includes crowd system messages that appear before character listings.
        
        Args:
            looker: Character looking at the room
            
        Returns:
            str: Combined crowd and character placement descriptions
        """
        characters = []
        
        for obj in self.contents:
            if obj.is_typeclass("typeclasses.characters.Character") and obj != looker:
                if obj.access(looker, "view"):
                    characters.append(obj)
        
        # Get crowd contributions (appears before character listings)
        crowd_msg = crowd_system.get_crowd_contributions(self, looker)
        
        if not characters:
            # No characters, but might still have crowd messages
            return crowd_msg if crowd_msg else ""
        
        # Group characters by their placement description
        placement_groups = {}
        
        for char in characters:
            # Check placement hierarchy: override_place > temp_place > look_place > fallback
            # Empty strings are treated as not set
            override_place = char.override_place or ""
            temp_place = char.temp_place or ""
            look_place = char.look_place or ""
            
            placement = (override_place if override_place else
                        temp_place if temp_place else
                        look_place if look_place else
                        "standing here.")
            
            if placement not in placement_groups:
                placement_groups[placement] = []
            placement_groups[placement].append(char.get_display_name(looker))
        
        # Generate natural language descriptions
        descriptions = []
        for placement, char_names in placement_groups.items():
            if len(char_names) == 1:
                descriptions.append(f"{char_names[0]} is {placement}")
            elif len(char_names) == 2:
                descriptions.append(f"{char_names[0]} and {char_names[1]} are {placement}")
            else:
                # Handle 3+ characters: "A, B, and C are here"
                all_but_last = ", ".join(char_names[:-1])
                descriptions.append(f"{all_but_last}, and {char_names[-1]} are {placement}")
        
        character_display = " ".join(descriptions) if descriptions else ""
        
        # Get adjacent character sightings (simple approach - no complex visibility logic)
        adjacent_sightings = self.get_adjacent_character_sightings(looker)
        
        # Combine crowd, local characters, and adjacent sightings
        all_displays = []
        if crowd_msg:
            all_displays.append(crowd_msg)
        if character_display:
            all_displays.append(character_display)
        if adjacent_sightings:
            all_displays.append(adjacent_sightings)
        
        return " ".join(all_displays) if all_displays else ""
    
    def get_adjacent_character_sightings(self, looker):
        """
        Simple adjacent room character detection.
        No complex visibility logic - just scan adjacent rooms and report characters.
        Encourages interaction and chase scenes.
        
        Args:
            looker: Character looking at the room
            
        Returns:
            str: Description of characters visible in adjacent rooms
        """
        sightings = []
        
        for exit_obj in self.exits:
            destination = exit_obj.destination
            if not destination:
                continue
                
            # Count visible characters (excluding looker)
            char_count = 0
            for obj in destination.contents:
                if (obj.is_typeclass("typeclasses.characters.Character") 
                    and obj != looker 
                    and obj.access(looker, "view")):
                    char_count += 1
            
            if char_count > 0:
                direction = exit_obj.key
                if char_count == 1:
                    sightings.append(f"You see a lone figure to the {direction}.")
                else:
                    sightings.append(f"You see a group of people standing to the {direction}.")
        
        return " ".join(sightings)
    
    def get_display_things(self, looker, **kwargs):
        """
        Override things display to exclude @integrate objects and use natural language formatting
        with stacking for identical items.
        
        @integrate objects are woven into the room description and
        should not appear in the traditional object listing.
        """
        import random
        from collections import defaultdict
        
        # Collect objects and group by display name
        item_counts = defaultdict(int)
        
        for obj in self.contents:
            # Skip characters (handled by get_display_characters)
            if obj.is_typeclass("typeclasses.characters.Character"):
                continue
            
            # Skip exits (handled by get_display_footer)
            if obj.is_typeclass("typeclasses.exits.Exit"):
                continue
            
            # Skip @integrate items - they're handled in room description  
            # Check Items, GraffitiObjects, BloodPools, and ShopContainers for integration
            if ((obj.is_typeclass("typeclasses.items.Item") or 
                 obj.is_typeclass("typeclasses.objects.GraffitiObject") or 
                 obj.is_typeclass("typeclasses.objects.BloodPool") or
                 obj.is_typeclass("typeclasses.shopkeeper.ShopContainer")) and 
                obj.db.integrate):
                continue
            
            # Skip objects the looker can't see
            if not obj.access(looker, "view"):
                continue
            
            display_name = obj.get_display_name(looker)
            item_counts[display_name] += 1
        
        if not item_counts:
            return ""
        
        # Quantity words for numbers 1-50
        quantity_words = {
            1: "a", 2: "two", 3: "three", 4: "four", 5: "five", 
            6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
            11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen", 15: "fifteen",
            16: "sixteen", 17: "seventeen", 18: "eighteen", 19: "nineteen", 20: "twenty",
            21: "twenty-one", 22: "twenty-two", 23: "twenty-three", 24: "twenty-four", 25: "twenty-five",
            26: "twenty-six", 27: "twenty-seven", 28: "twenty-eight", 29: "twenty-nine", 30: "thirty",
            31: "thirty-one", 32: "thirty-two", 33: "thirty-three", 34: "thirty-four", 35: "thirty-five",
            36: "thirty-six", 37: "thirty-seven", 38: "thirty-eight", 39: "thirty-nine", 40: "forty",
            41: "forty-one", 42: "forty-two", 43: "forty-three", 44: "forty-four", 45: "forty-five",
            46: "forty-six", 47: "forty-seven", 48: "forty-eight", 49: "forty-nine", 50: "fifty"
        }
        
        # Euphemisms for quantities > 50
        euphemisms = [
            "a shitload of", "a fuckton of", "a metric assload of", "way too many",
            "an ungodly amount of", "more {} than you know what to do with",
            "a ridiculous number of", "an obscene amount of", "a crapton of"
        ]
        
        # Format each item group with appropriate quantifier
        # Wrap item names in |w for bold white highlighting
        formatted_items = []
        for item_name, count in item_counts.items():
            if count == 1:
                formatted_items.append(f"a |w{item_name}|n")
            elif count <= 50:
                quantity = quantity_words[count]
                # Handle plural forms - simple approach for now
                if item_name.endswith('s') or item_name.endswith('x') or item_name.endswith('z'):
                    plural_name = item_name
                elif item_name.endswith('y'):
                    plural_name = item_name[:-1] + "ies"
                elif item_name.endswith('f'):
                    plural_name = item_name[:-1] + "ves"
                elif item_name.endswith('fe'):
                    plural_name = item_name[:-2] + "ves"
                else:
                    plural_name = item_name + "s"
                formatted_items.append(f"{quantity} |w{plural_name}|n")
            else:
                # Use random euphemism for large quantities
                euphemism = random.choice(euphemisms)
                if "{}" in euphemism:
                    # Handle template euphemisms like "more {} than you know what to do with"
                    plural_name = item_name + "s" if not item_name.endswith('s') else item_name
                    formatted_items.append(euphemism.format(f"|w{plural_name}|n"))
                else:
                    # Handle direct euphemisms like "a shitload of"
                    plural_name = item_name + "s" if not item_name.endswith('s') else item_name
                    formatted_items.append(f"{euphemism} |w{plural_name}|n")
        
        # Format using natural language similar to character placement
        # Item names are already wrapped in |w...|n from above
        if len(formatted_items) == 1:
            return f"You see {formatted_items[0]}."
        elif len(formatted_items) == 2:
            return f"You see {formatted_items[0]} and {formatted_items[1]}."
        else:
            # Handle 3+ item groups: "You see: A, B, and C"
            all_but_last = ", ".join(formatted_items[:-1])
            return f"You see {all_but_last}, and {formatted_items[-1]}."
    
    def get_display_footer(self, looker, **kwargs):
        """
        Get custom footer display for exits with edge/gap categorization.
        Let Evennia handle characters and objects via {characters} and {things} template variables.
        
        Returns:
            str: Formatted footer display string
        """
        lines = []
        
        # Only handle custom exit categorization in footer
        exit_display = self.get_custom_exit_display(looker)
        if exit_display:
            lines.append(exit_display)
        
        return '\n'.join(lines) if lines else ""
    
    def format_appearance(self, appearance, looker, **kwargs):
        """
        Final formatting step for room appearance.
        
        Simple approach: just add spacing after lines that start with "You see"
        since that's our consistent things pattern.
        
        Args:
            appearance (str): The formatted appearance string from the template
            looker: Character looking at the room
            
        Returns:
            str: Final formatted appearance with proper spacing
        """
        # Get components to determine what sections exist
        things = self.get_display_things(looker, **kwargs)
        characters = self.get_display_characters(looker, **kwargs)
        desc = self.db.desc or ""
        
        lines = appearance.split('\n')
        result = []
        
        for line in lines:
            # Skip empty lines from template (these are from empty sections)
            if not line.strip():
                continue
                
            result.append(line)
            
            # Add spacing after description if there's content following
            if desc and line.strip() == desc.strip() and (things or characters):
                result.append("")
            
            # Add spacing after any line that starts with "You see" (our things pattern)
            elif line.strip().startswith("You see"):
                result.append("")
        
        final = '\n'.join(result)
        
        # Clean up any triple+ newlines that might have been introduced
        while '\n\n\n' in final:
            final = final.replace('\n\n\n', '\n\n')
            
        return final
    
    def get_custom_exit_display(self, looker):
        """
        Get smart exit display using natural language based on destination room types.
        
        Returns:
            str: Formatted natural language exit display string
        """
        # Sky rooms don't display exits
        if self.is_sky_room:
            return ""
            
        exits = self.exits
        if not exits:
            return ""
        
        # Group exits by destination type and special properties
        exit_groups = {
            'streets': [],
            'edges': [],
            'gaps': [],
            'custom_types': {},
            'fallback': []
        }
        
        # Analyze each exit
        for exit_obj in exits:
            direction = exit_obj.key
            aliases = exit_obj.aliases.all()
            alias = aliases[0] if aliases else None
            destination = exit_obj.destination
            
            # Check if exit leads to a sky room (skip unless edge/gap)
            destination_is_sky = False
            if destination:
                destination_is_sky = destination.is_sky_room
            
            if destination_is_sky and not (exit_obj.db.is_edge or exit_obj.db.is_gap):
                continue  # Skip pure sky rooms
            
            # Check for edge/gap first (highest priority)
            if exit_obj.db.is_edge:
                exit_groups['edges'].append((direction, alias))
            elif exit_obj.db.is_gap:
                exit_groups['gaps'].append((direction, alias))
            # Check destination type
            elif destination and hasattr(destination, 'type') and destination.type:
                dest_type = destination.type
                if dest_type == 'street':
                    exit_groups['streets'].append((direction, alias))
                else:
                    if dest_type not in exit_groups['custom_types']:
                        exit_groups['custom_types'][dest_type] = []
                    exit_groups['custom_types'][dest_type].append((direction, alias))
            else:
                # Fallback for exits without type information
                exit_groups['fallback'].append((direction, alias))
        
        # Generate natural language descriptions
        return self.format_exit_groups(exit_groups)
    
    def format_exit_groups(self, exit_groups):
        """
        Format grouped exits into natural language descriptions.
        
        Args:
            exit_groups (dict): Dictionary of grouped exits by type
            
        Returns:
            str: Formatted natural language exit descriptions
        """
        descriptions = []
        
        # Format streets (analyze destination room layout and group by type)
        if exit_groups['streets']:
            # Group streets by their type
            dead_ends = []
            continues = []
            intersections = []
            
            for direction, alias in exit_groups['streets']:
                dir_text = self.format_direction_with_alias(direction, alias)
                
                # Analyze the destination room's exit count to determine type
                exit_obj = None
                for exit in self.exits:
                    if exit.key == direction:
                        exit_obj = exit
                        break
                
                if exit_obj and exit_obj.destination:
                    dest_exits = exit_obj.destination.exits
                    street_exit_count = sum(1 for e in dest_exits 
                                          if e.destination and hasattr(e.destination, 'type') 
                                          and e.destination.type == 'street')
                    
                    if street_exit_count <= 1:
                        dead_ends.append(dir_text)
                    elif street_exit_count == 2:
                        continues.append(dir_text)
                    else:
                        intersections.append(dir_text)
                else:
                    # Fallback if we can't analyze destination
                    continues.append(dir_text)
            
            # Format grouped street descriptions
            if dead_ends:
                if len(dead_ends) == 1:
                    descriptions.append(f"There is a dead-end to the {dead_ends[0]}.")
                else:
                    dead_end_desc = self.format_direction_list(dead_ends)
                    descriptions.append(f"There are dead-ends to the {dead_end_desc}.")
                    
            if continues:
                if len(continues) == 1:
                    descriptions.append(f"The street continues to the {continues[0]}.")
                else:
                    continue_desc = self.format_direction_list(continues)
                    descriptions.append(f"The street continues to the {continue_desc}.")
                    
            if intersections:
                if len(intersections) == 1:
                    descriptions.append(f"There is an intersection to the {intersections[0]}.")
                else:
                    intersection_desc = self.format_direction_list(intersections)
                    descriptions.append(f"There are intersections to the {intersection_desc}.")
        
        # Format custom types (grouped by type)
        for dest_type, exits in exit_groups['custom_types'].items():
            type_dirs = [self.format_direction_with_alias(direction, alias) 
                        for direction, alias in exits]
            if len(type_dirs) == 1:
                descriptions.append(f"There is a {dest_type} to the {type_dirs[0]}.")
            else:
                type_desc = self.format_direction_list(type_dirs)
                descriptions.append(f"There are {dest_type}s to the {type_desc}.")
        
        # Format edges (grouped)
        if exit_groups['edges']:
            edge_dirs = [self.format_direction_with_alias(direction, alias) 
                        for direction, alias in exit_groups['edges']]
            if len(edge_dirs) == 1:
                descriptions.append(f"There is an edge to the {edge_dirs[0]}.")
            else:
                edge_desc = self.format_direction_list(edge_dirs)
                descriptions.append(f"There are edges to the {edge_desc}.")
        
        # Format gaps (grouped)
        if exit_groups['gaps']:
            gap_dirs = [self.format_direction_with_alias(direction, alias) 
                       for direction, alias in exit_groups['gaps']]
            if len(gap_dirs) == 1:
                descriptions.append(f"There is a gap to the {gap_dirs[0]}.")
            else:
                gap_desc = self.format_direction_list(gap_dirs)
                descriptions.append(f"There are gaps to the {gap_desc}.")
        
        # Format fallback exits
        if exit_groups['fallback']:
            fallback_dirs = [self.format_direction_with_alias(direction, alias) 
                           for direction, alias in exit_groups['fallback']]
            if len(fallback_dirs) == 1:
                descriptions.append(f"There is an exit to the {fallback_dirs[0]}.")
            else:
                fallback_desc = self.format_direction_list(fallback_dirs)
                descriptions.append(f"There are exits to the {fallback_desc}.")
        
        return " ".join(descriptions) if descriptions else ""
    
    def format_direction_with_alias(self, direction, alias):
        """
        Format a direction with its alias in parentheses if available.
        
        Args:
            direction (str): The direction name
            alias (str): The alias, if any
            
        Returns:
            str: Formatted direction string
        """
        if alias and alias != direction:
            return f"{direction} ({alias})"
        return direction
    
    def format_direction_list(self, directions):
        """
        Format a list of directions using natural language conjunctions.
        
        Args:
            directions (list): List of formatted direction strings
            
        Returns:
            str: Natural language list of directions
        """
        if len(directions) == 1:
            return directions[0]
        elif len(directions) == 2:
            return f"{directions[0]} and {directions[1]}"
        else:
            # Handle 3+ directions: "north, south, and east"
            all_but_last = ", ".join(directions[:-1])
            return f"{all_but_last}, and {directions[-1]}"


# =============================================================================
# Specialized Room Types for Grid Building
# =============================================================================

class StreetRoom(Room):
    """
    A standard street room in the colony crater.
    Outdoor, crowded public space.
    
    Usage:
        @tunnel north = Hadley Corridor:typeclasses.rooms.StreetRoom
    """
    
    def at_object_creation(self):
        """Set default attributes for street rooms."""
        super().at_object_creation()
        self.db.crowd_base_level = 3
        self.db.outside = True
        self.db.is_sky_room = False
        self.db.type = "street"


class IndoorRoom(Room):
    """
    An interior room (building, shop, warehouse, etc.).
    Indoor, moderate crowd levels.
    
    Usage:
        @tunnel east = Warehouse:typeclasses.rooms.IndoorRoom
    """
    
    def at_object_creation(self):
        """Set default attributes for indoor rooms."""
        super().at_object_creation()
        self.db.crowd_base_level = 2
        self.db.outside = False
        self.db.is_sky_room = False
        self.db.type = "interior"


class BridgeRoom(Room):
    """
    A bridge or elevated walkway spanning between areas.
    Outdoor, moderate crowd levels.
    
    Usage:
        @tunnel north = Central Span:typeclasses.rooms.BridgeRoom
    """
    
    def at_object_creation(self):
        """Set default attributes for bridge rooms."""
        super().at_object_creation()
        self.db.crowd_base_level = 2
        self.db.outside = True
        self.db.is_sky_room = False
        self.db.type = "bridge"


class SkyRoom(Room):
    """
    An open sky area (rooftop, balcony, catwalk, etc.).
    Outdoor, low crowd levels, elevated.
    
    Usage:
        @tunnel up = Rooftop:typeclasses.rooms.SkyRoom
    """
    
    def at_object_creation(self):
        """Set default attributes for sky rooms."""
        super().at_object_creation()
        self.db.crowd_base_level = 1
        self.db.outside = True
        self.db.is_sky_room = True
        self.db.type = "sky"


class AlleyRoom(Room):
    """
    A narrow alley or side street.
    Outdoor, low to moderate crowd levels.
    
    Usage:
        @tunnel west = Dark Alley:typeclasses.rooms.AlleyRoom
    """
    
    def at_object_creation(self):
        """Set default attributes for alley rooms."""
        super().at_object_creation()
        self.db.crowd_base_level = 1
        self.db.outside = True
        self.db.is_sky_room = False
        self.db.type = "alley"


class CorridorRoom(Room):
    """
    An interior corridor or hallway.
    Indoor, low crowd levels.
    
    Usage:
        @tunnel south = Long Corridor:typeclasses.rooms.CorridorRoom
    """
    
    def at_object_creation(self):
        """Set default attributes for corridor rooms."""
        super().at_object_creation()
        self.db.crowd_base_level = 1
        self.db.outside = False
        self.db.is_sky_room = False
        self.db.type = "corridor"
