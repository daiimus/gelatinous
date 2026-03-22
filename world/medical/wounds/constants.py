"""
Wound Description Constants

Constants for wound stages, severity mapping, and other wound-related data.
"""

# Wound healing stages (matching the weapon message pattern)
WOUND_STAGES = [
    "fresh",      # Just inflicted, bleeding, raw
    "treated",    # Bandaged, sutured, basic medical care applied
    "healing",    # Scabbing, closing, reduced bleeding
    "destroyed",  # Internal organ completely destroyed/non-functional (permanent)
    "severed",    # Limb/appendage completely removed (permanent)
    "scarred",    # Scar formation, permanent mark (healed non-destroyed wounds)
]

# Map injury severity to wound description intensity
INJURY_SEVERITY_MAP = {
    "Light": "minor",
    "Moderate": "noticeable", 
    "Severe": "serious",
    "Critical": "grievous",
}

# Body location display mapping for wounds (dynamic - will adapt to character's anatomy)
def get_location_display_name(location, character=None):
    """
    Get the display name for a body location based on character's anatomy.
    
    Args:
        location (str): Body location key
        character: Character object (optional)
        
    Returns:
        str: Human-readable location name
    """
    # Handle legacy calling convention (character, location)
    if isinstance(location, str) is False and isinstance(character, str):
        # Swap arguments - old calling convention passed (character, location)
        character, location = location, character
    
    # Check if character has custom location names
    if character and hasattr(character, 'location_display_names'):
        custom_name = character.location_display_names.get(location)
        if custom_name:
            return custom_name
    
    # Default humanoid mappings (fallback)
    default_mappings = {
        "head": "head",
        "face": "face", 
        "chest": "chest",
        "abdomen": "abdomen",
        "back": "back",
        "left_arm": "left arm",
        "right_arm": "right arm",
        "left_hand": "left hand", 
        "right_hand": "right hand",
        "left_thigh": "left thigh",
        "right_thigh": "right thigh",
        "left_shin": "left shin",
        "right_shin": "right shin",
        "left_foot": "left foot",
        "right_foot": "right foot",
        "neck": "neck",
        "groin": "groin",
    }
    
    return default_mappings.get(location, location)

# Wound transition thresholds (days since injury)
WOUND_TRANSITION_DAYS = {
    "fresh_to_treated": 0,      # Can be treated immediately
    "treated_to_healing": 3,    # Starts healing after 3 days with treatment
    "healing_to_scarred": 14,    # Full healing after 2 weeks
    "fresh_to_healing": 7,      # Untreated wounds start healing after a week
    "fresh_to_scarred": 21,     # Untreated wounds fully heal after 3 weeks
}

# Maximum number of wound descriptions to show in longdesc
MAX_WOUND_DESCRIPTIONS = 3

# Medical color palette for bandages, instruments, etc.
MEDICAL_COLORS = {
    "bandage_color": "|W",        # White bandages
    "suture_color": "|K",         # Black stitches  
    "medical_tape_color": "|543", # Beige medical tape
    "medical_staple_color": "|555", # Silver staples
    "ice_pack_color": "|C",       # Cyan ice packs
    "compression_wrap_color": "|543", # Beige compression wraps
    "antiseptic_color": "|y",     # Yellow antiseptic
    "iodine_color": "|r",         # Red-brown iodine
}

# Keywords that trigger wound description updates
WOUND_UPDATE_TRIGGERS = [
    "take_damage",
    "heal_condition", 
    "medical_treatment",
    "time_passage",
    "wear_item",     # Clothing changes can conceal/reveal wounds
    "remove_item",   # Removing clothing can reveal wounds
]
