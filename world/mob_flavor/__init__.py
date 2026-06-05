"""Mob flavor data layer — random short descriptions, longdescs, and
look_place strings for spawned NPCs.

Designed to mirror ``world/combat/messages/`` in shape: each data axis is a
flat list (or dict of lists) that grows by appending entries. The public API
is the small set of getters below; ``apply_random_flavor(mob)`` is the
one-call convenience for ``CmdSpawnMob``.

Token conventions inherited from the longdesc/short-desc renderers:

* ``{their}`` / ``{they}`` / ``{them}`` / ``{theirs}`` / ``{themselves}``
  resolve per-observer to the mob's apparent gender. Capitalize the token
  (``{Their}``) to capitalize the resolved word.
* For symmetric paired locations (eyes, ears, arms, hands, thighs, shins,
  feet for humans; eyes, ears, forelegs, forepaws, hindlegs, hindpaws for
  rats; etc.), wrap the body noun in braces (``{eyes}`` / ``{forelegs}``)
  so the collapse-when-paired renderer can singularize it if one side is
  lost.
* Plain prose renders verbatim.

Species awareness (#356 follow-up): the getters take an optional
``species`` argument and dispatch to species-keyed data tables.
Unknown / None falls back to ``"human"`` so existing call sites keep
working unchanged.

See ``specs/IDENTITY_RECOGNITION_SPEC.md`` and ``specs/LONGDESC_SYSTEM_SPEC.md``
for the broader description rendering contract.
"""

from __future__ import annotations

from random import choice

from world.anatomy import get_species_pair_keys
from world.mob_flavor.longdescs import LONGDESCS
from world.mob_flavor.longdescs_rat import LONGDESCS_RAT
from world.mob_flavor.look_places import LOOK_PLACES
from world.mob_flavor.look_places_rat import LOOK_PLACES_RAT
from world.mob_flavor.short_descs import SHORT_DESCS
from world.mob_flavor.short_descs_rat import SHORT_DESCS_RAT


# Species → data-table mappings. New species: add an entry per axis.
_SHORT_DESCS_BY_SPECIES: dict[str, list[str]] = {
    "human": SHORT_DESCS,
    "rat":   SHORT_DESCS_RAT,
}

_LOOK_PLACES_BY_SPECIES: dict[str, list[str]] = {
    "human": LOOK_PLACES,
    "rat":   LOOK_PLACES_RAT,
}

_LONGDESCS_BY_SPECIES: dict[str, dict[str, list[str]]] = {
    "human": LONGDESCS,
    "rat":   LONGDESCS_RAT,
}


def _resolve_species(species):
    """Fall back to ``human`` when species is unknown / None."""
    return species if species in _SHORT_DESCS_BY_SPECIES else "human"


def random_short_desc(species=None) -> str:
    """Return a random short-description template (token-bearing)."""
    table = _SHORT_DESCS_BY_SPECIES[_resolve_species(species)]
    return choice(table)


def random_look_place(species=None) -> str:
    """Return a random look_place string (ends with terminal punctuation)."""
    table = _LOOK_PLACES_BY_SPECIES[_resolve_species(species)]
    return choice(table)


def random_longdesc(slot: str, species=None) -> str | None:
    """Return a random longdesc template for ``slot``.

    ``slot`` is the data-side key — either a singular location (``"hair"``,
    ``"face"``, ``"snout"``) or a pair-key (``"eyes"``, ``"forelegs"``)
    for symmetric pairs. Returns ``None`` when no entries are seeded for
    this species — extended anatomy and any new locations fall into this
    case until flavor data is authored.
    """
    table = _LONGDESCS_BY_SPECIES[_resolve_species(species)]
    entries = table.get(slot)
    if not entries:
        return None
    return choice(entries)


def apply_random_flavor(mob) -> None:
    """Fill a freshly-spawned mob with random short desc, longdescs, and
    look_place.

    Species-aware: reads ``mob.db.species`` and dispatches to the matching
    flavor tables. Unknown species fall back to ``"human"`` data, which
    is generally wrong for non-humans but keeps the call safe.

    For symmetric pairs (eyes / ears / arms / hands / thighs / shins /
    feet for humans; eyes / ears / forelegs / forepaws / hindlegs /
    hindpaws for rats) the *same* random template is applied to both
    sides so the renderer's paired-collapse path engages (rendering as
    a single plural line). If only one side of a pair exists (extended
    anatomy or post-severance mob), the pair entry is applied to that
    one side. Singular locations are filled independently.
    """
    species = getattr(mob.db, "species", None) or "human"

    mob.db.desc = random_short_desc(species)
    mob.look_place = random_look_place(species)

    get_locations = getattr(mob, "get_available_locations", None)
    if get_locations is None:
        return
    available = set(get_locations())
    handled: set[str] = set()

    # Paired slots — species-aware (rats pair forelegs/hindlegs/etc.,
    # not arms/thighs).  One selection applied to both sides so they
    # collapse.
    pair_keys = get_species_pair_keys(species)
    for pair_key, (left, right) in pair_keys.items():
        sides_present = [loc for loc in (left, right) if loc in available]
        if not sides_present:
            continue
        entry = random_longdesc(pair_key, species)
        if entry is None:
            continue
        for side in sides_present:
            mob.set_longdesc(side, entry)
            handled.add(side)

    # Remaining (singular) locations — keyed in the species' longdesc
    # table by location name.
    for location in available - handled:
        entry = random_longdesc(location, species)
        if entry is not None:
            mob.set_longdesc(location, entry)
