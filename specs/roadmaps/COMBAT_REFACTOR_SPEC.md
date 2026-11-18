# Combat System Refactor Specification

This roadmap orders the remaining refactor of the combat package, `world/combat/`. The aim is to turn the two oversized modules, `handler.py` and `utils.py`, into small modules with one responsibility each. Nothing here changes how combat plays. Every item below is work not yet done; none has an open issue.

Diagnostics routing is not part of this roadmap: all combat diagnostics go through the single sink in `world/combat/debug.py`, described in `COMBAT_AUDIT_LOGGING_SPEC.md`.

## Why

- **Two monoliths.** `handler.py` and `utils.py` are each far over the size a model can hold and reason about at once. Measure with `wc -l world/combat/*.py`.
- **Cross-file duplication.** The same patterns are written out again in many files:
  - Contests: opposed `randint` rolls are inline in `attack.py`, `actions.py`, `grappling.py` and `movement_resolution.py`, and `dice.py` has two dice styles. `handler.py` has no `randint` and no `motorics`; `utils.py` has one initiative roll, in `add_combatant`.
  - Debug messages: 273 `splattercast.msg` calls across the package, 119 of them in `handler.py` (78) and `utils.py` (41).
  - Attribute access: defensive `getattr` patterns in both files.
- **Utility dumping ground.** `utils.py` is a catch-all with mixed responsibilities. In order it holds: imports; the BACKWARD-COMPATIBLE RE-EXPORTS block (`debug`, `dice`, `explosives`, then `proximity`); weapon and item helpers (`find_best_weapon`, `get_weapon_damage`); the initiative bonus (`surplus_limb_initiative_bonus`); display-name, stat and aim-state helpers; `add_combatant` and `remove_combatant`; cleanup, handler-reference, dbref and orphan-sweep helpers; `resolve_bonus_attack`.
- **Method bloat** and **inconsistent patterns**: oversized methods remain, and the same operation is done different ways in different files.

**Root cause.** The code was built by a language model, feature by feature: additions made without architectural consideration, a context window too small to see the whole, a tendency to duplicate a pattern rather than extract a function, and limited ability to refactor across large files.

## Design goals

1. **Separation of concerns**: each module has a single responsibility.
2. **DRY**: no repeated patterns.
3. **LLM-friendly structure**: small, focused files that fit in a context window.
4. **Testability**: isolated functions that can be tested on their own.
5. **Maintainability**: clear interfaces and minimal coupling.

### Targets

- `handler.py` under 500 lines, orchestration only.
- `utils.py` eliminated: broken into focused modules.
- Every file under 300 lines. 10 of the 15 combat modules exceed it today; `__init__.py`, `dice.py`, `debug.py`, `capacity.py` and `weapon_choice.py` are under it.
- No code duplication: zero repeated patterns across all files.
- Fewer than 10 debug messages per file. Today: `handler.py` 78, `utils.py` 41, `movement_resolution.py` 38, `grappling.py` 35, `attack.py` 35, `throwing.py` 31, `actions.py` 12. None of the 273 calls has been removed.
- Defensive attribute access eliminated: 142 lines in `handler.py` and `utils.py` match `getattr(`, `hasattr(` or `.get(`.
- Combatant-entry lookups standardized: 9 remain, and there is no `find_combatant_entry()`.
- Error handling consolidated: 18 `except Exception` blocks remain in `handler.py` and `utils.py`.
- Function signatures standardized: `handler.py` has 35 methods and 2 module-level functions (`find_combat_handlers`, `get_or_create_combat`); `utils.py` has 27 module-level functions.
- The six-plus dice rolling patterns unified.
- 90%+ test coverage for extracted functions (unmeasured).
- Clear separation: orchestration vs implementation vs utilities.

Qualitative goals: clear separation of concerns; LLM-maintainable file sizes; consistent interfaces and naming; robust error handling and defensive programming; configurable combat parameters; better readability and debugging.

## Target layout

| Module | Responsibility | Key functions |
|---|---|---|
| `handler.py` | Combat round orchestration, script lifecycle, handler merging, combat state validation triggers | `at_repeat` |
| `attack.py` | Attack resolution, human shield | `process_attack`, `process_delayed_attack` |
| `movement_resolution.py` | Retreat, advance, charge | `resolve_retreat`, `resolve_advance`, `resolve_charge` |
| `actions.py` | Disarm and auto-escape | `resolve_disarm`, `resolve_auto_escape` |
| `grappling.py` | Grapple resolution and grapple state | `resolve_grapple_initiate`, `resolve_grapple_join`, `resolve_grapple_takeover`, `resolve_release_grapple` |
| `weapon_choice.py` | Weapon selection and hand access | `choose_weapon`, `weapon_options`, `has_ranged_option` |
| `debug.py` | Combat audit log sink | `get_splattercast` |
| `dice.py` | Dice rolls | `roll_stat`, `opposed_roll`, `standard_roll`, `roll_with_advantage`, `roll_with_disadvantage` |
| `explosives.py` | Sticky grenades, blast human shields | |
| `throwing.py` | Throw flight and landing | |
| `capacity.py` | Body capacities (sight) in hit math | |
| `proximity.py` | Proximity system | |
| `constants.py` | Shared constants | |
| `contest_system.py` | Contest mechanics: motorics rolls, opposed checks | to create (Phase 1A) |
| `state_manager.py` | State manipulation, combatant entry management | to create (Phase 1C) |
| `weapon_utilities.py` | Weapon access, validation | to create (Phase 2B) |
| `character_attributes.py` | Safe attribute access (defensive patterns) | to create (no phase) |

## How the work is done

These rules set the order and the size of each step.

- **Incremental extraction, validated at each step.** Order: extract repeated patterns first (safest, highest value), then simplify the handler structure (highest risk, essential for maintainability).
- **File size limit**: under 300 lines per file. Count lines before each change; if a file grows past 300, split it by responsibility.
- **Single change rule**: one type of extraction per session and per commit (for example, all motorics contests or debug logging, not both). Reason: it prevents overwhelming changes that lead to errors.
- **Documentation first**: specify before implementing.
- **Always keep a working system.**
- **One target file at a time.** Read it completely, find every instance of the pattern, extract to a new function with precise imports, then replace every instance, safest and most isolated first.
- **Steps for one extraction:**
  1. Identify the repeated block and count every instance across files, with its variations.
  2. Design the function signature to cover every existing variation and every error case in the originals.
  3. Extract it to the right module (a new file if needed) with imports and docstrings.
  4. Replace one instance, the safest; test in game with that action.
  5. Replace the rest; test in game after every 3 to 5 replacements.
  6. Remove the old code and update imports.
  7. Test a full combat round with all action types (grapple, attack, movement, escapes, disarms), check the file size, confirm in the debug log that the new functions work, and verify combat behaves as before.
- **Testing**: run the combat tests in `world/tests/` (for example `test_combat_audit_sink.py`, `test_peace_ends_multi_room_combat.py`) after each extraction. Every change also needs in-game combat testing.
- **Imports**: add them one at a time and test each.
- **Signatures**: keep parameters simple and explicit; carry over the error cases of the original code.
- **Backward compatibility**: maintain existing interfaces during the transition; keep original functions until they are fully replaced.

### High-risk areas

1. SaverList manipulation: database corruption risk.
2. Grapple state changes: complex two-way relationships.
3. Handler merging: coordination between several handlers.
4. Combat round processing: the core game loop.

Mitigation: start with the safest patterns (the contest system); test after each small change; commit working states often.

## Order of work

### Phase 1: cross-file consolidation

#### 1A. Contest system — `contest_system.py` (no issue)

Replace every opposed roll with one contest module. Today the opposed rolls are inline: motorics against motorics, `randint(1, max(1, get_numeric_stat(char, "motorics", 1)))` for each side, in `actions.py`, `grappling.py` and `movement_resolution.py`, and d20 plus skill against d20 plus dodge in `attack.py`. `dice.py` adds its own `opposed_roll`.

Wanted interface:

- `ContestResult`: `winner`, `loser`, `winner_roll`, `loser_roll`, `char1_won`, `contest_type`.
- `motorics_contest(char1, char2, contest_type="CONTEST", handler=None)`: motorics against motorics on d[stat] dice; `contest_type` names it in the log (GRAPPLE_ATTEMPT, AUTO_ESCAPE and so on); returns a `ContestResult`.
- `attack_contest(attacker, target, handler=None)`: d20 plus stat.
- `movement_contest(mover, opponents, contest_type, handler=None)`: against the highest opponent stat.

Plan: create `contest_system.py` consolidating all dice patterns; replace the dice functions first (safer, isolated), testing after each; then the contest instances in the resolution modules, testing a combat round with grapple attempts; check consistency across files with a full combat testing every contest type; remove all duplicate contest and dice code.

#### 1B. Debug message volume (no issue)

Bring the number of `splattercast.msg` calls down to the target of fewer than 10 per file and standardize message formats across files. The routing is not part of this work: every call already goes through the `debug.py` sink. Its API is `get_splattercast()`, which returns an always-truthy `_AuditRouter` whose `.msg()` stands in for the channel object, plus `debug_broadcast()`, `log_debug()` and `log_combat_action()`. It has no levels and no category filtering. Destinations are an always-on rotating audit file, `server/logs/combat_audit.log`, and a channel mirror gated by `settings.SPLATTERCAST_LIVE`.

A `combat_log(level, category, message, char=None, target=None, handler=None)` with levels (DEBUG, INFO, WARNING, ERROR) and categories (GRAPPLE, ATTACK, MOVEMENT, STATE) was proposed here. It was superseded by the audit sink (#461, #464); see `COMBAT_AUDIT_LOGGING_SPEC.md`.

#### 1C. State management — `state_manager.py` (also written `state_management.py`) (no issue)

Remove state-access, data-conversion and location-validation duplication from `handler.py` and `utils.py`. Patterns to replace:

- **SaverList conversions**: copying `db` combatants into a regular list of regular dicts, to avoid corruption during modification, next to direct `getattr(handler.db, DB_COMBATANTS, [])` reads.
- **Defensive attribute access**: `getattr(character, "hands", {})`, `getattr(char.ndb, NDB_PROXIMITY)`, `entry.get(DB_CHAR)`, `hasattr(character.ndb, NDB_PROXIMITY)`.
- **Combatant-entry lookups**: `next((e for e in combatants_list if e.get(DB_CHAR) == char), None)`.
- **Same-room checks**: inline `a.location == b.location` comparisons, in grapple targeting, retreat validation, advance validation, charge collision and charge targeting.

Wanted interface:

- `convert_combatants_list(saver_list)`: convert a SaverList to a regular list, avoiding corruption during modification.
- `validate_same_room(character1, character2)`: whether two characters are in the same location.
- `get_same_room_opponents(character, combatants_list)`: all opponents in the character's room.
- `validate_action_target_proximity(actor, target)`: whether a target is reachable for a combat action.

Plan: SaverList conversion utilities first (most isolated; test combatant data during combat); then defensive attribute access (test with characters missing expected attributes); then entry lookups (test combat with several participants); then remove the duplicates and test a full combat with edge cases (missing attributes, empty lists). Whether same-room checks get a shared helper is not decided (see below).

### Phase 2: decompose `utils.py`

#### 2A. Dice standardization in `dice.py` — 📋 UNBUILT (no issue)

`dice.py` rolls dice six ways: `randint(MIN_DICE_VALUE, max(MIN_DICE_VALUE, stat_value))` once and `randint(1, max(1, stat_value))` five times, plus three similar functions: `roll_with_advantage` (rolls twice, takes the higher), `roll_with_disadvantage` (rolls twice, takes the lower) and `standard_roll` (one roll). Wanted:

- `DiceResult`: `final_roll`, `all_rolls`, `roll_type` ("standard", "advantage", "disadvantage").
- `safe_roll(stat_value, roll_type="standard")`: one roll function with consistent bounds checking.
- `opposed_contest(char1, char2, stat1="motorics", stat2="motorics", contest_type="CONTEST")`: one opposed roll replacing the others.

#### 2B. Weapon utilities — `weapon_utilities.py` (no issue)

Weapon selection is in `weapon_choice.py` (#3695): `choose_weapon`, `weapon_options` and `has_ranged_option`, with hand access in one place, `_candidates`. `utils.py` keeps `find_best_weapon` (the best weapon carried, for drawing) and `get_weapon_damage`; its one `hands` read is in `surplus_limb_initiative_bonus`. Wanted:

- `get_character_hands(character)`: the single source of truth for hand access.
- `get_all_wielded_items(character)`: every item in the hands, weapon or not.
- `get_wielded_weapons(character, weapon_type=None)`: weapons, optionally filtered to ranged or melee.

`get_weapon_damage` moves out of `utils.py` into this module.

#### 2C. Combat entry management — `combat_entry_manager.py` (no issue)

`utils.py` holds two large functions that belong in a state module, not in utilities: `add_combatant` (about 115 lines, with extensive debug logging) and `remove_combatant` (about 350 lines, with cleanup logic). Wanted:

- `create_combatant_entry(character, target=None, **kwargs)`: a standard combatant entry.
- `add_combatant_to_handler(handler, character, entry)`: add with validation and logging.
- `remove_combatant_from_handler(handler, character)`: remove with cleanup and validation.

### Phase 4: simplify the handler

#### 4A. Round orchestration — 📋 UNBUILT (no issue)

Break down `CombatHandler.at_repeat()` (about 200 lines). It already calls `_validate_combatants`, `_check_peaceful_resolution`, `_handle_yielding_turn`, `_dispatch_combat_action`, `_schedule_attack` and `_remove_incapacitated`. Wanted shape, pure orchestration: `at_repeat` returns if `_validate_combat_state()` fails; gets the combatants from `_prepare_combatants()` and calls `stop_combat_logic()` if there are none; calls `_end_combat_peacefully(combatants)` if `_should_end_peacefully(combatants)`; otherwise calls `_process_combat_round(combatants)`, which runs `_process_combatant_turn(entry, combatants)` for each entry in `_get_initiative_order(combatants)`.

#### 4B. Handler responsibilities (no issue)

What stays in the handler: round orchestration, script lifecycle, handler-merging coordination, combat state validation triggers. Contest resolution moves to `contest_system.py` (1A) and state manipulation to `state_manager.py` (1C).

#### 4C. Final validation and optimization (no issue)

## Not yet placed in the order

These are wanted, with no position in the order above.

### Error handling and robustness — `error_handling.py` (no issue)

Consolidate scattered error handling and defensive programming:

- **Safe attribute access**: `getattr(self.db, DB_COMBATANTS, [])`, `getattr(script.db, DB_MANAGED_ROOMS, [])`, `entry.get(DB_CHAR)`, `hasattr(handler_script, "db") and hasattr(handler_script.db, DB_MANAGED_ROOMS)`.
- **Combatant-entry lookups**: the `next(...)` lookups, in both the `e.get(DB_CHAR) == char` and the `e[DB_CHAR] == grappler` forms.
- **Exception handling**: `try` / `except Exception as e` blocks that log the error and clean up or continue.
- **Null checks**: 20+ repeated `if not` validation patterns.

Wanted:

- `safe_get_combatants(handler)`: the combatants list, with error handling.
- `safe_get_attribute(obj, attr_path, default=None)`: nested attribute access with a fallback.
- `find_combatant_entry(combatants_list, character)`: find a combatant's entry.
- `safe_execute_with_logging(operation, error_context, handler=None)`: run an operation with consistent error handling and logging.

### Method signature standardization (no issue)

Parameter conventions differ across methods:

- **Handler reference**: some take `handler`, some use `self`. `attack.py`, `movement_resolution.py` and `actions.py` put the handler first, as in `resolve_retreat(handler, char, entry)` and `process_attack(handler, attacker, target, attacker_entry, combatants_list)`. `grappling.py` puts it last, as in `resolve_grapple_initiate(char_entry, combatants_list, handler)` and its siblings `resolve_grapple_join`, `resolve_grapple_takeover` and `resolve_release_grapple`. Four one-line delegators in `CombatHandler` (`_resolve_grapple_initiate` and its three siblings) exist only to bridge the two orders.
- **Combatants access**: some take `combatants_list`, others fetch it themselves.
- **Character naming**: `char`, `character` and `combatant` are mixed.
- **Entry naming**: `entry`, `combat_entry` and `char_entry` are mixed.

Proposed standard: `method_name(self, character, target=None, combatants=None, entry=None)` for methods, and `extracted_function(handler_context, character, **kwargs)` for functions outside the handler.

### Constants and magic numbers — `combat_config.py` (no issue)

Move hardcoded values into configuration:

- **Numeric constants**: the d20 attack and precision rolls and the d6 base damage in `attack.process_attack`, the d20 initiative roll in `utils.add_combatant`, and stat defaults of 1. `constants.py` already has `DEFAULT_MOTORICS` and `MIN_DICE_VALUE`, which `dice.roll_stat` uses.
- **String constants**: action names and message prefixes scattered in logic.
- **Database keys**: direct strings instead of constant references.
- **Timing**: attack staggering already uses `STAGGER_DELAY_INTERVAL` and `MAX_STAGGER_DELAY` from `constants.py` (`attack.calculate_attack_delay`).

Proposed for balance values: `ATTACK_DIE_SIZE = 20`, `DEFAULT_STAT_VALUE = 1`, `COMBAT_ACTION_DELAY = 0.5`. Proposed for message templates: `GRAPPLE_ATTEMPT_MSG = "GRAPPLE_ATTEMPT: {attacker} vs {target}"`, `AUTO_ESCAPE_MSG = "AUTO_ESCAPE: {character} (roll {roll})"`.

Proposed `combat_config.py`:

```python
# Dice and probability constants
ATTACK_DIE_SIZE = 20
CONTEST_DIE_SIZE_STAT_BASED = True
DEFAULT_STAT_VALUE = 1

# Timing constants
COMBAT_ROUND_DELAY = 0.5
DEATH_CLEANUP_DELAY = 1.0
HANDLER_MERGE_DELAY = 0.1

# Message templates
MESSAGE_TEMPLATES = {
    'grapple_attempt': "GRAPPLE_ATTEMPT: {attacker} vs {target}",
    'auto_escape': "AUTO_ESCAPE: {character} (roll {roll})",
    'contest_result': "CONTEST: {char1} ({roll1}) vs {char2} ({roll2})",
}

# Database key validation
def validate_db_key(key):
    """Validate database key against known constants"""
```

### Safe attribute access — `character_attributes.py` (no issue)

A module for the defensive attribute-access patterns now written inline in many files.

## Not decided

- Whether same-room checks (inline `a.location == b.location` comparisons) get a shared helper.

## Related documents

- `COMBAT_AUDIT_LOGGING_SPEC.md`: the combat diagnostics sink in `world/combat/debug.py`.
