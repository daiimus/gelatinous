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
# WOUND CARE TREATMENT CONSTANTS (#307, PR-B stabilization channel)
# ===================================================================
#
# Roll math for wound_care application:
#
#     roll   = 3d6 + medical_effectiveness + item.effectiveness[category]
#     target = WOUND_CARE_BASE_DIFFICULTY + severity_modifier + depth_modifier
#
# Outcome thresholds mirror the procedure verbs (success / partial /
# failure).  Numbers below are placeholders for early playtesting —
# all live in this single module so balancing is one-file work.

WOUND_CARE_BASE_DIFFICULTY = 12        # Matches PROCEDURE_BASE_DIFFICULTY for parity

#: Severity modifier added to the difficulty target.  Keys map the
#: wound's string severity ("Minor" / "Moderate" / "Severe" / "Critical")
#: as set by ``_determine_severity_from_damage`` in wound rendering.
#: Unknown severities default to MODERATE.
WOUND_CARE_SEVERITY_MODIFIERS = {
    "Minor":    0,
    "Moderate": 3,
    "Severe":   6,
    "Critical": 9,
}

#: Depth modifier added when the wound is at an internal-cavity
#: container and the item lacks an internal-effectiveness rating.
#: Soft scale per design — desperate medics get diminishing returns
#: rather than outright refusal.
WOUND_CARE_DEPTH_MODIFIER = 5

#: Outcome thresholds vs final roll.  Success: full effect; partial:
#: half effect; failure: stabilization only.
WOUND_CARE_SUCCESS_THRESHOLD = 18      # >= → success
WOUND_CARE_PARTIAL_THRESHOLD = 12      # >= → partial; < → failure

#: Per-category effect amounts on success.  Numbers are knobs.
WOUND_CARE_BLEEDING_REDUCTION = 2      # severity points reduced on bleeding success
WOUND_CARE_INFECTION_REDUCTION = 2     # severity points reduced on infection success
WOUND_CARE_PAIN_REDUCTION = 3          # severity points reduced on pain success

#: Categories the wound_care dispatch resolves in parallel.  Each is
#: one roll; failure of any one is stabilization-only for that
#: category.  ``wound_healing`` is dressing-tick driven (PR-C, not
#: a per-application roll).  ``organ_repair`` is the surgical-grade
#: direct repair channel (PR-D) — instant HP refund on success,
#: gated on an open incision at the wound's container.
WOUND_CARE_PARALLEL_CATEGORIES = (
    "bleeding", "infection", "pain", "organ_repair",
)

# ===================================================================
# WOUND HEALING (DRESSING TICK) CONSTANTS (#307, PR-C)
# ===================================================================
#
# Healing is the slow-recovery channel separate from stabilization.
# An applied wound_care item registers its ``wound_healing``
# effectiveness rating on the underlying organ; the medical script's
# tick walks stabilized organs and restores HP proportional to the
# stored rating.

#: HP restored per medical tick per dressing-rate point.  Integer
#: division — a low-rated dressing (rating 1-4) lands at 0 HP/tick
#: which models the wound staying stable but not actively healing.
#: Tuned for the existing 12s medical tick.  Balance knob.
WOUND_HEALING_DIVISOR = 5

#: Minimum HP recovered per tick when any dressing is registered
#: (rating > 0).  Floor protects against integer-division-to-zero
#: for low-rated dressings — a wound stays stable AND inches back
#: even with weak dressing, just very slowly.  Set to 0 to disable
#: the floor and let only high-rated dressings heal.
WOUND_HEALING_FLOOR_HP_PER_TICK = 0

# ===================================================================
# ORGAN REPAIR (SURGICAL DIRECT) CONSTANTS (#307, PR-D)
# ===================================================================
#
# Organ repair is the surgical-grade direct channel: applying a
# deep-treatment item during an open procedure restores HP to the
# underlying organ on the spot, scaled by the item's
# ``organ_repair`` effectiveness rating.  This is the third effect
# channel under the wound_care umbrella:
#
#   * stabilization — freezes wound state (PR-B)
#   * wound_healing — slow tick HP recovery (PR-C)
#   * organ_repair  — instant HP refund per surgical application (PR-D)
#
# Gated on an open incision at the organ's container — sealant
# applied to a closed chest doesn't reach the heart.  Substance
# tolerance principle holds: the application still succeeds; the
# effect simply doesn't land.

#: HP restored per organ_repair effectiveness point on a success
#: roll.  Integer division so the math is predictable.  Sealant
#: rating 8 → 8 // ORGAN_REPAIR_DIVISOR HP per success.  Balance
#: knob — small changes produce meaningful gameplay differences.
ORGAN_REPAIR_DIVISOR = 3

#: Partial-success scaling — fraction of full HP restored on a
#: partial outcome.  Numerator divided by denominator gives the
#: scaling; expressed as a pair so balance changes don't drift
#: into floating-point territory.
ORGAN_REPAIR_PARTIAL_NUMERATOR = 1
ORGAN_REPAIR_PARTIAL_DENOMINATOR = 2

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
# Issue #356 follow-up: source of truth lives in the species registry
# at ``SPECIES_DEFINITIONS[species]["body_capacities"]``.  This global
# is derived from the human entry so existing callers keep working;
# species-aware callers use
# :func:`world.anatomy.get_species_body_capacities(species)` directly.
# The legacy ``unconscious_threshold`` / ``fatal_threshold`` dict
# values were declarative — the actual thresholds enforced by
# ``is_dead()`` / ``is_unconscious()`` read the module constants
# (``CONSCIOUSNESS_UNCONSCIOUS_THRESHOLD`` / ``BLOOD_LOSS_DEATH_THRESHOLD``)
# directly, so they are not preserved through the species derivation.
from world.anatomy.species import SPECIES_DEFINITIONS as _SPECIES_DEFINITIONS_BC
BODY_CAPACITIES = {
    k: dict(v) for k, v in (
        _SPECIES_DEFINITIONS_BC["human"].get("body_capacities") or {}
    ).items()
}
del _SPECIES_DEFINITIONS_BC

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
