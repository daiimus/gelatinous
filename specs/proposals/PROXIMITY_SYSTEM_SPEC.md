# Proximity System Architecture Specification

> **Status:** 📋 Proposal — the live dual-proximity system it documents is accurate; the Option-A unification it proposes is NOT implemented.

## Overview
The G.R.I.M. Combat System currently operates with dual proximity systems that evolved to handle different use cases. This document outlines the current architecture, identifies the challenges, and proposes a unification strategy.

## Current Dual Proximity Architecture

### System 1: Combat Proximity (`NDB_PROXIMITY`)
**Purpose**: Character-to-character melee proximity for combat mechanics
**Constant**: `NDB_PROXIMITY = "in_proximity_with"`
**Data Structure**: `character.ndb.in_proximity_with = [list_of_characters]`
**Usage Pattern**: Bidirectional character relationships

#### Combat Proximity Characteristics
- **Scope**: Character-to-character only
- **Use Cases**: Melee combat, grappling, disarm actions
- **Establishment**: Combat actions (grapple, melee attack)
- **Cleanup**: Manual removal, retreat command, movement between rooms
- **Integration**: Deep integration with combat handler and special actions

#### Combat Proximity Code Locations
```python
# Primary usage in combat system
commands/combat/special_actions.py:
- CmdGrapple: Establishes proximity on successful grapple
- CmdDisarm: Requires proximity for disarm attempts
- CmdReleaseGrapple: Clears proximity relationships

# Movement cleanup
typeclasses/exits.py:
- at_traverse(): Clears combat proximity on room transitions
```

### System 2: Universal Proximity (`NDB_PROXIMITY_UNIVERSAL`)
**Purpose**: Character-to-object and object-to-character relationships
**Constant**: `NDB_PROXIMITY_UNIVERSAL = "proximity"`
**Data Structure**: `entity.ndb.proximity = [list_of_entities]`
**Usage Pattern**: Mixed entity relationships (characters, grenades, objects)

#### Universal Proximity Characteristics
- **Scope**: Any entity to any entity (characters, objects, grenades)
- **Use Cases**: Grenade blast zones, object landing proximity, defuse mechanics
- **Establishment**: Object throws, drops, grenade landings, defuse attempts
- **Cleanup**: Manual removal, retreat command, movement between rooms, defuse success
- **Integration**: Throw command, grenade system, defuse mechanics

#### Universal Proximity Code Locations
```python
# Primary usage in grenade/object system
commands/CmdThrow.py:
- Landing proximity: Objects inherit proximity from landing targets
- Grenade proximity: Blast zone establishment and inheritance
- Defuse proximity: Dynamic proximity establishment for defuse attempts

# Movement cleanup
typeclasses/exits.py:
- at_traverse(): Clears universal proximity on room transitions
```

## Current Implementation Status

### Combat Proximity Integration
- ✅ **Special Actions**: Grapple, disarm, release mechanics
- ✅ **Combat Handler**: Turn-based combat proximity validation
- ✅ **Movement Cleanup**: Room transition cleanup
- ✅ **Command Validation**: Proximity requirements for melee actions

### Universal Proximity Integration
- ✅ **Throw System**: Object landing and grenade proximity
- ✅ **Defuse System**: Dynamic proximity establishment
- ✅ **Grenade Mechanics**: Blast zone management and inheritance
- ✅ **Movement Cleanup**: Room transition cleanup
- ✅ **Auto-defuse**: Proximity-based automatic defuse attempts

### Cleanup Implementation
Both systems have identical cleanup patterns in `typeclasses/exits.py`:
```python
def at_traverse(self, traversing_object, target_location, **kwargs):
    # Combat proximity cleanup
    if hasattr(traversing_object.ndb, NDB_PROXIMITY):
        # Clear bidirectional combat proximity relationships
        
    # Universal proximity cleanup  
    if hasattr(traversing_object.ndb, NDB_PROXIMITY_UNIVERSAL):
        # Clear bidirectional universal proximity relationships
```

## Architectural Challenges

### Code Duplication
- **Identical cleanup logic**: Both systems require the same bidirectional cleanup patterns
- **Parallel command handling**: Retreat command must handle both systems
- **Redundant validation**: Similar proximity checks in different systems

### Conceptual Overlap
- **Character-to-character relationships**: Could be handled by either system
- **Mixed proximity scenarios**: Characters near grenades AND in combat proximity
- **System selection confusion**: Developers must choose which system to use

### Maintenance Burden
- **Dual updates required**: Changes to proximity logic must be applied to both systems
- **Inconsistent behavior**: Different systems may handle edge cases differently
- **Testing complexity**: All proximity features must be tested in both contexts

### Performance Implications
- **Memory overhead**: Characters may have duplicate proximity data
- **Cleanup overhead**: Movement transitions must clean up two separate systems
- **Lookup complexity**: Commands must check both systems for complete proximity picture

## Unification Strategy: Option A (Recommended)

### Core Principle
**Single Universal Proximity System**: Replace both systems with one unified proximity system that handles all entity-to-entity relationships.

### Unified System Design
```python
# Single proximity constant
NDB_PROXIMITY_UNIFIED = "proximity_relationships"

# Single data structure for all entities
entity.ndb.proximity_relationships = [list_of_entities]

# Usage pattern examples
character.ndb.proximity_relationships = [other_char, grenade, dropped_weapon]
grenade.ndb.proximity_relationships = [char1, char2, char3]
```

### Migration Strategy

#### Phase 1: Implementation
1. **Create unified constant**: Define `NDB_PROXIMITY_UNIFIED` in constants.py
2. **Implement unified utilities**: Create common proximity management functions
3. **Add compatibility layer**: Functions that write to both old and new systems during transition

#### Phase 2: Combat System Migration
1. **Update special_actions.py**: Migrate grapple, disarm, release to unified system
2. **Update combat handler**: Use unified proximity for combat validation
3. **Test combat functionality**: Ensure no regressions in combat mechanics

#### Phase 3: Universal System Migration
1. **Update CmdThrow.py**: Migrate grenade and object proximity to unified system
2. **Update defuse system**: Use unified proximity for defuse mechanics
3. **Test grenade functionality**: Ensure blast zones and defuse work correctly

#### Phase 4: Cleanup and Optimization
1. **Remove old constants**: Delete `NDB_PROXIMITY` and `NDB_PROXIMITY_UNIVERSAL`
2. **Simplify movement cleanup**: Single proximity cleanup in exits.py
3. **Update retreat command**: Single proximity system handling
4. **Remove compatibility layer**: Clean up transitional code

### Unified System Benefits

#### Architectural Simplification
- **Single source of truth**: One proximity system for all relationships
- **Unified cleanup**: One cleanup pattern for all proximity relationships
- **Consistent behavior**: Same proximity logic for all use cases
- **Simplified commands**: Single proximity check for all mechanics

#### Development Benefits
- **Reduced maintenance**: Changes apply to one system
- **Clearer mental model**: Developers work with one proximity concept
- **Easier testing**: Single system to validate
- **Performance improvement**: Eliminate redundant data and operations

#### Functional Benefits
- **Rich relationships**: Characters can be in proximity to any entity
- **Complex scenarios**: Natural handling of mixed proximity situations
- **Extensibility**: Easy addition of new proximity-based mechanics
- **Consistency**: Same proximity behavior across all game systems

### Implementation Details

#### Unified Proximity Utilities
```python
# world/combat/proximity.py
def establish_proximity(entity1, entity2):
    """Establish bidirectional proximity between any two entities."""

def remove_proximity(entity1, entity2):
    """Remove bidirectional proximity between two entities."""

def get_proximity_list(entity):
    """Get all entities in proximity to the given entity."""

def clear_all_proximity(entity):
    """Remove entity from all proximity relationships."""

def in_proximity(entity1, entity2):
    """Check if two entities are in proximity."""
```

#### Migration Compatibility Layer
```python
# Temporary functions during migration
def get_legacy_combat_proximity(character):
    """Return combat proximity using old or new system."""
    
def get_legacy_universal_proximity(entity):
    """Return universal proximity using old or new system."""
    
def establish_legacy_proximity(entity1, entity2, system_type):
    """Establish proximity in old and new systems during transition."""
```

## Alternative Approaches Considered

### Option B: System Specialization
Keep both systems but formalize their distinct roles:
- Combat proximity for character-to-character melee relationships
- Universal proximity for character-to-object relationships

**Rejected because**: Still maintains code duplication and conceptual overlap

### Option C: Hierarchical Systems
Create a base proximity system with specialized subclasses:
- BaseProximity → CombatProximity, UniversalProximity

**Rejected because**: Adds complexity without eliminating duplication

### Option D: Context-Based Single System
Use one system with context flags to distinguish relationship types:
- `proximity_relationships = [(entity, context), ...]`

**Rejected because**: Over-engineered for current needs

## Implementation Risks and Mitigation

### Risk: Combat System Regression
**Mitigation**: Comprehensive testing of all combat actions during migration
**Rollback Plan**: Keep old combat proximity as backup during Phase 2

### Risk: Grenade System Disruption  
**Mitigation**: Extensive testing of grenade mechanics during migration
**Rollback Plan**: Keep old universal proximity as backup during Phase 3

### Risk: Performance Degradation
**Mitigation**: Profile proximity operations before and after migration
**Optimization**: Implement proximity caching if needed

### Risk: Data Loss During Migration
**Mitigation**: Compatibility layer maintains both systems during transition
**Safety**: Migration can be paused at any phase if issues arise

## Testing Strategy

### Unit Tests
- **Proximity utilities**: Test all unified proximity functions
- **Bidirectional consistency**: Ensure proximity relationships are always mutual
- **Edge cases**: Null entities, invalid relationships, circular references

### Integration Tests
- **Combat actions**: All special actions work with unified proximity
- **Grenade mechanics**: Blast zones and defuse work correctly
- **Movement cleanup**: Room transitions clear all proximity properly

### Regression Tests
- **Combat scenarios**: All existing combat functionality preserved
- **Grenade scenarios**: All existing grenade mechanics preserved
- **Mixed scenarios**: Characters in combat near live grenades

### Performance Tests
- **Proximity operations**: Measure performance impact of unified system
- **Memory usage**: Ensure unified system reduces memory overhead
- **Cleanup efficiency**: Verify movement cleanup is faster with single system

## Success Metrics

### Code Quality Metrics
- **Lines of code reduction**: Expect 20-30% reduction in proximity-related code
- **Complexity reduction**: Cyclomatic complexity improvement in proximity functions
- **Duplication elimination**: Zero duplicate proximity logic patterns

### Performance Metrics
- **Memory usage**: Reduced NDB storage for proximity data
- **Operation speed**: Faster proximity lookups and modifications
- **Cleanup speed**: Faster room transition processing

### Maintainability Metrics
- **Development velocity**: Faster implementation of new proximity features
- **Bug reduction**: Fewer proximity-related edge case bugs
- **Documentation clarity**: Single proximity system easier to document

## Conclusion

The unification of our dual proximity systems represents a significant architectural improvement that will:

1. **Simplify the codebase** by eliminating redundant systems
2. **Improve maintainability** by providing a single proximity paradigm
3. **Enhance performance** by reducing duplicate operations
4. **Enable richer gameplay** through unified entity relationships

The proposed Option A migration strategy provides a safe, phased approach that minimizes risk while delivering substantial benefits. The unified system will serve as a solid foundation for future proximity-based features and game mechanics.

## Next Steps

1. **Review and approval**: Stakeholder review of this specification
2. **Create implementation timeline**: Estimate effort for each migration phase
3. **Set up testing framework**: Prepare comprehensive test suite for migration
4. **Begin Phase 1**: Implement unified proximity utilities and compatibility layer

---

*This specification serves as the architectural blueprint for proximity system unification. All implementation decisions should reference this document to ensure consistency with the overall strategy.*
