# Combat Message Format Specification

> **Status:** ✅ **SHIPPED** — verified against code 2026-08-02.
>
> **⚠ Spec-vs-code corrections — the following claims were FALSE when audited:**
> - "Required Phases: initiate, hit, miss, kill" — **33 weapon files have no `initiate` phase** (knife, katana, machete, staff, sledgehammer, whip, chainsaw…).
> - The colour scheme documented here is not what ships: `_apply_color` (`__init__.py:175-198`) colours hit/initiate/kill and miss only, and miss uses `|W` not `|w`. *Re-measured 2026-09-18 (#3427): `initiate` sits in `successful_hit_phases` (`:163-169`) and renders `|R` exactly like `hit`, so "initiate gets none" was wrong even in 2026-08; and the phase lists are no longer the whole story — `weapon_type == "grapple"` takes an override branch ahead of them (`:179-189`, see §Special Extended Phases), and an empty message string is now returned uncoloured (`:177-178`) instead of being wrapped into a bare `|R|n`.*
> - The third-person contract has moved on. `observer_msg` with `{attacker_name}`/`{target_name}` is now a **legacy fallback**; the shipped path is the identity-aware `observer_template` + `observer_char_refs` (`__init__.py:222-243`; re-measured 2026-09-18 the block sits at `__init__.py:229-262`). *This bullet is accurate: `observer_template` is built at `:232-257`, `observer_char_refs` at `:259-262`, and the live consumers pass `observer_msg` only as a fallback — `world/combat/attack.py` uses `observer_template` exclusively (`:618`, `:653`, `:698-717`), as does `resolve_auto_escape` (`world/combat/actions.py:623`, `:676`).*
> - `{damage}` is listed as a standard placeholder; 2 of 101 message files use it.

**Version 1.0 - Message Refactoring Guidelines**

## Overview

This specification defines the standardized format for combat messages across all weapon types in the gelatinous combat system. The goal is to refactor existing messages from the old single-string format to the new multi-perspective dictionary format while preserving the rich, atmospheric content and distinctive tone.

## Current State Analysis

### Format Status by File Type:
- ✅ **Already Converted**: `anti-material_rifle.py`, `unarmed.py`, `grapple.py`
- ✅ **Refactoring Complete**: ~80 weapon message files converted to new format
  - *Re-measured 2026-09-12:* `world/combat/messages/` now holds **100 weapon banks** (plus `__init__.py`), every one in the three-perspective dict format — no bank lacks `attacker_msg`. Median variants per core phase: 30 (min 3, max 45). There is also a second message family this spec never mentions: **`world/combat/messages/severance/`** — 12 location banks (head, arms, hands, thighs, shins, feet, tail, forelegs, forepaws, hindlegs, hindpaws, cybernetic) plus its own loader `get_severance_message` (`severance/__init__.py:202`), keyed by location / injury_type / severity rather than weapon / phase, returning the same render shape (#332).
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
   - *Corrected 2026-09-12 — it does not fall back to `hit`.* A bank with no `kill` phase falls through to the loader's **generic** `fallback_template_set` (`world/combat/messages/__init__.py:66-71`, selected at `:107-108`), which renders `"You kill {target_name} with {item_name}."` from the phase name — not to that weapon's richer `hit` prose. `_handle_kill` (`world/combat/attack.py:684-717`) asks only for `"kill"` and has no second lookup. In practice this never fires, because all 99 non-grapple banks author a `kill` phase; but an author who omits one on the strength of this line gets the flat generic sentence, not graceful degradation. (This is the "is the phase genuinely optional?" half of **#1513**: optional, yes — but the fallback is not what the parenthesis promises.)

### Special Extended Phases (for specific weapons):
- **`escape_hit`** / **`escape_miss`** - Grappling escape attempts
- **`release`** - Voluntary release of grapples
- **`grapple_damage_hit`** / **`grapple_damage_miss`** / **`grapple_damage_kill`** - Damage while grappling

> **Reachability re-measured 2026-09-18 (#3427) — 39 of `grapple.py`'s 76 authored variants now reach players.** This supersedes the 2026-09-12 measurement ("72 of 76 unreachable"): the wiring that measurement called for shipped, and what remains unreached is one unbuilt mechanic rather than a plumbing gap. `get_combat_message` is now asked for `grapple` phases at three production call sites, and all three run.
>
> | phase | variants | reaches players | requested by |
> |---|---|---|---|
> | `hit` | 30 | ✅ new 2026-09-18 | `_say_from_bank(char, target, "hit")` on a won roll in `resolve_grapple_initiate` (`world/combat/grappling.py:421`) |
> | `miss` | 3 | ✅ new 2026-09-18 | `_say_from_bank(char, target, "miss")` on a lost roll, same resolver (`:427`) |
> | `release` | 2 | ✅ new 2026-09-18 | `_say_from_bank(char, grappling_target, "release")` in `resolve_release_grapple` (`:735`) |
> | `escape_hit` | 2 | ✅ unchanged | `resolve_auto_escape` (`world/combat/actions.py:316`), which the round loop runs for anyone grappled (`world/combat/handler.py:701`) |
> | `escape_miss` | 2 | ✅ unchanged | `resolve_auto_escape` (`world/combat/actions.py:369`) |
> | `grapple_damage_hit` | 30 | ❌ | nothing |
> | `grapple_damage_miss` | 5 | ❌ | nothing |
> | `grapple_damage_kill` | 2 | ❌ | nothing |
>
> **Live: 39. Unreached: 37 — all of them `grapple_damage_*`.** No code path deals damage *for* a grapple, so there is no beat for those three banks to narrate. They are pending content behind an unbuilt mechanic, not a wiring gap: the owner question "was a grapple-damage exchange ever meant to ship?" is open on **#3285** (`specs/GRAPPLE_SYSTEM_SPEC.md` §Grapple Damage System carries the verified not-built note). Nothing should be hooked up to them until that is answered.
>
> **Delivery.** `_say_from_bank(actor, target, phase)` (`world/combat/grappling.py:296`) is the single door for the three new phases and it delivers exactly as the weapon banks do: `attacker_msg` to the actor, `victim_msg` to the target, and `observer_template` + `observer_char_refs` through `msg_room_identity` with the pair excluded — so every bystander sees the pair rendered through their own recognition state instead of a pre-baked name. It passes `hit_location` **for the `hit` phase only** — `select_hit_location(target, attacker=actor)` (`world/medical/utils.py:120`), the same anatomy-weighted, armour-aware draw an attack makes, the attacker reading the target's weak points — because `hit` is the one reachable grapple phase that spends the placeholder. `miss` and `release` are asked for without it and none of their five variants uses it, as with the escape call sites in `world/combat/actions.py`. There is no `or "arm"` fallback and no placeholder default dict: both were dead and were deleted on 2026-09-18 (#3427), so an unpassed `hit_location` would surface as the loader's `(Error: Missing placeholder …)` rather than a silent limb — which is the contract the other banks live under (`specs/archive/WEAPON_MESSAGE_CONVERSION_SPEC.md`, #1583).
>
> Two second-order, player-visible consequences of routing through the loader:
> - **Colour stayed the grapple's own** (re-measured 2026-09-18, after review). The deleted hardcoded lines were green on success (`|g`) and yellow on failure (`|y`), and the loader now preserves that rather than repainting the hold in the attack palette: `_apply_color` takes a `weapon_type == "grapple"` branch *ahead* of the phase lists (`world/combat/messages/__init__.py:179-189`) — `hit`, `release` and `escape_hit` → `|g`; `miss` and `escape_miss` → `|y`; anything else in the bank uncoloured. A hold is not a wound, and the consensual uncontested hold that still writes its own lines beside this one wears the same green. *(An intermediate version of #3427 let these phases fall through to the attack palette — `hit` → `|R`, `miss` → `|W`, `release` bare. That is not what ships; ignore any note describing it.)* Two side effects worth knowing: `escape_hit` / `escape_miss` are **coloured for the first time** — they had shipped bare since #3391, because their phase names were in neither colour list — and an empty message string is now returned untouched (`:177-178`) instead of becoming a bare `"|R|n"`.
> - **`{hit_location}` is always the TARGET's location, in every audience's line** — and as of 2026-09-18 every `hit` variant spends it that way. Three variants misused it and all three were corrected in #3427: one used it for a face on the attacker and observer lines (now the literal word `face`, `world/combat/messages/grapple.py:125`, `:127`, matching the victim line that already said "their face"); and two spent a target-side draw on the *attacker's own* limbs, `"locking your {hit_location}s around {target_name}'s {hit_location}"` (`grapple.py:10`) and `"Like a vise, your/{attacker_name}'s {hit_location}s clamp around …"` (`:70-72`), which rendered as "your left arms" — both now say `arms` outright (`grapple.py:10-12`, `:70-72`), keeping the target-side `{hit_location}` only where it describes the target. **No `hit` variant pluralises the placeholder any more**; the survivors all read `{target_name}'s {hit_location}` or `your {hit_location}`. The 30 unreached `grapple_damage_hit` variants are *not* clean — `:226` and `:311` still put `{hit_location}` on the attacker's own arm/shoulder — but that bank narrates an unbuilt mechanic (#3285) and was left alone.
>
> **What deliberately keeps bespoke prose**, because no bank phase carries its meaning: the consensual uncontested hold (`grappling.py:371-390` — the `hit` bank is all violent shoot-ins and vises, and a trusted `grab` involves no contest and no roll); `resolve_grapple_join` (`:457`) and `resolve_grapple_takeover` (`:574`), whose beats are three-party and name a *current grappler* or a *third victim* that a two-party bank line has no slot for. `establish_grapple` (`grappling.py:58`) also still returns a hardcoded string — it is imported at `world/combat/handler.py:49` and called by nothing in production; only tests exercise it, to pin its one-grappler-one-victim guard.

### Standard Placeholders:
- **`{attacker_name}`** - Attacker's display name (for victim/observer messages)
- **`{target_name}`** - Target's display name (for attacker/observer messages)  
- **`{item_name}`** - Weapon/item name
- **`{damage}`** - Damage dealt (for hit/kill messages)

> **Measured 2026-09-12 — this list is both incomplete and optimistic.** The loader (`world/combat/messages/__init__.py:121-160`) also supplies `{hit_location}`, `{blood}` / `{Blood}` (species-keyed *target* fluid — human crimson, synth cobalt, robot amber; #1206/#1207), the bare aliases `{attacker}` / `{target}` / `{item}`, and `{phase}`. Actual usage across the 100 weapon banks: `{attacker_name}` 100, `{target_name}` 100, `{hit_location}` 100, `{blood}` 64, `{Blood}` 13, `{item_name}` **1** (`bowel_disruptor.py`), `{damage}` **2** (`anti-material_rifle.py`, `heavy_pistol.py`), `{phase}` 0. `{item_name}` and `{damage}` are supported by the loader but are not the shipped authoring style — each bank bakes its weapon's name into the prose instead. Whether that is intended house style or a gap is an open owner call (#1513).

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

#### Name Capitalisation (all banks)

> **Recorded 2026-09-18 (#3427) — this is bank-wide, not a grapple detail.** Templates are handed **bare** names and the *rendered sentence* is capitalised once, so the sentence decides the capital instead of the placeholder. `get_combat_message` builds `target_sees_attacker` with no capitalisation of its own (`world/combat/messages/__init__.py:37-41`) and passes each formatted `attacker_msg` / `victim_msg` / `observer_msg` through `capitalize_first` before colouring (`:219`). This is the rule the identity-aware observer path has followed since #3209; the three audiences now agree.
>
> **What this replaced.** The accessor used to force-capitalise `{attacker_name}` in *every* victim line and never capitalised a `{target_name}` that opened an attacker line. A multi-word sdesc therefore took a capital mid-sentence — "You stumble as **A** lanky man ties you up!" — while an attacker line that opened on the target began lowercase — "a lanky man finds themselves trapped in your unyielding grapple!". Both are fixed for all 100 banks at once.
>
> **What it means for authors.** A name may sit anywhere in a line. An sdesc keeps its lowercase article mid-sentence ("as a lanky man ties you up") and takes the capital only when it opens the sentence ("A lanky man ties you up"). **Proper names are unaffected** — `capitalize_first` uppercases the first *visible* letter and one that is already a capital stays as it is; it also steps over colour markup, so a pre-coloured line is not silently promoted from `|r` to `|R` (`world/grammar.py:754-784`, #2207).

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
- **Kill Messages**: `|r{message}|n` (Bold red for fatal attacks) — *corrected 2026-09-12: the intensities in this table are inverted. In Evennia (and in this repo's own convention — see `specs/GRAMMAR_ENGINE_SPEC.md:32`, `world/grammar.py:776`, `world/tests/test_grammar_colour_safety.py:40`) lowercase is normal and uppercase is bright: `|r` is **normal** red, `|R` is **bright** red. The codes shipped in `world/combat/messages/__init__.py:175-185` are right; only the parenthetical labels in the three rows below are wrong.*
- **Hit Messages**: `|R{message}|n` (Regular red for successful hits)  
- **Initiate Messages**: `|R{message}|n` (Regular red for threat establishment)
- **Miss Messages**: `|w{message}|n` (White for failed attempts)
- **Other Messages**: No automatic coloring (neutral phases)

> **Amended 2026-09-18 (#3427) — the table above describes the *attack* palette, which is no longer the only one.** `_apply_color` (`world/combat/messages/__init__.py:175-198`) now checks two things before the phase lists: an **empty** message is returned as-is (`:177-178`), where it previously became the bare colour pair `"|R|n"`; and `weapon_type == "grapple"` takes its own branch (`:179-189`) — `hit` / `release` / `escape_hit` → `|g`, `miss` / `escape_miss` → `|y`, everything else uncoloured. A grapple is a hold, not a wound, so it keeps the green/yellow its hardcoded lines wore and its bespoke consensual-hold prose still wears. `escape_hit` / `escape_miss` are coloured by this for the first time (bare since #3391). The pre-coloured-template bypass (a message already wrapped `|…`…`|n`) applies in both branches.

#### Benefits:
- **Threat Escalation**: Visual progression from initiate → hit → kill
  - *Measured 2026-09-12 — there is no three-step progression.* `initiate` and `hit` are both in `successful_hit_phases` and both render `|R` (`world/combat/messages/__init__.py:163-169`, `:177-181`), so the first two steps are visually **identical**; `kill` renders `|r`, which is *less* bright than `|R`, not more. Whether the intended escalation is `|r` → `|R` → `|R` + something (bold, a prefix, a bright-magenta kill) is an open owner call; the code is internally consistent, the claimed escalation is not what a player sees.
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