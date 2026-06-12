"""Diagnose pane for the operate chart menu.

Translates the patient's visceral medical state into clinical
dialect for the surgeon's chart pane.  Two layers:

1. **Condition rung** — ``stable`` / ``tenuous`` / ``serious`` /
   ``critical`` / ``moribund`` / ``deceased`` — derived from
   :attr:`MedicalState.blood_level`, ``consciousness``,
   ``pain_level``, and active bleeders.  Always visible to the
   surgeon inside the chart.

2. **Detected findings** — every injured organ rolls Intellect
   against its obfuscation DC; passes render as a clinical phrase
   under the rung.  Conditions (bleeding, infection) roll
   separately against the condition DC table.

The roll is cached per (physician, patient) on
``patient.db.diagnose_cache`` keyed by physician sleeve UID (or
dbref) with a 5-minute TTL.  Wound-set changes invalidate the
cache so a freshly-arrived bleeder forces a new pose on the next
chart entry.

The pane only renders inside the operate chart (PATIENT block).
The room-facing ``look`` description stays visceral — the
clinical register is the surgeon's privilege.
"""
from __future__ import annotations

import time

from world.combat.constants import (
    DIAGNOSE_CACHE_TTL_SECONDS,
    DIAGNOSE_CONDITION_DCS,
    INTERNAL_ORGAN_OBFUSCATION_MOD,
    WOUND_OBFUSCATION_BY_TYPE,
)
from world.combat.dice import roll_stat


# ===================================================================
# Constants — module-local
# ===================================================================

DIAGNOSE_CACHE_ATTR = "diagnose_cache"

# Body-cavity containers — organs whose ``display_location`` equals
# their ``container`` AND whose container is in this set count as
# internal for obfuscation purposes (no surface tell).  Sensory
# organs and limb bones with explicit ``display_location`` (face,
# left_eye, etc.) escape this check naturally.
_INTERNAL_CONTAINERS = frozenset({"head", "chest", "abdomen", "back", "neck"})

# Condition rung labels.
RUNG_DECEASED = "deceased"
RUNG_MORIBUND = "moribund"
RUNG_CRITICAL = "critical"
RUNG_SERIOUS = "serious"
RUNG_TENUOUS = "tenuous"
RUNG_STABLE = "stable"

_RUNG_COLOUR = {
    RUNG_DECEASED: "|x",
    RUNG_MORIBUND: "|R",
    RUNG_CRITICAL: "|r",
    RUNG_SERIOUS: "|y",
    RUNG_TENUOUS: "|c",
    RUNG_STABLE: "|g",
}

# Pose templates broadcast on a fresh diagnostic roll.  Generic
# enough to read across physician fictions.  The room template is
# fed to :func:`world.identity_utils.msg_room_identity` so observer
# views get the physician's per-observer display name; the actor
# receives the self-form directly.
DIAGNOSE_POSE_ROOM = (
    "{physician}'s hands move methodically over the patient, "
    "checking pulse points and listening at the ribs."
)
DIAGNOSE_POSE_SELF = (
    "Your hands move methodically over the patient, checking "
    "pulse points and listening at the ribs."
)


# ===================================================================
# Condition rung classification
# ===================================================================

def classify_condition_rung(patient) -> str:
    """Bucket the patient into one of the rung labels.

    Reads :attr:`MedicalState.blood_level` (0-100),
    ``consciousness`` (0.0-1.0), ``pain_level`` (accumulated),
    and the active condition list.  No skill gate at this stage —
    the rung is always visible to the surgeon inside the chart.

    Corpses and severed parts (no live ``medical_state``) report
    as :data:`RUNG_DECEASED` — detected by the presence of a
    ``death_time`` attribute on ``.db``, which both
    :class:`~typeclasses.corpse.Corpse` and
    :class:`~typeclasses.items.SeveredHead` stamp at creation.
    """
    state = getattr(patient, "medical_state", None)
    if state is None:
        db = getattr(patient, "db", None)
        if db is not None and getattr(db, "death_time", None) is not None:
            return RUNG_DECEASED
        return RUNG_STABLE

    is_dead = getattr(state, "is_dead", None)
    if callable(is_dead) and is_dead():
        return RUNG_DECEASED

    blood = float(getattr(state, "blood_level", 100.0))
    consciousness = float(getattr(state, "consciousness", 1.0))
    pain = float(getattr(state, "pain_level", 0.0))
    conditions = list(getattr(state, "conditions", []) or [])
    bleeders = [
        c for c in conditions
        if getattr(c, "condition_type", None) == "bleeding"
    ]

    # Moribund — actively dying.
    if blood < 30.0 or consciousness < 0.2 or len(bleeders) >= 3:
        return RUNG_MORIBUND

    # Critical — high risk of decompensation.
    if blood < 55.0 or consciousness < 0.5 or pain > 70.0 or len(bleeders) >= 2:
        return RUNG_CRITICAL

    # Serious — significant injury, compensating.
    if blood < 75.0 or consciousness < 0.75 or pain > 40.0 or bleeders:
        return RUNG_SERIOUS

    # Tenuous — minor disturbance, watch closely.
    if blood < 90.0 or pain > 15.0 or conditions:
        return RUNG_TENUOUS

    return RUNG_STABLE


# ===================================================================
# Obfuscation & wound enumeration
# ===================================================================

def _is_internal_organ(organ) -> bool:
    """An organ is internal when it lives in a body cavity and has
    no separate surface display (``display_location == container``)."""
    container = getattr(organ, "container", None)
    display = getattr(organ, "display_location", None) or container
    return container in _INTERNAL_CONTAINERS and display == container


def wound_obfuscation_dc(organ) -> int:
    """Per-organ obfuscation DC for the surgeon's Intellect roll."""
    injury_type = getattr(organ, "injury_type", None) or "generic"
    base = WOUND_OBFUSCATION_BY_TYPE.get(
        injury_type, WOUND_OBFUSCATION_BY_TYPE["generic"],
    )
    if _is_internal_organ(organ):
        base += INTERNAL_ORGAN_OBFUSCATION_MOD
    return max(0, base)


# ===================================================================
# Clinical vocabulary
# ===================================================================

# Container → general clinical region.
_REGION_BY_CONTAINER = {
    "head":        "cranial",
    "neck":        "cervical",
    "chest":       "thoracic",
    "abdomen":     "abdominal",
    "back":        "dorsal",
    "groin":       "pelvic",
    "left_arm":    "left upper-arm",
    "right_arm":   "right upper-arm",
    "left_hand":   "left hand",
    "right_hand":  "right hand",
    "left_thigh":  "left femoral",
    "right_thigh": "right femoral",
    "left_shin":   "left tibial",
    "right_shin":  "right tibial",
    "left_foot":   "left foot",
    "right_foot":  "right foot",
}

# Specific organ → clinical adjective phrase.  Wins over the
# generic container-region lookup when a wound lands on a named
# internal organ.
_ORGAN_CLINICAL = {
    "brain":               "intracranial",
    "heart":               "cardiac",
    "left_lung":           "left pulmonary",
    "right_lung":          "right pulmonary",
    "liver":               "hepatic",
    "left_kidney":         "left renal",
    "right_kidney":        "right renal",
    "stomach":             "gastric",
    "cervical_spine":      "cervical spinal",
    "thoracolumbar_spine": "thoracolumbar spinal",
    "left_eye":            "left ocular",
    "right_eye":           "right ocular",
    "left_ear":            "left auricular",
    "right_ear":           "right auricular",
    "tongue":              "lingual",
    "jaw":                 "mandibular",
    "nose":                "nasal",
    "left_humerus":        "left humeral",
    "right_humerus":       "right humeral",
    "left_femur":          "left femoral",
    "right_femur":         "right femoral",
}

# Injury type → clinical noun-phrase template.  ``{region}`` is
# substituted with the organ-specific or container-derived label.
_INJURY_PHRASE = {
    "severance":  "open avulsion of the {region}",
    "bullet":     "penetrating ballistic trauma to the {region}",
    "stab":       "penetrating sharp-force injury to the {region}",
    "cut":        "open incised wound to the {region}",
    "laceration": "ragged laceration of the {region}",
    "burn":       "thermal injury to the {region}",
    "blunt":      "blunt-force trauma to the {region}",
    "harvested":  "surgical extraction of the {region}",
    "generic":    "trauma to the {region}",
}

# Wound stage → prefix qualifier for clinical severity reading.
_STAGE_PREFIX = {
    "fresh":     "active",
    "destroyed": "non-viable",
    "treated":   "stabilised",
    "healing":   "convalescent",
    "scarred":   "resolved",
}


def _region_for_organ(organ) -> str:
    name = getattr(organ, "name", "") or ""
    container = getattr(organ, "container", "") or ""
    return (
        _ORGAN_CLINICAL.get(name)
        or _REGION_BY_CONTAINER.get(container)
        or container.replace("_", " ")
        or "unspecified"
    )


def clinical_phrase(organ) -> str:
    """Translate an injured organ into a clinical noun phrase."""
    stage = getattr(organ, "wound_stage", None) or "fresh"
    injury_type = getattr(organ, "injury_type", None) or "generic"
    region = _region_for_organ(organ)

    # Severance reads as a completed event, not an ongoing state.
    if stage == "severed" or injury_type == "severance":
        return f"amputation at the {region} site"

    base = _INJURY_PHRASE.get(injury_type, _INJURY_PHRASE["generic"]).format(
        region=region,
    )
    prefix = _STAGE_PREFIX.get(stage)
    return f"{prefix} {base}" if prefix else base


_CONDITION_PHRASE = {
    "bleeding": "active haemorrhage from the {region}",
    "infection":      "septic focus at the {region}",
}


class _WoundDictAdapter:
    """Expose a ``wounds_at_death`` entry through the same surface
    a live :class:`~world.medical.core.Organ` would, so the
    phrasing / DC helpers stay uniform across living and deceased
    subjects.

    ``wounds_at_death`` entries are dicts (or ``_SaverDict`` for
    persisted nested dicts — duck-typed via ``.get``) shaped like::

        {"injury_type": ..., "location": <container>,
         "severity": ..., "stage": "fresh" | "old" | "treated",
         "organ": <specific_organ_name>, "organ_damage": {...}}
    """

    __slots__ = ("name", "container", "display_location",
                 "injury_type", "wound_stage")

    def __init__(self, wound_dict):
        get = wound_dict.get
        location = get("location") or ""
        organ = get("organ") or ""
        self.name = organ or location
        self.container = location or organ
        self.display_location = self.container
        self.injury_type = get("injury_type") or "generic"
        stage = get("stage") or "fresh"
        # Death-snapshot wounds tagged ``old`` still carry clinical
        # significance — they're old to the decay clock but the
        # finding itself is still active.  Map to ``fresh`` so the
        # clinical phrase reads "active …" rather than dropping
        # the severity prefix entirely.
        self.wound_stage = "fresh" if stage == "old" else stage


def _condition_clinical(condition):
    """Return ``(phrase, dc)`` or ``None`` if the condition has no
    diagnose surface."""
    ctype = getattr(condition, "condition_type", None)
    if ctype not in _CONDITION_PHRASE:
        return None
    location = getattr(condition, "location", None) or ""
    region = (
        _REGION_BY_CONTAINER.get(location)
        or location.replace("_", " ")
        or "unspecified site"
    )
    phrase = _CONDITION_PHRASE[ctype].format(region=region)
    dc = DIAGNOSE_CONDITION_DCS.get(ctype, 5)
    return phrase, dc


# ===================================================================
# Roll + cache
# ===================================================================

def _iter_wound_targets(patient):
    """Yield ``(detection_key, organ_like, dc)`` for every
    diagnosable wound on the patient.

    Living patients yield from :attr:`MedicalState.organs`;
    corpses and severed body parts yield from
    ``db.wounds_at_death``, wrapped through :class:`_WoundDictAdapter`
    so the same phrasing / DC helpers work uniformly.
    """
    state = getattr(patient, "medical_state", None)
    if state is not None:
        organs = getattr(state, "organs", {}) or {}
        for organ_name, organ in organs.items():
            if not getattr(organ, "wound_stage", None):
                continue
            yield (
                f"organ:{organ_name}",
                organ,
                wound_obfuscation_dc(organ),
            )
        return

    db = getattr(patient, "db", None)
    if db is None:
        return
    wounds = getattr(db, "wounds_at_death", None) or ()
    for idx, raw in enumerate(wounds):
        if not hasattr(raw, "get"):
            continue
        adapter = _WoundDictAdapter(raw)
        if not adapter.wound_stage:
            continue
        yield (
            f"wound:{idx}",
            adapter,
            wound_obfuscation_dc(adapter),
        )


def _wound_signature(patient) -> list[str]:
    """Order-insensitive token list used to detect wound-set
    changes for cache invalidation."""
    sig: list[str] = []
    for key, organ_like, _dc in _iter_wound_targets(patient):
        stage = getattr(organ_like, "wound_stage", "") or ""
        injury = getattr(organ_like, "injury_type", "") or "generic"
        sig.append(f"{key}:{stage}:{injury}")
    state = getattr(patient, "medical_state", None)
    if state is not None:
        for c in getattr(state, "conditions", []) or []:
            ctype = getattr(c, "condition_type", None)
            if ctype in _CONDITION_PHRASE:
                loc = getattr(c, "location", None) or ""
                sig.append(f"cond:{ctype}:{loc}")
    sig.sort()
    return sig


def _physician_cache_key(physician) -> str:
    """Per-physician cache key.  Uses ``sleeve_uid`` when present
    so a re-sleeved physician still benefits from prior diagnostic
    memory of the same patient; falls back to object id otherwise."""
    db = getattr(physician, "db", None)
    uid = getattr(db, "sleeve_uid", None) if db is not None else None
    if uid:
        return f"sleeve:{uid}"
    obj_id = getattr(physician, "id", None) or id(physician)
    return f"obj:{obj_id}"


def _get_or_init_cache(patient) -> dict:
    """Return the cache dict, initialising it on patient.db if
    absent.  Duck-types ``_SaverDict`` (no ``isinstance(dict)``
    check — Evennia wraps persisted nested dicts)."""
    db = getattr(patient, "db", None)
    if db is None:
        return {}
    cache = getattr(db, DIAGNOSE_CACHE_ATTR, None)
    if cache is None:
        cache = {}
        setattr(db, DIAGNOSE_CACHE_ATTR, cache)
        cache = getattr(db, DIAGNOSE_CACHE_ATTR, cache)
    return cache


def perform_diagnose(physician, patient, *, force_reroll: bool = False) -> dict:
    """Roll Intellect against each wound's obfuscation DC.

    Caches the result per-physician on the patient.  Returns the
    cache entry with an additional ``from_cache`` boolean
    signalling whether this call hit cache (caller decides whether
    to emit the examination pose based on the flag).
    """
    cache_key = _physician_cache_key(physician)
    cache = _get_or_init_cache(patient)
    raw_entry = cache.get(cache_key) if hasattr(cache, "get") else None
    now = time.time()
    current_sig = _wound_signature(patient)

    if not force_reroll and raw_entry is not None:
        ts = (
            raw_entry.get("timestamp", 0)
            if hasattr(raw_entry, "get") else 0
        )
        prior_sig = (
            list(raw_entry.get("wound_signature", []))
            if hasattr(raw_entry, "get") else []
        )
        if (now - ts) < DIAGNOSE_CACHE_TTL_SECONDS and prior_sig == current_sig:
            return {
                "timestamp": ts,
                "wound_signature": prior_sig,
                "detected_wounds": list(raw_entry.get("detected_wounds", [])),
                "detected_conditions": list(
                    raw_entry.get("detected_conditions", [])
                ),
                "from_cache": True,
            }

    # Fresh roll.
    detected_wounds: list[str] = []
    detected_conditions: list[str] = []
    for key, _organ_like, dc in _iter_wound_targets(patient):
        if roll_stat(physician, "intellect") >= dc:
            detected_wounds.append(key)
    state = getattr(patient, "medical_state", None)
    if state is not None:
        for c in getattr(state, "conditions", []) or []:
            rendered = _condition_clinical(c)
            if rendered is None:
                continue
            _, dc = rendered
            if roll_stat(physician, "intellect") >= dc:
                # Use (type, location) so duplicate condition_types
                # at different sites can be distinguished.
                ctype = getattr(c, "condition_type", "")
                loc = getattr(c, "location", "") or ""
                detected_conditions.append(f"{ctype}@{loc}")

    entry = {
        "timestamp": now,
        "wound_signature": current_sig,
        "detected_wounds": detected_wounds,
        "detected_conditions": detected_conditions,
    }
    cache[cache_key] = entry
    return {**entry, "from_cache": False}


# ===================================================================
# Rendering
# ===================================================================

def render_diagnose_lines(physician, patient) -> list[str]:
    """Render the diagnose lines for the chart PATIENT block.

    Assumes ``perform_diagnose`` has already populated the cache;
    on cache miss inside the renderer (rare — covers a chart-menu
    re-entry edge case) the render falls back to the rung only,
    without rolling, so the renderer never broadcasts a pose.
    """
    lines: list[str] = []
    rung = classify_condition_rung(patient)
    colour = _RUNG_COLOUR.get(rung, "|w")
    lines.append(f"condition: {colour}{rung}|n")

    cache = _get_or_init_cache(patient)
    raw_entry = cache.get(_physician_cache_key(physician)) \
        if hasattr(cache, "get") else None
    if raw_entry is None:
        return lines

    detected_wound_keys = set(raw_entry.get("detected_wounds", []) or [])
    detected_conditions = set(
        raw_entry.get("detected_conditions", []) or []
    )

    findings: list[str] = []
    for key, organ_like, _dc in _iter_wound_targets(patient):
        if key not in detected_wound_keys:
            continue
        findings.append(clinical_phrase(organ_like))

    state = getattr(patient, "medical_state", None)
    if state is not None:
        for c in getattr(state, "conditions", []) or []:
            rendered = _condition_clinical(c)
            if rendered is None:
                continue
            phrase, _ = rendered
            ctype = getattr(c, "condition_type", "")
            loc = getattr(c, "location", "") or ""
            if f"{ctype}@{loc}" not in detected_conditions:
                continue
            findings.append(phrase)

    if findings:
        lines.append("findings:")
        for f in findings:
            lines.append(f"  · {f}")
    else:
        lines.append("findings: no abnormalities detected")

    return lines
