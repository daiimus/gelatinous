"""
Messages module for wound descriptions.

Imports all wound message types for easy access.
"""

from . import bullet
from . import cut
from . import laceration
from . import stab
from . import blunt
from . import generic
from . import severed
from . import harvested
from . import robot
from . import synth

#: Species wound-prose packs (SPECIES_AUTHORING §wounds): a species listed
#: here NEVER falls through to human flesh prose — its pack is complete
#: across all stages. Species not listed (human, rat, ...) use the shared
#: per-injury-type modules above.
SPECIES_PACKS = {
    "robot": robot,
    "synthetic_humanoid": synth,
}


def species_pack(character):
    """The wound-prose pack for *character*'s species, or None (human
    default). Reads ``character.species`` with a ``db.species`` fallback so
    corpses (which carry species on db) resolve identically."""
    if character is None:
        return None
    species = getattr(character, "species", None)
    if not isinstance(species, str):
        species = None
    species = species or getattr(
        getattr(character, "db", None), "species", None)
    if not isinstance(species, str):
        return None
    return SPECIES_PACKS.get(species)
