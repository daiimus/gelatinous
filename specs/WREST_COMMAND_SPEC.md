# Wrest Command Implementation Specification

`wrest` snatches an item out of another character's hands, outside combat. It is the non-combat counterpart to `disarm`: a quick, opportunistic grab that resolves at once without entering combat mechanics. In combat a character uses `disarm` (contested, turn-based, stat-based); out of combat, `wrest` (Grit vs Grit, immediate resolution).

The command is self-contained in `CmdWrest` (key `"wrest"`, `commands/CmdInventory.py`). It is a general inventory command, not a standalone module, because it works outside combat and differs from the combat commands. It is added to the character cmdset in `commands/default_cmdsets.py` and listed in help under **Combat**.

## Command Syntax

```
wrest <object> from <target>
```

## Validation

The command checks, in this order, and stops at the first failure with the message shown:

1. **The caller is not in combat.** Wrest is non-combat only. → "You cannot wrest items while in combat. Use 'disarm' instead."
2. **The caller has at least one free hand** (any hand in `caller.hands` holding `None`). → "You need at least one free hand to grab something."
3. **The target is found in the caller's room.** → "You cannot find '<target>' here."
4. **The object is in the target's hands** (held via the Mr. Hand system). → "'<target>' is not holding '<object>' in their hands." Integrated cyberware is refused at this step (#516): it cannot be wrested even from an unconscious target.

Then the command checks whether the target is grappled, runs the contest (below), transfers the item if the caller won, and announces the result.

- **The target CAN be in combat.** This allows grabbing from grappled or distracted targets.
- **No proximity requirement.** Wrest works anywhere in the same room; proximity is combat-only.
- **Target lookup** is `resolve_character_target` (`commands/_identity_targeting.py`), the identity pipeline. It searches the caller's room and skips anyone the caller is unaware of; only characters with hands qualify. So `wrest knife from tall man` resolves on recognition rather than keys, and ambiguity gets a disambiguation prompt (`CmdWrest._find_target_in_room`; the canonical helper named by `IDENTITY_RECOGNITION_SPEC` §Command Authoring Rule).
- **There is no separate "object not found" or "same room required" message** (#3454). Neither could fire: the target lookup is room-scoped and perception-filtered, so a target in another room never resolves and gets "Target not found"; the object search covers only the target's hands, so an object not in their hands gets "not holding". The searches are not widened, because widening them would leak stealth presence.

## The Contest

- **Grit vs Grit.** A simple opposed roll using the G.R.I.M. system: each side rolls 1 to their Grit, and the wrester wins ties. A single roll decides the outcome immediately.
- **Grapple disadvantage.** A grappled target rolls with disadvantage: two rolls of 1 to their Grit (at least 1), keeping the lower. A target is grappled when their entry in their combat handler's combatants list has a `grappled_by_dbref` (`CmdWrest._is_target_grappled`).
- **Instant success only against the unconscious or dead.** There is no contest for an incapacitated target. Consciousness is read from `world.consent.is_conscious`; a target whose state cannot be read is contested.

## Transfer

- **Caller's hand:** the first free hand in `caller.hands` (`CmdWrest._find_free_hand`). Hand selection is automatic.
- **Target's hand:** the first hand holding the named object.
- **Object matching:** the caller's standard object-name search, limited to the items in the target's hands. With several matches the first is taken.
- **The move:** the item is moved to the caller (`move_to`); `Character.at_object_leave` frees the victim's hand (#2468). Then `caller.wield_item(item, free_hand)` fills the caller's hand by writing `held_items`. If the caller is not then wielding the item, it goes back to the victim's original hand (#2489, #2536). Nothing writes into a `hands` dictionary; there is none to write into (see Hands below).

## Messages

### Success
- **To caller**: "You quickly snatch the knife from Bob's hand!"
- **To target**: "Alice quickly snatches the knife from your hand!"
- **To room**: "Alice quickly snatches a knife from Bob's hand!"

### Failure
- **To caller**: "You try to grab the knife from Bob's hand, but they hold on tight!"
- **To target**: "Alice tries to grab the knife from your hand, but you maintain your grip!"
- **To room**: "Alice tries to grab a knife from Bob's hand, but they resist!"

The caller and the target each get a direct message, using each reader's own display names. Only the third line goes to the room, rendered per observer through `msg_room_identity` (`CmdWrest._announce_success`, `_announce_failure`).

Wresting is never quiet: the room line names the wrester as the one acting, so a hidden wrester is revealed before it is sent, whether the attempt wins or fails (`msg_room_identity`, #3769). The item is named as the wrester sees it, except remains (a corpse or a severed head), which each reader sees under their own name for it (`named_for_each`, #3821).

The messages are the ten `MSG_WREST_*` constants (success and failure for caller, target and room; in combat; no free hands; target not found; object not in hands).

## Edge Cases

- **Multiple objects with the same name**: the first match is grabbed; the player must try again for the others.
- **No window to react**: wrest resolves instantly in one call, so the target cannot drop the item or leave mid-attempt.
- **Caller becomes encumbered**: standard inventory management applies.
- **No cooldown**: wrest can be retried at once (see Unbuilt).

## Hands (Mr. Hand System)

- `Character.hands` (`typeclasses/characters.py`) is a view rebuilt on every read: `{container: held_item_or_None}` for each grasping container the species declares (for a human, `{"left_hand": None, "right_hand": None}`), plus any installed grasping augment, minus severed or dead ones, in the species' display order. What each hand holds is stored in the `held_items` AttributeProperty.
- `Character` provides `wield_item()`, `unwield_item()` and `list_held_items()`.
- **Losing a hand**: nobody removes anything; the view omits it. `hands` subtracts severed containers on every read and, under the #526 functional-anatomy gate, any container whose organs are all dead, so nothing can be wielded in a hand hanging off a severed arm.
- **Assigning to `hands`** only writes `held_items`; it does not add or remove a hand.

### Dynamic anatomy

Because `CmdWrest` iterates the view and never names a hand (`CmdWrest._find_free_hand`), it works unchanged with any slot set the species' grasping containers give: one hand, two, a third arm, a prehensile tail, a prosthetic, eight tentacles, descriptive names such as "cybernetic_left" or "tentacle_north". New appendage types need no change to the command.

This holds for **this command**, not for the Mr. Hand system as a whole: `HAND_NAME_ALIASES` hardcodes `left`/`right` (`typeclasses/characters.py`), and both `Character.wield_item` and `Character.unwield_item` default to `hand="right"`, so a defaulted call on a species with no `right_hand` answers "You don't have a right hand."

- **Disarm compatibility**: the combat disarm command should use the same dictionary iteration.
- **Display flexibility**: hand listings adapt to the available appendages.

## Integration

### Channels

Wrest breaks the victim's channel when the wrested item is one of that channel's tools (`CHANNELED_ACTIONS_SPEC.md` §2.3, "The tool leaving your hands"). `CmdWrest` does not call `interrupt_channel` itself. Moving the item off the victim fires `Character.at_object_leave`, which calls `tool_left_hands` (`world/channeled.py`), and that breaks any running channel that declared the item as a tool (#3376). Graffiti declares the spray can as its tool, so snatching a tagger's can stops the tag where it was (#3377, #3385).

### Systems used
- **Mr. Hand system**: wielding validation and hand management.
- **Combat handler**: to verify the caller is not in combat.
- **Identity targeting**: `resolve_character_target`, above.
- **Object search**: standard object-name matching.

### Not used
- **Proximity system**: non-combat command.
- **Aim system**: not applicable.
- **Turn-based mechanics**: instant execution.
- **Damage system**: no combat implications.

## Use Cases

- **Opportunistic theft**: grab items while the target is grappled by someone else.
- **Quick snatch-and-run**: grab a phone or keys and flee before combat starts.
- **Non-violent disarming**: remove weapons without entering combat.
- **Distraction grabs**: take advantage when the target is distracted by combat.

### Tactical Scenarios

Opportunistic theft:
```
# Bob is grappled by Charlie
wrest phone from bob
flee north
```

Non-violent disarming:
```
# Remove weapon without starting combat
wrest sword from alice
# Alice now unarmed, can roleplay resolution
```

Coordinated tactics:
```
# Team coordination
Player A: grapple bob
Player B: wrest gun from bob
Player A: release bob
# Bob now disarmed and can choose to flee or fight unarmed
```

## Design Rationale

### Why a Grit vs Grit contest?
- **G.R.I.M. integration**: uses the established attribute system.
- **Balanced competition**: both characters have a chance to succeed.
- **Instant resolution**: a single roll decides the outcome immediately.
- **Physical nature**: Grit represents physical strength and determination.
- **Roleplay**: creates dramatic tension and meaningful stakes.

### Why allow combat targets?
- **Tactical depth**: creates opportunities during combat.
- **Coordination**: enables team tactics (one grapples, another grabs).
- **Realism**: someone grappled or distracted is vulnerable to item theft.
- **Balance**: gives non-combatants ways to influence combat indirectly.

### Why no proximity requirement?
- **Non-combat nature**: the proximity system is combat-specific.
- **Accessibility**: anyone in the room can attempt (within reason).
- **Simplicity**: reduces validation complexity.
- **Roleplay focus**: room-scale interaction feels natural.

## Unbuilt

- **Cooldown** — 📋 UNBUILT (no issue). An optional 6-second cooldown after a wrest (the 6-second combat round timing is available for it). Wrest has no cooldown and can be retried at once.
- **Message variations by context** — 📋 UNBUILT (no issue). The command sends one fixed success set and one fixed failure set; nothing varies by grapple, weapon or item type. Examples of the variations described:
  - **Combat target**: "You quickly grab the phone from Bob while he's grappled!"
  - **Weapon snatch**: "You swiftly wrest the sword from Alice's grip!"
  - **Utility grab**: "You snatch the keys from Bob's hand and prepare to run!"

## Future Considerations

### Potential enhancements
- **Speed bonus**: slight delay before the target notices (2-3 seconds).
- **Alert system**: the target gets a notification after a brief delay.
- **Skill integration**: a future skill system could add success chances.
- **Weight limits**: heavy objects might require both hands.

### Integration opportunities
- **Emote system**: custom wrest emotes for different scenarios.
- **Messaging system**: more detailed context-aware messages.
- **Animation system**: visual indicators for successful wrests.

## Not decided

### Implementation details
1. **Command placement**: should this be in general commands or the combat module?
2. **Timing**: should there be any delay, or truly instant?
3. **Notifications**: should the target be notified immediately or after a delay?
4. **Logging**: should wrests be logged for admin oversight?

### Balance considerations
1. **Abuse prevention**: any mechanisms to prevent excessive wresting?
2. **Roleplay enforcement**: should there be RP requirements?
3. **Item protection**: should some items be "unwrestable"?
4. **Combat initiation**: should wresting weapons from someone trigger combat?

### Recommended answers
Based on the design philosophy of simplicity and non-combat focus:

1. **Command placement**: General commands (works outside combat)
2. **Timing**: Instant execution (speed is the point)
3. **Notifications**: Immediate (clear communication)
4. **Logging**: Standard command logging only
5. **Abuse prevention**: Rely on roleplay and admin oversight
6. **Item protection**: Not initially (keep it simple). Integrated cyberware cannot be wrested (#516); everything else held can be.
7. **Combat initiation**: No (maintains non-combat nature)

## Related Documents

- `CHANNELED_ACTIONS_SPEC.md` §2.3, "The tool leaving your hands" — how losing a tool breaks a channel.
- `IDENTITY_RECOGNITION_SPEC` §Command Authoring Rule — the identity-aware target helper.
