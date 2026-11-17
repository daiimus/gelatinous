# SPDR M9 Sticky Grenade System - IMPLEMENTATION COMPLETE

## Status: ✅ FULLY IMPLEMENTED AND TESTED

Not everything below is in the game. Behaviour the code does not have is marked `📋 UNBUILT` where it stands.

## Overview
The SPDR M9 "Spider" grenade is a repurposed asteroid mining tool that uses electromagnetic adhesion to stick to ferrous metal surfaces. Originally designed for breaching metallic ore deposits, it now serves as a tactical adhesive explosive with spider-like telescoping legs that seek and clamp onto armor based on metal content and magnetic properties.

### Grenade Representation Architecture

**Q: How do we represent the grenade once it's stuck?**

**A: The grenade is magnetically stuck to the armor item itself, moving with the armor wherever it goes:**

1. **Physical Location**: `grenade.location = armor_object` (magnetically bonded to the armor)
2. **State Tracking**: `grenade.db.stuck_to_armor = armor_object` (which armor it's stuck to)
3. **Bidirectional Reference**: `armor.db.stuck_grenade = grenade` (armor knows it has a grenade)
4. **Explosion Location**: `get_explosion_room(grenade)` walks up from the grenade through the armor and its wearer (if any) to the room

**Why This Makes Sense:**
- ✅ **Physical realism**: Magnetic bond is to the metal armor, not the person
- ✅ **Armor removal doesn't break bond**: Grenade stays stuck to armor when removed
- ✅ **Dropped armor = dropped grenade**: Grenade moves with armor automatically
- ✅ **Proximity danger**: Dropped armor with grenade stays in proximity (existing explosion logic)
- ✅ **Multi-step escape**: Must remove, drop, AND flee to be safe
- ✅ **Tactical depth**: Can't just remove and be safe - must get distance

**Object Hierarchy:**
```
grenade.location = armor (stuck to the armor item)
armor.location = character (worn) OR room (on ground)

When worn:  grenade → armor → character → room
When dropped: grenade → armor → room
```

**Alternative Rejected:**
- ❌ `grenade.location = character` - Implies grenade stuck to person, breaks on armor removal
- ❌ `grenade.location = room` - Doesn't move with armor automatically

---

## Implementation Status

### ✅ Completed Features

**Core Mechanics:**
- ✅ Magnetic adhesion system with `metal_level` and `magnetic_level` on all armor
- ✅ Stick chance calculation based on metal content, magnetic properties, and grenade strength
- ✅ SPDR M9 grenade prototype with `magnetic_strength=8` (mining-grade electromagnets)
- ✅ Spider-themed messages emphasizing telescoping legs and electromagnetic seeking
- ✅ Bidirectional sticky relationships (grenade ↔ armor)
- ✅ Grenade location hierarchy (grenade → armor → character/room)

**Throw Command Integration:**
- Untargeted sticky throws use magnetic target selection (`CmdThrow._pick_room_target`): `throw <grenade>` (into the aimed room, or this room) and `throw <grenade> to <direction>` land on the person whose outermost chest armor has the highest magnetic_level among those who pass the stick thresholds. The thrower and anyone the thrower cannot perceive are skipped. If nobody qualifies, the grenade lands by a random visible occupant. `throw <grenade> here` picks no target, so the grenade lands loose and cannot stick. `throw <grenade> at <name>` always goes to that person.
- ✅ Stick attempt after successful throw hit
- ✅ Outermost armor layer detection at hit location
- Only the outermost worn garment covering the hit location is tried, once; a failed roll bounces. 📋 UNBUILT (no issue): trying inner layers, and skipping a garment that already holds a grenade.
- ✅ Bounce mechanics for failed sticks or non-magnetic surfaces

**Rigged Grenade Integration:**
- ✅ Rigged sticky grenades use same magnetic targeting
- ✅ Reuses `select_most_magnetic_target_in_room()` logic
- ✅ Reuses `resolve_weapon_hit()` for stick resolution
- When a magnetic target was chosen, that person is in the blast whether or not the grenade stuck, and the person who tripped the trap is not. If no target qualified, the person who tripped it is in the blast.

**Explosion Mechanics:**
- ✅ Proximity-based damage system (grenades track their own proximity list)
- ✅ Armor hierarchy explosion (grenade → armor → character/room resolution)
- Human-shield modifiers (0.0/1.0/2.0) apply when the grenade explodes loose or on armor lying in a room; when it explodes on armor someone is wearing or carrying, the holder takes double and everyone else in proximity takes half, with no human-shield check
- ✅ Stuck grenades explode wherever armor currently is

**Messages & Narrative:**
- ✅ Success: Spider-legs deploy and electromagnetic lock
- ✅ Failure (weak field): Legs scrabble but can't grip
- ✅ Failure (no armor): Legs search but find no metal
- ✅ Combat red coloring for victim on successful stick
- ✅ Mining equipment backstory integrated into all messaging

**Prototype System:**
- ✅ Single SPDR M9 grenade prototype (consolidated from 3 variants)
- ✅ Key: "SPDR M9 grenade", aliases: "spdr", "spider grenade", "m9", "sticky grenade", "sticky"
- ✅ Rich description with asteroid mining origins
- ✅ Stats: magnetic_strength=8, blast_damage=30, fuse_time=10s, dud_chance=0.02, damage_type=laceration

**Key Functions Implemented:**
- ✅ `calculate_stick_chance(grenade, armor)` in world/combat/explosives.py
- ✅ `establish_stick(grenade, armor, hit_location)` in world/combat/explosives.py
- ✅ `get_outermost_armor_at_location(character, location)` in world/combat/explosives.py
- ✅ `get_stuck_grenades_on_character(character)` in world/combat/explosives.py
- ✅ `select_most_magnetic_target_in_room(room, grenade, exclude=None, seen_by=None)` in world/combat/throwing.py
- ✅ `resolve_weapon_hit(weapon, target, thrower)` in world/combat/throwing.py handles stick mechanics

### Code Locations

**Core Implementation:**
- **world/combat/throwing.py**: `handle_landing` → `resolve_weapon_hit` (hit roll and stick check); `select_most_magnetic_target_in_room`
- **commands/CmdThrow.py**: `CmdThrow._pick_room_target` (untargeted sticky throws)
- **commands/explosion_utils.py**: `check_rigged_grenade` and its inner `explode_rigged_grenade` (rigged targeting and explosion); `start_grenade_ticker`; `explode_standalone_grenade`
- **world/combat/explosives.py**: `calculate_stick_chance`, `get_explosion_room`, `establish_stick`, `get_stuck_grenades_on_character`, `get_outermost_armor_at_location`, `break_stick`

  Note: `world/combat/utils.py` only re-exports these symbols (`from .explosives import ...`); it does not define them.
- **world/prototypes.py**: `STICKY_GRENADE` (the SPDR M9 prototype)

### Testing Results

All scenarios tested and working correctly:
1. ✅ SPDR M9 sticks to steel plate mail (95% success rate)
2. ✅ SPDR M9 bounces off cloth/synthetic armor (0% - no magnetic response)
3. ✅ SPDR M9 bounces off aluminum/ceramic (0% - non-magnetic metals)
4. ✅ Rigged SPDR M9 selects most magnetic target in room
5. ✅ Rigged SPDR M9: the chosen magnetic target is in the blast, not the person who tripped it (that person is in the blast only when no target qualified)
6. Human-shield modifiers apply when a stuck grenade explodes on armor lying in a room, not when it explodes on armor someone is wearing or carrying
7. ✅ Spider-themed messages display correctly for all scenarios

---

## SPDR M9 "Spider" Grenade

### Narrative Identity

**Full Name:** SPDR M9 Spider-Class Magnetic Adhesion Grenade

**Origin Story:** Originally designed for breaching and clearing metallic ore deposits in asteroid mining operations. What was once a tool for breaking apart ore-rich asteroids has found a darker purpose in combat scenarios.

**Physical Description:**
- Compact black sphere bristling with eight telescoping articulated legs
- Tiny servos activate when thrown, extending legs with mechanical precision
- Electromagnetic tips pulse through leg tips seeking ferrous metal surfaces
- Single-minded purpose of industrial demolition equipment
- Soft blue LED pulses faster as detonation approaches

**Design Philosophy:**
- Industrial reliability standards (2% dud chance)
- Mining-grade electromagnets (magnetic_strength=8)
- Longer tactical fuse (10 seconds)
- Enhanced blast damage (30) for ore-breaking capability

### Technical Specifications

```python
STICKY_GRENADE = {
    "key": "SPDR M9 grenade",
    "aliases": ["spdr", "spider grenade", "m9", "sticky grenade", "sticky"],
    "magnetic_strength": 8,    # Mining-grade electromagnets (0-10 scale)
    "fuse_time": 10,           # Longer fuse for tactical use
    "damage_type": "laceration",
    "blast_damage": 30,        # Industrial demolition power
    "dud_chance": 0.02,        # 2% - Industrial reliability
    "is_sticky": True,         # Electromagnetic adhesion enabled
}
```

### Message Themes

All SPDR M9 messages emphasize:
- **Mechanical Precision**: "extend with mechanical precision", "electromagnetic sensors"
- **Spider-Like Behavior**: "telescoping legs", "skitter", "eight legs", "seeking metal"
- **Industrial Purpose**: Single-minded demolition equipment, frustrated when thwarted
- **Sound Design**: *CLACK-CLACK-CLACK*, *SNAPPING*, *CLAMPING*, whirring servos
- **Mining Origins**: References to ferrous metals, electromagnetic seeking, industrial demolition

### Combat Messages

**Success - Electromagnetic Lock (victim sees):**
```
|rThe SPDR M9 grenade's articulated legs extend with mechanical precision, their electromagnetic tips skittering across your plate mail before *CLAMPING* tight with magnetic fury!|n
```

**Success - Electromagnetic Lock (thrower sees):**
```
Your SPDR M9 grenade's spider-legs deploy and latch onto Marcia's plate mail with a satisfying *CLACK-CLACK-CLACK* of magnetic adhesion!
```

**Success - Electromagnetic Lock (observers see):**
```
The SPDR M9 grenade's eight legs telescope outward in a blur of motion, seeking metal across Marcia's plate mail before *SNAPPING* into electromagnetic lock!
```

**Failure - Weak Magnetic Field (victim sees):**
```
The SPDR M9 grenade's legs extend and scrabble frantically across your leather jacket, but the magnetic field is too weak - it bounces away with a frustrated clatter!
```

**Failure - Weak Magnetic Field (thrower sees):**
```
Your SPDR M9 grenade's spider-legs fail to find purchase on Marcia's leather jacket, bouncing off ineffectively!
```

**Failure - Weak Magnetic Field (observers see):**
```
The SPDR M9 grenade's articulated legs scrape and skitter across Marcia's leather jacket before losing grip and clattering away!
```

**Failure - No Armor (victim sees):**
```
The SPDR M9 grenade strikes your chest and its legs extend desperately, seeking metal that isn't there - it bounces away with a frustrated whir of servos!
```

**Failure - No Armor (thrower sees):**
```
Your SPDR M9 grenade's electromagnetic sensors find no ferrous surface on Marcia's chest - the spider-legs retract as it falls away!
```

**Failure - No Armor (observers see):**
```
The SPDR M9 grenade's articulated legs extend and search frantically across Marcia's chest before retracting in defeat!
```

**Color Usage:**
- Victim's success message uses combat red (`|r...|n`) for entire message
- All other messages use default colors
- No excessive color highlighting - maintains professional combat narrative

---

## 1. Armor/Clothing Material Properties

### New Attributes

Every armor/clothing item will have two new attributes:

```python
armor.db.metal_level (integer 0-10)
# Represents the amount of metal in the item
# 0 = No metal whatsoever
# 1-3 = Minimal metal (buckles, rivets, small fasteners)
# 4-6 = Moderate metal (metal plates, reinforcements, chainmail sections)
# 7-9 = Heavy metal (predominantly metal construction)
# 10 = Pure metal (entirely metal construction)

armor.db.magnetic_level (integer 0-10)  
# Represents how magnetically responsive the metal is
# 0 = Non-magnetic (no ferrous metals - aluminum, titanium, synthetic, cloth, leather)
# 1-3 = Weakly magnetic (stainless steel, treated/alloyed metals with low iron content)
# 4-6 = Moderately magnetic (mild steel, some carbon steel)
# 7-9 = Highly magnetic (carbon steel, most ferrous alloys)
# 10 = Pure ferrous metal (raw iron, unalloyed steel)
```

### Material Examples

**Non-Magnetic Materials:**
- Cloth/Leather: metal=0, magnetic=0
- Synthetic fabrics: metal=0, magnetic=0
- Aluminum plate: metal=8, magnetic=0
- Titanium plate: metal=9, magnetic=0
- Ceramic plate: metal=9, magnetic=0
- Brass: metal=7, magnetic=0

**Weakly Magnetic:**
- Stainless steel (304): metal=9, magnetic=2
- Stainless steel (430): metal=9, magnetic=3
- Bronze with steel fasteners: metal=4, magnetic=2

**Moderately Magnetic:**
- Mild steel plate: metal=9, magnetic=5
- Mixed steel/aluminum: metal=7, magnetic=4
- Treated carbon steel: metal=8, magnetic=6

**Highly Magnetic:**
- Carbon steel plate: metal=9, magnetic=8
- Iron plate: metal=10, magnetic=10
- Ferrous alloy armor: metal=9, magnetic=7

**Important Notes:**
- Titanium is NOT magnetic (magnetic=0) despite being metal
- Aluminum is NOT magnetic (magnetic=0) despite being metal
- Ceramic plates are NOT magnetic (magnetic=0) despite being hard/protective
- Only ferrous metals (iron-containing) are magnetic
- Builder responsibility to assign appropriate values

---

## 2. Sticky Grenade Properties

### No separate typeclass

There is no `StickyGrenade` class. The SPDR M9 is an ordinary explosive `Item`: the `STICKY_GRENADE` prototype in `world/prototypes.py` has `EXPLOSIVE_BASE` as its parent and sets `is_sticky` and `magnetic_strength`.

### Attributes

```python
grenade.db.is_sticky = True  # Boolean flag identifying sticky grenades
grenade.db.magnetic_strength = integer (1-10)  # Magnet power level

# Stuck state tracking
grenade.db.stuck_to_location = "body_location_string" or None  # e.g., "chest", "left_arm"
grenade.db.stuck_to_armor = Armor object or None  # The specific armor piece it's stuck to
```

### Magnetic Strength Levels

```
Higher strength is pickier: the armor needs magnetic_level >= strength - 3
and metal_level >= strength - 5 (calculate_stick_chance).
Strength 3 or less: every garment passes, even cloth (40% at 0/0).
Strength 5: magnetic_level >= 2.
Strength 8 (the SPDR M9): magnetic_level >= 5 and metal_level >= 3.
```

---

## 3. Stick Mechanics

### Stick Chance Calculation (Option C - Realistic)

```python
def calculate_stick_chance(grenade, armor):
    """
    Calculate probability that grenade will stick to armor.

    Note: the shipped signature is ``calculate_stick_chance(grenade, armor)``.
    ``grenade_strength`` is read from ``grenade.db.magnetic_strength`` and
    ``metal_level`` / ``magnetic_level`` are read from ``armor`` (including the
    highest values across installed plates for plate carriers).

    Requirements:
    - Magnetic level must be sufficient (ferrous metal present)
    - Metal level provides surface area for attachment
    - Both must meet minimum thresholds

    Returns: integer 0-95 (percentage chance)
    """
    grenade_strength = grenade.db.magnetic_strength or 5
    metal_level = armor.db.metal_level or 0
    magnetic_level = armor.db.magnetic_level or 0

    # THRESHOLD CHECK: magnetic enough AND enough metal surface?
    if magnetic_level < (grenade_strength - 3) or metal_level < (grenade_strength - 5):
        return 0  # Either threshold missed - no stick possible
    
    # CALCULATION: Both thresholds met
    base_chance = 40
    metal_bonus = metal_level * 5  # 0 to 50 bonus
    magnetic_bonus = magnetic_level * 5  # 0 to 50 bonus
    
    total_chance = base_chance + metal_bonus + magnetic_bonus
    
    # Cap at 95% (always 5% chance of failure for gameplay)
    return min(total_chance, 95)
```

### Example Calculations

**Example 1: Steel Plate Armor**
- metal_level = 9, magnetic_level = 8, grenade_strength = 5
- Thresholds: magnetic (8 >= 2) ✓, metal (9 >= 0) ✓
- Calculation: 40 + (9*5) + (8*5) = 40 + 45 + 40 = 125 → capped at 95%
- Result: 95% stick chance

**Example 2: Cloth Armor**
- metal_level = 0, magnetic_level = 0, grenade_strength = 5
- Thresholds: magnetic (0 >= 2) ✗
- Result: 0% stick chance

**Example 3: Aluminum Plate**
- metal_level = 8, magnetic_level = 0, grenade_strength = 5
- Thresholds: magnetic (0 >= 2) ✗
- Result: 0% stick chance (not magnetic)

**Example 4: Weak Magnet on Iron**
- metal_level = 10, magnetic_level = 10, grenade_strength = 2
- Thresholds: magnetic (10 >= -1) ✓, metal (10 >= -3) ✓
- Calculation: 40 + (10*5) + (10*5) = 40 + 50 + 50 = 140 → capped at 95%
- Result: 95% stick chance

**Example 5: Strong Magnet on Stainless Steel**
- metal_level = 9, magnetic_level = 2, grenade_strength = 8
- Thresholds: magnetic (2 >= 5) ✗
- Result: 0% stick chance (not magnetic enough for strong magnet requirements)

**Example 6: Moderate Setup**
- metal_level = 6, magnetic_level = 5, grenade_strength = 5
- Thresholds: magnetic (5 >= 2) ✓, metal (6 >= 0) ✓
- Calculation: 40 + (6*5) + (5*5) = 40 + 30 + 25 = 95%
- Result: 95% stick chance

---

## 4. Thrown Sticky Grenade Behavior

### Throw Resolution Flow

```
1. Normal throw mechanics (existing system)
   - Throw command executed
   - Target hit/miss: a flat 70% hit chance (resolve_weapon_hit);
     a miss sends the ordinary miss lines and no stick is tried

2. IF grenade.db.is_sticky == True:
   
   a. Hit location is always "chest"
   
   b. Find the outermost worn item covering the chest:
      item = get_outermost_armor_at_location(target, "chest")
      If there is none, the no-armor bounce lines are sent.
      
   c. Only that one item is tried. 📋 UNBUILT (no issue): skipping an
      item that already holds a grenade, and trying inner layers.
      
   d. Calculate stick chance:
      stick_chance = calculate_stick_chance(grenade, item)
      
   e. Roll for stick:
      roll = random(1, 100)
      
      IF roll <= stick_chance:
         ### STICK SUCCESS ###
         establish_stick(grenade, item, "chest"):
         the grenade moves inside the item (grenade.location = item),
         grenade.db.stuck_to_armor = item,
         grenade.db.stuck_to_location = "chest",
         item.db.stuck_grenade = grenade
         
         # Continue countdown normally
         # Send stick success messages
         
      ELSE:
         ### STICK FAILURE ###
         # Grenade bounces off (stick failure lines)
         # The target also takes 1d6 + the grenade's damage (default 1)
         # on the chest, with the ordinary 'strikes' lines
         # Grenade lands loose in the room; countdown continues
```

### Multi-Layer Armor Handling

📋 UNBUILT (no issue). As built, only the outermost layer is tried, once, and a failed roll bounces (resolve_weapon_hit). The sketch below of trying each layer inward is not in the game:

```python
# Example: Character has jacket (layer 3) and shirt (layer 2) both covering chest
# Grenade hits chest

layers_on_chest = [
    (jacket, layer=3, metal=2, magnetic=1),
    (shirt, layer=2, metal=0, magnetic=0)
]

# Check outermost first
for item in sorted(layers_on_chest, key=lambda x: x.layer, reverse=True):
    if item.already_has_grenade:
        continue  # Skip, try next layer
    
    stick_chance = calculate_stick_chance(grenade, item)
    if roll_stick(stick_chance):
        stick_to(item)
        break
    # If miss, try next layer inward
```

---

## 5. Rigged Sticky Grenade Behavior

### Rig Trigger Flow

When someone trips a rigged sticky grenade (`check_rigged_grenade` in `commands/explosion_utils.py`), the trap's 1-second fuse starts (`TRAP_FUSE_TIME`) and the grenade drops into the room. The person who rigged it does not trip it.

It does not target the person who tripped it. It picks the most magnetic other person in the room whom the person who tripped it can perceive, judged by the outermost worn armor on the chest (`select_most_magnetic_target_in_room`). It then makes the same hit-and-stick attempt as a throw (`resolve_weapon_hit`): 70% to hit, chest only, outermost armor only, with the throw's messages.

If nobody qualifies, it behaves as an ordinary rigged grenade and the person who tripped it is in its blast. A rigged grenade counts down without per-second lines (`start_standalone_grenade_ticker`).

---

## 6. Stuck Grenade State Management

### State Properties & Object Representation

**IMPLEMENTED DESIGN:** Grenade is physically located inside the armor object.

```python
# When grenade sticks to armor:
grenade.location = armor_object            # Physical location (CRITICAL)
grenade.db.stuck_to_armor = armor_object   # State tracking reference
grenade.db.stuck_to_location = "chest"     # Body location string
armor.db.stuck_grenade = grenade           # Bidirectional reference
```

**Stick Initialization (On Stick Success):**
```python
def establish_stick(grenade, armor, hit_location):
    """
    Establish magnetic bond between grenade and armor.
    Called after successful stick roll.
    """
    # Set physical location
    grenade.location = armor
    
    # Set state tracking
    grenade.db.stuck_to_armor = armor
    grenade.db.stuck_to_location = hit_location
    # Bidirectional reference
    armor.db.stuck_grenade = grenade
    
    # Grenade is now in armor.contents
    # When armor moves, grenade automatically moves with it
```

**Why This Design Works:**
- ✅ Grenade physically in armor (armor.contents)
- ✅ Moves automatically when armor moves
- Room found by `get_explosion_room`, which walks grenade → armor → wearer (if any) → room
- ✅ Integrates with existing explosion code (see Explosion Behavior below)
- ✅ Armor can be queried for stuck grenades
- ✅ Character relationship derived from armor.location

### Visual Representation

**In Character Inventory:** 📋 UNBUILT (no issue)
```
> inventory
You are carrying:
  a frag grenade (STUCK TO YOUR CHEST - 3 seconds!)
  a jacket (has stuck grenade!)
  a knife
```

**In Armor Display:** 📋 UNBUILT (no issue)
```
> armor comprehensive
╔════════════════════════════════════════════════════════╗
║              Armor Comprehensive Display              ║
╠════════════════════════════════════════════════════════╣
║                                                        ║
║ Location      Equipment           Rating               ║
║ ──────────────────────────────────────────────────    ║
║ Torso         jacket (III)         [!!! GRENADE !!!]  ║
║ Left Arm      sleeve (II)                              ║
║ Right Arm     sleeve (II)                              ║
║                                                        ║
╚════════════════════════════════════════════════════════╝
```

**In Room:** 📋 UNBUILT (no issue)
```
> look
A dark alley
This is a narrow alleyway between two buildings.
Obvious exits: north, south
You see:
  John is here (wearing jacket with LIVE GRENADE stuck to it!)
  a jacket (with LIVE GRENADE magnetically clamped - 2 seconds!)
```

**Item Appearance:**
Looking at an item with a grenade clamped to it (`Item.return_appearance` in `typeclasses/items.py`) adds, while the fuse runs, a red banner between rules of `=`: "!!! WARNING: LIVE GRENADE MAGNETICALLY CLAMPED TO THIS ITEM !!!" and "EXPLOSION IN N SECONDS!". When the grenade is not counting down it adds "A <grenade> is magnetically clamped to this item."

### Movement Behavior

The grenade sits in the armor, and the armor sits in its wearer's contents, so both move with the wearer with no extra code. 📋 UNBUILT (no issue): no arrival line is shown when someone walks in with a grenade stuck to them.

### Countdown Behavior

A grenade armed by `pull` or by a remote detonator counts down in `start_grenade_ticker` (`commands/explosion_utils.py`). Each second, while it is stuck to armor:

- if the armor is on a character (worn or carried), that character sees `|R*** N SECONDS ***|n <grenade> magnetically clamped to your <armor>!` and the room sees `<name> has a live <grenade> magnetically stuck to their <armor>! N seconds remaining!`;
- if the armor is lying in a room, the room sees `A <grenade> magnetically stuck to a <armor> ticks down: N seconds!`.

A grenade that is not stuck, in hand or on the ground, counts down silently. A rigged grenade uses `start_standalone_grenade_ticker`, which sends no per-second lines. Removing, dropping or picking up the armor does not reset or stop the countdown: the grenade explodes at 0 wherever the armor is.

The timelines below are illustrations; their "beeps" lines stand for the lines above.

**Example Timeline (Successful Escape):**
```
T=8s: Grenade sticks to worn jacket
      "The frag grenade CLAMPS onto your jacket!" 
T=7s: "The grenade stuck to your jacket beeps: 7 seconds!"
T=6s: "The grenade stuck to your jacket beeps: 6 seconds!"
T=5s: Player removes jacket (grenade STILL stuck to jacket!)
      "You frantically RIP OFF your jacket and hurl it to the ground!"
      "The grenade remains MAGNETICALLY CLAMPED to it!"
T=4s: "The frag grenade on the discarded jacket beeps: 4 seconds!"
      (Character STILL IN PROXIMITY - still in danger!)
T=3s: "The frag grenade on the discarded jacket beeps: 3 seconds!"
T=2s: Player flees north
      "You flee north!"
T=1s: "The frag grenade on the jacket beeps: 1 seconds!" (in old room)
T=0s: BOOM! (Grenade explodes in old room, player is safe)
```

**Example Timeline (Stayed Too Long - Death):**
```
T=8s: Grenade sticks to worn jacket
T=7s: "The grenade stuck to your jacket beeps: 7 seconds!"
T=6s: Player removes jacket
      "You frantically RIP OFF your jacket!"
T=5s: "The frag grenade on the discarded jacket beeps: 5 seconds!"
      (Player looking through inventory, distracted...)
T=4s: "The frag grenade on the discarded jacket beeps: 4 seconds!"
T=3s: "The frag grenade on the discarded jacket beeps: 3 seconds!"
T=2s: "The frag grenade on the discarded jacket beeps: 2 seconds!"
      (Player still in same room...)
T=1s: "The frag grenade on the discarded jacket beeps: 1 seconds!"
T=0s: BOOM! Player takes FULL grenade damage (in proximity to explosion)
      Only the grenade is destroyed; the jacket is left behind.
```

**Example Timeline (Picked Up Jacket - Very Bad):**
```
T=8s: Grenade sticks to worn jacket
T=7s: Player removes jacket
T=6s: Player picks up jacket (grenade still stuck!)
      "You pick up the jacket - the grenade is STILL STUCK to it!"
T=5s: "The frag grenade stuck to the jacket in your hands beeps: 5 seconds!"
T=4s: Player tries to drop jacket
      "You drop the jacket!"
T=3s: Player flees north
T=2s: Player is safe in new room
T=1s: Grenade explodes in old room
      Player survives!
```

### Explosion Behavior

A stuck grenade explodes through `explode_standalone_grenade` (`commands/explosion_utils.py`):

- If the armor is on a character (worn or carried), that character takes double blast damage and sees `|R*** CATASTROPHIC EXPLOSION! ***|n`, `The <grenade> magnetically clamped to your <armor> DETONATES against your <location>!` and `You take N damage!`. The room sees `<name>'s <grenade>, magnetically clamped to their <armor>, EXPLODES in a devastating blast!`. Everyone else in proximity takes half damage. There is no human-shield check.
- If the armor is lying in a room, the room found by `get_explosion_room` gets the standard explosion line and adjacent rooms are warned. Everyone in proximity takes full damage, with the human-shield modifiers.

Deleting the grenade severs the bond (`Item.at_object_delete` → `break_stick`). The armor is left behind.

**Explosion Scenarios:**

1. **Grenade stuck to worn armor:**
   - Double damage to wearer (explosion in inventory)
   - Half damage to nearby characters (body shields)
   
2. **Grenade stuck to armor on ground:**
   - Full damage to all in proximity (normal ground explosion)
   - Uses existing proximity system
   
3. **Grenade stuck to armor in someone's inventory (carried, not worn):**
   - Double damage to carrier (explosion in hands)
   - Half damage to nearby characters (body shields)

### Object Hierarchy Diagram

**When Grenade Stuck to Worn Armor:**
```
Room
└── Character (John)
    ├── .location = Room
    ├── .contents = [jacket, knife]  # Note: grenade NOT here
    └── .ndb.in_proximity_with = [OtherCharacter]
        
    Armor (jacket) - WORN
    ├── .location = Character (John)
    ├── .contents = [grenade]              # Grenade is IN the armor
    └── .db.stuck_grenade = Grenade (frag)
        
        Grenade (frag grenade) - STUCK TO JACKET
        ├── .location = Armor (jacket)           # IN the armor item
        ├── .db.stuck_to_armor = Armor (jacket)  # Which armor piece
        └── .ndb.countdown_remaining = 3         # Timer state
```

**When Armor Removed and Dropped:**
```
Room
├── Character (John)
│   ├── .contents = [knife]  # Jacket removed from inventory
│   └── .ndb.in_proximity_with = []
│
└── Armor (jacket) - ON GROUND
    ├── .location = Room              # Dropped on ground
    ├── .contents = [grenade]         # Grenade still IN the armor
    └── .db.stuck_grenade = Grenade (frag)
        
        Grenade (frag grenade) - STILL STUCK
        ├── .location = Armor (jacket)     # Still in armor
        ├── .db.stuck_to_armor = Armor (jacket)
        └── .ndb.countdown_remaining = 1   # Still ticking
```

**When Character Flees (After Remove + Drop):**
```
Old Room
└── Armor (jacket) - ON GROUND
    ├── .location = Old Room
    └── .contents = [grenade]
        
        Grenade (frag grenade) - BOOM!
        └── Explodes in Old Room
            Character is SAFE in New Room

New Room
└── Character (John) - SAFE
    └── No proximity to grenade
```

### State Queries

**Finding stuck grenades on a character:** `get_stuck_grenades_on_character(character)` (`world/combat/explosives.py`) returns `(grenade, armor, body_location)` tuples for every item the character holds, worn or carried, that has a grenade stuck to it.

**Finding the grenade on a specific armor item:** it is `armor.db.stuck_grenade`.

**Finding the room for the explosion:** `get_explosion_room(grenade)` (`world/combat/explosives.py`) returns the Room the grenade would explode in, walking up through the armor and its wearer, or None. Whether a character holds it is worked out separately in `explode_standalone_grenade`.

**Finding who the blast hits:** `get_unified_explosion_proximity(grenade)` (`commands/explosion_utils.py`): the grenade's own proximity list plus those people's combat proximity, limited to people in the blast room.

---

## 7. Armor Removal Integration

### Key Feature: Remove Armor (Grenade Stays Stuck)

**CRITICAL DESIGN:** Grenade is magnetically bonded to the armor, NOT the person. Removing armor does NOT break the magnetic bond.

```python
# When character attempts to remove armor piece:
> remove jacket

# Check if armor has stuck grenade:
IF jacket.db.stuck_grenade:
    grenade = jacket.db.stuck_grenade
    
    # Allow removal (this is a FEATURE)
    # BUT grenade stays magnetically bonded to armor!
    
    # Physical location: NO CHANGE
    # jacket.location = character             # remove only clears the worn record; the jacket stays in your inventory
    # grenade.location = jacket               # NO CHANGE - still stuck to armor!
    
    # Stuck state: NO CHANGE
    # grenade.db.stuck_to_armor = jacket      # Still stuck!
    # jacket.db.stuck_grenade = grenade       # Still has grenade!
    
    # Messages (CmdRemove.func in commands/CmdClothing.py):
    # - to the wearer, when the fuse is live: a red CRITICAL WARNING box with the
    #   countdown, the body location, "Removing this armor will NOT break the
    #   magnetic bond!" and "DROP ARMOR AND FLEE TO SURVIVE!"
    # - to the wearer, when it is not live: a yellow "*** WARNING ***" block
    # - to the room: "{actor} carefully removes their {item} - the magnetically
    #   attached {a grenade} moves with it!"
    
    # CRITICAL: Character is STILL IN DANGER!
    # - Jacket still in the character's inventory
    # - Grenade still stuck to jacket (in jacket.contents)
    # - If it explodes now, the character is its holder: double damage
    # - Character's body location now exposed
    # - Must drop the jacket and leave the room to be safe
```

### Multi-Step Escape Requirement

**To survive a stuck grenade, character must:**

```python
# Step 1: Remove armor (grenade still dangerous!)
> remove jacket
# The wearer sees the stuck-grenade warning (CmdRemove.func)
# State: jacket still in your inventory, grenade stuck to it.
# If it goes off now, you are its holder: double damage

# Step 2: Drop it
> drop jacket
# State: jacket on the floor, grenade stuck to it, you still in the room

# Step 3: FLEE to another room (get out of blast radius!)
> north
# State: Character safe in new room, grenade explodes in old room

# OR

# Step 2: Throw the jacket away instead of dropping it
> wield jacket
> throw jacket to north
# State: Jacket+grenade in a different room, character safe

# OR

# Step 2: Wait and hope (BAD IDEA)
> (do nothing)
# BOOM! The jacket is still in your inventory: double damage
```

### What Happens If You Pick Up Armor With Stuck Grenade?

```python
# Scenario: Armor on ground with stuck grenade
> look
You see:
  a jacket
# 📋 UNBUILT (no issue): no stuck-grenade marker in the room listing.
# `look jacket` shows the live-grenade warning and the seconds left
# (Item.return_appearance).

> get jacket
# Allowed, with no warning (📋 UNBUILT (no issue): pick-up warning)

# State change:
# jacket.location = character (in inventory)
# grenade.location = jacket (still stuck to armor)
# grenade.db.stuck_to_armor = jacket (still stuck)

# If grenade explodes while in inventory:
# Explosion occurs "in hands" (double damage to character)
# Because grenade.location.location = character
```

### Armor Removal Flow Diagram

```mermaid
graph TD
    INIT["INITIAL STATE\nGrenade stuck to jacket on Character"]
    INIT -->|"> remove jacket"| PROC

    PROC["REMOVE COMMAND PROCESSING\n1. Detect jacket.db.stuck_grenade\n2. Warn the wearer and the room\n3. Take the jacket off\n4. Grenade STAYS stuck (magnetic bond)\n5. Jacket stays in your inventory"]
    PROC --> AFTER

    AFTER["AFTER REMOVE\nJacket in your inventory, grenade still stuck\nIf it goes off now: double damage"]
    AFTER -->|"> drop jacket"| DROPPED

    DROPPED["AFTER DROP\nJacket on the floor, grenade still stuck\nCharacter still in the room — DANGER"]
    DROPPED --> GET
    DROPPED --> FLEE

    GET["&gt; get jacket\nBAD IDEA\nGrenade still stuck\nNow in YOUR inventory\nDouble damage"]
    FLEE["&gt; north (FLEE)\nCharacter flees\nGrenade + jacket stay in old room\nExplodes there — you are SAFE"]
```

### No Special "Remove Grenade" Command Needed

The existing `remove` command takes the garment off with the grenade still on it. `remove <item>` warns about the grenade; `remove all` takes the garment off too, but shows no stuck-grenade warning. This creates interesting tactical gameplay:

**Scenario 1: Light Armor**
- Sticky grenade on cloth jacket
- Quick to remove
- Minor loss of protection
- Grenade safely discarded

**Scenario 2: Heavy Armor**
- Sticky grenade on plate carrier
- Removing plate carrier exposes vital torso
- Significant loss of protection
- Difficult tactical choice

**Scenario 3: Multiple Layers**
- Sticky grenade on outer jacket
- Must remove jacket (easy)
- Inner layers still provide protection
- Good situation

**Scenario 4: Inner Layer**
- Sticky grenade on undershirt (somehow stuck through outer layer gap)
- Must remove outer layers first
- Then remove undershirt
- Time-consuming
- Dangerous situation

---

## 8. Targeting Priority System

### Multi-Target Scenarios

When no target is named (an untargeted throw, `_pick_room_target` in `commands/CmdThrow.py`) or a rigged sticky grenade is triggered (`check_rigged_grenade` in `commands/explosion_utils.py`), the grenade picks its target with `select_most_magnetic_target_in_room` (`world/combat/throwing.py`):

1. It skips the thrower, or the one who triggered the trap, and anyone that person cannot perceive.
2. It looks only at each person's outermost worn garment on the chest. On a plate carrier, the installed plates' highest values count.
3. The garment must pass both stick thresholds.
4. The highest `magnetic_level` wins. On a tie, the first person found wins.

📋 UNBUILT (no issue): preferring targets and garments without a stuck grenade, and scoring by metal level. The sketch below is not in the code:

```python
def select_best_stick_target(potential_targets, grenade):
    """
    From multiple potential targets, select best one for sticking.
    Used in area effect grenades or multi-target scenarios.
    """
    
    scored_targets = []
    
    for target in potential_targets:
        score = 0
        
        # Check if target already has ANY stuck grenades
        has_stuck_grenade = check_for_stuck_grenades(target)
        if not has_stuck_grenade:
            score += 100  # STRONG preference for clean targets
        
        # Check armor quality
        best_armor = find_best_armor_for_sticking(target, grenade)
        if best_armor:
            metal_score = best_armor.db.metal_level * 5
            magnetic_score = best_armor.db.magnetic_level * 5
            score += metal_score + magnetic_score
        
        scored_targets.append((target, score, best_armor))
    
    # Return highest scoring target
    return max(scored_targets, key=lambda x: x[1])
```

### Per-Item Limitation

```python
# Only ONE grenade can stick to each armor/clothing item
# This prevents unrealistic "covered in grenades" situations
# 📋 UNBUILT (no issue): not enforced. resolve_weapon_hit never checks
# armor.db.stuck_grenade, and establish_stick overwrites it: a second
# grenade that sticks to the same garment replaces the first in
# armor.db.stuck_grenade, and the first stays inside the garment, still armed.

armor_item.db.stuck_grenade = grenade_object or None

# When checking if grenade can stick (📋 UNBUILT (no issue); today only the
# outermost worn garment is tried, once):
if armor_item.db.stuck_grenade is not None:
    # Skip this armor piece
    # Try next layer inward
    # Or try different target entirely
```

---

## 9. Message System

### Message Categories

> **Drift (2026-09-12): these five dictionaries are v1.0 design text and do not exist in the code.** No `magnetic THUNK`, `CLAMPS onto`, `SPRINGS` or "DETONATES with devastating force" string appears anywhere in the repo (bare `THUNK` does occur, but only as `*CHLACK-THUNK*` in `world/combat/messages/semi-auto_shotgun.py`, an unrelated weapon). The shipped messages are (a) the spider-leg set quoted earlier in this same spec under "Combat Messages", which matches `world/combat/throwing.py` (`resolve_weapon_hit`) verbatim; (b) the stuck-countdown line in `commands/explosion_utils.py` (`start_grenade_ticker`); (c) the stuck-explosion lines in `commands/explosion_utils.py` (`explode_standalone_grenade`, holder branch); (d) the `remove` warning panel in `commands/CmdClothing.py` (`CmdRemove.func`). Treat the "Combat Messages" section above as the authority and this section as superseded design notes.

**Stick Success (Thrown):**
```python
{
    'attacker_msg': "Your {grenade} |rCLAMPS|n onto {target}'s {location} with a magnetic |rTHUNK|n!",
    'victim_msg': "The {grenade} |rCLAMPS|n onto your {location} with a magnetic |rTHUNK|n!",
    'observer_msg': "The {grenade} |rCLAMPS|n onto {target}'s {location} with a magnetic |rTHUNK|n!"
}
```

**Stick Success (Rigged):**
```python
{
    'victim_msg': "As you pass through, a {grenade} |rSPRINGS|n out and |rCLAMPS|n onto your {location}!",
    'observer_msg': "A {grenade} |rSPRINGS|n out and |rCLAMPS|n onto {victim}'s {location}!"
}
```

**Stick Failure (Bounces Off):**
```python
{
    'attacker_msg': "Your {grenade} |ybounces off|n {target}'s {location} and clatters to the ground.",
    'victim_msg': "The {grenade} |ybounces off|n your {location} and clatters to the ground.",
    'observer_msg': "The {grenade} |ybounces off|n {target}'s {location} and clatters to the ground."
}
```

**Stuck Countdown (Each Tick):**
```python
{
    'victim_msg': "The {grenade} |rSTUCK TO YOUR {location}|n beeps |Rmenacingly|n: |Y{countdown}|n seconds!",
    'observer_msg': "The {grenade} |rstuck to {victim}'s {location}|n beeps |Rmenacingly|n: |Y{countdown}|n seconds!"
}
```

**Stuck Explosion:**
```python
{
    'victim_msg': "The {grenade} |rSTUCK TO YOUR {location}|n |RDETONATES|n with |Rdevastating force|n!",
    'observer_msg': "The {grenade} |rstuck to {victim}'s {location}|n |RDETONATES|n with |Rdevastating force|n!"
}
```

**Armor Removal with Stuck Grenade:**
```python
{
    'character': "You frantically |yRIP OFF|n your {armor} and hurl it away! The stuck {grenade} beeps |Rmenacingly|n from the discarded armor.",
    'observer': "{character} frantically |yRIPS OFF|n their {armor} and hurls it away! A stuck {grenade} beeps |Rmenacingly|n from the discarded armor."
}
```

---

## 10. Integration Points & Files

### Files Requiring Modification

**typeclasses/items.py**
- Add metal_level attribute to base Item class (default 0)
- Add magnetic_level attribute to base Item class (default 0)
- These will be inherited by all armor/clothing
- Add return_appearance() enhancement to show stuck grenades

```python
# In Item class:
class Item(DefaultObject):
    metal_level = AttributeProperty(0, autocreate=True)
    magnetic_level = AttributeProperty(0, autocreate=True)
    
    def return_appearance(self, looker):
        """Enhanced to show stuck grenades."""
        # ... existing code ...
        # Add stuck grenade check
```

**Sticky grenade prototype** (there is no sticky-grenade typeclass and no `typeclasses/explosives.py`; the stick logic lives in `world/combat/explosives.py`)
- A sticky grenade is any explosive Item with `is_sticky = True`
- The SPDR M9 is the `STICKY_GRENADE` prototype in `world/prototypes.py` (parent `EXPLOSIVE_BASE`, typeclass `typeclasses.items.Item`)
- It sets `is_sticky`, `magnetic_strength` and the stuck-state attributes `stuck_to_armor` and `stuck_to_location`

```python
STICKY_GRENADE = {
    "prototype_parent": "EXPLOSIVE_BASE",
    "key": "SPDR M9 grenade",
    # ...
    "is_sticky": True,
    "magnetic_strength": 8,
    "stuck_to_armor": None,      # runtime
    "stuck_to_location": None,   # runtime
}
```

**world/combat/throwing.py**
- **Location:** `resolve_weapon_hit`, reached from `handle_landing` when a sticky grenade lands on a target
- Add stick check for sticky grenades
- Integrate stick success/failure handling
- Add stick-specific messages
- Set grenade.location = armor on stick success

```python
# After hit determination:
if obj.db.is_sticky:
    # Get armor covering hit location
    armor = get_outermost_armor_at_location(target, hit_location)
    if armor:  # no check for a grenade already stuck to it (one per garment: 📋 UNBUILT (no issue))
        stick_chance = calculate_stick_chance(obj, armor)
        if random.randint(1, 100) <= stick_chance:
            establish_stick(obj, armor, hit_location)
            # Send stick success messages
        else:
            # Send stick failure messages (bounce off)
```

**commands/explosion_utils.py - Explosion Code**
- **Location:** In explode_standalone_grenade() function
- **Hook:** Add armor hierarchy check before Character check
- Modify holder detection to handle armor hierarchy

```python
# In explode_standalone_grenade():
holder = None
if grenade.location:
    from typeclasses.characters import Character
    from typeclasses.items import Item
    
    # NEW: Check if grenade is in armor
    if isinstance(grenade.location, Item):
        armor = grenade.location
        if armor.location and isinstance(armor.location, Character):
            holder = armor.location
    # EXISTING: Check if grenade directly in character
    elif isinstance(grenade.location, Character):
        holder = grenade.location
```

**commands/explosion_utils.py** (`check_rigged_grenade`; the `rig` command is `CmdRig` in `commands/CmdExplosives.py`)
- A triggered rigged sticky grenade goes for the most magnetic person in the room other than the one who triggered it (`select_most_magnetic_target_in_room`)
- The stick attempt uses the thrown-grenade resolver, `resolve_weapon_hit`: its 70% hit roll, the chest, and the thrown-grenade messages
- Rigged-only stick messages: 📋 UNBUILT (no issue)
- The fuse runs on `start_standalone_grenade_ticker`, so a rigged grenade that sticks counts down without the per-second stuck warnings

**commands/CmdClothing.py**
- **Location:** `CmdRemove.func` (the `remove` command)
- When removing armor, check for stuck grenades
- Display warning messages about stuck grenade (`remove all` skips them)
- Grenade stays in armor, and the armor stays in the wearer's inventory (`remove_item` only clears the worn record)

```python
# In remove command:
if armor.db.stuck_grenade:
    # Warn the wearer (red CRITICAL WARNING box with the countdown, or a
    # yellow *** WARNING *** block when the grenade is not live) and the room
    # The armor stays in the wearer's inventory; the grenade stays in it
```

**world/combat/explosives.py**
- Add calculate_stick_chance() function
- Add get_stuck_grenades_on_character() helper
- Add get_explosion_room() helper (for hierarchy traversal)
- Add establish_stick() helper
- Untargeted and rigged sticky grenades pick their target with `select_most_magnetic_target_in_room` in `world/combat/throwing.py` (there is no `find_best_stick_target`)

```python
def calculate_stick_chance(grenade, armor):
    """Calculate stick probability. Returns 0-95."""
    # See Section 3 for full implementation
    
def get_explosion_room(grenade):
    """Get the room the blast happens in, or None."""
    # See Section 6.4 for full implementation
    
def establish_stick(grenade, armor, hit_location):
    """Establish magnetic bond between grenade and armor."""
    # See Section 6.1 for full implementation
```

**typeclasses/characters.py**
- **Optional, 📋 UNBUILT (no issue):** Add movement hook to display warning messages
- **Location:** In at_post_move() method
- Grenades automatically move (in armor, armor in character)
- Only need to add warning messages

```python
def at_after_move(self, source_location, **kwargs):
    """Warn room about stuck grenades."""
    # Check worn armor for stuck grenades
    for armor in self.contents:
        if armor.db.stuck_grenade:
            self.location.msg_contents(
                f"|r{self.key} enters with a live grenade stuck to their {armor.key}!|n",
                exclude=self
            )
```

---

## 10.5 Critical Helper Functions

These utility functions are essential for the sticky grenade system:

### calculate_stick_chance()
```python
def calculate_stick_chance(grenade, armor):
    """
    Calculate probability that grenade will stick to armor.

    Shipped signature is ``(grenade, armor)``. Internally derives
    ``grenade_strength`` from ``grenade.db.magnetic_strength`` and
    ``metal_level`` / ``magnetic_level`` from ``armor``.

    Returns:
        int: Stick chance percentage (0-95)
    """
    grenade_strength = grenade.db.magnetic_strength or 5
    metal_level = armor.db.metal_level or 0
    magnetic_level = armor.db.magnetic_level or 0

    # PLATE CARRIER: if armor.db.is_plate_carrier, take the highest
    # metal_level and magnetic_level across its installed plates

    # THRESHOLD CHECK: Is material magnetic enough?
    # THRESHOLD CHECK: Is there enough metal surface area?
    if (magnetic_level < (grenade_strength - 3)
            or metal_level < (grenade_strength - 5)):
        return 0  # Either threshold fails - no stick possible
    
    # CALCULATION: Both thresholds met
    base_chance = 40
    metal_bonus = metal_level * 5  # 0 to 50 bonus
    magnetic_bonus = magnetic_level * 5  # 0 to 50 bonus
    
    total_chance = base_chance + metal_bonus + magnetic_bonus
    
    # Cap at 95% (always 5% chance of failure for gameplay)
    return min(total_chance, 95)
```

### get_explosion_room()
```python
def get_explosion_room(grenade):
    """
    Get the room where the blast happens: grenade -> garment -> wearer -> room.

    Returns:
        Room, or None if what it reaches is not a Room.
        (The carrier is found separately, in explode_standalone_grenade.)
    """
    location = grenade.location if grenade else None

    # Stuck to a garment: go up one level
    if isinstance(location, Item):
        location = location.location

    # Worn or carried: go up to the room
    if isinstance(location, Character):
        location = location.location

    return location if isinstance(location, Room) else None
```

The explosion uses it to address the room's explosion message and to drop
anyone standing in another room from the damage list
(`get_unified_explosion_proximity`, #2490, #2549).

### establish_stick()
```python
def establish_stick(grenade, armor, hit_location):
    """
    Establish magnetic bond between grenade and armor.

    Args:
        grenade: sticky grenade (an explosive Item with is_sticky)
        armor: Armor/Item object
        hit_location: String like "chest"

    Returns:
        bool: True on success, False on invalid input
    """
    # Clear an earlier bond of this same grenade, if any

    # Set physical location (CRITICAL)
    grenade.location = armor

    # Set state tracking
    grenade.db.stuck_to_armor = armor
    grenade.db.stuck_to_location = hit_location

    # Bidirectional reference (overwrites any grenade already stuck to this armor)
    armor.db.stuck_grenade = grenade

    # Grenade is now in armor.contents
    # When armor moves, grenade automatically moves with it
    return True
```

### get_stuck_grenades_on_character()
```python
def get_stuck_grenades_on_character(character):
    """
    Get every grenade stuck to an item the character holds or wears.

    Args:
        character: Character object (anything else returns [])

    Returns:
        list: (grenade, garment, body_location) tuples
    """
    stuck = []
    for item in character.contents:   # carried as well as worn
        if item.db.stuck_grenade:
            grenade = item.db.stuck_grenade
            stuck.append((grenade, item, grenade.db.stuck_to_location or "unknown"))
    return stuck
# No game code calls it; world/combat/utils.py only re-exports it.
```

### get_outermost_armor_at_location()
```python
def get_outermost_armor_at_location(character, body_location):
    """
    Get the outermost armor piece covering a body location.
    
    Args:
        character: Character object
        body_location: String like "chest", "left_arm", etc.
    
    Returns:
        Item: Outermost armor covering location, or None
    """
    if not isinstance(character, Character):
        return None

    outermost, highest_layer = None, -1
    for item in character.get_worn_items(body_location):   # worn only (#2492)
        coverage = item.db.coverage or []
        if coverage and body_location not in coverage:
            continue
        layer = item.layer or 0   # the Item.layer property, not db.clothing_layer
        if layer > highest_layer:
            outermost, highest_layer = item, layer

    return outermost
```

### break_stick()
```python
def break_stick(grenade):
    """
    Break magnetic bond between grenade and armor.
    Used when grenade is forcibly removed or for special circumstances.
    
    Args:
        grenade: StickyGrenade object
    """
    armor = grenade.db.stuck_to_armor
    
    if armor:
        # Clear bidirectional reference
        armor.db.stuck_grenade = None
    
    # Clear grenade state
    grenade.db.stuck_to_armor = None
    grenade.db.stuck_to_location = None
    
    # Move grenade to ground
    if armor and armor.location:
        if isinstance(armor.location, Character):
            grenade.location = armor.location.location  # character's room
        else:
            grenade.location = armor.location  # same room as armor
```

**As shipped** (`world/combat/explosives.py`): the live `break_stick()`
clears the bond only — it does **not** relocate the grenade, because its
callers already own that decision (an explosion deletes the object; a
forcible removal would place it deliberately). It returns `True`/`False`
for "was there a stick to break", so callers need no guard of their own.

**Callers.** `Item.at_object_delete` (`typeclasses/items.py`) calls it
for any stuck grenade being deleted — so the three explosion terminators
in `commands/explosion_utils.py`, a builder's `@destroy` and any sweep all
perform the *Clean up stuck state* step of the §Explosion Behavior
pseudocode above through one hook (#3552; #3412 first wired the three
terminators explicitly). Before that the step was skipped entirely: the garment kept a
`stuck_grenade` Attribute row pointing at the deleted grenade. It was
never player-visible (Evennia unpacks a deleted dbobj as `None`, so the
`is not None` / truthiness guards in `CmdRemove.func`,
`Item.return_appearance` and `get_stuck_grenades_on_character` all
skipped correctly), but severance was an accident of the serializer
rather than something the explosion performed.

**The armor side, and a deleted grenade's fuse (#3561, 2026-09-24).**
The hook above covered only a dying *grenade*. A dying *armor* left the
grenade inside it, and Evennia's `delete()` then runs `clear_contents`,
which evicts contents to their home — for a grenade, which sets none,
Limbo. The still-armed grenade landed there, its per-second warnings
stopped (the stuck check requires its location to be an Item), and it
detonated a few seconds later, gone from the fight. Reachable by a
builder's `@destroy` and by `_perish()` deleting a single-use garment off
a body. **Owner ruling (#3561, 2026-09-25): the grenade goes with the armor** —
"this situation should never occur as is". `Item.at_object_delete`
now severs the bond from the armor side and deletes the grenade before
`clear_contents` can move it.

Deleting a live grenade is only safe if its fuse stops. A pulled pin is a
scheduled timer (`ndb.grenade_timer`), not a flag, and the scheduled tick
holds the Python object after a delete — still truthy, still with an
`ndb` — so the countdown ran on and exploded it (reproduced before the
fix). Every deleted item now stops its fuse through
`commands.explosion_utils.stop_grenade_fuse`, and
both explosion resolvers (`explode_standalone_grenade`,
`trigger_auto_defuse_explosion`) and both ticks refuse a grenade whose
database row is gone (`pk is None`) — the botched-defuse and chain
timers are scheduled outside `ndb.grenade_timer`, so the guard, not the
cancel, is what covers them. The rigged-grenade explosion (`explode_rigged_grenade` in `check_rigged_grenade`) has no such check; it relies on `stop_grenade_fuse` cancelling its timer, which is held in `ndb.grenade_timer`. `stop_grenade_fuse` is the one door
for stopping a fuse: defuse, auto-defuse, both botched-defuse early
triggers, `rig` and the jump sacrifice each carried their own copy, most
calling a bare `cancel()` that could raise on a timer that had just
fired, and `rig` forgot the reference without cancelling at all.

---

## 11. Edge Cases & Special Situations

### Edge Case: Picking Up Armor With Stuck Grenade

**Critical:** Grenade stays magnetically bonded to armor even when picked up.

```python
# Armor on ground with stuck grenade
> look
A dark alley
You see:
  a jacket
# 📋 UNBUILT (no issue): no stuck-grenade marker in the room listing;
# `look jacket` shows the warning (Item.return_appearance)

> get jacket
# Allowed, with no warning (📋 UNBUILT (no issue): pick-up warning)

# Result:
# - jacket.location = character (in inventory)
# - grenade.location = jacket (still stuck to armor)
# - jacket.db.stuck_grenade = grenade (still bonded)
# - grenade.db.stuck_to_armor = jacket (still bonded)

# Character is now carrying a ticking time bomb!
# When it explodes: "explosion in hands" logic (double damage)
```

**Edge Case: Wearing Armor With Stuck Grenade**

```python
# Can you wear armor that has a stuck grenade? (not decided)
# Today: allowed, with no message (wear_item has no stuck-grenade check);
# the grenade then explodes as held, double damage
> wear jacket

# Option A: Prevent wearing
"You can't wear that - there's a |RTICKING GRENADE|n magnetically clamped to it!"

# Option B: Allow wearing (dramatic!)
"You desperately pull on the jacket - the stuck grenade presses against your chest!"
# jacket.location = character (worn)
# grenade.location = jacket (still stuck)
# Grenade explodes on character's body (double damage + specific location)
```

**Edge Case: Dropping Worn Armor With Stuck Grenade**

```python
# drop refuses a worn item; there is no implicit remove
> drop jacket
"You can't put down something you're wearing. Remove it first."
```

**Edge Case: Grenade Stuck to Armor in Someone's Inventory**

```python
# A grenade only sticks to a WORN garment: get_outermost_armor_at_location
# searches get_worn_items, so a carried jacket is never chosen (#2492).
# A carried garment with a grenade already on it (picked up, or removed
# and not dropped) explodes as held:
character.contents = [jacket, knife]   # jacket carried, grenade stuck to it

# Result:
# Character carrying ticking time bomb
# Double damage to the character, half to others in proximity
```

### Edge Case: Character Dies with Stuck Grenade

```python
# Character death handling (existing system handles this via damage)
# No special code needed - grenade just explodes wherever character is
# Corpse takes damage (existing corpse system)
# Nearby characters take damage (existing proximity system)
```

### Edge Case: Grenade Timer Expires While Unstuck

```python
# Removing the garment does not unstick the grenade (CmdRemove.func and
# remove_item never call break_stick). It explodes wherever the garment is.
```

### Edge Case: Multiple Grenades Same Character

```python
# Every stick attempt is at the chest: resolve_weapon_hit sets
# hit_location = "chest" for thrown and rigged grenades alike, so a
# grenade never sticks at left_arm or right_leg.
# 📋 UNBUILT (no issue): hit locations for sticky grenades.
# Intended: one on chest, one on left_arm, one on right_leg
# Each grenade tracked independently
# Each armor piece can have ONE grenade max (📋 UNBUILT (no issue): not enforced)

stuck_grenades = [
    (grenade1, "chest", jacket),
    (grenade2, "left_arm", sleeve),
    (grenade3, "right_leg", pants)
]

# Limit: One grenade per armor item (📋 UNBUILT (no issue))
```

### Edge Case: Layered Armor Same Location

```python
# Grenade hits chest with multiple layers:
# - Plate carrier (outer, metal=9, magnetic=8)
# - Shirt (inner, metal=0, magnetic=0)

# Only the outermost worn garment at the hit location is tried, once
# (resolve_weapon_hit via get_outermost_armor_at_location)
if stick_check(plate_carrier):
    stick_to(plate_carrier)
    # Done
else:
    # Bounce off; the shirt is never tried
    fall_to_ground()
# 📋 UNBUILT (no issue): trying an inner layer when the outer one fails
```

---

## 12. Gameplay Balance

### Tactical Considerations

**Advantages of Sticky Grenades:**
- Guaranteed to track target if stuck
- Cannot be easily discarded
- Forces difficult choices (protection vs. safety)
- Psychological warfare potential
- Effective against heavily armored targets

**Disadvantages of Sticky Grenades:**
- May not stick at all (bounce off)
- Completely ineffective against non-magnetic armor
- Telegraphed threat (visible countdown)
- Can be removed via armor removal
- Requires magnetic properties to function

**Counterplay Options:**
- Wear non-magnetic armor (aluminum, titanium, ceramic plates)
- Wear minimal metal armor (cloth, leather, synthetic)
- Practice quick armor removal
- Use layered armor (sacrifice outer layer)
- Maintain distance from throwers
- Use cover effectively
- Grapple someone as a human shield (only when the grenade is not on anyone: when it is on a garment someone wears or carries, everyone else nearby takes half damage, grapple or not)

### Armor Meta-Game

This system creates interesting armor choices:

**Heavy Metal Armor:**
- Pros: High protection, intimidating
- Cons: Vulnerable to sticky grenades

**Light Non-Magnetic Armor:**
- Pros: Immune to sticky grenades, mobile
- Cons: Less protection overall

**Mixed Armor:**
- Pros: Balance of protection and magnetic resistance
- Cons: Compromise solution

**Layered Armor:**
- Pros: Can sacrifice outer layer to remove grenade
- Cons: Bulky, expensive

---

## 13. Testing Checklist

### Basic Functionality Tests

- [ ] Sticky grenade sticks to steel armor
- [ ] Sticky grenade bounces off cloth armor
- [ ] Sticky grenade bounces off aluminum armor
- [ ] Sticky grenade bounces off titanium armor
- [ ] Countdown continues while stuck
- [ ] Explosion occurs at character location
- [ ] Character moves, grenade follows
- [ ] Removing the garment keeps the grenade on it; the countdown goes on wherever the garment is
- [ ] Multiple grenades on different locations work (📋 UNBUILT (no issue): every stick is at the chest)
- [ ] Only one grenade per armor piece enforced (📋 UNBUILT (no issue))

### Layered Armor Tests

- [ ] Grenade checks outer layer first
- [ ] Grenade tries inner layer if outer fails (📋 UNBUILT (no issue): only the outermost garment is tried)
- [ ] Grenade bounces if all layers fail
- [ ] Removing outer layer with grenade works
- [ ] Inner layer remains after outer removal

### Rigged Grenade Tests

- [ ] Rigged sticky sticks when triggered
- [ ] Rigged sticky bounces if non-magnetic
- [ ] Rigged stick uses correct location
- [ ] Rigged stick messages display correctly

### Edge Case Tests

- [ ] Character with stuck grenade dies → explosion occurs
- [ ] Character with stuck grenade disconnects → handled gracefully
- [ ] Grenade stuck to armor on ground can be examined
- [ ] Multiple characters with stuck grenades in same room
- [ ] Armor with stuck grenade can be picked up (warning: 📋 UNBUILT (no issue))

### Message Tests

- [ ] Stick success messages display correctly
- [ ] Stick failure messages display correctly
- [ ] Stuck countdown messages display correctly
- [ ] Stuck explosion messages display correctly
- [ ] Armor removal messages display correctly

---

## 14. Implementation Priority

### Phase 1: Foundation
1. Add metal_level and magnetic_level to Item class
2. Set default values (0, 0) for backward compatibility
3. Create material reference guide for builders
4. Test attribute system on sample armor

### Phase 2: Sticky Grenade Class
1. Create StickyGrenade typeclass
2. Implement is_sticky flag
3. Implement magnetic_strength attribute
4. Implement stuck_to_* tracking attributes
5. Test grenade creation and attributes

### Phase 3: Stick Calculation
1. Implement calculate_stick_chance() function
2. Test calculation with various inputs
3. Verify threshold logic
4. Verify cap at 95%
5. Document edge cases

### Phase 4: Throw Integration
1. Add stick check to throw command after hit determination
2. Implement stick success path (attach to armor)
3. Implement stick failure path (bounce to ground)
4. Add stick-specific messages
5. Test throwing sticky grenades

### Phase 5: Stuck State Management
1. Implement movement tracking
2. Implement countdown while stuck
3. Implement explosion while stuck
4. Test character movement with stuck grenade
5. Test stuck grenade explosion

### Phase 6: Armor Removal
1. Modify remove/wear commands to check for stuck grenades
2. Keep the grenade on the armor when the armor is removed
3. Add armor-removal-with-grenade messages
4. Test armor removal scenarios

### Phase 7: Rigged Integration
1. Add stick check to rig trigger
2. Implement rigged stick success/failure
3. Test rigged sticky grenades

### Phase 8: Multi-Grenade Support
1. Implement per-item grenade limitation
2. Implement multi-location support
3. Test multiple stuck grenades
4. Test targeting priority

### Phase 9: Polish & Testing
1. Complete message system
2. Handle all edge cases
3. Full integration testing
4. Balance adjustments
5. Documentation for builders

---

## 15. Builder Documentation

### For Game Builders: Setting Armor Properties

When creating armor/clothing items, consider these guidelines:

**Cloth/Fabric Items:**
```python
metal_level = 0
magnetic_level = 0
# Examples: shirts, pants, cloth armor, robes
```

**Leather Items:**
```python
metal_level = 1-2  # Buckles, studs
magnetic_level = 0-1  # Usually non-magnetic
# Examples: leather jackets, leather armor, belts
```

**Synthetic/Modern Materials:**
```python
metal_level = 0-2  # Minimal fasteners
magnetic_level = 0  # Non-magnetic
# Examples: plain kevlar, synthetic jackets, nylon gear
# (a vest with steel trauma plates is magnetic: the shipped "kevlar vest" is metal 7, magnetic 6)
```

**Aluminum/Titanium Armor:**
```python
metal_level = 8-9  # Mostly metal
magnetic_level = 0  # NOT MAGNETIC
# Examples: aluminum plates, titanium armor, aircraft-grade materials
```

**Stainless Steel:**
```python
metal_level = 9
magnetic_level = 2-3  # Weakly magnetic
# Examples: decorative armor, stainless plate, modern tactical gear
```

**Carbon Steel Armor:**
```python
metal_level = 9
magnetic_level = 7-8  # Highly magnetic
# Examples: tactical steel plates, ballistic armor, combat gear
```

**Iron/Medieval Armor:**
```python
metal_level = 10
magnetic_level = 10  # Maximum magnetic
# Examples: iron plates, medieval armor, pure ferrous construction
```

**Ceramic Plates:**
```python
metal_level = 0-3  # Ceramic is not metal; at most a metal backing
magnetic_level = 0  # NOT MAGNETIC
# Examples: ceramic trauma plates (shipped "trauma plate": metal 3, magnetic 0), composite armor
```

### Builder Commands

```
@set armor/metal_level = 5
@set armor/magnetic_level = 3
@spawn sticky_grenade
@set grenade/magnetic_strength = 7
```

---

## 16. Future Enhancements (Post-Implementation)

### Potential Future Features

**Electromagnetic Pulse (EMP):**
- Temporarily disables sticky grenades
- Causes them to fall off
- Tactical counter-play option

**Magnetic Field Generators:**
- Worn device that reduces stick chance
- Drains power over time
- High-tech counter-measure

**Different Magnet Types:**
- Permanent magnets (standard)
- Electromagnets (can be toggled off)
- Shaped charge magnets (directional)

**Armor Coating:**
- Non-stick coating reduces stick chance
- Wears off over time
- Maintenance requirement

**Multiple Grenade Types:**
- Sticky fragmentation
- Sticky incendiary
- Sticky flash-bang
- Sticky smoke

**Advanced Targeting:**
- Ability to aim for specific body location
- Skill check to hit desired location
- Increases tactical depth

---

## Summary

This specification defines a comprehensive magnetic sticky grenade system that:

1. Uses realistic metal/magnetic properties
2. Integrates with existing throw and rig systems
3. Creates tactical gameplay through armor removal
4. Balances effectiveness with counterplay options
5. Maintains backward compatibility
6. Provides clear builder guidelines
7. Handles edge cases appropriately
8. Supports future enhancements

The system is builder-controlled (they set material properties) and creates interesting tactical choices for players without requiring complex new commands.

---

## Summary: Key Architectural Decisions

### Grenade Bonding Mechanics

**CRITICAL DECISION:** Grenade is magnetically bonded to the armor item, NOT to the character.

```python
# Correct hierarchy:
grenade.location = armor           # Grenade physically in armor
armor.location = character OR room # Armor can be worn or on ground
```

**Why This Design:**
1. **Physical Realism:** Magnetic bond is to metal in armor, not to flesh
2. **Persistent Bond:** Removing armor doesn't break magnetic attraction
3. **Proximity Danger:** Dropped armor with grenade still threatens nearby characters
4. **Tactical Depth:** Must remove, drop, AND flee to be safe (3 steps, not 1)
5. **Existing Systems:** Integrates with existing explosion proximity logic

### Escape Sequence

To survive a sticky grenade:
1. **Remove armor** - Grenade stays stuck to armor; the armor stays in your inventory
2. **Drop it** - Armor and grenade on the ground; you are still in the room, still in danger
3. **Flee to safety** - Must leave the room; a blast does not reach another room

**Failed escapes:**
- Remove but don't drop → double damage (you are holding it)
- Drop but don't leave → full damage if you are in its proximity, with human-shield modifiers
- Pick up dropped armor → Now carrying ticking bomb (double damage)
- Wear armor with stuck grenade → Suicide

### Integration Points

- **Existing explosion code** works with `grenade.location.location` hierarchy
- **Proximity system** already handles ground explosions
- **Inventory system** naturally handles armor as container
- **Message system** can detect stuck state via `grenade.db.stuck_to_armor`

---

**Document Version:** 2.0  
**Date:** October 13, 2025  
**Status:** Implementation Ready - Complete  
**Last Updated:** Added implementation details, code hooks, helper functions, and quick reference guide

**Changelog:**
- v1.0: Initial specification with design decisions
- v1.1: Revised to armor-centric bonding model
- v2.0: Added concrete code locations, helper function implementations, quick reference checklist, and armor appearance enhancements
