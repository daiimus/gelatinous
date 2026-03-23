"""
Characters

Characters are (by default) Objects setup to be puppeted by Accounts.
They are what you "see" in game. The Character class in this module
is setup to be the "default" character type created by the default
creation commands.

"""

from evennia.objects.objects import DefaultCharacter
from evennia.typeclasses.attributes import AttributeProperty
from evennia.comms.models import ChannelDB  # Ensure this is imported

from world.combat.constants import NDB_AIMED_AT_BY, NDB_AIMING_AT, NDB_AIMING_DIRECTION, NDB_COMBAT_HANDLER
from world.identity_utils import msg_room_identity

from .objects import ObjectParent
from .armor_mixin import ArmorMixin
from .clothing_mixin import ClothingMixin
from .appearance_mixin import AppearanceMixin


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

    # Shop System Attributes
    is_merchant = AttributeProperty(False, category="shop", autocreate=True)
    is_holographic = AttributeProperty(False, category="shop", autocreate=True)
    tokens = AttributeProperty(0, category="shop", autocreate=True)
    
    # Death tracking system
    death_count = AttributeProperty(0, category='mortality', autocreate=True)
    
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

        # Initialize longdesc system with default anatomy
        from world.combat.constants import DEFAULT_LONGDESC_LOCATIONS
        if not self.longdesc:
            self.longdesc = DEFAULT_LONGDESC_LOCATIONS.copy()

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
        from evennia.comms.models import ChannelDB
        from world.combat.constants import SPLATTERCAST_CHANNEL, NDB_COMBAT_HANDLER
        from evennia.utils.utils import delay
        
        # Prevent double unconsciousness processing
        if hasattr(self, 'ndb') and getattr(self.ndb, 'unconsciousness_processed', False):
            try:
                splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
                splattercast.msg(f"UNCONSCIOUS_SKIP: {self.key} already processed unconsciousness, skipping")
            except Exception:
                pass
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
            try:
                splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
                splattercast.msg(f"UNCONSCIOUS_COMBAT: {self.key} unconsciousness message deferred - in active combat")
            except Exception:
                pass
            
            # Safety fallback - trigger message after 5 seconds if combat doesn't handle it
            def fallback_unconsciousness_message():
                if hasattr(self.ndb, 'unconsciousness_pending') and self.ndb.unconsciousness_pending:
                    try:
                        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
                        splattercast.msg(f"UNCONSCIOUS_FALLBACK: {self.key} triggering fallback unconsciousness message")
                    except Exception:
                        pass
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
                # Optional: Debug broadcast for tracking
                try:
                    from world.combat.utils import debug_broadcast
                    debug_broadcast(f"{self.key} removed from combat due to unconsciousness", "MEDICAL", "UNCONSCIOUS")
                except ImportError:
                    pass  # debug_broadcast not available
            except Exception as e:
                # Optional: Debug broadcast for tracking errors
                try:
                    from world.combat.utils import debug_broadcast
                    debug_broadcast(f"Error removing {self.key} from combat on unconsciousness: {e}", "MEDICAL", "ERROR")
                except ImportError:
                    pass  # debug_broadcast not available
        
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
            try:
                from world.combat.constants import SPLATTERCAST_CHANNEL
                splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
                splattercast.msg(f"WARNING: Archiving staff character {self.key} (Account: {self.account.key}, Reason: {reason})")
            except Exception:
                pass
        
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
            try:
                from world.combat.constants import SPLATTERCAST_CHANNEL
                splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
                splattercast.msg(f"ARCHIVE: Moved {self.key} from {current_location.key if current_location else 'None'} to Limbo")
            except Exception:
                pass
        
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
        from evennia.comms.models import ChannelDB
        from world.combat.constants import SPLATTERCAST_CHANNEL, NDB_COMBAT_HANDLER
        from evennia.utils.utils import delay
        
        # Prevent double death processing using PERSISTENT db flag (survives server reload)
        if self.db.death_processed:
            try:
                splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
                splattercast.msg(f"AT_DEATH_SKIP: {self.key} already processed death (db flag), skipping")
            except Exception:
                pass
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
        
        # Always show death analysis when character dies
        try:
            splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
            death_analysis = self.debug_death_analysis()
            splattercast.msg(death_analysis)
        except Exception as e:
            # Fallback if splattercast channel not available
            pass
        
        # Check if character is in active combat - if so, defer death curtain
        is_in_combat = hasattr(self.ndb, NDB_COMBAT_HANDLER) and getattr(self.ndb, NDB_COMBAT_HANDLER) is not None
        
        if is_in_combat:
            # Set flag for combat system to trigger death curtain after kill message
            self.ndb.death_curtain_pending = True
            try:
                splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
                splattercast.msg(f"AT_DEATH_COMBAT: {self.key} death curtain deferred - in active combat")
            except Exception:
                pass
            
            # Safety fallback - trigger curtain after 5 seconds if combat doesn't handle it
            def fallback_death_curtain():
                if hasattr(self.ndb, 'death_curtain_pending') and self.ndb.death_curtain_pending:
                    try:
                        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
                        splattercast.msg(f"AT_DEATH_FALLBACK: {self.key} triggering fallback death curtain")
                    except Exception:
                        pass
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
            pass  # No default cmdset to remove, that's fine
            
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
                pass  # No default cmdset to remove, that's fine
                
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
            pass  # No default cmdset to remove, that's fine
            
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
            pass  # No default cmdset to remove, that's fine
            
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
                from evennia.comms.models import ChannelDB
                from world.combat.constants import SPLATTERCAST_CHANNEL
                splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
                
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
                try:
                    splattercast.msg(f"REVIVAL_ERROR: Failed to restart medical script for {self.key}: {e}")
                except Exception:
                    pass
        
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
        from evennia.comms.models import ChannelDB
        from world.combat.constants import SPLATTERCAST_CHANNEL
        
        # Update placement description for permanent death
        self.override_place = "lying motionless and deceased."
        
        # Ensure death cmdset is applied (should already be done)
        if not hasattr(self, '_death_cmdset_applied'):
            self.apply_death_state(force_test=True)
            self._death_cmdset_applied = True
        
        # Log final death
        try:
            splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
            splattercast.msg(f"FINAL_DEATH: {self.key} has entered permanent death state")
        except Exception:
            pass

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
          2. Outermost clothing item
          3. Hair (colour/style)
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

        # 1. Wielded weapon / explosive
        hands = self.hands or {}
        for _hand, item in hands.items():
            if item is not None:
                return format_wielded_feature(item.key)

        # 2. Outermost clothing item (pick the first location with coverage)
        coverage_map = self._build_clothing_coverage_map()
        if coverage_map:
            # Deterministic: pick the first location alphabetically so the
            # feature is stable between calls.
            for _location in sorted(coverage_map):
                item = coverage_map[_location]
                if item is not None:
                    return format_clothing_feature(item.key)

        # 3. Hair
        hair_color = self.hair_color
        hair_style = self.hair_style
        if hair_color or hair_style:
            return format_hair_feature(color=hair_color, style=hair_style)

        # 4. Nothing
        return None

    def get_sdesc(self):
        """Return the composed short description for this character.

        The sdesc has no leading article — callers prepend ``a``/``an``/
        ``the`` as needed via :func:`world.grammar.get_article`.

        If height/build/keyword are not yet set (pre-chargen character),
        falls back to ``self.key``.

        Returns:
            Sdesc string, e.g. ``"lanky man wielding a Kitchen Knife"``.
        """
        from world.identity import compose_sdesc, get_physical_descriptor
        from world.grammar import DEFAULT_SDESC_KEYWORDS

        height = self.height
        build = self.build
        if not height or not build:
            return self.key

        descriptor = get_physical_descriptor(height, build)
        keyword = self.sdesc_keyword
        if not keyword:
            keyword = DEFAULT_SDESC_KEYWORDS.get(self.gender, "person")

        feature = self.get_distinguishing_feature()
        return compose_sdesc(descriptor, keyword, feature)

    def get_display_name(self, looker=None, **kwargs):
        """Return the name of this character as seen by *looker*.

        Resolution order:
          1. ``looker is self`` → ``self.key`` (own real name)
          2. *looker* has an assigned name in ``recognition_memory``
             for this character's ``sleeve_uid`` → that assigned name
          3. Otherwise → composed sdesc with indefinite article
             (e.g. ``"a lanky man in a Black Trenchcoat"``)

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

        # Check if looker has a recognized name for this sleeve
        sleeve_uid = self.sleeve_uid
        if sleeve_uid is not None and hasattr(looker, "recognition_memory"):
            memory = looker.recognition_memory
            if memory and sleeve_uid in memory:
                entry = memory[sleeve_uid]
                assigned = entry.get("assigned_name")
                if assigned:
                    return assigned

        # Fall back to sdesc with indefinite article
        from world.grammar import get_article

        sdesc = self.get_sdesc()
        # If sdesc fell back to self.key, return it as-is (no article)
        if sdesc == self.key:
            return self.key
        article = get_article(sdesc)
        return f"{article} {sdesc}"

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
    # MR. HANDS SYSTEM
    # ===================================================================
    # Persistent hand slots: supports dynamic anatomy eventually
    hands = AttributeProperty(
        {"left": None, "right": None},
        category="equipment",
        autocreate=True
    )

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
        hands = self.hands
        if hand not in hands:
            return f"You don't have a {hand} hand."

        if hands[hand]:
            return f"You're already holding something in your {hand}."
        
        # Check if item is already in another hand
        for other_hand, held_item in hands.items():
            if held_item == item:
                if other_hand == hand:
                    return f"You're already wielding {item.get_display_name(self)} in your {hand} hand."
                else:
                    return f"You're already wielding {item.get_display_name(self)} in your {other_hand} hand."

        if item.location != self:
            return "You're not carrying that item."
        
        # Check if item is currently worn
        if hasattr(self, 'is_item_worn') and self.is_item_worn(item):
            return "You can't wield something you're wearing. Remove it first."

        hands[hand] = item
        # Keep item.location = self (wielded items stay in inventory location-wise)
        # They're just tracked separately in the hands dict
        self.hands = hands  # Save updated hands dict
        return f"You wield {item.get_display_name(self)} in your {hand} hand."
    
    def unwield_item(self, hand="right"):
        hands = self.hands
        item = hands.get(hand, None)

        if not item:
            return f"You're not holding anything in your {hand} hand."

        item.move_to(self, quiet=True)
        hands[hand] = None
        self.hands = hands
        return f"You unwield {item.get_display_name(self)} from your {hand} hand."
    
    def list_held_items(self):
        hands = self.hands
        lines = []
        for hand, item in hands.items():
            if item:
                lines.append(f"{hand.title()} Hand: {item.get_display_name(self)}")
            else:
                lines.append(f"{hand.title()} Hand: (empty)")
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
        from world.combat.constants import SPLATTERCAST_CHANNEL
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
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
