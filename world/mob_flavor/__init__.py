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
  feet), wrap the body noun in braces (``{eyes}`` / ``{ears}``) so the
  collapse-when-paired renderer can singularize it if one side is lost.
* Plain prose renders verbatim.

See ``specs/IDENTITY_RECOGNITION_SPEC.md`` and ``specs/LONGDESC_SYSTEM_SPEC.md``
for the broader description rendering contract.
"""

from __future__ import annotations

from random import choice

from world.combat.constants import PAIR_MERGE_KEYS
from world.mob_flavor.longdescs import LONGDESCS
from world.mob_flavor.look_places import LOOK_PLACES
from world.mob_flavor.short_descs import SHORT_DESCS


def random_short_desc() -> str:
    """Return a random short-description template (token-bearing)."""
    return choice(SHORT_DESCS)


def random_look_place() -> str:
    """Return a random look_place string (ends with terminal punctuation)."""
    return choice(LOOK_PLACES)


def random_longdesc(slot: str) -> str | None:
    """Return a random longdesc template for ``slot``.

    ``slot`` is the data-side key — either a singular location (``"hair"``,
    ``"face"``) or a pair-key (``"eyes"``, ``"hands"``) for symmetric pairs.
    Returns ``None`` when no entries are seeded — extended anatomy and any
    new locations fall into this case until flavor data is authored.
    """
    entries = LONGDESCS.get(slot)
    if not entries:
        return None
    return choice(entries)


def apply_random_flavor(mob) -> None:
    """Fill a freshly-spawned mob with random short desc, longdescs, and
    look_place.

    For symmetric pairs (eyes, ears, arms, hands, thighs, shins, feet) the
    *same* random template is applied to both sides so the renderer's
    paired-collapse path engages (rendering as a single plural line). If
    only one side of a pair exists (extended anatomy or post-severance
    mob), the pair entry is applied to that one side. Singular locations
    are filled independently.
    """
    mob.db.desc = random_short_desc()
    mob.look_place = random_look_place()

    get_locations = getattr(mob, "get_available_locations", None)
    if get_locations is None:
        return
    available = set(get_locations())
    handled: set[str] = set()

    # Paired slots: one selection applied to both sides so they collapse.
    for pair_key, (left, right) in PAIR_MERGE_KEYS.items():
        sides_present = [loc for loc in (left, right) if loc in available]
        if not sides_present:
            continue
        entry = random_longdesc(pair_key)
        if entry is None:
            continue
        for side in sides_present:
            mob.set_longdesc(side, entry)
            handled.add(side)

    # Remaining (singular) locations — keyed in LONGDESCS by location name.
    for location in available - handled:
        entry = random_longdesc(location)
        if entry is not None:
            mob.set_longdesc(location, entry)
