"""
Medical System Constants

All constants used throughout the medical system, organized by category
for easy maintenance and modification. These values are designed to be
balanced during implementation and testing.

Following the specification from HEALTH_AND_SUBSTANCE_SYSTEM_SPEC.md
"""

# ===================================================================
# DEATH/UNCONSCIOUSNESS THRESHOLDS
# ===================================================================

# Blood loss and consciousness thresholds
BLOOD_LOSS_DEATH_THRESHOLD = 85        # Placeholder - needs balancing
CONSCIOUSNESS_UNCONSCIOUS_THRESHOLD = 30  # Placeholder - needs balancing

# Hit weight distribution (combat handler integration)
HIT_WEIGHT_VERY_RARE = 2              # Brain, spinal cord
HIT_WEIGHT_RARE = 8                   # Eyes, ears, jaw, neck  
HIT_WEIGHT_UNCOMMON = 15              # Heart, lungs, organs, hands
HIT_WEIGHT_COMMON = 25                # Arms, legs, major limbs

# Pain/Consciousness Modifiers
PAIN_UNCONSCIOUS_THRESHOLD = 80       # High pain causes unconsciousness
PAIN_CONSCIOUSNESS_MODIFIER = 0.5     # How much pain affects consciousness

# ===================================================================
# TREATMENT SUCCESS MODIFIERS
# ===================================================================

BASE_TREATMENT_SUCCESS = 50           # Base % before stat modifiers
STAT_MODIFIER_SCALING = 5             # Points per stat level
TOOL_EFFECTIVENESS_SCALING = 10       # Effectiveness points per tool quality

# Medical Treatment Success Constants (Phase 2)
MEDICAL_TREATMENT_BASE_DIFFICULTY = 12  # Base d20 target for medical treatments
PARTIAL_SUCCESS_MARGIN = 3            # How close to success counts as partial

# ===================================================================
# MEDICAL RESOURCE CONSTANTS
# ===================================================================

BANDAGE_EFFECTIVENESS = 15            # HP healed per bandage
SURGERY_BASE_DIFFICULTY = 75          # Base difficulty for surgery
INFECTION_CHANCE_BASE = 10            # Base infection chance %

# ===================================================================
# MEDICAL CONDITION TICKER CONSTANTS (Phase 2.6)
# ===================================================================

# Ticker intervals for different condition types
COMBAT_TICK_INTERVAL = 6              # Combat speed (matches combat rounds)
SEVERE_BLEEDING_INTERVAL = 12         # 2 combat rounds - balanced threat
MEDICAL_TICK_INTERVAL = 60            # Medical progression speed

# Condition type to ticker interval mapping
CONDITION_INTERVALS = {
    "burning": COMBAT_TICK_INTERVAL,           # 6s - immediate tactical threat
    "acid_exposure": COMBAT_TICK_INTERVAL,     # 6s - immediate tactical threat  
    "severe_bleeding": SEVERE_BLEEDING_INTERVAL, # 12s - significant but manageable
    "minor_bleeding": MEDICAL_TICK_INTERVAL,   # 60s - natural clotting
    "wound_healing": MEDICAL_TICK_INTERVAL,    # 60s - progression over time
    "infection": MEDICAL_TICK_INTERVAL,        # 60s - slow development
    "pain": MEDICAL_TICK_INTERVAL              # 60s - gradual reduction
}

# Condition severity thresholds based on damage amounts
BLEEDING_DAMAGE_THRESHOLDS = {
    "severe": 20,     # >20 damage = severe bleeding (12s ticks)
    "minor": 10       # >10 damage = minor bleeding (60s ticks)
}

# Condition creation triggers by injury type
CONDITION_TRIGGERS = {
    "bullet": ["bleeding"],
    "stab": ["bleeding"], 
    "cut": ["bleeding"],
    "burn": ["burning"],
    "acid": ["acid_exposure"],
    "blunt": []  # Blunt trauma typically doesn't cause bleeding
}

# Tool effectiveness modifiers - Phase 2 implementation
TOOL_EFFECTIVENESS_MODIFIERS = {
    # To be defined in Phase 2 - tool appropriateness table
    # Example: {"blood_bag": {"bleeding": -2, "fracture": +5}, ...}
    # Negative = easier, Positive = harder
    "placeholder": "to_be_defined_in_phase_2"
}

# Medical condition progression constants
BLOOD_LOSS_PER_SEVERITY = {
    1: 0.5,   # Minor bleeding - 0.5% blood loss per tick
    2: 1.0,   # Light bleeding - 1% blood loss per tick  
    3: 1.5,   # Moderate bleeding - 1.5% blood loss per tick
    4: 2.0,   # Heavy bleeding - 2% blood loss per tick
    5: 3.0,   # Severe bleeding - 3% blood loss per tick
    6: 4.0,   # Critical bleeding - 4% blood loss per tick
    7: 5.0,   # Arterial bleeding - 5% blood loss per tick
    8: 6.0,   # Massive bleeding - 6% blood loss per tick
    9: 8.0,   # Catastrophic bleeding - 8% blood loss per tick
    10: 10.0  # Fatal bleeding - 10% blood loss per tick
}

# Treatment effectiveness by quality
HEALING_EFFECTIVENESS = {
    "poor": 0.3,      # Makeshift treatment
    "average": 0.5,   # Basic medical care
    "good": 0.7,      # Competent treatment
    "excellent": 0.9  # Expert medical care
}

# Injury severity multipliers (for future use)
INJURY_SEVERITY_MULTIPLIERS = {
    "minor": 1.0,
    "moderate": 1.5, 
    "severe": 2.0,
    "critical": 3.0
}

# ===================================================================
# ORGAN SYSTEM CONSTANTS
# ===================================================================

# Hit weight descriptors mapped to numerical values
HIT_WEIGHTS = {
    "very_rare": HIT_WEIGHT_VERY_RARE,      # Brain, spinal cord
    "rare": HIT_WEIGHT_RARE,                # Eyes, ears, jaw, neck
    "uncommon": HIT_WEIGHT_UNCOMMON,        # Heart, lungs, organs, hands
    "common": HIT_WEIGHT_COMMON             # Arms, legs, major limbs
}

# Contribution descriptors for organs to body capacities
CONTRIBUTION_VALUES = {
    "total": 1.0,       # 100% - loss means complete loss of capacity
    "major": 0.5,       # 50% - significant contribution
    "moderate": 0.25,   # 25% - moderate contribution  
    "minor": 0.05,      # 5% - minor contribution
}

# ===================================================================
# BODY CAPACITIES SYSTEM
# ===================================================================

# Core body capacities that organs contribute to
BODY_CAPACITIES = {
    # Vital Capacities - Loss causes death or unconsciousness
    "consciousness": {
        "organs": ["brain"],
        "modifiers": ["pain", "blood_pumping", "breathing", "blood_filtration"],
        "unconscious_threshold": CONSCIOUSNESS_UNCONSCIOUS_THRESHOLD,
        "effect": "unconscious_flag",
        "description": "Difference between functioning PC and unconscious state"
    },
    "blood_pumping": {
        "organs": ["heart"],
        "fatal_threshold": 0.0,
        "directly_fatal": True,
        "affects": ["consciousness", "moving"],
        "description": "Circulation of blood through body - zero equals death"
    },
    "breathing": {
        "organs": ["left_lung", "right_lung"],
        "fatal_threshold": 0.0,  # Death if both lungs lost
        "organ_contribution": 0.5,  # Each lung contributes 50%
        "affects": ["consciousness", "moving"]
    },
    "digestion": {
        "organs": ["liver", "stomach"],
        "liver_contribution": 1.0,   # Liver is primary
        "stomach_contribution": 0.5,  # Stomach is secondary
        "fatal_threshold": 0.0  # Death if liver lost
    },
    "neck_integrity": {
        # Decapitation gate. The cervical spine bundles the airway, the
        # great vessels, and the spinal cord at the neck; severing it is
        # immediately fatal. Modeled as its own vital capacity (rather
        # than folding into "breathing") so destruction reads as a clean
        # decapitation death without perturbing the lungs' contribution
        # math. See is_dead() in core.py and combat-sever Phase A (#243).
        "organs": ["cervical_spine"],
        "fatal_threshold": 0.0,
        "directly_fatal": True,
        "affects": ["consciousness", "breathing", "moving"],
        "description": "Integrity of the neck - zero equals decapitation/death"
    },
    
    # Blood Loss System
    "blood_loss": {
        "source": "bleeding_injuries",
        "fatal_threshold": BLOOD_LOSS_DEATH_THRESHOLD,
        "directly_fatal": True,
        "description": "Blood loss kills - exact threshold uses constants"
    },
    
    # Functional Capacities - Loss reduces effectiveness but not fatal
    "sight": {
        "organs": ["left_eye", "right_eye"],
        "organ_contribution": 0.5,  # Each eye contributes 50% 
        "affects": ["shooting_accuracy", "melee_hit_chance", "work_speed"],
        "total_loss_penalty": "blindness"
    },
    "hearing": {
        "organs": ["left_ear", "right_ear"],
        "organ_contribution": 0.5,
        "affects": ["trade_price_improvement"],
        "total_loss_penalty": "deafness"
    },
    "moving": {
        "organs": ["thoracolumbar_spine", "pelvis", "left_femur", "right_femur", "left_tibia", "right_tibia", 
                  "left_metatarsals", "right_metatarsals"],
        "thoracolumbar_spine_contribution": 1.0,    # Spine damage = paralysis
        "pelvis_contribution": 1.0,   # Essential for walking
        "femur_contribution": 0.4,    # Each femur contributes 40%
        "tibia_contribution": 0.4,    # Each tibia contributes 40%
        "metatarsal_contribution": 0.1,  # Each foot contributes 10%
        "incapacitation_threshold": 0.15,  # Below 15% = cannot move
        "affects": ["movement_speed"]
    },
    "manipulation": {
        "organs": ["left_humerus", "right_humerus", "left_metacarpals", "right_metacarpals"],
        "humerus_contribution": 0.4,     # Each humerus contributes 40%
        "metacarpal_contribution": 0.2,  # Each hand contributes 20%
        "affects": ["work_speed", "melee_accuracy"]
    },
    "talking": {
        "organs": ["jaw", "tongue"],
        "affects": ["social_impact"],
        "total_loss_effects": ["cannot_negotiate", "social_penalty"]
    },
    "eating": {
        "organs": ["jaw", "tongue"],
        "jaw_primary": True,
        "affects": ["nutrition_efficiency"]
    },
    "blood_filtration": {
        "organs": ["left_kidney", "right_kidney"],
        "organ_contribution": 0.5,  # Each kidney contributes 50%
        "affects": ["disease_resistance", "consciousness"],
        "total_loss_fatal": True
    }
}

# Capacities whose total loss kills or incapacitates the character. This is the
# single source of truth for "what makes a body location vital": the union of
# the capacities is_dead() enforces (blood_pumping, breathing, digestion,
# neck_integrity) plus consciousness (brain). _get_vital_locations() maps each
# of these capacities' organs to their containers to build the vital-location
# set used by the combat hit-location bias. Keep in sync with is_dead() in
# world/medical/core.py.
LETHAL_CAPACITY_NAMES = (
    "blood_pumping",
    "breathing",
    "digestion",
    "neck_integrity",
    "consciousness",
)

# ===================================================================
# ORGAN DEFINITIONS
# ===================================================================
#
# Issue #356 Phase 1: the canonical source of truth for the organ
# table now lives in the species registry
# (``world.anatomy.species.SPECIES_DEFINITIONS[species]["organs"]``).
# This global constant is derived from the human entry so existing
# callers that import ``ORGANS`` keep working unchanged for human
# characters.  Non-humans (rat, etc.) are constructed via
# :func:`world.anatomy.get_species_organs` directly — that function
# returns a species-aware organ table without going through this
# human-only alias.
from world.anatomy.species import SPECIES_DEFINITIONS as _SPECIES_DEFINITIONS
ORGANS = dict(_SPECIES_DEFINITIONS["human"].get("organs") or {})
del _SPECIES_DEFINITIONS

# ===================================================================
# INJURY TYPES AND MEDICAL CONDITIONS
# ===================================================================

# Different types of damage that can occur
INJURY_TYPES = {
    "cut": {
        "pain_per_damage": "low",
        "bleed_rate": "moderate", 
        "infection_chance": "low",
        "scar_chance": "low",
        "healing_time": "moderate",
        "treatment_difficulty": "easy",
        "description": "Clean cuts from blades or sharp objects"
    },
    "burn": {
        "pain_per_damage": "high",
        "bleed_rate": "minimal",
        "infection_chance": "high", 
        "scar_chance": "high",
        "healing_time": "slow",
        "treatment_difficulty": "moderate",
        "permanent_damage_chance": "moderate",
        "description": "Fire, heat, or chemical burns"
    },
    "blunt": {
        "pain_per_damage": "moderate",
        "bleed_rate": "minimal",
        "fracture_chance": "moderate",
        "internal_damage_chance": "high",
        "healing_time": "slow",
        "treatment_difficulty": "easy",
        "description": "Crushing, impact, or bludgeoning damage"
    },
    "bullet": {
        "pain_per_damage": "moderate", 
        "bleed_rate": "severe",
        "penetration_chance": "high",
        "fragmentation_chance": "low",
        "infection_chance": "moderate",
        "healing_time": "slow",
        "treatment_difficulty": "hard",
        "description": "Projectile wounds from firearms"
    },
    "stab": {
        "pain_per_damage": "low",
        "bleed_rate": "severe",
        "organ_damage_chance": "high",
        "infection_chance": "moderate", 
        "healing_time": "moderate",
        "treatment_difficulty": "moderate",
        "description": "Deep puncture wounds from thrusting weapons"
    },
    "laceration": {
        "pain_per_damage": "high",
        "bleed_rate": "high",
        "infection_chance": "high",
        "scar_chance": "very_high", 
        "healing_time": "slow",
        "treatment_difficulty": "hard",
        "description": "Ragged tears from claws, shrapnel, or serrated weapons"
    }
}
