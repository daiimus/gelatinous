# Robot Species & MOB Spec — Mechanical Bodies, Control Modes, and the Police MOB

> Designs **robots** as a
> fully-inorganic **species** (the next rung on the shipped `synthetic_humanoid`
> pattern + the existing `inorganic` organ machinery), plus the **control modes**
> that animate them (autonomous-deterministic, autonomous-LLM, PC remote-control)
> and the **police MOB** as the showcase — our **first MOB NPC**, and the first
> concrete consumer of `NPC_DISPATCH_AND_SIMULATION_SPEC` (LEO response) and
> `STEALTH_AND_DETECTION_SPEC` (the deterministic awareness/hunt loop). PC
> remote-control is 📋 UNBUILT (no issue) and waits on the parked possession
> pipeline.

---

## 1 · Intent

We want machines in the world: some **piloted by players** (a drone, a proxy
body), some **autonomous NPCs**. The first real use is **police** — a security
robot that patrols, notices trouble, challenges, and escalates, deterministically
and cheaply (no LLM in those steps; the unit talks through one). Robots are also the cleanest possible **first MOB**: a
mechanical body sidesteps the full organic medical model and leans on
infrastructure the game already shipped for synthetics and cyberware.

---

## 2 · Three orthogonal axes

A robot is a **body** wearing a **control mode** running a **role**. Keeping these
separate is the whole design:

| Axis | What it is | Examples |
|---|---|---|
| **Body** (§3) | the robot *species* — anatomy, damage, repair, decay | humanoid security chassis |
| **Control** (§4) | what drives it | deterministic AI · LLM · PC remote-pilot |
| **Role** (§5) | the behaviour it runs | police MOB · industrial · companion bot |

The species is **control- and role-agnostic**: the same chassis can be a
deterministic police unit, an LLM-driven character, or a player's piloted drone.

---

## 3 · The robot species (the buildable core)

Robots ride the **species framework** (`SPECIES_AUTHORING.md`,
`world/anatomy/species.py`) so combat, severance, longdesc, decay, and corpse
prose all behave **without renderer changes** — the entire point of that system.
And they extend a pattern that's **already shipped**:

* `SPECIES_DEFINITIONS["synthetic_humanoid"]` exists, **derived from human** via
  `_derive_synthetic_humanoid(base)` (deepcopy + targeted overrides: cobalt
  blood, `infection_immune`, durability multiplier, no-rot decay names →
  "deactivated synth / inert synth chassis / stripped synth frame").
* The **`inorganic` organ flag** is live across the medical stack — the
  inorganic-organ filter (`world/medical/core.py`, #516), the cyberware-status
  readout, the **inorganic severed-part prose path**
  (`get_severed_part_description(..., inorganic=True)`), "synthetics don't go
  septic" (`world/medical/procedures.py`), and "cobalt fluid; mechanical
  stillness rather than a final breath" death messaging
  (`world/medical/medical_messages.py`).

A robot is therefore **`_derive_robot(...)`** — the synthetic pattern taken all
the way to fully mechanical. It derives from `human` (deepcopy + overrides),
parallel to `_derive_synthetic_humanoid`; there is no shared inorganic helper
(see §8).

### 3.1 · Capacity-organ remap (components, not organs)

Keep the **capacity framework** (so shooting a sensor cluster or shearing an
actuator still resolves through existing combat/severance) — just remap the
organs to components and rename:

| Human organ → capacity | Robot component | Capacity |
|---|---|---|
| brain → consciousness, brain_integrity | **processor core** | consciousness; brain_integrity (a **vital**) |
| heart → blood_pumping | **power core** | blood_pumping (a **vital**) |
| eyes → sight | **optical sensors** | sight |
| ears → hearing | **audio sensors** | hearing |
| limbs → moving / manipulation | **actuators / manipulators** | moving / manipulation |
| jaw+tongue → talking | **mandible servo, vocal modulator** | talking |
| lungs → breathing | **cooling units** | breathing (a **vital**) |
| stomach, liver → digestion | **fuel cell, fluid reclaimer** | digestion (a **vital**) |
| kidneys → blood_filtration | **coolant filters** | blood_filtration |

The organs and capacities are human's, unchanged; only the names differ
(`organ_display` in `_derive_robot`). Pruning breathing and blood_filtration
is 📋 UNBUILT (no issue), deferred in `_derive_robot`.

* **Per-component `inorganic` flags** are 📋 UNBUILT (no issue), deliberately
  deferred in `_derive_robot`: `is_augment_organ` (`world/medical/core.py`)
  would treat inorganic components as installed chrome. No-sepsis comes from
  the species `infection_immune` flag, and severed-part prose from the robot
  table in `world/anatomy/severed_parts.py`.
* **Death = capacity-derived.** Destroying the processor core
  (brain_integrity → 0) kills, with the revival window every brain death has;
  destroying the power core (blood_pumping), both cooling units (breathing),
  the fuel cell and fluid reclaimer together (digestion), or the neck servo
  column (neck_integrity) also kills (`LETHAL_CAPACITY_NAMES`,
  `world/medical/constants.py`). Consciousness 0 is a knockout, not death.
  The robot has its own amber death lines (`"robot"` in
  `world/medical/medical_messages.py`).
* **Fluid:** robots leak **hydraulic/coolant fluid** for flavour (visually
  distinct pools, like cobalt does). As built, a robot can die of fluid loss
  the same way a human dies of blood loss; only infection is suppressed
  (`infection_immune`). (Open question §8: keep fluid-loss death or go fully
  bloodless.)
* **No rot** → decay names become salvage states: *deactivated robot → inert
  robot chassis → wrecked robot chassis → stripped robot frame*
  (`decay_corpse_names` in `_derive_robot`).

### 3.2 · Repair, not heal

Organic medical commands gate on living tissue; robots use **repair** — the
heal-analog (weld a frame member, swap a fried sensor, hot-swap the power core).
Much of the routing already exists (the `inorganic` filter keeps organic
treatment from applying); the **new** piece is a small repair verb/flow
(field-repair vs. a workbench), reserved as a build step. **Note 2026-09-12:**
still accurate that no chassis repair *verb* exists — `commands/CmdArmor.py`'s
`repair` covers armor and breachable structure, not a chassis. But the
capability landed in a different shape, as a **service**: see the sibling
`ROBOT_SERVICE_SPEC` (✅ BUILT, #2262/#2266), the species→door mapping
(`world/souls/needs.py` `CLINIC_SERVICE = {"robot": "repair"}`), the
mechanic's bench kit and `restock_mechanic` (`world/director/medical.py`), and
species-gated supplies that refuse organic kit on a chassis
(`world/medical/utils.py` `serves_species`). Component swap also
means robots are the natural home for **salvage** (a stripped frame yields parts).
Today a destroyed security unit's shotgun arm module is stripped and the
chassis is kept in the scrapyard (`strip_and_junk`,
`world/director/disposal.py`); a general salvage verb is 📋 UNBUILT (no issue).

### 3.3 · What's reused vs. new

| Reused (shipped) | New (this spec) |
|---|---|
| Species framework, `_derive_*` pattern, no-sepsis (`infection_immune`), capacity-derived death, severance/longdesc/decay routing | The `robot` species definition (component names, amber fluid, decay names, its own death, bleed and severed-part lines, `longdesc_flex_nouns`), the police MOB (§5); 📋 UNBUILT (no issue): per-component `inorganic` flags, the repair verb, general salvage, PC remote-control (§4), hacking, the grapple/cuff rung |

The anatomy is **mostly assembly of parts the game already had**.

---

## 4 · Control modes

The species is inert until something drives it. Three modes, same body:

* **Autonomous — deterministic (the police MOB, §5).** A hardcoded behaviour
  state machine fed by the **stealth awareness meter** and the **dispatch
  director**. Detention, hunt and force never wait on a model. As built, each
  unit is still an `LLMNpc` with `SECURITY_BOT_PERSONA` for conversation, and
  it carries a soul (robot needs profile) (`spawn_secbot`,
  `world/director/population.py`).
* **Autonomous — LLM.** A character robot (a quirky android bartender, a
  companion unit) via the existing `LLMNpcMixin` / `llm_driven`, acting through
  **real in-game commands** like every other LLM NPC (the standing mandate).
* **PC remote-control (pilot a robot).** A player drives a robot as a drone/proxy.
  This depends on the **parked possession pipeline** — reserved, not built here.
  Its shape mirrors the phase two-body model (`PHASE_LAYER_SPEC` §5.3): the
  pilot's **real body is elsewhere and vulnerable** while they're "in" the
  robot; losing the link (jammed, destroyed bot, EMP) snaps them back. The
  control link is the seam; the body↔pilot vulnerability is the tension.

Control mode is a **property of the instance, not the species** — the same
chassis prototype can be spawned deterministic, LLM, or pilotable.

---

## 5 · The police MOB (the showcase)

The first MOB, and the first thing that exercises the new world-sim stack
end-to-end — deterministically.

> **Status note (2026-06-30):** the **reactive half is live** — dispatch →
> route → arrive → **BOLO scan-and-match** → challenge/question →
> watch → return-to-post (#853/#863/#867, `world/director/security.py`).
> That covers the *Challenge* step keyed off a reported crime. The
> **Patrol** step walks the unit's `db.patrol_beat` (`world/director/routines.py`).
> The **Detect** step is the stealth **awareness meter** (`world/stealth.py`)
> driving the deterministic hunt (`tick_hunt`, `world/director/hunt.py`). The
> high-confidence *watch cycle* (`watch_once`, `security.py`) runs alongside
> the hunt; it was not replaced. The grapple/cuff *Restrain* rung is
> 📋 UNBUILT (no issue), as below.

**Behaviour state machine** (hardcoded; consumes the specced systems):

```
Patrol (routine) ─▶ Detect ─▶ Challenge ─▶ Escalate ─▶ Restrain / Engage
   ▲ (dispatch       │(stealth   │           │            │
   │  routine +      │ awareness)│(verbal)   │(force)     │(combat/grapple)
   │  coord patrol)  │           │           │            │
   └─────────────────┴── give up / stand down ◀───────────┘
```

* **Patrol** — a `dispatch` routine moving a beat over the **coordinate**
  graph (`SPATIAL_COORDINATE_SYSTEM_SPEC` pathfinder).
* **Detect** — the **stealth awareness meter** (`STEALTH_AND_DETECTION_SPEC` §4):
  a crime/threat/hidden suspect raises awareness → suspicious → searching. The
  bot *is* the deterministic AI that spec was built to showcase. A hunt needs
  cause (`_has_cause`, `world/director/hunt.py`, recorded there as decided
  2026-07-03): the target is on the wanted record, or an unresolved incident is
  hot where they were sensed or where the unit stands. Without cause, a hidden
  person is noticed but never hunted, and a pardon mid-hunt stands the unit
  down silently (`_engage`).
* **Challenge / Escalate** — verbal warning → show of force → restraint, via
  **real commands**.

  **Escalation ladder & combat order-of-operations (DESIGN RESOLVED
  2026-06-30; aim rung SHIPPED).** How an NPC responds under pressure is
  **hardcoded, never LLM-dependent** — combat timing can't wait on a model;
  the LLM only talks. The security ladder, each rung a real command:

  1. **Aim — innocuous detainment** *(✅ shipped)*: on a confirmed match the
     unit levels its sidearm and takes an **aim lock** — the existing aim
     system pins the subject in place (they cannot move), with the **flee
     contest as the counterplay**: breaking the lock and running is allowed,
     and fleeing an aim lock is itself information. No touch, no consent
     question — detainment by threat posture. The unit lowers its weapon
     when it stands down. **Robots don't wield weapons — they mount them:**
     secbots are factory-fitted with the `ROBOT_SHOTGUN_MODULE` (an
     `integrated_weapon` forearm module seated as a standalone augment
     organ, the tail pattern). Same augment backend as human chrome
     (`SHOTGUN_MODULE`), species-true presentation — a subsystem on the
     frame's bill of materials, not grafted chrome. `/shotgun` deploys the
     `ROBOT_ARM_GUN`, which carries its **own robot-voiced combat bank**
     (`robot_riot_gun.py`, #885/#895 — house-style, `{hit_location}`-
     grounded; distinct from the human chrome's `cybernetic_shotgun`).
     Deterministic lines address people as **"Colonist"** (never sdesc/
     name, #888), and targeting resolves via the suspect's sdesc through
     the identity-aware pipeline (#890 — real keys are builder-gated).
  2. **Grapple — lawful restraint** *(⬜, sequenced behind the trust gate)*:
     an uncooperative or fleeing subject is subdued by grapple/cuff — the
     conscious-and-unrestrained contest per `TRUST_AND_CONSENT_SPEC`.
  3. **Combat — force** *(🟡 engage-on-violence SHIPPED)*: **violence in
     progress in front of the unit authorizes force** — a confirmed suspect
     currently in combat (on arrival, or turning violent under watch) skips
     detainment: the unit warns once, deploys the arm gun (`/shotgun`), and
     attacks (all real commands; the combat handler owns the fight from
     there). A unit **never walks home mid-fight** (the watch loop defers
     while it is in combat). Still ahead: force *initiation* beyond
     violence-in-progress (fleeing-felon directives, lethality tuning).

  The **general NPC combat order-of-operations** (all NPCs, not just
  security) is the same requirement one level down — hardcoded reflexes for:
  **wield-on-threat** (draw a carried weapon when combat starts), **range
  discipline** (advance/retreat to the wielded weapon's engagement range;
  the #616 auto-prioritizer already picks among in-hand weapons per
  engagement), and **respond/flee thresholds**. ⬜ — the next behaviour
  layer after the security ladder proves the shape.
* **Restrain — the trust seam.** A police bot grabbing a **conscious,
  unrestrained, non-consenting citizen** must route through
  `TRUST_AND_CONSENT_SPEC`: it cannot act freely on an able-to-resist target, so
  it must **lawfully subdue first** (grapple/cuff). This is the exact
  reserved "authority NPC" seam from the dispatch spec (§6) and trust spec (§6) —
  the police MOB is what makes it concrete. Sequence coercive force *after* that
  gate exists.

  > **Note 2026-09-12 — the sequencing is past tense now.** The trust gate
  > shipped 2026-07-03: `world/consent.py` (`is_restrained`, `can_contest`,
  > `has_trust`, `check_consent`) + `commands/CmdTrust.py`, and
  > `TRUST_AND_CONSENT_SPEC` is ✅ SHIPPED IN FULL, re-verified against code
  > 2026-08-02. So coercive force is no longer *waiting* on the gate — the
  > grapple/cuff rung above is simply unbuilt (no grapple or cuff path exists
  > in `world/director/security.py`). Both §6 citations in this sentence were
  > re-checked and are **correct**: `NPC_DISPATCH_AND_SIMULATION_SPEC` §6
  > closes with "Third-party action safety", which reserves this exact seam
  > ("a security bot restrains … NPC-initiated actions targeting
  > able-to-resist players are subject to the same consent rules … Reserve
  > the seam now"), and `TRUST_AND_CONSENT_SPEC` §6 is "NPC participation —
  > self-action only".
* **Dispatch backup** — when a hunt reacquires its target, the unit challenges,
  radios for backup, raises a `disturbance` `WorldEvent`, and sets every other
  security unit searching at the sighting room (`_engage`, `propagate_alert`,
  `world/director/hunt.py`). A unit critically damaged on a call radios a
  mayday once and holds the scene (`_mayday`, `security.py`). A destroyed unit
  raises no event: it goes silent and its call closes as `unit_lost`
  (`security_death`). A unit that finds a downed unit carries it home
  (`recover_casualty`, `world/director/medical.py`), and the wreck's shotgun
  arm module is stripped and the chassis left in the scrapyard
  (`strip_and_junk`, `world/director/disposal.py`).
* **Lethality / jurisdiction** — as built, a matched subject who is not
  fighting gets an aim lock, and violence in progress gets the arm gun and
  `attack` (`_engage`, `security.py`). The design intent here was non-lethal
  by default (deterrence, restraint), jurisdiction as a `dispatch` role scope,
  and lethal force tuned conservatively; a non-lethal mode and jurisdiction
  scoping are 📋 UNBUILT (not decided).
* **Calls and intel** — a face on the force-wide wanted record is challenged
  even when it has nothing to do with the call (`_scan_wanted`). A unit's
  sightings stay local until it returns to post and syncs them
  (`sync_bot_intel` in `security_completion`). A phoned-in call is closed on
  the call ledger as unfounded, detained, checked or unit_lost, and the unit
  radios the outcome (`close_call_for`). Units are spawned and respawned at the
  security base with a built-in transceiver (`spawn_secbot`,
  `factory_fit_comms`, `world/director/population.py`).

Because every step reads an existing system, the police bot is **integration
glue, not new mechanics** — the proof that the world-sim primitives compose.

---

## 6 · Integration map

| System | Relationship |
|---|---|
| **Species / anatomy** (`SPECIES_AUTHORING`, `world/anatomy`) | `robot` species via `_derive_robot`; capacity-death; per-component `inorganic` flags, a repair verb and general salvage are 📋 UNBUILT (no issue). |
| **Dispatch** (`NPC_DISPATCH_AND_SIMULATION_SPEC`) | The police MOB is its first consumer — patrol routines, LEO response, alert propagation, materialization/LOD. |
| **Stealth** (`STEALTH_AND_DETECTION_SPEC`) | The bot's deterministic awareness meter drives detect→challenge→pursue; the showcase for the non-LLM hunt. |
| **Coordinates** (`SPATIAL_COORDINATE_SYSTEM_SPEC`) | Patrol beats, pursuit pathfinding, last-known-position search. |
| **Trust** (`TRUST_AND_CONSENT_SPEC`) | Lawful restraint — a bot must subdue a conscious citizen before acting; the concrete "authority NPC" case. |
| **Phase / net** (`PHASE_LAYER_SPEC`) | **Hacking seam:** a robot is a prime target for net intrusion (a decker seizes/blinds a police bot) — a cross-phase causal bridge (net→meat). Reserved. |
| **Identity** (`IDENTITY_RECOGNITION_SPEC`) | A unit is keyed by finish ("a <finish> security robot", `ROBOT_FINISHES`) and calls itself "Unit <id>" (its database id) on the radio. A recognisable serial identity is 📋 UNBUILT (no issue). |
| **LLM** (`LLM_GAMEMASTER_SPEC`) | Optional control mode for *character* bots. Police units talk through it (`SECURITY_BOT_PERSONA`); their detention, hunt and force never depend on it. |

---

## 7 · Build ladder

| Phase | Scope | Depends on |
|---|---|---|
| **1 — Robot species** | `_derive_robot` (component remap, names, inorganic, no-rot, fluid, decay/salvage names); a spawnable chassis prototype | Shipped species framework — **buildable now** |
| **2 — Simple autonomous bot** | A stationary/short-patrol NPC with no dispatch (sanity test of the body + basic behaviour) | Phase 1 |
| **3 — Repair & salvage** | Field/workbench repair verb; stripped-frame salvage | Phase 1 |
| **4 — Police MOB** | The §5 behaviour state machine; its grapple/cuff rung is 📋 UNBUILT (no issue) | Dispatch + stealth-awareness |
| **5 — PC remote-control** | Pilot a robot; the two-body link | Parked possession pipeline |
| **6 — Hacking** | Net intrusion seizes/blinds a bot | Phase/net (specced, unbuilt) |

Phases 1–3 ship on today's foundations; 4–6 are the consumers of the new
world-sim stack and the parked possession work.

---

## 8 · Risks & open questions

* **Derive from `synthetic_humanoid` or `human`?** From synth inherits no-rot /
  infection-immune / durability for free; from human is a flatter base. **Lean:**
  a shared `_derive_inorganic(base)` helper that synth and robot both call, with
  robot adding the all-`inorganic` + component-rename layer.
* **Fluid model.** Hydraulic/coolant leak for flavour vs. fully bloodless. **Lean:**
  flavour leak, no bleed-out/infection; component HP is the threat.
* **Repair verb scope.** Field-repair vs. workbench; who can repair (skill/tool
  gating, consistent with parked stats — lean tool-gated).
* **Power as a resource.** A souled robot already has a depleting `charge`
  need and a `maintenance` need (`PROFILES["robot"]`, `world/souls/needs.py`);
  the power core organ is only an HP vital. Is the power core just a vital HP
  pool, or also a *charge* that depletes (a bot needs recharging)? Charge adds logistics
  (downtime, charging stations) — reserve unless wanted.
* **Remote-control vulnerability & lag.** The pilot's exposed body, link-loss
  behaviour, and whether piloting has perceptual latency. Tied to the possession
  pipeline.
* **Police escalation tuning.** Non-lethal default, force thresholds, jurisdiction
  scope — gameplay-tune, avoid an oppressive or trivial police presence.
* **Hacking depth.** How much a decker can do to a seized bot (blind it, walk it,
  weaponise it) — a phase/net cross-causation design, reserved.
* **Salvage economy.** A stripped frame yielding parts touches the item/economy
  layer; keep v1 cosmetic until the economy exists.
