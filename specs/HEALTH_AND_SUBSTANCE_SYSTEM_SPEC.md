# Health and Substance System Specification

Health in the game is entirely medical. There are no hit points on a
character: each body has a set of organs and bones with their own HP, a list
of medical conditions, a blood level, a pain level and a consciousness value.
Death and unconsciousness follow from organ function and blood loss. Damage
lands on one body location and then one organ. Treatment goes through
natural-language consumption verbs (`inject`, `apply`, `bandage`, `eat`,
`drink`, `inhale`, ...) and through surgical procedure verbs and the
`operate` chart. The same consumption verbs carry recreational and other
substances.

## Design principles

- **Anatomical realism**: injuries affect specific body parts and organs with
  logical consequences.
- **Tactical medicine**: medical tools have specific purposes and limited
  effectiveness.
- **Consequence-driven**: injuries create gameplay effects, not just a number
  going down.
- **Resource management**: medical supplies are valuable and consumable.
- **Skill-based**: treatment success depends on the character's abilities.

Integration with other systems:

- **Longdesc**: wounds show in character descriptions (see Wounds below).
- **Combat**: damage targets specific anatomical locations.
- **G.R.I.M. stats**: procedures and wound care use Intellect ×0.75 +
  Motorics ×0.25 (`calculate_treatment_skill`); consumable items
  (`calculate_treatment_success`) use Intellect ×2 alone. A code comment calls
  unifying the two a future balance pass.
- **Clothing and armour**: armour and clothing affect injury locations and
  severity, and what is worn covers wounds (`MODULAR_ARMOR_SYSTEM_SPEC.md`).

## Medical conditions

### Roster

Six conditions exist (`world/medical/conditions.py`): **bleeding, pain,
infection, consciousness-suppression, addiction, renal failure**.

- Renal failure is spawned when both kidneys are gone. It weakens and does
  not kill (#3402; see `CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC.md` §7.2).
- Burning and acid are **not** implemented. They are parked until fire
  exists as content. There is no `BurningCondition` or `AcidCondition`.
- There is no fracture condition: a bone at 0 HP is broken and heals (#3253).

Conditions are stored in two places:

- **On the body** (`medical_state.conditions`): either body-wide, with no
  location, or bound to a location. These stay with the body when an organ is
  swapped.
- **On an organ** (`Organ.conditions`): these travel with the organ through
  harvest and install. Install a damaged organ and the recipient inherits its
  conditions.

Damage creates conditions automatically. A condition's effects and its
message are applied together, so nobody dies without being told why.
Infection from a botched procedure is seeded location-bound. No code creates
an organ-bound condition yet.

### Cadence

Conditions run on one per-character `MedicalScript`, not on Evennia's global
`TICKER_HANDLER`. Condition effects are **rates per minute of real time**,
sampled at each tick; a tick is only a sampling moment. Each condition tracks
`last_processed` and applies the effect for the elapsed time, capped at
`ELAPSED_CAP_MINUTES` so that reloads and crashes do not bill players. There
are no multi-speed tickers. Full design: `CONDITION_CADENCE_SPEC.md`.

### Bleeding: layered brakes

The condition is named `bleeding` (the old name `minor_bleeding` still
deserializes to it). The blood-loss rate comes from the bleed's **current**
severity (`BLOOD_LOSS_PER_SEVERITY`, per minute); a rate is never stored.
Bleeds from several wounds add up.

- **Bandage** (a roll, `wound_care`): cuts severity and sets `treated`. The
  residual flow drops to `BLEEDING_TREATED_MULTIPLIER` (0.3) and the clot
  hazard doubles. A bandage closes modest wounds outright, but a field
  bandage cannot shut an artery: at severity 5 or more it takes a capped −4.
- **Wound-care dressing / stabilization**: a full stop at the location, plus
  a healing channel.
- **Tourniquet** (#509): limbs only; an instant full hold at any severity.
  Nothing heals under it. Bleeding resumes if it is removed with the wound
  untreated. A proper dressing supersedes it.
- **Natural clotting**: only a bleed of severity `BLEEDING_SELF_CLOT_MAX_SEVERITY`
  (5) or less resolves on its own, through `BLEEDING_CLOT_HAZARD_PER_MINUTE`.
  An arterial bleed of 6 or more never clots on its own: it takes
  intervention, or the patient dies.
- **Death** at `BLOOD_LOSS_DEATH_THRESHOLD` (85%) loss, that is, blood at or
  below 15%.

`inorganic` organs take pain-only damage: no bleeding, no infection. Robots
are `infection_immune`. A robot bleeds amber hydraulic fluid.

### Medical messages

`MedicalScript._send_medical_messages` (`world/medical/script.py`) sends one
combined medical message per tick, covering bleeding, pain and infection
together, instead of a separate line per condition. Message timing is kept
from spamming while keeping the urgency.

- The personal bleeding line is tinted in the species' blood colour and names
  its fluid: crimson blood for a human, cobalt blood for a synth, amber
  hydraulic fluid for a robot.
- The pain and infection lines, and the room's bleeding line, are `|r`.
- The room line goes through `msg_room_identity`.
- For a dead character nothing is sent: no bleeding, pain or infection line
  to the character, and no bleeding line to the room. The death curtain is
  not interrupted by medical messages.

Other medical text uses other colours: the death progression lines are `|R`;
`world/medical/medical_messages.py` also uses `|y` and `|B`; the diagnose
rungs, the procedure interruption lines and the `operate` menu use their own.

## Anatomy

### Per-character anatomy

The character's `organs` dict (on `medical_state`) is the single source of
present anatomy. Nothing auto-creates an organ: `get_organ()` returns `None`
for an organ the body does not have, and such an organ adds nothing to a
capacity (#516). Severed organs persist as 0-HP tombstones.

`db.species` selects the organ and capacity tables (human, rat,
synthetic_humanoid, robot). Each species' organs, with their containers and
properties, are defined in the species registry (`SPECIES_DEFINITIONS` in
`world/anatomy/species.py`); `ORGANS` is the human entry. Organ-to-location
mappings are explicit per species; an unregistered species falls back to
human. Injury types (fractures, bleeding, infection) are meant to work on any
anatomy: the same splint mechanics would apply to any appendage. (No tentacle
or spider species exists; those examples are illustrative.)

Organs live inside body-location containers (`head`, `chest`, `left_arm`,
...). Organs with a distinct `display_location` (eyes, ears, nose, tongue,
jaw; on a chassis the optical and audio sensors, vocal modulator and mandible
servo) are surface organs.

Three layers decide what can be hit and what works:

1. **Longdesc locations**: the keys of `character.longdesc`. A location absent
   from the dict does not exist on that character; a key with `None` exists
   with no description.
2. **The species organ table**: each organ's container, `max_hp`, hit weight
   and properties.
3. **The character's medical state**: each organ's current HP at runtime.

Ways anatomy varies between characters:

1. **Species templates**: different creature types get different default
   organs and locations.
2. **Injury loss**: destroyed organs stop contributing to capacities, but
   still count toward hit targeting for their location.
3. **Prosthetic addition**: new locations and organs can be added; new
   artificial limbs add hit locations with their own organ mappings.
4. **Mr. Hands integration**: custom body modifications extend the longdesc
   and organ system and work with hit targeting.

### Cybernetics

Cybernetics follow the chassis + module standard (#516, #526), with five
templates: replacement organ, anatomy augment, limb chassis, hardpoint
module, flesh implant. Prosthetic limbs are augment organs installed through
the surgery verbs; they carry a `prosthetic_frame` marker, take pain-only
damage (`inorganic`), and reattach whole when severed. Severing a prosthetic
limb narrates as sheared hardware, not bleeding meat
(`get_severance_message(..., material="chrome")`, keyed on `prosthetic_frame`,
#551). `@heal` and `@resetmedical` are chrome-aware. Full design:
`ANATOMY_AUGMENTS_SPEC.md` and `AUGMENT_ABILITIES_SPEC.md`.

### Organs and bones

- **Individual organs** (vital or complex): `brain`, `heart`, `liver`,
  `left_eye`, and so on.
- **Individual bones** (structural), one bone per body location for a clean
  display:

| Bones | Capacity | Weight each |
|---|---|---|
| `left/right_humerus` (arms) | manipulation | 0.4 |
| `left/right_metacarpals` (hands) | manipulation | 0.2 |
| `left/right_femur` (thighs) | moving | 0.4 |
| `left/right_tibia` (shins) | moving | 0.4 |
| `left/right_metatarsals` (feet) | moving | 0.1 |
| `thoracolumbar_spine`, `pelvis` | moving | 1.0 |

A capacity is the weighted share of its total. Moving totals 3.8, so one
femur is about 11% of it; manipulation totals 1.2, so one humerus is about
33%. A fracture is local: a humerus can break without affecting other bones,
and blunt trauma to a leg can break the femur.

### Capacities

1. The medical state is initialized from the species organ table
   (`get_species_organs`).
2. A capacity is calculated from the organs listed in
   `BODY_CAPACITIES[capacity]["organs"]`, which must reference organs that
   exist in the organ table.
3. A referenced organ the body does not have is skipped.
4. Bone contributions (femur, humerus, ...) give balanced capacity totals.

### Organ states and what can be repaired

- **Functional**: `current_hp > 0`. Can be damaged; contributes to
  capacities.
- **Destroyed**: `current_hp` is 0. Cannot be damaged further; contributes
  nothing to capacities; stays in the medical state.
- **Missing**: not in the medical state at all (removed, or never existed).

Owner ruling 2026-09-28 (#3253): a soft organ at 0 HP stays destroyed until a
donor or cybernetic install; a bone at 0 HP is broken and heals (the cervical
spine is a bone; a *severed* one is a decapitation and one-way); anything
severed stays severed; a harvested organ is gone.
`MedicalState.organ_beyond_repair` is the one question; `Organ.heal` refuses
on it. Staff `@heal` keeps its override. Sealant and dressings refuse a
destroyed soft organ, so only a replacement brings one back.

### Spinal Anatomy, Decapitation & Combat Severance

This section is the reference for the spine, decapitation and severance
anatomy (issues #243, #245, #247, #249). The identity and forensic
consequences are in `IDENTITY_RECOGNITION_SPEC.md` § "Combat-Driven
Severance"; the vital-area targeting math is in `MODULAR_ARMOR_SYSTEM_SPEC.md`
§ "Vital Area Targeting Ability". The `is_dead()` wiring is in Death › What
kills.

The spine is **two organs**:

| Organ | Container | Destroyable? | Capacity | Loss effect |
|-------|-----------|--------------|----------|-------------|
| `cervical_spine` | `neck` | **Yes** (`can_be_destroyed`) | `neck_integrity` | At 0 HP, a broken neck: death with a window; a bone, so it can be set inside the window and the body revived. **Severed**, a decapitation: one-way (#3253) |
| `thoracolumbar_spine` | `back` | **No** (`cannot_be_destroyed`) | `moving` (1.0 total) | Paralysis (`paralysis_if_destroyed`) |

When severed, `cervical_spine` is the decapitation locus: an edged neck hit
takes the whole head cluster with it. `thoracolumbar_spine` is the thoracic
and lumbar column (renamed from a plain `spine` in #254 to remove the
ambiguity with `cervical_spine`).

**Neck hits.** `neck` holds a single organ, so a neck hit always lands on the
kill organ and takes 100% of the post-armour damage. The neck is still a
low-probability location: its only organ is `hit_weight: "rare"` (8), against
`uncommon` (15) for the chest and `common` (25) for limbs.

**Combat severance.** A body part comes off during combat (not only through
the corpse `sever` command) when a location's representative bone is freshly
destroyed by a blow of a severing type:

```python
# world/combat/constants.py
SEVERING_INJURY_TYPES = frozenset({"cut", "stab", "laceration"})
```

`ArmorMixin.take_damage` detects the destroyed bone and applies the severance
(`ArmorMixin._maybe_sever_from_damage` → `apply_sever_to_character`). For the
neck, `db.decapitation_pending` is set during the hit and consumed later in
the death flow (`_create_corpse_from_character`), which spawns a
`SeveredHead`. The item-retention rules are in the identity spec.

If every organ at a location is already destroyed, a hit there applies no
damage; the damage result carries a `limb_lost` flag, kept for future limb
loss mechanics. The limb itself comes off only through severance.

**Vital locations.** `_get_vital_locations` maps each lethal capacity's
organs to their containers, giving `{head, chest, neck, abdomen}` for the
stock anatomy (#251). Because it is data-driven, `neck` is vital by data
(cervical spine → `neck_integrity`), and anatomy changes carry through. See
`MODULAR_ARMOR_SYSTEM_SPEC.md` for how the vital set feeds targeting.

#### `neck_integrity` capacity & death wiring

`neck_integrity` reads only `cervical_spine`, with `fatal_threshold` 0.0 and
`directly_fatal`. A cervical spine at 0 HP drives `neck_integrity` to 0.0
without touching the lungs' contribution math. The full list of lethal
capacities is in Death › What kills.

## Death

### What kills

`MedicalState.is_dead()` is true when any capacity in `LETHAL_CAPACITY_NAMES`
is at 0, or blood is at or below 15%:

| Capacity | Organs | Death |
|---|---|---|
| `blood_pumping` | heart | heart destroyed or stopped |
| `breathing` | both lungs | both lungs destroyed (one lung reduces function) |
| `digestion` | liver and stomach | both destroyed |
| `neck_integrity` | cervical spine | broken: death with a window; severed: decapitation, no window (#243, #3253, #3835) |
| `brain_integrity` | brain | brain destroyed: death with a window (#3248) |

`consciousness` is the awake axis and never gates death. Owner, 2026-09-26
(#3248): "Conscious capacity 0 should not be death". Unconsciousness is a
flag: `is_unconscious()` is true when runtime consciousness (0.0 to 1.0, with
pain, blood loss and suppression applied) is below
`CONSCIOUSNESS_UNCONSCIOUS_THRESHOLD` / 100. Reduced function lowers what a
character can do while they stay conscious.

Total kidney loss is **not** fatal (#3402): it spawns renal failure, a lasting
obtundation that leaves the patient fragile. The original design had both
kidneys destroyed mean death, like the lungs; the owner ruled otherwise.
Losing one kidney reduces function.

### The death window

Every death except a beheading has a 90-second window
(`DEATH_PROGRESSION_DURATION`, `world/combat/constants.py`), run by
`DeathProgressionScript` (`typeclasses/death_progression.py`). Revival is
exactly `not is_dead()`: if treatment inside the window resolves the fatal
condition, the character revives on the next check. The script checks every
few seconds (`DEATH_PROGRESSION_CHECK_INTERVAL`, 60% of the message spacing)
and stops and deletes itself when the window ends. The window mutates no
organ HP: it sends progression messages and re-checks `is_dead()`.

**Brain death** (owner ruling "Death with a window", 2026-09-26, #3248): a
destroyed brain zeroes the structural `brain_integrity` capacity (the twin of
`neck_integrity`), and the body is dead on the blow, with the window.
Restoring the brain inside the window restores the capacity and revives the
body. A brain install is the only route (#3253, 2026-09-28): sealant and
dressings refuse a destroyed soft organ. Because `brain_integrity` is checked
on its own, a body dead of anything with a destroyed brain stays dead until
the brain is restored. Brain death was earlier described as "cannot be
revived", and as a threshold on consciousness; the owner ruled instead for a
structural capacity with a window ("Conscious capacity 0 should not be death",
then "Death with a window", 2026-09-26, #3248), so it is "revived only by
getting the brain back". This closes the §10.4 hole in
`DEATH_AND_SLEEVE_LIFECYCLE_SPEC.md` (a brain-destroyed patient who never
dies and is handed back whole).

**A beheading has no death window** (#3835). Owner, 2026-11-14: *"is someone
really dying if there head is missing? They should be a corpse."* The death
curtain plays and tells the room the cause; then `complete_a_beheading`
(`typeclasses/death_progression.py`) finishes the death at once: no revival
check, no dying messages, and the corpse and `SeveredHead` are built straight
away. If that call never runs, the progression script's next tick completes
the death instead.

### Dying messages

- **11 messages**, spaced evenly across the window
  (`DEATH_PROGRESSION_DURATION // DEATH_PROGRESSION_MESSAGE_COUNT`: every 8
  seconds at the current 90).
- The dying character reads an internal narrative; the room sees progression
  indicators.
- Style: visceral stream-of-consciousness in the manner of Chuck Palahniuk
  and Hunter S. Thompson, with substantial literary content.
- Themes: the first third of the window is medical shock, surreal sensory
  experience and dark humour; the middle third existential reflection, memory
  fragmentation and acceptance; the last third peaceful transition, universal
  human experience and gentle release.
- The messages avoid specific cultural and family references.
- Text is centred to the session's width, using the death curtain patterns.

### `Character.at_death`

`Character.at_death` (`typeclasses/characters.py`) is the single place death
is processed, for combat deaths, medical deaths and other causes. In order:

1. Return at once if `db.death_processed` is already set (this prevents
   duplicate death curtains).
2. End any channel and any procedure on the body.
3. Set `db.death_processed`.
4. Set the placement "lying motionless and deceased."
5. Break stealth.
6. Release any dispatcher call.
7. Write the souls audit.
8. Write `debug_death_analysis()` (including the medical state) to the combat
   audit log (Splattercast).
9. Show the death curtain: deferred while in combat, with a 5-second
   fallback.

It sends no death line of its own and does not call `super()`; the death
curtain does the telling. The combat handler holds no death analysis of its
own.

A delayed attack checks both sides before it lands
(`process_delayed_attack` in `world/combat/attack.py`): a dead attacker's attack is cancelled, and an
attack on a dead target is cancelled, each with a Splattercast line.

**Placements.** An unconscious character's placement reads "unconscious and
motionless."; a dead one "lying motionless and deceased." The unconscious
placement is cleared when the character comes round or is healed.

### The corpse

When the window ends, the character is moved to a temporary death room for
processing, and a corpse is made that carries the character over for
forensic examination:

- every carried item, piece of equipment and worn garment moves to the
  corpse;
- the appearance is kept: longdesc, clothing coverage and template
  processing, with `{They}`, `{their}` and `{color}` substituted and the
  skintone colour applied;
- the cause of death is recorded (`db.death_cause`, from `get_death_cause`).

## Combat damage

### Injury type

A weapon prototype (`world/prototypes.py`) carries a `damage_type`: `bullet`,
`cut`, `stab`, `blunt`, `laceration` or `burn`. The combat handler maps
`weapon.db.damage_type` to the injury type of the hit (`world/combat/attack.py`).
Weapon damage comes from `get_weapon_damage(weapon, 0)`. Every damage call
passes character, damage, location and injury type. Damage to the "chest"
reaches the heart and lungs.

### Hit location (stage 1)

After a hit, the success margin is the attacker's roll minus the defender's.
`select_hit_location(target, success_margin, attacker)`
(`world/medical/utils.py`) weights every location in the character's
`longdesc` by the summed hit weight of the organs the body has there, whether
those organs still work or not, with a minimum weight of 1. Nothing drops a
location whose organs are all destroyed or severed. Vital areas come from
organ criticality (`_get_vital_locations`), not a fixed list.

Every combat attack passes the attacker. Then:

- The base vital bias comes from the attacker's Grit + Motorics: 4 or less
  ×1.1, 6 or less ×1.3, 8 or less ×1.6, otherwise ×2.0.
- It is raised 10% per point of success margin (× (1 + 0.1 × margin)) when
  the margin is above 0. At margin 0 the Grit + Motorics bias still applies.
- An attacker with Intellect 5 or more weights an unarmoured vital location
  ×1.5 and a heavily armoured one ×0.6; with Intellect 3 or 4, ×1.3 and ×0.8.

With no attacker, the margin alone sets the vital bias: margin 3 or less
×1.25, 8 or less ×1.5, 15 or less ×2.0, 16 or more ×3.0. Margin 0 with no
attacker gives no bias.

### Organ (stage 2)

A separate precision roll picks the organ inside the location:
`precision_roll` is d20, `precision_skill` is
`int(motorics × 0.7 + intellect × 0.3)`, and
`select_target_organ(hit_location, precision_roll, precision_skill, medical_state=...)`
weights each organ by its hit-weight category against
`precision_total = precision_roll + precision_skill`:

| Category | Examples (human) | 25+ | 20–24 | 15–19 | below 15 |
|---|---|---|---|---|---|
| `very_rare` (2) | brain | ×3.0 | ×2.0 | ×0.5 | ×0.5 |
| `rare` (8) | eyes, ears, jaw, cervical spine | ×2.0 | ×2.0 | ×1.5 | ×1.0 |
| `uncommon` (15) | heart, lungs, liver, kidneys, stomach | ×0.7 | ×0.7 | ×1.0 | ×1.0 |
| `common` (25) | arm and leg bones | ×0.7 | ×0.7 | ×1.0 | ×1.0 |

So high precision reaches the brain and the rare organs, and skilled
attackers hit the easy organs less often.

### Single-organ damage

`take_damage(amount, location, injury_type, target_organ)` calls
`apply_anatomical_damage(character, damage_amount, location, injury_type, target_organ)`
(`world/medical/utils.py`), which puts **all** the damage on the targeted
organ (`distribute_damage_to_organs`). If no organ is targeted, or the
targeted one is already destroyed, the damage is spread by hit weight over
the location's working organs. A destroyed organ takes no further damage.
Death and unconsciousness are then read from the medical state.

The combat message's `{hit_location}` is filled with the actual location.
The debug line reads, for example:

```
PRECISION_TARGET: attacker margin=8, precision=24, hit chest:heart
```

`attack <target>` takes a target only; the location comes from the roll.

## Treatment

### The two treatment rolls

There are two treatment rolls. Neither uses a d20.

- **Most treatment** (`inject`, `eat`, `drink`, `inhale`, `bandage`, and
  `apply` without a location): 3d6 + Intellect × 2 (+ the AutoDoc bonus)
  against 15 minus the item's effectiveness for the condition. Five or more
  over that is a full success, at or above it a partial success, below it a
  failure (`calculate_treatment_success`, `world/medical/utils.py`).
- **Wound care on a named location** (`apply <item> on <target>'s
  <location>`): 3d6 + (Intellect × 0.75 + Motorics × 0.25) + the item's
  rating (+ the AutoDoc bonus) against a target set by the wound's severity
  and depth (`roll_treatment`, `world/medical/treatments.py`).

The code notes unifying the two as a future balance pass. Intellect (75%)
stands for medical knowledge, diagnosis and anatomy; Motorics (25%) for steady
hands and dexterity with tools.

### Medical items

Medical items are ordinary `Item` prototypes (`typeclasses.items.Item`, no
custom typeclass) tagged `medical_item`, in `world/prototypes.py`, spawnable
with the built-in `spawn` command. The items are: blood bag, painkiller, gauze
bandages, medical splint, tourniquet, surgical kit, stimpak, oxygen tank,
stimpak inhaler, anesthetic gas, medicinal herb and pain relief cigarette
(smoking medical types; see `smoke`), and `TOOL_ROLL` (the robot analogue of the
surgical kit). An item declares which verbs may use it with a
`delivery_method` tag. The shape an author follows:

```python
BLOOD_BAG = {
    "key": "blood bag",
    "typeclass": "typeclasses.items.Item",
    "tags": [("medical_item", "item_type"), ("inject", "delivery_method")],
    "attrs": [
        ("medical_type", "blood_restoration"),
        ("uses_left", 1),
        ("effectiveness", {"bleeding": 9, "blood_loss": 10}),
    ],
}
```

Helpers: `is_medical_item`, `can_be_used`, `get_medical_type`,
`apply_medical_effects` (`world/medical/utils.py`). Using an item spends a
use. The remaining uses of a medical item are shown only by the post-use
message; `inventory` and a look at the item do not show them.

### When an item is spent

The consumption gate `ConsumptionCommand._check_treatment_possible`
(`commands/CmdConsumption.py`) and the effect branches in
`apply_medical_effects` (`world/medical/utils.py`) both implement this table,
so an item is spent only where it can treat something:

| Medical type | Spent when |
|---|---|
| `surgical_treatment` | only for damaged soft-tissue organs: bones (`fracture_vulnerable` / `bone_type`) and destroyed organs (`current_hp <= 0`) are excluded; a destroyed organ reports back as "beyond surgical repair" |
| `fracture_treatment` | only for damaged bones (`fracture_vulnerable` or `bone_type`) |
| `blood_restoration` | when `blood_level` < 100, or a bleeding condition is present |
| `wound_care` | only for bleeding conditions (external wound dressing) |
| `pain_relief` | always (detecting pain is complex) |
| `antiseptic` | always (infection prevention) |

So surgery kits go to soft-tissue organs, splints to bones, bandages to
bleeding and blood bags to blood loss, and nothing is spent on a healthy
patient or on an examination alone. The gate reads the medical state and the
real condition types (`bleeding`, `pain`, `infection`), not message text.

Three limits on that table:

1. **The surgical kit never reaches the `surgical_treatment` row.** Every
   consumption verb checks `supports_delivery` first; `SURGICAL_KIT` carries
   no `delivery_method` tag and `surgical_treatment` is absent from
   `LEGACY_MEDICAL_TYPE_DELIVERIES`, so no delivery verb reaches it. This is
   deliberate: `CmdApply` says "surgical kits are NOT applicable — they're
   tools for the procedure verbs". The kit is spent through the `incise` /
   `harvest` / `install` / `suture` verbs instead. The one item that reaches
   this row is `TOOL_ROLL`, which declares `("apply", "delivery_method")`.
2. **"Only spent when" covers the success branch only.** The need check gates
   the `success` arm of `execute_treatment`; a partial success or a failed
   roll calls `use_item()` regardless, so a botched roll burns the supply with
   nothing treated.
3. None of this is in `world/medical/procedures.py`, the surgery verb set,
   which has no consumption table.

### Consumption verbs

The full substance rules are in `SUBSTANCES_AND_DELIVERY_SPEC.md`. A verb
accepts an item that carries its delivery tag (category `delivery_method`:
`inject`, `apply`, `bandage`, `eat`, `drink`, `inhale`, `smoke`;
`supports_delivery` in `world/consumables.py`). What a dose does comes from
the item's substance (`world/substances/registry.py`); medical items also run
the treatment roll. Every verb acts at once. Each verb reflects how a
substance is actually taken (realistic delivery methods), and all
consumption methods use the same core mechanics with method-specific
modifiers.

| Command | What it does |
|---|---|
| `inject <item> [target]` (aliases `shot`, `jab`) | injectable substances |
| `apply <item> [to <target>]` (aliases `rub`, `spread`) | topical treatment |
| `apply <item> on <target>'s <location>` | wound care at a location (below) |
| `bandage [<target>'s] <body_part> with <item>` (aliases `wrap`, `patch`) | bandaging at a body location. `dress` belongs to clothing (#307); `patch` is the machine word (#2278) |
| `eat <item>` (aliases `consume`, `swallow`) | solid substances. With nothing held by that name, eats from a serving fixture in the room (a bar's snacks) |
| `drink <item>` (aliases `sip`, `gulp`) | liquids |
| `inhale <item> [target]` (aliases `huff`, `breathe`) | gases, vapours, oxygen, anesthetic. Refuses an unconscious target |
| `chug <drink>` / `devour <food>` | take every remaining sip or bite at once; the doses stack. Medical items are refused |

There is no `help <target> ...` form; `help` is the help command. `smoke` is a
separate command (below).

Rules every verb shares (`commands/CmdConsumption.py`):

- Dosing or treating anyone else needs their trust, or that they cannot
  resist (`check_consent`, `heal`; `TRUST_AND_CONSENT_SPEC.md`). This holds
  for every consumable, medical or not. A third party treats with the same
  roll as self-treatment.
- An unconscious patient can still be given blood, surgery, wound care,
  antiseptic, a splint, organ repair or a tourniquet; anything else is
  refused (`check_medical_requirements`).
- A tourniquet needs a named limb: `apply tourniquet to <target>'s <limb>`.
- `apply <item> on <target>'s <location>` with a wound-care or organ-repair
  item stabilizes the wound and starts healing from the dressing
  (`apply_wound_care`, #307). `bandage`, and `apply` with no location, only
  cut the severity of one bleed (`execute_treatment`). The two routes give
  different results.
- An item must carry a suitable `medical_type` for the verb. Inhalation
  types: `oxygen`, `anesthetic`, `inhaler`, `gas`, `vapor`. Their effects are
  respiratory treatment, pain relief and consciousness effects.

**`apply` at a location.** `apply <item> on <target>'s <location>` targets one
body location; `to` works as well as `on`, and the location may name an
organ. The location must exist on the target, but an open incision is **not**
required, at an internal container or anywhere else: per the #307 design
pass, delivery to any location is accepted, and what the item does there is
left to the drug rules. (`CmdApply`'s own help text says deep treatments need
an open incision; the code does not check.) `apply` has no `surgery` or
`operate` alias; the procedure verbs replace them.

**`smoke`.** `smoke <smokable>` (`commands/CmdSmoke.py`, #454) takes a puff
from a lit smokable held in your hand. Light it first with a held lighter
(`light <cigarette>` or `light <person>'s <cigarette>`); `snuff` puts it out.
There is no `burn`. Each puff gives one dose of the item's substance and uses
one puff. Smoking is self-only and runs no medical treatment roll. The smoking
medical types (`herb`, `cigarette`, `medicinal_plant`, `dried_medicine`) still
have branches in `apply_medical_effects`, but no command reaches them.

### Healing from a dressing

The slow heal is `rating // 5` HP per minute (`WOUND_HEALING_DIVISOR`,
`WOUND_HEALING_FLOOR_HP_PER_TICK`). The six items that carry `wound_healing`
(gauze bandages 6, surgical sealant 5, sealant patches 6, conformal coating 5,
stimpak 8, antiseptic spray 5) all heal one point per minute, so the
"excellent" and "modest" comments on them describe a gradient that does not
exist; the items differ in their other effects. This is parked for the
balance pass (#3254, 2026-10-26). Owner: "We're bug hunting not fine tuning."
Fix shapes when the pass comes: fractional accumulation, a smaller divisor, or
re-authored ratings.

## Surgery

Surgery is a set of procedure verbs that leaves the order of operations to
the player (#307). The open-ended `surgery <target>` button no longer exists.
The surgical order is `incise → remove → (optionally suture)`.

### Procedure Verb Set

Four standalone verbs, all gated on a surgical kit in inventory (a tool roll
for a robot patient) (`commands/CmdSurgical.py`, dispatch in
`world/medical/procedures.py`):

| Verb | Syntax | Delay |
| --- | --- | --- |
| `incise` (alias `cut`) | `incise <target> at <location>` | 6s |
| `harvest` (alias `extract`) | `harvest <organ> from <target>`; `harvest <target>` lists what can be taken | 18s |
| `install` (aliases `fit`, `graft`) | `install <organ> in <target> [at <side/location>]` | 18s |
| `suture` (aliases `stitch`, `seal`) | `suture <target>` or `suture <target>'s <location>` | 9s |

Augment, module and limb installs use the same `install` command and route by
the item (18s / 9s / 18s). Two more procedures exist only as chart steps in
`operate`: `amputate` (12s; typing `amputate` reaches `sever` instead, which
keeps it as an alias) and `autopsy` (30s, deceased subjects only).

`harvest` works on corpses, severed parts, unconscious and conscious living
targets. A harvested organ item carries a condition (`pristine`, `damaged` or
`putrid`) from the source's decay tier at extraction
(`ORGAN_CONDITION_BY_DECAY`). `install` is the inverse of `harvest`;
organ-bound conditions travel with the organ.

All the verbs work on one accessor, `get_organ_snapshot`, which treats living
characters, corpses, severed heads and severed appendages the same way, so
practice on a corpse transfers directly to a living patient. Condition
modifiers are re-derived from the current organ snapshot on each scan, not
kept in a table, so replacing an organ rolls the modifiers forward with no
cleanup and no organ state leaks across a transplant (#378).

### Rules every procedure runs under

These hold at every door, the standalone verbs and the `operate` chart alike
(`start_procedure` and `roll_procedure` in `world/medical/procedures.py`,
`_resolve_target` in `commands/CmdSurgical.py`).

* **Instruments.** The surgeon needs a surgical kit in inventory; a robot
  patient needs a tool roll instead.
* **One at a time.** A patient can have only one procedure running (#2509).
* **Consent.** A conscious patient other than yourself must trust you with
  `heal`, or be restrained. An unconscious patient has no say.
* **Deployed hardware.** Before the work starts, any deployed augment
  hardware at the site is stowed (#3360).
* **Channeled act.** Surgery is a channeled act (#2926). Damage to the
  surgeon, combat, a grapple, the surgeon losing consciousness or dying, or a
  forced move breaks it, and the work is lost. The patient's death interrupts
  it the same way. A procedure never resolves on a patient who is no longer
  in the surgeon's room or hands, or whose body is gone.
* **Skill.** `(intellect × 0.75) + (motorics × 0.25)`.
* **Difficulty.** Base **12** (`PROCEDURE_BASE_DIFFICULTY`), **+5** when the
  patient is conscious (resistance), **−3** when the patient is anesthetized,
  a corpse or a severed part (no resistance, full focus).
* **Outcome.** The roll is 3d6 + skill. Success at total ≥ difficulty + 5,
  partial at total ≥ difficulty, otherwise failure. A patient lying on an
  AutoDoc adds its station bonus to the total.
* **Pain.** On a conscious patient each verb seeds a `PainCondition` scaled by
  its invasiveness (`CONSCIOUS_PAIN_SEVERITY` in `procedures.py`).

`SURGERY_BASE_DIFFICULTY = 75` in `world/medical/constants.py` is read by
nothing; the procedures read their constants from `procedures.py`. A later
cleanup can remove it.

### Outcomes

| Verb | Partial | Failure |
|---|---|---|
| `incise` | the incision opens, but every organ at the site takes 2 HP | no incision opens; every organ at the site takes 3 HP; location-bound `InfectionCondition` |
| `harvest` | the organ comes out one tier worse (pristine becomes damaged) | the organ is torn out and lost (marked removed from the source, no item), plus `InfectionCondition` and `PainCondition` (pain skipped on an unconscious target) |
| `install` | the organ takes, plus `InfectionCondition` | the organ does not take, plus `InfectionCondition` |
| `suture` | closes, and the stump is recorded as a partial, with rougher prose | closes, plus `InfectionCondition` |

The failure paths are real and tested; the severity values are placeholders
until treatment depth is calibrated.

### Anesthesia is a drug, not a verb

There is no `anesthetize` verb. Anesthetic gas is inhaled through the
consumption verbs (`inhale anesthetic gas`, or `inhale <item> <target>` for
someone else). It relieves pain and adds a consciousness-suppression condition
that wears off. The procedures read `target.is_unconscious()` to apply the
difficulty bonus and skip pain seeding: the unconscious state is the contract,
not its cause.

### Known gap: an open incision costs nothing

**Deferred deliberately. Owner ruling: leave it, tune first.**

The first arrow of `incise → remove → (optionally suture)` is enforced; the
second is left to the surgeon's conscience.

**What is enforced.** `_resolve_harvest` refuses to reach an organ whose
`display_location` equals its `container` unless that container has an open
incision, and marks the running chart step **failed** rather than done. The
gate is in the resolver, under both the `operate` chart and the standalone
`harvest` command, so the two routes cannot disagree about it. Surface organs
(eyes, ears, nose, tongue, jaw; on a chassis the optical and audio sensors,
vocal modulator and mandible servo) declare a distinct `display_location`
and are reachable without opening anything, by design.

**What is not.** Every reader of incision state is a gate ("is it open so I
can work through it?") and none is a consequence: `procedures.py` (five
places), `treatments.py` (`organ_repair` needs an active field) and
`CmdOperate` (chart display). Nothing treats *being open* as harm. Incising
seeds pain once; after that an open cavity costs the patient nothing: no
bleeding, no infection risk, no healing penalty. A colonist can walk around
indefinitely with an open abdomen; a secbot can patrol with its chest hanging
open. A comment in `procedures.py` (where a procedure's surgeon has gone away)
says *"the incision stays open and bleeds"*, which the code does not do.

**Why it waits.** The obvious fixes, a bleeding source that persists until
sutured or a contamination risk scaled by time open, both land on systems that
have never been balanced. Owner, 2026-08-24: *"We haven't really balanced any
of our systems yet. We've just connected a lot of dots and built a ton of
them."* A new consumer of bleeding or infection added before either is tuned
would bake this gap's cost into whatever those numbers are today, and tuning
them later would silently retune surgery too. Bleeding and infection get a
balance pass first; closing this gap comes after that, not alongside it.

For whoever does it: robots are `infection_immune`, so an infection-only
answer costs a chassis nothing and leaves the gap open for machines. Bleeding
translates (amber hydraulic fluid); infection does not.

### The `operate` chart

`operate <target>` opens an EvMenu (`commands/CmdOperate.py`, per
`EVMENU_PATTERNS_SPEC.md`) where a surgeon plans a sequence of procedures on
the patient and then commences it, or leaves the chart on the patient for
someone else. It drives the same dispatch as the verbs (`start_procedure`), so
there is one execution path and any new verb becomes chartable once it is
offered in the verb picker. Failure seeding (infection, pain, organ damage)
is the same whether a verb was typed or charted. The verbs are the "what is happening right now"
layer; the chart is the "here is the plan" layer.

| Layer | When it's right | What it optimises for |
| --- | --- | --- |
| Procedure verbs (`incise`, `harvest`, `install`, `suture`) | Back-alley triage, mid-combat field work, single-step improvisation | Tension, immediacy, per-step risk |
| `operate` chart | Planned multi-step transplants, training, async handoff, complex diagnoses | Deliberation, sequencing, persistence across sessions |

A surgeon mid-firefight uses the verbs; a surgeon at a hospital bed plans with
`operate`, and either can switch to the verbs at any time. The chart is never
compulsory.

**Menu.** The top menu:

1. Add procedure step: incise / harvest / install / suture / amputate, plus
   autopsy on a deceased subject.
2. Edit chart: `u N` / `d N` move a step, `r N` removes it, `i N` inserts a
   step before it, `v N` views its recorded finding.
3. Commence pending steps (runs them back to back).
4. Save and exit.
5. Discard chart.
x. Exit (no save).

No "N/N steps succeeded" summary is printed. The PATIENT / CHART / OPTIONS
sections are joined by tree-branched box-drawing labels, in the idiom of
`armor comprehensive`.

The menu is **not centred**, unlike `score`. The chart is a working document:
a surgeon scans, edits and re-scans many times, and centring makes the eye
re-anchor on every refresh, while a left-flush block sits in a stable reading
column and matches the editing posture of `describe`.

It follows the `describe` EvMenu conventions (`_DescribeEvMenu` in
`commands/CmdCharacter.py`): a custom `EvMenu` subclass whose formatters pass
through so each node owns its whole visual; `x` as the universal exit token;
`_default` as the sole option, routed through a `_process_*_choice` dispatcher
that validates input and returns the next node; transient state on
`caller.ndb._operate_*`, cleared by a `cmd_on_exit` callback; and text-input
nodes guarded with `if raw_string and raw_string.strip():` (not a bare
`if raw_string:`) to avoid the blank-input regression.

**Pickers.**

* The suture location picker reads three sources: open incisions, planned
  chart steps, and severed-organ stumps from the medical state (see
  `EVMENU_PATTERNS_SPEC.md`, "Pattern D — Multi-Source Picker with Status
  Tags").
* The install location picker (`_list_install_locations(target, donor_item)`)
  offers only the slots the donor fits:

| Path | When it fires | Source of truth |
|---|---|---|
| **Biological** | the donor's `db.organ_name` is in the target species' organ table | `get_species_organs(target_species)[organ_name]`: its `display_location` if distinct from its container, else the container |
| **Cyberware** | the donor declares `db.target_container` and/or `db.target_display_locations` | the item's own declaration; the donor needs no entry in the species table |

  The species gate runs first: `donor_item.db.compatible_species` (stamped
  `[source_species]` at harvest by `_configure_harvested_item`) must include
  the target's species, or the picker shows nothing. An older item without
  that field falls back to `[source_species]` from its harvest provenance. An
  item with neither field is still listed by the picker, but the install
  resolver refuses it (#3070), so the two doors disagree about it. For an
  ability module the picker offers only free matching hardpoints. Each slot is
  tagged `(empty)` or `(occupied)` from the slot organ's current HP; an
  occupied slot can still be picked (the resolver replaces), but the tag
  warns.

**`amputate`.** The chart's `amputate` goes through the same severance
pipeline as combat (`apply_sever_to_character` /
`spawn_severed_head_for_living`), gated on a surgical kit instead of an edged
weapon.

**The diagnose pane** (`world/medical/diagnose.py`, #445) sits inside the
PATIENT block. It shows a condition rung (stable / tenuous / serious /
critical / moribund / deceased) and the findings the surgeon detects: each
injured organ and each condition is rolled on Intellect against an
obfuscation DC. The result is cached per surgeon and patient for 5 minutes,
and a fresh roll shows the room a pose. The procedure rolls use the
Intellect/Motorics formula, so the two do not share a skill ladder.

**Chart storage.** The chart is a dict on `target.db.medical_chart`, made by
`new_chart` (`world/medical/charts.py`), and survives reloads and restarts:

```python
target.db.medical_chart = {
    "version": 1,
    "authored_by": <surgeon dbref>,
    "authored_at": <timestamp>,
    "last_modified_at": <timestamp>,
    "status": "draft" | "in_progress" | "completed" | "aborted",
    "next_step_id": <int>,
    "steps": [
        {
            "id": <int, stable across edits>,
            "verb": ...,            # the procedure verb
            "args": {...},          # mirrors the command's argument shape
            "notes": <str>,         # surgeon's free-text annotation
            "status": "pending" | "running" | "done" | "skipped" | "failed",
            "outcome": <str|None>,  # filled after execution
            # "result": the autopsy report, read with `v N`
        },
    ],
}
```

Step IDs are stable, so a surgeon resuming a plan can reorder and edit steps
without losing references. `args` mirrors each command's argument shape: the
runner rebuilds the call the verb would make at the prompt. There is no
`last_modified_by`, no per-step author and no `diagnoses` list.

**Commencing.** `commence_chart` (`world/medical/charts.py`) runs the pending
steps one after another through `start_procedure`; the next step fires when
the previous one finishes. The timer is the surgeon's channeled act (#2926);
`evennia.utils.delay` is only the fallback when a channel cannot start. Each
step is checked against the patient's state when it runs, not when it was
charted, so a chart can hold steps that are not valid yet (a `harvest` before
the `incise` has run), and changes between sessions are picked up: if the
patient woke between charting and execution, the step takes the
conscious-patient +5. What each verb checks when its step runs:

| Verb | Prerequisite check |
| --- | --- |
| `harvest <organ>` from an internal location | location currently incised; organ still present |
| `harvest <organ>` from an external source (severed parts, corpse) | organ still present |
| `install <organ>` in an internal location | location currently incised; donor organ on hand |
| `suture <loc>` | location currently incised, or an untreated stump there |

`incise` has no prerequisite of its own: several incisions may be open at
once. An occupied install slot is not refused; the resolver replaces the
organ there.

Per step:

- **Inputs missing at run time** (organ no longer present, donor not in the
  surgeon's inventory): the step is marked `failed` with the reason, and the
  chain moves on to the next step. There is no prompt.
- **Refused by a resolver gate** (no incision, wrong species, skeletal
  remains): the step is marked `failed` with the reason, and the chain moves
  on.
- **Roll fails** (for example "The graft won't take"): the step is marked
  `done`. The consequences (infection, pain, damage) land on the patient, but
  the chart does not record the failed roll.
- **Patient busy** (another procedure already running on them): the step is
  marked `failed` and the chart `aborted`.
- **Treatment step** (`apply` / `inject`): marked `skipped` with an outcome
  note.

**Interruption.**

- **Surgeon gone, or server restart mid-chain.** The chain stops. If the
  surgeon no longer exists when the step's timer ends, nothing resolves and
  the step stays `running`; after a restart the in-memory chain hook is lost
  the same way. The next time anyone commences the chart, a step left
  `running` with nothing timing it is put back to `pending` (and an `aborted`
  chart back to `in_progress`), and the chain resumes from it
  (`requeue_stranded_steps`). There is no `last_step_completed` field.
- **The channel breaks** (damage to the surgeon, combat, a grapple, the
  surgeon unconscious or dead, a forced move): `interrupt_procedure` marks the
  running step `failed` ("interrupted: …") and the chart `aborted`. The
  surgeon re-opens `operate` and commences again to carry on.
- **The patient dies or is moved.** Death interrupts the same way. A patient
  dragged off in a grapple takes the procedure with them
  (`take_patient_away`): the step fails, and the surgeon, the patient and the
  room are told.
- **A different surgeon.** Anyone who can target the patient can open
  `operate`, see the pending steps and commence, which runs from the first
  pending step. There is no chart permission check: for a conscious patient
  other than yourself, that means passing the `heal` trust gate, or the
  patient being restrained.

**Target resolution.** Surgical commands target whole-body patients only.
`_resolve_target` (`commands/CmdSurgical.py`) drops `Appendage` and
`SeveredHead` items from the first-stage candidate set, so `operate <mob>`
finds the body even with severed parts in the room; detached parts are still
reached in the later stages by `autopsy`, `sever` and `harvest`. When an NPC's
`get_sdesc()` returns its bare key, `_match_sdesc` (`world/search.py`) falls
through from the prefix match to a word-boundary match, so `tom` finds "Tom
Hanks" and `rat` finds "a scrawny ragged rat".

## Severance and stumps

`world/medical/severance.py` is the single source of truth for severance
questions:

* `compute_severed_containers(target)`: the containers holding at least one
  organ with `wound_stage="severed"` and `current_hp == 0` (both, so a
  partly zeroed organ is not taken for a severance).
* `compute_cut_points(target)`: one entry per severance, after two collapse
  rules:
  - **Head cluster**: when `"head"` is severed (the brain is there and is
    zeroed by `sever_character_body` in any decapitation), every cluster peer
    from `get_species_severed_head_locations` (face / neck / eyes / ears /
    hair or fur, by species) collapses into one `"head"` cut point.
  - **Limb chain**: a container whose `get_species_limb_parent` ancestor is
    also severed collapses into the chain root. A thigh amputation shows as
    `"left_thigh"`; the shin and foot go with it.
* `normalize_sutured_stumps(target)`: returns `{location: outcome}` whatever
  the stored shape; an old flat-list value reads as `"success"` for each
  entry.

Three readers agree through these helpers:

| Reader | Reads | Purpose |
|---|---|---|
| `world.medical.wounds.wound_descriptions.get_character_wounds` | `compute_cut_points` | the cut-point wounds |
| `commands.CmdOperate._list_severed_locations` | `compute_cut_points` − `normalize_sutured_stumps.keys()` | suture picker entries |
| `world.medical.procedures._resolve_suture` | `procedures.untreated_stump_locations` (the same subtraction; `CmdSuture` reads it too, through `sutureable_locations`, #2554) | the untreated stumps for `suture all` |

**Cut-point wounds on a living body.** `get_character_wounds` hides every
per-organ wound at a container in `compute_severed_containers`, so a
decapitation does not render as "brain destroyed", "left eye destroyed" and so
on. It emits one wound per cut point, the same shape the corpse path
(`apply_sever_to_corpse`) writes:

```python
{
    "injury_type": "severed",
    "location": cut_point,
    "severity": "Critical",
    "stage": _stump_stage(character, cut_point),
    "organ": None,
    "organ_obj": None,
}
```

The prose comes from `world/medical/wounds/messages/severed.py`, so the living
body during the death window and the corpse afterwards read the same.

**Sutured stumps.** `_resolve_suture` records each cut point it closes in
`character.db.sutured_stumps`, keyed by location, valued by the suture roll:

```python
character.db.sutured_stumps = {"head": "success", "left_arm": "partial", "right_arm": "failure"}
```

`_stump_stage(character, location)` turns the outcome into one of three
stages, `treated_success`, `treated_partial`, `treated_failure`, each with 3–4
variants in `severed.py`: a clean roll reads "carefully sutured shut, the
dressing clean", a botched one "crudely bandaged, the seam pulling dirty". The
failure prose matches the infection a failed suture seeds.

**Stumps on a corpse.** A corpse has no live medical state; it renders from
`wounds_at_death`. Its cut-point wound reads raw and weeping on a fresh corpse
(severed.py stage `fresh`), dried and desiccated (`old`) as the corpse decays,
and `treated_<outcome>` once the stump is sutured; suturing after death is
allowed through `_resolve_suture`. The decay mapping is
`stump_stage_for_corpse(corpse)`:

| Corpse decay tier | severed.py stage |
| --- | --- |
| `fresh`, `early` | `fresh` |
| `moderate`, `advanced`, `skeletal` | `old` |

`apply_sever_to_corpse` writes the first stage with this helper. After that,
`sync_severance_wound_stages(corpse)` is the **only writer**: it walks
`wounds_at_death` and refreshes every severance wound's stored stage. It runs
at the top of `Corpse.get_preserved_wound_descriptions` (on look; usually a
no-op) and in `_resolve_suture` right after the suture is recorded, so an
autopsy straight after a suture sees the new state. The stored
`wound_data['stage']` is authoritative for every reader (corpse renderer,
`inspect`, autopsy); readers trust the dict and need no helper. (This
event-driven stored state was chosen over recomputing at read time, which
would make every reader know about the helper, #437.)

`Corpse.get_preserved_wound_descriptions` collapses wounds that share
`(injury_type, location, stage)` into one description, so a corpse killed by
an abdomen-wide injury does not say "the abdomen is shredded" once per
destroyed organ.

A severed head or appendage does not progress: `Appendage.return_appearance`
renders carried wounds at `stage="old"`, frozen at sever time. This is left as
it is because a detached part is not progressing the way a body is. If
severed parts should progress later, the `sync_severance_wound_stages`
pattern applies.

**Every severance leaves an incision.** `open_incision` takes an optional
`surgeon`. `apply_sever_to_character` and `spawn_severed_head_for_living` both
call it right after `sever_character_body`, so any severance (combat through
`ArmorMixin.take_damage`, or the chart's `_resolve_amputate`) leaves an open
incision at the cut point, and `suture` finds a wound to close however the
stump came to be. `_resolve_amputate` calls `open_incision` again, recording
the chart surgeon as `opened_by`; combat records the attacker. `opened_by` is
forensic-only and nothing reads it.

**Decapitation flags.** `spawn_severed_head_for_living` sets both
`head_severed_at_decap = True` and `decapitation_pending = True`, whoever
calls it (#419). The corpse-side cleanup in
`DeathProgressionScript._create_corpse_from_character` gates on
`decapitation_pending`: it strips head-cluster prose and wounds and makes the
neck-stump wound on the corpse.

## Wounds in descriptions

Wounds, not conditions, show in character descriptions, by organ wound stage
and injury type. Each organ carries its wound state on `Organ`
(`world/medical/core.py`), all persisted through `Organ.to_dict` /
`from_dict`: `wound_stage`, `injury_type`, `wound_timestamp`, `stabilized`
(wound care applied, #307), `dressing_rate` and `dressing_progress` (healing
from the dressing, #307/#501), `tourniqueted` (#509) and `ability_state`. The
state survives server restarts.

### Wound stages

| Stage | Set when | Prose |
|---|---|---|
| `fresh` | first damage | bleeding, swelling, immediate trauma; intensity by severity ("blood seeping from his left shoulder") |
| `destroyed` | the organ reaches 0 HP | the raw aftermath: "mangled beyond recognition", "bloody mess", "hanging by sinew"; needs urgent care to prevent death or infection |
| `treated` | a harvest site is closed, or a broken bone set from 0 HP starts to heal | bandaged, sutured or medicated |
| `severed` | a part is cut off (`typeclasses/items.py`, `world/medical/severance.py`) | a clean amputation: "surgical amputation", "sterile bandaging", "proper closure"; permanent, and safe for a prosthetic |

- A wound that heals to full HP disappears (its stage is cleared).
- A destroyed soft organ, a severed part or a harvested slot does not heal in
  place; only a replacement fixes it (owner ruling 2026-09-28, #3253).
- Treatment does not turn `destroyed` into `severed`.
- `healing` and `scarred` exist as prose in the message files but nothing
  sets them on a living body (see Unbuilt).

### Rendering

`get_wound_description(injury_type, location, severity, stage, organ, character)`
(`world/medical/wounds/wound_descriptions.py`) takes the stage it is given
(`get_character_wounds` works it out) and:

1. Picks the prose table. A species with a wound pack (synth, robot) uses its
   own pack, by injury type where the pack has `BY_INJURY`; an injury type the
   pack has not authored gets a plain neutral line (#3514). Other bodies use
   the module for the injury type, else `messages.generic`.
2. For a destroyed stage, uses the module's `DESTROYED_BY_LOCATION` overlay
   where the location has one (eyes, ears, face).
3. Picks a random variant and fills `{severity}`, `{location}` and `{organ}`.
   `{organ}` is the species' name for the organ (`get_organ_display_name`,
   `world/anatomy/organs.py`, #3537), else the location; the destroyed overlays
   use it.
4. Fills pronoun tokens, then runs `_format_wound_grammar`, which capitalizes
   the first real letter and ends with a single period while keeping colour
   codes (`|r`, `|g`, `|n`) and template variables (`{skintone}`) intact.

Message files (`world/medical/wounds/messages/`): injury modules `blunt.py`,
`bullet.py`, `cut.py`, `laceration.py`, `stab.py`, and `generic.py` as the
fallback; special cases `harvested.py` (extraction sites) and `severed.py`
(stumps); species packs `synth.py` and `robot.py`, which replace the human
prose wholesale for those bodies. Each human injury module has seven variants
per stage; the synth, robot, harvested and severed packs have fewer.

The `harvested` injury type is made by `_mark_organ_removed`
(`world/medical/procedures.py`) after a successful harvest on a corpse-shaped
source. It feeds the autopsy narrative and carries onto severed items. The
procedure dispatch holds the forensics side of harvesting; there is no
`CmdHarvest` in `commands/forensics.py`.

### Several wounds at one location

Both render paths share one summarizer, `_summarize_location_wounds`
(`world/medical/wounds/longdesc_hooks.py`, #258):

- **A location with a longdesc**: `append_wounds_to_longdesc` adds the
  summary as a trailing clause. It strips the summary's final period (keeping
  any `|n` reset) so the sentence flows, then ends it with one period.
- **A location without one**: `get_standalone_wound_description` returns the
  summary as its own sentence.
- **One wound** renders through `get_wound_description`.
- **Two or more wounds** collapse into one line from the worst wound's
  (severity, then stage priority) `COMPOUND_DESCRIPTIONS[stage]`: its injury
  module's, else `messages.generic`; a species pack uses its own
  `COMPOUND_DESCRIPTIONS` / `COMPOUND_BY_INJURY`. The line is filled with
  severity, location and a count of the rest ("another wound" or "several
  other wounds"), not every wound's full text (`_compound_phrase`). An inline
  phrasing (a calm, skintone-coloured "multiple old wounds" line when the
  worst is treated, healing or scarred) is used only when no template
  resolves.

Wounds join the body view in `typeclasses/appearance_mixin.py`: a location
with a longdesc gets `append_wounds_to_longdesc(desc, character, location,
looker)` (in `_render_body_longdesc`); one without gets
`get_standalone_wound_description(character, location, looker)` (in
`_get_visible_body_descriptions`). A wound is hidden when anything worn covers
its location (`_is_wound_visible` → `is_location_covered`,
`typeclasses/clothing_mixin.py`); there is no coverage percentage.

## Forensics

### Blood pools

Blood pools are a proof of concept: atmosphere and a data foundation for a
fuller forensic system, not an investigation game.

- A `BloodPool` (`typeclasses/objects.py`) records its creation time and
  source incident.
- It is woven into the room description, like graffiti, by
  `Room.get_integrated_objects_content` (`typeclasses/rooms.py`), which picks
  objects by typeclass (Item, GraffitiObject, BloodPool, ShopContainer,
  Furniture) and the `db.integrate` flag, not by tag. So `look` shows blood as
  part of the scene, not as an object in a list.
- Its room line (`db.integration_desc`) ages through four tiers: under 1 hour,
  under 6 hours, under 24 hours, and older (fresh → dried → stained). Its own
  look text uses finer age wording.
- `inspect <blood pool>` (alias `autopsy`, `commands/forensics.py`) reads a
  pool's forensic detail.

### Cleaning

`spray here with <solvent can>` (`commands/CmdGraffiti.py`,
`_handle_clean_with_solvent` and `_apply_solvent`) is a channelled scrub that
works on graffiti and blood in one application.

- With nothing to clean it says "There's nothing here to clean."
- Each application spends up to 10 units of solvent and strips that many
  random characters from graffiti.
- Blood pools are broken down only if the channel completes, and a pool can
  resist.
- Several applications may be needed; neither is necessarily gone after one.
- The messages speak of "colors" for graffiti and "stains" for blood, with a
  combined message when both are present.

### Corpse examination

`inspect <corpse>` (alias `autopsy`) shows the organ inventory, with harvested
and severed organs marked absent and damage shown. It also accepts severed
heads and blood pools. Organs on a corpse deteriorate with time after death,
which sets the condition of a harvested organ (`ORGAN_CONDITION_BY_DECAY`).

## Staff and diagnostic commands

- `medical [target]` (aliases `diagnose`, `medstat`, `health`, `ht`): the
  medical status readout. Kept by owner ruling 2026-10-09 (#3728): "Medical
  IS player facing but incomplete... We'll want a way to represent injuries to
  a player narratively and not with numbers which the current iteration
  does." The numeric readout is the current iteration.
- `medinfo [target] [organs|conditions|capacities|summary]`: detailed medical
  diagnostics.
- `@heal`: staff healing, with an override past `organ_beyond_repair`; it
  also clears placements.
- `@resetmedical <character>` resets one character's medical state;
  `@resetmedical confirm all` resets every character (Builder+). A character
  gets the current medical structure on next access. After a medical
  structure change, `@resetmedical confirm all` (a clean slate) is the
  recommended migration. Uses: medical system
  updates (new organs, changed mechanics), server maintenance, development
  testing, migration between game updates.

By owner ruling 2026-10-09 (#3728) there is no `medlist`, `mediteminfo`,
`refillmed` (no tests, no callers, present only on a spec checklist;
`refillmed` was a testing tool), `@medaudit` (it audited the 2025-09
organ-structure migration, which is complete) or `damagetest` (a development
test command).

## Configuration constants

All numbers are placeholders until the balance pass; the constants exist so
they are easy to change.

Read by code:

| Constant | Value | Meaning |
|---|---|---|
| `BLOOD_LOSS_DEATH_THRESHOLD` | 85 | % blood lost at death |
| `CONSCIOUSNESS_UNCONSCIOUS_THRESHOLD` | 30 | consciousness % below which a character is unconscious |
| `HIT_WEIGHT_VERY_RARE` | 2 | brain |
| `HIT_WEIGHT_RARE` | 8 | eyes, ears, jaw, neck |
| `HIT_WEIGHT_UNCOMMON` | 15 | heart, lungs, other organs, hands |
| `HIT_WEIGHT_COMMON` | 25 | arms, legs, major limbs |
| `PAIN_UNCONSCIOUS_THRESHOLD` | 80 | high pain causes unconsciousness |
| `PAIN_CONSCIOUSNESS_MODIFIER` | 0.5 | how much pain affects consciousness |

Defined in `world/medical/constants.py` and read by nothing: the item roll in
`calculate_treatment_success` is hardcoded (see The two treatment rolls).

| Constant | Value | Meant for |
|---|---|---|
| `BASE_TREATMENT_SUCCESS` | 50 | base % before stat modifiers |
| `STAT_MODIFIER_SCALING` | 5 | points per stat level |
| `TOOL_EFFECTIVENESS_SCALING` | 10 | effectiveness points per tool quality |
| `BANDAGE_EFFECTIVENESS` | 15 | HP healed per bandage |
| `SURGERY_BASE_DIFFICULTY` | 75 | base surgery difficulty |
| `INFECTION_CHANCE_BASE` | 10 | base infection chance % |
| `MEDICAL_TREATMENT_BASE_DIFFICULTY` | 12 | base d20 target for treatment |
| `PARTIAL_SUCCESS_MARGIN` | 3 | how close to success counts as partial |
| `TOOL_EFFECTIVENESS_MODIFIERS` | placeholder | tool appropriateness per condition (negative easier, positive harder) |

## Storage

`character.db.medical_state` holds `organs` (each `Organ.to_dict()`: name,
data, current_hp, max_hp, conditions, container, display_location,
wound_stage, injury_type, wound_timestamp, stabilized, dressing_rate,
dressing_progress, tourniqueted, ability_state), `removed_organs`,
`conditions` (each `condition.to_dict()`), `blood_level` (percentage of normal
volume), `pain_level` and `consciousness` (a fraction from 0 to 1).

## Overturned and replaced designs

Short notes where something the document once recorded as the plan was
replaced. The replaced designs are not wanted.

- **Brain death.** Once described as "cannot be revived" and as a threshold
  on the `consciousness` capacity. Ruled 2026-09-26 (#3248): "Conscious
  capacity 0 should not be death" and "Death with a window". Brain death is
  the structural `brain_integrity` capacity, revived only by getting the brain
  back (see The death window).
- **Kidneys.** The design had both kidneys destroyed mean death. By owner
  ruling (#3402) total kidney loss spawns renal failure and does not kill.
- **Consent for surgery and charts.** The chart proposal treated consent and
  ethics as roleplay, with no hard block on an unwilling patient. Replaced by
  the trust gate: a conscious patient other than yourself must trust the
  surgeon with `heal` or be restrained (`TRUST_AND_CONSENT_SPEC.md` §3); an
  unconscious patient still has no say.
- **Condition tickers.** A global `TICKER_HANDLER` design with multi-speed
  intervals (combat 6s, severe bleeding 12s, medical 60s), clotting that ran
  every wound down to 0, and burning and acid conditions, was replaced by the
  per-minute cadence on per-character scripts (#504/#506,
  `CONDITION_CADENCE_SPEC.md`) and the layered-brakes bleeding model with the
  clot cap at severity 5 and tourniquets (#508/#509).
- **Armour.** A per-layer armour loop on worn items (rating, type, condition)
  was replaced by `MODULAR_ARMOR_SYSTEM_SPEC.md` (stacking, plate carriers,
  tactical targeting; armour degrades through `ArmorMixin._degrade_armor`).
- **Limb loss.** A design where destroying every organ at a location removes
  the limb, with a massive bleed (severity 10), permanent penalties and an
  emergency stabilization check (`check_location_viability`,
  `process_limb_loss`, `apply_limb_loss_effects`, `emergency_stabilization`),
  was replaced by combat severance: an edged hit that freshly destroys a
  location's representative bone detaches it. The sketched penalties were:
  arm loss, no two-handed weapons, −50% carrying capacity, no two-handed
  actions (climbing, some crafting), −2 to fine motor tasks, equipment drops
  from the severed limb, optional phantom limb pain; leg loss, −60% movement,
  no running, no climbing without a prosthetic, −3 to acrobatics and easier
  to knock down, "hobbles" instead of "walks"; head or torso loss, death.
- **Prosthetics.** A `Prosthetic` class with quality tiers (crude 0.3,
  mechanical 0.6, cybernetic 0.9 of normal function) was replaced by the
  chassis + module standard (#516, #526; `ANATOMY_AUGMENTS_SPEC.md`).
- **`operate` layout.** A boxed, `score`-style frame (`BOX_*` constants,
  `COLOR_SUCCESS` chrome, 48-character content width, tee separators), with
  separate "Add procedure step" and "Add treatment step" options and a prompt
  on an invalid step, was replaced by the tree-branched layout, the single
  add-step option and the per-step rules above.
- **Diagnose reveal.** The design gated reveal depth on the procedure formula
  (Intellect ×0.75 + Motorics ×0.25), so that planning and execution share
  one skill ladder, for consistency in learning. The reveal rolls Intellect
  alone instead (see The diagnose pane).

## Original design sketches

These are the original design. Where they differ from the rules above, the
rules above are what the game does: there is no fracture condition, bleeding
at severity 5 or less clots on its own, and blood loss is a per-minute rate
set by severity, not a percentage per round. Whether these sketches stay as
intent is not decided (see Not decided). The exact mechanics were to be
balanced during implementation.

**Injury types** (values are descriptive):

| Type | Pain | Bleed | Infection | Other | Healing | Treatment | Description |
|---|---|---|---|---|---|---|---|
| cut | low | moderate | low | scar low | moderate | easy | clean cuts from blades or sharp objects |
| burn | high | minimal | high | scar high; permanent damage moderate | slow | moderate | fire, heat or chemical burns |
| blunt | moderate | minimal | — | fracture moderate; internal damage high | slow | easy | crushing, impact or bludgeoning |
| bullet | moderate | severe | moderate | penetration high; fragmentation low | slow | hard | projectile wounds from firearms |
| stab | low | severe | moderate | organ damage high | moderate | moderate | deep puncture wounds from thrusting weapons |
| laceration | high | high | high | scar very high | slow | hard | ragged tears from claws, shrapnel or serrated weapons |
| frostbite | very high | none | high | permanent damage high; amputation risk moderate | very slow | hard | cold damage causing tissue death |

**Pain.** Pain is the sum of injury severity × the injury type's pain rating,
modified by creature size (large creatures feel less), tolerance (drugs,
traits, training) and adrenaline (combat and stress reduce it for a time).

| Level | Threshold | Mood | Consciousness | Reads as | Effects |
|---|---|---|---|---|---|
| none | 0% | 0 | none | no discomfort | — |
| minor | 1–10% | slight | none | a little discomfort | — |
| moderate | 10–25% | noticeable | minimal | distracting pain | concentration penalty |
| severe | 25–50% | significant | moderate | intense pain | action penalties, focus loss |
| extreme | 50–80% | major | severe | excruciating agony | severe penalties, periodic stunning |
| unbearable | 80%+ | overwhelming | critical | mind-shattering torture | unconsciousness risk, shock |

Consciousness is one value that every factor lowers and that stacks: pain
(moderate to severe), blood loss (severe), organ damage (varies by organ;
brain damage is direct). Unconscious at 30%. The sketch also had death at 0%
consciousness; that is not live and was ruled out (see Overturned and
replaced designs).

**Blood.** Blood is tracked like pain: a percentage of a maximum that varies
by creature size, lost per round as the sum of all bleeding wounds, with a
severe consciousness effect below 60%.

| Blood | Status | Consciousness penalty |
|---|---|---|
| 90–100% | healthy | none |
| 70–90% | light blood loss | minimal |
| 50–70% | moderate blood loss | moderate |
| 30–50% | severe blood loss | major |
| 10–30% | critical blood loss | severe |
| 0–10% | exsanguination | unconscious |

**Conditions.**

- *Bleeding*: per-round loss by level, stacking across wounds, stable until
  treated: minor 1% ("small bloodstains"), moderate 3% ("steady bleeding"),
  severe 8% ("heavy blood loss"), arterial 15% ("spurting blood"). A basic
  bandage (moderate success) stops minor and moderate; a surgical kit (high
  success, needs medical skill) stops all levels; a blood bag (guaranteed)
  restores volume.
- *Infection*: develops over time from untreated wounds; minor, major,
  systemic; treated by basic cleaning, surgical kit or antibiotics; failure
  leaves chronic infection and permanent pain.
- *Fracture*: a universal injury on any appendage of any species; the
  appendage is unusable, with constant pain and impaired movement; treated by
  splint or surgical kit; failure leaves permanently reduced function and
  chronic pain.

## Unbuilt

### Forensics and death

- **Death cause attribution.** The cause is recorded on the corpse
  (`db.death_cause`); the weapon used and the attacker are not.
  📋 UNBUILT (no issue)
- **Advanced forensic evidence**: DNA markers, blood typing, time-of-death
  analysis. 📋 UNBUILT (no issue)
- **Decay progression**: enhanced corpse aging and decomposition.
  📋 UNBUILT (no issue)
- **A forensic investigation system.** 📋 UNBUILT (no issue). Wanted:
  - dedicated investigation commands (`examine evidence`, `examine
    bloodstain`, `analyze bloodstain`, `analyze evidence`, `forensic scan`,
    `collect sample`);
  - skill-based discovery: hidden evidence visible only to characters with
    investigation skills;
  - evidence collection and laboratory analysis, DNA and blood type
    identification;
  - crime scene reconstruction: timeline analysis and incident recreation;
  - more evidence types: fingerprints, DNA traces, ballistic evidence,
    chemical residues;
  - investigation equipment: forensic kits, evidence bags, portable labs,
    scanning devices;
  - chain of custody: evidence handling and legal admissibility;
  - time-of-death estimation from evidence age, and evidence quality that
    falls over time and affects analysis.
  The blood pool data structure is the foundation for it.
- **Death progression message themes**: a narrative consistency and
  emotional progression pass. 📋 UNBUILT (no issue)
- **Consciousness threshold**: revival eligibility tied to brain organ
  health and the consciousness capacity. Not live: nothing on the revival
  path reads brain HP or the `consciousness` capacity. Whether it is still
  wanted after #3248 is not decided.
- **Progressive brain damage**: brain deterioration during the window that
  lowers revival chances over time. 📋 UNBUILT (no issue)
- **Progressive organ failure**: time-based organ deterioration after death
  with realistic timelines (brain ~3 rounds, heart ~8, liver ~12, ...).
  📋 UNBUILT (no issue)

### Anatomy, combat and cybernetics

- **Removing from hit targeting a location whose organs are all destroyed or
  severed.** 📋 UNBUILT (not decided)
- **Called shots.** 📋 UNBUILT (no issue):
  ```
  > attack bandit             # normal attack (success decides location)
  > attack bandit head        # deliberate headshot (harder roll, -4 penalty)
  > attack bandit center      # centre mass (+2 bonus, chest/abdomen)
  > attack bandit limbs       # extremities (+1 bonus, arms/legs only)
  ```
- **Organ density-based targeting**: vital organ areas harder to hit
  precisely. 📋 UNBUILT (no issue). The sketched difficulties: head 8 (brain,
  eyes; very high vital density), chest 4 (heart, lungs; high), abdomen 5
  (liver, stomach, kidneys; medium), arm 2 (humerus, metacarpals; none), leg 3
  (femur, tibia, metatarsals; none).
- **Weapon penetration**: different weapons against different armour types.
  📋 UNBUILT (no issue). Armour itself is `MODULAR_ARMOR_SYSTEM_SPEC.md`. The
  sketched penetration (share of damage that gets through):

  | Weapon | cloth | leather | kevlar | plate |
  |---|---|---|---|---|
  | bullet | 0.95 | 0.80 | 0.30 | 0.60 |
  | stab | 0.90 | 0.50 | 0.70 | 0.20 |
  | cut | 0.85 | 0.60 | 0.40 | 0.15 |
  | blunt | 0.95 | 0.80 | 0.70 | 0.30 |

- **Weapon-specific injury patterns** (blade: laceration then organ damage;
  blunt: fracture then internal bleeding; projectile: organ damage then
  internal bleeding; explosive: multiple trauma then burns). No code has this
  table. 📋 UNBUILT (no issue)
- **Combat effects of injury**: critical injury immediate effects; pain and
  injury penalties on dice rolls, unified with the existing stat
  calculations; medical condition modifiers on combat, skill checks and other
  mechanics; medical emergency scenarios. 📋 UNBUILT (no issue)
- **Long-term healing and recovery; infection and complication systems;
  advanced surgical procedures.** 📋 UNBUILT (no issue)
- **Cybernetics beyond the chassis standard**: bio-compatibility (rejection,
  adaptation, maintenance); Mr. Hands integration; prosthetic quality and
  coating tiers as an item-data layer; multi-slot capacity (more limbs on one
  slot, plugging into `target_display_locations` without rework).
  📋 UNBUILT (no issue)
- **G.R.I.M. beyond Intellect and Motorics**: Grit for pain tolerance in
  self-treatment and working while injured; Resonance for bedside manner,
  patient stabilization and a calming effect on others. 📋 UNBUILT (no issue)
- **Fracture, arrhythmia and sepsis conditions, the carry-over of
  location-bound conditions onto a severed part, and per-tier treatment**:
  splints resolving location-bound fractures (leg fracture), organ-specific
  treatment resolving organ-bound damage (heart arrhythmia, damaged liver)
  and systemic drugs resolving body-bound infection (sepsis). The tiers
  themselves (body-bound: systemic state such as blood level, total pain,
  consciousness; location-bound; organ-bound) are under Roster.
  📋 UNBUILT (no issue)

### Treatment and consumption

- **Field tools as designed**: multi-round use, a success formula per item,
  failure consequences. 📋 UNBUILT (no issue). The sketch:

  | Item | Uses | Time | Effects | Requirement | On failure |
  |---|---|---|---|---|---|
  | Blood bag | 1 | 3 rounds | restores 25% of maximum blood, stops minor to moderate bleeding, reduces shock | Intellect ≥ 2; success (Int × 0.75) + (Mot × 0.25) | infection risk, scar tissue |
  | Painkiller | 1 | 1 round | significant temporary pain relief, Grit +1 for 10 rounds; after-effect of dulled awareness | none | overdose risk, addiction chance |
  | Gauze bandages | 3 | 2 rounds | stops minor to moderate bleeding, basic infection protection, stabilizes wounds | Intellect ≥ 1; same formula | incomplete bleeding control, infection risk |
  | Splint | 1 | 2 rounds | stabilizes a fracture on any appendage, restores 50% of function, prevents further damage, moderate pain relief | Intellect ≥ 1; same formula | improper healing, permanently reduced function |
  | Surgical kit | 3 | 5 rounds | repairs organs, stops internal bleeding, removes foreign objects, restores 80% of function | Intellect ≥ 4; +2 sterile environment, +1 assistant, −3 time pressure | organ damage, massive bleeding, death |

- **Consumption verbs that take time.** 📋 UNBUILT (no issue). The design:

  | Verb | Time | For |
  |---|---|---|
  | `inject` | 1–2 rounds | painkillers, stimpaks, adrenal boosters, toxins, vaccines; requirements vary by substance |
  | `apply` | 1–3 rounds | burn gel, antiseptic, salves, contact toxins, medicated patches; basic Motorics for precise application |
  | `eat` | 1 round | pills, tablets, food, edible drugs, rations; third-party form `eat <item> <target>` |
  | `drink` | 1 round | liquid medicines, water, alcohol, liquid drugs, nutritional drinks; third-party form `drink <item> <target>` |
  | `inhale` | 1–2 rounds | inhalers, oxygen, anesthetic gases, vaporized drugs; conscious target |
  | `smoke` | 3–5 rounds | herbs, cigarettes, pipes, combustible drugs; fire source |
  | `bandage` | 2–3 rounds | gauze, bandages, medicated wraps, splints; basic first aid |

- **`boof` / `insert` / `administer`** (`boof <item>`, `administer <item> to
  <target>`; 2–3 rounds; suppositories, rectal and emergency medication;
  medical knowledge and consent for third-party use). 📋 UNBUILT (no issue)
- **Self versus third-party administration**: third-party use +2 difficulty
  and 20% longer, needing consent, and refusing an unconscious target except
  by `inject`, `apply` or `bandage`. 📋 UNBUILT design (no issue)
- **Substance categories**: medical (healing; minimal therapeutic side
  effects; regulated legal), recreational (psychological effect; varied
  unpredictable side effects; varies by jurisdiction), performance (stat
  enhancement; temporary crash; controlled military), toxic (harm; damage or
  death; restricted illegal). No code has this table. 📋 UNBUILT design (no
  issue)
- **Tool appropriateness**: for bleeding, gauze highly effective for minor
  and moderate, blood bag restores volume only, surgical kit effective for
  severe internal, splint ineffective, painkiller counter-productive; for
  fracture, splint highly effective, surgical kit effective but complex,
  painkiller helps pain only, others ineffective; for infection, surgical kit
  effective with cleaning, gauze basic prevention only, others ineffective.
  Surgical kits are now spent as a tool for the procedure verbs, not by
  `apply`; this mapping is the design. 📋 UNBUILT design (no issue)
- **Diagnosis and treatment as sketched** (`diagnose_patient`: d20 +
  Intellect against 8 for obvious injuries, 14 for internal injuries, 18 for
  systemic conditions; `apply_medical_treatment`: d20 + (Int × 0.75 + Mot ×
  0.25) against `MEDICAL_TREATMENT_BASE_DIFFICULTY` + the tool modifier, with
  partial success within `PARTIAL_SUCCESS_MARGIN`). Neither function exists;
  diagnosis is `world/medical/diagnose.py` and treatment is the two rolls
  above. 📋 UNBUILT sketch (no issue)
- **Smoking types as treatment**: whether `herb`, `cigarette`,
  `medicinal_plant` and `dried_medicine` are meant to treat again.
  📋 UNBUILT (not decided)

### Wounds

- **Conditions in the longdesc**: bleeding ("blood soaking through their
  clothing", "leaving a trail of blood behind them", "pale and trembling from
  blood loss"), a fractured arm ("their arm held in a makeshift splint",
  "cradling their obviously broken arm"), impaired vision ("squinting as if
  having trouble seeing", "feeling around carefully with their hands"), with
  more severe conditions overriding less severe ones. Overtaken by the wound
  descriptions. 📋 UNBUILT design (no issue)
- **`healing` and `scarred` stages on a living body.** 📋 UNBUILT (no issue).
  Healing: scabbing, bruising progression, reduced severity, time-based stages
  with evolving text. Scarred: permanent marks for healed wounds that were not
  destroyed, described from the original injury, and only for wounds that
  healed naturally.
- **Time-based stump progression** past `treated_<outcome>` into the
  `healing` and `scarred` stages already written in `severed.py`; parked until
  Evennia ticker semantics are researched. 📋 UNBUILT (no issue)
- **Organ-specific wound descriptions**: organ-type categories (`organ_type`,
  `ORGAN_TYPE_MAPPING`: vital organ, sensory organ, bone, limb organ) and
  organ-specific variants in the per-stage lists, so a wound reads "a severe
  bullet wound through the heart" instead of "a severe bullet wound on the
  chest", with location-based lines kept as the fallback. Example lines: "a
  {severity} bullet wound piercing the {organ}", "a devastating gunshot has
  obliterated the {organ} beyond repair", "a high-caliber bullet has shattered
  the {organ} into fragments", "ballistic trauma has destroyed the {organ}
  completely". When an organ is known, only variants that use `{organ}` are
  picked; otherwise only location variants. Work left: organ-type variants,
  then updating every message file. It can start with the most common organs
  (heart, brain, eyes). 📋 UNBUILT (no issue)
- **Treatment quality and method.** 📋 UNBUILT (no issue). The one built case
  is a sutured stump, whose prose follows the suture roll. Quality levels:
  `poor` (makeshift field treatment, improvised materials: "crudely bandaged
  with torn cloth", "hastily wrapped with dirty rags"), `adequate` (basic
  first aid with proper supplies: "bandaged with clean gauze", "neatly dressed
  with field dressing"), `professional` (skilled treatment in a clinical
  setting: "expertly sutured and professionally bandaged", "precisely
  stitched with medical precision"), `surgical` (advanced surgical
  intervention with specialized equipment: "surgically repaired with
  synthetic sutures", "reconstructed with surgical mesh"). Methods: `bandage`
  (standard covering and pressure), `suture` (stitching deep lacerations and
  surgical wounds), `cauterize` (heat or chemical sealing for bleeding
  control), `field_dressing` (emergency battlefield treatment),
  `surgical_repair` (complex surgical reconstruction). Treated prose would be
  keyed by quality in each injury module, each a list of variants:

  ```python
  # world/medical/wounds/messages/bullet.py
  TREATED_DESCRIPTIONS = {
      'poor': [...], 'adequate': [...], 'professional': [...], 'surgical': [...],
  }
  ```

  Example treated lines: "A crude bandage made from torn cloth covers the
  bullet wound on his arm, already showing signs of seepage." (poor
  bandage); "His arm bears an expertly sutured bullet wound with pristine
  white bandaging and precise surgical tape." (professional suture); "A
  complex surgical repair covers his chest, with visible surgical mesh
  beneath transparent medical dressing." (surgical repair with mesh).
  There is no `apply_treatment(quality, method)` or `advance_healing_stage()`. Extensions
  on top: message variants by medical skill; treatment quality set by the
  character's medical ability; quality modifiers from the tools at hand; poor
  treatment leading to complications; treatment quality setting recovery time
  through `wound_timestamp`.

### The `operate` chart

- **Treatment steps** (`apply` / `inject`; there is no `spray` or `inhale`).
  The add-step node offers no treatment verb, and a treatment step already on
  a chart is skipped. Treatment steps would reuse the consumption commands,
  with `args` carrying the item, target and location the player would type.
  📋 UNBUILT (no issue; the code calls it PR-OP3)
- **The diagnose pane as designed**: an organ snapshot (every container with
  its organs and per-organ condition tier); the condition stack with severity
  and location; open incisions, who opened them and how long ago;
  cybernetic versus biological tags; prior chart history; recent vitals
  trajectory; reveal depth gated by medical skill (surface findings at low
  skill, internal organ condition and cybernetic identification at higher
  skill); and a "note a finding" action appending to a `diagnoses` list other
  surgeons see on handoff. Of these, the note-a-finding action and the
  `diagnoses` list, cybernetic identification, vitals trajectory and prior
  chart history are 📋 UNBUILT (no issue).
- **Permissions and visibility** (phases 2 and 4 of the plan below).
  📋 UNBUILT (no issue):

  | Action | Who can do it |
  | --- | --- |
  | Read the chart (diagnose pane) | any character with non-zero medical skill in line of sight of the patient |
  | Author / edit a chart | the character who started `operate` (becomes `authored_by`); later edits by anyone with edit permission |
  | Grant edit permission | the chart author, by a menu action; author-only by default |
  | Commence the chart | anyone with edit permission |
  | Resume an aborted chart | anyone with edit permission |
  | Annotate diagnoses | anyone with read permission (additive only) |
  | Patient's own visibility | the patient sees the chart in `operate` when conscious; an unconscious patient has no recourse, and that tension is intended |

- **Display surface.** 📋 UNBUILT (no issue). None exists:
  1. `medical info <target>` gains an "Active chart" footer naming the author
     and step count; the full chart needs `operate`.
  2. Looking at the patient, a character with enough medical skill sees a cue
     such as *"a paper chart is clipped to a board at the foot of the bed"* or
     *"a tablet rests on her chest, displaying surgical annotations"*,
     flavoured to the setting. Non-medical observers do not see the chart in
     `look`.
  3. Autopsy shows completed and aborted charts as the medical history, as
     forensic narrative even when the patient died on the table.
- **The chart plan** after its first slice (the chart, a minimal menu and the
  runner). Each phase is useful on its own, and none needs a redesign of an
  earlier one. 📋 UNBUILT (no issue):
  - Phase 2, handoff: edit-permission delegation, multi-author edits.
  - Phase 3, diagnostic depth: cybernetic identification, diagnosis notes,
    vitals trajectory (the skill-gated reveal is built as an Intellect roll
    per finding; see The diagnose pane).
  - Phase 4, display: `medical info` footer, look-at-patient cue, autopsy.
  - Phase 5, stretch: saved procedure templates ("standard appendectomy"),
    faction-shared chart libraries, billing hooks; out of scope for the #307
    follow-up but compatible with it.

## Not decided

- **The original design sketches** (injury types, pain, blood, conditions):
  whether they stay as intent.
- **Narrative injury rendering for `medical`**: how to represent injuries to
  a player narratively rather than with numbers (#3728).
- **`operate` chart questions**:
  - Should aborted charts auto-purge after some time, or persist
    indefinitely? Leaning persist: narrative value outweighs storage cost, and
    autopsy use depends on retention.
  - Chart-driven anesthesia loop: if anesthesia wears off mid-chart and pain
    spikes, should the runner pause and prompt to re-anesthetize, or carry on
    with the conscious-patient penalty? Probably prompt with continue as the
    default, the surgeon's call.
  - Multiple concurrent charts on one patient: realistically one active chart
    at a time; should drafts queue, or does the menu enforce a single active
    chart? Single-active is simpler.
  - Patient-authored "advance directives": a patient pre-authors a chart on
    themselves while conscious (DNR, organ donor flags, allergies), and other
    surgeons see it on diagnose. Probably stretch; the schema accommodates it.
  - NPC use: should NPC surgeons (faction medics, hospital staff) chart on
    patients to telegraph intent? A strong narrative tool, but it needs AI
    behaviour design beyond this spec.
- **Rectal delivery** (`boof` / `administer`): is it still wanted, or should
  its design block under Unbuilt be deleted?
- **Multi-round administration and the third-party penalty**: are
  consumption verbs that take several rounds, and the +2 difficulty and
  longer time for treating someone else, still intended?
- **Organ-specific wound descriptions**: is organ-specific wound prose
  (organ types and organ variants in the per-stage lists) still wanted and
  in need of an issue, or should that section be deleted?
- **The d20 diagnosis and treatment sketch**: should it stay as intent, or
  be deleted in favour of the two 3d6 rolls as built?
- **`bandage` and wound care**: should `bandage` go through wound care
  (stabilize and dress) the way `apply <item> on <target>'s <location>`
  does?
- **A failed roll in a chart step**: when a step's roll fails (for example
  an install that does not take), should the chart record the step as
  failed, as the proposal intended, or is today's `done` acceptable?
- **Called shots** (`attack <target> head` / `center` / `limbs`): still
  wanted and worth filing, or should that block be deleted?
- **Chart permissions**: is an author-only chart with delegated edit
  permission still the intent, or is today's open model (anyone past the
  `heal` trust gate can edit and commence) the design?

## Related documents

- `CONDITION_CADENCE_SPEC.md`: per-minute condition cadence.
- `CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC.md` §7.2: renal failure.
- `DEATH_AND_SLEEVE_LIFECYCLE_SPEC.md`: death and sleeves.
- `IDENTITY_RECOGNITION_SPEC.md` § "Combat-Driven Severance": identity and
  forensic consequences of severance.
- `MODULAR_ARMOR_SYSTEM_SPEC.md`: armour and vital-area targeting.
- `ANATOMY_AUGMENTS_SPEC.md`, `AUGMENT_ABILITIES_SPEC.md`: cybernetics.
- `SUBSTANCES_AND_DELIVERY_SPEC.md`: substances and delivery tags.
- `TRUST_AND_CONSENT_SPEC.md`: the trust gate.
- [EVMENU_PATTERNS_SPEC.md](EVMENU_PATTERNS_SPEC.md): menu patterns.

---

*"In space, a medical emergency doesn't wait for convenient timing. Every blood bag, every splint, every steady hand could mean the difference between coming home or floating in the void."*
- Dr. Sarah Chen, Frontier Medical Corps, 2387 TST
