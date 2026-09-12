# G.R.I.M. Combat System Documentation

> **Status:** ✅ Shipped — high-level overview of the running combat system. NOTE: some features described below are aspirational and NOT implemented — skill progression, reputation, ammunition tracking, weapon durability, and formation fighting. Treat the combat code and COMBAT_REFACTOR (roadmap) as current truth where they disagree.
>
> **⚠ Spec-vs-code corrections — the following claims were FALSE when audited 2026-09-11, and are NOT covered by the aspirational list above.** Each is annotated in place below.
> - **No cover system.** §Ranged Combat's "Cover System" has no implementation; nothing about the room, an object or terrain reaches the hit math (`world/combat/attack.py:422-470`).
> - **No environmental modifier.** §Multi-Room Combat's "Environmental Factors" contradicts this spec's own "Planned Enhancements", which still lists weather/terrain/lighting as unbuilt.
> - **`aim` grants no accuracy bonus.** The to-hit roll is `randint(1,20) + motorics × sight × manipulation` (`world/combat/attack.py:437`, `:469`) and never reads the aim state. Aim locks the target, posts a visible tell, enables cross-room fire along an aimed exit, and buys an opportunity attack if the target flees.
> - **Grappling auto-yields only the grappler**, not both parties (`world/combat/grappling.py:353-356`, matching `GRAPPLE_SYSTEM_SPEC.md:91-92` and `:413-414`).
> - **Resonance is unused by combat.** It appears under `world/combat/` only as `STAT_RESONANCE` (`constants.py:24`) and a descriptor-table entry (`:830`), and nowhere at all under `commands/combat/`; its live consumers are perception and recognition (`world/stealth.py:162`, `world/identity.py:1758`, `world/voice.py:485`, `world/radio.py:744`). There is no social-combat resolver.
> - **Grit drives no health pool and no damage resistance.** There is no character-level hit-point stat; health is the organ model (`world/medical/core.py:15`) and mitigation is armor (`typeclasses/armor_mixin.py:320`).
> - **No per-weapon accuracy stat.** Weapons carry `db.damage` and `db.is_ranged` only; every weapon lands on the attacker's motorics alone.
> - **`INITIATIVE_BASE`, `DAMAGE_MULTIPLIER` and `GRAPPLE_DIFFICULTY` do not exist** anywhere in the repo.
> - **No performance instrumentation.** `world/combat/debug.py` is a diagnostics/audit sink with no timing, counter or throughput metric.
> - **"(Sept 2024)"** on the improvements section is an off-by-one-year error — that section was added 2025-09-14 (`bba77e22`).
>
> **Two things that look like drift and are not** (checked 2026-09-11, recorded so the next auditor does not "fix" them): `look` really is combat-aware from the main character cmdset — Evennia's own `CmdLook` arrives by inheritance at `commands/default_cmdsets.py:150`, the game's custom subclass having been deleted with `commands/combat/info_commands.py` in `d8261f7e`; and the kill/hit colour escalation really is as documented, because in Evennia lowercase `|r` is the HILITE (bold) red and uppercase `|R` the regular one (`world/combat/messages/__init__.py:175-183`; cf. commit `ef3b18e6` "Bold white -> regular white", which changed `|w` → `|W`).

## Overview

The **G.R.I.M. Combat System** is a roleplay-focused, turn-based combat engine that emphasizes both violent and non-violent conflict resolution. It's built around four core character attributes and supports complex tactical scenarios while maintaining narrative focus.

## Core Attributes - The G.R.I.M. System

### **Grit** - Physical Foundation
- **Physical toughness** and endurance
- **Willpower** and mental fortitude  
- **Health points** and damage resistance
- **Recovery** from injuries and fatigue

*Used for: Absorbing damage, resisting effects, enduring hardship*

> **⚠ Corrected 2026-09-11 — aspirational, not shipped.** There is no character-level hit-point stat, and nothing consults Grit for absorption, resistance or recovery. Health is the organ-based medical model (`world/medical/core.py:15` `class Organ`, per-organ HP) and damage mitigation is armor (`typeclasses/armor_mixin.py:320` `_calculate_armor_damage_reduction`, called from `take_damage` at `:69`). The fossil of the system this paragraph describes is still in the tree: `world/combat/constants.py:29-30` declares `DEFAULT_HP = 10` and `HP_GRIT_MULTIPLIER = 2` under a `# Health system` heading, and **neither name is read anywhere in the repo**. Grit's three real uses are the disarm contest (`world/combat/actions.py:133-134`, grit vs grit), the drag contest (`world/combat/movement_resolution.py:462-463`, `typeclasses/exits.py:306-307`) and vital-targeting skill (`world/medical/utils.py:160-165`). `world/manifest.py:67-81` does map melee/unarmed/athletics onto Grit, but those skills are a creation-time snapshot that nothing rolls (see the module docstring). The toughness/willpower framing above is character-concept flavour, not a mechanic.

### **Resonance** - Social Awareness
- **Empathy** and emotional intelligence
- **Social awareness** and reading people
- **Communication** and persuasion
- **Conflict de-escalation** abilities

*Used for: Sensing intentions, social combat, peaceful resolution*

> **⚠ Corrected 2026-09-11 — no combat use.** Resonance is read nowhere under `world/combat/` or `commands/combat/`; it exists there only as `STAT_RESONANCE` (`world/combat/constants.py:24`) and a descriptor-table entry (`:830`). Where it IS live is outside combat: stealth detection (`world/stealth.py:162`, `:240`, `:274`) and identity/voice/radio recognition (`world/identity.py:1758`, `world/voice.py:485`, `world/radio.py:744`) — i.e. the "sensing" half of this line ships, the "social combat" half does not.

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
  > **⚠ Corrected 2026-09-11 — NOT implemented.** No cover mechanic exists anywhere in `world/combat/`; the only "cover" hits are clothing coverage (`constants.py:133-184`) and two flee messages about covered exits (`constants.py:587`, `:594`). The to-hit roll (`world/combat/attack.py:422-470`) takes no term derived from the room or its contents.
- **Ammunition**: Limited shots require tactical resource management

### Grappling System

#### **Restraint Mode** (Default)
- **Auto-Yielding**: Both parties start in non-violent mode
  > **⚠ Corrected 2026-09-11 — only the grappler auto-yields.** `world/combat/grappling.py:353-356` sets `char_entry[DB_IS_YIELDING] = True` for the grappler and deliberately leaves the victim non-yielding (the line that would yield them is commented out) so the victim auto-resists every turn. `GRAPPLE_SYSTEM_SPEC.md:91-92` and `:413-414` document the shipped behaviour correctly; this line is the outlier. A knock-on: `escape`'s "you switch to violent struggle" message only fires if the victim *was* yielding (`commands/combat/special_actions.py:248-252`), so in a default grapple it never appears. Both parties yielding is reachable, but only if the victim chooses it.
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
  > **⚠ Corrected 2026-09-11 — no accuracy bonus is applied.** `world/combat/attack.py:437` computes `effective_skill = attacker_skill * sight_factor * manip_factor` and `:469` rolls `randint(1, 20) + effective_skill`; `NDB_AIMING_AT` is never read in that file. What aiming actually buys: the target is held in place, a visible tell is posted, `aim <direction>` unlocks cross-room fire through that exit (`commands/combat/core_actions.py:97-115`), and the aimer gets an opportunity attack if the aimed-at target flees (`commands/combat/movement.py:229`). Whether the bonus should be built or the promise withdrawn is an open owner question — `CmdAim`'s own help text (`commands/combat/special_actions.py:361`) makes the same claim.

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
  > **⚠ Corrected 2026-09-11 — NOT implemented, and contradicted by this spec's own roadmap.** No weather, terrain or lighting term reaches any combat roll (a repo grep for those words under `world/combat/` hits only weapon prose). "Planned Enhancements" below still lists "Environmental Effects: Weather, terrain, lighting impact" as future work — that entry is the accurate one. Room layout does matter, but only through exits and multi-room handler management (`DB_MANAGED_ROOMS`), not through any terrain property.

### Weapon System
- **Weapon Types**: Melee, ranged, thrown, improvised
- **Weapon Stats**: Damage, accuracy, range, special properties
  > **⚠ Corrected 2026-09-11 — damage and range ship; accuracy does not.** Weapons carry `db.damage` (read via `get_weapon_damage`, `world/combat/utils.py:209-229`) and `db.is_ranged` (`:232-233`). There is no per-weapon accuracy attribute anywhere in the repo; every weapon lands on the attacker's motorics alone (`world/combat/attack.py:422-470`), so a pistol and a brick are equally easy to hit with. Thrown objects are blunter still — `world/combat/throwing.py:433` flat-rates a 70% hit chance under the comment "could be enhanced with accuracy system".
- **Ammunition**: Limited resources for ranged weapons
- **Durability**: Weapons can break or become damaged

### Status Effects
- **Grappled**: Restricted movement and actions
- **Aimed**: Bonus accuracy on next attack
  > **⚠ Corrected 2026-09-11.** The aimed state is real (`NDB_AIMING_AT` / `NDB_AIMED_AT_BY`, set at `commands/combat/special_actions.py:632-633`) but confers no accuracy bonus — see the `aim <target>` note under Command Structure. Its mechanical effects are immobilising the target, the visible tell, cross-room fire, and an opportunity attack on a flee attempt.
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
  > **⚠ Corrected 2026-09-11 — NOT implemented.** No social-combat resolver exists, and Resonance is never read by any combat code path. The non-violent resolution that DOES ship is the yielding system: when every combatant is yielding and no grapple is active, the handler ends the fight peacefully (`world/combat/handler.py:755-793` `_check_peaceful_resolution`). That is a state check, not a Resonance contest.

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
  > **⚠ Corrected 2026-09-11 — NOT implemented.** `world/combat/debug.py` (236 lines) is a single diagnostics sink — `get_splattercast` (`:160`), `debug_broadcast` (`:175`), `log_debug` (`:191`), `log_combat_action` (`:212`) — plus the durable audit log described by `COMBAT_AUDIT_LOGGING_SPEC.md`. It emits no timing, counter or throughput metric, and nothing anywhere under `world/combat/` measures performance. The other three bullets in this section are earned.

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

> **⚠ Corrected 2026-09-11 — the four `DEFAULT_*` lines are real (`world/combat/constants.py:17-20`); the three "Combat mechanics" lines are not.** `INITIATIVE_BASE`, `DAMAGE_MULTIPLIER` and `GRAPPLE_DIFFICULTY` appear nowhere in the repo. What actually ships:
> - **Initiative** — `randint(1, 20) + motorics + surplus_limb_initiative_bonus(char) + ambush_bonus`, rolled once when a combatant is added (`world/combat/utils.py:668-673`; the limb bonus is defined at `:295`).
> - **Damage** — `randint(1, 6)` base plus the weapon's own `db.damage`, with no global multiplier (`world/combat/attack.py:531-534`), then armor reduction in `take_damage` (`typeclasses/armor_mixin.py:69`, `:320`).
> - **Grapple** — an opposed motorics contest, not a fixed difficulty number (`world/combat/grappling.py`).
>
> Also in this file and **defined but never read anywhere**: `DEFAULT_HP = 10` and `HP_GRIT_MULTIPLIER = 2` (`:29-30`) — see the Grit note above. The timing constants this spec cites elsewhere are all genuine: `COMBAT_ROUND_INTERVAL = 6`, `STAGGER_DELAY_INTERVAL = 1.5`, `MAX_STAGGER_DELAY = 4.5` (`:806-808`).

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

> **⚠ Corrected 2026-09-11 — the date is wrong and "Recent" is stale.** This section was added **2025-09-14** in commit `bba77e22` ("Updated specs to reflect recent changes"), which appended sibling blocks to `COMBAT_MESSAGE_FORMAT_SPEC.md` and `DEATH_CURTAIN_SPEC.md` the same day. Read it as a **historical changelog entry for Sept 2025**, not as a description of recent work. The substance below verified accurate on re-check: perspective-specific messaging; the dual initiate, including its documented contextual triggers (`commands/combat/core_actions.py:493-503` — since #1584 it additionally requires the target to be conscious and alive, because a corpse should not square up); automatic phase colouring (`world/combat/messages/__init__.py:163-183`, in place since 2025-05-24, `1c8c6a3c`), the threat-escalation order included — `|r` is Evennia's bold red and `|R` the regular one; the removal of combat entry/exit spam; and medical-cause death messages.

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
