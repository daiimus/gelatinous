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
| `shopkeeper.py` | Shop containers and merchant NPCs |

## Conventions

- **`obj.db.attr is None`** to check for missing attributes (never `hasattr(obj.db, ...)`)
- **`hasattr(obj.ndb, ...)`** is correct for NDB (non-database) attributes
- **AttributeProperty** descriptors are accessed directly on the object (e.g. `character.grit`, not `character.db.grit`)
- Prototypes define data variation; typeclasses define behavior
