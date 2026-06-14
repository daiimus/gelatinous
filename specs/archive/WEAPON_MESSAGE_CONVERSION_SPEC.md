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

## File Naming Convention

- Original: `weapon.py`
- Backup: `weapon_old.py` 
- New Version: `weapon_new.py` (temporary)
- Final: `weapon.py` (after verification and replacement)

This specification ensures consistent, high-quality conversions that maintain the combat system's immersive multi-perspective messaging while preserving each weapon's unique character and mechanical details.
