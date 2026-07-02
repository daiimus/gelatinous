# Robot Species & MOB Spec — Mechanical Bodies, Control Modes, and the Police MOB

> **Status:** 📋 Proposal — not implemented. Designs **robots** as a
> fully-inorganic **species** (the next rung on the shipped `synthetic_humanoid`
> pattern + the existing `inorganic` organ machinery), plus the **control modes**
> that animate them (autonomous-deterministic, autonomous-LLM, PC remote-control)
> and the **police MOB** as the showcase — our **first MOB NPC**, and the first
> concrete consumer of `NPC_DISPATCH_AND_SIMULATION_SPEC` (LEO response) and
> `STEALTH_AND_DETECTION_SPEC` (the deterministic awareness/hunt loop). The
> **species/anatomy is buildable now**; the MOB behaviour and remote-control are
> gated on those specced-but-unbuilt systems.

---

## 1 · Intent

We want machines in the world: some **piloted by players** (a drone, a proxy
body), some **autonomous NPCs**. The first real use is **police** — a security
robot that patrols, notices trouble, challenges, and escalates, deterministically
and cheaply (no LLM). Robots are also the cleanest possible **first MOB**: a
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
  "deactivated synth / inert chassis / stripped frame").
* The **`inorganic` organ flag** is live across the medical stack — the
  inorganic-organ filter (`world/medical/core.py`, #516), the cyberware-status
  readout, the **inorganic severed-part prose path**
  (`get_severed_part_description(..., inorganic=True)`), "synthetics don't go
  septic" (`world/medical/procedures.py`), and "cobalt fluid; mechanical
  stillness rather than a final breath" death messaging
  (`world/medical/medical_messages.py`).

A robot is therefore **`_derive_robot(...)`** — the synthetic pattern taken all
the way to fully mechanical. (Open question §8: derive from `synthetic_humanoid`
to inherit no-rot/infection-immune/durability, or from `human` directly.)

### 3.1 · Capacity-organ remap (components, not organs)

Keep the **capacity framework** (so shooting a sensor cluster or shearing an
actuator still resolves through existing combat/severance) — just remap the
organs to components and rename:

| Human organ → capacity | Robot component | Capacity |
|---|---|---|
| brain → consciousness | **CPU / processor core** | consciousness (a **vital**) |
| heart → blood_pumping | **power core / battery** | power (the second **vital**) |
| eyes → sight | **optical sensors** | sight |
| ears → hearing | **audio sensors** | hearing |
| limbs → moving / manipulation | **actuators / manipulators** | moving / manipulation |
| jaw+tongue → talking | **vocalizer** | talking |
| lungs → breathing | *(dropped)* | — |
| kidneys → blood_filtration | *(dropped)* | — |

* **All components flagged `inorganic`** → reuses the medical filter, the
  inorganic severed prose, the cyberware-status readout, no-sepsis.
* **Death = capacity-derived, already.** Destroy the **CPU** (consciousness → 0)
  or the **power core** (the blood_pumping-slot vital → 0) and the existing
  capacity-death model deactivates the unit; the "mechanical stillness" death
  messaging is already authored.
* **Fluid:** robots leak **hydraulic/coolant fluid** for flavour (visually
  distinct pools, like cobalt does), but the bleed-to-death/infection course is
  suppressed (`infection_immune`); the vital threat is component HP, not blood
  level. (Open question §8: keep a fluid-loss analog or go fully bloodless.)
* **No rot** → decay names become salvage states: *deactivated unit → inert
  chassis → stripped frame / scrapped hulk* (mirror the synth decay override).

### 3.2 · Repair, not heal

Organic medical commands gate on living tissue; robots use **repair** — the
heal-analog (weld a frame member, swap a fried sensor, hot-swap the power core).
Much of the routing already exists (the `inorganic` filter keeps organic
treatment from applying); the **new** piece is a small repair verb/flow
(field-repair vs. a workbench), reserved as a build step. Component swap also
means robots are the natural home for **salvage** (a stripped frame yields parts).

### 3.3 · What's reused vs. new

| Reused (shipped) | New (this spec) |
|---|---|
| Species framework, `_derive_*` pattern, `inorganic` flag, no-sepsis, mechanical-death messaging, capacity-derived death, severance/longdesc/decay routing | The `robot` species definition (component remap + names), the repair verb, salvage, control modes (§4), the police MOB (§5) |

The anatomy is **mostly assembly of shipped parts** — which is why it's buildable
now, ahead of the dispatch/awareness systems the MOB needs.

---

## 4 · Control modes

The species is inert until something drives it. Three modes, same body:

* **Autonomous — deterministic (the police MOB, §5).** A hardcoded behaviour
  state machine fed by the **stealth awareness meter** and the **dispatch
  director**. **No LLM** — cheap, scalable, the right fit for patrolling units.
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
> **Patrol** and **Detect** steps below remain ahead: Detect specifies the
> stealth **awareness meter** (`STEALTH_AND_DETECTION_SPEC` §4, unbuilt) —
> the shipped high-confidence *watch cycle* is an interim stand-in the
> awareness meter will subsume. *Escalate/Restrain* stay sequenced behind
> the trust gate, as below.

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
  bot *is* the deterministic AI that spec was built to showcase.
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
* **Dispatch backup** — escalation raises a `WorldEvent` so more units converge
  (alert propagation), and a downed bot is itself an event.
* **Lethality / jurisdiction** — non-lethal by default (deterrence, restraint);
  jurisdiction is a `dispatch` role scope. Lethal force tuned conservatively.

Because every step reads an existing system, the police bot is **integration
glue, not new mechanics** — the proof that the world-sim primitives compose.

---

## 6 · Integration map

| System | Relationship |
|---|---|
| **Species / anatomy** (`SPECIES_AUTHORING`, `world/anatomy`) | `robot` species via `_derive_robot`; `inorganic` components; capacity-death; repair/salvage. |
| **Dispatch** (`NPC_DISPATCH_AND_SIMULATION_SPEC`) | The police MOB is its first consumer — patrol routines, LEO response, alert propagation, materialization/LOD. |
| **Stealth** (`STEALTH_AND_DETECTION_SPEC`) | The bot's deterministic awareness meter drives detect→challenge→pursue; the showcase for the non-LLM hunt. |
| **Coordinates** (`SPATIAL_COORDINATE_SYSTEM_SPEC`) | Patrol beats, pursuit pathfinding, last-known-position search. |
| **Trust** (`TRUST_AND_CONSENT_SPEC`) | Lawful restraint — a bot must subdue a conscious citizen before acting; the concrete "authority NPC" case. |
| **Phase / net** (`PHASE_LAYER_SPEC`) | **Hacking seam:** a robot is a prime target for net intrusion (a decker seizes/blinds a police bot) — a cross-phase causal bridge (net→meat). Reserved. |
| **Identity** (`IDENTITY_RECOGNITION_SPEC`) | A bot has an sdesc / serial identity; citizens recognise "unit 47" via the normal recognition path. |
| **LLM** (`LLM_GAMEMASTER_SPEC`) | Optional control mode for *character* bots; never required for police units. |

---

## 7 · Build ladder

| Phase | Scope | Depends on |
|---|---|---|
| **1 — Robot species** | `_derive_robot` (component remap, names, inorganic, no-rot, fluid, decay/salvage names); a spawnable chassis prototype | Shipped species framework — **buildable now** |
| **2 — Simple autonomous bot** | A stationary/short-patrol NPC with no dispatch (sanity test of the body + basic behaviour) | Phase 1 |
| **3 — Repair & salvage** | Field/workbench repair verb; stripped-frame salvage | Phase 1 |
| **4 — Police MOB** | The §5 behaviour state machine | Dispatch + stealth-awareness (specced, unbuilt) |
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
* **Power as a resource.** Is the power core just a vital HP pool, or also a
  *charge* that depletes (a bot needs recharging)? Charge adds logistics
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
