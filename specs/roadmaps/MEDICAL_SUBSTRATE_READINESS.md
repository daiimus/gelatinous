# Medical Substrate Readiness Index

This is the flag→consumer ledger paired with `MEDICAL_SUBSTRATE_ROADMAP.md`. It lists the anatomy flags declared in the species and organ specs, what reads each one, and, for each flag nothing reads, which substrate will consume it and which audit phase wires it in. The roadmap's Core Insight states its purpose:

> The medical system has a top-down anatomical schema whose bottom-up consumer systems were never built. Each declarative flag advertises a consumer system that hasn't been written yet. Deleting them would be deleting design documentation. The right work is *building the substrates*.

The schema is described in `HEALTH_AND_SUBSTANCE_SYSTEM_SPEC.md`. The audit in `MEDICAL_SUBSTRATE_ROADMAP.md` is the plan; this file is the at-a-glance map.

---

## How to use this document

- **Adding a new flag** to a species table in `world/anatomy/species.py` (`organs` or `body_capacities`) or to an augment organ spec in `world/prototypes.py`? Add a row here too. `BODY_CAPACITIES` in `world/medical/constants.py` is a copy of the human table, not a place to declare flags. If the flag has no current consumer, point at the substrate phase that will eventually read it.
- **Wiring a flag into a runtime consumer**? Move its row to the read tables, link the audit phase that resolved it, and remove it on the next cleanup pass.
- **Adding a new consumer system** (substrate)? Read down the table for which flags it should consume on first wiring.
- **Re-validating the audit**? Cross-check these tables against the code by grepping each flag.

---

## Flags waiting for a consumer

Nothing reads these flags at runtime.

| Flag (declaration site) | Consumer it waits for | Audit phase | Disposition |
|---|---|---|---|
| `vital` (Organ init from species spec) | None. Superseded by the data-driven `_get_vital_locations`, which reads `LETHAL_CAPACITY_NAMES` | Phase 4 — Vestigial-Flag Deletion | **Vestigial** — delete in Phase 4 |
| `fatal_threshold` (`body_capacities` in `world/anatomy/species.py`) | A data-driven `is_dead` that compares each lethal capacity against this threshold instead of the literal `<= 0.0` floor | Phase 5 was done another way (#3248) and does not wire this; decide at the Phase 7 audit whether to wire it or delete it | Keep until the Phase 7 audit |
| `incapacitation_threshold: 0.15` on `moving` | **Movement Policing system** — when capacity is below this, the character cannot move (movement commands refuse / sleep into low-stamina locomotion) | Phase 7 — Movement Policing Substrate + Phase 10 wiring | **Substrate gap** — movement policing. Movement itself is not gated. The dodge curve (`MOVING_CURVE_DODGE` in `world/combat/capacity.py`) copies 0.15 by hand instead of reading this flag. |
| `modifiers: [...]` on `consciousness` | None. The cascade (pain → consciousness, blood → consciousness, suppression → consciousness) is implemented imperatively in `update_vital_signs`; this list is design documentation only | Phase 4 — Vestigial-Flag Deletion (or convert to spec comment) | **Vestigial** — delete or document-only |
| `affects: [...]` on capacities | None today. Could drive a generic capacity-effect graph if such a substrate is ever built | Phase 4 — Vestigial-Flag Deletion (unless an effect-graph substrate is in plan) | **Vestigial unless** the graph is on the roadmap |
| `total_loss_penalty: "blindness"` on `sight` | **Senses System** — total sight loss spawns a `BlindCondition` that gates perception (combat targeting, look output, sdesc rendering) | Phase 8 — Senses System | **Partly met another way.** Sight gates perception by reading the capacity directly (`can_see` in `world/perception.py`) and scales hit chance (`sight_hit_factor` in `world/combat/capacity.py`). No `BlindCondition` exists. |
| `total_loss_penalty: "deafness"` on `hearing` | **Senses System** — total hearing loss spawns a `DeafCondition` that gates audio perception (combat broadcasts, room sounds, conversation) | Phase 8 — Senses System | **Partly met another way.** Hearing gates perception by reading the capacity directly (`can_hear` in `world/perception.py`). No `DeafCondition` exists. |
| `total_loss_penalty: "anosmia"` on `smell` | **Senses System**. Smell already gates perception by reading the capacity directly (`can_smell` in `world/perception.py`) | Phase 8 — Senses System | Unread |
| `total_loss_effects: ["cannot_negotiate", ...]` on `talking` | **Social interaction substrate** — can't speak → can't negotiate / persuade / bid in trade | No audit phase yet — open design | **Substrate gap** — social policing (out of audit scope). The `talking` capacity already garbles speech (`is_voice_garbled` in `world/voice.py`); nothing gates negotiation. |
| `cannot_be_destroyed: True` on `thoracolumbar_spine` | 📋 UNBUILT (no issue): `Organ.take_damage` should floor this organ at 1 HP; today it floors every organ at 0 | Phase 7 follow-up (movement policing wires this) | **Direct wire** — small fix, ~Phase 7 cleanup |
| `paralysis_if_destroyed: True` on `thoracolumbar_spine` | **Movement Policing system** — produces a permanent `ParalysisCondition` that zeroes `moving` capacity | Phase 7 — Movement Policing Substrate + Phase 11 wiring | **Substrate gap** — movement policing |
| `effect: "unconscious_flag"` on `consciousness` | None known; `is_unconscious` reads `CONSCIOUSNESS_UNCONSCIOUS_THRESHOLD` | Not assigned | Unread |
| `source: "bleeding_injuries"` on `blood_loss` | None known; `BLOOD_LOSS_DEATH_THRESHOLD` is the real gate | Not assigned | Unread — declarative |
| `jaw_primary` on `eating` | None known | Not assigned | Unread |
| `causes_pain_when_damaged` (organ spec) | None known | Not assigned | Unread |
| `backup_available` (organ spec) | None known | Not assigned | Unread |
| `can_be_replaced` (augment / organ spec) | None: nothing reads it, and `_resolve_install` does not check it | — | 📋 UNBUILT (not decided) |

**Kidney loss is not fatal.** The schema once carried `total_loss_fatal: True` on `blood_filtration`, declaring total kidney loss fatal. By owner ruling (#3402), kidney loss is **not fatal**; renal failure's lasting obtundation is the cost. The flag was deleted with that ruling (2026-09-24).

---

## Flags read today

### Death and anatomy flags (declarative or read)

| Flag (declaration site) | What reads it |
|---|---|
| `directly_fatal` (`body_capacities` in `world/anatomy/species.py`) | Nothing at runtime. A test pins it to equal `LETHAL_CAPACITY_NAMES` for every species (#3677). It declares which capacities terminate life; `is_dead` loops over the tuple the flags must match (#3248 removed `consciousness` from it; #3677 made the check a loop). Keep: declarative and tested. |
| `can_be_destroyed` (most organs) | `_is_leg_bone` in `world/gravity.py`. Fall damage: an organ that feeds `moving` and carries `can_be_destroyed: True` counts as a leg. This keeps the pelvis and the spine out of the leg set. Load-bearing. |
| `fracture_vulnerable` | `organ_is_bone` in `world/medical/core.py`, which decides whether an organ is a bone. Splinting (`world/medical/utils.py`), the consumption treatment path (`commands/CmdConsumption.py`) and `MedicalState.organ_beyond_repair` all call `organ_is_bone`. Load-bearing. |
| `bone_type` | Bone identity (`organ_is_bone` in `world/medical/core.py`) and the bone name in the splint message (`world/medical/utils.py`). Load-bearing. |

### Flags from the augment / cyberware arc (#511–#551)

These organ-spec flags came with the anatomy-augments and cyberware chassis+module work. Runtime code consumes them; they are load-bearing, not substrate gaps.

| Flag (declaration site) | What reads it |
|---|---|
| `inorganic` (organ spec) | Damage model — chrome takes pain only, no bleed/infection (`MedicalState.take_organ_damage`); chrome rendering (`appearance_mixin`); chrome severance prose (`get_severance_message`) |
| `prosthetic_frame` (chassis organs) | `is_cybernetic_limb` — reattachment eligibility + chrome severance routing |
| `hardpoint` (chassis slot organ) | `find_hardpoint` — module seating (`world/medical/procedures.py`) |
| `module_type` (module item / hardpoint) | Install dispatch + hardpoint match + harvest provenance |
| `abilities` (organ spec) | Ability layer — `find_ability`, `iter_abilities`, toggle dispatcher |
| `flesh_organ` (flesh-mount module) | Names the specific host organ in a multi-organ container (Jawz→jaw) |
| `can_be_harvested` | Harvest gate (`can_harvest_organ` in `world/medical/removable.py`) |
| `capacities` (list) + `*_contribution` | Per-character capacity math for replacement/augment organs (`calculate_body_capacity`) |
| `grasping` (organ spec) | Prehensile `hands` overlay — extra held slot from a grasping container |
| `severable_container` (augment organ) | Severable-overlay + operate-menu sever listing |
| `display_location` / `hit_weight` | Surface-access incision gate + hit-distribution weighting (older than the augment arc) |

**Capacity-extension note.** Augment organs can *add* anatomy and capacities a species table never declared (the cyber tail; a future Doc-Ock rig). The substrate phases below (movement policing, senses, equipment-handling) assume the static species table is the full capacity set. Per-character capacity *extension* is an un-catalogued wrinkle to fold in when those substrates are scoped. See `MEDICAL_SUBSTRATE_ROADMAP.md`.

---

## Substrate → Phases the Audit Sequences

Substrate work blocks the wiring phases that depend on it: build the substrate first, then wire the flags to it.

| Substrate | Build in | Wires up |
|---|---|---|
| Chronic Medical Conditions framework | Phase 6 | `RenalFailureCondition` extends `MedicalCondition`; 📋 UNBUILT (no issue): a generic `ChronicCondition` base. Phase 12 (kidney death via `RenalFailure`) is declined (#3402). |
| Movement Policing | Phase 7 | Phase 10 (functional-capacity incapacitation), Phase 11 (paralysis). Today `moving` only scales dodge (`moving_dodge_factor`); movement is not gated |
| Senses System | Phase 8 | Blindness / deafness conditions. Perception is already gated by capacity reads (`can_see` / `can_hear` / `can_smell` in `world/perception.py`), and sight scales hit chance |
| Equipment-Handling (manipulation consequences) | Phase 9 | Weapon-drop / can't-wield on low `manipulation` capacity. Today manipulation and under-grip scale hit chance (`manipulation_hit_factor` / `grip_hit_factor` in `world/combat/capacity.py`); 📋 UNBUILT (no issue): refusing to wield and dropping items |
| Social interaction substrate | (open — no audit phase) | `talking` total-loss effects (`cannot_negotiate`, etc.) |

Phase 4 (Vestigial-Flag Deletion) does not depend on a substrate and can be done at any time. Phase 5 was done another way (#3248): one tuple, `LETHAL_CAPACITY_NAMES`, is both the death set and the vital-target set.

---

## Contributor checklist when adding a new flag

1. Decide whether the flag will be consumed by *existing* runtime code or by a future substrate.
2. If existing runtime: wire it on the same PR. Don't add unconsumed declarative state.
3. If future substrate: add a row to the waiting table above with the substrate name and audit phase that will wire it. **An unconsumed flag without a row here is the symptom the audit catalogues** — that's how flag-debt accumulates.

As the audit's Phases 4–13 are done, prune rows here and remove the flag-debt in `MEDICAL_SUBSTRATE_ROADMAP.md`'s "Flag readiness ledger" section.

---

## Not decided

- Whether `fatal_threshold` is wired into `is_dead` or deleted: decide at the Phase 7 audit.
- The social interaction substrate (`talking` total-loss effects) has no audit phase: open design.
- For each unread flag with no audit phase (`anosmia` on `smell`, `unconscious_flag` on `consciousness`, `source` on `blood_loss`, `jaw_primary`, `causes_pain_when_damaged`, `backup_available`): is it vestigial and due for Phase 4 deletion, or waiting for a substrate?
- The dodge curve copies the 0.15 `incapacitation_threshold` by hand: should it be built now from one source (the constant or the species flag), or stay as written until Phase 7 wires the flag?

---

## See Also

- `MEDICAL_SUBSTRATE_ROADMAP.md` — full audit catalogue, remediation phases, sequencing
- `HEALTH_AND_SUBSTANCE_SYSTEM_SPEC.md` — the canonical health/medical spec; "Spinal Anatomy, Decapitation & Combat Severance" section is the canonical reference for how death wiring crosses the schema boundary
- `world/medical/constants.py` — `LETHAL_CAPACITY_NAMES`, `BODY_CAPACITIES`, `CONSCIOUSNESS_UNCONSCIOUS_THRESHOLD`, `BLOOD_LOSS_DEATH_THRESHOLD`
- `world/medical/core.py` — `MedicalState.is_dead`, `is_unconscious`, `calculate_body_capacity`
- `world/anatomy/species.py` — per-species organ specs (where most of the unconsumed flags above are declared)
