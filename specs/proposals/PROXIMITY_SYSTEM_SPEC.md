# Proximity System Architecture Specification

## Overview

The G.R.I.M. Combat System keeps two proximity systems, which grew up to handle different uses: combat proximity (character to character, for melee) and universal proximity (any entity to any entity, for grenades and objects). This document describes how the two work, the problems of keeping two, and proposes unifying them into one system (Option A). The unification is 📋 UNBUILT (no issue).

## The two systems

### System 1: Combat proximity (`NDB_PROXIMITY`)

- **Purpose**: character-to-character melee proximity for combat mechanics.
- **Constant**: `NDB_PROXIMITY = "in_proximity_with"`.
- **Data structure**: `character.ndb.in_proximity_with = {set_of_characters}`. It is a set; the universal store `ndb.proximity` is a list.
- **Usage pattern**: bidirectional character relationships.
- **Scope**: character to character only.
- **Use cases**: melee combat, grappling, disarm actions. Turn-based combat validates proximity through the combat handler, and melee actions require proximity.
- **Established by**: a successful grapple, advance or charge; a melee attack that starts a fight, or that joins one and wins the contested roll; joining combat already grappling; jumping on an explosive (melee links to everyone on the explosive's universal list); and the same-room re-link of fighters after a server reload.
- **Cleared by**: a won retreat (melee links to opponents only); leaving combat (`clear_all_proximity` in `world/combat/utils.py`); exit traversal (`at_traverse` in `typeclasses/exits.py`); and combat movement and falls (`clear_proximity_on_room_change`, called from `world/combat/movement_resolution.py` and `world/gravity.py`).
- **Integration**: deep integration with the combat handler and special actions.

Where it is used:

- `commands/combat/special_actions.py`:
  - `CmdGrapple` needs no prior proximity ("rush in"). `establish_grapple`, `resolve_grapple_initiate` and `resolve_grapple_takeover` in `world/combat/grappling.py` establish it on success.
  - `CmdDisarm` requires proximity for a disarm attempt.
  - `CmdReleaseGrapple` queues a release; `resolve_release_grapple` in `world/combat/grappling.py` ends the hold but leaves the pair in melee proximity.
- `typeclasses/exits.py`, `at_traverse`: clears combat proximity on room transitions.
- `world/combat/proximity.py`, `clear_proximity_on_room_change`: clears both stores when a character changes room without an exit: advance, cross-room charge and grapple drag (`world/combat/movement_resolution.py`) and each cell of a fall (`world/gravity.py`).

### System 2: Universal proximity (`NDB_PROXIMITY_UNIVERSAL`)

- **Purpose**: character-to-object and object-to-character relationships.
- **Constant**: `NDB_PROXIMITY_UNIVERSAL = "proximity"`.
- **Data structure**: `entity.ndb.proximity = [list_of_entities]`.
- **Usage pattern**: mixed entity relationships (characters, grenades, objects).
- **Scope**: any entity to any entity (characters, objects, grenades).
- **Use cases**: grenade blast zones, object landing proximity, defuse mechanics, proximity-based automatic defuse.
- **Established by**: object throws, drops, grenade landings, defuse attempts, and a thrown weapon that hits (the thrower goes on the target's list). A landed grenade or object inherits its target's proximity.
- **Cleared by**: manual removal, movement between rooms, defuse success. Retreat does not clear it (see "Retreat" below).
- **Integration**: throw command, grenade system, defuse mechanics.

Where it is used:

- `world/combat/throwing.py`: `assign_landing_proximity` and `handle_grenade_landing` give a landed object its target's proximity; `resolve_weapon_hit` puts the thrower of a thrown weapon that hits on the target's list.
- `commands/CmdExplosives.py`: `CmdDefuse.establish_mutual_proximity` (defuse attempts) and `clear_grenade_proximity` (defuse success).
- `commands/explosion_utils.py`: `check_auto_defuse` (proximity-based automatic defuse) and `get_unified_explosion_proximity` (the blast list at detonation).
- `commands/CmdInventory.py`: drop adds the dropper to the item's list.
- `typeclasses/exits.py`, `at_traverse`: clears universal proximity on room transitions.
- `world/combat/proximity.py`, `clear_proximity_on_room_change`: clears both stores when a character changes room without an exit (combat movement and falls).
- `world/gravity.py`, `_reset_proximity`: empties a falling item's universal list in each cell.

### Who is in the blast at detonation

At detonation, `get_unified_explosion_proximity` in `commands/explosion_utils.py` adds everyone melee-linked to anyone on the grenade's list (human shields), then drops anyone not in the blast room (#2490). A stale entry left by retreat or by walking out still counts while that person is in the blast room, but does not reach through a wall.

## Cleanup on movement

### Exit traversal

`at_traverse` in `typeclasses/exits.py` cleans both stores with the same pattern. For combat proximity it clears the mover's bidirectional relationships: it removes the mover from each linked character's set, then empties the mover's own set. For universal proximity it walks the mover's OWN universal list, removes the mover from each entry's list, then empties the mover's list. Throw and landing write only the object's list, so a person a thrown grenade lists stays on that list after leaving through an exit (#2540).

Both cleanups are skipped for a victim being dragged in a grapple, so the victim stays linked to the grappler. The advance drag in `world/combat/movement_resolution.py` likewise clears only the grappler and re-links the pair after the move.

### Movement without an exit

Exit traversal is not the only movement-cleanup site. Combat movement (`advance`, a cross-room `charge`, a grapple drag) calls `char.move_to()` directly and never traverses an exit, so `at_traverse` never fires on those paths. `clear_proximity_on_room_change` in `world/combat/proximity.py` (#2490) covers them: it is invoked from `world/combat/movement_resolution.py` and from each cell of a fall in `world/gravity.py`, and clears both stores.

### Retreat

`CmdRetreat` in `commands/combat/movement.py` contains no reference to `NDB_PROXIMITY_UNIVERSAL`. Its resolver, `resolve_retreat` in `world/combat/movement_resolution.py`, reads the grenade list only to decide whether there is anyone to retreat from (it unions both stores into `all_proximity`). On success it calls `break_proximity` against melee opponents and never touches `NDB_PROXIMITY_UNIVERSAL`. Retreating therefore does not remove you from a grenade's blast list. This is the same asymmetry family as #2540.

## Architectural challenges

### Code duplication
- **Identical cleanup logic**: both systems require the same bidirectional cleanup patterns.
- **Parallel command handling**: the retreat command has to handle both systems; today it reads both and cleans only the melee one (see "Retreat").
- **Redundant validation**: similar proximity checks in different systems.

### Conceptual overlap
- **Character-to-character relationships**: could be handled by either system.
- **Mixed proximity scenarios**: characters near grenades AND in combat proximity.
- **System selection confusion**: developers must choose which system to use.

### Maintenance burden
- **Dual updates required**: changes to proximity logic must be applied to both systems.
- **Inconsistent behavior**: different systems may handle edge cases differently.
- **Testing complexity**: all proximity features must be tested in both contexts.

### Performance implications
- **Memory overhead**: characters may have duplicate proximity data.
- **Cleanup overhead**: movement transitions must clean up two separate systems.
- **Lookup complexity**: commands must check both systems for a complete proximity picture.

## 📋 UNBUILT (no issue): Unification strategy, Option A (recommended)

### Core principle
**Single universal proximity system**: replace both systems with one unified proximity system that handles all entity-to-entity relationships.

### Unified system design

```python
# Single proximity constant
NDB_PROXIMITY_UNIFIED = "proximity_relationships"

# Single data structure for all entities
entity.ndb.proximity_relationships = [list_of_entities]

# Usage pattern examples
character.ndb.proximity_relationships = [other_char, grenade, dropped_weapon]
grenade.ndb.proximity_relationships = [char1, char2, char3]
```

Any consolidation has to account for the non-traversal movement path (`clear_proximity_on_room_change`) as well as exit traversal.

### Unified proximity utilities

The proposed utilities in `world/combat/proximity.py`: `establish_proximity(entity1, entity2)` establishes bidirectional proximity between any two entities; `remove_proximity(entity1, entity2)` removes it; `get_proximity_list(entity)` returns all entities in proximity to an entity; `clear_all_proximity(entity)` removes an entity from all proximity relationships; `in_proximity(entity1, entity2)` checks whether two entities are in proximity.

`world/combat/proximity.py` already holds melee-only helpers: `establish_proximity`, `break_proximity`, `clear_all_proximity`, `get_proximity_list` and `is_in_proximity` (plus `clear_proximity_on_room_change`, which clears both stores). The proposal calls two of them by other names: `remove_proximity` is `break_proximity`, and `in_proximity` is `is_in_proximity`.

### Migration strategy

#### Phase 1: Implementation
1. **Create unified constant**: define `NDB_PROXIMITY_UNIFIED` in constants.py.
2. **Implement unified utilities**: create common proximity management functions.
3. **Add compatibility layer**: functions that write to both old and new systems during transition.

This compatibility layer (and its removal in Phase 4, the "Migration compatibility layer" below and the data-loss mitigation) conflicts with `DEVELOPMENT_GUIDE.md`, Pull Request Process: "repoint every caller and delete the old name in the same PR: no aliases, wrappers or re-exports left for callers".

#### Phase 2: Combat system migration
1. **Update special_actions.py**: migrate grapple, disarm, release to the unified system.
2. **Update combat handler**: use unified proximity for combat validation.
3. **Test combat functionality**: ensure no regressions in combat mechanics.

#### Phase 3: Universal system migration
1. **Update `world/combat/throwing.py`**: migrate grenade and object proximity to the unified system.
2. **Update defuse system**: use unified proximity for defuse mechanics.
3. **Test grenade functionality**: ensure blast zones and defuse work correctly.

#### Phase 4: Cleanup and optimization
1. **Remove old constants**: delete `NDB_PROXIMITY` and `NDB_PROXIMITY_UNIVERSAL`.
2. **Simplify movement cleanup**: single proximity cleanup in exits.py.
3. **Update retreat command**: single proximity system handling.
4. **Remove compatibility layer**: clean up transitional code.

### Migration compatibility layer

Temporary functions during migration: `get_legacy_combat_proximity(character)` returns combat proximity using the old or new system; `get_legacy_universal_proximity(entity)` returns universal proximity using the old or new system; `establish_legacy_proximity(entity1, entity2, system_type)` establishes proximity in the old and new systems during transition.

### Benefits

#### Architectural simplification
- **Single source of truth**: one proximity system for all relationships.
- **Unified cleanup**: one cleanup pattern for all proximity relationships.
- **Consistent behavior**: same proximity logic for all use cases.
- **Simplified commands**: single proximity check for all mechanics.

#### Development benefits
- **Reduced maintenance**: changes apply to one system.
- **Clearer mental model**: developers work with one proximity concept.
- **Easier testing**: single system to validate.
- **Performance improvement**: eliminate redundant data and operations.

#### Functional benefits
- **Rich relationships**: characters can be in proximity to any entity.
- **Complex scenarios**: natural handling of mixed proximity situations.
- **Extensibility**: easy addition of new proximity-based mechanics.
- **Consistency**: same proximity behavior across all game systems.

In sum, the unification would simplify the codebase by eliminating redundant systems, improve maintainability with a single proximity paradigm, enhance performance by reducing duplicate operations, and enable richer gameplay through unified entity relationships. The phased Option A migration is proposed as a safe approach that minimizes risk, and the unified system as the foundation for future proximity-based features and game mechanics.

### Implementation risks and mitigation

| Risk | Mitigation | Fallback |
|---|---|---|
| Combat system regression | Comprehensive testing of all combat actions during migration | Rollback plan: keep old combat proximity as backup during Phase 2 |
| Grenade system disruption | Extensive testing of grenade mechanics during migration | Rollback plan: keep old universal proximity as backup during Phase 3 |
| Performance degradation | Profile proximity operations before and after migration | Optimization: implement proximity caching if needed |
| Data loss during migration | Compatibility layer maintains both systems during transition | Safety: migration can be paused at any phase if issues arise |

### Testing strategy

- **Unit tests**: test all unified proximity functions; bidirectional consistency (proximity relationships are always mutual); edge cases (null entities, invalid relationships, circular references).
- **Integration tests**: all special actions work with unified proximity; blast zones and defuse work correctly; room transitions clear all proximity properly.
- **Regression tests**: all existing combat functionality preserved; all existing grenade mechanics preserved; mixed scenarios (characters in combat near live grenades).
- **Performance tests**: measure the performance impact of the unified system; ensure it reduces memory overhead; verify movement cleanup is faster with a single system.

### Success metrics

- **Code quality**: expect a 20-30% reduction in proximity-related code; cyclomatic complexity improvement in proximity functions; zero duplicate proximity logic patterns.
- **Performance**: reduced NDB storage for proximity data; faster proximity lookups and modifications; faster room transition processing.
- **Maintainability**: faster implementation of new proximity features; fewer proximity-related edge-case bugs; a single proximity system is easier to document.

### Next steps
1. **Review and approval**: stakeholder review of this specification.
2. **Create implementation timeline**: estimate effort for each migration phase.
3. **Set up testing framework**: prepare a comprehensive test suite for migration.
4. **Begin Phase 1**: implement unified proximity utilities and the compatibility layer.

This specification is the architectural blueprint for proximity system unification; implementation decisions should reference it for consistency with the overall strategy.

## Alternative approaches considered

### Option B: System specialization
Keep both systems but formalize their distinct roles: combat proximity for character-to-character melee relationships, universal proximity for character-to-object relationships.

**Rejected because**: still maintains code duplication and conceptual overlap.

### Option C: Hierarchical systems
Create a base proximity system with specialized subclasses: BaseProximity → CombatProximity, UniversalProximity.

**Rejected because**: adds complexity without eliminating duplication.

### Option D: Context-based single system
Use one system with context flags to distinguish relationship types: `proximity_relationships = [(entity, context), ...]`.

**Rejected because**: over-engineered for current needs.

## Not decided

- Should the phased migration plan be kept at all, given that its compatibility layer conflicts with the no-wrappers rule in `DEVELOPMENT_GUIDE.md`?
- Should the two proximity stores be unified (Option A, another option), or both kept and merged when read, as the code does today? Also open on #3335.
