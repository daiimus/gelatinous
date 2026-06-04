"""Anatomy package.

Species-overlay data and helpers for body-location display, decay-tier
naming, per-organ presentation prose, and per-severed-part default
descriptions.  Currently ships only the ``human`` species; the
registry is structured as a minimal overlay so non-humans can be
added without refactoring corpse / severed-item / organ rendering
code.

Public surface:

* :data:`world.anatomy.species.SPECIES_DEFINITIONS`
* :func:`world.anatomy.species.get_species_part_name`
* :func:`world.anatomy.species.get_species_corpse_name`
* :func:`world.anatomy.species.get_species_corpse_description`
* :func:`world.anatomy.species.get_species_location_display`
* :func:`world.anatomy.species.get_species_organ_name`
* :data:`world.anatomy.severed_parts.SEVERED_PART_DESCRIPTIONS`
* :func:`world.anatomy.severed_parts.get_severed_part_description`
* :data:`world.anatomy.organs.ORGAN_DISPLAY`
* :func:`world.anatomy.organs.get_organ_display_name`
* :func:`world.anatomy.organs.get_organ_default_description`
* :func:`world.anatomy.conditions.format_condition_tagline`
* :func:`world.anatomy.conditions.prepend_condition_to_desc`
* :func:`world.anatomy.longdesc_tokens.substitute_pronoun_tokens`
"""

from .conditions import (
    format_condition_tagline,
    prepend_condition_to_desc,
)
from .longdesc_tokens import substitute_pronoun_tokens
from .organs import (
    BONE_ORGANS,
    ORGAN_DISPLAY,
    get_organ_default_description,
    get_organ_display_name,
)
from .severed_parts import (
    SEVERED_PART_DESCRIPTIONS,
    get_severed_part_description,
)
from .species import (
    SPECIES_DEFINITIONS,
    get_species_corpse_description,
    get_species_corpse_name,
    get_species_location_display,
    get_species_organ_name,
    get_species_part_name,
    get_species_severed_chain_name,
)

__all__ = (
    "BONE_ORGANS",
    "ORGAN_DISPLAY",
    "SEVERED_PART_DESCRIPTIONS",
    "SPECIES_DEFINITIONS",
    "format_condition_tagline",
    "get_organ_default_description",
    "get_organ_display_name",
    "get_severed_part_description",
    "get_species_corpse_description",
    "get_species_corpse_name",
    "get_species_location_display",
    "get_species_organ_name",
    "get_species_part_name",
    "get_species_severed_chain_name",
    "prepend_condition_to_desc",
    "substitute_pronoun_tokens",
)
