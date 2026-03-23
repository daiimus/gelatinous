# world/

Game systems, data, and logic that aren't commands or typeclasses.

## Subsystems

### combat/
Core combat system. Turn-based handler with initiative, proximity, grappling, and 96 weapon-specific message templates. Decomposed into focused modules: `handler.py` (turn loop), `attack.py` (hit resolution), `actions.py` (action processing), `movement_resolution.py` (tactical movement), `proximity.py` (melee/ranged positioning), `grappling.py` (restraint mechanics), `utils.py`, `dice.py`, `debug.py`, `explosives.py`, and `constants.py`. See [AGENTS.md](../AGENTS.md) for comprehensive architecture documentation.

### medical/
Medical trauma simulation with organ-level anatomy. Individual bone tracking, organ HP and functionality, body capacities (consciousness, blood pumping, breathing, manipulation), wound types, bleeding, pain, and death conditions. See `medical/README.md` for details.

### weather/
Weather state management and atmospheric messaging. `weather_system.py` handles weather transitions, `weather_messages.py` contains sensory descriptions per weather type and time of day, and `time_system.py` tracks in-game time.

### crowd/
Crowd simulation system. `crowd_system.py` generates ambient NPCs for populated areas, `crowd_messages.py` provides atmospheric crowd descriptions.

### shop/
Shop pricing and inventory logic. `utils.py` handles markup calculation, prototype-based inventory, and stock management.

### tests/
Test suite for identity, emote, and communication systems. Tests run via `evennia test world.tests.<module>`.

### utils/
Shared utilities. `boxtable.py` provides table formatting for in-game displays.

## Top-Level Files

| File | Description |
|------|-------------|
| `emote.py` | Dot-pose and emote tokenizer/renderer with 5 token types (Text, Verb, Pronoun, Speech, CharRef) |
| `emote_templates.py` | Social template commands for room-wide narrative actions |
| `grammar.py` | Grammar engine: third-person verb conjugation, a/an articles, capitalization, keyword lists |
| `identity.py` | Identity system core: sdescs, recognition memory, keyword validation, custom keyword catalog |
| `identity_utils.py` | Identity message helper (`msg_room_identity` for observer-specific character names) |
| `namebank.py` | First and last name lists for NPC generation |
| `prototypes.py` | Object prototypes for weapons, items, and NPCs |
| `search.py` | Identity-aware target resolution: assigned names, sdescs, ordinals, word-boundary matching |
| `help_entries.py` | Custom help system entries |
| `batch_cmds.ev` | Batch command definitions for world building |
