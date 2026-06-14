# Combat System Refactor Specification

> **Status:** 🛣 Roadmap (partial) — dice.py/debug.py/actions.py were split out; several proposed modules and the size-reduction targets are NOT done. The diagnostics-routing section is superseded by COMBAT_AUDIT_LOGGING_SPEC.

## Overview

This specification outlines a systematic refactor of the combat module to address technical debt accumulated through incremental LLM development. The refactor will transform both the monolithic `handler.py` (originally 1,470 lines; currently ~1,077) and the oversized `utils.py` (originally 1,007 lines; currently ~1,047) into a maintainable, modular system. **Status:** partially delivered — `dice.py`, `debug.py`, and `actions.py` were split out, but several proposed modules below were never created and the size-reduction targets have not yet been met.

## Problem Statement

### Current State: Post-Initial Refactor
The combat module has already undergone one refactoring attempt that extracted functions from `handler.py` to `utils.py`. However, this created new problems:

```
Current Architecture:
├── handler.py       # ~1,077 lines (was 1,470) - Combat orchestration + action processing  
├── utils.py         # ~1,047 lines (was 1,007) - Mixed utilities (refactor dumping ground)
├── grappling.py     # ~300 lines - Specialized grappling logic
├── proximity.py     # ~250 lines - Specialized proximity logic
└── constants.py     # ~200 lines - Shared constants

Total: ~3,200 lines with significant cross-file duplication
```

### Current Issues
- **Dual Monoliths**: Both `handler.py` (~1,077 lines, was 1,470) and `utils.py` (~1,047 lines, was 1,007) exceed maintainable size
- **Cross-File Duplication**: Same patterns repeated across both files
  - Contest patterns: `handler.py` (6 instances) + `utils.py` (inconsistent dice patterns)
  - Debug messages: `handler.py` (128) + `utils.py` (19) = 147 total splattercast calls
    *(routing superseded — diagnostics now go through the single
    `world/combat/debug.py` sink, not raw
    `ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)` lookups; see
    `COMBAT_AUDIT_LOGGING_SPEC.md`. The raw idiom referenced
    throughout this doc was retired in #464.)*
  - Attribute access: Defensive `getattr` patterns in both files
- **Utility Dumping Ground**: `utils.py` became catch-all with mixed responsibilities:
  - Dice rolling + debug logging + weapon handling + combat entry management
- **Method Bloat**: Still have oversized methods despite extraction attempts
- **Inconsistent Patterns**: Different approaches to same operations across files

### Root Cause
**LLM Development Challenges**:
- Incremental feature additions without architectural consideration
- Context window limitations preventing holistic view
- Tendency to duplicate patterns rather than extract functions
- Limited refactoring capabilities across large files

## Design Goals

### Primary Objectives
1. **Separation of Concerns**: Each module has single responsibility
2. **DRY Compliance**: Eliminate all repeated patterns
3. **LLM-Friendly Structure**: Small, focused files that fit in context windows
4. **Testability**: Isolated functions that can be tested independently
5. **Maintainability**: Clear interfaces and minimal coupling

### Success Metrics
- `handler.py` reduced to <500 lines (orchestration only) — **NOT yet met** (currently ~1,077)
- `utils.py` broken down into focused modules (<300 lines each) — **NOT yet met** (still ~1,047)
- No code duplication (0 repeated patterns across ALL files)
- <10 debug messages per file
- Each file <300 lines (fits in LLM context) — **target; not met for handler.py/utils.py**
- Clear separation: orchestration vs implementation vs utilities

## Refactor Strategy

### Phase-Based Approach
Given LLM limitations, we'll use **incremental extraction** with **validation at each step**:

1. **Extract Repeated Patterns** (safest, highest value)
2. **Extract Action Processors** (medium risk, high value)  
3. **Simplify Handler Structure** (highest risk, essential for maintainability)

### LLM-Aware Constraints
- **File Size Limit**: <300 lines per file (fits in context window)
- **Single Change Rule**: One type of change per commit
- **Validation Required**: Test each extraction before proceeding
- **Incremental Safety**: Always maintain working system
- **Documentation First**: Specify before implementing

## Target Architecture

### Current vs Target Comparison

**Current (Post-Initial Refactor)**:
```
world/combat/
├── handler.py       # ~1,077 lines (was 1,470) - Mixed orchestration + processing
├── utils.py         # ~1,047 lines (was 1,007) - Mixed utilities dumping ground
├── grappling.py     # ~300 lines - Grappling logic  
├── proximity.py     # ~250 lines - Proximity system
└── constants.py     # ~200 lines - Constants
```

**Target (Responsibility-Based)**:

Status legend: ✅ delivered (file exists) · ❌ NOT implemented (never split out).
```
world/combat/
├── handler.py              # target <500 lines - Pure orchestration (❌ still ~1,077)
├── actions.py              # ✅ delivered - Combat action resolution
├── contest_system.py       # ❌ NOT implemented - contest logic still lives in handler.py/utils.py
├── state_manager.py        # ❌ NOT implemented - state manipulation still in handler.py/utils.py
├── debug.py                # ✅ delivered - Centralized logging
├── dice.py                 # ✅ delivered - Standardized dice rolling
├── weapon_utilities.py     # ❌ NOT implemented - weapon helpers still in utils.py
├── character_attributes.py # ❌ NOT implemented - safe attribute access still inline
├── grappling.py            # ✅ delivered - Grappling logic
├── proximity.py            # ✅ delivered - Proximity system
└── constants.py            # ✅ delivered - Constants
```

### Responsibility Matrix

| Module | Primary Responsibility | Key Functions | Source Files | Status |
|--------|----------------------|---------------|--------------|--------|
| `handler.py` | Combat orchestration | Round management, script lifecycle | Current handler.py | ✅ exists (not yet slimmed) |
| `actions.py` | Action resolution | Process attacks, grapples, movement | Current handler.py | ✅ delivered |
| `contest_system.py` | Contest mechanics | Motorics rolls, opposed checks | Both handler.py + utils.py | ❌ NOT implemented |
| `state_manager.py` | State manipulation | Combatant entry management | Both handler.py + utils.py | ❌ NOT implemented |
| `debug.py` | Logging coordination | Centralized debug system | Both handler.py + utils.py | ✅ delivered |
| `dice.py` | Dice operations | Standardized rolling patterns | Current utils.py | ✅ delivered |
| `weapon_utilities.py` | Weapon handling | Weapon access, validation | Current utils.py | ❌ NOT implemented |
| `character_attributes.py` | Safe attribute access | Defensive patterns | Both handler.py + utils.py | ❌ NOT implemented |

## Phase 1: Extract Cross-File Repeated Patterns

### Priority 1A: Contest System Extract (Cross-File Consolidation)

**Target**: Eliminate contest duplication across BOTH `handler.py` AND `utils.py`

**Cross-File Duplication Found**:

**In `handler.py` (6 instances - exact line references needed)**:
```python
# Pattern 1: Contest with randint (6 instances)
# Located at lines: ~597, ~648, ~706, ~756, ~778, ~833 (approximate - verify with grep)
escaper_roll = randint(1, max(1, get_numeric_stat(char, "motorics", 1)))
grappler_roll = randint(1, max(1, get_numeric_stat(grappler, "motorics", 1)))
splattercast.msg(f"CONTEST_TYPE: {char.key} (roll {escaper_roll}) vs {grappler.key} (roll {grappler_roll}).")
```

**In `utils.py` (6 inconsistent instances - exact line references needed)**:
```python
# Pattern 2: Inconsistent dice rolling (6 different approaches)
# Search command: grep -n "randint.*max.*stat" world/combat/utils.py
randint(MIN_DICE_VALUE, max(MIN_DICE_VALUE, stat_value))  # Used once
randint(1, max(1, stat_value))                           # Used 5 times

# Pattern 3: Opposed roll logic (duplicated in utils)
# Search command: grep -n "roll.*roll.*>" world/combat/utils.py
roll1 = roll_stat(char1, stat1)
roll2 = roll_stat(char2, stat2)
return roll1, roll2, roll1 > roll2
```

**Reference Commands for LLM Context**:
```bash
# Find all contest patterns:
grep -n "randint.*max.*motorics" world/combat/handler.py
grep -n "randint.*max" world/combat/utils.py  
grep -n "splattercast.msg.*CONTEST" world/combat/handler.py
grep -n "_roll.*_roll" world/combat/utils.py

# Count total instances:
grep -c "randint(" world/combat/handler.py world/combat/utils.py
```

**Total Impact**: 12+ instances across both files using different patterns for same operations

**New Interface** (`contest_system.py`):
```python
from dataclasses import dataclass
from random import randint
from .utils import get_numeric_stat

@dataclass
class ContestResult:
    """Result of a contest between two characters"""
    winner: object
    loser: object
    winner_roll: int
    loser_roll: int
    char1_won: bool
    contest_type: str

def motorics_contest(char1, char2, contest_type="CONTEST", handler=None):
    """
    Standardized motorics vs motorics contest using d[stat] dice.
    
    Args:
        char1: First character (typically initiator)
        char2: Second character (typically defender)  
        contest_type: Type for logging (GRAPPLE_ATTEMPT, AUTO_ESCAPE, etc.)
        handler: Combat handler for logging
        
    Returns:
        ContestResult: Complete contest outcome
    """

def attack_contest(attacker, target, handler=None):
    """Attack-specific contest using d20+stat"""
    
def movement_contest(mover, opponents, contest_type, handler=None):
    """Movement contest vs highest opponent stat"""
```

**Extraction Plan**:
1. **Survey Phase**: 
   ```bash
   # Get exact locations and variations:
   grep -n "randint.*max" world/combat/handler.py world/combat/utils.py
   grep -n "motorics" world/combat/handler.py world/combat/utils.py | grep -v import
   ```
2. Create unified `contest_system.py` consolidating ALL dice patterns
3. Replace `utils.py` dice functions first (safer, isolated)
   - **Manual Test**: After each function replacement
4. Replace `handler.py` contest instances using new system
   - **Manual Test**: Combat round with grapple attempts
5. Validate cross-file consistency
   - **Manual Test**: Full combat scenario testing all contest types
6. Remove ALL duplicate contest/dice code from both files
   - **Final Test**: Complete combat sequence to ensure no regressions

### Priority 1B: Debug Logging Extract (Cross-File Consolidation)

**Target**: Replace 147 total `splattercast.msg()` calls across both files

**Cross-File Debug Spam**:
- **handler.py**: 128 `splattercast.msg()` calls (verify: `grep -c "splattercast.msg" world/combat/handler.py`)
- **utils.py**: 19 `splattercast.msg()` calls (verify: `grep -c "splattercast.msg" world/combat/utils.py`)
- **Total**: 147 direct debug calls using same pattern

**Repeated Channel Access Pattern** (found in both files):
```bash
# Reference command to find all instances:
grep -n "ChannelDB.objects.get_channel" world/combat/*.py
grep -n "SPLATTERCAST_CHANNEL" world/combat/*.py
```

```python
# This exact pattern appears 8+ times in utils.py alone:
splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
splattercast.msg(f"SOME_PREFIX: detailed message with {variables}")

# Plus 128+ times in handler.py with slight variations
```

**Cross-File Impact**: Both files have identical channel access ceremonies, different message formats

**New Interface** (`debug.py`):
```python
def combat_log(level, category, message, char=None, target=None, handler=None):
    """
    Centralized combat logging with levels and filtering.
    
    Args:
        level: DEBUG, INFO, WARNING, ERROR
        category: GRAPPLE, ATTACK, MOVEMENT, STATE, etc.
        message: Log message template
        char: Primary character (optional)
        target: Target character (optional)  
        handler: Combat handler for context (optional)
    """

# Usage examples:
combat_log("DEBUG", "GRAPPLE", "Attempt: {char} vs {target}", char=char1, target=char2)
combat_log("INFO", "ATTACK", "Hit for {damage} damage", char=attacker, target=victim)
```

**Extraction Plan**:
1. **Survey Phase**:
   ```bash
   # Get exact counts and message patterns:
   grep -n "splattercast.msg" world/combat/handler.py | wc -l  # Should show 128
   grep -n "splattercast.msg" world/combat/utils.py | wc -l    # Should show 19
   grep -n "SPLATTERCAST_CHANNEL" world/combat/*.py
   ```
2. Create unified `debug.py` for ALL combat debug messages
3. Replace `utils.py` debug calls first (19 instances, easier to validate)
   - **Manual Test**: Verify debug output appears correctly in splattercast channel
4. Replace `handler.py` debug calls in batches of 15-20
   - **Manual Test**: After each batch, run combat to verify debug messages
5. Standardize message formats across both files
   - **Manual Test**: Full combat round to verify all debug categories work
6. Remove ALL direct `splattercast.msg()` calls from both files
   - **Final Test**: Combat with debug channel monitoring to ensure complete coverage

### Priority 1C: State Management Extract (Cross-File Consolidation)

**Target**: Eliminate state access duplication across both files

**Cross-File State Patterns**:

**SaverList Conversions** (found in both files):
```bash
# Reference commands to find patterns:
grep -n "SaverList\|combatants_list\|regular_entry" world/combat/handler.py
grep -n "getattr.*db.*DB_COMBATANTS" world/combat/*.py
```

```python
# handler.py: 3 separate conversion ceremonies (find exact lines with grep)
combatants_list = []
if getattr(self.db, DB_COMBATANTS, None):
    for entry in getattr(self.db, DB_COMBATANTS):
        regular_entry = dict(entry)
        combatants_list.append(regular_entry)

# utils.py: Direct access patterns
combatants = getattr(handler.db, DB_COMBATANTS, [])
```

**Defensive Attribute Access** (found extensively in both files):
```bash
# Reference commands to count defensive patterns:
grep -c "getattr(" world/combat/handler.py world/combat/utils.py
grep -c "hasattr(" world/combat/handler.py world/combat/utils.py  
grep -c "\.get(" world/combat/handler.py world/combat/utils.py
```

```python
# Both files use these patterns repeatedly:
hands = getattr(character, "hands", {})
getattr(char.ndb, NDB_PROXIMITY)  
entry.get(DB_CHAR)
hasattr(character.ndb, NDB_PROXIMITY)
```

**Character Entry Lookups** (found in both files):
```bash
# Reference command to find all entry lookup patterns:
grep -n "next.*e for e in.*combatants" world/combat/*.py
```

```python
# Pattern repeated across both files:
entry = next((e for e in combatants_list if e.get(DB_CHAR) == char), None)
```

**Extraction Plan**:
1. **Survey Phase**:
   ```bash
   # Map all state access patterns:
   grep -n "getattr.*db\|hasattr.*db\|\.get(" world/combat/handler.py world/combat/utils.py
   grep -n "next.*combatants" world/combat/handler.py world/combat/utils.py
   ```
2. Create unified `state_manager.py` for ALL state manipulation patterns
3. Extract SafeList conversion utilities first (most isolated)
   - **Manual Test**: Verify combatant data integrity during combat
4. Extract defensive attribute access patterns (cross-file)
   - **Manual Test**: Test with characters missing expected attributes
5. Extract character entry lookup patterns
   - **Manual Test**: Combat with multiple participants to verify lookups
6. Remove ALL duplicate state access code from both files
   - **Final Test**: Full combat with edge cases (missing attributes, empty lists)

### Priority 2B: State Management Extract

**Target**: Remove data conversion and location validation duplication

**Current Problem**: Repeated validation and conversion patterns
- **SaverList Conversions**: 3 separate conversion ceremonies (lines 417-424)
- **Location Validations**: 5 repeated patterns (lines 706, 1036, 1091, 1144, 1270)
  ```python
  if target.location == char.location:  # Repeated 5 times
  if opponent.location == char.location:  # Similar pattern
  ```

**Extraction Targets**:

#### 2B.1: Data Conversion Utilities
**Lines to Extract**: SaverList conversion ceremonies
```python
# Convert SaverList to regular list to avoid corruption during modifications (line 417)
# Convert each entry to a regular dict to avoid SaverList issues (line 421)
```

#### 2B.2: Location Validation Utilities  
**Lines to Extract**: Repeated location checks (5 instances)
```python
# Same-room validation pattern used in:
# - Grapple targeting (line 706)
# - Retreat validation (line 1036)  
# - Advance validation (line 1091)
# - Charge collision (line 1144)
# - Charge targeting (line 1270)
```

**New Interface** (`state_management.py`):
```python
def convert_combatants_list(saver_list):
    """Convert SaverList to regular list avoiding corruption during modifications"""
    
def validate_same_room(character1, character2):
    """Validate that two characters are in the same location"""
    
def get_same_room_opponents(character, combatants_list):
    """Get all opponents in the same room as character"""
    
def validate_action_target_proximity(actor, target):
    """Validate target is accessible for combat actions"""
```

## Phase 2: Extract Utility-Specific Patterns

### Priority 2A: Dice System Standardization (from utils.py)

**Target**: Consolidate inconsistent dice rolling patterns in `utils.py`

**Current Problem**: `utils.py` has 6 different approaches to dice rolling:
```python
# Pattern 1: Using constants (1 instance)
randint(MIN_DICE_VALUE, max(MIN_DICE_VALUE, stat_value))

# Pattern 2: Hardcoded values (5 instances)  
randint(1, max(1, stat_value))

# Pattern 3: Three separate functions doing similar things
roll_with_advantage(stat_value)    # rolls twice, takes max
roll_with_disadvantage(stat_value) # rolls twice, takes min  
standard_roll(stat_value)          # single roll
```

**New Interface** (`dice.py`):
```python
@dataclass
class DiceResult:
    final_roll: int
    all_rolls: list
    roll_type: str  # "standard", "advantage", "disadvantage"

def safe_roll(stat_value, roll_type="standard"):
    """Unified dice rolling with consistent bounds checking"""
    
def opposed_contest(char1, char2, stat1="motorics", stat2="motorics", contest_type="CONTEST"):
    """Standardized opposed roll replacing both handler and utils patterns"""
```

### Priority 2B: Weapon Utilities Consolidation (from utils.py)

**Target**: Extract weapon-related functions with repeated hand access patterns

**Current Problem**: `utils.py` has 3+ functions all using same hand access pattern:
```python
# This pattern appears 3+ times:
hands = getattr(character, "hands", {})
# Then different logic for each function
```

**Functions to Extract**:
- `get_wielded_weapon()` - 15 lines
- `is_wielding_ranged_weapon()` - 12 lines  
- `get_wielded_weapons()` - 18 lines
- `get_weapon_damage()` - 10 lines

**New Interface** (`weapon_utilities.py`):
```python
def get_character_hands(character):
    """Single source of truth for hand access"""
    
def get_all_wielded_items(character):
    """Get all items in hands, weapons or not"""
    
def get_wielded_weapons(character, weapon_type=None):
    """Get weapons, optionally filtered by type (ranged/melee)"""
```

### Priority 2C: Combat Entry Management (from utils.py)

**Target**: Extract large combat entry functions from `utils.py`

**Current Problem**: `utils.py` contains two large functions:
- `add_combatant()` - ~60 lines with extensive debug logging
- `remove_combatant()` - ~45 lines with cleanup logic

Both functions should be in a dedicated state management module, not utilities.

**New Interface** (`combat_entry_manager.py`):
```python
def create_combatant_entry(character, target=None, **kwargs):
    """Create standardized combatant entry"""
    
def add_combatant_to_handler(handler, character, entry):
    """Add combatant with proper validation and logging"""
    
def remove_combatant_from_handler(handler, character):
    """Remove combatant with cleanup and validation"""
```

## Phase 3: Extract Action Processors (from handler.py)

### Priority 3A: Action Processing Extract

**Target**: Remove specific oversized methods from handler

**Current Problem**: Large embedded methods within handler class
- `at_repeat()`: 432 lines (lines 402-833)
- `_process_attack()`: 112 lines (lines 876-987)  
- `_resolve_retreat()`: 55+ lines (lines 1013-1068)
- `_resolve_advance()`: 170+ lines (lines 1068-1238)
- `_resolve_charge()`: 144+ lines (lines 1238-1382)
- `_resolve_disarm()`: 88+ lines (lines 1382-1470)

**Extraction Targets**:

#### 3A.1: Grapple Processing (from `at_repeat()`)
**Lines to Extract**: ~100 lines of grapple logic from `at_repeat()`
```python
# Auto-resistance processing (lines 597-648) 
# Grapple intent processing (lines 700-780)
# Manual escape processing (lines 756-778)
```

#### 3A.2: Attack Processing  
**Lines to Extract**: `_process_attack()` method (112 lines)
- Proximity validation
- Weapon handling
- Roll calculation with modifiers
- Damage application
- Death handling

#### 3A.3: Movement Processing
**Lines to Extract**: All `_resolve_*` movement methods (400+ lines total)
- `_resolve_retreat()`: 55 lines
- `_resolve_advance()`: 170 lines  
- `_resolve_charge()`: 144 lines
- `_resolve_disarm()`: 88 lines

**New Interface** (`actions.py`):
```python
def process_auto_resistance(handler, combatants_list):
    """Process automatic escape attempts for non-yielding victims"""

def process_grapple_intent(handler, character, intent_dict, combatants_list):
    """Process grapple attempt from action intent"""

def process_escape_intent(handler, character, combatants_list):
    """Process manual escape attempt"""

def process_standard_attack(handler, attacker, target, attacker_entry):
    """Process standard combat attack (extracted from _process_attack)"""

def process_retreat_action(handler, character, character_entry):
    """Process retreat movement action"""

def process_advance_action(handler, character, character_entry):
    """Process advance movement action"""

def process_charge_action(handler, character, character_entry):
    """Process charge movement action"""

def process_disarm_action(handler, character, character_entry):
    """Process disarm combat action"""
```

## Phase 4: Simplify Handler Structure

### Priority 4A: Round Orchestration

**Target**: Break down 400+ line `at_repeat()` method

**New Structure**:
```python
def at_repeat(self):
    """Main combat loop - pure orchestration"""
    if not self._validate_combat_state():
        return
        
    combatants = self._prepare_combatants()
    if not combatants:
        self.stop_combat_logic()
        return
        
    if self._should_end_peacefully(combatants):
        self._end_combat_peacefully(combatants)
        return
        
    self._process_combat_round(combatants)

def _process_combat_round(self, combatants):
    """Process single combat round"""
    for combatant_entry in self._get_initiative_order(combatants):
        self._process_combatant_turn(combatant_entry, combatants)
```

### Priority 4B: Handler Responsibilities

**Final Handler Responsibilities**:
- Combat round orchestration  
- Script lifecycle management
- Handler merging coordination
- Combat state validation triggers

**Extracted Responsibilities**:
- ❌ Contest resolution → `contest_system.py` (NOT implemented; still inline in handler.py/utils.py)
- ✅ Debug logging → `debug.py`  
- ❌ State manipulation → `state_manager.py` (NOT implemented; still inline in handler.py/utils.py)
- ✅ Action processing → `actions.py`

## LLM Reference Commands & Context Management

### Essential Commands for Each Phase

#### File Analysis Commands
```bash
# Get current file sizes
wc -l world/combat/handler.py world/combat/utils.py

# Get total line count for project scope
find world/combat -name "*.py" -exec wc -l {} + | tail -1

# Count patterns across files
grep -c "pattern" world/combat/handler.py world/combat/utils.py

# Get file structure overview
find world/combat -name "*.py" | head -20
```

#### Pattern Discovery Commands  
```bash
# Find all contest/dice patterns:
grep -n "randint.*max" world/combat/handler.py world/combat/utils.py
grep -n "motorics.*contest\|contest.*motorics" world/combat/*.py

# Find all debug patterns:
grep -n "splattercast.msg" world/combat/handler.py world/combat/utils.py
grep -n "SPLATTERCAST_CHANNEL" world/combat/*.py

# Find all state access patterns:
grep -n "getattr.*db\|hasattr.*db" world/combat/handler.py world/combat/utils.py
grep -n "next.*combatants" world/combat/handler.py world/combat/utils.py

# Find defensive programming patterns:
grep -n "getattr(\|hasattr(\|\.get(" world/combat/handler.py world/combat/utils.py
```

#### Context Building Commands
```bash
# Read file sections for context:
sed -n '400,500p' world/combat/handler.py    # Read lines 400-500
sed -n '1,100p' world/combat/utils.py        # Read first 100 lines

# Find function definitions:
grep -n "^def " world/combat/handler.py world/combat/utils.py

# Find class definitions and structure:
grep -n "^class \|^    def " world/combat/handler.py
```

#### Validation Commands (for Manual Testing Reference)
```bash
# Check import statements after changes:
grep -n "^from\|^import" world/combat/handler.py world/combat/utils.py

# Verify no syntax errors:
python -m py_compile world/combat/handler.py
python -m py_compile world/combat/utils.py

# Find remaining old patterns after extraction:
grep -n "OLD_PATTERN" world/combat/handler.py world/combat/utils.py
```

### Pre-Phase Survey Commands

#### Before Phase 1 (Cross-File Consolidation):
```bash
# Get baseline metrics:
echo "=== BASELINE METRICS ==="
wc -l world/combat/handler.py world/combat/utils.py
echo "Contest patterns:" && grep -c "randint.*max" world/combat/handler.py world/combat/utils.py
echo "Debug messages:" && grep -c "splattercast.msg" world/combat/handler.py world/combat/utils.py
echo "State access:" && grep -c "getattr.*db\|\.get(" world/combat/handler.py world/combat/utils.py
```

#### Before Phase 2 (Utils Decomposition):
```bash
# Analyze utils.py structure:
echo "=== UTILS.PY ANALYSIS ==="
grep -n "^def " world/combat/utils.py | wc -l  # Function count
grep -n "randint(" world/combat/utils.py | wc -l  # Dice patterns
grep -n "hands.*getattr\|getattr.*hands" world/combat/utils.py  # Hand access patterns
```

#### Before Phase 3 (Handler Decomposition):
```bash
# Analyze handler.py methods:
echo "=== HANDLER.PY METHODS ==="
grep -n "def at_repeat\|def _process_\|def _resolve_" world/combat/handler.py
sed -n '402,833p' world/combat/handler.py | wc -l  # at_repeat() size
```

### Context Management for Large File Reads

#### Reading handler.py (~1,077 lines, was 1,470) in chunks:
```bash
# Method 1: By sections
sed -n '1,200p' world/combat/handler.py      # Header and imports
sed -n '400,600p' world/combat/handler.py    # at_repeat() start  
sed -n '600,833p' world/combat/handler.py    # at_repeat() end
sed -n '834,1100p' world/combat/handler.py   # Process methods
sed -n '1100,1470p' world/combat/handler.py  # Resolve methods

# Method 2: By method boundaries
grep -n "def " world/combat/handler.py | head -10  # First 10 methods
```

#### Reading utils.py (~1,047 lines, was 1,007) in chunks:
```bash
# By function groups
sed -n '1,100p' world/combat/utils.py       # Imports and constants
sed -n '100,300p' world/combat/utils.py     # Dice functions
sed -n '300,600p' world/combat/utils.py     # Weapon functions  
sed -n '600,1007p' world/combat/utils.py    # Combat entry functions
```

### Progress Tracking Commands

#### After each extraction:
```bash
# Check file sizes:
wc -l world/combat/handler.py world/combat/utils.py world/combat/new_module.py

# Verify pattern removal:
grep -c "OLD_PATTERN" world/combat/handler.py world/combat/utils.py

# Check new module structure:
grep -n "^def \|^class " world/combat/new_module.py
```

This reference section provides comprehensive command patterns for LLM context management throughout the refactoring process. Each command can be copied directly and executed to gather the exact context needed for systematic refactoring decisions.

## Implementation Guidelines

### LLM-Specific Best Practices

#### 1. **File Size Management**
- **Rule**: No file >300 lines (LLM context limit)
- **Check**: Count lines before each change
- **Split**: If file grows >300 lines, split by responsibility
- **Reference Commands**: 
  ```bash
  wc -l world/combat/handler.py  # Current: ~1,077 lines (was 1,470)
  wc -l world/combat/utils.py    # Current: ~1,047 lines (was 1,007)
  ```

#### 2. **Single Change Principle**
- **Rule**: One type of extraction per session
- **Example**: Extract all motorics contests OR debug logging, not both
- **Reason**: Prevents overwhelming changes that lead to errors
- **Manual Testing**: After each extraction, test in-game with actual combat scenarios

#### 3. **Validation at Each Step (Manual Testing Required)**
- **Rule**: Test system after each extraction
- **Method**: 
  1. Extract function
  2. Replace ONE usage
  3. **Manual Test**: Start combat, trigger specific action type
  4. Replace remaining usages
  5. **Manual Test**: Full combat round with all action types
  6. Remove old code
- **Test Scenarios**: Grapple attempts, attacks, movement, escapes, disarms

#### 4. **Context Management for Large Files**
- **Rule**: Work with one target file at a time
- **Technique**: 
  1. Read target file completely (use large line ranges)
  2. Search for patterns with `grep_search` for overview
  3. Identify ALL instances of pattern with exact line numbers
  4. Extract to new function with precise imports
  5. Replace ALL instances starting with safest/most isolated
  6. Validate complete replacement with manual testing

#### 5. **Error Prevention (No Automated Testing)**
- **Import Management**: Add imports incrementally, test each addition
- **Function Signatures**: Keep parameters simple and explicit
- **Error Handling**: Include error cases from original code
- **Backward Compatibility**: Maintain existing interfaces during transition
- **Manual Validation**: Every change requires in-game combat testing

### Extraction Methodology

#### Step-by-Step Process
1. **Identify Pattern**: Find repeated code block
   - Use `grep_search` to find all instances across files
   - Document exact line numbers and variations
2. **Count Instances**: Locate ALL occurrences
   - Example: `grep -n "splattercast.msg" world/combat/*.py`
   - Record: handler.py (lines X,Y,Z), utils.py (lines A,B,C)
3. **Design Interface**: Create function signature
   - Include all parameter variations from existing usage
   - Plan for error cases found in original implementations
4. **Extract Function**: Move to appropriate module
   - Create new file if needed: `touch world/combat/new_module.py`
   - Add proper imports and docstrings
5. **Replace First**: Replace one instance, test
   - Choose safest/most isolated usage first
   - **Manual Test**: In-game combat with specific action
6. **Replace All**: Replace remaining instances
   - Work through list systematically
   - **Manual Test**: After every 3-5 replacements
7. **Clean Up**: Remove old code, update imports
8. **Validate**: Test complete functionality
   - **Manual Test**: Full combat scenario with all action types
   - Verify no regression in combat behavior

#### Safety Checklist (Manual Testing Workflow)
- [ ] Pattern identified and counted with exact line references
- [ ] Function interface designed matching all existing usage patterns
- [ ] New module created (if needed) with proper imports
- [ ] First replacement tested with in-game combat scenario
- [ ] All instances replaced systematically with testing every 3-5 changes
- [ ] Old code removed completely
- [ ] Imports updated and verified
- [ ] System tested with full combat round (grapple + attack + movement)
- [ ] File size checked (<300 lines): `wc -l filename`
- [ ] Debug logging confirms new functions work as expected

## Risk Mitigation

### High-Risk Areas
1. **SaverList Manipulation**: Database corruption risk
2. **Grapple State Changes**: Complex bidirectional relationships
3. **Handler Merging**: Multi-handler coordination
4. **Combat Round Processing**: Core game loop

### Mitigation Strategies
1. **Conservative Extraction**: Start with safest patterns (contest system)
2. **Incremental Validation**: Test after each small change
3. **Backup Strategy**: Commit working states frequently
4. **Rollback Plan**: Keep original functions until fully replaced

## Additional Refactoring Opportunities

### Priority 5: Error Handling & Robustness Extract

**Target**: Consolidate error handling patterns and defensive programming

**Current Problem**: Scattered error handling with inconsistent patterns
- **Exception Handling**: 8 try/except blocks with generic `Exception` catches
- **Attribute Access**: 98+ instances of `getattr()`, `hasattr()`, `.get()` calls
- **Null Checks**: 20+ repeated `if not` validation patterns
- **Iterator Patterns**: 6 identical `next()` lookups for combatant entries

**Specific Patterns for Extraction**:

#### 5A: Safe Attribute Access
**Lines to Extract**: 98 instances of defensive attribute access
```python
# Pattern: Safe database access (repeated 98 times)
getattr(self.db, DB_COMBATANTS, [])
getattr(script.db, DB_MANAGED_ROOMS, [])
entry.get(DB_CHAR)
hasattr(handler_script, "db") and hasattr(handler_script.db, DB_MANAGED_ROOMS)
```

#### 5B: Combatant Entry Lookups  
**Lines to Extract**: 6 identical `next()` pattern lookups
```python
# Pattern: Find combatant entry (repeated 6 times)
entry = next((e for e in combatants_list if e.get(DB_CHAR) == char), None)
grappler_entry = next((e for e in combatants_list if e[DB_CHAR] == grappler), None)
target_entry = next((e for e in combatants_list if e[DB_CHAR] == action_target_char), None)
```

#### 5C: Exception Handling Consolidation
**Lines to Extract**: 8 try/except blocks with similar error recovery
```python
# Pattern: Generic exception handling (8 instances)
try:
    # Some operation
except Exception as e:
    splattercast.msg(f"ERROR: {e}")
    # Cleanup or continue
```

**New Interface** (`error_handling.py`):
```python
def safe_get_combatants(handler):
    """Safely retrieve combatants list with error handling"""
    
def safe_get_attribute(obj, attr_path, default=None):
    """Safely access nested attributes with fallback"""
    
def find_combatant_entry(combatants_list, character):
    """Safely find combatant entry by character"""
    
def safe_execute_with_logging(operation, error_context, handler=None):
    """Execute operation with consistent error handling and logging"""
```

### Priority 6: Method Signature Standardization

**Target**: Standardize inconsistent parameter patterns across methods

**Current Problem**: 30 methods with inconsistent parameter conventions
- **Handler Reference**: Some methods take `handler`, others access via `self`
- **Combatants Access**: Some take `combatants_list`, others fetch internally
- **Character Access**: Mixed `char`/`character`/`combatant` naming
- **Entry Access**: Inconsistent `entry`/`combat_entry`/`char_entry` patterns

**Standardization Targets**:

#### 6A: Parameter Naming Convention
```python
# Current inconsistencies:
def some_method(self, char, target, combatants_list)      # Mixed styles
def other_method(self, character, action_target_char)      # Different naming
def third_method(self, combat_entry, char_entry)          # Entry confusion

# Proposed standard:
def method_name(self, character, target=None, combatants=None, entry=None)
```

#### 6B: Handler Context Standardization
```python
# Current: Mixed self/handler usage
def extracted_function(handler, character, combatants):   # External functions
def handler_method(self, character):                      # Internal methods

# Proposed: Consistent context passing
def extracted_function(handler_context, character, **kwargs):
```

### Priority 7: Constants and Magic Numbers Extract

**Target**: Eliminate hardcoded values and improve configurability

**Current Problem**: Magic numbers and strings scattered throughout code
- **Numeric Constants**: Hardcoded dice ranges (1, 20), stat defaults (1)
- **String Constants**: Action names, message prefixes scattered in logic
- **Database Keys**: Direct string usage instead of constant references
- **Timeout Values**: Hardcoded delay values in combat timing

**Extraction Targets**:

#### 7A: Combat Balance Constants
```python
# Current: Magic numbers in code
randint(1, 20)                    # Attack roll range
get_numeric_stat(char, "motorics", 1)  # Default stat value
delay(0.5, callback)              # Hardcoded timing

# Proposed: Configuration constants
ATTACK_DIE_SIZE = 20
DEFAULT_STAT_VALUE = 1
COMBAT_ACTION_DELAY = 0.5
```

#### 7B: Message Template Constants
```python
# Current: Inline message formatting
splattercast.msg(f"GRAPPLE_ATTEMPT: {char.key} vs {target.key}")
splattercast.msg(f"AUTO_ESCAPE: {char.key} (roll {roll})")

# Proposed: Template constants
GRAPPLE_ATTEMPT_MSG = "GRAPPLE_ATTEMPT: {attacker} vs {target}"
AUTO_ESCAPE_MSG = "AUTO_ESCAPE: {character} (roll {roll})"
```

**New Interface** (`combat_config.py`):
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

## Success Criteria

### Quantitative Goals
- [ ] `handler.py` <500 lines — **NOT met** (currently ~1,077, was 1,470)
- [ ] `utils.py` eliminated - broken into focused modules — **NOT met** (still ~1,047)
- [ ] No code duplication (0 repeated patterns across ALL files)  
- [ ] All files <300 lines
- [ ] <10 debug messages per file
- [ ] 147+ debug messages consolidated (128 from handler + 19 from utils)
- [ ] 98+ attribute access patterns eliminated across both files
- [ ] 6 combatant lookup patterns standardized across both files
- [ ] 8 error handling blocks consolidated
- [ ] 39 function signatures standardized (30 handler + 39 utils)
- [ ] 6+ dice rolling patterns unified
- [ ] 90%+ test coverage for extracted functions

### Qualitative Goals
- [ ] Clear separation of concerns
- [ ] LLM-maintainable file sizes
- [ ] Consistent interfaces and naming conventions
- [ ] Robust error handling and defensive programming
- [ ] Configurable combat parameters
- [ ] Improved readability and debugging experience

## Implementation Order

### Immediate Priority (Phase 1 - Cross-File Consolidation)
1. **Week 1**: Extract contest system (`contest_system.py`) - consolidate from both files
2. **Week 1**: Extract debug logging (`debug.py`) - consolidate 147 total messages  
3. **Week 2**: Extract state management (`state_manager.py`) - cross-file patterns

### Medium Priority (Phase 2 - Utils Decomposition)
4. **Week 2**: Extract dice system (`dice.py`) - standardize 6 patterns
5. **Week 2**: Extract weapon utilities (`weapon_utilities.py`) - clean interface
6. **Week 3**: Extract combat entry management (`combat_entry_manager.py`)

### High Priority (Phase 3 - Handler Decomposition)  
7. **Week 3**: Extract grapple processors (`actions.py`)
8. **Week 3**: Extract combat processors (`actions.py`)

### Final Priority (Phase 4 - Handler Simplification)
9. **Week 4**: Simplify handler structure
10. **Week 4**: Final validation and optimization

This specification provides a systematic, LLM-aware approach to refactoring the combat system. Each phase builds on the previous while maintaining system stability and improving maintainability.
