# Wrest Command Implementation Specification

## Overview
The `wrest` command enables **non-combat item snatching** from other characters' hands. It serves as the non-combat counterpart to the `disarm` command, allowing quick opportunistic grabbing of objects without entering combat mechanics.

## Core Mechanics

### Command Syntax
```
wrest <object> from <target>
```

### Validation Requirements
1. **Caller must NOT be in combat** (wrest is non-combat only)
2. **Target CAN be in combat** (allows grabbing from grappled/distracted targets)
3. **Caller must have at least one free hand** in Mr. Hand system
4. **Target must be in same room** as caller
5. **Object must exist in target's hands** (wielded via Mr. Hand system)

### Strategic Use Cases
- **Opportunistic theft**: Grab items while target is grappled by someone else
- **Quick snatch-and-run**: Grab phone/keys and flee before combat starts
- **Non-violent disarming**: Remove weapons without entering combat
- **Distraction grabs**: Take advantage when target is distracted by combat

## Design Philosophy

### Simplicity Over Complexity
- **Grit vs Grit contest**: Simple opposed roll using G.R.I.M. system
- **Grapple disadvantage**: Grappled targets roll with disadvantage (roll twice, take lower)
- **Instant success only against unconscious/dead**: No contest for incapacitated targets
- **Automatic hand selection**: System chooses hands automatically
- **First-match object selection**: Multiple objects with same name default to first found
- **No proximity requirements**: Works anywhere in same room (proximity is combat-only)

### Combat/Non-Combat Complementarity
- **In combat**: Use `disarm` (contested, turn-based, stat-based)
- **Out of combat**: Use `wrest` (Grit vs Grit, immediate resolution)

## Technical Implementation

### Technical Infrastructure Notes
- **Mr. Hand System**: Fully implemented in `typeclasses/characters.py` with `hands` AttributeProperty
- **Hand Structure**: Dictionary-based (`{"left": None, "right": None}`) supporting dynamic anatomy
- **Hand Management**: Complete `wield_item()`, `unwield_item()`, `list_held_items()` methods available
- **Combat State Detection**: Existing combat system integration for state validation
- **Timer System**: 6-second combat round timing available for cooldown implementation

### Validation Flow
```
1. Check caller not in combat
2. Check caller has free hand
3. Validate target exists in same room
4. Validate object exists in target's hands
5. Check if target is grappled (for disadvantage)
6. Execute Grit vs Grit contest (with disadvantage if target grappled, or instant success if target unconscious/dead)
7. If successful: Execute transfer
8. Announce action and result
9. Apply 6-second cooldown (optional)
```

### Mr. Hand Integration
- **Caller hand selection**: Use first available free hand from `caller.hands` dictionary
- **Target hand selection**: Take from first hand containing the specified object
- **Object matching**: Use standard object name matching (first match wins)
- **Dynamic anatomy support**: Works with any hand names in dictionary (third_hand, tail, etc.)
- **Post-transfer state**: Update both characters' hand dictionaries properly

#### Mr. Hand System Requirements
- **Caller validation**: Check `caller.hands` for any hand with `None` value
- **Target validation**: Check `target.hands.values()` for object presence
- **Transfer logic**: Use existing `unwield_item()` and `wield_item()` methods for proper state management
- **State consistency**: AttributeProperty automatically saves dictionary changes
- **Multi-Hand Flexibility**: Dictionary structure naturally supports additional appendages

### Object Selection Logic
```python
# Pseudo-code for object matching
def find_object_in_hands(target, object_name):
    for hand_name, wielded_object in target.hands.items():
        if wielded_object and object_name.lower() in wielded_object.key.lower():
            return hand_name, wielded_object
    return None, None

def find_free_hand(caller):
    for hand_name, wielded_object in caller.hands.items():
        if wielded_object is None:
            return hand_name
    return None
```

### Grapple Disadvantage Mechanics
```python
# Pseudo-code for grapple disadvantage
def roll_grit_with_disadvantage(character):
    grit_value = max(1, character.grit)
    roll1 = randint(1, grit_value)
    roll2 = randint(1, grit_value)
    return min(roll1, roll2)  # Take the lower roll

def is_target_grappled(target):
    # Check if target has grappled status in combat system
    # Implementation depends on grapple status tracking
    return hasattr(target.ndb, 'grappled') and target.ndb.grappled
```

## Room Announcements

### Success Messages
- **To caller**: "You quickly snatch the knife from Bob's hand!"
- **To target**: "Alice quickly snatches the knife from your hand!"
- **To room**: "Alice quickly snatches a knife from Bob's hand!"

### Failure Messages
- **To caller**: "You try to grab the knife from Bob's hand, but he holds on tight!"
- **To target**: "Alice tries to grab the knife from your hand, but you maintain your grip!"
- **To room**: "Alice tries to grab a knife from Bob's hand, but he resists!"

### Message Variations by Context
- **Combat target**: "You quickly grab the phone from Bob while he's grappled!"
- **Weapon snatch**: "You swiftly wrest the sword from Alice's grip!"
- **Utility grab**: "You snatch the keys from Bob's hand and prepare to run!"

## Error Handling

### Validation Failures
- **Caller in combat**: "You cannot wrest items while in combat. Use 'disarm' instead."
- **No free hands**: "You need at least one free hand to grab something."
- **Target not found**: "You cannot find '<target>' here."
- **Object not in hands**: "'<target>' is not holding '<object>' in their hands."
- **Object not found**: "You cannot find '<object>' to wrest."
- **Same room required**: "You must be in the same room as '<target>' to wrest from them."

### Edge Cases
- **Multiple objects same name**: Grabs first match, user must try again for others
- **Target drops object during attempt**: "The object is no longer in their hands"
- **Target leaves room**: "Your target is no longer here"
- **Caller becomes encumbered**: Standard inventory management applies

## Integration Points

### Existing Systems Used
- **Mr. Hand system**: For wielding validation and hand management
- **Combat handler checking**: To verify caller not in combat state
- **Room validation**: Standard same-room checking
- **Object searching**: Standard object name matching

### No Integration Required
- **Proximity system**: Not used (non-combat command)
- **Aim system**: Not applicable
- **Turn-based mechanics**: Instant execution
- **Damage system**: No combat implications

## Implementation Architecture

### Command Flow Overview
```
1. Parse "wrest <object> from <target>" syntax
2. Validate caller not in combat
3. Validate caller has free hand
4. Find and validate target in room
5. Find object in target's hands
6. Check target grapple status
7. Execute Grit vs Grit contest (with disadvantage if target grappled, unless target unconscious/dead)
8. If successful: Update both hand dictionaries
9. Announce result to room
```

### Constants Required
- `MSG_WREST_SUCCESS_CALLER`
- `MSG_WREST_SUCCESS_TARGET` 
- `MSG_WREST_SUCCESS_ROOM`
- `MSG_WREST_FAILED_CALLER`
- `MSG_WREST_FAILED_TARGET`
- `MSG_WREST_FAILED_ROOM`
- `MSG_WREST_IN_COMBAT`
- `MSG_WREST_NO_FREE_HANDS`
- `MSG_WREST_TARGET_NOT_FOUND`
- `MSG_WREST_OBJECT_NOT_IN_HANDS`
- `MSG_WREST_OBJECT_NOT_FOUND`

### Command Location
- **File**: `commands/CmdInventory.py` — `CmdWrest` (key `"wrest"`), with related logic in `commands/combat/special_actions.py`
- **Import location**: General inventory commands, not a standalone module
- **Reason**: Works outside combat, different from combat commands

## Testing Scenarios

### Basic Functionality
1. Wrest object from non-combat target
2. Wrest object from combat target (grappled)
3. Multiple objects same name (grab one, try again)
4. Caller has no free hands (error)

### Edge Cases
1. Target not in room
2. Object not in target's hands
3. Caller enters combat (command blocked)
4. Target leaves room during command

### Integration Tests
1. Wrest weapon then enter combat with it
2. Wrest from grappled target while they're in combat
3. Multiple players wresting from same target
4. Wrest then immediate flee scenarios

## Tactical Scenarios

### Opportunistic Theft
```
# Bob is grappled by Charlie
wrest phone from bob
flee north
```

### Non-Violent Disarming
```
# Remove weapon without starting combat
wrest sword from alice
# Alice now unarmed, can roleplay resolution
```

### Coordinated Tactics
```
# Team coordination
Player A: grapple bob
Player B: wrest gun from bob  
Player A: release bob
# Bob now disarmed and can choose to flee or fight unarmed
```

## Design Rationale

### Why Grit vs Grit Contest?
- **G.R.I.M. system integration**: Uses established attribute system
- **Balanced competition**: Both characters have chance to succeed
- **Instant resolution**: Single roll determines outcome immediately
- **Physical nature**: Grit represents physical strength and determination
- **Roleplay enhancement**: Creates dramatic tension and meaningful stakes

### Why Allow Combat Targets?
- **Tactical depth**: Creates opportunities during combat situations
- **Coordination**: Enables team tactics (one grapples, another grabs)
- **Realism**: Someone grappled/distracted is vulnerable to item theft
- **Balance**: Gives non-combatants ways to influence combat indirectly

### Why No Proximity Requirement?
- **Non-combat nature**: Proximity system is combat-specific
- **Accessibility**: Anyone in room can attempt (within reason)
- **Simplicity**: Reduces validation complexity
- **Roleplay focus**: Room-scale interaction feels natural

## Mr. Hand System Flexibility Analysis

### Dynamic Anatomy Support
The Mr. Hand system's dictionary-based design provides excellent flexibility for non-standard anatomy:

#### Current Implementation
```python
# Default human anatomy
hands = AttributeProperty(
    {"left": None, "right": None},
    category="equipment",
    autocreate=True
)
```

#### Extended Anatomy Examples
```python
# Alien with three arms
hands = {"left": None, "right": None, "third_arm": None}

# Character with prehensile tail
hands = {"left": None, "right": None, "tail": None}

# Disabled character with prosthetics
hands = {"left": None, "prosthetic_right": None}

# Fantasy creature with tentacles
hands = {"tentacle_1": None, "tentacle_2": None, "tentacle_3": None, "tentacle_4": None}
```

#### Wrest Command Compatibility
The wrest command naturally supports any hand configuration because it uses dictionary iteration:

```python
# Find object in any appendage
for hand_name, held_item in target.hands.items():
    if held_item and held_item.key.lower() == object_name.lower():
        return hand_name, held_item

# Find free appendage for wrested item
for hand_name, held_item in caller.hands.items():
    if held_item is None:
        return hand_name
```

### System Benefits
1. **No hardcoded assumptions**: No references to specific hand names like "left" or "right"
2. **Automatic scaling**: Works with 1 hand, 2 hands, 8 tentacles, etc.
3. **Graceful degradation**: If a character loses a hand, simply remove it from dictionary
4. **Name flexibility**: Hand names can be descriptive ("cybernetic_left", "tentacle_north", etc.)
5. **Future-proof**: New appendage types require no command modifications

### Implementation Implications
- **Wrest works unchanged**: Will automatically handle third hands, tails, tentacles
- **Disarm compatibility**: Combat disarm command should use same dictionary iteration
- **Display flexibility**: Hand listings adapt automatically to available appendages
- **Admin tools**: Easy to modify character anatomy by updating hands dictionary

## Future Considerations

### Potential Enhancements
- **Speed bonus**: Slight delay before target notices (2-3 seconds)
- **Alert system**: Target gets notification after brief delay
- **Skill integration**: Future skill system could add success chances
- **Weight limits**: Heavy objects might require both hands

### Integration Opportunities
- **Identity system**: Better target resolution when implemented
- **Emote system**: Custom wrest emotes for different scenarios
- **Messaging system**: More detailed context-aware messages
- **Animation system**: Visual indicators for successful wrests

## Open Questions

### Implementation Details
1. **Command placement**: Should this be in general commands or combat module?
2. **Timing**: Should there be any delay, or truly instant?
3. **Notifications**: Should target be notified immediately or after delay?
4. **Logging**: Should wrests be logged for admin oversight?

### Balance Considerations
1. **Abuse prevention**: Any mechanisms to prevent excessive wresting?
2. **Roleplay enforcement**: Should there be RP requirements?
3. **Item protection**: Should some items be "unwrestable"?
4. **Combat initiation**: Should wresting weapons from someone trigger combat?

## Recommended Answers
Based on the design philosophy of simplicity and non-combat focus:

1. **Command placement**: General commands (works outside combat)
2. **Timing**: Instant execution (speed is the point)
3. **Notifications**: Immediate (clear communication)
4. **Logging**: Standard command logging only
5. **Abuse prevention**: Rely on roleplay and admin oversight
6. **Item protection**: Not initially (keep it simple)
7. **Combat initiation**: No (maintains non-combat nature)
