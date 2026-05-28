"""Anatomy package.

Species-overlay data and helpers for body-location display, decay-tier
naming, and per-organ presentation prose.  Currently ships only the
``human`` species; the registry is structured as a minimal overlay so
non-humans can be added without refactoring corpse / severed-item /
organ rendering code.

Public surface:

* :data:`world.anatomy.species.SPECIES_DEFINITIONS`
* :func:`world.anatomy.species.get_species_part_name`
* :func:`world.anatomy.species.get_species_corpse_name`
* :func:`world.anatomy.species.get_species_location_display`
"""

from .species import (
    SPECIES_DEFINITIONS,
    get_species_corpse_name,
    get_species_location_display,
    get_species_part_name,
)

__all__ = (
    "SPECIES_DEFINITIONS",
    "get_species_corpse_name",
    "get_species_location_display",
    "get_species_part_name",
)
