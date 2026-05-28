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
        "organs": ["spine", "pelvis", "left_femur", "right_femur", "left_tibia", "right_tibia", 
                  "left_metatarsals", "right_metatarsals"],
        "spine_contribution": 1.0,    # Spine damage = paralysis
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

# ===================================================================
# ORGAN DEFINITIONS
# ===================================================================

# Individual organ properties and characteristics
ORGANS = {
    # HEAD CONTAINER → ORGANS INSIDE
    "brain": {
        "container": "head", "max_hp": 10, "hit_weight": "very_rare",
        "vital": True, "capacity": "consciousness", "contribution": "total",
        "special": "damage_always_scars", "can_scar": True, "can_heal": False,
        "can_be_harvested": True
    },
    "left_eye": {
        "container": "head", "max_hp": 10, "hit_weight": "rare",
        "capacity": "sight", "contribution": "major", "disfiguring_if_lost": True,
        "damage_always_scars": True, "vulnerable_to_blunt": False,
        "can_be_harvested": True
    },
    "right_eye": {
        "container": "head", "max_hp": 10, "hit_weight": "rare",
        "capacity": "sight", "contribution": "major", "disfiguring_if_lost": True,
        "damage_always_scars": True, "vulnerable_to_blunt": False,
        "can_be_harvested": True
    },
    "left_ear": {
        "container": "head", "max_hp": 12, "hit_weight": "rare",
        "capacity": "hearing", "contribution": "major", "disfiguring_if_lost": True,
        "can_be_harvested": True
    },
    "right_ear": {
        "container": "head", "max_hp": 12, "hit_weight": "rare",
        "capacity": "hearing", "contribution": "major", "disfiguring_if_lost": True,
        "can_be_harvested": True
    },
    "tongue": {
        "container": "head", "max_hp": 20, "hit_weight": "rare",
        "capacities": ["talking", "eating"], "talking_contribution": "major",
        "eating_contribution": "major", "disfiguring_if_lost": True,
        "can_be_harvested": True
    },
    "jaw": {
        "container": "head", "max_hp": 10, "hit_weight": "rare",
        "capacities": ["talking", "eating"], "talking_contribution": "major",
        "eating_contribution": "moderate", "disfiguring_if_lost": True, "can_scar": False,
        "can_be_harvested": True
    },

    # CHEST CONTAINER → VITAL ORGANS INSIDE  
    "heart": {
        "container": "chest", "max_hp": 15, "hit_weight": "uncommon",
        "vital": True, "capacity": "blood_pumping", "contribution": "total",
        "can_be_harvested": True, "can_be_replaced": True
    },
    "left_lung": {
        "container": "chest", "max_hp": 20, "hit_weight": "uncommon",
        "capacity": "breathing", "contribution": "major", "can_be_harvested": False,
        "backup_available": True  # Can survive with one lung
    },
    "right_lung": {
        "container": "chest", "max_hp": 20, "hit_weight": "uncommon",
        "capacity": "breathing", "contribution": "major", "can_be_harvested": False,
        "backup_available": True
    },

    # ABDOMEN CONTAINER → DIGESTIVE/FILTER ORGANS INSIDE
    "liver": {
        "container": "abdomen", "max_hp": 20, "hit_weight": "uncommon",
        "vital": True, "capacity": "digestion", "contribution": "total",
        "can_be_harvested": True, "can_be_replaced": True
    },
    "left_kidney": {
        "container": "abdomen", "max_hp": 15, "hit_weight": "uncommon",
        "capacity": "blood_filtration", "contribution": "major",
        "can_be_harvested": True, "backup_available": True
    },
    "right_kidney": {
        "container": "abdomen", "max_hp": 15, "hit_weight": "uncommon",
        "capacity": "blood_filtration", "contribution": "major",
        "can_be_harvested": True, "backup_available": True
    },
    "stomach": {
        "container": "abdomen", "max_hp": 20, "hit_weight": "uncommon",
        "capacity": "digestion", "contribution": "moderate", "vital": False,
        "can_survive_loss": True
    },

    # BACK CONTAINER → STRUCTURAL ORGANS INSIDE
    "spine": {
        "container": "back", "max_hp": 25, "hit_weight": "uncommon",
        "capacity": "moving", "contribution": "total", "cannot_be_destroyed": True,
        "causes_pain_when_damaged": True, "paralysis_if_destroyed": True
    },

    # ARM BONES → MANIPULATION STRUCTURES
    "left_humerus": {
        "container": "left_arm", "max_hp": 25, "hit_weight": "common",
        "capacity": "manipulation", "contribution": "major", "can_be_destroyed": True,
        "fracture_vulnerable": True, "bone_type": "long_bone"
    },
    "right_humerus": {
        "container": "right_arm", "max_hp": 25, "hit_weight": "common",
        "capacity": "manipulation", "contribution": "major", "can_be_destroyed": True,
        "fracture_vulnerable": True, "bone_type": "long_bone"
    },

    # HAND BONES → FINE MANIPULATION STRUCTURES
    "left_metacarpals": {
        "container": "left_hand", "max_hp": 15, "hit_weight": "uncommon",
        "capacity": "manipulation", "contribution": "moderate", "can_be_destroyed": True,
        "fracture_vulnerable": True, "bone_type": "small_bones"
    },
    "right_metacarpals": {
        "container": "right_hand", "max_hp": 15, "hit_weight": "uncommon",
        "capacity": "manipulation", "contribution": "moderate", "can_be_destroyed": True,
        "fracture_vulnerable": True, "bone_type": "small_bones"
    },

    # LEG BONES → MOVEMENT STRUCTURES
    "left_femur": {
        "container": "left_thigh", "max_hp": 30, "hit_weight": "common",
        "capacity": "moving", "contribution": "major", "can_be_destroyed": True,
        "fracture_vulnerable": True, "bone_type": "long_bone"
    },
    "right_femur": {
        "container": "right_thigh", "max_hp": 30, "hit_weight": "common", 
        "capacity": "moving", "contribution": "major", "can_be_destroyed": True,
        "fracture_vulnerable": True, "bone_type": "long_bone"
    },
    "left_tibia": {
        "container": "left_shin", "max_hp": 25, "hit_weight": "common",
        "capacity": "moving", "contribution": "major", "can_be_destroyed": True,
        "fracture_vulnerable": True, "bone_type": "long_bone"
    },
    "right_tibia": {
        "container": "right_shin", "max_hp": 25, "hit_weight": "common",
        "capacity": "moving", "contribution": "major", "can_be_destroyed": True,
        "fracture_vulnerable": True, "bone_type": "long_bone"
    },

    # FOOT BONES → BALANCE/MOBILITY STRUCTURES
    "left_metatarsals": {
        "container": "left_foot", "max_hp": 20, "hit_weight": "uncommon",
        "capacity": "moving", "contribution": "minor", "can_be_destroyed": True,
        "fracture_vulnerable": True, "bone_type": "small_bones"
    },
    "right_metatarsals": {
        "container": "right_foot", "max_hp": 20, "hit_weight": "uncommon",
        "capacity": "moving", "contribution": "minor", "can_be_destroyed": True,
        "fracture_vulnerable": True, "bone_type": "small_bones"
    },

    # STRUCTURAL ORGANS FOR MOVEMENT
    "pelvis": {
        "container": "abdomen", "max_hp": 25, "hit_weight": "uncommon",
        "capacity": "moving", "contribution": "total", "vital": True
    }
}

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
