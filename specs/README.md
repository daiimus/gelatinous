# specs/

Design specifications for game systems and features. 37 spec files covering combat, commands, UI, medical, identity, communication, and integrations.

## Core Systems

| Spec | Description |
|------|-------------|
| `COMBAT_SYSTEM.md` | Overall combat system design |
| `COMBAT_REFACTOR_SPEC.md` | Combat module decomposition plan |
| `COMBAT_MESSAGE_FORMAT_SPEC.md` | Combat messaging and template system |
| `PROXIMITY_SYSTEM_SPEC.md` | Tactical positioning mechanics |
| `GRAPPLE_SYSTEM_SPEC.md` | Grappling and restraint mechanics |
| `HEALTH_AND_SUBSTANCE_SYSTEM_SPEC.md` | Medical/trauma system design |
| `CLOTHING_SYSTEM_SPEC.md` | Clothing and layering system |
| `MODULAR_ARMOR_SYSTEM_SPEC.md` | Armor coverage and damage reduction |
| `SHOP_SYSTEM_SPEC.md` | Shop pricing and inventory |
| `TIME_SYSTEM_SPEC.md` | In-game time and day/night cycle |
| `WORLD_STATE_INTELLIGENCE_SYSTEM_SPEC.md` | Zone-level world simulation (design phase) |
| `IDENTITY_RECOGNITION_SPEC.md` | Sleeve-based identity, recognition memory, and assigned names |
| `EMOTE_POSE_SPEC.md` | Emote, pose, and communication system with identity integration |

## Commands

| Spec | Description |
|------|-------------|
| `JUMP_COMMAND_SPEC.md` | Inter-room jumping |
| `THROW_COMMAND_SPEC.md` | Cross-room projectile throwing |
| `WREST_COMMAND_SPEC.md` | Taking items by force |
| `BUG_COMMAND_SPEC.md` | In-game bug reporting |
| `LOOK_COMMAND_SPEC.md` | Enhanced look command |
| `GRAFFITI_SYSTEM_SPEC.md` | Environmental writing |
| `REMOTE_DETONATOR_SPEC.md` | Remote explosive detonation |
| `STICKY_GRENADE_SPEC.md` | Sticky grenade mechanics |

## Character & Display

| Spec | Description |
|------|-------------|
| `DESCRIPTIVE_STAT_SYSTEM_SPEC.md` | G.R.I.M. stat descriptors |
| `LONGDESC_SYSTEM_SPEC.md` | Character appearance generation |
| `DEATH_CURTAIN_SPEC.md` | Narrative death experience |
| `NATURAL_POSING_AND_PRONOUN_FIXES_SPEC.md` | Pronoun handling |
| `PRONOUN_DEEP_DIVE_IMPLEMENTATION_SPEC.md` | Pronoun system internals |
| `ORDINAL_NUMBERS_SPEC.md` | Ordinal number object display |
| `WEAPON_MESSAGE_CONVERSION_SPEC.md` | Weapon message migration plan |
| `EVMENU_PATTERNS_SPEC.md` | EvMenu usage patterns |

## Web & UI

| Spec | Description |
|------|-------------|
| `STYLING_SPEC.md` | Web client styling |
| `WEBCLIENT_SCREEN_SIZE_DETECTION_SPEC.md` | Responsive client layout |
| `WEB_CHARACTER_CREATION_ALIGNMENT.md` | Web/game character creation parity |
| `WEB_RESPAWN_CHARACTER_CREATION_SPEC.md` | Web respawn flow |
| `GMCP_PACKAGES_SPEC.md` | GMCP protocol packages |
| `TURNSTILE_INTEGRATION_SPEC.md` | Cloudflare Turnstile captcha |

## Forum Integration (Optional)

These only apply if running a Discourse forum alongside the game:

| Spec | Description |
|------|-------------|
| `FORUM_INTEGRATION_GUIDE.md` | Overview and decision guide |
| `DISCOURSE_INTEGRATION.md` | Step-by-step Discourse setup |
