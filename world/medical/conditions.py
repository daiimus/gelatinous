"""
Medical condition classes for the health system.

This module defines the base MedicalCondition class and specific condition types
like bleeding. Conditions are managed by per-character MedicalScript instances.
"""

import random
from evennia.comms.models import ChannelDB
from .constants import (
    INJURY_SEVERITY_MULTIPLIERS,
    BLOOD_LOSS_PER_SEVERITY,
    HEALING_EFFECTIVENESS,
    CONDITION_INTERVALS, 
    BLEEDING_DAMAGE_THRESHOLDS, 
    CONDITION_TRIGGERS
)


class MedicalCondition:
    """
    Base class for all medical conditions.
    
    Medical conditions are now managed by per-character MedicalScript instances
    instead of individual TICKER_HANDLER subscriptions.
    """
    
    def __init__(self, condition_type, severity, location=None, tick_interval=60):
        self.condition_type = condition_type
        self.severity = severity
        self.max_severity = severity  # Track original severity
        self.location = location
        self.tick_interval = tick_interval  # Not used directly anymore, but kept for compatibility
        self.requires_ticker = True
        self.treated = False
        
    def start_condition(self, character):
        """Begin condition management for character."""
        from world.medical.script import start_medical_script
        from evennia.comms.models import ChannelDB
        from world.combat.constants import SPLATTERCAST_CHANNEL
        
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        
        # Don't add conditions to archived characters (permanently dead)
        # Dying characters can still be resuscitated, so they should keep conditions
        if getattr(character.db, 'archived', False):
            splattercast.msg(f"CONDITION_START: {character.key} is archived, not adding {self.condition_type}")
            return
        
        if not self.requires_ticker:
            splattercast.msg(f"CONDITION_START: {self.condition_type} for {character.key} doesn't require ticker")
            return
            
        splattercast.msg(f"CONDITION_START: Adding {self.condition_type} severity {self.severity} to {character.key}")
        
        # Ensure character has medical script running
        medical_script = start_medical_script(character)
        if medical_script:
            splattercast.msg(f"CONDITION_START: Medical script active for {character.key}")
        else:
            splattercast.msg(f"CONDITION_START: Failed to start medical script for {character.key}")
            
    def tick_effect(self, character):
        """Override in subclasses to implement specific effects."""
        pass
        
    def should_end(self):
        """Check if condition should be removed. Override in subclasses."""
        return self.severity <= 0
        
    def get_pain_contribution(self):
        """Return pain contribution from this condition. Override in subclasses."""
        return 0  # Base conditions don't contribute pain by default
        
    def get_blood_loss_rate(self):
        """Return blood loss rate from this condition. Override in subclasses."""
        return 0  # Base conditions don't cause blood loss by default
        
    @property
    def type(self):
        """Alias for condition_type for backward compatibility."""
        return self.condition_type
        
    def to_dict(self):
        """Serialize condition for persistence."""
        return {
            "condition_type": self.condition_type,
            "severity": self.severity,
            "max_severity": self.max_severity,
            "location": self.location,
            "tick_interval": self.tick_interval,
            "requires_ticker": self.requires_ticker,
            "treated": self.treated
        }
        
    @classmethod
    def from_dict(cls, data):
        """Deserialize condition from persistence."""
        condition = cls(
            data.get("condition_type", "unknown"),
            data.get("severity", 1),
            data.get("location")
        )
        condition.max_severity = data.get("max_severity", condition.severity)
        condition.tick_interval = data.get("tick_interval", 60)
        condition.requires_ticker = data.get("requires_ticker", True)
        condition.treated = data.get("treated", False)
        return condition
        
    def end_condition(self, character):
        """Clean up when condition ends."""
        # No ticker cleanup needed - script handles lifecycle
        pass
        
    def apply_treatment(self, treatment_quality="adequate"):
        """Apply medical treatment to this condition."""
        self.treated = True
        # Subclasses should override for specific treatment effects


class BleedingCondition(MedicalCondition):
    """Bleeding condition that causes blood loss over time."""
    
    def __init__(self, severity, location=None):
        super().__init__("minor_bleeding", severity, location, tick_interval=60)
        self.blood_loss_rate = BLOOD_LOSS_PER_SEVERITY.get(severity, 1)
        
    def tick_effect(self, character):
        """Apply blood loss and potentially reduce severity."""
        from world.combat.constants import SPLATTERCAST_CHANNEL
        
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        
        if not hasattr(character, 'medical_state'):
            return
            
        medical_state = character.medical_state
        
        # Calculate blood loss
        blood_loss = self.blood_loss_rate
        if self.treated:
            blood_loss = int(blood_loss * 0.3)  # Treated bleeding loses less blood
            
        # Apply blood loss
        old_blood = medical_state.blood_level
        medical_state.blood_level = max(0, medical_state.blood_level - blood_loss)
        
        splattercast.msg(f"BLOOD_LOSS: {character.key} loses {blood_loss} blood ({old_blood} -> {medical_state.blood_level})")
        
        # Check for natural healing (random chance to reduce severity)
        if not self.treated and random.randint(1, 100) <= 10:  # 10% chance per tick
            self.severity = max(0, self.severity - 1)
            splattercast.msg(f"BLEEDING_HEAL: {character.key} bleeding severity reduced to {self.severity}")
            
        # Note: Individual bleeding messages removed - now handled by consolidated messaging in medical script
                
    def should_end(self):
        """Bleeding ends when severity reaches 0."""
        return self.severity <= 0
        
    def get_pain_contribution(self):
        """Return pain contribution from bleeding."""
        # Bleeding causes pain proportional to severity
        return max(1, self.severity // 2)  # Half severity as pain
        
    def get_blood_loss_rate(self):
        """Return blood loss rate per tick."""
        blood_loss = self.blood_loss_rate
        if self.treated:
            blood_loss = int(blood_loss * 0.3)  # Treated bleeding loses less blood
        return blood_loss
        
    def apply_treatment(self, treatment_quality="adequate"):
        """Apply medical treatment to bleeding."""
        super().apply_treatment(treatment_quality)
        
        # Treatment effectiveness
        effectiveness = HEALING_EFFECTIVENESS.get(treatment_quality, 0.5)
        severity_reduction = max(1, int(self.severity * effectiveness))
        
        self.severity = max(0, self.severity - severity_reduction)
        
        # Reduce blood loss rate for treated bleeding
        self.blood_loss_rate = max(1, int(self.blood_loss_rate * 0.3))
        
    def to_dict(self):
        """Serialize bleeding condition for persistence."""
        data = super().to_dict()
        data["blood_loss_rate"] = self.blood_loss_rate
        return data
        
    @classmethod
    def from_dict(cls, data):
        """Deserialize bleeding condition from persistence."""
        condition = cls(
            data.get("severity", 1),
            data.get("location")
        )
        condition.max_severity = data.get("max_severity", condition.severity)
        condition.tick_interval = data.get("tick_interval", 60)
        condition.requires_ticker = data.get("requires_ticker", True)
        condition.treated = data.get("treated", False)
        condition.blood_loss_rate = data.get("blood_loss_rate", condition.blood_loss_rate)
        return condition


class PainCondition(MedicalCondition):
    """Pain condition that affects character abilities."""
    
    def __init__(self, severity, location=None):
        super().__init__("pain", severity, location, tick_interval=120)  # Longer interval
        
    def tick_effect(self, character):
        """Pain naturally diminishes over time."""
        from world.combat.constants import SPLATTERCAST_CHANNEL
        
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        
        # Natural pain reduction
        if random.randint(1, 100) <= 20:  # 20% chance per tick
            self.severity = max(0, self.severity - 1)
            splattercast.msg(f"PAIN_HEAL: {character.key} pain severity reduced to {self.severity}")
            
        # Note: Individual pain messages removed - now handled by consolidated messaging in medical script
            
    def should_end(self):
        """Pain ends when severity reaches 0."""
        return self.severity <= 0
        
    def get_pain_contribution(self):
        """Return pain contribution from this condition."""
        return self.severity  # Pain conditions contribute their full severity to total pain
        
    def apply_treatment(self, treatment_quality="adequate"):
        """Apply medical treatment to pain."""
        super().apply_treatment(treatment_quality)
        
        # Pain treatment is very effective
        effectiveness = HEALING_EFFECTIVENESS.get(treatment_quality, 0.5)
        severity_reduction = max(1, int(self.severity * effectiveness * 1.5))  # Extra effective
        
        self.severity = max(0, self.severity - severity_reduction)


class InfectionCondition(MedicalCondition):
    """Infection condition that can worsen over time if untreated."""
    
    def __init__(self, severity, location=None):
        super().__init__("infection", severity, location, tick_interval=300)  # 5 minute interval
        self.base_progression_chance = 1.0  # Base % chance to worsen per 12s tick (adjustable by environment)
        self.last_progression_check = 0  # Track time for proper progression timing
        self.environmental_modifier = 1.0  # Multiplier for environmental conditions (sewers, etc.)
        
    def tick_effect(self, character):
        """Infection can worsen if untreated, or improve if treated."""
        from world.combat.constants import SPLATTERCAST_CHANNEL
        import time
        
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        current_time = time.time()
        
        # Initialize timing tracking if needed
        if self.last_progression_check == 0:
            self.last_progression_check = current_time
            return  # Skip first tick to establish baseline
        
        if self.treated:
            # Treated infection improves every ~5 minutes (25 ticks at 12s intervals)
            if random.randint(1, 100) <= 12:  # ~30% chance over 25 ticks = 1.2% per tick
                self.severity = max(0, self.severity - 1)
                splattercast.msg(f"INFECTION_HEAL: {character.key} infection severity reduced to {self.severity}")
        else:
            # Calculate effective progression chance based on timing and environment
            effective_chance = self.base_progression_chance * self.environmental_modifier
            
            # Untreated infection can worsen - designed for realistic ~20min progression
            if random.randint(1, 10000) <= int(effective_chance * 100):  # More granular probability
                self.severity = min(10, self.severity + 1)  # Cap at 10
                splattercast.msg(f"INFECTION_WORSEN: {character.key} infection severity increased to {self.severity} (env modifier: {self.environmental_modifier}x)")
                
        self.last_progression_check = current_time
    
    def set_environmental_modifier(self, modifier):
        """Set environmental infection risk modifier (e.g., 3.0 for sewers, 0.5 for sterile conditions)"""
        self.environmental_modifier = max(0.1, modifier)  # Minimum 0.1x, no maximum
                
        # Note: Infection effect messages removed - now handled by consolidated messaging in medical script
            
    def should_end(self):
        """Infection ends when severity reaches 0."""
        return self.severity <= 0
        
    def apply_treatment(self, treatment_quality="adequate"):
        """Apply medical treatment to infection."""
        super().apply_treatment(treatment_quality)
        
        # Treatment is crucial for infections
        effectiveness = HEALING_EFFECTIVENESS.get(treatment_quality, 0.5)
        severity_reduction = max(1, int(self.severity * effectiveness))
        
        self.severity = max(0, self.severity - severity_reduction)
        
        # Stop progression when treated
        self.base_progression_chance = 0


def create_condition_from_damage(damage_amount, damage_type, location=None):
    """
    Create appropriate medical conditions based on damage dealt.
    
    Args:
        damage_amount: Amount of damage dealt
        damage_type: Type of damage (bullet, blade, blunt, etc.)
        location: Body location affected
        
    Returns:
        list: List of MedicalCondition instances
    """
    conditions = []
    
    # Always create bleeding for significant damage
    threshold = BLEEDING_DAMAGE_THRESHOLDS.get('minor', 5)
    
    if damage_amount >= threshold:
        bleeding_severity = min(10, max(1, damage_amount // 3))
        conditions.append(BleedingCondition(bleeding_severity, location))
    
    # Add pain for any damage
    if damage_amount > 0:
        pain_severity = min(8, max(1, damage_amount // 2))
        conditions.append(PainCondition(pain_severity, location))
    
    # Add infection risk for penetrating wounds
    if damage_type in ['bullet', 'blade', 'pierce'] and damage_amount >= 8:
        if random.randint(1, 100) <= 25:  # 25% chance
            infection_severity = random.randint(1, 3)
            conditions.append(InfectionCondition(infection_severity, location))
    
    return conditions


class ConsciousnessSuppressionCondition(MedicalCondition):
    """
    Condition that directly suppresses consciousness levels.
    
    This represents the effects of drugs, knockout trauma, sedatives, 
    anesthesia, or other factors that directly impair consciousness
    without necessarily causing physical damage.
    """
    
    def __init__(self, severity, location=None, suppression_type="knockout"):
        super().__init__("consciousness_suppression", severity, location, tick_interval=180)  # 3 minute interval
        self.suppression_type = suppression_type  # "knockout", "sedative", "anesthesia", "trauma"
        self.consciousness_penalty = min(1.0, severity * 0.15)  # Up to 1.5 consciousness reduction at severity 10
        
    def tick_effect(self, character):
        """Consciousness suppression naturally diminishes over time."""
        from world.combat.constants import SPLATTERCAST_CHANNEL
        
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        
        # Natural recovery from consciousness suppression 
        # Different types recover at different rates
        recovery_rates = {
            "knockout": 25,      # Fast recovery from blunt trauma
            "sedative": 15,      # Moderate recovery from drugs  
            "anesthesia": 10,    # Slower recovery from medical anesthesia
            "trauma": 20         # Moderate recovery from head trauma
        }
        
        recovery_chance = recovery_rates.get(self.suppression_type, 20)
        
        if random.randint(1, 100) <= recovery_chance:
            self.severity = max(0, self.severity - 1)
            # Recalculate consciousness penalty
            self.consciousness_penalty = min(1.0, self.severity * 0.15)
            splattercast.msg(f"CONSCIOUSNESS_RECOVERY: {character.key} {self.suppression_type} severity reduced to {self.severity} (penalty: {self.consciousness_penalty:.2f})")
            
    def should_end(self):
        """Consciousness suppression ends when severity reaches 0."""
        return self.severity <= 0
        
    def get_consciousness_penalty(self):
        """Return direct consciousness penalty from this condition."""
        return self.consciousness_penalty
        
    def apply_treatment(self, treatment_quality="adequate"):
        """Apply medical treatment to consciousness suppression."""
        super().apply_treatment(treatment_quality)
        
        # Medical treatment can help with some types of suppression
        if self.suppression_type in ["sedative", "anesthesia"]:
            effectiveness = HEALING_EFFECTIVENESS.get(treatment_quality, 0.5)
            severity_reduction = max(1, int(self.severity * effectiveness))
            self.severity = max(0, self.severity - severity_reduction)
            self.consciousness_penalty = min(1.0, self.severity * 0.15)
        
    def to_dict(self):
        """Serialize condition for persistence."""
        data = super().to_dict()
        data["suppression_type"] = self.suppression_type
        data["consciousness_penalty"] = self.consciousness_penalty
        return data
        
    @classmethod
    def from_dict(cls, data):
        """Deserialize condition from persistence."""
        condition = cls(
            data.get("severity", 1),
            data.get("location"),
            data.get("suppression_type", "knockout")
        )
        condition.consciousness_penalty = data.get("consciousness_penalty", 0.15)
        condition.max_severity = data.get("max_severity", condition.severity)
        condition.tick_interval = data.get("tick_interval", 180)
        condition.requires_ticker = data.get("requires_ticker", True)
        condition.treated = data.get("treated", False)
        return condition


def remove_condition_by_type(character, condition_type):
    """
    Remove all conditions of a specific type from character.
    
    Args:
        character: Character to remove conditions from
        condition_type: Type of condition to remove
    """
    if not hasattr(character, 'medical_state'):
        return
        
    medical_state = character.medical_state
    conditions_to_remove = [c for c in medical_state.conditions if c.condition_type == condition_type]
    
    for condition in conditions_to_remove:
        medical_state.conditions.remove(condition)
        condition.end_condition(character)


def set_infection_environmental_risk(character, modifier, reason="environmental conditions"):
    """
    Modify infection progression risk for environmental conditions.
    
    Args:
        character: Character to modify infection risk for
        modifier: Risk multiplier (1.0 = normal, 3.0 = high risk like sewers, 0.5 = low risk like sterile)
        reason: Description for debug logging
        
    Examples:
        set_infection_environmental_risk(character, 3.0, "walking through sewers")
        set_infection_environmental_risk(character, 0.3, "sterile medical facility")
        set_infection_environmental_risk(character, 5.0, "toxic waste exposure")
    """
    if not hasattr(character, 'medical_state'):
        return
        
    from world.combat.constants import SPLATTERCAST_CHANNEL
    from evennia.comms.models import ChannelDB
    
    medical_state = character.medical_state
    infection_conditions = [c for c in medical_state.conditions if c.condition_type == "infection"]
    
    if infection_conditions:
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        for condition in infection_conditions:
            condition.set_environmental_modifier(modifier)
        
        splattercast.msg(f"INFECTION_ENV_RISK: {character.key} infection risk set to {modifier}x due to {reason}")
    # If no infections, the modifier would apply to future infections created in this environment
