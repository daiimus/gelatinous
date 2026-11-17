# world/

Game systems, data, and logic that aren't commands or typeclasses.

## Subsystems

### combat/
Core combat system. Turn-based handler with initiative, proximity, grappling, and 104 weapon-specific message templates. Decomposed into focused modules: `handler.py` (turn loop), `attack.py` (hit resolution), `actions.py` (action processing), `movement_resolution.py` (tactical movement), `proximity.py` (melee/ranged positioning), `grappling.py` (restraint mechanics), `utils.py`, `dice.py`, `debug.py`, `explosives.py`, `throwing.py` (thrown-object flight and landing), `capacity.py` (sight's effect on hit math), `weapon_choice.py` (which held weapon a body fights with), and `constants.py`. See [specs/COMBAT_SYSTEM.md](../specs/COMBAT_SYSTEM.md) for comprehensive architecture documentation.

### medical/
Medical trauma simulation with organ-level anatomy. Individual bone tracking, organ HP and functionality, body capacities (consciousness, blood pumping, breathing, manipulation), wound types, bleeding, pain, and death conditions. See `medical/README.md` for details.

### weather/
Weather state management and atmospheric messaging. `weather_system.py` handles weather transitions, `weather_messages.py` contains sensory descriptions per weather type and time of day, and `time_system.py` tracks in-game time.

### crowd/
Crowd simulation system. `crowd_system.py` works out a room's crowd level, picks the crowd lines a looker sees, and decides whether the crowd hides figures; `crowd_messages.py` provides atmospheric crowd descriptions.

### shop/
Shop pricing and inventory logic. `utils.py` reads prototype values, prices with markup, formats currency and moves tokens; `service.py` is the selling a shop's post does, for whoever stands it.

### tests/
The game's test suite, covering every system. Tests run inside the game's container: `evennia test --settings settings.py world.tests.<module>` (see `AGENTS.md`).

### utils/
Shared utilities. `boxtable.py` provides table formatting for in-game displays.

### anatomy/
Species anatomy and body-part display data. `species.py` names body parts by species (human, synthetic humanoid, rat, robot); `organs.py` and `severed_parts.py` hold organ and severed-part descriptions.

### director/
The deterministic world-simulation engine that moves NPCs and dispatches them to world events (crime, security, couriers, routines). See `specs/proposals/NPC_DISPATCH_AND_SIMULATION_SPEC.md`.

### llm/
The language-model layer for AI NPCs. `client.py` makes the model call, `prompt.py` builds the prompt and parses the reply, `memory.py` is each NPC's long-term memory, `detached.py` runs slow calls off Evennia's worker pool, and `decision_log.py` is the opt-in log of raw and rendered turns.

### migrations/
Django migrations for `models.py`.

### mob_flavor/
Random short descriptions, longdescs and place strings for spawned NPCs, per species.

### npcs/
`blueprints.py`: each hand-built named NPC as a recipe the game can rebuild them from.

### souls/
Deterministic NPC needs, goals and jobs. `engine.py` runs the heartbeat, `posts.py` handles posts and succession, `economy.py` the colony treasury and wages, and `audit.py` writes the souls audit log.

### spatial/
The (x, y, z) coordinates laid over the world (`coordinates.py`) and pathfinding over the real exits (`pathfind.py`).

### substances/
The substance registry and effect pipeline (`registry.py`).

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
| `access.py` | Biometric access grants: a lock checks the presenter's sleeve against its grant file |
| `admin.py` | Django admin registration for the `world` models |
| `apps.py` | Django app configuration for `world` |
| `atlas.py` | Builds the colony atlas page (`build_atlas3d_html`) for the website and the offline generator |
| `audit_guard.py` | `under_test()`: tells the audit logs that a test run is driving the process |
| `bar.py` | Bars and recipes engine: ingredients, mixing, drinks |
| `butchery.py` | The butcher gig's core: breaking a carcass into cuts |
| `channeled.py` | Channeled actions: timed acts that an interruption cuts short |
| `client_address.py` | The client address a login may trust, and the key login throttling uses |
| `clinic.py` | Service at a clinic: what the doctor's post does |
| `consent.py` | Trust and consent: whether an actor may do a thing to a target |
| `consumables.py` | The shared use-count helper for consumable items |
| `death_records.py` | Death records: the out-of-character tombstone kept on the account |
| `food.py` | The food layer: food ingredients and dish recipes |
| `forensics.py` | The forensic recognition engine behind `inspect` |
| `fuzzy.py` | Narrow fuzzy matching of a phrase against a short list of real candidates |
| `gametime.py` | The colony clock: the one source of the game's hour and date |
| `gravity.py` | Gravity: what happens to anything in an air cell that cannot stay up |
| `imprint.py` | The imprint: what a person is as of their last backup, used by every resleeve |
| `insurance.py` | Sleeve insurance: a personal policy, bought alive, spent by a return |
| `manifest.py` | The slowboat manifest: each colonist's vessel, department and rating before planetfall |
| `mapping.py` | The colony map export (`export_map`) |
| `models.py` | The one custom Django model, `KeywordEvent` (the custom keyword log) |
| `movement_coupling.py` | `follow` and `escort` movement coupling |
| `ownership.py` | Who owns a body: the check to make before deleting one |
| `perception.py` | Which senses a looker currently receives |
| `radio.py` | Radio: transmissions heard on a powered radio tuned to the band |
| `rental.py` | Cube rental: the one permanent residence every person may claim |
| `service.py` | Service at a post: what each job does, keyed by the job's name |
| `smoke.py` | Cigarette, pack and lighter helpers and message banks |
| `speech.py` | Speech shared by `say`, `to` and pose/emote |
| `stealth.py` | Stealth and detection: the contest engine and graded awareness |
| `style.py` | Style motifs for garments and for how a person dresses |
| `voice.py` | Voice identity: recognising people by their voice |
| `wsis.py` | The world signal bus (WSIS P0) |
