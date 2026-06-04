"""
Wound Description System

Phase 2.4 implementation for wound descriptions and longdesc integration.
Provides automatic wound descriptions that change based on healing stage,
respect clothing concealment, and integrate with character longdesc.

Key Features:
- Multiple description variants per injury type and healing stage
- Red color coding for fresh wounds (|R....|n)
- Clothing/armor concealment system
- Concise single-line summaries when a location carries multiple wounds
- Integration with medical system and longdesc

Usage:
    from world.medical.wounds import (
        append_wounds_to_longdesc,
        get_standalone_wound_description,
    )

    # Append wounds onto a location that already has a longdesc
    desc = append_wounds_to_longdesc(desc, character, location, looker)

    # Render wounds for a location with no longdesc set
    line = get_standalone_wound_description(character, location, looker)
"""

from .wound_descriptions import (
    get_wound_description,
    get_character_wounds,
)

from .longdesc_hooks import (
    append_wounds_to_longdesc,
    get_destroyed_display_locations,
    get_destroyed_locations_from_snapshot,
    get_paired_destroyed_description,
    get_paired_severed_description,
    get_standalone_wound_description,
)

from .constants import (
    WOUND_STAGES,
    INJURY_SEVERITY_MAP,
    get_location_display_name,
    MAX_WOUND_DESCRIPTIONS,
    MEDICAL_COLORS
)

# Main exports for easy import
__all__ = [
    # Core wound functions
    'get_wound_description',
    'get_character_wounds',

    # Longdesc integration hooks
    'append_wounds_to_longdesc',
    'get_destroyed_display_locations',
    'get_destroyed_locations_from_snapshot',
    'get_paired_destroyed_description',
    'get_paired_severed_description',
    'get_standalone_wound_description',

    # Constants
    'WOUND_STAGES',
    'INJURY_SEVERITY_MAP',
    'get_location_display_name',
    'MAX_WOUND_DESCRIPTIONS',
    'MEDICAL_COLORS'
]
