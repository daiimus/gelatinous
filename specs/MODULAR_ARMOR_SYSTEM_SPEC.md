# Modular Armor System Specification

> **Status:** 🚧 **PARTIAL** — armour stacking, plate carriers, tactical targeting and commands shipped; **weight/encumbrance not built**. ~~Verified 2026-08-02~~ **re-checked 2026-09-11: 25 claim(s) false, annotated inline**.
>
> **⚠ Spec-vs-code corrections — the following claims were FALSE when audited:**
> - The **Weight and Encumbrance System** section describes load thresholds, −1/−2/−3 movement penalties and `get_total_weight(character)`. **None of it exists.** Weight is a per-item attribute summed for display only (`typeclasses/items.py:56`, `:537-541`).

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
2. **Realistic Weight**: All equipment has weight that affects movement and encumbrance
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

> **⚠ 2026-09-11 re-verify — the example below misstates the mechanic twice.**
> (a) **Ratings are never summed for mitigation.**
> `_expand_plate_carrier_layers` (`typeclasses/armor_mixin.py:470-569`) returns
> the carrier at its own layer and each applicable plate at `layer + 1` as
> *separate* entries, and `_calculate_armor_damage_reduction` (`:405-443`)
> applies each sequentially with its own effectiveness. A rating-2 carrier and a
> rating-6 plate reduce damage twice, in series; they never form one rating-8
> layer. The summed form (`_get_total_armor_rating`, `:571-611`) has exactly one
> caller — `_get_location_armor_coverage` in `world/medical/utils.py:315-316`,
> which feeds the armour-aware **targeting** weights, not display; the armour
> display re-derives its own totals in `commands/CmdArmor.py:33-78`. (b) **The
> live layer numbers are lower**: the plate carrier is layer 2
> (`world/prototypes.py:1358`) and the tactical jumpsuit layer 1 (`:1270`), so
> the plate lands on 3. The relative order the example teaches is still right.

```python
# Example armor stack on chest:
Layer 3: Plate Carrier (armor_rating: 2) + Medium Ballistic Plate (armor_rating: 6) = 8 total
Layer 2: Tactical Jumpsuit (armor_rating: 1)
Layer 1: Undershirt (armor_rating: 0)
```

### Damage Reduction Calculation

Each armor layer processes damage sequentially:

1. **Get armor effectiveness** based on armor type vs damage type
2. **Calculate percentage reduction** from armor rating
3. **Apply remaining damage** to next layer
4. **Continue until** damage absorbed or all layers processed

### Armor Effectiveness Matrix

> **⚠ 2026-09-11 re-verify — the block below is NOT the shipped matrix.** The live
> table is `ARMOR_EFFECTIVENESS_MATRIX` in `world/combat/constants.py:377-426`,
> read by `ArmorMixin._get_armor_effectiveness`
> (`typeclasses/armor_mixin.py:625-634`). It differs in kind, not just in
> detail: kevlar `stab` 0.3 / `cut` 0.4 (not 0.20 / 0.15), steel `bullet` 0.9
> (not 0.60) / `stab` 0.8 / `cut` 0.9, leather `cut` 0.6 / `blunt` 0.3, ceramic
> `bullet` 0.95 (not 0.90) — and **ceramic `blunt` is 0.8, commented "Very good
> vs blunt force"** (`constants.py:406`), the exact inverse of the 0.30 "Poor vs
> blunt (shatters)" design recorded here. (The player-facing blurb at
> `typeclasses/items.py:592` still says ceramic is "brittle vs blunt force", so
> the shipped prose and the shipped number also disagree with each other — one of
> the two is a bug, and which one is an owner call.) The live matrix additionally
> carries two armour types this block omits: `synthetic` (`constants.py:410` —
> the `armor_type` of both the tactical jumpsuit and the plate carrier itself)
> and `generic` (`:418`, the fallback for an unrecognised type), and every type
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
# Per layer calculation
base_effectiveness = ARMOR_EFFECTIVENESS[armor_type][damage_type]
rating_multiplier = min(1.0, armor_rating / 10.0)
final_effectiveness = base_effectiveness * rating_multiplier
# Use round() instead of int() to avoid losing effectiveness on low damage
damage_reduction = round(remaining_damage * final_effectiveness)
remaining_damage = max(0, remaining_damage - damage_reduction)
```

---

## Weight and Encumbrance System

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

> **⚠ 2026-09-11 re-verify — `torso` is wrong, in both this block and the
> `carrier.db` example below.** The shipped mapping is
> `world/prototypes.py:1374-1379`: `front → ["chest"]`, `back → ["back"]`,
> `left_side → ["abdomen"]`, `right_side → ["abdomen"]`. **There is no `torso`
> body location in this anatomy** (see `COVERAGE_INHERITANCE`,
> `world/combat/constants.py:133-156`, which enumerates all 22 locations), so a
> carrier authored to the mapping below would protect nothing at its sides. One
> shipped rule is also missing here: at the abdomen each side plate contributes
> only **half** its rating (`typeclasses/armor_mixin.py:556-559`,
> `plate_rating // 2`), because an angled side plate only partly covers the
> abdomen. Note that the halving is applied in three different places three
> different ways — mitigation halves each plate then layers them
> (`:556-559`), the coverage display sums both then halves the total
> (`commands/CmdArmor.py:65-77`), and the targeting rating does not halve at all
> (`armor_mixin.py:598-607`) — so quote the mitigation path when a number has to
> be right. (`plate_slot_coverage` reached its `getattr` consumers only after
> #2581 gave it an `AttributeProperty`; mitigation was always correct because it
> reads through `.db.`.)
```python
plate_slot_coverage = {
    "front": ["chest"],        # Front plate protects chest
    "back": ["back"],          # Back plate protects back
    "left_side": ["torso"],    # Left side plate protects torso
    "right_side": ["torso"]    # Right side plate protects torso
}
```

**Protection Calculation**:
- When calculating armor for a hit location, only plates in slots covering that location contribute
- Example: A shot to "chest" only counts the front plate, not back or side plates
- This creates realistic protection profiles where sides can be vulnerable even with chest/back plates installed

### Plate Types and Specifications

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
- Plates must match carrier slot types
- Only one plate per slot
- Installation/removal takes time (prevents combat swapping)
- Damaged plates have reduced effectiveness

```python
# Plate carrier slots example
carrier.db.plate_slots = ["front", "back", "left_side", "right_side"]
carrier.db.installed_plates = {
    "front": None,      # Can accept chest plates
    "back": None,       # Can accept back plates  
    "left_side": None,  # Can accept side plates
    "right_side": None  # Can accept side plates
}
carrier.db.plate_slot_coverage = {
    "front": ["chest"],      # Front plate only protects chest
    "back": ["back"],        # Back plate only protects back
    "left_side": ["torso"],  # Left side only protects torso
    "right_side": ["torso"]  # Right side only protects torso
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
> (`LETHAL_CAPACITY_NAMES` in `world/medical/constants.py` — the capacities
> `is_dead()` enforces plus `consciousness`). Each lethal capacity's organs are
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
    (`commands/CmdArmor.py:29-30`), and passed only as `center=` to
    `BoxTable.add_header` (`:236`, `:426`), where it decides whether the header
    **title** is centred inside its own box (`world/utils/boxtable.py:119-128`).
    The table's on-screen centering is unconditional — `center_on_screen` runs
    whenever the caller has a session, regardless of the flag
    (`CmdArmor.py:238-244`, `:428-433`). The two bullets below are correct:
    `get_terminal_width` falls back to 78 columns and floors the detected width
    at 60 (`world/utils/boxtable.py:13-31`).
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
- Item name, armor type, protection rating
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
- For plate carriers, shows which plates protect which locations

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
- Kevlar, Steel, Leather, Ceramic armor types
- Bullet, Stab, Cut, Blunt, Laceration, Burn damage types
- Shows base effectiveness percentage
- Centered table presentation

#### `armor` - Legacy Text Format (when centering disabled)

> **⚠ 2026-09-11 re-verify: there is no legacy format.** `center_armor_headers`
> is read once, by `_get_center_headers` (`commands/CmdArmor.py:29-30`), and is
> passed only to `table.add_header(..., center=...)` (`:236`, `:426`) — the
> `BoxTable` and its on-screen centering run either way (`:238-244`). Setting it
> `False` un-centers the header title inside the box; it does not switch to plain
> text. The sample output below is unreachable line by line: no code path prints
> a **character-level** weight total, a load band or an encumbrance line (the two
> "Total Weight" lines that do ship are per-carrier — `CmdArmor.py:1421` in lbs,
> `typeclasses/items.py:628` in kg — and belong to the unbuilt weight system's
> prerequisites, #1509), and nothing anywhere prints an "Effectiveness vs Common
> Threats" summary. What `armor` actually renders is a five-column table — Item,
> Type, Rating, Durability (a coloured ▓/░ bar), Coverage (first three locations,
> then "& N more") — at `:158-245`.
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
> (`commands/CmdArmor.py:841-842`). Typing `armor repair plate carrier` falls
> through `CmdArmor.func`'s four-way dispatch into `_show_item_details` and
> answers *"You are not wearing any armor matching 'repair plate carrier'"*
> (`:450-452`). The shipped surface is `repair <armor> [with <tool>]`,
> `repair <armor> field` and `repair <armor> full` (`:831-838`), and it carries:
> an **Intellect roll that can fail**, with per-material failure prose
> (`:1182-1223`); tool bonuses up to +12, with the tool degrading and
> occasionally breaking (`:1068-1131`, `:1225-1258`); a workshop-access gate on
> `full` (`:1259-1272`); and a shared branch that repairs breachable structures
> before armour (`:858-862`). Success reports a durability delta and percentage —
> "Durability improved by N points. Current condition: N%" (`:1167-1170`) — never
> the named condition states ("damaged" → "worn") shown below. Multi-word armour
> names parse correctly here; #2521 fixed that by reading the modifier from the
> end of the phrase (`parse_repair_args`, `:887-930`), and that parser is the
> one piece of armour code with real test coverage
> (`world/tests/test_repair_reads_the_whole_name.py`).
```
> armor repair plate carrier
You begin field-repairing the plate carrier, restoring some of its protective capability.
The plate carrier's condition improves from 'damaged' to 'worn'.
```

### Enhanced Look Command

> **⚠ 2026-09-11 re-verify: the carrier example is right; the plate example
> cannot render.** `look <carrier>` works as shown — base protection, per-slot
> configuration, totals (`Item._get_plate_carrier_details`,
> `typeclasses/items.py:599-630`), though it labels weight **kg** (`:544`,
> `:628`) while `slot list` labels the same attribute **lbs**
> (`commands/CmdArmor.py:1419-1421`). `look <plate>` never prints the Plate Type
> / Threat Level / Slot Compatibility lines: they come from `_get_plate_details`
> (`items.py:632-645`), reached only through `elif hasattr(self, 'plate_type')`
> (`:553`), and **`plate_type` is not declared in the AttributeProperty family**
> (`:107-134`) nor written by any prototype — so `hasattr` is always False and
> the branch is dead code. A plate shows Protection Rating, Armor Type, Weight
> and Condition only. This is the same dead-read shape as the
> `weakness_exploited` key removed in #2473, and it needs the same resolution:
> delete the branch, or declare `plate_type` and populate the four plate
> prototypes. Already recorded twice in the code-review ledger (#2477) as
> read-but-unfiled.

#### `look <item>` - Shows Armor Information
```
> look medium ballistic plate
A curved ceramic armor plate rated for rifle protection.

Armor Information:
  Protection Rating: 6 (Excellent)
  Armor Type: Ceramic (Strong vs bullets, weak vs blunt force)
  Weight: 2.5 kg
  Plate Type: Chest plate
  Threat Level: IIIA
  Condition: Excellent
  
Slot Compatibility: Can be installed in chest slots of plate carriers.
```

```
> look plate carrier
A modular plate carrier system with MOLLE webbing and adjustable straps.

Armor Information:
  Base Protection: 2 (Light)
  Coverage: Chest, Back
  Weight: 2.0 kg (plus installed plates)
  Current Configuration:
    Chest Slot: Medium Ballistic Plate (+6 protection)
    Back Slot: [Empty]
    Left Side: [Empty] 
    Right Side: [Empty]
  
Total Protection: 8 (Base 2 + Plates 6)
Total Weight: 4.5 kg
```

### Equipment Management Commands

#### `slot <plate> [in] <carrier> [<slot>]` - Install Armor Plate
```  
> slot medium ballistic plate in plate carrier
You install the medium ballistic plate into the chest slot of the plate carrier.
The carrier's protection increases significantly.

> slot back plate in carrier back
You install the back plate into the back slot of the plate carrier.

> slot side plate vest
You install the side plate into the left_side slot of the vest.
```

#### `unslot <plate> [from <carrier>]` - Remove Armor Plate
```
> unslot medium ballistic plate
You carefully remove the medium ballistic plate from the plate carrier.
```

#### `slot list [carrier]` - List Installed Plates

> **⚠ 2026-09-11 re-verify: this invocation does not parse, and the output is
> not what ships.** `slot list plate carrier` is three tokens; `CmdSlot.func`
> matches `list` only in its one- and two-token forms
> (`commands/CmdArmor.py:1307-1315`), so three tokens fall through to
> `_parse_install_command` and bind plate=`"list"`, carrier=`"plate"`,
> slot=`"carrier"`. Working today: `slot list` (all carriers) and
> `slot <single-token-carrier>` — see the parser defect noted under
> `slot <plate> [in] <carrier>` above; **the spec is right about the syntax, so
> fix the parser rather than these examples.** When `_show_carrier_details` is
> reached (`:1385-1430`) it prints `=== <Carrier Key> ===`, a Carrier Statistics
> block (Base / Plate / Total Protection as `N/10`, then Carrier / Plate / Total
> Weight in **lbs**) and a Plate Configuration list with a condition colour per
> slot. There is no "Total Protection Bonus" line and no kg anywhere in that
> output. Note also that the Total Protection it prints is a plain sum, which the
> damage model never computes — mitigation applies each plate as its own capped
> layer.
```
> slot list plate carrier
=== PLATE CARRIER CONFIGURATION ===
Chest Slot: Medium Ballistic Plate (Rating 6, Weight 2.5kg)
Back Slot: Back Ballistic Plate (Rating 6, Weight 2.3kg) 
Left Side: [Empty]
Right Side: [Empty]

Total Plate Weight: 4.8kg
Total Protection Bonus: +12 armor rating
```

---

## Integration Points

### Character Damage Processing

**`take_damage()` method in `typeclasses/armor_mixin.py`** (class `ArmorMixin`, mixed into `Character`):
1. Calculate armor coverage for hit location
2. Process armor layers sequentially (outermost first)  
3. Apply damage reduction from each layer
4. Pass remaining damage to medical system

### Combat Handler Integration

**Modified hit location selection in `world/combat/handler.py`**:
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
     cost alone. A reinforced plate weighs 8.5 (`world/prototypes.py:1466`) and
     currently costs its wearer nothing. The one live protection-versus-mobility
     trade-off is the carrier's `rolled` style, which drops `abdomen` coverage
     (`:1382-1387`) — and therefore both side plates with it. Per the
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
    contains no occurrence of "weight" or "encumbr" in any of its 689 lines.
    See the correction block at the top of this spec and issue #1509. The file's
    real fifth responsibility, undocumented here, is combat-driven severance and
    decapitation: `_bone_freshly_destroyed` (`:140`), `_maybe_sever_from_damage`
    (`:174`), `_broadcast_decapitation_message` (`:258`), plus the `death_blow`
    record `take_damage` persists for the corpse pipeline (`:120-132`, #2778).

**`world/medical/utils.py`**:
- `select_hit_location()` - Tactical targeting system
- `_get_location_armor_coverage()` - Analyzes armor at location
- Integration with existing medical system

**`world/combat/handler.py`**:
- Modified hit location selection to pass attacker
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
- Shows protection ratings, armor types, and slot compatibility  
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
     `CERAMIC_PLATES`, key `"trauma plate"`, rating 10 with deliberately low
     durability so it shatters after absorbing damage
     (`world/prototypes.py:1484-1509`). Side protection: the carrier's
     `left_side` / `right_side` slots, mapped to the abdomen at half rating
     (`:1372-1379`, `typeclasses/armor_mixin.py:556-559`). Only **neck guards**
     remain unbuilt — four prototypes cover `neck` (a rebreather, a collar, a
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
   hit. **UNBUILT.** `_calculate_armor_damage_reduction` once read a
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

**Code Quality**: The implementation includes performance optimizations (coverage caching), safety features (null checks), mathematical accuracy improvements (proper rounding), and robust error handling. All code has undergone thorough review and testing.

> **⚠ 2026-09-11 re-verify: the optimisations are real; "thorough testing" is not
> — though the gap is narrower than a first pass suggests.** Coverage caching
> (`typeclasses/armor_mixin.py:341-359`), the deleted-mid-combat null check
> (`:415-417`) and `round()` over `int()` (`:439`) all verified present. The
> "Improved Exception Handling" snippet above is the one that reads backwards: it
> shows `except Exception:` while its comment claims narrowing, and the shipped
> line is narrower than either — `except (ImportError, AttributeError):`
> (`world/medical/utils.py:272`).
>
> Armour tests exist in **four** files, and none of them reaches the parts this
> re-verify found wrong:
>
> - `world/tests/test_repair_reads_the_whole_name.py` — ~15 tests pinning
>   `parse_repair_args` against the shipped multi-word names (#2521). The
>   best-covered armour code in the repo.
> - `world/tests/test_the_vestigial_sweep.py` — `TestArmourStillReduces`
>   (`:98-129`) calls `_calculate_armor_damage_reduction` directly: armour
>   reduces, never below zero, an uncovered location is untouched. Its vest uses
>   `armor_type = "ballistic"`, which is not in the matrix, so it exercises the
>   `generic` fallback and asserts no specific number.
> - `world/tests/test_reads_reach_their_data.py` — the `plate_slot_coverage`
>   AttributeProperty fix (#2581).
> - `world/tests/test_armor_rendering.py` — five per-observer *broadcast* tests
>   (`TestArmorPerObserverRendering`, `:128-290`). Two of them
>   (`test_remove_plate_broadcast`, `test_swap_plates_broadcast`) drive
>   `CmdSlot._remove_plate` / `_swap_plates`, which **no command dispatch can
>   reach** — `CmdSlot.func` (`commands/CmdArmor.py:1300-1318`) routes only to
>   `_list_plate_carriers`, `_show_carrier_details` and
>   `_parse_install_command`, so those two tests cover dead player-facing code.
>
> Untested: the effectiveness matrix values, multi-layer stacking and plate
> expansion, the slot→location mapping and the abdomen halving, degradation, and
> the `slot` / `unslot` parsers — which is why the multi-word parsing defect
> recorded above survived.

This system transforms combat from simple damage exchanges into tactical engagements where equipment choices, character builds, and intelligent play all contribute to success.

---

## Revision History

**October 4, 2025 - v1.2**:
- Implemented slot-specific plate protection system
- Added `plate_slot_coverage` mapping to plate carriers
- Updated armor rating calculation to be location-aware
- Front plate → chest, back plate → back, side plates → torso
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

---

*This specification represents the complete, production-ready implementation as of October 2025. All components have been integrated, code-reviewed, optimized, and tested within the Evennia framework.*