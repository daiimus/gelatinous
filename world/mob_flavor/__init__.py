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
from world.mob_flavor.longdescs_robot import LONGDESCS_ROBOT
from world.mob_flavor.longdescs_synth import LONGDESCS_SYNTH
from world.mob_flavor.look_places import LOOK_PLACES
from world.mob_flavor.look_places_rat import LOOK_PLACES_RAT
from world.mob_flavor.look_places_robot import LOOK_PLACES_ROBOT
from world.mob_flavor.look_places_synth import LOOK_PLACES_SYNTH
from world.mob_flavor.short_descs import SHORT_DESCS
from world.mob_flavor.short_descs_rat import SHORT_DESCS_RAT
from world.mob_flavor.short_descs_robot import SHORT_DESCS_ROBOT
from world.mob_flavor.short_descs_synth import SHORT_DESCS_SYNTH


# Species → data-table mappings. New species: add an entry per axis.
_SHORT_DESCS_BY_SPECIES: dict[str, list[str]] = {
    "human": SHORT_DESCS,
    "rat":   SHORT_DESCS_RAT,
    "robot": SHORT_DESCS_ROBOT,
    "synthetic_humanoid": SHORT_DESCS_SYNTH,
}

_LOOK_PLACES_BY_SPECIES: dict[str, list[str]] = {
    "human": LOOK_PLACES,
    "rat":   LOOK_PLACES_RAT,
    "robot": LOOK_PLACES_ROBOT,
    "synthetic_humanoid": LOOK_PLACES_SYNTH,
}

_LONGDESCS_BY_SPECIES: dict[str, dict[str, list[str]]] = {
    "human": LONGDESCS,
    "rat":   LONGDESCS_RAT,
    "robot": LONGDESCS_ROBOT,
    "synthetic_humanoid": LONGDESCS_SYNTH,
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


#: Build tags a longdesc line may be marked with. A line tagged for a
#: build is only offered to that kind of body; an UNTAGGED line is
#: universal and always eligible. That asymmetry is deliberate — most
#: of the catalogue (moles, grit, posture, old scars) is true of any
#: body, and only the ~20% that assert a shape need constraining.
BUILD_TAGS = ("slight", "lean", "athletic", "average", "stocky", "heavyset")

#: Builds that read as close enough to swap for one another when a
#: slot has nothing tagged for the exact build.
BUILD_NEIGHBOURS = {
    "slight": ("lean",),
    "lean": ("slight", "athletic"),
    "athletic": ("lean", "average"),
    "average": ("athletic", "stocky"),
    "stocky": ("average", "heavyset"),
    "heavyset": ("stocky",),
}


def _eligible(entries, build):
    """Lines this body could plausibly own.

    Entries may be plain strings (universal) or ``(tag, line)`` pairs.
    A tagged line is offered only to its build or a neighbouring one;
    untagged lines are always in the pool. Falls back to the whole
    pool rather than ever returning empty — a slightly wrong line
    beats a blank body.
    """
    if not entries:
        return []
    plain, tagged = [], []
    for item in entries:
        if isinstance(item, (tuple, list)) and len(item) == 2:
            tagged.append((str(item[0]).lower(), item[1]))
        else:
            plain.append(item)
    if not tagged:
        return plain
    build = (build or "").lower()
    near = set(BUILD_NEIGHBOURS.get(build, ())) | ({build} if build else set())
    fitting = [line for tag, line in tagged if tag in near]
    pool = plain + fitting
    return pool or plain or [line for _tag, line in tagged]


def random_longdesc(slot: str, species=None, sex=None, build=None) -> str | None:
    """Return a random longdesc template for ``slot``.

    ``slot`` is the data-side key — either a singular location (``"hair"``,
    ``"face"``, ``"snout"``) or a pair-key (``"eyes"``, ``"forelegs"``)
    for symmetric pairs. Returns ``None`` when no entries are seeded for
    this species — extended anatomy and any new locations fall into this
    case until flavor data is authored.

    Entries may also be ``(build_tag, line)`` pairs — see ``_eligible``.
    A heavyset body is never handed "thin enough that the iliac crest is
    sharply visible", which it was until now, in the same breath as its
    own sdesc calling it heavyset.

    A slot's entries may be a flat list (unisex) or a **sex-keyed dict**
    (``{"male": [...], "female": [...], "any": [...]}``) for anatomy where
    gender-correct prose matters (chest, groin). Resolution: the mob's
    sex → the ``"any"`` pool → all pools flattened (never empty-handed).
    """
    table = _LONGDESCS_BY_SPECIES[_resolve_species(species)]
    entries = table.get(slot)
    if isinstance(entries, dict):
        pool = entries.get(sex) or entries.get("any")
        if not pool:
            pool = [line for lines in entries.values() for line in lines]
        entries = pool
    entries = _eligible(entries, build)
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
        entry = random_longdesc(pair_key, species,
                                sex=getattr(mob, "sex", None),
                                build=getattr(mob, "build", None))
        if entry is None:
            continue
        for side in sides_present:
            mob.set_longdesc(side, entry)
            handled.add(side)

    # Remaining (singular) locations — keyed in the species' longdesc
    # table by location name.
    for location in available - handled:
        entry = random_longdesc(location, species,
                                sex=getattr(mob, "sex", None),
                                build=getattr(mob, "build", None))
        if entry is not None:
            mob.set_longdesc(location, entry)


def fill_missing_longdescs(character) -> int:
    """Describe the slots a character has left blank, and only those.

    The counterpart to `apply_random_flavor` for people who are already
    written: it never overwrites an authored line, never touches the
    short desc (that is the glance, and it is somebody's prose), and
    only fills what is empty. Authored cast members typically have head
    and hands and nothing below the neck — this gives them a body
    without taking away a face.

    Returns the number of slots filled.
    """
    species = getattr(character.db, "species", None) or "human"
    existing = {k: v for k, v in (character.longdesc or {}).items() if v}
    get_locations = getattr(character, "get_available_locations", None)
    if get_locations is None:
        return 0
    available = set(get_locations())
    sex = getattr(character, "sex", None)
    build = getattr(character, "build", None)
    filled = 0

    pair_keys = get_species_pair_keys(species)
    handled: set[str] = set()
    for pair_key, (left, right) in pair_keys.items():
        sides = [loc for loc in (left, right) if loc in available]
        blank = [loc for loc in sides if loc not in existing]
        handled.update(sides)
        if not blank:
            continue
        entry = random_longdesc(pair_key, species, sex=sex, build=build)
        if entry is None:
            continue
        for side in blank:
            character.set_longdesc(side, entry)
            filled += 1

    for location in available - handled:
        if location in existing:
            continue
        entry = random_longdesc(location, species, sex=sex, build=build)
        if entry is not None:
            character.set_longdesc(location, entry)
            filled += 1
    return filled

