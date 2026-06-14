# G.R.I.M. Combat System Documentation

> **Status:** ✅ Shipped — high-level overview of the running combat system. NOTE: some features described below are aspirational and NOT implemented — skill progression, reputation, ammunition tracking, weapon durability, and formation fighting. Treat the combat code and COMBAT_REFACTOR (roadmap) as current truth where they disagree.

## Overview

The **G.R.I.M. Combat System** is a roleplay-focused, turn-based combat engine that emphasizes both violent and non-violent conflict resolution. It's built around four core character attributes and supports complex tactical scenarios while maintaining narrative focus.

## Core Attributes - The G.R.I.M. System

### **Grit** - Physical Foundation
- **Physical toughness** and endurance
- **Willpower** and mental fortitude  
- **Health points** and damage resistance
- **Recovery** from injuries and fatigue

*Used for: Absorbing damage, resisting effects, enduring hardship*

### **Resonance** - Social Awareness
- **Empathy** and emotional intelligence
- **Social awareness** and reading people
- **Communication** and persuasion
- **Conflict de-escalation** abilities

*Used for: Sensing intentions, social combat, peaceful resolution*

### **Intellect** - Mental Acuity
- **Problem-solving** and tactical thinking
- **Pattern recognition** and analysis
- **Memory** and knowledge retention
- **Strategic planning** abilities

*Used for: Combat tactics, understanding complex situations, learning*

### **Motorics** - Physical Coordination
- **Dexterity** and hand-eye coordination
- **Reflexes** and reaction time
- **Balance** and physical grace
- **Fine motor control** for precise actions

*Used for: Attack accuracy, dodging, weapon handling, escape attempts*

## Combat Mechanics

### Turn-Based System
- **Initiative Order**: Based on character stats and situational modifiers
- **Action Economy**: Each character gets one primary action per turn
- **Reaction System**: Defensive actions and responses to attacks
- **Round Structure**: Clear turn order with automatic progression

#### **Round Timing**
- **6-Second Rounds**: Each combat round represents 6 seconds of in-game time (configurable via `COMBAT_ROUND_INTERVAL`)
- **Staggered Attacks**: Individual attacks are staggered within each round to prevent message spam
  - First attacker: Executes immediately when round begins
  - Subsequent attackers: Delayed by 1.5 seconds each (configurable via `STAGGER_DELAY_INTERVAL`)
  - Maximum delay: 4.5 seconds (configurable via `MAX_STAGGER_DELAY`) to ensure all attacks complete before next round
- **Instant Actions**: Some actions (flee, jump) bypass the round system for emergency situations
- **Turn-Based Actions**: Most tactical actions (advance, retreat, charge, disarm) are queued for the next round

**Configuration**: All timing values can be adjusted in `world/combat/constants.py` without code changes.

### Proximity-Based Engagement

#### **Melee Range**
- **Close Combat**: Hand-to-hand, melee weapons, grappling
- **Proximity Required**: Must be in melee range to engage
- **Movement Costs**: Advancing/retreating affects action economy
- **Weapon Restrictions**: Some weapons require specific ranges

#### **Ranged Combat**
- **Shooting**: Firearms, bows, thrown weapons
- **Line of Sight**: Clear path required for ranged attacks
- **Cover System**: Objects and terrain affect accuracy
- **Ammunition**: Limited shots require tactical resource management

### Grappling System

#### **Restraint Mode** (Default)
- **Auto-Yielding**: Both parties start in non-violent mode
- **Gentle Hold**: Grappler maintains control without harm
- **Peaceful Resolution**: Preferred method for conflicts
- **De-escalation**: Allows for roleplay and negotiation

#### **Violent Mode** (Escalation)
- **Active Resistance**: Victim chooses to fight back
- **Escape Attempts**: Violent struggles to break free
- **Damage Potential**: Can cause harm during struggle
- **Last Resort**: When peaceful resolution fails

### Yielding Mechanics

#### **Yielding State**
- **Non-Violent**: Character chooses not to fight
- **Peaceful Stance**: Attempts to de-escalate conflict
- **Defensive Only**: No aggressive actions taken
- **Roleplay Focus**: Emphasis on character interaction

#### **Active Combat**
- **Aggressive Stance**: Character fights actively
- **Full Actions**: All combat options available
- **Tactical Depth**: Complex combat maneuvers possible
- **Consequence Awareness**: Higher stakes and risks

## Command Structure

### Core Actions (`commands/combat/core_actions.py`)
- **`attack <target>`**: Initiate or continue combat
- **`stop attacking`**: Cease aggressive actions, enter yielding state

### Movement Commands (`commands/combat/movement.py`)
- **`flee`**: Attempt to escape combat entirely (once per round, instant execution)
- **`retreat`**: Back away from melee range (same room)
- **`advance <target>`**: Close distance for melee combat
- **`charge <target>`**: Reckless rush attack with bonuses/penalties

### Special Actions (`commands/combat/special_actions.py`)
- **`grapple <target>`**: Attempt to grab and restrain target
- **`escape`**: Break free from grapple (switches to violent mode)
- **`release`**: Let go of grappled target
- **`disarm <target>`**: Attempt to remove target's weapon
- **`aim <target>`**: Improve accuracy for next attack

### Information Commands (main character cmdset)
There is no dedicated combat info-command module. Combat-aware `look` is provided
by the main character cmdset (so it works both in and out of combat) rather than a
separate `commands/combat/` file.
- **`look`**: Enhanced awareness during combat (registered on the main character cmdset)

## Combat Flow

### 1. **Initiation**
```
Player A: attack Player B
→ Combat handler created
→ Initiative order established
→ Both players enter combat state
```

### 2. **Turn Processing**
```
→ Check initiative order
→ Process active player's action
→ Apply results and consequences
→ Check for combat end conditions
→ Move to next player's turn
```

### 3. **Resolution**
```
→ All players yielding: Peaceful end
→ One player defeated: Combat victory
→ All players flee: Combat dispersed
→ Handler cleanup and state reset
```

## Tactical Features

### Multi-Room Combat
- **Room Transitions**: Combat can span multiple locations
- **Ranged Coverage**: Archers can control exits
- **Tactical Positioning**: Room layout affects combat options
- **Environmental Factors**: Terrain and obstacles matter

### Weapon System
- **Weapon Types**: Melee, ranged, thrown, improvised
- **Weapon Stats**: Damage, accuracy, range, special properties
- **Ammunition**: Limited resources for ranged weapons
- **Durability**: Weapons can break or become damaged

### Status Effects
- **Grappled**: Restricted movement and actions
- **Aimed**: Bonus accuracy on next attack
- **Yielding**: Non-violent stance with limited options
- **Wounded**: Injury effects on performance

## Roleplay Integration

### Narrative Focus
- **Rich Messaging**: Detailed, contextual combat descriptions
- **Emotional Context**: Messages reflect character motivations
- **Consequence Awareness**: Actions have meaningful narrative impact
- **Story Enhancement**: Combat serves the story, not vice versa

### Non-Violent Resolution
- **Default Yielding**: Peaceful resolution preferred
- **De-escalation**: Multiple opportunities to avoid violence
- **Restraint Options**: Subdue without permanent harm
- **Social Combat**: Resonance-based conflict resolution

### Character Development
- **Skill Progression**: Combat experience improves abilities
- **Reputation System**: Combat actions affect social standing
- **Psychological Impact**: Violence has emotional consequences
- **Relationship Dynamics**: Combat affects character relationships

## Technical Implementation

### State Management
- **NDB Attributes**: Temporary combat state (proximity, targeting, etc.)
- **DB Attributes**: Persistent character data (stats, equipment, etc.)
- **Handler Persistence**: Combat state survives server restarts
- **Cleanup Systems**: Automatic state cleanup when combat ends

### Performance Considerations
- **Efficient Algorithms**: Optimized for multiple simultaneous combats
- **Memory Management**: Proper cleanup of temporary data
- **Scalability**: Handles large numbers of participants
- **Error Handling**: Robust error recovery and logging

### Debug Infrastructure
- **Comprehensive Logging**: Detailed debug information
- **State Inspection**: Tools for examining combat state
- **Error Reporting**: Clear error messages for players and developers
- **Performance Monitoring**: Tracking system performance

## Configuration

### Combat Constants (`world/combat/constants.py`)
```python
# Default attribute values
DEFAULT_GRIT = 1
DEFAULT_RESONANCE = 1
DEFAULT_INTELLECT = 1
DEFAULT_MOTORICS = 1

# Combat mechanics
INITIATIVE_BASE = 10
DAMAGE_MULTIPLIER = 1.5
GRAPPLE_DIFFICULTY = 8
```

### Message Templates
- **Action Messages**: Descriptions of combat actions
- **Result Messages**: Outcomes of attacks and defenses
- **State Messages**: Changes in combat state
- **Weapon Messages**: Weapon-specific descriptions

## Advanced Features

### Planned Enhancements
- **Formation Fighting**: Group tactics and coordination
- **Environmental Effects**: Weather, terrain, lighting impact
- **Equipment Durability**: Weapon and armor degradation
- **Combat Styles**: Different fighting approaches and techniques

### Customization Options
- **House Rules**: Server-specific combat modifications
- **Weapon Varieties**: Easy addition of new weapon types
- **Special Abilities**: Character-specific combat techniques
- **Environmental Hazards**: Location-based combat modifiers

## Best Practices

### For Players
- **Roleplay First**: Use combat to enhance story
- **Consider Consequences**: Actions have meaningful impact
- **Communicate Intent**: Clear communication prevents misunderstandings
- **Respect Boundaries**: Honor other players' comfort levels

### For Developers
- **Maintain Modularity**: Keep combat systems cleanly separated
- **Document Changes**: Update documentation with modifications
- **Test Thoroughly**: Ensure changes don't break existing functionality
- **Preserve Philosophy**: Maintain roleplay-first approach

### For Administrators
- **Monitor Balance**: Ensure fair and engaging combat
- **Handle Disputes**: Mediate conflicts between players
- **Maintain Standards**: Enforce roleplay and conduct standards
- **Support Community**: Foster positive gaming environment

## Recent System Improvements (Sept 2024)

### Quality of Life Enhancements

#### Enhanced Message Personalization
Combat messaging now provides proper perspective-specific experiences:
- **First-Person Actions**: Attackers see "You draw your knife..." instead of observer messages
- **Second-Person Reactions**: Victims see "Nick prepares to strike you!" for direct engagement
- **Third-Person Observation**: Bystanders see appropriate third-person descriptions

#### Dual Initiate System
Combat initiation now shows both aggressive and defensive stances:
- **Attacker Initiate**: Shows weapon-specific aggressive preparation
- **Victim Defensive**: Automatic defensive stance when surprised or not currently engaged
- **Contextual Triggers**: Defensive messages only when target isn't already in combat or targeting

#### Automatic Color Coding
Visual clarity improved through contextual color application:
- **Threat Escalation**: Red initiate → Red hit → Bold red kill
- **Clear Misses**: White coloring for failed attempts
- **Automatic Application**: No manual color coding required in weapon templates
- **Override Support**: Pre-colored messages respected

#### Clean Narrative Flow
Removed meta-gaming elements for better immersion:
- **No Entry/Exit Spam**: Eliminated "You enter combat!" and "You are no longer in combat!" messages
- **Weapon-Focused**: Combat flows directly from weapon initiate to action
- **Natural Transitions**: Combat begins and ends with narrative actions, not system announcements

### Death System Integration

#### Medical Cause Integration
Death messages now reflect actual medical causes:
- **Informed Death**: "Nick is dying from blood loss..." based on medical analysis
- **Cause Detection**: Leverages existing medical system for accurate reporting
- **Fallback Graceful**: Beautiful atmospheric messages when analysis unavailable

#### Enhanced Death Curtain
Visual death experience improved significantly:
- **Proper Color Rendering**: Fixed color code parsing for perfect centering
- **Medical Suppression**: Prevented "lifeless body" message conflicts
- **Timing Coordination**: Clean message flow from cause → curtain → confirmation

#### Race Condition Prevention
Eliminated message ordering conflicts:
- **Attack Before Consequences**: Attack messages now appear before damage/death
- **Curtain Exclusivity**: Death curtain gets uninterrupted control during animation
- **Medical Coordination**: Bleeding messages suppressed during death processing

### Technical Improvements

#### Message Architecture
- **Perspective-Aware**: Three-message format (attacker/victim/observer) fully implemented
- **Context-Sensitive**: Messages adapt based on combat state and participant status
- **Weapon-Agnostic**: System works consistently across all weapon types

#### System Coordination
- **Combat-Medical Sync**: Proper handoff between combat damage and medical processing
- **Death-Medical Sync**: Clean separation of death curtain and medical ticker messaging
- **State Management**: Improved tracking of combat initiation and defensive states

---

*The G.R.I.M. combat system is designed to be a tool for storytelling, not a replacement for good roleplay. Its complexity serves the narrative, providing depth and consequence while maintaining focus on character development and compelling stories.*
