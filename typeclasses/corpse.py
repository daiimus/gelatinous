# =============================================================================
# CORPSE OBJECT - Just-In-Time Decay System
# =============================================================================

from .items import Item
import time

class Corpse(Item):
    """
    A corpse object that preserves forensic data and uses just-in-time decay.
    Decay is calculated on-demand when the corpse is looked at or referenced,
    rather than using continuous scripts.
    """
    
    def at_object_creation(self):
        """Initialize corpse with decay tracking."""
        super().at_object_creation()
        
        # Core corpse properties
        self.db.is_corpse = True
        self.db.creation_time = time.time()
        
        # Preserve original descriptions for decay calculations
        self.db.base_description = self.db.desc if self.db.desc is not None else ''
        self.db.base_longdesc = {}
        
        # Forensic data (set by death progression script)
        self.db.original_character_name = "someone"
        self.db.original_character_dbref = None  # Character object dbref
        self.db.original_account_dbref = None    # Account object dbref
        self.db.death_time = time.time()
        self.db.death_cause = "unknown"
        self.db.medical_conditions = []
        self.db.physical_description = ""
        self.db.longdesc_data = {}
        
        # Preserve character appearance data for proper display
        self.db.original_skintone = None
        self.db.original_gender = "neutral"
        
        # Decay settings
        self.db.decay_stages = {
            "fresh": 3600,      # < 1 hour
            "early": 86400,     # < 1 day
            "moderate": 259200, # < 3 days  
            "advanced": 604800, # < 1 week
            "skeletal": float('inf')  # > 1 week
        }
    
    def get_decay_stage(self):
        """Calculate current decay stage based on time elapsed."""
        elapsed = time.time() - self.db.creation_time
        
        for stage, threshold in self.db.decay_stages.items():
            if elapsed < threshold:
                return stage
        return "skeletal"
    
    def get_decay_factor(self):
        """Get decay factor (0.0 = fresh, 1.0 = fully decayed)."""
        elapsed = time.time() - self.db.creation_time
        max_decay_time = self.db.decay_stages["advanced"]  # 1 week
        return min(1.0, elapsed / max_decay_time)
    
    def get_display_name(self, looker, **kwargs):
        """Update display name based on current decay stage."""
        stage = self.get_decay_stage()
        
        decay_names = {
            "fresh": "fresh corpse",
            "early": "pale corpse", 
            "moderate": "decomposing remains",
            "advanced": "putrid remains",
            "skeletal": "skeletal remains"
        }
        
        return decay_names.get(stage, 'corpse')
    
    def _get_preserved_longdesc_descriptions(self):
        """Get visible longdesc descriptions with clothing integration, like living characters."""
        if not self.db.longdesc_data:
            return []
        
        # Import anatomical display order
        try:
            from world.combat.constants import ANATOMICAL_DISPLAY_ORDER
        except ImportError:
            # Fallback order if constants not available
            ANATOMICAL_DISPLAY_ORDER = [
                "head", "face", "left_eye", "right_eye", "left_ear", "right_ear", "neck",
                "chest", "back", "abdomen", "groin",
                "left_arm", "right_arm", "left_hand", "right_hand",
                "left_thigh", "right_thigh", "left_shin", "right_shin", "left_foot", "right_foot"
            ]
        
        descriptions = []
        longdesc_data = self.db.longdesc_data
        
        # Build clothing coverage map from corpse contents
        coverage_map = self._build_corpse_clothing_coverage_map()
        added_clothing_items = set()
        
        # Process in anatomical order, integrating clothing like living characters
        for location in ANATOMICAL_DISPLAY_ORDER:
            if location in coverage_map:
                # Location covered by clothing - use clothing description instead
                clothing_item = coverage_map[location]
                
                # Only add each clothing item once, regardless of how many locations it covers
                if clothing_item not in added_clothing_items:
                    # Get clothing description for corpse context
                    desc = self._get_clothing_desc_for_corpse(clothing_item, location)
                    if desc:
                        descriptions.append((location, desc))
                        added_clothing_items.add(clothing_item)
            else:
                # Location not covered - use preserved longdesc if available
                final_desc = ""
                if location in longdesc_data and longdesc_data[location]:
                    description = longdesc_data[location]
                    # Process template variables like living characters do
                    processed_desc = self._process_corpse_description_variables(description)
                    # Apply decay modifications to the description
                    final_desc = self._apply_decay_to_description(processed_desc)
                
                # Add preserved wound descriptions for this location
                wound_descriptions = self.get_preserved_wound_descriptions(location)
                if wound_descriptions:
                    wound_text = " ".join(wound_descriptions)
                    if final_desc:
                        final_desc = f"{final_desc} {wound_text}"
                    else:
                        # No base description, just use wound descriptions
                        final_desc = wound_text
                
                if final_desc:
                    descriptions.append((location, final_desc))
        
        return descriptions
    
    def _build_corpse_clothing_coverage_map(self):
        """Build a map of body locations covered by clothing items in corpse."""
        coverage_map = {}
        
        # Get clothing items from corpse contents
        clothing_items = []
        for item in self.contents:
            # Check if item appears to be clothing (has coverage attribute)
            if item.db.coverage:
                clothing_items.append(item)
        
        # For each clothing item, map its coverage to body locations
        for item in clothing_items:
            coverage = item.db.coverage or []
            for location in coverage:
                # Use outermost item (last one wins for now - could be enhanced)
                coverage_map[location] = item
        
        return coverage_map
    
    def get_preserved_wound_descriptions(self, location=None):
        """
        Get wound descriptions for this corpse based on preserved wound data.
        
        Args:
            location (str, optional): Specific body location to check. If None, returns all wounds.
            
        Returns:
            list: List of wound description strings for the location(s)
        """
        wound_descriptions = []
        
        # Get preserved wound data
        wounds_at_death = self.db.wounds_at_death or []
        if not wounds_at_death:
            return wound_descriptions
        
        # Filter by location if specified
        relevant_wounds = wounds_at_death
        if location:
            relevant_wounds = [w for w in wounds_at_death if w.get('location') == location]
        
        # Generate descriptions for each wound
        for wound_data in relevant_wounds:
            try:
                from world.medical.wounds import get_wound_description
                
                # Generate wound description using preserved data
                wound_desc = get_wound_description(
                    injury_type=wound_data['injury_type'],
                    location=wound_data['location'],
                    severity=wound_data['severity'],
                    stage='old',  # Corpse wounds are considered 'old' stage
                    organ=wound_data.get('organ'),
                    character=self  # Pass corpse as character for any skintone processing
                )
                
                if wound_desc:
                    wound_descriptions.append(wound_desc)
                    
            except Exception as e:
                # Don't break corpse display if wound description fails
                try:
                    from evennia.comms.models import ChannelDB
                    splattercast = ChannelDB.objects.get_channel("Splattercast")
                    splattercast.msg(f"CORPSE_WOUND_ERROR: Failed to generate wound description for {self.key}: {e}")
                except:
                    pass
                continue
        
        return wound_descriptions
    
    def _get_clothing_desc_for_corpse(self, clothing_item, location):
        """Get clothing description for corpse context."""
        # Set item context for color processing
        self._current_item_context = clothing_item
        
        # Try to get worn description first
        worn_desc = clothing_item.db.worn_desc
        if worn_desc:
            # Process template variables like living characters do
            processed_desc = self._process_corpse_description_variables(worn_desc)
            
            # Modify for corpse context - change "you" to "the corpse"
            corpse_desc = processed_desc.replace("You are wearing", "The corpse is wearing")
            corpse_desc = corpse_desc.replace("you are wearing", "the corpse is wearing")
            corpse_desc = corpse_desc.replace("Your", "The corpse's")
            corpse_desc = corpse_desc.replace("your", "the corpse's")
            
            # Ensure the description ends with proper punctuation
            corpse_desc = corpse_desc.strip()
            if corpse_desc and not corpse_desc.endswith(('.', '!', '?')):
                corpse_desc += '.'
            
            # Clear item context
            if hasattr(self, '_current_item_context'):
                delattr(self, '_current_item_context')
            
            # Apply decay modifications
            return self._apply_decay_to_description(corpse_desc)
        
        # Fallback to item description
        item_desc = clothing_item.db.desc
        if item_desc:
            # Process template variables
            processed_desc = self._process_corpse_description_variables(item_desc)
            
            # Create a simple worn description
            item_name = clothing_item.get_display_name(None)
            corpse_desc = f"The corpse is wearing {item_name}."
            
            # Clear item context
            if hasattr(self, '_current_item_context'):
                delattr(self, '_current_item_context')
                
            return self._apply_decay_to_description(corpse_desc)
        
        # Clear item context
        if hasattr(self, '_current_item_context'):
            delattr(self, '_current_item_context')
        
        return None
    
    def _format_corpse_longdescs(self, longdesc_list):
        """
        Format the longdesc descriptions for corpse display with smart paragraph breaks.
        
        Uses the same intelligent paragraph formatting as living characters for readability.
        """
        if not longdesc_list:
            return ""
        
        # Use the character's smart paragraph formatting logic
        try:
            from world.combat.constants import (
                PARAGRAPH_BREAK_THRESHOLD, 
                ANATOMICAL_REGIONS,
                REGION_BREAK_PRIORITY
            )
        except ImportError:
            # Fallback to simple formatting if constants not available
            descriptions = [desc for location, desc in longdesc_list]
            return " ".join(descriptions)
        
        paragraphs = []
        current_paragraph = []
        current_char_count = 0
        current_region = None
        
        for location, description in longdesc_list:
            # Determine which anatomical region this location belongs to
            location_region = self._get_anatomical_region(location)
            
            # Check if we should break for a new paragraph
            should_break = False
            
            if REGION_BREAK_PRIORITY and current_region and location_region != current_region:
                # Region changed - check if we should break
                if current_char_count >= PARAGRAPH_BREAK_THRESHOLD * 0.7:  # 70% threshold for region breaks
                    should_break = True
            elif current_char_count + len(description) > PARAGRAPH_BREAK_THRESHOLD:
                # Would exceed threshold - break now
                should_break = True
            
            if should_break and current_paragraph:
                # Finish current paragraph and start new one
                paragraphs.append(" ".join(current_paragraph))
                current_paragraph = []
                current_char_count = 0
            
            # Add description to current paragraph
            current_paragraph.append(description)
            current_char_count += len(description) + 1  # +1 for space
            current_region = location_region
        
        # Add final paragraph
        if current_paragraph:
            paragraphs.append(" ".join(current_paragraph))
        
        return "\n\n".join(paragraphs)
    
    def _get_anatomical_region(self, location):
        """
        Determines which anatomical region a location belongs to.
        
        Args:
            location: Body location string
            
        Returns:
            str: Region name or 'extended' for non-standard anatomy
        """
        try:
            from world.combat.constants import ANATOMICAL_REGIONS
            
            for region_name, locations in ANATOMICAL_REGIONS.items():
                if location in locations:
                    return region_name
            return "extended"
        except ImportError:
            # Fallback if constants not available
            return "extended"
    
    def _process_corpse_description_variables(self, description):
        """Process template variables in corpse descriptions using preserved character data."""
        if not description:
            return description
            
        # Get preserved character data for template processing
        original_name = self.db.original_character_name or "the corpse"
        
        # Manual processing using preserved character data (more reliable than character method)
        processed_desc = description
        
        # Get preserved character data
        original_gender = self.db.original_gender if self.db.original_gender is not None else 'neutral'
        original_skintone = self.db.original_skintone
        
        # Process color templates FIRST (before other processing)
        if hasattr(self, '_current_item_context'):
            # If we have item context, use the item's color
            item = getattr(self, '_current_item_context', None)
            if item and item.db.color:
                # Get the proper color code from COLOR_DEFINITIONS
                try:
                    from typeclasses.items import COLOR_DEFINITIONS
                    color_name = item.db.color
                    color_code = COLOR_DEFINITIONS.get(color_name, "")
                    if color_code:
                        # Replace {color} with proper color code and space
                        processed_desc = processed_desc.replace("{color}", f"{color_code}")
                    else:
                        # No color definition found, just remove the tag
                        processed_desc = processed_desc.replace("{color}", "")
                    
                except ImportError:
                    # Fallback if COLOR_DEFINITIONS not available
                    processed_desc = processed_desc.replace("{color}", "")
            else:
                processed_desc = processed_desc.replace("{color}", "")
        else:
            # No item context, just remove color tags
            processed_desc = processed_desc.replace("{color}", "")
        
        # Process gender pronouns (always third person for corpses)
        gender_mapping = {
            'male': 'male',
            'female': 'female', 
            'neutral': 'plural',
            'nonbinary': 'plural',
            'other': 'plural'
        }
        
        character_gender = gender_mapping.get(original_gender, 'plural')
        
        # Pronoun processing - comprehensive mapping
        pronoun_map = {
            'male': {
                'They': 'He', 'they': 'he', 
                'Their': 'His', 'their': 'his',
                'Them': 'Him', 'them': 'him',
                'Theirs': 'His', 'theirs': 'his',
                'Themselves': 'Himself', 'themselves': 'himself',
                'Themself': 'Himself', 'themself': 'himself'
            },
            'female': {
                'They': 'She', 'they': 'she',
                'Their': 'Her', 'their': 'her', 
                'Them': 'Her', 'them': 'her',
                'Theirs': 'Hers', 'theirs': 'hers',
                'Themselves': 'Herself', 'themselves': 'herself',
                'Themself': 'Herself', 'themself': 'herself'
            },
            'plural': {
                'They': 'They', 'they': 'they',
                'Their': 'Their', 'their': 'their',
                'Them': 'Them', 'them': 'them', 
                'Theirs': 'Theirs', 'theirs': 'theirs',
                'Themselves': 'Themselves', 'themselves': 'themselves',
                'Themself': 'Themselves', 'themself': 'themselves'
            }
        }
        
        pronouns = pronoun_map.get(character_gender, pronoun_map['plural'])
        for template, replacement in pronouns.items():
            if f"{{{template}}}" in processed_desc:
                processed_desc = processed_desc.replace(f"{{{template}}}", replacement)
        
        # Process name variables
        processed_desc = processed_desc.replace("{name}", original_name)
        processed_desc = processed_desc.replace("{name's}", f"{original_name}'s")
        
        # Apply skintone coloring if preserved (only to body descriptions, not clothing items)
        if original_skintone and not hasattr(self, '_current_item_context'):
            try:
                from world.combat.constants import SKINTONE_PALETTE
                color_code = SKINTONE_PALETTE.get(original_skintone)
                if color_code:
                    # Apply skintone color to ALL body part descriptions
                    processed_desc = f"{color_code}{processed_desc}|n"
            except ImportError:
                # Fallback if constants not available
                pass
        
        return processed_desc
    
    def _apply_decay_to_description(self, description):
        """Modify a description based on current decay stage."""
        stage = self.get_decay_stage()
        
        decay_modifiers = {
            "fresh": "",  # No modification for fresh corpses
            "early": " The area shows early signs of pallor and cooling.",
            "moderate": " Visible discoloration and early decomposition changes are apparent.",
            "advanced": " Severe decomposition changes have altered the appearance significantly.", 
            "skeletal": " Only skeletal remains and dried tissue are visible."
        }
        
        modifier = decay_modifiers.get(stage, "")
        return f"{description}{modifier}"
    
    def return_appearance(self, looker, **kwargs):
        """Update appearance based on current decay stage when looked at."""
        # Check for complete decay first
        if self._handle_complete_decay():
            return None  # Corpse was destroyed
            
        # Update decay-based descriptions just-in-time
        self._update_decay_descriptions()
        
        # Build appearance similar to character with preserved longdesc data
        parts = []
        
        # 1. Corpse name and main description (current decay state)
        name_and_desc = [self.get_display_name(looker)]
        if self.db.desc:
            name_and_desc.append(self.db.desc)
        parts.append('\n'.join(name_and_desc))
        
        # 2. Display preserved longdesc data with clothing integration
        if self.db.longdesc_data:
            longdesc_descriptions = self._get_preserved_longdesc_descriptions()
            if longdesc_descriptions:
                formatted_longdesc = self._format_corpse_longdescs(longdesc_descriptions)
                parts.append(formatted_longdesc)
        
        return '\n\n'.join(parts)
    
    def at_object_receive(self, moved_obj, source_location, **kwargs):
        """Called when an object is moved to this corpse."""
        super().at_object_receive(moved_obj, source_location, **kwargs)
        # Clear any cached appearance data since contents changed
        if hasattr(self.ndb, 'cached_appearance'):
            delattr(self.ndb, 'cached_appearance')
        
        # Debug logging removed to reduce noise
    
    def at_object_leave(self, moved_obj, target_location, **kwargs):
        """Called when an object leaves this corpse."""
        super().at_object_leave(moved_obj, target_location, **kwargs)
        # Clear any cached appearance data since contents changed
        if hasattr(self.ndb, 'cached_appearance'):
            delattr(self.ndb, 'cached_appearance')
        
        # Debug logging removed to reduce noise
    
    def _update_decay_descriptions(self):
        """Update descriptions based on current decay stage."""
        stage = self.get_decay_stage()
        decay_factor = self.get_decay_factor()
        
        # Base physical description
        base_desc = self.db.physical_description or "A lifeless body."
        
        # Update aliases to match decay stage so players can reference the corpse correctly
        decay_names = {
            "fresh": "fresh corpse",
            "early": "pale corpse", 
            "moderate": "decomposing remains",
            "advanced": "putrid remains",
            "skeletal": "skeletal remains"
        }
        
        stage_name = decay_names.get(stage, 'corpse')
        # Update aliases to include the current decay stage name
        # Don't use clear() as it wipes out Evennia's multi-match tracking
        # Instead, get current aliases and add our decay-related ones
        current_aliases = set(self.aliases.all())
        
        # Define the aliases we want for this decay stage
        desired_aliases = {stage_name, "corpse", "remains", "body"}
        
        # Add any missing aliases
        for alias in desired_aliases:
            if alias not in current_aliases:
                self.aliases.add(alias)
        
        # Stage-specific description modifications
        decay_descriptions = {
            "fresh": f"A recently deceased human body. {base_desc} "
                    f"The body appears fresh, with no signs of decomposition yet visible.",
            
            "early": f"A pale human corpse. {base_desc} "
                    f"The skin has begun to pale and cool, with early signs of lividity visible.",
            
            "moderate": f"Decomposing human remains. "
                       f"Bloating and discoloration have begun, with a distinct odor of decay. "
                       f"The original features are still recognizable but deteriorating.",
            
            "advanced": f"Putrid human remains. "
                       f"Advanced decomposition has set in with severe bloating, fluid leakage, "
                       f"and strong putrid odors. Identification is becoming difficult.",
            
            "skeletal": f"Skeletal human remains. "
                       f"Only bones, dried tissue, and clothing remain. The decomposition process "
                       f"is nearly complete."
        }
        
        # Update main description
        self.db.desc = decay_descriptions.get(stage, base_desc)
        
        # Update longdesc if it exists
        if hasattr(self, 'longdesc') and self.longdesc:
            self._update_longdesc_for_decay(stage, decay_factor)
    
    def _update_longdesc_for_decay(self, stage, decay_factor):
        """Update longdesc details based on decay stage."""
        # This would modify specific longdesc body parts based on decay
        # For now, we'll just add a general decay note
        if hasattr(self, 'longdesc') and self.longdesc:
            # Add decay information to longdesc
            decay_notes = {
                "fresh": "appears fresh and recently deceased",
                "early": "shows early signs of decomposition with pale skin",
                "moderate": "displays moderate decomposition with bloating and discoloration", 
                "advanced": "exhibits advanced putrefaction with severe decay",
                "skeletal": "has decomposed to mostly skeletal remains"
            }
            
            decay_note = decay_notes.get(stage, "shows signs of decay")
            
            # You could modify specific body parts here based on your longdesc system
            # For example: modify skin color, add bloating to torso, etc.
    
    def get_forensic_data(self):
        """Return forensic data for investigation purposes."""
        stage = self.get_decay_stage()
        
        forensic_info = {
            "original_name": self.db.original_character_name,
            "original_character_dbref": self.db.original_character_dbref,
            "original_account_dbref": self.db.original_account_dbref,
            "death_time": self.db.death_time,
            "death_cause": self.db.death_cause,
            "medical_conditions": self.db.medical_conditions,
            "decay_stage": stage,
            "time_since_death": self.get_time_since_death(),
            "identifiable": stage in ["fresh", "early", "moderate"]
        }
        
        return forensic_info
    
    def get_time_since_death(self):
        """Get human-readable time since death."""
        elapsed = time.time() - self.db.death_time
        
        if elapsed < 3600:
            minutes = int(elapsed / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''}"
        elif elapsed < 86400:
            hours = int(elapsed / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''}"
        else:
            days = int(elapsed / 86400)
            return f"{days} day{'s' if days != 1 else ''}"
    
    def get_original_character(self):
        """Get the original character object if it still exists."""
        if self.db.original_character_dbref:
            from evennia.utils.search import search_object
            chars = search_object(f"#{self.db.original_character_dbref}")
            return chars[0] if chars else None
        return None
    
    def get_original_account(self):
        """Get the original account object if it still exists.""" 
        if self.db.original_account_dbref:
            from evennia.utils.search import search_object
            accounts = search_object(f"#{self.db.original_account_dbref}")
            return accounts[0] if accounts else None
        return None
    
    def is_character_still_active(self):
        """Check if the original character is still active in the game."""
        char = self.get_original_character()
        if not char:
            return False
        # Character exists but might be in limbo or archived
        return char.location and char.location.key != "Limbo"
    
    def get_admin_info(self):
        """Get administrative information about this corpse (staff only)."""
        char = self.get_original_character()
        account = self.get_original_account()
        
        admin_info = {
            "corpse_dbref": self.dbref,
            "original_character_name": self.db.original_character_name,
            "original_character_dbref": self.db.original_character_dbref,
            "original_account_dbref": self.db.original_account_dbref,
            "character_still_exists": char is not None,
            "character_still_active": self.is_character_still_active(),
            "account_still_exists": account is not None,
            "creation_time": self.db.creation_time,
            "death_time": self.db.death_time,
            "decay_stage": self.get_decay_stage()
        }
        
        return admin_info
    
    def check_complete_decay(self):
        """Check if corpse should be completely decayed and cleaned up."""
        elapsed = time.time() - self.db.creation_time
        
        # 2 weeks for complete decay and cleanup
        complete_decay_time = 1209600  # 2 weeks in seconds
        
        return elapsed > complete_decay_time
    
    def _handle_complete_decay(self):
        """Handle complete decay - drop items and remove corpse (called when looked at)."""
        if not self.check_complete_decay():
            return False
            
        # Drop all items to the room
        if self.location:
            for item in self.contents:
                item.move_to(self.location, quiet=True)
                
        # Log the decay completion
        try:
            from evennia.comms.models import ChannelDB
            splattercast = ChannelDB.objects.get_channel("Splattercast")
            splattercast.msg(f"CORPSE_DECAY: {self.key} completely decayed and removed from {self.location}")
        except:
            pass
            
        # Remove the corpse
        self.delete()
        return True