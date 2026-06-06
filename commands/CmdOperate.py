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

# Muted accent colour used for secondary / parenthetical info.
# Was |x (dark grey / near-black) which read as illegible on most
# clients.  Burnt orange via XTERM-256 (|520 = R5 G2 B0) reads
# clean against both dark and light backgrounds while still
# de-emphasising the text.  Eventually persistent per-player
# colour preferences can override this default — for now it's
# a single module-level knob so swapping shades is one-line work.
MUTED = "|520"

LABEL_BOX_WIDTH = 15                # Content width inside ║...║
LABEL_BOX_TOTAL = LABEL_BOX_WIDTH + 2  # Including ║ borders
BRANCH_CORNER = "──┐"               # Emerge from label box, turn
                                    # down into the trunk
INLINE_STEM = "────"                # Inline-first w/ no trunk
                                    # below — simple horizontal stem
INLINE_TEE = "──┬──"                # Inline-first w/ trunk below —
                                    # tee splits content rightward
                                    # and trunk downward in one
                                    # connected glyph
JOIN_MID = "├──"                    # Trunk continues
JOIN_END = "└──"                    # Trunk terminates
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


def _render_section(
    label: str,
    lines: list[str],
    *,
    inline_first: bool = False,
) -> list[str]:
    """Render one labeled section.

    Two layout modes:

    * **Default (equidistant)** — ``──┐`` corner emerges from the
      box-middle row, trunk continues through ``│`` past the
      box bottom, every content line hangs off the trunk as
      ``├── …`` / ``└── …``.  Used by CHART and OPTIONS.

    * **inline_first** — first content line sits on the box-mid
      row via a short ``────`` stem; remaining lines drop below
      the box bottom and trunk down as before.  Used by PATIENT
      where the identity (sdesc or recognised name, per the
      identity pipeline) reads as the section header rather than
      a list entry, and conditions hang below.

    Empty ``lines`` renders the box alone with no branch.
    """
    top, mid, bot = _label_box(label)
    if not lines:
        return [top, mid, bot]

    if inline_first:
        first = lines[0]
        rest = lines[1:]
        if not rest:
            # No conditions — simple inline stem, box closes cleanly.
            return [
                top,
                f"{mid}{INLINE_STEM} {first}",
                bot,
            ]
        # Conditions follow — use a tee (``──┬──``) so the identity
        # on the right and the trunk to the conditions below share
        # one connected glyph rather than a disconnected stem.
        out = [
            top,
            f"{mid}{INLINE_TEE} {first}",
            f"{bot}  │",
        ]
        for line in rest[:-1]:
            out.append(f"{EMPTY_GUTTER}{JOIN_MID} {line}")
        out.append(f"{EMPTY_GUTTER}{JOIN_END} {rest[-1]}")
        return out

    # Default: every item drops below the box, uniform tree.
    out = [
        top,
        f"{mid}{BRANCH_CORNER}",
        f"{bot}  │",
    ]
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
    if not chart or not (chart.get("steps") or []):
        return [f"{MUTED}0 documented procedures|n"]
    steps = chart["steps"]
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
        ("2", f"Edit chart  {MUTED}(view / reorder / remove)|n"),
        ("3", "Commence next step"),
        ("4", "Save and exit"),
        ("5", "Discard chart"),
        ("x", "Exit (no save)"),
    ]

    blocks = []
    # PATIENT uses the inline-first layout so the identity reads as
    # the section header (per identity pipeline — sdesc or
    # recognised name), with conditions hanging below.
    blocks.append(_render_section(
        "PATIENT", _render_patient_lines(caller, target),
        inline_first=True,
    ))
    blocks.append(_render_section("CHART", _render_chart_lines(chart)))
    blocks.append(_render_section("OPTIONS", _render_options_lines(options)))

    # No header — the PATIENT box leads directly.  Flavour text /
    # thematic framing (clipboard?  HUD overlay?  cyberbrain
    # interface?) can land here once we settle on what the chart
    # IS in the fiction.
    parts = []
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
    for attr in (
        "_operate_target",
        "_operate_pickable",
        "_operate_install_donor",
        "_operate_pending_verb",
        "_operate_insert_before",
    ):
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
        return "node_edit_chart"
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
        "  5. amputate\n"
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
        "1": "incise",   "incise":   "incise",
        "2": "harvest",  "harvest":  "harvest",
        "3": "install",  "install":  "install",
        "4": "suture",   "suture":   "suture",
        "5": "amputate", "amputate": "amputate",
    }
    verb = verb_map.get(choice)
    if verb is None:
        caller.msg("|rPick 1-5 or x to cancel.|n")
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
    if verb == "amputate":
        return "node_amputate_location"
    return "node_top"


# ===================================================================
# PICKABLE LIST HELPERS
# ===================================================================
#
# Each "add step" flow renders a numbered list of valid choices
# pulled live from the target / surgeon state, so the surgeon
# picks rather than types.  Free-text fallback is still accepted
# (a surgeon who knows the canonical name can short-circuit), but
# the default flow is point-and-shoot.


def _list_containers(target):
    """Return the sorted unique container names from ``target``'s
    organ snapshot — the set of body locations that can be
    incised."""
    from world.medical.procedures import get_organ_snapshot
    snapshot = get_organ_snapshot(target)
    organs = snapshot.get("organs") or {}
    containers = set()
    for data in organs.values():
        if not hasattr(data, "get"):
            continue
        container = data.get("container")
        if container:
            containers.add(container)
    return sorted(containers)


def _list_organs(target):
    """Return ``(organ_name, container)`` pairs from ``target``'s
    snapshot, sorted by container then organ name.  Drops organs
    already in ``removed_organs``."""
    from world.medical.procedures import get_organ_snapshot
    snapshot = get_organ_snapshot(target)
    organs = snapshot.get("organs") or {}
    removed = set(
        getattr(getattr(target, "db", None), "removed_organs", None)
        or ()
    )
    out = []
    for name, data in organs.items():
        if name in removed:
            continue
        if not hasattr(data, "get"):
            continue
        container = data.get("container") or "?"
        out.append((name, container))
    out.sort(key=lambda nc: (nc[1], nc[0]))
    return out


def _list_donor_organs(caller):
    """Return ``(item, organ_name)`` pairs — Organ items in the
    caller's inventory that came from a harvest and can be installed."""
    out = []
    for obj in (getattr(caller, "contents", None) or ()):
        organ_name = getattr(getattr(obj, "db", None), "organ_name", None)
        if organ_name:
            out.append((obj, organ_name))
    return out


def _list_open_incisions(target):
    """Return sorted list of locations with open incisions on
    ``target``."""
    from world.medical.procedures import open_incision_locations
    try:
        return sorted(open_incision_locations(target))
    except Exception:
        return []


def _list_severed_locations(target):
    """Return every container on ``target`` carrying a severed organ.

    Direct read off the live medical state — catches stumps the chart
    can't infer from pending steps (combat-driven amputation, prior
    surgical amputation whose chart step is no longer ``PENDING``,
    or any other path that bypasses chart authoring entirely).
    Already-sutured stumps are filtered out so the picker doesn't
    re-offer them.
    """
    state = getattr(target, "medical_state", None)
    if state is None or not hasattr(state, "organs"):
        return []
    already_sutured = set(
        getattr(getattr(target, "db", None), "sutured_stumps", None) or ()
    )
    seen = set()
    out = []
    for organ in state.organs.values():
        if getattr(organ, "wound_stage", None) != "severed":
            continue
        container = getattr(organ, "container", None)
        if not container or container in seen:
            continue
        if container in already_sutured:
            continue
        seen.add(container)
        out.append(container)
    return out


def _list_planned_incisions(caller):
    """Return locations slated to have an open wound after pending
    chart steps fire.

    Walks the chart on the active target and returns locations
    from pending ``incise`` *and* ``amputate`` steps — both leave
    open wounds that need suturing.  Amputation stumps are
    registered in the incisions list by ``_resolve_amputate`` so
    the existing suture machinery handles them uniformly with
    surgical openings.

    Lets the suture picker include locations that *will* be
    sutureable by the time the suture step fires — important for
    chart-authoring flows like ``incise chest → harvest heart →
    suture chest`` or ``amputate leg → suture leg`` where nothing
    is currently open at chart-author time.
    """
    target = getattr(caller.ndb, "_operate_target", None)
    if target is None:
        return []
    chart = chart_lib.get_chart(target)
    if not chart:
        return []
    out = []
    for step in chart.get("steps", []) or ():
        if step.get("status") != chart_lib.PENDING:
            continue
        if step.get("verb") not in ("incise", "amputate"):
            continue
        loc = (step.get("args") or {}).get("location")
        if loc:
            out.append(loc)
    return out


def _render_numbered(items, render_fn):
    """Format a numbered pickable list.

    ``items`` is any iterable; ``render_fn(item)`` returns the
    display string for each.  Renders as ``  1. label`` rows with
    1-based indices.
    """
    return "\n".join(
        f"  {idx}. {render_fn(item)}"
        for idx, item in enumerate(items, start=1)
    )


def _parse_pick(raw, items):
    """Resolve a user pick (numeric index or substring match)
    against ``items``.

    Returns the chosen item or ``None`` if no match.  Numeric
    picks are 1-based.  String picks match case-insensitively
    against ``str(item)``; for tuples, the *first* element is
    matched (organ name, container name).
    """
    if not raw or not raw.strip():
        return None
    raw = raw.strip().lower()
    # Numeric pick.
    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(items):
            return items[idx]
        return None
    # String pick — substring match against str() of the first
    # tuple element (or the whole value).
    for item in items:
        haystack = item[0] if isinstance(item, tuple) else item
        if raw in str(haystack).lower():
            return item
    return None


# ===================================================================
# Incise picker
# ===================================================================


def _node_incise_location(caller, raw_string, **kwargs):
    target = caller.ndb._operate_target
    containers = _list_containers(target)
    if not containers:
        caller.msg("|rNo incisable locations on this target.|n")
        return "node_top"
    caller.ndb._operate_pickable = containers
    listing = _render_numbered(
        containers, lambda loc: loc.replace("_", " "),
    )
    text = (
        "\n|wIncise location|n\n\n"
        "Pick a body location to incise:\n\n"
        f"{listing}\n\n"
        "  x. Cancel\n\n"
        "|wWhich location?|n (number or name)"
    )
    options = ({"key": "_default", "goto": _process_incise_location},)
    return text, options


def _process_incise_location(caller, raw_string, **kwargs):
    raw = (raw_string or "").strip()
    if raw.lower() in ("x", "exit", "cancel"):
        return "node_top"
    if not raw:
        return None
    pick = _parse_pick(raw, caller.ndb._operate_pickable or [])
    if pick is None:
        caller.msg("|rPick a number from the list, or type the name.|n")
        return None
    _add_step_to_chart(caller, "incise", {"location": pick})
    return "node_top"


# ===================================================================
# Amputate picker
# ===================================================================


def _list_severable_containers(target):
    """Return sorted list of severable containers for ``target``'s
    species — limbs and head per the species table."""
    from world.anatomy import get_species_severable_containers
    species = getattr(getattr(target, "db", None), "species", None)
    try:
        return sorted(get_species_severable_containers(species))
    except Exception:
        return []


def _node_amputate_location(caller, raw_string, **kwargs):
    target = caller.ndb._operate_target
    locations = _list_severable_containers(target)
    if not locations:
        caller.msg(
            "|rNo severable locations on this target.  Amputation "
            "requires species anatomy that declares severable "
            "containers (limbs / head).|n"
        )
        return "node_top"
    caller.ndb._operate_pickable = locations
    listing = _render_numbered(
        locations, lambda loc: loc.replace("_", " "),
    )
    text = (
        "\n|wAmputate location|n\n\n"
        "Pick a body location to amputate:\n\n"
        f"{listing}\n\n"
        "  x. Cancel\n\n"
        "|wWhich location?|n (number or name)"
    )
    options = ({"key": "_default", "goto": _process_amputate_location},)
    return text, options


def _process_amputate_location(caller, raw_string, **kwargs):
    raw = (raw_string or "").strip()
    if raw.lower() in ("x", "exit", "cancel"):
        return "node_top"
    if not raw:
        return None
    pick = _parse_pick(raw, caller.ndb._operate_pickable or [])
    if pick is None:
        caller.msg("|rPick a number from the list, or type the name.|n")
        return None
    _add_step_to_chart(caller, "amputate", {"location": pick})
    return "node_top"


# ===================================================================
# Harvest picker
# ===================================================================


def _node_harvest_organ(caller, raw_string, **kwargs):
    target = caller.ndb._operate_target
    organs = _list_organs(target)
    if not organs:
        caller.msg("|rNo harvestable organs on this target.|n")
        return "node_top"
    caller.ndb._operate_pickable = organs
    listing = _render_numbered(
        organs,
        lambda nc: f"{nc[0].replace('_', ' ').ljust(18)}  "
                   f"{MUTED}({nc[1].replace('_', ' ')})|n",
    )
    text = (
        "\n|wHarvest organ|n\n\n"
        "Pick an organ to harvest:\n\n"
        f"{listing}\n\n"
        "  x. Cancel\n\n"
        "|wWhich organ?|n (number or name)"
    )
    options = ({"key": "_default", "goto": _process_harvest_organ},)
    return text, options


def _process_harvest_organ(caller, raw_string, **kwargs):
    raw = (raw_string or "").strip()
    if raw.lower() in ("x", "exit", "cancel"):
        return "node_top"
    if not raw:
        return None
    pick = _parse_pick(raw, caller.ndb._operate_pickable or [])
    if pick is None:
        caller.msg("|rPick a number from the list, or type the organ name.|n")
        return None
    organ_name = pick[0]  # First tuple element is the organ name.
    _add_step_to_chart(caller, "harvest", {"organ_name": organ_name})
    return "node_top"


# ===================================================================
# Install picker — donor organ + target location
# ===================================================================


def _node_install_organ(caller, raw_string, **kwargs):
    donors = _list_donor_organs(caller)
    if not donors:
        caller.msg(
            "|rNo donor organs in your inventory.  Harvest one "
            "first, then re-enter operate to install.|n"
        )
        return "node_top"
    caller.ndb._operate_pickable = donors
    listing = _render_numbered(
        donors, lambda item_organ: item_organ[0].key,
    )
    text = (
        "\n|wInstall organ — pick the donor|n\n\n"
        "Pick which donor organ to install:\n\n"
        f"{listing}\n\n"
        "  x. Cancel\n\n"
        "|wWhich donor?|n (number or name)"
    )
    options = ({"key": "_default", "goto": _process_install_donor},)
    return text, options


def _process_install_donor(caller, raw_string, **kwargs):
    raw = (raw_string or "").strip()
    if raw.lower() in ("x", "exit", "cancel"):
        return "node_top"
    if not raw:
        return None
    donors = caller.ndb._operate_pickable or []
    # _parse_pick matches against the FIRST tuple element (Item key).
    # We need to match against item.key text; adapt by building a
    # name-keyed list for parse_pick.
    name_pairs = [
        (item.key, (item, name)) for item, name in donors
    ]
    if raw.isdigit():
        idx = int(raw) - 1
        if not (0 <= idx < len(name_pairs)):
            caller.msg("|rOut of range.|n")
            return None
        pick = name_pairs[idx][1]
    else:
        pick = None
        for key, payload in name_pairs:
            if raw.lower() in key.lower():
                pick = payload
                break
        if pick is None:
            caller.msg("|rNo donor matches.|n")
            return None
    item, organ_name = pick
    caller.ndb._operate_install_donor = item.key
    # Now ask for the install location.
    return "node_install_location"


def _node_install_location(caller, raw_string, **kwargs):
    target = caller.ndb._operate_target
    containers = _list_containers(target)
    donor_key = getattr(caller.ndb, "_operate_install_donor", "?")
    if not containers:
        caller.msg("|rNo install locations on this target.|n")
        return "node_top"
    caller.ndb._operate_pickable = containers
    listing = _render_numbered(
        containers, lambda loc: loc.replace("_", " "),
    )
    text = (
        f"\n|wInstall {donor_key} — pick the location|n\n\n"
        f"Pick where to install {donor_key}:\n\n"
        f"{listing}\n\n"
        "  x. Cancel\n\n"
        "|wWhich location?|n (number or name)"
    )
    options = ({"key": "_default", "goto": _process_install_location},)
    return text, options


def _process_install_location(caller, raw_string, **kwargs):
    raw = (raw_string or "").strip()
    if raw.lower() in ("x", "exit", "cancel"):
        return "node_top"
    if not raw:
        return None
    pick = _parse_pick(raw, caller.ndb._operate_pickable or [])
    if pick is None:
        caller.msg("|rPick a number or location name.|n")
        return None
    donor_key = getattr(caller.ndb, "_operate_install_donor", None)
    if not donor_key:
        caller.msg("|rDonor selection lost; please retry from the top.|n")
        return "node_top"
    _add_step_to_chart(
        caller, "install",
        {"organ_item_key": donor_key, "location": pick},
    )
    return "node_top"


# ===================================================================
# Suture picker
# ===================================================================


def _node_suture_location(caller, raw_string, **kwargs):
    target = caller.ndb._operate_target
    open_locs = set(_list_open_incisions(target))
    planned_locs = set(_list_planned_incisions(caller))
    stump_locs = set(_list_severed_locations(target))
    all_locs = sorted(open_locs | planned_locs | stump_locs)
    if not all_locs:
        text = (
            "\n|wSuture|n\n\n"
            "No incisions currently open and no incise steps in your "
            "chart.  Adding a 'suture all' step anyway — useful if you "
            "plan to add incise steps later.\n\n"
            "  |wEnter|n - add 'suture all' step\n"
            "  |wx|n     - Cancel"
        )
        options = (
            {"key": "_default", "goto": _process_suture_no_open},
        )
        return text, options

    # Label each entry with its source so the surgeon can see at
    # a glance which are live state vs planned-by-chart vs already-
    # severed (combat or prior procedure).
    options_list = [
        (f"|wall|n  {MUTED}(open + planned + stumps)|n",
         "all open incisions"),
    ]
    for loc in all_locs:
        humanized = loc.replace("_", " ")
        tags = []
        if loc in open_locs:
            tags.append("open")
        if loc in planned_locs:
            tags.append("planned")
        if loc in stump_locs:
            tags.append("stump")
        tag = f"{MUTED}({' + '.join(tags)})|n"
        options_list.append((f"{humanized}  {tag}", loc))

    caller.ndb._operate_pickable = options_list
    listing = "\n".join(
        f"  {idx}. {label}"
        for idx, (label, _val) in enumerate(options_list, start=1)
    )
    text = (
        "\n|wSuture|n\n\n"
        "Pick what to suture:\n\n"
        f"{listing}\n\n"
        "  x. Cancel\n\n"
        "|wWhich?|n (number or name)"
    )
    options = ({"key": "_default", "goto": _process_suture_location},)
    return text, options


def _process_suture_no_open(caller, raw_string, **kwargs):
    raw = (raw_string or "").strip().lower()
    if raw in ("x", "exit", "cancel"):
        return "node_top"
    _add_step_to_chart(caller, "suture", {})
    return "node_top"


def _process_suture_location(caller, raw_string, **kwargs):
    raw = (raw_string or "").strip()
    if raw.lower() in ("x", "exit", "cancel"):
        return "node_top"
    if not raw:
        return None
    options_list = caller.ndb._operate_pickable or []
    # Numeric index.
    if raw.isdigit():
        idx = int(raw) - 1
        if not (0 <= idx < len(options_list)):
            caller.msg("|rOut of range.|n")
            return None
        _label, val = options_list[idx]
    else:
        # Substring against display label.
        match = None
        for label, val in options_list:
            if raw.lower() in label.lower():
                match = val
                break
        if match is None:
            caller.msg("|rNo match.|n")
            return None
        val = match
    args = {} if val == "all open incisions" else {"location": val}
    _add_step_to_chart(caller, "suture", args)
    return "node_top"


def _add_step_to_chart(caller, verb: str, args: dict) -> None:
    """Add a step to the chart on the active target.

    Consults ``caller.ndb._operate_insert_before`` — when set by
    the edit-chart node's ``i <N>`` command, inserts the new step
    before the targeted step rather than appending.  The flag is
    cleared after consumption so the next "Add procedure step"
    invocation appends normally.

    Creates the chart on demand if absent.  Persists immediately.
    """
    target = caller.ndb._operate_target
    chart = chart_lib.get_chart(target) or chart_lib.new_chart(caller)
    before_id = getattr(caller.ndb, "_operate_insert_before", None)
    try:
        if before_id is not None:
            step = chart_lib.insert_step(
                chart, verb, args, before_id=before_id,
            )
        else:
            step = chart_lib.add_step(chart, verb, args)
    except ValueError as exc:
        caller.msg(f"|r{exc}|n")
        return
    chart_lib.save_chart(target, chart)
    summary = chart_lib.render_step_summary(step)
    if before_id is not None:
        caller.msg(f"|wStep inserted:|n {summary}")
        # Clear the insertion point so subsequent adds append.
        delattr(caller.ndb, "_operate_insert_before")
    else:
        caller.msg(f"|wStep added:|n {summary}")


# -------------------------------------------------------------------
# View / commence / save / discard
# -------------------------------------------------------------------


def _node_edit_chart(caller, raw_string, **kwargs):
    """Edit-chart node — view steps, reorder, remove, insert.

    Steps are listed with Roman-numeral indices.  Action commands
    are short prefix+number forms so editing is one keystroke per
    step shuffled:

      u <N>   move step N up
      d <N>   move step N down
      r <N>   remove step N
      i <N>   insert a new step before step N
      x       back to top

    Insertion routes into the same verb-pick flow as ``Add
    procedure step``; the insertion point is held on
    ``caller.ndb._operate_insert_before`` and consumed when the
    step is added.
    """
    target = caller.ndb._operate_target
    chart = chart_lib.get_chart(target)
    if not chart or not (chart.get("steps") or []):
        text = (
            "\n|wEdit chart|n\n\n"
            "The chart is empty.  Add steps from the top-level "
            "menu.\n\n"
            "|wEnter to return.|n"
        )
        options = ({"key": "_default", "goto": "node_top"},)
        return text, options
    parts = ["\n|wEdit chart|n\n"]
    for idx, step in enumerate(chart["steps"], start=1):
        roman = _roman(idx).rjust(4)
        summary = chart_lib.render_step_summary(step)
        status = step.get("status", "pending")
        outcome = step.get("outcome")
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
        line = f"  {roman}. {summary.ljust(36)} [{tag}]"
        if outcome:
            line += f"\n          └── {outcome}"
        parts.append(line)
    parts.append("")
    parts.append("|wActions|n  (lowercase):")
    parts.append("  |wu|n <N>    move step |wN|n up")
    parts.append("  |wd|n <N>    move step |wN|n down")
    parts.append("  |wr|n <N>    remove step |wN|n")
    parts.append("  |wi|n <N>    insert a new step before step |wN|n")
    parts.append("  |wx|n        back to top")
    parts.append("")
    parts.append("|wAction?|n")
    text = "\n".join(parts)
    options = ({"key": "_default", "goto": _process_edit_choice},)
    return text, options


def _process_edit_choice(caller, raw_string, **kwargs):
    raw = (raw_string or "").strip().lower()
    if raw in ("", "x", "exit", "back", "cancel"):
        return "node_top"

    parts = raw.split()
    if len(parts) != 2 or parts[0] not in ("u", "d", "r", "i"):
        caller.msg(
            "|rExpected: |wu N|r, |wd N|r, |wr N|r, |wi N|r, or |wx|r.|n"
        )
        return None

    cmd, num_str = parts
    try:
        num = int(num_str)
    except ValueError:
        caller.msg("|rN must be a number.|n")
        return None

    target = caller.ndb._operate_target
    chart = chart_lib.get_chart(target)
    if not chart:
        return "node_top"
    steps = chart.get("steps") or []
    if not (1 <= num <= len(steps)):
        caller.msg(f"|rNo step {num} in chart (1-{len(steps)}).|n")
        return None

    step = steps[num - 1]
    step_id = step["id"]

    if cmd == "u":
        if chart_lib.move_step(chart, step_id, -1):
            chart_lib.save_chart(target, chart)
            caller.msg(f"|wMoved step {num} up.|n")
        else:
            caller.msg("|yAlready at top.|n")
        return "node_edit_chart"

    if cmd == "d":
        if chart_lib.move_step(chart, step_id, +1):
            chart_lib.save_chart(target, chart)
            caller.msg(f"|wMoved step {num} down.|n")
        else:
            caller.msg("|yAlready at bottom.|n")
        return "node_edit_chart"

    if cmd == "r":
        if chart_lib.remove_step(chart, step_id):
            chart_lib.save_chart(target, chart)
            caller.msg(f"|wRemoved step {num}.|n")
        return "node_edit_chart"

    if cmd == "i":
        # Stash the insertion point and route into the verb-pick
        # flow.  ``_add_step_to_chart`` reads
        # ``_operate_insert_before`` and uses ``insert_step``
        # instead of ``add_step``.
        caller.ndb._operate_insert_before = step_id
        return "node_add_verb"

    return None


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
    # Exit cleanly — empty text + None options is EvMenu's "close
    # without re-prompting" signal.  Returning the string
    # ``"node_exit"`` from a *node* function would be rendered as
    # display text, not interpreted as a goto.
    return "", None


def _node_save_exit(caller, raw_string, **kwargs):
    target = caller.ndb._operate_target
    chart = chart_lib.get_chart(target)
    if chart is None:
        caller.msg("No chart to save.")
    else:
        chart_lib.save_chart(target, chart)
        caller.msg("|wChart saved on patient.|n")
    # Empty text + None options exits cleanly — see note in
    # ``_node_commence`` above.
    return "", None


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
                "node_install_location": _node_install_location,
                "node_suture_location":  _node_suture_location,
                "node_amputate_location":_node_amputate_location,
                "node_edit_chart":       _node_edit_chart,
                "node_commence":         _node_commence,
                "node_save_exit":        _node_save_exit,
                "node_discard_confirm":  _node_discard_confirm,
                "node_exit":             _node_exit,
            },
            startnode="node_top",
            cmd_on_exit=_menu_exit,
        )
