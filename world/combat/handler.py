"""
Combat Handler Module

The combat handler that manages turn-based combat for all combatants
in one or more locations. This module contains the core CombatHandler script
and utility functions for combat management.

This is the central component that orchestrates combat encounters, handling:
- Combat initialization and cleanup
- Turn management and initiative
- Multi-room combat coordination
- Combatant state management
- Integration with proximity and grappling systems

Attack processing, movement resolution, and special actions have been
extracted into focused modules (``attack``, ``movement_resolution``,
``actions``) to improve maintainability. The handler's ``at_repeat``
method acts as a thin dispatcher that delegates to those modules.
"""

from evennia import DefaultScript, create_script, search_object
from evennia.utils.utils import delay
from evennia.comms.models import ChannelDB

from .constants import (
    COMBAT_SCRIPT_KEY, SPLATTERCAST_CHANNEL,
    DB_COMBATANTS, DB_COMBAT_RUNNING, DB_MANAGED_ROOMS,
    DB_CHAR, DB_TARGET_DBREF, DB_GRAPPLING_DBREF, DB_GRAPPLED_BY_DBREF,
    DB_IS_YIELDING,
    DB_COMBAT_ACTION, DB_COMBAT_ACTION_TARGET, DB_INITIATIVE,
    NDB_COMBAT_HANDLER, NDB_PROXIMITY, NDB_SKIP_ROUND,
    DEBUG_PREFIX_HANDLER, DEBUG_SUCCESS, DEBUG_FAIL, DEBUG_ERROR,
    DEBUG_CLEANUP,
    COMBAT_ACTION_RETREAT, COMBAT_ACTION_ADVANCE, COMBAT_ACTION_CHARGE,
    COMBAT_ACTION_DISARM,
    COMBAT_ACTION_GRAPPLE_INITIATE, COMBAT_ACTION_GRAPPLE_JOIN,
    COMBAT_ACTION_GRAPPLE_TAKEOVER,
    COMBAT_ACTION_RELEASE_GRAPPLE, COMBAT_ACTION_ESCAPE_GRAPPLE,
    COMBAT_ROUND_INTERVAL,
)
from .utils import (
    get_numeric_stat, add_combatant, remove_combatant,
    cleanup_combatant_state, cleanup_all_combatants,
    get_combatant_target, get_combatant_grappling_target,
    get_combatant_grappled_by, get_character_dbref, get_character_by_dbref,
    resolve_bonus_attack, get_combatants_safe,
)
from .grappling import (
    break_grapple, establish_grapple, resolve_grapple_initiate,
    resolve_grapple_join, resolve_grapple_takeover,
    resolve_release_grapple, validate_and_cleanup_grapple_state,
)

# Import extracted module functions
from .attack import (
    calculate_attack_delay,
    process_delayed_attack,
    process_attack,
)
from .movement_resolution import (
    resolve_retreat,
    resolve_advance,
    resolve_charge,
)
from .actions import (
    resolve_disarm,
    resolve_grapple_attempt,
    resolve_escape_grapple,
    resolve_auto_escape,
)


def get_or_create_combat(location):
    """
    Get an existing combat handler for a location or create a new one.
    
    This function ensures that each location has at most one active combat
    handler managing it, and handles the complex logic of multi-room combat
    coordination.
    
    Args:
        location: The room/location that needs combat management
        
    Returns:
        CombatHandler: The combat handler managing this location
    """
    splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
    
    # First, check if 'location' is already managed by ANY active CombatHandler
    # This requires iterating through all scripts, which can be slow.
    # A better way might be a global list of active combat handlers, but for now:
    from evennia.scripts.models import ScriptDB
    active_handlers = ScriptDB.objects.filter(db_key=COMBAT_SCRIPT_KEY, db_is_active=True)

    for handler_script in active_handlers:
        # Ensure it's our CombatHandler type and has managed_rooms
        if handler_script.db.managed_rooms is not None:
            if location in (handler_script.db.managed_rooms or []):
                splattercast.msg(f"{DEBUG_PREFIX_HANDLER}_GET: Location {location.key} is already managed by active handler {handler_script.key} (on {handler_script.obj.key}). Returning it.")
                return handler_script
    
    # If not managed by an existing handler, check for an inactive one on THIS location
    for script in location.scripts.all():
        if script.key == COMBAT_SCRIPT_KEY:
            # Found a handler on this specific location
            if script.is_active: # Should have been caught by the loop above if it managed this location
                splattercast.msg(f"{DEBUG_PREFIX_HANDLER}_GET: Found active handler {script.key} directly on {location.key} (missed by global check or manages only self). Returning it.")
                # Ensure it knows it manages this location
                managed_rooms = script.db.managed_rooms or []
                if location not in managed_rooms:
                    managed_rooms.append(location)
                    script.db.managed_rooms = managed_rooms
                return script
            else:
                splattercast.msg(f"{DEBUG_PREFIX_HANDLER}_GET: Found inactive handler {script.key} on {location.key}. Attempting cleanup.")
                # Only perform database operations if the handler has been saved to the database
                if hasattr(script, 'id') and script.id:
                    try:
                        script.stop() # Ensure it's fully stopped
                        script.save()
                        script.delete()
                        splattercast.msg(f"{DEBUG_PREFIX_HANDLER}_GET: Deleted inactive handler {script.key}.")
                    except Exception as e:
                        splattercast.msg(f"{DEBUG_PREFIX_HANDLER}_GET: Error cleaning up inactive handler {script.key}: {e}. Leaving as-is.")
                else:
                    splattercast.msg(f"{DEBUG_PREFIX_HANDLER}_GET: Inactive handler {script.key} was not saved to database, skipping cleanup.")
                break # Only one handler script per location by key

    # If no suitable handler found, create a new one on this location
    new_script = create_script(
        "world.combat.handler.CombatHandler",
        key=COMBAT_SCRIPT_KEY,
        obj=location, # New handler is "hosted" by this location
        persistent=True,
    )
    
    # Ensure the script is saved to the database before returning
    # This is critical because attributes cannot be set on unsaved objects
    if not new_script.id:
        new_script.save()
        splattercast.msg(f"{DEBUG_PREFIX_HANDLER}_GET: Saved new CombatHandler {new_script.key} to database (id={new_script.id}).")
    
    splattercast.msg(f"{DEBUG_PREFIX_HANDLER}_GET: Created new CombatHandler {new_script.key} on {location.key}.")
    return new_script


class CombatHandler(DefaultScript):
    """
    Script that manages turn-based combat for all combatants in a location.
    
    This is the central orchestrator of combat encounters, handling:
    - Combat state management and lifecycle
    - Turn-based initiative and action resolution
    - Multi-room combat coordination through handler merging
    - Integration with proximity and grappling systems
    - Cleanup and state consistency
    
    Attack processing, movement resolution, and special actions are
    delegated to the ``attack``, ``movement_resolution``, and ``actions``
    modules respectively. The ``at_repeat`` method dispatches to those
    modules based on each combatant's queued action.
    
    The handler uses a database-backed combatants list with entries containing:
    - char: The character object
    - target_dbref: DBREF of their current target
    - grappling_dbref: DBREF of who they're grappling
    - grappled_by_dbref: DBREF of who's grappling them
    - is_yielding: Whether they're actively attacking
    """

    def at_script_creation(self):
        """
        Initialize combat handler script attributes.
        
        Sets up the initial state for a new combat handler, including
        the combatants list, round counter, and room management.
        """
        self.key = COMBAT_SCRIPT_KEY
        self.interval = COMBAT_ROUND_INTERVAL  # Use configurable round interval
        self.persistent = True
        
        # Initialize database attributes using constants
        self.db.combatants = []
        self.db.round = 0
        self.db.managed_rooms = [self.obj]  # Initially manages only its host room
        self.db.combat_is_running = False
        
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        managed_rooms = self.db.managed_rooms or []
        splattercast.msg(f"{DEBUG_PREFIX_HANDLER}_CREATE: New handler {self.key} created on {self.obj.key}, initially managing: {[r.key for r in managed_rooms]}. Combat logic initially not running.")

    def start(self):
        """
        Start the combat handler's repeat timer if combat logic isn't already running
        or if the Evennia ticker isn't active.
        
        This method ensures the combat handler is properly running and handles
        cases where the internal state might be out of sync with Evennia's ticker.
        """
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)

        # Use super().is_active to check Evennia's ticker status
        evennia_ticker_is_active = super().is_active
        combat_is_running = self.db.combat_is_running

        if combat_is_running and evennia_ticker_is_active:
            splattercast.msg(f"{DEBUG_PREFIX_HANDLER}_START: Handler {self.key} on {self.obj.key} - combat logic and Evennia ticker are already active. Skipping redundant start.")
            return

        managed_rooms = self.db.managed_rooms or []
        splattercast.msg(f"{DEBUG_PREFIX_HANDLER}_START: Handler {self.key} on {self.obj.key} (managing {[r.key for r in managed_rooms]}) - ensuring combat logic is running and ticker is scheduled.")
        
        if not combat_is_running:
            splattercast.msg(f"{DEBUG_PREFIX_HANDLER}_START_DETAIL: Setting {DB_COMBAT_RUNNING} = True for {self.key}.")
            self.db.combat_is_running = True
        
        if not evennia_ticker_is_active:
            splattercast.msg(f"{DEBUG_PREFIX_HANDLER}_START_DETAIL: Evennia ticker for {self.key} is not active (super().is_active=False). Calling force_repeat().")
            self.force_repeat()
        else:
            splattercast.msg(f"{DEBUG_PREFIX_HANDLER}_START_DETAIL: Evennia ticker was already active, but combat logic flag was corrected.")

    def stop_combat_logic(self, cleanup_combatants=True):
        """
        Stop the combat logic while optionally cleaning up combatants.
        
        This method stops the internal combat logic flag and can optionally
        clean up all combatant state. The Evennia ticker may continue running
        but no combat processing will occur.
        
        Args:
            cleanup_combatants (bool): Whether to remove all combatants and clean state
        """
        # CRITICAL: Check if handler has been deleted or never saved
        # This can happen when:
        # 1. remove_combatant() calls stop_combat_logic() on already-deleted handler
        # 2. Handler was created but never saved to database
        if not self.pk or not self.id:
            return
        
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        
        combat_was_running = self.db.combat_is_running
        
        splattercast.msg(f"{DEBUG_PREFIX_HANDLER}_{DEBUG_CLEANUP}: Handler {self.key} stopping combat logic. Was running: {combat_was_running}, cleanup_combatants: {cleanup_combatants}")

        if cleanup_combatants:
            self._cleanup_all_combatants()
        
        # Determine if we should delete the script BEFORE modifying db attributes
        combatants = self.db.combatants or []
        should_delete_script = False
        if not combatants and self.pk:
            splattercast.msg(f"{DEBUG_PREFIX_HANDLER}_{DEBUG_CLEANUP}: Handler {self.key} is empty and persistent. Marking for deletion.")
            should_delete_script = True
        
        if should_delete_script:
            # CRITICAL: Delete handler BEFORE setting db attributes
            # After delete(), self.pk becomes None and db attribute access will crash
            # See: COMBAT_HANDLER_DELETION_ANALYSIS.md
            splattercast.msg(f"{DEBUG_PREFIX_HANDLER}_{DEBUG_CLEANUP}: Preparing to delete handler script {self.key}.")
            if hasattr(self, 'id') and self.id:
                try:
                    self.save()
                    self.delete()
                    splattercast.msg(f"{DEBUG_PREFIX_HANDLER}_{DEBUG_CLEANUP}: Successfully deleted handler {self.key}.")
                    # Early return - handler is deleted, no further cleanup needed
                    return
                except Exception as e:
                    splattercast.msg(f"{DEBUG_PREFIX_HANDLER}_{DEBUG_CLEANUP}: Error deleting handler {self.key}: {e}. Trying stop().")
                    try:
                        self.stop()
                        splattercast.msg(f"{DEBUG_PREFIX_HANDLER}_{DEBUG_CLEANUP}: Successfully stopped handler {self.key}.")
                        return  # Don't continue if stop() succeeded - handler may be in invalid state
                    except Exception as e2:
                        splattercast.msg(f"{DEBUG_PREFIX_HANDLER}_{DEBUG_CLEANUP}: Error stopping handler {self.key}: {e2}. Leaving as-is.")
                        return  # Don't continue if both delete() and stop() failed
            else:
                splattercast.msg(f"{DEBUG_PREFIX_HANDLER}_{DEBUG_CLEANUP}: Handler {self.key} was not saved to database, skipping all database operations.")
                return
        
        # Only reach here if handler was NOT deleted
        # Now it's safe to modify db attributes (self.pk is still valid)
        self.db.combat_is_running = False
        self.db.round = 0
        
        # Stop the ticker if the script is saved to the database
        if hasattr(self, 'id') and self.id:
            try:
                splattercast.msg(f"{DEBUG_PREFIX_HANDLER}_{DEBUG_CLEANUP}: Handler {self.key} is not being deleted. Calling self.stop() to halt ticker.")
                self.stop()
            except Exception as e:
                splattercast.msg(f"{DEBUG_PREFIX_HANDLER}_{DEBUG_CLEANUP}: Error stopping handler {self.key}: {e}. Leaving as-is.")
        else:
            splattercast.msg(f"{DEBUG_PREFIX_HANDLER}_{DEBUG_CLEANUP}: Handler {self.key} is not saved to database, skipping stop() call.")
        
        splattercast.msg(f"{DEBUG_PREFIX_HANDLER}_{DEBUG_CLEANUP}: Combat logic stopped for {self.key}. Round reset to 0.")

    def _cleanup_all_combatants(self):
        """
        Clean up all combatant state and remove them from the handler.
        
        This method clears all proximity relationships, breaks grapples,
        and removes combat-related NDB attributes from all combatants.
        """
        cleanup_all_combatants(self)

    def at_stop(self):
        """
        Called when the script is stopped.
        
        Performs cleanup of all combatant state when the handler is stopped,
        unless a merge is in progress.
        """
        # CRITICAL: Prevent recursive calls when delete() triggers at_stop()
        # If handler is already deleted, don't try to clean up again
        if not self.pk or not self.id:
            return
        
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        splattercast.msg(f"{DEBUG_PREFIX_HANDLER}_STOP: Handler {self.key} at_stop() called. Cleaning up combat state.")
        
        # Skip cleanup if merge is in progress to preserve combatant references
        if hasattr(self, '_merge_in_progress') and self._merge_in_progress:
            splattercast.msg(f"{DEBUG_PREFIX_HANDLER}_STOP: Merge in progress for {self.key}, skipping combatant cleanup.")
            self.stop_combat_logic(cleanup_combatants=False)
        else:
            self.stop_combat_logic(cleanup_combatants=True)

    def enroll_room(self, room_to_add):
        """
        Add a room to be managed by this handler.
        
        Args:
            room_to_add: The room to add to managed rooms
        """
        managed_rooms = self.db.managed_rooms or []
        if room_to_add not in managed_rooms:
            managed_rooms.append(room_to_add)
            self.db.managed_rooms = managed_rooms

    def merge_handler(self, other_handler):
        """
        Merge another combat handler into this one.
        
        This method handles the complex logic of merging two combat handlers
        when characters move between rooms that are managed by different handlers.
        
        Args:
            other_handler: The CombatHandler to merge into this one
        """
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        
        # Defensive logging to understand the merge scenario
        splattercast.msg(f"{DEBUG_PREFIX_HANDLER}_MERGE_DEBUG: self={self} (key={self.key}, id={getattr(self, 'id', 'None')}, obj={self.obj.key})")
        splattercast.msg(f"{DEBUG_PREFIX_HANDLER}_MERGE_DEBUG: other_handler={other_handler} (key={other_handler.key}, id={getattr(other_handler, 'id', 'None')}, obj={other_handler.obj.key})")
        splattercast.msg(f"{DEBUG_PREFIX_HANDLER}_MERGE_DEBUG: Identity check: self is other_handler = {self is other_handler}")
        
        # Safety check: Don't merge a handler with itself
        if other_handler is self:
            splattercast.msg(f"{DEBUG_PREFIX_HANDLER}_MERGE: Attempted to merge handler with itself. Skipping merge.")
            return
        
        # Get combatants from both handlers
        our_combatants = self.db.combatants or []
        their_combatants = other_handler.db.combatants or []
        
        # Merge combatants lists
        for entry in their_combatants:
            char = entry.get(DB_CHAR)
            if char and char not in [e.get(DB_CHAR) for e in our_combatants]:
                our_combatants.append(entry)
        
        # Merge managed rooms
        our_rooms = self.db.managed_rooms or []
        their_rooms = other_handler.db.managed_rooms or []
        for room in their_rooms:
            if room not in our_rooms:
                our_rooms.append(room)
        
        # Update our state
        self.db.combatants = our_combatants
        self.db.managed_rooms = our_rooms
        
        # CRITICAL FIX: Update ALL combatants' handler references after merge
        # This ensures both existing and newly merged combatants point to the correct handler
        from .utils import update_all_combatant_handler_references
        update_all_combatant_handler_references(self)
        
        # Stop and clean up the other handler WITHOUT triggering at_stop cleanup
        # Set a flag to prevent at_stop() from cleaning up combatants during merge
        other_handler._merge_in_progress = True
        other_handler.stop_combat_logic(cleanup_combatants=False)
        
        # Only delete if the handler has been saved to the database
        if hasattr(other_handler, 'id') and other_handler.id:
            try:
                # Ensure the handler is properly saved before deletion
                other_handler.save()
                other_handler.delete()
                splattercast.msg(f"{DEBUG_PREFIX_HANDLER}_MERGE: Deleted other handler {other_handler.key}.")
            except Exception as e:
                splattercast.msg(f"{DEBUG_PREFIX_HANDLER}_MERGE: Error deleting other handler {other_handler.key}: {e}. Handler stopped but not deleted.")
        else:
            splattercast.msg(f"{DEBUG_PREFIX_HANDLER}_MERGE: Other handler {other_handler.key} was not saved to database, skipping delete.")
        
        # Clear the merge flag now that deletion is complete
        if hasattr(other_handler, '_merge_in_progress'):
            delattr(other_handler, '_merge_in_progress')
        
        splattercast.msg(f"{DEBUG_PREFIX_HANDLER}_MERGE: Merged {other_handler.key} into {self.key}. Now managing {len(our_rooms)} rooms with {len(our_combatants)} combatants.")

    def add_combatant(self, char, target=None, initial_grappling=None, initial_grappled_by=None, initial_is_yielding=False):
        """
        Add a character to combat.
        
        Args:
            char: The character to add
            target: Optional initial target
            initial_grappling: Optional character being grappled initially
            initial_grappled_by: Optional character grappling this char initially
            initial_is_yielding: Whether the character starts yielding
        """
        add_combatant(self, char, target, initial_grappling, initial_grappled_by, initial_is_yielding)

    def remove_combatant(self, char):
        """
        Remove a character from combat and clean up their state.
        
        Args:
            char: The character to remove from combat
        """
        remove_combatant(self, char)

    def _cleanup_combatant_state(self, char, entry):
        """
        Clean up all combat-related state for a character.
        
        Args:
            char: The character to clean up
            entry: The character's combat entry
        """
        cleanup_combatant_state(char, entry, self)

    def validate_and_cleanup_grapple_state(self):
        """
        Validate and clean up stale grapple references in the combat handler.
        
        This method checks for and fixes:
        - Stale DBREFs to characters no longer in the database
        - Invalid cross-references (A grappling B but B not grappled by A)
        - Self-grappling references
        - References to characters no longer in combat
        - Orphaned grapple states
        
        Called periodically during combat to maintain data integrity.
        """
        validate_and_cleanup_grapple_state(self)

    # ── Main combat loop ───────────────────────────────────────────────

    def at_repeat(self):
        """
        Main combat loop — dispatches to extracted modules for action
        resolution.

        Processes each combatant's turn in initiative order, delegating
        attack processing, movement resolution, and special actions to
        the ``attack``, ``movement_resolution``, and ``actions`` modules.
        """
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        if not self.db.combat_is_running:
            splattercast.msg(f"AT_REPEAT: Handler {self.key} on {self.obj.key} combat logic is not running ({DB_COMBAT_RUNNING}=False). Returning.")
            return

        if not super().is_active:
             splattercast.msg(f"AT_REPEAT: Handler {self.key} on {self.obj.key} Evennia script.is_active=False. Marking {DB_COMBAT_RUNNING}=False and returning.")
             self.db.combat_is_running = False
             return

        # Convert SaverList to regular list to avoid corruption during modifications
        combatants_list = []
        db_combatants = get_combatants_safe(self)
        for entry in db_combatants:
            # Convert each entry to a regular dict to avoid SaverList issues
            regular_entry = dict(entry)
            combatants_list.append(regular_entry)
        splattercast.msg(f"AT_REPEAT_DEBUG: Converted SaverList to regular list with {len(combatants_list)} entries")
        
        # Set up active list tracking for set_target to work during round processing
        self._active_combatants_list = combatants_list
        
        # Debug: Show target_dbref for all combatants at start of round
        for entry in combatants_list:
            char = entry.get(DB_CHAR)
            target_dbref = entry.get(DB_TARGET_DBREF)
            if char:
                splattercast.msg(f"AT_REPEAT_TARGET_DEBUG: {char.key} has target_dbref: {target_dbref}")
        
        # Debug: Also show what's actually in the database
        db_combatants_debug = get_combatants_safe(self)
        for entry in db_combatants_debug:
            char = entry.get(DB_CHAR)
            target_dbref = entry.get(DB_TARGET_DBREF)
            if char:
                splattercast.msg(f"AT_REPEAT_DB_DEBUG: {char.key} has target_dbref: {target_dbref} in database")

        # Validate and clean up stale grapple references
        self.validate_and_cleanup_grapple_state()

        # Remove orphaned combatants (no target, not grappling, not grappled, not targeted)
        from .utils import detect_and_remove_orphaned_combatants
        orphaned_chars = detect_and_remove_orphaned_combatants(self)
        if orphaned_chars:
            # Re-fetch combatants list after orphan removal
            combatants_list = []
            db_combatants = get_combatants_safe(self)
            for entry in db_combatants:
                regular_entry = dict(entry)
                combatants_list.append(regular_entry)
            # Update active list reference after orphan removal
            self._active_combatants_list = combatants_list

        # Prune invalid combatants (dead, no location, wrong room)
        combatants_list = self._validate_combatants(combatants_list)
        self._active_combatants_list = combatants_list

        if not combatants_list:
            splattercast.msg(f"AT_REPEAT: No valid combatants remain in managed rooms for handler {self.key}. Stopping.")
            self._active_combatants_list = None
            self.stop_combat_logic()
            return

        if self.db.round == 0:
            splattercast.msg(f"AT_REPEAT: Handler {self.key}. Combatants present. Starting combat in round 1.")
            self.db.round = 1

        managed_rooms = self.db.managed_rooms or []
        splattercast.msg(f"AT_REPEAT: Handler {self.key} (managing {[r.key for r in managed_rooms]}). Round {self.db.round} begins.")
        
        if len(combatants_list) <= 1:
            splattercast.msg(f"AT_REPEAT: Handler {self.key}. Not enough combatants ({len(combatants_list)}) to continue. Ending combat.")
            self._active_combatants_list = None
            self.stop_combat_logic()
            return

        # Check peaceful resolution (all yielding with no active grapples)
        if self._check_peaceful_resolution(combatants_list, managed_rooms):
            return

        # Sort combatants by initiative for processing
        initiative_order = sorted(combatants_list, key=lambda e: e.get(DB_INITIATIVE, 0), reverse=True)
        
        # Process each combatant's turn
        for combat_entry in initiative_order:
            char = combat_entry.get(DB_CHAR)
            if not char:
                splattercast.msg(f"DEBUG_LOOP_ITERATION: Skipping entry with missing character.")
                continue
            splattercast.msg(f"DEBUG_LOOP_ITERATION: Starting processing for {char.key}, combat_entry: {combat_entry}")

            # Always get a fresh reference to ensure we have current data
            current_entry = next((e for e in combatants_list if e.get(DB_CHAR) == char), None)
            if not current_entry:
                splattercast.msg(f"AT_REPEAT: {char.key} no longer in combatants list. Skipping.")
                continue

            # Skip dead/unconscious characters
            if char.is_dead():
                splattercast.msg(f"AT_REPEAT: {char.key} is dead, skipping turn.")
                continue
            elif hasattr(char, 'is_unconscious') and char.is_unconscious():
                splattercast.msg(f"AT_REPEAT: {char.key} is unconscious, skipping turn.")
                continue

            # Skip if character has skip_combat_round flag
            if hasattr(char.ndb, NDB_SKIP_ROUND) and getattr(char.ndb, NDB_SKIP_ROUND):
                delattr(char.ndb, NDB_SKIP_ROUND)
                splattercast.msg(f"AT_REPEAT: {char.key} skipping this round as requested.")
                char.msg("|yYou skip this combat round.|n")
                continue

            # Clear flee attempt flag at start of each round
            if hasattr(char.ndb, "flee_attempted_this_round"):
                delattr(char.ndb, "flee_attempted_this_round")
                splattercast.msg(f"AT_REPEAT: Cleared flee attempt flag for {char.key} at start of new round.")

            # START-OF-TURN NDB CLEANUP for charge flags
            self._cleanup_charge_flags(char, current_entry)

            # Get combat action for this character
            combat_action = current_entry.get(DB_COMBAT_ACTION)
            splattercast.msg(f"AT_REPEAT: {char.key} combat_action: {combat_action}")

            # Check if character is yielding first
            if current_entry.get(DB_IS_YIELDING, False):
                # Exception: Allow certain actions even when yielding
                if combat_action in [COMBAT_ACTION_RELEASE_GRAPPLE, COMBAT_ACTION_ADVANCE, COMBAT_ACTION_RETREAT, COMBAT_ACTION_CHARGE]:
                    splattercast.msg(f"{char.key} is yielding but can still perform {combat_action} action.")
                    # Fall through to normal action processing
                else:
                    self._handle_yielding_turn(char, current_entry)
                    continue

            # Handle being grappled (auto resist unless yielding)
            if resolve_auto_escape(self, char, current_entry, combatants_list):
                continue

            # Process combat action intent
            if combat_action:
                if self._dispatch_combat_action(char, current_entry, combatants_list, combat_action, initiative_order):
                    continue

            # Standard attack processing — get target and schedule attack
            self._schedule_attack(char, current_entry, combatants_list, initiative_order)

            # Clear the combat action after processing
            current_entry[DB_COMBAT_ACTION] = None

        # Save the modified combatants list to the database FIRST to persist
        # combat_action changes and grapple state from round processing.
        self.db.combatants = combatants_list
        splattercast.msg(f"AT_REPEAT_SAVE: Saved modified combatants list back to database.")

        # Clear active list tracking BEFORE death check
        self._active_combatants_list = None

        # Check for dead or unconscious combatants after all attacks
        self._remove_incapacitated(splattercast)

        # Check if combat should continue
        remaining_combatants = self.db.combatants or []
        if not remaining_combatants:
            splattercast.msg(f"AT_REPEAT: No combatants remain in handler {self.key}. Stopping.")
            self.stop_combat_logic()
            return
        elif len(remaining_combatants) <= 1:
            splattercast.msg(f"AT_REPEAT: Only {len(remaining_combatants)} combatant(s) remain in handler {self.key}. Ending combat.")
            self.stop_combat_logic()
            return

        self.db.round += 1
        splattercast.msg(f"AT_REPEAT: Handler {self.key}. Round {self.db.round} scheduled for next interval.")

    # ── at_repeat helper methods ───────────────────────────────────────

    def _validate_combatants(self, combatants_list):
        """
        Prune combatants with missing characters, no location, or in
        unmanaged rooms.

        Args:
            combatants_list: List of combat entry dicts.

        Returns:
            list: Filtered list of valid combat entry dicts.
        """
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        valid = []
        managed_rooms = self.db.managed_rooms or []
        for entry in combatants_list:
            char = entry.get(DB_CHAR)
            if not char:
                splattercast.msg(f"AT_REPEAT: Pruning missing character from handler {self.key}.")
                continue
            if not char.location:
                splattercast.msg(f"AT_REPEAT: Pruning {char.key} (no location) from handler {self.key}.")
                if hasattr(char, "ndb") and getattr(char.ndb, NDB_COMBAT_HANDLER) == self:
                    delattr(char.ndb, NDB_COMBAT_HANDLER)
                continue
            if char.location not in managed_rooms:
                splattercast.msg(f"AT_REPEAT: Pruning {char.key} (in unmanaged room {char.location.key}) from handler {self.key}.")
                if hasattr(char, "ndb") and getattr(char.ndb, NDB_COMBAT_HANDLER) == self:
                    delattr(char.ndb, NDB_COMBAT_HANDLER)
                continue
            valid.append(entry)
        return valid

    def _check_peaceful_resolution(self, combatants_list, managed_rooms):
        """
        Check if all combatants are yielding with no active grapples.
        If so, end combat peacefully.

        Args:
            combatants_list: List of combat entry dicts.
            managed_rooms: List of managed room objects.

        Returns:
            bool: ``True`` if combat was ended peacefully.
        """
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)

        all_yielding = all(
            entry.get(DB_IS_YIELDING, False) for entry in combatants_list
        )
        any_active_grapples = any(
            entry.get(DB_GRAPPLING_DBREF) is not None
            or entry.get(DB_GRAPPLED_BY_DBREF) is not None
            for entry in combatants_list
        )

        if all_yielding and not any_active_grapples:
            splattercast.msg(f"AT_REPEAT: Handler {self.key}. All combatants are yielding with no active grapples. Ending combat peacefully.")
            for entry in combatants_list:
                char = entry.get(DB_CHAR)
                if char and char.location:
                    char.msg("|gWith all hostilities ceased, the confrontation comes to a peaceful end.|n")
            for room in managed_rooms:
                if room:
                    room.msg_contents(
                        "|gThe confrontation ends peacefully as all participants stand down.|n",
                        exclude=[entry.get(DB_CHAR) for entry in combatants_list if entry.get(DB_CHAR)],
                    )
            self._active_combatants_list = None
            self.stop_combat_logic()
            return True
        elif all_yielding and any_active_grapples:
            splattercast.msg(f"AT_REPEAT: Handler {self.key}. All combatants yielding but active grapples present. Combat continues in restraint mode.")

        return False

    def _cleanup_charge_flags(self, char, entry):
        """
        Clean up charge-related NDB flags at the start of a turn.

        Args:
            char: The character whose flags to clean.
            entry: The character's combat entry dict.
        """
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)

        if hasattr(char.ndb, "charging_vulnerability_active"):
            splattercast.msg(f"AT_REPEAT_START_TURN_CLEANUP: Clearing charging_vulnerability_active for {char.key} (was active from their own previous charge).")
            delattr(char.ndb, "charging_vulnerability_active")

        if hasattr(char.ndb, "charge_attack_bonus_active") and getattr(char.ndb, "charge_attack_bonus_active", False):
            if (
                entry.get(DB_IS_YIELDING, False)
                or char.is_dead()
                or (hasattr(char, 'is_unconscious') and char.is_unconscious())
            ):
                splattercast.msg(f"AT_REPEAT_START_TURN_CLEANUP: Clearing unused charge_attack_bonus_active for {char.key} (won't attack this turn).")
                delattr(char.ndb, "charge_attack_bonus_active")
            else:
                splattercast.msg(f"AT_REPEAT_START_TURN_CLEANUP: {char.key} has charge_attack_bonus_active - will be consumed during attack.")

    def _handle_yielding_turn(self, char, entry):
        """
        Handle a yielding character's turn (restraint mode or passive).

        Args:
            char: The yielding character.
            entry: The character's combat entry dict.
        """
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)

        grappling_target = self.get_grappling_obj(entry)
        if grappling_target:
            # Grappler in restraint mode — maintain hold without violence
            splattercast.msg(f"{char.key} is yielding but maintains restraining hold on {grappling_target.key}.")
            char.msg(f"|gYou maintain a restraining hold on {grappling_target.key} without violence.|n")
            grappling_target.msg(f"|g{char.key} maintains a gentle but firm restraining hold on you.|n")
            char.location.msg_contents(f"|g{char.key} maintains a restraining hold on {grappling_target.key}.|n", exclude=[char, grappling_target])
        else:
            # Regular yielding behavior
            splattercast.msg(f"{char.key} is yielding and takes no hostile action this turn.")
            char.location.msg_contents(f"|y{char.key} holds their action, appearing non-hostile.|n", exclude=[char])
            char.msg("|yYou hold your action, appearing non-hostile.|n")

    def _dispatch_combat_action(self, char, entry, combatants_list, combat_action, initiative_order):
        """
        Dispatch a combat action to the appropriate handler.

        Args:
            char: The acting character.
            entry: The character's combat entry dict.
            combatants_list: List of all combat entry dicts.
            combat_action: The action to dispatch (str or dict).
            initiative_order: List of entries sorted by initiative.

        Returns:
            bool: ``True`` if the action consumed the turn.
        """
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        splattercast.msg(f"AT_REPEAT: {char.key} has action_intent: {combat_action}")

        if isinstance(combat_action, str):
            return self._dispatch_string_action(
                char, entry, combatants_list, combat_action,
            )
        elif isinstance(combat_action, dict):
            return self._dispatch_dict_action(
                char, entry, combatants_list, combat_action,
            )

        return False

    def _dispatch_string_action(self, char, entry, combatants_list, combat_action):
        """
        Dispatch a string-based combat action.

        Args:
            char: The acting character.
            entry: The character's combat entry dict.
            combatants_list: List of all combat entry dicts.
            combat_action: The action string.

        Returns:
            bool: ``True`` if the action consumed the turn.
        """
        if combat_action == COMBAT_ACTION_GRAPPLE_INITIATE:
            self._resolve_grapple_initiate(entry, combatants_list)
            entry[DB_COMBAT_ACTION] = None
            return True
        elif combat_action == COMBAT_ACTION_GRAPPLE_JOIN:
            self._resolve_grapple_join(entry, combatants_list)
            entry[DB_COMBAT_ACTION] = None
            return True
        elif combat_action == COMBAT_ACTION_GRAPPLE_TAKEOVER:
            self._resolve_grapple_takeover(entry, combatants_list)
            entry[DB_COMBAT_ACTION] = None
            return True
        elif combat_action == COMBAT_ACTION_RELEASE_GRAPPLE:
            self._resolve_release_grapple(entry, combatants_list)
            entry[DB_COMBAT_ACTION] = None
            return True
        elif combat_action == COMBAT_ACTION_RETREAT:
            resolve_retreat(self, char, entry)
            entry[DB_COMBAT_ACTION] = None
            entry[DB_COMBAT_ACTION_TARGET] = None
            return True
        elif combat_action == COMBAT_ACTION_ADVANCE:
            resolve_advance(self, char, entry)
            entry[DB_COMBAT_ACTION] = None
            entry[DB_COMBAT_ACTION_TARGET] = None
            return True
        elif combat_action == COMBAT_ACTION_CHARGE:
            resolve_charge(self, char, entry, combatants_list)
            entry[DB_COMBAT_ACTION] = None
            entry[DB_COMBAT_ACTION_TARGET] = None
            return True
        elif combat_action == COMBAT_ACTION_DISARM:
            resolve_disarm(self, char, entry)
            entry[DB_COMBAT_ACTION] = None
            entry[DB_COMBAT_ACTION_TARGET] = None
            return True

        return False

    def _dispatch_dict_action(self, char, entry, combatants_list, combat_action):
        """
        Dispatch a dict-based combat action (grapple attempt or escape).

        Args:
            char: The acting character.
            entry: The character's combat entry dict.
            combatants_list: List of all combat entry dicts.
            combat_action: The action dict with ``type`` and ``target``.

        Returns:
            bool: ``True`` if the action consumed the turn.
        """
        intent_type = combat_action.get("type")

        if intent_type == "grapple":
            return resolve_grapple_attempt(
                self, char, entry, combatants_list,
            )
        elif intent_type == COMBAT_ACTION_ESCAPE_GRAPPLE:
            return resolve_escape_grapple(
                self, char, entry, combatants_list,
            )

        return False

    def _schedule_attack(self, char, entry, combatants_list, initiative_order):
        """
        Schedule a standard attack for a character using staggered delay.

        Args:
            char: The attacking character.
            entry: The character's combat entry dict.
            combatants_list: List of all combat entry dicts.
            initiative_order: List of entries sorted by initiative.
        """
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)

        target = self.get_target(char)
        splattercast.msg(f"AT_REPEAT: After get_target(), {char.key} target is {target.key if target else None}")
        if target:
            attack_delay = calculate_attack_delay(
                self, char, initiative_order,
            )
            splattercast.msg(f"AT_REPEAT: Scheduling attack for {char.key} -> {target.key} with {attack_delay}s delay")
            delay(
                attack_delay, process_delayed_attack,
                self, char, target, entry, combatants_list,
            )
        else:
            splattercast.msg(f"AT_REPEAT: {char.key} has no valid target for attack.")

    def _remove_incapacitated(self, splattercast):
        """
        Remove dead or unconscious combatants after all attacks are
        processed.

        Args:
            splattercast: The Splattercast channel object.
        """
        remaining_combatants = self.db.combatants or []
        incapacitated = []

        for entry in remaining_combatants:
            char = entry.get(DB_CHAR)
            if char and hasattr(char, 'is_dead') and char.is_dead():
                incapacitated.append(char)
                splattercast.msg(f"POST_ROUND_DEATH_CHECK: {char.key} is dead, removing from combat.")
            elif char and hasattr(char, 'is_unconscious') and char.is_unconscious():
                incapacitated.append(char)
                splattercast.msg(f"POST_ROUND_UNCONSCIOUS_CHECK: {char.key} is unconscious, removing from combat.")

        for incapacitated_char in incapacitated:
            self.remove_combatant(incapacitated_char)

    # ── Target management ──────────────────────────────────────────────

    def get_target(self, char):
        """Get the target character for a given character."""
        # Use active list if available (during round processing), otherwise use database
        active_list = getattr(self, '_active_combatants_list', None)
        if active_list:
            combatants_list = active_list
        else:
            combatants_list = self.db.combatants or []
        
        entry = next((e for e in combatants_list if e.get(DB_CHAR) == char), None)
        if entry:
            return self.get_target_obj(entry)
        return None
    
    def set_target(self, char, target):
        """Set the target for a given character."""
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        
        # Follow the same pattern as utils.py functions:
        # 1. Get a copy of the combatants list
        # 2. Modify the copy
        # 3. Save the entire modified copy back
        combatants = self.db.combatants or []
        db_entry = next((e for e in combatants if e.get(DB_CHAR) == char), None)
        
        if db_entry:
            new_target_dbref = self._get_dbref(target) if target else None
            old_target_dbref = db_entry.get(DB_TARGET_DBREF)
            
            # Update database entry in the copy
            db_entry[DB_TARGET_DBREF] = new_target_dbref
            
            # CRITICAL: Also update active processing list if it exists
            # This prevents the working copy from reverting the change at end of round
            active_list = getattr(self, '_active_combatants_list', None)
            if active_list:
                active_entry = next((e for e in active_list if e.get(DB_CHAR) == char), None)
                if active_entry:
                    active_entry[DB_TARGET_DBREF] = new_target_dbref
                    splattercast.msg(f"SET_TARGET: Updated both DB and active list for {char.key}")
            
            # Save the modified copy back (following utils.py pattern)
            self.db.combatants = combatants
            
            if target:
                splattercast.msg(f"SET_TARGET: {char.key} target changed from {old_target_dbref} to {new_target_dbref} ({target.key})")
                # Verify the change was saved
                verification_list = self.db.combatants or []
                verification_entry = next((e for e in verification_list if e.get(DB_CHAR) == char), None)
                if verification_entry:
                    actual_dbref = verification_entry.get(DB_TARGET_DBREF)
                    splattercast.msg(f"SET_TARGET_VERIFY: {char.key} database now shows target_dbref: {actual_dbref}")
            else:
                splattercast.msg(f"SET_TARGET: {char.key} target cleared to None")
            
            return True
        return False

    # ── Utility wrappers ───────────────────────────────────────────────

    def get_target_obj(self, combatant_entry):
        """Get the target object for a combatant entry."""
        return get_combatant_target(combatant_entry, self)
    
    def get_grappling_obj(self, combatant_entry):
        """Get the character that this combatant is grappling."""
        return get_combatant_grappling_target(combatant_entry, self)
    
    def get_grappled_by_obj(self, combatant_entry):
        """Get the character that is grappling this combatant."""
        return get_combatant_grappled_by(combatant_entry, self)
    
    def _get_dbref(self, char):
        """Get DBREF for a character object."""
        return get_character_dbref(char)
    
    def _get_char_by_dbref(self, dbref):
        """Get character object by DBREF."""
        return get_character_by_dbref(dbref)
    
    def _are_characters_in_mutual_combat(self, char1, char2):
        """
        Check if two characters are targeting each other in active combat.
        Used to restore proximity after server reloads.
        """
        combatants_list = self.db.combatants or []
        char1_entry = None
        char2_entry = None
        
        # Find both characters in combatants list
        for entry in combatants_list:
            if entry[DB_CHAR] == char1:
                char1_entry = entry
            elif entry[DB_CHAR] == char2:
                char2_entry = entry
        
        # Both must be in combat and targeting each other
        if char1_entry and char2_entry:
            char1_target_dbref = char1_entry.get(DB_TARGET_DBREF)
            char2_target_dbref = char2_entry.get(DB_TARGET_DBREF) 
            char1_dbref = self._get_dbref(char1)
            char2_dbref = self._get_dbref(char2)
            
            return (char1_target_dbref == char2_dbref and 
                   char2_target_dbref == char1_dbref)
        
        return False

    # ── Grapple resolution wrappers ────────────────────────────────────

    def _resolve_grapple_initiate(self, char_entry, combatants_list):
        """Resolve a grapple initiate action."""
        resolve_grapple_initiate(char_entry, combatants_list, self)
    
    def _resolve_grapple_join(self, char_entry, combatants_list):
        """Resolve a grapple join action."""
        resolve_grapple_join(char_entry, combatants_list, self)
    
    def _resolve_grapple_takeover(self, char_entry, combatants_list):
        """Resolve a grapple takeover action."""
        resolve_grapple_takeover(char_entry, combatants_list, self)
    
    def _resolve_release_grapple(self, char_entry, combatants_list):
        """Resolve a release grapple action."""
        resolve_release_grapple(char_entry, combatants_list, self)
    
    def resolve_bonus_attack(self, attacker, target):
        """
        Resolve a bonus attack triggered by specific combat events.
        
        Args:
            attacker: The character making the bonus attack
            target: The target of the bonus attack
        """
        resolve_bonus_attack(self, attacker, target)
