"""
Medical condition script for characters.

This script manages all medical conditions for a single character,
ticking them at regular intervals and cleaning up when no conditions remain.
"""

from evennia import DefaultScript
from evennia.comms.models import ChannelDB
from world.combat.constants import SPLATTERCAST_CHANNEL


class MedicalScript(DefaultScript):
    """
    Per-character script that manages all medical conditions.
    
    This script:
    - Runs every 60 seconds to process medical conditions
    - Automatically starts when first condition is added
    - Automatically stops when no conditions remain
    - Provides centralized medical condition management
    """
    
    def at_script_creation(self):
        """Called when script is first created."""
        self.key = "medical_script"  # Use consistent key for searching
        self.desc = f"Medical condition manager for {self.obj.key}"
        self.interval = 12  # Tick every 12 seconds (was 60 for production)
        self.persistent = True
        self.start_delay = True  # Wait before first regular execution
        
        # Schedule first medical message with a delay longer than max combat delay
        from evennia.utils import delay
        delay(5, self._initial_medical_check)  # 5s delay ensures combat messages appear first
        
    def _initial_medical_check(self):
        """Perform initial medical check after creation delay."""
        # This replaces the first at_repeat call with proper timing
        self.at_repeat()
        # Note: start_delay is managed by Evennia, not modifiable at runtime
        
    def at_repeat(self):
        """Process all medical conditions for this character."""
        try:
            # Get splattercast for debugging
            splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
            
            # Get character's medical state
            if not hasattr(self.obj, 'medical_state'):
                splattercast.msg(f"MEDICAL_SCRIPT: {self.obj.key} has no medical_state, stopping script")
                self.stop()
                return
                
            medical_state = self.obj.medical_state
            conditions = medical_state.conditions.copy()  # Copy to avoid modification during iteration
            
            if not conditions:
                splattercast.msg(f"MEDICAL_SCRIPT: {self.obj.key} has no conditions, stopping and deleting script")
                self.stop()
                self.delete()
                return
                
            splattercast.msg(f"MEDICAL_SCRIPT: Processing {len(conditions)} conditions for {self.obj.key}")
            
            # Process each condition
            conditions_to_remove = []
            total_bleeding_severity = 0
            total_pain_severity = 0
            total_infection_severity = 0
            
            for condition in conditions:
                try:
                    if hasattr(condition, 'requires_ticker') and condition.requires_ticker:
                        splattercast.msg(f"MEDICAL_SCRIPT: Ticking {condition.condition_type} severity {condition.severity}")
                        condition.tick_effect(self.obj)
                        
                        # Track bleeding severity for consolidated messaging
                        if condition.condition_type == "minor_bleeding":
                            total_bleeding_severity += condition.severity
                        
                        # Track pain severity for consolidated messaging
                        if condition.condition_type == "pain":
                            total_pain_severity += condition.severity
                            
                        # Track infection severity for consolidated messaging
                        if condition.condition_type == "infection":
                            total_infection_severity += condition.severity
                        
                        # Check if condition should be removed (e.g., severity reached 0)
                        if hasattr(condition, 'should_end') and condition.should_end():
                            conditions_to_remove.append(condition)
                            splattercast.msg(f"MEDICAL_SCRIPT: {condition.condition_type} marked for removal")
                            
                except Exception as e:
                    splattercast.msg(f"MEDICAL_SCRIPT_ERROR: Error processing {condition.condition_type}: {e}")
                    conditions_to_remove.append(condition)
            
            # Send consolidated messaging if conditions are active
            if total_bleeding_severity > 0 or total_pain_severity > 0 or total_infection_severity > 0:
                self._send_medical_messages(total_bleeding_severity, total_pain_severity, total_infection_severity)
            
            if total_bleeding_severity > 0:
                self._create_blood_pool(total_bleeding_severity)
            
            # Remove ended conditions
            for condition in conditions_to_remove:
                medical_state.conditions.remove(condition)
                splattercast.msg(f"MEDICAL_SCRIPT: Removed {condition.condition_type}")
            
            # Update vital signs after processing all conditions
            # This ensures consciousness includes all penalties (pain, blood loss, suppression)
            medical_state.update_vital_signs()
            
            # Check for death/unconsciousness after processing conditions
            if medical_state.is_dead():
                splattercast.msg(f"MEDICAL_SCRIPT_DEATH: {self.obj.key} has died from medical conditions")
                
                # Check if death has already been processed to prevent double death curtains
                if hasattr(self.obj, 'ndb') and getattr(self.obj.ndb, 'death_processed', False):
                    splattercast.msg(f"MEDICAL_SCRIPT_DEATH_SKIP: {self.obj.key} death already processed")
                else:
                    # Trigger full death processing (includes death analysis and death curtain)
                    self.obj.at_death()
                    
                # Stop script but preserve it for potential revival
                self.stop()
                splattercast.msg(f"MEDICAL_SCRIPT_PAUSED: {self.obj.key} medical script stopped but preserved for revival")
                return
            elif medical_state.is_unconscious():
                splattercast.msg(f"MEDICAL_SCRIPT_UNCONSCIOUS: {self.obj.key} has become unconscious")
                
                # Check if unconsciousness has already been processed to prevent double messages
                if hasattr(self.obj, 'ndb') and getattr(self.obj.ndb, 'unconsciousness_processed', False):
                    splattercast.msg(f"MEDICAL_SCRIPT_UNCONSCIOUS_SKIP: {self.obj.key} unconsciousness already processed")
                else:
                    # Use character's own unconsciousness handling method
                    self.obj._handle_unconsciousness()
            else:
                # Character is conscious - clear unconsciousness flag if it was set
                # BUT only if they're not dead (prevent "regains consciousness" when dying)
                if (hasattr(self.obj, 'ndb') and getattr(self.obj.ndb, 'unconsciousness_processed', False) 
                    and not medical_state.is_dead()):
                    splattercast.msg(f"MEDICAL_SCRIPT_RECOVERY: {self.obj.key} has regained consciousness")
                    self.obj.ndb.unconsciousness_processed = False
                    # Clear unconsciousness placement description when regaining consciousness
                    # But ONLY clear unconscious description, not death description
                    if (hasattr(self.obj, 'override_place') and 
                        self.obj.override_place == "unconscious and motionless."):
                        splattercast.msg(f"MEDICAL_SCRIPT_CLEAR_UNCONSCIOUS: Clearing unconscious override_place for {self.obj.key}")
                        self.obj.override_place = None
            
            # Check if we should stop (no conditions left)
            if not medical_state.conditions:
                splattercast.msg(f"MEDICAL_SCRIPT: All conditions processed, stopping and deleting script for {self.obj.key}")
                self.stop()
                self.delete()
                
        except Exception as e:
            try:
                splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
                splattercast.msg(f"MEDICAL_SCRIPT_CRITICAL_ERROR: {self.obj.key}: {e}")
            except Exception:
                pass
            self.stop()
            self.delete()
    
    def at_stop(self):
        """Called when script stops."""
        try:
            splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
            splattercast.msg(f"MEDICAL_SCRIPT_STOP: Medical script stopped for {self.obj.key}")
        except Exception:
            pass
    
    def _send_medical_messages(self, bleeding_severity, pain_severity, infection_severity=0):
        """Send consolidated medical messages combining bleeding, pain, and infection."""
        import random
        
        # Check if character is dead - don't send personal messages to preserve death curtain
        medical_state = getattr(self.obj, 'medical_state', None)
        is_dead = medical_state and medical_state.is_dead()
        
        # Build message components
        personal_parts = []
        room_parts = []
        
        # Add bleeding components if present
        if bleeding_severity > 0:
            if is_dead:
                # Suppress all bleeding messages for dead characters
                # Death curtain will handle death-related messaging
                pass
            else:
                # Normal living character bleeding messages
                if bleeding_severity <= 3:
                    personal_parts.append("|rYou feel warm blood trickling from your wounds.|n")
                    room_parts.append("Small droplets of blood fall from {actor}'s wounds.")
                elif bleeding_severity <= 7:
                    personal_parts.append("|rBlood flows freely from your wounds, leaving crimson trails.|n")
                    room_parts.append("Blood steadily drips from {actor}, forming dark stains.")
                elif bleeding_severity <= 12:
                    personal_parts.append("|rYou feel your life ebbing away as blood pours from your wounds.|n")
                    room_parts.append("Crimson flows freely from {actor}'s wounds, pooling on the ground.")
                else:  # 13+
                    personal_parts.append("|rYour vision dims as life-blood gushes from grievous wounds.|n")
                    room_parts.append("{actor} leaves a trail of blood, their wounds gushing freely.")
        
        # Add pain components if present (only for living characters)
        if pain_severity > 0 and not is_dead:
            if pain_severity <= 5:
                personal_parts.append("|rYou feel a persistent ache from your injuries.|n")
            elif pain_severity <= 12:
                personal_parts.append("|rSharp pain flares from your wounds.|n")
            elif pain_severity <= 20:
                personal_parts.append("|rAgony courses through your battered form.|n")
            else:  # 21+
                personal_parts.append("|rUnbearable agony threatens to drive you unconscious.|n")
        
        # Add infection components if present (only for living characters)
        if infection_severity > 0 and not is_dead:
            if infection_severity <= 3:
                personal_parts.append("|rYou feel a mild warmth and tenderness at your injured areas.|n")
            elif infection_severity <= 5:
                personal_parts.append("|rYour wounds throb with inflamed heat.|n")
            elif infection_severity <= 7:
                personal_parts.append("|rYour wounds feel hot and inflamed, infection spreading.|n")
            else:  # 8+
                personal_parts.append("|rFever burns through you as infection spreads through your body.|n")
        
        # Combine and send messages
        if personal_parts and not is_dead:
            # Only send personal messages to living characters to preserve death curtain
            personal_msg = " ".join(personal_parts)
            self.obj.msg(personal_msg)
        
        if room_parts:
            # Join room messages and send via identity-aware system
            room_template = f"|r{' '.join(room_parts)}|n"
            if self.obj.location:
                from world.identity_utils import msg_room_identity
                msg_room_identity(
                    location=self.obj.location,
                    template=room_template,
                    char_refs={"actor": self.obj},
                    exclude=[self.obj],
                )
    
    def _create_blood_pool(self, severity):
        """Create or update blood pool object in the room (like graffiti system)."""
        if not self.obj.location:
            return
            
        # Check for existing blood pool (single pool per room)
        existing_pool = None
        for obj in self.obj.location.contents:
            if hasattr(obj, 'db') and obj.db.is_blood_pool:
                existing_pool = obj
                break
        
        if existing_pool:
            # Merge into existing pool (like graffiti entries)
            existing_pool.add_bleeding_incident(self.obj.key, severity)
        else:
            # Create new blood pool
            from evennia import create_object
            from typeclasses.objects import BloodPool
            
            blood_pool = create_object(
                BloodPool,
                key="blood stains",
                location=self.obj.location
            )
            blood_pool.add_bleeding_incident(self.obj.key, severity)


def start_medical_script(character):
    """
    Start or get the medical script for a character.
    
    Args:
        character: The character to start medical script for
        
    Returns:
        MedicalScript: The active medical script
    """
    try:
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        splattercast.msg(f"START_MEDICAL_SCRIPT: Checking for existing script on {character.key}")
    except Exception:
        pass
        
    # Don't create scripts for dead characters
    if hasattr(character, 'medical_state') and character.medical_state.is_dead():
        try:
            splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
            splattercast.msg(f"START_MEDICAL_SCRIPT: {character.key} is dead, not creating medical script")
        except Exception:
            pass
        return None
        
    # Check if script already exists
    existing_script = character.scripts.get("medical_script")
    if existing_script:
        try:
            splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
            splattercast.msg(f"START_MEDICAL_SCRIPT: Found existing script for {character.key}")
        except Exception:
            pass
        return existing_script.first() if existing_script else None
    
    # Create new script
    try:
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        splattercast.msg(f"START_MEDICAL_SCRIPT: Creating new script for {character.key}")
    except Exception:
        pass
        
    script = character.scripts.add(MedicalScript)
    
    try:
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        splattercast.msg(f"START_MEDICAL_SCRIPT: Script created: {script}")
    except Exception:
        pass
        
    return script


def stop_medical_script(character):
    """
    Stop and delete the medical script for a character.
    
    Args:
        character: The character to stop medical script for
    """
    try:
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        splattercast.msg(f"STOP_MEDICAL_SCRIPT: Looking for medical scripts on {character.key}")
    except Exception:
        pass
    
    # Find and delete all medical scripts (active or stopped)
    existing_scripts = character.scripts.get("medical_script")
    if existing_scripts:
        for script in existing_scripts:
            try:
                splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
                splattercast.msg(f"STOP_MEDICAL_SCRIPT: Found script {script}, deleting it")
            except Exception:
                pass
            script.stop()
            script.delete()
    else:
        try:
            splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
            splattercast.msg(f"STOP_MEDICAL_SCRIPT: No medical scripts found on {character.key}")
        except Exception:
            pass
