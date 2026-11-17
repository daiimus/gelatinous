# EvMenu Pattern Reference Specification

## Document Status
- **Version:** 1.0 REFERENCE
- **Date:** October 14, 2025
- **Status:** Canonical Reference Guide
- **Context:** Flash Cloning System character creation menu implementation

---

## Overview

This specification documents the correct patterns for implementing text-input nodes in Evennia's EvMenu system. These patterns were discovered through trial and error while implementing the Flash Cloning character creation system, which revealed two bugs that illuminate EvMenu's non-obvious behavior.

**Purpose:** Serve as the canonical reference for all future EvMenu implementations in this project.

---

## Critical Bugs Discovered

When implementing text-input nodes in EvMenu (where users type freeform text rather than selecting numbered options), we encountered two bugs that revealed important EvMenu behavior patterns.

---

## Bug #1: Blank Input Processing

**Symptom:**
```
Press <Enter> to begin character creation.
> [user presses Enter]
Invalid name: Name must be 2-30 characters.
```

**Root Cause:**
```python
def node(caller, raw_string, **kwargs):
    if raw_string:  # ❌ WRONG - whitespace-only input still triggers this
        # Process input
```

**The Issue:** `if raw_string:` is `True` for whitespace-only input such as a single space, which then gets validated as a name. Checking `raw_string and raw_string.strip()` makes blank or whitespace-only input show the prompt instead.

**Solution:**
```python
def node(caller, raw_string, **kwargs):
    if raw_string and raw_string.strip():  # ✅ CORRECT
        # Process input - only when actual text entered
```

---

## Bug #2: Node Transition During Input Processing

**Symptom:**
```
What is your FIRST name?
> Akumamitsu
first_char_name_last    ← Debug output of node name!

> Wakka
Command 'Wakka' is not available.  ← Menu exited!
```

**Root Cause:**
```python
def first_char_name_first(caller, raw_string, **kwargs):
    if raw_string and raw_string.strip():
        # Validate and store
        caller.ndb.data['first_name'] = raw_string.strip()
        return "first_char_name_last"  # ❌ WRONG!
    
    text = "What is your FIRST name?"
    options = ({"key": "_default", "goto": "first_char_name_first"},)
    return text, options
```

**The Issue:** When a node function returns a string, EvMenu:
1. **Displays that string as the node text** (which is why we saw "first_char_name_last" printed)
2. **Exits the menu**, because the node has no options (which is why the next input became a command)

**Why This Happens:**
- A node function must return `(text, options)`. If it returns a bare string, EvMenu shows that string as the node text, finds no options, and closes the menu. If it returns `None`, the menu also closes. This holds whatever `raw_string` contains.
- Only a goto-callable (an option's `goto` that is a function) may return a node name, to go to that node, or `None`, to re-display the current node.
- The "input" and "display" branches inside a node are this project's convention for nodes that are their own `_default` target, not something EvMenu provides.

**Solution - Pattern #1: Call the node itself to re-display**
```python
# ⚠️ WARNING: return None actually EXITS the menu!
# Use recursive call instead:
def node(caller, raw_string, **kwargs):
    if raw_string and raw_string.strip():
        # Validate
        if not valid:
            caller.msg("Error message")
            return node(caller, "", **kwargs)  # ✅ Re-displays current node
```

**Solution - Pattern #2: Call Next Node Directly**
```python
def node(caller, raw_string, **kwargs):
    if raw_string and raw_string.strip():
        # Validate and store
        caller.ndb.data['field'] = raw_string.strip()
        
        # Call next node function directly
        return next_node(caller, "", **kwargs)  # ✅ CORRECT
    
    text = "Prompt text"
    options = ({"key": "_default", "goto": "node"},)
    return text, options
```

---

## The Correct Patterns

### Pattern A: Numbered Menu with Goto-Callable

**Use Case:** Menu with numbered options, input routing via separate function.

```python
def menu_node(caller, raw_string, **kwargs):
    """Display menu with options."""
    text = """
Choose an option:
[1] Option 1
[2] Option 2
"""
    options = (
        {"key": "_default", "goto": process_choice},  # Callable, not string!
    )
    return text, options

def process_choice(caller, raw_string, **kwargs):
    """Process user's choice."""
    choice = raw_string.strip()
    
    if choice == "1":
        return "option1_node"  # OK - goto-callable can return node name
    elif choice == "2":
        return "option2_node"
    else:
        caller.msg("Invalid choice")
        return None  # Re-display menu
```

### Pattern B: Text Input Node (Self-Processing)

**Use Case:** Freeform text input (names, descriptions, etc.)

```python
def text_input_node(caller, raw_string, **kwargs):
    """Get text input from user."""
    
    # Input mode - process user's text
    if raw_string and raw_string.strip():
        text = raw_string.strip()
        
        # Validate
        if not is_valid(text):
            caller.msg("|rError: Invalid input|n")
            # Re-display this node; a node that returns None closes the menu.
            return text_input_node(caller, "", **kwargs)
        
        # Store and advance
        caller.ndb.data['field'] = text
        return next_input_node(caller, "", **kwargs)  # ✅ Call next node
    
    # Display mode - show prompt
    text = "|wEnter text:|n"
    options = (
        {"key": "_default", "goto": "text_input_node"},
    )
    return text, options
```

### Pattern C: Command Parser Node

**Use Case:** Multiple commands in one node (e.g., GRIM stat distribution)

```python
def command_parser_node(caller, raw_string, **kwargs):
    """Process multiple command types."""
    
    # Input mode
    if raw_string and raw_string.strip():
        args = raw_string.strip().lower().split()
        
        # Re-display by calling this node; a node that returns None
        # closes the menu.
        if not args:
            return command_parser_node(caller, "", **kwargs)
        
        command = args[0]
        
        # Command: done - advance to next node
        if command == "done":
            if not validate_state():
                caller.msg("|rNot ready yet|n")
                return command_parser_node(caller, "", **kwargs)
            return next_node(caller, "", **kwargs)  # ✅ Advance
        
        # Command: reset - modify state and re-display
        elif command == "reset":
            reset_values()
            return command_parser_node(caller, "", **kwargs)  # ✅ Re-display with reset values
        
        # Command: set value - modify state and re-display
        elif command in ["stat1", "stat2"]:
            if len(args) < 2:
                caller.msg("|rUsage: stat <value>|n")
                return command_parser_node(caller, "", **kwargs)
            try:
                value = int(args[1])
                caller.ndb.data[command] = value
            except ValueError:
                caller.msg("|rValue must be a number|n")
            return command_parser_node(caller, "", **kwargs)  # ✅ Re-display with new values
        
        # Anything else is ignored, not rejected: fall through and display.
    
    # Display mode
    stat1 = caller.ndb.data.get('stat1', 0)
    stat2 = caller.ndb.data.get('stat2', 0)
    
    text = f"""
Stat1: {stat1}
Stat2: {stat2}

Commands: stat1 <value>, stat2 <value>, reset, done
"""
    options = (
        {"key": "_default", "goto": "command_parser_node"},
    )
    return text, options
```

A node reached by a goto receives the input that chose it as `raw_string` (for example the `3` typed at the previous menu). A self-processing node therefore ignores input it does not recognise and simply displays; it does not reject it. `first_char_grim` in `commands/charcreate.py` does this.

### Pattern D: Multi-Source Picker with Status Tags

**Use Case:** Location / target pickers whose entries come from more than one underlying source — e.g. surgery's suture picker (open incisions + planned chart steps + severed-organ stumps), the install picker (species-valid slots tagged occupied/empty). Each source contributes the same kind of entry; tags on each row tell the player *why* an entry is there.

**Use case characteristics:**

* Picker draws from N independent data sources, each potentially contributing the same location/value. (The amputate picker is single-source: `severable_containers` already drops severed containers, and its rows carry no tags.)
* When a single value has multiple sources, the row should tag *all* of them (`(open + planned)`) rather than appear N times.
* An "all" sentinel entry up top lets the player apply the verb without picking one.
* Empty-source path needs its own handling — when every source is empty, the menu either offers a sentinel action or short-circuits with an explanation rather than rendering an empty list.

**Reference implementation:** `commands/CmdOperate.py` → `_node_suture_location`, drawing from `_list_open_incisions` (live surgical state) + `_list_planned_incisions` (locations of pending `incise` and `amputate` chart steps, since both leave an open wound) + `_list_severed_locations` (severed-organ stumps inferred from the medical state).

```python
def _node_picker(caller, raw_string, **kwargs):
    target = caller.ndb._operate_target

    # Pull each source as a set so union / membership is cheap.
    open_locs    = set(_list_open_incisions(target))
    planned_locs = set(_list_planned_incisions(caller))
    stump_locs   = set(_list_severed_locations(target))
    all_locs     = sorted(open_locs | planned_locs | stump_locs)

    # Empty-source fall-through.  Offer the sentinel directly so the
    # surgeon can still author a "suture all" step that'll find
    # incisions later if/when they exist.
    if not all_locs:
        text = (
            "\n|wSuture|n\n\n"
            "No incisions currently open and no incise steps in your "
            "chart.  Adding a 'suture all' step anyway — useful if you "
            "plan to add incise steps later.\n\n"
            "  |wEnter|n - add 'suture all' step\n"
            "  |wx|n     - Cancel"
        )
        options = ({"key": "_default", "goto": _process_picker_no_open},)
        return text, options

    # Build the option list.  Index 0 is the "all" sentinel; subsequent
    # entries are individual picker targets with tags assembled
    # union-style from all matching sources.
    # Entries are (value, label), value first.
    options_list = [
        (SUTURE_ALL,  # SUTURE_ALL = "all"
         f"|wall|n  {MUTED}(open + planned + stumps)|n"),
    ]
    for loc in all_locs:
        tags = []
        if loc in open_locs:    tags.append("open")
        if loc in planned_locs: tags.append("planned")
        if loc in stump_locs:   tags.append("stump")
        tag = f"{MUTED}({' + '.join(tags)})|n"
        options_list.append((loc, f"{loc.replace('_', ' ')}  {tag}"))

    # Persist on ndb so the processor can resolve the surgeon's pick.
    caller.ndb._operate_pickable = options_list
    listing = "\n".join(
        f"  {idx}. {label}"
        for idx, (_val, label) in enumerate(options_list, start=1)
    )
    text = (
        "\n|wSuture|n\n\n"
        "Pick what to suture:\n\n"
        f"{listing}\n\n"
        "  x. Cancel\n\n"
        "|wWhich?|n (number or name)"
    )
    options = ({"key": "_default", "goto": _process_picker},)
    return text, options
```

Picker entries are always `(value, label)`, value first, and the value is the single word a player would type (`all`, not a phrase). `_parse_pick` matches against the value, never the coloured label (#2553).

**The processor unpacks `(value, label)`.** When a typed name matches more than one entry, `_parse_pick` returns `_Several` and the processor asks which one was meant, following the ruling recorded in `_parse_pick`'s docstring: "Owner ruling 2026-08-24: never guess" (#2276). Every live caller passes the target's species.

```python
def _process_picker(caller, raw_string, **kwargs):
    raw = (raw_string or "").strip()
    if raw.lower() in ("x", "exit", "cancel"):
        return "node_top"
    if not raw:
        return None
    species = _species_of_target(caller)
    pick = _parse_pick(raw, caller.ndb._operate_pickable or [], species)
    if isinstance(pick, _Several):
        caller.msg(f"|wWhich did you mean?|n {_name_picks(pick, species)}.")
        return None
    if pick is None:
        caller.msg("|rPick a number or location name.|n")
        return None
    # Pickable entries are (value, label) tuples — take the value.
    value = pick[0] if isinstance(pick, tuple) else pick
    # ... record the chart step / fire the action ...
    return "node_top"
```

**Status-tag conventions:**

* Tag text wraps in `MUTED` (the orange `|520` accent code) so it visually de-emphasises beside the location name.
* Multiple-source tags collapse with `" + "` so `open + planned` reads naturally.
* The sentinel "all" row's tag describes the *broadest* set the action covers (`(open + planned + stumps)`).

**Sources can be derived from any state.** The suture picker's "stump" source consults the medical state directly — `_list_severed_locations` reads `compute_cut_points` from the severance module so combat-driven amputation (which never goes through the chart) still surfaces. It subtracts stumps already sutured (`normalize_sutured_stumps`), so only untreated stumps appear. Picker design should ask *"what's the real source of truth for this entry?"* rather than enumerating the obvious surface (e.g. just open incisions). Multi-source pickers are the way to bridge surfaces that don't share a single backing store.

**Testing.** Each source contributes via its own helper; the picker node is then a thin composition. Test the helpers individually and add a single node-level test for each *combination* you care about (a row that's both open and stump should tag both). See `world/tests/test_operate_menu.py` `SutureLocationPicker` for the regression-history-grounded pattern: each historical bug in the picker became one test.

---

## Key Takeaways

### ✅ DO:
- Check `if raw_string and raw_string.strip():` for text input validation
- Return recursive call to re-display current node: `return current_node(caller, "", **kwargs)`
- Call next node function directly when advancing: `return next_node(caller, "", **kwargs)`
- Use goto-callables for menu option routing (they can return node name strings)
- Turn off EvMenu's built-in `q`/`look`/`help` by passing `auto_quit=False, auto_look=False, auto_help=False` to the EvMenu constructor (see `_NO_MENU_BUILTINS` in `commands/charcreate.py`). Put in an option dict, they do nothing (#2551).
- When the node text already lists the options, override `options_formatter` to return an empty string, as `CharCreateEvMenu` does.

### ❌ DON'T:
- Check just `if raw_string:` (whitespace-only input passes it)
- Return node name string during input processing: `return "node_name"`
- Return `None` from a node function (this EXITS the menu, doesn't re-display!). Only a goto-callable may return `None` to re-display.
- Forget to pass empty string when calling nodes: `node(caller, "", **kwargs)`

### 🔍 Debugging:
If you see node names appearing as text output, you're returning a string during input processing instead of calling the node function.

This applies to any return from a node, not only during input processing: a node with nothing to list must return another node's output (`return _node_top(caller, raw_string, **kwargs)` in `commands/CmdOperate.py`), never its name. `world/tests/test_operate_nodes_never_print_their_goto.py` shows how to test this: assert that the node returns a tuple.

> Nine node returns in `commands/charcreate.py` still hand EvMenu a bare
> node name, which prints the name and closes the menu. For an account with
> no active sleeve (respawning accounts included, since their sleeves are
> archived), `_charcreate_exit_callback` then disconnects the session that
> ran the menu, if it is still connected:
>
> * `first_char_finalize`: `return "first_char_name_first"` when the name was
>   taken, and `return "first_char_confirm"` on any other creation error. The
>   first is the #2550 route back to the name prompt; it prints
>   `first_char_name_first` and ends the session instead.
>   `world/tests/test_chargen_name_check_can_fire.py` tests `validate_name`
>   only, never the route.
> * `respawn_confirm_template`: a bad template index.
> * `respawn_finalize_template`: no template, no session, creation error.
> * `respawn_flash_clone`: no old character, no session, creation error. Its
>   refused-policy branch is correct: it re-displays with
>   `return respawn_welcome(caller, "")`.
>
> These are code defects; the fix is 📋 UNBUILT (no issue). The correct
> re-display is the recursion `first_char_grim` uses, or a goto-callable. Do not read this note
> as blessing any of the nine.

---

## Implementation Checklist

When creating a new EvMenu text-input node:

- [ ] Input validation checks `if raw_string and raw_string.strip():`
- [ ] Errors re-display by calling the node itself: `return this_node(caller, "", **kwargs)`. Never `return None` from a node; that closes the menu. `None` means "re-display" only when a goto-callable returns it.
- [ ] Successful input calls next node: `return next_node(caller, "", **kwargs)`
- [ ] Display mode returns `(text, options)` tuple
- [ ] Options include `{"key": "_default", "goto": "<this node's own name>"}`
- [ ] Tested: blank input doesn't trigger validation
- [ ] Tested: valid input advances to next node
- [ ] Tested: invalid input re-displays with error message

---

## Fixed Files

**Date:** October 14, 2025  
**Files Modified:** `commands/charcreate.py`

**Nodes Fixed:**
- `first_char_name_first()` - Text input with validation
- `first_char_name_last()` - Text input with validation
- `first_char_grim()` - Command parser with multiple commands

**Pattern Applied:** Pattern B (text input) and Pattern C (command parser)

---

*This document should be consulted when implementing any future EvMenu systems requiring text input.*
