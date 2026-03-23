# commands/

Game commands organized by functionality. Each module implements one or more Evennia `Command` subclasses.

## Command Modules

| Module | Description |
|--------|-------------|
| `combat/` | Combat command subpackage (attack, movement, grapple, aim, etc.) |
| `charcreate.py` | EvMenu-based character creation flow |
| `CmdAdmin.py` | Administrative and builder commands (`@keywords` custom keyword catalog) |
| `CmdArmor.py` | Armor inspection and coverage display |
| `CmdBug.py` | In-game bug reporting |
| `CmdCharacter.py` | Character sheet, stats, appearance, and `@shortdesc` keyword management |
| `CmdClothing.py` | Wearing and removing clothing |
| `CmdCommunication.py` | Identity-aware say, whisper, emote, and dot-pose commands |
| `CmdConsumption.py` | Eating and drinking |
| `CmdExplosives.py` | Grenade and explosive device commands |
| `CmdFixCharacterOwnership.py` | Admin tool for repairing character ownership |
| `CmdGraffiti.py` | Spray-painting and environmental writing |
| `CmdInventory.py` | Inventory management: wield, get, drop, give, wrest, frisk |
| `CmdMedical.py` | Medical status and diagnostic commands |
| `CmdMedicalItems.py` | Medical item usage and management |
| `CmdSpawnMob.py` | NPC spawning with randomized stats (builder+) |
| `CmdThrow.py` | Cross-room projectile throwing |
| `default_cmdsets.py` | Command set definitions (which commands are available where) |
| `explosion_utils.py` | Shared explosion/blast radius logic |
| `shop.py` | Shop browsing, buying, and selling |
| `unloggedin_email.py` | Email-based login/registration commands |

## Command Sets

`default_cmdsets.py` defines the command sets that determine which commands are available:
- **CharacterCmdSet** -- Commands available to in-game characters
- **AccountCmdSet** -- Commands available at the account level
- **UnloggedinCmdSet** -- Commands available before login (handled by `unloggedin_email.py`)
