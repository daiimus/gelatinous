# Medical Substrate Readiness Index

This document is the load-bearing artifact spun out of Phase 1 of `MEDICAL_SUBSTRATE_ROADMAP.md`. Its purpose is captured in that spec's Core Insight:

> The medical system has a top-down anatomical schema whose bottom-up consumer systems were never built. Each declarative flag advertises a consumer system that hasn't been written yet. Deleting them would be deleting design documentation. The right work is *building the substrates*.

The schema is mature (see `HEALTH_AND_SUBSTANCE_SYSTEM_SPEC.md` Phases 1 through 2.10). The substrates are not. This index is the table that tells a contributor — current or future — *what each unconsumed flag is waiting for, and which audit phase will wire it in*.

The audit itself is the planning artifact and lifecycle: this is the at-a-glance map.

---

## How to use this document

- **Adding a new flag** to `world/medical/constants.py` or a species `organs` spec? Add a row here too. If the flag has no current consumer, point at the substrate phase that will eventually read it.
- **Wiring a flag into a runtime consumer**? Mark the row as live, link the audit phase that resolved it, and remove it on the next cleanup pass.
- **Adding a new consumer system** (substrate)? Read down the table for which flags it should consume on first wiring.
- **Re-validating the audit**? Cross-check this table against current code via the grep-counts column.

---

## Flag → Consumer System Map

| Flag (declaration site) | Reads (current) | Intended consumer | Audit phase | Status |
|---|---|---|---|---|
| `vital` (Organ init from species spec) | 0 | None — superseded by data-driven `_get_vital_locations` reading `LETHAL_CAPACITY_NAMES` | Phase 4 — Vestigial-Flag Deletion | **Vestigial** — delete when Phase 4 lands |
| `fatal_threshold` (BODY_CAPACITIES) | 0 | A data-driven `is_dead` that compares each lethal capacity against this threshold instead of the literal `<= 0.0` floor | Phase 5 — `LETHAL_CAPACITY_NAMES` Split | Keep until Phase 5 |
| `directly_fatal` (BODY_CAPACITIES) | 0 (1 test) | Same as `fatal_threshold` — declares which capacities terminate life vs incapacitate | Phase 5 — `LETHAL_CAPACITY_NAMES` Split | Keep until Phase 5 |
| `total_loss_fatal: True` on `blood_filtration` | 0 | **Chronic Conditions framework** — total kidney loss should spawn a fatal `RenalFailure` condition that kills via the tick path, not instant `is_dead` death | Phase 6 — Chronic Medical Conditions Framework + Phase 12 wiring | **Substrate gap** — chronic conditions |
| `incapacitation_threshold: 0.15` on `moving` | 0 | **Movement Policing system** — when capacity is below this, character cannot move (movement commands refuse / sleep into low-stamina locomotion) | Phase 7 — Movement Policing Substrate + Phase 10 wiring | **Substrate gap** — movement policing |
| `unconscious_threshold` (in `consciousness` capacity dict) | 0 | None — duplicated as top-level `CONSCIOUSNESS_UNCONSCIOUS_THRESHOLD` (the one `is_unconscious` actually reads) | Phase 4 — Vestigial-Flag Deletion | **Vestigial** — delete when Phase 4 lands |
| `modifiers: [...]` on `consciousness` | 0 | None — the cascade (pain → consciousness, blood → consciousness, suppression → consciousness) is implemented imperatively in `update_vital_signs`; this list is design documentation only | Phase 4 — Vestigial-Flag Deletion (or convert to spec comment) | **Vestigial** — delete or document-only |
| `affects: [...]` on capacities | 0 | None today — could drive a generic capacity-effect graph if such a substrate is ever built | Phase 4 — Vestigial-Flag Deletion (unless effect-graph substrate is in plan) | **Vestigial unless** the graph is on the roadmap |
| `total_loss_penalty: "blindness"` on `sight` | 0 | **Senses System** — total sight loss spawns a `BlindCondition` that gates perception (combat targeting, look output, sdesc rendering) | Phase 8 — Senses System | **Substrate gap** — senses |
| `total_loss_penalty: "deafness"` on `hearing` | 0 | **Senses System** — total hearing loss spawns a `DeafCondition` that gates audio perception (combat broadcasts, room sounds, conversation) | Phase 8 — Senses System | **Substrate gap** — senses |
| `total_loss_effects: ["cannot_negotiate", ...]` on `talking` | 0 | **Social interaction substrate** — can't speak → can't negotiate / persuade / bid in trade | (No audit phase yet — open design) | **Substrate gap** — social policing (out of audit scope) |
| `cannot_be_destroyed: True` on `thoracolumbar_spine` | 0 | `Organ.take_damage` floors at 1 HP for this organ | Phase 7 follow-up (movement policing wires this) | **Direct wire** — small fix, ~Phase 7 cleanup |
| `paralysis_if_destroyed: True` on `thoracolumbar_spine` | 0 | **Movement Policing system** — produces a permanent `ParalysisCondition` that zeroes `moving` capacity | Phase 7 — Movement Policing Substrate + Phase 11 wiring | **Substrate gap** — movement policing |
| `can_be_destroyed` (most organs) | 0 (1 test) | Inverse of `cannot_be_destroyed`; redundant once `cannot_be_destroyed` is wired | Phase 4 — Vestigial-Flag Deletion | **Vestigial** — delete after spine wiring |
| `fracture_vulnerable` | 2 files | Bone-fracture condition spawn path (`world/medical/utils.py`, `commands/CmdConsumption.py`) | — (live) | **Live** — load-bearing |
| `bone_type` | 3 files | Bone-fracture and severance routing (`world/medical/utils.py`, `world/medical/core.py`, `commands/CmdConsumption.py`) | — (live) | **Live** — load-bearing |

> **Read-count caveat (2026-06-14):** the "Reads (current)" column above was
> last validated June 2026 and is stale — re-run the grep-counts before
> relying on a specific number. The flags are correctly *classified*
> (vestigial / gap / live); only the integer counts drift.

---

## Flags from the augment / cyberware arc (#511–#551)

These organ-spec flags landed with the anatomy-augments and cyberware
chassis+module work and are **already consumed by runtime** — they are
live and load-bearing, not substrate-gaps. Catalogued here because the
"Adding a new flag" checklist below requires a row per flag, and the
arc shipped before this index was updated (the flag-debt symptom this
doc exists to catch, turned on the doc itself).

| Flag (declaration site) | Intended consumer | Status |
|---|---|---|
| `inorganic` (organ spec) | Damage model — chrome takes pain only, no bleed/infection (`Organ.take_damage`); chrome rendering (`appearance_mixin`); chrome severance prose (`get_severance_message`) | **Live** — load-bearing |
| `prosthetic_frame` (chassis organs) | `is_cybernetic_limb` — reattachment eligibility + chrome severance routing | **Live** — load-bearing |
| `hardpoint` (chassis slot organ) | `find_hardpoint` — module seating (`world/medical/procedures.py`) | **Live** — load-bearing |
| `module_type` (module item / hardpoint) | Install dispatch + hardpoint match + harvest provenance | **Live** — load-bearing |
| `abilities` (organ spec) | Ability layer — `find_ability`, `iter_abilities`, toggle dispatcher | **Live** — load-bearing |
| `flesh_organ` (flesh-mount module) | Names the specific host organ in a multi-organ container (Jawz→jaw) | **Live** — load-bearing |
| `can_be_harvested` / `can_be_replaced` | Harvest / install gates (operate menu + resolvers) | **Live** — load-bearing |
| `capacities` (list) + `*_contribution` | Per-character capacity math for replacement/augment organs (`calculate_body_capacity`) | **Live** — load-bearing |
| `grasping` (organ spec) | Prehensile `hands` overlay — extra held slot from a grasping container | **Live** — load-bearing |
| `severable_container` (augment organ) | Severable-overlay + operate-menu sever listing | **Live** — load-bearing |
| `display_location` / `hit_weight` | Surface-access incision gate + hit-distribution weighting (pre-arc, never catalogued) | **Live** — load-bearing |

**Capacity-extension note:** augment organs can *add* anatomy and
capacities a species table never declared (the cyber tail; a future
Doc-Ock rig). The substrate phases below (movement policing, senses,
equipment-handling) assume the static species table is the full
capacity set — per-character capacity *extension* is an un-catalogued
wrinkle to fold in when those substrates are scoped. See
`MEDICAL_SUBSTRATE_ROADMAP.md`.

---

## Substrate → Phases the Audit Sequences

Substrate work blocks the wiring phases that depend on it. Sequence per the audit:

| Substrate | Build in | Wires up |
|---|---|---|
| Chronic Medical Conditions framework | Phase 6 | Phase 12 (kidney death via `RenalFailure`) |
| Movement Policing | Phase 7 | Phase 10 (functional-capacity incapacitation), Phase 11 (paralysis) |
| Senses System | Phase 8 | Blindness / deafness conditions and downstream perception gating |
| Equipment-Handling (manipulation consequences) | Phase 9 | Weapon-drop / can't-wield on low `manipulation` capacity |
| Social interaction substrate | (open — no audit phase) | `talking` total-loss effects (`cannot_negotiate`, etc.) |

Phases 4 (Vestigial-Flag Deletion) and 5 (`LETHAL_CAPACITY_NAMES` Split) don't depend on substrates and can ship at any time.

---

## Contributor checklist when adding a new flag

1. Decide whether the flag will be consumed by *existing* runtime code or by a future substrate.
2. If existing runtime: wire it on the same PR. Don't add unconsumed declarative state.
3. If future substrate: add a row to the table above with the substrate name and audit phase that will wire it. **An unconsumed flag without a row here is the symptom the audit catalogues** — that's how flag-debt accumulates.

When the audit's Phases 4–13 land, prune rows here and remove the flag-debt in `MEDICAL_SUBSTRATE_ROADMAP.md`'s "Drift Quick Reference" headline list.

---

## See Also

- `MEDICAL_SUBSTRATE_ROADMAP.md` — full audit catalogue, remediation phases, sequencing
- `HEALTH_AND_SUBSTANCE_SYSTEM_SPEC.md` — the canonical health/medical spec; "Spinal Anatomy, Decapitation & Combat Severance" section is the canonical reference for how death wiring crosses the schema boundary
- `world/medical/constants.py` — `LETHAL_CAPACITY_NAMES`, `BODY_CAPACITIES`, `CONSCIOUSNESS_UNCONSCIOUS_THRESHOLD`, `BLOOD_LOSS_DEATH_THRESHOLD`
- `world/medical/core.py` — `MedicalState.is_dead`, `is_unconscious`, `calculate_body_capacity`
- `world/anatomy/species.py` — per-species organ specs (where most of the unconsumed flags above are declared)
