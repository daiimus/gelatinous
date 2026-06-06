"""Surgical chart data layer (#307, PR-OP1).

The ``operate`` command stores a structured chart on the patient's
``db.medical_chart`` so a surgeon can sequence procedure steps,
walk away, and either commence the chart or hand it off to a
colleague.  This module is the pure data + dispatch surface; the
EvMenu UI lives in ``commands.CmdOperate``.

The chart structure was settled in the Phase 5 spec section of
``HEALTH_AND_SUBSTANCE_SYSTEM_SPEC.md``.  Steps are stored as
plain dicts so the persistence layer round-trips cleanly through
Evennia's attribute system (no typeclass for the chart itself).

# ===================================================================
# CHART STRUCTURE
# ===================================================================
#
# target.db.medical_chart = {
#     "version":          1,
#     "authored_by":      <dbref-str of the originating surgeon>,
#     "authored_at":      <unix timestamp>,
#     "last_modified_at": <unix timestamp>,
#     "status":           "draft" | "in_progress" | "completed" | "aborted",
#     "next_step_id":     <int>,
#     "steps": [
#         {
#             "id":       <int, stable across edits>,
#             "verb":     "incise" | "harvest" | "install" | "suture"
#                         | "inject" | "apply",
#             "args":     {...},      # verb-specific argument shape
#             "notes":    <str>,
#             "status":   "pending" | "running" | "done"
#                         | "skipped" | "failed",
#             "outcome":  <str | None>,
#         },
#         ...
#     ],
# }
#
# The chart is *additive* during authoring — steps are appended,
# not inserted at arbitrary positions, to keep the data model
# simple.  Reordering is a future feature.
"""

from __future__ import annotations

import time
from typing import Optional


# ===================================================================
# CHART STATUS LITERALS
# ===================================================================

DRAFT = "draft"
IN_PROGRESS = "in_progress"
COMPLETED = "completed"
ABORTED = "aborted"

CHART_STATUSES = (DRAFT, IN_PROGRESS, COMPLETED, ABORTED)


# ===================================================================
# STEP STATUS LITERALS
# ===================================================================

PENDING = "pending"
RUNNING = "running"
DONE = "done"
SKIPPED = "skipped"
FAILED = "failed"

STEP_STATUSES = (PENDING, RUNNING, DONE, SKIPPED, FAILED)


# ===================================================================
# PROCEDURE VERBS RECOGNISED BY THE CHART DISPATCH
# ===================================================================
#
# The chart can store these verbs as steps.  Procedure verbs
# (incise/harvest/install/suture) dispatch via
# ``world.medical.procedures.start_procedure``; treatment verbs
# (apply/inject) dispatch via the consumption command surfaces.
# Each verb declares its required and optional args so the menu
# UI can validate input at chart-authoring time.

PROCEDURE_VERBS = ("incise", "harvest", "install", "suture")
TREATMENT_VERBS = ("apply", "inject")
ALL_VERBS = PROCEDURE_VERBS + TREATMENT_VERBS

VERB_ARG_SPEC = {
    "incise":   {"required": ("location",),               "optional": ()},
    "harvest":  {"required": ("organ_name",),             "optional": ()},
    "install":  {"required": ("organ_item_key", "location"), "optional": ()},
    "suture":   {"required": (),                          "optional": ("location",)},
    "apply":    {"required": ("item_key", "location"),    "optional": ()},
    "inject":   {"required": ("item_key",),               "optional": ("location",)},
}


# ===================================================================
# CHART LIFECYCLE
# ===================================================================


def new_chart(surgeon) -> dict:
    """Build a fresh empty chart authored by ``surgeon``.

    The surgeon's identity is stored as a dbref string (not the
    object reference itself) so the chart survives the surgeon
    leaving / quitting / being deleted.  Resolution back to a
    character happens at execute time.
    """
    now = time.time()
    return {
        "version":          1,
        "authored_by":      getattr(surgeon, "dbref", None),
        "authored_at":      now,
        "last_modified_at": now,
        "status":           DRAFT,
        "next_step_id":     1,
        "steps":            [],
    }


def get_chart(target) -> Optional[dict]:
    """Read the chart stored on ``target``, or ``None`` when absent.

    Coerces Evennia's ``_SaverDict`` to a plain dict so callers can
    treat the result as a normal mapping without worrying about
    write-through semantics on the snapshot.
    """
    db = getattr(target, "db", None)
    if db is None:
        return None
    raw = getattr(db, "medical_chart", None)
    if raw is None:
        return None
    return dict(raw)


def save_chart(target, chart: dict) -> None:
    """Persist ``chart`` onto ``target.db.medical_chart``.

    Updates ``last_modified_at`` automatically; callers should not
    pre-stamp the timestamp themselves.
    """
    chart["last_modified_at"] = time.time()
    target.db.medical_chart = chart


def discard_chart(target) -> None:
    """Remove the chart from ``target``."""
    if getattr(target, "db", None) is not None:
        target.db.medical_chart = None


# ===================================================================
# STEP AUTHORING
# ===================================================================


def add_step(
    chart: dict,
    verb: str,
    args: Optional[dict] = None,
    notes: str = "",
) -> dict:
    """Append a new step to ``chart`` and return the step dict.

    Validates ``verb`` against :data:`ALL_VERBS` and the supplied
    ``args`` against the verb's required-arg list.  Raises
    ``ValueError`` on unknown verb or missing required arg so the
    UI can surface the failure cleanly.

    Each step is assigned an ``id`` from ``chart["next_step_id"]``
    that's stable across reorders / annotation passes — UI can
    reference steps by id rather than list index.
    """
    if verb not in ALL_VERBS:
        raise ValueError(
            f"Unknown verb {verb!r}; expected one of {ALL_VERBS}."
        )
    spec = VERB_ARG_SPEC[verb]
    args = dict(args or {})
    missing = [key for key in spec["required"] if key not in args]
    if missing:
        raise ValueError(
            f"Verb {verb!r} requires args {missing}."
        )
    step_id = chart.get("next_step_id", 1)
    step = {
        "id":      step_id,
        "verb":    verb,
        "args":    args,
        "notes":   notes,
        "status":  PENDING,
        "outcome": None,
    }
    chart.setdefault("steps", []).append(step)
    chart["next_step_id"] = step_id + 1
    return step


def remove_step(chart: dict, step_id: int) -> bool:
    """Remove the step with ``step_id`` from ``chart``.

    Returns True when a step was removed, False when no step with
    that id existed.  The step list contracts in place; the
    ``next_step_id`` counter is NOT rewound, so future additions
    won't collide with the removed id.
    """
    steps = chart.get("steps", [])
    for idx, step in enumerate(steps):
        if step.get("id") == step_id:
            del steps[idx]
            return True
    return False


def find_step(chart: dict, step_id: int) -> Optional[dict]:
    """Return the step dict for ``step_id``, or ``None`` when absent."""
    for step in chart.get("steps", []):
        if step.get("id") == step_id:
            return step
    return None


# ===================================================================
# CHART SUMMARY HELPERS — UI-friendly accessors
# ===================================================================


def pending_steps(chart: dict) -> list:
    """Return the ordered list of pending steps in ``chart``."""
    return [
        s for s in chart.get("steps", [])
        if s.get("status") == PENDING
    ]


def step_count(chart: dict) -> int:
    """Total step count (all statuses)."""
    return len(chart.get("steps", []))


def is_chart_complete(chart: dict) -> bool:
    """True when every step in ``chart`` is in a terminal status
    (done / skipped / failed)."""
    terminal = {DONE, SKIPPED, FAILED}
    return all(
        s.get("status") in terminal
        for s in chart.get("steps", [])
    )


# ===================================================================
# CHART DISPATCH — commence execution
# ===================================================================


def render_step_summary(step: dict) -> str:
    """One-line UI rendering of a step for chart display.

    Examples:
        ``incise chest``
        ``harvest left lung``
        ``install donor heart in chest``
        ``apply gauze on chest``
    """
    verb = step.get("verb", "?")
    args = step.get("args") or {}
    if verb == "incise":
        return f"incise {_humanize(args.get('location'))}"
    if verb == "harvest":
        return f"harvest {_humanize(args.get('organ_name'))}"
    if verb == "install":
        organ = _humanize(args.get("organ_item_key"))
        loc = _humanize(args.get("location"))
        return f"install {organ} in {loc}"
    if verb == "suture":
        loc = args.get("location")
        return f"suture {_humanize(loc)}" if loc else "suture all"
    if verb == "apply":
        item = _humanize(args.get("item_key"))
        loc = _humanize(args.get("location"))
        return f"apply {item} on {loc}"
    if verb == "inject":
        item = _humanize(args.get("item_key"))
        loc = args.get("location")
        if loc:
            return f"inject {item} at {_humanize(loc)}"
        return f"inject {item}"
    return verb


def _humanize(value) -> str:
    """Underscore → space for display.  Falls back to ``"?"`` on
    None / non-string."""
    if not isinstance(value, str):
        return "?"
    return value.replace("_", " ")
