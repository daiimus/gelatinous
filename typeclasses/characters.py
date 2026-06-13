"""
Characters

Characters are (by default) Objects setup to be puppeted by Accounts.
They are what you "see" in game. The Character class in this module
is setup to be the "default" character type created by the default
creation commands.

"""

from evennia.objects.objects import DefaultCharacter
from evennia.typeclasses.attributes import AttributeProperty
from world.combat.debug import get_splattercast

from world.combat.constants import NDB_AIMED_AT_BY, NDB_AIMING_AT, NDB_AIMING_DIRECTION, NDB_COMBAT_HANDLER
from world.identity_utils import msg_room_identity

from .objects import ObjectParent
from .armor_mixin import ArmorMixin
from .clothing_mixin import ClothingMixin
from .appearance_mixin import AppearanceMixin


# ---------------------------------------------------------------------
# Mr. Hands name aliases (#307, PR-H2)
# ---------------------------------------------------------------------
#: User-facing shorthand → canonical anatomical container name.
#: Lets ``wield baton in left`` continue to work while the underlying
#: storage uses the anatomical key (``left_hand``).  Aliases that
#: don't resolve fall through unchanged, so callers can pass a
#: canonical key directly without a round-trip.
HAND_NAME_ALIASES = {
    "left": "left_hand",
    "right": "right_hand",
    "l": "left_hand",
    "r": "right_hand",
}


def _canonical_hand(hand):
    """Resolve user-facing ``hand`` shorthand to canonical
    anatomical container name.

    Lower-cases the input, then maps via :data:`HAND_NAME_ALIASES`.
    Unmapped values pass through unchanged (so canonical inputs
    like ``"left_hand"`` are no-ops).
    """
    if not isinstance(hand, str):
        return hand
    lowered = hand.strip().lower()
    return HAND_NAME_ALIASES.get(lowered, lowered)


def _humanize_hand(canonical):
    """Render a canonical container name for player-facing prose.

    ``left_hand`` → ``"left hand"``.  Generic fallback: underscores
    to spaces.  Future species-aware rendering can consult
    ``get_species_location_display`` if needed.
    """
    if not isinstance(canonical, str):
        return str(canonical)
    return canonical.replace("_", " ")


class Character(
    ArmorMixin, ClothingMixin, AppearanceMixin, ObjectParent, DefaultCharacter
):
    """
    The Character just re-implements some of the Object's methods and hooks
    to represent a Character entity in-game.

    See mygame/typeclasses/objects.py for a list of
    properties and methods available on all Object child classes like this.

    In this instance, we are also adding the G.R.I.M. attributes using AttributeProperty.

    Mixins (Phase 4 decomposition):
        ArmorMixin: Damage reduction, plate carrier expansion, armor degradation.
        ClothingMixin: Clothing wearing/removal, layer conflicts, coverage queries.
        AppearanceMixin: Longdesc system, appearance rendering, pronoun resolution.
    """
    
    # G.R.I.M. Attributes
    # Grit, Resonance, Intellect, Motorics
    grit = AttributeProperty(1, category='stat', autocreate=True)
    resonance = AttributeProperty(1, category='stat', autocreate=True)
    intellect = AttributeProperty(1, category='stat', autocreate=True)
    motorics = AttributeProperty(1, category='stat', autocreate=True)
    sex = AttributeProperty("ambiguous", category="biology", autocreate=True)

    # Identity & Recognition System (Phase 1b)
    # sleeve_uid is the physical body identity — flash clones inherit it.
    # Set in at_object_creation() via uuid.uuid4(); chargen may override.
    sleeve_uid = AttributeProperty(None, category="identity")
    height = AttributeProperty(None, category="identity")
    build = AttributeProperty(None, category="identity")
    hair_color = AttributeProperty(None, category="identity")
    hair_style = AttributeProperty(None, category="identity")
    sdesc_keyword = AttributeProperty(None, category="identity")
    recognition_memory = AttributeProperty({}, category="identity", autocreate=True)
    species = AttributeProperty("human", category="identity")

    # Shop System Attributes
    is_merchant = AttributeProperty(False, category="shop", autocreate=True)
    is_holographic = AttributeProperty(False, category="shop", autocreate=True)
    tokens = AttributeProperty(0, category="shop", autocreate=True)
    
    # Sleeve iteration counter (cosmetic; drives Roman-numeral suffix in
    # display name). Starts at 1 so first sleeve renders as "<name> I";
    # incremented in at_death so each subsequent clone advances the numeral.
    # Player-facing only — not consumed by any combat/identity mechanic.
    death_count = AttributeProperty(1, category='mortality', autocreate=True)
    
    # Appearance attributes - stored in db but no auto-creation for optional features
    # skintone is set via @skintone command and stored as db.skintone

    @property
    def gender(self):
        """
        Maps the existing sex attribute to Evennia's pronoun system.
        Returns a string suitable for use with $pron() functions.
        
        Maps:
        - "male", "man", "masculine" -> "male"
        - "female", "woman", "feminine" -> "female"  
        - "ambiguous", "neutral", "non-binary", "they" -> "neutral"
        - default -> "neutral"
        """
        sex_value = (self.sex or "ambiguous").lower().strip()
        
        # Male mappings
        if sex_value in ("male", "man", "masculine", "m"):
            return "male"
        # Female mappings
        elif sex_value in ("female", "woman", "feminine", "f"):
            return "female"
        # Neutral/ambiguous mappings (default)
        else:
            return "neutral"

# Possession Identifier
    def is_possessed(self):
        """
        Returns True if this character is currently puppeted by a player session.
        """
        return bool(self.sessions.all())

# Health Points - REMOVED in Phase 3: Pure Medical System
    # Legacy HP system eliminated - health now managed entirely by medical system
    # Death/unconsciousness determined by organ functionality and medical conditions

    # Character Placement Descriptions
    look_place = AttributeProperty("standing here.", category='description', autocreate=True)
    temp_place = AttributeProperty("", category='description', autocreate=True)
    override_place = AttributeProperty("", category='description', autocreate=True)
    
    def at_object_creation(self):
        """
        Called once, at creation, to set dynamic stats.
        """
        super().at_object_creation()

        # Initialize longdesc system with species-appropriate anatomy
        # (issue #356 Phase 3).  Default species at this point is None
        # → falls back to human; chargen / spawn flows that set species
        # before ``at_object_creation`` get rat-appropriate longdesc
        # surfaces directly.
        from world.anatomy import get_species_default_longdesc_locations
        if not self.longdesc:
            self.longdesc = get_species_default_longdesc_locations(
                getattr(self.db, "species", None)
            )

        # Initialize identity: assign a unique sleeve_uid for this body
        if self.sleeve_uid is None:
            import uuid
            self.sleeve_uid = str(uuid.uuid4())

        # Initialize medical system - replaces legacy HP system
        self._initialize_medical_state()

    def _initialize_medical_state(self):
        """Initialize the character's medical state."""
        from world.medical.utils import initialize_character_medical_state
        initialize_character_medical_state(self)

    @property
    def medical_state(self):
        """Get the character's medical state, loading from db if needed."""
        if not hasattr(self, '_medical_state') or self._medical_state is None:
            from world.medical.utils import load_medical_state
            load_medical_state(self)
        return self._medical_state
        
    @medical_state.setter
    def medical_state(self, value):
        """Set the character's medical state."""
        self._medical_state = value
        
    def save_medical_state(self):
        """Save medical state to database."""
        from world.medical.utils import save_medical_state
        save_medical_state(self)

    def msg(self, text=None, from_obj=None, session=None, **kwargs):
        """
        Override msg method to implement death curtain message filtering.
        
        Dead characters receive only essential messages for immersive death experience.
        This catches ALL messages to characters, including combat, explosives, admin commands.
        """
        # If not dead, use normal messaging
        if not self.is_dead():
            return super().msg(text=text, from_obj=from_obj, session=session, **kwargs)
            
        # Death curtain filtering for dead characters
        if not text:
            return
            
        # Block most system messages (from_obj=None), but allow death curtain animations
        if not from_obj:
            # Allow death curtain animations (contains block characters)
            if '▓' in str(text):
                return super().msg(text=text, from_obj=from_obj, session=session, **kwargs)
            else:
                # Block other system messages (combat, explosives, medical, etc.)
                return
            
        # Allow messages from staff (for admin commands, but not social)
        if hasattr(from_obj, 'locks') and from_obj.locks.check(from_obj, "perm(Builder)"):
            # Even staff social messages should be blocked for immersion
            # But allow admin command messages through
            if not self._is_social_message(text, kwargs):
                return super().msg(text=text, from_obj=from_obj, session=session, **kwargs)
            else:
                return
            
        # Allow death progression messages from curtain of death
        if hasattr(from_obj, 'key') and 'curtain' in str(from_obj.key).lower():
            return super().msg(text=text, from_obj=from_obj, session=session, **kwargs)
            
        # Allow death progression script messages
        if hasattr(from_obj, 'key') and 'death_progression' in str(from_obj.key).lower():
            return super().msg(text=text, from_obj=from_obj, session=session, **kwargs)
            
        # Block all other messages (social commands, medical, etc.)
        return
        
    def _is_social_message(self, text, kwargs):
        """
        Determine if this is a social message that should be blocked even for staff.
        
        Args:
            text: Message text
            kwargs: Message parameters
            
        Returns:
            bool: True if this is a social message, False otherwise
        """
        # Check for social message indicators
        if isinstance(kwargs.get('type'), str):
            social_types = ['say', 'pose', 'emote', 'tell', 'whisper', 'ooc']
            if kwargs['type'] in social_types:
                return True
                
        # Check text patterns for social messages
        if isinstance(text, str):
            social_patterns = [' says, "', ' tells you', ' whispers', ' emotes']
            for pattern in social_patterns:
                if pattern in text:
                    return True
                    
        return False

    # ===================================================================
    # MORTALITY MANAGEMENT
    # ===================================================================
    # NOTE: take_damage() and armor methods are in ArmorMixin.
    # Legacy method take_anatomical_damage removed - functionality merged into take_damage()
    
    def is_dead(self):
        """
        Returns True if character should be considered dead.
        
        Uses pure medical system - death from vital organ failure or blood loss.
        """
        try:
            medical_state = self.medical_state
            if medical_state:
                return medical_state.is_dead()
        except AttributeError:
            pass  # Medical system not available - character is alive
        
        return False
        
    def is_unconscious(self):
        """
        Returns True if character is unconscious.
        
        Uses medical system to determine unconsciousness from injuries,
        blood loss, or pain.
        """
        try:
            medical_state = self.medical_state
            if medical_state:
                return medical_state.is_unconscious()
        except AttributeError:
            pass  # Medical system not available
        return False

    def _handle_unconsciousness(self):
        """
        Handle character becoming unconscious from medical injuries.
        
        Provides unconsciousness messaging to character and room.
        Triggers removal from combat if currently fighting.
        """
        from world.combat.constants import NDB_COMBAT_HANDLER
        from evennia.utils.utils import delay
        
        # Prevent double unconsciousness processing
        if hasattr(self, 'ndb') and getattr(self.ndb, 'unconsciousness_processed', False):
            splattercast = get_splattercast()
            splattercast.msg(f"UNCONSCIOUS_SKIP: {self.key} already processed unconsciousness, skipping")
            return
            
        # Mark unconsciousness as processed
        self.ndb.unconsciousness_processed = True
        
        # Set unconscious placement description
        self.override_place = "unconscious and motionless."
        
        # Check if character is in active combat - if so, defer unconsciousness message
        is_in_combat = hasattr(self.ndb, NDB_COMBAT_HANDLER) and getattr(self.ndb, NDB_COMBAT_HANDLER) is not None
        
        if is_in_combat:
            # Set flag for combat system to trigger unconsciousness message after attack message
            self.ndb.unconsciousness_pending = True
            splattercast = get_splattercast()
            splattercast.msg(f"UNCONSCIOUS_COMBAT: {self.key} unconsciousness message deferred - in active combat")
            
            # Safety fallback - trigger message after 5 seconds if combat doesn't handle it
            def fallback_unconsciousness_message():
                if hasattr(self.ndb, 'unconsciousness_pending') and self.ndb.unconsciousness_pending:
                    splattercast = get_splattercast()
                    splattercast.msg(f"UNCONSCIOUS_FALLBACK: {self.key} triggering fallback unconsciousness message")
                    self._show_unconsciousness_message()
                    self.ndb.unconsciousness_pending = False
            
            delay(5, fallback_unconsciousness_message)
        else:
            # Not in combat - show unconsciousness message immediately
            self._show_unconsciousness_message()

    def _show_unconsciousness_message(self):
        """
        Show the unconsciousness message to character and room.
        Separated from _handle_unconsciousness for deferred messaging coordination.
        
        NOTE: Messages commented out to avoid duplicates with consciousness suppression conditions.
        """
        # self.msg("|rYou collapse, unconscious from your injuries!|n")
        # if self.location:
        #     self.location.msg_contents(
        #         f"|r{self.key} collapses, unconscious!|n",
        #         exclude=self
        #     )
        
        # Check if character is in combat and remove them
        combat_handler = getattr(self.ndb, NDB_COMBAT_HANDLER, None)
        if combat_handler:
            try:
                combat_handler.remove_combatant(self)
                from world.combat.utils import debug_broadcast
                debug_broadcast(f"{self.key} removed from combat due to unconsciousness", "MEDICAL", "UNCONSCIOUS")
            except Exception as e:
                # Deliberate guard (#469): a combat-removal bug must not
                # abort the unconsciousness transition itself.  Logged.
                from world.combat.utils import debug_broadcast
                debug_broadcast(f"Error removing {self.key} from combat on unconsciousness: {e}", "MEDICAL", "ERROR")
        
        # Optional: Debug broadcast for tracking
        try:
            from world.combat.utils import debug_broadcast
            debug_broadcast(f"{self.key} became unconscious from medical injuries", "MEDICAL", "UNCONSCIOUS")
        except ImportError:
            pass  # debug_broadcast not available
        
        # Apply unconscious command restrictions
        self.apply_unconscious_state()

    def debug_death_analysis(self):
        """
        Debug method to show detailed cause of death analysis.
        Returns comprehensive information about why character died or current vital status.
        """
        try:
            medical_state = self.medical_state
            if not medical_state:
                return "No medical state available"
            
            from world.medical.constants import BLOOD_LOSS_DEATH_THRESHOLD
            
            # Check vital organ capacities
            blood_pumping = medical_state.calculate_body_capacity("blood_pumping")
            breathing = medical_state.calculate_body_capacity("breathing") 
            digestion = medical_state.calculate_body_capacity("digestion")
            consciousness = medical_state.calculate_body_capacity("consciousness")
            
            # Check blood level
            blood_level = medical_state.blood_level
            blood_loss_fatal = blood_level <= (100.0 - BLOOD_LOSS_DEATH_THRESHOLD)
            
            # Build analysis
            analysis = [
                f"=== DEATH ANALYSIS FOR {self.key} ===",
                f"Blood Pumping Capacity: {blood_pumping:.1%} {'FATAL' if blood_pumping <= 0 else 'OK'}",
                f"Breathing Capacity: {breathing:.1%} {'FATAL' if breathing <= 0 else 'OK'}",
                f"Digestion Capacity: {digestion:.1%} {'FATAL' if digestion <= 0 else 'OK'}",
                f"Consciousness: {consciousness:.1%} {'UNCONSCIOUS' if consciousness < 0.3 else 'CONSCIOUS'}",
                f"Blood Level: {blood_level:.1f}% {'FATAL BLOOD LOSS' if blood_loss_fatal else 'OK'}",
                f"Pain Level: {medical_state.pain_level:.1f}",
                f"Overall Status: {'DEAD' if self.is_dead() else 'ALIVE'}"
            ]
            
            # If dead, identify primary cause
            if self.is_dead():
                causes = []
                if blood_pumping <= 0:
                    causes.append("HEART FAILURE")
                if breathing <= 0:
                    causes.append("RESPIRATORY FAILURE") 
                if digestion <= 0:
                    causes.append("LIVER FAILURE")
                if blood_loss_fatal:
                    causes.append("BLOOD LOSS")
                
                analysis.append(f"Primary Cause(s): {', '.join(causes)}")
            
            return "\n".join(analysis)
            
        except Exception as e:
            return f"Error in death analysis: {e}"
    
    def archive_character(self, reason="manual", disconnect_msg=None):
        """
        Archive this character and disconnect any active sessions.
        
        Args:
            reason (str): Why the character is being archived (e.g., "death", "manual")
            disconnect_msg (str): Optional custom disconnect message. If None, uses default.
        """
        import time
        
        # Log warning if archiving a staff character (shouldn't happen normally)
        if self.account and self.account.is_superuser:
            splattercast = get_splattercast()
            splattercast.msg(f"WARNING: Archiving staff character {self.key} (Account: {self.account.key}, Reason: {reason})")
        
        # Set account's last_character for respawn flow
        if self.account:
            self.account.db.last_character = self
        
        # Increment death_count for proper Roman numeral naming on respawn
        # (This ensures "Jorge Jackson" -> "Jorge Jackson II" etc.)
        self.death_count += 1
        
        # Set archive flags
        self.db.archived = True
        self.db.archived_reason = reason
        self.db.archived_date = time.time()
        
        # Move character to Limbo to prevent appearing as NPC in game world
        from evennia import search_object
        limbo = search_object("#2")  # Limbo is always dbref #2
        if limbo:
            limbo = limbo[0]
            current_location = self.location
            self.move_to(limbo, quiet=True, move_hooks=False)
            
            # Log the move
            splattercast = get_splattercast()
            splattercast.msg(f"ARCHIVE: Moved {self.key} from {current_location.key if current_location else 'None'} to Limbo")
        
        # Disconnect any active sessions
        if self.sessions.all():
            if not disconnect_msg:
                disconnect_msg = "|ySleeve has been archived. Please reconnect to continue.|n"
            
            for session in self.sessions.all():
                session.sessionhandler.disconnect(session, reason=disconnect_msg)
    
    def get_death_cause(self):
        """
        Get simple death cause for user-facing messages.
        
        Returns:
            str: Simple death cause description or None if not dead
        """
        if not self.is_dead():
            return None
            
        try:
            medical_state = self.medical_state
            if not medical_state:
                return "unknown causes"
            
            from world.medical.constants import BLOOD_LOSS_DEATH_THRESHOLD
            
            # Check causes in priority order
            blood_pumping = medical_state.calculate_body_capacity("blood_pumping")
            breathing = medical_state.calculate_body_capacity("breathing") 
            digestion = medical_state.calculate_body_capacity("digestion")
            blood_level = medical_state.blood_level
            blood_loss_fatal = blood_level <= (100.0 - BLOOD_LOSS_DEATH_THRESHOLD)
            
            # Return first fatal condition found (in priority order)
            if blood_loss_fatal:
                return "blood loss"
            elif blood_pumping <= 0:
                return "heart failure"
            elif breathing <= 0:
                return "respiratory failure"
            elif digestion <= 0:
                return "organ failure"
            else:
                return "critical injuries"
                
        except Exception:
            return "unknown causes"
        
    def get_medical_status(self):
        """
        Get a detailed medical status report.
        
        Returns:
            str: Human-readable medical status
        """
        from world.medical.utils import get_medical_status_summary
        return get_medical_status_summary(self)
        
    def add_medical_condition(self, condition_type, location=None, severity="minor", **kwargs):
        """
        Add a medical condition to this character.
        
        Args:
            condition_type (str): Type of condition (bleeding, fracture, etc.)
            location (str, optional): Body location affected
            severity (str): Severity level
            **kwargs: Additional condition properties
            
        Returns:
            MedicalCondition: The added condition
        """
        condition = self.medical_state.add_condition(condition_type, location, severity, **kwargs)
        self.save_medical_state()
        return condition

    def get_search_candidates(self, searchdata, **kwargs):
        """
        Override to include aimed-at room contents when aiming.
        
        This is called by the search method to determine what objects
        are available to search through. When aiming at a direction,
        this includes both current room and aimed-room contents.
        
        Args:
            searchdata (str): The search criterion
            **kwargs: Same as passed to search method
            
        Returns:
            list: Objects that can be searched through
        """
        # Get the default candidates first
        candidates = super().get_search_candidates(searchdata, **kwargs)
        
        # Don't interfere with self-lookup or basic character functionality
        # Only enhance when specifically aiming at a direction
        aiming_direction = getattr(self.ndb, 'aiming_direction', None) if hasattr(self, 'ndb') else None
        
        if (candidates is not None and 
            aiming_direction and 
            self.location and
            hasattr(self.location, 'search_for_target')):  # Make sure the room supports this
            try:
                # Use the room's search_for_target method to get unified candidates
                # This leverages the existing vetted aiming logic
                unified_candidates = self.location.search_for_target(
                    self, searchdata, return_candidates_only=True
                )
                if unified_candidates:
                    # Use the unified candidates instead of default ones
                    # This maintains ordinal support and all existing logic
                    candidates = unified_candidates
            except (AttributeError, TypeError):
                # If anything goes wrong, fall back to default candidates
                # This ensures we never break normal searching
                pass
        
        return candidates

    def at_death(self):
        """
        Handles what happens when this character dies.
        Shows death curtain which will then start the death progression system.
        """
        from .curtain_of_death import show_death_curtain
        from world.combat.constants import NDB_COMBAT_HANDLER
        from evennia.utils.utils import delay
        
        # Prevent double death processing using PERSISTENT db flag (survives server reload)
        if self.db.death_processed:
            splattercast = get_splattercast()
            splattercast.msg(f"AT_DEATH_SKIP: {self.key} already processed death (db flag), skipping")
            return
            
        # Mark death as processed IMMEDIATELY using db (persistent) to prevent ANY race conditions
        self.db.death_processed = True
        
        # Also set NDB flag for backwards compatibility
        self.ndb.death_processed = True
        
        # Note: death_count is NOT incremented here - it will be incremented in the 
        # death_progression.py script at the definitive point of permanent death
        # (right before the character is moved to limbo). This ensures it only
        # increments exactly once, even if at_death() is called multiple times.
        
        # Clear any previous unconsciousness state since death supersedes it
        if getattr(self.ndb, 'unconsciousness_processed', False):
            self.ndb.unconsciousness_processed = False
        
        # Set death placement description for persistent visual indication
        self.override_place = "lying motionless and deceased."
        
        # Always show death analysis when character dies.
        # debug_death_analysis is fail-soft internally and the audit
        # router cannot raise (#464), so no wrapper is needed.
        splattercast = get_splattercast()
        splattercast.msg(self.debug_death_analysis())
        
        # Check if character is in active combat - if so, defer death curtain
        is_in_combat = hasattr(self.ndb, NDB_COMBAT_HANDLER) and getattr(self.ndb, NDB_COMBAT_HANDLER) is not None
        
        if is_in_combat:
            # Set flag for combat system to trigger death curtain after kill message
            self.ndb.death_curtain_pending = True
            splattercast = get_splattercast()
            splattercast.msg(f"AT_DEATH_COMBAT: {self.key} death curtain deferred - in active combat")
            
            # Safety fallback - trigger curtain after 5 seconds if combat doesn't handle it
            def fallback_death_curtain():
                if hasattr(self.ndb, 'death_curtain_pending') and self.ndb.death_curtain_pending:
                    splattercast = get_splattercast()
                    splattercast.msg(f"AT_DEATH_FALLBACK: {self.key} triggering fallback death curtain")
                    show_death_curtain(self)
                    self.ndb.death_curtain_pending = False
            
            delay(5, fallback_death_curtain)
        else:
            # Not in combat - show death curtain immediately
            # Death curtain will start death progression when it completes
            show_death_curtain(self)
        
        # Apply death command restrictions immediately
        self.apply_death_state()

    # MEDICAL REVIVAL SYSTEM - Command Set Management
    
    def apply_unconscious_state(self, force_test=False):
        """
        Apply unconscious command restrictions by replacing the default cmdset.
        
        Args:
            force_test (bool): If True, apply restrictions even for staff (for testing)
        """
        if not force_test and not self.is_unconscious():
            return
            
        # Check if character has builder/developer permissions
        if not force_test and self.locks.check(self, "perm(Builder)"):
            return  # Staff bypass cmdset restrictions
        
        # Remove current default cmdset and replace with unconscious cmdset
        try:
            self.cmdset.remove_default()
        except Exception:
            # Deliberate (#469): removing an absent default cmdset is a
            # legitimate no-op during state transitions.
            pass
            
        from commands.default_cmdsets import UnconsciousCmdSet
        self.cmdset.add_default(UnconsciousCmdSet)
        
        # Set placement description
        self.override_place = "unconscious and motionless."
        
        # Notify area
        if self.location:
            msg_room_identity(
                location=self.location,
                template="{actor} collapses on the ground in an unconscious heap.",
                char_refs={"actor": self},
                exclude=[self],
            )
        self.msg("You lose consciousness and slip into darkness...")

    def apply_death_state(self, force_test=False):
        """
        Apply death command restrictions by replacing the default cmdset.
        
        Args:
            force_test (bool): If True, apply restrictions even for staff (for testing)
        """
        if not force_test and not self.is_dead():
            return
            
        # Remove unconscious restrictions first if they exist
        self.remove_unconscious_state()
        
        # Check if character has builder/developer permissions
        if not force_test and self.locks.check(self, "perm(Builder)"):
            # Staff bypass cmdset restrictions unless force_test=True
            pass
        else:
            # Remove current default cmdset and replace with death cmdset
            try:
                self.cmdset.remove_default()
            except Exception:
                # Deliberate (#469): removing an absent default cmdset
                # is a legitimate no-op during state transitions.
                pass
                
            from commands.default_cmdsets import DeathCmdSet
            self.cmdset.add_default(DeathCmdSet)
        
        # Placement description already set in at_death()
        # TODO: Add death experience script for atmospheric immersion when implemented

    def remove_unconscious_state(self):
        """
        Remove unconscious command restrictions by restoring the normal default cmdset.
        """
        try:
            # Remove current default cmdset (should be unconscious cmdset)
            self.cmdset.remove_default()
        except Exception:
            # Deliberate (#469): removing an absent default cmdset is a
            # legitimate no-op during state transitions.
            pass
            
        # Restore normal character cmdset
        from commands.default_cmdsets import CharacterCmdSet
        self.cmdset.add_default(CharacterCmdSet)
        
        # Clear placement description - but only if it's unconscious-specific
        if (hasattr(self, 'override_place') and 
            self.override_place == "unconscious and motionless."):
            self.override_place = None
        
        # Notify recovery - but only if character is not dead
        if not self.is_dead():
            if self.location:
                msg_room_identity(
                    location=self.location,
                    template="{actor} regains consciousness.",
                    char_refs={"actor": self},
                    exclude=[self],
                )
            self.msg("You slowly regain consciousness...")

    def remove_death_state(self):
        """
        Remove death command restrictions and restore normal cmdset.
        """
        try:
            # Remove current default cmdset (should be death cmdset)
            self.cmdset.remove_default()
        except Exception:
            # Deliberate (#469): removing an absent default cmdset is a
            # legitimate no-op during state transitions.
            pass
            
        # Restore normal character cmdset
        from commands.default_cmdsets import CharacterCmdSet
        self.cmdset.add_default(CharacterCmdSet)
        
        # Clear placement description
        if hasattr(self, 'override_place'):
            self.override_place = None
        
        # Restart medical script if character has conditions and script is stopped
        if (hasattr(self, 'medical_state') and self.medical_state and 
            self.medical_state.conditions):
            try:
                splattercast = get_splattercast()
                
                # Find stopped medical script and restart it
                medical_scripts = self.scripts.get("medical_script")
                stopped_scripts = [s for s in medical_scripts if not s.is_active]
                
                if stopped_scripts:
                    stopped_scripts[0].start()
                    splattercast.msg(f"REVIVAL_RESTART: Restarted medical script for {self.key}")
                    
                    # Force immediate processing to overcome start_delay
                    from evennia.utils import delay
                    delay(0.1, stopped_scripts[0].at_repeat)
                    splattercast.msg(f"REVIVAL_IMMEDIATE: Forced immediate medical processing for {self.key}")
                else:
                    # Create new script if none exists
                    from world.medical.script import MedicalScript
                    from evennia import create_script
                    script = create_script(MedicalScript, obj=self, autostart=True)
                    splattercast.msg(f"REVIVAL_CREATE: Created new medical script for {self.key}")
                    
                    # Force immediate processing for new script too
                    from evennia.utils import delay
                    delay(0.1, script.at_repeat)
                    splattercast.msg(f"REVIVAL_IMMEDIATE_NEW: Forced immediate medical processing for new script for {self.key}")
            except Exception as e:
                splattercast.msg(f"REVIVAL_ERROR: Failed to restart medical script for {getattr(self, 'key', '?')}: {e}")
        
        # Clear death processing flags (both ndb and db)
        if hasattr(self.ndb, 'death_processed'):
            self.ndb.death_processed = False
        if self.db.death_processed is not None:
            del self.db.death_processed
        
        # Notify revival
        if self.location:
            msg_room_identity(
                location=self.location,
                template="|g{actor} has been revived!|n",
                char_refs={"actor": self},
                exclude=[self],
            )
        self.msg("|gYou have been revived! You feel the spark of life return.|n")

    def apply_final_death_state(self):
        """
        Apply final death state after death progression completes.
        This is permanent death until manual revival by admin.
        """
        
        # Update placement description for permanent death
        self.override_place = "lying motionless and deceased."
        
        # Ensure death cmdset is applied (should already be done)
        if not hasattr(self, '_death_cmdset_applied'):
            self.apply_death_state(force_test=True)
            self._death_cmdset_applied = True
        
        # Log final death
        splattercast = get_splattercast()
        splattercast.msg(f"FINAL_DEATH: {self.key} has entered permanent death state")

    def validate_attack_target(self):
        """
        Validate if this character can be attacked.
        
        Called by CmdAttack before combat initiation. Returns None for valid
        targets, or an error message string to prevent the attack.
        
        Returns:
            None if valid target, or str with error message if invalid
        """
        # Holographic merchants cannot be attacked
        if self.db.is_holographic:
            return "A holographic merchant cannot be attacked - target validation failed"
        
        # Character is a valid attack target
        return None

    # ===================================================================
    # IDENTITY & RECOGNITION SYSTEM
    # ===================================================================

    def get_distinguishing_feature(self):
        """Return the distinguishing feature clause for this character's sdesc.

        Priority chain (first non-empty wins):
          1. Wielded weapon or explosive
          2. Outermost clothing item.  Non-disguise items are preferred
             over items flagged ``is_disguise_item = True``; the
             disguise pool is consulted only when nothing else is worn
             (the naked-but-masked carve-out — a lone balaclava still
             reads as ``"in a black balaclava"`` rather than vanishing).
             When chosen, the item's ``worn_sdesc_short`` is used in
             preference to its ``key``.  Items flagged
             ``disguise_silent_feature = True`` are sub-visible
             (e.g. contact lenses) and never selected here, regardless
             of pool — they remain in the disguise / Apparent UID
             system but contribute nothing to the feature clause.
          3. Hair (colour/style) — suppressed when any worn item covers
             the ``"hair"`` body location (via the clothing coverage
             system); under coverage we fall through to "nothing"
             rather than describing hair the observer cannot see.
             Scope is feature-fallback only; longdesc gating lives
             with the existing clothing-coverage code.
          4. ``None`` — no feature

        Returns:
            Feature clause string (e.g. ``"wielding a Kitchen Knife"``,
            ``"in a Black Trenchcoat"``, ``"with blonde braids"``),
            or ``None`` if nothing qualifies.
        """
        from world.identity import (
            format_clothing_feature,
            format_hair_feature,
            format_wielded_feature,
        )

        # 1. Wielded weapon / explosive.  A deployed cyber weapon
        # dominates the sdesc with normal weapon weight (#516 review):
        # integrated weapons already sit in ``hands`` (held-is-
        # wielded); active natural weapons (claws) live off-grid, so
        # check them explicitly first.
        try:
            from world.medical.augments import get_active_natural_weapon
            natural = get_active_natural_weapon(self)
            if natural is not None:
                return format_wielded_feature(natural.key)
        except Exception:
            pass
        hands = self.hands or {}
        for _hand, item in hands.items():
            if item is not None:
                return format_wielded_feature(item.key)

        # 2. Outermost clothing item (pick the first location with coverage).
        # Partition disguise vs non-disguise so the clothing feature reads
        # the wearer's "real" outfit when there is one, and only falls
        # back to disguise items in the solo-disguise carve-out.  Items
        # flagged ``disguise_silent_feature`` (e.g. contacts) are
        # sub-visible — excluded from both pools so they never surface as
        # the feature clause, while remaining in the disguise / UID
        # system elsewhere.
        coverage_map = self._build_clothing_coverage_map()
        if coverage_map:
            non_disguise: dict = {}
            disguise: dict = {}
            for _location, item in coverage_map.items():
                if item is None:
                    continue
                if getattr(item, "disguise_silent_feature", False):
                    continue
                if getattr(item, "is_disguise_item", False):
                    disguise[_location] = item
                else:
                    non_disguise[_location] = item
            chosen_pool = non_disguise or disguise
            if chosen_pool:
                # Deterministic: pick the first location alphabetically.
                for _location in sorted(chosen_pool):
                    item = chosen_pool[_location]
                    label = (
                        getattr(item, "worn_sdesc_short", "") or item.key
                    )
                    return format_clothing_feature(label)

        # 3. Hair — suppressed when the "hair" body location is covered
        # by any worn item (see #176; replaces the legacy ``covers_hair``
        # boolean with the unified clothing-coverage vocabulary).
        if "hair" not in coverage_map:
            hair_color = self.hair_color
            hair_style = self.hair_style
            if hair_color or hair_style:
                return format_hair_feature(
                    color=hair_color, style=hair_style
                )

        # 4. Nothing
        return None

    def get_sdesc(self):
        """Return the composed short description for this character.

        Consumes the active presentation overrides
        (``db.height_override``, ``db.build_override``,
        ``db.keyword_override``) when set; otherwise falls back to the
        character's real ``height`` / ``build`` / ``sdesc_keyword``.
        This is the engine-PR consumption point that makes the
        ``appear`` command's overrides actually visible to observers.

        The sdesc has no leading article — callers prepend ``a``/``an``/
        ``the`` as needed via :func:`world.grammar.get_article`.

        If height/build are not yet set (pre-chargen character), falls
        back to ``self.key``.

        Returns:
            Sdesc string, e.g. ``"lanky man wielding a Kitchen Knife"``.
        """
        from world.identity import (
            compose_sdesc,
            get_disguise_adjective,
            get_physical_descriptor,
        )
        from world.grammar import DEFAULT_SDESC_KEYWORDS

        # Override axes take precedence over real values.
        height = self.db.height_override or self.height
        build = self.db.build_override or self.build
        if not height or not build:
            return self.key

        descriptor = get_physical_descriptor(height, build)
        keyword = self.db.keyword_override or self.sdesc_keyword
        if not keyword:
            keyword = DEFAULT_SDESC_KEYWORDS.get(self.gender, "person")

        feature = self.get_distinguishing_feature()
        adjective = get_disguise_adjective(self)
        return compose_sdesc(
            descriptor, keyword, feature, disguise_adjective=adjective
        )

    def get_display_name(self, looker=None, **kwargs):
        """Return the name of this character as seen by *looker*.

        Resolution order:
          1. ``looker is self`` → ``self.key`` (own real name)
          2. *looker* has an assigned name in ``recognition_memory``
             keyed on this character's current Apparent UID → that
             assigned name
          3. Otherwise → composed sdesc with indefinite article
             (e.g. ``"a lanky man in a Black Trenchcoat"``)

        The Apparent UID is derived from the target's full identity
        signature (real ``sleeve_uid`` + active overrides + essential
        items), so the same physical body produces different
        recognition entries under different disguises.

        If *looker* is ``None`` (system / log context), returns
        ``self.key``.

        Args:
            looker: The character observing this character, or ``None``.
            **kwargs: Passed through from Evennia's display-name pipeline.

        Returns:
            Display name string.
        """
        # No observer context — use real name
        if looker is None:
            return self.key

        # Self-perception — always own real name
        if looker is self:
            return self.key

        # Check if looker has a recognized name for this Apparent UID.
        from world.identity import get_apparent_uid, get_assigned_name

        assigned = get_assigned_name(looker, self)
        if assigned:
            return assigned

        apparent_uid = get_apparent_uid(self)
        # Disguise piercing: looker doesn't know this presentation, but
        # may have previously remembered the underlying sleeve under a
        # different presentation.  Opposed Intellect-vs-Resonance roll
        # (cached per presentation) decides whether they see through.
        from world.identity import attempt_display_pierce

        pierced_name = attempt_display_pierce(looker, self, apparent_uid)
        if pierced_name is not None:
            return pierced_name

        # Fall back to sdesc with indefinite article
        from world.grammar import with_article

        sdesc = self.get_sdesc()
        # If sdesc fell back to self.key, return it as-is (no article)
        if sdesc == self.key:
            return self.key
        return with_article(sdesc)

    def get_look_header(self, looker=None, **kwargs):
        """Return the appearance-header form of this character's name.

        Used by ``return_appearance`` to render the first line of a
        ``look <character>`` output.  Richer than
        :meth:`get_display_name` because it appends the composed sdesc
        in parentheses when there is a name to attach it to:

        - ``looker is None`` → ``self.key`` (no observer context).
        - ``looker is self`` → ``"{key} ({article} {sdesc})"`` so the
          player sees their own current sdesc when looking at
          themselves.
        - looker has an assigned name for our Apparent UID →
          ``"{assigned} ({article} {sdesc})"``.
        - Otherwise → identical to :meth:`get_display_name` (just the
          articled sdesc; strangers don't get a redundant parenthetical).

        The parenthetical is omitted whenever :meth:`get_sdesc` falls
        back to ``self.key`` (pre-chargen characters with no
        height/build) so we don't render ``Name (Name)``.

        Args:
            looker: The character observing this character, or ``None``.
            **kwargs: Reserved for future expansion / hook symmetry.

        Returns:
            Display header string for the appearance pipeline.
        """
        if looker is None:
            return self.key

        sdesc = self.get_sdesc()

        # Determine the leading name token.
        if looker is self:
            name = self.key
        else:
            from world.identity import get_apparent_uid

            name = None
            apparent_uid = get_apparent_uid(self)
            if apparent_uid is not None and hasattr(
                looker, "recognition_memory"
            ):
                memory = looker.recognition_memory
                if memory and apparent_uid in memory:
                    assigned = memory[apparent_uid].get("assigned_name")
                    if assigned:
                        name = assigned
            # Disguise piercing — if not yet recognised, see through?
            if name is None:
                from world.identity import attempt_display_pierce

                name = attempt_display_pierce(looker, self, apparent_uid)
            # Stranger: defer to the standard display name (article + sdesc)
            # without a parenthetical to avoid noisy duplication.
            if name is None:
                return self.get_display_name(looker, **kwargs)

        # If sdesc collapsed to self.key (pre-chargen), don't duplicate.
        if sdesc == self.key:
            return name

        from world.grammar import with_article

        return f"{name} ({with_article(sdesc)})"

    def announce_move_from(
        self, destination, msg=None, mapping=None, **kwargs
    ):
        """Broadcast our departure to the source room, per-observer.

        Overrides Evennia's default, which interpolates the mover's
        name in a way that effectively renders ``self.key`` for every
        observer regardless of their recognition memory.  Routes the
        broadcast through :func:`world.identity_utils.msg_room_identity`
        so each observer sees the mover rendered according to their
        own recognition memory (assigned name, sdesc, or distinguishing
        feature as appropriate).

        Honors caller-provided ``msg``/``mapping`` by delegating to
        ``super()`` — this preserves any future customization a caller
        might want to layer on top of the default announcement.

        See ``specs/IDENTITY_RECOGNITION_SPEC.md`` §"Phase 2 —
        Consistency" (Φ₅) for the broader sweep.

        Args:
            destination: Room the mover is heading to.
            msg: Optional caller-provided message template; when set,
                we delegate to ``super()`` to preserve customization.
            mapping: Optional caller-provided template mapping; when
                set, we delegate to ``super()`` for the same reason.
            **kwargs: Forwarded to ``super()`` on the delegation path
                (e.g. ``move_type``).
        """
        if msg is not None or mapping is not None:
            return super().announce_move_from(
                destination, msg=msg, mapping=mapping, **kwargs
            )
        if not self.location:
            return
        origin_name = (
            self.location.get_display_name(self)
            if self.location
            else "somewhere"
        )
        dest_name = (
            destination.get_display_name(self) if destination else "somewhere"
        )
        template = (
            f"{{actor}} is leaving {origin_name}, heading for {dest_name}."
        )
        msg_room_identity(
            self.location,
            template,
            {"actor": self},
            exclude=[self],
        )

    def announce_move_to(
        self, source_location, msg=None, mapping=None, **kwargs
    ):
        """Broadcast our arrival to the destination room, per-observer.

        Overrides Evennia's default for the same reason as
        :meth:`announce_move_from` — to ensure observers see the
        mover rendered according to their own recognition memory.

        See ``specs/IDENTITY_RECOGNITION_SPEC.md`` §"Phase 2 —
        Consistency" (Φ₅) for the broader sweep.

        Args:
            source_location: Room the mover came from (may be ``None``
                for fresh spawns / teleports without a prior location).
            msg: Optional caller-provided message template; when set,
                we delegate to ``super()`` to preserve customization.
            mapping: Optional caller-provided template mapping; when
                set, we delegate to ``super()`` for the same reason.
            **kwargs: Forwarded to ``super()`` on the delegation path
                (e.g. ``move_type``).
        """
        if msg is not None or mapping is not None:
            return super().announce_move_to(
                source_location, msg=msg, mapping=mapping, **kwargs
            )
        if not self.location:
            return
        origin_name = (
            source_location.get_display_name(self)
            if source_location
            else "somewhere"
        )
        dest_name = self.location.get_display_name(self)
        template = (
            f"{{actor}} arrives to {dest_name} from {origin_name}."
        )
        msg_room_identity(
            self.location,
            template,
            {"actor": self},
            exclude=[self],
        )

    def at_post_move(self, source_location, **kwargs):
        """Hook called after this character lands in a new location.

        Extends the default Evennia behavior with a passive recognition
        recency pass so that walking into a room with someone whose
        Apparent UID is already in our memory refreshes their
        ``last_seen`` (and friends).  See
        :func:`world.identity.bump_recognition_recency` for the
        per-target contract.

        Args:
            source_location: Location we just left (may be ``None``).
            **kwargs: Forwarded to the parent hook (e.g. ``move_type``).
        """
        super().at_post_move(source_location, **kwargs)
        self._refresh_recognition_recency()

    def _refresh_recognition_recency(self):
        """Bump recognition recency for every visible character we know.

        Iterates the current room's contents, computes each
        character's Apparent UID, and calls
        :func:`world.identity.bump_recognition_recency`.  The helper
        is a no-op for UIDs we have never explicitly remembered, so
        this method only mutates entries that already exist.

        Per-target failures are caught and logged — a single bad
        recognition entry must never break room entry.
        """
        if self.location is None:
            return
        memory = self.recognition_memory
        if not memory:
            return

        from evennia.utils import logger

        from world.identity import bump_recognition_recency, get_apparent_uid

        for obj in self.location.contents:
            if obj is self:
                continue
            if not isinstance(obj, Character):
                continue
            try:
                apparent_uid = get_apparent_uid(obj)
                if apparent_uid is None:
                    continue
                bump_recognition_recency(self, obj, apparent_uid)
            except (AttributeError, TypeError, ValueError):
                logger.log_trace(
                    f"Recognition recency bump failed for "
                    f"observer={self!r} target={obj!r}; continuing."
                )

    def search(
        self,
        searchdata,
        global_search=False,
        use_nicks=True,
        typeclass=None,
        location=None,
        attribute_name=None,
        quiet=False,
        exact=False,
        candidates=None,
        use_locks=True,
        nofound_string=None,
        multimatch_string=None,
        use_dbref=None,
        tags=None,
        stacked=0,
    ):
        """Identity-aware search override.

        Intercepts character targeting so players resolve targets via
        assigned names and short descriptions rather than real character
        keys.  Items, exits, and non-identity objects pass through to
        the standard Evennia search unmodified.

        **Bypass conditions** (uses default search only):
          - ``global_search`` is ``True``
          - Searcher has Builder+ permission
          - ``searchdata`` is a dbref (``#123``)
          - ``candidates`` or ``location`` is explicitly provided
          - ``attribute_name`` is set

        **Magic keywords** (always short-circuit, all permissions):
          - ``me`` / ``self`` → the caller
          - ``here`` → the caller's location

        **Identity pipeline** (local room search):
          1. Try identity matching (assigned names → sdescs) against
             room occupants.
          2. If identity matches are found, return them.
          3. Otherwise, run the default Evennia search for items/exits.
          4. Filter out any Characters from default results that were
             NOT identity-matched (blocks ``.key`` targeting of
             unrecognized characters).

        See :mod:`world.search` for the matching utilities and
        ``specs/IDENTITY_RECOGNITION_SPEC.md`` §Target Resolution for
        the full specification.
        """
        from world.combat.constants import PERM_BUILDER
        from world.search import identity_match_characters, is_identity_match

        # ----------------------------------------------------------
        # Magic keyword shortcut: ``me`` / ``self`` / ``here``
        # ----------------------------------------------------------
        # Evennia's DefaultObject.search resolves these tokens to the
        # caller / caller.location.  Our identity filter would then
        # strip the caller (because ``is_identity_match(self, self,
        # "me")`` is False) and return ``Could not find 'me'.`` for
        # any non-Builder.  Short-circuit before the identity pipeline
        # so these tokens always resolve, regardless of permissions.
        # See ``specs/IDENTITY_RECOGNITION_SPEC.md`` §Target Resolution.
        if isinstance(searchdata, str):
            stripped = searchdata.strip().lower()
            if stripped in ("me", "self"):
                return [self] if quiet else self
            if stripped == "here":
                loc = self.location
                if quiet:
                    return [loc] if loc else []
                return loc

        # ----------------------------------------------------------
        # Bypass: let Evennia handle non-local or privileged searches
        # ----------------------------------------------------------
        bypass = (
            global_search
            or attribute_name is not None
            or candidates is not None
            or location is not None
            or not isinstance(searchdata, str)
        )

        # Builder+ can also target by .key — tracked as a flag so the
        # identity pipeline still runs first (sdesc/assigned-name
        # matching works for Builders too), but the fallback filter
        # allows .key results through instead of blocking them.
        is_builder = (
            not bypass and self.check_permstring(PERM_BUILDER)
        )

        # Dbref query — full bypass
        if (
            not bypass
            and isinstance(searchdata, str)
            and searchdata.strip().startswith("#")
        ):
            bypass = True

        if bypass:
            return super().search(
                searchdata,
                global_search=global_search,
                use_nicks=use_nicks,
                typeclass=typeclass,
                location=location,
                attribute_name=attribute_name,
                quiet=quiet,
                exact=exact,
                candidates=candidates,
                use_locks=use_locks,
                nofound_string=nofound_string,
                multimatch_string=multimatch_string,
                use_dbref=use_dbref,
                tags=tags,
                stacked=stacked,
            )

        # ----------------------------------------------------------
        # Identity-aware local search
        # ----------------------------------------------------------
        query = searchdata.strip()
        if not query:
            return super().search(
                searchdata, global_search=global_search,
                use_nicks=use_nicks, typeclass=typeclass,
                location=location, attribute_name=attribute_name,
                quiet=quiet, exact=exact, candidates=candidates,
                use_locks=use_locks, nofound_string=nofound_string,
                multimatch_string=multimatch_string, use_dbref=use_dbref,
                tags=tags, stacked=stacked,
            )

        # Gather room occupants (identity candidates)
        room = self.location
        room_contents = room.contents if room else []

        identity_matches = identity_match_characters(
            self, query, room_contents
        )

        if identity_matches:
            if quiet:
                return identity_matches
            if len(identity_matches) == 1:
                return identity_matches[0]
            # Multiple matches — prompt for disambiguation
            names = [
                obj.get_display_name(self) for obj in identity_matches
            ]
            header = (
                multimatch_string
                or f"Multiple matches for '{query}':"
            )
            listing = "\n".join(
                f"  {i}. {name}" for i, name in enumerate(names, 1)
            )
            self.msg(f"{header}\n{listing}")
            return None

        # ----------------------------------------------------------
        # Fallback: standard Evennia search (items, exits, etc.)
        # ----------------------------------------------------------
        # Use quiet=True so we can filter before messaging
        default_results = super().search(
            searchdata,
            global_search=global_search,
            use_nicks=use_nicks,
            typeclass=typeclass,
            location=location,
            attribute_name=attribute_name,
            quiet=True,
            exact=exact,
            candidates=candidates,
            use_locks=use_locks,
            nofound_string=nofound_string,
            multimatch_string=multimatch_string,
            use_dbref=use_dbref,
            tags=tags,
            stacked=stacked,
        )

        # Filter out unrecognized Characters from default results.
        # Items, exits, rooms — anything without identity — passes
        # through unmodified.  Builders skip the identity filter so
        # they can also target by .key (their privilege).
        if is_builder:
            filtered = list(default_results)
        else:
            filtered = [
                obj for obj in default_results
                if is_identity_match(self, obj, query)
            ]

        # Return using the caller's original quiet mode
        if quiet:
            return filtered
        if len(filtered) == 1:
            return filtered[0]
        if not filtered:
            self.msg(
                nofound_string
                or f"Could not find '{query}'."
            )
            return None
        # Multiple results — show disambiguation
        names = [
            (
                obj.get_display_name(self)
                if hasattr(obj, "get_display_name")
                else obj.key
            )
            for obj in filtered
        ]
        header = (
            multimatch_string
            or f"Multiple matches for '{query}':"
        )
        listing = "\n".join(
            f"  {i}. {name}" for i, name in enumerate(names, 1)
        )
        self.msg(f"{header}\n{listing}")
        return None

    # ===================================================================
    # MR. HANDS SYSTEM (#307, PR-H2)
    # ===================================================================
    # ``held_items`` is the persistent backing store, keyed by the
    # canonical anatomical container name (e.g. ``"left_hand"``,
    # ``"right_hand"`` on humans; future tentacle / claw / prehensile-
    # tail variants extend the keyspace naturally).
    #
    # ``hands`` is a derived ``@property`` view: it walks the species'
    # ``grasping_containers`` set against the current severance state,
    # so a character who has lost their left arm sees ``hands`` as
    # ``{"right_hand": <item or None>}`` — the severed slot is gone,
    # not just empty.  This drives correct UX: ``wield baton in left``
    # on someone missing a left arm responds "you don't have a left
    # hand — it's been severed."
    #
    # Writes accept the derived shape AND the legacy
    # ``{"left": ..., "right": ...}`` shorthand for backward compat
    # with consumers that haven't migrated yet.
    held_items = AttributeProperty(
        {},
        category="equipment",
        autocreate=True,
    )

    @property
    def hands(self):
        """Derived view of grasping appendage slots.

        Returns a dict keyed by canonical container name (e.g.
        ``"left_hand"``) mapping to the held item or ``None``.
        The set of slots is computed each read from:

        * The species' ``grasping_containers`` declaration
        * Minus any container currently severed
        * Backing values from ``self.held_items``

        Reads are cheap (one species lookup + one severance scan)
        and intentionally not cached — severance state can change
        at any time, and over-caching here was the root cause of
        the pre-PR-H2 "wield in severed hand" bug.
        """
        # One-shot legacy migration: if old ``hands`` AttributeProperty
        # data exists, fold it into ``held_items`` with anatomical
        # keys.  Safe to call on every read — short-circuits after
        # the first run.
        self._migrate_legacy_hands_if_needed()

        from world.anatomy import get_species_grasping_containers

        species = getattr(self.db, "species", None)
        grasping = set(get_species_grasping_containers(species))

        # Per-character grasping overlay (ANATOMY_AUGMENTS_SPEC §3.4):
        # an installed organ flagged ``grasping`` adds its container
        # as a held-item slot — the prehensile cybernetic tail is a
        # third hand.  The severance subtraction below already covers
        # "the severed tail drops what it held".
        try:
            medical_state = self.medical_state
        except AttributeError:
            medical_state = None
        if medical_state is not None:
            for organ in getattr(medical_state, "organs", {}).values():
                organ_data = getattr(organ, "data", None)
                if organ_data and organ_data.get("grasping"):
                    container = getattr(organ, "container", None)
                    if container:
                        grasping.add(container)

        severed = (
            self._get_severed_locations()
            if hasattr(self, "_get_severed_locations") else set()
        )

        # Functional-anatomy gate (#526 review): a grasping slot
        # needs LIVING organs at its container.  The severed-set
        # subtraction alone misses chain severances — the cut-point
        # wound filter suppresses downstream wounds, so a hand
        # attached to a severed arm never appeared "severed" and
        # kept holding items.  Organ truth closes it: all organs at
        # the container tombstoned (severed, harvested, or pulped
        # in place) = no grip.  Characters without organ data at a
        # location keep the legacy severed-set behavior.
        if medical_state is not None:
            organs = getattr(medical_state, "organs", {}) or {}
            for location in list(grasping):
                at_location = [
                    o for o in organs.values()
                    if getattr(o, "container", None) == location
                ]
                if at_location and not any(
                        getattr(o, "current_hp", 1) > 0
                        for o in at_location):
                    severed = set(severed) | {location}

        held = self.held_items or {}
        return {
            location: held.get(location)
            for location in grasping
            if location not in severed
        }

    @hands.setter
    def hands(self, value):
        """Compat setter: route writes through to ``held_items``.

        Existing consumers do ``character.hands = updated_dict``;
        this setter accepts that and writes through to the new
        backing store.  Keys may be either canonical
        (``"left_hand"``) or legacy shorthand (``"left"``); both
        resolve to the canonical anatomical container name.

        Keys that don't correspond to any species container pass
        through unchanged — defensive in case future systems use
        the dict for ad-hoc storage.
        """
        if not isinstance(value, dict):
            return
        held = dict(self.held_items or {})
        for key, item in value.items():
            held[_canonical_hand(key)] = item
        self.held_items = held

    def _migrate_legacy_hands_if_needed(self):
        """Move legacy ``{"left": ..., "right": ...}`` data from the
        old ``hands`` AttributeProperty into ``held_items`` with
        canonical anatomical keys.

        Pre-PR-H2 characters have a persisted ``hands`` attribute
        in the ``equipment`` category.  Once migrated, the legacy
        attribute is removed so subsequent reads short-circuit.

        No-op if the legacy attribute is absent or non-dict.  Only
        carries forward slots that aren't already populated in
        ``held_items`` (avoids clobbering newer writes during the
        transition window).
        """
        legacy = self.attributes.get("hands", category="equipment")
        if not isinstance(legacy, dict):
            return

        held = dict(self.held_items or {})
        for legacy_key, item in legacy.items():
            canonical = _canonical_hand(legacy_key)
            if canonical not in held:
                held[canonical] = item
        self.held_items = held
        self.attributes.remove("hands", category="equipment")

    # ===================================================================
    # LONGDESC SYSTEM
    # ===================================================================
    # Detailed body part descriptions: anatomy source of truth
    longdesc = AttributeProperty(
        None,  # Will be set to copy of DEFAULT_LONGDESC_LOCATIONS in at_object_creation
        category="appearance",
        autocreate=True
    )
    
    # ===================================================================
    # CLOTHING SYSTEM
    # ===================================================================
    # Storage for worn clothing items organized by body location
    # NOTE: Clothing methods are in ClothingMixin.
    worn_items = AttributeProperty({}, category="clothing", autocreate=True)
    # Structure: {
    #     "chest": [jacket_obj, shirt_obj],  # Ordered by layer (outer first)
    #     "head": [hat_obj],
    #     "left_hand": [glove_obj],
    #     "right_hand": [glove_obj]
    # }

    def wield_item(self, item, hand="right"):
        """Wield ``item`` in ``hand``.

        ``hand`` may be either the canonical anatomical key
        (``"left_hand"``) or a user-facing shorthand
        (``"left"`` / ``"l"``).  Severed slots return a specific
        rejection so the player knows the limb is missing rather
        than just empty.
        """
        canonical = _canonical_hand(hand)
        display = _humanize_hand(canonical)
        current = self.hands  # triggers migration + severance scan

        if canonical not in current:
            # Either the species doesn't have this slot, or it's
            # severed.  Distinguish the two for legibility.
            from world.anatomy import get_species_grasping_containers
            species = getattr(self.db, "species", None)
            grasping = get_species_grasping_containers(species)
            if canonical in grasping:
                # Slot exists on species but is missing in current
                # view → severed.
                return f"You don't have a {display} — it's been severed."
            return f"You don't have a {display}."

        if current[canonical] is not None:
            return f"You're already holding something in your {display}."

        # Check if item is already in another hand
        for other_canonical, held in current.items():
            if held == item:
                other_display = _humanize_hand(other_canonical)
                return (
                    f"You're already wielding "
                    f"{item.get_display_name(self)} in your "
                    f"{other_display}."
                )

        if item.location != self:
            return "You're not carrying that item."

        # Integrated cyberware (#516) never takes the wield path —
        # it deploys into its own slot via /<ability>.  Without this
        # gate a freed integrated weapon could be wielded into the
        # WRONG hand, desyncing the toggle state.
        if item.db.integrated:
            return (
                f"{item.get_display_name(self)} is part of your body — "
                f"it deploys and retracts, it doesn't wield."
            )

        # Check if item is currently worn
        if hasattr(self, 'is_item_worn') and self.is_item_worn(item):
            return "You can't wield something you're wearing. Remove it first."

        held = dict(self.held_items or {})
        held[canonical] = item
        # Keep item.location = self (wielded items stay in inventory
        # location-wise) — they're just tracked separately in held_items.
        self.held_items = held
        return f"You wield {item.get_display_name(self)} in your {display}."

    def unwield_item(self, hand="right"):
        canonical = _canonical_hand(hand)
        display = _humanize_hand(canonical)
        current = self.hands

        if canonical not in current:
            from world.anatomy import get_species_grasping_containers
            species = getattr(self.db, "species", None)
            grasping = get_species_grasping_containers(species)
            if canonical in grasping:
                return f"You don't have a {display} — it's been severed."
            return f"You don't have a {display}."

        item = current[canonical]
        if not item:
            return f"You're not holding anything in your {display}."

        # Integrated cyberware (#516): the deployed arm-gun is not
        # held, it IS the hand.  unwield and freehands both route
        # through here — refusing here closes both paths.
        if item.db.integrated:
            return (
                f"{item.get_display_name(self)} is part of your "
                f"{display} — retract it instead."
            )

        item.move_to(self, quiet=True)
        held = dict(self.held_items or {})
        held[canonical] = None
        self.held_items = held
        return f"You unwield {item.get_display_name(self)} from your {display}."

    def list_held_items(self):
        current = self.hands
        lines = []
        for canonical, item in current.items():
            display = _humanize_hand(canonical).title()
            if item:
                lines.append(f"{display}: {item.get_display_name(self)}")
            else:
                lines.append(f"{display}: (empty)")
        return lines

    # ===================================================================
    # AIM STATE MANAGEMENT
    # ===================================================================

    def clear_aim_state(self, reason_for_clearing=""):
        """
        Clears any current aiming state (character or direction) for this character.
        Provides feedback to the character and any previously aimed-at target.

        Args:
            reason_for_clearing (str, optional): A short phrase describing why aim is cleared,
                                                 e.g., "as you move", "as you stop aiming".
        Returns:
            bool: True if an aim state was actually cleared, False otherwise.
        """
        splattercast = get_splattercast()
        stopped_aiming_message_parts = []
        log_message_parts = []
        action_taken = False

        # Clear character-specific aim
        old_aim_target_char = getattr(self.ndb, NDB_AIMING_AT, None)
        if old_aim_target_char:
            action_taken = True
            del self.ndb.aiming_at
            log_message_parts.append(f"stopped aiming at {old_aim_target_char.key}")
            
            if hasattr(old_aim_target_char, "ndb") and getattr(old_aim_target_char.ndb, NDB_AIMED_AT_BY, None) == self:
                del old_aim_target_char.ndb.aimed_at_by
                old_aim_target_char.msg(f"{self.get_display_name(old_aim_target_char)} is no longer aiming directly at you.")
            
            # Clear override_place and handle mutual showdown cleanup
            self._clear_aim_override_place_on_aim_clear(old_aim_target_char)
            
            stopped_aiming_message_parts.append(f"at {old_aim_target_char.get_display_name(self)}")

        # Clear directional aim
        old_aim_direction = getattr(self.ndb, NDB_AIMING_DIRECTION, None)
        if old_aim_direction:
            action_taken = True
            del self.ndb.aiming_direction
            log_message_parts.append(f"stopped aiming {old_aim_direction}")
            
            # Clear directional aim override_place
            self.override_place = ""
            
            stopped_aiming_message_parts.append(f"{old_aim_direction}")

        if action_taken:
            # Construct details of what was being aimed at for the player message
            aim_details_for_msg = ""
            if stopped_aiming_message_parts:
                # stopped_aiming_message_parts contains things like "at {target_name}" or "{direction}"
                # Example: " at YourTarget", " east", or " at YourTarget, east"
                aim_details_for_msg = f" {', '.join(stopped_aiming_message_parts)}"

            # Base player message
            player_msg_text = f"You stop aiming{aim_details_for_msg}"

            # Append the reason, but only if it's not the default "as you stop aiming"
            # (which is implicit when the player uses the 'stop aiming' command)
            if reason_for_clearing and reason_for_clearing != "as you stop aiming":
                player_msg_text += f" {reason_for_clearing.strip()}"
            
            player_msg_text += "." # Add a period at the end.
            self.msg(player_msg_text)

            # Construct log message (this part's logic for suffix remains the same)
            log_reason_suffix = ""
            if reason_for_clearing:
                log_reason_suffix = f" ({reason_for_clearing.strip()})" # Log always includes the reason clearly
            splattercast.msg(f"AIM_CLEAR: {self.key} {', '.join(log_message_parts)}{log_reason_suffix}.")
        
        return action_taken

    def _clear_aim_override_place_on_aim_clear(self, target):
        """
        Clear override_place for aiming when clearing aim state, handling mutual showdown cleanup.
        
        Args:
            target: The character that was being aimed at
        """
        # Check if they were in a mutual showdown
        if (hasattr(self, 'override_place') and hasattr(target, 'override_place') and
            self.override_place == "locked in a deadly showdown." and 
            target.override_place == "locked in a deadly showdown."):
            # They were in a showdown - clear aimer's place, check if target should revert to normal aiming
            self.override_place = ""
            
            # If target is still aiming at aimer, revert them to normal aiming
            target_still_aiming = getattr(target.ndb, NDB_AIMING_AT, None)
            if target_still_aiming == self:
                target.override_place = "aiming carefully at {aim_target}."
            else:
                # Target isn't aiming at anyone, clear their place too
                target.override_place = ""
