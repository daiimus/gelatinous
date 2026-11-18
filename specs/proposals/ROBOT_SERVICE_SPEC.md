# Robot Service — the same hands, different words

Servicing a robot is the same act as operating on a person: the same
charting UI, the same steps, the same hit locations. Only the words a
player reads change, by the patient's species. Supplies and instruments
are gated by species too, so a unit can only be put right with machine
supplies at the bench.

**Depends on:** `world/anatomy/species.py` (`_derive_robot`),
`world/anatomy/organ_descriptions.py`, `commands/CmdOperate.py`,
`world/medical/*`
**Related:** #2261 (the bench and its three keepers),
`SECURITY_UNIT_LIFECYCLE_SPEC` (#2255)

---

## 1. The principle

A secbot is human-shaped on purpose — antenna ears, a jaw, two hands.
So servicing one is the same act as operating on a person, performed by
somebody with the same charting UI, the same steps, and the same hit
locations. **Nothing about the mechanics should fork.** What should
differ is the vocabulary: you do not suture a robot.

That makes this a NAMING and VERB problem sitting on top of a medical
system that already works, not an anatomy rewrite.

## 2. The robot species

`_derive_robot(human)` in `species.py` gives a robot:

* **amber hydraulic fluid** in place of blood, "visually distinct so a
  mixed pool reads as a mixture"
* **`infection_immune`** — "machines don't culture biological
  infection", the species-level analogue of an inorganic graft
* **`ROBOT_ORGAN_DURABILITY`** — every component tougher
* **a decay track that is not rot**: deactivated → inert chassis →
  wrecked chassis → stripped frame, with part and organ prefixes to
  match ("fried robot {organ}", "salvaged robot {organ}")

`factory_fit_comms` seats the transceiver in an **ear / antenna**
augment organ, which is the human-shaped-machine idea working.

So a unit bleeds amber, cannot go septic, and its heart looks like a
power core.

## 3. Organ labels and descriptions

**Organ identity is the dict KEY.** What a player reads is resolved by
species.

**Labels.** `robot["organ_display"]` in `_derive_robot`
(`world/anatomy/species.py`) maps 28 organs to machine labels:
`brain` → processor core, `heart` → power core, `left_kidney` → left
coolant filter, `liver` → fluid reclaimer, `left_femur` → left thigh
strut, `cervical_spine` → neck servo column. `get_organ_display_name(name,
species)` resolves them. Every surface that shows an organ goes through
it: the operate chart (`charts.py`), and the organ lists in
`CmdOperate`, `CmdMedical` and `CmdSurgical`. So a mechanic charting a
job picks *power core* from the list, and the prose beneath describes a
power core.

**Descriptions.** `ORGAN_DESCRIPTIONS_ROBOT` reworks 28 organs. It is
built by `_expand()` from `_ROBOT_SINGLES` and `_ROBOT_PAIRS`, turning
each pair into a left and a right. A live unit carries 30 organs; 28 have a machine
description and a machine label. The two that do not are the augments
`comms_module` and `integrated_shotgun_module`, which are machine-named
already.

| key | what you actually see |
|---|---|
| brain | a sealed processor core, status LEDs cycling |
| heart | a heavy power core, humming with a reciprocating pulse |
| tongue | a supple vocal modulator |
| liver, stomach, nose, jaw, spine, pelvis | likewise machine-read |

## 4. The operate chart and its verbs

**Organs and locations.** `render_step_summary` in
`world/medical/charts.py` takes an optional `species` and resolves
organs through the SAME `get_organ_display_name` that `CmdMedical` and
`CmdSurgical` use, so the chart cannot drift from the readout printed
beside it. Locations go through `get_species_location_display`. Item
keys deliberately do NOT translate: they are already the words a player
sees. `_humanize()` is used only for item keys. The argument is
optional, so a caller that does not pass it keeps working.

**Verbs.** `_SPECIES_VERBS` in `charts.py`: on a chassis `incise` reads
*cut into*, `harvest` *pull*, `install` *seat*, `amputate` *shear off*,
`suture` *seal*. It is a partial override, so any verb without an entry
keeps its organic word. Same chart, same flow, same Roman-numeral step
list. Running prose uses a matching table, `_SPECIES_GERUNDS`
(*sealing*, *pulling*, *shearing off*), through `gerund_for`; the
standalone surgical commands in `CmdSurgical.py` call it from the same
module (#2278). `bandage` also answers to `patch`, the machine word for
the same act.

Same chart, same keys, same resolvers — only the words move:

    human                        robot
    incise chest                 cut into chest
    harvest heart                pull power core
    harvest left kidney          pull left coolant filter
    install power core in chest  seat power core in chest
    suture chest                 seal chest

## 5. Why keys must not change

Tempting to rename `heart` to `power_core` in the data. Don't:

* hit locations, wound tables, severed parts and the harvest/appraisal
  paths all key off organ names, and the junkyard salvager's appraisal
  is coming for exactly these. (The spec once named the Ripper's chrome
  appraisal here. Corrected 2026-09-14: robots are robots, not chrome;
  owner 2026-09-14: the Ripper refuses robots.)
* `_derive_robot` deep-copies the human table, so the two stay
  structurally identical for free — that is the whole reason a robot is
  operable at all
* a synthetic humanoid already renames by presentation without renaming
  keys, and it works

Keys never change, so damage, hit locations, severed parts, harvesting
and every existing test keep working untouched.

Rename what people READ. Never what the system JOINS on.

## 6. Consequences worth wanting

* **The mechanic's shift becomes legible.** #2261 gives her a bench and
  units to rack; this gives her something to actually do to them, in
  words that fit.
* **Salvage reads right.** A stripped frame yields a power core and a
  vocal modulator, not a heart and a tongue — which is what the junkyard
  **salvager** wants (`SECURITY_UNIT_LIFECYCLE_SPEC`; owner 2026-09-14:
  the Ripper refuses robots).
* **Repair becomes real.** A downed unit is carried to the recovery
  bay, the Secure Corridor where the bench stands (#2255, #2282), and
  recovering it means nothing until somebody there can put it back
  together (§8.1).

## 7. Supplies — the other half of repair

Charting a job is only half of it. The other half is what you put in
your hands. Robots carry human-shaped medical state, so without a gate
a secbot could be bandaged, given a painkiller, and transfused with a
blood bag, and all of it would work. `serves_species` is that gate: the
organic articles refuse a chassis.

The vocabulary is `medical_type`, carried on every item. Sorted by
whether a machine could possibly benefit:

| type | item | on a machine |
|---|---|---|
| `tourniquet` | tourniquet | **works as-is** — clamping a line stops amber fluid as well as blood |
| `fracture_treatment` | medical splint | translates — a strut brace |
| `blood_restoration` | blood bag | translates — a hydraulic charge |
| `wound_care` | gauze bandages | translates — sealant patches |
| `organ_repair` | surgical sealant | translates — a conformal coating |
| `surgical_treatment` | surgical kit | translates — a tool roll |
| `pain_relief` | painkiller | **refuse** — nothing to hurt |
| `cigarette` | pain relief cigarette | **refuse** — nothing to hurt |
| `anesthetic` | anesthetic gas | **refuse** — nothing to sedate |
| `oxygen` | oxygen tank | **refuse** — nothing breathing |
| `antiseptic` | antiseptic spray | **refuse** — `infection_immune` already makes it pointless |
| `healing_acceleration` | stimpak | **refuse** — biology, not repair |
| `vapor`, `herb` | inhaler, herb | **refuse** |

**Refusing is the interesting half.** If a first aid kit fixes a
secbot, the bench has no reason to exist and neither do its three
keepers. A unit that can only be put right by somebody with the right
supplies at the right bench is what makes #2261 a job rather than a
costume.

**The gate.** `serves_species(item, target)` in `world/medical/utils.py`
is checked in `check_medical_requirements` — the one method all six
treatment verbs (inject / apply / bandage / eat / drink / inhale) route
through, so the gate cannot be live on one verb and absent on another
(#2268).

**Shape:** items declare who they serve — a `serves` set, or the
inverse `not_for` — checked in the same apply path that asks
`is_medical_item`. Untagged items keep working on a person. On a
chassis an untagged item is judged by its `medical_type`, and only a
tourniquet passes.

The reason for that fallback: `serves` / `not_for` are PROTOTYPE
attributes, so they only reach items spawned after they were authored.
Dressings already lying around the colony declare nothing. Judging
undeclared stock by `medical_type` on a chassis catches them, and only
genuinely shared articles pass. This tightens only the machine side;
undeclared stock used on a person behaves exactly as before, which is
what keeps the change additive.

**The machine articles.** Five: hydraulic charge, sealant patches,
strut brace, conformal coating (all Boiler Run, #2268), and `TOOL_ROLL`
— "tool roll", `medical_type` `surgical_treatment`, `serves: ["robot"]`
— with `SURGICAL_KIT` carrying the matching `not_for: ["robot"]`
(#2270). The tourniquet declares nothing and so serves both.
Robot-side supplies are ordinary prototypes with the machine
`medical_type`s, stocked at the bench by `restock_mechanic` from
`MECHANIC_PAR` (§8.2), not from the clinic's `PAR` (`GAUZE_BANDAGES`,
`TOURNIQUET`, `PAINKILLER`).

**Instruments are gated the same way.** `find_surgical_kit(caller,
target)` in `world/medical/utils.py` accepts only instruments that
serve the patient's species, so `operate` and the standalone surgical
commands need a tool roll on a chassis and a surgical kit on a person,
and `instruments_wanted` names the one that is missing (#2278).

**Watch the synthetic humanoid.** It is organic-presenting and
people-shaped; it should take the human kit. This gate keys on species,
not on "is it a person", and those are different questions.

## 8. The clinic is the model

Owner, 2026-08-24: *"This should all really work the same as the
doctors and the clinic but for robots."* Laid against each other:

| the clinic | the bench |
|---|---|
| `health` need, `clinic` shape — the walking wounded self-deliver | `health` need, `clinic` shape, looking for the `repair` advertiser: a damaged unit walks to the bench, but nothing there repairs it (§8.1) |
| `treatment` advertiser (the billing terminal) | `maintenance` (wear) and `repair` (damage) advertisers on the bench, both staffed: no keeper, no service (#2261, #2262) |
| an AutoDoc to lie in | the charging rack, or its own cradle |
| doctors on three shifts | Marisol, Tuck, Halina (#2261) |
| `restock_medic` keeps PAR supplies at post | `restock_mechanic` keeps `MECHANIC_PAR` supplies at the bench |
| billing — triage free, healing costs | open |

### 8.1 A damaged unit seeks repair (#2266)

The robot profile in `world/souls/needs.py` carries `health` beside
`charge`, `maintenance` and `safety`. Wear is not damage: without a
`health` need, a secbot could take a shotgun blast, keep patrolling on
a wrecked chassis, and turn up at the bench a week later for a routine
service.

The need has the same shape the humans use. A damaged unit walks itself
to the bench: its `health` need is shaped `clinic`, and `clinic_service`
in `world/souls/needs.py` sends a machine to the `repair` advertiser,
exactly as the walking wounded self-deliver, so the mechanic's queue
fills for the right reason.

📋 UNBUILT (no issue): the `treat` step in `world/souls/jobs.py` still
looks for somebody standing the `doctor` job and applies the clinic's
bandage, so at the bench it faults "no doctor on the floor" and nothing
repairs the unit.

### 8.2 Supplies at the post (#2266, kit #2268)

`MECHANIC_PAR` is the machine kit, not the clinic's par list: a
painkiller is no use to something with no nociception, and the organic
articles refuse a chassis outright (§7), so a mechanic holding clinic
supplies would hold supplies that bounce off every patient she has.

`restock_medic` keeps a clinic's medic stocked to `PAR` from anchored
stock. `restock_mechanic` in `world/director/medical.py` does the same
for the bench keeper, to `MECHANIC_PAR`: 2 sealant patches, 2
tourniquets, 2 conformal coatings, 1 strut brace. `_work_mechanic` in
`world/souls/salience.py` (`ROLE_WORK["mechanic"]`) calls it each beat
the keeper is at the post, beside the racking behaviour. The kit holds
no tool roll and no hydraulic charge.

### 8.3 Synthetics get their own tier, later

Owner: *"Synths should also have their own equivalent tbh but that's
not a priority right now."*

Deliberately deferred, and the reason is worth writing down: a
synthetic humanoid is organic-presenting and people-shaped, so it takes
the HUMAN kit and that is not wrong — merely coarse. It already has its
own organ labels (`synth["organ_display"]` in `species.py`: `heart`
reads *vat-heart*) and its own descriptions
(`ORGAN_DESCRIPTIONS_SYNTH`); it still takes the human verbs and the
human supplies. Its own tier would add verbs and supplies, in the same
species-keyed tables this spec uses. Nothing here should make that
harder: the tables are keyed by species precisely so a third column
costs a data entry rather than a redesign.

## 9. Not decided

* **Does a mechanic use `operate`, or a re-verbed alias?** Same command
  with species-aware wording is less to maintain; a separate `service`
  verb reads better on the tin and duplicates a large menu.
  There is no `service` command: a mechanic uses `operate`, which words
  each step for the patient's species. Not decided.
* **Do human surgeons work on robots and vice versa?** Skill-gating is
  not modelled. Instruments are: a chassis needs a tool roll and a
  person a surgical kit (`find_surgical_kit`), so who can work on whom
  follows what they carry.
* **Does the vocabulary follow the SPECIES or the PATIENT'S state?** A
  synthetic humanoid is people-shaped and organic-presenting; a robot
  is not. The table is per-species, so this mostly answers itself.
* **Band.** For a human, critical `health` outranks duty. A unit that
  limps back to the bench mid-shift instead of holding a scene is
  probably correct, and is the owner's call when it lands.
* **Billing at the bench.** The clinic bills (triage free, healing
  costs); for the bench it is open.
* **The bench keeper's kit.** Should `MECHANIC_PAR` hold only carried
  consumables, as the clinic's par list does, or should the keeper also
  get the tool roll and hydraulic charge (or a clinic-style draw on
  demand) so it can operate on a chassis or restore its fluid? This
  matters only once a keeper can operate (see the first item).
