"""What can come off THIS body -- living or dead.

One answer for every door (#3380, #3381; owner rulings 2026-09-13/14):

* **Harvest** offers an organ when the body's own species table flags it
  ``can_be_harvested`` (the harvest axis, #3068) OR the organ is a GRAFTED
  augment -- "anything installed can be uninstalled".
* **Severance** allows a container when it is in the species severable set
  OR any organ at it flags ``severable_container`` (ANATOMY_AUGMENTS §3.5).
* **Grafted vs native**: an organ is native when the body's OWN species
  table declares it (a robot's arm bone is robot anatomy, not chrome, even
  though it is inorganic -- "robots are robots"); it is grafted when the
  table does not know it (a tail, a hardpoint, a seated module) or when it
  carries augment markers the table's entry for that name does not
  (a cyber humerus keeps the canonical name ``left_humerus``).
* **Chrome doesn't rot**: a skeletal-stage body still yields its grafted
  inorganic parts; only flesh is gone.

Everything reads the SNAPSHOT (``get_organ_snapshot``), so a corpse, a
severed head or an appendage answers exactly like a living character.
Before this module the harvest rule was inlined in one command and absent
from the other and from the resolver, and corpse severability read the
species set alone at three sites while the living paths honoured the
overlay -- two doors, four implementations.
"""
from __future__ import annotations

from typing import Iterable

_AUGMENT_MARKERS = ("inorganic", "hardpoint", "module_type", "abilities",
                    "prosthetic_frame", "severable_container")


def _species_of(target):
    try:
        from world.anatomy.species import species_of
        return species_of(target)
    except Exception:  # noqa: BLE001 -- an odd target reads as unknown species
        return getattr(getattr(target, "db", None), "species", None)


def _entries(target) -> list[tuple[str, dict]]:
    """``(organ_name, entry)`` pairs from the snapshot, duck-typed on ``.get``
    (Evennia wraps persisted dicts in ``_SaverDict``)."""
    from world.medical.procedures import get_organ_snapshot
    snapshot = get_organ_snapshot(target) or {}
    organs = snapshot.get("organs") or {}
    return [(name, data) for name, data in organs.items() if hasattr(data, "get")]


def organ_spec_of(entry) -> dict:
    """The organ's own spec dict as the snapshot carries it."""
    spec = entry.get("data") if hasattr(entry, "get") else None
    return spec if hasattr(spec, "get") else {}


def is_grafted(organ_name: str, entry, species) -> bool:
    """Grafted augment (chrome / added anatomy) vs the body's native anatomy."""
    from world.anatomy.species import get_species_organs
    table = get_species_organs(species) or {}
    if organ_name not in table:
        return True                       # fitted at runtime: tail, hardpoint, module
    native = table.get(organ_name) or {}
    spec = organ_spec_of(entry)
    for marker in _AUGMENT_MARKERS:
        if spec.get(marker) and not native.get(marker):
            return True                   # canonical-name chrome on a flesh slot
    return False


def can_harvest_organ(organ_name: str, entry, species) -> bool:
    """The harvest axis OR a grafted augment."""
    from world.anatomy.species import get_organ_spec
    spec = get_organ_spec(organ_name, species) or {}
    if spec.get("can_be_harvested"):
        return True
    return is_grafted(organ_name, entry, species)


def _skeletal(target) -> bool:
    getter = getattr(target, "get_decay_stage", None)
    if not callable(getter):
        return False
    try:
        return getter() == "skeletal"
    except Exception:  # noqa: BLE001
        return False


def harvestable_organs(target) -> list[tuple[str, str]]:
    """``(organ_name, container)`` pairs a harvest door may OFFER on *target*:
    harvestable by axis or graft, not already removed, not in a severed
    container, not destroyed; on a skeletal body only bones and grafted
    inorganic parts remain. Sorted by container then name."""
    from world.anatomy.organs import BONE_ORGANS
    species = _species_of(target)
    db = getattr(target, "db", None)
    removed = set(getattr(db, "removed_organs", None) or ())
    severed = set(getattr(db, "severed_locations", None) or ())
    skeletal = _skeletal(target)
    out = []
    for name, entry in _entries(target):
        if name in removed:
            continue
        container = entry.get("container") or "?"
        if container in severed:
            continue
        if (entry.get("current_hp") or 0) <= 0:
            continue
        if not can_harvest_organ(name, entry, species):
            continue
        if skeletal and name not in BONE_ORGANS and not (
                is_grafted(name, entry, species) and organ_spec_of(entry).get("inorganic")):
            continue                       # flesh is gone; chrome doesn't rot
        out.append((name, container))
    out.sort(key=lambda nc: (nc[1], nc[0]))
    return out


def container_is_severable(target, container: str) -> bool:
    """Species set OR any organ at the container flagging ``severable_container``."""
    from world.anatomy.species import get_species_severable_containers
    species = _species_of(target)
    try:
        if container in get_species_severable_containers(species):
            return True
    except Exception:  # noqa: BLE001
        pass
    for _name, entry in _entries(target):
        if entry.get("container") == container and organ_spec_of(entry).get("severable_container"):
            return True
    return False


def severable_containers(target, *, present_only: bool = True) -> list[str]:
    """Containers that may be severed from *target* now: species set union the
    overlay, restricted (by default) to containers the snapshot actually has
    organs in, minus those already severed. Sorted."""
    from world.anatomy.species import get_species_severable_containers
    species = _species_of(target)
    try:
        candidates = set(get_species_severable_containers(species))
    except Exception:  # noqa: BLE001
        candidates = set()
    present = set()
    for _name, entry in _entries(target):
        container = entry.get("container") or ""
        if container:
            present.add(container)
        if organ_spec_of(entry).get("severable_container"):
            candidates.add(container)
    severed = set(getattr(getattr(target, "db", None), "severed_locations", None) or ())
    out = [c for c in candidates if c and c not in severed and (c in present or not present_only)]
    return sorted(out)
