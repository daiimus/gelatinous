# Robot Service — the same hands, different words

**Status:** proposed 2026-08-24, NOT built (#2262)
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

## 7. Open questions

* **Does a mechanic use `operate`, or a re-verbed alias?** Same command
  with species-aware wording is less to maintain; a separate `service`
  verb reads better on the tin and duplicates a large menu.
* **Do human surgeons work on robots and vice versa?** Skill-gating is
  not modelled; today anyone with the command can open anything.
* **Does the vocabulary follow the SPECIES or the PATIENT'S state?** A
  synthetic humanoid is people-shaped and organic-presenting; a robot
  is not. The table is per-species, so this mostly answers itself.
