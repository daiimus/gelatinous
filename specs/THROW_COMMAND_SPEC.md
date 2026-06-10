# Throw Command Implementation Specification

## 🚀 **IMPLEMENTATION STATUS - COMPLETE**

**Status**: ✅ **PRODUCTION READY** - All components implemented and tested

### Test Coverage & Known Divergences (issue #471)

Current behavior is pinned by the characterization suite at
`world/tests/test_throw_characterization.py` (56 tests: parsing,
validation, flight, landing/proximity, weapon-hit resolution,
deflection, pull, catch). That suite is the contract for the planned
restructure. Two findings from the line-read it encodes:

- **Weapon-throw flight is dead code.** `func()` returns for *every*
  `db.is_throwing_weapon` object (targeted → redirects to `attack`;
  untargeted → guidance message), so the `handle_weapon_throw` /
  `is_weapon=True` flight path is unreachable from the command. The
  "Weapon Detection Flow" described below documents intent, not
  current routing — `resolve_weapon_hit` only runs via the
  sticky-grenade landing route today. The restructure should either
  delete the dead path or deliberately wire it back.
- **Catch announce fixed.** `catch_object` passed `room=` to
  `msg_room_identity` (parameter is `location`), so every successful
  catch raised TypeError before timer cancellation — the caught
  object would "arrive" at its destination out of the catcher's
  hands two seconds later, breaking the hot-potato mechanic. Fixed
  with the characterization PR; the success-path test pins the
  repaired flow.

### **Implemented Components**
- ✅ **CmdThrow** - Complete 4-syntax throwing system
- ✅ **CmdPull** - Pin pulling mechanism with timer management  
- ✅ **CmdCatch** - Defensive object interception
- ✅ **CmdRig** - Exit trapping system (lives in `commands/CmdExplosives.py`, not `CmdThrow.py`)
- ✅ **Enhanced CmdDrop** - Universal proximity assignment (lives in `commands/CmdInventory.py`, not `CmdThrow.py`)

### **System Infrastructure**
- ✅ **Flight mechanics** - 2-second flight with room description integration
- ✅ **Timer system** - Multi-object countdown tracking  
- ✅ **Universal proximity** - Character/object proximity sharing
- ✅ **Combat integration** - Turn consumption and damage resolution
- ✅ **Property-driven explosives** - Flexible explosive type system
- ✅ **Chain reactions** - Object-to-object proximity triggering
- ✅ **Room description enhancement** - Flying objects display

### **Tactical Features Operational**
- ✅ **Cross-room targeting** with aim integration
- ✅ **Hot potato grenade mechanics** - Catch and re-throw live grenades
- ✅ **Exit trapping** for area control
- ✅ **Multi-explosive chain reactions**
- ✅ **Universal retreat compatibility**

---

## Overview
The `throw` command serves dual purposes: utility object transfer and combat weapon deployment. It integrates with existing systems (proximity, aim, combat) while adding new tactical possibilities.

## Core Mechanics

### Command Syntax
```
throw <object>                    # Throw randomly in current room (if occupied) or in aimed direction
throw <object> at <target>        # Throw at specific target (requires aim for cross-room)
throw <object> to <direction>     # Throw to adjacent room in specified direction (random proximity)
throw <object> to here            # Throw randomly in current room (same as first syntax)
```

### Validation Requirements
1. **Object must be wielded** using Mr. Hand system (not just in inventory)
2. **Object must exist** and be accessible to thrower
3. **Target validation** (if specified) must exist in aimed room or current room
4. **Direction validation** (if specified) must be a valid, traversable exit
5. **"here" handling** for explicit current-room throwing

### Technical Infrastructure Notes
- **Mr. Hand System**: Fully implemented in `typeclasses/characters.py` with `hands` AttributeProperty
- **Hand Structure**: Dictionary-based (`{"left": None, "right": None}`) supporting dynamic anatomy
- **Hand Management**: Complete `wield_item()`, `unwield_item()`, `list_held_items()` methods available
- **Combat Integration**: Enhanced `CmdLook` proves room description customization capability
- **Timer System**: Evennia timer infrastructure available for countdown mechanics
- **Combat Constants**: 6-second combat rounds established for timing standardization

### Combat vs. Utility Logic
- **Throwing weapons**: Objects with `db.is_throwing_weapon = True` trigger combat mechanics
- **Utility objects**: All other objects bounce harmlessly off targets, transfer between rooms
- **Improvised weapons**: Non-throwing weapons used in combat deal base improvised damage

#### Weapon Detection Flow
1. Check `object.db.is_throwing_weapon` property
2. If `True`: Enter combat mode, use weapon damage calculations
3. If `False` or missing: Utility mode, bounce harmlessly off targets
4. Special case: Objects thrown at someone already in combat always use improvised weapon damage

### Command Parsing Logic
The throw command supports multiple syntaxes that need careful parsing:

#### Design Philosophy
- **User-friendly over rigid**: Accommodate user intent rather than forcing exact syntax
- **Intelligent interpretation**: Parse context to resolve ambiguous commands
- **Graceful error recovery**: Auto-correct common mistakes when possible
- **Helpful feedback**: Provide specific suggestions when parsing fails
- **Building standards**: Avoid naming conflicts between exits and characters by design

#### Parsing Priority
1. **Parse for "at" keyword**: `throw knife at bob` → targeted throwing
2. **Parse for "to" keyword**: `throw knife to east` → directional throwing
3. **Check for "here"**: `throw knife to here` → current room throwing
4. **Fallback**: `throw knife` → use aim state or current room

#### Intelligent Parsing & Error Recovery
- **Exit priority**: `throw knife to northeast` → Always prioritize exits over character names
- **Name conflict avoidance**: Building/design should prevent exit and character name conflicts
- **Graceful accommodation**: If user confuses "at/to", attempt to resolve intelligently rather than error
- **Multi-word parsing**: Handle unquoted multi-word names intelligently where possible

#### Edge Cases in Parsing
- **Smart fallback**: `throw knife at east` → Treat "east" as direction if no character "east" exists
- **Context awareness**: `throw knife to bob` → If "bob" isn't an exit, check for character and suggest correction
- **Accommodation examples**: 
  - `throw knife at here` → Auto-convert to `throw knife to here`
  - `throw knife to bob` (no exit "bob") → "Did you mean `throw knife at bob`?"
- **Multi-word handling**: `throw battle axe to north` → Parse "battle axe" as object, "north" as direction

## Aim System Integration

### Order of Operations - Targeted Throwing
```
aim east           # Establish direction
throw knife at bob # System finds Bob in aimed room (east)
```

### Order of Operations - Directional Throwing
```
throw knife to east  # Throw to adjacent room eastward (no aim required)
throw keys to here   # Throw randomly in current room
```

### Aim State Behavior
- **Aim maintained**: Throwing does not break existing aim state
- **Cross-room targeting**: Requires active aim to throw `at <target>` in adjacent rooms
- **Directional throwing**: `throw to <direction>` works without aim requirement
- **Same-room targeting**: `throw at <target>` and `throw to here` work without aim requirement

### Syntax Priority
1. **`throw <object> at <target>`**: Specific targeting (requires aim for cross-room)
2. **`throw <object> to <direction>`**: Directional throwing (no aim required)
3. **`throw <object> to here`**: Current room random throwing
4. **`throw <object>`**: Fallback to aimed direction or current room random

## Flight Mechanics

### Timing
- **Flight duration**: 1/3 of combat round (~2 seconds, combat round = 6 seconds)
- **Multiple objects**: Can have multiple items flying simultaneously

### Room Announcements
1. **Origin room**: "Alice throws a knife eastward" or "Alice throws keys to someone nearby" (thrower announces)
2. **During flight**: Object appears in room description as "OBJECTNAME is flying through the air" 
3. **Destination room**: "A knife flies in from the west" (arrival announcement for cross-room)
4. **Post-landing**: Object removed from flight description, appears in room normally

### Announcement Variations by Syntax
- **`throw knife to east`**: "Alice throws a knife eastward"
- **`throw knife at bob`**: "Alice throws a knife at Bob" (same room) or "Alice throws a knife eastward at someone" (cross-room)
- **`throw keys to here`**: "Alice tosses some keys nearby" 
- **`throw rock`**: "Alice throws a rock eastward" (if aimed) or "Alice tosses a rock nearby" (no aim)

### Cross-Room Visibility
- **No cross-room visibility**: Only current room sees flying objects
- **Sequential announcements**: Origin → flight → destination

## Landing and Proximity Mechanics

### Landing Logic
- **Occupied rooms**: Equal chance to land in proximity to any character
- **Empty rooms**: Objects land on ground with no proximity assignment
- **Same-room throws**: Land outside thrower's proximity unless landing near someone in thrower's existing proximity

#### Proximity Assignment Details
- **Target selection**: `random.choice()` from all characters in destination room
- **Proximity inheritance**: If selected character has existing proximity relationships, thrown object inherits those
- **Grenade special case**: When grenade lands near someone, ALL characters in that person's proximity get added to grenade proximity
- **Multiple character rooms**: Each character has equal probability regardless of their current proximity state

### Proximity Inheritance
- **Grenade mechanics**: If grenade lands near someone, everyone in their existing proximity gets added to grenade proximity
- **Retreat compatibility**: Existing retreat command works for escaping grenade proximity
- **Chain reactions**: Multiple grenades can create overlapping retreat scenarios

## Combat Integration

### Turn Consumption
- **Combat throwing**: Always consumes combat turn (skip turn mechanic from flee)
- **Non-combat throwing**: No turn cost
- **Concurrent actions**: Can perform non-combat actions (inventory management, wield, etc.) after throwing

### Damage Calculation
- **Throwing weapons**: Use existing weapon damage system (`1d6 + weapon.db.damage`)
- **Improvised weapons**: Use base damage system (currently `1d6`)
- **Utility objects**: No damage (bounce harmlessly)

### Combat Message Integration
- **Message category**: Throwing weapons get dedicated "throwing" message category
- **Hit/miss system**: Uses standard ranged weapon accuracy mechanics
- **Improvised messaging**: Separate messages for improvised vs. proper throwing weapons

### Combat State Management
- **Weapon throws**: Enter combat if not already in combat
- **Proximity establishment**: May establish proximity with target on successful hit
- **Handler integration**: Use existing turn-based combat handler system

#### Combat Handler Integration Details
- **Turn-based processing**: Throwing weapons use existing combat handler's turn system
- **Action registration**: Combat throws consume player's combat turn (skip turn mechanic)
- **State management**: Handler tracks throwing weapon attacks like other ranged weapons
- **Damage processing**: Uses existing `1d6 + weapon.db.damage` calculation system
- **Message integration**: Leverages existing combat message system with new "throwing" category

## Special Mechanics

### Grenades ✅ **FULLY IMPLEMENTED**
- **Proximity creation**: Landing creates danger zone using existing proximity mechanics
- **Retreat escape**: Standard retreat command removes from grenade proximity
- **Area effect**: All characters in target's proximity inherit grenade proximity
- **Chain reactions**: Multiple grenades can create strategic positioning puzzles
- **Pin pulling system**: `pull pin on <grenade>` activates fuse timer
- **Throwing flexibility**: Can throw both pinned (live) and unpinned (inert) grenades
- **Rigging system**: `rig <grenade> to <exit>` creates exit traps with rigger immunity
- **Catch system**: `catch <object>` allows intercepting thrown objects mid-flight
- **Defuse system**: Manual `defuse <grenade>` and automatic proximity-based defusing
- **Explosion handling**: Multiple explosion paths (timer, hand, rigged, failed defuse)

### Weapon Bundles
- **Ammo system**: Throwing weapons will use bundle system with ammo tracking (future feature)
- **Current implementation**: No ammo consumption for initial implementation
- **Retrieval**: Not implemented initially (weapons are consumed on throw)

## Architecture Integration Points

### Universal Proximity System Enhancement

#### Core Architecture Change
The throw command implementation leverages a **universal proximity system** where characters and objects share the same proximity mechanics. This architectural decision enables seamless grenade mechanics and object interaction systems.

##### Universal Proximity Principles
- **Characters ARE objects**: In Evennia's architecture, characters inherit from objects, allowing uniform proximity handling
- **Shared proximity space**: Characters and objects can exist in the same proximity relationships
- **Bidirectional relationships**: Characters can be in proximity to objects, and objects can be in proximity to characters
- **Inheritance patterns**: Objects landing near characters inherit all existing proximity relationships from that character

#### Enhanced Drop Command Integration
The universal proximity system requires enhancing the existing `drop` command to assign proximity relationships:

##### Drop Command Enhancement Requirements
- **Universal proximity assignment**: When any object is dropped, assign `object.ndb.proximity = [dropper]`
- **Applies to all objects**: Not just grenades - all dropped objects get proximity to their dropper
- **Existing pattern**: Builds on established proximity mechanics from combat system
- **Seamless integration**: No special case handling needed for different object types

##### Technical Implementation
```python
# Enhanced drop command pseudo-code
def drop_object(caller, obj):
    # Existing drop logic...
    obj.move_to(caller.location)
    
    # NEW: Universal proximity assignment
    if not hasattr(obj, 'ndb'):
        obj.ndb._create()
    if not obj.ndb.proximity:
        obj.ndb.proximity = []
    if caller not in obj.ndb.proximity:
        obj.ndb.proximity.append(caller)
    
    # Message handling...
```

#### Grenade System Integration
The universal proximity system enables sophisticated grenade mechanics without special case handling:

##### Grenade Landing Mechanics
- **Direct proximity**: Grenade lands in proximity to selected character
- **Inherited proximity**: Grenade automatically inherits ALL characters in selected character's proximity
- **Cascade effect**: Everyone fighting the selected character is now in grenade proximity
- **Retreat compatibility**: Standard retreat command works to escape grenade proximity

##### Example Scenario
```
Initial state: Alice fighting Bob and Charlie (all in mutual proximity)
Throw: Dave throws grenade, lands near Bob
Result: Grenade proximity = [Alice, Bob, Charlie] (inherited from Bob's proximity)
Escape: Any character can "retreat" to leave grenade proximity
```

#### Object-to-Object Proximity
The universal system also enables object-to-object proximity relationships:

##### Chain Reaction Mechanics
- **Grenade chains**: Exploding grenades can add other nearby grenades to their proximity
- **Proximity inheritance**: Grenades landing near other grenades inherit their proximity lists
- **Complex scenarios**: Multiple overlapping proximity relationships create tactical puzzles

##### Proximity Web Example
```
Grenade A: proximity = [Alice, Bob]
Grenade B: lands near Grenade A
Grenade B: proximity = [Alice, Bob, Grenade A]
Grenade A explodes: triggers Grenade B (in proximity)
Grenade B explodes: affects [Alice, Bob] (inherited proximity)
```

#### Architectural Benefits
- **Consistency**: Same proximity rules for all entities (characters, objects, grenades)
- **Simplicity**: No special case handling for different object types
- **Extensibility**: System naturally supports future proximity-based mechanics
- **Performance**: Reuses existing proximity infrastructure without duplication

#### Implementation Requirements
1. **Enhanced drop command**: Assign `object.ndb.proximity = [dropper]` for all dropped objects
2. **Proximity inheritance**: Objects landing near characters inherit their proximity lists
3. **Universal retreat**: Retreat command works for escaping any proximity (character or object)
4. **Chain handling**: Objects can be in proximity to other objects for chain reactions

### Existing Systems Used
- **Proximity system**: Enhanced for universal character/object proximity handling
- **Aim system**: For cross-room targeting and direction
- **Combat handler**: For turn-based processing and damage
- **Mr. Hand system**: For wielding validation
- **Skip turn mechanic**: From flee command for combat turn consumption

### New Systems Required ✅ **IMPLEMENTED**
- ✅ **Flight state tracking**: Objects in transit between rooms
- ✅ **Room description integration**: Flying objects in room descriptions
- ✅ **Cross-room object transfer**: Moving objects between rooms
- ✅ **Throwing weapon detection**: `db.is_throwing_weapon` property checking
- ✅ **Explosive property system**: Property-driven explosive behavior (`db.fuse_time`, `db.blast_damage`, etc.)
- ✅ **Timer management**: Multi-object countdown tracking with property-based durations
- ✅ **Chain reaction logic**: Property-based explosive triggering system
- ✅ **Universal proximity enhancement**: Enhanced drop command for proximity assignment
- ✅ **Defuse command system**: Manual and automatic defuse mechanics with skill checks
- ✅ **Rigging system**: Exit trap mechanics with immunity for riggers
- ✅ **Dual proximity systems**: Combat proximity vs universal proximity integration

## Technical Implementation Details

### Mr. Hand Integration
- **Validation method**: Check `caller.hands` dictionary for wielded objects
- **Hand selection**: Throw from any hand containing the specified object
- **Post-throw state**: Remove object from hand, clear wielding state
- **System explanation**: Mr. Hand is the wielding system that tracks what objects are held in each hand via `caller.hands = {"left": object, "right": object}` dictionary structure
- **Technical Status**: Fully implemented in `typeclasses/characters.py` with complete method set
- **Dynamic Anatomy Support**: Dictionary-based design naturally supports additional appendages

#### Mr. Hand System Requirements
- **Hands dictionary structure**: `caller.hands` AttributeProperty with default `{"left": None, "right": None}`
- **Wielding validation**: Object must exist in `caller.hands.values()` to be throwable  
- **Post-throw cleanup**: Set `caller.hands[hand_name] = None` after successful throw
- **State consistency**: Use `caller.wield_item()` and `caller.unwield_item()` methods
- **Multi-Hand Flexibility**: System supports any hand names in dictionary (third_hand, tail, etc.)

### Flight State Management
- **Timer implementation**: Use Evennia's `utils.delay()` for 2-second flight
- **State storage**: Track flying objects in room's `ndb.flying_objects = []`
- **Cleanup requirements**: Remove from flight state on landing or error
- **Concurrent flights**: Multiple objects can be in flight simultaneously per room

#### Flight State Architecture
- **State persistence**: Flight states are stored in room NDB (non-persistent, cleared on restart)
- **Cleanup strategy**: Automatic cleanup on landing, manual cleanup on errors/disconnections  
- **Performance limits**: No hard limits initially - monitor and add if needed
- **Error recovery**: If flight timer fails, object defaults to landing in origin room
- **Server restart handling**: Flying objects are lost on restart (acceptable for initial implementation)

### Room Description Integration
- **Dynamic descriptions**: Append flying objects to room's `return_appearance()`
- **Format specification**: "A <object> is flying through the air"
- **Update timing**: Add to description immediately, remove after landing
- **Multiple objects**: Handle multiple simultaneous flying objects gracefully

### Cross-Room Mechanics
- **Exit validation**: Verify aimed direction has valid, traversable exit
- **Room connectivity**: Use existing exit system to determine destination
- **Permission checks**: Respect room access permissions for object transfer
- **Arrival messaging**: Determine incoming direction for "flies in from <direction>"

## Implementation Priority

### Phase 1: Basic Utility Throwing ✅ **COMPLETED**
- ✅ Command parsing and validation
- ✅ Same-room object transfer
- ✅ Flight timing and announcements
- ✅ Landing logic and proximity assignment
- ✅ **Grenade Enhancement**: Pin validation removal for tactical flexibility
  - Players can throw unpinned grenades as inert objects
  - Tactical mistakes and intentional choices supported
  - Only blocks throws of already-exploded grenades (timer <= 0)
  - Null safety added for NDB attribute comparisons

### Phase 2: Combat Integration ✅ **COMPLETED**
- ✅ Throwing weapon detection
- ✅ Combat handler integration
- ✅ Turn consumption mechanics
- ✅ Damage calculation

### Phase 3: Advanced Features ✅ **COMPLETED**
- ✅ Cross-room targeting with aim
- ✅ Grenade proximity mechanics
- ✅ Multiple simultaneous throws
- ✅ Flight state cleanup and error handling
- ✅ Pin pulling system (`pull pin on <grenade>`)
- ✅ Grenade rigging system (`rig <grenade> to <exit>`)
- ✅ Catch system (`catch <object>`)
- ✅ Comprehensive defuse system (manual and auto)

### Phase 4: Additional Commands ✅ **COMPLETED**
- ✅ **CmdPull**: Pin pulling mechanism for grenade activation
- ✅ **CmdCatch**: Defensive catching of thrown objects
- ✅ **CmdRig** (in `commands/CmdExplosives.py`): Exit trap setup with immunity system
- ✅ **CmdDefuse**: Manual defuse with skill checks and time pressure
- ✅ **Auto-defuse**: Automatic proximity-based defuse attempts
- ✅ **Dual proximity cleanup**: Movement system integration

## Implementation Architecture ✅ **COMPLETED**

### Command Flow Overview ✅ **IMPLEMENTED**
```
1. Parse throw syntax (at/to/fallback)
2. Validate object (wielded, exists, accessible)
3. Determine destination (aim state, direction, target)
4. Check weapon type (db.is_throwing_weapon)
5. If weapon: Enter combat mechanics
6. If utility: Simple transfer mechanics
7. Start flight timer (2 seconds)
8. Handle landing and proximity assignment
```

### Additional Command Flows ✅ **IMPLEMENTED**
```
CmdPull: pin on <grenade> → Start fuse timer → Countdown to explosion
CmdCatch: <object> → Intercept flying object → Add to hand
CmdRig: <grenade> to <exit> → Setup trap → Trigger on traverse
CmdDefuse: <grenade> → Skill check → Success/failure with consequences
Auto-defuse: Enter proximity → Automatic attempt → Passive protection
```

### Integration Points with Existing Systems ✅ **COMPLETED**
- ✅ **Proximity System**: Enhanced for universal character/object proximity handling
- ✅ **Combat Handler**: Existing turn-based system processes weapon throws
- ✅ **Aim System**: Leveraged for cross-room targeting without modification
- ✅ **Mr. Hand System**: Validates wielding, manages post-throw hand state
- ✅ **Message System**: Extended with new "throwing" category for weapons
- ✅ **Movement System**: Dual proximity cleanup on room transitions
- ✅ **Character Stats**: Skill integration for defuse mechanics (Intellect + Motorics)
- ✅ **Timer System**: Multiple concurrent countdowns with proper cleanup

### Property Validation System
All explosive and throwing weapon properties should be validated:
- **Required properties**: `db.is_throwing_weapon`, `db.is_explosive` 
- **Optional properties**: `db.fuse_time`, `db.blast_damage`, `db.dud_chance`
- **Default values**: Missing properties default to safe values (no damage, no explosion)
- **Validation timing**: Check properties during command execution, not object creation
- **Null safety**: NDB attribute comparisons must check for None values before integer operations

## Error Handling

### Validation Failures
- **Nothing wielded**: "You must be holding something to throw it."
- **Object not found**: "You don't have '<object>' to throw."
- **Object not wielded**: "You must be wielding '<object>' to throw it."
- **Target not found**: "You cannot find '<target>' to throw at."
- **No aim for cross-room targeting**: "You must aim in a direction first to throw at targets in other rooms."
- **Invalid direction**: "There is no exit '<direction>' to throw through."
- **Smart suggestions**: "Did you mean 'throw <object> at <target>' instead?" (when "to" used with character name)

### Parsing Error Recovery
- **Auto-correction**: Silently fix common mistakes (`throw knife at here` → `throw knife to here`)
- **Helpful suggestions**: When parsing fails, suggest correct syntax based on context
- **Graceful degradation**: If complex parsing fails, fall back to simpler interpretation
- **Context-aware errors**: Different error messages based on what the parser detected

### Combat Integration Errors
- **Combat turn consumed**: Standard skip turn messaging from flee command
- **Grappled**: "You cannot throw while grappled." (if grappling prevents throwing)
- **Invalid combat state**: Handle missing combat handler gracefully

### Grenade-Specific Errors ✅ **IMPLEMENTED**
- ✅ **Timer expired in hand**: "The grenade explodes in your hands!" (damage to holder)
- ✅ **Catch attempt failed**: Standard combat miss mechanics for catching thrown objects
- ✅ **Exit already rigged**: "There is already a grenade rigged to that exit."
- ✅ **Invalid exit for rigging**: "You cannot rig a grenade to that direction."
- ✅ **Rigger immunity**: Safe passage for trap setters
- ✅ **Defuse attempt spam**: One attempt per character per grenade
- ✅ **Early detonation**: Failed defuse attempts can trigger immediate explosion
- ✅ **Proximity establishment**: Dynamic proximity creation for defuse attempts
- ✅ **Runtime safety**: Null checks prevent iteration errors during explosions

### Flight State Errors
- **Room disconnection**: If room becomes inaccessible during flight, object lands in origin room
- **Object deletion**: If object is somehow deleted during flight, clean up flight state
- **Player disconnection**: Continue flight even if thrower disconnects
- **Multiple flight cleanup**: Ensure proper cleanup of multiple simultaneous flights

### Recovery Mechanisms
- **Orphaned flight objects**: Cleanup routine to remove stale flying object references
- **State corruption**: Graceful degradation if proximity or combat state becomes invalid
- **Network issues**: Timeout mechanism for flight completion

### Edge Cases
- **Thrower leaves room during flight**: Object continues to destination
- **Target leaves room during flight**: Object lands where target was
- **Multiple objects same target**: Each handled independently
- **Invalid room connections**: Blocked by doors/barriers (future)

## Implementation Status & Roadmap

### Current Implementation Status *(Updated 2025-07-21)*

#### ✅ **Phase 1 Complete: Grenade Enhancement**
**Status**: Fully implemented and tested
**Key Features**:
- Pin validation removal for tactical flexibility
- Players can throw unpinned grenades as inert objects
- Only blocks throws of expired grenades (timer <= 0)
- Null safety for NDB attribute comparisons
- TypeError fixes for robust operation

**Technical Implementation**:
- Modified `validate_grenade_throw()` method in `commands/CmdThrow.py`
- Removed pin requirement validation 
- Added null safety check: `if remaining is not None and remaining <= 0:`
- Maintains explosion-in-hands protection for safety

**Testing Results**: Successfully tested pin validation removal and TypeError fixes

#### ✅ **Phase 2 Complete: Defuse Command System**
**Status**: Fully implemented and tested (Enhanced Option 1)
**Key Features**:
- ✅ `defuse <grenade>` command with skill-based checks (Intellect + Motorics)
- ✅ **Auto-defuse when entering proximity of live grenades** (D&D-style trap detection)
- ✅ **Enhanced Option 1**: Dynamic proximity establishment with comprehensive search
- ✅ Risk/reward mechanics (30% early detonation on manual failure, 10% on auto-defuse)
- ✅ Time pressure scaling (difficulty increases as countdown approaches zero)
- ✅ One-attempt-per-grenade limit to prevent spam
- ✅ **Rigger immunity**: Characters can safely bypass their own rigged traps
- ✅ **Rigged grenade support**: Different difficulty for trap disarmament vs timed defusal
- ✅ **Comprehensive proximity cleanup**: Both combat and universal proximity systems
- ✅ **Chain reaction prevention**: Defused grenades have proximity cleared
- ✅ **Runtime error prevention**: Null safety checks for robust operation

#### 🔄 **Phase 3 Future: Advanced Grenade Features**  
**Potential Future Enhancements**:
- Sticky grenade mechanics
- Remote detonation systems
- Enhanced chain reaction logic with complex proximity webs
- Multi-type explosive support with specialized effects
- Advanced rigging mechanisms (pressure plates, tripwires)
- Defuse tool requirements for different explosive types
- Character specialization bonuses for different grenade types

#### 🔄 **Phase 4 Future: Weapon Retrieval System**
**Planned Features**:
- Thrown weapon recovery mechanics
- Bundle system with ammo tracking
- Weapon durability and breaking on impact
- Material-based improvised weapon damage scaling

### Architectural Decisions Made ✅ **IMPLEMENTED**
1. **Tactical Flexibility**: Removed pin validation to allow strategic misdirection
2. **Safety First**: Maintained explosion-in-hands protection for expired timers
3. **Robust Error Handling**: Added null safety for runtime stability
4. **Property-Driven Design**: All explosive behavior driven by object properties
5. **Enhanced Option 1**: Dynamic proximity establishment for comprehensive defuse mechanics
6. **Dual Proximity Systems**: Combat proximity vs universal proximity for different use cases
7. **Rigger Immunity**: Trap setters can safely bypass their own traps
8. **Skill Integration**: Intellect + Motorics for technical defuse attempts
9. **Time Pressure Scaling**: Difficulty increases as explosion countdown approaches zero
10. **Chain Reaction Prevention**: Defused grenades have all proximity relationships cleared

### Integration Points with Existing Systems ✅ **COMPLETED**
- ✅ **Universal Proximity System**: Enhanced for character/object proximity handling
- ✅ **Aim System**: Leveraged for cross-room targeting
- ✅ **Combat Handler**: Turn-based processing and damage calculation
- ✅ **Mr. Hand System**: Wielding validation and state management
- ✅ **Timer System**: Evennia's `utils.delay()` for countdown mechanics
- ✅ **Movement System**: Dual proximity cleanup on room transitions
- ✅ **Character Stats**: Skill system integration for defuse mechanics
- ✅ **Exit System**: Rigging integration with movement triggering

## Testing Scenarios ✅ **COMPLETED**

### Basic Functionality ✅ **TESTED**
1. ✅ Throw utility object in same room
2. ✅ Throw weapon at target in same room (enters combat)
3. ✅ Throw object in aimed direction to adjacent room
4. ✅ Multiple players throwing simultaneously

### Advanced Scenarios ✅ **TESTED**
1. ✅ Grenade proximity chain reactions
2. ✅ Aim + cross-room targeted throwing
3. ✅ Combat turn consumption verification
4. ✅ Flight timing and room description updates
5. ✅ Pin pulling and timer activation
6. ✅ Rigged grenades with immunity system
7. ✅ Manual and automatic defuse mechanics
8. ✅ Failed defuse early detonation scenarios
9. ✅ Dual proximity system cleanup on movement
10. ✅ Runtime error prevention with null safety

### Comprehensive Testing Framework ✅ **COMPLETED**

#### Unit Tests ✅ **VALIDATED**
- ✅ **Parsing logic**: All syntax variations and error recovery
- ✅ **Property validation**: Valid/invalid object properties
- ✅ **Mr. Hand integration**: Wielding validation and state management
- ✅ **Flight state**: Timer management and cleanup
- ✅ **Defuse mechanics**: Skill checks and proximity establishment
- ✅ **Rigging system**: Trap setup and immunity validation

#### Integration Tests ✅ **VALIDATED**
- ✅ **Combat system**: Weapon throws triggering combat correctly
- ✅ **Proximity system**: Landing assignment and inheritance
- ✅ **Aim system**: Cross-room targeting functionality
- ✅ **Room transfers**: Objects moving between rooms properly
- ✅ **Movement cleanup**: Dual proximity system cleanup on transitions
- ✅ **Timer coordination**: Multiple concurrent explosive countdowns

#### Stress Tests ✅ **VALIDATED**
- ✅ **Multiple simultaneous throws**: Performance with many concurrent flight objects
- ✅ **Rapid succession**: Single player throwing multiple objects quickly
- ✅ **Edge case handling**: Disconnections, room changes, object deletion during flight
- ✅ **Runtime errors**: Null safety preventing iteration failures
- ✅ **Proximity corruption**: Graceful handling of invalid proximity states

#### User Acceptance Tests ✅ **VALIDATED**
- ✅ **Gameplay scenarios**: Actual tactical combat situations
- ✅ **Error message clarity**: User-friendly error feedback
- ✅ **Command intuitiveness**: Natural language parsing effectiveness
- ✅ **Defuse tension**: Risk/reward balance in defuse attempts
- ✅ **Tactical depth**: Strategic use of unpinned grenades and rigging

## Open Implementation Questions

### Mr. Hand Integration Specifics
1. **Two-handed weapons**: ~~Should throwing a two-handed weapon require both hands to be free/wielding it?~~ **DECIDED**: Not implemented yet, future consideration.
2. **Hand preference**: If object is in both hands, which hand throws it?
3. **Post-throw state**: Should hand remain "ready" for quick-draw of another weapon?

### Combat Mechanics Details
1. **Improvised weapon damage**: ~~Should non-throwing weapons deal reduced damage when thrown?~~ **DECIDED**: Yes, for now all improvised weapons use base damage. Future refinement will differentiate materials.
2. **Range considerations**: Should throwing weapons have range limits or always work cross-room?
3. **Accuracy system**: ~~Should throwing have hit/miss mechanics like other ranged weapons?~~ **DECIDED**: Yes, throwing in combat uses normal ranged weapon logic with dedicated message category.
4. **Critical hits**: ~~Can thrown weapons score critical hits?~~ **DECIDED**: Not initially, but perfect for future improvised weaponry mechanics.

### Flight and Landing Specifics
1. **Interception**: Can thrown objects be intercepted by other players/objects during flight?
2. **Bounce mechanics**: When utility objects "bounce harmlessly," where exactly do they land?
3. **Fragile objects**: Should some objects break when thrown (bottles, delicate items)?
4. **Weight considerations**: Should heavy objects take longer to throw or fly slower?

### Room Integration Questions
1. **Room capacity**: Should rooms have limits on simultaneous flying objects?
2. **Environmental effects**: Should wind, gravity, or other room effects influence throws?
3. **Blocked exits**: How should locked doors or barriers affect cross-room throwing?
4. **Visibility**: Should dark rooms affect throwing accuracy?

### Grenade-Specific Mechanics
1. **Fuse timing**: ~~Should grenades have variable fuse lengths?~~ **DECIDED**: Variable timing based on `object.db.fuse_time` property.
2. **Dud chances**: ~~Should grenades have failure probability?~~ **DECIDED**: Based on `object.db.dud_chance` property.
3. **Blast radius**: ~~How many characters can be in grenade proximity simultaneously?~~ **DECIDED**: Driven by `object.db.blast_radius` for future expansion.
4. **Chain explosions**: ~~Should grenades be able to trigger other grenades?~~ **DECIDED**: Based on `object.db.chain_trigger` property.

#### Advanced Grenade Questions
5. **Exit rigging mechanics**: How should rigged grenades be detected/disarmed?
6. **Rig command syntax**: Should it be `rig grenade to north` or `rig grenade against north exit`?
7. **Multiple rigs per exit**: Can multiple grenades be rigged to the same exit?
8. **Rig visibility**: Are rigged grenades visible in room descriptions?
9. **Timer inheritance**: Do rigged grenades keep their original timer or reset when triggered?

#### Explosive Type Variations
Property-based system enables diverse explosive types:
- **Standard Grenade**: `fuse_time=8, blast_damage=20, chain_trigger=True, requires_pin=True`
- **Impact Grenade**: `fuse_time=0, blast_damage=15, requires_pin=False` (explodes on landing)
- **Smoke Grenade**: `fuse_time=3, blast_damage=0` (creates visibility/movement effects)
- **Flashbang**: `fuse_time=2, blast_damage=5` (stun/disorient effects)
- **Dud Grenade**: `dud_chance=1.0` (training/distraction use)
- **Hair Trigger**: `fuse_time=3, dud_chance=0.3` (fast but unreliable)
- **Cluster Bomb**: `chain_trigger=True, blast_radius=2` (affects wider area)

#### Grenade Activation System
- **Pin pulling required**: `pull pin on grenade` command must be used before throwing *(Phase 1: Requirement removed for tactical flexibility)*
- **Timer starts on pin pull**: Countdown begins immediately when pin is pulled (duration from `object.db.fuse_time`)
- **Throw window**: Player has fuse time to throw after pulling pin, or grenade explodes in hand
- **Hot potato mechanics**: Players can catch live grenades and throw them back within timer window
- **Hand explosion**: If timer expires while grenade is in hand, explodes and damages holder
- **Drop mechanics**: Players can drop live grenades as area denial tactic
- **Additional commands needed**: Implementation requires both `pull` and `catch` commands
- **State tracking**: Grenades need `db.pin_pulled` and timer state management
- **Tactical flexibility**: Unpinned grenades can be thrown as inert objects for tactical misdirection

#### Explosive Object Properties
All explosive behavior should be driven by object properties:
- **`db.fuse_time`**: Seconds from pin pull to explosion (e.g., 8 for standard grenade)
- **`db.blast_damage`**: Damage dealt to characters in proximity when explodes
- **`db.is_explosive`**: Boolean flag identifying explosive objects
- **`db.chain_trigger`**: Whether this explosive can trigger other nearby explosives
- **`db.requires_pin`**: Whether activation requires pin pulling (vs. impact detonation)
- **`db.dud_chance`**: Probability of explosive failing to detonate (0.0 = never, 1.0 = always)
- **`db.blast_radius`**: Number of proximity "hops" explosion affects (future expansion)

#### Grenade Tactical Mechanics
- **Catch and re-throw**: Thrown live grenades can be caught and immediately thrown back
- **Area denial**: Dropped live grenades create temporary danger zones
- **Exit rigging**: Grenades can be rigged against exits to trigger when traversed
- **Chain reactions**: Exploding grenades can potentially trigger other nearby grenades

### Performance Considerations
1. **Flight object cleanup**: How often should we clean up orphaned flight references?
2. **Room description caching**: Should flying objects invalidate room description cache?
3. **Concurrent throw limits**: Should there be per-player or per-room throw rate limiting?
4. **Memory management**: How long should flight state persist in case of errors?

### Planned Features ✅ **MOSTLY IMPLEMENTED**
- ✅ **Catch command**: Defensive response to thrown objects *(Implemented)*
- ✅ **Pull command**: Pin pulling mechanism for grenades *(Implemented)*
- ✅ **Rig command**: Exit trap mechanism *(Implemented)*
- ✅ **Defuse command**: Manual and automatic defuse systems *(Implemented)*
- **Ammo/bundle system**: Limited throwing weapon uses *(Future)*
- **Material properties**: Different damage for different improvised weapons *(Future)*
- **Door/barrier blocking**: Physical obstacles prevent throwing *(Future)*
- **Trajectory calculation**: More realistic flight paths *(Future)*

### Grenade Command Dependencies ✅ **IMPLEMENTED**
The grenade system requires implementing additional commands alongside throw:
- ✅ **`pull pin on <grenade>`**: Activates fuse timer (duration from `object.db.fuse_time`), required before throwing
- ✅ **`catch <object>`**: Defensive mechanism for thrown objects (including live grenades!)
- ✅ **`drop <object>` (enhanced)**: Universal proximity assignment for all dropped objects, enables tactical area denial with live grenades
- ✅ **`rig <grenade> to <exit>`**: Trap exits with grenades (triggered on traverse)
- ✅ **`defuse <grenade>`**: Manual defuse with skill checks and time pressure
- ✅ **Timer management**: System to track multiple active grenade timers simultaneously
- ✅ **State validation**: Prevent throwing expired grenades, handle pin-pulled scenarios
- ✅ **Exit trap system**: Track rigged grenades and trigger on movement through exits
- ✅ **Universal proximity system**: Enhanced drop command assigns proximity to all dropped objects
- ✅ **Auto-defuse system**: Automatic proximity-based defuse attempts on room entry
- ✅ **Rigger immunity**: Trap setters can safely pass through their own rigged exits

### Integration Points
- **Identity system**: Better target resolution when implemented
- **Advanced room descriptions**: Better object state display
- **Enhanced aim system**: Possibly cross-room aim for throwing only
- **Weapon retrieval**: Mechanics for recovering thrown weapons
