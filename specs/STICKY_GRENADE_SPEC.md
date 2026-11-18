# SPDR M9 Sticky Grenade System

The SPDR M9 "Spider" is a sticky grenade. It is a repurposed asteroid mining tool that uses electromagnetic adhesion to stick to ferrous metal surfaces: spider-like telescoping legs seek and clamp onto armor according to its metal content and magnetic properties. When it sticks, it is bonded to the garment, not to the person. It goes wherever the garment goes and explodes wherever the garment is when the fuse runs out. To survive it, a character must take the garment off, drop it, and leave the room.

Not everything below is in the game. Behaviour the code does not have is marked `📋 UNBUILT` where it stands.

---

## The grenade

### Narrative identity

**Full Name:** SPDR M9 Spider-Class Magnetic Adhesion Grenade

**Origin:** Designed for breaching and clearing metallic ore deposits in asteroid mining operations. What was once a tool for breaking apart ore-rich asteroids has found a darker purpose in combat scenarios.

**Physical description:**
- Compact black sphere bristling with eight telescoping articulated legs
- Tiny servos activate when thrown, extending legs with mechanical precision
- Electromagnetic tips pulse through leg tips seeking ferrous metal surfaces
- Single-minded purpose of industrial demolition equipment
- Soft blue LED pulses faster as detonation approaches

**Design philosophy:**
- Industrial reliability standards (2% dud chance)
- Mining-grade electromagnets (magnetic_strength=8)
- Longer tactical fuse (10 seconds)
- Enhanced blast damage (30) for ore-breaking capability

### Prototype

There is no `StickyGrenade` class and no sticky-grenade typeclass. A sticky grenade is any explosive `Item` with `is_sticky = True`. The SPDR M9 is the `STICKY_GRENADE` prototype in `world/prototypes.py`, with parent `EXPLOSIVE_BASE` (typeclass `typeclasses.items.Item`). The stick logic lives in `world/combat/explosives.py`.

| field | value |
|---|---|
| key | `SPDR M9 grenade` |
| aliases | `spdr`, `spider grenade`, `m9`, `sticky grenade`, `sticky` |
| `magnetic_strength` | 8 (mining-grade electromagnets) |
| `fuse_time` | 10 seconds |
| `blast_damage` | 30 |
| `dud_chance` | 0.02 |
| `damage_type` | laceration |
| `is_sticky` | True |
| `stuck_to_armor`, `stuck_to_location` | None (set at runtime) |

The description tells the asteroid mining origin.

### Grenade attributes

- `is_sticky` (bool): marks a sticky grenade.
- `magnetic_strength` (integer, 1-10): magnet power level. The prototype's comment calls it a 0-10 scale.
- `stuck_to_armor`: the garment it is stuck to, or None.
- `stuck_to_location`: the body location string it is stuck at (for example "chest"), or None.

### Magnetic strength

Higher strength is pickier. The armor needs `magnetic_level >= strength - 3` and `metal_level >= strength - 5` (`calculate_stick_chance`).

- Strength 3 or less: every garment passes, even cloth (40% at 0/0).
- Strength 5: `magnetic_level >= 2`.
- Strength 8 (the SPDR M9): `magnetic_level >= 5` and `metal_level >= 3`.

---

## Armor material properties

Every item has two attributes, `metal_level` and `magnetic_level`, both integers 0-10 and both 0 by default (`AttributeProperty` on `Item` in `typeclasses/items.py`). All armor and clothing inherit them.

**`metal_level`**: how much metal is in the item.
- 0 = No metal whatsoever
- 1-3 = Minimal metal (buckles, rivets, small fasteners)
- 4-6 = Moderate metal (metal plates, reinforcements, chainmail sections)
- 7-9 = Heavy metal (predominantly metal construction)
- 10 = Pure metal (entirely metal construction)

**`magnetic_level`**: how magnetically responsive the metal is.
- 0 = Non-magnetic (no ferrous metals: aluminum, titanium, synthetic, cloth, leather)
- 1-3 = Weakly magnetic (stainless steel, treated/alloyed metals with low iron content)
- 4-6 = Moderately magnetic (mild steel, some carbon steel)
- 7-9 = Highly magnetic (carbon steel, most ferrous alloys)
- 10 = Pure ferrous metal (raw iron, unalloyed steel)

Only ferrous (iron-containing) metals are magnetic. Titanium, aluminum and ceramic plates are NOT magnetic (magnetic 0), despite being metal or hard and protective. Assigning the values is the builder's responsibility.

### Material guide for builders

| material | metal | magnetic | examples |
|---|---|---|---|
| Cloth/fabric | 0 | 0 | shirts, pants, cloth armor, robes |
| Leather | 1-2 (buckles, studs) | 0-1 (usually non-magnetic) | leather jackets, leather armor, belts |
| Synthetic/modern | 0-2 (minimal fasteners) | 0 | plain kevlar, synthetic jackets, nylon gear |
| Aluminum plate | 8 | 0 | aluminum plates, aircraft-grade materials |
| Titanium plate | 9 | 0 | titanium armor |
| Ceramic plates | 0-3 (ceramic is not metal; at most a metal backing) | 0 | ceramic trauma plates (the shipped "trauma plate" is metal 3, magnetic 0), composite armor |
| Brass | 7 | 0 | |
| Stainless steel (304) | 9 | 2 | decorative armor, stainless plate, modern tactical gear |
| Stainless steel (430) | 9 | 3 | |
| Bronze with steel fasteners | 4 | 2 | |
| Mixed steel/aluminum | 7 | 4 | |
| Mild steel plate | 9 | 5 | |
| Treated carbon steel | 8 | 6 | |
| Ferrous alloy armor | 9 | 7 | |
| Carbon steel plate | 9 | 7-8 | tactical steel plates, ballistic armor, combat gear |
| Iron plate / medieval armor | 10 | 10 | iron plates, pure ferrous construction |

A vest with steel trauma plates is magnetic: the shipped "kevlar vest" is metal 7, magnetic 6.

### Builder commands

```
@set armor/metal_level = 5
@set armor/magnetic_level = 3
@spawn sticky_grenade
@set grenade/magnetic_strength = 7
```

---

## Stick chance

`calculate_stick_chance(grenade, armor)` (`world/combat/explosives.py`) returns a whole-number percentage, 0 to 95.

1. It reads `grenade.db.magnetic_strength` (5 if unset) and the armor's `metal_level` and `magnetic_level` (0 if unset). On a plate carrier (`armor.db.is_plate_carrier`) it takes the highest `metal_level` and the highest `magnetic_level` across the installed plates.
2. Threshold check: if `magnetic_level < strength - 3` (not magnetic enough) or `metal_level < strength - 5` (not enough metal surface), the chance is 0.
3. Otherwise the chance is `40 + metal_level × 5 + magnetic_level × 5`, capped at 95. The cap leaves a 5% chance of failure for gameplay.

### Examples

| case | metal | magnetic | strength | thresholds | chance |
|---|---|---|---|---|---|
| Steel plate | 9 | 8 | 5 | 8 >= 2 ✓, 9 >= 0 ✓ | 40+45+40 = 125 → 95% |
| Cloth | 0 | 0 | 5 | 0 >= 2 ✗ | 0% |
| Aluminum plate | 8 | 0 | 5 | 0 >= 2 ✗ | 0% (not magnetic) |
| Weak magnet on iron | 10 | 10 | 2 | 10 >= -1 ✓, 10 >= -3 ✓ | 40+50+50 = 140 → 95% |
| Strong magnet on stainless | 9 | 2 | 8 | 2 >= 5 ✗ | 0% (not magnetic enough for a strong magnet) |
| Moderate setup | 6 | 5 | 5 | 5 >= 2 ✓, 6 >= 0 ✓ | 40+30+25 = 95% |

For the SPDR M9 (strength 8): steel plate mail sticks 95% of the time; cloth and synthetic armor never stick (no magnetic response); aluminum and ceramic never stick (non-magnetic).

---

## Throwing a sticky grenade

### Choosing the target

- `throw <grenade> at <name>` always goes to that person.
- `throw <grenade>` (into the aimed room, or this room) and `throw <grenade> to <direction>` choose a target by magnetism (`CmdThrow._pick_room_target` in `commands/CmdThrow.py`, using `select_most_magnetic_target_in_room`, below). The grenade lands on the person whose outermost chest armor has the highest `magnetic_level` among those who pass the stick thresholds. If nobody qualifies, the grenade lands by a random visible occupant.
- `throw <grenade> here` picks no target, so the grenade lands loose and cannot stick.

### Magnetic target selection

`select_most_magnetic_target_in_room(room, grenade, exclude=None, seen_by=None)` (`world/combat/throwing.py`) is used by untargeted throws and by rigged sticky grenades:

1. It skips the thrower, or the one who triggered the trap, and anyone that person cannot perceive.
2. It looks only at each person's outermost worn garment on the chest. On a plate carrier, the installed plates' highest values count.
3. The garment must pass both stick thresholds.
4. The highest `magnetic_level` wins. On a tie, the first person found wins.

There is no `find_best_stick_target`.

📋 UNBUILT (no issue): preferring targets and garments without a stuck grenade, and scoring by metal level. The sketch was to score each potential target: +100 if the target has no stuck grenade at all ("STRONG preference for clean targets"), plus the best garment's `metal_level × 5 + magnetic_level × 5`, and pick the highest score.

### Hit and stick

`handle_landing` → `resolve_weapon_hit(weapon, target, thrower)` (`world/combat/throwing.py`), in this order:

1. **Hit roll.** A flat 70% hit chance. A miss sends the ordinary miss lines and no stick is tried.
2. **Hit location.** Always "chest", for thrown and rigged grenades alike. A grenade never sticks at left_arm or right_leg.
3. **Garment.** The outermost worn item covering the chest (`get_outermost_armor_at_location(target, "chest")`). If there is none, the no-armor bounce lines are sent.
4. **Only that one item is tried, once.** There is no check for a grenade already stuck to it.
5. **Roll.** `stick_chance = calculate_stick_chance(grenade, item)`; roll 1-100.
   - **Roll <= chance: stick.** `establish_stick(grenade, item, "chest")` bonds the grenade to the garment (see "Stuck state"). The countdown continues normally. The stick success lines are sent.
   - **Otherwise: bounce.** The stick failure lines are sent. The target also takes 1d6 + the grenade's damage (default 1) on the chest, with the ordinary "strikes" lines. The grenade lands loose in the room and its countdown continues.

`get_outermost_armor_at_location(character, body_location)` (`world/combat/explosives.py`) returns None for anything that is not a Character. It looks only at worn items (`get_worn_items`), so a carried jacket is never chosen (#2492). It skips an item whose coverage list is set and does not include the location. Of the rest, it returns the one with the highest layer (the `Item.layer` property, not `db.clothing_layer`); on a tie the first found wins.

On layered armor, for example a plate carrier (outer, metal 9, magnetic 8) over a shirt (inner, metal 0, magnetic 0): only the plate carrier is tried. If it fails, the grenade bounces off and the shirt is never tried.

📋 UNBUILT (no issue): trying inner layers when the outer one fails, and skipping a garment that already holds a grenade. The sketch: sort the layers covering the hit location outermost first; skip a layer that already has a grenade; roll for each in turn and stick to the first that succeeds; if a roll misses, try the next layer inward.

📋 UNBUILT (no issue): hit locations for sticky grenades. Intended: one on chest, one on left_arm, one on right_leg; each grenade tracked independently.

### Stick messages

All SPDR M9 messages emphasize:
- **Mechanical precision**: "extend with mechanical precision", "electromagnetic sensors"
- **Spider-like behavior**: "telescoping legs", "skitter", "eight legs", "seeking metal"
- **Industrial purpose**: single-minded demolition equipment, frustrated when thwarted
- **Sound design**: *CLACK-CLACK-CLACK*, *SNAPPING*, *CLAMPING*, whirring servos
- **Mining origins**: ferrous metals, electromagnetic seeking, industrial demolition

The lines (`resolve_weapon_hit`), with `<armor>` the garment's name and `<target>` the target as the reader perceives them:

**Success, victim** (the whole line in combat red):
```
|rThe SPDR M9 grenade's articulated legs extend with mechanical precision, their electromagnetic tips skittering across your <armor> before *CLAMPING* tight with magnetic fury!|n
```
**Success, thrower:**
```
Your SPDR M9 grenade's spider-legs deploy and latch onto <target>'s <armor> with a satisfying *CLACK-CLACK-CLACK* of magnetic adhesion!
```
**Success, observers:**
```
The SPDR M9 grenade's eight legs telescope outward in a blur of motion, seeking metal across <target>'s <armor> before *SNAPPING* into electromagnetic lock!
```
**Failure (weak field), victim:**
```
The SPDR M9 grenade's legs extend and scrabble frantically across your <armor>, but the magnetic field is too weak - it bounces away with a frustrated clatter!
```
**Failure (weak field), thrower:**
```
Your SPDR M9 grenade's spider-legs fail to find purchase on <target>'s <armor>, bouncing off ineffectively!
```
**Failure (weak field), observers:**
```
The SPDR M9 grenade's articulated legs scrape and skitter across <target>'s <armor> before losing grip and clattering away!
```
**Failure (no armor), victim:**
```
The SPDR M9 grenade strikes your chest and its legs extend desperately, seeking metal that isn't there - it bounces away with a frustrated whir of servos!
```
**Failure (no armor), thrower:**
```
Your SPDR M9 grenade's electromagnetic sensors find no ferrous surface on <target>'s chest - the spider-legs retract as it falls away!
```
**Failure (no armor), observers:**
```
The SPDR M9 grenade's articulated legs extend and search frantically across <target>'s chest before retracting in defeat!
```

Only the victim's success line is coloured (combat red, `|r...|n`, for the entire line). All other lines use default colours. No excessive colour highlighting: it keeps a professional combat narrative.

---

## Rigged sticky grenades

The `rig` command is `CmdRig` in `commands/CmdExplosives.py`. When someone trips a rigged sticky grenade (`check_rigged_grenade` in `commands/explosion_utils.py`), the trap's 1-second fuse starts (`TRAP_FUSE_TIME`) and the grenade drops into the room. The person who rigged it does not trip it.

It does not target the person who tripped it. It picks the most magnetic other person in the room whom the person who tripped it can perceive, judged by the outermost worn armor on the chest (`select_most_magnetic_target_in_room`). It then makes the same hit-and-stick attempt as a throw (`resolve_weapon_hit`): 70% to hit, chest only, outermost armor only, with the throw's messages.

- When a magnetic target was chosen, that person is in the blast whether or not the grenade stuck, and the person who tripped the trap is not.
- If nobody qualifies, it behaves as an ordinary rigged grenade and the person who tripped it is in its blast.
- A rigged grenade counts down on `start_standalone_grenade_ticker`, without per-second lines, so a rigged grenade that sticks gives no per-second stuck warnings.
- It explodes through `explode_rigged_grenade`, inside `check_rigged_grenade`.

📋 UNBUILT (no issue): rigged-only stick messages. The v1.0 design text (superseded, not in the code) had these rigged lines:
```
victim:   As you pass through, a {grenade} |rSPRINGS|n out and |rCLAMPS|n onto your {location}!
observer: A {grenade} |rSPRINGS|n out and |rCLAMPS|n onto {victim}'s {location}!
```

---

## Stuck state

### The grenade is bonded to the garment

`establish_stick(grenade, armor, hit_location)` (`world/combat/explosives.py`):

1. clears any earlier bond of this same grenade;
2. moves the grenade inside the garment: `grenade.location = armor` (so it is in `armor.contents`);
3. sets `grenade.db.stuck_to_armor = armor` and `grenade.db.stuck_to_location = hit_location`;
4. sets `armor.db.stuck_grenade = grenade`, overwriting any grenade already stuck to that garment.

It returns True on success and False on invalid input.

The resulting hierarchy:
```
grenade.location = armor (stuck to the armor item)
armor.location = character (worn or carried) OR room (on the ground)

When worn:    grenade → armor → character → room
When dropped: grenade → armor → room
```

**Why the bond is to the garment:**
- Physical realism: the magnetic bond is to the metal in the armor, not to flesh.
- Persistent bond: removing the armor does not break the magnetic attraction; the grenade stays stuck to it.
- Dropped armor = dropped grenade: the grenade moves with the armor automatically.
- Proximity danger: dropped armor with a grenade on it still threatens the characters near it, through the existing explosion proximity logic.
- Tactical depth: a character must remove, drop, AND flee to be safe (3 steps, not 1); removing alone is not enough, they must get distance.

**Alternatives rejected:**
- `grenade.location = character`: implies the grenade is stuck to the person, and breaks on armor removal.
- `grenade.location = room`: does not move with the armor automatically.

### Movement

The grenade sits in the garment, and the garment sits in its wearer's contents, so both move with the wearer with no extra code. Who holds it is derived from `armor.location`.

📋 UNBUILT (no issue): an arrival line when someone walks in with a grenade stuck to them. It was sketched as an optional movement hook on the character (`at_post_move` in `typeclasses/characters.py`) that checks the character's garments for a stuck grenade and tells the room `|r{name} enters with a live grenade stuck to their {armor}!|n`.

### Countdown

A grenade armed by `pull` or by a remote detonator counts down in `start_grenade_ticker` (`commands/explosion_utils.py`). Each second, while it is stuck to armor (its location is an Item):

- if the armor is on a character (worn or carried), that character sees `|R*** N SECONDS ***|n <grenade> magnetically clamped to your <armor>!` and the room sees `<name> has a live <grenade> magnetically stuck to their <armor>! N seconds remaining!`;
- if the armor is lying in a room, the room sees `A <grenade> magnetically stuck to a <armor> ticks down: N seconds!`.

A grenade that is not stuck, in hand or on the ground, counts down silently. A rigged grenade uses `start_standalone_grenade_ticker`, which sends no per-second lines. Removing, dropping or picking up the armor does not reset or stop the countdown: the grenade explodes at 0 wherever the armor is.

### Explosion

A stuck grenade explodes through `explode_standalone_grenade` (`commands/explosion_utils.py`). If the grenade's location is an Item whose location is a Character, that character is the holder. A grenade directly in a character's inventory also makes that character the holder.

- **On armor someone wears or carries:** the holder takes double blast damage ("explosion in hands") and sees `|R*** CATASTROPHIC EXPLOSION! ***|n`, `The <grenade> magnetically clamped to your <armor> DETONATES against your <location>!` and `You take N damage!`. The room sees `<name>'s <grenade>, magnetically clamped to their <armor>, EXPLODES in a devastating blast!`. Everyone else in proximity takes half damage (body shields). There is no human-shield check.
- **On armor lying in a room:** the room found by `get_explosion_room` gets the standard explosion line and adjacent rooms are warned. Everyone in proximity takes full damage (a normal ground explosion), with the human-shield modifiers (0.0/1.0/2.0).
- **Loose on the ground (not stuck):** the human-shield modifiers apply.

The grenade explodes wherever the armor currently is. Only the grenade is destroyed; the garment is left behind.

**Who the blast hits:** grenades track their own proximity list. `get_unified_explosion_proximity(grenade)` (`commands/explosion_utils.py`) takes the grenade's own proximity list plus those people's combat proximity, limited to people in the blast room. A blast does not reach another room.

**Which room:** `get_explosion_room(grenade)` (`world/combat/explosives.py`) walks up from the grenade: from a garment to what holds it, from a character to their room. It returns that Room, or None if what it reaches is not a Room. The explosion uses it to address the room's explosion message and to drop anyone standing in another room from the damage list (#2490, #2549). Whether a character holds the grenade is worked out separately, in `explode_standalone_grenade`.

**A character who dies with a stuck grenade:** no special code. The grenade explodes wherever the character is; the corpse takes damage (existing corpse system) and nearby characters take damage (existing proximity system).

### Deleting a grenade or its garment

`Item.at_object_delete` (`typeclasses/items.py`) handles both sides, so every way an item is deleted (the three explosion terminators in `commands/explosion_utils.py`, a builder's `@destroy`, any sweep) goes through one hook:

- **A stuck grenade is deleted (#3552):** it calls `break_stick`, which severs the bond. The armor is left behind.
- **A garment holding a grenade is deleted (#3561):** it severs the bond from the armor side and deletes the grenade before Evennia's `clear_contents` can move it. A garment is deleted this way by a builder's `@destroy`, or by `_perish()` deleting a single-use garment off a body. Otherwise `clear_contents` would evict the still-armed grenade to its home (Limbo, for a grenade, which sets none), where it would stop sending warnings and detonate out of the fight.

**Owner ruling (#3561, 2026-09-25): the grenade goes with the armor** — "this situation should never occur as is".

`break_stick(grenade)` (`world/combat/explosives.py`) clears the bond only: `armor.db.stuck_grenade`, `grenade.db.stuck_to_armor` and `grenade.db.stuck_to_location`. It does **not** relocate the grenade, because its callers own that decision (an explosion deletes the object; a forcible removal would place it deliberately). It returns True/False for "was there a stick to break", so callers need no guard of their own.

**A deleted grenade's fuse stops.** A pulled pin is a scheduled timer (`ndb.grenade_timer`), not a flag, and the scheduled tick holds the Python object after a delete (still truthy, still with an `ndb`), so without a stop the countdown would run on and explode it. So:

- Every deleted item stops its fuse through `commands.explosion_utils.stop_grenade_fuse`.
- Both explosion resolvers (`explode_standalone_grenade`, `trigger_auto_defuse_explosion`) and both ticks refuse a grenade whose database row is gone (`pk is None`). The botched-defuse and chain timers are scheduled outside `ndb.grenade_timer`, so the guard, not the cancel, is what covers them.
- The rigged-grenade explosion (`explode_rigged_grenade` in `check_rigged_grenade`) has no such check; it relies on `stop_grenade_fuse` cancelling its timer, which is held in `ndb.grenade_timer`.
- `stop_grenade_fuse` is the one door for stopping a fuse: defuse, auto-defuse, both botched-defuse early triggers, `rig` and the jump sacrifice all use it.

### Looking at a stuck grenade

Looking at an item with a grenade clamped to it (`Item.return_appearance` in `typeclasses/items.py`) adds, while the fuse runs, a red banner between rules of `=`: "!!! WARNING: LIVE GRENADE MAGNETICALLY CLAMPED TO THIS ITEM !!!" and "EXPLOSION IN N SECONDS!". When the grenade is not counting down it adds "A <grenade> is magnetically clamped to this item." So a grenade stuck to armor on the ground can be examined: `look jacket` shows the live-grenade warning and the seconds left.

📋 UNBUILT (no issue): a stuck-grenade marker in the inventory:
```
> inventory
You are carrying:
  a frag grenade (STUCK TO YOUR CHEST - 3 seconds!)
  a jacket (has stuck grenade!)
  a knife
```

📋 UNBUILT (no issue): a stuck-grenade marker in the armor display:
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

📋 UNBUILT (no issue): a stuck-grenade marker in the room listing. Today a jacket on the ground with a grenade on it is listed as plain `a jacket`. The marker sketched:
```
> look
A dark alley
This is a narrow alleyway between two buildings.
Obvious exits: north, south
You see:
  <name> is here (wearing jacket with LIVE GRENADE stuck to it!)
  a jacket (with LIVE GRENADE magnetically clamped - 2 seconds!)
```

### State queries

- **Stuck grenades on a character:** `get_stuck_grenades_on_character(character)` (`world/combat/explosives.py`) returns `(grenade, armor, body_location)` tuples for every item the character holds, worn or carried, that has a grenade stuck to it (body location "unknown" if unset). Anything that is not a Character returns `[]`. No game code calls it.
- **The grenade on a garment:** `armor.db.stuck_grenade`.
- **The room for the explosion:** `get_explosion_room(grenade)` (above).

### One grenade per garment

Only ONE grenade should stick to each armor or clothing item. This prevents unrealistic "covered in grenades" situations. When checking whether a grenade can stick, a garment with `stuck_grenade` set would be skipped, and the grenade would try the next layer inward or a different target entirely.

📋 UNBUILT (no issue): not enforced. `resolve_weapon_hit` never checks `armor.db.stuck_grenade`, and `establish_stick` overwrites it: a second grenade that sticks to the same garment replaces the first in `armor.db.stuck_grenade`, and the first stays inside the garment, still armed.

---

## Getting rid of a stuck grenade

### Remove: the grenade stays on the garment

The grenade is bonded to the armor, NOT the person. Removing the armor does NOT break the bond. There is no special "remove grenade" command: the existing `remove` command takes the garment off with the grenade still on it.

`remove <item>` (`CmdRemove.func` in `commands/CmdClothing.py`) on a garment with a stuck grenade:

- allows the removal;
- warns the wearer: when the fuse is live, a red CRITICAL WARNING box with the countdown, the body location, "Removing this armor will NOT break the magnetic bond!" and "DROP ARMOR AND FLEE TO SURVIVE!"; when it is not live, a yellow "*** WARNING ***" block;
- tells the room: "{actor} carefully removes their {item} - the magnetically attached {a grenade} moves with it!";
- only clears the worn record (`remove_item`): the garment stays in the character's inventory, the grenade stays in the garment, and both stay stuck. Neither `CmdRemove.func` nor `remove_item` calls `break_stick`.

`remove all` takes the garment off too, but shows no stuck-grenade warning.

After `remove`, the character is STILL IN DANGER: the garment is still in their inventory, so if the grenade explodes now the character is its holder and takes double damage. Their body location is now exposed. They must drop the garment and leave the room to be safe.

### The escape

To survive a stuck grenade, a character must:

1. **Remove the armor** (`remove jacket`). The grenade stays stuck to it; the armor stays in their inventory.
2. **Drop it** (`drop jacket`). The armor and grenade are on the floor; the character is still in the room, still in danger. Or throw it away instead of dropping it: `wield jacket`, then `throw jacket to north`; the jacket and grenade land in a different room and the character is safe.
3. **Flee** (for example `north`). They must leave the room; a blast does not reach another room. The grenade and jacket explode in the old room.

`drop` refuses a worn item; there is no implicit remove:
```
> drop jacket
You can't put down something you're wearing. Remove it first.
```

**Failed escapes:**
- Remove but don't drop: double damage (you are holding it).
- Drop but don't leave: full damage if you are in its proximity, with human-shield modifiers.
- Pick up the dropped armor: now carrying a ticking bomb, double damage.
- Wait and hope: the jacket is still in your inventory, double damage.
- Wear the armor with the stuck grenade: double damage (see below).

### Picking up armor with a stuck grenade

`get jacket` is allowed, with no warning. The jacket goes into the character's inventory with the grenade still stuck to it and still bonded both ways. If it explodes there, it explodes "in hands": double damage to the character (because `grenade.location.location` is the character), half to others in proximity. Picking it up and dropping it again before fleeing still lets the character escape.

📋 UNBUILT (no issue): a pick-up warning.

### Wearing armor with a stuck grenade

Today `wear` allows it, with no message (`wear_item` has no stuck-grenade check). The grenade then explodes as held: double damage. Whether this should be allowed is not decided (see "Not decided").

### Removal choices

How costly removal is depends on what the grenade is stuck to:

- **Light armor** (sticky grenade on a cloth jacket): quick to remove, minor loss of protection, grenade safely discarded.
- **Heavy armor** (on a plate carrier): removing it exposes the vital torso, a significant loss of protection: a difficult tactical choice.
- **Multiple layers** (on an outer jacket): must remove the jacket (easy); inner layers still protect. A good situation.
- **Inner layer** (on an undershirt, somehow stuck through an outer layer gap): must remove the outer layers first, then the undershirt. Time-consuming and dangerous.

---

## Gameplay balance

**Advantages of sticky grenades:**
- Guaranteed to track the target if stuck
- Cannot be easily discarded
- Forces difficult choices (protection vs. safety)
- Psychological warfare potential
- Effective against heavily armored targets

**Disadvantages:**
- May not stick at all (bounce off)
- Completely ineffective against non-magnetic armor
- Telegraphed threat (visible countdown)
- Can be removed via armor removal
- Requires magnetic properties to function

**Counterplay:**
- Wear non-magnetic armor (aluminum, titanium, ceramic plates)
- Wear minimal-metal armor (cloth, leather, synthetic)
- Practice quick armor removal
- Use layered armor (sacrifice the outer layer)
- Maintain distance from throwers
- Use cover effectively
- Grapple someone as a human shield (only when the grenade is not on anyone: when it is on a garment someone wears or carries, everyone else nearby takes half damage, grapple or not)

**Armor choices:**
- Heavy metal armor: high protection, intimidating; vulnerable to sticky grenades.
- Light non-magnetic armor: immune to sticky grenades, mobile; less protection overall.
- Mixed armor: a balance of protection and magnetic resistance; a compromise.
- Layered armor: can sacrifice the outer layer to remove the grenade; bulky, expensive.

The system is builder-controlled (builders set material properties) and creates tactical choices for players without requiring complex new commands.

---

## Unbuilt

Each is described where it stands above. All are `📋 UNBUILT (no issue)`:

- Trying inner layers when the outermost garment fails ("Hit and stick").
- One grenade per garment: skipping a garment that already holds one ("One grenade per garment"; "Hit and stick").
- Hit locations other than the chest, so grenades can stick at several locations ("Hit and stick").
- Preferring targets and garments without a stuck grenade, and scoring by metal level ("Magnetic target selection").
- Rigged-only stick messages ("Rigged sticky grenades").
- An arrival line for someone walking in with a stuck grenade ("Movement").
- Stuck-grenade markers in the inventory, the armor display and the room listing ("Looking at a stuck grenade").
- A warning on picking up a garment with a stuck grenade ("Picking up armor").

---

## Potential future features

Ideas only; none is marked unbuilt or decided.

**Electromagnetic Pulse (EMP):** temporarily disables sticky grenades; causes them to fall off; a tactical counter-play option.

**Magnetic Field Generators:** a worn device that reduces stick chance; drains power over time; a high-tech counter-measure.

**Different Magnet Types:** permanent magnets (standard); electromagnets (can be toggled off); shaped charge magnets (directional).

**Armor Coating:** a non-stick coating reduces stick chance; wears off over time; a maintenance requirement.

**Multiple Grenade Types:** sticky fragmentation, sticky incendiary, sticky flash-bang, sticky smoke.

**Advanced Targeting:** the ability to aim for a specific body location; a skill check to hit the desired location; increases tactical depth.

---

## Not decided

**Can you wear armor that has a stuck grenade?** Today it is allowed, with no message, and the grenade explodes as held (double damage). The options:

- Option A: prevent wearing: "You can't wear that - there's a |RTICKING GRENADE|n magnetically clamped to it!"
- Option B: allow wearing (dramatic!): "You desperately pull on the jacket - the stuck grenade presses against your chest!" The jacket is worn, the grenade stays stuck, and it explodes on the character's body (double damage + specific location).

**Should a rigged sticky grenade stick to the person who trips it, as the old rigged flow said, or to the most magnetic other person present, as the code does now?**

**Is it intended that a stronger magnet sticks to fewer materials, so a strength-2 grenade sticks even to cloth while the strength-8 SPDR M9 needs `magnetic_level` 5 or more?**

**Are the stuck-grenade markers (inventory, armor display, room listing) and the arrival line for someone walking in with a stuck grenade still wanted, or should those passages be deleted?**

**Should a sticky grenade that fails on the outermost layer go on to try the layers underneath, and skip a garment that already holds a grenade, as "Hit and stick" sketches?**

**Are preferring targets and garments with no grenade already stuck, and scoring by metal level ("Magnetic target selection"), still wanted, or should they be deleted?**

**Should a stuck grenade on a garment that has moved onto a corpse damage the corpse?**

---

## Code pointers

- `world/combat/explosives.py`: `calculate_stick_chance`, `establish_stick`, `break_stick`, `get_explosion_room`, `get_outermost_armor_at_location`, `get_stuck_grenades_on_character`. `world/combat/utils.py` only re-exports these (`from .explosives import ...`); it does not define them.
- `world/combat/throwing.py`: `handle_landing` → `resolve_weapon_hit` (hit roll, stick check, stick messages); `select_most_magnetic_target_in_room`.
- `commands/CmdThrow.py`: `CmdThrow._pick_room_target` (untargeted sticky throws).
- `commands/explosion_utils.py`: `check_rigged_grenade` and its inner `explode_rigged_grenade`; `start_grenade_ticker`; `start_standalone_grenade_ticker`; `explode_standalone_grenade`; `get_unified_explosion_proximity`; `stop_grenade_fuse`; `trigger_auto_defuse_explosion`.
- `commands/CmdExplosives.py`: `CmdRig`.
- `commands/CmdClothing.py`: `CmdRemove.func`.
- `typeclasses/items.py`: `Item` (`metal_level`, `magnetic_level`, `return_appearance`, `at_object_delete`).
- `world/prototypes.py`: `STICKY_GRENADE`.
