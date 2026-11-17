# Substances and Delivery Spec

> **Status:** 🚧 **PARTIAL** — §§1-4 shipped; §5 roll-your-own remains open. ~~Verified 2026-08-02~~ **re-checked 2026-09-11: 19 claim(s) false, annotated inline**.

## 0 · Purpose

Items that introduce substances into a body — cigarettes, joints,
pills, vials, drinks, food, inhalers, patches — share more than
they differ.  This spec names the layers so future commands and
items align on the same shape instead of each inventing its own
item-type validation.

The smoke system (issue #454, then refactored under #456) is the
working example.  Medical consumption (`CmdConsumption` —
`eat`/`drink`/`inhale`/`inject`/`apply`/`bandage`) is the older
example that pre-dates this layering and will be migrated
incrementally.

## 1 · The three layers

```
   ┌────────────────────────────────────────────────────────┐
   │ ITEM         cigarette / joint / pill / vial / beer    │
   │              - holds a substance id                    │
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
   │              - prerequisites (smoke needs ignition;    │
   │                inject needs vein access)               │
   └────────────────────────────────────────────────────────┘
```

Three layers, three independent axes:

* **Item** is what the player holds.  One item, one substance,
  one or more delivery methods declared via tag.

  **Superseded 2026-09-11 — "one item, one substance" no longer
  holds.**  A recipe-composed drink or plated dish carries
  `db.drink_effects`, a `{substance_id: doses}` MAP written by
  `make_drink` in `world/bar.py`, and `_apply_substance_dose` applies every entry
  through the same pipeline (`commands/CmdConsumption.py`; 22
  prototypes carry it, e.g. `DOUBLESHIFT_LAGER` alcohol,
  `CHEWING_TOBACCO_PLUG` tobacco_neutral, `RAT_TAIL` nutrition, all in
  `world/prototypes.py`).  That shape is
  deliberate — `BARS_AND_RECIPES_SPEC` §3-§4 owns it as an
  ingredient's `contributions` summed and capped into the drink's
  `effects`, and §6 there says it rides `apply_substance` so the
  alcohol cap, tolerance and addiction all hold — it was simply never
  folded back into this spec, and the shipped attribute name
  (`db.drink_effects`) appears in no spec at all.
* **Substance** is what's actually doing pharmacology to the
  consumer.  Lives in a registry keyed by id.  Effects compose
  through the existing `MedicalState.conditions` system — no new
  runtime infrastructure needed.
* **Delivery** is the verb-level entry point.  Each delivery
  method has a command (`CmdSmoke`, `CmdInject`, etc.) that
  validates "this item supports this delivery" and applies the
  substance's effects modulated by the delivery's magnitude /
  speed.

  **Unbuilt 2026-09-11 — there is no per-delivery magnitude or speed
  modifier**, here or in the diagram's DELIVERY box above.  Greps for
  `delivery_magnitude` / `magnitude_modifier` / a delivery multiplier
  return nothing repo-wide.  `apply_substance`'s only dial is a plain
  `doses` count (`apply_substance` in `world/substances/registry.py`): `CmdSmoke` passes
  the default 1 per puff (`CmdSmoke.func`), the ingestion
  verbs pass 1 or the item's own `drink_effects` count, and
  `chug`/`devour` pass `uses_left`.  A smoked dose and an injected dose
  of the same substance are identical.  Dose count is per ITEM, never
  per delivery.

  `apply` and `bandage` deliver no substance: neither calls
  `apply_substance`, so an item's `db.substance` does nothing through
  them.  They run the treatment path (`medical_type`) only.  A
  substance taken through the skin is 📋 UNBUILT (no issue).

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
| Sealed / opened | Tag (TBD when bottles arrive) | bool |
| Loaded (pipe) | `db.substance` set to non-null when loaded | implicit; 📋 UNBUILT (no issue): no pipe exists |
| Ignition charges | `db.uses_left` on the **lighter** (absent = infinite) | int / unset |
| Substances (composed) | `db.drink_effects` | `{substance_id: doses}` map, e.g. `{"alcohol": 1}`; when set (even empty) it is used instead of `db.substance` |
| Taste line | `db.drink_taste` | string, shown with the effect lines on each sip or bite, only on items that carry `db.drink_effects` |
| Smoke form | `db.smoke_form` | string such as `"cigarette"`, `"joint"`, `"cigar"`: the item's noun in light / snuff / burnout lines; unset falls back by substance (cannabis → joint, else cigarette) |

**Ignition source charges**: a lighter's `db.uses_left` (when
present) is an independent charge counter, decremented per
`CmdLight`.  An unset `uses_left` means infinite — the reusable
Zippo carries no counter; the `DISPOSABLE_LIGHTER` prototype
seeds `uses_left = 20` and is consumed to nothing.  This is the
same `uses_left` field as cigarette puffs, used on a different
item layer (the ignition source rather than the consumable).

**Why tags for booleans + delivery method**: per AGENTS.md.  DB-
indexed, no pickle round-trip.

**Why an attribute for substance**: substance ids are open-ended
strings, not a fixed enum, and we'll want to read them as keys
into the registry from many places.  Attribute fits better than
tag here.

## 3 · Substance registry (✅ v1 shipped — issue #458)

Lives at `world/substances/registry.py`.  The shipped v1 differs
from the original sketch below in two deliberate ways:

* **Effect vocabulary is severity-based, not float-magnitude.**
  Effects translate into the existing condition system's integer
  severities rather than carrying their own magnitude/duration
  model: `pain_relief` shaves `PainCondition` severity,
  `sedation` adds/stacks a capped
  `ConsciousnessSuppressionCondition(suppression_type="sedative")`.
  `pain_inflict` adds a `PainCondition` of that severity (#498).
  `nourish` eases a souled NPC's hunger meter by magnitude × 0.05
  per dose; a consumer with no soul meter (players, for now) gets
  nothing (#2074).  Food carries it through the `nutrition`
  substance.
  Decay rides the conditions' own tick recovery — no parallel
  timing model.
* **There is no generic `ConditionSpec` list.**  Tolerance and
  addiction are `ToleranceSpec` / `AddictionSpec` fields on each
  `Substance` (#485; see §5 item 4).  `apply_substance` also counts
  every dose in `consumer.db.substance_doses`; the addiction
  threshold reads that lifetime count.  Organ damage (lung damage
  and the like) is 📋 UNBUILT (no issue).

Registered entries: `tobacco_neutral` (pain_relief 1/dose),
`tobacco_noir` (pain_relief 1 + sedation 1 capped at 2 total —
woozy ceiling, never blackout), `cannabis` (pain_relief 1 +
sedation 1, cap 2), `alcohol` (pain_relief 1 + sedation 1, cap 4),
`opium` (pain_relief 3 + sedation 2, cap 5), `guttervenom`
(pain_inflict 3 + sedation 1, cap 3; no tolerance or addiction) and
`nutrition` (nourish 3; no tolerance or addiction).  `apply_substance(consumer, id)`
is the single pipeline entry point; unknown ids no-op so
flavor-only items stay legitimate.

Original sketch, superseded and kept for the record.  The built
`Substance` has `effects` (severity-based), `tolerance` and
`addiction` fields in place of `conditions`, and `flavor_bank_key`
was removed by owner ruling 2026-09-05 (#2767); the note on
`Substance` says the field was read by nothing and only repeated
the substance id:

```python
@dataclass(frozen=True)
class Substance:
    id: str
    display_name: str
    effects: list[Effect]           # immediate per-dose effects
    conditions: list[ConditionSpec] # tolerance, addiction, damage
    flavor_bank_key: str            # which bank in world/smoke.py
                                    # (or world/drink.py etc.) to use


SUBSTANCES: dict[str, Substance] = {
    "tobacco_neutral": Substance(
        id="tobacco_neutral",
        display_name="standard tobacco",
        effects=[
            Effect("pain_level", magnitude=-0.5, duration=60),
            Effect("consciousness", magnitude=+0.02, duration=120),
        ],
        conditions=[
            ConditionSpec("tobacco_tolerance", on_use=True, ...),
            ConditionSpec("lung_damage", on_threshold=100, ...),
        ],
        flavor_bank_key="tobacco_neutral",
    ),
    "tobacco_noir": Substance(
        id="tobacco_noir",
        ...,
        flavor_bank_key="tobacco_noir",
    ),
    "cannabis": Substance(...),
    "opium": Substance(...),
}
```

Effects and conditions compose through the existing
`MedicalState` runtime — substances *declare*, the medical
script *applies and ticks*.

## 4 · Delivery methods

Initial set, mapped to existing or planned commands:

| Method | Command | Tag value | Prerequisites |
|---|---|---|---|
| smoke | `CmdSmoke` | `smoke` | lit; ignition source (lighter / match) for `CmdLight` |
| inject | `CmdInject` | `inject` | vein access (skin not heavily armored) |
| inhale | `CmdInhale` | `inhale` | conscious |
| drink | `CmdDrink` | `drink` | conscious; mouth not gagged |
| eat | `CmdEat` | `eat` | conscious; mouth not gagged |
| snort | 📋 UNBUILT (#1513) | `snort` | conscious; nose not destroyed |
| apply | `CmdApply` | `apply` | skin contact |
| bandage | `CmdBandage` | `bandage` | medical item only; no substance |
| chug | `CmdChug` | `drink` | refuses medical items; every remaining use at once |
| devour | `CmdDevour` | `eat` | refuses medical items; every remaining use at once |

A single item can declare multiple delivery methods.  A pill
might support `eat` only.  A vial might support `inject` and
`drink`.  A pipe loaded with a substance supports `smoke` (📋 UNBUILT (no issue):
no pipe exists yet).

The `CmdConsumption` commands (`eat`, `drink`, `inhale`,
`inject`, `apply`, `bandage`) gate on delivery-method tags via
`world/consumables.py:supports_delivery` (#474), with lazy legacy
migration from the old `medical_type` strings.

> **Correction 2026-09-11 — three things this table and paragraph get
> wrong about the shipped delivery layer:**
>
> - **The command list is short by two.**  `CmdChug`
>   and `CmdDevour` (both in `commands/CmdConsumption.py`) also
>   gate on `supports_delivery` (`drink` / `eat` respectively) and
>   apply every remaining use at once via `_apply_full_dose`.
> - **Most of the Prerequisites column is intent rather than code —
>   but the consciousness rows are enforced one layer up.**
>   `CmdInject` performs no vein-access and no armor check whatsoever
>   (`CmdInject.func`); `apply` enforces no skin contact; and there is no gag
>   mechanic anywhere in the repo — the only `gag` in the tree is
>   combat prose — so the `eat` / `drink` row describes a check nothing
>   could make today.  "Conscious", however, IS honoured: the
>   `UnconsciousCmdSet` REPLACES the character cmdset entirely and
>   carries no consumption verb at all (`UnconsciousCmdSet` in `commands/default_cmdsets.py`,
>   with `no_objs = True` since #2528 so room fixtures can't hand one
>   back), so an unconscious character cannot `eat` / `drink` /
>   `inhale` / `inject` / `chug` / `devour` / `smoke`.  What is
>   unenforced is the THIRD-PARTY path: `check_medical_requirements`
>   refuses a medical procedure on an unconscious patient (`:328-333`)
>   and `CmdInhale` checks its target explicitly (`CmdInhale.func`), but the
>   other verbs let a conscious character put a non-medical substance
>   into an unconscious one — and that is partly deliberate, because
>   `check_consent` grants the free path for a target that cannot
>   contest (`can_contest` and `check_consent` in `world/consent.py`), which is what lets
>   a medic dose a patient who is out cold.  As a PRESENTATION failure
>   the column is the same class as the `snort` row, tracked in #1513.
> - **The one prerequisite that IS enforced is missing from the
>   table: trust/consent.**  `get_item_and_target` refuses every
>   consumption verb aimed at another character without `heal`-class
>   consent, hoisted to that funnel by #2458 after the
>   medical-only gate let `inject guttervenom bob` land 3 pain on an
>   unwilling target.

## 5 · Current state vs target state

### What exists today

* **`world/consumables.py:consume_use`** — generic
  decrement-and-delete.  Smoke and medical both delegate.
* **`world/smoke.py`** — flavor banks per substance,
  `get_substance` with legacy `brand` migration, `is_smokable`
  with legacy-tag migration, helpers for lit-state and
  held-item lookup, possessive-name parser.
* **`world/medical/utils.py:use_item`** — medical-item-gated
  wrapper over `consume_use` with "crumbles away" broadcast.
* **`commands/CmdSmoke.py`** — `light` / `smoke` / `snuff`
  routing on the `("smoke", "delivery_method")` tag.  `light`
  alone takes a possessive (`light <person>'s cigarette`): it lights a
  smokable in another character's hand with the caller's lighter.
  `smoke` and `snuff` act only on the caller's own hands.  The smokable is named
  through the core matcher over the smokables in the hands
  (`_held_smokables`, #3783): key or alias, ordinals (`2nd cig`),
  and a held smoke grenade never answers `smoke smoke`.  Each puff applies one
  dose through `apply_substance` (#458).  `CmdLight._spend_lighter`
  burns one `db.uses_left` charge per light (#803): unset =
  infinite (Zippo), zero → the lighter announces its last flame
  and `delete()`s itself, with a low-charge warning at ≤3.
* **`typeclasses/smoke.py`** — `CigarettePack` fills itself to
  `capacity` cigarettes when it is created, stamping its `substance`
  on each.  That fill runs before a prototype's attributes land, so
  looking at the pack repairs it first: cigarettes in it that carry
  the wrong substance are replaced one for one (#2430), and a pack
  never filled (`db.filled_once` unset) is filled.  Deleting the pack
  deletes the cigarettes still in it (#2635).  Its
  `at_object_leave` self-destructs the pack when the **last**
  cigarette is drawn (#801): once no cigarette remains, it tells
  the taker "that's the last one" and `delay(0, self.delete)`s the
  empty pack rather than leaving a junk husk in inventory.
* **Vending** — a street `cigarette machine` (a live-placed
  `ShopContainer` fixture, not a repo prototype) sells the
  `CIGARETTE_PACK_NOIR` pack and a `DISPOSABLE_LIGHTER` (both
  zero-cost for now).  It carries an integration desc with only
  the words "cigarette machine" colored cyan, and a `get:false()`
  lock so the fixture itself can't be picked up.
* **`world/substances/`** (#458) — `Substance` /
  `SubstanceEffect` dataclasses, registry with the seven
  entries listed in §3, `apply_substance` pipeline feeding the medical
  condition system, per-substance dose bookkeeping on
  `db.substance_doses`.
* **`commands/CmdConsumption.py`** — the medical / substance
  command cluster (eat/drink/inhale/inject/apply/bandage).
  Delivery gating migrated to tags in #474; treatment effects
  still key off `medical_type` pending the substance-entry
  migration (item 6).
  **Correction 2026-09-11:** the cluster is EIGHT verbs — `CmdChug`
  and `CmdDevour` ship too, gate on the same
  `drink` / `eat` tags, refuse medical items
  outright, and apply every remaining use at once via
  `_apply_full_dose`.  The "pending" clause is stale in both
  halves: item 6 closed in #487, and #3207 (item 3 above) settled that
  treatment pharmacology riding `medical_type`
  (`apply_medical_effects` in `world/medical/utils.py`) is the DESIGN, not a migration
  waiting on a substance entry — the registry owns the habit half
  (tolerance, addiction), the treatment path owns healing.  Also
  unrecorded here: the trust/consent gate #2458 hoisted into
  `get_item_and_target`, the one delivery prerequisite
  enforced for every third-party use.
  `eat` also serves from a room fixture's `db.snacks` list
  (`eat <snack> [from <fixture>]`) when the eater holds no match:
  bottomless, nothing enters inventory, and the snack's `effects`
  map goes through `apply_substance` (#2074).

### Gaps to close (separate PRs)

1. ~~**Substance registry** at `world/substances/`~~ — ✅ shipped
   v1 in #458 (see §3).
2. ~~**Effect pipeline** — `apply_substance`~~ — ✅ shipped v1 in
   #458 with the severity-based vocabulary (`pain_relief`,
   `sedation`).
3. ~~**`CmdConsumption` migration**~~ — ✅ shipped in #474.
   Delivery gating runs on `("eat", "delivery_method")` tags via
   `world/consumables.py:supports_delivery`, which self-heals
   pre-#474 items from their legacy `medical_type` (the
   `is_smokable` pattern).  `medical_type` remains the
   pharmacology key for the treatment system.  The dead
   `CmdConsumption.CmdSmoke` (unregistered since #454) was
   deleted.  ~~Known preserved gap: `healing_acceleration` (the
   stim auto-injector) maps to no delivery verb — it was not
   consumable before and stays that way until its substance entry
   exists.~~ **Closed in #3207 without waiting for the substance
   entry.** The gate named the wrong subsystem: a stimpak's effect
   rides the TREATMENT path (`medical_type` + `effectiveness` →
   `apply_medical_effects`), which has carried a working
   `healing_acceleration` branch since before the gap was recorded.
   The substance registry is the pharmacology half — tolerance and
   addiction — which a healing stim does not need.  Meanwhile the
   item was stocked in two shops at 150 and 350 credits and
   dispatched by `CLINIC_SUPPLIES` with the verb `inject`, so the
   preserved gap was shipping a purchasable no-op.
4. ~~**Tolerance / addiction conditions**~~ — ✅ shipped in #485
   (flavor-first by design decision).
   * **Tolerance** (`ToleranceSpec`): each dose adds a point to
     `db.substance_tolerance[id]`; points decay lazily by
     wall-clock hours (no tick — computed in `apply_substance`).
     Each full `points_per_level` is one level; each level shaves
     one point of per-dose effect magnitude.  A fully-blunted
     application gets "It doesn't hit like it used to."
   * **Addiction** (`AddictionSpec`): crossing `threshold_doses`
     lifetime doses adds a persistent
     `AddictionCondition` (never `should_end`s — treatment is the
     future exit).  Dormant while fed; `craving_after` seconds
     without a dose makes it contribute 1 pain via
     `get_pain_contribution` and surface craving prose
     (`CRAVING_PROSE` banks) on the first medical tick of the craving,
     then about every five minutes of real time (#501).  Both clear
     on the next dose.  **No hard stat penalties in v1** — the
     escalation path (withdrawal stages) is deliberate future
     growth once the flavor pass is tuned.
   * Cost note: an addicted character keeps a medical script
     ticking permanently; the dormant path is two time
     comparisons.  Addiction is PC-facing; mass-NPC addiction
     would need a rethink.
5. **Roll-your-own** (📋 UNBUILT (no issue)) — `roll` command that consumes raw
   substance + paper + filter and spawns a cigarette / joint
   prototype with the substance baked on.
6. ~~**More substances**~~ — ✅ cannabis, alcohol, opium shipped
   in #487, all expressible in the existing severity vocabulary
   (pain_relief + sedation at different magnitudes/caps): cannabis
   is mellow (cap 2), alcohol numbs to properly-drunk (cap 4 =
   0.60 consciousness penalty, standing), opium is the serious
   analgesic (3 pain relief/dose, sedation to the nod at cap 5)
   and hooks in ten doses.  New effect kinds (euphoria,
   stimulation, coordination penalty) remain future vocabulary —
   grown per substance when one actually needs them.  First
   *harmful* kind shipped in #498: ``pain_inflict`` (guttervenom —
   a weapon, not a habit: no tolerance/addiction specs).  #498 also
   wired ``inject`` to carry pharmacology — the one verb #487
   missed.
   Also in #487: **eat/drink/inhale now call ``apply_substance``**
   (previously only smoke delivered pharmacology), non-medical
   consumables route through ``consume_use``, and the ingestion
   verbs no longer require ``medical_item`` — the delivery tag is
   the gate (a bottle of rotgut is drinkable without being a
   medkit).  Prototypes: PRE_ROLLED_JOINT, ROTGUT_BOTTLE,
   OPIUM_CIGARETTE (and GUTTERVENOM_SYRINGE from #498).

## 6 · Anti-patterns to avoid

* **Per-item-type command validation.** `CmdSmoke` should not
  ask "is this a Cigarette typeclass" or "does the item key
  contain 'cig'."  Always check the delivery-method tag.
* **Brand-as-substance.** The substance id is the substance,
  not a brand.  Tobacco is tobacco regardless of which company
  bagged it.  Style variants live as substance ids
  (`tobacco_neutral` vs `tobacco_noir`) or eventually as a
  separate `style` axis within a substance entry.
* **Effects in the command.** Don't put pharmacology in
  `CmdSmoke.func()`.  Effects live in the substance entry; the
  command's job is to identify the item, validate the delivery,
  and call the apply-substance pipeline.
* **Hardcoded delivery prerequisites.** The "smoke needs a
  lighter" check belongs near the smoke delivery, not buried
  in CmdSmoke.  When other ignition sources exist (matches,
  embers, plasma cutter) the check should still pass.

## 7 · Fire as a separate concern

Out of scope here.  The smoke system's "lit cigarette" state is
*not* a fire — it's a tag.  When the broader fire system arrives
(propagation, incendiary explosives, controlled burns), it will
sit alongside this layering rather than being entangled with it.
Ignition sources (lighter, match, ember) will gain a "can ignite"
verb that the smoke delivery's `light` step delegates to.

## 8 · Maintenance contract

* **§1 (layers)** is stable design.  Don't change without a
  refactor PR.
* **§3 (registry)** grows as substances and effect kinds are
  added; update it in the same PR.
* **§4 (delivery methods)** can grow — add new methods as the
  game introduces them.
* **§5 (current state)** ages quickly; refresh when substantive
  PRs land.
