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
* :func:`world.anatomy.species.get_species_location_display`
* :data:`world.anatomy.severed_parts.SEVERED_PART_DESCRIPTIONS`
* :func:`world.anatomy.severed_parts.get_severed_part_description`
"""

from .severed_parts import (
    SEVERED_PART_DESCRIPTIONS,
    get_severed_part_description,
)
from .species import (
    SPECIES_DEFINITIONS,
    get_species_corpse_name,
    get_species_location_display,
    get_species_part_name,
)

__all__ = (
    "SEVERED_PART_DESCRIPTIONS",
    "SPECIES_DEFINITIONS",
    "get_severed_part_description",
    "get_species_corpse_name",
    "get_species_location_display",
    "get_species_part_name",
)
