"""
Object

The Object is the class for general items in the game world.

Use the ObjectParent class to implement common features for *all* entities
with a location in the game world (like Characters, Rooms, Exits).

"""

from evennia.objects.objects import DefaultObject
from evennia.utils import gametime
import random
import re


class ObjectParent:
    """
    This is a mixin that can be used to override *all* entities inheriting at
    some distance from DefaultObject (Objects, Exits, Characters and Rooms).

    Just add any method that exists on `DefaultObject` to this class. If one
    of the derived classes has itself defined that same hook already, that will
    take precedence.

    """
    
    # Ordinal word mapping for natural language search
    ORDINAL_WORDS = {
        'first': 1, 'second': 2, 'third': 3, 'fourth': 4, 'fifth': 5,
        'sixth': 6, 'seventh': 7, 'eighth': 8, 'ninth': 9, 'tenth': 10,
        '1st': 1, '2nd': 2, '3rd': 3, '4th': 4, '5th': 5, '6th': 6,
        '7th': 7, '8th': 8, '9th': 9, '10th': 10, '11th': 11, '12th': 12,
        '13th': 13, '14th': 14, '15th': 15, '16th': 16, '17th': 17,
        '18th': 18, '19th': 19, '20th': 20
    }
    
    # Regex for numeric ordinals (1st, 2nd, 3rd, etc.)
    ORDINAL_REGEX = re.compile(r'(?P<number>\d+)(?:st|nd|rd|th)\s+(?P<name>.*)', re.I)
    
    def get_search_query_replacement(self, searchdata, **kwargs):
        """
        Override Evennia's search to handle ordinal numbers (1st, 2nd, first, second, etc.)
        
        This method is called before the actual search to allow modification of the search string.
        We intercept ordinal queries and convert them to Evennia's standard dash-number format.
        """
        # First call the parent method for any existing replacements
        searchdata = super().get_search_query_replacement(searchdata, **kwargs)
        
        if not isinstance(searchdata, str):
            return searchdata
            
        searchdata = searchdata.strip()
        
        # Try numeric ordinals first (1st sword, 2nd ball, etc.)
        ordinal_match = self.ORDINAL_REGEX.match(searchdata)
        if ordinal_match:
            number = int(ordinal_match.group('number'))
            name = ordinal_match.group('name').strip()
            if number > 0:
                # Convert to Evennia's dash-number format
                return f"{name}-{number}"
        
        # Try word ordinals (first sword, second ball, etc.)
        words = searchdata.split()
        if len(words) >= 2:
            first_word = words[0].lower()
            if first_word in self.ORDINAL_WORDS:
                remaining_words = ' '.join(words[1:])
                number = self.ORDINAL_WORDS[first_word]
                # Convert to Evennia's dash-number format
                return f"{remaining_words}-{number}"
        
        # No ordinal found, return unchanged
        return searchdata


class Object(ObjectParent, DefaultObject):
    """
    This is the root Object typeclass, representing all entities that
    have an actual presence in-game. DefaultObjects generally have a
    location. They can also be manipulated and looked at. Game
    entities you define should inherit from DefaultObject at some distance.

    It is recommended to create children of this class using the
    `evennia.create_object()` function rather than to initialize the class
    directly - this will both set things up and efficiently save the object
    without `obj.save()` having to be called explicitly.

    Note: Check the autodocs for complete class members, this may not always
    be up-to date.

    * Base properties defined/available on all Objects

     key (string) - name of object
     name (string)- same as key
     dbref (int, read-only) - unique #id-number. Also "id" can be used.
     date_created (string) - time stamp of object creation

     account (Account) - controlling account (if any, only set together with
                       sessid below)
     sessid (int, read-only) - session id (if any, only set together with
                       account above). Use `sessions` handler to get the
                       Sessions directly.
     location (Object) - current location. Is None if this is a room
     home (Object) - safety start-location
     has_account (bool, read-only)- will only return *connected* accounts
     contents (list, read only) - returns all objects inside this object
     exits (list of Objects, read-only) - returns all exits from this
                       object, if any
     destination (Object) - only set if this object is an exit.
     is_superuser (bool, read-only) - True/False if this user is a superuser
     is_connected (bool, read-only) - True if this object is associated with
                            an Account with any connected sessions.
     has_account (bool, read-only) - True is this object has an associated account.
     is_superuser (bool, read-only): True if this object has an account and that
                        account is a superuser.

    * Handlers available

     aliases - alias-handler: use aliases.add/remove/get() to use.
     permissions - permission-handler: use permissions.add/remove() to
                   add/remove new perms.
     locks - lock-handler: use locks.add() to add new lock strings
     scripts - script-handler. Add new scripts to object with scripts.add()
     cmdset - cmdset-handler. Use cmdset.add() to add new cmdsets to object
     nicks - nick-handler. New nicks with nicks.add().
     sessions - sessions-handler. Get Sessions connected to this
                object with sessions.get()
     attributes - attribute-handler. Use attributes.add/remove/get.
     db - attribute-handler: Shortcut for attribute-handler. Store/retrieve
            database attributes using self.db.myattr=val, val=self.db.myattr
     ndb - non-persistent attribute handler: same as db but does not create
            a database entry when storing data

    * Helper methods (see src.objects.objects.py for full headers)

     get_search_query_replacement(searchdata, **kwargs)
     get_search_direct_match(searchdata, **kwargs)
     get_search_candidates(searchdata, **kwargs)
     get_search_result(searchdata, attribute_name=None, typeclass=None,
                       candidates=None, exact=False, use_dbref=None, tags=None, **kwargs)
     get_stacked_result(results, **kwargs)
     handle_search_results(searchdata, results, **kwargs)
     search(searchdata, global_search=False, use_nicks=True, typeclass=None,
            location=None, attribute_name=None, quiet=False, exact=False,
            candidates=None, use_locks=True, nofound_string=None,
            multimatch_string=None, use_dbref=None, tags=None, stacked=0)
     search_account(searchdata, quiet=False)
     execute_cmd(raw_string, session=None, **kwargs))
     msg(text=None, from_obj=None, session=None, options=None, **kwargs)
     for_contents(func, exclude=None, **kwargs)
     msg_contents(message, exclude=None, from_obj=None, mapping=None,
                  raise_funcparse_errors=False, **kwargs)
     move_to(destination, quiet=False, emit_to_obj=None, use_destination=True)
     clear_contents()
     create(key, account, caller, method, **kwargs)
     copy(new_key=None)
     at_object_post_copy(new_obj, **kwargs)
     delete()
     is_typeclass(typeclass, exact=False)
     swap_typeclass(new_typeclass, clean_attributes=False, no_default=True)
     access(accessing_obj, access_type='read', default=False,
            no_superuser_bypass=False, **kwargs)
     filter_visible(obj_list, looker, **kwargs)
     get_default_lockstring()
     get_cmdsets(caller, current, **kwargs)
     check_permstring(permstring)
     get_cmdset_providers()
     get_display_name(looker=None, **kwargs)
     get_extra_display_name_info(looker=None, **kwargs)
     get_numbered_name(count, looker, **kwargs)
     get_display_header(looker, **kwargs)
     get_display_desc(looker, **kwargs)
     get_display_exits(looker, **kwargs)
     get_display_characters(looker, **kwargs)
     get_display_things(looker, **kwargs)
     get_display_footer(looker, **kwargs)
     format_appearance(appearance, looker, **kwargs)
     return_apperance(looker, **kwargs)

    * Hooks (these are class methods, so args should start with self):

     basetype_setup()     - only called once, used for behind-the-scenes
                            setup. Normally not modified.
     basetype_posthook_setup() - customization in basetype, after the object
                            has been created; Normally not modified.

     at_object_creation() - only called once, when object is first created.
                            Object customizations go here.
     at_object_delete() - called just before deleting an object. If returning
                            False, deletion is aborted. Note that all objects
                            inside a deleted object are automatically moved
                            to their <home>, they don't need to be removed here.

     at_init()            - called whenever typeclass is cached from memory,
                            at least once every server restart/reload
     at_first_save()
     at_cmdset_get(**kwargs) - this is called just before the command handler
                            requests a cmdset from this object. The kwargs are
                            not normally used unless the cmdset is created
                            dynamically (see e.g. Exits).
     at_pre_puppet(account)- (account-controlled objects only) called just
                            before puppeting
     at_post_puppet()     - (account-controlled objects only) called just
                            after completing connection account<->object
     at_pre_unpuppet()    - (account-controlled objects only) called just
                            before un-puppeting
     at_post_unpuppet(account) - (account-controlled objects only) called just
                            after disconnecting account<->object link
     at_server_reload()   - called before server is reloaded
     at_server_shutdown() - called just before server is fully shut down

     at_access(result, accessing_obj, access_type) - called with the result
                            of a lock access check on this object. Return value
                            does not affect check result.

     at_pre_move(destination)             - called just before moving object
                        to the destination. If returns False, move is cancelled.
     announce_move_from(destination)         - called in old location, just
                        before move, if obj.move_to() has quiet=False
     announce_move_to(source_location)       - called in new location, just
                        after move, if obj.move_to() has quiet=False
     at_post_move(source_location)          - always called after a move has
                        been successfully performed.
     at_pre_object_leave(leaving_object, destination, **kwargs)
     at_object_leave(obj, target_location, move_type="move", **kwargs)
     at_object_leave(obj, target_location)   - called when an object leaves
                        this object in any fashion
     at_pre_object_receive(obj, source_location)
     at_object_receive(obj, source_location, move_type="move", **kwargs) - called when this object receives
                        another object
     at_post_move(source_location, move_type="move", **kwargs)

     at_traverse(traversing_object, target_location, **kwargs) - (exit-objects only)
                              handles all moving across the exit, including
                              calling the other exit hooks. Use super() to retain
                              the default functionality.
     at_post_traverse(traversing_object, source_location) - (exit-objects only)
                              called just after a traversal has happened.
     at_failed_traverse(traversing_object)      - (exit-objects only) called if
                       traversal fails and property err_traverse is not defined.

     at_msg_receive(self, msg, from_obj=None, **kwargs) - called when a message
                             (via self.msg()) is sent to this obj.
                             If returns false, aborts send.
     at_msg_send(self, msg, to_obj=None, **kwargs) - called when this objects
                             sends a message to someone via self.msg().

     return_appearance(looker) - describes this object. Used by "look"
                                 command by default
     at_desc(looker=None)      - called by 'look' whenever the
                                 appearance is requested.
     at_pre_get(getter, **kwargs)
     at_get(getter)            - called after object has been picked up.
                                 Does not stop pickup.
     at_pre_give(giver, getter, **kwargs)
     at_give(giver, getter, **kwargs)
     at_pre_drop(dropper, **kwargs)
     at_drop(dropper, **kwargs)          - called when this object has been dropped.
     at_pre_say(speaker, message, **kwargs)
     at_say(message, msg_self=None, msg_location=None, receivers=None, msg_receivers=None, **kwargs)

     at_look(target, **kwargs)
     at_desc(looker=None)

    """

    pass


class GraffitiObject(Object):
    """
    Graffiti storage object for rooms.
    Stores up to 7 graffiti entries with FIFO management.
    """
    
    def at_object_creation(self):
        """Initialize graffiti storage."""
        super().at_object_creation()
        
        # Set up graffiti storage
        self.db.graffiti_entries = []  # List of graffiti entries
        self.db.max_entries = 7       # Maximum entries before cannibalization
        
        # Set basic properties
        self.key = "graffiti"
        self.db.desc = "The walls are clean."
        
        # Make it non-takeable and locked in place
        self.locks.add("get:false()")
        self.locks.add("drop:false()")
        
        # Add aliases for examination
        self.aliases.add(["tags", "writing", "wall", "walls"])
        
        # Set @integrate attribute for room integration
        self.db.integrate = True
        self.db.integration_priority = 3  # Lower priority than flying objects
        self.db.integration_desc = "The walls have been daubed with colorful |Cgraffiti|n."
        
    def add_graffiti(self, message, color, author=None):
        """
        Add a graffiti entry to the storage.
        
        Args:
            message (str): The graffiti message
            color (str): Full color name (e.g., 'red', 'blue', etc.)
            author (Object, optional): Who created the graffiti
            
        Returns:
            str: The formatted graffiti entry that was added
        """
        if not self.db.graffiti_entries:
            self.db.graffiti_entries = []
            
        # Map full color names to Evennia single-letter codes
        color_map = {
            'red': 'r', 'blue': 'b', 'green': 'g', 'yellow': 'y',
            'magenta': 'm', 'cyan': 'c', 'white': 'w', 'black': 'x',
            'purple': 'm', 'pink': 'm', 'orange': 'y'
        }
        # Handle None color gracefully
        if color is None:
            color = "white"
        color_code = color_map.get(color.lower(), 'w')  # Default to white
        
        # Format the entry with proper Evennia color codes
        color_start = f"|{color_code}"
        color_end = "|n"
        formatted_entry = f"Scrawled in {color_start}{color}{color_end} paint: {color_start}{message}{color_end}"
        
        # Add to storage
        self.db.graffiti_entries.append({
            'entry': formatted_entry,
            'message': message,
            'color': color,  # Store full color name for display
            'color_code': color_code,  # Store single-letter code for formatting
            'author': author.key if author else 'someone',
            'timestamp': gametime.gametime()
        })
        
        # Enforce FIFO limit (cannibalization)
        if len(self.db.graffiti_entries) > self.db.max_entries:
            self.db.graffiti_entries.pop(0)  # Remove oldest entry
            
        # Update description and integration
        self._update_description()
        return formatted_entry
    
    def remove_random_characters(self, amount=10):
        """
        Remove random characters from random graffiti entries (solvent effect).
        
        Args:
            amount (int): Approximate number of characters to remove
            
        Returns:
            int: Actual number of characters removed
        """
        if not self.db.graffiti_entries:
            return 0
            
        removed_count = 0
        entries_to_remove = []
        
        # Randomly remove characters from random messages
        for _ in range(amount):
            if not self.db.graffiti_entries:
                break
                
            # Pick a random entry
            entry_index = random.randrange(len(self.db.graffiti_entries))
            entry = self.db.graffiti_entries[entry_index]
            
            # Remove a random character from the message (replace with space)
            message = entry['message']
            if message:
                # Only replace non-space characters to avoid creating double spaces
                non_space_indices = [i for i, char in enumerate(message) if char != ' ']
                if non_space_indices:
                    char_index = random.choice(non_space_indices)
                    new_message = message[:char_index] + ' ' + message[char_index + 1:]
                    entry['message'] = new_message
                
                # Update the formatted entry with proper color codes
                color_code = entry.get('color_code', 'w')  # Use stored code or default to white
                color_name = entry.get('color', 'white')   # Use stored color name or default
                color_start = f"|{color_code}"
                color_end = "|n"
                entry['entry'] = f"Scrawled in {color_start}{color_name}{color_end} paint: {color_start}{new_message}{color_end}"
                removed_count += 1
                
                # Mark entries for removal if they're all spaces or empty
                if len(new_message.strip()) == 0:
                    entries_to_remove.append(entry_index)
        
        # Remove empty entries (in reverse order to maintain indices)
        for index in sorted(entries_to_remove, reverse=True):
            if index < len(self.db.graffiti_entries):
                self.db.graffiti_entries.pop(index)
        
        self._update_description()
        return removed_count
    
    def clear_all_graffiti(self):
        """Remove all graffiti entries and delete the object."""
        self.db.graffiti_entries = []
        self.delete()
        
    def has_graffiti(self):
        """
        Check if there are any graffiti entries.
        
        Returns:
            bool: True if graffiti exists
        """
        return bool(self.db.graffiti_entries)
    
    def get_total_characters(self):
        """
        Get total character count across all graffiti entries.
        
        Returns:
            int: Total character count
        """
        if not self.db.graffiti_entries:
            return 0
        return sum(len(entry['message']) for entry in self.db.graffiti_entries)
    
    def _update_description(self):
        """Update the object's description based on current graffiti."""
        if not self.db.graffiti_entries:
            # No graffiti left - delete this object
            self.delete()
        else:
            self.db.desc = "The walls are covered with graffiti in various colors and styles."
            # Ensure integration is active when graffiti exists
            self.db.integrate = True
    
    def return_appearance(self, looker, **kwargs):
        """
        Show graffiti entries when examined.
        
        Args:
            looker (Object): The one looking at the graffiti
            
        Returns:
            str: Formatted appearance
        """
        if not self.db.graffiti_entries:
            # This shouldn't happen since empty objects get deleted,
            # but just in case...
            return "The walls are clean and free of graffiti."
        
        # Header
        appearance = ["Daubed on the walls you see:"]
        
        # Add entries in chronological order (oldest first)
        for entry in self.db.graffiti_entries:
            if entry['message'].strip():  # Only show entries with content
                appearance.append(entry['entry'])
        
        return "\n".join(appearance)


class BloodPool(Object):
    """
    Blood pool object for forensic evidence and atmospheric effect.
    
    Like graffiti, consolidates multiple bleeding incidents into a single object.
    Ages over time with progressive descriptions and can be cleaned with solvents.
    """
    
    def at_object_creation(self):
        """Called when the blood pool is first created."""
        self.db.is_blood_pool = True
        self.db.bleeding_incidents = []  # List of forensic incidents like graffiti entries
        self.db.total_volume = 0
        self.db.created_time = gametime.gametime()
        self.db.last_updated = self.db.created_time
        
        # Set up integration for room description (like graffiti)
        self.db.integrate = True
        self.db.integration_priority = 4  # Lower priority than graffiti
        self.db.integration_desc = "Dark |Rstains|n mark the ground where blood has pooled."
        
        self.locks.add("get:false()")  # Can't be picked up
        
        # Add aliases for examination
        self.aliases.add(["blood", "stains", "pool", "evidence"])
        
    def add_bleeding_incident(self, character_name, severity, sleeve_uid=None):
        """Add a new bleeding incident to this pool (like adding graffiti).

        Args:
            character_name: Display name of the character (used for staff
                forensic display only, NOT shown to regular players).
            severity: Numeric severity of the bleeding event.
            sleeve_uid: Optional sleeve UID for forensic identity tracking.
                If provided, stored as the behind-the-scenes identifier.
        """
        current_time = gametime.gametime()
        
        incident = {
            'character': character_name,
            'sleeve_uid': sleeve_uid,
            'severity': severity,
            'timestamp': current_time,
            'age_hours': 0  # Will be calculated dynamically
        }
        
        if not self.db.bleeding_incidents:
            self.db.bleeding_incidents = []
            
        self.db.bleeding_incidents.append(incident)
        self.db.total_volume = (self.db.total_volume or 0) + severity
        self.db.last_updated = current_time
        
        # Update room integration
        self._update_description()
    
    def clean_with_solvent(self, cleaner=None, tool_quality="basic"):
        """Clean blood stains with solvent (like cleaning graffiti)."""
        if not self.db.bleeding_incidents:
            return 0, "There are no blood stains to clean."
            
        # Cleaning effectiveness based on tool quality and age
        oldest_incident = min(self.db.bleeding_incidents, key=lambda x: x['timestamp'])
        age_hours = (gametime.gametime() - oldest_incident['timestamp']) / 3600.0
        
        if tool_quality == "professional":
            base_effectiveness = 90
        elif tool_quality == "industrial":
            base_effectiveness = 70
        else:  # basic
            base_effectiveness = 50
            
        # Older blood is harder to clean
        age_penalty = min(30, age_hours * 2)  # Up to 30% penalty
        final_effectiveness = max(20, base_effectiveness - age_penalty)
        
        if random.randint(1, 100) <= final_effectiveness:
            # Successful cleaning
            cleaned_volume = self.db.total_volume
            self.db.bleeding_incidents = []
            self.db.total_volume = 0
            self.delete()  # Remove like cleaned graffiti
            return cleaned_volume, f"The blood stains have been successfully cleaned away."
        else:
            # Partial cleaning
            incidents_removed = max(1, len(self.db.bleeding_incidents) // 2)
            removed_incidents = self.db.bleeding_incidents[:incidents_removed]
            self.db.bleeding_incidents = self.db.bleeding_incidents[incidents_removed:]
            
            removed_volume = sum(incident['severity'] for incident in removed_incidents)
            self.db.total_volume -= removed_volume
            
            self._update_description()
            return removed_volume, f"Some of the blood stains have been cleaned, but traces remain."
    
    def get_age_hours(self):
        """Get the age of the oldest blood in hours."""
        if not self.db.bleeding_incidents:
            return 0
            
        oldest_incident = min(self.db.bleeding_incidents, key=lambda x: x['timestamp'])
        current_time = gametime.gametime()
        age_seconds = current_time - oldest_incident['timestamp']
        return age_seconds / 3600.0
    
    def get_volume_description(self):
        """Get description based on total blood volume."""
        volume = self.db.total_volume or 0
        if volume <= 3:
            return "small droplets"
        elif volume <= 10:
            return "modest stains"
        elif volume <= 20:
            return "significant pooling"
        elif volume <= 35:
            return "extensive blood loss"
        else:
            return "massive carnage"
    
    def get_age_description(self):
        """Get progressive description based on age of oldest blood."""
        age_hours = self.get_age_hours()
        
        if age_hours < 0.5:
            return "still glistening wet"
        elif age_hours < 2:
            return "beginning to coagulate"
        elif age_hours < 6:
            return "dark and tacky"
        elif age_hours < 24:
            return "dried and brown"
        elif age_hours < 72:
            return "old and flaking"
        else:
            return "ancient and barely visible"
    
    def _update_description(self):
        """Update object description like graffiti system."""
        if not self.db.bleeding_incidents:
            self.delete()  # Remove empty pools like empty graffiti
        else:
            volume_desc = self.get_volume_description()
            age_desc = self.get_age_description()
            self.db.desc = f"Blood evidence shows {volume_desc}, {age_desc}."
            
            # Update integration description based on current state
            age_hours = self.get_age_hours()
            if age_hours < 1:
                self.db.integration_desc = "Fresh |Rcrimson stains|n glisten wetly on the ground."
            elif age_hours < 6:
                self.db.integration_desc = "Dark |Rblood stains|n mark the ground ominously."
            elif age_hours < 24:
                self.db.integration_desc = "Dried |Rbrown stains|n show where blood once pooled."
            else:
                self.db.integration_desc = "Faint |Rrusty marks|n hint at old bloodshed."
    
    def return_appearance(self, looker, **kwargs):
        """Return detailed forensic description showing all incidents."""
        if not self.db.bleeding_incidents:
            return "There are no blood stains here."
            
        volume_desc = self.get_volume_description()
        age_desc = self.get_age_description()
        
        # Main description
        age_hours = self.get_age_hours()
        if age_hours < 1:
            base_desc = f"Crimson blood marks this area with {volume_desc}, {age_desc}."
        elif age_hours < 6:
            base_desc = f"Dark blood stains mark this spot with {volume_desc}, now {age_desc}."
        elif age_hours < 24:
            base_desc = f"Dried blood residue shows {volume_desc} occurred here, {age_desc}."
        else:
            base_desc = f"Faint rusty stains hint at {volume_desc} that happened here, {age_desc}."
        
        # Forensic incident summary — do NOT reveal character names
        # Blood evidence shows patterns but not identities
        incident_summary = []
        unique_sources = set()
        
        for incident in self.db.bleeding_incidents:
            uid = incident.get('sleeve_uid')
            if uid:
                unique_sources.add(uid)
            else:
                # Legacy incidents without sleeve_uid — count as unknown
                unique_sources.add(incident.get('character', 'unknown'))
        
        if len(unique_sources) == 1:
            incident_summary.append("Evidence suggests this blood came from a single source.")
        else:
            incident_summary.append(f"Evidence suggests blood from {len(unique_sources)} different sources.")
        
        details = [
            base_desc,
            "",
            *incident_summary,
            f"Forensic analysis: {len(self.db.bleeding_incidents)} separate bleeding events",
            f"Total blood volume: {self.db.total_volume} severity units",
            f"Evidence age span: {self.get_age_hours():.1f} hours"
        ]
        
        return "\n".join(details)
    
    def get_display_name(self, looker, **kwargs):
        """Return the name as it appears in room contents."""
        age_hours = self.get_age_hours()
        volume = self.db.total_volume or 0
        
        if volume > 20:
            size_prefix = "extensive "
        elif volume > 10:
            size_prefix = "significant "
        elif volume > 5:
            size_prefix = ""
        else:
            size_prefix = "small "
        
        if age_hours < 1:
            return f"{size_prefix}fresh blood stains"
        elif age_hours < 6:
            return f"{size_prefix}blood stains"
        elif age_hours < 24:
            return f"{size_prefix}dried blood stains"
        else:
            return f"{size_prefix}old blood stains"
