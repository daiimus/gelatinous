"""Severance helpers — single source of truth for cut-point computation
and sutured-stump bookkeeping.

The picker (``CmdOperate._list_severed_locations``), the runtime suture
verb (``_resolve_suture``), and the wound renderer
(``get_character_wounds``) all need to agree on three things:

1. Which body containers are currently carrying a severed organ.
2. Which of those containers count as a *cut point* — the canonical
   single entry per severance, after the head cluster (face / neck /
   eyes / ears / hair-or-fur / snout) collapses into ``head`` and
   downstream limb chain pieces collapse into the chain root.
3. Which cut points have already been sutured, including the legacy
   list-shaped storage from earlier PRs.

Pre-consolidation each consumer answered these in its own way (three
copies of the cluster + chain filter, three copies of the
``hasattr(raw, "keys")`` backward-compat shim).  This module owns the
answer; the consumers now ask.
"""

from __future__ import annotations


# ---------------------------------------------------------------------
# Sutured-stump storage shape
# ---------------------------------------------------------------------


def normalize_sutured_stumps(target) -> dict:
    """Return ``target.db.sutured_stumps`` as a ``{location: outcome}`` dict.

    Two storage shapes ever land here:

    * **Current** — dict keyed by cut-point location, valued by the
      suture-roll outcome (``"success"`` / ``"partial"`` /
      ``"failure"``).
    * **Legacy** — flat list of cut-point locations from before the
      outcome-flavoured renderer landed.  Each entry is imported as
      ``"success"`` outcome (matches the implicit flavour the older
      ``treated`` stage subset rendered).

    ``None`` and missing ``db`` resolve to an empty dict.  The returned
    dict is a fresh copy; callers can mutate freely without affecting
    the stored Attribute.
    """
    raw = getattr(getattr(target, "db", None), "sutured_stumps", None)
    if raw is None:
        return {}
    if hasattr(raw, "keys"):
        return dict(raw)
    return {loc: "success" for loc in raw}


# ---------------------------------------------------------------------
# Severed-container set
# ---------------------------------------------------------------------


def compute_severed_containers(target) -> set:
    """Return the set of containers carrying any severed organ on
    ``target``.

    A severed organ has ``wound_stage="severed"`` AND
    ``current_hp <= 0`` — both gates so a partially-zeroed organ
    isn't promoted to a severance.  ``sever_character_body`` is the
    only writer that sets both fields together.
    """
    state = getattr(target, "medical_state", None)
    if state is None or not hasattr(state, "organs"):
        return set()
    out = set()
    for organ in state.organs.values():
        if (getattr(organ, "wound_stage", None) == "severed"
                and getattr(organ, "current_hp", 0) <= 0):
            container = getattr(organ, "container", None)
            if container:
                out.add(container)
    return out


# ---------------------------------------------------------------------
# Cut-point computation
# ---------------------------------------------------------------------


def compute_cut_points(target) -> set:
    """Return the set of cut-point locations on ``target``.

    A *cut point* is the canonical single location per severance:

    * **Head-cluster collapse** — when the ``head`` container is in
      the severed set (the brain lives there and ``sever_character_body``
      always zeros it during decapitation), every cluster peer from
      ``get_species_severed_head_locations`` (``neck`` / ``left_eye`` /
      ``right_eye`` / ``left_ear`` / ``right_ear`` / face-or-snout /
      hair-or-fur, species-dependent) collapses into ``head``.
    * **Limb-chain collapse** — downstream containers whose
      ``get_species_limb_parent`` ancestor is also severed collapse
      into the chain root.  Thigh amputation surfaces as
      ``left_thigh`` only; the shin and foot ride with it.

    Returns the FULL cut-point set — callers that want only untreated
    cut points should subtract ``normalize_sutured_stumps(target)``
    keys.  This keeps the renderer (which needs every cut point) and
    the picker / runtime (which need un-sutured cut points only)
    sharing a single computation.
    """
    severed_containers = compute_severed_containers(target)
    if not severed_containers:
        return set()

    species = getattr(getattr(target, "db", None), "species", None)

    head_cluster = frozenset()
    if "head" in severed_containers:
        try:
            from world.anatomy import get_species_severed_head_locations
            head_cluster = get_species_severed_head_locations(species)
        except ImportError:
            pass

    try:
        from world.anatomy import get_species_limb_parent
        limb_parent = get_species_limb_parent(species)
    except ImportError:
        limb_parent = {}

    out = set()
    for container in severed_containers:
        # Head-cluster peers collapse into ``head``.
        if head_cluster and container in head_cluster and container != "head":
            continue
        # Limb-chain downstream collapses into the chain root.
        parent = limb_parent.get(container)
        if parent and parent in severed_containers:
            continue
        out.add(container)
    return out
