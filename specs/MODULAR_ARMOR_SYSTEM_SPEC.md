# Modular Armor System Specification

> **Status:** 🚧 **PARTIAL** — armour stacking, plate carriers, tactical targeting and commands shipped; **weight/encumbrance not built**. ~~Verified 2026-08-02~~ **re-checked 2026-09-11: 25 claim(s) false, annotated inline**.
>
> **⚠ Spec-vs-code corrections — the following claims were FALSE when audited:**
> - The **Weight and Encumbrance System** section describes load thresholds, −1/−2/−3 movement penalties and `get_total_weight(character)`. **None of it exists.** Weight is a per-item attribute summed for display only (the `weight` attribute of `Item` in `typeclasses/items.py`).

## Overview

The Modular Armor System provides a comprehensive tactical combat experience with realistic armor mechanics, weight management, modular equipment, and intelligent targeting systems. This system integrates with the existing G.R.I.M. combat system and clothing layers to create depth and strategic choice in combat encounters.

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Armor Stacking Mechanics](#armor-stacking-mechanics)
3. [Weight and Encumbrance System](#weight-and-encumbrance-system)
4. [Modular Plate Carrier System](#modular-plate-carrier-system)
5. [Tactical Targeting System](#tactical-targeting-system)
6. [Equipment and Prototypes](#equipment-and-prototypes)
7. [Commands and Interface](#commands-and-interface)
8. [Integration Points](#integration-points)
9. [Balance Considerations](#balance-considerations)
10. [Implementation Files](#implementation-files)

---

## System Architecture

### Core Principles

1. **Layered Protection**: Multiple armor pieces can stack for cumulative protection
2. **Realistic Weight**: All equipment has weight that affects movement and encumbrance. 📋 UNBUILT (#1509): items have weight, shown by `look` and `slot list`; nothing reads it for a penalty yet.
3. **Modular Design**: Plate carriers accept swappable armor plates for customization
4. **Intelligent Targeting**: Combat targeting considers both skill and tactical intelligence
5. **Strategic Depth**: Players make meaningful trade-offs between protection, mobility, and cost

### Integration with Existing Systems

- **Clothing System**: Uses existing coverage and layering mechanics
- **G.R.I.M. Combat**: Integrates with Grit, Resonance, Intellect, Motorics stats
- **Medical System**: Armor reduces damage before medical damage calculation
- **Command System**: New armor management commands alongside existing combat commands

---

## Armor Stacking Mechanics

### Stacking Rules

**Layer Processing Order**: Outermost → Innermost (highest layer number first)

> **Ruling 2026-09-20 (#3366): an abdomen hit meets ONE side plate, in full.** Two slots
> share the abdomen. The hit lands on the left or the right at even odds
> (`_expand_plate_carrier_layers`, `random.choice` over the slots whose declared
> coverage includes the location) and meets that slot's plate at its full rating,
> then the carrier; an empty landed slot means carrier only. There is no gap
> outcome: the abdomen *is* the sides, the front and back plates own their own
> locations. Before this, both side plates were stacked at half rating as two
> sequential layers, which handed the wearer roughly a whole plate against every
> abdomen hit while the halving comment claimed the opposite (owner: the halving
> was a band-aid for two slots sharing one location). Recorded against the balance
> pass: abdomen mitigation changed, nothing tuned.

> **⚠ 2026-09-11 re-verify — the example below misstated the mechanic twice; it now shows the live stack.**
> (a) **Ratings are never summed for mitigation.**
> `_expand_plate_carrier_layers` (`typeclasses/armor_mixin.py`) returns
> the carrier at its own layer and the plate a hit meets at `layer + 1` as
> *separate* entries, and `_calculate_armor_damage_reduction`
> applies each sequentially with its own effectiveness. A rating-2 carrier and a
> rating-6 plate reduce damage twice, in series; they never form one rating-8
> layer. The summed form (`_get_total_armor_rating`) has exactly one
> caller — `_get_location_armor_coverage` in `world/medical/utils.py`,
> which feeds the armour-aware **targeting** weights (a heuristic with thresholds
> at 0 and 4), not display; since #3366 the armour display sums nothing and reads
> the carrier's declared coverage through `commands/CmdArmor.plate_layers_at`. (b) **The
> live layer numbers**: the plate carrier is layer 2 (`PLATE_CARRIER` in
> `world/prototypes.py`) and the tactical jumpsuit layer 1 (`TACTICAL_JUMPSUIT`),
> so the plate lands on 3.

```python
# Example armor stack on chest, applied outermost first. Each layer
# reduces what the layer above it left; ratings are never added.
Layer 3: standard plate (armor_rating: 7, ceramic)   # the plate in the front slot
Layer 2: plate carrier (armor_rating: 2, synthetic)
Layer 1: tactical jumpsuit (armor_rating: 1, synthetic)
```

### Damage Reduction Calculation

Each armor layer processes damage sequentially:

1. **Get armor effectiveness** based on armor type vs damage type
2. **Calculate percentage reduction** from armor rating
3. **Apply remaining damage** to next layer
4. **Continue until** damage absorbed or all layers processed

### Armor Effectiveness Matrix

> **⚠ 2026-09-11 re-verify — the block below is NOT the shipped matrix.** The live
> table is `ARMOR_EFFECTIVENESS_MATRIX` in `world/combat/constants.py`,
> read by `ArmorMixin._get_armor_effectiveness`
> (`typeclasses/armor_mixin.py`). It differs in kind, not just in
> detail: kevlar `stab` 0.3 / `cut` 0.4 (not 0.20 / 0.15), steel `bullet` 0.9
> (not 0.60) / `stab` 0.8 / `cut` 0.9, leather `cut` 0.6 / `blunt` 0.3, ceramic
> `bullet` 0.95 (not 0.90) — and **ceramic `blunt` is 0.8, commented "Very good
> vs blunt force"**, the exact inverse of the 0.30 "Poor vs
> blunt (shatters)" design recorded here. (The player-facing blurb at
> `typeclasses/items.py` (`Item._get_armor_type_info`) still says ceramic is "brittle vs blunt force", so
> the shipped prose and the shipped number also disagree with each other — one of
> the two is a bug, and which one is an owner call.) The live matrix additionally
> carries three armour types this block omits: `synthetic` (
> the `armor_type` of both the tactical jumpsuit and the plate carrier itself)
> `composite` (#3440, 2026-09-15 -- the lightweight plate's row, first-cut
> values approved as a placeholder for the balance pass; before it the plate
> mitigated silently on `generic`) and `generic` (the fallback for an
> unrecognised type), and every type
> defines all six damage keys (`bullet`, `stab`, `cut`, `blunt`, `laceration`,
> `burn`). Treat `world/combat/constants.py` as the source of truth; the values
> below are kept as the original design intent.

```python
ARMOR_EFFECTIVENESS = {
    # Format: armor_type: {damage_type: base_effectiveness}
    "kevlar": {
        "bullet": 0.80,    # Excellent vs bullets
        "stab": 0.20,      # Poor vs stabbing
        "cut": 0.15,       # Poor vs cutting
    },
    "ceramic": {
        "bullet": 0.90,    # Excellent vs bullets
        "blunt": 0.30,     # Poor vs blunt (shatters)
    },
    "steel": {
        "cut": 0.85,       # Excellent vs cutting
        "stab": 0.75,      # Good vs stabbing
        "bullet": 0.60,    # Moderate vs bullets
    },
    "leather": {
        "cut": 0.50,       # Moderate vs cutting
        "blunt": 0.40,     # Moderate vs blunt
        "bullet": 0.10,    # Poor vs bullets
    }
}
```

### Damage Reduction Formula

```python
# Per layer calculation (ArmorMixin._get_armor_effectiveness)
row = ARMOR_EFFECTIVENESS_MATRIX.get(armor_type, ARMOR_EFFECTIVENESS_MATRIX["generic"])
base_effectiveness = row.get(damage_type, 0.2)
rating_multiplier = min(1.0, armor_rating / 10.0)
final_effectiveness = min(0.95, base_effectiveness * rating_multiplier)
# Use round() instead of int() to avoid losing effectiveness on low damage
damage_reduction = round(remaining_damage * final_effectiveness)
remaining_damage = max(0, remaining_damage - damage_reduction)
```

An armour type not in the matrix uses the `generic` row, and a damage type missing from a row counts as 0.2. One layer never stops more than 95%. After each layer, `_degrade_armor` takes the damage that layer stopped off its durability, then sets its rating to its original rating times the share of durability left, rounded down and never below 1.

---

## Weight and Encumbrance System

📋 UNBUILT (#1509). Items have weight, shown by `look` (kg) and `slot list` (lbs); nothing below is built, and nothing reads weight for a penalty yet.

### Weight Categories

**Equipment Weight Classes**:
- **Light**: 0.1-1.0 kg (clothing, small items)
- **Medium**: 1.1-5.0 kg (armor pieces, weapons)
- **Heavy**: 5.1-15.0 kg (plate carriers, heavy armor)
- **Very Heavy**: 15.1+ kg (full tactical loadouts)

### Encumbrance Effects

**Total Weight Thresholds** (based on character strength):
- **Light Load** (0-20kg): No penalties
- **Medium Load** (21-40kg): -1 to movement-based rolls
- **Heavy Load** (41-60kg): -2 to movement-based rolls, slower combat
- **Overloaded** (61+kg): -3 to movement-based rolls, significant combat penalties

### Weight Calculation

```python
def get_total_weight(character):
    total = 0
    for location, items in character.worn_items.items():
        for item in items:
            base_weight = getattr(item, 'weight', 0)
            # Add weight of installed plates for carriers
            if hasattr(item, 'installed_plates'):
                for plate in item.installed_plates.values():
                    if plate:
                        total += getattr(plate, 'weight', 0)
            total += base_weight
    return total
```

---

## Modular Plate Carrier System

### Plate Carrier Mechanics

**Core Functionality**:
- Base carrier provides minimal protection (armor_rating: 1-2)
- Accepts armor plates in designated slots (front, back, left_side, right_side)
- **Slot-Specific Protection**: Each plate only protects the hit locations its slot covers
- Plates can be swapped in/out for different threat profiles

**Slot-to-Location Mapping**:

> **⚠ 2026-09-11 re-verify — `torso` was wrong in both this block and the
> `carrier.db` example below; both now read `abdomen`.** The shipped mapping is
> `plate_slot_coverage` on `PLATE_CARRIER` in `world/prototypes.py`: `front → ["chest"]`, `back → ["back"]`,
> `left_side → ["abdomen"]`, `right_side → ["abdomen"]`. **There is no `torso`
> body location in this anatomy** (see `COVERAGE_INHERITANCE`,
> `world/combat/constants.py:133-156`, which enumerates all 22 locations), so a
> carrier authored with `torso` would protect nothing at its sides. One
> more rule, corrected 2026-09-20 (#3366): at the abdomen a hit meets ONE side
> plate in full (see the ruling under Stacking Rules); the old half-rating
> average, applied three different ways in three places, is gone, and every
> display path reads `plate_slot_coverage` through `commands/CmdArmor.plate_layers_at`
> rather than a hand-typed map. (`plate_slot_coverage` reached its `getattr` consumers only after
> #2581 gave it an `AttributeProperty`; mitigation was always correct because it
> reads through `.db.`.)
```python
plate_slot_coverage = {
    "front": ["chest"],        # Front plate protects chest
    "back": ["back"],          # Back plate protects back
    "left_side": ["abdomen"],    # Left side plate protects abdomen
    "right_side": ["abdomen"]    # Right side plate protects abdomen
}
```

**Protection Calculation**:
- When calculating armor for a hit location, only plates in slots covering that location contribute
- Example: A shot to "chest" only counts the front plate, not back or side plates
- This creates realistic protection profiles where sides can be vulnerable even with chest/back plates installed

### Plate Types and Specifications

> **Original design, superseded.** Neither plate below exists, and no plate carries `coverage` or `threat_level`. The shipped plates are listed under Equipment and Prototypes. A plate has no coverage of its own; it protects whatever its slot covers (`plate_slot_coverage` on the carrier).

```python
# Example plate specifications
BALLISTIC_PLATE_MEDIUM = {
    "name": "Medium Ballistic Plate",
    "armor_rating": 6,
    "armor_type": "ceramic",
    "weight": 2.5,  # kg
    "coverage": ["chest"],  # or ["back"] for back plate
    "threat_level": "IIIA",  # NIJ protection level
    "description": "Multi-curve ceramic plate rated for rifle threats"
}

SOFT_ARMOR_INSERT = {
    "name": "Soft Armor Insert", 
    "armor_rating": 3,
    "armor_type": "kevlar",
    "weight": 0.8,
    "coverage": ["chest", "back"],
    "threat_level": "II",
    "description": "Flexible Kevlar insert for pistol protection"
}
```

### Installation System

**Plate Installation Rules**:
- Any plate fits any slot, as built (the plate prototypes are headed "Universal fit"). The original design had plates match carrier slot types: 📋 UNBUILT (not decided)
- Only one plate per slot
- Installing and removing a plate is instant, as built: the plate must be in your hand to go in, comes out into a free hand, and the plate verbs refuse while you are channeling. Nothing stops a plate change during a fight. The original design had it take time, to prevent combat swapping: 📋 UNBUILT (not decided)
- Damaged plates have reduced effectiveness (`_degrade_armor` lowers a plate's rating as its durability falls)

```python
# Plate carrier slots example
carrier.db.plate_slots = ["front", "back", "left_side", "right_side"]
carrier.db.installed_plates = {}  # filled as plates go in; an emptied slot stays as None
carrier.db.plate_slot_coverage = {
    "front": ["chest"],      # Front plate only protects chest
    "back": ["back"],        # Back plate only protects back
    "left_side": ["abdomen"],  # Left side only protects abdomen
    "right_side": ["abdomen"]  # Right side only protects abdomen
}
```

---

## Tactical Targeting System

### Targeting Philosophy

The system separates **ability to hit** from **target selection wisdom**:

- **Grit + Motorics**: Determines ability to execute precise vital strikes
- **Intellect**: Determines tactical wisdom in target selection relative to armor

### Vital Area Targeting Ability

> **Vital area derivation (#251)**: the set of vital body locations is computed
> dynamically by `_get_vital_locations` from the lethal body capacities
> (`LETHAL_CAPACITY_NAMES` in `world/medical/constants.py` — exactly the
> capacities `is_dead()` enforces; since #3248 the head is vital through
> `brain_integrity`, not `consciousness`). Each lethal capacity's organs are
> mapped to their `container`, yielding `{head, chest, neck, abdomen}` for the
> stock anatomy. It is data-driven, not a hardcoded literal, so anatomy changes
> propagate automatically. See `HEALTH_AND_SUBSTANCE_SYSTEM_SPEC.md` §
> "Spinal Anatomy, Decapitation & Combat Severance" for the canonical anatomy
> and death model behind the lethal capacities.

**Skill Calculation**: `vital_targeting_skill = attacker_grit + attacker_motorics`

**Ability Tiers**:
- **Poor (2-4)**: 1.1x vital area bias - struggles with precision
- **Moderate (5-6)**: 1.3x vital area bias - decent precision
- **Good (7-8)**: 1.6x vital area bias - skilled precision
- **Excellent (9+)**: 2.0x vital area bias - expert precision

### Tactical Target Selection

**Intellect Levels**:
- **Low (1-2)**: No armor consideration - hits any vital area randomly
- **Moderate (3-4)**: Basic armor awareness
  - Unarmored vitals: +30% targeting preference
  - Heavily armored vitals: -20% targeting preference
- **High (5+)**: Advanced tactical analysis
  - Unarmored vitals: +50% targeting preference
  - Heavily armored vitals: -40% targeting preference

As built (`select_hit_location`, `world/medical/utils.py`): the Intellect adjustments touch vital locations only. "Unarmored" means a summed armour rating of 0 and "heavily armored" means 4 or more; a vital rated 1 to 3 gets no adjustment. A positive success margin multiplies the vital bias by 1 + 0.1 per point. The armour figure comes from `_get_location_armor_coverage`, which adds every worn item covering the location and every plate whose slot covers it, so both side plates count at the abdomen (unlike damage, where a hit meets one). With no attacker the bias comes from the margin alone: ×1.25 up to 3, ×1.5 up to 8, ×2.0 up to 15, ×3.0 above that, applied to vital locations only when the margin is above 0.

### Targeting Decision Matrix

**Example Scenario**: Target with armored chest/head, unarmored neck/abdomen

| Fighter Profile | Chest (Armored) | Head (Armored) | Neck (Unarmored) | Abdomen (Unarmored) |
|----------------|-----------------|----------------|------------------|---------------------|
| Berserker (G7,M6,I2) | 2.0x | 2.0x | 2.0x | 2.0x |
| Tactician (G3,M4,I7) | 0.96x | 0.96x | 2.4x | 2.4x |  
| Elite (G6,M6,I6) | 1.2x | 1.2x | 3.0x | 3.0x |

### Implementation Logic

```python
def select_hit_location(character, success_margin=0, attacker=None):
    if attacker:
        # Calculate vital targeting ability
        grit = get_character_stat(attacker, "grit", 1)
        motorics = get_character_stat(attacker, "motorics", 1)
        intellect = get_character_stat(attacker, "intellect", 1)
        
        vital_skill = grit + motorics
        tactical_wisdom = intellect
        
        # Apply skill-based vital bias
        base_vital_bias = calculate_vital_bias(vital_skill)
        vital_bias = base_vital_bias * (1 + success_margin * 0.1)
        
        # Apply tactical target selection
        for location in vital_areas:
            armor_coverage = get_location_armor_coverage(character, location)
            
            if tactical_wisdom >= 5:
                if armor_coverage == 0:
                    location_weight *= vital_bias * 1.5  # Unarmored vital
                elif armor_coverage >= 4:
                    location_weight *= vital_bias * 0.6  # Heavily armored vital
            # ... additional tactical logic
```

---

## Equipment and Prototypes

> **Original design, superseded.** The blocks in this section are not the shipped prototypes. What ships, in `world/prototypes.py`:
>
> | prototype | layer | armor_type | rating | weight | notes |
> |---|---|---|---|---|---|
> | `tactical jumpsuit` | 1 | synthetic | 1 | 1.8 | covers chest, back, abdomen, groin, both arms, thighs, shins and feet; durability 20 |
> | `plate carrier` | 2 | synthetic | 2 | 2.5 | covers chest, back, abdomen; `plate_slots` is the list `front`, `back`, `left_side`, `right_side`; `installed_plates` starts empty; the `rolled` style drops abdomen; durability 40 |
> | `lightweight plate` | 0 (not worn) | composite | 5 | 1.8 | durability 100 |
> | `standard plate` | 0 (not worn) | ceramic | 7 | 3.2 | durability 140 |
> | `reinforced plate` | 0 (not worn) | steel | 9 | 8.5 | durability 180 |
> | `trauma plate` | 0 (not worn) | ceramic | 10 | 4.0 | durability 50 |
>
> Plates carry `is_armor_plate` and `plate_class`, not `plate_type` or `threat_level`. Plates are universal fit: any plate goes in any slot. A plate a hit meets counts as the layer above its carrier.

### Tactical Uniform Base Layer

```python
TACTICAL_JUMPSUIT = {
    "typeclass": "typeclasses.items.Item",
    "key": "tactical jumpsuit",
    "desc": "A durable tactical jumpsuit made from ripstop fabric with reinforced knees and elbows.",
    "weight": 1.2,
    "armor_rating": 1,
    "armor_type": "synthetic",
    "coverage": ["chest", "back", "left_arm", "right_arm", "left_leg", "right_leg", "abdomen"],
    "layer": 2,
    "clothing_type": "jumpsuit"
}
```

### Modular Plate Carrier

```python
PLATE_CARRIER = {
    "typeclass": "typeclasses.items.Item", 
    "key": "plate carrier",
    "desc": "A modular plate carrier system with MOLLE webbing and adjustable straps.",
    "weight": 2.0,
    "armor_rating": 2,  # Base protection from carrier itself
    "armor_type": "synthetic",
    "coverage": ["chest", "back"],
    "layer": 3,
    "is_plate_carrier": True,
    "plate_slots": {
        "chest": None,
        "back": None,
        "left_side": None,
        "right_side": None
    }
}
```

### Armor Plates

```python
BALLISTIC_PLATE_MEDIUM = {
    "typeclass": "typeclasses.items.Item",
    "key": "medium ballistic plate",
    "desc": "A curved ceramic armor plate rated for rifle protection.",
    "weight": 2.5,
    "armor_rating": 6,
    "armor_type": "ceramic", 
    "plate_type": "chest",  # Can install in chest slots
    "threat_level": "IIIA"
}

BALLISTIC_PLATE_BACK = {
    "typeclass": "typeclasses.items.Item", 
    "key": "back ballistic plate",
    "desc": "A ceramic armor plate designed for back protection.",
    "weight": 2.3,
    "armor_rating": 6,
    "armor_type": "ceramic",
    "plate_type": "back",   # Can install in back slots
    "threat_level": "IIIA"
}
```

---

## Commands and Interface

### Display System and UI Enhancements

**BoxTable System** (`world/utils/boxtable.py`):
- Enhanced EvTable with Unicode box-drawing characters (╔═╗║╚╝╠╣╦╩╬)
- Screen-width detection via session protocol flags
- Automatic table centering on player's screen
- Centered boxed headers matching table styling
- ANSI-aware text width calculations for accurate centering

**Player Configuration**:
- `caller.db.center_armor_headers` - Enable/disable table centering (default: `True`)
  - **⚠ 2026-09-11 re-verify: it does not enable or disable table centering.**
    The flag is read once, by `_get_center_headers`
    (`commands/CmdArmor.py`), and passed only as `center=` to
    `BoxTable.add_header` in the `armor`, `armor coverage` and
    `armor effectiveness` tables, where it decides whether the header
    **title** is centred inside its own box (`world/utils/boxtable.py`).
    The table's on-screen centering ignores the flag: `center_on_screen` runs
    for `armor` whenever the caller has a session, and for `armor coverage`
    and `armor effectiveness` always. The two bullets below are correct:
    `get_terminal_width` falls back to 78 columns and floors the detected width
    at 60.
- Automatically detects screen width with fallback to 78 columns
- Minimum width of 60 columns enforced

**Display Features**:
- Tables automatically centered on screen based on detected terminal width
- Headers presented in bordered boxes that connect seamlessly to table top
- Consistent box-drawing character style across all armor displays
- Color-aware width calculations prevent misalignment from ANSI codes

### Armor Inspection Commands

#### `armor` - Comprehensive Armor Status
```
> armor
                            ╔═══════════════════════════╗
                            ║     ARMOR STATUS          ║
                            ╠══════╦═══════╦════════╦═══╣
                            ║ Item ║ Type  ║ Rating ║...║
                            ╠══════╬═══════╬════════╬═══╣
                            ║ ...  ║ ...   ║ ...    ║...║
                            ╚══════╩═══════╩════════╩═══╝
```

Displays:
- Item name, armor type, protection rating (a carrier shows its own rating plus the count of installed plates, e.g. `2/10 (2 plates)`; the plates a hit meets are per location and listed by `armor coverage` -- #3366)
- Durability bar with visual indicator
- Body coverage areas
- All tables centered on screen with boxed headers

#### `armor coverage` - Location-Specific Protection Map
```
> armor coverage
                      ╔═══════════════════════════════╗
                      ║   ARMOR COVERAGE MAP          ║
                      ╠═══════════╦═════════╦════╦════╣
                      ║ Location  ║ Armor   ║... ║... ║
                      ╠═══════════╬═════════╬════╬════╣
                      ║ ...       ║ ...     ║... ║... ║
                      ╚═══════════╩═════════╩════╩════╝
```

Shows detailed protection for each body location:
- Lists all armor pieces protecting each location
- Shows armor type and rating per location
- Highlights unprotected areas
- For plate carriers, shows which plates protect which locations, read from `plate_slot_coverage`: `plate carrier [front: standard plate (7)]`, and for two slots on one location the alternatives a hit lands on, `plate carrier [one of left side: standard plate (7) | right side: trauma plate (10)]`. The Rating column is the carrier's own; nothing is summed (#3366).

#### `armor effectiveness` - Damage Type Matrix
```
> armor effectiveness
                ╔══════════════════════════════════╗
                ║ ARMOR EFFECTIVENESS MATRIX       ║
                ╠══════╦════════╦═══════╦═══════╦══╣
                ║ Type ║ Bullet ║ Stab  ║ Cut   ║..║
                ╠══════╬════════╬═══════╬═══════╬══╣
                ║ ...  ║ ...    ║ ...   ║ ...   ║..║
                ╚══════╩════════╩═══════╩═══════╩══╝
```

Displays effectiveness percentages for each armor type vs damage type:
- Every matrix row but the `generic` fallback: Kevlar, Steel, Leather, Ceramic, Synthetic, Composite (the table iterates the matrix since #3440, so a new material cannot go missing)
- Bullet, Stab, Cut, Blunt, Laceration, Burn damage types
- Shows base effectiveness percentage
- Centered table presentation

#### `armor <item>` - One Worn Piece

Details of one piece you wear, named through the core matcher (#3783): its description, type, material, current rating out of 10 and how far it has dropped from its original, condition with durability, and the locations it protects (`CmdArmor._show_item_details`). A name that matches nothing you wear answers "You are not wearing any armor matching '<name>'."

#### `armor comprehensive` - Layered View

Every body location with the worn items over it, in layer order (`CmdArmor._show_comprehensive_view`).

`armour` is an alias of `armor`.

#### `armor` - Legacy Text Format (when centering disabled)

> **⚠ 2026-09-11 re-verify: there is no legacy format.** `center_armor_headers`
> is read once, by `_get_center_headers` (`commands/CmdArmor.py`), and is
> passed only to `table.add_header(..., center=...)` — the
> `BoxTable` and its on-screen centering run either way. Setting it
> `False` un-centers the header title inside the box; it does not switch to plain
> text. The sample output below is unreachable line by line: no code path prints
> a **character-level** weight total, a load band or an encumbrance line (the two
> "Total Weight" lines that do ship are per-carrier — `CmdSlot._show_carrier_details` in lbs,
> `Item._get_plate_carrier_details` in kg — and belong to the unbuilt weight system's
> prerequisites, #1509), and nothing anywhere prints an "Effectiveness vs Common
> Threats" summary. What `armor` actually renders is a five-column table — Item,
> Type, Rating, Durability (a coloured ▓/░ bar), Coverage (first three locations,
> then "& N more") — in `CmdArmor._list_armor`.
```
> armor
=== ARMOR STATUS ===
Coverage Analysis:
  chest: Plate Carrier (Layer 3, Rating 8) + Tactical Jumpsuit (Layer 2, Rating 1) = 9 total
  back: Plate Carrier (Layer 3, Rating 8) + Tactical Jumpsuit (Layer 2, Rating 1) = 9 total  
  left_arm: Tactical Jumpsuit (Layer 2, Rating 1) = 1 total
  
Total Weight: 8.7 kg (Light Load)
Encumbrance: No penalties

Effectiveness vs Common Threats:
  Bullets: 85% (chest/back), 25% (arms/legs)
  Blades: 60% (chest/back), 35% (arms/legs)
```

#### `armor repair` - Repair Damaged Armor

> **⚠ 2026-09-11 re-verify: wrong invocation, wrong output, and the real system
> is much larger.** Repair is its own command, not an `armor` subcommand:
> `CmdArmorRepair`, `key = "repair"`, aliases `fix` / `mend`
> (`commands/CmdArmor.py`). Typing `armor repair plate carrier` falls
> through `CmdArmor.func`'s five-way dispatch into `_show_item_details` and
> answers *"You are not wearing any armor matching 'repair plate carrier'"*.
> The shipped surface is `repair <armor> [with <tool>]`,
> `repair <armor> field` and `repair <armor> full` (the command's help), and it carries:
> an **Intellect roll that can fail**, with per-material failure prose
> (`_send_repair_failure_messages`); tool bonuses up to +12, with the tool degrading and
> occasionally breaking (`_get_tool_bonus`, `_degrade_repair_tool`, `_damage_repair_tool`); a workshop-access gate on
> `full` (`_has_workshop_access`); and a shared branch that repairs breachable structures
> before armour (`try_repair_structure`, first in `func`). Success reports a durability delta and percentage —
> "Durability improved by N points. Current condition: N%" (`_send_repair_success_messages`) — never
> the named condition states ("damaged" → "worn") shown below. Multi-word armour
> names parse correctly here; #2521 fixed that by reading the modifier from the
> end of the phrase (`parse_repair_args`), and that parser is pinned by
> `world/tests/test_repair_reads_the_whole_name.py`.
```
> armor repair plate carrier
You begin field-repairing the plate carrier, restoring some of its protective capability.
The plate carrier's condition improves from 'damaged' to 'worn'.
```

### Enhanced Look Command

> **⚠ 2026-09-11 re-verify: neither sample below matched the code; both now show
> the real output.** `look <carrier>` shows Protection Rating, Armor Type,
> Weight, Base Protection, one line for each slot that has ever held a plate
> (`installed_plates` starts empty, so an unused slot is not listed, and a slot
> emptied by `unslot` shows `[Empty]`), Total Weight, Coverage and Condition
> (`Item._get_armor_information`, `Item._get_plate_carrier_details`,
> `typeclasses/items.py`). It labels weight **kg** while `slot list` labels the
> same attribute **lbs** (`CmdSlot._show_carrier_details`). `look <plate>` never prints the Plate Type
> / Threat Level / Slot Compatibility lines: they come from `_get_plate_details`,
> reached only through `elif hasattr(self, 'plate_type')` in
> `_get_armor_information`, and **`plate_type` is not declared in the
> AttributeProperty family** of `Item` nor written by any prototype — so `hasattr` is always False and
> the branch is dead code. A plate shows Protection Rating, Armor Type, Weight
> and Condition only. This is the same dead-read shape as the
> `weakness_exploited` key removed in #2473, and it needs the same resolution:
> delete the branch, or declare `plate_type` and populate the four plate
> prototypes. Already recorded twice in the code-review ledger (#2477) as
> read-but-unfiled.

#### `look <item>` - Shows Armor Information
```
> look standard plate
A standard ballistic plate made from advanced ceramic composite. Offers excellent protection against rifle rounds while maintaining reasonable weight.

=== Armor Information ===
  Protection Rating: 7 (Heavy)
  Armor Type: Ceramic (Excellent vs bullets, brittle vs blunt force)
  Weight: 3.2 kg
  Condition: Excellent
```

With one standard plate in the front slot:

```
> look plate carrier
A modular plate carrier system with front and back plate pockets, side plate slots, and tactical webbing. Designed to accept ballistic plates for customizable protection levels.

=== Armor Information ===
  Protection Rating: 2 (Light)
  Armor Type: Synthetic (Lightweight, basic protection)
  Weight: 2.5 kg
  Base Protection: 2
  Current Configuration:
    Front Slot: standard plate (+7 protection, 3.2kg)

  Total Weight: 5.7 kg
  Coverage: chest, back, abdomen
  Condition: Excellent
```

> *2026-09-20 (#3366): the `Total Protection: 8 (Base 2 + Plates 6)` line this example used to end with is gone; a sum of plate ratings across slots is a number no body location ever has. Each slot line still says what its plate is worth where a hit meets it.*

### Equipment Management Commands

#### `slot <plate> [in] <carrier> [<slot>]` - Install Armor Plate

The plate must be **in your hand** (#3463, 2026-09-18). Plates move through
the hands ledger (`character.hands`), so a plate loose in the pack is not
being handled and is refused ("You need to be holding the standard plate
to slot it."); wield it first. Moving the plate into the carrier releases
the hand. Anyone without a free hand cannot work plates at all: limb loss
is meant to be felt here.

```  
> slot standard plate in plate carrier
You install the standard plate into the front slot of your plate carrier.

> slot trauma plate in plate carrier back
You install the trauma plate into the back slot of your plate carrier.

> slot lightweight plate carrier left side
You install the lightweight plate into the left_side slot of your plate carrier.
```

#### `unslot <plate> [from <carrier>]` - Remove Armor Plate

Two doors, by owner ruling (#3463): `unslot <plate>` alone looks only in
the carriers you are **wearing**; `unslot <plate> from <carrier>` (or
`unslot <slot> from <carrier>`) reaches a carrier anywhere in your
inventory. A bare `unslot` that finds the plate in a carrier you merely
carry names the `from` form instead of acting. Either way the plate comes
out **into a free hand** and is refused when both hands are full ("Your
hands are full. Free one to take the standard plate out."). Every unslot
path goes through one door, `pull_plate_into_hand`, in
`commands/CmdArmor.py`. The resolvers are kept generic (carriers you wear;
an item in your inventory) because slot/unslot are expected to gain
non-plate uses.

**Naming (#3783).** `armor <item>`, `repair <armor> [with <tool>]` and both
`unslot` doors name their object through the core matcher,
`caller.search(name, candidates=pool, quiet=True)`: worn armour for `armor`;
the armour you carry for `repair`, a worn piece winning over a carried one;
repair tools you carry for `with`; the plates installed in the carriers you
wear, then in the ones you carry, for bare `unslot`; your carriers and then
that carrier's plates for the `from` form. So a piece answers to its key or
an alias, exact first, then a partial name in which each typed word starts a
word; `2nd plate` picks the second; a fragment from the middle of a word
finds nothing. The refusal texts are unchanged.

```
> unslot standard plate
You pull the standard plate out of the front slot of your plate carrier and hold it.
```

#### `get <plate> from <carrier>` / `put <plate> in <carrier> [<slot>]` - The General Verbs

Owner ruling (#3619, 2026-09-20): "get/put should work as unslot/slot but
require further clarification with the from command." `get <plate> from
<carrier>` goes through the unslot door (`pull_plate_into_hand`) and
`put <plate> in <carrier> [<slot>]` through the install door
(`install_plate_from_hand`, extracted from `CmdSlot` for this), so the
hands rule, the messages and the carrier's `installed_plates` ledger are
the same whichever verb is used. Before this, `get` lifted the plate
through the plain container path and left the ledger pointing at a plate
in your hand: the carrier kept counting it, `slot list` showed it, and
`unslot` "found" it. A bare `get <plate>` cannot see into a carrier (it
searches the room), which is the "further clarification": you must say
`from`.

The general verbs reach a carrier lying in the room as well as one you
wear or carry; the messages then say "the plate carrier", not "your"
(`whose()`). `slot`/`unslot` keep their inventory reach. `put` is a new
game-wide verb (`commands/CmdInventory.py`): it takes a plate into a
carrier, an item into your open locker at a bank of lockers
(`LockerBank.stash_item`, the door `stash` itself uses), and refuses everything else ("The X can't hold
that.") — there are no carried containers. The Kettle's locker bank used
to carry a `put` alias of its own, which a game-wide verb would have
hidden in that one room; it was dropped so one command answers `put`
everywhere. `put` resolves the ITEM first and only an Item you carry will
do (`me`/`here` short-circuit `Character.search` ahead of every reach
argument, so a name-taking door handed back the player), and it does not
see a hidden object, the same as `get`. `slot` and `unslot` refuse while
channeling like every other hands verb (#3376, #3635), so the four verbs
answer alike.

```
> put standard plate in plate carrier front
You install the standard plate into the front slot of your plate carrier.
> get standard plate from plate carrier
You pull the standard plate out of the front slot of your plate carrier and hold it.
> get standard plate
You don't see a 'standard plate' here.
```

#### `slot list [carrier]` - List Installed Plates

> `slot list <carrier>` (the carrier's whole name, #3365) prints
> `=== <Carrier> ===`, the description, Carrier Statistics (Base Protection as
> `N/10`, then Carrier, Plate and Total Weight in **lbs**), then Plate
> Configuration: every slot the carrier has, with its plate, the plate's rating
> as `N/10` and a (Good)/(Fair)/(Poor) condition, or `[Empty Slot]`
> (`CmdSlot._show_carrier_details`). There is no "Total Protection Bonus" line
> and no kg anywhere in that output. The Plate Protection and Total Protection
> sums it used to print were deleted 2026-09-20 (#3366): the damage model never
> computed them. `slot list` alone, or a bare `slot`, lists every carrier you
> wear or carry, with each slot's plate or `[Empty]`
> (`CmdSlot._list_plate_carriers`).
```
> slot list plate carrier
=== Plate Carrier ===
Description: A modular plate carrier system with front and back plate pockets, side plate slots, and tactical webbing. Designed to accept ballistic plates for customizable protection levels.

Carrier Statistics:
  Base Protection: 2/10
  Carrier Weight: 2.5 lbs
  Plate Weight: 3.2 lbs
  Total Weight: 5.7 lbs

Plate Configuration:
  Front: standard plate (7/10) (Good)
  Back: [Empty Slot]
  Left_Side: [Empty Slot]
  Right_Side: [Empty Slot]
```

---

## Integration Points

### Character Damage Processing

**`take_damage()` method in `typeclasses/armor_mixin.py`** (class `ArmorMixin`, mixed into `Character`):
1. Interrupt any channel the victim is running, then refuse an amount that is not a number or is not above 0 (no damage)
2. Break the victim's hiding: being hit reveals them (#3763)
3. Calculate armor coverage for hit location
4. Process armor layers sequentially (outermost first)
5. Apply damage reduction from each layer
6. Pass remaining damage to medical system
7. Run the combat severance and decapitation checks (`_maybe_sever_from_damage`)
8. On death, record the first fatal blow in `db.death_blow` for the corpse and call `at_death`; on unconsciousness, call `_handle_unconsciousness`

### Combat Handler Integration

**Hit location is chosen by `select_hit_location(target, success_margin, attacker)` in `world/medical/utils.py`**, called with the attacker from `world/combat/attack.py` (attacks), `world/combat/grappling.py`, `world/combat/utils.py` and `commands/combat/core_actions.py`:
1. Pass attacker to `select_hit_location()` 
2. Calculate targeting based on attacker's G.R.I.M. stats
3. Apply tactical target selection logic
4. Proceed with normal combat resolution

### Clothing System Integration

**Uses existing clothing mechanics**:
- Coverage areas determine armor protection zones
- Layer system determines armor processing order
- Worn items system manages equipped armor

---

## Balance Considerations

### Trade-off Matrix

| Loadout Type | Protection | Mobility | Cost | Tactical Flexibility |
|-------------|-----------|----------|------|---------------------|
| No Armor | None | Excellent | Free | Maximum |
| Light Armor | Low | Good | Low | High |
| Tactical Gear | Moderate | Fair | Moderate | Moderate |
| Heavy Armor | High | Poor | High | Low |
| Elite Setup | Very High | Poor | Very High | Low |

### Balancing Mechanisms

1. **Weight Penalties**: Heavy armor reduces mobility and combat effectiveness
   - **⚠ 2026-09-11 re-verify: unbuilt (#1509).** Nothing reads item weight for
     any penalty, so the Mobility column of the Trade-off Matrix above is design
     intent rather than shipped behaviour, and "Resource Limits" below rests on
     cost alone. A reinforced plate weighs 8.5 (`REINFORCED_PLATE` in `world/prototypes.py`) and
     currently costs its wearer nothing. The one live protection-versus-mobility
     trade-off is the carrier's `rolled` style, which drops `abdomen` coverage
     (`style_configs` on `PLATE_CARRIER`) — and therefore both side plates with it. Per the
     balance-pass rule, nothing should be tuned against these thresholds until
     the system exists.
2. **Cost Barriers**: Better armor requires significant resource investment
3. **Tactical Counters**: High-Intellect fighters can exploit armor gaps
4. **Maintenance**: Armor degrades and requires repair/replacement
5. **Situational**: Different armor works better in different scenarios

### Power Scaling Prevention

- **Diminishing Returns**: Additional armor layers provide less benefit
- **Specialization**: No single armor type excels against all damage
- **Resource Limits**: Weight and cost prevent "best of everything" builds
- **Tactical Counters**: Every defensive strategy has offensive counters

---

## Implementation Files

### Core System Files

**`typeclasses/armor_mixin.py`** (class `ArmorMixin`, mixed into `Character`; `characters.py` only inherits it):
- `take_damage()` - Entry point for armor + medical damage processing
- `_calculate_armor_damage_reduction()` - Main armor processing
- `_get_total_armor_rating()` - Calculates armor + plates
- `_get_armor_effectiveness()` - Armor type vs damage type
- Weight calculation and encumbrance effects
  - **⚠ 2026-09-11 re-verify: not present.** `typeclasses/armor_mixin.py`
    contains no occurrence of "weight" or "encumbr".
    See the correction block at the top of this spec and issue #1509. The file's
    real fifth responsibility, undocumented here, is combat-driven severance and
    decapitation: `_bone_freshly_destroyed`, `_maybe_sever_from_damage`,
    `_broadcast_decapitation_message`, plus the `death_blow`
    record `take_damage` persists for the corpse pipeline (#2778).

**`world/medical/utils.py`**:
- `select_hit_location()` - Tactical targeting system
- `_get_location_armor_coverage()` - Analyzes armor at location
- Integration with existing medical system

**`world/combat/attack.py`** (also `world/combat/grappling.py`, `world/combat/utils.py`, `commands/combat/core_actions.py`):
- Hit location selection passes the attacker
- Integration with tactical targeting system

### Equipment and Commands

**`typeclasses/items.py`**:
- Enhanced Item class with armor and weight attributes
- Plate carrier system implementation
- Modular plate support
- Enhanced `return_appearance` method for automatic armor display

**`commands/CmdArmor.py`**:
- `CmdArmor` - Armor inspection and status
- `CmdArmorRepair` - Field repair capabilities  
- `CmdSlot` - Armor plate installation
- `CmdUnslot` - Armor plate removal

**Enhanced Look Integration**:
- Modified `typeclasses/items.py` Item class `return_appearance` method
- Shows protection ratings and armor types (the slot-compatibility lines never render; see Enhanced Look Command)
- Displays current plate carrier configurations
- Automatic armor detection and detailed analysis
- Preserves all existing look functionality

**`world/prototypes.py`**:
- Tactical uniform prototypes
- Plate carrier and armor plate definitions
- Complete equipment ecosystem

**`commands/default_cmdsets.py`**:
- Integration of new commands into character command sets

---

## Code Quality and Optimizations

### Performance Improvements

**Coverage Caching** (`typeclasses/armor_mixin.py`):
```python
# Cache coverage calculations to avoid repeated function calls
coverage_cache = {}
for item in armor_items:
    if item not in coverage_cache:
        coverage_cache[item] = item.get_current_coverage()
    current_coverage = coverage_cache[item]
```
- **Impact**: Significantly improves performance when processing multiple armor layers
- **Benefit**: Eliminates redundant `get_current_coverage()` calls in nested loops

### Safety Features

**Null Safety Checks** (`typeclasses/armor_mixin.py`):
```python
# Safety check: ensure item still exists (edge case: deleted mid-combat)
if not item or not hasattr(item, 'pk') or not item.pk:
    continue
```
- **Impact**: Prevents crashes if armor is deleted during combat
- **Benefit**: Graceful handling of edge cases

**Improved Exception Handling** (`world/medical/utils.py`):
```python
except Exception:
    # Catch only expected exceptions, let system errors propagate
    pass
```
- **Impact**: Avoids catching critical system errors like `KeyboardInterrupt`
- **Benefit**: Better error handling and debugging

### Mathematical Accuracy

**Rounding vs Truncation** (`typeclasses/armor_mixin.py`):
```python
# Use round() instead of int() to avoid losing effectiveness on low damage
layer_damage_reduction = round(remaining_damage * final_reduction_percent)
```
- **Before**: 2 damage × 40% = 0.8 → `int()` = 0 (armor does nothing!)
- **After**: 2 damage × 40% = 0.8 → `round()` = 1 (armor blocks 1 damage)
- **Impact**: Light armor now properly protects against small damage amounts

---

## Future Enhancement Opportunities

### Advanced Features

1. **Armor Degradation**: Realistic wear and damage over time
2. **Environmental Effects**: Weather, temperature affecting armor
3. **Specialized Plates**: Trauma plates, side protection, neck guards
   - **⚠ 2026-09-11 re-verify: two of these three already ship.** Trauma plates:
     `CERAMIC_PLATES` in `world/prototypes.py`, key `"trauma plate"`, rating 10
     with low durability (50), so its rating falls fastest as it absorbs damage
     (`_degrade_armor`: never below 1; nothing destroys a plate, though its
     description says it shatters). Side protection: the carrier's
     `left_side` / `right_side` slots, mapped to the abdomen; a hit meets one of
     them in full (#3366, `_expand_plate_carrier_layers` in `typeclasses/armor_mixin.py`). Only **neck guards**
     remain 📋 UNBUILT (no issue) — four prototypes cover `neck` (a rebreather, a collar, a
     necktie, a scarf) and none carries an armour rating.  
4. **Advanced Materials**: Exotic armor types with unique properties
5. **Armor Crafting**: Player-created armor with custom properties

### Tactical Enhancements

1. **Formation Combat**: Group tactics and armor coordination
2. **Penetration Mechanics**: Armor-piercing weapons and ammunition
3. **Ballistic Trajectories**: Angle-dependent armor effectiveness
4. **Armor Profiles**: Different effectiveness vs range/weapon types
5. **Weakness Exploitation**: an attacker who knows a plate's seam,
   joint or damaged section reduces that layer's effectiveness for the
   hit. 📋 **UNBUILT** (no issue). `_calculate_armor_damage_reduction` once read a
   `weakness_exploited` key off each armour layer and subtracted it from
   the layer's reduction — but nothing in the codebase ever wrote that
   key, so the subtraction was always `- 0.0` and the `(-N%)` it fed
   into the combat debug line could never render. The dead read was
   removed in #2473 and the idea recorded here instead, because a no-op
   that looks like a mechanic reads to the next person as a shipped
   feature that is quietly broken. Building it needs a source of truth
   for *what* a weakness is (armour condition? a called shot? a
   recognised seam on a specific prototype?), which is the part that
   was never designed.

### Quality of Life

1. **Loadout Presets**: Save/load complete armor configurations
2. **Armor Recommendations**: System suggests optimal armor for threats
3. **Maintenance Tracking**: Automated armor condition monitoring
4. **Visual Indicators**: Clear armor status in character descriptions

---

## Conclusion

The Modular Armor System provides a comprehensive tactical combat experience that rewards both preparation and intelligent play. By separating physical capability (Grit/Motorics) from tactical intelligence (Intellect), the system creates meaningful character differentiation and strategic depth.

The integration with existing systems ensures compatibility while adding significant new gameplay dimensions. The modular design allows for future expansion and customization while maintaining balance through realistic trade-offs and resource management.

**Code Quality**: The implementation includes performance optimizations (coverage caching), safety features (null checks), mathematical accuracy improvements (proper rounding), and robust error handling.

> **⚠ 2026-09-11 re-verify: the optimisations are real; "thorough testing" is not
> — though the gap is narrower than a first pass suggests.** Coverage caching
> (`_calculate_armor_damage_reduction` in `typeclasses/armor_mixin.py`), the
> deleted-mid-combat null check and `round()` over `int()` (same function) all verified present.
> "Improved Exception Handling" snippet above is the one that reads backwards: it
> shows `except Exception:` while its comment claims narrowing, and the shipped
> line is narrower than either — `except (ImportError, AttributeError):`
> (`select_hit_location` in `world/medical/utils.py`).
>
> Armour tests exist in **eight** files (the fifth and sixth added 2026-09-20 by
> #3366 and #3619; two more came with #3440 and #3783):
>
> - `world/tests/test_repair_reads_the_whole_name.py` — ~15 tests pinning
>   `parse_repair_args` against the shipped multi-word names (#2521).
> - `world/tests/test_the_vestigial_sweep.py` — `TestArmourStillReduces`
>   calls `_calculate_armor_damage_reduction` directly: armour
>   reduces, never below zero, an uncovered location is untouched. Its vest uses
>   `armor_type = "ballistic"`, which is not in the matrix, so it exercises the
>   `generic` fallback and asserts no specific number.
> - `world/tests/test_reads_reach_their_data.py` — the `plate_slot_coverage`
>   AttributeProperty fix (#2581).
> - `world/tests/test_armor_rendering.py` — three per-observer *broadcast* tests
>   (`TestArmorPerObserverRendering`): install, unslot, and the actor's exclusion.
>   It had five; the two that drove `CmdSlot._remove_plate` / `_swap_plates` went
>   with those methods (**#3366, 2026-09-20**: both were born dead in d308a3ab,
>   2025-10-06, unreachable from `CmdSlot.func`, and contradicted the "no combat
>   swapping" note above; `_find_installed_plate`, `_calculate_total_carrier_rating`
>   and every "New total protection" / "Total Protection" line went with them).
> - `world/tests/test_an_abdomen_hit_meets_one_side_plate.py` — nine tests (#3366):
>   a chest hit meets the front plate in full plus the carrier; an abdomen hit
>   meets exactly one side plate in full; the side is rolled; an empty side means
>   carrier only; the display reads the declared coverage (a re-mapped carrier
>   follows); the coverage screen lists layers and never sums; the armour table
>   shows the carrier rating and a plate count; `look` at a carrier and `slot`
>   print no protection total.
> - `world/tests/test_get_and_put_use_the_plate_doors.py` — 32 tests (#3619,
>   #3635): `get <plate> from <carrier>` clears the ledger and lands the plate
>   in a hand (carried, worn, and on the floor), is refused with full hands,
>   and a bare `get` cannot see in; `put` installs (by slot, by two-word slot,
>   from a hand only, into a floor carrier), refuses a non-plate, a plain item,
>   a person, the room, `me`/`here` as the item, a hidden carrier, and an
>   article alone; `put <item> in locker` reaches `LockerBank.stash_item`,
>   `me` cannot be stowed or retrieved, the bank carries no `put` alias and
>   exactly one command answers `put` in the merged locker-room cmdset;
>   `slot`/`unslot` are refused mid-channel (state); `peel_slot_name`. The
>   refusal LINE for `put`, `slot`, `unslot`, `stash` and `retrieve` is pinned
>   in the BLOCKED-verb register, `test_a_tool_leaving_your_hands_breaks_the_channel.py`.
> - `world/tests/test_armor_table_lists_every_material.py` — six tests (#3440):
>   the `armor effectiveness` table has a row for every material in the matrix
>   but `generic`.
> - `world/tests/test_armor_verbs_use_the_core_matcher.py` — 26 tests (#3783):
>   `armor <item>`, `repair` and `unslot` name their object through the core
>   matcher.
>
> Untested: the effectiveness matrix values and degradation of the landed plate.
> (The `slot` / `unslot` parsers are pinned by
> `world/tests/test_slot_and_unslot_take_whole_names.py` since #3365.)

This system transforms combat from simple damage exchanges into tactical engagements where equipment choices, character builds, and intelligent play all contribute to success.

---

## Revision History

**October 4, 2025 - v1.2**:
- Implemented slot-specific plate protection system
- Added `plate_slot_coverage` mapping to plate carriers
- Updated armor rating calculation to be location-aware
- Front plate → chest, back plate → back, side plates → abdomen (the shipped mapping; there is no `torso` location)
- Creates realistic protection profiles with vulnerable flanks

**October 4, 2025 - v1.1**:
- Added performance optimizations (coverage caching)
- Implemented null safety checks for edge cases
- Fixed mathematical rounding for low-damage scenarios
- Improved exception handling specificity
- Updated damage reduction formula documentation

**October 4, 2025 - v1.0**:
- Initial implementation and documentation
- Complete armor stacking mechanics
- Tactical targeting system with Intellect integration
- Modular plate carrier system
- Command interface and user experience
