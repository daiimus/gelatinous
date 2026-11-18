# EvMenu Pattern Reference Specification

## Overview

This is the project's reference for writing EvMenu nodes, above all text-input nodes, where the player types freeform text rather than picking a numbered option. It covers how EvMenu treats what a node returns, the four node shapes the project uses (A to D), and the rules every new EvMenu menu follows. Character creation (`commands/charcreate.py`) and the surgery menu (`commands/CmdOperate.py`) are the working examples.

---

## How EvMenu treats a node's return

- **A node function must return `(text, options)`.** If it returns a bare string, EvMenu shows that string as the node text, finds no options, and closes the menu. If it returns `None`, the menu also closes. This holds whatever `raw_string` contains.
- **Only a goto-callable** (an option's `goto` that is a function) may return a node name, to go to that node, or `None`, to re-display the current node.
- **A node reached by a goto receives the input that chose it as `raw_string`** (for example the `3` typed at the previous menu). A self-processing node therefore ignores input it does not recognise and simply displays; it does not reject it. `first_char_grim` in `commands/charcreate.py` does this.
- The "input" and "display" branches inside a node are this project's convention for nodes that are their own `_default` target, not something EvMenu provides.

### What a player sees when a node returns a name

If a node returns a node name instead of calling that node, the player reads the name as text, and the menu is gone, so their next input is read as a command:

```
What is your FIRST name?
> <first name>
first_char_name_last

> <last name>
Command '<last name>' is not available.
```

### Blank input

`if raw_string:` is `True` for whitespace-only input such as a single space, which then gets validated as input (for a name prompt, as a name). On the name prompt the player then reads `Invalid name: Name must be 2-30 characters.` instead of the prompt. Checking `raw_string and raw_string.strip()` makes blank or whitespace-only input show the prompt instead.

```python
def node(caller, raw_string, **kwargs):
    if raw_string and raw_string.strip():
        # Process input - only when actual text entered
```

### Re-displaying and advancing from a node

- To re-display the current node (after an error, say), the node calls itself with an empty string and returns the result: `return node(caller, "", **kwargs)`.
- To advance, the node calls the next node function directly and returns its result: `return next_node(caller, "", **kwargs)`.
- Either way, pass `""` as `raw_string`.

---

## The Correct Patterns

### Pattern A: Numbered Menu with Goto-Callable

**Use Case:** Menu with numbered options, input routing via a separate function. The `_default` option's `goto` is a function, not a string; that function returns a node name to go there, or `None` to re-display the menu.

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

**Use Case:** Freeform text input (names, descriptions, etc.). `first_char_name_first` and `first_char_name_last` in `commands/charcreate.py` follow it.

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
        return next_input_node(caller, "", **kwargs)  # Call next node

    # Display mode - show prompt
    text = "|wEnter text:|n"
    options = (
        {"key": "_default", "goto": "text_input_node"},
    )
    return text, options
```

### Pattern C: Command Parser Node

**Use Case:** Multiple commands in one node (e.g., GRIM stat distribution, `first_char_grim` in `commands/charcreate.py`). Each command either advances (`done`, once the state is valid) or changes state and re-displays; a usage or value error prints a message and re-displays. Anything that is not a command is ignored, not rejected: the node falls through and displays.

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
            return next_node(caller, "", **kwargs)  # Advance

        # Command: reset - modify state and re-display
        elif command == "reset":
            reset_values()
            return command_parser_node(caller, "", **kwargs)  # Re-display with reset values

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
            return command_parser_node(caller, "", **kwargs)  # Re-display with new values

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

### Pattern D: Multi-Source Picker with Status Tags

**Use Case:** Location / target pickers whose entries come from more than one underlying source — e.g. surgery's suture picker (open incisions + planned chart steps + severed-organ stumps), the install picker (species-valid slots tagged occupied/empty). Each source contributes the same kind of entry; tags on each row tell the player *why* an entry is there.

**Use case characteristics:**

* Picker draws from N independent data sources, each potentially contributing the same location/value. (The amputate picker is single-source: `severable_containers` already drops severed containers, and its rows carry no tags.)
* When a single value has multiple sources, the row should tag *all* of them (`(open + planned)`) rather than appear N times.
* An "all" sentinel entry up top lets the player apply the verb without picking one.
* Empty-source path needs its own handling — when every source is empty, the menu either offers a sentinel action or short-circuits with an explanation rather than rendering an empty list.

**Reference implementation:** `commands/CmdOperate.py` → `_node_suture_location`, drawing from `_list_open_incisions` (live surgical state) + `_list_planned_incisions` (locations of pending `incise` and `amputate` chart steps, since both leave an open wound) + `_list_severed_locations` (severed-organ stumps inferred from the medical state).

**The node.** `_node_suture_location` reads each source as a set and takes the sorted union. The heading, `all`, `Which?` and the `Enter`/`x` keys are bold white (`|w`); every tag is in `MUTED`.

* When the union is empty, it offers the sentinel directly, so the surgeon can still author a "suture all" step that will find incisions later if they exist. Its `_default` goto is `_process_suture_no_open` (a goto-callable). The player reads:

  ```
  Suture

  No incisions currently open and no incise steps in your chart.  Adding a 'suture all' step anyway — useful if you plan to add incise steps later.

    Enter - add 'suture all' step
    x     - Cancel
  ```

* Otherwise it builds the entry list. Entry 1 is the "all" sentinel (`SUTURE_ALL`, the value `"all"`), labelled `all  (open + planned + stumps)`. Each location after it is labelled with its name (underscores as spaces) and a tag naming every source it came from, in the order open, planned, stump. It stores the list on `caller.ndb._operate_pickable`, so the processor can resolve the pick, and its `_default` goto is the processor (a goto-callable). The player reads:

  ```
  Suture

  Pick what to suture:

    1. all  (open + planned + stumps)
    2. <location>  (<tags>)
    ...

    x. Cancel

  Which? (number or name)
  ```

Picker entries are always `(value, label)`, value first, and the value is the single word a player would type (`all`, not a phrase). `_parse_pick` matches against the value, never the coloured label (#2553).

**The processor unpacks `(value, label)`.** When a typed name matches more than one entry, `_parse_pick` returns `_Several` and the processor asks which one was meant, following the ruling recorded in `_parse_pick`'s docstring: "Owner ruling 2026-08-24: never guess" (#2276). Every live caller passes the target's species. The suture processor, `_process_suture_location`, in order:

1. `x`, `exit` or `cancel` returns to `node_top`.
2. Blank input returns `None` (re-display).
3. Several matches: the player reads `Which did you mean? <names>.` (`_name_picks`, given the target's species), and the picker re-displays.
4. No match: the player reads `Pick a number or location name.` and the picker re-displays.
5. Otherwise it takes the entry's value, records the chart step or fires the action, and returns to `node_top`.

**Status-tag conventions:**

* Tag text wraps in `MUTED` (the orange `|520` accent code) so it visually de-emphasises beside the location name.
* Multiple-source tags collapse with `" + "` so `open + planned` reads naturally.
* The sentinel "all" row's tag describes the *broadest* set the action covers (`(open + planned + stumps)`).

**Sources can be derived from any state.** The suture picker's "stump" source consults the medical state directly — `_list_severed_locations` reads `compute_cut_points` from the severance module so combat-driven amputation (which never goes through the chart) still surfaces. It subtracts stumps already sutured (`normalize_sutured_stumps`), so only untreated stumps appear. Picker design should ask *"what's the real source of truth for this entry?"* rather than enumerating the obvious surface (e.g. just open incisions). Multi-source pickers are the way to bridge surfaces that don't share a single backing store.

**Testing.** Each source contributes via its own helper; the picker node is then a thin composition. Test the helpers individually and add a single node-level test for each *combination* you care about (a row that's both open and stump should tag both). `world/tests/test_operate_menu.py` `SutureLocationPicker` follows this pattern: each bug found in the picker became one test.

---

## Key Takeaways

### DO:
- Check `if raw_string and raw_string.strip():` for text input validation.
- Return a recursive call to re-display the current node: `return current_node(caller, "", **kwargs)`.
- Call the next node function directly when advancing: `return next_node(caller, "", **kwargs)`.
- Use goto-callables for menu option routing (they can return node name strings).
- Turn off EvMenu's built-in `q`/`look`/`help` by passing `auto_quit=False, auto_look=False, auto_help=False` to the EvMenu constructor (see `_NO_MENU_BUILTINS` in `commands/charcreate.py`). Put in an option dict, they do nothing (#2551).
- When the node text already lists the options, override `options_formatter` to return an empty string, as `CharCreateEvMenu` does.

### DON'T:
- Check just `if raw_string:` (whitespace-only input passes it).
- Return a node name string from a node: `return "node_name"`.
- Return `None` from a node function (this EXITS the menu, doesn't re-display). Only a goto-callable may return `None` to re-display.
- Forget to pass an empty string when calling nodes: `node(caller, "", **kwargs)`.

### Debugging:
If you see node names appearing as text output, a node is returning a string instead of calling the node function.

This applies to any return from a node, not only during input processing: a node with nothing to list must return another node's output (`return _node_top(caller, raw_string, **kwargs)` in `commands/CmdOperate.py`), never its name. `world/tests/test_operate_nodes_never_print_their_goto.py` shows how to test this: assert that the node returns a tuple.

---

## Implementation Checklist

When creating a new EvMenu text-input node:

- Input validation checks `if raw_string and raw_string.strip():`
- Errors re-display by calling the node itself: `return this_node(caller, "", **kwargs)`. Never `return None` from a node; that closes the menu. `None` means "re-display" only when a goto-callable returns it.
- Successful input calls the next node: `return next_node(caller, "", **kwargs)`
- Display mode returns a `(text, options)` tuple
- Options include `{"key": "_default", "goto": "<this node's own name>"}`
- Test that blank input doesn't trigger validation
- Test that valid input advances to the next node
- Test that invalid input re-displays with an error message

---

## Unbuilt

### Nine node returns in `commands/charcreate.py` hand EvMenu a bare node name

📋 UNBUILT (no issue): the fix.

Nine node returns in `commands/charcreate.py` still hand EvMenu a bare node name, which prints the name and closes the menu. For an account with no active sleeve (respawning accounts included, since their sleeves are archived), `_charcreate_exit_callback` then disconnects the session that ran the menu, if it is still connected:

* `first_char_finalize`: `return "first_char_name_first"` when the name was taken, and `return "first_char_confirm"` on any other creation error. The first is the #2550 route back to the name prompt; it prints `first_char_name_first` and ends the session instead. `world/tests/test_chargen_name_check_can_fire.py` tests `validate_name` only, never the route.
* `respawn_confirm_template`: a bad template index.
* `respawn_finalize_template`: no template, no session, creation error.
* `respawn_flash_clone`: no old character, no session, creation error. Its refused-policy branch is correct: it re-displays with `return respawn_welcome(caller, "")`.

These are code defects. The correct re-display is the recursion `first_char_grim` uses, or a goto-callable. Do not read this note as blessing any of the nine.

---

## Related documents

- [HEALTH_AND_SUBSTANCE_SYSTEM_SPEC.md](HEALTH_AND_SUBSTANCE_SYSTEM_SPEC.md): the `operate` menu, whose pickers follow Pattern D.
- [SLEEVE_INSURANCE_SPEC.md](SLEEVE_INSURANCE_SPEC.md): the respawn refusal path in `respawn_flash_clone`.
- [NEW_PLAYER_EXPERIENCE_SPEC.md](NEW_PLAYER_EXPERIENCE_SPEC.md): character creation.
