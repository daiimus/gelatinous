# Combat Commands Package

Combat commands organized into modules by tactical function.

## Structure

```
commands/combat/
├── cmdset_combat.py         # Combat command set definition
├── core_actions.py          # CmdAttack, CmdStop
├── movement.py              # CmdFlee, CmdRetreat, CmdAdvance, CmdCharge
├── jump.py                  # CmdJump (inter-room jumping)
├── special_actions.py       # CmdGrapple, CmdEscape, CmdRelease, CmdDisarm, CmdAim
└── README.md
```

## Modules

### core_actions.py
Fundamental combat commands that initiate or control combat flow:
- **CmdAttack** -- Primary combat initiation with proximity and weapon validation
- **CmdStop** -- Cease attacking/aiming, enter yielding state

### movement.py
Tactical movement and positioning within combat:
- **CmdFlee** -- Attempt to flee from combat or aiming situations
- **CmdRetreat** -- Disengage from melee proximity within the same room
- **CmdAdvance** -- Close distance with a target for melee engagement
- **CmdCharge** -- Reckless rush with bonus/penalty tradeoff

### jump.py
- **CmdJump** -- Jump between rooms (e.g. across gaps, over obstacles)

### special_actions.py
Specialized combat commands for tactical depth:
- **CmdGrapple** -- Initiate a grapple with a target
- **CmdEscapeGrapple** -- Attempt to escape from being grappled
- **CmdReleaseGrapple** -- Release a grapple hold
- **CmdDisarm** -- Attempt to disarm a target's weapon
- **CmdAim** -- Aim at a target or direction for ranged attacks

### cmdset_combat.py
Defines `CombatCmdSet` which bundles all combat commands and is added to characters when combat begins.

## Integration

Commands interact with the combat system modules in `world/combat/`:
- **Constants** from `world.combat.constants` -- no hardcoded strings
- **Utilities** from `world.combat.utils` -- stat access, validation, formatting
- **Proximity** from `world.combat.proximity` -- melee range management
- **Grappling** from `world.combat.grappling` -- restraint state management
- **Handler** from `world.combat.handler` -- `get_or_create_combat()` for handler lifecycle
