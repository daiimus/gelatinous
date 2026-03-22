# Medical System

Organ-level trauma simulation for the Gelatinous MUD.

## What's Implemented

- **Individual Bone Anatomy**: Hospital-grade anatomical accuracy (humerus, femur, tibia, metacarpals, metatarsals)
- **Organ System**: Individual organs with HP, functionality, and anatomical mapping
- **Body Capacities**: Vital (consciousness, blood pumping, breathing, digestion) and functional (sight, hearing, moving, manipulation, talking) capacities affected by organ health
- **Medical Conditions**: Bleeding, fractures, infections, and other status effects
- **Vital Signs**: Blood level, pain level, consciousness tracking
- **Anatomical Damage**: Location-based damage with organ targeting and injury types
- **Wound Descriptions**: Injury-type-specific wound messages for longdesc integration
- **Death Conditions**: Death from vital organ failure or blood loss
- **Unconsciousness**: Based on consciousness capacity and vital signs

## Files

```
world/medical/
├── __init__.py          # Package initialization
├── constants.py         # Medical system constants and thresholds
├── core.py              # Core classes (Organ, MedicalCondition, MedicalState)
├── conditions.py        # Condition definitions and processing
├── utils.py             # Integration utilities and helper functions
├── script.py            # Medical system scripts (timers, periodic effects)
├── wounds/              # Wound description subsystem
│   ├── __init__.py
│   ├── constants.py     # Wound-related constants
│   ├── wound_descriptions.py  # Wound description generation
│   ├── longdesc_hooks.py      # Character longdesc integration
│   ├── longdesc_integration.py # Longdesc system bridge
│   └── messages/        # Injury-type-specific wound messages
│       ├── blunt.py
│       ├── bullet.py
│       ├── cut.py
│       ├── generic.py
│       └── stab.py
└── README.md
```

## Data Storage

Medical state is persisted in the character database:
```python
character.db.medical_state = {
    "organs": {"brain": {"current_hp": 8, "max_hp": 10, ...}, ...},
    "conditions": [{"type": "bleeding", "location": "chest", ...}, ...],
    "blood_level": 85.0,
    "pain_level": 23.0,
    "consciousness": 78.0
}
```

## Damage Flow

1. `character.take_anatomical_damage(damage, location, injury_type)`
2. Damage distributed to organs in location based on hit weights
3. Medical conditions generated based on injury type and severity
4. Vital signs updated (blood loss, pain, consciousness)
5. Medical state saved to database

## Body Capacities

Organs contribute to body capacities that affect character function:
- **Vital**: `consciousness`, `blood_pumping`, `breathing`, `digestion`
- **Functional**: `sight`, `hearing`, `moving`, `manipulation`, `talking`

Individual bones provide specific capacity contributions:
- **Long Bones**: Femur and tibia each contribute 40% to moving capacity
- **Arm Bones**: Humerus contributes 40% to manipulation capacity
- **Hand/Foot Bones**: Metacarpals (20%) and metatarsals (10%) for fine motor functions

## Death Conditions

Character dies if:
- Heart destroyed (blood_pumping = 0)
- Both lungs destroyed (breathing = 0)
- Liver destroyed (digestion = 0)
- Blood loss exceeds fatal threshold (85% by default)

## Commands

- `medical [target]` -- Check medical status
- `medinfo [organs|conditions|capacities]` -- Detailed medical information
- `damagetest <amount> [location] [injury_type]` -- Test damage application
- `healtest [condition|all]` -- Test healing (development command)
- `@resetmedical [character|confirm all]` -- Reset character medical states (admin)
- `@medaudit` -- Comprehensive medical system diagnostics (admin)

## Integration Points

- **Combat**: Location-based damage targeting, weapon-specific injury patterns
- **Longdesc**: Medical conditions automatically appear in character descriptions via `wounds/` subsystem
- **Clothing/Armor**: Affects which body locations can be hit and damage reduction

## Constants and Balance

All numerical values are defined as constants in `constants.py` for easy balancing: death/unconsciousness thresholds, organ HP values and hit weights, treatment success modifiers, pain and blood loss rates.
