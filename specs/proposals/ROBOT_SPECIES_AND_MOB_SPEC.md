# Robot Species & MOB Spec — Mechanical Bodies, Control Modes, and the Police MOB

Robots are a fully-inorganic **species**: the next rung on the
`synthetic_humanoid` pattern plus the `inorganic` organ machinery. This spec
covers the robot body, the **control modes** that animate it
(autonomous-deterministic, autonomous-LLM, PC remote-control), and the
**police MOB** as the showcase — the first MOB NPC, and the first concrete
consumer of `NPC_DISPATCH_AND_SIMULATION_SPEC` (LEO response) and
`STEALTH_AND_DETECTION_SPEC` (the deterministic awareness/hunt loop).

---

## 1 · Intent

We want machines in the world: some **piloted by players** (a drone, a proxy
body), some **autonomous NPCs**. The first real use is **police** — a security
robot that patrols, notices trouble, challenges, and escalates, deterministically
and cheaply (no LLM in those steps; the unit talks through one). Robots are also
the cleanest possible **first MOB**: a mechanical body sidesteps the full organic
medical model and leans on infrastructure the game already has for synthetics and
cyberware.

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

## 3 · The robot species

Robots ride the **species framework** (`SPECIES_AUTHORING.md`,
`world/anatomy/species.py`) so combat, severance, longdesc, decay, and corpse
prose all behave **without renderer changes** — the entire point of that system.
They extend the synthetic pattern:

* `SPECIES_DEFINITIONS["synthetic_humanoid"]` is **derived from human** via
  `_derive_synthetic_humanoid(base)` (deepcopy + targeted overrides: cobalt
  blood, `infection_immune`, durability multiplier, no-rot decay names →
  "deactivated synth / inert synth chassis / stripped synth frame").
* The **`inorganic` organ flag** runs across the medical stack — the
  inorganic-organ filter (`world/medical/core.py`, #516), the cyberware-status
  readout, the **inorganic severed-part prose path**
  (`get_severed_part_description(..., inorganic=True)`), "synthetics don't go
  septic" (`world/medical/procedures.py`), and "cobalt fluid; mechanical
  stillness rather than a final breath" death messaging
  (`world/medical/medical_messages.py`).

A robot is **`_derive_robot(...)`** (`world/anatomy/species.py`) — the synthetic
pattern taken all the way to fully mechanical. It derives from `human`
(deepcopy + overrides), parallel to `_derive_synthetic_humanoid`; there is no
shared inorganic helper (see Not decided).

### 3.1 · Capacity-organ remap (components, not organs)

The **capacity framework** stays (so shooting a sensor cluster or shearing an
actuator still resolves through existing combat/severance); the organs are
remapped to components and renamed:

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
  distinct pools, like cobalt does). A robot can die of fluid loss the same
  way a human dies of blood loss; only infection is suppressed
  (`infection_immune`). Whether to keep fluid-loss death or go fully bloodless
  is open (see Not decided).
* **No rot** → decay names are salvage states: *deactivated robot → inert
  robot chassis → wrecked robot chassis → stripped robot frame*
  (`decay_corpse_names` in `_derive_robot`).

### 3.2 · Repair, not heal

Organic medical commands gate on living tissue; robots use **repair** — the
heal-analog (weld a frame member, swap a fried sensor, hot-swap the power core).
The `inorganic` filter keeps organic treatment from applying.

* **Repair as a service.** Chassis repair is a **service**: see the sibling
  `ROBOT_SERVICE_SPEC` (#2262/#2266), the species→door mapping
  (`world/souls/needs.py` `CLINIC_SERVICE = {"robot": "repair"}`), the
  mechanic's bench kit and `restock_mechanic` (`world/director/medical.py`),
  and species-gated supplies that refuse organic kit on a chassis
  (`world/medical/utils.py` `serves_species`).
* **No chassis repair verb.** `commands/CmdArmor.py`'s `repair` covers armor
  and breachable structure, not a chassis. A small repair verb/flow
  (field-repair vs. a workbench) is 📋 UNBUILT (no issue).
* **Salvage.** Component swap makes robots the natural home for **salvage** (a
  stripped frame yields parts). A destroyed security unit's shotgun arm module
  is stripped and the chassis is kept in the scrapyard (`strip_and_junk`,
  `world/director/disposal.py`); a general salvage verb is 📋 UNBUILT (no issue).

### 3.3 · What's reused vs. new

| Reused | New (this spec) |
|---|---|
| Species framework, `_derive_*` pattern, no-sepsis (`infection_immune`), capacity-derived death, severance/longdesc/decay routing | The `robot` species definition (component names, amber fluid, decay names, its own death, bleed and severed-part lines, `longdesc_flex_nouns`), the police MOB (§5); 📋 UNBUILT (no issue): per-component `inorganic` flags, the repair verb, general salvage, PC remote-control (§4), hacking, the grapple/cuff rung |

The anatomy is **mostly assembly of parts the game already had**.

---

## 4 · Control modes

The species is inert until something drives it. Three modes, same body:

* **Autonomous — deterministic (the police MOB, §5).** A hardcoded behaviour
  state machine fed by the **stealth awareness meter** and the **dispatch
  director**. Detention, hunt and force never wait on a model. Each unit is
  still an `LLMNpc` with `SECURITY_BOT_PERSONA` for conversation, and it
  carries a soul (robot needs profile) (`spawn_secbot`,
  `world/director/population.py`).
* **Autonomous — LLM.** A character robot (a quirky android bartender, a
  companion unit) via the existing `LLMNpcMixin` / `llm_driven`, acting through
  **real in-game commands** like every other LLM NPC (the standing mandate).
* **PC remote-control (pilot a robot).** 📋 UNBUILT (no issue); waits on the
  parked possession pipeline. See Unbuilt.

Control mode is a **property of the instance, not the species** — the same
chassis prototype can be spawned deterministic, LLM, or pilotable.

---

## 5 · The police MOB

The first MOB, and the first thing that exercises the world-sim stack
end-to-end — deterministically. Because every step reads an existing system,
the police bot is **integration glue, not new mechanics** — the proof that the
world-sim primitives compose.

**Behaviour state machine** (hardcoded; consumes the specced systems):

```
Patrol (routine) ─▶ Detect ─▶ Challenge ─▶ Escalate ─▶ Restrain / Engage
   ▲ (dispatch       │(stealth   │           │            │
   │  routine +      │ awareness)│(verbal)   │(force)     │(combat/grapple)
   │  coord patrol)  │           │           │            │
   └─────────────────┴── give up / stand down ◀───────────┘
```

The reactive path keyed off a reported crime runs dispatch → route → arrive →
**BOLO scan-and-match** → challenge/question → watch → return-to-post
(#853/#863/#867, `world/director/security.py`).

### 5.1 · Patrol

A `dispatch` routine moving a beat over the **coordinate** graph
(`SPATIAL_COORDINATE_SYSTEM_SPEC` pathfinder). The unit walks its
`db.patrol_beat` (`world/director/routines.py`).

### 5.2 · Detect

The **stealth awareness meter** (`STEALTH_AND_DETECTION_SPEC` §4,
`world/stealth.py`): a crime/threat/hidden suspect raises awareness →
suspicious → searching, driving the deterministic hunt (`tick_hunt`,
`world/director/hunt.py`). The bot *is* the deterministic AI that spec was
built to showcase. The high-confidence *watch cycle* (`watch_once`,
`security.py`) runs alongside the hunt; the hunt does not replace it.

A hunt needs cause (`_has_cause`, `world/director/hunt.py`, recorded there as
decided 2026-07-03): the target is on the wanted record, or an unresolved
incident is hot where they were sensed or where the unit stands. Without
cause, a hidden person is noticed but never hunted, and a pardon mid-hunt
stands the unit down silently (`_engage`).

### 5.3 · Challenge / Escalate

Verbal warning → show of force → restraint, via **real commands**.

**Escalation ladder & combat order-of-operations (design resolved
2026-06-30).** How an NPC responds under pressure is **hardcoded, never
LLM-dependent** — combat timing can't wait on a model; the LLM only talks. The
security ladder, each rung a real command:

1. **Aim — innocuous detainment.** On a confirmed match the unit levels its
   sidearm and takes an **aim lock** — the existing aim system pins the
   subject in place (they cannot move), with the **flee contest as the
   counterplay**: breaking the lock and running is allowed, and fleeing an aim
   lock is itself information. No touch, no consent question — detainment by
   threat posture. The unit lowers its weapon when it stands down.
   **Robots don't wield weapons — they mount them:** secbots are
   factory-fitted with the `ROBOT_SHOTGUN_MODULE` (an `integrated_weapon`
   forearm module seated as a standalone augment organ, the tail pattern).
   Same augment backend as human chrome (`SHOTGUN_MODULE`), species-true
   presentation — a subsystem on the frame's bill of materials, not grafted
   chrome. `/shotgun` deploys the `ROBOT_ARM_GUN`, which carries its **own
   robot-voiced combat bank** (`robot_riot_gun.py`, #885/#895 — house-style,
   `{hit_location}`-grounded; distinct from the human chrome's
   `cybernetic_shotgun`). Deterministic lines address people as
   **"Colonist"** (never sdesc/name, #888), and targeting resolves via the
   suspect's sdesc through the identity-aware pipeline (#890 — real keys are
   builder-gated).
2. **Grapple — lawful restraint.** 📋 UNBUILT (no issue): an uncooperative or
   fleeing subject is subdued by grapple/cuff — the conscious-and-unrestrained
   contest per `TRUST_AND_CONSENT_SPEC`. No grapple or cuff path exists in
   `world/director/security.py`. See 5.4.
3. **Combat — force.** **Violence in progress in front of the unit authorizes
   force** — a confirmed suspect currently in combat (on arrival, or turning
   violent under watch) skips detainment: the unit warns once, deploys the arm
   gun (`/shotgun`), and attacks (all real commands; the combat handler owns
   the fight from there). A unit **never walks home mid-fight** (the watch
   loop defers while it is in combat). Force *initiation* beyond
   violence-in-progress (fleeing-felon directives, lethality tuning) is still
   ahead (see Unbuilt).

The **general NPC combat order-of-operations** (all NPCs, not just security)
is the same requirement one level down — hardcoded reflexes for
**wield-on-threat** (draw a carried weapon when combat starts), **range
discipline** (advance/retreat to the wielded weapon's engagement range), and
**respond/flee thresholds**. The #616 auto-prioritizer already picks among
in-hand weapons per engagement. The reflex layer is 📋 UNBUILT —
the next behaviour layer after the security ladder proves the shape.

### 5.4 · Restrain — the trust seam

A police bot grabbing a **conscious, unrestrained, non-consenting citizen**
must route through `TRUST_AND_CONSENT_SPEC`: it cannot act freely on an
able-to-resist target, so it must **lawfully subdue first** (grapple/cuff).
This is the reserved "authority NPC" seam from `NPC_DISPATCH_AND_SIMULATION_SPEC`
§6 ("Third-party action safety", which reserves this seam: "a security bot
restrains … NPC-initiated actions targeting able-to-resist players are subject
to the same consent rules … Reserve the seam now") and `TRUST_AND_CONSENT_SPEC`
§6 ("NPC participation — self-action only"). The police MOB is what makes it
concrete.

The trust gate exists (`world/consent.py`: `is_restrained`, `can_contest`,
`has_trust`, `check_consent`; `commands/CmdTrust.py`), so coercive force no
longer waits on it; the grapple/cuff rung is simply 📋 UNBUILT (no issue).

### 5.5 · Dispatch backup and casualties

* When a hunt reacquires its target, the unit challenges, radios for backup,
  raises a `disturbance` `WorldEvent`, and sets every other security unit
  searching at the sighting room (`_engage`, `propagate_alert`,
  `world/director/hunt.py`).
* A unit critically damaged on a call radios a mayday once and holds the scene
  (`_mayday`, `security.py`).
* A destroyed unit raises no event: it goes silent and its call closes as
  `unit_lost` (`security_death`).
* A unit that finds a downed unit carries it home (`recover_casualty`,
  `world/director/medical.py`), and the wreck's shotgun arm module is stripped
  and the chassis left in the scrapyard (`strip_and_junk`,
  `world/director/disposal.py`).

### 5.6 · Lethality / jurisdiction

A matched subject who is not fighting gets an aim lock, and violence in
progress gets the arm gun and `attack` (`_engage`, `security.py`). The design
intent here was non-lethal by default (deterrence, restraint), jurisdiction as
a `dispatch` role scope, and lethal force tuned conservatively; a non-lethal
mode and jurisdiction scoping are 📋 UNBUILT (not decided).

### 5.7 · Calls and intel

* A face on the force-wide wanted record is challenged even when it has
  nothing to do with the call (`_scan_wanted`).
* A unit's sightings stay local until it returns to post and syncs them
  (`sync_bot_intel` in `security_completion`).
* A phoned-in call is closed on the call ledger as unfounded, detained,
  checked or unit_lost, and the unit radios the outcome (`close_call_for`).
* Units are spawned and respawned at the security base with a built-in
  transceiver (`spawn_secbot`, `factory_fit_comms`,
  `world/director/population.py`).

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

## 7 · Unbuilt

* **Pruning breathing and blood_filtration** from the robot — 📋 UNBUILT (no
  issue), deferred in `_derive_robot` (§3.1).
* **Per-component `inorganic` flags** — 📋 UNBUILT (no issue) (§3.1).
* **Repair verb** — field/workbench repair — 📋 UNBUILT (no issue) (§3.2).
* **General salvage** — stripped-frame salvage verb — 📋 UNBUILT (no issue)
  (§3.2).
* **Grapple/cuff rung** of the police ladder — 📋 UNBUILT (no issue) (§5.3,
  §5.4).
* **Force initiation beyond violence-in-progress** (fleeing-felon directives,
  lethality tuning) — still ahead (§5.3).
* **General NPC combat order-of-operations** (wield-on-threat, range
  discipline, respond/flee thresholds) — 📋 UNBUILT; the next
  behaviour layer after the security ladder proves the shape (§5.3).
* **Non-lethal mode and jurisdiction scoping** — 📋 UNBUILT (not decided)
  (§5.6).
* **Recognisable serial identity** — 📋 UNBUILT (no issue) (§6).
* **PC remote-control (pilot a robot)** — 📋 UNBUILT (no issue). A player
  drives a robot as a drone/proxy. Depends on the **parked possession
  pipeline**. Its shape mirrors the phase two-body model (`PHASE_LAYER_SPEC`
  §5.3): the pilot's **real body is elsewhere and vulnerable** while they're
  "in" the robot; losing the link (jammed, destroyed bot, EMP) snaps them
  back. The control link is the seam; the body↔pilot vulnerability is the
  tension.
* **Hacking** — 📋 UNBUILT (no issue). Net intrusion seizes/blinds a bot.
  Depends on phase/net (specced, unbuilt).

The repair verb and general salvage need only the robot species and can be
built on today's foundations; PC remote-control and hacking are consumers of
the world-sim stack and the parked possession work.

---

## 8 · Not decided

* **Derive from `synthetic_humanoid` or `human`?** From synth inherits no-rot /
  infection-immune / durability for free; from human is a flatter base. **Lean:**
  a shared `_derive_inorganic(base)` helper that synth and robot both call, with
  robot adding the all-`inorganic` + component-rename layer.
* **Fluid model.** Keep fluid-loss death, or go fully bloodless? Hydraulic/coolant
  leak for flavour vs. fully bloodless. **Lean:** flavour leak, no
  bleed-out/infection; component HP is the threat.
* **Repair verb scope.** Field-repair vs. workbench; who can repair (skill/tool
  gating, consistent with parked stats — lean tool-gated).
* **Power as a resource.** A souled robot already has a depleting `charge`
  need and a `maintenance` need (`PROFILES["robot"]`, `world/souls/needs.py`);
  the power core organ is only an HP vital. Is the power core just a vital HP
  pool, or also a *charge* that depletes (a bot needs recharging)? Charge adds
  logistics (downtime, charging stations) — reserve unless wanted.
* **Remote-control vulnerability & lag.** The pilot's exposed body, link-loss
  behaviour, and whether piloting has perceptual latency. Tied to the possession
  pipeline.
* **Police escalation tuning.** Non-lethal default, force thresholds, jurisdiction
  scope — gameplay-tune, avoid an oppressive or trivial police presence.
* **Hacking depth.** How much a decker can do to a seized bot (blind it, walk it,
  weaponise it) — a phase/net cross-causation design, reserved.
* **Salvage economy.** A stripped frame yielding parts touches the item/economy
  layer; keep v1 cosmetic until the economy exists.

---

## 9 · Related documents

`SPECIES_AUTHORING.md` · `ROBOT_SERVICE_SPEC` · `NPC_DISPATCH_AND_SIMULATION_SPEC`
· `STEALTH_AND_DETECTION_SPEC` · `SPATIAL_COORDINATE_SYSTEM_SPEC` ·
`TRUST_AND_CONSENT_SPEC` · `PHASE_LAYER_SPEC` · `IDENTITY_RECOGNITION_SPEC` ·
`LLM_GAMEMASTER_SPEC`
