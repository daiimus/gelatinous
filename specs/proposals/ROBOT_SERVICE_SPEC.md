# Robot Service — the same hands, different words

**Status:** partly built. §8.1 + §8.2 shipped (#2266); §7 supplies
shipped (#2268). §4 labels/verbs and the remaining organ DESCRIPTIONS
are open on #2262.

**Correction, 2026-08-24:** §4.1 below asked for a per-species organ
label table. **It already existed** — `robot["organ_display"]` at
`world/anatomy/species.py:1315` maps 28 organs (`brain` → processor
core, `heart` → power core, `left_femur` → left thigh strut), resolved
by `get_organ_display_name(name, species)` with tests. `CmdMedical` and
`CmdSurgical` already use it. This spec was written without reading
that first, and the table was described as missing when it was not.
The REAL gap is narrower: `world/medical/charts.py` renders operate
steps through a species-blind `_humanize()`, so the chart is the one
surface still saying *heart*.
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

## 2. What already exists (more than expected)

`_derive_robot(human)` in `species.py`:

* **amber hydraulic fluid** in place of blood, "visually distinct so a
  mixed pool reads as a mixture"
* **`infection_immune`** — "machines don't culture biological
  infection", the species-level analogue of an inorganic graft
* **`ROBOT_ORGAN_DURABILITY`** — every component tougher
* **a decay track that is not rot**: deactivated → inert chassis →
  wrecked chassis → stripped frame, with part and organ prefixes to
  match ("fried robot {organ}", "salvaged robot {organ}")

`ORGAN_DESCRIPTIONS_ROBOT` already reworks **nine** organs where it
matters most:

| key | what you actually see |
|---|---|
| brain | a sealed processor core, status LEDs cycling |
| heart | a heavy power core, humming with a reciprocating pulse |
| tongue | a supple vocal modulator |
| liver, stomach, nose, jaw, spine, pelvis | likewise machine-read |

And `factory_fit_comms` already seats the transceiver in an **ear /
antenna** augment organ, which is exactly the human-shaped-machine
idea working.

So the *fiction* is largely there. A unit bleeds amber, cannot go
septic, and its heart looks like a power core.

## 3. Where the human word still leaks

**The label, not the description.** Organ identity is the dict KEY, and
the UI humanises it directly — `charts.py` and `CmdOperate` both do
`value.replace("_", " ")`. So a mechanic charting a job picks from a
list that says *heart*, *liver*, *left kidney*, while the prose beneath
describes a power core. The description is machine; the noun is meat.

**Thirty of thirty-nine organs have no robot description at all** —
only nine are covered, so kidneys, lungs, femurs, humeri, metacarpals
and the rest still read as biology in full.

**The verbs.** `incise / harvest / install / suture` are surgical.
A mechanic *cuts in*, *pulls a module*, *seats* it, and *closes the
panel*.

## 4. The change

1. **A per-species organ LABEL table**, beside the description table it
   already has. `heart → power core`, `left_kidney → left coolant
   exchanger`, `liver → fluid reclaimer`. Keys never change, so damage,
   hit locations, severed parts, harvesting and every existing test
   keep working untouched.
2. **One label helper**, used everywhere `replace("_", " ")` is used
   today — `charts.py`, `CmdOperate`, severed parts, corpse rendering.
   That single seam is what makes the rest cheap.
3. **A per-species VERB table** over the same procedure steps. Same
   chart, same flow, same Roman-numeral step list; `suture` reads
   `seal panel` on a chassis.
4. **Finish the description table** — the remaining thirty organs.

## 5. Why keys must not change

Tempting to rename `heart` to `power_core` in the data. Don't:

* hit locations, wound tables, severed parts and the harvest/appraisal
  paths all key off organ names, and the Ripper's chrome appraisal is
  coming for exactly these
* `_derive_robot` deep-copies the human table, so the two stay
  structurally identical for free — that is the whole reason a robot is
  operable at all today
* a synthetic humanoid already renames by presentation without renaming
  keys, and it works

Rename what people READ. Never what the system JOINS on.

## 6. Consequences worth wanting

* **The mechanic's shift becomes legible.** #2261 gives her a bench and
  units to rack; this gives her something to actually do to them, in
  words that fit.
* **Salvage reads right.** A stripped frame yields a power core and a
  vocal modulator, not a heart and a tongue — which is what the Ripper
  and the junkyard both want (`SECURITY_UNIT_LIFECYCLE_SPEC`).
* **Repair becomes real**, which is the dependency `#2255` is blocked
  on: recovering a downed unit means nothing until somebody can put it
  back together.

## 7. Supplies — the other half of repair

Charting a job is only half of it. The other half is what you put in
your hands, and **nothing today gates a medical item by species.**
Robots carry human-shaped medical state, so a secbot can be bandaged,
given a painkiller, and transfused with a blood bag — and all of it
works.

The existing vocabulary is `medical_type`, already carried on every
item. Sorting it by whether a machine could possibly benefit:

| type | item | on a machine |
|---|---|---|
| `tourniquet` | tourniquet | **works as-is** — clamping a line stops amber fluid as well as blood |
| `fracture_treatment` | medical splint | translates — a strut brace |
| `blood_restoration` | blood bag | translates — a hydraulic/coolant charge |
| `wound_care` | gauze bandages | translates — a sealant patch |
| `organ_repair` | surgical sealant | translates — conformal coating |
| `surgical_treatment` | surgical kit | translates — a tool roll |
| `pain_relief` | painkiller, cigarette | **refuse** — nothing to hurt |
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

**SHIPPED (#2268).** `serves_species(item, target)` in
`world/medical/utils.py`, checked in `check_medical_requirements` —
the one method all six treatment verbs (inject / apply / bandage /
eat / drink / inhale) already route through, so the gate cannot be
live on one verb and absent on another. Four machine articles added:
hydraulic charge, sealant patches, strut brace, conformal coating, all
Boiler Run. The tourniquet declares nothing and so serves both.

**Left universal deliberately:** the surgical kit. A scalpel is a
scalpel — it is instruments rather than a consumable, and gating it
risked blocking robot surgery for no fictional gain.

**Shape:** items declare who they serve — a `serves` set, or the
inverse `not_for` — checked in the same apply path that already asks
`is_medical_item`. Untagged items keep working on everyone, so nothing
existing breaks; only the refusals are new. Robot-side supplies are
then ordinary prototypes with the machine `medical_type`s, stocked at
the bench the way `restock_medic` stocks a clinic (`PAR` is currently
`GAUZE_BANDAGES`, `TOURNIQUET`, `PAINKILLER` — two of which a mechanic
would never reach for).

**Watch the synthetic humanoid.** It is organic-presenting and
people-shaped; it should take the human kit. This gate keys on species,
not on "is it a person", and those are different questions.

## 8. The clinic is the model

Owner, 2026-08-24: *"This should all really work the same as the
doctors and the clinic but for robots."* Laid against what exists:

| the clinic | the bench |
|---|---|
| `health` need, `clinic` shape — the walking wounded self-deliver | **MISSING** |
| `treatment` advertiser (the billing terminal) | `maintenance` advertiser ✅ staffed (#2261) |
| an AutoDoc to lie in | the charging rack, or its own cradle |
| doctors on three shifts | Marisol, Tuck, Halina ✅ (#2261) |
| `restock_medic` keeps PAR supplies at post | **MISSING** |
| billing — triage free, healing costs | open |

### 8.1 A damaged unit does not seek repair — SHIPPED (#2266)

The robot profile was `charge`, `maintenance`, `safety`. There is **no
`health`**, so nothing drives a damaged unit anywhere.

Consequence today: a secbot can take a shotgun blast, keep patrolling
on a wrecked chassis, and turn up at the bench a week later for a
routine service. The wear timer is the only thing that ever brings one
in, and wear is not damage.

The fix is the same shape the humans already use — a `health`-equivalent
need on the robot profile, shaped `clinic`, pointed at the bench. Then
a damaged unit self-delivers exactly as the walking wounded do, and the
mechanic's queue fills for the right reason.

Note the interaction with band: for a human, critical `health` outranks
duty. A unit that limps back to the bench mid-shift instead of holding
a scene is probably correct, and is the owner's call when it lands.

### 8.2 Supplies at the post — SHIPPED (#2266, kit corrected #2268)

Shipped first with the CLINIC's par list, which was wrong twice over:
a painkiller is no use to something with no nociception, and once §7
landed the organic articles refuse a chassis outright — so the
mechanic would have stood her shift holding supplies that bounce off
every patient she has. `MECHANIC_PAR` is now the machine kit.

`restock_medic` keeps a clinic's medic stocked to `PAR` from anchored
stock. The bench has no equivalent, so a mechanic has hands and no
parts. Same function, robot `medical_type`s, and it slots into
`ROLE_WORK["mechanic"]` beside the racking behaviour — the medic's
restock already lives in that registry (#2236), so this is one more
entry rather than a new mechanism.

### 8.3 Synthetics get their own tier, later

Owner: *"Synths should also have their own equivalent tbh but that's
not a priority right now."*

Deliberately deferred, and the reason is worth writing down: a
synthetic humanoid is organic-presenting and people-shaped, so it takes
the HUMAN kit today and that is not wrong — merely coarse. Its own
tier means its own labels, verbs and supplies, in the same three tables
this spec introduces. Nothing here should make that harder: the tables
are keyed by species precisely so a third column costs a data entry
rather than a redesign.

## 9. Open questions

* **Does a mechanic use `operate`, or a re-verbed alias?** Same command
  with species-aware wording is less to maintain; a separate `service`
  verb reads better on the tin and duplicates a large menu.
* **Do human surgeons work on robots and vice versa?** Skill-gating is
  not modelled; today anyone with the command can open anything.
* **Does the vocabulary follow the SPECIES or the PATIENT'S state?** A
  synthetic humanoid is people-shaped and organic-presenting; a robot
  is not. The table is per-species, so this mostly answers itself.
