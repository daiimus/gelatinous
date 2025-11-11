"""
Death Progression Script - Time-Delayed Death System

This script creates a dramatic window between death and final death,
allowing for medical intervention and creating suspenseful RP opportunities.

The system works as follows:
1. Character "dies" - death curtain plays, they enter dying state
2. Timer begins with periodic progression messages
3. Other characters can attempt revival during this window
4. After time expires, final death occurs (permanent until manual revival)

Duration is configurable via DEATH_PROGRESSION_DURATION in world/combat/constants.py:
- Default: 360 seconds (6 minutes) - provides RP and revival window
- Testing: Can be reduced to 60 (1 minute) or 120 (2 minutes) for faster iteration

This creates urgency for medical response while making death less instantaneous.
"""

from evennia import DefaultScript
from evennia.utils import delay
from evennia.comms.models import ChannelDB
from world.combat.constants import (
    DEATH_PROGRESSION_DURATION,
    DEATH_PROGRESSION_CHECK_INTERVAL,
    DEATH_PROGRESSION_MESSAGE_COUNT
)
import random
import time
import re


def _get_terminal_width(session=None):
    """Get terminal width from session, defaulting to 78 for MUD compatibility."""
    if session:
        try:
            detected_width = session.protocol_flags.get("SCREENWIDTH", [78])[0]
            return max(60, detected_width)  # Minimum 60 for readability
        except (IndexError, KeyError, TypeError):
            pass
    return 78


def _strip_color_codes(text):
    """Remove Evennia color codes from text to get actual visible length."""
    # Remove all |x codes (where x is any character) - same pattern as death curtain
    return re.sub(r'\|.', '', text)


def _center_text(text, width=None, session=None):
    """Center text using same approach as curtain_of_death.py for consistency."""
    if width is None:
        width = _get_terminal_width(session)
    
    # Use same width calculation as curtain for consistent centering
    # Reserve small buffer for color codes like the curtain does
    message_width = width - 1  # Match curtain_width calculation
    
    # Split into lines and center each line - same as curtain
    lines = text.split('\n')
    centered_lines = []
    
    for line in lines:
        if not line.strip():  # Empty line
            centered_lines.append("")
            continue
            
        # Calculate visible text length (without color codes) - same as curtain
        visible_text = _strip_color_codes(line)
        
        # Use Python's built-in center method for proper centering - same as curtain  
        centered_visible = visible_text.center(message_width)
        
        # Calculate the actual padding that center() applied
        padding_needed = message_width - len(visible_text)
        left_padding = padding_needed // 2
        
        # Apply the same left padding to the original colored text
        centered_line = " " * left_padding + line
        centered_lines.append(centered_line)
    
    return '\n'.join(centered_lines)


class DeathProgressionScript(DefaultScript):
    """
    Script that manages the time-delayed death progression.
    
    Attached to a character who is dying but not yet permanently dead.
    Provides a window for medical intervention and creates dramatic tension.
    """
    
    def at_msg_send(self, msg, to_obj=None, **kwargs):
        """
        Called when this script sends a message to someone via msg().
        
        This hook is required for scripts that are passed as from_obj to character.msg().
        Since we send death progression messages with from_obj=self, Evennia calls this
        method to allow the script to intercept or modify outgoing messages.
        
        Args:
            msg: The message being sent
            to_obj: The object receiving the message
            **kwargs: Additional message parameters
            
        Returns:
            None - allows message to be sent normally
        """
        # We don't need to intercept or modify messages, just allow them to pass through
        pass
    
    def at_script_creation(self):
        """Initialize the death progression script."""
        self.key = "death_progression"
        self.desc = f"Time-delayed death progression for {self.obj.key}"
        self.persistent = True
        self.autostart = True  # Can use autostart since we'll use self.obj
        
        # Death progression timing - now configurable via constants
        self.db.total_duration = DEATH_PROGRESSION_DURATION
        
        # Calculate message intervals dynamically based on duration and message count
        # This ensures messages are evenly distributed regardless of total duration
        interval_spacing = DEATH_PROGRESSION_DURATION // DEATH_PROGRESSION_MESSAGE_COUNT
        self.db.message_intervals = [
            interval_spacing * i for i in range(1, DEATH_PROGRESSION_MESSAGE_COUNT + 1)
        ]
        
        self.db.start_time = time.time()
        self.db.messages_sent = []
        self.db.can_be_revived = True
        
        # Start the progression interval - use configurable check interval
        self.interval = DEATH_PROGRESSION_CHECK_INTERVAL
        
        # Debug logging
        try:
            splattercast = ChannelDB.objects.get_channel("Splattercast")
            splattercast.msg(
                f"DEATH_PROGRESSION: Script at_script_creation for {self.obj.key} "
                f"(duration: {DEATH_PROGRESSION_DURATION}s, "
                f"interval: {DEATH_PROGRESSION_CHECK_INTERVAL}s, "
                f"messages: {DEATH_PROGRESSION_MESSAGE_COUNT})"
            )
        except:
            pass
        
    def at_start(self):
        """Called when script starts."""
        character = self.obj
        if not character:
            self.stop()
            return
            
        # Log start of death progression with configurable duration
        try:
            splattercast = ChannelDB.objects.get_channel("Splattercast")
            duration_minutes = DEATH_PROGRESSION_DURATION / 60
            splattercast.msg(
                f"DEATH_PROGRESSION: Started for {character.key} - "
                f"{duration_minutes:.1f} minute revival window"
            )
        except:
            pass
            
        # Send initial dying message
        self._send_initial_message()
        
    def at_repeat(self):
        """Called every 30 seconds during death progression."""
        character = self.obj
        if not character:
            # Log cleanup for invalid character
            try:
                splattercast = ChannelDB.objects.get_channel("Splattercast")
                splattercast.msg(f"DEATH_SCRIPT_CLEANUP: Stopping and deleting death progression script (invalid character)")
            except:
                pass
            self.stop()
            self.delete()
            return
            
        current_time = time.time()
        elapsed = current_time - self.db.start_time
        
        # Debug logging
        try:
            splattercast = ChannelDB.objects.get_channel("Splattercast")
            splattercast.msg(f"DEATH_PROGRESSION: at_repeat for {character.key}, elapsed: {elapsed:.1f}s")
        except:
            pass
        
        # Check if medical conditions have been resolved and character should be revived
        if self._check_medical_revival_conditions(character):
            self._handle_medical_revival()
            return
        
        # Check if we should send a progression message
        for interval in self.db.message_intervals:
            if interval not in self.db.messages_sent and elapsed >= interval:
                self._send_progression_message(interval)
                self.db.messages_sent.append(interval)
                
        # Check if death progression is complete
        if elapsed >= self.db.total_duration:
            self._complete_death_progression()
            
    def _check_medical_revival_conditions(self, character):
        """
        Check if the character's medical state has improved enough to warrant revival.
        This integrates with the existing medical system.
        
        Args:
            character: The character to check
            
        Returns:
            bool: True if character should be revived due to medical improvement
        """
        if not hasattr(character, 'medical_state') or not character.medical_state:
            return False
            
        medical_state = character.medical_state
        
        # Check if the character is no longer dead according to medical system
        if not medical_state.is_dead():
            # Medical treatment has resolved the fatal conditions!
            return True
            
        # Additional checks for improvement trends could go here
        # For example: blood level increasing, organ HP being restored, etc.
        
        return False
        
    def _handle_medical_revival(self):
        """Handle revival due to successful medical intervention."""
        character = self.obj
        if not character:
            return
            
        # Log medical revival
        try:
            splattercast = ChannelDB.objects.get_channel("Splattercast")
            elapsed = time.time() - self.db.start_time
            splattercast.msg(f"MEDICAL_REVIVAL: {character.key} revived by medical treatment after {elapsed:.1f}s")
            splattercast.msg(f"DEATH_SCRIPT_CLEANUP: Stopping and deleting death progression script for {character.key} (medical revival)")
        except:
            pass
            
        # Medical revival messages
        character.msg(
            "|gThe medical treatment takes effect! You feel life returning to your body.|n\n"
            "|gYou have been pulled back from death's door by skilled medical intervention.|n",
            from_obj=self
        )
        
        if character.location:
            room_msg = f"|g{character.key} responds to medical treatment and returns from the brink of death!|n"
            character.location.msg_contents(room_msg, exclude=[character])
            
        # Restore character to living state
        if hasattr(character, 'remove_death_state'):
            character.remove_death_state()
            
        # Stop and delete the death progression script
        self.stop()
        self.delete()
            
    def _send_initial_message(self):
        """Send the initial message when death progression begins."""
        character = self.obj
        if not character:
            return
            
        # Message to the dying character - use exact same approach as curtain DEATH message
        # Get session for proper width detection, just like curtain of death does
        session = None
        if hasattr(character, 'sessions') and character.sessions.all():
            session = character.sessions.all()[0]
        
        # Get width using the same function as curtain of death
        width = _get_terminal_width(session)
        
        # Use same width calculation as curtain for consistent centering
        # Reserve small buffer for color codes like the curtain does
        message_width = width - 1  # Match curtain_width calculation
        
        # Use exact same pattern as curtain: "|r" + text.center(message_width) + "|n"
        dying_line1 = "|R" + "You hover at the threshold between life and death.".center(message_width) + "|n"
        dying_line2 = "|r" + "Your essence flickers like a candle in the wind...".center(message_width) + "|n"
        dying_line3 = "|R" + "There may still be time for intervention.".center(message_width) + "|n"
        
        # Send each line separately with line breaks
        centered_dying_msg = dying_line1 + "\n" + dying_line2 + "\n" + dying_line3 + "\n"
        character.msg(centered_dying_msg, from_obj=self)
        
        # Don't send observer messages - they were overwhelming and redundant
        # The death curtain already provides a vivid death notification
            
    def _send_progression_message(self, interval):
        """Send a message at specific intervals during death progression."""
        character = self.obj
        if not character:
            return
            
        # Calculate remaining time
        elapsed = time.time() - self.db.start_time
        remaining = self.db.total_duration - elapsed
        minutes_remaining = int(remaining / 60)
        
        # Calculate which message index to use based on interval position
        # This ensures messages scale with duration
        try:
            message_index = self.db.message_intervals.index(interval)
        except (ValueError, AttributeError):
            message_index = len(self.db.message_intervals) - 1  # Default to last message
        
        # Get all messages as a list
        messages_list = self._get_progression_messages()
        
        # Use modulo to ensure we don't exceed available messages
        message_data = messages_list[message_index % len(messages_list)]
        
        # Send message to dying character with death progression script as from_obj
        character.msg(message_data["dying"], from_obj=self)
        
        # Skip observer messages during progression - they tick too fast and overwhelm
            
        # Log progression
        try:
            splattercast = ChannelDB.objects.get_channel("Splattercast")
            splattercast.msg(f"DEATH_PROGRESSION: {character.key} at {interval}s (msg {message_index + 1}/{len(messages_list)}) - {minutes_remaining}m remaining")
        except:
            pass
            
    def _get_progression_messages(self):
        """Get the progression messages as an ordered list."""
        return [
            {  # Message 0 - First progression message
                "dying": "|nTime becomes elastic, like chewing gum stretched between your teeth, and the fluorescent lights are humming a song you remember from childhood but can't quite place. The edges of everything are soft now, melting like crayons left in a hot car, and you're floating in this warm red soup that tastes like copper pennies and your mother's disappointment. The clock on the wall is ticking backwards and each second is a small death, a tiny funeral for the person you were just a moment ago. You can taste colors now, hear the weight of silence, feel the texture of your own heartbeat as it stumbles through its final choreography. Someone is playing a violin made of broken dreams in the distance, and the melody sounds suspiciously like that hold music from the unemployment office. Your teeth feel loose in your skull, like Chiclets rattling in a box that someone keeps shaking just to hear the sound.|n\n",
                "observer": "|n{name}'s eyes roll back, showing only whites.|n"
            },
            {  # Message 1
                "dying": "|nYou're sinking through the floor now, through layers of concrete and earth and forgotten promises, and the voices above sound like they're speaking underwater. Everything tastes like iron and regret. Your body feels like it belongs to someone else, some stranger whose story you heard in a bar once but never really believed. The pain has become philosophical, an abstract concept that your meat vessel is interpreting through nerve endings that no longer quite remember their job. You're watching your life insurance policy come to life, literally, walking around the room in a three-piece suit made of your own skin, calculating actuarial tables with your dying breath. The wallpaper is breathing now, in and out, like the lungs of some massive beast that swallowed your apartment whole. Your fingernails taste like the metal part of pencil erasers, and somewhere a cash register is tallying up the cost of your accumulated mistakes.|n\n",
                "observer": "|n{name}'s breathing becomes shallow and erratic.|n"
            },
            {  # Message 2
                "dying": "|nThe world is a television with bad reception and someone keeps changing the channels. Static. Your grandmother's kitchen. Static. That time you nearly drowned. Static. The taste of blood and birthday cake and the sound of someone crying who might be you but probably isn't, because you're somewhere else now, somewhere darker. Your consciousness is a drunk driver careening through memories it doesn't own anymore, sideswiping moments that belonged to other people, other versions of yourself that died small deaths every day until this final, grand production. The static tastes like Saturday mornings and broken promises. The remote control is made of your own ribs, and every channel change cracks another bone in your chest. Your eyeballs feel like they're dissolving into television snow, white noise with a hint of desperation and the aftertaste of commercial jingles.|n\n",
                "observer": "|n{name} makes a low, rattling sound in their throat.|n"
            },
            {  # Message 3
                "dying": "|nYou're watching yourself from the ceiling corner like a security camera recording the most boring crime ever committed. That body down there, that meat puppet with your face, is leaking life like a punctured water balloon. And you're thinking, this is it? This is the grand finale? This wet, messy, disappointing finale? Your ghost is already filling out paperwork in triplicate, applying for unemployment benefits in the afterlife, wondering if death comes with dental coverage. The irony tastes like pennies and pharmaceutical advertisements. The ceiling tiles are counting down in languages you've never heard, and your soul is doing inventory on a warehouse full of unused potential. Your shadow is packing its bags, ready to find employment with someone who might actually cast an interesting silhouette.|n\n",
                "observer": "|n{name}'s skin takes on a waxy, gray pallor.|n"
            },
            {  # Message 4
                "dying": "|nMemory becomes a kaleidoscope where every piece is broken glass and every turn cuts deeper. You taste the last cigarette you ever smoked, feel the first hand you ever held, hear the last lie you ever told, and it's all happening simultaneously in this carnival of consciousness where the rides are broken and the music is playing backward. Your neurons are firing their final clearance sale—everything must go, rock-bottom prices on experiences you can't even remember having. The carousel horses are bleeding carousel blood and the cotton candy tastes like regret. The funhouse mirrors are showing you every version of yourself you never became, and they're all pointing and laughing at the version you did. Your thoughts are circus peanuts dissolving on your tongue, artificially flavored and ultimately disappointing.|n\n",
                "observer": "|n{name}'s fingers twitch spasmodically.|n"
            },
            {  # Message 5
                "dying": "|nThe darkness isn't dark anymore; it's every color that doesn't have a name, every sound that was never made, every word that was never spoken. You're dissolving into the spaces between seconds, becoming the pause between heartbeats, the silence between screams. And it's beautiful and terrible and completely, utterly ordinary. Your soul is a closing-time bar where the lights have come on and everyone can see exactly how pathetic they really are, but the bartender is Death and she's not calling last call — she's calling first call for the next shift. The jukebox is playing your theme song, but it's off-key and the record keeps skipping on the part where you were supposed to matter. Your consciousness is a newspaper blowing down an empty street at 3 AM, full of yesterday's problems and tomorrow's disappointments.|n\n",
                "observer": "|n{name}'s body convulses once, violently.|n"
            },
            {  # Message 6
                "dying": "|nYou're a radio losing signal, static eating away at the song of yourself until there's nothing left but the spaces between the notes. The pain is gone now, replaced by this vast emptiness that feels like Sunday afternoons and unfinished conversations and all the things you meant to say but never did. Your thoughts are evaporating like water on hot asphalt, leaving behind these weird mineral deposits of memory that taste like childhood and smell like hospitals. The static between radio stations sounds like your mother's voice reading you the phone book. Your bones are tuning forks that no longer vibrate at the right frequency, and your blood has become elevator music for a building that's being demolished. The antenna of your soul is bent and rusty, receiving only test patterns from a broadcasting system that went off the air decades ago.|n\n",
                "observer": "|n{name} lies perfectly still except for the barely perceptible rise and fall of their chest.|n"
            },
            {  # Message 7
                "dying": "|nYou're becoming weather now, becoming the wind that carries other people's secrets, the rain that washes away their sins. You're evaporating into stories that will never be told, jokes that will never be finished, dreams that will never be dreamed. And it's okay. It's all okay. Everything is okay in this place between places. Your consciousness is a going-out-of-business sale where everything is marked down 90%, but nobody wants to buy your used thoughts, your secondhand emotions, your clearance-rack dreams. The clouds are made of your exhaled words, and it's starting to rain all the conversations you never had. Your temperature is dropping to match the ambient disappointment of the universe, and your pulse is keeping time with a metronome that's winding down like a broken music box.|n\n",
                "observer": "|n{name}'s breathing has become so faint it's almost imperceptible.|n"
            },
            {  # Message 8
                "dying": "|nThe last thoughts are like photographs burning in a fire, curling at the edges before disappearing into ash. You remember everything and nothing. You are everyone and no one. The boundary between self and not-self becomes as meaningless as the difference between Tuesday and the color blue. Your identity is melting like ice cream in hell—sweet and messy and ultimately disappointing, leaving behind sticky residue that attracts flies and regret. The photographs in your memory are developing in reverse, turning back into silver and chemicals and possibility. Your name tastes like alphabet soup that's gone cold, and your fingerprints are evaporating off your fingers like steam from a cup of coffee nobody wants to drink. The mirror in your mind has cracked down the middle, and both halves are reflecting someone you've never met.|n\n",
                "observer": "|n{name}'s lips have turned blue.|n"
            },
            {  # Message 9
                "dying": "|nYou're the echo of an echo, the shadow of a shadow, the dream that someone else is forgetting. The darkness isn't coming for you anymore because you ARE the darkness, you are the silence, you are the space where something used to be. And in this final moment of dissolution, you understand everything and nothing at all. Your last coherent thought is wondering if this is how mayonnaise feels when it expires—this slow dissolution into component parts that never really belonged together anyway. The universe is yawning, and you're the sound it makes between sleeping and waking, the pause before the snooze button gets hit for the final time. Your existence is a receipt from a store that went out of business, crumpled in the pocket of a coat you never liked but wore anyway because it was practical.|n\n",
                "observer": "|n{name} doesn't appear to be breathing anymore.|n"
            },
            {  # Message 10 - Final progression message
                "dying": "|n...so tired... ...so very... ...tired... ...the light is... ...warm... ...like being... ...held... ...you can hear... ...laughter... ...from somewhere... ...safe... ...you're not... ...scared anymore... ...just... ...tired... ...tell them... ...tell them... ...you tried... ...but... ...so tired... ...|n\n",
                "observer": "|n{name} lies motionless, their body completely still.|n"
            }
        ]
        
    def _complete_death_progression(self):
        """Complete the death progression - character is now permanently dead."""
        character = self.obj
        if not character:
            self.stop()
            self.delete()
            return
            
        # Mark as permanently dead
        self.db.can_be_revived = False
        
        # Send final death messages - use exact same approach as curtain DEATH message
        # Get session for proper width detection, just like curtain of death does
        session = None
        if hasattr(character, 'sessions') and character.sessions.all():
            session = character.sessions.all()[0]
        
        # Get width using the same function as curtain of death
        width = _get_terminal_width(session)
        
        # Use same width calculation as curtain for consistent centering
        # Reserve small buffer for color codes like the curtain does
        message_width = width - 1  # Match curtain_width calculation
        
        # Use exact same pattern as curtain: "|r" + text.center(message_width) + "|n"
        final_line1 = "|R" + "The darkness claims you completely...".center(message_width) + "|n"
        final_line2 = "|r" + "Your consciousness fades into the void.".center(message_width) + "|n"
        
        # Send each line with line breaks
        centered_final_msg = final_line1 + "\n" + final_line2 + "\n"
        character.msg(centered_final_msg, from_obj=self)
        
        # Send final death rattle to observers - this is the transition to permanent death
        if character.location:
            observer_msg = f"|r{character.key}'s form grows utterly still, life's final spark extinguished forever.|n"
            character.location.msg_contents(observer_msg, exclude=[character])
            
        # Apply final death state (if not already done)
        if hasattr(character, 'apply_final_death_state'):
            character.apply_final_death_state()
        
        # Note: Medical script cleanup now happens in _complete_death_progression
        # before teleport to prevent hook spam
            
        # Complete death progression - corpse creation and character transition
        self._handle_corpse_creation_and_transition(character)
            
        # Log completion
        try:
            splattercast = ChannelDB.objects.get_channel("Splattercast")
            splattercast.msg(f"DEATH_PROGRESSION: {character.key} completed - corpse created, character transitioned")
            splattercast.msg(f"DEATH_SCRIPT_CLEANUP: Stopping and deleting death progression script for {character.key}")
        except:
            pass
            
        # Stop and delete the script to clean up completely
        self.stop()
        self.delete()

    def _handle_corpse_creation_and_transition(self, character):
        """
        Complete the death progression by creating corpse and transitioning character.
        This separates the dead character object from the corpse object for investigation.
        """
        try:
            # 1. Create corpse object with forensic data
            corpse = self._create_corpse_from_character(character)
            
            # 2. Get account and session before unpuppeting
            account = character.account
            session = None
            if account and account.sessions.all():
                session = account.sessions.all()[0]
            
            # 3. Transition character out of play (includes unpuppeting now)
            self._transition_character_to_death(character)
            
            # 4. Initiate character creation for account
            if account and session:
                self._initiate_new_character_creation(account, character, session)
                
            # 5. Log the transition
            try:
                splattercast = ChannelDB.objects.get_channel("Splattercast")
                splattercast.msg(f"DEATH_COMPLETION: {character.key} -> Corpse created, character transitioned")
            except:
                pass
                
        except Exception as e:
            # Fallback - log error but don't crash the death progression
            try:
                splattercast = ChannelDB.objects.get_channel("Splattercast")
                splattercast.msg(f"DEATH_COMPLETION_ERROR: {character.key} - {e}")
            except:
                pass

    def _create_corpse_from_character(self, character):
        """Create a corpse object that preserves forensic data from the character."""
        from evennia import create_object
        import time
        
        # Create corpse object using specialized Corpse typeclass
        corpse = create_object(
            typeclass="typeclasses.corpse.Corpse",
            key="fresh corpse",  # Anonymous corpse name
            location=character.location
        )
        
        # The Corpse typeclass automatically sets up most properties in at_object_creation()
        # Just need to transfer the specific forensic data from this character
        
        # Transfer forensic data for investigation
        corpse.db.original_character_name = character.key
        corpse.db.original_character_dbref = character.dbref
        corpse.db.original_account_dbref = character.account.dbref if character.account else None
        corpse.db.death_time = time.time()
        corpse.db.physical_description = getattr(character.db, 'desc', 'A person.')
        
        # Preserve character appearance data for proper corpse display
        corpse.db.original_gender = getattr(character, 'gender', 'neutral')
        corpse.db.original_skintone = getattr(character.db, 'skintone', None)
        
        # Transfer medical/death data if available
        if hasattr(character, 'medical_state') and character.medical_state:
            corpse.db.death_cause = character.get_death_cause()
            corpse.db.medical_conditions = character.medical_state.get_condition_summary()
            corpse.db.blood_type = getattr(character.db, 'blood_type', 'unknown')
            
            # Transfer wound data for corpse wound descriptions
            try:
                from world.medical.wounds import get_character_wounds
                wound_data = get_character_wounds(character)
                if wound_data:
                    # Store wound data with additional forensic information
                    corpse.db.wounds_at_death = []
                    for wound in wound_data:
                        wound_record = {
                            'injury_type': wound['injury_type'],
                            'location': wound['location'],
                            'severity': wound['severity'],
                            'stage': wound['stage'],
                            'organ': wound.get('organ'),
                            # Store organ state for potential forensic analysis
                            'organ_damage': {
                                'current_hp': wound.get('organ_obj', {}).current_hp if wound.get('organ_obj') else 0,
                                'max_hp': wound.get('organ_obj', {}).max_hp if wound.get('organ_obj') else 100,
                                'container': wound.get('organ_obj', {}).container if wound.get('organ_obj') else wound['location']
                            }
                        }
                        corpse.db.wounds_at_death.append(wound_record)
                    
                    splattercast.msg(f"DEATH_WOUNDS_PRESERVED: {len(wound_data)} wounds preserved on corpse for {character.key}")
            except Exception as e:
                # Don't fail death progression if wound preservation fails
                try:
                    splattercast.msg(f"DEATH_WOUNDS_ERROR: Failed to preserve wounds for {character.key}: {e}")
                except:
                    pass
        
        # Transfer character description data
        if hasattr(character, 'longdesc') and character.longdesc:
            corpse.db.longdesc_data = dict(character.longdesc)  # Copy the dictionary data
        
        # Transfer inventory and worn items to corpse
        transferred_items = []
        
        # Transfer regular inventory items (contents) - this includes held items
        for item in character.contents:
            if item != corpse:  # Don't move the corpse itself
                item.move_to(corpse, quiet=True)
                transferred_items.append(f"{item.key} (#{item.dbref}) (inventory)")
        
        # Transfer worn clothing items
        if hasattr(character, 'worn_items') and character.worn_items:
            for location, items in character.worn_items.items():
                for item in items[:]:  # Create a copy of the list to avoid modification during iteration
                    item.move_to(corpse, quiet=True)
                    transferred_items.append(f"{item.key} (#{item.dbref}) (worn on {location})")
            
            # Clear the worn_items structure
            character.worn_items = {}
        
        # Clear hands (items already moved via contents transfer above)
        if hasattr(character, 'hands') and character.hands:
            for hand_name in character.hands:
                character.hands[hand_name] = None
        
        # Debug logging for item transfer
        try:
            splattercast = ChannelDB.objects.get_channel("Splattercast")
            if transferred_items:
                splattercast.msg(f"DEATH_ITEMS_TRANSFERRED: {len(transferred_items)} items moved to corpse: {', '.join(transferred_items)}")
            else:
                splattercast.msg(f"DEATH_ITEMS_TRANSFERRED: No items found on {character.key} to transfer")
        except:
            pass
        
        # Set corpse description
        corpse.db.desc = f"The lifeless body of {character.key}. {corpse.db.physical_description}"
        
        return corpse

    def _transition_character_to_death(self, character):
        """Move character out of play and unpuppet from account."""
        from evennia import search_object
        
        # Get account reference before unpuppeting
        account = character.account
        
        # Note: death_count will be incremented by archive_character() below
        # We don't increment here to avoid double-counting
        
        # Stop and delete medical scripts BEFORE teleport to prevent hook spam
        try:
            from evennia.scripts.models import ScriptDB
            medical_scripts = ScriptDB.objects.filter(
                db_obj=character,
                db_key="medical_script"
            )
            for script in medical_scripts:
                try:
                    script.stop()
                    script.delete()
                    try:
                        splattercast = ChannelDB.objects.get_channel("Splattercast")
                        splattercast.msg(f"DEATH_MEDICAL_CLEANUP: Stopped and deleted medical script for {character.key}")
                    except:
                        pass
                except Exception as e:
                    try:
                        splattercast = ChannelDB.objects.get_channel("Splattercast")
                        splattercast.msg(f"DEATH_MEDICAL_CLEANUP_ERROR: {character.key} - {e}")
                    except:
                        pass
        except Exception as e:
            try:
                splattercast = ChannelDB.objects.get_channel("Splattercast")
                splattercast.msg(f"DEATH_MEDICAL_CLEANUP_FAIL: {character.key} - {e}")
            except:
                pass
        
        # Move character to limbo/OOC room (Evennia's default limbo is #2)
        # Use move_hooks=False to prevent medical script spam on teleport
        try:
            limbo_room = search_object("#2")[0]  # Limbo room
            old_location = character.location
            character.move_to(limbo_room, quiet=True, move_hooks=False)
            
            # Debug logging for successful teleportation
            try:
                splattercast = ChannelDB.objects.get_channel("Splattercast")
                splattercast.msg(f"DEATH_TELEPORT_SUCCESS: {character.key} moved from {old_location} to {limbo_room}")
            except:
                pass
                
        except Exception as e:
            # Log the specific error instead of silently failing
            try:
                splattercast = ChannelDB.objects.get_channel("Splattercast")
                splattercast.msg(f"DEATH_TELEPORT_ERROR: {character.key} - {e}")
            except:
                pass
        
        # Unpuppet character from account
        if account:
            # Get session before unpuppeting
            session = None
            if account.sessions.all():
                session = account.sessions.all()[0]
            
            # Unpuppet the dead character
            if session:
                account.unpuppet_object(session)
                
                try:
                    splattercast = ChannelDB.objects.get_channel("Splattercast")
                    splattercast.msg(f"DEATH_UNPUPPET: {character.key} unpuppeted from {account.key}")
                except:
                    pass
        
        # Archive the dead character (also handles any lingering sessions)
        character.archive_character(reason="death")
        character.db.death_cause = getattr(character.db, 'death_cause', 'unknown')

    def _initiate_new_character_creation(self, account, old_character, session):
        """Start the character creation process for the account after death."""
        # Give the account feedback about what happened
        account.msg("|r" + "=" * 60 + "|n")
        account.msg("|rYour character has died and cannot be revived.|n")
        account.msg("|rA corpse has been left behind for investigation.|n")
        account.msg("|r" + "=" * 60 + "|n")
        account.msg("")
        
        # Start character creation flow (respawn mode)
        try:
            from commands.charcreate import start_character_creation
            start_character_creation(account, is_respawn=True, old_character=old_character)
        except ImportError as e:
            # Fallback if character creation not yet implemented
            account.msg("|yCharacter creation system is under development.|n")
            account.msg("|yPlease contact staff for assistance creating a new character.|n")
            
            try:
                splattercast = ChannelDB.objects.get_channel("Splattercast")
                splattercast.msg(f"CHARCREATE_IMPORT_ERROR: {e}")
            except:
                pass
        account.msg("")
        
        # TODO: Future implementation might:
        # - Set account state to "needs_character_creation"
        # - Redirect to character creation interface
        # - Provide character creation commands
        # - Handle character naming, stats, description setup


def start_death_progression(character):
    """
    Start the death progression script for a character.
    
    Args:
        character: The character entering death progression
        
    Returns:
        DeathProgressionScript: The created script
    """
    # Check if character already has a death progression script
    existing_script = character.scripts.get("death_progression")
    if existing_script:
        try:
            splattercast = ChannelDB.objects.get_channel("Splattercast")
            splattercast.msg(f"DEATH_PROGRESSION: Existing script found for {character.key}")
        except:
            pass
        return existing_script
        
    # Create new death progression script
    try:
        splattercast = ChannelDB.objects.get_channel("Splattercast")
        splattercast.msg(f"DEATH_PROGRESSION: Creating new script for {character.key}")
    except:
        pass
        
    # Create script using the same pattern as medical script
    script = character.scripts.add(DeathProgressionScript)
    
    try:
        splattercast = ChannelDB.objects.get_channel("Splattercast")
        splattercast.msg(f"DEATH_PROGRESSION: Script created and started: {script} for {character.key}")
    except:
        pass
        
    return script
def get_death_progression_script(character):
    """
    Get the death progression script for a character if it exists.
    
    Args:
        character: The character to check
        
    Returns:
        DeathProgressionScript or None: The script if found, None otherwise
    """
    return character.scripts.get("death_progression")


def get_death_progression_status(character):
    """
    Get the status of a character's death progression for medical system integration.
    
    Args:
        character: The character to check
        
    Returns:
        dict: Status information including time remaining, condition, etc.
    """
    script = get_death_progression_script(character)
    if not script:
        return {"in_progression": False}
        
    import time
    elapsed = time.time() - script.db.start_time
    remaining = script.db.total_duration - elapsed
    
    return {
        "in_progression": True,
        "time_elapsed": elapsed,
        "time_remaining": remaining,
        "total_duration": script.db.total_duration,
        "can_be_revived": script.db.can_be_revived,
        "time_factor": 1.0 - (elapsed / script.db.total_duration)
    }
