# Species Authoring Guide

How to add a new species to Gelatinous so combat, severance, medical, longdesc rendering, decay naming, and corpse / severed-part prose all behave correctly without renderer code changes.

This guide is the species-onboarding playbook produced as Phase 5 of issue #356. Phases 1–4 lifted previously-global humanoid constants into the species registry. The rat (`SPECIES_DEFINITIONS["rat"]`) is the reference non-human implementation.

## Where species data lives

Two files hold the per-species data; everything else in the codebase consumes them via helpers:

- **`world/anatomy/species.py`** — `SPECIES_DEFINITIONS[species]` declares every per-species table (organs, severability, display order, decay templates, pair keys).
- **`world/anatomy/severed_parts.py`** — `SEVERED_PART_DESCRIPTIONS[species]` holds the prose for severed body parts at the three decay-condition tiers.

Two optional secondary places:

- **`world/medical/wounds/messages/*.py`** — per-injury-type wound prose. The existing tables are species-agnostic (humans share them). If a species needs distinct destruction or severance prose, declare a species-keyed overlay on each injury-type module (currently only human prose is shipped).
- **`world/anatomy/organs.py`** — `ORGAN_DISPLAY` for organ-name display. Species-agnostic today; new species reuse the existing mammalian organ names where biologically equivalent.

## Required tables in `SPECIES_DEFINITIONS[species]`

Every species declaration MUST include the following keys. Missing entries fall through to the human default and the renderer will produce wrong prose — anatomically distinct species need all of them filled in.

### Display

| Key | Type | Notes |
|---|---|---|
| `display_name` | str | Short glance-tag — `"rat"`, `"cyclops"`, etc. |
| `location_display` | dict | `body_location → "display string"`. Drives every species-routed location name in player-facing prose. |
| `severed_chain_display` | dict | Compound names for multi-segment severance (`{"left_thigh": "left leg"}`). Used by `get_species_severed_chain_name`. |
| `anatomical_display_order` | list | Render order (head-to-toe by convention). Drives the per-location loop in living, corpse, and severed-part renderers. |
| `anatomical_regions` | dict | `region_name → [locations]`. Drives the paragraph-break formatter. |
| `default_longdesc_locations` | dict | `location → None` seed map for fresh-character longdesc initialization. |

### Decay

| Key | Type | Notes |
|---|---|---|
| `decay_part_prefixes` | dict | `decay_stage → template` with `{species}` / `{part}` substitution. Drives severed-part naming. |
| `decay_organ_prefixes` | dict | Same shape, for harvested organ names. |
| `decay_corpse_names` | dict | Tier-to-name mapping (`fresh → "rat carcass"`, `skeletal → "skeletal remains"`). |
| `decay_corpse_descriptions` | dict | Tier-to-prose mapping; the body paragraph rendered on `look`. |

### Pair keys

| Key | Type | Notes |
|---|---|---|
| `pair_keys` | dict | `shorthand → (left_location, right_location)`. Drives longdesc pair-collapse, side-aware singular flex (#341), and the `describe` shorthand expansion. Empty `{}` for single-instance organs (cyclops, compound eye). |

### Organs

| Key | Type | Notes |
|---|---|---|
| `organs` | dict | `organ_name → spec`. Spec keys: `container`, optional `display_location` (for sensory organs surfacing at a specific longdesc line — see #346), `max_hp`, `hit_weight`, `vital`, `capacity` / `capacities`, contribution wiring, capability flags (`can_be_harvested`, `can_be_destroyed`, `damage_always_scars`, `backup_available`, ...). Mirrors the shape `MedicalState.to_dict()["organs"][name]` produces. |

### Severability

| Key | Type | Notes |
|---|---|---|
| `severable_containers` | frozenset | Body locations that can be detached as discrete items. |
| `severed_head_locations` | frozenset | Cluster bundled with decapitation (head, neck, face/snout, hair/fur, eyes, ears, ...). |
| `sever_hand_by_container` | dict | `limb_container → hand_side` for wielded-weapon detachment. Empty `{}` for species that can't wield. |
| `limb_downstream_chain` | dict | `proximal → (chain tuple including proximal)`. Severing a thigh takes the shin and foot, etc. |
| `limb_parent` | dict | `distal → proximal`. Reverse view used by the cut-point wound filter. |

## Required entries in `SEVERED_PART_DESCRIPTIONS[species]`

Each severable container needs prose at three condition tiers (`pristine`, `damaged`, `putrid`). The container set must match `species["severable_containers"]` — every container the species can lose. Falls through to human entries when missing; for anatomically distinct species the human prose will read wrong (e.g., "severed left arm" prose on a rat foreleg).

Example minimal declaration:

```python
SEVERED_PART_DESCRIPTIONS["rat"]["tail"] = {
    "pristine": "A long, ringed rat tail, severed at the base and weeping a thin line of blood.",
    "damaged":  "A dried-out rat tail, the rings gone leathery.",
    "putrid":   "A swollen rat tail, the rings discoloured.",
}
```

## Adding a species — step by step

1. **Sketch the anatomy** outside code first: which longdesc surfaces (head/snout vs head/face? wings? extra arms? tail?), which pair structure, which severable containers, which organs.
2. **Add the `SPECIES_DEFINITIONS[species]` entry** in `world/anatomy/species.py` filling every required table above. Copy the human entry as a starting template; rewrite as anatomy demands.
3. **Add `SEVERED_PART_DESCRIPTIONS[species]` entries** in `world/anatomy/severed_parts.py` for every severable container × condition tier (severable_containers × 3 entries).
4. **Write a `world/tests/test_<species>_species.py` test module** patterned on `test_rat_species.py`. Cover: registry shape, distinct organ set vs human, distinct severability tables, distinct display order, distinct pair keys, end-to-end `MedicalState` construction producing species-shaped organs.
5. **Run the full suite** — `evennia test --settings settings.py world` — and confirm no human regressions. The species architecture should mean no humans see any difference.
6. **Smoke-test in game** — spawn the species, `look` at one, kill it, `look` at the corpse, sever a limb / tail / head, look at the appendage. Every string should read as the species; check for any leaked "human" / "left arm" / "thigh" vocabulary.

## Consumer pattern

When writing code that branches on anatomy, never read the global constants in `world/combat/constants.py` if the call site has a character / corpse / appendage context. Use the species-keyed helpers:

```python
from world.anatomy import (
    get_organ_spec,
    get_species_anatomical_display_order,
    get_species_anatomical_regions,
    get_species_default_longdesc_locations,
    get_species_limb_downstream_chain,
    get_species_limb_parent,
    get_species_organs,
    get_species_pair_keys,
    get_species_severable_containers,
    get_species_sever_hand_by_container,
    get_species_severed_head_locations,
)
```

Each helper takes a species identifier and falls back to human on `None` / unknown so test stubs and species-less call sites keep working. The global constants in `world/combat/constants.py` (`PAIR_MERGE_KEYS`, `ORGANS`, `SEVERABLE_CONTAINERS`, etc.) remain importable as **derived aliases of the human entry** — keep using them at call sites that don't have a species context (admin commands, mob-flavor generators, tests that always operate on humans).

## What `Phases 1–4` migrated

For reference, the consumers updated to be species-aware during the rollout:

- `MedicalState._initialize_default_organs`, `MedicalState.get_organ`, `Organ.__init__`
- `ArmorMixin._maybe_sever_from_damage` (severable set)
- `apply_sever_to_character`, `Appendage.configure_from_sever`, `Appendage.configure_from_living_sever` (downstream chain)
- `apply_sever_to_corpse`, `apply_severed_head_overlay`, `apply_severed_head_overlay_from_living`, `spawn_severed_head_for_living`, `SeveredHead.configure_from_sever`, `SeveredHead.configure_from_living_decap` (head cluster)
- `detach_items_to_appendage` (hand-side map)
- `get_character_wounds` (limb-parent map, cut-point filter)
- `AppearanceMixin.get_longdesc_appearance`, `_build_paired_longdesc_collapse`, `_flex_noun_vocabulary`, `_substitute_longdesc_tokens` (display order, pair keys)
- `Corpse._get_preserved_longdesc_descriptions`, `_process_corpse_description_variables`, `_build_decay_desc_paragraph` (display order, pair keys, decay templates)
- `Appendage.return_appearance` (display order, pair keys)
- `Character.at_object_creation` (default longdesc surfaces)

If you add a new consumer that reads a global anatomy constant, ask whether it should be species-aware — and if so, migrate it via the matching helper.

## Open follow-ups (not yet species-keyed)

The architecture is now complete enough to ship anatomically distinct species. The only remaining global is:

- `ORGAN_DISPLAY` (`world/anatomy/organs.py`). Per-organ display name and condition prose for autopsy / harvest rendering. Currently human-anchored. Rats fall through gracefully — shared organ names (brain / heart / left_lung / liver / etc.) get human prose which reads OK on a smaller body, and rat-specific bones (`left_foreleg_bone` / `tail_vertebrae`) get an underscore-stripped display name and empty prose (the renderer drops empty prose cleanly). A future species with biologically distinct organs (a synth with mechanical organs, an alien with non-mammalian systems) would need its own organ-prose table. Same migration pattern as the other follow-ups: add to `SPECIES_DEFINITIONS[species]`, write a `get_species_organ_display(species)` helper, derive the legacy global from the human entry.

### Migrated follow-ups (now species-keyed)

- `LONGDESC_FLEX_NOUNS` (`SPECIES_DEFINITIONS[species]["longdesc_flex_nouns"]`). Rats add `tail` / `snout` / `fur` / `whisker` / `paw` / `claw`; pair-keyed singulars flow through `pair_keys` automatically. Use `get_species_longdesc_flex_nouns(species)`.
- `BODY_CAPACITIES` (`SPECIES_DEFINITIONS[species]["body_capacities"]`). Rat's `moving` references hindleg/hindpaw bones; `manipulation` references foreleg/forepaw bones; `talking` is intentionally absent (rats squeak, they don't talk). Use `get_species_body_capacities(species)`. Consumers updated: `MedicalState.calculate_body_capacity`, `world.medical.utils._get_vital_locations`.

## Item-level compatibility layer (Phase 2.10 follow-up)

The species spec answers *"what slots does a species have?"* Organ items (harvested or cyberware) layer a complementary question on top: *"can this particular organ instance be installed in this target?"* This is item-side, not species-side — both layers coexist.

Three item-side fields land on every donor organ:

| Item attribute | Source | Purpose |
|---|---|---|
| `db.compatible_species` | Stamped `[source_species]` at harvest by `_configure_harvested_item`; freely declared on cyberware at item creation | Cross-species gate. Picker / install resolver refuses if target's species isn't in the list. Legacy items pre-dating this field fall back to `[db.source_species]` via the existing harvest provenance. |
| `db.target_container` | Cyberware only; biological harvest doesn't set it | Override for items that don't have an `organ_name` matching the species spec (cyberware bulk-slot replacements — artificial heart, etc.). |
| `db.target_display_locations` | Cyberware only; list of valid display surfaces | Override for items installable at multiple display locations (cybernetic eye → `["left_eye", "right_eye"]`). |

Picker flow (`CmdOperate._list_install_locations`):

1. **Cross-species gate.** If `donor.db.compatible_species` is set and doesn't include the target's species, return empty (picker refuses).
2. **Candidate slots.** If the item declares `target_display_locations` (cyberware paired-slot path), use those. Else if it declares `target_container` (cyberware bulk-slot path), use that. Else look up the donor's `organ_name` in `get_species_organs(target_species)` (biological path) and use `display_location` if distinct from `container`, otherwise `container`.
3. **Status tag.** Each candidate is tagged `(empty)` or `(occupied)` based on the current HP of the organ at that slot.

The cybernetic-eye case validates the model end-to-end: a single item declares `compatible_species = ["human", "rat", "lizard"]` and `target_display_locations = ["left_eye", "right_eye"]` — the picker offers both eye sockets on whichever recipient species the item supports, and refuses on uncompatible species. Cyberware items don't need entries in any species spec.

Multi-slot capacity (Doctor Octopus arms — installing multiple instances of the same organ type into augmented anatomy) is future work and will need a `state.organs` → `state.slots` schema change. It plugs into the same `target_display_locations` declaration without rework.
