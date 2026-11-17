# Species Authoring Guide

> **Status:** ✅ **SHIPPED** — guide verified against code 2026-08-02.

How to add a new species to Gelatinous so combat, severance, medical, longdesc rendering, decay naming, and corpse / severed-part prose all behave correctly without renderer code changes.

This guide is the species-onboarding playbook produced as Phase 5 of issue #356. Phases 1–4 lifted previously-global humanoid constants into the species registry. The rat (`SPECIES_DEFINITIONS["rat"]`) is the reference non-human implementation.

## Where species data lives

Two files hold the per-species data; everything else in the codebase consumes them via helpers:

> **CORRECTION (2026-09-12):** no longer two, and a species that skips the undocumented sites silently wears human prose. Beyond the two below and the two "optional secondary" places, four more locations carry species-keyed data. None of them are new — every one predates this guide's 2026-08-02 "verified" banner:
>
> - **`world/anatomy/organ_descriptions.py`** — `ORGAN_DESCRIPTIONS_BY_SPECIES`, per-organ *condition prose* for non-organic bodies (robot, synth). Consulted before `ORGAN_DISPLAY` by `get_organ_default_description(organ, condition, species)` (`world/anatomy/organs.py`). Landed 2026-06-26, PR #845. (#2262 / PR #2275, 2026-08-24, is often miscited for this — that change routed the surgical *chart* through `get_organ_display_name` and filled one missing component description; it neither created the module nor the species lookup.)
> - **`world/medical/medical_messages.py`** — `BLEEDING_ROOM_BY_SPECIES`, `DEATH_CAUSE_TEMPLATES_BY_SPECIES`, `_GENERIC_DEATH_BY_SPECIES`; #375, 2026-06-04. All four registered species are populated; an unpopulated species gets human death and bleeding prose.
> - **`world/mob_flavor/__init__.py`** — `_SHORT_DESCS_BY_SPECIES`, `_LOOK_PLACES_BY_SPECIES`, `_LONGDESCS_BY_SPECIES`; #372, 2026-06-04. All four populated.
> - **`world/combat/messages/unarmed_<species>.py`** — `get_combat_message` prefers a species-suffixed module over the human-anchored `unarmed.py` (`world/combat/messages/__init__.py`); #365, 2026-06-04. `unarmed_rat.py` is the shipped example.

- **`world/anatomy/species.py`** — `SPECIES_DEFINITIONS[species]` declares every per-species table (organs, severability, display order, decay templates, pair keys).
- **`world/anatomy/severed_parts.py`** — `SEVERED_PART_DESCRIPTIONS[species]` holds the prose for severed body parts at the three decay-condition tiers.

Two optional secondary places:

- **`world/medical/wounds/messages/*.py`** — per-injury-type wound prose. The existing tables are species-agnostic (humans share them). **Species packs (shipped 2026-07-05):** a species whose wounds must not read as human flesh registers a COMPLETE pack module in `messages.SPECIES_PACKS` (`robot.py` — torn plating, amber hydraulic weep, weld-seam scars; `synth.py` — cobalt blood, pearlescent seam scars). A pack species renders ALL surface-wound prose (every stage, plus `DESTROYED_BY_LOCATION` and `COMPOUND_DESCRIPTIONS`) from its pack — it never falls through to the shared flesh tables, which is the no-leak guarantee (pin new packs with a completeness test like `test_species_wounds.py`). Pack prose should hardcode the species `blood_color` (`world/anatomy/species.py`) and match the register of its `organ_descriptions.py` entries so surface and organ damage read as one body. **NOTE (2026-07-13, #1206):** WEAPON + severance message prose no longer hardcodes colour — it uses `{blood}`/`{Blood}` format fields resolved from the TARGET's species (human crimson / synth cobalt / robot amber) in `get_combat_message` + `get_severance_message`; a validator (`test_blood_tokens.py`) forbids bare colour words there. Pack wound tables (the species-keyed medical prose) still hardcode their own colour — that's the species speaking about ITSELF, not a weapon describing an arbitrary target. Humans and pack-less species (rat, ...) keep the shared modules unchanged. **Per-injury vocabulary (2026-09-14, #3512):** a pack may also carry `BY_INJURY = {injury_type: {stage: [...]}}` and `COMPOUND_BY_INJURY`; the lookup prefers them, so a blow, a bullet and a blade read differently on a synth or a robot (a synth pools cobalt under the dermis; a robot dents). A pack that has `BY_INJURY` must author every injury type the species can take. `get_wound_description` (`world/medical/wounds/wound_descriptions.py`) answers a type the pack lacks with a plain line ("a severe plasma wound on the left arm"), not with the pack's stage-only table and never with flesh prose. Only `generic`, an unset type and the destroyed stage fall back to the stage-only tables. A compound line for a type missing from `COMPOUND_BY_INJURY` falls back to the pack's `COMPOUND_DESCRIPTIONS`. Compound lines keep `{severity}` on ONE wound and spend `{others_phrase}` on the rest; single-wound lines never use `{others_phrase}`; robot lines never use `{skintone}`. `test_species_wounds.PacksAnswerByInjuryType` pins all of it: blunt, bullet, stab, laceration, burn and cut at fresh, treated, healing and scarred, a compound fresh line for each, and `harvested` and `severed` at every stage the test lists.
- **`world/anatomy/organs.py`** — `ORGAN_DISPLAY`, the shared organic organ names and prose. A species renames organs with `organ_display` in its `SPECIES_DEFINITIONS` entry and rewrites their prose in `ORGAN_DESCRIPTIONS_BY_SPECIES` (`world/anatomy/organ_descriptions.py`). A species that keeps mammalian organs can reuse the shared names.

Code also branches on species by name, and a new species gets the default branch in each: the butcher's refusal line (`_refusal_line` in `world/butchery.py`), the medical supply gate (`serves_species` in `world/medical/utils.py`, with its robot special case for supplies that declare neither `serves` nor `not_for`, and the robot's "tool roll"), and the soul needs profiles (the `profile_name(...) == "robot"` checks in `world/souls/`). Decide for each whether the default is right.

## Required tables in `SPECIES_DEFINITIONS[species]`

Every species declaration MUST include the following keys. A registered species that leaves one out gets an empty table from its getter, not the human one: missing anatomy and no prose. Only an unknown or unset species name falls back to the human entry.

> **CORRECTION (2026-09-12):** two errors in the paragraph above.
>
> 1. **The fallback is per-SPECIES, not per-KEY.** `_resolve_species` (`world/anatomy/species.py`) substitutes the whole human entry only for an unknown or `None` species *name*. A REGISTERED species that omits a key gets an EMPTY collection from the getter — `frozenset(spec.get("severable_containers") or frozenset())`, and the same `or {}` / `or ()` shape in `get_species_pair_keys`, `get_species_organs`, `get_species_grasping_containers`. So the real failure mode of a missing table is *absent anatomy and silent prose*, not human prose. (Species built by `_derive_*` deepcopy do inherit human values for anything they don't override — that path is the exception.)
> 2. **The list below is incomplete.** Every registered species also declares `grasping_containers` — the Mr. Hands slot set (#307 / PR-H1), declared on the human and rat entries (the rat's set is empty), read by `get_species_grasping_containers` and consumed in `typeclasses/characters.py` and `world/combat/utils.py`; the rat's empty set is why a rat can't wield. Non-flesh bodies additionally declare `infection_immune` (synth and robot; getter `get_species_infection_immune`) and `organ_display` (synth and robot). `blood_color` is declared by **human too** (alongside synth and robot; getter `get_species_blood_color`) — the rat is the species that omits it and silently inherits crimson from `_DEFAULT_BLOOD_COLOR`, which is the trap for any new species whose fluid is not red. `body_capacities` and `longdesc_flex_nouns` are required too — they are documented under "Migrated follow-ups" below rather than in this table.

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
| `organs` | dict | `organ_name → spec`. Spec keys: `container`, optional `display_location` (for sensory organs surfacing at a specific longdesc line — see #346), `max_hp`, `hit_weight`, `vital`, `capacity` / `capacities`, contribution wiring, capability flags (`can_be_harvested`, `can_be_destroyed`, `damage_always_scars`, `backup_available`, ...). Each organ object keeps this spec as its `data` (`Organ.to_dict()["data"]`). |

### Severability

| Key | Type | Notes |
|---|---|---|
| `severable_containers` | frozenset | Body locations that can be detached as discrete items. |
| `severed_head_locations` | frozenset | Cluster bundled with decapitation (head, neck, face/snout, hair/fur, eyes, ears, ...). |
| `sever_hand_by_container` | dict | `limb_container → hand_side` for wielded-weapon detachment. Empty `{}` for species that can't wield. |
| `limb_downstream_chain` | dict | `proximal → (chain tuple including proximal)`. Severing a thigh takes the shin and foot, etc. |
| `limb_parent` | dict | `distal → proximal`. Reverse view used by the cut-point wound filter. |

## Required entries in `SEVERED_PART_DESCRIPTIONS[species]`

Each severable container needs prose at three condition tiers (`pristine`, `damaged`, `putrid`). The container set must match `species["severable_containers"]` — every container the species can lose. ~~Falls through to human entries when missing~~ **Corrected 2026-09-13 (#3362):** a REGISTERED species with no bank gets *silence* (empty string, so the part renders with no description), not human prose — that fallback exists only for an *unknown* species name (#2725). As of #3362 all four registered species carry a full bank (human, rat, robot, synthetic_humanoid); a new species MUST ship one, and `world/tests/test_severed_part_descriptions.py` fails if any registered species is missing a location or a condition tier. A part whose organs are augment chrome reads from `CYBERNETIC_PART_DESCRIPTIONS` instead, unless the species is `infection_immune` and has its own bank (`get_severed_part_description`). A non-flesh species' bank must not say "blood" or "human"; `test_inorganic_species_prose_is_not_flesh` checks robot and synth.

Example: the rat's `tail` entry. The real bank is built with `SEVERED_PART_DESCRIPTIONS.setdefault("rat", {...})`.

```python
SEVERED_PART_DESCRIPTIONS["rat"]["tail"] = {
    "pristine": "A long, ringed rat tail, severed at the base and weeping a thin line of blood from the cut.",
    "damaged":  "A dried-out rat tail, the rings gone leathery and the base-cut crusted hard.",
    "putrid":   "A swollen rat tail, the rings discoloured and the flesh sloughing softly off the vertebrae.",
}
```

## Adding a species — step by step

1. **Sketch the anatomy** outside code first: which longdesc surfaces (head/snout vs head/face? wings? extra arms? tail?), which pair structure, which severable containers, which organs.
2. **Add the `SPECIES_DEFINITIONS[species]` entry** in `world/anatomy/species.py` filling every required table above. Copy the human entry as a starting template; rewrite as anatomy demands.
3. **Add `SEVERED_PART_DESCRIPTIONS[species]` entries** in `world/anatomy/severed_parts.py` for every severable container × condition tier (severable_containers × 3 entries).
4. **Write a `world/tests/test_<species>_species.py` test module** patterned on `test_rat_species.py`. Cover: registry shape, distinct organ set vs human, distinct severability tables, distinct display order, distinct pair keys, end-to-end `MedicalState` construction producing species-shaped organs.
5. **Run the full suite** — `docker exec <CONTAINER> evennia test --settings settings.py world` — and confirm no human regressions. The species architecture should mean no humans see any difference.
6. **Register the species in `@spawnmob`** — add a switch to `SPECIES_SWITCHES` in `commands/CmdSpawnMob.py`; the command refuses any other switch. A species listed in `PERSON_SPECIES` spawns as a person and needs civilian archetypes for that species (`archetypes_for`), or the command answers "No archetype is authored". Any other species spawns as a bare body through `spawn_body`, keyed "a <species>" unless you give it a name or add one there.
7. **Smoke-test in game** — spawn the species, `look` at one, kill it, `look` at the corpse, sever a limb / tail / head, look at the appendage. Every string should read as the species; check for any leaked "human" / "left arm" / "thigh" vocabulary.

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

Each helper takes a species identifier and falls back to human on `None` / unknown so test stubs and species-less call sites keep working. Get the species from an object with `species_of(obj)` (from `world.anatomy`), not `obj.db.species`: severed parts and harvested organs carry their species only in `db.source_species`, and `species_of` reads both. The global constants in `world/combat/constants.py` (`PAIR_MERGE_KEYS`, `SEVERABLE_CONTAINERS`, etc.) and `world/medical/constants.py` (`ORGANS`, `BODY_CAPACITIES`) remain importable as **derived aliases of the human entry** — keep using them at call sites that don't have a species context (admin commands, mob-flavor generators, tests that always operate on humans).

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

`ORGAN_DISPLAY` is the shared organic table, and species override it:

- `ORGAN_DISPLAY` (`world/anatomy/organs.py`). Per-organ display name and condition prose for autopsy / harvest rendering. Currently human-anchored. **SUPERSEDED (2026-09-12):** no longer the only remaining global, and no longer human-anchored on either axis — and both overrides shipped 2026-06-26, i.e. this follow-up register was already out of date when this guide was last verified on 2026-08-02. *Display names:* `organ_display` ships for BOTH `synthetic_humanoid` (the wetware register described below) and `robot` — a full MECHANICAL register (brain→processor core, heart→power core, eyes→optical sensors, limb bones→struts/servos) in `_derive_robot` (`world/anatomy/species.py`), resolved by `get_organ_display_name(organ, species)` (`world/anatomy/organs.py`); issue #842 / PR #843. *Condition prose:* `world/anatomy/organ_descriptions.py` carries `ORGAN_DESCRIPTIONS_BY_SPECIES` banks for robot and synth, consulted first by `get_organ_default_description(organ, condition, species)` (`world/anatomy/organs.py`); PR #845. `ORGAN_DISPLAY` is now the shared ORGANIC table and the fallback for unoverridden organs — a new non-flesh species overrides at BOTH sites, not one. Rats fall through gracefully — shared organ names (brain / heart / left_lung / liver / etc.) get human prose which reads OK on a smaller body, and rat-specific bones (`left_foreleg_bone` / `tail_vertebrae`) get an underscore-stripped display name and empty prose (the renderer drops empty prose cleanly). **SHIPPED for synth (2026-07-13, #1204):** `SPECIES_DEFINITIONS[synthetic_humanoid]["organ_display"]` + `get_organ_display_name(organ, species)` — the WETWARE register (`_SYNTH_WETWARE` in `species.py`): soft core renamed to engineered-tissue nouns (brain→wetcore, heart→vat-heart, lungs→culture-lungs, liver→filter gland, kidneys→flush glands, stomach→culture gut) while bones/senses/form-visible organs stay "synthetic <organ>"; decay tiers compose free ("inert wetcore"); a test forbids industrial vocabulary (the rejected "cardiac pump" register — a Synthetic Humanoid is a replicant, not a machine). Humans untouched. An alien with non-mammalian systems would follow the same pattern.

### Migrated follow-ups (now species-keyed)

- `LONGDESC_FLEX_NOUNS` (`SPECIES_DEFINITIONS[species]["longdesc_flex_nouns"]`). Rats add `tail` / `snout` / `fur` / `whisker` / `paw` / `claw`; robots add chassis nouns (`manipulator`, `strut`, `housing`, ...); pair-keyed singulars flow through `pair_keys` automatically. A noun that a species' longdesc lines write as a `{token}` flexes between singular and plural only if it is in this set or is a pair singular. Use `get_species_longdesc_flex_nouns(species)`.
- `BODY_CAPACITIES` (`SPECIES_DEFINITIONS[species]["body_capacities"]`). Rat's `moving` references hindleg/hindpaw bones; `manipulation` references foreleg/forepaw bones; `talking` is intentionally absent (rats squeak, they don't talk). Use `get_species_body_capacities(species)`. Consumers updated: `MedicalState.calculate_body_capacity`, `world.medical.utils._get_vital_locations`. `body_capacities` must wire every capacity in `LETHAL_CAPACITY_NAMES` (`world/medical/constants.py`), each with `directly_fatal: True`. `calculate_body_capacity` reads a capacity with no organs as full, so a species that leaves one out cannot die that way. `consciousness` is not a death gate.

## Item-level compatibility layer (Phase 2.10 follow-up)

The species spec answers *"what slots does a species have?"* Organ items (harvested or cyberware) layer a complementary question on top: *"can this particular organ instance be installed in this target?"* This is item-side, not species-side — both layers coexist.

The install picker reads three item-side fields. Harvested organs and the cyberware prototypes carry `compatible_species`. No item in the game sets `target_container` or `target_display_locations`; only the picker tests use them:

| Item attribute | Source | Purpose |
|---|---|---|
| `db.compatible_species` | Stamped `[source_species]` at harvest by `_configure_harvested_item`; freely declared on cyberware at item creation | Cross-species gate. Picker / install resolver refuses if target's species isn't in the list. Legacy items pre-dating this field fall back to `[db.source_species]` via the existing harvest provenance. |
| `db.target_container` | Cyberware only; biological harvest doesn't set it | Override for items that don't have an `organ_name` matching the species spec. No item uses it: the cybernetic heart installs by `organ_name = "heart"` and carries its own `organ_spec`. |
| `db.target_display_locations` | Cyberware only; list of valid display surfaces | Override for items installable at multiple display locations. No item uses it: the cybernetic eyes are two items that install by `organ_name` (`left_eye`, `right_eye`). |

Picker flow (`_list_install_locations` in `commands/CmdOperate.py`):

1. **Cross-species gate.** If `donor.db.compatible_species` is set and doesn't include the target's species, return empty (picker refuses).
   The install itself (`_resolve_install` in `world/medical/procedures.py`) checks again, and is stricter as built: an organ with neither `compatible_species` nor `source_species` is refused there ("The <organ> isn't <species> anatomy — it won't take."), although the picker lets it through. That refusal is not a failed roll.
2. **Candidate slots.** If the item has a `module_type` (on the item or in its `organ_spec`), the slots are the target's free containers whose organ `hardpoint` matches it, and nothing below applies. Else if the item declares `target_display_locations` (cyberware paired-slot path), use those. Else if it declares `target_container` (cyberware bulk-slot path), use that. Else look up the donor's `organ_name` in `get_species_organs(target_species)` (biological path) and use `display_location` if distinct from `container`, otherwise `container`.
3. **Status tag.** Each candidate is tagged `(empty)` or `(occupied)` based on the current HP of the organ at that slot.

The picker tests exercise `target_display_locations` with a made-up cybernetic eye declaring `compatible_species = ["human", "rat", "lizard"]` ("lizard" exists only in that test) and `target_display_locations = ["left_eye", "right_eye"]`: the picker offers both eye sockets on a species the item supports and refuses on any other. Cyberware items don't need entries in any species spec: the game's replacement organs (cybernetic heart, eyes, ears, jaw) use `organ_name` and carry their own `organ_spec`. Augments (items with `augment_organs`, such as the cybernetic tail and arm) do not use this picker; they mount at their `augment_anchor`, or at their `augment_container` when no anchor is set.

Multi-slot capacity (Doctor Octopus arms — installing multiple instances of the same organ type into augmented anatomy) is future work and will need a `state.organs` → `state.slots` schema change. It plugs into the same `target_display_locations` declaration without rework.
