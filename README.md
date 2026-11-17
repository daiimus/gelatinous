# Gelatinous

A text-based multiplayer game built on the [Evennia](https://www.evennia.com/) MUD framework. Gelatinous implements a tactical turn-based combat system with proximity mechanics, grappling, medical trauma simulation, and messaging systems designed to prioritize storytelling.

**Live Instance**: [https://gel.monster](https://gel.monster)

## Overview

Gelatinous is a pre-alpha MUD (Multi-User Dungeon) that explores tactical combat design with a focus on narrative depth. The game features the G.R.I.M. system (Grit, Resonance, Intellect, Motorics) -- a four-attribute framework governing character capabilities in combat, social interactions, and skill resolution.

The current setting is a sci-fi offworld colony, though the codebase is designed to be setting-agnostic.

### G.R.I.M. Attribute System

| Attribute | Governs |
|-----------|---------|
| **Grit** | Physical toughness, endurance, raw strength |
| **Resonance** | Social awareness, empathy, interpersonal influence |
| **Intellect** | Mental acuity, tactical thinking, problem-solving |
| **Motorics** | Physical coordination, dexterity, reflexes |

These attributes drive contested rolls, skill checks, and combat resolution throughout the game.

### Core Features

- **Turn-Based Tactical Combat** -- Initiative-driven system with 6-second rounds
- **Proximity System** -- Melee/ranged positioning with movement commands (advance, retreat, charge, flee)
- **Grappling Mechanics** -- Multi-participant restraint system with contested rolls, dragging, and human shield functionality
- **Medical Simulation** -- Organ-level wound tracking, bleeding mechanics, pain management, bone anatomy, and recovery systems
- **Projectile Physics** -- Cross-room throwing with flight timing, trajectory calculation, and interception
- **Explosives** -- Grenade and explosive device systems with blast radius and shrapnel
- **Environmental Interaction** -- Trap rigging, graffiti system, crowd dynamics, and weather effects
- **Equipment Systems** -- Layered clothing with armor values, weapon wielding, and inventory consolidation
- **Shop System** -- Prototype-based shops with infinite/limited inventory and merchant NPCs
- **Death and Corpses** -- Death progression system with forensic corpses, decay mechanics, and curtain-of-death boundary
- **Object Interaction** -- Wrest command for contested item acquisition, frisk for searching
- **Consumption System** -- Eating, drinking, and substance effects
- **104 Weapon Message Templates** -- Three-perspective combat narration (attacker, victim, observer) per weapon type
- **GMCP WebSocket** -- Custom WebSocket handler speaking GMCP wire format for MUD client compatibility
- **Web Authentication** -- Email-based login, Discourse SSO integration, Cloudflare Turnstile CAPTCHA
- **Identity & Recognition** -- Sleeve-based physical identity with short descriptions, stranger perception, manual name assignment, and custom keyword catalog
- **Emote, Pose & Communication** -- Dot-pose engine, traditional emote with character references, identity-aware say/whisper, social templates, and perspective-transformed pronouns
- **Grammar Engine** -- Third-person verb conjugation, article selection (a/an), first-letter capitalization, and sdesc keyword validation
- **Natural Language Parsing** -- Ordinal number recognition and flexible command parsing
- **AI NPCs** -- NPCs driven by a language model at a configurable endpoint (`typeclasses/llm_npc.py`, `world/llm/`); whatever the model decides goes out as a command a player could type
- **NPC Souls** -- A deterministic simulation of NPC needs, schedules, jobs and posts, where a vacant post passes to a successor (`world/souls/`); a director dispatches NPCs to world events such as a crime (`world/director/`)
- **Radio** -- Handheld radios with `transmit`, `tune` and `toggle`; a powered radio tuned to the band hears the traffic, attributed by voice only
- **Stealth and Detection** -- `hide`, `sneak`, `search`, `steal` and `pickpocket`, resolved as contests
- **Cyberware and Surgery** -- Installed augments toggled with `/<ability>`, and surgery through `operate`, `incise`, `harvest`, `install` and `suture`
- **Bars, Food and Gigs** -- Bar counters with drink recipes and a mixing menu, cooked food, and the butcher gig that turns animal corpses into dishes
- **Housing and Insurance** -- One permanent rental cube per person, claimed at a rental terminal; a sleeve insurance policy, bought alive, pays for a return after death
- **Verticality** -- Jumping between rooms, falling through air cells (`world/gravity.py`), doors with biometric locks, and elevators
- **Trust and Consent** -- `trust` and `distrust` decide which third-party actions a conscious, unrestrained character accepts
- **Species** -- Human, synthetic humanoid, rat and robot bodies
- **Colony Atlas** -- A public 3D map of the colony at `/atlas/`

## Quick Start

**Play**: [https://gel.monster](https://gel.monster)

**Local Development**: Requires [Evennia](https://www.evennia.com/docs/latest/Setup/Installation.html). Standard `evennia migrate` and `evennia start` workflow. Combat and medical diagnostics go to `server/logs/combat_audit.log`. To mirror them in game, create a channel named Splattercast and set `SPLATTERCAST_LIVE = True`.

## Architecture

The codebase follows Evennia's standard structure with custom extensions for combat, medical, environmental, and web systems.

```
gelatinous/
├── commands/       # Game commands (see commands/README.md)
├── typeclasses/    # Game object definitions (see typeclasses/README.md)
├── world/          # Game systems, data and the test suite (see world/README.md)
├── server/         # Evennia server configuration (see server/README.md)
├── web/            # Website, web client and forum theme (see web/README.md)
├── scripts/        # Offline tools: atlas, planning, brand, numbered builds (see each folder's README)
├── specs/          # Design specifications (see specs/README.md)
├── tests/          # GMCP websocket wire-format tests
└── AGENTS.md       # Agent operational reference: conventions, workflow, file map
```

### Key Systems

**Combat** -- Turn-based Script-driven handler with initiative order, opposed rolls, and 6-second rounds. The combat system was decomposed from monolithic files into focused modules: `handler.py` orchestrates turns, `attack.py` resolves hits, `actions.py` processes queued actions, `movement_resolution.py` handles tactical movement, `proximity.py` manages melee/ranged positioning, and `grappling.py` handles restraint mechanics. All constants are centralized in `constants.py` with no magic strings.

**Medical** -- Hospital-grade anatomical simulation with individual bone tracking (humerus, femur, tibia, metacarpals), organ systems with HP and functionality, body capacities (consciousness, blood pumping, breathing, manipulation), wound severity tracking, bleeding accumulation, pain effects, and death from organ failure or blood loss.

**Messages** -- 104 weapon-specific template files with three-perspective narration (attacker, victim, observer) and dynamic content loading. Messages are organized by combat phase (initiate, hit, miss, kill) with multiple random variants per phase.

**Death and Corpses** -- Death progression system managing unconsciousness, death state, and corpse creation with forensic data preservation. Corpses use just-in-time decay calculations. The curtain-of-death exit provides a narrative boundary for the death experience.

**Character Architecture** -- The Character typeclass uses a mixin decomposition pattern: `armor_mixin.py` handles armor calculation, `clothing_mixin.py` manages wear/remove logic, and `appearance_mixin.py` builds longdesc from wounds, clothing, and equipment. This keeps `characters.py` focused on core G.R.I.M. stats and combat integration.

**Shops** -- A `ShopContainer` holds the wares, with infinite or limited stock and a price markup. Players `buy <item> from <container>`, and whoever stands the shop's post sells from it too (`world/shop/service.py`).

**GMCP WebSocket** -- Custom WebSocket protocol handler (`server/conf/gmcp_websocket.py`) that speaks GMCP wire format when clients negotiate the `gmcp.mudstandards.org` subprotocol, with fallback to Evennia's standard JSON protocol for browser clients. Sends game text as BINARY frames with ANSI escape codes and OOB data as TEXT frames.

**Web and Authentication** -- Email-based login system replacing Evennia's default username auth. Includes Discourse SSO for forum integration, Cloudflare Turnstile CAPTCHA for registration, and a security middleware chain (CSP headers, X-Frame-Options, SecurityMiddleware).

**Identity & Recognition** -- Sleeve-based physical identity system where characters appear as short descriptions ("a lanky man in a leather jacket") to strangers. Players name the people they know with `remember <target> as <name>`. Short descriptions are composed from auto-derived physical descriptors (height x build table), player-selected keywords (curated list or custom words), and auto-derived distinguishing features (wielded weapons, clothing, hair). Recognition memory is stored per `sleeve_uid` for flash-clone compatibility. `describe keyword <word>` sets the sdesc keyword; a custom keyword is logged as a `KeywordEvent` record that staff review with `@keywords`. Identity-aware `get_display_name()` renders assigned names for recognized characters and sdescs for strangers across all game output.

**Communication** -- Identity-aware emote, pose, and communication system. Dot-pose (`.emote`) provides a full tokenizer with verb markers, pronoun tokens, speech blocks, and character references that resolve to identity-appropriate names per observer. Traditional emote supports character reference resolution. Say and whisper commands render speaker identity per-observer. Social templates provide room-wide narrative actions. The grammar engine handles third-person verb conjugation, a/an article selection, and first-letter capitalization.

### Design Principles

- **Roleplay-First Combat** -- Combat enhances narrative rather than dominating it. Auto-yielding mechanics default to non-violent resolution. Tie-breaking favors the defender.
- **Modular Architecture** -- Each system aspect lives in focused modules with clear responsibilities. Loose coupling through well-defined interfaces.
- **Evennia-Native** -- Leverages Evennia's typeclass system, Script handlers, Command patterns, and attribute storage. No reinvention of platform capabilities.
- **Constants Centralization** -- No magic strings. All combat and medical constants live in dedicated `constants.py` files.
- **Setting-Agnostic Core** -- The G.R.I.M. system and combat mechanics are designed to work across settings. The current sci-fi colony is one implementation.

## Project Status

**Current Phase**: Pre-Alpha Development

### Implemented Systems

- Turn-based combat with initiative
- G.R.I.M. attribute system
- Proximity and tactical positioning
- Multi-participant grappling with contests
- Medical trauma with organ-level wound tracking
- Cross-room throwing mechanics
- Explosive/grenade systems
- Equipment and layered clothing with armor
- Shop system with prototype-based inventory
- Death progression and corpse forensics
- Object wresting and contested acquisition
- Consumption system (eating/drinking)
- Character creation menu system
- 104 weapon-specific combat message templates
- Environmental systems (graffiti, crowds, weather)
- GMCP WebSocket protocol for MUD clients
- Email-based authentication with Discourse SSO
- Cloudflare Turnstile CAPTCHA integration
- Security middleware (CSP, clickjacking protection)
- Identity & Recognition system (Phases 1-3 complete)
- Disguise: `appear`, personas, and seeing through a disguise
- Sleeve-based physical identity with short descriptions
- Manual name assignment and recognition memory
- Custom sdesc keywords with admin catalog
- Identity-aware target resolution (assigned names and sdescs)
- Dot-pose engine with verb markers, pronouns, speech blocks, and character references
- Traditional emote with character reference resolution
- Identity-aware say and whisper commands
- Social template system for narrative actions
- Grammar engine (verb conjugation, articles, capitalization)
- Over ten thousand automated tests

### In Development

- Identity Phase 4: Cybernetics (cyberbrain, digital ID, memory backup)
- Identity Phase 5: Resonance mechanics (memory decay, auto-recognition, perception checks)
- Additional weapon types and combat moves
- Expanded medical conditions and treatments
- Economic systems and trade
- Quest and narrative frameworks
- Character progression systems

See `specs/README.md` for the index of shipped specifications; proposals, roadmaps and archived specs are in its subfolders.

## Documentation

- **[AGENTS.md](AGENTS.md)** -- Agent operational reference: project conventions, deploy workflow, and a file-to-concept map. Architecture details live in `specs/`.
- **[specs/](specs/)** -- Design specifications (index in `specs/README.md`) covering combat, medical, identity, communication, grappling, proximity, shops, explosives, web integration, and planned features.
- **[specs/IDENTITY_RECOGNITION_SPEC.md](specs/IDENTITY_RECOGNITION_SPEC.md)** -- Sleeve-based identity and recognition system design.
- **[specs/EMOTE_POSE_SPEC.md](specs/EMOTE_POSE_SPEC.md)** -- Emote, pose, and communication system with identity integration.

## Contributing

Personal project in active development. Open an issue or visit the game to discuss contributions.

## Built With

[Evennia](https://www.evennia.com/) -- Python MUD/MU* framework | [Documentation](https://www.evennia.com/docs/latest/) | [GitHub](https://github.com/evennia/evennia)
