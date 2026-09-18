# Combat Message Format Specification

> **Status:** ✅ **SHIPPED** — verified against code 2026-08-02.
>
> **⚠ Spec-vs-code corrections — the following claims were FALSE when audited:**
> - "Required Phases: initiate, hit, miss, kill" — **33 weapon files have no `initiate` phase** (knife, katana, machete, staff, sledgehammer, whip, chainsaw…).
> - The colour scheme documented here is not what ships: `_apply_color` (`__init__.py:182-207`) colours hit/initiate/kill and miss only, and miss uses `|W` not `|w`. *Re-measured 2026-09-18 (#3427, line refs refreshed after #3615): `initiate` sits in `successful_hit_phases` (`:170-176`) and renders `|R` exactly like `hit`, so "initiate gets none" was wrong even in 2026-08; and the phase lists are no longer the whole story — `weapon_type == "grapple"` takes an override branch ahead of them (`:186-198`, see §Special Extended Phases), and an empty message string is now returned uncoloured (`:184-185`) instead of being wrapped into a bare `|R|n`.*
> - The third-person contract has moved on. `observer_msg` with `{attacker_name}`/`{target_name}` is now a **legacy fallback**; the shipped path is the identity-aware `observer_template` + `observer_char_refs` (`__init__.py:222-243`; re-measured 2026-09-18 after #3615 the block sits at `__init__.py:238-272`). *This bullet is accurate: `observer_template` is built at `:238-266`, `observer_char_refs` at `:268-272`, and the live consumers pass `observer_msg` only as a fallback — `world/combat/attack.py` uses `observer_template` exclusively (`:618`, `:653`, `:698-717`), as does `resolve_auto_escape` (`world/combat/actions.py:623`, `:676`).*
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
- **`release_charge`** / **`release_charge_away`** / **`release_jump`** / **`release_blast`** - A hold that ends for a reason other than the holder choosing it (#3615): letting go to charge a third party, letting go to charge out of the room, letting go for a gap jump, and a blast tearing the pair apart
- **`release_intent`** - The actor-only *preview* printed when a charge is queued while holding someone (#3615). Nothing has happened to the hold yet, so the variant's `victim_msg` and `observer_msg` are authored as empty strings

> **Reachability re-measured 2026-09-18 (#3615) — `grapple.py` is now 13 phases / 87 authored variants, and 50 of them reach players.** This supersedes the same-day #3427 measurement ("39 of 76"), which itself superseded 2026-09-12's "72 of 76 unreachable". #3427 wired the three resolver beats to the bank as it stood; #3615 **authored five new phases (11 variants)** for the ways a hold ends without its holder choosing to end it, and wired the four remaining doors onto them — the owner's call: *"adding the missing messages to our list that can be expanded/subtracted like all our combat messages and then wiring it in - makes the most sense."* What is still unreached is one unbuilt mechanic, not a plumbing gap. `get_combat_message` is asked for `grapple` phases at **ten** production call sites — three resolver beats, two auto-escape beats, and five release beats across four doors (the charge door branches same-room / cross-room) — and all ten run.
>
> | phase | variants | reaches players | requested by |
> |---|---|---|---|
> | `hit` | 30 | ✅ 2026-09-18 (#3427) | `speak_grapple_beat(char, target, "hit")` on a won roll in `resolve_grapple_initiate` (`world/combat/grappling.py:426`) |
> | `miss` | 3 | ✅ 2026-09-18 (#3427) | `speak_grapple_beat(char, target, "miss")` on a lost roll, same resolver (`:432`) |
> | `release` | 2 | ✅ 2026-09-18 (#3427) | `speak_grapple_beat(char, grappling_target, "release")` in `resolve_release_grapple` (`:740`) |
> | `escape_hit` | 2 | ✅ unchanged | `resolve_auto_escape` (`world/combat/actions.py:316`), which the round loop runs for anyone grappled (`world/combat/handler.py:701`) |
> | `escape_miss` | 2 | ✅ unchanged | `resolve_auto_escape` (`world/combat/actions.py:369`) |
> | `release_charge` | 3 | ✅ new 2026-09-18 (#3615) | same-room branch of `_release_grapple_for_charge` — `speak_grapple_beat(char, grappled_victim, "release_charge", charge_target=target)` (`world/combat/movement_resolution.py:887`). Spends the third-party placeholder `{charge_target}` |
> | `release_charge_away` | 2 | ✅ new 2026-09-18 (#3615) | the cross-room branch of the same helper (`:885`). Names no third party: the charge target is in another room, so the line says "charges away" instead |
> | `release_jump` | 3 | ✅ new 2026-09-18 (#3615) | gap jump in `CmdJump` (`commands/combat/jump.py:714`), after `break_grapple` and before the caller moves |
> | `release_blast` | 2 | ✅ new 2026-09-18 (#3615) | the blast on a human-shield sacrifice jump (`jump.py:411`). The only one of the five where the *actor* did not choose it, and the prose says so ("The blast tears {target_name} out of your arms!") |
> | `release_intent` | 1 | ✅ new 2026-09-18 (#3615) — **actor only** | queue-time charge preview in `CmdCharge` (`commands/combat/movement.py:779`), called with `audiences=("actor",)` and `charge_target=target_search` |
> | `grapple_damage_hit` | 30 | ❌ | nothing |
> | `grapple_damage_miss` | 5 | ❌ | nothing |
> | `grapple_damage_kill` | 2 | ❌ | nothing |
>
> **Live: 50. Unreached: 37 — all of them `grapple_damage_*`.** No code path deals damage *for* a grapple, so there is no beat for those three banks to narrate. They are pending content behind an unbuilt mechanic, not a wiring gap: the owner question "was a grapple-damage exchange ever meant to ship?" is open on **#3285** (`specs/GRAPPLE_SYSTEM_SPEC.md` §Grapple Damage System carries the verified not-built note). Nothing should be hooked up to them until that is answered.
>
> **Delivery — one public helper.** `speak_grapple_beat(actor, target, phase, *, audiences=("actor", "victim", "room"), **extra_chars)` (`world/combat/grappling.py:296`) is the single door onto the bank for every grapple beat. It was `_say_from_bank` until #3615 made it public: three modules outside its own now call it (`world/combat/movement_resolution.py`, `commands/combat/jump.py`, `commands/combat/movement.py`), so the leading underscore had stopped describing its reach. It delivers exactly as the weapon banks do: `attacker_msg` to the actor, `victim_msg` to the target, and `observer_template` + `observer_char_refs` through `msg_room_identity` with the pair excluded — so every bystander sees the pair rendered through their own recognition state instead of a pre-baked name. Three details of its signature:
>
> - **`audiences`** narrows delivery to a subset of `("actor", "victim", "room")`; the default is all three. Only `release_intent` uses it (`audiences=("actor",)`), because a *queued* charge has not ended the hold yet and telling the victim or the room would describe a world state that does not exist. Belt and braces: that phase's single variant also authors empty strings for the other two audiences, so the narrowing and the bank say the same thing and either alone would suffice.
> - **`**extra_chars`** is forwarded verbatim as the accessor's `extra_chars` argument — a third party the line names, rendered per audience; see §Standard Placeholders for the contract. `release_charge` and `release_intent` are the only phases that spend one, both as `charge_target`.
> - **`hit_location`** is passed **for the `hit` phase only** — `select_hit_location(target, attacker=actor)` (`world/medical/utils.py:120`), the same anatomy-weighted, armour-aware draw an attack makes, the attacker reading the target's weak points — because `hit` is the one reachable grapple phase that spends the placeholder. Every other phase, the five new ones included, is asked for without it and none of their variants uses it, as with the escape call sites in `world/combat/actions.py`. There is no `or "arm"` fallback and no placeholder default dict: both were dead and were deleted on 2026-09-18 (#3427), so an unpassed `hit_location` would surface as the loader's `(Error: Missing placeholder …)` rather than a silent limb — which is the contract the other banks live under (`specs/archive/WEAPON_MESSAGE_CONVERSION_SPEC.md`, #1583).
>
> **Where the room broadcast lands.** `msg_room_identity` is given `location=actor.location`, read at send time. For four of the five new doors that is the room the hold was in, because each speaks before its mover moves (or does not move at all). The **cross-room charge is the exception**: `_resolve_charge_cross_room` calls `char.move_to(target_room)` (`world/combat/movement_resolution.py:1098`) *before* `_release_grapple_for_charge` (`:1101`), so `release_charge_away` is heard by the room the charger **arrived in** — where the victim is not — and the room the pair was grappling in still hears nothing. The victim's own line is unaffected (it is sent directly). Recorded as measured, not asserted as intended: whether that broadcast should be sent from the origin room instead is a question for whoever revisits the charge mover.
>
> Two second-order, player-visible consequences of routing through the loader:
> - **Colour stayed the grapple's own** (re-measured 2026-09-18, after review; extended by #3615). The deleted hardcoded lines were green on success (`|g`) and yellow on failure (`|y`), and the loader preserves that rather than repainting the hold in the attack palette: `_apply_color` takes a `weapon_type == "grapple"` branch *ahead* of the phase lists (`world/combat/messages/__init__.py:186-198`) — `hit`, `release` and `escape_hit` → `|g`; `miss`, `escape_miss` and **all five #3615 phases** (`release_charge`, `release_charge_away`, `release_jump`, `release_blast`, `release_intent`) → `|y`; anything else in the bank uncoloured. The split is not success-vs-failure but *hold kept or let go on purpose* (green) against *a grip lost, or about to be* (yellow), which is what the five new phases narrate — including the preview, where the grip is not lost yet. A hold is not a wound, and the consensual uncontested hold that still writes its own lines beside this one wears the same green. *(An intermediate version of #3427 let these phases fall through to the attack palette — `hit` → `|R`, `miss` → `|W`, `release` bare. That is not what ships; ignore any note describing it.)* Two side effects worth knowing: `escape_hit` / `escape_miss` are **coloured for the first time** — they had shipped bare since #3391, because their phase names were in neither colour list — and an **empty** message string is returned untouched (`:184-185`) instead of becoming a bare `"|R|n"`, which is what keeps `release_intent`'s empty victim and observer lines from arriving as two stray colour codes.
> - **`{hit_location}` is always the TARGET's location, in every audience's line** — and as of 2026-09-18 every `hit` variant spends it that way. Three variants misused it and all three were corrected in #3427: one used it for a face on the attacker and observer lines (now the literal word `face`, `world/combat/messages/grapple.py:125`, `:127`, matching the victim line that already said "their face"); and two spent a target-side draw on the *attacker's own* limbs, `"locking your {hit_location}s around {target_name}'s {hit_location}"` (`grapple.py:10`) and `"Like a vise, your/{attacker_name}'s {hit_location}s clamp around …"` (`:70-72`), which rendered as "your left arms" — both now say `arms` outright (`grapple.py:10-12`, `:70-72`), keeping the target-side `{hit_location}` only where it describes the target. **No `hit` variant pluralises the placeholder any more**; the survivors all read `{target_name}'s {hit_location}` or `your {hit_location}`. The 30 unreached `grapple_damage_hit` variants are *not* clean — `:226` and `:311` still put `{hit_location}` on the attacker's own arm/shoulder — but that bank narrates an unbuilt mechanic (#3285) and was left alone.
>
> **What deliberately keeps bespoke prose**, because no bank phase carries its meaning: the consensual uncontested hold (`grappling.py:371-390` — the `hit` bank is all violent shoot-ins and vises, and a trusted `grab` involves no contest and no roll); `resolve_grapple_join` (`:457`) and `resolve_grapple_takeover` (`:574`), whose beats are three-party and name a *current grappler* or a *third victim* that a two-party bank line has no slot for. `establish_grapple` (`grappling.py:58`) also still returns a hardcoded string — it is imported at `world/combat/handler.py:49` and called by nothing in production; only tests exercise it, to pin its one-grappler-one-victim guard.

### Standard Placeholders:
- **`{attacker_name}`** - Attacker's display name (for victim/observer messages)
- **`{target_name}`** - Target's display name (for attacker/observer messages)  
- **`{item_name}`** - Weapon/item name
- **`{damage}`** - Damage dealt (for hit/kill messages)

> **Measured 2026-09-12 — this list is both incomplete and optimistic.** The loader (`world/combat/messages/__init__.py:121-160`) also supplies `{hit_location}`, `{blood}` / `{Blood}` (species-keyed *target* fluid — human crimson, synth cobalt, robot amber; #1206/#1207), the bare aliases `{attacker}` / `{target}` / `{item}`, and `{phase}`. Actual usage across the 100 weapon banks: `{attacker_name}` 100, `{target_name}` 100, `{hit_location}` 100, `{blood}` 64, `{Blood}` 13, `{item_name}` **1** (`bowel_disruptor.py`), `{damage}` **2** (`anti-material_rifle.py`, `heavy_pistol.py`), `{phase}` 0. `{item_name}` and `{damage}` are supported by the loader but are not the shipped authoring style — each bank bakes its weapon's name into the prose instead. Whether that is intended house style or a gap is an open owner call (#1513). *(Re-measured 2026-09-18 after #3615 the shared-kwargs block sits at `:124-167`.)*

#### Third parties — `extra_chars` (added 2026-09-18, #3615)

> A line sometimes has to name **someone who is neither the attacker nor the target** — the person a grappler lets go of their victim to charge at. `get_combat_message` takes a keyword `extra_chars={placeholder_name: object}` alongside `attacker` / `target` / `item` (`world/combat/messages/__init__.py:8`). Each entry adds one placeholder to the bank's vocabulary, and the point of the mechanism is that it is **rendered per audience, exactly as the two principals already are**, rather than resolved once and baked in:
>
> | audience | how the object renders | built at |
> |---|---|---|
> | `attacker_msg` | `get_display_name_safe(obj, attacker)` — the third party as the **actor** knows them | `__init__.py:144` |
> | `victim_msg` | `get_display_name_safe(obj, target)` — as the **victim** knows them | `:154` |
> | legacy `observer_msg` | `obj.key`, pre-resolved — matching what that legacy field already does for the pair | `:166` |
> | identity-aware `observer_template` | **left as the literal `{placeholder}`**, and the object is carried in `observer_char_refs` | `:238-266`, `:268-272` |
>
> The last row is the one that carries the design. The observer template is formatted with `format_map(_PassThrough(shared_kwargs))` (`:260-262`), and `extra_chars` is deliberately **not** folded into `shared_kwargs` — so an entry the map does not know survives formatting as the literal `{charge_target}` instead of being resolved early or raising `KeyError`. `observer_char_refs` then carries the object under that same key (`:268-272`), and `msg_room_identity` (`world/identity_utils.py:108`) substitutes it once per observer through *that observer's* recognition state. A bystander who knows the charge target by name reads the name; one who does not reads their sdesc — in the same sentence where the grappler and the victim are already resolved that way. Placeholders `msg_room_identity` has no ref for pass through untouched, as they always have, so this costs nothing to the other 100 banks.
>
> `extra_chars` defaults to `None` and is normalised to `{}` at `:123`, so a caller that passes nothing gets exactly the behaviour it got before. The only shipped users are the grapple bank's `release_charge` and `release_intent` phases, whose `{charge_target}` is supplied by `speak_grapple_beat(..., charge_target=target)` (§Special Extended Phases). A placeholder named in a template but absent from `extra_chars` fails the way every other missing placeholder does — `(Error: Missing placeholder …)` in the rendered line, not a silent blank.
>
> **One reading to know about.** The room broadcast excludes only the attacker and the target, so the third party themself is an ordinary observer and `get_display_name(self)` returns their own key (`typeclasses/characters.py:1295-1296`) — the person being charged reads *"Jorge lets go of Skullface and goes for Iver"*, not *"…goes for you"*. `msg_room_identity` has no second-person substitution and never has; any door that wants one has to send that person their own line, the way the attacker and victim get theirs.

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

> **Recorded 2026-09-18 (#3427) — this is bank-wide, not a grapple detail.** Templates are handed **bare** names and the *rendered sentence* is capitalised once, so the sentence decides the capital instead of the placeholder. `get_combat_message` builds `target_sees_attacker` with no capitalisation of its own (`world/combat/messages/__init__.py:37-41`) and passes each formatted `attacker_msg` / `victim_msg` / `observer_msg` through `capitalize_first` before colouring (`:228` after #3615). This is the rule the identity-aware observer path has followed since #3209; the three audiences now agree.
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
- Extended phases: `escape_hit`, `escape_miss`, `release`, `release_charge`, `release_charge_away`, `release_jump`, `release_blast`, `release_intent`, `grapple_damage_*` — 13 phases / 87 variants in all as of #3615
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

> **Amended 2026-09-18 (#3427, extended by #3615) — the table above describes the *attack* palette, which is no longer the only one.** `_apply_color` (`world/combat/messages/__init__.py:182-207`) checks two things before the phase lists: an **empty** message is returned as-is (`:184-185`), where it previously became the bare colour pair `"|R|n"`; and `weapon_type == "grapple"` takes its own branch (`:186-198`) — `hit` / `release` / `escape_hit` → `|g`, `miss` / `escape_miss` / `release_charge` / `release_charge_away` / `release_jump` / `release_blast` / `release_intent` → `|y`, everything else uncoloured. A grapple is a hold, not a wound, so it keeps the green/yellow its hardcoded lines wore and its bespoke consensual-hold prose still wears. `escape_hit` / `escape_miss` are coloured by this for the first time (bare since #3391). The pre-coloured-template bypass (a message already wrapped `|…`…`|n`) applies in both branches.

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