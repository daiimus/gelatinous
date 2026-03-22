"""
Medical Core Classes

Core classes for tracking organ health, medical conditions, and medical state
persistence. These form the foundation of the medical system.
"""

from evennia.comms.models import ChannelDB
from .constants import (
    ORGANS, BODY_CAPACITIES, CONTRIBUTION_VALUES, 
    CONSCIOUSNESS_UNCONSCIOUS_THRESHOLD, BLOOD_LOSS_DEATH_THRESHOLD,
    PAIN_CONSCIOUSNESS_MODIFIER, PAIN_UNCONSCIOUS_THRESHOLD
)


class Organ:
    """
    Represents a single organ within a character's anatomy.
    
    Tracks current HP, max HP, and medical conditions affecting this organ.
    Integrates with the body capacity system to determine functional impact.
    """
    
    def __init__(self, organ_name, organ_data=None):
        """
        Initialize an organ instance.
        
        Args:
            organ_name (str): Name of the organ (key in ORGANS dict)
            organ_data (dict, optional): Override organ data, defaults to ORGANS[organ_name]
        """
        self.name = organ_name
        self.data = organ_data or ORGANS.get(organ_name, {})
        
        # Core properties
        self.max_hp = self.data.get("max_hp", 10)
        self.current_hp = self.max_hp  # Start at full health
        self.container = self.data.get("container", "unknown")
        self.hit_weight = self.data.get("hit_weight", "common")
        
        # Functional properties
        self.vital = self.data.get("vital", False)
        self.capacity = self.data.get("capacity", None)
        self.capacities = self.data.get("capacities", [])
        self.contribution = self.data.get("contribution", "minor")
        
        # Medical conditions affecting this organ
        self.conditions = []
        
        # Wound state tracking for longdesc integration
        self.wound_stage = None      # fresh, treated, healing, scarred
        self.injury_type = None      # bullet, cut, stab, blunt, generic
        self.wound_timestamp = None  # When the wound occurred (for future healing)
        
    def is_destroyed(self):
        """Returns True if organ HP is 0 or below."""
        return self.current_hp <= 0
        
    def is_functional(self):
        """Returns True if organ can perform its function."""
        return not self.is_destroyed() and not self._has_disabling_conditions()
        
    def _has_disabling_conditions(self):
        """Check if any conditions disable this organ's function."""
        # For now, return False - will be expanded in later phases
        return False
        
    def get_functionality_percentage(self):
        """
        Returns the percentage of normal function this organ provides.
        
        Returns:
            float: 0.0 to 1.0 representing functional capacity
        """
        if self.is_destroyed():
            return 0.0
            
        # Base functionality based on current HP
        base_function = self.current_hp / self.max_hp
        
        # TODO: Apply condition modifiers in later phases
        # condition_modifier = self._get_condition_penalty()
        # return max(0.0, base_function * condition_modifier)
        
        return base_function
        
    def take_damage(self, amount, injury_type="generic"):
        """
        Apply damage to this organ.
        
        Args:
            amount (int): Damage amount
            injury_type (str): Type of injury (for future expansion)
            
        Returns:
            bool: True if organ was destroyed by this damage
        """
        if amount <= 0:
            return False
            
        old_hp = self.current_hp
        self.current_hp = max(0, self.current_hp - amount)
        
        # Set wound state when damage is first applied
        if old_hp == self.max_hp:  # First damage to this organ
            self.injury_type = injury_type
            self.wound_stage = 'fresh'
            # TODO: Set wound_timestamp when time system is implemented
        elif not hasattr(self, 'injury_type') or self.injury_type == "generic":
            # Update injury type if this is more specific than previous
            self.injury_type = injury_type
        
        # Update wound stage based on organ state
        if self.current_hp <= 0:
            # All destroyed organs start as "destroyed" regardless of location
            self.wound_stage = 'destroyed'  # Immediate aftermath of destruction
        # Keep existing stage if organ was already damaged (don't reset to fresh)
        
        # Return True if this damage destroyed the organ
        return old_hp > 0 and self.current_hp <= 0
    
    def _is_limb_container(self, container):
        """
        Determine if a container represents a limb/appendage vs internal body cavity.
        
        Args:
            container (str): Body location container
            
        Returns:
            bool: True if container is a limb/appendage
        """
        # Internal body cavities - organs here get "destroyed"
        internal_containers = {
            'head', 'chest', 'abdomen', 'back', 'neck', 'groin', 'face'
        }
        
        # Limb/appendage containers - organs here get "severed"
        limb_containers = {
            'left_arm', 'right_arm', 'left_hand', 'right_hand',
            'left_thigh', 'right_thigh', 'left_shin', 'right_shin', 
            'left_foot', 'right_foot', 'tail', 'left_wing', 'right_wing'
        }
        
        # Check for tentacles or other numbered appendages
        if 'tentacle_' in container or '_leg_' in container or '_arm_' in container:
            return True
        
        return container in limb_containers
        
    def heal(self, amount):
        """
        Heal damage to this organ.
        
        Args:
            amount (int): Healing amount
            
        Returns:
            int: Actual amount healed
        """
        if amount <= 0:
            return 0
            
        old_hp = self.current_hp
        self.current_hp = min(self.max_hp, self.current_hp + amount)
        
        # Update wound stage if fully healed
        if self.current_hp == self.max_hp and hasattr(self, 'wound_stage'):
            self.wound_stage = None  # No wound if fully healed
            self.injury_type = None
        
        return self.current_hp - old_hp
        
    def apply_treatment(self, treatment_type="basic"):
        """
        Apply medical treatment to this organ's wound.
        Future-proofing method for medical treatment system.
        
        Args:
            treatment_type (str): Type of treatment applied
        """
        if hasattr(self, 'wound_stage'):
            if self.wound_stage == 'fresh':
                self.wound_stage = 'treated'
                # TODO: Add treatment effects, healing bonuses, etc.
            elif self.wound_stage == 'destroyed':
                # Medical treatment of destroyed organs results in clean amputation/severance
                self.wound_stage = 'severed'
                # TODO: Add surgical amputation effects, pain management, etc.
    
    def advance_healing_stage(self):
        """
        Advance the wound to the next healing stage.
        Future-proofing method for time-based healing system.
        
        Note: Destroyed organs can be treated to "severed" (clean amputation/medical care).
        Severed organs are permanent and cannot heal further.
        """
        if not hasattr(self, 'wound_stage') or not self.wound_stage:
            return
            
        stage_progression = {
            'fresh': 'healing',
            'treated': 'healing', 
            'healing': 'scarred',
            'destroyed': 'destroyed',  # Stays destroyed until medical treatment
            'severed': 'severed',      # Permanent - clean amputation/medical care
            'scarred': 'scarred'       # Permanent marks
        }
        
        self.wound_stage = stage_progression.get(self.wound_stage, self.wound_stage)
        
        # Scarred stage only applies to organs that still have HP (non-destroyed)
        if self.wound_stage == 'scarred' and self.current_hp <= 0:
            # Destroyed organs can't become scars - they stay destroyed
            self.wound_stage = 'destroyed'
            # TODO: Consider if we want visible scars for non-destroyed organs
            pass
        
    def add_condition(self, condition):
        """Add a medical condition to this organ."""
        if condition not in self.conditions:
            self.conditions.append(condition)
            
    def remove_condition(self, condition):
        """Remove a medical condition from this organ."""
        if condition in self.conditions:
            self.conditions.remove(condition)
            
    def to_dict(self):
        """
        Serialize organ state for persistence.
        
        Returns:
            dict: Serialized organ state
        """
        return {
            "name": self.name,
            "current_hp": self.current_hp,
            "max_hp": self.max_hp,
            "conditions": self.conditions.copy(),
            "container": self.container,
            "wound_stage": self.wound_stage,
            "injury_type": self.injury_type,
            "wound_timestamp": self.wound_timestamp
        }
        
    @classmethod
    def from_dict(cls, data):
        """
        Deserialize organ state from persistence.
        
        Args:
            data (dict): Serialized organ state
            
        Returns:
            Organ: Restored organ instance
        """
        organ = cls(data["name"])
        organ.current_hp = data.get("current_hp", organ.max_hp)
        organ.max_hp = data.get("max_hp", organ.max_hp)
        organ.conditions = data.get("conditions", [])
        organ.wound_stage = data.get("wound_stage")
        organ.injury_type = data.get("injury_type")
        organ.wound_timestamp = data.get("wound_timestamp")
        return organ


class MedicalState:
    """
    Manages the complete medical state of a character.
    
    Coordinates between organs, conditions, vital signs, and body capacities.
    Handles persistence and provides high-level medical queries.
    """
    
    def __init__(self, character=None):
        """
        Initialize medical state.
        
        Args:
            character: Reference to the character this belongs to
        """
        self.character = character
        self.organs = {}
        self.conditions = []
        
        # Vital signs
        self.blood_level = 100.0  # Percentage of normal blood volume
        self.pain_level = 0.0     # Current pain accumulation
        self.consciousness = 1.0  # Current consciousness level (0.0 to 1.0)
        
        # Cache for expensive calculations
        self._capacity_cache = {}
        self._cache_dirty = True
        
        # Initialize default human organs
        self._initialize_default_organs()
        
    def _initialize_default_organs(self):
        """Initialize standard human organ set."""
        for organ_name in ORGANS.keys():
            self.organs[organ_name] = Organ(organ_name)
            
    def get_organ(self, organ_name):
        """Get organ by name, creating if it doesn't exist."""
        if organ_name not in self.organs:
            self.organs[organ_name] = Organ(organ_name)
        return self.organs[organ_name]
        
    def get_conditions_by_location(self, location):
        """Get all conditions affecting a specific body location."""
        return [c for c in self.conditions if c.location == location]
        
    def calculate_total_pain(self):
        """Calculate total pain from all conditions."""
        total_pain = sum(condition.get_pain_contribution() for condition in self.conditions)
        return total_pain
        
    def calculate_blood_loss_rate(self):
        """Calculate total blood loss per round from all bleeding conditions."""
        total_loss = sum(condition.get_blood_loss_rate() for condition in self.conditions)
        return total_loss
        
    def calculate_body_capacity(self, capacity_name):
        """
        Calculate current level of a body capacity.
        
        Args:
            capacity_name (str): Name of capacity to calculate
            
        Returns:
            float: 0.0 to 1.0 representing capacity level
        """
        if not self._cache_dirty and capacity_name in self._capacity_cache:
            return self._capacity_cache[capacity_name]
            
        capacity_data = BODY_CAPACITIES.get(capacity_name, {})
        capacity_organs = capacity_data.get("organs", [])
        
        if not capacity_organs:
            return 1.0  # No organs defined = full capacity
            
        total_capacity = 0.0
        max_possible_capacity = 0.0
        
        for organ_name in capacity_organs:
            organ = self.get_organ(organ_name)
            organ_functionality = organ.get_functionality_percentage()
            
            # Get contribution level - check for organ-specific contributions first
            contribution_value = None
            
            # Check for organ-specific contributions (e.g., liver_contribution, stomach_contribution)
            organ_contribution_key = f"{organ_name}_contribution"
            if organ_contribution_key in capacity_data:
                contribution_value = capacity_data[organ_contribution_key]
            else:
                # Check for bone-specific contributions (e.g., femur_contribution, humerus_contribution)
                bone_type = organ_name.split('_')[-1]  # Get bone name (femur, humerus, etc.)
                if bone_type in ['femur', 'tibia', 'humerus']:
                    bone_contribution_key = f"{bone_type}_contribution"
                elif 'metacarpals' in organ_name:
                    bone_contribution_key = "metacarpal_contribution"
                elif 'metatarsals' in organ_name:
                    bone_contribution_key = "metatarsal_contribution"
                else:
                    bone_contribution_key = None
                    
                if bone_contribution_key and bone_contribution_key in capacity_data:
                    contribution_value = capacity_data[bone_contribution_key]
                else:
                    # Fall back to organ's defined contribution or generic lookup
                    contribution_key = organ.data.get(f"{capacity_name}_contribution", organ.contribution)
                    if isinstance(contribution_key, str):
                        contribution_value = CONTRIBUTION_VALUES.get(contribution_key, 0.05)
                    else:
                        contribution_value = float(contribution_key)
                
            # Add to totals
            total_capacity += organ_functionality * contribution_value
            max_possible_capacity += contribution_value
            
        # Normalize to 0.0-1.0 range based on maximum possible capacity
        if max_possible_capacity > 0:
            capacity_level = total_capacity / max_possible_capacity
        else:
            capacity_level = 1.0
            
        # Clamp to valid range
        capacity_level = max(0.0, min(1.0, capacity_level))
        
        # Cache the result
        self._capacity_cache[capacity_name] = capacity_level
        return capacity_level
        
    def is_unconscious(self):
        """Returns True if character is unconscious."""
        # Use the final consciousness value that includes all penalties:
        # - organ damage penalties (from calculate_body_capacity)
        # - pain penalties 
        # - blood loss penalties
        # - consciousness suppression penalties from conditions
        return self.consciousness < (CONSCIOUSNESS_UNCONSCIOUS_THRESHOLD / 100.0)
        
    def is_dead(self):
        """Returns True if character should be considered dead."""
        # Death from vital organ failure
        if self.calculate_body_capacity("blood_pumping") <= 0.0:
            return True
        if self.calculate_body_capacity("breathing") <= 0.0:
            return True
        if self.calculate_body_capacity("digestion") <= 0.0:
            return True  # Liver failure
            
        # Death from blood loss
        if self.blood_level <= (100.0 - BLOOD_LOSS_DEATH_THRESHOLD):
            return True
            
        return False
        
    def update_vital_signs(self):
        """Update vital signs based on current conditions and organ state."""
        # Update pain level
        self.pain_level = self.calculate_total_pain()
        
        # Update blood loss
        blood_loss_rate = self.calculate_blood_loss_rate()
        if blood_loss_rate > 0:
            self.blood_level = max(0.0, self.blood_level - blood_loss_rate)
            
        # Update consciousness based on multiple factors
        base_consciousness = self.calculate_body_capacity("consciousness")
        
        # Pain penalty
        pain_penalty = 0.0
        if self.pain_level > PAIN_UNCONSCIOUS_THRESHOLD:
            pain_penalty = (self.pain_level - PAIN_UNCONSCIOUS_THRESHOLD) * PAIN_CONSCIOUSNESS_MODIFIER
            
        # Blood loss penalty
        blood_penalty = max(0.0, (100.0 - self.blood_level) / 100.0)
        
        # Consciousness suppression penalty from medical conditions
        consciousness_suppression_penalty = 0.0
        for condition in self.conditions:
            if hasattr(condition, 'get_consciousness_penalty'):
                consciousness_suppression_penalty += condition.get_consciousness_penalty()
        
        self.consciousness = max(0.0, base_consciousness - pain_penalty - blood_penalty - consciousness_suppression_penalty)
        
        # Mark cache as dirty after vital sign updates
        self._cache_dirty = True
        
    def take_organ_damage(self, organ_name, damage_amount, injury_type="generic"):
        """
        Apply damage to a specific organ and create appropriate medical conditions.
        
        Args:
            organ_name (str): Name of organ to damage
            damage_amount (int): Amount of damage
            injury_type (str): Type of injury
            
        Returns:
            bool: True if organ was destroyed
        """
        organ = self.get_organ(organ_name)
        was_destroyed = organ.take_damage(damage_amount, injury_type)
        
        # Create medical conditions based on damage type and amount (Phase 2.6)
        if damage_amount > 0:
            new_conditions = self._create_conditions_from_damage(
                damage_amount, injury_type, organ.container
            )
            
            # Add and start new conditions
            for condition in new_conditions:
                self.add_condition(condition)
        
        self._cache_dirty = True
        return was_destroyed
        
    def _create_conditions_from_damage(self, damage_amount, injury_type, location):
        """
        Create appropriate medical conditions based on damage dealt.
        
        Args:
            damage_amount (int): Amount of damage
            injury_type (str): Type of injury
            location (str): Body location affected
            
        Returns:
            list: List of medical conditions to add
        """
        try:
            from .conditions import create_condition_from_damage
            conditions = create_condition_from_damage(damage_amount, injury_type, location)
            return conditions
        except ImportError as e:
            # Fallback if conditions module not available
            return []
        except Exception as e:
            return []
            
    def add_condition(self, condition):
        """
        Add a medical condition and start its ticker if needed.
        
        Args:
            condition: MedicalCondition instance
        """
        # Don't add conditions if character is archived (permanently dead)
        # Dying characters can still be resuscitated, so they should keep conditions
        character = self._get_character_reference()
        if character and character.db.archived:
            try:
                from world.combat.constants import SPLATTERCAST_CHANNEL
                splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
                char_name = character.key if character else "unknown"
                splattercast.msg(f"ADD_CONDITION: {char_name} is archived, not adding {condition.condition_type}")
            except Exception:
                pass
            return
            
        if condition not in self.conditions:
            self.conditions.append(condition)
            
            try:
                from world.combat.constants import SPLATTERCAST_CHANNEL
                splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
                splattercast.msg(f"ADD_CONDITION: Added {condition.condition_type} severity {condition.severity}")
            except Exception:
                pass
            
            # Start ticker if condition requires it
            if hasattr(condition, 'requires_ticker') and condition.requires_ticker:
                # Get character reference - this is a bit tricky since MedicalState
                # doesn't directly hold character reference
                character = self._get_character_reference()
                if character:
                    try:
                        from world.combat.constants import SPLATTERCAST_CHANNEL
                        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
                        splattercast.msg(f"ADD_CONDITION: Starting ticker for {condition.condition_type} on {character.key}")
                    except Exception:
                        pass
                    condition.start_condition(character)
                else:
                    try:
                        from world.combat.constants import SPLATTERCAST_CHANNEL
                        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
                        splattercast.msg(f"ADD_CONDITION: No character reference found for {condition.condition_type}")
                    except Exception:
                        pass
            
            # Save medical state after adding condition to ensure persistence
            if self.character:
                self.character.save_medical_state()
                    
    def remove_condition(self, condition):
        """
        Remove a medical condition and stop its ticker.
        
        Args:
            condition: MedicalCondition instance to remove
        """
        if condition in self.conditions:
            self.conditions.remove(condition)
            
            # Stop ticker if condition had one
            if hasattr(condition, 'stop_condition'):
                condition.stop_condition()
                
    def get_conditions_by_type(self, condition_type):
        """
        Get all conditions of a specific type.
        
        Args:
            condition_type (str): Type of condition to search for
            
        Returns:
            list: Conditions matching the type
        """
        return [c for c in self.conditions if c.condition_type == condition_type]
        
    def get_condition_summary(self):
        """
        Get a summary of all active medical conditions.
        
        Returns:
            dict: Summary of conditions by type with counts and severity
        """
        summary = {}
        for condition in self.conditions:
            ctype = condition.condition_type
            if ctype not in summary:
                summary[ctype] = {'count': 0, 'severity': 0, 'locations': []}
            
            summary[ctype]['count'] += 1
            summary[ctype]['severity'] += getattr(condition, 'severity', 1)
            if hasattr(condition, 'location'):
                summary[ctype]['locations'].append(condition.location)
                
        return summary
                    
    def _get_character_reference(self):
        """
        Get reference to character that owns this medical state.
        """
        return self.character
        
    def to_dict(self):
        """Serialize medical state for persistence."""
        return {
            "organs": {name: organ.to_dict() for name, organ in self.organs.items()},
            "conditions": [condition.to_dict() for condition in self.conditions],
            "blood_level": self.blood_level,
            "pain_level": self.pain_level,
            "consciousness": self.consciousness
        }
        
    @classmethod 
    def from_dict(cls, data, character=None):
        """Deserialize medical state from persistence."""
        medical_state = cls(character)
        
        # Restore organs
        organ_data = data.get("organs", {})
        for organ_name, organ_dict in organ_data.items():
            medical_state.organs[organ_name] = Organ.from_dict(organ_dict)
            
        # Restore conditions - using proper deserialization
        condition_data = data.get("conditions", [])
        for condition_dict in condition_data:
            try:
                # Import condition classes
                from .conditions import (
                    MedicalCondition, BleedingCondition, PainCondition,
                    InfectionCondition, ConsciousnessSuppressionCondition,
                )
                
                # Get condition type
                condition_type = condition_dict.get("condition_type", "minor_bleeding")
                
                # Create appropriate condition using its from_dict method
                if condition_type == "minor_bleeding":
                    condition = BleedingCondition.from_dict(condition_dict)
                elif condition_type == "pain":
                    condition = PainCondition.from_dict(condition_dict) 
                elif condition_type == "infection":
                    condition = InfectionCondition.from_dict(condition_dict)
                elif condition_type == "consciousness_suppression":
                    condition = ConsciousnessSuppressionCondition.from_dict(condition_dict)
                else:
                    # Fallback to base class
                    condition = MedicalCondition.from_dict(condition_dict)
                
                medical_state.conditions.append(condition)
                # Re-start condition ticker if character is available and not archived
                # Archived characters are permanently dead; dying characters can still be resuscitated
                if character and not character.db.archived:
                    condition.start_condition(character)
                    
            except Exception as e:
                # If condition restoration fails, skip it
                pass
            
        # Restore vital signs
        medical_state.blood_level = data.get("blood_level", 100.0)
        medical_state.pain_level = data.get("pain_level", 0.0)
        
        # Handle consciousness migration: old data stored as percentage (100.0), new as decimal (1.0)
        consciousness_value = data.get("consciousness", 1.0)
        if consciousness_value > 1.0:
            # Old percentage format, convert to decimal
            medical_state.consciousness = consciousness_value / 100.0
        else:
            # New decimal format
            medical_state.consciousness = consciousness_value
        
        return medical_state
