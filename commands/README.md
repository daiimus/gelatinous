# commands/

Game commands organized by functionality. Each module implements one or more Evennia `Command` subclasses.

## Command Modules

| Module | Description |
|--------|-------------|
| `combat/` | Combat command subpackage (attack, movement, grapple, aim, etc.) |
| `charcreate.py` | EvMenu-based character creation flow |
| `CmdAdmin.py` | Administrative and builder commands (`@keywords` custom keyword catalog) |
| `CmdArmor.py` | Armor inspection and coverage display |
| `CmdBreach.py` | `sabotage` of breachable infrastructure (radio masts), and the structure branch of `repair` |
| `CmdBug.py` | In-game bug reporting |
| `CmdBuildTools.py` | Builder tools: `@room` (a room's whole profile), `@building` (audit a structure), `@airfill` (generate sky cells) |
| `CmdCharacter.py` | Character sheet (`@stats`), `describe` (longdesc and sdesc keyword), `@voice`, `@skintone`, recognition (`remember`, `forget`, `recall`, `memory`), disguise (`appear`, `stop appearing`, `personas`, `persona`), and `@look_place` / `@temp_place` |
| `CmdClothing.py` | Wearing and removing clothing |
| `CmdCommunication.py` | Identity-aware say, whisper, emote, and dot-pose commands |
| `CmdConsumption.py` | Eating and drinking |
| `CmdCoordSeed.py` | `@coordseed`: give rooms (x, y, z) coordinates by walking exits out from the pinned origin room |
| `CmdCyberware.py` | The cyberware dispatcher: `/` lists installed cyberware, `/<ability>` toggles one |
| `CmdDoors.py` | Door verbs: `open`, `close`, `lock`, `unlock`, `knock`, and `@door` for builders |
| `CmdExplosives.py` | Grenade and explosive device commands |
| `CmdFollow.py` | `follow` and `escort`, and their `stop` forms |
| `CmdFurniture.py` | Posture on furniture: `sit`, `lie`, `stand` |
| `CmdGraffiti.py` | Spray-painting and environmental writing |
| `CmdInsure.py` | `@insure`: a standing sleeve policy for staff and play testing |
| `CmdInventory.py` | Inventory management: wield, get, drop, give, wrest, frisk |
| `CmdLook.py` | `look`, reaching into the room the looker is aiming at |
| `CmdMedical.py` | Medical status and diagnostic commands |
| `CmdOperate.py` | `operate`: the charting menu over the surgical procedure verbs |
| `CmdPatrol.py` | `@patrol`: post an NPC to a base and put it on a beat |
| `CmdPin.py` | `@pin` / `@unpin`: freeze a soul in time |
| `CmdRadio.py` | Device comms: `transmit`, `tune`, `toggle` (receiving needs no command) |
| `CmdSmoke.py` | `light`, `smoke`, `snuff` |
| `CmdSoul.py` | `@soul`: the souls-engine diagnostic |
| `CmdSpawnMob.py` | `@spawnmob`: spawn a whole, pinned person (human or synth) or a rat or robot body; `/secbot` for a security unit (builder+) |
| `CmdStealth.py` | `hide`, `unhide`, `sneak`, `search` |
| `CmdSurgical.py` | Surgical procedures: `incise`, `harvest`, `install`, `suture` |
| `CmdTheft.py` | `steal`, `pickpocket` |
| `CmdThrow.py` | Cross-room projectile throwing |
| `CmdTrust.py` | `trust` / `distrust`: consent grants |
| `_identity_targeting.py` | Helpers that resolve a character target through identity recognition (no commands) |
| `bar_menu.py` | The `use <bar>` mixing menu |
| `command.py` | Evennia's template base `Command` class |
| `default_cmdsets.py` | Command set definitions (which commands are available where) |
| `explosion_utils.py` | Shared explosion/blast radius logic |
| `forensics.py` | `inspect` (alias `autopsy`) and `sever` |
| `shop.py` | `buy <item> from <container>` |
| `unloggedin_email.py` | Email-based login/registration commands |

## Command Sets

`default_cmdsets.py` defines the command sets that determine which commands are available:
- **CharacterCmdSet** -- Commands available to in-game characters
- **AccountCmdSet** -- Commands available at the account level
- **UnloggedinCmdSet** -- Commands available before login (handled by `unloggedin_email.py`)
- **UnconsciousCmdSet** / **DeathCmdSet** -- The few out-of-character commands left to an unconscious or dead character
- **SessionCmdSet** -- Session-level commands (empty; Evennia's template)
