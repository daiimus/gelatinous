# Jump Command Implementation Specification

**Status: IMPLEMENTATION COMPLETE** ✅  
**Location:** `commands/combat/jump.py` - CmdJump class  
**Integration:** Added to combat cmdset, ready for live testing

## Overview
The `jump` command serves two distinct heroic and tactical functions: **explosive sacrifice** to protect others from blast damage, and **tactical descent** from elevated positions via edge exits. It integrates with existing explosive mechanics and introduces new vertical combat positioning.

## Core Mechanics

### Command Syntax
```
jump on <explosive>           # Heroic sacrifice - absorb explosive damage
jump off <direction> edge     # Tactical descent from elevated position
jump across <direction> edge  # Horizontal leap across gaps at same level
```

### Function 1: Explosive Sacrifice

#### Purpose
**Ultimate heroic action** - absorb ALL explosive damage to completely protect others in proximity.

#### Validation Requirements
1. **Explosive must exist** in current room
2. **Explosive must be armed** (`db.pin_pulled = True`)
3. **Explosive must be counting down** (active timer)
4. **Caller can be in or out of combat** (heroic actions transcend combat state)
5. **No proximity requirement** (can jump on explosive from anywhere in room)

#### Timing Mechanics
- **Timer-based window**: Can only jump on explosive while countdown is active
- **Instant execution**: No delay once command is entered
- **Timer inheritance**: Takes over explosive's remaining countdown
- **Damage amplification**: Hero takes ALL explosive damage (100% absorption)
- **Complete protection**: Everyone else in proximity takes zero damage

#### Damage Calculation
```
Hero damage = explosive.db.blast_damage + positional_bonus
Others damage = 0 (complete protection)
```

#### Integration with Grenade System
- **Works with all explosive types**: Standard grenades, flashbangs, smoke grenades, etc.
- **Property-driven**: Uses existing `db.blast_damage`, `db.fuse_time` properties
- **Chain reaction prevention**: Hero absorbs damage, explosive doesn't trigger other explosives
- **Timer system**: Integrates with existing countdown mechanics from throw command
- **Proximity positioning**: Hero ends up in proximity to explosive (and inherits ALL its proximity relationships)

### Function 2: Tactical Descent

#### Purpose
**Vertical repositioning** from elevated sniper positions to ground level.

#### Edge Exit System
- **New exit property**: `db.is_edge = True` flag on exits
- **Elevated positioning**: Edge exits represent rooftops, ledges, balconies
- **One-way descent**: Jump down only (climbing back up requires different mechanics)
- **Safe landing**: No fall damage (tactical descent, not accidental fall)

### Function 3: Horizontal Leap

#### Purpose
**Same-level gap crossing** between buildings, rooftops, or across dangerous terrain.

#### Gap Jump System
- **Gap edge property**: `db.is_gap = True` flag on exits (can combine with `db.is_edge`)
- **Same-level movement**: Horizontal jump between rooms at equal elevation
- **Risk/reward**: Potential for failure and consequences
- **Tactical repositioning**: Quick movement across obstacles

#### Validation Requirements
1. **Edge exit must exist** in current room
2. **Edge must be valid**: `db.is_edge = True` on exit object
3. **Destination must exist**: Exit leads to valid room below
4. **Caller movement allowed**: Standard movement restrictions apply

#### Gap Jump Validation Requirements
1. **Gap exit must exist** in current room
2. **Gap must be valid**: `db.is_gap = True` on exit object  
3. **Destination must exist**: Exit leads to valid room at same level
4. **Jump success check**: General Motorics stat check vs gap difficulty
5. **Caller movement allowed**: Standard movement restrictions apply

#### Tactical Advantages of Edge Positions
- **Elevated combat**: Height advantage for ranged attacks
- **Protected position**: Not adjacent to ground level - prevents melee advancement
- **Sniper mechanics**: Enhanced aim and attack capabilities
- **Observation**: Can look down on ground level (enhanced reconnaissance)
- **Melee immunity**: Ground-level opponents cannot advance for melee attacks

## Technical Implementation

### Technical Infrastructure Notes
- **Timer System**: Evennia timer infrastructure available for countdown/cooldown mechanics
- **Combat Integration**: Existing 6-second combat round timing for standardization
- **Room Customization**: Enhanced `CmdLook` proves room description modification capability
- **Object Properties**: Property-based system (`db.is_edge`, `db.blast_damage`) validated working
- **Exit System**: Standard Evennia exit objects ready for property enhancement

### Explosive Sacrifice Implementation

#### Validation Flow
```
1. Parse "jump on <explosive>" syntax
2. Find explosive object in room
3. Validate explosive is armed and counting down
4. Calculate heroic damage (full blast + bonus)
5. Cancel explosive's normal detonation
6. Apply damage to hero only
7. Announce heroic sacrifice
8. Clean up explosive and timer state
```

#### Timer System Integration
```python
# Pseudo-code for explosive timing
def jump_on_explosive(caller, explosive):
    if not explosive.db.pin_pulled:
        return "The explosive is not armed!"
    
    current_timer = explosive.ndb.countdown_remaining
    if current_timer <= 0:
        return "Too late! The explosive has already detonated!"
    
    # Hero takes all damage
    hero_damage = explosive.db.blast_damage + 10  # heroic bonus damage
    explosive_damage_type = getattr(explosive.db, "damage_type", "laceration")
    apply_damage(caller, hero_damage, location="chest", injury_type=explosive_damage_type)
    
    # Cancel normal explosion
    cancel_explosive_timer(explosive)
    
    # Clean up proximity effects
    clear_explosive_proximity(explosive)
    
    # Heroic announcement
    announce_heroic_sacrifice(caller, explosive)
```

### Edge Exit Implementation

#### Edge Exit Implementation

#### Sky Room System (Pre-existing Architecture)

**Philosophy**: Sky rooms are permanent world features, not temporary objects. This prepares for future XYZ coordinate systems and flying vehicle mechanics.

**Room Lookup Strategy**:
1. **Tagged rooms**: Sky rooms tagged with `sky_{origin_id}_{destination_id}`
2. **Property-based**: Sky rooms with `db.origin_room` and `db.destination_room` properties
3. **Bidirectional**: Sky rooms that work for both directions of travel
4. **Fallback**: Direct movement if no sky room configured (graceful degradation)

**Fall Room Strategy**:
1. **Exit-specified**: `exit.db.fall_room` points to specific crash site
2. **Tagged rooms**: Fall rooms tagged with `fall_room_{destination_id}`
3. **Dedicated crash sites**: Rooms with `db.is_fall_room = True` near destination
4. **Fallback**: Use intended destination for soft landing

**Future XYZ Integration**:
- Sky rooms become normal traversable rooms at elevated coordinates
- Flying characters/vehicles use regular movement through sky rooms
- Jump mechanics become special case of general aerial movement
- No dynamic creation/deletion required

**Builder Workflow**:
```python
# Create sky room between rooftops
sky_room = create_object("typeclasses.rooms.Room", key="Sky above Downtown")
sky_room.tags.add("sky_room", category="room_type")
sky_room.db.origin_room = rooftop_a
sky_room.db.destination_room = rooftop_b
sky_room.db.desc = "You soar through the air between towering buildings..."

# Create fall room for failures
crash_site = create_object("typeclasses.rooms.Room", key="Alley Crash Site")
crash_site.tags.add(f"fall_room_{rooftop_b.id}")
crash_site.db.is_fall_room = True

# Configure gap exit
gap_exit.db.is_gap = True
gap_exit.db.gap_difficulty = 10
gap_exit.db.fall_room = crash_site
```

#### Exit Property System
```python
# Exit object properties for edge designation
exit.db.is_edge = True
exit.db.edge_type = "rooftop"     # Optional categorization
exit.db.edge_difficulty = 8       # Motorics check difficulty (1-20 scale)
exit.db.fall_damage = 8           # Damage for failed edge descent

# Gap jump properties (can combine with is_edge)
exit.db.is_gap = True
exit.db.gap_difficulty = 10       # Higher difficulty for gap jumps
exit.db.gap_distance = "wide"     # Descriptive distance category
exit.db.fall_distance = 2         # Rooms fallen for gap jump failures
exit.db.fall_room = room_obj       # Specific fall destination (optional)

# Sky room properties (pre-existing rooms)
sky_room.db.is_sky_room = True     # Marks transit-only sky rooms
sky_room.db.origin_room = room1    # Where gap jump originates
sky_room.db.destination_room = room2  # Where gap jump lands
sky_room.tags.add("sky_room", category="room_type")  # For lookup

# Fall room properties
fall_room.db.is_fall_room = True   # Marks crash landing sites
fall_room.tags.add(f"fall_room_{destination.id}")  # For destination-specific falls

# 3D Room Structure Example:
# Rooftop (origin) --east--> Sky Room (transit only) --east--> Adjacent Rooftop (destination)
#                                 |
#                               down
#                                 |
#                            Fall Room (failure destination)
# Each sky room has corresponding directional exits (east sky room has west back to origin)
#
# Future Compatibility: Sky rooms will naturally support flying vehicles/characters
# who can traverse these exits normally without jump mechanics
```

#### Jump Descent Flow
```
1. Parse "jump off <direction> edge" syntax
2. Find edge exit in specified direction
3. Validate edge properties
4. Move character to destination room
5. Announce dramatic descent
6. Update character position
```

#### Gap Jump Flow
```
1. Parse "jump across <direction> edge" syntax
2. Find gap exit in specified direction
3. Validate gap properties and difficulty
4. Make jump success roll (Motorics stat vs gap difficulty)
5. On success or tie: Move to destination room (flee-like action, transit through sky)
6. **Check for rigged grenades on landing edge** (new security integration)
7. On failure or critical failure: Fall to failure_room with fall damage
8. Announce jump attempt and outcome
9. Consume combat turn (flee-like timing)
10. Calculate fall damage: rooms_fallen × damage_multiplier
```

#### Rigged Grenade Integration for Gap Jumps

**New Security Feature**: Gap jumps now integrate with the rigged grenade system to detect and trigger traps when landing on rigged edges.

**Detection Logic**:
1. **Return edge identification**: When landing from a gap jump, identifies the return edge leading back to origin
2. **Direction mapping**: Uses opposite direction mapping (jump north → look for south edge on landing)
3. **Edge matching**: Checks both exit key AND aliases for proper direction matching
4. **Rigged grenade check**: Calls existing `check_rigged_grenade` function on matched edge
5. **Rigger immunity**: Maintains rigger immunity system (can't trigger own traps)

**Technical Implementation**:
```python
# Find return edge by opposite direction
opposite_direction = self.get_opposite_direction(self.direction)

# Check destination contents for matching edge
for obj in destination.contents:
    # Match by key or aliases
    key_matches = obj.key.lower() == opposite_direction
    aliases_match = any(alias.lower() == opposite_direction 
                       for alias in obj.aliases.all())
    
    if ((key_matches or aliases_match) and 
        hasattr(obj.db, 'is_edge') and obj.db.is_edge):
        # Found return edge - check for rigged grenades
        check_rigged_grenade(self.caller, obj)
```

**Integration Points**:
- **Uses existing rigged grenade system**: No new mechanics, leverages CmdThrow rigging
- **Respects rigger immunity**: Riggers cannot trigger their own traps
- **Full explosion sequence**: Pin pull, countdown, proximity, damage, cleanup
- **Edge cleanup**: Automatically cleans up rigged grenades after triggering
- **Debug logging**: Enhanced debug output for troubleshooting edge detection

#### Room Integration
- **Elevated rooms**: Rooms with edge exits have tactical advantage
- **Ground rooms**: Normal rooms accessible via edge descent
- **Sky rooms**: Transit-only spaces for edge/gap movement - **restricted from normal traversal**
- **Fall rooms**: Failure destinations with fall damage based on room count fallen
- **3D connectivity**: Sky rooms have bidirectional exits (east sky has west return)
- **Damage calculation**: Fall damage = rooms fallen × damage multiplier
- **Bidirectional awareness**: People below can potentially see elevated positions
- **Edge visibility**: Edge and gap properties visible in room descriptions (future look framework)
- **Framework building**: Current implementation focuses on mechanics, visibility enhancements later

#### Sky Room Traversal Restrictions

**Philosophy**: Sky rooms are transit-only spaces that cannot be accessed through normal movement commands. This prevents bypassing the gap jump mechanics while maintaining their function as aerial transit zones.

**Restriction Implementation**:
- **Normal movement blocked**: Characters cannot use standard movement commands (n, s, e, w, up, down) to enter or exit sky rooms
- **Jump system exempt**: Jump commands can move through sky rooms using `ndb.jump_movement_allowed` flag
- **Visibility filtering**: Pure sky rooms are hidden from room exit displays (not shown in "Exits:" listing)
- **Edge/gap exception**: Sky rooms that are also edges/gaps are visible but blocked by existing edge/gap restrictions
- **Clear error messages**: Informative feedback when players attempt forbidden movement
- **Gravity system support**: Fall mechanics work normally through sky rooms

**Technical Details**:
```python
# In Exit.at_traverse() - sky room restriction check
current_room_is_sky = getattr(traversing_object.location.db, "is_sky_room", False)
target_room_is_sky = getattr(target_location.db, "is_sky_room", False)
is_jump_movement = getattr(traversing_object.ndb, "jump_movement_allowed", False)

if (current_room_is_sky or target_room_is_sky) and not is_jump_movement:
    # Block traversal with appropriate error message
    return

# In Room.get_custom_exit_display() - visibility filtering
destination_is_sky = getattr(exit_obj.destination.db, "is_sky_room", False)
if destination_is_sky and not (is_edge or is_gap):
    continue  # Skip pure sky rooms from exit display
```

**Error Messages**:
- **Entering sky room**: "You cannot enter sky rooms through normal movement! Use jump commands to access aerial transit."
- **Leaving sky room**: "You cannot leave sky rooms through normal movement! You are falling - wait for gravity to take effect."
- **Between sky rooms**: "You cannot traverse between sky rooms! Sky rooms are transit-only spaces."

**Visibility Behavior**:
- **Pure sky rooms**: Completely invisible in room exit listings
- **Sky + edge rooms**: Visible in "Edges:" section, blocked by edge restrictions
- **Sky + gap rooms**: Visible in "Edges:" section, blocked by gap restrictions
- **Result**: Players cannot see or access pure transit sky rooms

**Jump System Integration**:
- Jump commands temporarily set `ndb.jump_movement_allowed = True` before sky room movement
- Flag is cleared immediately after successful movement
- Ensures only legitimate jump mechanics can use sky rooms
- Maintains security while allowing intended functionality

## Combat Integration

### Explosive Sacrifice Combat Effects
- **Instant resolution**: Not turn-based, immediate heroic action
- **Combat bypass**: Works regardless of combat state
- **Proximity clearing**: Removes explosive threat from all characters
- **Chain reaction prevention**: Stops multiple explosive chains

### Edge Position Combat Advantages
- **Aim bonus**: Enhanced accuracy from elevated position
- **Range advantage**: Extended effective range for attacks
- **Melee immunity**: Ground opponents cannot advance to edge positions (not adjacent)
- **Retreat limitation**: Limited escape routes from elevated position

### Turn-Based Considerations
- **Jump on explosive**: Immediate action, bypasses turn system (heroic emergency action)
- **Jump off edge**: Counts as movement action if in combat (flee-like timing)
- **Jump across gap**: Counts as movement action if in combat (flee-like timing)
- **Position bonuses**: Elevated positions provide combat modifiers

## Room Announcements

### Explosive Sacrifice Messages
- **Hero message**: "You leap onto the grenade, shielding everyone with your body!"
- **Room message**: "Alice heroically leaps onto the grenade, absorbing the blast!"
- **Outcome message**: "The explosion is muffled beneath Alice's sacrifice - everyone else is safe!"

### Edge Descent Messages
- **Caller message**: "You leap off the rooftop edge, dropping to the street below!"
- **Origin room**: "Alice leaps off the edge, disappearing toward the street below!"
- **Destination room**: "Alice drops down from above, landing dramatically!"

### Gap Jump Messages
- **Success caller**: "You sprint forward and leap across the gap, landing safely!"
- **Success origin**: "Alice takes a running leap across the gap and disappears!"
- **Success destination**: "Alice comes flying across the gap, landing with a roll!"
- **Failure caller**: "You leap toward the gap but fall short, tumbling down!"
- **Failure origin**: "Alice attempts the jump but falls short, disappearing below!"
- **Failure destination**: "Alice crashes down from above, having missed the jump!"

### Message Variations by Context
- **Different explosives**: "Alice dives onto the flashbang!" vs "Alice covers the pipe bomb!"
- **Edge types**: "Alice leaps from the fire escape!" vs "Alice jumps down from the balcony!"
- **Gap types**: "Alice vaults across the alley!" vs "Alice bounds between rooftops!"

## Error Handling

### Explosive Sacrifice Errors
- **Explosive not found**: "You cannot find '<explosive>' to jump on."
- **Explosive not armed**: "The <explosive> is not armed - there's no danger to absorb."
- **Timer expired**: "Too late! The <explosive> has already detonated."
- **No explosive timer**: "The <explosive> is not counting down."

### Edge Descent Errors
- **No edge exit**: "There is no edge to jump off here."
- **Invalid exit**: "That is not an edge you can jump from."
- **Blocked exit**: "The edge is blocked - you cannot jump off."
- **No destination**: "The edge leads nowhere - jumping would be suicide."

### Gap Jump Errors
- **No gap exit**: "There is no gap to jump across here."
- **Invalid gap**: "That is not a gap you can jump across."
- **Blocked gap**: "The gap is blocked - you cannot make the jump."
- **No destination**: "The gap leads nowhere safe to land."
- **Movement restricted**: "You cannot attempt that jump right now."

### Safety Validations
- **Explosive state checking**: Ensure explosive object is in valid state
- **Timer state validation**: Confirm countdown is active and accessible
- **Exit state verification**: Validate edge exit is traversable
- **Character state checks**: Ensure character can perform action

## Architecture Integration Points

### Existing Systems Used
- **Explosive system**: Uses grenade properties and timer mechanics from throw command
- **Room system**: Standard room connectivity and movement
- **Combat handler**: For position-based combat modifiers
- **Damage system**: For heroic damage application

### New Systems Required
- **Edge exit flagging**: Property system for marking edge exits
- **Gap jump system**: Horizontal leap mechanics with success/failure
- **Vertical combat**: Height-based combat advantages
- **Heroic sacrifice**: Damage absorption mechanics
- **Timer cancellation**: Ability to interrupt explosive countdowns
- **Jump skill system**: Stat-based success probability for gap jumps
- **Fall damage calculation**: Distance-based damage (rooms fallen × multiplier)
- **3D room navigation**: Transit-only sky rooms with bidirectional connectivity

### Integration with Throw Command
- **Shared explosive properties**: Uses same `db.blast_damage`, `db.fuse_time` system
- **Timer compatibility**: Works with existing countdown mechanics
- **Proximity system**: Interacts with grenade proximity from throw command
- **Chain reaction handling**: Prevents chain explosions through sacrifice
- **Rigged grenade detection**: Gap jumps check for and trigger rigged grenades on landing edges
- **Direction mapping system**: Uses opposite direction calculation for return edge detection
- **Alias matching**: Enhanced edge detection that checks both exit keys and aliases

## Implementation Priority

### Phase 1: Explosive Sacrifice
- Command parsing for "jump on" syntax
- Explosive object validation and timer checking
- Heroic damage calculation and application
- Timer cancellation and cleanup mechanics

### Phase 2: Edge Exit System
- Exit property system for edge designation
- Command parsing for "jump off" syntax
- Vertical movement mechanics
- Room transition and announcements

### Phase 2b: Gap Jump System  
- Gap exit property system
- Command parsing for "jump across" syntax
- Success/failure mechanics based on stats
- Horizontal movement with risk elements

### Phase 3: Combat Integration
- Elevated position combat bonuses
- Enhanced aim system for edge positions
- Turn-based integration for edge jumping
- Advanced tactical positioning mechanics

## Tactical Scenarios

### Heroic Sacrifice
```
# Live grenade in room, multiple people in proximity
jump on grenade
# Hero takes all blast damage, everyone else unharmed
# Ultimate team protection at personal cost
```

### Sniper Positioning
```
# On rooftop with edge exit
look down        # Observe street below
aim street       # Target ground level
attack bob       # Snipe from elevated position
jump off edge    # Tactical descent when position compromised
```

### Gap Crossing
```
# Rooftop-to-rooftop movement
look across north    # Check destination rooftop
jump across north    # Attempt horizontal leap
# On success: tactical repositioning
# On failure: fall to street level or take damage
```

### Gap Crossing with Rigged Traps
```
# Advanced tactical scenario - rigged edge traps
Player A: rig grenade to s     # Rig the south edge
Player B: jump across n edge   # Jump from opposite direction (north to south)
# Player B lands on south edge and triggers Player A's rigged grenade
# Rigged grenades provide area denial for gap jump landing zones
```

### Coordinated Tactics
```
# Team sniper support
Player A: aim street, attack target (from rooftop)
Player B: advance target (ground level)
Player A: jump off edge (when needed for repositioning)
```

## Design Rationale

### Why Timer-Based Explosive Sacrifice?
- **Tension creation**: Creates dramatic timing pressure
- **Skill requirement**: Must recognize and react to explosive threats
- **Integration consistency**: Uses existing grenade timer system
- **Heroic opportunity**: Limited window makes action more meaningful

### Why One-Way Edge Descent?
- **Tactical asymmetry**: Creates interesting positional advantages
- **Simple mechanics**: Avoids complex climbing systems
- **Dramatic effect**: Jumping down is more dramatic than climbing up
- **Balance consideration**: Prevents easy position abuse

### Why Gap Jumps Have Failure Risk?
- **Skill expression**: Allows character abilities to matter
- **Tactical decision**: Risk/reward for rapid repositioning
- **Dramatic tension**: Success is not guaranteed
- **Balance mechanism**: Prevents gap jumping from being too powerful

### Why Complete Damage Absorption?
- **Ultimate heroism**: Makes sacrifice truly meaningful
- **Clear mechanics**: Binary outcome (hero hurt, others safe)
- **Tactical value**: Completely removes explosive threat
- **Roleplay emphasis**: Encourages heroic character moments

## Implementation Notes & Technical Details

### Direction Mapping System
Gap jump rigged grenade detection uses opposite direction mapping to find return edges:

```python
direction_map = {
    'north': 'south', 'n': 's',
    'south': 'north', 's': 'n', 
    'east': 'west', 'e': 'w',
    'west': 'east', 'w': 'e',
    'northeast': 'southwest', 'ne': 'sw',
    'northwest': 'southeast', 'nw': 'se',
    'southeast': 'northwest', 'se': 'nw',
    'southwest': 'northeast', 'sw': 'ne',
    'up': 'down', 'u': 'd',
    'down': 'up', 'd': 'u'
}
```

### Edge Detection Enhancement
Critical fix implemented for proper edge matching - exits may have different keys and aliases:

```python
# Enhanced matching logic checks both key and aliases
key_matches = obj.key.lower() == opposite_direction
aliases_match = any(alias.lower() == opposite_direction 
                   for alias in obj.aliases.all())

if key_matches or aliases_match:
    # Found matching edge - proceed with rigged grenade check
```

**Why this matters**: Exit with key "south" and alias "s" will match when looking for direction "s", enabling proper rigged grenade detection on landing.

### Origin Room Tracking
Gap jumps now track origin room for proper return edge detection:

```python
def finalize_successful_gap_jump(self, destination, origin_room):
    # Enhanced to accept origin_room parameter for rigged grenade checking
    if origin_room:
        opposite_direction = self.get_opposite_direction(self.direction)
        # Look for edge that leads back to origin_room
```

### Debug Enhancement
Comprehensive debug logging added for troubleshooting edge detection:
- Function entry/exit logging
- Rigged grenade presence detection  
- Rigger immunity checking
- Direction matching results
- Edge detection success/failure

## Future Considerations

### Potential Enhancements
- **Climbing system**: Ways to get back to elevated positions
- **Fall damage**: Variable damage based on edge height
- **Multiple edge types**: Different tactical advantages per edge
- **Explosive shielding**: Partial protection mechanics

### Integration Opportunities
- **Skill system**: Future skills could modify jump effectiveness
- **Equipment system**: Special gear for edge traversal
- **Advanced explosives**: More complex explosive types and interactions
- **Environmental effects**: Weather/conditions affecting jumps
- **Flying mechanics**: Sky rooms naturally support flying vehicles/characters
- **Aerial combat**: Future aerial positioning and combat in sky rooms

## Open Implementation Questions

### Explosive Sacrifice Details
1. **Damage bonus**: How much extra damage should hero take for jumping on explosive?
2. **Death mechanics**: Should heroic sacrifice have special death/injury rules?
3. **Multiple explosives**: Can you jump on multiple explosives simultaneously?
4. **Combat state**: Should explosive sacrifice consume combat turn if in combat?

### Edge Exit Mechanics
1. **Height categories**: Should different edge heights have different effects?
2. **Landing positioning**: Do you land in specific proximity to anyone below?
3. **Equipment effects**: Should gear affect jumping ability or safety?
4. **Observation range**: How far can you see/aim from elevated positions?

### Gap Jump Mechanics
1. **Success calculation**: What stats determine jump success? (Motorics? Athletics?)
2. **Failure consequences**: Damage? Different destination? Equipment loss?
3. **Gap difficulty scaling**: How to categorize gap difficulty (1-5 scale)?
4. **Combat integration**: Can you gap jump while in combat? Turn cost?
5. **Motorics check**: Success on success or tie, failure means falling to fall room

### System Integration
1. **Aim system**: Should elevated positions enhance existing aim mechanics?
2. **Retreat mechanics**: Can you retreat "up" to edges, or only down from them?
3. **Grappling**: Can you grapple someone off an edge?
4. **Throwing**: Do elevated positions affect throw range/accuracy?

## Recommended Design Decisions

Based on the philosophy of heroic action and tactical depth:

1. **Damage bonus**: +10 damage for heroic sacrifice (meaningful cost)
2. **Death mechanics**: Standard death rules (heroism doesn't change lethality)  
3. **Multiple explosives**: One at a time (keeps action focused)
4. **Combat turn**: Bypasses turn system (emergency heroic action)
5. **Height effects**: Binary advantage (simple elevated vs ground)
6. **Landing position**: Random proximity if room occupied
7. **Observation**: Enhanced look/aim range from elevated positions
8. **Retreat direction**: Can retreat to edges, one-way descent only
9. **Gap success**: General Motorics stat check vs gap difficulty (success on success or tie)
10. **Gap failure**: Fall to failure_room with distance-based fall damage (rooms fallen × multiplier)
11. **Gap combat**: Counts as movement action if in combat (flee-like timing)
12. **Gap difficulty**: 1-5 scale (trivial to nearly impossible)
13. **Jump syntax**: Uses direction-based syntax (`jump off north edge`, `jump across east edge`)
14. **Proximity inheritance**: Hero inherits ALL proximity relationships from explosive
15. **Framework focus**: Mechanics first, visibility/discovery enhancements in future look system
