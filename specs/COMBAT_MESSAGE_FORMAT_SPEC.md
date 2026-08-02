# Combat Message Format Specification

> **Status:** ✅ **SHIPPED** — verified against code 2026-08-02.
>
> **⚠ Spec-vs-code corrections — the following claims were FALSE when audited:**
> - "Required Phases: initiate, hit, miss, kill" — **33 weapon files have no `initiate` phase** (knife, katana, machete, staff, sledgehammer, whip, chainsaw…).
> - The colour scheme documented here is not what ships: `__init__.py:175-185` colours only hit/kill/miss, `initiate` gets none, and miss uses `|W` not `|w`.
> - The third-person contract has moved on. `observer_msg` with `{attacker_name}`/`{target_name}` is now a **legacy fallback**; the shipped path is the identity-aware `observer_template` + `observer_char_refs` (`__init__.py:222-243`).
> - `{damage}` is listed as a standard placeholder; 2 of 101 message files use it.

**Version 1.0 - Message Refactoring Guidelines**

## Overview

This specification defines the standardized format for combat messages across all weapon types in the gelatinous combat system. The goal is to refactor existing messages from the old single-string format to the new multi-perspective dictionary format while preserving the rich, atmospheric content and distinctive tone.

## Current State Analysis

### Format Status by File Type:
- ✅ **Already Converted**: `anti-material_rifle.py`, `unarmed.py`, `grapple.py`
- ✅ **Refactoring Complete**: ~80 weapon message files converted to new format
- ✅ **Special Cases Handled**: `grapple.py` (extended phases), `unarmed.py` (base template)

### Existing Content Quality:
- **Rich, atmospheric messages** with visceral descriptions
- **Cinematic tone** influenced by:
  - Film noir and gritty crime fiction
  - Horror/thriller aesthetics  
  - Hardboiled detective fiction
  - Industrial/urban decay atmosphere
  - Psychological tension and dread
- **Technical weapon details** integrated naturally
- **Multiple message variants** per phase (10-20+ per category)
- **Consistent voice** across different weapon types

## Target Format Specification

### Standard Structure:
```python
MESSAGES = {
    "phase_name": [
        {
            "attacker_msg": "You [action] with {item_name}...",
            "victim_msg": "{attacker_name} [action] at you with {item_name}...", 
            "observer_msg": "{attacker_name} [action] with {item_name}..."
        },
        # ... additional message variants (10-20+ recommended)
    ],
    # ... additional phases
}
```

### Required Phases:
1. **`initiate`** - Combat preparation/weapon readying messages
2. **`hit`** - Successful attack messages  
3. **`miss`** - Failed attack messages
4. **`kill`** - Fatal blow messages (optional, can fall back to hit)

### Special Extended Phases (for specific weapons):
- **`escape_hit`** / **`escape_miss`** - Grappling escape attempts
- **`release`** - Voluntary release of grapples
- **`grapple_damage_hit`** / **`grapple_damage_miss`** / **`grapple_damage_kill`** - Damage while grappling

### Standard Placeholders:
- **`{attacker_name}`** - Attacker's display name (for victim/observer messages)
- **`{target_name}`** - Target's display name (for attacker/observer messages)  
- **`{item_name}`** - Weapon/item name
- **`{damage}`** - Damage dealt (for hit/kill messages)

### Message Perspective Guidelines:

#### Attacker Messages (First Person):
- Use "You" perspective
- Focus on the character's actions, sensations, intent
- Include tactical/technical weapon details
- Emphasize control and deliberation

**Example**: 
```
"You meticulously line up the shot with your anti-material rifle, knowing a single round can vaporize {target_name}."
```

#### Victim Messages (Second Person):
- Use "you" for the victim, "{attacker_name}" for the aggressor
- Emphasize the threat/danger directed at the victim
- Include victim-specific sensory details
- Build tension and immediacy

**Example**:
```
"{attacker_name} meticulously lines up the shot with their anti-material rifle, knowing a single round can vaporize you."
```

#### Observer Messages (Third Person):
- Use "{attacker_name}" and "{target_name}"
- Focus on external, visible actions
- Maintain atmospheric tension
- Avoid victim-specific internal details

**Example**:
```
"{attacker_name} meticulously lines up the shot with the anti-material rifle, knowing a single round can vaporize {target_name}."
```

## Tone and Style Guidelines

### Core Aesthetic Influences:
- **Film Noir**: Shadows, moral ambiguity, stark contrasts
- **Industrial Horror**: Mechanical brutality, urban decay
- **Hardboiled Fiction**: Terse, economical prose with punch
- **Psychological Thriller**: Building dread, intimate violence
- **Crime Drama**: Professional competence meets personal stakes

### Writing Style Requirements:

#### Language Characteristics:
- **Terse, punchy sentences** with strong rhythm
- **Visceral, tactile descriptions** that engage multiple senses
- **Technical authenticity** woven naturally into narrative
- **Atmospheric details** that build mood and tension
- **Varied sentence structure** to create rhythm and flow

#### Tone Elements:
- **Deliberate pacing** - Actions feel inevitable, not rushed
- **Professional competence** - Characters know their weapons/craft
- **Underlying menace** - Even preparation feels threatening
- **Sensory richness** - Sound, texture, weight, temperature
- **Emotional restraint** - Violence is matter-of-fact, not theatrical

#### Example Analysis from Existing Content:

**Chainsaw (old format)**:
```
"A guttural sound fills the room as the saw turns over. It doesn't want to start — it *needs* to."
```
- ✅ Mechanical personification
- ✅ Ominous inevitability  
- ✅ Sensory detail (sound)
- ✅ Psychological undertones

**Anti-material Rifle (new format)**:
```
"attacker_msg": "You meticulously line up the shot with your anti-material rifle, knowing a single round can vaporize {target_name}."
```
- ✅ Technical competence
- ✅ Calculated deliberation
- ✅ Understated lethality
- ✅ Professional focus

## Refactoring Process

### Step 1: Content Preservation
- **DO NOT TRUNCATE** existing message content
- **PRESERVE** the atmospheric quality and specific details
- **MAINTAIN** the established voice and tone
- **CONVERT** single strings to three-perspective format

### Step 2: Perspective Adaptation
For each existing message, create three versions:
1. **Attacker**: Convert to first-person "You" perspective
2. **Victim**: Add victim-specific threat awareness
3. **Observer**: Maintain third-person observational view

### Step 3: Placeholder Updates
- Replace `{attacker}` with `{attacker_name}` (victim/observer only)
- Replace `{target}` with `{target_name}` (attacker/observer only)
- Add `{item_name}` references where appropriate
- Add `{damage}` for hit/kill messages

### Step 4: Content Enhancement
- **Expand message variety** if needed (target: 10-20 per phase)
- **Add technical details** specific to weapon type
- **Enhance sensory descriptions** while maintaining tone
- **Ensure phase coverage** (initiate, hit, miss, kill minimum)

## Quality Assurance Checklist

### Content Quality:
- [ ] All existing atmospheric content preserved
- [ ] Three-perspective format implemented correctly
- [ ] Tone consistency maintained across perspectives
- [ ] Technical weapon details included naturally
- [ ] Sensory descriptions rich and varied

### Technical Requirements:
- [ ] Standard placeholders used correctly
- [ ] Required phases present (initiate, hit, miss, kill)
- [ ] Dictionary structure matches specification
- [ ] No truncated or lost content from original
- [ ] Message variety adequate (10+ per phase preferred)

### Tone Verification:
- [ ] Professional competence conveyed
- [ ] Atmospheric tension maintained
- [ ] Industrial/noir aesthetic preserved
- [ ] Violence portrayed as matter-of-fact, not glorified
- [ ] Pacing feels deliberate and inevitable

## Special Cases

### Grapple.py:
- Already converted ✅
- Extended phases: `escape_hit`, `escape_miss`, `release`, `grapple_damage_*`
- Use as template for other close-combat weapons

### Unarmed.py:
- Already converted ✅
- Standard four-phase structure
- Good baseline template for conversion

### Weapon-Specific Considerations:
- **Firearms**: Emphasize technical preparation, recoil, ballistics
- **Bladed Weapons**: Focus on edge quality, precision, intimate violence
- **Improvised Weapons**: Highlight adaptation, desperation, creativity
- **Power Tools**: Mechanical personality, industrial brutality
- **Explosives**: Countdown tension, area effect awareness

## Implementation Priority

### Phase 1: High-Priority Weapons (in use by prototypes)
- [ ] `knife.py` - DAGGER prototype
- [ ] `long_sword.py` - SWORD prototype  
- [ ] `baseball_bat.py` - BASEBALL_BAT prototype
- [ ] `staff.py` - STAFF prototype
- [ ] `throwing_knife.py` - THROWING_KNIFE prototype
- [ ] `throwing_axe.py` - THROWING_AXE prototype
- [ ] `shuriken.py` - SHURIKEN prototype

### Phase 2: Common Weapons
- [ ] `crowbar.py`, `hammer.py`, `machete.py`, `katana.py`
- [ ] `battle_axe.py`, `chainsaw.py`, `pipe_wrench.py`
- [ ] `brick.py`, `broken_bottle.py`, `tire_iron.py`

### Phase 3: Specialized/Exotic Weapons
- [ ] Firearms, exotic melee, improvised weapons
- [ ] Less common but atmospheric weapons

## Notes for Implementation

### Conversion Workflow:
1. **Backup original** file content
2. **Analyze existing messages** for tone and content
3. **Create three-perspective versions** of each message
4. **Test format** with message system
5. **Verify tone consistency** across perspectives
6. **Expand content** if message count is low

### Common Pitfalls to Avoid:
- ❌ Truncating rich atmospheric content
- ❌ Making victim messages identical to observer messages
- ❌ Losing technical weapon-specific details
- ❌ Breaking the established noir/industrial tone
- ❌ Rushing the conversion without preserving quality

### Success Criteria:
- ✅ All original atmospheric content preserved and enhanced
- ✅ Three distinct but consistent perspectives per message
- ✅ Technical integration with combat system
- ✅ Tone consistency maintained across all weapon types
- ✅ Enhanced player immersion through perspective-specific details

---

**Remember**: These messages are a core part of the game's atmospheric identity. The refactoring should enhance and preserve this identity, not diminish it through technical convenience.

## Recent Quality of Life Improvements (Sept 2024)

### Automatic Color Application System
The combat message system now automatically applies contextual colors based on message phase:

#### Color Scheme:
- **Kill Messages**: `|r{message}|n` (Bold red for fatal attacks)
- **Hit Messages**: `|R{message}|n` (Regular red for successful hits)  
- **Initiate Messages**: `|R{message}|n` (Regular red for threat establishment)
- **Miss Messages**: `|w{message}|n` (White for failed attempts)
- **Other Messages**: No automatic coloring (neutral phases)

#### Benefits:
- **Threat Escalation**: Visual progression from initiate → hit → kill
- **Clarity**: White misses clearly indicate failed attempts
- **Consistency**: Automatic application ensures uniform presentation
- **Override Support**: Pre-colored templates bypass automatic coloring

### Enhanced Initiate Message System
Combat initiation now provides proper perspective-specific messages and defensive reactions:

#### Dual Initiate Messages:
- **Attacker Initiate**: Aggressive stance establishment ("You draw your knife...")
- **Victim Defensive**: Defensive reaction when not already engaged ("Nick raises his baton defensively...")

#### Conditions for Victim Defensive Messages:
- Target wasn't already in combat, OR
- Target was in combat but not targeting anyone

#### Message Personalization:
- **Attackers** see first-person messages (`attacker_msg`)
- **Victims** see second-person messages (`victim_msg`)  
- **Observers** see third-person messages (`observer_msg`)

### Meta-Message Removal
Eliminated generic combat state announcements for cleaner narrative flow:
- **Removed**: "You enter combat!" message
- **Removed**: "You are no longer in combat." message  
- **Added**: TODO placeholder for narrative combat exit messages

#### Benefits:
- More immersive combat transitions
- Focus on weapon-specific narrative content
- Reduced message spam
- Natural flow from threat establishment to action

### Death Message Improvements
Enhanced death system messaging with medical cause integration:

#### Informed Death Messages:
- **Observer**: "Nick Kramer is dying from blood loss..."
- **Victim**: "Your body succumbs to blood loss. The end draws near..."
- **Fallback**: Beautiful mixed red death curtain message

#### Death Curtain Enhancements:
- **Color-corrected** random |r/|R block coloring
- **Proper text centering** accounting for color code length
- **Medical system integration** for cause-specific messaging
- **Race condition prevention** with bleeding message suppression

#### Kill Message Timing Fix (September 2024)
**Problem**: Death curtain animation was starting before kill messages could be displayed, causing narrative sequence issues where the death animation interrupted the climactic kill message.

**Root Cause**: Medical system's `take_damage()` method called `at_death()` immediately upon fatal damage determination, starting the death curtain before combat system could send contextual kill messages.

**Solution**: Implemented deferred death curtain system in `at_death()` method:
- **Combat Detection**: `at_death()` checks for active combat via `ndb.combat_handler`
- **Deferred Execution**: If in combat, sets `ndb.death_curtain_pending = True` and skips immediate curtain
- **Combat Integration**: Combat handler triggers deferred curtain after sending kill message
- **Safety Fallback**: 5-second delayed trigger ensures curtain appears even if combat fails to handle it

**Result**: Proper narrative sequence restored:
1. Fatal damage determined by medical system
2. Kill message sent by combat system ("Nick's bullet strikes you in the heart, killing you instantly")
3. Death curtain animation begins after kill message
4. Medical death analysis continues normally

**Benefits**:
- ✅ **Preserved Narrative Flow**: Kill messages appear before death animation
- ✅ **System Integration**: Medical and combat systems coordinate without coupling
- ✅ **Backward Compatibility**: Non-combat deaths (bleeding out) work unchanged
- ✅ **Robust Fallback**: Safety mechanism prevents stuck death states

---