# specs/

Design specifications for **shipped** game systems — the index below
describes how the game works today. Each entry is a running system
(deferred sub-features are noted inline within each spec).

Specs that are **not** shipped live in subfolders and are kept out of this
index:

- **`proposals/`** — 📋 designed, nothing built yet.
- **`roadmaps/`** — 🛣 forward build-plans layered on live systems (partial).
- **`archive/`** — 🗄 task complete or superseded; kept for context only.

Every spec in those folders carries a `> **Status:**` banner at the top.

---

## Combat

| Spec | Description |
|------|-------------|
| `COMBAT_SYSTEM.md` | High-level overview of the combat system (some listed features are aspirational — see banner) |
| `COMBAT_AUDIT_LOGGING_SPEC.md` | Single-sink combat/medical diagnostics: always-on audit file + gated Splattercast channel (`world/combat/debug.py`) |
| `COMBAT_MESSAGE_FORMAT_SPEC.md` | Three-perspective combat messaging format |
| `GRAPPLE_SYSTEM_SPEC.md` | Grappling, restraint, human-shield mechanics |

## Medical, Anatomy & Body

| Spec | Description |
|------|-------------|
| `HEALTH_AND_SUBSTANCE_SYSTEM_SPEC.md` | Canonical medical/trauma system: anatomy, organs, death/decapitation, substances |
| `CONDITION_CADENCE_SPEC.md` | Elapsed-time condition rates: per-minute rates, ticks as sampling, downtime cap (#501) |
| `ANATOMY_AUGMENTS_SPEC.md` | Per-character anatomy; augment install; the cybernetic tail; inorganic organs |
| `AUGMENT_ABILITIES_SPEC.md` | Toggleable cyberware; the chassis+module standard; reattachment; chrome severance |
| `SPECIES_AUTHORING.md` | How to add a species so combat/severance/medical/longdesc behave without renderer changes |
| `SUBSTANCES_AND_DELIVERY_SPEC.md` | Item → substance → delivery model; registry, tolerance/addiction |
| `CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC.md` | What body capacity actually gates: sight, movement, manipulation, and the chrome that restores them |

## Identity, Communication & Appearance

| Spec | Description |
|------|-------------|
| `IDENTITY_RECOGNITION_SPEC.md` | Sleeve-based identity, recognition memory, personas, disguise piercing |
| `EMOTE_POSE_SPEC.md` | Emote, pose, say/whisper/think with per-observer identity rendering |
| `LONGDESC_SYSTEM_SPEC.md` | Per-location body descriptions; pair-collapse; chrome rendering |
| `GRAMMAR_ENGINE_SPEC.md` | Pronoun/conjugation/article engine (`{they}`/`{their}` tokens) |
| `DEATH_CURTAIN_SPEC.md` | Narrative death animation + death-progression timer |
| `TRUST_AND_CONSENT_SPEC.md` | Trust/distrust gating for intimate actions — clothing, medical, frisk, follow/escort |
| `NPC_MEMORY_AND_IDENTITY_SPEC.md` | RAG memory for LLM NPCs: embedding records, similarity retrieval, salience decay |

## Items, Equipment & World

| Spec | Description |
|------|-------------|
| `BUILDING_PLAYBOOK.md` | 🧭 Living doctrine for building the city: the six criteria every build answers, settled grid/vertical/door/room law, the session ritual, and the ledger of the remaining city |
| `CLOTHING_SYSTEM_SPEC.md` | Clothing, coverage-based visibility, layering, dynamic styling |
| `MODULAR_ARMOR_SYSTEM_SPEC.md` | Armor stacking, plate carriers, tactical targeting |
| `SHOP_SYSTEM_SPEC.md` | Container-based shops, pricing, inventory (Phase 2 deferred — #302) |
| `GRAFFITI_SYSTEM_SPEC.md` | Spray-paint / solvent environmental writing |
| `NPC_POSTS_AND_REINCARNATION_SPEC.md` | Named NPCs as reconstructible blueprints: posts, watcher, successor, resleeving |
| `GIG_PROTOTYPE_BUTCHER_SPEC.md` | The first gig: corpse → condition-gated cuts → cooked dishes, with a closed till loop |

## Commands

| Spec | Description |
|------|-------------|
| `LOOK_COMMAND_SPEC.md` | Enhanced, combat-aware look |
| `THROW_COMMAND_SPEC.md` | Cross-room projectile throwing |
| `WREST_COMMAND_SPEC.md` | Taking held items by force (non-combat) |
| `JUMP_COMMAND_SPEC.md` | Inter-room jumping |
| `BUG_COMMAND_SPEC.md` | In-game bug reporting |
| `REMOTE_DETONATOR_SPEC.md` | Remote explosive detonation |
| `STICKY_GRENADE_SPEC.md` | Sticky grenade mechanics |
| `CHANNELED_ACTIONS_SPEC.md` | Multi-turn actions that can be interrupted — the channel/interrupt contract |

## Patterns, Web & UI

| Spec | Description |
|------|-------------|
| `NEW_PLAYER_EXPERIENCE_SPEC.md` | Connection → chargen → decant flow and the locked messaging conventions (frame, terminal wrap, TST dates, informing-not-telling, puppet lifecycle) |
| `EVMENU_PATTERNS_SPEC.md` | EvMenu text-input / multi-source-picker patterns |
| `STYLING_SPEC.md` | Web client / terminal-brutalist styling |
| `COLONY_MAPPING_SPEC.md` | The colony atlas: canonical map export + the live 3D render at `/atlas/` (Cycles-baked vertices, day/night, HUD, 'you are here') + the builder's sprite plate; §M3 player chart deferred inline |
| `WEBCLIENT_SCREEN_SIZE_DETECTION_SPEC.md` | Responsive client layout / screen-width detection |
| `WEB_CHARACTER_CREATION_ALIGNMENT.md` | Web/game character-creation parity |
| `WEB_RESPAWN_CHARACTER_CREATION_SPEC.md` | Web respawn flow |
| `TURNSTILE_INTEGRATION_SPEC.md` | Cloudflare Turnstile captcha on registration |

## Forum Integration (Optional)

Only applies if running a Discourse forum alongside the game:

| Spec | Description |
|------|-------------|
| `FORUM_INTEGRATION_GUIDE.md` | Overview and decision guide |
| `DISCOURSE_INTEGRATION.md` | Step-by-step Discourse setup |
