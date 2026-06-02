# G.R.I.M. Grappling System Specification

## Overview

The G.R.I.M. Grappling System is a comprehensive close-combat mechanism that emphasizes **restraint over violence** while providing tactical depth for complex combat scenarios. It integrates seamlessly with the proximity system, movement mechanics, and yielding philosophy to create dynamic, roleplay-focused grappling encounters.

## Design Philosophy

### 1. **Restraint-First Approach**
- **Default Intent**: Grappling begins as restraint, not violence
- **Escalation Control**: Violence requires explicit choice by participants
- **De-escalation Opportunities**: Multiple chances to avoid harm
- **Roleplay Priority**: Combat serves narrative, not mechanics

### 2. **Tactical Complexity**
- **Movement Integration**: Grappling affects and is affected by positioning
- **Multi-Character Dynamics**: Complex interactions between multiple grapplers
- **State Management**: Rich state system supporting various scenarios
- **Strategic Depth**: Advanced options for experienced players

### 3. **Mechanical Consistency**
- **Attribute-Based**: Uses core G.R.I.M. attributes (primarily Motorics)
- **Contest System**: Opposed rolls determine outcomes
- **State Validation**: Robust error checking and cleanup
- **Integration**: Seamless connection to combat, movement, and social systems

---

## Core Mechanics

### Grapple States

#### **Grappling Relationship States**
1. **Not Grappling**: Character has no grapple involvement
2. **Grappling Someone**: Character is holding/restraining another
3. **Being Grappled**: Character is held/restrained by another
4. **Mutual Grapple**: Two characters grappling each other (rare, contest-based)

#### **Grapple Intent States**
1. **Restraint Mode** (Default): Non-violent holding/control
2. **Violent Mode**: Active struggle with damage potential

#### **Participation States**
1. **Yielding**: Accepting restraint, no resistance
2. **Non-Yielding**: Active resistance, automatic escape attempts

### Primary Attributes
- **Motorics**: Primary attribute for grapple initiation, contests, and escape attempts
- **Grit**: Used for drag resistance during room traversal (physical endurance/willpower)
- **Resonance**: Tertiary for reading intent and de-escalation (future implementation)

---

## Grapple Initiation

### Command: `grapple <target>`

#### **Prerequisites**
- Must be in same room as target
- Target must be valid character
- Cannot grapple self
- Cannot grapple if already grappling someone
- Cannot grapple if being grappled by someone else

#### **Proximity Requirements**
- **Combat Initiation**: Grapple can initiate combat and establish proximity
- **Existing Combat**: Must be in melee proximity with target
- **Rush Mechanics**: Can "rush in" when initiating new combat

#### **Contest Resolution**
```
Grappler Roll: 1d[Motorics]
Defender Roll: 1d[Motorics]

Success: Grappler > Defender
Failure: Defender >= Grappler
```

*Note: All grapple initiation, takeover, and escape attempts use Motorics vs Motorics*

#### **Success Outcomes**
1. **Grapple Established**: Two-way relationship created
   - Grappler: `grappling_dbref` → Target
   - Target: `grappled_by_dbref` → Grappler
2. **State Changes**:
   - Grappler: Auto-yields (restraint intent)
   - Target: Remains non-yielding (auto-resistance)
3. **Proximity**: Both characters enter/maintain proximity
4. **Targeting**: Target auto-targets grappler for potential retaliation

#### **Failure Outcomes**
1. **No Relationship**: No grapple state changes
2. **Yielding Consequences**: 
   - If grappler initiated combat: Auto-yield
   - If defender joined combat this round AND has no existing combat target: Also auto-yield
   - If defender was already engaged in combat: Continue existing fight
3. **Messaging**: Failure messages with narrative context

---

## Grapple Contests (Takeover)

### Multi-Grapple Scenarios

#### **Scenario 1: Contest for Existing Victim**
- **Setup**: A grapples B, then C attempts to grapple B
- **Mechanism**: Contest between A and C for control of B
- **Resolution**: Winner gets B, loser gets nothing
- **Outcome**: B remains grappled by winner

#### **Scenario 2: Grappling an Active Grappler** ✅ **IMPLEMENTED**
- **Setup**: A grapples B, then C attempts to grapple A
- **Implementation**: System now detects "grapple_takeover" scenario
- **Behavior**: Force A to release B, then C can grapple A
- **Sequence**: 
  1. C initiates grapple on A (detected as grapple_takeover)
  2. Contest: C's Motorics vs A's Motorics
  3. If successful: A releases B automatically, C grapples A
  4. If failed: A maintains grapple on B, C becomes yielding (if initiated combat)

### Contest Mechanics
```
Challenger Roll: 1d[Motorics]
Current Grappler Roll: 1d[Motorics]

Success: Challenger > Current Grappler → Takeover
Failure: Current Grappler >= Challenger → Maintains control
```

---

## Grapple Maintenance

### Automatic Resistance System

#### **Non-Yielding Victims**
- **Auto-Escape**: Attempt escape every combat round
- **Contest**: Victim Motorics vs Grappler Motorics
- **Success**: Break free, switch to violent mode, target grappler
- **Failure**: Remain grappled, continue struggling

#### **Yielding Victims**
- **No Auto-Escape**: Accept restraint peacefully
- **Manual Escape**: Can use `escape` command to switch to violent mode
- **Roleplay Focus**: Emphasis on negotiation and de-escalation

### Grapple Damage System

#### **Restraint Mode** (Default)
- **No Damage**: Pure control/positioning
- **Messaging**: Restraint-focused descriptions
- **Intent**: Subdue without harm

#### **Violent Mode** (Escalation)
- **Damage Potential**: Both parties can take/deal damage
- **Escalation Triggers**:
  - Victim uses `escape` command
  - Automatic escape success
  - External violence (attacks on grappling pair)
- **Damage Types**:
  - Grapple damage hits: Control damage during struggle
  - Grapple damage misses: Failed attempts to harm

### Human Shield System

#### **Bodyshield Mechanics** ✅ **IMPLEMENTED**
When a character attacks someone who is grappling a victim, the victim may intercept the attack as an involuntary human shield.

#### **Shield Chance Calculation**
```
Base Shield Chance: 40%
+ Grappler Motorics modifier: +5% per point above 1
+ Victim Resistance modifier: 
  - Yielding victim: +10% (easier to position)
  - Non-yielding victim: -10% (struggling against positioning)
- Ranged Attack modifier: -20% (harder to shield against projectiles)
```

#### **Shield Resolution Process**
1. **Attack Targeting**: Someone attacks a grappler
2. **Shield Check**: Roll d100 vs calculated shield chance
3. **Shield Success**: 
   - **Shield Messages**: Inform all parties about interception
   - **Target Redirect**: Change attack target to grappled victim
   - **Normal Combat Flow**: Proceed with standard attack resolution on victim
4. **Shield Failure**: Attack proceeds normally against intended grappler target

#### **Shield Messaging System**
- **Attacker Message**: `"Your attack is intercepted by {victim} as {grappler} uses them as a shield!"`
- **Grappler Message**: `"You position {victim} to absorb {attacker}'s attack!"`
- **Victim Message**: `"You are forced into the path of {attacker}'s attack by {grappler}!"`
- **Observer Message**: `"{grappler} uses {victim} as a human shield against {attacker}'s attack!"`

#### **Integration with Combat System** ✅ **IMPLEMENTED**
- **Pre-Attack Check**: Shield check occurs before normal attack resolution
- **Target Substitution**: Victim becomes new target for existing combat flow
- **Damage Application**: Uses normal `take_damage()` on victim
- **Combat Messages**: Uses existing weapon-based combat message system
- **Natural Escalation**: Existing "external violence" triggers handle mode changes automatically

#### **Strategic Implications**
- **Defensive Grappling**: Makes grappling a protective strategy
- **Victim Motivation**: Strong incentive for victims to escape or negotiate
- **Multi-Character Tactics**: Affects targeting decisions in group combat
- **Roleplay Opportunities**: Creates dramatic tension and moral dilemmas

#### **Grenade Bodyshield System** ⚠️ **MISSING IMPLEMENTATION**
When grenades explode in proximity to grappling pairs, the grappled victim can absorb damage intended for their grappler.

#### **Current Grenade Shielding**
- **Holder Shielding**: When grenade explodes in someone's hands, others in proximity take 50% damage due to "body shielding"
- **Proximity-Based**: All characters in proximity list take equal damage (except holder reduction)
- **No Grappling Integration**: Grenade explosions do not check for grappling-based human shields

#### **Proposed Grenade Human Shield Mechanics**
When a grenade explodes, before applying damage to characters in proximity:

1. **Grappling Check**: For each character in the explosion proximity list who is grappling someone
2. **Shield Calculation**: Use modified shield chance calculation:
   ```
   Base Shield Chance: 30% (reduced from attack-based 40%)
   + Grappler Motorics modifier: +5% per point above 1
   + Victim Resistance modifier: 
     - Yielding victim: +10% (easier to position as blast shield)
     - Non-yielding victim: -10% (struggling against positioning)
   - Area Effect modifier: -10% (harder to shield against explosions)
   ```
3. **Shield Success**: 
   - **Damage Redirect**: Grappler takes no explosion damage
   - **Victim Absorption**: Grappled victim takes grappler's full explosion damage + their own
   - **Shield Messages**: Explosive-specific messaging for dramatic effect
4. **Shield Failure**: Both grappler and victim take normal explosion damage

#### **Explosive Shield Messaging System**
- **Grappler Message**: `"You instinctively use {victim} to shield yourself from the {grenade} blast!"`
- **Victim Message**: `"You are forcibly positioned to absorb the {grenade} explosion meant for {grappler}!"`
- **Observer Message**: `"{grappler} uses {victim} as a blast shield against the {grenade} explosion!"`

#### **Implementation Gap**
The grenade explosion system (`CmdThrow.py`, with detonation logic now largely in `commands/CmdExplosives.py` and `commands/explosion_utils.py`) bypasses combat handler's `_process_attack()` method, using direct `apply_damage(character, damage, location, injury_type)` calls instead. Integration would require adding grappling shield checks within the explosion damage resolution before `apply_damage()` calls.

---

## Movement Integration

### Current Implementation ✅

#### **Exit Traversal (Drag System)**
- **Conditions for Dragging**:
  - Grappler is yielding (restraint mode)
  - Grappler not targeted by others (except victim)
  - Victim fails resistance roll (Victim Grit vs Grappler Grit)
- **Successful Drag**:
  - Both characters move to new room
  - Combat state transfers to new handler
  - Grapple relationship preserved
- **Failed Resistance**:
  - Grapple broken automatically
  - Movement blocked

#### **Combat Movement Restrictions**
- **Being Grappled**: Blocks flee, retreat, advance, charge
- **Grappling Someone**: Charge auto-releases grapple if targeting others

### Needed Implementations ⚠️

#### **Advance While Grappling** ✅ **IMPLEMENTED**
- **Current Implementation**: Full logic for grappler advancing while maintaining hold
- **Behavior**: 
  - Allow advance to new target while holding victim
  - Drag victim along during advance if conditions met
  - Victim inherits grappler's new proximity relationships
- **Restrictions**: Only if victim is yielding for room traversal

#### **Retreat While Grappling** ✅ **IMPLEMENTED**
- **Current Implementation**: Complete grapple-specific retreat logic
- **Behavior**:
  - Allow retreat while maintaining grapple
  - Drag victim back with grappler
  - Both maintain proximity after retreat
- **Consistency**: Both remain in proximity post-retreat

#### **Proximity Inheritance** ✅ **IMPLEMENTED**
- **Principle**: Victim inherits all of grappler's proximity relationships
- **Timing**: After successful movement (advance/retreat/charge)
- **Mechanism**: Copy grappler's proximity set to victim
- **Rationale**: Victim is "dragged along" and gains same positioning

---

## Special Actions

### Escape Grapple: `escape`

#### **Mechanics**
- **State Change**: Victim switches from yielding to non-yielding
- **Immediate Effect**: Violent mode engaged
- **Contest**: Handled on next combat round
- **Targeting**: Auto-target grappler for retaliation

#### **Outcomes**
- **Success**: Break free, remain in proximity, target grappler
- **Failure**: Remain grappled but now in violent mode

### Release Grapple: `release`

#### **Mechanics**
- **Voluntary Action**: Grappler chooses to let go
- **No Contest**: Automatic success
- **State Preservation**: Yielding states maintained
- **Proximity**: Both remain in proximity

#### **Strategic Use**
- **De-escalation**: Peaceful resolution option
- **Tactical**: Free up for other actions
- **Roleplay**: Character development opportunities

---

## State Management

### Database Fields

#### **Combat Entry Fields**
```python
{
    "char": Character object,
    "grappling_dbref": int or None,      # Who this character is grappling
    "grappled_by_dbref": int or None,    # Who is grappling this character
    "is_yielding": bool,                 # Yielding state
    "target_dbref": int or None,         # Combat target
    # ... other combat fields
}
```

#### **Validation Rules**
1. **Mutual Exclusivity**: Can't grapple multiple people
2. **Relationship Consistency**: Cross-references must match
3. **Combat Participation**: All grapple participants must be in combat
4. **Proximity Requirement**: Grappling requires proximity

### State Cleanup System

#### **Automatic Validation** (`validate_and_cleanup_grapple_state`)
- **Stale References**: Remove references to non-existent characters
- **Cross-Reference Validation**: Ensure bidirectional consistency
- **Combat State Sync**: Align with combat handler state
- **Self-Grapple Prevention**: Block impossible relationships

#### **Cleanup Triggers**
- Every combat round (proactive)
- Character removal from combat
- Handler shutdown
- Error conditions

---

## Integration Points

### Combat System Integration

#### **Handler Processing Order**
1. **Validation**: Check and clean grapple states
2. **Auto-Resistance**: Process non-yielding victim escapes
3. **Special Actions**: Handle grapple/escape/release commands
4. **Movement Actions**: Process advance/retreat/charge with grapple logic
5. **Standard Combat**: Regular attacks with grapple considerations

#### **Action Restrictions**
- **Being Grappled**: Limited to escape, talk, yielding actions
- **Grappling Someone**: Can advance/retreat (with victim), limited other actions
- **Attack Restrictions**: Can't attack your grappler while being grappled

### Proximity System Integration

#### **Establishment Rules**
- **Grapple Creation**: Always establishes proximity
- **Maintenance**: Grappling maintains proximity automatically
- **Release**: Proximity persists after grapple ends
- **Movement**: Proximity inherited during movement

#### **Movement Interactions**
- **Room Changes**: Drag system handles proximity transfer
- **Within Room**: Advance/retreat maintains grapple proximity
- **Multiple Targets**: Victim gains grappler's proximity to others

### Yielding System Integration

#### **State Relationships**
- **Default Grappler**: Auto-yields (restraint intent)
- **Default Victim**: Remains non-yielding (resistance mode)
- **Manual Override**: Both can change yielding state independently
- **Escalation**: Non-yielding victims auto-attempt escape

#### **Combat Mode Interactions**
- **Peaceful Mode**: Both yielding, no auto-resistance
- **Mixed Mode**: Yielding grappler, non-yielding victim
- **Violent Mode**: Neither yielding, active struggle

---

## Implementation Priorities

### High Priority ✅ **COMPLETED**

1. **Multi-Grapple Chain Logic**: ✅ **COMPLETED**
   - ✅ Fix scenario where C tries to grapple A (who is grappling B)
   - ✅ Implement forced release mechanism  
   - ✅ Test edge cases thoroughly

2. **Proximity Inheritance**: ✅ **COMPLETED**
   - ✅ Implement victim proximity copying during grappler movement
   - ✅ Ensure consistency across advance/retreat/charge
   - ✅ Handle multi-character scenarios

3. **Human Shield System**: ✅ **COMPLETED**
   - ✅ Add bodyshield mechanics to attack resolution
   - ✅ Implement shield chance calculation
   - ✅ Add shield-specific messaging system
   - ✅ Integrate with existing combat damage flow
   - ⚠️ **Missing**: Grenade explosion human shield integration

4. **Advance While Grappling**: ✅ **COMPLETED**
   - ✅ Add grapple check to advance command
   - ✅ Implement victim dragging during advance
   - ✅ Maintain grapple state through movement

### Medium Priority

5. **Retreat Grapple Logic**: ✅ **COMPLETED**
   - ✅ Add grapple awareness to retreat command
   - ✅ Implement victim dragging during retreat
   - ✅ Ensure proximity maintenance

6. **Enhanced Contest System**:
   - Add modifiers for different situations
   - Implement fatigue mechanics for extended grapples
   - Add environmental factors

7. **Grenade Human Shield Integration**:
   - Integrate grappling-based blast shields with grenade explosions
   - Implement damage absorption mechanics (victim takes grappler's damage + own)
   - Add explosive-specific shield chance calculation (reduced effectiveness)
   - Create dramatic explosive-specific messaging system
   - Balance tactical opportunity with moral consequences

### Low Priority

8. **Advanced Grapple Moves**:
   - Submission attempts
   - Position-based modifiers
   - Team grappling mechanics

9. **Grapple Specialization**:
   - Character-specific grappling styles
   - Equipment modifiers
   - Training-based improvements

---

## Edge Cases and Considerations

### Multi-Character Scenarios

#### **Chain Grapples**
- **A→B→C**: Multiple dependency chains
- **Circular References**: Prevention and detection
- **Cascade Releases**: When one grapple affects others

#### **Team Grappling**
- **Multiple Grapplers**: Two people trying to grapple same target
- **Assistance**: Helping teammate with grapple
- **Interference**: Attacking grappling pairs

### Room Transition Edge Cases

#### **Handler Boundaries**
- **Cross-Handler Grapples**: When characters end up in different handlers
- **Handler Merging**: When grapple brings handlers together
- **Handler Cleanup**: When handlers shut down during grapples

#### **Movement Restrictions**
- **Yielding Requirements**: Room traversal requiring victim consent
- **Failed Drags**: What happens when drag fails
- **Escape During Movement**: Mid-transition escapes

### Error Recovery

#### **State Corruption**
- **Orphaned References**: Cleanup strategies
- **Inconsistent States**: Recovery mechanisms
- **Data Loss**: Graceful degradation

#### **System Failures**
- **Handler Crashes**: Grapple preservation
- **Network Issues**: State synchronization
- **Resource Limits**: Performance under load

---

## Testing Scenarios

### Basic Functionality
1. **Simple Grapple**: A grapples B successfully
2. **Grapple Failure**: A fails to grapple B
3. **Escape Success**: B escapes from A
4. **Escape Failure**: B fails to escape from A
5. **Voluntary Release**: A releases B voluntarily

### Contest Scenarios
6. **Grapple Contest**: A grapples B, C contests for B
7. **Chain Grapple**: A grapples B, C grapples A
8. **Multiple Contesters**: A grapples B, both C and D contest

### Movement Integration
9. **Room Drag Success**: A drags B to new room
10. **Room Drag Failure**: B resists A's drag attempt
11. **Advance While Grappling**: A advances to C while holding B
12. **Retreat While Grappling**: A retreats while holding B

### Edge Cases
13. **Handler Transitions**: Grapple across room boundaries
14. **Combat Initiation**: Grapple starting new combat
15. **State Corruption**: Recovery from invalid states
16. **Multi-Grapple Chains**: Complex relationship webs

---

## Conclusion

The G.R.I.M. Grappling System provides a sophisticated, roleplay-focused framework for close combat scenarios that emphasizes restraint while maintaining tactical depth. The system's integration with movement, proximity, and yielding mechanics creates a cohesive combat experience that serves narrative goals while providing meaningful strategic choices.

The specification identifies key implementation gaps that need addressing to complete the system's vision, particularly around proximity inheritance and multi-grapple scenarios. Once these elements are implemented, the grappling system will provide a robust foundation for complex, engaging combat encounters that prioritize character development and story progression.

## Implementation Roadmap

### Phase 1: Core Fixes (High Priority) ✅ **COMPLETED**
- ✅ Fix multi-grapple chain logic
- ✅ Implement proximity inheritance
- ✅ Add advance-while-grappling support
- ✅ Implement human shield system
- ✅ Complete retreat-while-grappling logic

### Phase 2: Enhancement Features (Medium Priority)  
- Enhanced contest system with modifiers
- Environmental factors integration
- Performance optimization

### Phase 3: Advanced Features (Low Priority)
- Specialized grapple moves
- Character customization
- Team grappling mechanics

This roadmap shows the grappling system has achieved its core functionality goals, with Phase 1 completely implemented. The system now provides a robust foundation for complex, engaging combat encounters that prioritize character development and story progression.
