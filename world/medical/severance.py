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

    Two target shapes supported:

    * **Living character** — reads ``target.medical_state.organs``
      for any organ at ``wound_stage="severed"`` AND
      ``current_hp <= 0`` (both gates so a partially-zeroed organ
      isn't promoted to a severance).  ``sever_character_body`` is
      the only writer that sets both fields together.
    * **Corpse-shaped** (Corpse, SeveredHead, Appendage) — the live
      ``medical_state`` is empty post-death, so we fall back to
      ``target.db.wounds_at_death`` and treat any entry with
      ``injury_type="severed"`` as a stump.  ``apply_sever_to_corpse``
      is the writer.  Lets the suture verb detect post-death stumps
      so corpse stumps can progress to ``treated_<outcome>`` prose.
    """
    state = getattr(target, "medical_state", None)
    organs = getattr(state, "organs", None) if state is not None else None
    if organs:
        out = set()
        for organ in organs.values():
            if (getattr(organ, "wound_stage", None) == "severed"
                    and getattr(organ, "current_hp", 0) <= 0):
                container = getattr(organ, "container", None)
                if container:
                    out.add(container)
        return out

    # Corpse-shaped fallback: derive from wounds_at_death.
    db = getattr(target, "db", None)
    if db is None:
        return set()
    wounds = getattr(db, "wounds_at_death", None) or ()
    out = set()
    for wound in wounds:
        if not hasattr(wound, "get"):
            continue
        if wound.get("injury_type") == "severed":
            loc = wound.get("location")
            if loc:
                out.add(loc)
    return out


# ---------------------------------------------------------------------
# Corpse stump prose stage
# ---------------------------------------------------------------------


# Two-tier mapping between the corpse's decay tier and the severed.py
# prose stage for an unsutured stump.  Defined here so the JIT renderer
# (``Corpse.get_wound_descriptions_for_location``) and the sever-time
# writer (``apply_sever_to_corpse``) both consult the same table.
_DECAY_TO_STUMP_STAGE = {
    "fresh":    "fresh",
    "early":    "fresh",
    "moderate": "old",
    "advanced": "old",
    "skeletal": "old",
}


def stump_stage_for_corpse(corpse) -> str:
    """Return the severed.py prose stage for ``corpse``'s current
    decay tier — JIT computed.

    Falls back to ``"old"`` when the corpse lacks a decay accessor
    or returns an unknown tier (defensive — old prose is the safer
    miss; weeping prose on a long-dead corpse would be jarring).

    Consumed at render time by
    :meth:`typeclasses.corpse.Corpse.get_wound_descriptions_for_location`
    so a corpse severed when fresh and later decayed to ``advanced``
    renders the dried-stump prose on subsequent looks, without any
    write-back to the stored wound dict.  Wounds-as-time-stamped-state
    + JIT presentation: forensics-friendly contract.
    """
    decay_getter = getattr(corpse, "get_decay_stage", None)
    if not callable(decay_getter):
        return "old"
    try:
        decay_stage = decay_getter() or "fresh"
    except Exception:
        return "old"
    return _DECAY_TO_STUMP_STAGE.get(decay_stage, "old")


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
