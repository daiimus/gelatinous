# Medical Substrate Roadmap

> Renamed from `MEDICAL_COMBAT_AUDIT_AND_REMEDIATION_SPEC` (2026-06-14).
> This is a **forward roadmap**, not a historical audit — the findings
> below seeded a phased plan for building the medical/combat substrate
> consumers, and most phases are still ahead. The at-a-glance flag map
> lives in `MEDICAL_SUBSTRATE_READINESS.md`.

## Overview

Started as an end-to-end audit of the medical and combat systems, the
death-progression pipeline, and the tertiary systems they depend on
(wounds, conditions, armor, corpse, hit selection). It catalogued every
drift, dead metadata flag, and documented-but-unimplemented feature found,
and laid out a prioritised remediation plan with discrete phases. That
remediation plan — building the substrate consumers the schema advertises —
is the live content; the audit catalogue is its rationale.

Status: **active roadmap** (Phase 1 complete; 2–13 ahead — see the
Implementation Progress true-up below). Origin: audit pass after the
pelvis-in-groin fix (issue #325) surfaced broader questions about the
death model and dead metadata.

## Implementation Progress (June 2026 true-up)

This spec is a planning artifact; as phases land, their content gets
absorbed into canonical specs and the corresponding section here is
trimmed. The current state of the remediation plan against shipped
work:

| Phase | Status | Notes |
|---|---|---|
| Phase 1 — Documentation & Architectural Clarification | **✅ Complete** | All four tasks shipped. Task 1: `LETHAL_CAPACITY_NAMES` comment in `world/medical/constants.py` now explicitly documents the union role. Task 2: `MedicalState.is_dead` / `is_unconscious` / `calculate_body_capacity` docstrings spell out the substrate-vs-runtime split and cross-reference the audit's phase numbers. Task 3: HEALTH spec's brain-death `# NEXT:` pseudo-code now explicitly points at audit Phase 2 instead of reading as an open design note. Task 4: `specs/MEDICAL_SUBSTRATE_READINESS.md` index lists every unconsumed flag with its intended consumer system and audit phase. |
| Phase 2 — Brain Death Blocks Revival | Not started | `_check_medical_revival_conditions` still gates only on `is_dead()`. |
| Phase 3 — Failure-Mode Surfacing | Not started | Empty-distribution / unbacked-container warnings not wired. |
| Phase 4 — Vestigial-Flag Deletion | Not started | All flags listed under "Vestigial (delete)" still present. |
| Phase 5 — `LETHAL_CAPACITY_NAMES` Split | Not started | Split into `IS_DEAD_LETHAL_CAPACITIES` + `TARGETING_VITAL_CAPACITIES` not done. |
| Phase 6 — Chronic Medical Conditions Framework (Track 2) | Not started | Substrate gate for kidney death + other long-term conditions. |
| Phase 7 — Movement Policing Substrate (Track 2) | Not started | Substrate gate for `moving` incapacitation + paralysis. |
| Phase 8 — Senses System (Track 2) | Not started | Substrate gate for blindness / deafness. |
| Phase 9 — Equipment-Handling Substrate (Track 2) | Not started | Substrate gate for `manipulation` consequences. |
| Phase 10–13 — Wiring & Cleanup (Track 3) | Blocked | Each phase has substrate dependencies that aren't met yet. |

**Recent surgery work (June 2026) is orthogonal to this audit.** The
procedural surgery system (Phase 2.8 in `HEALTH_AND_SUBSTANCE_SYSTEM_SPEC.md`),
the operate charting command (Phase 2.9), and the severance / suture-stump /
install-picker / combat-incision-symmetry work (Phase 2.10) all sit *above*
the substrate gaps this audit identified — the procedural verbs read /
mutate organ HP and `wound_stage`, but none of them introduces or resolves
a substrate consumer for things like `incapacitation_threshold`,
`paralysis_if_destroyed`, or `total_loss_penalty`. Those substrate phases
remain the right next focus for an audit-aligned arc.

**The anatomy-augments + cyberware arc (#511–#551) is likewise orthogonal
to the substrate gaps.** Chassis+module cyberware, spec-carrying
replacement organs, inorganic damage (pain-only), reattachment, and
chrome severance prose all read / mutate organ HP, `wound_stage`,
`inorganic`, and `abilities` — but none introduces or resolves a consumer
for `incapacitation_threshold`, `paralysis_if_destroyed`, or
`total_loss_penalty`. The substrate phases are unchanged by it. One
*genuine new wrinkle* the arc exposed, though: augment organs can **add**
anatomy and capacities a species table never declared (the cyber tail).
The substrate plan (Phases 7–9) assumes the static species table is the
full capacity set; **per-character capacity extension** is an
un-catalogued substrate concern to fold into movement-policing /
senses / equipment-handling whenever those are scoped. Tracked in
`MEDICAL_SUBSTRATE_READINESS.md`.

The audit's Core Insight ("schema without consumers") still stands and
sequences correctly: build substrate before wiring schema to it.

**On the "unconsumed flag" findings** — the validation pass against
current code (June 2026) confirmed all 13 of the Category B flag
read-counts still hold: those flags really are sitting un-consumed by
runtime code. But the framing was wrong to call them drift. They aren't
half-finished code waiting for cleanup; they are **declarative metadata
deliberately authored ahead of the consumer systems that will read them**,
exactly as the Core Insight describes. The audit is acting as a
substrate-readiness map: each flag advertises a design hook for a system
that hasn't been scoped yet (movement policing, senses, chronic
conditions, social policing, equipment-handling). Treat the audit doc as
a *forward-looking design index*, not a bug list. The phased remediation
plan still applies whenever any of those substrates does get scoped.

---

## Core Insight — Schema Without Consumers

The repeated pattern surfaced by this audit isn't "dead code from sloppy
work" — it's **a top-down anatomical schema whose bottom-up consumers were
never built**. The medical system has three intended layers:

1. **Schema** (`ORGANS`, `BODY_CAPACITIES`, threshold constants). Authored
   anatomically — heart, lungs, kidneys, spine, brain, with realistic
   contributions and thresholds.
2. **Capacity calculation** (`MedicalState.calculate_body_capacity`,
   `update_vital_signs`). Implemented and load-bearing.
3. **Consumer systems** that *react to* capacity loss — perception/senses,
   movement policing, equipment-handling rules, chronic medical
   conditions. **Largely unbuilt.**

Capacity loss therefore has nowhere to go. A character with 0 `sight`
capacity can still see; with 0 `hearing` they hear; with 12% `moving`
they walk normally; with the spine destroyed they stand. The schema
predicts these outcomes; nothing in the runtime enforces them.

This means the dead flags are *not* a cleanup target. They are a
**substrate-readiness signal**: each flag advertises a consumer system
that hasn't been written yet. Deleting them would be deleting design
documentation. The right work is **building the substrates**, then wiring
the flags into them.

The plan in this spec is sequenced around that insight: foundational
consumer systems first (where their absence is the gate), then wiring,
then a final flag-audit pass that deletes only what no consumer ever
plans to use.

---

## Background

The medical system is structured as three layers:

1. **Static schema** in `world/medical/constants.py` — `ORGANS`, `BODY_CAPACITIES`,
   `LETHAL_CAPACITY_NAMES`, thresholds.
2. **Runtime state** in `world/medical/core.py` — `Organ`, `MedicalState`,
   `is_dead`, `is_unconscious`, `calculate_body_capacity`, `update_vital_signs`.
3. **Tickers and effects** in `world/medical/conditions.py` and
   `world/medical/script.py` — bleeding / pain / infection / consciousness
   suppression, with a 12-second per-character `MedicalScript` driving them.

Combat reaches into the medical layer through `ArmorMixin.take_damage`
(`typeclasses/armor_mixin.py`), which applies armor reduction, calls
`apply_anatomical_damage`, then checks `is_dead()` / `is_unconscious()`
and dispatches to `at_death()` / `_handle_unconsciousness()`. The combat
handler itself (`world/combat/handler.py`) orchestrates turns; the per-attack
logic lives in `world/combat/attack.py`.

Death after the synchronous attack is *not* immediate — `at_death()` shows
the death curtain and launches a 360-second `DeathProgressionScript`
(`typeclasses/death_progression.py`) with an 11-message narrative and a
medical-revival window.

The system has evolved through ~14 medical-related PRs (#243 decapitation,
#251/#252 vital-locations refactor, #254 spinal rename, #325 pelvis-in-groin)
plus many incremental fixes. The aggregate result is **correct in the paths
that get exercised, but carries substantial unimplemented design intent in
the form of declarative metadata**.

---

## Findings

### Category A — Death Model: Aligned, Documented, But Comment-Drifted

| Item | Current Code | Spec Intent | Verdict |
|---|---|---|---|
| `is_dead()` checks `blood_pumping`, `breathing`, `digestion`, `neck_integrity`, blood loss | Yes | Yes (`HEALTH_AND_SUBSTANCE_SYSTEM_SPEC.md` L731–746) | **Correct** |
| Brain destruction → unconsciousness, not death | Yes | Yes (L732 "consciousness is unconsciousness, not death") | **Intentional** |
| Brain destruction eventually kills via secondary bleeding | Yes (head wound → `BleedingCondition` → blood loss → `is_dead`) | Implicit | **Works** |
| Kidney loss is fatal | **No** (`is_dead` never reads `blood_filtration`) | Schema says `total_loss_fatal: True` | **DRIFT** |
| Comment above `LETHAL_CAPACITY_NAMES` "Keep in sync with is_dead()" | Misleading — it's actually a superset (adds `consciousness` for vital-location bias) | Spec clarifies | **✅ RESOLVED** (Phase 1 Task 1 — comment at `world/medical/constants.py:273-279` now explicitly documents the union role) |

**Action**: ~~Rewrite the `LETHAL_CAPACITY_NAMES` comment to explicitly say~~
~~"this is the union of `is_dead()` lethal capacities PLUS `consciousness`,~~
~~which makes the head a vital target but is unconsciousness rather than~~
~~death".~~ ✅ **Done.** The comment now explicitly states the
union-of-lethal-and-targeting role and notes consciousness drives unconsciousness, not death. ~~This stops future devs from incorrectly "syncing" `consciousness`~~
into `is_dead`. **Resolve kidney case** as a separate design call (below).

### Category B — Declarative Metadata Awaiting Substrate

I audited every flag in `ORGANS` and `BODY_CAPACITIES` for read-counts
outside of the constants file and tests. The "Disposition" column
reflects the Core Insight above: most of these are *not* dead code, they
are waiting on a consumer system that hasn't been built.

| Flag | Reads | Intended Consumer | Disposition |
|---|---|---|---|
| `vital` (on `Organ`) | 0 | None — superseded by data-driven `_get_vital_locations` | **Vestigial**: delete. |
| `fatal_threshold` (on capacity) | 0 | Could replace the `<= 0.0` literal in `is_dead` if `is_dead` were refactored to be data-driven | Keep until Phase 7 audit (delete or wire). |
| `directly_fatal` (on capacity) | 0 (1 test assertion) | Same as `fatal_threshold` — data-driven `is_dead` | Keep until Phase 7 audit. |
| `total_loss_fatal: True` on `blood_filtration` | 0 | **Chronic Conditions framework** — total kidney loss should spawn a fatal `RenalFailure` condition that takes time to kill (not instant death) | **Substrate gap**: chronic conditions. |
| `incapacitation_threshold: 0.15` on `moving` | 0 | **Movement Policing system** — when capacity is below this, character cannot move | **Substrate gap**: movement policing. |
| `unconscious_threshold` (in `consciousness` capacity dict) | 0 | None — duplicated as top-level `CONSCIOUSNESS_UNCONSCIOUS_THRESHOLD` (the one that's actually read) | **Vestigial**: delete. |
| `modifiers: ["pain", "blood_pumping", ...]` on `consciousness` | 0 | The cascade is already implemented imperatively in `update_vital_signs`; this list is documentation only | **Vestigial**: delete or convert to spec comment. |
| `affects: ["consciousness", "moving"]` on capacities | 0 | Could drive a generic capacity-effect graph; currently a manual `update_vital_signs` formula does the work | **Vestigial unless** a generic effect-graph is built. |
| `total_loss_penalty: "blindness"` / `"deafness"` | 0 | **Senses System** — total loss should spawn `BlindCondition` / `DeafCondition` and gate perception | **Substrate gap**: senses. |
| `total_loss_effects: ["cannot_negotiate", ...]` on `talking` | 0 | **Social interaction rules** — can't speak → can't negotiate, persuade, etc. | **Substrate gap**: social system policing. |
| `cannot_be_destroyed: True` on `thoracolumbar_spine` | 0 | Should clamp `Organ.take_damage` to floor at 1 HP for this organ | **Direct wire** — small fix, no substrate dependency. |
| `paralysis_if_destroyed: True` on `thoracolumbar_spine` | 0 | **Movement Policing system** — produces a permanent `ParalysisCondition` that zeroes `moving` capacity | **Substrate gap**: movement policing. |
| `can_be_destroyed` (most organs) | 0 (1 test) | Inverse of `cannot_be_destroyed`; redundant if the negative form is the canonical one | **Vestigial**: delete after `cannot_be_destroyed` is wired. |
| `fracture_vulnerable` | 4 | Used by bone-fracture condition spawn path | Live, keep. |
| `bone_type` | 5 | Used by bone-fracture and severance routing | Live, keep. |

**13 of 15 audited flags are unconsumed by code today.** Reclassified by
the rubric above:

* **Vestigial (delete)**: `vital` (organ), `unconscious_threshold` (dict
  copy), `modifiers`, `affects`, `can_be_destroyed`.
* **Direct wire (no substrate)**: `cannot_be_destroyed` on spine.
* **Substrate-gap (build substrate first, then wire)**: `total_loss_fatal`
  (chronic conditions), `incapacitation_threshold` (movement),
  `total_loss_penalty` blindness/deafness (senses), `total_loss_effects`
  (social), `paralysis_if_destroyed` (movement).
* **Audit-later**: `fatal_threshold`, `directly_fatal` — keep until
  `is_dead` refactor lands.

**This reclassification is the central reason the original Phase 4 and
Phase 5 cannot ship as I originally scoped them**: their work is gated on
substrate that doesn't exist yet.

### Category C — Documented "Next" Features

These features are explicitly described in `HEALTH_AND_SUBSTANCE_SYSTEM_SPEC`
as future work or "could be added".

| Feature | Spec ref | Current state |
|---|---|---|
| **Brain death blocks revival** in death progression | L273–296 — has `# NEXT:` pseudo-code | Not implemented. `_check_medical_revival_conditions` only checks `is_dead()`. A brain-destroyed character whose bleeding stops could currently revive into a vegetative shell. |
| **Movement incapacitation at <15% moving capacity** | L219 (`incapacitation_threshold: 0.15`) | Not enforced. Walk commands don't check capacity. |
| **Blindness on `sight = 0`** | `total_loss_penalty: "blindness"` | Not enforced. Combat targeting / look unaffected. |
| **Deafness on `hearing = 0`** | `total_loss_penalty: "deafness"` | Not enforced. |
| **Paralysis on thoracolumbar spine destruction** | `paralysis_if_destroyed: True` | Not enforced. Spine can be destroyed but produces no paralysis condition. |
| **Manipulation loss → drop weapons / can't wield** | `affects: ["work_speed", "melee_accuracy"]` | Not enforced beyond hit accuracy implicitly. |
| **Pain-driven unconsciousness path** | `PAIN_UNCONSCIOUS_THRESHOLD: 80` | **Partially**: pain reduces `self.consciousness` float, which then trips the consciousness threshold. Not a direct check, but functionally equivalent. |

### Category D — Combat-Side Drift

| Item | State |
|---|---|
| `select_hit_location` falls back to `chest` when character has no longdesc | Defensive but masks bad data — a logged warning would surface broken anatomy. |
| `damage_distribution = {}` falls through to `total_damage: damage_amount` with no organs damaged | This was the **groin pre-#325 bug**. Now fixed for groin, but the *failure mode* still exists: any future location with no organs silently absorbs damage with no medical effect. Should raise / log. |
| `select_target_organ` returns `None` for organ-less locations, but `take_damage` accepts `target_organ=None` and routes via location-wide distribution | Coherent but only works *if* the location has any organs. |
| `take_damage` claim/reality split | `take_damage` returns `(died, final_damage)` to the combat system, but if the medical layer applied no actual damage (organ-less location, all destroyed), the `final_damage` value is misleading — combat sees "hit for X" but body has no record. |
| Combat-driven severance trigger checks `SEVERING_INJURY_TYPES` (`cut`/`stab`/`laceration`) | Documented in spec, works. |
| `unconscious_pending` flag on combat hit defers UI message until after the hit narrative | Works. |
| `_calculate_armor_damage_reduction` runs before `apply_anatomical_damage` | Correct ordering. |

### Category E — Tertiary System Touchpoints

| System | Touch point | State |
|---|---|---|
| **Wounds** (`world/medical/wounds/`) | `take_organ_damage` calls `_create_conditions_from_damage` which spawns `BleedingCondition`/`PainCondition`/`InfectionCondition`. Wound *prose* renders via `append_wounds_to_longdesc` and the per-injury-type message dicts. | Solid. |
| **Armor** (`typeclasses/armor_mixin.py`) | `_calculate_armor_damage_reduction(amount, location, injury_type)` via the effectiveness matrix in `world/combat/constants.py` | Works. Tied to clothing coverage. |
| **Conditions / `MedicalScript`** | 12-second per-character ticker, drives bleeding-out, pain decay, infection progression | Works. Calls `is_dead()` after each tick → triggers `at_death()` if conditions push body past threshold. This is the path that makes brain destruction *eventually* lethal. |
| **Death Progression** (`typeclasses/death_progression.py`) | 360s revival window with 11 narrative messages; `_check_medical_revival_conditions` calls `is_dead()` to detect treatment success | Works, but doesn't check brain HP for revival blocking (per Category C). |
| **Corpse** (`typeclasses/corpse.py`) | Death-time snapshot of `physical_description`, `longdesc_data`, `wounds_at_death`, `apparent_uid_at_death`, `signature_at_death`, medical snapshot | Works. Recently de-bugged (#319, #320, #323, #324). |
| **Forensics** (`world/forensics.py`) | Reads corpse signature for autopsy; blood-pool extractor exists but has no command | **✅ Fully resolved (PR #441 / #442)**: corpse-side surfaces all shipped — `commands/forensics.py` carries `CmdInspect` (alias `autopsy`) / `CmdSever` / `CmdHarvest`, and the procedural surgery verbs read the same snapshots. `CmdInspect` also handles `BloodPool` by dispatching `extract_subject_from_blood_pool_incident` per unique apparent UID, with distinguishable / indistinguishable bucketing so old crime scenes render readably. The full audit Finding 39 plan now has player surface coverage. |
| **Hit Selection** (`select_hit_location`) | Data-driven from organ schema; vital-location bias from `_get_vital_locations` (which derives from `LETHAL_CAPACITY_NAMES`) | Works. |

### Category F — Architectural Tensions

1. **Two consciousness names mean different things.**
   - `self.consciousness` (float on `MedicalState`) is the *runtime value*
     including pain/blood penalties.
   - `calculate_body_capacity("consciousness")` is the *organ-only floor*
     (brain HP fraction).
   - `is_unconscious()` checks `self.consciousness < threshold`.
   - `is_dead()` doesn't check either.
   - **No bug, but confusing**. A docstring on each helper clarifying which
     value it reads would prevent future drift.

2. **The "no organs in container" failure mode is silent.**
   - Pre-#325 groin demonstrated this: a damage call to a location with
     zero registered organs returns success-shaped data but applies no
     medical effect.
   - Now that the bug is fixed for groin, the failure mode itself remains —
     any future anatomy slot missing organ coverage will repeat it without
     a single log line.

3. **`LETHAL_CAPACITY_NAMES` overloads two concepts.**
   - It's both the "what kills you" set AND the "what makes a location a
     vital target" set, with `consciousness` artificially added for the
     latter purpose.
   - Splitting into `LETHAL_CAPACITY_NAMES` (true lethal) and
     `VITAL_TARGETING_CAPACITY_NAMES` (lethal ∪ incapacitating) would
     remove the comment confusion that triggered this audit.

4. **`_get_vital_locations` is called per-attack.**
   - Iterates `LETHAL_CAPACITY_NAMES` → `BODY_CAPACITIES` → `ORGANS` →
     containers on every hit selection. Acceptable but cacheable; not
     urgent.

---

## Drift Quick Reference (Headline Items)

* ~~`LETHAL_CAPACITY_NAMES` comment overstates synchrony with `is_dead`.~~ ✅ Resolved — comment now documents the union role.
* `blood_filtration.total_loss_fatal` is data-true but code-false (kidney loss is "fatal" in spec, ignored in runtime).
* `incapacitation_threshold` on `moving` is documented but never enforced.
* `total_loss_penalty` on `sight`/`hearing` describes blindness/deafness; neither is produced as a condition.
* `cannot_be_destroyed` and `paralysis_if_destroyed` on `thoracolumbar_spine` are noted in the spec; neither is honored.
* Brain-blocks-revival is `# NEXT:` in spec and not in code.
* `Organ.vital` is set on init from schema; never read.

---

## Remediation Plan

The plan is sequenced around the Core Insight: **build substrate before
wiring schema to it**. Phases are grouped into three tracks:

* **Track 1 — Standalone Now** (no substrate dependency).
* **Track 2 — Foundational Substrates** (build the missing consumer systems).
* **Track 3 — Wiring & Cleanup** (only meaningful after Track 2 lands).

Each phase ships as a single PR (sub-issues if review-sized).

---

### Track 1 — Standalone Now

These phases have no substrate dependency. They ship in any order and
deliver visible value immediately.

#### Phase 1 — Documentation & Architectural Clarification (no behavior change)

**Goal**: Lock in the intentional design boundaries so future audits stop
re-discovering the same drift.

Tasks:

1. Rewrite the `LETHAL_CAPACITY_NAMES` comment in `world/medical/constants.py`
   to explicitly state the dual role (lethal ∪ targeting-vital), and that
   consciousness is in it for *targeting* not for *death*.
2. Add per-method docstrings to `MedicalState.is_dead`, `is_unconscious`,
   `calculate_body_capacity` clarifying:
   - `is_dead` enforces four lethal capacities + blood-loss floor.
   - `is_unconscious` reads the runtime `self.consciousness` (which
     includes pain / blood / suppression penalties).
   - `calculate_body_capacity` returns the organ-only floor for that
     capacity.
3. Reframe `HEALTH_AND_SUBSTANCE_SYSTEM_SPEC.md`'s `# NEXT:` brain-death
   pseudo-code: point it at Phase 2 of this spec.
4. Add a `specs/MEDICAL_SUBSTRATE_READINESS.md` index that documents
   each declarative flag, its intended consumer system, and the phase
   that will wire it.

**Effort**: half-day.
**Risk**: zero.
**Dependencies**: none.

#### Phase 2 — Brain Death Blocks Revival

**Goal**: Ship the spec's `# NEXT:` feature. A brain-destroyed character
cannot revive from the death-progression window, even if other lethal
capacities are repaired.

Tasks:

1. Add `_brain_is_destroyed()` helper on `MedicalState`.
2. Update `DeathProgressionScript._check_medical_revival_conditions` to
   return `False` when brain is destroyed regardless of other state.
3. Add a revival-failure message for the dying character (RP cue).
4. Tests: revival succeeds when bleeding stops; revival fails when brain
   destroyed.

**Effort**: small.
**Risk**: low.
**Dependencies**: none.

#### Phase 3 — Failure-Mode Surfacing

**Goal**: The "location has no organs" failure mode (pre-#325 groin)
shipped silently for a long time. Make the next one loud.

Tasks:

1. `apply_anatomical_damage`: when `damage_distribution` is empty AND
   `get_organ_by_body_location(location)` is empty, log a Splattercast
   warning (`ANATOMY_GAP: damage to {location} on {character} had no
   organ to receive it`).
2. `select_hit_location`: log when all available locations have a total
   weight of 0 (would-be-floor masks broken anatomy).
3. Optional: startup self-check that walks the anatomy table and reports
   unbacked containers.

**Effort**: small.
**Risk**: zero — log-only.
**Dependencies**: none.

#### Phase 4 — Vestigial-Flag Deletion (no-substrate cases)

**Goal**: Delete the flags that the audit clearly classified as
vestigial, separate from the substrate-gated ones.

Tasks:

1. Remove `Organ.vital` field and the per-organ `vital` flags.
2. Remove `unconscious_threshold` from the `consciousness` capacity dict
   (the top-level constant is the only source actually read).
3. Remove `can_be_destroyed` flags (redundant with negative form once
   spine clamp lands in Phase 7).
4. Update any tests that assert these values.

Excluded from this phase: `modifiers`, `affects` lists, and the
`total_loss_*` strings — those wait on substrate-resolution decisions.

**Effort**: small.
**Risk**: low.
**Dependencies**: none for items 1–2. Item 3 should wait on Phase 7
to avoid touching the same file twice.

#### Phase 5 — `LETHAL_CAPACITY_NAMES` Split

**Goal**: Remove the dual-role ambiguity that triggered this audit.

```python
LETHAL_CAPACITY_NAMES = (
    "blood_pumping", "breathing", "digestion", "neck_integrity",
)                                              # what kills you
VITAL_TARGETING_CAPACITIES = LETHAL_CAPACITY_NAMES + ("consciousness",)
```

Update `_get_vital_locations` to read `VITAL_TARGETING_CAPACITIES`; leave
`is_dead` reading `LETHAL_CAPACITY_NAMES` (or its inline literals). The
comment becomes self-evident.

**Effort**: small.
**Risk**: low — pure rename / split.
**Dependencies**: none (but ships nicer alongside Phase 1 docs).

---

### Track 2 — Foundational Substrates

These phases build the consumer systems whose absence makes most of the
medical flags appear dead. Each is a real piece of architecture and
deserves its own design pass (and probably its own spec doc, linked
back here).

#### Phase 6 — Chronic Medical Conditions Framework

**Goal**: A pattern for slow-kill conditions that accumulate organ failure
over time. Today's `Bleeding` / `Pain` / `Infection` / `ConsciousnessSuppression`
are all *acute* conditions with severity-based blood loss or pain or
suppression. A `RenalFailure` / `LiverFailure` / `RespiratoryFailure`
condition needs a different shape — a long-running degradation that
escalates to a death trigger.

Tasks:

1. Design pass: what does a chronic condition look like? A new base class
   `ChronicCondition` extending `MedicalCondition` with:
   - A `progression_rate` (how fast it worsens).
   - A `fatal_at_severity` threshold.
   - An `apply_tick_effect` that escalates severity over time even when
     untreated.
   - Integration with `is_dead`: when any chronic condition reaches its
     fatal threshold, `is_dead` returns True.
2. Refactor `is_dead` to consult chronic conditions in addition to its
   capacity checks.
3. Document patterns and edge cases in a new
   `specs/CHRONIC_MEDICAL_CONDITIONS_SPEC.md`.

**Effort**: medium.
**Risk**: medium — touches the death determination path.
**Dependencies**: Phase 1 (docs/clarification).
**Unlocks**: Kidney death (Phase 9), other organ-failure cascades.

#### Phase 7 — Movement Policing Substrate

**Goal**: A rule layer that commands consult before allowing a character
to move. Today nothing checks `moving` capacity before letting a
character walk. Needs to.

Tasks:

1. Design pass: where does movement get gated? Candidate hooks:
   - In `Character.move_to` / `at_pre_move` — generic check.
   - In `CmdFlee`, `CmdAdvance`, `CmdRetreat`, `CmdCharge` — combat
     movement.
   - In compass movement commands (north, south, etc.).
2. Add a `can_move()` method on `Character` (or `MedicalState`) that
   returns `(allowed, reason)` based on:
   - `moving` capacity above `incapacitation_threshold` (0.15).
   - No `ParalysisCondition` present (added in Phase 11).
   - No "downed/prone" state (future state machine).
3. Wire `at_pre_move` and combat-movement commands to call it.
4. Implement the `cannot_be_destroyed` clamp on `thoracolumbar_spine`
   in `Organ.take_damage` (spine HP can't drop below 1 from normal
   damage — combat-severance still routes through the edged-weapon
   path).
5. Document in a new `specs/MOVEMENT_POLICING_SPEC.md`.

**Effort**: medium.
**Risk**: medium — touches a lot of command surface.
**Dependencies**: Phase 1.
**Unlocks**: Paralysis (Phase 11), movement incapacitation (Phase 10).

#### Phase 8 — Senses System

**Goal**: Perception (sight, hearing) becomes a gated capability rather
than a free always-available power. When a character has zero sight,
`look` shows blank/dark output; combat targeting is much harder; movement
through unknown rooms fails.

Tasks:

1. Design pass: the senses system is its own architecture. At minimum:
   - `BlindCondition` and `DeafCondition` produced when respective
     capacities reach 0.
   - `look` hooks check the looker's `sight` capacity and modify output:
     full at 1.0, blurred at 0.5, no detail at 0.1, nothing at 0.
   - Combat: blind attacker takes a per-hit penalty.
   - Communication: deaf character receives no `say` / `whisper` content
     in their session output.
2. Implement `BlindCondition` and `DeafCondition` (subclass `MedicalCondition`).
3. Wire them to spawn when `sight = 0` / `hearing = 0` via a hook in
   `update_vital_signs` or a periodic check in `MedicalScript`.
4. Hook the appropriate command and render points.
5. Document in `specs/SENSES_SYSTEM_SPEC.md`.

**Effort**: large — this is real architecture.
**Risk**: medium-high — touches perception across the codebase.
**Dependencies**: Phase 1.
**Unlocks**: Sight/hearing penalty wiring.

**Note from user**: this phase is acknowledged as significant. The
likely path is ship the *infrastructure* (conditions + hook points) in
Phase 8, but defer the *consequences* (combat penalties, blanked look,
muted comm) to incremental follow-ups so the substrate can land without
gating on every consumer being perfect.

#### Phase 9 — Equipment-Handling Substrate (manipulation)

**Goal**: Manipulation capacity actually gates wielding, wearing, and
fine-motor combat actions.

Tasks:

1. Design pass: threshold tiers for manipulation:
   - Above ~0.7: full function.
   - 0.3–0.7: clumsy (combat accuracy penalty, slower equip).
   - Below 0.3: can hold what's already wielded but cannot equip/disequip;
     reduced attack accuracy.
   - At 0.0: drops everything currently held.
2. Add `can_wield()` / `can_equip()` checks at the relevant command
   sites (`wield`, `wear`, `wrest`, `disarm`, `give`, `get`).
3. Wire a drop-on-zero hook in `update_vital_signs`.
4. Document in `specs/EQUIPMENT_HANDLING_SPEC.md`.

**Effort**: medium.
**Risk**: medium — equipment commands span several files.
**Dependencies**: Phase 1.
**Unlocks**: Manipulation incapacitation (Phase 10).

---

### Track 3 — Wiring & Cleanup

Each phase here depends on a substrate from Track 2 being live. They
are the "wire the schema into the consumer" pass.

#### Phase 10 — Functional Capacity Incapacitation Wiring

**Goal**: Now that substrates exist, wire each capacity's
`incapacitation_threshold` and `total_loss_penalty` into the consumer.

Tasks:

1. **Movement**: `moving < incapacitation_threshold (0.15)` → character
   is "downed", cannot move. Uses Phase 7 substrate.
2. **Manipulation**: tiered penalties from Phase 9 substrate.
3. **Sight**: `sight = 0` → spawn `BlindCondition` (Phase 8 substrate).
4. **Hearing**: `hearing = 0` → spawn `DeafCondition` (Phase 8 substrate).
5. **Talking**: `talking = 0` → spawn `MuteCondition` (small extension
   of senses substrate).

**Effort**: medium — one PR per capacity.
**Risk**: medium — first time mechanical penalties land on players.
**Dependencies**: Phases 7 (movement), 8 (senses), 9 (manipulation).

#### Phase 11 — Paralysis

**Goal**: Ship the `paralysis_if_destroyed` intent on `thoracolumbar_spine`.

Tasks:

1. Add `ParalysisCondition` (extends `MedicalCondition`, location =
   `back`, severity 1, permanent).
2. Spawn it when spine HP drops below a threshold (default ~50% — final
   value during balancing). Spine itself doesn't go to 0 thanks to
   the Phase 7 clamp.
3. `ParalysisCondition` zeroes `moving` capacity via Phase 7's
   `can_move()` check returning False with reason "paralyzed".
4. Combat-driven severance from edged hits (per #243) still applies —
   that's *decapitation* via the neck container, which already kills.

**Effort**: medium.
**Risk**: medium — interactions with sever-from-living path need test
coverage.
**Dependencies**: Phase 7 (movement policing, spine clamp).

#### Phase 12 — Kidney Death via Chronic Condition

**Goal**: Total kidney loss becomes fatal — but as a chronic condition
(realistic acute-on-chronic renal failure), not as an instant `is_dead`
check.

Tasks:

1. Add `RenalFailureCondition` extending `ChronicCondition` from Phase 6.
2. Spawn it when `blood_filtration <= 0` (both kidneys destroyed).
3. Progression: severity escalates over time; fatal at severity threshold
   (timeline TBD during balancing — likely real-time hours, in-game
   days once the time system lands).
4. Treatment paths: dialysis substitute? Cybernetic kidney replacement?
   Deferred to future medical-tools work.
5. Tests: kidney destruction spawns the condition; condition escalates
   over time; reaching fatal severity triggers death.

**Effort**: small (the substrate from Phase 6 does the heavy lifting).
**Risk**: low.
**Dependencies**: Phase 6 (chronic conditions framework).

#### Phase 13 — Final Dead-Flag Audit & Cleanup

**Goal**: After substrates are live, the remaining substrate-gated flags
have either been wired (keep) or remain unused (delete).

Tasks:

1. Re-audit `modifiers` / `affects` lists: if Phase 10's wiring uses
   them as data, keep; otherwise delete and document the cascade
   imperatively.
2. `fatal_threshold` / `directly_fatal`: either refactor `is_dead` to
   be data-driven over these (single source of truth) or delete.
3. `total_loss_effects` on `talking`: if Phase 10 wires a `MuteCondition`
   that consumes them, keep; else delete the strings (they're
   declarative-only documentation).
4. Confirm `total_loss_penalty` strings are referenced by Phase 10's
   wiring; otherwise delete.

**Effort**: small once Track 2 lands.
**Risk**: low — non-load-bearing.
**Dependencies**: Phases 6, 7, 8, 9, 10.

---

## Implementation Sequence

Recommended ordering, with reasoning:

**Sprint 1 — fast wins, no substrate dependency**:

1. Phase 1 (docs)
2. Phase 5 (`LETHAL_CAPACITY_NAMES` split)
3. Phase 2 (brain blocks revival)
4. Phase 3 (failure-mode logging)
5. Phase 4 (vestigial-flag deletion, partial)

All five can ship in a short session — half-day to full day each.

**Sprint 2 — substrate buildout**:

6. Phase 6 (chronic conditions framework)
7. Phase 7 (movement policing) — and the spine clamp it includes
8. Phase 9 (equipment handling) — smaller than senses, lower risk
9. Phase 8 (senses system) — biggest single piece of new architecture

This sprint is the main effort. Each phase is a real spec + PR cycle.

**Sprint 3 — wiring**:

10. Phase 11 (paralysis)
11. Phase 12 (kidney chronic condition)
12. Phase 10 (functional incapacitation wiring, one capacity per PR)
13. Phase 13 (final dead-flag audit)

By the end, every audited flag is either consumed by working code or
deleted. The medical schema reads as truthful runtime documentation.

---

## Out of Scope

Explicitly **not** addressed here, for clarity:

* **Blood pool forensic command** (PR-ready, separate spec).
* **Phase 5 identity mechanics** (memory decay, auto-recognition via Resonance).
* **Treatment / healing balance pass** (existing `apply_treatment` paths
  are functional but un-balanced; that's a separate playtest exercise).
* **Time system integration** (wound timestamps, decay — blocked on
  issue #301).
* **Per-region decay rendering** on corpses (was decided as a future
  feature when removing the per-location decay spam in #323).
* **GMCP / web client / shop / world-state** (open issues #302–#308,
  not medical/combat work).
* **`_get_vital_locations` caching** — low-priority perf nit.

---

## Acceptance for This Spec

* User reviews and either approves the plan or marks specific phases as
  no-go.
* Approved phases are converted to GitHub issues, each with the relevant
  test plan and acceptance criteria already drafted in this spec.
* `specs/README.md` index entry added for this spec.
