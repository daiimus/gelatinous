# Substances and Delivery Spec

## 0 · Purpose

Items that introduce substances into a body — cigarettes, joints,
pills, vials, drinks, food, inhalers, patches — share more than
they differ. This spec names the layers so commands and items align
on the same shape instead of each inventing its own item-type
validation.

The smoke system (issue #454, refactored under #456) is the working
example. The medical consumption verbs (`commands/CmdConsumption.py`:
`eat`, `drink`, `inhale`, `inject`, `apply`, `bandage`, `chug`,
`devour`) gate on the same delivery tags (#474); their treatment
effects stay on the treatment path (`medical_type`) by design (#3207,
§5 item 3).

## 1 · The three layers

```
   ┌────────────────────────────────────────────────────────┐
   │ ITEM         cigarette / joint / pill / vial / beer    │
   │              - holds a substance id (or a composed     │
   │                substance map, see below)               │
   │              - declares its delivery method(s) via tag │
   │              - tracks uses_left, state (lit/sealed/…)  │
   └─────────────────┬──────────────────────────────────────┘
                     │ resolves
                     ▼
   ┌────────────────────────────────────────────────────────┐
   │ SUBSTANCE    tobacco / cannabis / opium / alcohol / …  │
   │              - effects (pain, consciousness, mood)     │
   │              - conditions caused (addiction, tolerance,│
   │                lung damage, withdrawal)                │
   │              - flavor bank (per substance, possibly    │
   │                per-style within the substance)         │
   └─────────────────┬──────────────────────────────────────┘
                     │ applies via
                     ▼
   ┌────────────────────────────────────────────────────────┐
   │ DELIVERY     smoke / inject / inhale / drink / eat /   │
   │              snort / apply                             │
   │              - command surface (CmdSmoke, CmdInject…)  │
   │              - magnitude modifier (smoking ≠ injection)│
   │                — 📋 UNBUILT (no issue), see below      │
   │              - prerequisites (smoke needs ignition;    │
   │                inject needs vein access — see §4 for   │
   │                which are enforced)                     │
   └────────────────────────────────────────────────────────┘
```

Three layers, three independent axes:

* **Item** is what the player holds. It declares one or more
  delivery methods via tag. It carries either one substance
  (`db.substance`) or a composed map of several.

  A recipe-composed drink or plated dish carries `db.drink_effects`,
  a `{substance_id: doses}` map written by `make_drink` in
  `world/bar.py`. `_apply_substance_dose` (`commands/CmdConsumption.py`)
  applies every entry through the same pipeline. 22 prototypes in
  `world/prototypes.py` carry it, e.g. `DOUBLESHIFT_LAGER` alcohol,
  `CHEWING_TOBACCO_PLUG` tobacco_neutral, `RAT_TAIL` nutrition. The
  shape is deliberate: `BARS_AND_RECIPES_SPEC` §3-§4 owns it as an
  ingredient's `contributions` summed and capped into the drink's
  `effects`, and §6 there says it rides `apply_substance` so the
  alcohol cap, tolerance and addiction all hold.

  This spec first recorded "one item, one substance"; the composed
  map replaced that for recipe-composed drinks and dishes.
* **Substance** is what does pharmacology to the consumer. It lives
  in a registry keyed by id (§3). Effects compose through the
  existing `MedicalState.conditions` system — no new runtime
  infrastructure. Substances *declare*; the medical script *applies
  and ticks*.
* **Delivery** is the verb-level entry point. Each delivery method
  has a command (`CmdSmoke`, `CmdInject`, etc.) that validates "this
  item supports this delivery" and applies the substance's effects.

  A per-delivery magnitude or speed modifier is 📋 UNBUILT (no
  issue). `apply_substance` (`world/substances/registry.py`) has one
  dial, a plain `doses` count:
  - `CmdSmoke` passes the default 1 per puff (`CmdSmoke.func`);
  - the ingestion verbs pass 1, or the item's own `drink_effects`
    count;
  - `chug` / `devour` pass `uses_left`.

  A smoked dose and an injected dose of the same substance are
  identical. Dose count is per ITEM, never per delivery.

  `apply` and `bandage` deliver no substance: neither calls
  `apply_substance`, so an item's `db.substance` does nothing
  through them. They run the treatment path (`medical_type`) only.
  A substance taken through the skin is 📋 UNBUILT (no issue).

## 2 · Encoding on items

Three pieces of metadata per consumable item:

| Field | Where | Shape | Example |
|---|---|---|---|
| Substance | `db.substance` (attribute) | string id into the registry | `"tobacco_neutral"`, `"cannabis"`, `"opium"` |
| Delivery method(s) | Tag, category `delivery_method` | one or more | `("smoke", "delivery_method")`, `("inject", "delivery_method")` |
| Usage | `db.uses_left` / `db.max_uses` (attributes) | int | `6` puffs per cigarette, `1` per pill |

Optional state:

| Field | Where | Shape |
|---|---|---|
| Lit | Tag `("lit", "cigarette_state")` (smoke only) | bool |
| Sealed / opened | Tag (TBD when bottles arrive; see Not decided) | bool |
| Loaded (pipe) | `db.substance` set to non-null when loaded | implicit; 📋 UNBUILT (no issue): no pipe exists |
| Ignition charges | `db.uses_left` on the **lighter** (absent = infinite) | int / unset |
| Substances (composed) | `db.drink_effects` | `{substance_id: doses}` map, e.g. `{"alcohol": 1}`; when set (even empty) it is used instead of `db.substance` |
| Taste line | `db.drink_taste` | string, shown with the effect lines on each sip or bite, only on items that carry `db.drink_effects` |
| Smoke form | `db.smoke_form` | string such as `"cigarette"`, `"joint"`, `"cigar"`: the item's noun in light / snuff / burnout lines; unset falls back by substance (cannabis → joint, else cigarette) |

**Ignition source charges**: a lighter's `db.uses_left` (when
present) is an independent charge counter, decremented per
`CmdLight`. An unset `uses_left` means infinite — the reusable
Zippo carries no counter; the `DISPOSABLE_LIGHTER` prototype seeds
`uses_left = 20` and is consumed to nothing. This is the same
`uses_left` field as cigarette puffs, used on a different item layer
(the ignition source rather than the consumable).

**Why tags for booleans + delivery method**: per AGENTS.md. DB-
indexed, no pickle round-trip.

**Why an attribute for substance**: substance ids are open-ended
strings, not a fixed enum, and they are read as keys into the
registry from many places. An attribute fits better than a tag here.

## 3 · Substance registry (issue #458)

Lives at `world/substances/registry.py`. `apply_substance(consumer,
id)` is the single pipeline entry point; unknown ids no-op, so
flavor-only items stay legitimate.

* **Effect vocabulary is severity-based, not float-magnitude.**
  Effects translate into the existing condition system's integer
  severities rather than carrying their own magnitude/duration
  model:
  - `pain_relief` shaves `PainCondition` severity;
  - `sedation` adds/stacks a capped
    `ConsciousnessSuppressionCondition(suppression_type="sedative")`;
  - `pain_inflict` adds a `PainCondition` of that severity (#498);
  - `nourish` eases a souled NPC's hunger meter by magnitude × 0.05
    per dose; a consumer with no soul meter (players, for now) gets
    nothing (#2074). Food carries it through the `nutrition`
    substance.

  Decay rides the conditions' own tick recovery — no parallel
  timing model.
* **There is no generic `ConditionSpec` list.** Tolerance and
  addiction are `ToleranceSpec` / `AddictionSpec` fields on each
  `Substance` (#485; see §5 item 4). `apply_substance` also counts
  every dose in `consumer.db.substance_doses`; the addiction
  threshold reads that lifetime count. Organ damage (lung damage and
  the like) is 📋 UNBUILT (no issue).

Registered entries:

| id | effects per dose | sedation cap | notes |
|---|---|---|---|
| `tobacco_neutral` | pain_relief 1 | — |  |
| `tobacco_noir` | pain_relief 1 + sedation 1 | 2 total — woozy ceiling, never blackout |  |
| `cannabis` | pain_relief 1 + sedation 1 | 2 |  |
| `alcohol` | pain_relief 1 + sedation 1 | 4 |  |
| `opium` | pain_relief 3 + sedation 2 | 5 |  |
| `guttervenom` | pain_inflict 3 + sedation 1 | 3 | no tolerance or addiction |
| `nutrition` | nourish 3 | — | no tolerance or addiction |

The built `Substance` has `effects` (severity-based), `tolerance`
and `addiction` fields. The original sketch of this spec gave
`Substance` float-magnitude `effects` with durations, a
`conditions: list[ConditionSpec]` field and a `flavor_bank_key`
naming which bank in `world/smoke.py` (or a drink module) to use.
`flavor_bank_key` was removed by owner ruling 2026-09-05 (#2767);
the note on `Substance` says the field was read by nothing and only
repeated the substance id.

## 4 · Delivery methods

| Method | Command | Tag value | Prerequisites |
|---|---|---|---|
| smoke | `CmdSmoke` | `smoke` | lit; ignition source (lighter / match) for `CmdLight` |
| inject | `CmdInject` | `inject` | vein access (skin not heavily armored) — not enforced |
| inhale | `CmdInhale` | `inhale` | conscious |
| drink | `CmdDrink` | `drink` | conscious; mouth not gagged — gag not enforced |
| eat | `CmdEat` | `eat` | conscious; mouth not gagged — gag not enforced |
| snort | 📋 UNBUILT (#1513) | `snort` | conscious; nose not destroyed |
| apply | `CmdApply` | `apply` | skin contact — not enforced |
| bandage | `CmdBandage` | `bandage` | medical item only; no substance |
| chug | `CmdChug` | `drink` | refuses medical items; every remaining use at once |
| devour | `CmdDevour` | `eat` | refuses medical items; every remaining use at once |

Every consumption verb aimed at another character also needs
trust/consent (below).

A single item can declare multiple delivery methods. A pill might
support `eat` only. A vial might support `inject` and `drink`. A
pipe loaded with a substance supports `smoke` (📋 UNBUILT (no
issue): no pipe exists yet).

The `CmdConsumption` commands gate on delivery-method tags via
`supports_delivery` (`world/consumables.py`, #474), with lazy legacy
migration from the old `medical_type` strings. `CmdChug` and
`CmdDevour` (both in `commands/CmdConsumption.py`) gate on
`supports_delivery` (`drink` / `eat` respectively) and apply every
remaining use at once via `_apply_full_dose`.

**What the Prerequisites column enforces.**

- **Conscious** is enforced one layer up. The `UnconsciousCmdSet`
  (`commands/default_cmdsets.py`) REPLACES the character cmdset
  entirely and carries no consumption verb at all, with `no_objs =
  True` (#2528) so room fixtures can't hand one back. An unconscious
  character cannot `eat` / `drink` / `inhale` / `inject` / `chug` /
  `devour` / `smoke`.
- **Third party on an unconscious target.** `check_medical_requirements`
  (`commands/CmdConsumption.py`) refuses a medical procedure on an
  unconscious patient, and `CmdInhale` checks its target explicitly
  (`CmdInhale.func`). The other verbs let a conscious character put a
  non-medical substance into an unconscious one. That is partly
  deliberate: `check_consent` grants the free path for a target that
  cannot contest (`can_contest` and `check_consent` in
  `world/consent.py`), which is what lets a medic dose a patient who
  is out cold.
- **Vein access, skin contact, gag** are not enforced. `CmdInject`
  performs no vein-access and no armor check (`CmdInject.func`);
  `apply` enforces no skin contact; and there is no gag mechanic
  anywhere in the repo (the only `gag` in the tree is combat prose),
  so the `eat` / `drink` gag check is one nothing could make. These
  rows are the same class as the `snort` row, tracked in #1513.
- **Trust/consent** is enforced for every third-party use.
  `get_item_and_target` (`commands/CmdConsumption.py`) refuses every
  consumption verb aimed at another character without `heal`-class
  consent (#2458). The gate sits in that shared funnel because a
  medical-only gate let `inject guttervenom bob` land 3 pain on an
  unwilling target.

## 5 · Current state vs target state

### Modules

* **`consume_use` (`world/consumables.py`)** — generic
  decrement-and-delete. Smoke and medical both delegate. Non-medical
  consumables route through it (#487).
* **`world/smoke.py`** — flavor banks per substance, `get_substance`
  with legacy `brand` migration, `is_smokable` with legacy-tag
  migration, helpers for lit-state and held-item lookup,
  possessive-name parser.
* **`use_item` (`world/medical/utils.py`)** — medical-item-gated
  wrapper over `consume_use` with "crumbles away" broadcast.
* **`commands/CmdSmoke.py`** — `light` / `smoke` / `snuff` routing on
  the `("smoke", "delivery_method")` tag.
  - `light` alone takes a possessive (`light <person>'s cigarette`):
    it lights a smokable in another character's hand with the
    caller's lighter. `smoke` and `snuff` act only on the caller's
    own hands.
  - The smokable is named through the core matcher over the
    smokables in the hands (`_held_smokables`, #3783): key or alias,
    ordinals (`2nd cig`), and a held smoke grenade never answers
    `smoke smoke`.
  - Each puff applies one dose through `apply_substance` (#458).
  - `CmdLight._spend_lighter` burns one `db.uses_left` charge per
    light (#803): unset = infinite (Zippo); a low-charge warning at
    ≤3; at zero the lighter announces its last flame and `delete()`s
    itself.
* **`typeclasses/smoke.py`** — `CigarettePack` fills itself to
  `capacity` cigarettes when it is created, stamping its `substance`
  on each. That fill runs before a prototype's attributes land, so
  looking at the pack repairs it first: cigarettes in it that carry
  the wrong substance are replaced one for one (#2430), and a pack
  never filled (`db.filled_once` unset) is filled. Deleting the pack
  deletes the cigarettes still in it (#2635). Its `at_object_leave`
  self-destructs the pack when the **last** cigarette is drawn
  (#801): once no cigarette remains, it tells the taker "that's the
  last one" and `delay(0, self.delete)`s the empty pack rather than
  leaving a junk husk in inventory.
* **Vending** — a street `cigarette machine` (a live-placed
  `ShopContainer` fixture, not a repo prototype) sells the
  `CIGARETTE_PACK_NOIR` pack and a `DISPOSABLE_LIGHTER` (both
  zero-cost for now). It carries an integration desc with only the
  words "cigarette machine" colored cyan, and a `get:false()` lock so
  the fixture itself can't be picked up.
* **`world/substances/`** (#458) — `Substance` / `SubstanceEffect`
  dataclasses, the registry with the seven entries in §3, the
  `apply_substance` pipeline feeding the medical condition system,
  per-substance dose bookkeeping on `db.substance_doses`.
* **`commands/CmdConsumption.py`** — the medical / substance command
  cluster, eight verbs: `eat`, `drink`, `inhale`, `inject`, `apply`,
  `bandage`, `chug`, `devour`. Delivery gating runs on tags (#474);
  trust/consent is checked in `get_item_and_target` (#2458, §4).
  `chug` and `devour` gate on the `drink` / `eat` tags, refuse
  medical items outright, and apply every remaining use at once via
  `_apply_full_dose`. `eat` also serves from a room fixture's
  `db.snacks` list (`eat <snack> [from <fixture>]`) when the eater
  holds no match: bottomless, nothing enters inventory, and the
  snack's `effects` map goes through `apply_substance` (#2074).

### The numbered areas

1. **Substance registry** at `world/substances/` (#458) — see §3.
2. **Effect pipeline** — `apply_substance` (#458), with the
   severity-based vocabulary (§3).
3. **`CmdConsumption` delivery gating** (#474). Gating runs on
   `("eat", "delivery_method")`-style tags via `supports_delivery`
   (`world/consumables.py`), which self-heals older items from their
   legacy `medical_type` (the `is_smokable` pattern).
   `medical_type` remains the pharmacology key for the treatment
   system, by design (#3207): treatment pharmacology riding
   `medical_type` (`apply_medical_effects` in
   `world/medical/utils.py`) is the design, not a migration waiting
   on a substance entry. The registry owns the habit half
   (tolerance, addiction); the treatment path owns healing.

   The stim auto-injector (`healing_acceleration`) is consumed with
   `inject`. Its effect rides the TREATMENT path (`medical_type` +
   `effectiveness` → `apply_medical_effects`, which has a
   `healing_acceleration` branch). A healing stim does not need the
   substance registry's tolerance and addiction. It is sold in two
   shops at 150 and 350 credits, and `CLINIC_SUPPLIES` dispatches it
   with the verb `inject`.

   Overturned intention: this spec recorded that the stim would map
   to no delivery verb, and that treatment effects would move to
   substance entries, until its substance entry existed. #3207
   settled instead that the treatment path is the design, and closed
   the stim gap without a substance entry. The old gate named the
   wrong subsystem, and leaving the gap meant selling a stim no verb
   could use.
4. **Tolerance / addiction** (#485), flavor-first by design decision.
   * **Tolerance** (`ToleranceSpec`): each dose adds a point to
     `db.substance_tolerance[id]`; points decay lazily by wall-clock
     hours (no tick — computed in `apply_substance`). Each full
     `points_per_level` is one level; each level shaves one point of
     per-dose effect magnitude. A fully-blunted application gets
     "It doesn't hit like it used to."
   * **Addiction** (`AddictionSpec`): crossing `threshold_doses`
     lifetime doses adds a persistent `AddictionCondition` (never
     `should_end`s — treatment is the future exit). Dormant while
     fed; `craving_after` seconds without a dose makes it contribute 1 pain via `get_pain_contribution` and
     surface craving prose (`CRAVING_PROSE` banks) on the first
     medical tick of the craving, then about every five minutes of
     real time (#501). Both clear on the next dose. **No hard stat
     penalties** — the escalation path (withdrawal stages) is
     deliberate future growth once the flavor pass is tuned.
   * Cost note: an addicted character keeps a medical script ticking
     permanently; the dormant path is two time comparisons.
     Addiction is PC-facing; mass-NPC addiction would need a
     rethink.
5. **Roll-your-own** (📋 UNBUILT (no issue)) — `roll` command that
   consumes raw substance + paper + filter and spawns a cigarette /
   joint prototype with the substance baked on.
6. **More substances** — cannabis, alcohol, opium (#487), all
   expressible in the severity vocabulary (pain_relief + sedation at
   different magnitudes/caps): cannabis is mellow (cap 2), alcohol
   numbs to properly-drunk (cap 4 = 0.60 consciousness penalty,
   standing), opium is the serious analgesic (3 pain relief/dose,
   sedation to the nod at cap 5) and hooks in ten doses. The first
   *harmful* kind is `pain_inflict` (#498): guttervenom is a weapon,
   not a habit — no tolerance/addiction specs. `inject` carries
   pharmacology (#498).

   `eat` / `drink` / `inhale` / `inject` call `apply_substance`
   (#487, #498), and the ingestion verbs do not require
   `medical_item` — the delivery tag is the gate (a bottle of rotgut
   is drinkable without being a medkit). Prototypes:
   `PRE_ROLLED_JOINT`, `ROTGUT_BOTTLE`, `OPIUM_CIGARETTE`,
   `GUTTERVENOM_SYRINGE`.

   New effect kinds (euphoria, stimulation, coordination penalty)
   are future vocabulary, grown per substance when one actually
   needs them.

## 6 · Anti-patterns to avoid

* **Per-item-type command validation.** `CmdSmoke` should not ask
  "is this a Cigarette typeclass" or "does the item key contain
  'cig'." Always check the delivery-method tag.
* **Brand-as-substance.** The substance id is the substance, not a
  brand. Tobacco is tobacco regardless of which company bagged it.
  Style variants live as substance ids (`tobacco_neutral` vs
  `tobacco_noir`) or eventually as a separate `style` axis within a
  substance entry.
* **Effects in the command.** Don't put pharmacology in
  `CmdSmoke.func()`. Effects live in the substance entry; the
  command's job is to identify the item, validate the delivery, and
  call the apply-substance pipeline.
* **Hardcoded delivery prerequisites.** The "smoke needs a lighter"
  check belongs near the smoke delivery, not buried in CmdSmoke.
  When other ignition sources exist (matches, embers, plasma cutter)
  the check should still pass.

## 7 · Fire as a separate concern

Out of scope here. The smoke system's "lit cigarette" state is *not*
a fire — it's a tag. When the broader fire system arrives
(propagation, incendiary explosives, controlled burns), it will sit
alongside this layering rather than being entangled with it.
Ignition sources (lighter, match, ember) will gain a "can ignite"
verb that the smoke delivery's `light` step delegates to.

## 8 · Maintenance contract

* **§1 (layers)** is stable design. Don't change without a refactor
  PR.
* **§3 (registry)** grows as substances and effect kinds are added;
  update it in the same PR.
* **§4 (delivery methods)** can grow — add new methods as the game
  introduces them.
* **§5 (current state)** ages quickly; refresh when substantive PRs
  land.

## Unbuilt

Each item is described where it stands above; this is the list.

- Per-delivery magnitude / speed modifier — 📋 UNBUILT (no issue), §1.
- A substance taken through the skin (`apply`) — 📋 UNBUILT (no issue), §1.
- Pipe (loaded pipe supports `smoke`) — 📋 UNBUILT (no issue), §2, §4.
- Organ damage (lung damage and the like) — 📋 UNBUILT (no issue), §3.
- `snort` delivery — 📋 UNBUILT (#1513), §4.
- Vein-access, skin-contact and gag prerequisites — stated in the §4 table but not enforced; the table's presentation is tracked with the `snort` row in #1513.
- Treatment as the exit from addiction — the future exit, §5 item 4.
- Withdrawal stages — deliberate future growth, §5 item 4.
- Roll-your-own `roll` command — 📋 UNBUILT (no issue), §5 item 5.
- New effect kinds (euphoria, stimulation, coordination penalty) — future vocabulary, §5 item 6.
- A "can ignite" verb on ignition sources, with the fire system — §7.

## Not decided

- Sealed / opened state for bottles: the tag is TBD when bottles
  arrive (§2).
- Roll-your-own: is a `roll` command that makes a cigarette or joint
  from raw substance, paper and filter still wanted, and if so which
  issue should its UNBUILT marker point at?
- Organ damage from substances (such as lung damage from smoking): is
  it still wanted, and is there an issue for it?
- Loadable pipes: are they still wanted, and is there an issue for
  them?
- Substances through the skin: should a substance applied with
  `apply` ever deliver its pharmacology, or is `apply` meant to stay
  treatment-only?

## Related documents

- `BARS_AND_RECIPES_SPEC.md` — recipe-composed drinks and dishes,
  `contributions` → `effects` (§3-§4), riding `apply_substance` (§6).
