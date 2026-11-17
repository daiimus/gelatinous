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
├── appearance.py        # Symptoms a condition shows on the body
├── augments.py          # Toggled cyberware abilities
├── charts.py            # Surgical chart data
├── clock.py             # The medical clock (elapsed-time rates)
├── cyberware_status.py  # The `/system` cyberware readout
├── diagnose.py          # The diagnose pane of the `operate` menu
├── medical_messages.py  # Species-aware medical and death prose
├── procedures.py        # Surgical procedure pipeline
├── removable.py         # What can come off a body, living or dead
├── severance.py         # Cut-point computation for severing
├── treatments.py        # Wound-care treatment dispatch
├── wounds/              # Wound description subsystem
│   ├── __init__.py
│   ├── constants.py     # Wound-related constants
│   ├── wound_descriptions.py  # Wound description generation
│   ├── longdesc_hooks.py      # Character longdesc integration
│   └── messages/        # Injury-type-specific wound messages
│       ├── blunt.py
│       ├── bullet.py
│       ├── cut.py
│       ├── generic.py
│       ├── harvested.py
│       ├── laceration.py
│       ├── robot.py
│       ├── severed.py
│       ├── stab.py
│       └── synth.py
└── README.md
```

## Data Storage

In play, `character.medical_state` is a `MedicalState` object (`core.py`). `save_medical_state` in `utils.py` stores it as a dict in the character's database, and `load_medical_state` rebuilds the object from it:
```python
character.db.medical_state = {
    "organs": {"brain": {"current_hp": 8, "max_hp": 10, ...}, ...},
    "removed_organs": [...],
    "conditions": [{"type": "bleeding", "location": "chest", ...}, ...],
    "blood_level": 85.0,
    "pain_level": 23.0,
    "consciousness": 78.0
}
```

## Damage Flow

1. `character.take_damage(amount, location, injury_type, target_organ=None)` (`typeclasses/armor_mixin.py`): armor reduces the damage, then `world.medical.utils.apply_anatomical_damage` applies what is left
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

Character dies if any capacity in `LETHAL_CAPACITY_NAMES` (`constants.py`) reaches zero, or blood runs out:
- Heart destroyed (blood_pumping = 0)
- Both lungs destroyed (breathing = 0)
- Liver and stomach destroyed (digestion = 0)
- Cervical spine destroyed, a broken neck (neck_integrity = 0)
- Brain destroyed (brain_integrity = 0): dead on the blow, with a death window in which a new brain revives the body (#3248)
- Blood loss reaches `BLOOD_LOSS_DEATH_THRESHOLD` (85% by default)

Low consciousness makes a character unconscious, never dead.

## Commands

(`damagetest` and `@medaudit` were development and migration tools, removed 2026-10-09, #3728; `healtest` went earlier, 2025-09-06, folded into `@heal`.)

- `medical [target]` (`diagnose`, `medstat`, `health`, `ht`) -- Check medical status; kept by owner ruling, narrative rendering is the open design

- `medinfo [organs|conditions|capacities]` -- Detailed medical information
- `@resetmedical [character|confirm all]` -- Reset character medical states (admin)

## Integration Points

- **Combat**: Location-based damage targeting, weapon-specific injury patterns
- **Longdesc**: Medical conditions automatically appear in character descriptions via `wounds/` subsystem
- **Clothing/Armor**: Affects which body locations can be hit and damage reduction

## Constants and Balance

All numerical values are defined as constants in `constants.py` for easy balancing: death/unconsciousness thresholds, organ HP values and hit weights, treatment success modifiers, pain and blood loss rates.
