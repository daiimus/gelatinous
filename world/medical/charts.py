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


# ===================================================================
# CHART RUNNER — auto-chain pending steps back-to-back
# ===================================================================
#
# Single entry point: :func:`commence_chart`.  Dispatches the first
# pending step via ``start_procedure`` with an ``on_complete`` hook
# that recursively advances to the next pending step.  Stops when:
#
#   * No pending steps remain → chart marked ``COMPLETED``
#   * A step's verb isn't a procedure verb yet (treatment verbs
#     ``apply`` / ``inject``) → step marked ``SKIPPED``, chain
#     continues to the next step
#   * The procedure is interrupted → ``interrupt_procedure`` clears
#     the hook AND marks the running step as ``FAILED``; chain
#     dies cleanly because the hook never fires
#   * Process restart mid-chain → hook is in-memory only, chain
#     dies but chart state persists so the surgeon can re-commence


def commence_chart(target, actor) -> Optional[dict]:
    """Run the chart on ``target`` from its first pending step.

    Dispatches one procedure step via
    ``world.medical.procedures.start_procedure`` with an
    ``on_complete`` hook that re-enters ``commence_chart`` after
    the step's resolver fires.  The full chain executes back-to-
    back without further input from the surgeon.

    Returns the dispatched step dict (so callers can render
    "dispatching step X" prose), or ``None`` when the chart was
    already complete / had no dispatchable steps.

    Treatment verbs (``apply`` / ``inject``) aren't dispatched
    through ``start_procedure`` — they're skipped with an outcome
    note so the chain continues to whatever procedure step comes
    next.  Treatment-step dispatch is deferred to a follow-on PR.
    """
    chart = get_chart(target)
    if chart is None:
        return None

    pending = pending_steps(chart)
    if not pending:
        chart["status"] = COMPLETED
        save_chart(target, chart)
        return None

    step = pending[0]
    verb = step.get("verb")
    args = dict(step.get("args") or {})

    # Treatment verbs aren't wired yet — skip them and chain forward.
    if verb in TREATMENT_VERBS:
        step["status"] = SKIPPED
        step["outcome"] = (
            f"treatment verb {verb!r} not yet dispatchable from "
            "chart — deferred to PR-OP3"
        )
        save_chart(target, chart)
        return commence_chart(target, actor)

    if verb not in PROCEDURE_VERBS:
        step["status"] = SKIPPED
        step["outcome"] = f"unknown verb {verb!r}"
        save_chart(target, chart)
        return commence_chart(target, actor)

    # Translate the chart-stored verb args into the kwargs the
    # resolver actually expects.  Chart authoring captures the
    # player's intent ("harvest brain"); the resolver dispatch
    # needs richer context (container location for harvest /
    # install, the actual item object for install).  Resolving
    # at dispatch time — rather than at chart-author time —
    # means a chart authored before a transplant donor was on
    # hand can still find it later when the surgeon picks it up.
    try:
        resolved_args = _resolve_step_args(verb, args, target, actor)
    except _StepResolutionError as exc:
        step["status"] = FAILED
        step["outcome"] = f"resolution error: {exc}"
        save_chart(target, chart)
        return commence_chart(target, actor)

    step["status"] = RUNNING
    chart["status"] = IN_PROGRESS
    save_chart(target, chart)

    def _advance(target_arg, actor_arg):
        """on_complete hook — mark the running step done, then
        chain to the next pending step."""
        latest = get_chart(target_arg)
        if latest is None:
            return
        # Find the step that was running and mark it done.
        for s in latest.get("steps") or ():
            if s.get("status") == RUNNING:
                s["status"] = DONE
                break
        save_chart(target_arg, latest)
        # Recursive advancement — runs the next pending step, or
        # finalises the chart status if none remain.
        commence_chart(target_arg, actor_arg)

    from world.medical.procedures import start_procedure
    try:
        start_procedure(
            target, verb=verb, actor=actor,
            on_complete=_advance, **resolved_args,
        )
    except Exception as exc:
        # Dispatch failure (e.g. surgeon dropped their kit between
        # chart authoring and commence).  Mark the step failed and
        # advance to the next so a recoverable later step still gets
        # a shot.
        step["status"] = FAILED
        step["outcome"] = f"dispatch error: {exc}"
        save_chart(target, chart)
        return commence_chart(target, actor)

    return step


class _StepResolutionError(Exception):
    """Raised when a chart step's args can't be resolved into the
    kwargs the resolver expects (e.g. organ not in snapshot, donor
    organ no longer in surgeon's inventory).  Caller handles by
    marking the step ``FAILED`` and advancing to the next."""


def _resolve_step_args(verb: str, chart_args: dict, target, actor) -> dict:
    """Translate chart-stored args to resolver kwargs.

    The chart captures user intent ("harvest brain") and stores
    minimal args (``organ_name``).  Resolvers want richer context:

    * ``incise``  — needs ``location``; passes through unchanged
    * ``harvest`` — needs ``organ_name`` + ``location`` (container);
      we look up the container from the target's organ snapshot
    * ``install`` — needs ``organ_item`` (object) + ``location``;
      we look up the organ item from the actor's inventory by key
      and pass through the chart's ``location``
    * ``suture``  — optional ``location``; passes through

    Raises :class:`_StepResolutionError` when a required lookup
    fails so the chart runner can mark the step failed cleanly
    and chain to the next step.
    """
    if verb == "incise":
        if "location" not in chart_args:
            raise _StepResolutionError("incise requires a location")
        return {"location": chart_args["location"]}

    if verb == "harvest":
        organ_name = chart_args.get("organ_name")
        if not organ_name:
            raise _StepResolutionError("harvest requires an organ name")
        # Resolve the container from the target's snapshot.  Falls
        # back to organ_name as the location string if the snapshot
        # doesn't carry it (defensive — the resolver gracefully
        # handles that case).
        from world.medical.procedures import get_organ_snapshot
        snapshot = get_organ_snapshot(target)
        organs = snapshot.get("organs") or {}
        entry = organs.get(organ_name)
        if entry is None or not hasattr(entry, "get"):
            raise _StepResolutionError(
                f"no organ {organ_name!r} on target"
            )
        container = entry.get("container") or organ_name
        return {"organ_name": organ_name, "location": container}

    if verb == "install":
        organ_item_key = chart_args.get("organ_item_key")
        location = chart_args.get("location")
        if not organ_item_key or not location:
            raise _StepResolutionError(
                "install requires organ_item_key + location"
            )
        # Find the matching organ item in the actor's inventory.
        # Case-insensitive substring match on key.
        contents = getattr(actor, "contents", None) or ()
        match = None
        needle = organ_item_key.lower()
        for obj in contents:
            key = getattr(obj, "key", "")
            if isinstance(key, str) and needle in key.lower():
                match = obj
                break
        if match is None:
            raise _StepResolutionError(
                f"no donor organ matching {organ_item_key!r} in "
                "your inventory"
            )
        return {"organ_item": match, "location": location}

    if verb == "suture":
        out = {}
        if chart_args.get("location"):
            out["location"] = chart_args["location"]
        return out

    raise _StepResolutionError(f"unknown verb {verb!r}")
