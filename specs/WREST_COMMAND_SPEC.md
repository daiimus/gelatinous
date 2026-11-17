# Wrest Command Implementation Specification

> **Status:** ✅ **SHIPPED** — verified against code 2026-08-02.
>
> **⚠ Spec-vs-code corrections — the following claims were FALSE when audited:**
> - "Related logic in `commands/combat/special_actions.py`" — there is none; the command is self-contained in `CmdWrest` (`commands/CmdInventory.py`).
> - Code is ahead of spec: `CmdWrest` refuses to wrest integrated cyberware. Tests: `world/tests/test_wrest_contest_branches.py` (contest branches) and `world/tests/test_a_failed_wrest_gives_it_back.py` (transfer and restore).

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
- **Instant success only against unconscious/dead**: No contest for incapacitated targets. Consciousness is read from `world.consent.is_conscious`; a target whose state cannot be read is contested. Integrated cyberware cannot be wrested even from the unconscious
- **Automatic hand selection**: System chooses hands automatically
- **First-match object selection**: Multiple objects with same name default to first found
- **No proximity requirements**: Works anywhere in same room (proximity is combat-only)

### Combat/Non-Combat Complementarity
- **In combat**: Use `disarm` (contested, turn-based, stat-based)
- **Out of combat**: Use `wrest` (Grit vs Grit, immediate resolution)

## Technical Implementation

### Technical Infrastructure Notes
- **Mr. Hand System**: `Character.hands` (`typeclasses/characters.py`) is a view rebuilt on every read from the species' grasping containers, minus severed or dead ones. What each hand holds is stored in the `held_items` AttributeProperty
- **Hand Structure**: Dictionary keyed by anatomical container name (`{"left_hand": None, "right_hand": None}` for a human) supporting dynamic anatomy
- **Hand Management**: Complete `wield_item()`, `unwield_item()`, `list_held_items()` methods available
- **Combat State Detection**: Existing combat system integration for state validation
- **Timer System**: 6-second combat round timing available for cooldown implementation; wrest uses no cooldown (📋 UNBUILT (no issue))

### Validation Flow
```
1. Check caller not in combat
2. Check caller has free hand
3. Validate target exists in same room
4. Validate object exists in target's hands (integrated cyberware is refused here)
5. Check if target is grappled (for disadvantage)
6. Execute Grit vs Grit contest (with disadvantage if target grappled, or instant success if target unconscious/dead)
7. If successful: Execute transfer
8. Announce action and result
9. Apply 6-second cooldown (optional) — 📋 UNBUILT (no issue): wrest has no cooldown and can be retried at once
```

### Mr. Hand Integration
- **Caller hand selection**: Use first available free hand from `caller.hands` dictionary
- **Target hand selection**: Take from first hand containing the specified object
- **Object matching**: Use standard object name matching (first match wins)
- **Dynamic anatomy support**: Works with any hand names in dictionary (third_hand, tail, etc.)
- **Post-transfer state**: the victim's hand is freed when the item leaves them; the caller's hand is filled by `wield_item`, which writes `held_items`

#### Mr. Hand System Requirements
- **Caller validation**: Check `caller.hands` for any hand with `None` value
- **Target validation**: Check `target.hands.values()` for object presence
- **Transfer logic**: move the item to the caller (`move_to`); `Character.at_object_leave` frees the victim's hand (#2468). Then `caller.wield_item(item, free_hand)`. If the caller is not then wielding it, the item goes back to the victim's original hand (#2489, #2536)
- **Multi-Hand Flexibility**: Dictionary structure naturally supports additional appendages

### Object Selection Logic
```python
# Pseudo-code for object matching
def find_object_in_hands(caller, target, object_name):
    # The caller's standard search, limited to the items in the
    # target's hands; with several matches the first is taken.
    held = [item for item in target.hands.values() if item]
    matches = caller.search(object_name, candidates=held, quiet=True)
    return matches[0] if matches else None

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
    # Grappled = the target's entry in their combat handler's
    # combatants list has a grappled_by_dbref.
    handler = target.ndb.combat_handler
    entry = next(e for e in handler.db.combatants if e["char"] == target)
    return entry.get("grappled_by_dbref") is not None
```

## Room Announcements

### Success Messages
- **To caller**: "You quickly snatch the knife from Bob's hand!"
- **To target**: "Alice quickly snatches the knife from your hand!"
- **To room**: "Alice quickly snatches a knife from Bob's hand!"

### Failure Messages
- **To caller**: "You try to grab the knife from Bob's hand, but they hold on tight!"
- **To target**: "Alice tries to grab the knife from your hand, but you maintain your grip!"
- **To room**: "Alice tries to grab a knife from Bob's hand, but they resist!"

Wresting is never quiet, as built: the room line names the wrester as the one acting, so a hidden wrester is revealed before it is sent, whether the attempt wins or fails (`msg_room_identity`, #3769). The item is named as the wrester sees it, except remains (a corpse or a severed head), which each reader sees under their own name for it (`named_for_each`, #3821).

### Message Variations by Context
📋 UNBUILT (no issue): the command sends one fixed success set and one fixed failure set; nothing varies by grapple, weapon or item type.

- **Combat target**: "You quickly grab the phone from Bob while he's grappled!"
- **Weapon snatch**: "You swiftly wrest the sword from Alice's grip!"
- **Utility grab**: "You snatch the keys from Bob's hand and prepare to run!"

## Error Handling

### Validation Failures
- **Caller in combat**: "You cannot wrest items while in combat. Use 'disarm' instead."
- **No free hands**: "You need at least one free hand to grab something."
- **Target not found**: "You cannot find '<target>' here."
- **Object not in hands**: "'<target>' is not holding '<object>' in their hands."
- _(2026-09-15, #3454: two rows deleted here — "Object not found" and "Same room required". Neither could fire: the target lookup was rerouted through the identity pipeline in 2026-05 (room-scoped, perception-filtered), so a cross-room target can never resolve, and the object search covers only the target's hands, so "not in their hands" is already "Target not found"/"nothing in hand". Their constants were deleted rather than widening the searches, which would also have leaked stealth presence.)_

### Edge Cases
- **Multiple objects same name**: Grabs first match, user must try again for others
- **No window to react**: wrest resolves instantly in one call, so the target cannot drop the item or leave mid-attempt
- **Caller becomes encumbered**: Standard inventory management applies

## Integration Points

### Existing Systems Used
- **Mr. Hand system**: For wielding validation and hand management
- **Combat handler checking**: To verify caller not in combat state
- **Target lookup**: `resolve_character_target` (`commands/_identity_targeting.py`), the identity pipeline searching the caller's room and skipping anyone the caller is unaware of; only characters with hands qualify
- **Object searching**: Standard object name matching

### No Integration Required
- **Proximity system**: Not used (non-combat command)
- **Aim system**: Not applicable
- **Turn-based mechanics**: Instant execution
- **Damage system**: No combat implications

> **One integration: channels.** Wrest breaks the victim's channel when the wrested item is one of that channel's tools (`CHANNELED_ACTIONS_SPEC.md` §2.3, "The tool leaving your hands"). `CmdWrest` does not call `interrupt_channel` itself. Moving the item off the victim fires `Character.at_object_leave`, which calls `tool_left_hands` (`world/channeled.py`), and that breaks any running channel that declared the item as a tool (#3376). Graffiti declares the spray can as its tool, so snatching a tagger's can stops the tag where it was (#3377, #3385).
>
> The four rows above verify as written: nothing in `CmdWrest` touches proximity, aiming, turn order or damage.

## Implementation Architecture

### Command Flow Overview
```
1. Parse "wrest <object> from <target>" syntax
2. Validate caller not in combat
3. Validate caller has free hand
4. Find and validate target in room
5. Find object in target's hands (integrated cyberware is refused here)
6. Check target grapple status
7. Execute Grit vs Grit contest (with disadvantage if target grappled, unless target unconscious/dead)
8. If successful: Update both hand dictionaries
9. Announce result to room
```

> **Stale 2026-09-12 — third instance of the same no-op.** Step 8 is the flow-chart form of the line corrected under `#### Mr. Hand System Requirements`: nothing updates a hand dictionary, and there is no dictionary to update. The victim's slot is released by `Character.at_object_leave` off `target_object.move_to(caller, quiet=True)` (#2468) and the caller's is written by `wield_item` into `held_items`; assigning into `target.hands` here was the discarded write filed as #2489 / #2536. Step 9 is accurate but partial — caller and target each get a direct `msg()`, and only the third line goes to the room, rendered per-observer through `msg_room_identity` (`CmdWrest._announce_success`, `_announce_failure`).

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

### Command Location
- **File**: `commands/CmdInventory.py` — `CmdWrest` (key `"wrest"`), self-contained
- **Import location**: General inventory commands, not a standalone module; added to the character cmdset in `commands/default_cmdsets.py`, and listed in help under **Combat**
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
- **Balanced competition**: Both characters have chance to succeed: each rolls 1 to their Grit, and the wrester wins ties
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
`hands` is a property: `{container: held_item_or_None}` for each grasping container the species declares (for a human, `left_hand` and `right_hand`), plus any installed grasping augment, minus severed or dead ones, in the species' display order. What each hand holds is stored in the `held_items` AttributeProperty.

#### Extended Anatomy Examples
Illustrations of possible slot sets only: slots come from the species' grasping containers, and assigning to `hands` does not change them.
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
# Find object in any appendage: standard search over whatever the hands hold
held = [item for item in target.hands.values() if item]
matches = caller.search(object_name, candidates=held, quiet=True)

# Find free appendage for wrested item
for hand_name, held_item in caller.hands.items():
    if held_item is None:
        return hand_name
```

### System Benefits
1. **No hardcoded assumptions**: No references to specific hand names like "left" or "right"
2. **Automatic scaling**: Works with 1 hand, 2 hands, 8 tentacles, etc.
3. **Graceful degradation**: If a character loses a hand, simply remove it from dictionary
   - *Corrected 2026-09-12:* nobody removes anything — the derived view omits it. `hands` subtracts severed containers on every read and, since the #526 functional-anatomy gate, also any container whose organs are all dead, which is what finally closed "wield in a hand hanging off a severed arm" (`Character.hands`, `typeclasses/characters.py`). Benefits 2, 4 and 5 hold as written. Benefit 1 holds for **this command** — `CmdWrest` never names a hand, it iterates the view (`CmdWrest._find_free_hand`, `commands/CmdInventory.py`) — but not for the Mr. Hand system as a whole: `HAND_NAME_ALIASES` hardcodes `left`/`right` (`typeclasses/characters.py`), and both `Character.wield_item` and `Character.unwield_item` default to `hand="right"`, so a defaulted call on a species with no `right_hand` answers "You don't have a right hand."
4. **Name flexibility**: Hand names can be descriptive ("cybernetic_left", "tentacle_north", etc.)
5. **Future-proof**: New appendage types require no command modifications

### Implementation Implications
- **Wrest works unchanged**: Will automatically handle third hands, tails, tentacles
- **Disarm compatibility**: Combat disarm command should use same dictionary iteration
- **Display flexibility**: Hand listings adapt automatically to available appendages
- **Anatomy**: a character's hands come from their species' grasping containers (plus any installed grasping augment); a severed or dead hand drops out of the view by itself. Assigning to `hands` only writes `held_items` and does not add or remove a hand

## Future Considerations

### Potential Enhancements
- **Speed bonus**: Slight delay before target notices (2-3 seconds)
- **Alert system**: Target gets notification after brief delay
- **Skill integration**: Future skill system could add success chances
- **Weight limits**: Heavy objects might require both hands

### Integration Opportunities
- **Identity system**: Better target resolution when implemented
  - *Shipped 2026-09-12 — no longer an opportunity.* `CmdWrest._find_target_in_room` calls `resolve_character_target` (`commands/_identity_targeting.py`), the canonical identity-aware helper named by `IDENTITY_RECOGNITION_SPEC` §Command Authoring Rule, so `wrest knife from tall man` resolves on recognition rather than keys, and ambiguity gets a disambiguation prompt. The caller and target lines use each reader's own display names, and the room line is rendered per observer through `msg_room_identity`.
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
6. **Item protection**: Not initially (keep it simple). As built, integrated cyberware cannot be wrested (#516); everything else held can be.
7. **Combat initiation**: No (maintains non-combat nature)
