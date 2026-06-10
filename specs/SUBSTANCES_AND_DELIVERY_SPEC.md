# Substances and Delivery Spec

**Status**: descriptive of the three-layer model and how
current code maps onto it.  Substance registry + effect →
condition pipeline are scoped for a future PR, not implemented
here.

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
* **Substance** is what's actually doing pharmacology to the
  consumer.  Lives in a registry keyed by id.  Effects compose
  through the existing `MedicalState.conditions` system — no new
  runtime infrastructure needed.
* **Delivery** is the verb-level entry point.  Each delivery
  method has a command (`CmdSmoke`, `CmdInject`, etc.) that
  validates "this item supports this delivery" and applies the
  substance's effects modulated by the delivery's magnitude /
  speed.

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
| Loaded (pipe) | `db.substance` set to non-null when loaded | implicit |

**Why tags for booleans + delivery method**: per AGENTS.md.  DB-
indexed, no pickle round-trip.

**Why an attribute for substance**: substance ids are open-ended
strings, not a fixed enum, and we'll want to read them as keys
into the registry from many places.  Attribute fits better than
tag here.

## 3 · Substance registry (planned, not built)

When ready, lives at `world/substances/registry.py`:

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
| snort | `CmdSnort` | `snort` | conscious; nose not destroyed |
| apply | `CmdApply` | `apply` | skin contact |

A single item can declare multiple delivery methods.  A pill
might support `eat` only.  A vial might support `inject` and
`drink`.  A pipe loaded with a substance supports `smoke`.

The currently-shipped `CmdConsumption` commands (`eat`, `drink`,
`inhale`, `inject`, `apply`, `bandage`) check for `medical_type`
strings rather than delivery-method tags.  They'll migrate to
this scheme when the substance registry lands.

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
  routing on the `("smoke", "delivery_method")` tag.  Cross-
  character syntax via possessive parser.
* **`commands/CmdConsumption.py`** — the older medical /
  substance command cluster (eat/drink/inhale/inject/apply/
  bandage).  Pre-dates the layering.

### Gaps to close (separate PRs)

1. **Substance registry** at `world/substances/`.  Centralises
   substance metadata; replaces the implicit registry in flavor
   banks.
2. **Effect pipeline** — `apply_substance(substance, consumer)`
   that emits effects into the medical condition system.
3. **`CmdConsumption` migration** — switch from `medical_type`
   strings to `("eat", "delivery_method")` / `("drink", ...)`
   tags.  Same shape as the smoke commands.
4. **Tolerance / addiction conditions** — concrete
   `ConditionSpec` examples + medical-script tick integration.
5. **Roll-your-own** — `roll` command that consumes raw
   substance + paper + filter and spawns a cigarette / joint
   prototype with the substance baked on.

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
* **§3 (registry)** is the next implementation target; expect
  this section to evolve as the registry lands.
* **§4 (delivery methods)** can grow — add new methods as the
  game introduces them.
* **§5 (current state)** ages quickly; refresh when substantive
  PRs land.
