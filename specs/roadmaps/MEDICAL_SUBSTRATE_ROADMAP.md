# Medical Substrate Roadmap

This roadmap orders the work of building the consumer systems that the
medical schema advertises: movement policing, senses, equipment handling,
chronic conditions, and the wiring of schema flags into them. It grew out
of an audit of the medical and combat systems, the death pipeline, and the
systems they depend on (wounds, conditions, armor, corpse, hit selection);
the audit findings below are the reasons for the order. The at-a-glance
flag map lives in `MEDICAL_SUBSTRATE_READINESS.md`.

## Core insight: schema without consumers

The medical system has three layers:

1. **Schema** (`ORGANS`, `BODY_CAPACITIES`, threshold constants). Authored
   anatomically: heart, lungs, kidneys, spine, brain, with realistic
   contributions and thresholds.
2. **Capacity calculation** (`MedicalState.calculate_body_capacity`,
   `update_vital_signs`). Load-bearing.
3. **Consumer systems** that react to capacity loss: perception/senses,
   movement policing, equipment-handling rules, chronic medical conditions.
   Largely unbuilt.

Some capacity loss has somewhere to go: a character with no `sight` cannot
see and one with no `hearing` cannot hear (`world/perception.py`), and
sight, manipulation and `moving` scale combat rolls
(`world/combat/capacity.py`; see `CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC.md`).
But with 12% `moving` a character still walks normally, and with the spine
destroyed they still stand: nothing polices movement.

The unread flags are therefore not a cleanup target. They are declarative
metadata deliberately authored ahead of the consumer systems that will read
them: each flag advertises a design hook for a system that has not been
written yet. Deleting them would delete design documentation. Treat this
document as a forward-looking design index, not a bug list.

**Sequencing rule: build the substrate before wiring schema to it.**
Foundational consumer systems come first (where their absence is the
gate), then wiring, then a final flag audit that deletes only what no
consumer ever plans to use.

## How the medical layers fit together

1. **Static schema** in `world/anatomy/species.py` (`SPECIES_DEFINITIONS`:
   per species, the organs and body capacities with their flags).
   `world/medical/constants.py` derives the human `ORGANS` /
   `BODY_CAPACITIES` from it and holds `LETHAL_CAPACITY_NAMES` and the
   thresholds.
2. **Runtime state** in `world/medical/core.py`: `Organ`, `MedicalState`,
   `is_dead`, `is_unconscious`, `calculate_body_capacity`,
   `update_vital_signs`.
3. **Tickers and effects** in `world/medical/conditions.py` and
   `world/medical/script.py`: bleeding, pain, infection and consciousness
   suppression, driven by a per-character `MedicalScript` every 60 seconds
   (`MEDICAL_TICK_INTERVAL`). After each tick it calls `is_dead()` and
   triggers `at_death()` if conditions pushed the body past a threshold.

Combat reaches the medical layer through `ArmorMixin.take_damage`
(`typeclasses/armor_mixin.py`). It applies armor reduction first
(`_calculate_armor_damage_reduction(amount, location, injury_type)`, via
the effectiveness matrix in `world/combat/constants.py`, tied to clothing
coverage), then calls `apply_anatomical_damage`, then checks `is_dead()` /
`is_unconscious()` and dispatches to `at_death()` /
`_handle_unconsciousness()`. The combat handler (`world/combat/handler.py`)
runs turns; per-attack logic is in `world/combat/attack.py`.

- Combat severance checks `SEVERING_INJURY_TYPES` (`cut` / `stab` /
  `laceration`).
- `_handle_unconsciousness` sets `ndb.unconsciousness_pending` during
  combat, which defers the unconsciousness message until after the hit
  narrative (5 s fallback).
- Wounds (`world/medical/wounds/`): `take_organ_damage` calls
  `_create_conditions_from_damage`, which spawns `BleedingCondition` /
  `PainCondition` / `InfectionCondition`. Wound prose renders through
  `append_wounds_to_longdesc` and the per-injury-type message dicts.
- Hit selection (`select_hit_location`) is data-driven from the organ
  schema, with a vital-location bias from `_get_vital_locations`, which
  derives from `LETHAL_CAPACITY_NAMES`. It falls back to `chest` when the
  character has no longdesc.
- Corpse (`typeclasses/corpse.py`): a death-time snapshot of
  `physical_description`, `longdesc_data`, `wounds_at_death`,
  `apparent_uid_at_death`, `signature_at_death` and a medical snapshot.
- Forensics (`world/forensics.py`) reads the corpse signature for autopsy.
  `commands/forensics.py` carries `CmdInspect` (alias `autopsy`) and
  `CmdSever`; `CmdHarvest` is in `commands/CmdSurgical.py`; the procedural
  surgery verbs read the same snapshots. `CmdInspect` also handles
  `BloodPool` by dispatching `extract_subject_from_blood_pool_incident`
  per unique apparent UID, with distinguishable / indistinguishable
  bucketing so old crime scenes render readably.

### Category A — Death model

- `is_dead()` fires when any capacity in `LETHAL_CAPACITY_NAMES`
  (`blood_pumping`, `breathing`, `digestion`, `neck_integrity`,
  `brain_integrity`) reaches zero, or on blood loss. The comment above
  `LETHAL_CAPACITY_NAMES` in `world/medical/constants.py` says the tuple is
  exactly the set `is_dead()` enforces and that `consciousness` must never
  be in it. The same tuple is the vital-target set for hit selection, and
  a test pins the schema's `directly_fatal` flag to it for every species
  (#3677).
- **Consciousness 0 is not death** (#3248). `consciousness` is the awake
  axis. Brain destruction is a death, with the window, through the
  separate structural capacity `brain_integrity`. The head bleed still
  runs for a body brought back.
- Death after the synchronous attack is not immediate. `at_death()` shows
  the death curtain and starts a `DeathProgressionScript`
  (`typeclasses/death_progression.py`) lasting `DEATH_PROGRESSION_DURATION`
  (90 s), with an 11-message narrative and a medical-revival window. A
  beheading is the exception: the death completes at once, with no
  revival check and no dying messages (#3840, 2026-11-14).
- `_check_medical_revival_conditions` gates revival only on `is_dead()`.
  A destroyed brain keeps `brain_integrity` at zero, so a body dead of
  anything with a destroyed brain stays `is_dead()` until the brain is
  restored. What restores it is a brain install; sealant and dressings
  refuse a destroyed soft organ (#3253).
- **Kidney loss is not fatal** (#3402). `MedicalState._update_renal_failure()`
  spawns and clears `RenalFailureCondition` from the `blood_filtration`
  capacity inside `update_vital_signs`, and clears it when a kidney is
  restored, cyber or donor. `is_dead` never reads `blood_filtration`.
  Renal failure's lasting obtundation (consciousness 0.4 at maximum
  severity, ten points above the knockout line) is the cost.
- **Pain-driven unconsciousness** (`PAIN_UNCONSCIOUS_THRESHOLD: 80`) works
  indirectly: pain lowers the `self.consciousness` float, which then trips
  the consciousness threshold. Not a direct check, but functionally
  equivalent.

### Two consciousness values

- `self.consciousness` (float on `MedicalState`) is the runtime value,
  including pain, blood and suppression penalties. `is_unconscious()`
  checks `self.consciousness < threshold`.
- `calculate_body_capacity("consciousness")` is the organ-only floor
  (brain HP fraction).
- `is_dead()` checks neither.

The runtime `self.consciousness` must never gate death, because every
knockout would become a kill.

## Flag readiness ledger

Every flag in `ORGANS` and `BODY_CAPACITIES`, with its read count outside
the constants file and tests, the system meant to consume it, and its
disposition. Most are not dead code; they wait on a consumer system.

| Flag | Reads | Intended consumer | Disposition |
|---|---|---|---|
| `vital` (on `Organ`) | 0 | None: superseded by data-driven `_get_vital_locations`. `Organ.vital` is set on init from schema and never read. | **Vestigial**: delete (Phase 4). |
| `fatal_threshold` (on capacity) | 0 | Could replace the `<= 0.0` literal in `is_dead` if `is_dead` were refactored to be data-driven | Keep until the final flag audit (delete or wire). |
| `directly_fatal` (on capacity) | 0 at runtime; pinned by test (#3677) to equal `LETHAL_CAPACITY_NAMES` for every species, which `is_dead` loops over | A declaration the test keeps honest; `is_dead` reads the tuple, not the flag | Keep (declarative, tested). |
| `incapacitation_threshold: 0.15` on `moving` | 0 | **Movement policing**: below this, the character cannot move. The dodge factor (`moving_dodge_factor` in `world/combat/capacity.py`) copies the 0.15 instead of reading the flag. | **Substrate gap**: movement policing. |
| `unconscious_threshold` | — | None: the top-level `CONSCIOUSNESS_UNCONSCIOUS_THRESHOLD` is the one read | Absent from the `consciousness` dict in `world/anatomy/species.py`; only a comment in `world/medical/constants.py` still names it. |
| `modifiers: ["pain", "blood_pumping", ...]` on `consciousness` | 0 | The cascade is implemented imperatively in `update_vital_signs`; this list is documentation only | **Vestigial**: delete or convert to spec comment (Phase 13). |
| `affects: ["consciousness", "moving"]` on capacities | 0 | Could drive a generic capacity-effect graph; a manual `update_vital_signs` formula does the work | **Vestigial unless** a generic effect graph is built (Phase 13). |
| `total_loss_penalty: "blindness"` / `"deafness"` | 0 | **Senses**: total loss should spawn `BlindCondition` / `DeafCondition` and gate perception. Perception is gated through capacity reads instead (`world/perception.py`); no condition is produced. | **Substrate gap**: senses. |
| `total_loss_effects: ["cannot_negotiate", ...]` on `talking` | 0 | **Social interaction rules**: cannot speak, so cannot negotiate, persuade, etc. | **Substrate gap**: social system policing. |
| `cannot_be_destroyed: True` on `thoracolumbar_spine` | 0 | Should clamp `Organ.take_damage` to a 1 HP floor for this organ | **Direct wire**: small fix, no substrate dependency (Phase 7). |
| `paralysis_if_destroyed: True` on `thoracolumbar_spine` | 0 | **Movement policing**: produces a permanent `ParalysisCondition` that zeroes `moving` | **Substrate gap**: movement policing. |
| `can_be_destroyed` (most organs) | 1 (`_is_leg_bone` in `world/gravity.py`, #3584) | Picks the leg bones a fall damages | **Read**: deleting it would leave falls with no leg bone to damage. |
| `fracture_vulnerable` | 4 | Bone-fracture condition spawn path | Live, keep. |
| `bone_type` | 5 | Bone-fracture and severance routing | Live, keep. |

`total_loss_fatal` on `blood_filtration` is deleted (#3402): kidney loss is
not fatal by ruling, and the unread flag stated the opposite.

Ten of the thirteen audited flags still in the schema are unread by
runtime code.
By the rubric above:

- **Vestigial (delete)**: `vital`, `modifiers`, `affects`, `can_be_destroyed`
  (now read by falls, #3584; see its row).
- **Direct wire (no substrate)**: `cannot_be_destroyed` on the spine.
- **Substrate gap (build substrate first, then wire)**:
  `incapacitation_threshold` (movement), `total_loss_penalty`
  blindness/deafness (senses), `total_loss_effects` (social),
  `paralysis_if_destroyed` (movement).
- **Audit later**: `fatal_threshold`, `directly_fatal` — keep until the
  `is_dead` refactor lands.

## Order of work

Phases are grouped into three tracks. Track 1 phases have no substrate
dependency and ship in any order. Track 2 builds the consumer systems and
gates Track 3. Each phase ships as a single PR (sub-issues if
review-sized).

Gates: Phase 10 waits on Phases 7, 8 and 9; Phase 11 waits on Phase 7;
Phase 13 waits on the rest. Phase 4 also unblocks the flag cleanup.

Recommended order:

1. Phase 3 (failure-mode logging) — Track 1
2. Phase 4 (vestigial-flag deletion, partial) — Track 1
3. Phase 6 (chronic conditions framework) — Track 2
4. Phase 7 (movement policing), with the spine clamp it includes — Track 2
5. Phase 9 (equipment handling) — smaller than senses, lower risk
6. Phase 8 (senses) — the biggest single piece of new architecture
7. Phase 11 (paralysis) — Track 3
8. Phase 10 (functional incapacitation wiring, one capacity per PR)
9. Phase 13 (final dead-flag audit)

Track 1 phases are a half-day to a full day each. Track 2 is the main
effort; each phase is a real spec and PR cycle. By the end, every audited
flag is either consumed by working code or deleted, and the medical schema
reads as truthful runtime documentation.

The surgery work (`HEALTH_AND_SUBSTANCE_SYSTEM_SPEC.md` § Surgery, § Surgery > The `operate`
chart and § Severance and stumps:
procedural surgery, the operate charting command, severance /
suture-stump / install-picker / combat-incision symmetry) and the
anatomy-augments and cyberware arc (#511–#551: chassis+module cyberware,
spec-carrying replacement organs, inorganic damage (pain-only),
reattachment, chrome severance prose) sit above these gaps. They read and
mutate organ HP, `wound_stage`, `inorganic` and `abilities`, but none
introduces or resolves a consumer for `incapacitation_threshold`,
`paralysis_if_destroyed` or `total_loss_penalty`. The substrate phases
are unchanged by them.

---

## Track 1 — Standalone

### Phase 3 — Failure-mode surfacing

📋 UNBUILT (no issue)

**Goal**: a location with no organs fails silently. The pre-#325 groin
showed it: a damage call to a location with zero registered organs returns
success-shaped data but applies no medical effect. The groin is fixed, but
any future anatomy slot missing organ coverage will repeat it without a
single log line. Make the next one loud.

The gaps it addresses:

- When `damage_distribution = {}`, `apply_anatomical_damage` falls through
  to `total_damage: damage_amount` with no organs damaged. Should raise or
  log.
- `select_target_organ` returns `None` for organ-less locations;
  `take_damage` accepts `target_organ=None` and routes through
  location-wide distribution. Coherent, but only works if the location has
  any organs.
- `take_damage` returns `(died, final_damage)` to combat, but if the
  medical layer applied no damage (organ-less location, all destroyed),
  `final_damage` is misleading: combat sees "hit for X" but the body has no
  record.
- `select_hit_location` falls back to `chest` when the character has no
  longdesc: defensive, but it masks bad data; a logged warning would
  surface broken anatomy.

Tasks:

1. `apply_anatomical_damage`: when `damage_distribution` is empty AND
   `get_organ_by_body_location(location)` is empty, log a Splattercast
   warning (`ANATOMY_GAP: damage to {location} on {character} had no
   organ to receive it`).
2. `select_hit_location`: log when all available locations have a total
   weight of 0 (would-be-floor masks broken anatomy). This case cannot
   happen as built: each location's weight is floored at 1
   (`max(total_weight, 1)`), so a location with no organs stays hittable.
   The silent fallback that can happen is the return of `chest` for a
   character with no longdesc.
3. Optional: a startup self-check that walks the anatomy table and reports
   unbacked containers.

Effort: small. Risk: zero, log-only. Dependencies: none.

### Phase 4 — Vestigial-flag deletion (no-substrate cases)

📋 UNBUILT (no issue)

**Goal**: delete the flags classified as vestigial, separate from the
substrate-gated ones.

Tasks:

1. Remove the `Organ.vital` field and the per-organ `vital` flags.
2. Remove `can_be_destroyed` flags (redundant with the negative form once
   the spine clamp lands in Phase 7). Since #3584 the fall code reads
   `can_be_destroyed` to pick the leg bones, so removing it would break
   falls.
3. Update any tests that assert these values.

Excluded: `modifiers`, `affects`, and the `total_loss_*` strings; those
wait on substrate-resolution decisions.

Effort: small. Risk: low. Dependencies: none for task 1. Task 2 should
wait on Phase 7 to avoid touching the same file twice.

---

## Track 2 — Foundational substrates

These phases build the consumer systems whose absence makes most of the
medical flags appear dead. Each is a real piece of architecture and
deserves its own design pass (and probably its own spec, linked back
here).

### Phase 6 — Chronic medical conditions framework

📋 UNBUILT (no issue): the generic `ChronicCondition` base.

`RenalFailureCondition` exists and is wired, but it extends
`MedicalCondition` directly, so `LiverFailure` / `RespiratoryFailure`
would each be hand-rolled. It does not kill, by ruling (#3402).

**Goal**: a pattern for slow-kill conditions that accumulate organ failure
over time. `Bleeding` / `Pain` / `Infection` / `ConsciousnessSuppression`
are acute conditions with severity-based blood loss, pain or suppression.
A `LiverFailure` / `RespiratoryFailure` condition needs a different shape:
a long-running degradation that escalates to a death trigger.

Tasks:

1. Design pass: a new base class `ChronicCondition` extending
   `MedicalCondition`, with:
   - a `progression_rate` (how fast it worsens);
   - a `fatal_at_severity` threshold;
   - an `apply_tick_effect` that escalates severity over time even when
     untreated;
   - integration with `is_dead`: when any chronic condition reaches its
     fatal threshold, `is_dead` returns True.
2. Refactor `is_dead` to consult chronic conditions in addition to its
   capacity checks.
3. Document patterns and edge cases in a new
   `specs/CHRONIC_MEDICAL_CONDITIONS_SPEC.md`.

Effort: medium. Risk: medium, touches the death determination path.
Unlocks: other organ-failure cascades (kidney death is declined, #3402).

### Phase 7 — Movement policing substrate

📋 UNBUILT (no issue)

**Goal**: a rule layer that commands consult before allowing a character
to move. Nothing checks `moving` capacity before letting a character walk;
walk commands do not check capacity. `moving` has one consumer, the dodge
factor (`moving_dodge_factor` in `world/combat/capacity.py`).

Tasks:

1. Design pass: where does movement get gated? Candidate hooks:
   - `Character.move_to` / `at_pre_move`: a generic check.
   - `CmdFlee`, `CmdAdvance`, `CmdRetreat`, `CmdCharge`: combat movement.
   - Compass movement commands (north, south, etc.).
2. Add a `can_move()` method on `Character` (or `MedicalState`) that
   returns `(allowed, reason)` based on:
   - `moving` capacity above `incapacitation_threshold` (0.15);
   - no `ParalysisCondition` present (added in Phase 11);
   - no "downed/prone" state (future state machine).
3. Wire `at_pre_move` and the combat-movement commands to call it.
4. Implement the `cannot_be_destroyed` clamp on `thoracolumbar_spine` in
   `Organ.take_damage` (spine HP cannot drop below 1 from normal damage;
   combat severance still routes through the edged-weapon path).
5. Document in a new `specs/MOVEMENT_POLICING_SPEC.md`.

Effort: medium. Risk: medium, touches a lot of command surface.
Unlocks: paralysis (Phase 11), movement incapacitation (Phase 10).

### Phase 8 — Senses system

📋 UNBUILT (no issue): `BlindCondition` / `DeafCondition` and the rest of
the plan below.

Sight, hearing and smell gate what a character perceives through capacity
reads: `can_see` / `can_hear` / `can_smell` in `world/perception.py`. Below
the sight threshold a character cannot see (read by the room description,
speech, emote, radio, stealth and identity); below the hearing threshold
they do not hear (read by speech, voice and radio). Sight scales hit chance
(`sight_hit_factor` in `world/combat/capacity.py`). See
`CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC.md`. No blindness or deafness
condition is produced, and the `total_loss_penalty` strings are unread.

**Goal**: perception (sight, hearing) becomes a gated capability rather
than a free always-available power. When a character has zero sight,
`look` shows blank/dark output; combat targeting is much harder; movement
through unknown rooms fails.

Tasks:

1. Design pass: the senses system is its own architecture. At minimum:
   - `BlindCondition` and `DeafCondition` produced when the respective
     capacities reach 0;
   - `look` hooks check the looker's `sight` capacity and modify output:
     full at 1.0, blurred at 0.5, no detail at 0.1, nothing at 0;
   - combat: a blind attacker takes a per-hit penalty;
   - communication: a deaf character receives no `say` / `whisper`
     content in their session output.
2. Implement `BlindCondition` and `DeafCondition` (subclass
   `MedicalCondition`).
3. Spawn them when `sight = 0` / `hearing = 0`, through a hook in
   `update_vital_signs` or a periodic check in `MedicalScript`.
4. Hook the command and render points.
5. Document in `specs/SENSES_SYSTEM_SPEC.md`.

Effort: large, real architecture. Risk: medium-high, touches perception
across the codebase. Unlocks: sight/hearing penalty wiring.

**Note from user**: this phase is acknowledged as significant. The likely
path is ship the *infrastructure* (conditions + hook points) in Phase 8,
but defer the *consequences* (combat penalties, blanked look, muted comm)
to incremental follow-ups so the substrate can land without gating on
every consumer being perfect.

### Phase 9 — Equipment-handling substrate (manipulation)

📋 UNBUILT (no issue): refusing wield or wear, and dropping items at zero
manipulation.

Manipulation scales hit chance per gripping hand, with an under-grip
penalty (`manipulation_hit_factor` and `grip_hit_factor` in
`world/combat/capacity.py`; #3717). Nothing drops a weapon or refuses wield
or wear. The schema's manipulation `affects` lists `work_speed` and
`melee_accuracy`.

**Goal**: manipulation capacity gates wielding, wearing, and fine-motor
combat actions.

Tasks:

1. Design pass: threshold tiers for manipulation:
   - above ~0.7: full function;
   - 0.3–0.7: clumsy (combat accuracy penalty, slower equip);
   - below 0.3: can hold what is already wielded but cannot
     equip/disequip; reduced attack accuracy;
   - at 0.0: drops everything currently held.
2. Add `can_wield()` / `can_equip()` checks at the command sites (`wield`,
   `wear`, `wrest`, `disarm`, `give`, `get`).
3. Wire a drop-on-zero hook in `update_vital_signs`.
4. Document in `specs/EQUIPMENT_HANDLING_SPEC.md`.

Effort: medium. Risk: medium, equipment commands span several files.
Unlocks: manipulation incapacitation (Phase 10).

---

## Track 3 — Wiring and cleanup

Each phase here depends on a Track 2 substrate being live. They wire the
schema into the consumer.

### Phase 10 — Functional capacity incapacitation wiring

📋 UNBUILT (no issue)

**Goal**: wire each capacity's `incapacitation_threshold` and
`total_loss_penalty` into its consumer.

Tasks:

1. **Movement**: `moving < incapacitation_threshold (0.15)` → the
   character is "downed" and cannot move. Uses the Phase 7 substrate.
2. **Manipulation**: tiered penalties from the Phase 9 substrate.
3. **Sight**: `sight = 0` → spawn `BlindCondition` (Phase 8 substrate).
4. **Hearing**: `hearing = 0` → spawn `DeafCondition` (Phase 8 substrate).
5. **Talking**: `talking = 0` → spawn `MuteCondition` (a small extension
   of the senses substrate).

Effort: medium, one PR per capacity. Risk: medium, the first time
mechanical penalties land on players. Dependencies: Phases 7 (movement),
8 (senses), 9 (manipulation).

### Phase 11 — Paralysis

📋 UNBUILT (no issue)

**Goal**: honour `paralysis_if_destroyed` on `thoracolumbar_spine`. The
spine can be destroyed but produces no paralysis condition.

Tasks:

1. Add `ParalysisCondition` (extends `MedicalCondition`, location `back`,
   severity 1, permanent).
2. Spawn it when spine HP drops below a threshold (default ~50%, final
   value during balancing). The spine itself does not go to 0, thanks to
   the Phase 7 clamp.
3. `ParalysisCondition` zeroes `moving` through Phase 7's `can_move()`
   returning False with reason "paralyzed".
4. Combat-driven severance from edged hits (per #243) still applies; that
   is decapitation through the neck container, which already kills.

Effort: medium. Risk: medium; interactions with the sever-from-living path
need test coverage. Dependencies: Phase 7 (movement policing, spine
clamp).

### Phase 13 — Final dead-flag audit and cleanup

📋 UNBUILT (no issue)

**Goal**: after the substrates are live, each remaining substrate-gated
flag has either been wired (keep) or remains unused (delete).

Tasks:

1. Re-audit the `modifiers` / `affects` lists: if Phase 10's wiring uses
   them as data, keep; otherwise delete and document the cascade
   imperatively.
2. `fatal_threshold` / `directly_fatal`: `is_dead` loops over
   `LETHAL_CAPACITY_NAMES`, and a test pins `directly_fatal` to that tuple
   for every species (#3677); `fatal_threshold` stays declarative (the
   floor is `<= 0.0`).
3. `total_loss_effects` on `talking`: if Phase 10 wires a `MuteCondition`
   that consumes them, keep; else delete the strings (they are
   declarative-only documentation).
4. Confirm the `total_loss_penalty` strings are referenced by Phase 10's
   wiring; otherwise delete.

Effort: small once Track 2 lands. Risk: low, non-load-bearing.
Dependencies: Phases 6, 7, 8, 9, 10.

---

## Rulings

- **2026-09-26 (#3248)**: _"Conscious capacity 0 should not be death"_.
  A 2026-09-11 ruling had made the consciousness capacity
  (`calculate_body_capacity("consciousness")`, brain HP only) a death
  gate; it is withdrawn. Brain death goes through `brain_integrity`
  instead. The same change ended the planned split of
  `LETHAL_CAPACITY_NAMES` into a lethal set and a vital-targeting set
  (`lethal ∪ consciousness`): `consciousness` left the tuple and
  `brain_integrity` joined it, so the head stays a vital target through a
  capacity that IS lethal, and one tuple is both sets.
- **2026-09-24 (#3402)**: "Considering how much weaker it makes someone — I
  think that's tough enough." Total kidney loss is survivable. The roadmap
  had planned kidney death as a chronic condition (`RenalFailureCondition`
  extending `ChronicCondition`, fatal at a severity threshold); that phase
  is declined. The `ChronicCondition` framework of Phase 6 remains useful
  for other organ failures.

## Not decided

- **Skill / stat model**, upstream of all the tuning here. Every medical
  roll (`roll_procedure`, `calculate_treatment_success`) and forensic check
  is a placeholder formula on G.R.I.M. stats that all default to `1`.
  Difficulty/effectiveness balance cannot be tuned, and capacity→roll
  penalties (the point of Tracks 2–3) have no real roll to modify, until
  the skill/stat design is decided. The skill board is ruled (2026-08-19,
  amended the same day; `specs/proposals/SKILLS_AND_DESIGNATION_SPEC.md`),
  but it is not built, and how the medical rolls use it is not settled
  here.
- **Per-character capacity extension.** Augment organs can add anatomy and
  capacities a species table never declared (the cyber tail). Phases 7–9
  assume the static species table is the full capacity set; extension is
  an un-catalogued substrate concern to fold into movement policing,
  senses and equipment handling whenever those are scoped. See
  `MEDICAL_SUBSTRATE_READINESS.md`.
- **Social-interaction substrate.** `talking` total-loss effects
  (`cannot_negotiate`, …) have no phase: open design, depending on a
  trade/negotiation system that does not exist.

## Out of scope

- **Blood pool forensics**: handled by `inspect` (`commands/forensics.py`,
  PR #441 / #442).
- **Phase 5 identity mechanics** (memory decay, auto-recognition via
  Resonance).
- **Treatment / healing balance pass**: the `apply_treatment` paths are
  functional but unbalanced; that is a separate playtest exercise.
- **Time system integration**: wounds are stamped with
  `world.gametime.stamp` (#301, `specs/TIME_SYSTEM_SPEC.md`). Decay tuning
  against it is out of scope here.
- **Per-region decay rendering** on corpses (decided as a future feature
  when the per-location decay spam was removed in #323).
- **GMCP / shop / world-state** (open issues #302, #303, #305; not
  medical/combat work). #308 (death-state TODOs) is open and touches this
  area.
- **`_get_vital_locations` caching**: it walks `LETHAL_CAPACITY_NAMES` →
  `BODY_CAPACITIES` → `ORGANS` → containers on every hit selection.
  Acceptable but cacheable; a low-priority perf nit.

## Acceptance for this roadmap

- The owner reviews and either approves the plan or marks specific phases
  as no-go.
- Approved phases are converted to GitHub issues, each with the test plan
  and acceptance criteria drafted here.
- A `specs/README.md` index entry is added for this document.

## Related documents

- `specs/roadmaps/MEDICAL_SUBSTRATE_READINESS.md`: the at-a-glance flag map.
- `specs/HEALTH_AND_SUBSTANCE_SYSTEM_SPEC.md`: the medical system, including
  `neck_integrity` capacity and death wiring.
- `specs/CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC.md`: the capacity reads
  that gate perception and scale combat rolls.
- `specs/proposals/SKILLS_AND_DESIGNATION_SPEC.md`: the ruled skill board.
- `specs/TIME_SYSTEM_SPEC.md`.
