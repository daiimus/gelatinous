# Modular Armor System Specification

Armour in this game is worn clothing that also carries an armour rating and an armour type. Worn pieces stack in layers, and a plate carrier takes swappable plates in four slots. Each hit meets the layers over its location one after another, outermost first, and what gets through goes to the medical system. Who chooses the hit location depends on the attacker: Grit and Motorics decide how well they reach vital areas, Intellect decides how well they avoid armour. The system sits on the clothing system's coverage and layers and on the G.R.I.M. stats (Grit, Resonance, Intellect, Motorics). Items have weight, but nothing reads weight for a penalty (📋 UNBUILT, #1509; see Weight and Encumbrance).

## Principles

1. **Layered protection**: several armour pieces can cover one location, and each one reduces the hit in turn.
2. **Realistic weight**: all equipment has weight that affects movement and encumbrance. 📋 UNBUILT (#1509): items have weight, shown by `look` and `slot list`; nothing reads it for a penalty yet.
3. **Modular design**: plate carriers accept swappable armour plates.
4. **Intelligent targeting**: where a hit lands depends on both the attacker's skill and their tactical sense.
5. **Strategic depth**: players trade off protection, mobility and cost.

How it meets other systems:

- **Clothing system**: an item's coverage areas are where it protects; its layer sets the order layers are met; the worn-items system holds what is equipped.
- **G.R.I.M. combat**: Grit, Motorics and Intellect drive hit location (Tactical Targeting).
- **Medical system**: armour reduces damage before the medical system sees it.
- **Commands**: `armor`, `repair`, `slot`, `unslot`, and the general verbs `get` and `put`.

---

## Armor Stacking

### Layer order

Layers are met outermost first: the highest layer number first.

Ratings are never summed for mitigation. Each layer is applied on its own, in series, each with its own effectiveness: a rating-2 carrier and a rating-6 plate reduce the damage twice, one after the other; they never act as one rating-8 layer. `_expand_plate_carrier_layers` (`typeclasses/armor_mixin.py`) returns the carrier at its own layer and the plate a hit meets at the carrier's layer + 1, as separate entries, and `_calculate_armor_damage_reduction` applies them in turn.

Layer numbers: the tactical jumpsuit (`TACTICAL_JUMPSUIT`) is layer 1, the plate carrier (`PLATE_CARRIER`, `world/prototypes.py`) layer 2, so a plate in the carrier is met at layer 3.

```
# Example stack on the chest, met outermost first. Each layer
# reduces what the layer above it left; ratings are never added.
Layer 3: standard plate (armor_rating: 7, ceramic)   # the plate in the front slot
Layer 2: plate carrier (armor_rating: 2, synthetic)
Layer 1: tactical jumpsuit (armor_rating: 1, synthetic)
```

### An abdomen hit meets one side plate

> **Ruling 2026-09-20 (#3366): an abdomen hit meets ONE side plate, in full.** Two slots
> share the abdomen. The hit lands on the left or the right at even odds
> (`_expand_plate_carrier_layers`, `random.choice` over the slots whose declared
> coverage includes the location) and meets that slot's plate at its full rating,
> then the carrier; an empty landed slot means carrier only. There is no gap
> outcome: the abdomen *is* the sides, the front and back plates own their own
> locations.

This replaced stacking both side plates at half rating as two sequential layers, which handed the wearer roughly a whole plate against every abdomen hit while the halving comment claimed the opposite (owner: the halving was a band-aid for two slots sharing one location). Recorded against the balance pass: abdomen mitigation changed, nothing tuned.

### Damage reduction, layer by layer

Each layer, outermost first:

1. Find the layer's effectiveness for its armour type against the damage type (`ArmorMixin._get_armor_effectiveness`).
2. Turn that and the layer's rating into a percentage reduction.
3. Take the reduction off; pass what remains to the next layer.
4. Stop when the damage is gone or every layer has been met.

The formula per layer:

- `base_effectiveness` = the matrix value for the armour type and damage type. An armour type not in the matrix uses the `generic` row; a damage type missing from a row counts as 0.2.
- `rating_multiplier` = armour rating ÷ 10, at most 1.0.
- `final_effectiveness` = `base_effectiveness × rating_multiplier`, at most 0.95: one layer never stops more than 95%.
- `damage_reduction` = `round(remaining_damage × final_effectiveness)`.
- `remaining_damage` = `remaining_damage − damage_reduction`, never below 0.

The reduction is rounded, not truncated, so light armour still stops something on small hits: 2 damage × 40% = 0.8 rounds to 1 blocked, where truncating would block nothing.

A worn piece that no longer exists (deleted mid-combat) is skipped.

### Degradation

After each layer, `_degrade_armor` takes the damage that layer stopped off its durability, then sets its rating to its original rating times the share of durability left, rounded down and never below 1. So a damaged plate protects less. Nothing destroys a plate: the trauma plate's rating falls fastest as it absorbs damage (rating 10, durability 50), though its description says it shatters.

### Armor effectiveness matrix

The table is `ARMOR_EFFECTIVENESS_MATRIX` in `world/combat/constants.py`, read by `ArmorMixin._get_armor_effectiveness`; it is the source of truth. Every armour type in it defines all six damage keys: `bullet`, `stab`, `cut`, `blunt`, `laceration`, `burn`. Its rows are `kevlar`, `steel`, `leather`, `ceramic`, `synthetic` (the armour type of both the tactical jumpsuit and the plate carrier), `composite` (the lightweight plate's row; its first-cut values were approved 2026-09-15 as a placeholder for the balance pass, #3440) and `generic` (the fallback for an unrecognised type).

Some of its values: kevlar `stab` 0.3, `cut` 0.4; steel `bullet` 0.9, `stab` 0.8, `cut` 0.9; leather `cut` 0.6, `blunt` 0.3; ceramic `bullet` 0.95, and ceramic `blunt` 0.8, commented "Very good vs blunt force".

The original design intent, which the live matrix does not follow, was:

| armour | design values |
|---|---|
| kevlar | bullet 0.80 (excellent), stab 0.20 (poor), cut 0.15 (poor) |
| ceramic | bullet 0.90 (excellent), blunt 0.30 ("Poor vs blunt (shatters)") |
| steel | cut 0.85 (excellent), stab 0.75 (good), bullet 0.60 (moderate) |
| leather | cut 0.50 (moderate), blunt 0.40 (moderate), bullet 0.10 (poor) |

The player-facing blurb (`Item._get_armor_type_info`, `typeclasses/items.py`) says ceramic is "brittle vs blunt force", so the live number and the live prose disagree; see Not decided.

---

## Weight and Encumbrance

📋 UNBUILT (#1509). Items have weight, shown by `look` (kg) and `slot list` (lbs); nothing below is built, and nothing reads weight for a penalty yet. Weight is a per-item attribute (`weight` on `Item`, `typeclasses/items.py`), summed for display only. No code prints a character-level weight total, a load band or an encumbrance line; the two "Total Weight" lines that do exist are per carrier (`CmdSlot._show_carrier_details` in lbs, `Item._get_plate_carrier_details` in kg) and belong to this system's prerequisites.

What is wanted:

**Equipment weight classes**:
- **Light**: 0.1-1.0 kg (clothing, small items)
- **Medium**: 1.1-5.0 kg (armor pieces, weapons)
- **Heavy**: 5.1-15.0 kg (plate carriers, heavy armor)
- **Very Heavy**: 15.1+ kg (full tactical loadouts)

**Total weight thresholds** (based on character strength):
- **Light Load** (0-20kg): No penalties
- **Medium Load** (21-40kg): -1 to movement-based rolls
- **Heavy Load** (41-60kg): -2 to movement-based rolls, slower combat
- **Overloaded** (61+kg): -3 to movement-based rolls, significant combat penalties

**Total weight**: the weight of every worn item, plus the weight of every plate installed in a worn carrier.

A reinforced plate weighs 8.5 (`REINFORCED_PLATE` in `world/prototypes.py`) and costs its wearer nothing. The one live protection-versus-mobility trade-off is the carrier's `rolled` style, which drops `abdomen` coverage (`style_configs` on `PLATE_CARRIER`), and both side plates with it. Per the balance-pass rule, nothing should be tuned against these thresholds until the system exists.

---

## Modular Plate Carrier

### How a carrier works

- The carrier itself gives a little protection (armour rating 1-2).
- It takes plates in four slots: `front`, `back`, `left_side`, `right_side`. Only one plate per slot.
- **Slot-specific protection**: a plate protects only the hit locations its slot covers.
- Plates can be swapped in and out for different threats.
- A plate has no coverage of its own; it protects whatever its slot covers.

### Slot-to-location mapping

The mapping is `plate_slot_coverage` on `PLATE_CARRIER` in `world/prototypes.py`:

```python
plate_slot_coverage = {
    "front": ["chest"],        # Front plate protects chest
    "back": ["back"],          # Back plate protects back
    "left_side": ["abdomen"],    # Left side plate protects abdomen
    "right_side": ["abdomen"]    # Right side plate protects abdomen
}
```

There is no `torso` body location in this anatomy (`COVERAGE_INHERITANCE` in `world/combat/constants.py` enumerates all 22 locations), so a carrier authored with `torso` would protect nothing at its sides.

When armour is worked out for a hit location, only plates in slots covering that location count: a shot to the chest meets the front plate, not the back or side plates. Sides can be vulnerable with chest and back plates installed. At the abdomen, a hit meets one side plate in full (see the ruling under Armor Stacking). Every display path reads `plate_slot_coverage` through `commands/CmdArmor.plate_layers_at`, not a hand-typed map.

A carrier's data:

```python
carrier.db.plate_slots = ["front", "back", "left_side", "right_side"]
carrier.db.installed_plates = {}  # filled as plates go in; an emptied slot stays as None
carrier.db.plate_slot_coverage = {
    "front": ["chest"],      # Front plate only protects chest
    "back": ["back"],        # Back plate only protects back
    "left_side": ["abdomen"],  # Left side only protects abdomen
    "right_side": ["abdomen"]  # Right side only protects abdomen
}
```

### Installation rules

- Any plate fits any slot (the plate prototypes are headed "Universal fit").
- Only one plate per slot.
- Installing and removing a plate is instant. The plate must be in your hand to go in, comes out into a free hand, and the plate verbs refuse while you are channeling. Nothing stops a plate change during a fight.
- Damaged plates have reduced effectiveness (`_degrade_armor` lowers a plate's rating as its durability falls).

---

## Tactical Targeting

### Philosophy

The system separates **ability to hit** from **target selection wisdom**:

- **Grit + Motorics**: the ability to make precise vital strikes.
- **Intellect**: tactical sense in choosing a target relative to armour.

Hit location is chosen by `select_hit_location(target, success_margin, attacker)` in `world/medical/utils.py`.

### Vital Area Targeting Ability

The set of vital body locations is computed by `_get_vital_locations` from the lethal body capacities (`LETHAL_CAPACITY_NAMES` in `world/medical/constants.py`, exactly the capacities `is_dead()` enforces; the head is vital through `brain_integrity`, not `consciousness`, #3248). Each lethal capacity's organs are mapped to their `container`, which yields `{head, chest, neck, abdomen}` for the stock anatomy. It is data-driven, not a hardcoded list, so anatomy changes carry through (#251). See `HEALTH_AND_SUBSTANCE_SYSTEM_SPEC.md` § "Spinal Anatomy, Decapitation & Combat Severance" for the anatomy and death model behind the lethal capacities.

`vital_targeting_skill = attacker_grit + attacker_motorics`

| skill | vital area bias |
|---|---|
| Poor (2-4) | 1.1x, struggles with precision |
| Moderate (5-6) | 1.3x, decent precision |
| Good (7-8) | 1.6x, skilled precision |
| Excellent (9+) | 2.0x, expert precision |

A positive success margin multiplies the vital bias by 1 + 0.1 per point.

With no attacker the bias comes from the margin alone: ×1.25 up to 3, ×1.5 up to 8, ×2.0 up to 15, ×3.0 above that, applied to vital locations only when the margin is above 0.

### Tactical target selection (Intellect)

- **Low (1-2)**: No armour consideration; hits any vital area at random.
- **Moderate (3-4)**: Basic armour awareness.
  - Unarmored vitals: +30% targeting preference
  - Heavily armored vitals: -20% targeting preference
- **High (5+)**: Advanced tactical analysis.
  - Unarmored vitals: +50% targeting preference
  - Heavily armored vitals: -40% targeting preference

The Intellect adjustments touch vital locations only. "Unarmored" means a summed armour rating of 0 and "heavily armored" means 4 or more; a vital rated 1 to 3 gets no adjustment. The armour figure comes from `_get_location_armor_coverage` (`world/medical/utils.py`), which adds every worn item covering the location and every plate whose slot covers it, so both side plates count at the abdomen (unlike damage, where a hit meets one). This sum, `_get_total_armor_rating`, has exactly one caller, `_get_location_armor_coverage`, and so feeds targeting only; the armour displays sum nothing.

### Decision matrix

**Example**: a target with armoured chest and head, unarmoured neck and abdomen.

| Fighter Profile | Chest (Armored) | Head (Armored) | Neck (Unarmored) | Abdomen (Unarmored) |
|----------------|-----------------|----------------|------------------|---------------------|
| Berserker (G7,M6,I2) | 2.0x | 2.0x | 2.0x | 2.0x |
| Tactician (G3,M4,I7) | 0.96x | 0.96x | 2.4x | 2.4x |
| Elite (G6,M6,I6) | 1.2x | 1.2x | 3.0x | 3.0x |

---

## Equipment and Prototypes

In `world/prototypes.py`:

| prototype | layer | armor_type | rating | weight | notes |
|---|---|---|---|---|---|
| `tactical jumpsuit` | 1 | synthetic | 1 | 1.8 | covers chest, back, abdomen, groin, both arms, thighs, shins and feet; durability 20 |
| `plate carrier` | 2 | synthetic | 2 | 2.5 | covers chest, back, abdomen; `plate_slots` is the list `front`, `back`, `left_side`, `right_side`; `installed_plates` starts empty; the `rolled` style drops abdomen; durability 40 |
| `lightweight plate` | 0 (not worn) | composite | 5 | 1.8 | durability 100 |
| `standard plate` | 0 (not worn) | ceramic | 7 | 3.2 | durability 140 |
| `reinforced plate` | 0 (not worn) | steel | 9 | 8.5 | durability 180 |
| `trauma plate` | 0 (not worn) | ceramic | 10 | 4.0 | durability 50 |

Plates carry `is_armor_plate` and `plate_class`, not `plate_type`, `threat_level` or `coverage`. Plates are universal fit: any plate goes in any slot. A plate a hit meets counts as the layer above its carrier.

---

## Commands and Interface

### Tables

The armour tables are `BoxTable` (`world/utils/boxtable.py`): an EvTable drawn with Unicode box characters (╔═╗║╚╝╠╣╦╩╬), with a boxed header that joins the table top, and ANSI-aware width so colour codes do not misalign it. `get_terminal_width` reads the screen width from the session's protocol flags, falls back to 78 columns, and floors the width at 60. The table is centred on screen by `center_on_screen`: for `armor` whenever the caller has a session, and for `armor coverage` and `armor effectiveness` always.

`caller.db.center_armor_headers` (default `True`) does not turn table centering on or off. It is read once, by `_get_center_headers` (`commands/CmdArmor.py`), and passed only as `center=` to `BoxTable.add_header` in the `armor`, `armor coverage` and `armor effectiveness` tables, where it decides whether the header **title** is centred inside its own box. Setting it `False` un-centres the title; the boxed table and its on-screen centering run either way, and there is no plain-text format.

### `armor` — armour status

`armour` is an alias of `armor`. `CmdArmor.func` dispatches five ways: `armor`, `armor coverage`, `armor effectiveness`, `armor comprehensive`, and `armor <item>` for anything else.

`armor` alone (`CmdArmor._list_armor`) renders a five-column table: Item, Type, Rating, Durability (a coloured ▓/░ bar), Coverage (the first three locations, then "& N more"). A carrier's Rating shows its own rating plus the count of installed plates, e.g. `2/10 (2 plates)`; the plates a hit meets are per location and listed by `armor coverage` (#3366). Nothing prints an "Effectiveness vs Common Threats" summary.

### `armor coverage` — protection by location

For each body location: every armour piece protecting it, with its armour type and rating; unprotected areas are highlighted. For a plate carrier it shows which plates protect which locations, read from `plate_slot_coverage`: `plate carrier [front: standard plate (7)]`, and for two slots on one location the alternatives a hit lands on, `plate carrier [one of left side: standard plate (7) | right side: trauma plate (10)]`. The Rating column is the carrier's own; nothing is summed (#3366).

### `armor effectiveness` — damage type matrix

The base effectiveness percentage of each armour type against each damage type (Bullet, Stab, Cut, Blunt, Laceration, Burn). It has a row for every matrix row but the `generic` fallback: Kevlar, Steel, Leather, Ceramic, Synthetic, Composite. The table iterates the matrix (#3440), so a new material cannot go missing.

### `armor <item>` — one worn piece

Details of one piece you wear, named through the core matcher (#3783): its description, type, material, current rating out of 10 and how far it has dropped from its original, condition with durability, and the locations it protects (`CmdArmor._show_item_details`). A name that matches nothing you wear answers "You are not wearing any armor matching '<name>'."

### `armor comprehensive` — layered view

Every body location with the worn items over it, in layer order (`CmdArmor._show_comprehensive_view`).

### `repair` — repair damaged armour

Repair is its own command, not an `armor` subcommand: `CmdArmorRepair`, `key = "repair"`, aliases `fix` / `mend` (`commands/CmdArmor.py`). Typing `armor repair plate carrier` reaches `armor <item>` and answers "You are not wearing any armor matching 'repair plate carrier'".

The forms are `repair <armor> [with <tool>]`, `repair <armor> field` and `repair <armor> full` (the command's help). It carries:

- A shared branch repairs breachable structures before armour (`try_repair_structure`, first in `func`).
- `full` needs workshop access (`_has_workshop_access`).
- An **Intellect roll can fail**, with per-material failure prose (`_send_repair_failure_messages`).
- Tools give bonuses up to +12; the tool degrades and occasionally breaks (`_get_tool_bonus`, `_degrade_repair_tool`, `_damage_repair_tool`).
- Success reports a durability delta and percentage, "Durability improved by N points. Current condition: N%" (`_send_repair_success_messages`), not a named condition state.

Multi-word armour names parse correctly: `parse_repair_args` reads the modifier from the end of the phrase (#2521).

### `look <item>` — armour information

`Item.return_appearance` (`typeclasses/items.py`) adds an armour block through `Item._get_armor_information` and `Item._get_plate_carrier_details`.

`look <carrier>` shows Protection Rating, Armor Type, Weight, Base Protection, one line for each slot that has ever held a plate (`installed_plates` starts empty, so an unused slot is not listed, and a slot emptied by `unslot` shows `[Empty]`), Total Weight, Coverage and Condition. Each slot line says what its plate is worth where a hit meets it; there is no total-protection line, because a sum of plate ratings across slots is a number no body location ever has (#3366). It labels weight **kg** while `slot list` labels the same attribute **lbs**.

A plate shows Protection Rating, Armor Type, Weight and Condition only.

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

**Dead branch.** `look <plate>` never prints Plate Type / Threat Level / Slot Compatibility lines. They come from `_get_plate_details`, reached only through `elif hasattr(self, 'plate_type')` in `_get_armor_information`, and `plate_type` is not declared in the AttributeProperty family of `Item` nor written by any prototype, so `hasattr` is always False. This is the same dead-read shape as the `weakness_exploited` key removed in #2473, and it needs the same resolution: delete the branch, or declare `plate_type` and populate the four plate prototypes. It is recorded twice in the code-review ledger (#2477) as read-but-unfiled.

### `slot <plate> [in] <carrier> [<slot>]` — install a plate

The plate must be **in your hand** (#3463, 2026-09-18). Plates move through the hands ledger (`character.hands`), so a plate loose in the pack is not being handled and is refused ("You need to be holding the standard plate to slot it."); wield it first. Moving the plate into the carrier releases the hand. Anyone without a free hand cannot work plates at all: limb loss is meant to be felt here.

```
> slot standard plate in plate carrier
You install the standard plate into the front slot of your plate carrier.

> slot trauma plate in plate carrier back
You install the trauma plate into the back slot of your plate carrier.

> slot lightweight plate carrier left side
You install the lightweight plate into the left_side slot of your plate carrier.
```

### `unslot <plate> [from <carrier>]` — remove a plate

Two doors, by owner ruling (#3463): `unslot <plate>` alone looks only in the carriers you are **wearing**; `unslot <plate> from <carrier>` (or `unslot <slot> from <carrier>`) reaches a carrier anywhere in your inventory. A bare `unslot` that finds the plate in a carrier you merely carry names the `from` form instead of acting. Either way the plate comes out **into a free hand** and is refused when both hands are full ("Your hands are full. Free one to take the standard plate out."). Every unslot path goes through one door, `pull_plate_into_hand`, in `commands/CmdArmor.py`. The resolvers are kept generic (carriers you wear; an item in your inventory) because slot/unslot are expected to gain non-plate uses.

```
> unslot standard plate
You pull the standard plate out of the front slot of your plate carrier and hold it.
```

### Naming (#3783)

`armor <item>`, `repair <armor> [with <tool>]` and both `unslot` doors name their object through the core matcher, `caller.search(name, candidates=pool, quiet=True)`, with these pools:

- `armor`: worn armour.
- `repair`: the armour you carry, a worn piece winning over a carried one; for `with`, the repair tools you carry.
- bare `unslot`: the plates installed in the carriers you wear, then in the ones you carry.
- `unslot ... from`: your carriers, and then that carrier's plates.

So a piece answers to its key or an alias, exact first, then a partial name in which each typed word starts a word; `2nd plate` picks the second; a fragment from the middle of a word finds nothing.

### `get <plate> from <carrier>` / `put <plate> in <carrier> [<slot>]` — the general verbs

Owner ruling (#3619, 2026-09-20): "get/put should work as unslot/slot but
require further clarification with the from command."

`get <plate> from <carrier>` goes through the unslot door (`pull_plate_into_hand`) and `put <plate> in <carrier> [<slot>]` through the install door (`install_plate_from_hand`, shared with `CmdSlot`), so the hands rule, the messages and the carrier's `installed_plates` ledger are the same whichever verb is used. A bare `get <plate>` cannot see into a carrier (it searches the room), which is the "further clarification": you must say `from`.

The general verbs reach a carrier lying in the room as well as one you wear or carry; the messages then say "the plate carrier", not "your" (`whose()`). `slot`/`unslot` keep their inventory reach.

`put` is a game-wide verb (`commands/CmdInventory.py`). It takes a plate into a carrier, an item into your open locker at a bank of lockers (`LockerBank.stash_item`, the door `stash` itself uses), and refuses everything else ("The X can't hold that."); there are no carried containers. One command answers `put` everywhere, including at the Kettle's locker bank, which carries no `put` alias of its own (a room-local `put` alias would hide the game-wide verb in that room). `put` resolves the ITEM first and only an Item you carry will do (`me`/`here` short-circuit `Character.search` ahead of every reach argument, so a name-taking door would hand back the player), and it does not see a hidden object, the same as `get`. An article alone is refused, and `me` cannot be stowed in or retrieved from a locker.

`slot` and `unslot` refuse while channeling like every other hands verb (#3376, #3635), so the four verbs answer alike.

```
> put standard plate in plate carrier front
You install the standard plate into the front slot of your plate carrier.
> get standard plate from plate carrier
You pull the standard plate out of the front slot of your plate carrier and hold it.
> get standard plate
You don't see a 'standard plate' here.
```

### `slot list [carrier]` — list installed plates

`slot list <carrier>` (the carrier's whole name, #3365) prints `=== <Carrier> ===`, the description, Carrier Statistics (Base Protection as `N/10`, then Carrier, Plate and Total Weight in **lbs**), then Plate Configuration: every slot the carrier has, with its plate, the plate's rating as `N/10` and a (Good)/(Fair)/(Poor) condition, or `[Empty Slot]` (`CmdSlot._show_carrier_details`). There is no protection-total line and no kg anywhere in that output: the damage model never computes a sum of plate ratings (#3366).

`slot list` alone, or a bare `slot`, lists every carrier you wear or carry, with each slot's plate or `[Empty]` (`CmdSlot._list_plate_carriers`).

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

### Taking damage

`take_damage()` in `typeclasses/armor_mixin.py` (class `ArmorMixin`, mixed into `Character`), in order:

1. Interrupt any channel the victim is running, then refuse an amount that is not a number or is not above 0 (no damage).
2. Break the victim's hiding: being hit reveals them (#3763).
3. Work out the armour covering the hit location.
4. Meet the armour layers in turn, outermost first.
5. Apply each layer's damage reduction.
6. Pass the remaining damage to the medical system.
7. Run the combat severance and decapitation checks (`_maybe_sever_from_damage`).
8. On death, record the first fatal blow in `db.death_blow` for the corpse and call `at_death`; on unconsciousness, call `_handle_unconsciousness`.

### Choosing the hit location

`select_hit_location(target, success_margin, attacker)` in `world/medical/utils.py` is called with the attacker from `world/combat/attack.py` (attacks), `world/combat/grappling.py`, `world/combat/utils.py` and `commands/combat/core_actions.py`. It works out targeting from the attacker's G.R.I.M. stats, applies tactical target selection, and combat resolution goes on as normal.

---

## Balance Considerations

### Trade-off matrix

| Loadout Type | Protection | Mobility | Cost | Tactical Flexibility |
|-------------|-----------|----------|------|---------------------|
| No Armor | None | Excellent | Free | Maximum |
| Light Armor | Low | Good | Low | High |
| Tactical Gear | Moderate | Fair | Moderate | Moderate |
| Heavy Armor | High | Poor | High | Low |
| Elite Setup | Very High | Poor | Very High | Low |

The Mobility column is design intent: nothing reads item weight for a penalty (📋 UNBUILT, #1509).

### Balancing mechanisms

1. **Weight penalties**: heavy armour reduces mobility and combat effectiveness. 📋 UNBUILT (#1509); see Weight and Encumbrance.
2. **Cost barriers**: better armour requires significant resource investment.
3. **Tactical counters**: high-Intellect fighters can exploit armour gaps.
4. **Maintenance**: armour degrades and requires repair or replacement.
5. **Situational**: different armour works better in different scenarios.

### Power scaling prevention

- **Diminishing returns**: additional armour layers provide less benefit.
- **Specialization**: no single armour type excels against all damage.
- **Resource limits**: weight and cost prevent "best of everything" builds. Until weight is built (#1509), this rests on cost alone.
- **Tactical counters**: every defensive strategy has offensive counters.

---

## Unbuilt

- **Weight and encumbrance**: 📋 UNBUILT (#1509). See Weight and Encumbrance.
- **Plates matched to slot types**: the original design had plates match carrier slot types. 📋 UNBUILT (not decided)
- **Plate changes take time**: the original design had installing and removing a plate take time, to prevent combat swapping. 📋 UNBUILT (not decided)
- **Neck guards**: 📋 UNBUILT (no issue). Four prototypes cover `neck` (a rebreather, a collar, a necktie, a scarf) and none carries an armour rating. (Trauma plates and side protection, the other specialised plates once listed with neck guards, are the trauma plate and the carrier's `left_side` / `right_side` slots above.)
- **Weakness Exploitation**: an attacker who knows a plate's seam, joint or damaged section reduces that layer's effectiveness for the hit. 📋 **UNBUILT** (no issue). A `weakness_exploited` read in `_calculate_armor_damage_reduction` was never written anywhere, so it always subtracted 0; it was removed in #2473 and the idea recorded here, because a no-op that looks like a mechanic reads to the next person as a shipped feature that is quietly broken. Building it needs a source of truth for *what* a weakness is (armour condition? a called shot? a recognised seam on a specific prototype?), which is the part that was never designed.

### Future enhancement opportunities

Ideas listed for the future, with no issue:

Advanced features:
1. **Armor Degradation**: realistic wear and damage over time.
2. **Environmental Effects**: weather, temperature affecting armour.
3. **Advanced Materials**: exotic armour types with unique properties.
4. **Armor Crafting**: player-created armour with custom properties.

Tactical enhancements:
1. **Formation Combat**: group tactics and armour coordination.
2. **Penetration Mechanics**: armour-piercing weapons and ammunition.
3. **Ballistic Trajectories**: angle-dependent armour effectiveness.
4. **Armor Profiles**: different effectiveness vs range/weapon types.

Quality of life:
1. **Loadout Presets**: save/load complete armour configurations.
2. **Armor Recommendations**: the system suggests optimal armour for threats.
3. **Maintenance Tracking**: automated armour condition monitoring.
4. **Visual Indicators**: clear armour status in character descriptions.

---

## Not decided

- **Ceramic against blunt.** The live matrix gives ceramic `blunt` 0.8, commented "Very good vs blunt force"; the original design gave 0.30, "Poor vs blunt (shatters)"; the player-facing blurb (`Item._get_armor_type_info`) says ceramic is "brittle vs blunt force". The live number and the live prose disagree: one of the two is a bug, and which one is an owner call.
- **Steel against the specialization principle.** Steel's live values are good against every damage type but burn, while Power scaling prevention says no single armour type excels against all damage. Should steel be brought in line with the principle in the balance pass, or should the principle be softened?

---

## Where things live

- `typeclasses/armor_mixin.py` (class `ArmorMixin`, mixed into `Character`; `characters.py` only inherits it): `take_damage()` (entry point for armour and medical damage), `_calculate_armor_damage_reduction()` (the layer loop), `_expand_plate_carrier_layers()`, `_get_armor_effectiveness()`, `_degrade_armor()`, `_get_total_armor_rating()` (the summed rating, used only for targeting). It also holds combat-driven severance and decapitation: `_bone_freshly_destroyed`, `_maybe_sever_from_damage`, `_broadcast_decapitation_message`, and the `death_blow` record `take_damage` keeps for the corpse pipeline (#2778).
- `world/medical/utils.py`: `select_hit_location()`, `_get_location_armor_coverage()`.
- `world/combat/attack.py`, `world/combat/grappling.py`, `world/combat/utils.py`, `commands/combat/core_actions.py`: pass the attacker to `select_hit_location()`.
- `world/combat/constants.py`: `ARMOR_EFFECTIVENESS_MATRIX`, `COVERAGE_INHERITANCE`.
- `typeclasses/items.py`: `Item` with its armour and weight attributes, plate carrier and plate support, and `return_appearance` with the armour block.
- `commands/CmdArmor.py`: `CmdArmor`, `CmdArmorRepair`, `CmdSlot`, `CmdUnslot`, `plate_layers_at`, `pull_plate_into_hand`, `install_plate_from_hand`.
- `commands/CmdInventory.py`: `put`.
- `world/utils/boxtable.py`: `BoxTable`.
- `world/prototypes.py`: the jumpsuit, the plate carrier and the plates.
- `commands/default_cmdsets.py`: adds the commands to the character command set.
- `HEALTH_AND_SUBSTANCE_SYSTEM_SPEC.md`: anatomy and the death model.
