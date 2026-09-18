# Weapon Message Conversion Specification

> **Status:** 🗄 Historical — a one-time migration how-to; the conversion is complete (~80 files). Superseded as the format reference by COMBAT_MESSAGE_FORMAT_SPEC.

## Overview
This specification defines the process for converting weapon message files from the old single-perspective format to the new multi-perspective format in the Evennia combat system.

## Format Transformation

### Old Format (Single Perspective)
```python
MESSAGES = {
    "initiate": [
        "{attacker} produces a shockingly large cellphone, its blocky, beige casing a substantial piece of mobile technology.",
        "With a grim look, {attacker} brandishes the bulky cellphone, its long, rigid antenna jutting out menacingly."
    ],
    "hit": [
        "A swift, brutal swing from {attacker}'s cellphone connects with {target}'s arm with a sickening, hard plastic *CRACK* and a jolt."
    ]
}
```

### New Format (Multi-Perspective)

> *Note 2026-09-12: the `hit` entry below has drifted from the bank it was copied from — `world/combat/messages/cellphone.py:156-158` now parameterises the struck body part as `{target_name}'s {hit_location}` rather than `{target_name}'s arm`. Read the note at §Example Conversion before copying either block.*
```python
MESSAGES = {
    "initiate": [
        {
            "attacker_msg": "You produce a shockingly large cellphone, its blocky, beige casing a substantial piece of mobile technology.",
            "victim_msg": "{attacker_name} produces a shockingly large cellphone, its blocky, beige casing a substantial piece of mobile technology.",
            "observer_msg": "{attacker_name} produces a shockingly large cellphone, its blocky, beige casing a substantial piece of mobile technology."
        }
    ],
    "hit": [
        {
            "attacker_msg": "A swift, brutal swing from your cellphone connects with {target_name}'s arm with a sickening, hard plastic *CRACK* and a jolt.",
            "victim_msg": "A swift, brutal swing from {attacker_name}'s cellphone connects with your arm with a sickening, hard plastic *CRACK* and a jolt.",
            "observer_msg": "A swift, brutal swing from {attacker_name}'s cellphone connects with {target_name}'s arm with a sickening, hard plastic *CRACK* and a jolt."
        }
    ]
}
```

## Variable Substitution Rules

### Variable Mapping
| Old Format | New Format Perspectives |
|------------|------------------------|
| `{attacker}` | `You` (attacker) / `{attacker_name}` (victim/observer) |
| `{target}` | `{target_name}` (attacker/observer) / `you` (victim) |
| `{item_name}` | Remains `{item_name}` in all perspectives |
| `{damage}` | Remains `{damage}` in all perspectives (when present) |

> **Measured 2026-09-12 — the bottom two rows describe a mapping the shipped banks barely use, and the table predates the placeholders they actually use.** Across the 100 weapon banks: `{attacker_name}` 100 banks, `{target_name}` 100, **`{hit_location}` 100** (anatomy grounding added after this migration — #333 / PR #369 parameterised the kill templates, and the pattern then spread to hit/miss/initiate), `{blood}` 64, `{Blood}` 13 (species-keyed *target* fluid — human crimson, synth cobalt, robot amber; #1206 / PR #1207), `{item}` **1** (`melee.py`), `{item_name}` **1** (`bowel_disruptor.py`), `{damage}` **2** (`anti-material_rifle.py`, `heavy_pistol.py`), `{phase}` 0. No bank anywhere still uses the bare `{attacker}` / `{target}` of the old format, so the §After Conversion check for leftover variables passes.
>
> Two boundaries worth knowing before authoring. The loader *supplies* `blood` / `Blood` / `item` / `item_name` / `phase` itself, along with the bare `{attacker}` / `{target}` back-compat aliases (`world/combat/messages/__init__.py:121-160`) — which is why grepping the loader for `{attacker}` still hits even though no bank uses the old form. **`{hit_location}` is not loader-supplied**: it arrives only in the calling site's `**kwargs`, and a call site that omits it renders `(Error: Missing placeholder 'hit_location' …)` straight into the room (`__init__.py:220-223`; re-measured 2026-09-18 after #3427 moved the format loop). That was #1583 — so a bank is free to use `{hit_location}`, but only phases whose callers pass one are safe, and that is a per-call-site contract rather than a property of the format. Nothing in the table is broken; the authoring style that emerged simply bakes the weapon's name into the prose and parameterises the *body part* instead. Whether `{item_name}` / `{damage}` authoring was meant to survive is an open owner call (#1513).

### Perspective-Specific Pronoun Usage

#### Attacker Perspective (`attacker_msg`)
- Use "You" for the attacker
- Use "{target_name}" for the target
- Use possessive "your" for attacker's items/actions
- Use "{target_name}'s" for target's body parts/possessions

#### Victim Perspective (`victim_msg`)
- Use "{attacker_name}" for the attacker
- Use "you" for the target
- Use "{attacker_name}'s" for attacker's items/actions
- Use "your" for target's body parts/possessions

#### Observer Perspective (`observer_msg`)
- Use "{attacker_name}" for the attacker
- Use "{target_name}" for the target
- Use "{attacker_name}'s" for attacker's items/actions
- Use "{target_name}'s" for target's body parts/possessions

## Message Categories

### Required Categories
1. **initiate** - Messages for beginning combat with the weapon
2. **hit** - Messages for successful attacks
3. **miss** - Messages for failed attacks
4. **kill** - Messages for fatal blows

> **Measured 2026-09-12 — "required" is stronger than what the code enforces, and this list is not the whole phase vocabulary.** 99 of 100 banks carry all four. `grapple.py` carries neither `initiate` nor `kill`, correctly: its vocabulary is `hit` / `miss` plus `escape_hit` / `escape_miss` / `release` / `grapple_damage_hit` / `grapple_damage_miss` / `grapple_damage_kill`. Of those alternates only `escape_hit` and `escape_miss` were requested by a caller when this was measured; **corrected 2026-09-18 (#3427): `hit`, `miss` and `release` are requested now too**, through `speak_grapple_beat` — named `_say_from_bank` at the time — in `world/combat/grappling.py:296` (see `specs/GRAPPLE_SYSTEM_SPEC.md` §Grapple Messaging). **Corrected again the same day (#3615): the vocabulary grew by five, to 13 phases / 87 variants** — `release_charge`, `release_charge_away`, `release_jump`, `release_blast`, `release_intent`, for the ways a hold ends without its holder choosing to end it — and all five are requested through that same helper. What is still referenced nowhere but the loader's phase-colouring lists (`world/combat/messages/__init__.py:170-180`) is the three `grapple_damage_*` phases alone (37 authored entries), and that is an unbuilt mechanic — #3285 — rather than a wiring gap. The guard test added for #2823 deliberately requires only that a bank offer *one* populated phase, not the four (`world/tests/test_combat_message_banks.py:52-66`). A bank that omits `kill` does **not** degrade to its own `hit` prose — it falls through to the loader's generic sentence (`world/combat/messages/__init__.py:67-71`, selected at `:107-108`); see the correction block in `specs/COMBAT_MESSAGE_FORMAT_SPEC.md`.
>
> One trap for anyone auditing this: 32 banks spell the key single-quoted as `'initiate'` and 68 double-quoted, so a double-quote-only grep reports 32 banks as missing the phase. That is the provenance of the "33 weapon files have no `initiate` phase" claim carried in `specs/COMBAT_MESSAGE_FORMAT_SPEC.md` and in open issue **#1513** — 32 single-quoted banks + `grapple.py` = 33. Parsed rather than grepped, `knife`, `katana`, `machete`, `staff`, `sledgehammer` and `whip` each carry a 30-variant `initiate` phase and `chainsaw` carries 41.

### Message Count Guidelines
- Maintain the same number of messages per category as the original
- Typical counts: 30 initiate, 30 hit, 30 miss, 30 kill messages
- Some variation is acceptable but avoid significant reduction

## Content Transformation Rules

### 1. One-for-One Refactor
- Transform existing messages by adjusting perspective ONLY
- Do NOT rewrite, expand, or change the core content
- Keep the exact same action, imagery, and details
- Only modify pronouns and perspective-specific variables

### 2. Perspective Consistency
- Each message must be adjusted for all three perspectives
- Maintain the core action and imagery while ONLY adapting pronouns
- Ensure grammatical correctness in each perspective
- Preserve the original sentence structure and word choice

### 3. Minimal Contextual Adjustments
- Only add minimal context when grammatically necessary
- Avoid adding new descriptive elements or threat awareness
- Keep observer messages as neutral third-person versions
- Do not embellish or enhance the original content

### 4. Preserve Original Content
- Maintain the exact emotional tone and intensity
- Keep all weapon-specific character and atmosphere unchanged
- Preserve all sound effects (e.g., "*CRACK*", "*THUMP*") exactly
- Keep all damage descriptions and physical effects identical
- **CRITICAL**: Preserve poetic and atmospheric language exactly
- Maintain metaphors, imagery, and distinctive voice
- Keep all descriptive phrases that define weapon character

### 5. Atmospheric Writing Preservation Examples
**✅ PRESERVE EXACTLY:**
- "The metal stretches and sighs"
- "like trust on the verge of betrayal"
- "drops with the grace of rubble"
- "kissing air and threat into the space between them"
- "The chain doesn't creak. It hums."

**❌ AVOID:**
- Generic rewrites that lose atmospheric voice
- Simplifying poetic language
- Removing metaphors or distinctive imagery
- Adding new content not in the original

## Quality Assurance Checklist

### Before Conversion
- [ ] Read and understand the original weapon's character
- [ ] Note the total message count per category
- [ ] Identify unique weapon-specific elements
- [ ] Check for any special formatting or effects

### During Conversion
- [ ] Convert ALL messages, not just a subset
- [ ] Maintain consistent pronoun usage per perspective
- [ ] Preserve weapon-specific terminology and characteristics exactly
- [ ] Keep sound effects and onomatopoeia unchanged
- [ ] Ensure grammatical correctness in each perspective
- [ ] Perform ONLY perspective adjustments, no content rewrites

### After Conversion
- [ ] Verify message count matches original (±2 messages acceptable)
- [ ] Check that all dictionary structures are properly formatted
- [ ] Confirm no old format variables remain ({attacker}, {target})
- [ ] Test a sample message from each category for variable substitution
- [ ] Ensure no duplicate or corrupted content

## File Handling Process

### Recommended Workflow
1. **Create Blank**: Use `create_file` to create a blank test file with "_new" suffix first
2. **Set Up Structure**: Add basic MESSAGES dictionary structure with empty arrays
3. **Read Original**: Use `read_file` to examine the complete original file
4. **Systematic Chunking**: Convert messages in groups of 5 to prevent replacement failures
5. **Build Incrementally**: Use `replace_string_in_file` to add each chunk of converted messages
6. **Verify Quality**: Review the conversion for completeness and accuracy
7. **Replace Original**: Move original to backup and rename new file (manual process)

### Chunking Strategy (Critical for Success)
- **Convert 5 messages at a time** to avoid string replacement failures
- **Use specific context** when replacing - include 3-5 lines before/after target
- **Build systematically**: First 5 messages, then next 5, etc.
- **Track progress**: Note which messages have been converted to avoid duplication

### Example Chunking Pattern
```
Initiate Messages: 1-5 (first chunk) → 6-10 (second chunk) → 11-15 (third chunk)...
Hit Messages: 1-5 (first chunk) → 6-10 (second chunk) → 11-15 (third chunk)...
Miss Messages: 1-5 (first chunk) → 6-10 (second chunk) → 11-15 (third chunk)...
Kill Messages: 1-5 (first chunk) → 6-10 (second chunk) → 11-15 (third chunk)...
```

### Avoid In-Place Editing
- Do NOT use `replace_string_in_file` for large conversions on original files
- In-place editing can cause corruption with complex multi-line changes
- Always create clean new files for weapon conversions
- Large single replacements often fail - use systematic chunking instead

## Error Prevention

### Common Mistakes to Avoid
1. **Incomplete Conversion**: Converting only some messages while leaving others in old format
2. **Pronoun Confusion**: Mixing up perspective-specific pronouns
3. **Variable Errors**: Leaving old format variables or incorrect new format usage
4. **Content Loss**: Accidentally truncating or omitting messages
5. **Format Corruption**: Malformed dictionaries or syntax errors
6. **Content Rewriting**: Adding new content instead of only adjusting perspective
7. **Embellishment**: Enhancing or expanding on the original message content

### Validation Steps
1. Count messages in each category before and after conversion
2. Search for old format variables to ensure complete conversion
3. Verify dictionary structure syntax
4. Check that each message has all three perspectives

## Example Conversion

> **Drifted 2026-09-12 — the worked example no longer matches the bank it was drawn from.** `world/combat/messages/cellphone.py:4-6` still carries the `initiate` example verbatim, but the `hit` example's hardcoded body part is gone: `cellphone.py:166-168` now reads `"Your cellphone smashes against {target_name}'s {hit_location}, its hard casing and keypad imprinting a painful, rapidly swelling bruise."` The §New Format example higher up drifted the same way (`cellphone.py:156-158`, `{target_name}'s {hit_location}` for `{target_name}'s arm`). All 100 banks now carry `{hit_location}` somewhere (#333 / PR #369 onward), so a conversion done to the letter of either example would ship a hardcoded limb. The prose is otherwise unchanged — the one-for-one refactor rule in §Content Transformation Rules held.
>
> **Scope of that substitution, for anyone repeating it.** `{hit_location}` is the *target's* struck location, chosen by `select_hit_location` at the call site. It is right in `{target_name}'s {hit_location}` (attacker/observer) and `your {hit_location}` (victim); it is wrong anywhere it stands for the attacker's own anatomy. 215 `attacker_msg` lines in the `initiate` phase currently read `your {hit_location}` in positions that plainly described the attacker's own face, shoulder or wrist — `baton.py` "A flick of your {hit_location} brings your baton to full length", `assault_rifle.py` "You snap your assault rifle to your {hit_location}" — which render in play as "a flick of your left thigh". That is collateral damage from the sweep, not the house style: parameterise the body part being *hit*, never the body part doing the hitting.

### Original Message
```python
"hit": [
    "{attacker}'s cellphone smashes against {target}'s face, its hard casing and keypad imprinting a painful, rapidly swelling bruise."
]
```

### Converted Message
```python
"hit": [
    {
        "attacker_msg": "Your cellphone smashes against {target_name}'s face, its hard casing and keypad imprinting a painful, rapidly swelling bruise.",
        "victim_msg": "{attacker_name}'s cellphone smashes against your face, its hard casing and keypad imprinting a painful, rapidly swelling bruise.",
        "observer_msg": "{attacker_name}'s cellphone smashes against {target_name}'s face, its hard casing and keypad imprinting a painful, rapidly swelling bruise."
    }
]
```

## Success Criteria

A successful conversion must:
1. Transform ALL messages in ALL categories with perspective adjustments only
2. Maintain weapon character and atmosphere exactly as written
3. Use correct perspective-specific pronouns
4. Preserve technical details and effects unchanged
5. Result in clean, properly formatted Python dictionaries
6. Pass basic syntax validation
7. Keep original content intact with only pronoun/perspective changes

> **Partly machine-enforced now, noted 2026-09-12.** `world/tests/test_combat_message_banks.py` pins part of this contract structurally for every bank `pkgutil` finds: that it exports the name the loader reads (`:38`), that it offers at least one populated phase (`:52`), and that every entry present carries all three observer roles (`:68`). That covers criterion 6 (the test imports each bank, so a syntax error fails here), most of criterion 5, and the *per-entry* half of criterion 1. It does **not** cover completeness — nothing asserts message counts, so a bank that lost half its variants during conversion still passes, and the §After Conversion count check remains a human step. Criteria 2, 3, 4 and 7 — voice, perspective, atmosphere, no-embellishment — remain human-judged and unpinned.
>
> The test exists because four banks shipped exporting `SCALPEL_MESSAGES` / `SCIMITAR_MESSAGES` / `SEMI_AUTO_RIFLE_MESSAGES` / `STREETLIGHT_MESSAGES` instead of `MESSAGES`, and 478 authored lines fell silently through to the loader's generic fallback for months — an empty bank and a weapon that was never given one are indistinguishable at `getattr(module, "MESSAGES", {})` (#2823, fixed).

## File Naming Convention

- Original: `weapon.py`
- Backup: `weapon_old.py` 
- New Version: `weapon_new.py` (temporary)
- Final: `weapon.py` (after verification and replacement)

This specification ensures consistent, high-quality conversions that maintain the combat system's immersive multi-perspective messaging while preserving each weapon's unique character and mechanical details.
