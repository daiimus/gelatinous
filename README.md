# Gelatinous

A text-based multiplayer game built on the [Evennia](https://www.evennia.com/) MUD framework. Gelatinous implements a tactical turn-based combat system with proximity mechanics, grappling, medical trauma simulation, and messaging systems designed to prioritize storytelling.

**Live Instance**: [https://gel.monster](https://gel.monster)

## Overview

Gelatinous is a pre-alpha MUD (Multi-User Dungeon) that explores tactical combat design with a focus on narrative depth. The game features the G.R.I.M. system (Grit, Resonance, Intellect, Motorics) - a four-attribute framework governing character capabilities in combat, social interactions, and skill resolution.

### Core Features

- **Turn-Based Tactical Combat**: Initiative-driven combat system with 6-second rounds
- **Proximity System**: Melee/ranged positioning with tactical movement commands (advance, retreat, charge, flee)
- **Grappling Mechanics**: Multi-participant restraint system with contested rolls, dragging, and human shield functionality
- **Medical Simulation**: Wound tracking, bleeding mechanics, pain management, and recovery systems
- **Projectile Physics**: Cross-room throwing with flight timing, trajectory calculation, and interception mechanics
- **Environmental Interaction**: Trap rigging, graffiti system, crowd dynamics, and weather effects
- **Equipment Systems**: Layered clothing with armor values, weapon wielding, and inventory consolidation
- **Shop System**: Prototype-based shops with infinite/limited inventory and merchant NPCs
- **Death & Corpses**: Death progression system with forensic corpses and decay mechanics
- **Object Interaction**: Wrest command for contested item acquisition, frisk for searching
- **Consumption System**: Eating, drinking, and substance effects
- **Bug Reporting**: In-game bug reporting command
- **Natural Language Processing**: Ordinal number recognition and flexible command parsing
- **Atmospheric Messaging**: 95+ weapon-specific message templates with three-perspective combat narration

### G.R.I.M. Attribute System

- **Grit**: Physical toughness, endurance, and raw strength
- **Resonance**: Social awareness, empathy, and interpersonal skills
- **Intellect**: Mental acuity, tactical thinking, and problem-solving
- **Motorics**: Physical coordination, dexterity, and reflexes

These attributes drive contested rolls, skill checks, and combat resolution throughout the game.

## Quick Start

**Connect**: [https://gel.monster](https://gel.monster)

**Local Development**: Requires [Evennia](https://www.evennia.com/docs/latest/Setup/Installation.html). Standard `evennia migrate` and `evennia start` workflow. (Gelatinous does currently make extensive use of a channel called Splattercast which requires manual creation at this time.)

## For Developers

### Architecture Overview

The codebase follows Evennia's standard structure with custom extensions for combat, medical, and environmental systems:

```
gelatinous/
├── commands/          # Command implementations
│   ├── combat/       # Combat commands (attack, grapple, flee, aim, etc.)
│   ├── CmdInventory.py   # Wield, get, drop, give, wrest, frisk
│   ├── CmdCharacter.py   # Character sheet and stats
│   ├── CmdThrow.py       # Projectile throwing
│   ├── CmdMedical.py     # Medical treatment commands
│   ├── CmdMedicalItems.py # Medical item management
│   ├── CmdClothing.py    # Clothing and armor
│   ├── CmdArmor.py       # Armor-specific commands
│   ├── CmdConsumption.py # Eating and drinking
│   ├── CmdGraffiti.py    # Environmental writing
│   ├── CmdSpawnMob.py    # NPC spawning (admin)
│   ├── CmdBug.py         # Bug reporting
│   ├── shop.py           # Shop interaction commands
│   └── charcreate.py     # Character creation menu
├── typeclasses/      # Game object definitions
│   ├── objects.py         # Base object with ordinal number support
│   ├── characters.py      # Character typeclass with G.R.I.M. stats
│   ├── items.py           # Weapons, armor, consumables
│   ├── rooms.py           # Room features and environmental systems
│   ├── corpse.py          # Corpse with forensic data and decay
│   ├── shopkeeper.py      # Shop containers and merchants
│   ├── death_progression.py # Death state management
│   └── exits.py           # Custom exit functionality
├── world/            # Game systems and handlers
│   ├── combat/       # Combat system modules
│   │   ├── handler.py     # CombatHandler script
│   │   ├── constants.py   # System constants
│   │   ├── messages/      # 95+ weapon-specific message templates
│   │   ├── proximity.py   # Tactical positioning
│   │   ├── grappling.py   # Restraint mechanics
│   │   └── utils.py       # Utility functions
│   ├── medical/      # Medical trauma simulation
│   │   ├── core.py        # Medical state management
│   │   ├── conditions.py  # Status effects and wounds
│   │   ├── script.py      # Automated processes (bleeding, healing)
│   │   ├── constants.py   # Medical system constants
│   │   └── wounds/        # Wound type definitions
│   ├── shop/         # Shop system
│   │   └── utils.py       # Shop pricing and inventory
│   ├── utils/        # Shared utilities
│   │   └── boxtable.py    # Table formatting
│   ├── crowd/        # Crowd simulation
│   └── weather/      # Weather and environmental effects
├── server/           # Evennia configuration
│   └── conf/         # Game settings
├── specs/            # Design documents and specifications
└── docs/             # Project documentation
```

### Key Systems

**Combat**: Turn-based Script-driven handler with initiative order, opposed rolls, and 6-second rounds. See [`AGENTS.md`](AGENTS.md) for comprehensive architecture.

**Proximity**: Tactical positioning distinguishing melee/ranged engagement with movement commands (advance, retreat, charge, flee).

**Grappling**: Multi-participant restraint with contested rolls, dragging, takeover mechanics, and human shield functionality.

**Medical**: Wound severity tracking, bleeding accumulation, pain effects, and treatment requirements.

**Messages**: 95+ weapon-specific templates with three-perspective narration (attacker, victim, observer) and dynamic content loading.

**Death & Corpses**: Death progression system managing unconsciousness, death state, and corpse creation with forensic data preservation and just-in-time decay calculations.

**Shops**: Prototype-based shop system supporting infinite/limited inventory, dynamic pricing with markup, and merchant NPC integration.

## Documentation

- **[AGENTS.md](AGENTS.md)** - Combat system architecture and patterns
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Project structure overview
- **[PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)** - Design philosophy
- **[specs/](specs/)** - 20+ detailed specifications for implemented and planned features

## Project Status

**Current Phase**: Pre-Alpha Development

### Implemented Systems

- ✅ Turn-based combat with initiative
- ✅ G.R.I.M. attribute system
- ✅ Proximity and tactical positioning
- ✅ Multi-participant grappling with contests
- ✅ Medical trauma and wound tracking
- ✅ Cross-room throwing mechanics
- ✅ Equipment and clothing systems with armor
- ✅ Shop system with prototype-based inventory
- ✅ Death progression and corpse forensics
- ✅ Object wresting and contested acquisition
- ✅ Consumption system (eating/drinking)
- ✅ Medical item management system
- ✅ Bug reporting system
- ✅ Natural language command parsing
- ✅ Atmospheric combat messaging (95+ templates)
- ✅ Environmental systems (graffiti, crowds, weather)
- ✅ Character creation menu system

### In Development

- 🚧 Additional weapon types and combat moves
- 🚧 Expanded medical conditions and treatments
- 🚧 Economic systems and trade
- 🚧 Quest and narrative frameworks
- 🚧 Character progression systems

### Planned Features

See `specs/` directory for 20+ detailed specifications of planned expansions including advanced environmental interactions, crafting systems, social mechanics, and faction systems.

## Contributing

Personal project in active development. Open an issue or visit the game to discuss contributions.

## Built With

[Evennia](https://www.evennia.com/) - Python MUD/MU* framework | [Documentation](https://www.evennia.com/docs/latest/) | [GitHub](https://github.com/evennia/evennia)




