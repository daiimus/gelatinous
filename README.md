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
- **96 Weapon Message Templates** -- Three-perspective combat narration (attacker, victim, observer) per weapon type
- **GMCP WebSocket** -- Custom WebSocket handler speaking GMCP wire format for MUD client compatibility
- **Web Authentication** -- Email-based login, Discourse SSO integration, Cloudflare Turnstile CAPTCHA
- **Security Middleware** -- CSP headers, X-Frame-Options, SecurityMiddleware chain
- **Natural Language Parsing** -- Ordinal number recognition and flexible command parsing

## Quick Start

**Play**: [https://gel.monster](https://gel.monster)

**Local Development**: Requires [Evennia](https://www.evennia.com/docs/latest/Setup/Installation.html). Standard `evennia migrate` and `evennia start` workflow. The game uses a debug channel called Splattercast which requires manual creation at this time.

## Architecture

The codebase follows Evennia's standard structure with custom extensions for combat, medical, environmental, and web systems.

```
gelatinous/
├── commands/                  # Game commands
│   ├── combat/                # Combat commands (modular)
│   │   ├── cmdset_combat.py       # Combat command set definition
│   │   ├── core_actions.py        # CmdAttack, CmdStop
│   │   ├── movement.py            # CmdFlee, CmdRetreat, CmdAdvance, CmdCharge
│   │   ├── jump.py                # CmdJump (inter-room jumping)
│   │   └── special_actions.py     # CmdGrapple, CmdEscape, CmdRelease, CmdDisarm, CmdAim
│   ├── charcreate.py              # Character creation menu
│   ├── CmdAdmin.py                # Administrative commands
│   ├── CmdArmor.py                # Armor inspection and management
│   ├── CmdBug.py                  # In-game bug reporting
│   ├── CmdCharacter.py            # Character sheet and stats
│   ├── CmdClothing.py             # Clothing and wearing
│   ├── CmdConsumption.py          # Eating and drinking
│   ├── CmdExplosives.py           # Grenade and explosive commands
│   ├── CmdFixCharacterOwnership.py # Admin character ownership repair
│   ├── CmdGraffiti.py             # Environmental writing
│   ├── CmdInventory.py            # Wield, get, drop, give, wrest, frisk
│   ├── CmdMedical.py              # Medical status and treatment commands
│   ├── CmdMedicalItems.py         # Medical item management
│   ├── CmdSpawnMob.py             # NPC spawning (builder+)
│   ├── CmdThrow.py                # Projectile throwing
│   ├── default_cmdsets.py         # Command set definitions
│   ├── explosion_utils.py         # Shared explosion/blast logic
│   ├── shop.py                    # Shop interaction commands
│   └── unloggedin_email.py        # Email-based login commands
├── typeclasses/               # Game object definitions
│   ├── accounts.py                # Player accounts (email login, multi-character)
│   ├── characters.py              # Character typeclass with G.R.I.M. stats
│   ├── appearance_mixin.py        # Character appearance and longdesc
│   ├── armor_mixin.py             # Armor calculation and coverage
│   ├── clothing_mixin.py          # Clothing wear/remove logic
│   ├── corpse.py                  # Forensic corpse with decay
│   ├── curtain_of_death.py        # Death boundary exit
│   ├── death_progression.py       # Death state management
│   ├── exits.py                   # Custom exit functionality
│   ├── items.py                   # Weapons, armor, consumables, tools
│   ├── objects.py                 # Base objects, graffiti, blood pools
│   ├── rooms.py                   # Room features and environmental systems
│   └── shopkeeper.py              # Shop containers and merchants
├── world/                     # Game systems and data
│   ├── combat/                    # Core combat system
│   │   ├── constants.py               # All combat constants
│   │   ├── handler.py                 # CombatHandler script (turn loop)
│   │   ├── attack.py                  # Attack resolution logic
│   │   ├── actions.py                 # Combat action processing
│   │   ├── movement_resolution.py     # Movement action resolution
│   │   ├── proximity.py               # Tactical positioning
│   │   ├── grappling.py              # Restraint mechanics
│   │   ├── utils.py                   # Combat utility functions
│   │   ├── dice.py                    # Dice rolling and stat checks
│   │   ├── debug.py                   # Debug logging to Splattercast
│   │   ├── explosives.py             # Explosion/blast radius logic
│   │   └── messages/                  # 96 weapon-specific message templates
│   ├── medical/                   # Medical trauma simulation
│   │   ├── core.py                    # Organs, conditions, medical state
│   │   ├── conditions.py             # Status effects and wound types
│   │   ├── constants.py               # Medical system constants
│   │   ├── script.py                  # Automated bleeding/healing processes
│   │   ├── utils.py                   # Medical helper functions
│   │   └── wounds/                    # Wound descriptions and anatomy
│   ├── crowd/                     # Crowd simulation
│   │   ├── crowd_system.py            # Crowd generation and behavior
│   │   └── crowd_messages.py          # Crowd atmospheric messages
│   ├── weather/                   # Weather and time systems
│   │   ├── weather_system.py          # Weather state management
│   │   ├── weather_messages.py        # Weather atmospheric messages
│   │   └── time_system.py            # In-game time tracking
│   ├── shop/                      # Shop system
│   │   └── utils.py                   # Pricing and inventory logic
│   ├── utils/                     # Shared utilities
│   │   └── boxtable.py               # Table formatting
│   ├── namebank.py                # Name generation (first/last names)
│   └── prototypes.py             # Object prototypes (weapons, items, NPCs)
├── server/                    # Server configuration
│   └── conf/
│       ├── settings.py                # Game settings and Django config
│       ├── gmcp_websocket.py          # GMCP-over-WebSocket protocol handler
│       ├── connection_screens.py      # Login screen
│       ├── mssp.py                    # MUD Server Status Protocol metadata
│       └── [Evennia hook modules]     # at_server_startstop, lockfuncs, etc.
├── web/                       # Web interface
│   ├── website/views/             # Django views
│   │   ├── accounts.py                # Registration with Turnstile CAPTCHA
│   │   ├── characters.py             # Character management views
│   │   ├── discourse_sso.py          # Discourse SSO (DiscourseConnect)
│   │   ├── discourse_session_sync.py  # Discourse session synchronization
│   │   ├── channels.py               # Channel views
│   │   └── header_only.py            # Iframe-embeddable header
│   ├── utils/                     # Web utilities
│   │   ├── auth_backends.py           # Email authentication backend
│   │   └── security_middleware.py     # CSP and security headers
│   └── templates/                 # HTML templates
├── tests/                     # Test suite
│   └── test_gmcp_websocket.py     # GMCP wire format validation
├── specs/                     # Design specifications (36 documents)
└── AGENTS.md                  # Agent reference for combat system architecture
```

### Key Systems

**Combat** -- Turn-based Script-driven handler with initiative order, opposed rolls, and 6-second rounds. The combat system was decomposed from monolithic files into focused modules: `handler.py` orchestrates turns, `attack.py` resolves hits, `actions.py` processes queued actions, `movement_resolution.py` handles tactical movement, `proximity.py` manages melee/ranged positioning, and `grappling.py` handles restraint mechanics. All constants are centralized in `constants.py` with no magic strings.

**Medical** -- Hospital-grade anatomical simulation with individual bone tracking (humerus, femur, tibia, metacarpals), organ systems with HP and functionality, body capacities (consciousness, blood pumping, breathing, manipulation), wound severity tracking, bleeding accumulation, pain effects, and death from organ failure or blood loss.

**Messages** -- 96 weapon-specific template files with three-perspective narration (attacker, victim, observer) and dynamic content loading. Messages are organized by combat phase (initiate, hit, miss, kill) with multiple random variants per phase.

**Death and Corpses** -- Death progression system managing unconsciousness, death state, and corpse creation with forensic data preservation. Corpses use just-in-time decay calculations. The curtain-of-death exit provides a narrative boundary for the death experience.

**Character Architecture** -- The Character typeclass uses a mixin decomposition pattern: `armor_mixin.py` handles armor calculation, `clothing_mixin.py` manages wear/remove logic, and `appearance_mixin.py` builds longdesc from wounds, clothing, and equipment. This keeps `characters.py` focused on core G.R.I.M. stats and combat integration.

**Shops** -- Prototype-based shop system supporting infinite/limited inventory, dynamic pricing with markup, and merchant NPC integration.

**GMCP WebSocket** -- Custom WebSocket protocol handler (`server/conf/gmcp_websocket.py`) that speaks GMCP wire format when clients negotiate the `gmcp.mudstandards.org` subprotocol, with fallback to Evennia's standard JSON protocol for browser clients. Sends game text as BINARY frames with ANSI escape codes and OOB data as TEXT frames.

**Web and Authentication** -- Email-based login system replacing Evennia's default username auth. Includes Discourse SSO for forum integration, Cloudflare Turnstile CAPTCHA for registration, and a security middleware chain (CSP headers, X-Frame-Options, SecurityMiddleware).

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
- 96 weapon-specific combat message templates
- Environmental systems (graffiti, crowds, weather)
- GMCP WebSocket protocol for MUD clients
- Email-based authentication with Discourse SSO
- Cloudflare Turnstile CAPTCHA integration
- Security middleware (CSP, clickjacking protection)

### In Development

- Additional weapon types and combat moves
- Expanded medical conditions and treatments
- Economic systems and trade
- Quest and narrative frameworks
- Character progression systems

See `specs/` for 36 detailed specifications covering implemented and planned features.

## Documentation

- **[AGENTS.md](AGENTS.md)** -- Combat system architecture, patterns, and agent reference. The most comprehensive technical document in the project.
- **[specs/](specs/)** -- 36 design specifications covering combat, medical, grappling, proximity, shops, explosives, web integration, and planned features.

## Contributing

Personal project in active development. Open an issue or visit the game to discuss contributions.

## Built With

[Evennia](https://www.evennia.com/) -- Python MUD/MU* framework | [Documentation](https://www.evennia.com/docs/latest/) | [GitHub](https://github.com/evennia/evennia)
