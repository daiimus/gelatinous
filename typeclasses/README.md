# typeclasses/

Game object definitions using Evennia's typeclass system. Each module defines one or more classes that inherit from Evennia's base typeclasses.

## Architecture

The Character typeclass uses a **mixin decomposition** pattern to keep `characters.py` focused on core G.R.I.M. stats and combat integration:

```
characters.py          # Character typeclass (G.R.I.M. stats, combat, medical)
├── armor_mixin.py     # Armor calculation and damage reduction
├── clothing_mixin.py  # Clothing wear/remove and layering
└── appearance_mixin.py # Longdesc generation from wounds, clothing, equipment
```

## Modules

| Module | Description |
|--------|-------------|
| `accounts.py` | Player accounts with email login and multi-character support |
| `characters.py` | Character typeclass with G.R.I.M. stats, combat, medical, and identity system (`get_display_name`, `get_sdesc`, identity-aware search override) |
| `llm_npc.py` | `LLMNpc`, the one NPC typeclass: a body with the language-model brain; what it can do comes from its post and its soul |
| `llm_persona.py` | Builds an NPC's persona card for the model from the NPC's live fields (no typeclass) |
| `identity_bearer.py` | `IdentityBearerMixin`: recognition and forensic recovery for objects that keep an identity snapshot (corpses, severed heads) |
| `appearance_mixin.py` | Character appearance and longdesc generation |
| `armor_mixin.py` | Armor value calculation and body coverage |
| `clothing_mixin.py` | Clothing wear/remove logic and layering |
| `corpse.py` | Forensic corpse objects with inventory and decay |
| `curtain_of_death.py` | Death boundary exit (narrative death experience) |
| `death_progression.py` | Death state management (unconsciousness through death) |
| `exits.py` | Custom exit functionality |
| `items.py` | Weapons, armor, consumables, tools, and medical items |
| `objects.py` | Base objects, ordinal number support, graffiti walls, blood pools |
| `rooms.py` | Room features, environmental systems, and integration hooks |
| `bar.py` | `BarCounter`: the bar's counter and crafting station, with its own commands (`menu`, `order`, `use`, `prepare`, `clean`, `till`) |
| `butcher.py` | `FoodCart`: the butcher gig's cart, a shop that is also seating |
| `channels.py` | Evennia's template `Channel` class |
| `clinic.py` | No typeclass; re-exports the clinic's vocabulary from `world/clinic.py` |
| `crane.py` | `CraneConsole`: the Boiler Run crane's console, which answers radio band 27.0 |
| `doors.py` | `DoorExit`: a door that is the exit itself |
| `elevator.py` | The elevator: a car that is a real room, its door exits, call buttons and panel |
| `furniture.py` | `Furniture` and `Seating` for sitting and lying, and the `AutoDoc` |
| `lockers.py` | `LockerBank`: the locker fixture, with its own `rent`, `locker`, `stash` and `retrieve` commands |
| `scripts.py` | Evennia's template `Script` class |
| `smoke.py` | `CigarettePack`: a pack that spawns its branded cigarettes |
| `terminals.py` | Pressable machines: the rental terminal, sleeve dispenser and insurance terminal |
| `shopkeeper.py` | `ShopContainer`, the shelf a shop sells from |

## Conventions

- **`obj.db.attr is None`** to check for missing attributes (never `hasattr(obj.db, ...)`)
- **`obj.ndb.attr is None`** for NDB (non-database) attributes too: an unset name reads as `None`, so `hasattr(obj.ndb, ...)` is always true
- **AttributeProperty** descriptors are accessed directly on the object (e.g. `character.grit`, not `character.db.grit`)
- Prototypes define data variation; typeclasses define behavior
