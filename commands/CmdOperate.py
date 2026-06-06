"""Operate command — charting menu over the procedure verbs (#307, PR-OP1).

``operate <target>`` opens an EvMenu where a surgeon can build a
medical chart (sequence of procedure steps) and either commence
the next pending step or save the chart on the patient for later /
handoff to a colleague.

The chart data lives in ``world.medical.charts``; this module is
the UI surface only.  Visual idiom mirrors ``armor comprehensive``:
left-aligned, box-drawn section labels on the left
(PATIENT / CHART / OPTIONS), tree-branched content on the right,
Roman-numeral step ordering.  No centering.

Scope for PR-OP1 (MVP):

  ✓ Add procedure step (incise / harvest / install / suture)
  ✓ View chart with rendered step list
  ✓ Commence next pending step
  ✓ Save chart and exit
  ✓ Discard chart

Deferred to follow-on PRs:

  • Diagnose pane (skill-gated organ-state inspection)
  • Add treatment step (apply / inject)
  • Reorder / remove / annotate steps
  • Resume from arbitrary step
  • Auto-chaining (commence all steps back-to-back)
  • Permission delegation (multi-author charts)
  • Trust/consent integration for conscious targets

# ===================================================================
# VISUAL DESIGN
# ===================================================================
#
# Mirrors ``armor comprehensive`` (commands/CmdArmor.py:_show_
# comprehensive_view):
#
#   ╔═══════════════╗
#   ║  PATIENT      ║──── the battered drifter
#   ╚═══════════════╝
#
#   ╔═══════════════╗
#   ║  CHART        ║──┬──  I. incise chest                [pending]
#   ╚═══════════════╝  ├── II. harvest heart               [pending]
#                      └── III. suture chest                [pending]
#
#   ╔═══════════════╗
#   ║  OPTIONS      ║──┬── 1. Add procedure step
#   ╚═══════════════╝  ├── 2. View chart detail
#                      ├── 3. Commence next step
#                      ├── 4. Save and exit
#                      ├── 5. Discard chart
#                      └── x. Exit (no save)
#
# Section labels are SHOUTING CAPS in a 17-char box; content
# branches off via ────, ├──, └── glyphs.  Roman numerals for
# chart steps (cosmetic — matches the procedure-as-clinical-act
# vibe).  Per-line padding suppressed when ``center_headers`` is
# disabled at session level.
"""

from __future__ import annotations

from evennia import Command
from evennia.utils.evmenu import EvMenu

from world.medical import charts as chart_lib


# ===================================================================
# VISUAL CONSTANTS
# ===================================================================

LABEL_BOX_WIDTH = 15                # Content width inside ║...║
LABEL_BOX_TOTAL = LABEL_BOX_WIDTH + 2  # Including ║ borders
STEM = "────"                       # Single-item simple stem
BRANCH_CORNER = "──┐"               # Multi-item: emerge from label box,
                                    # turn down into the trunk
JOIN_MID = "├──"
JOIN_END = "└──"
EMPTY_GUTTER = " " * (LABEL_BOX_TOTAL + 2)  # Aligns trunk under the corner


# ===================================================================
# RENDERING — left-aligned tree-branch chart display
# ===================================================================


def _roman(num: int) -> str:
    """Roman-numeral conversion (1..50 covers any sensible chart)."""
    if num <= 0:
        return "0"
    val = [50, 40, 10, 9, 5, 4, 1]
    syms = ["L", "XL", "X", "IX", "V", "IV", "I"]
    out = ""
    for v, s in zip(val, syms):
        while num >= v:
            out += s
            num -= v
    return out


def _label_box(label: str) -> tuple[str, str, str]:
    """Build the three lines of a section-label box.

    Returns ``(top, middle, bottom)`` as bare strings (no trailing
    newline).  Middle includes the centered label inside the
    box borders.
    """
    label = label.upper()
    pad_left = (LABEL_BOX_WIDTH - len(label)) // 2
    pad_right = LABEL_BOX_WIDTH - len(label) - pad_left
    text = " " * pad_left + label + " " * pad_right
    top = "╔" + "═" * LABEL_BOX_WIDTH + "╗"
    mid = "║" + text + "║"
    bot = "╚" + "═" * LABEL_BOX_WIDTH + "╝"
    return top, mid, bot


def _render_section(label: str, lines: list[str]) -> list[str]:
    """Render one labeled section.

    ``lines`` is the list of content lines that should branch off
    the right side of the label box.  Single-line content uses a
    simple ──── stem; multi-line uses ──┬── / ├── / └── tree.
    Empty ``lines`` renders the box alone with no branch.
    """
    if not lines:
        top, mid, bot = _label_box(label)
        return [top, mid, bot]

    top, mid, bot = _label_box(label)
    out = []
    if len(lines) == 1:
        out.append(top)
        out.append(f"{mid}{STEM} {lines[0]}")
        out.append(bot)
        return out

    # Multi-line: branched tree, equidistant rows.  Every item
    # hangs off the trunk uniformly — no special treatment for the
    # first item.  The label box emits ``──┐`` from its middle
    # row, turns down through ``│`` past the box bottom, and the
    # items follow as ``├── …`` / ``└── …`` rows.  Trade one extra
    # row for a cleaner read.
    out.append(top)
    out.append(f"{mid}{BRANCH_CORNER}")
    out.append(f"{bot}  │")
    for line in lines[:-1]:
        out.append(f"{EMPTY_GUTTER}{JOIN_MID} {line}")
    out.append(f"{EMPTY_GUTTER}{JOIN_END} {lines[-1]}")
    return out


def _render_patient_lines(caller, target) -> list[str]:
    """One identity line + vital-summary line(s) for the PATIENT
    section."""
    lines = [target.get_display_name(caller)]

    state = getattr(target, "medical_state", None)
    if state is not None:
        vitals = []
        is_unc = getattr(target, "is_unconscious", None)
        if callable(is_unc) and is_unc():
            vitals.append("unconscious")
        is_dead = getattr(state, "is_dead", None)
        if callable(is_dead) and is_dead():
            vitals.append("|rdying|n")
        conditions = getattr(state, "conditions", None) or []
        if conditions:
            count_by_type = {}
            for c in conditions:
                t = getattr(c, "condition_type", "condition")
                count_by_type[t] = count_by_type.get(t, 0) + 1
            for k, n in count_by_type.items():
                tag = k.replace("_", " ")
                vitals.append(f"{n}× {tag}" if n > 1 else tag)
        if vitals:
            lines.append(" · ".join(vitals))

    # Open incisions from the surgical_state attr (set by procedures).
    surgical_state = getattr(getattr(target, "db", None),
                             "surgical_state", None)
    if surgical_state:
        open_locs = surgical_state.get("incisions") or []
        if open_locs:
            humanized = [loc.replace("_", " ") for loc in open_locs]
            lines.append(f"open incision: {', '.join(humanized)}")

    return lines


def _render_chart_lines(chart: dict | None) -> list[str]:
    """Render the chart's step list (or a placeholder when empty)."""
    if not chart:
        return ["no active chart — pick option 1 to add a step"]
    steps = chart.get("steps") or []
    if not steps:
        return [
            f"{chart.get('status', 'draft')} · 0 steps "
            f"(empty — add procedure steps)"
        ]
    out = []
    for idx, step in enumerate(steps, start=1):
        roman = _roman(idx).rjust(4)
        summary = chart_lib.render_step_summary(step)
        status = step.get("status", "pending")
        # Color cue per status — pending neutral, done green, failed red.
        if status == chart_lib.DONE:
            tag = "|gdone|n"
        elif status == chart_lib.FAILED:
            tag = "|rfailed|n"
        elif status == chart_lib.SKIPPED:
            tag = "|yskipped|n"
        elif status == chart_lib.RUNNING:
            tag = "|crunning|n"
        else:
            tag = "pending"
        out.append(f"{roman}. {summary.ljust(36)} [{tag}]")
    return out


def _render_options_lines(option_numbers: list[tuple[str, str]]) -> list[str]:
    """Format the OPTIONS block.  ``option_numbers`` is a list of
    ``(label, description)`` tuples; we render as
    ``  1. Description``."""
    return [
        f"{num}. {desc}" for num, desc in option_numbers
    ]


def render_top_level(caller, target) -> str:
    """Compose the full top-level menu render: PATIENT → CHART →
    OPTIONS, three labeled sections, blank-line separated."""
    chart = chart_lib.get_chart(target)

    options = [
        ("1", "Add procedure step"),
        ("2", "View chart detail"),
        ("3", "Commence next step"),
        ("4", "Save and exit"),
        ("5", "Discard chart"),
        ("x", "Exit (no save)"),
    ]

    blocks = []
    blocks.append(_render_section("PATIENT",
                                  _render_patient_lines(caller, target)))
    blocks.append(_render_section("CHART", _render_chart_lines(chart)))
    blocks.append(_render_section("OPTIONS", _render_options_lines(options)))

    header = "|wSURGICAL CHART|n"
    rule = "═" * 60
    parts = [header, rule, ""]
    for block in blocks:
        parts.extend(block)
        parts.append("")
    parts.append("|wSelect an option:|n")
    return "\n".join(parts)


# ===================================================================
# MENU — follows the describe pattern (suppress default decorations)
# ===================================================================


class _OperateMenu(EvMenu):
    """EvMenu subclass that suppresses default decorations.

    Each node renders its full content (header, sections, options,
    prompt).  Default separators and auto-formatted option blocks
    would conflict with the armor-comprehensive visual idiom.
    """

    def nodetext_formatter(self, nodetext):
        return nodetext

    def options_formatter(self, optionlist):
        return ""

    def node_formatter(self, nodetext, optionstext):
        return nodetext


def _menu_exit(caller, menu):
    """Cleanup callback when the menu exits."""
    for attr in ("_operate_target",):
        if hasattr(caller.ndb, attr):
            delattr(caller.ndb, attr)


# ===================================================================
# NODES
# ===================================================================


def _node_top(caller, raw_string, **kwargs):
    """Top-level node — render PATIENT/CHART/OPTIONS and route
    on input."""
    target = getattr(caller.ndb, "_operate_target", None)
    if target is None:
        return "|rNo patient set; aborting.|n", None
    text = render_top_level(caller, target)
    options = ({"key": "_default", "goto": _process_top_choice},)
    return text, options


def _process_top_choice(caller, raw_string, **kwargs):
    """Top-level option dispatcher.  Validates input and returns
    the next node name."""
    choice = raw_string.strip().lower()
    if not choice:
        return None  # Re-display top.
    if choice in ("x", "exit"):
        return "node_exit"
    if choice == "1":
        return "node_add_verb"
    if choice == "2":
        return "node_view_chart"
    if choice == "3":
        return "node_commence"
    if choice == "4":
        return "node_save_exit"
    if choice == "5":
        return "node_discard_confirm"
    caller.msg("|rInvalid option. Enter 1-5 or x.|n")
    return None


# -------------------------------------------------------------------
# Add-step flow: verb → arg(s) → confirm
# -------------------------------------------------------------------


def _node_add_verb(caller, raw_string, **kwargs):
    """Prompt the surgeon for a procedure verb."""
    text = (
        "\n|wAdd procedure step|n\n\n"
        "  1. incise\n"
        "  2. harvest\n"
        "  3. install\n"
        "  4. suture\n"
        "  x. Cancel\n\n"
        "|wWhich verb?|n"
    )
    options = ({"key": "_default", "goto": _process_verb_choice},)
    return text, options


def _process_verb_choice(caller, raw_string, **kwargs):
    choice = raw_string.strip().lower()
    if choice in ("x", "exit", "cancel"):
        return "node_top"
    verb_map = {
        "1": "incise", "incise": "incise",
        "2": "harvest", "harvest": "harvest",
        "3": "install", "install": "install",
        "4": "suture", "suture": "suture",
    }
    verb = verb_map.get(choice)
    if verb is None:
        caller.msg("|rPick 1-4 or x to cancel.|n")
        return None
    caller.ndb._operate_pending_verb = verb
    # Suture has optional location; the rest are required.
    if verb == "suture":
        return "node_suture_location"
    if verb == "incise":
        return "node_incise_location"
    if verb == "harvest":
        return "node_harvest_organ"
    if verb == "install":
        return "node_install_organ"
    return "node_top"


def _node_incise_location(caller, raw_string, **kwargs):
    text = (
        "\n|wIncise location|n\n\n"
        "Enter the body location to incise (e.g. chest, abdomen, head).\n"
        "Underscores will be normalised from spaces automatically.\n\n"
        "|wLocation|n (or |yx|n to cancel):"
    )
    options = ({"key": "_default", "goto": _process_incise_location},)
    return text, options


def _process_incise_location(caller, raw_string, **kwargs):
    if raw_string and raw_string.strip().lower() in ("x", "exit", "cancel"):
        return "node_top"
    if not raw_string or not raw_string.strip():
        return None
    location = raw_string.strip().lower().replace(" ", "_")
    _add_step_to_chart(caller, "incise", {"location": location})
    return "node_top"


def _node_harvest_organ(caller, raw_string, **kwargs):
    text = (
        "\n|wHarvest organ|n\n\n"
        "Enter the organ name to harvest (e.g. heart, left lung, "
        "left kidney).\n\n"
        "|wOrgan|n (or |yx|n to cancel):"
    )
    options = ({"key": "_default", "goto": _process_harvest_organ},)
    return text, options


def _process_harvest_organ(caller, raw_string, **kwargs):
    if raw_string and raw_string.strip().lower() in ("x", "exit", "cancel"):
        return "node_top"
    if not raw_string or not raw_string.strip():
        return None
    organ = raw_string.strip().lower().replace(" ", "_")
    _add_step_to_chart(caller, "harvest", {"organ_name": organ})
    return "node_top"


def _node_install_organ(caller, raw_string, **kwargs):
    text = (
        "\n|wInstall organ|n\n\n"
        "Enter the donor-organ key from your inventory followed by "
        "'in' and the target location.  Example:\n\n"
        "  donor heart in chest\n\n"
        "|wOrgan and location|n (or |yx|n to cancel):"
    )
    options = ({"key": "_default", "goto": _process_install_organ},)
    return text, options


def _process_install_organ(caller, raw_string, **kwargs):
    if raw_string and raw_string.strip().lower() in ("x", "exit", "cancel"):
        return "node_top"
    if not raw_string or not raw_string.strip():
        return None
    raw = raw_string.strip()
    if " in " not in raw:
        caller.msg("|rExpected: <organ key> in <location>|n")
        return None
    organ_key, _, location = raw.partition(" in ")
    organ_key = organ_key.strip().lower()
    location = location.strip().lower().replace(" ", "_")
    if not organ_key or not location:
        caller.msg("|rBoth organ key and location are required.|n")
        return None
    _add_step_to_chart(caller, "install",
                       {"organ_item_key": organ_key, "location": location})
    return "node_top"


def _node_suture_location(caller, raw_string, **kwargs):
    text = (
        "\n|wSuture location|n\n\n"
        "Enter the location to suture, or press Enter to suture "
        "all open incisions.\n\n"
        "|wLocation|n (or |yx|n to cancel):"
    )
    options = ({"key": "_default", "goto": _process_suture_location},)
    return text, options


def _process_suture_location(caller, raw_string, **kwargs):
    if raw_string and raw_string.strip().lower() in ("x", "exit", "cancel"):
        return "node_top"
    raw = (raw_string or "").strip()
    args = {}
    if raw:
        args["location"] = raw.lower().replace(" ", "_")
    _add_step_to_chart(caller, "suture", args)
    return "node_top"


def _add_step_to_chart(caller, verb: str, args: dict) -> None:
    """Append a step to the chart on the active target, creating
    the chart if absent.  Persists immediately."""
    target = caller.ndb._operate_target
    chart = chart_lib.get_chart(target) or chart_lib.new_chart(caller)
    try:
        step = chart_lib.add_step(chart, verb, args)
    except ValueError as exc:
        caller.msg(f"|r{exc}|n")
        return
    chart_lib.save_chart(target, chart)
    caller.msg(
        f"|wStep added:|n {chart_lib.render_step_summary(step)}"
    )


# -------------------------------------------------------------------
# View / commence / save / discard
# -------------------------------------------------------------------


def _node_view_chart(caller, raw_string, **kwargs):
    target = caller.ndb._operate_target
    chart = chart_lib.get_chart(target)
    if not chart or not (chart.get("steps") or []):
        text = (
            "\n|wChart detail|n\n\n"
            "The chart is empty.  Add steps from the top-level menu.\n\n"
            "|wEnter to return.|n"
        )
        options = ({"key": "_default", "goto": "node_top"},)
        return text, options
    parts = ["\n|wChart detail|n\n"]
    for idx, step in enumerate(chart["steps"], start=1):
        roman = _roman(idx)
        summary = chart_lib.render_step_summary(step)
        status = step.get("status", "pending")
        outcome = step.get("outcome")
        line = f"  {roman}. {summary}  [{status}]"
        if outcome:
            line += f"\n     └── outcome: {outcome}"
        parts.append(line)
    parts.append("\n|wEnter to return.|n")
    text = "\n".join(parts)
    options = ({"key": "_default", "goto": "node_top"},)
    return text, options


def _node_commence(caller, raw_string, **kwargs):
    """Commence the chart — auto-chains all pending steps back-to-
    back via :func:`world.medical.charts.commence_chart`.

    The runner registers an ``on_complete`` hook on
    ``start_procedure`` so each step advances to the next when its
    resolver fires.  Interruption (combat, target movement, death)
    halts the chain via the procedure dispatch's
    ``interrupt_procedure`` path; the running step gets marked
    ``failed`` with outcome ``"interrupted"`` so the surgeon can
    see the abort reason on re-entry.
    """
    target = caller.ndb._operate_target
    chart = chart_lib.get_chart(target)
    if not chart:
        caller.msg("|rNo chart to commence.|n")
        return "node_top"

    pending = chart_lib.pending_steps(chart)
    if not pending:
        caller.msg(
            "|wChart complete — no pending steps.|n  "
            "Use option 5 to discard if you're done."
        )
        return "node_top"

    step = chart_lib.commence_chart(target, caller)
    if step is None:
        caller.msg("|wChart complete.|n")
        return "node_top"

    summary = chart_lib.render_step_summary(step)
    caller.msg(
        f"|wDispatched chart:|n {len(pending)} pending steps, "
        f"running back-to-back."
    )
    caller.msg(
        f"|yFirst step in flight:|n {summary}.  Subsequent steps "
        "auto-chain on completion."
    )
    return "node_exit"


def _node_save_exit(caller, raw_string, **kwargs):
    target = caller.ndb._operate_target
    chart = chart_lib.get_chart(target)
    if chart is None:
        caller.msg("No chart to save.")
    else:
        chart_lib.save_chart(target, chart)
        caller.msg("|wChart saved on patient.|n")
    return "node_exit"


def _node_discard_confirm(caller, raw_string, **kwargs):
    text = (
        "\n|wDiscard chart|n\n\n"
        "Permanently remove the chart from this patient?  "
        "Pending steps will not be executed.\n\n"
        "  |wy|n - yes, discard\n"
        "  |wn|n - no, return to top\n"
    )
    options = ({"key": "_default", "goto": _process_discard_confirm},)
    return text, options


def _process_discard_confirm(caller, raw_string, **kwargs):
    choice = (raw_string or "").strip().lower()
    if choice in ("y", "yes"):
        target = caller.ndb._operate_target
        chart_lib.discard_chart(target)
        caller.msg("|wChart discarded.|n")
        return "node_exit"
    if choice in ("n", "no"):
        return "node_top"
    caller.msg("|ry|n or |rn|n.")
    return None


def _node_exit(caller, raw_string, **kwargs):
    return "", None


# ===================================================================
# COMMAND
# ===================================================================


class CmdOperate(Command):
    """Open the surgical-chart menu for a patient.

    Usage:
        operate <target>

    Examples:
        operate bob
        operate the woman
        operate corpse
        operate severed left arm

    The chart persists on the patient between sessions — you can
    save a draft, walk away, and have another surgeon (or yourself
    later) commence the next step.  Conscious targets are gated by
    the trust/consent system (not yet implemented); for now,
    operate only resolves to unconscious / dead / severed targets
    cleanly.

    See ``help surgery`` for the procedure verbs underneath.
    """

    key = "operate"
    aliases = ()
    locks = "cmd:all()"
    help_category = "Medical"

    def func(self):
        caller = self.caller
        raw = (self.args or "").strip()
        if not raw:
            caller.msg("Usage: operate <target>")
            return

        # Reuse the same target-resolution chain as the surgical verbs
        # so sdescs and inventory-held severed parts resolve identically.
        from commands.CmdSurgical import _resolve_target
        target = _resolve_target(caller, raw)
        if target is None:
            return  # _resolve_target / search emit their own messages

        from world.medical.procedures import get_organ_snapshot
        if not get_organ_snapshot(target):
            caller.msg(
                f"{target.get_display_name(caller)} doesn't have an "
                f"anatomy you can operate on."
            )
            return

        caller.ndb._operate_target = target
        _OperateMenu(
            caller,
            {
                "node_top":              _node_top,
                "node_add_verb":         _node_add_verb,
                "node_incise_location":  _node_incise_location,
                "node_harvest_organ":    _node_harvest_organ,
                "node_install_organ":    _node_install_organ,
                "node_suture_location":  _node_suture_location,
                "node_view_chart":       _node_view_chart,
                "node_commence":         _node_commence,
                "node_save_exit":        _node_save_exit,
                "node_discard_confirm":  _node_discard_confirm,
                "node_exit":             _node_exit,
            },
            startnode="node_top",
            cmd_on_exit=_menu_exit,
        )
