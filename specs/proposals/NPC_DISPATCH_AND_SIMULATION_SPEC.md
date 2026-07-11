# NPC Dispatch & World Simulation Specification

> **Status:** 🟡 Proposal — **dispatch core SHIPPED & LIVE** (2026-06-27, #853);
> **RADIO REPORTS ROLL REAL UNITS (2026-07-11):** player traffic on 911MHz is classified by the civic lane's structured-verdict contract (constrained decoding, `world/director/radio_report.py`) and a CONFIRMED report raises a real `WorldEvent` — two-signal gate (report flag AND type enum agree), plain-code location resolution against room names (fallback: the caller's room), 120s scene debounce, severity one notch under witnessed crime. Caller UNVERIFIED by design: false reports drain the finite pool (swatting is a mechanic). NPC/witness traffic never re-classifies (no double dispatch). Failure at any layer = silence. **GROUNDED VOICE LANE (2026-07-11, user: 'Copy. Coffee. Units rolling.'): the lanes are SEQUENCED — the verdict classifies first, then the operator's reply gets the finding as [CONTEXT] (chatter→channel discipline / confirmed+dispatched→units announce themselves / held→do-not-claim), and `_clean_reply` carries a deterministic no-false-units backstop: any units-moving claim is struck unless dispatch actually moved units this turn. Exemplars retrained — she never announces units; units announce themselves.** **The receipt is the UNITS' voices (2026-07-11, user call — the console restating the operator's ack was an echo): each dispatched responder keys up its own staggered 'Unit <id> responding — <where>.' through the real `xmit` verb + comms organ (wrecked organ/downed unit = honest silence); the drained-pool 'No units available' stays dispatch's announcement.** **REACHABILITY GATE (2026-07-11, same arc): dispatch orders ARE radio traffic — `world.radio.hears_emergency_band` (comms organ or powered carried radio on 911MHz) gates BOTH `find_responders` and the console's availability count. A deafened unit (shot ear, snatched walkie) stands at post, never rolls, and drops off Petra's 'units on the line' — ear-sniping neutralizes without destroying. Open follow-on seam: range physics for the ORDER itself (mast-wrecked dispatch shouldn't reach cross-colony units; ride the breach arc).**
> remaining layers below. Designs the **director**: a hardcoded, deterministic
> world-simulation engine that manages the NPC population (spawn / despawn /
> routine / death) and **dispatches** them in response to world events — routing
> them through the spatial pathfinder. The LLM-NPC puppeting layer brings
> selected NPCs to life **only when a player is there to witness it and the
> moment is worth the cost.** Built on `SPATIAL_COORDINATE_SYSTEM_SPEC`
> (Phases 1–2 shipped: coordinate volume + A\* pathfinder).
>
> **Shipped (`world/director/`):** the dispatch core (#853): `travel_to`
> (pathfinder-driven movement via real exit commands), `WorldEvent` +
> `find_responders` (by `db.role`, nearest-by-travel) + `dispatch`
> (severity-scaled) + `@dispatch`. The **assignment lifecycle** (#863): en
> route → on-scene (role-keyed `ARRIVAL_HANDLERS`) → linger → return-to-post;
> committed responders skip other incidents (the finite pool is real);
> `@dispatch/status`. **Crime slice 1** (#867): `build_bolo`/`match_bolo` —
> the responder gets a perception-graded **BOLO** (apparent_uid + coarse
> silhouette), scans who it can *see* on scene, and acts on **tiered
> confidence** (high → challenge + watch cycle; low → question the lookalike —
> mistaken identity intended; blind bot scans nothing).
>
> **Identification design RESOLVED (§5.1, 2026-06-30); crime taxonomy + heat
> (§5.2, 2026-06-30).** Chain status: BOLO ✅ · tiered confidence ✅ (detain
> deferred to the trust gate) · combat auto-raise ✅ #871 (45s→witness window, per-scene debounce, crime-time BOLO) · witness spawn ✅ #873 (crowd-gated, interdictable, first flash-temp ephemeral; flees to cower via director travel #888) · base intel-sync ✅ #876 (per-bot sightings → force-wide wanted record only on return-to-post; latency window real; repeat-offender counts; @dispatch/wanted) · radio report ✅ (2026-07-05: NO magic radios left on the crime chain — witness calls ride a real walkie via wield/xmit (#1009/#1020); a caught theft routes through report_crime's crowd-gated witness instead of a raw raise_event; patrol wanted-flags and hunt challenges key the unit's comms organ on 911MHz (xmit fallback) before the deterministic raise — the security net is audible to anyone tuned in. Explosions stay direct: a detonation is its own broadcast)
> (`RADIO_COMMS_SPEC` drafted #859; magic placeholder until built) ·
> no-trace window ⬜. Population/identity presentation layer
> still open — see §10.

## 1 · Intent

We want the colony to feel **inhabited and reactive** without a builder
hand-scripting every life. A population of NPCs — civilians (flash-temp miners,
bartenders, companions, gangers) and authority (security robots, LEO
dispatchers) — should live on routines and **respond to events**: an assault
triggers a LEO response, a mining incident deploys a search-and-rescue crew, a
shift change sends a worker in for a drink. Gigs, tasks, and events for *players*
hang off the same machinery.

This is a **core hardcoded element** — a world simulation that runs whether or
not anyone is watching. The LLM NPC system (`LLM_GAMEMASTER_SPEC`) is the
**performance layer on top**: when the simulation puts a meaningful NPC in front
of a player, the director may hand that beat to the model. Most of the
simulation never touches the LLM at all.

Two layers, one engine:
* **Simulation / dispatch** — population lifecycle, routines, event response,
  traversal. Deterministic, always-on, cheap.
* **Tasks / gigs / events** — the player-facing hooks (the favor/gig loop) and
  the world-event triggers, both feeding the same dispatcher.

## 2 · Design stance — simulate deterministically, narrate selectively

The governing principle, because LLM time is the scarcest resource:

> **The simulation always runs on rules. The LLM is a camera light — switched on
> only when a player is present, the beat is salient, and budget allows.**

| Mode | When | Cost |
|---|---|---|
| **Abstract** | No player anywhere near (off-screen) | ~zero — state advances as data, NPCs need not even be instantiated (§3 LOD) |
| **Deterministic on-screen** | Player present, ordinary beat | cheap — real in-game commands with templated content (§6) |
| **LLM-narrated** | Player present **and** salient beat **and** within budget | expensive — gated hand-off to the model |

This is what makes the **NPC↔NPC problem** tractable. Two NPCs interacting
off-screen is pure data (or skipped). On-screen, they interact through a
**deterministic interaction vocabulary** (templated poses/says via real
commands) — the simulation visibly "does its thing" for free. The model is
spent only on the rare witnessed, high-salience exchange — never as the default
for NPC-to-NPC chatter. The existing bartender engagement gate (directed /
ambient / cooldown) is the seed of this idea; the director generalizes it to the
whole population with a shared budget.

**Mandate inherited from the LLM-NPC work:** every NPC action — dispatched,
routine, deterministic, or LLM-driven — executes through **real in-game
commands** (`execute_cmd`), never a Python backdoor. The director decides
*what an NPC does*; the NPC *does it* the same way a player would, respecting
command validation and messaging. (See `LLM_GAMEMASTER_SPEC`; this is a hard
rule.)

## 3 · Population & lifecycle

A **population registry** (`world/director/population.py`) is the census: who
exists, their role, home region, state, and whether they are persistent or
ephemeral.

* **Persistent NPCs** — named, durable citizens (Sable the bartender, Doctor
  Vance, companions). They have stable identity, recognition memory, voice.
* **Ephemeral / flash-temp NPCs** — spawned for a shift, a gig, or an event
  (a flash-temp mining crew, a LEO response squad) and **despawned** when the
  reason ends. The bulk of the visible population is ephemeral.

**Level-of-detail (LOD) — spawn-on-approach.** The director does **not**
instantiate the whole city. Off-screen population is **virtual** — a row of
state in the registry. When a player enters (or nears, via the coordinate
proximity query) a region, its due NPCs **materialize** as real objects; when
the last player leaves and a grace period passes, they **dematerialize** back to
state. This bounds object count and tick cost to where players actually are.

**Death & lifecycle monitoring.** The director subscribes to the medical/death
system (death-curtain hooks). An NPC death is itself a **world event** (§5): a
murder may summon LEO; a mining death may trigger S&R; a flash-temp's death just
updates the census and schedules cleanup. The director owns despawn, corpse
handling hand-off, and any respawn/replacement cadence — so the world neither
leaks corpses nor depopulates permanently.

## 4 · Roles & routines

Each NPC has a **role** defining its spawn rules, schedule, event
subscriptions, and jurisdiction. Roles are data-authored, not hardcoded per-NPC.

```python
@dataclass(frozen=True)
class Role:
    id: str                     # "miner", "bartender", "security_bot", "ganger"
    faction: str | None         # NPC-only factions (see growth direction)
    routine: str                # schedule key -> deterministic behavior
    responds_to: list[str]      # event types this role is dispatched for
    jurisdiction: str | None    # region/zone scoping for response eligibility
    persistence: str            # "persistent" | "ephemeral"
    llm_persona: str | None     # if set, eligible for LLM narration when salient
```

**Routines** are deterministic behavior — a state machine / lightweight behavior
tree driven by the time system and the NPC's role: a miner cycles shaft → break
→ home; a shift change routes a worker to the bar for a drink; a security bot
patrols a beat. Routines move NPCs via the **pathfinder** (§5 of the coordinate
spec) and act via real commands. No LLM required for any of it.

## 5 · The event bus & dispatch

The heart of "both layers."

**Events** (`world/director/events.py`) are typed, located, and weighted:

```python
@dataclass
class WorldEvent:
    type: str            # "assault", "mining_incident", "shift_change", "death", "gig"
    location: object      # a room (carries coordinates -> distance/routing)
    severity: int         # drives responder count & LLM salience
    source: object | None # instigator (a PC, an NPC, a system tick)
    payload: dict         # event-specific detail
```

Events are raised by the world: combat (assault), the mining system (incident),
the time system (shift change), the medical system (death), the gig system
(task posted). They land on a bus the **dispatcher** consumes.

**The dispatcher** (`world/director/dispatch.py`):

1. **Match** — find candidate responders by `role.responds_to`, `jurisdiction`,
   and **coordinate proximity** (`rooms_within` / straight-line distance).
2. **Select** — pick responder count from `severity`; nearest-first by travel
   path. Materialize a flash-temp squad if no standing responders exist (a LEO
   van rolls in; an S&R crew is deployed).
3. **Route** — A\* over the real exit graph (coordinate spec §5) toward the
   event; respects locks, warps, and collapsed tunnels automatically.
4. **Monitor** — track arrival, resolution, and casualties; a responder death
   re-enters the bus as a new event. *(Arrival tracking + role-keyed handlers
   ✅ #863; casualty-monitoring ⬜.)*
5. **Resolve** — on completion, return standing NPCs to routine; despawn the
   flash-temp squad after a grace period. *(Linger → return-to-post ✅ #863;
   flash-temp despawn ⬜ — the population layer.)*

*(Steps 1–3 shipped in #853 minus `jurisdiction` scoping and flash-temp
materialization, both ⬜ pending the population layer.)*

Dispatch is the bridge between the **simulation** (who exists, where, doing
what) and the **spatial system** (how they get there). It is fully
deterministic; the LLM enters only if step 4 puts a responder in front of a
player during a salient beat.

### 5.1 · Crime is an information problem — the chain (DESIGN RESOLVED 2026-06-30)

A responder must never be handed the perpetrator as an object reference — that
omniscience is the real "small-worlding." **The security force is a
bounded-rational agent: it knows only what was perceived, reported,
transmitted, and synced — and every link of that chain is attackable.**

```
crime happens
 → is anyone there to see it?         WITNESS — gated by crowd
   → witness spawns as a real NPC     interdictable (intimidate/bribe/harm/kill)
     → can they report it?            COMMS — radio; break the chain
       → what did they actually see?  BOLO — perception-graded, can mislead
         → does the force know yet?   INTEL — syncs at base, not instantly
           → can a bot act on it?     bounded attention, tiered confidence
```

Each link, and the play it creates:

* **Witnesses are gated by crowd, and are real.** Whether a crime *has* a
  witness derives from the room's **crowd** level (no crowd → no witness →
  no report). When there is one, the witness **spawns as an actual NPC** —
  so a PC can interdict them: intimidate, bribe, harm, or kill the witness
  before the report goes out. Multiple witnesses **corroborate** (sharpen the
  BOLO) or **conflict** — and witnesses **can mislead** (a false description
  sends the force after the wrong profile; manipulating witnesses is play).
* **Reports travel by radio** (`RADIO_COMMS_SPEC`, the colony's primary comms).
  No transmission → the force never learns. Disrupting comms is a first-class
  criminal avenue: snatch the walkie from a witness's hand, break the rooftop
  antenna, jam the band. Until radio ships, dispatch's report step is an
  acknowledged *magic placeholder*.
* **The BOLO is a perception-graded descriptor, not a handle.** What the event
  carries is *what witnesses saw*: a clear witness yields the perp's
  `apparent_uid` (the identity system's presentation hash); a poor/distant one
  yields only a coarse descriptor (build/height); one who *recognised* the perp
  yields a name. On scene, a responder **scans who it can currently perceive**
  (perception-gated — stealth/blindness apply) and matches against the BOLO.
  Consequences fall out of the identity system for free: **flight** (not
  present), **disguise/re-sleeve** (UID changes → BOLO stale), **blending**
  (a coarse descriptor matches many → ambiguity), **looking generic is cover**.
* **Mistaken identity is intended.** Matching yields a **confidence**, and
  action is **tiered**: high confidence → detain; low confidence → challenge /
  question / observe (friction, not instant injustice). A coarse BOLO can put
  an innocent lookalike in the hot seat — and a smart perp exploits that.
* **Intel is hybrid and syncs at base.** A bot's identifications are **per-bot**
  knowledge until it **returns to base and syncs**, only then joining the
  force-wide wanted record. The force knows your face *eventually*; a given bot
  still has to *see* you (per-bot perception always gates action). The sync
  latency is an exploitable window; the base is a meaningful place (and target).
  Repeat offenders accumulate a record keyed to `apparent_uid` — which a
  re-sleeve or disguise resets (a clean face costs something).
* **Attention & triage are bounded.** A responder continuously triages its
  assigned event against what it *perceives en route* — an armed individual, an
  active assault, graffiti-in-progress — by severity × immediacy × proximity.
  It can be **preempted / distracted** (bait play). At the force level,
  **capacity is finite** (a configured pool of security bots + deployment
  dynamics, later): multiple incidents force allocation, some go unanswered —
  **overwhelming the force is an intended heist tactic**.
* **The no-trace window.** A skilled criminal can render witnesses inert —
  *including security bots* (they are perceivers, not oracles) — before acting:
  gas, blackout, EMP. Ties to the cross-phase EMP seam (`PHASE_LAYER_SPEC` §9)
  and the robot chassis (an EMP'd bot saw nothing, reports nothing). No
  perceiver → no chain → no consequence. Reserved as a seam.

The colony feels large because information is **expensive, lossy, and
physical**. Scouting (crowd timing), violence (silence the witness), sabotage
(kill the comms), deception (disguise / false reports), speed (beat the sync),
and coordination (overwhelm the pool) are all valid ways to get away with it.

### 5.2 · Crime taxonomy & heat (DESIGN RESOLVED 2026-06-30)

**Crimes are mechanical acts, not declarations.** There is no "commit crime"
verb — a mugging *is* grapple+frisk+steal; shoplifting *is* a stealth-take from
a shop container; vandalism *is* the graffiti command. The crime layer
**instruments existing acts**: it classifies what happened, decides who noticed
(§5.1), and raises the event. Anything the systems permit, you can do — the
only question is whether you were *seen*.

| Crime | The act | Severity (1–5, tunable) | How the force learns |
|---|---|---|---|
| Shoplifting | stealth-take from a shop | 1 | often never; stocktake shrinkage later (no BOLO) |
| Vandalism | graffiti on property | 1 | witnessed-in-the-act only |
| Pickpocketing | `pickpocket` (tokens) | 1–2 | victim notices late/never; coarse BOLO |
| Mugging | threaten/grapple → frisk → steal | 2–3 | **the victim reports** (if alive, conscious, able) |
| Armed robbery | wielded weapon + take (shop/NPC) | 3–4 | victim + crowd witnesses; good BOLO |
| Assault | combat on an unwilling target | 3–4 | loud — crowd-gated witnesses |
| Murder | death | 5 | **discovered via the corpse** → forensic BOLO off `signature_at_death` (`world/forensics.py`, exists) |
| Sabotage | break antenna / infrastructure | 2–3 | discovered when the hole is noticed |

**Three report paths** (what actually varies per crime):
1. **Witnessed at commission** — the §5.1 chain as designed (loud crimes).
2. **Victim-reports** — the victim *is* the witness; everything in §5.1 applies
   to them (silence, snatch the walkie, intimidate). A mugging done right
   leaves a victim who *chooses* not to report.
3. **Discovered later** — quiet crimes raise events off the *evidence*:
   stocktake shrinkage (no BOLO), a found corpse (**forensic BOLO** — degraded,
   cold-trail), a district gone radio-dark. Note the grim emergent truth:
   unwitnessed murder is *quieter* than assault — finishing the job silences
   the best witness. Intended.

**NPC victims** (what makes mugging/robbery real):
* **Pockets** — civilians spawn with **100–500 tokens** (everything is priced
  at 0 today, so this sets the reference scale; worth mugging, not farming).
* **Reactions** — comply / flee / resist, **role-weighted for now** (a laborer
  complies, a ganger resists, a shopkeeper raises the alarm). Future: a
  **nature/demeanor/traits axis** on NPCs informs both these deterministic
  reactions *and* the LLM persona when one is puppeted — one personality
  substrate, two consumers.

  **✅ ESCALATION LADDER (shipped 2026-07-04):** reactions are stateful
  (`ndb.reaction_stage`), not a stateless one-shot — continued violence
  climbs: **comply → flee** (surrender answered with violence is off the
  table; the rung persists, so a beaten hawker never re-offers hands-up),
  **flee → resist when armed** (the *cornered rat*: a scavver denied an
  exit turns and draws; unarmed keeps retrying the run), **resist is
  terminal** (no re-reaction, no spam — the old form re-fired the same
  emote every swing). Dialogue is NEVER scripted: for LLM NPCs the attack +
  their own mechanical response is *observed into the action buffer*
  (combat informs the prompt; the model owns the words, no forced turn).

  **Decision (2026-07-04, closes the #1004 revert question):** melee
  **proximity is positional, not combat membership** — the orphan sweep
  keeps target/targeted-by/grapple/aim relationships only. An attacker who
  ever swung holds their victim via target-lock; the sole dissolve case is
  someone who closed distance but never attacked, and re-attacking simply
  re-forms combat. Watch item: yield-to-dissolve initiative resets (fix, if
  ever needed, is re-engage initiative carry-over — not
  proximity-as-membership).
* **The report step** — the victim runs the §5.1 witness pipeline on
  themselves: delay (the interdiction window), then report if able.

**Heat — the spatio-temporal crime map.** Crimes accumulate **heat** at their
coordinates over time (decaying), and heat **dictates patrol allocation**:
hot districts draw patrols, quiet ones thin out. Getting away with quiet crime
is consequence-*free for you* but raises district heat — the world responds to
patterns, not just incidents. **Except where it deliberately doesn't:** certain
areas are **purposefully under-patrolled due to special interests** — a
per-district patrol bias the heat system honors (gang arrangements, corporate
carve-outs). Corruption is data, not lore; discovering *which* districts are
cold-by-design is player knowledge worth having.

**Dependency:** mugging/shoplifting/pickpocketing need the **theft verbs**
(`steal`/`pickpocket`/frisk-reveal, `STEALTH_AND_DETECTION_SPEC` §6.2) —
specced, unbuilt; crime pulls them forward in the build order.

## 6 · Interaction & the LLM escalation gate

The hardest part, by your call, is **NPC↔NPC interaction** — and the answer is
to make the *default* free.

* **Deterministic interaction vocabulary** — templated exchanges keyed by the
  role pair + context, rendered through real `pose`/`say`/`emote` commands:
  two gangers posture; a miner orders from the bartender; a security bot
  challenges a loiterer. Cheap, on-brand, and visible. This is what "the
  simulation does its thing" looks like on-screen with zero model cost.
* **The escalation gate** — a single director-owned decision, generalizing the
  bartender's directed/ambient gate, that hands a beat to the LLM only when
  **all** hold:
  1. **Witnessed** — a player can perceive it (coordinate proximity +
     perception). No witness → never spend.
  2. **Salient** — `severity` / role significance clears a threshold (a
     named-NPC confrontation, not ambient banter).
  3. **In budget** — a global/regional **LLM budget** (rate + cooldown) has
     room. The director spends scarce budget on the highest-salience witnessed
     beats and lets the rest run deterministic.
* When the gate opens, narration uses the existing LLM-NPC pipeline
  (`build_persona`, `execute_cmd`) — the director chooses *that this NPC speaks
  now*; the LLM chooses *what it says*; the NPC says it through the real command.

**Third-party action safety.** When a dispatched NPC acts **on a player**
(a security bot restrains, a companion touches, a ganger shoves), that action
must route through the future **trust/consent gate** (`TRUST_AND_CONSENT_SPEC`,
flagged SUPER IMPORTANT). The director must not paint this into a corner:
NPC-initiated actions targeting able-to-resist players are subject to the same
consent rules as player-initiated ones. Reserve the seam now.

## 7 · Worked examples

* **Assault → LEO response.** Combat raises `assault` at a room. Dispatcher
  matches `security_bot` / LEO by jurisdiction + proximity, materializes a squad
  if none stand nearby, routes them via A\* to the scene, monitors. If a player
  is present when they arrive and severity is high, the dispatcher (LEO) may get
  an LLM line ("Hands where I can see them"); otherwise it acts on templated
  commands.
* **Mining incident → S&R.** Mining system raises `mining_incident` (a collapse,
  a death) deep at `Z < 0`. Dispatcher deploys a flash-temp S&R crew, routes
  them down through the vertical Drifts rooms, runs the rescue
  deterministically; despawns the crew after.
* **Shift change → a drink.** Time system raises `shift_change`. A worker's
  routine reroutes to the bar; they order from Sable via the deterministic
  vocabulary. If a player is at the bar, the director *may* escalate the
  exchange to the LLM — usually it stays templated.

## 8 · Integration seams

* **Spatial coordinate system (dependency).** Proximity (`rooms_within`),
  distance, and the A\* dispatch routing all come from
  `SPATIAL_COORDINATE_SYSTEM_SPEC`. The director is its first major consumer.
* **LLM Gamemaster.** This spec is the *when/why* an NPC acts; that spec is the
  *what it says*. Sable, Vance, and companions become director-managed citizens
  whose existing LLM behavior is now budgeted and scheduled by the director.
* **Trust/consent.** §6 — NPC-initiated actions on players go through the gate.
* **Gigs / favor loop.** Player-facing gigs (the NPC-faction freelancer/favor
  economy from the growth direction) are events on the same bus: a posted gig is
  a `WorldEvent`; completing it shifts faction/rep state. Gigs are the player's
  *interface into* the simulation.
* **NPC memory & identity.** Persistent NPCs carry recognition memory / voice;
  ephemerals generally do not (cost). The director decides who is "someone."
* **Medical / death-curtain.** Lifecycle monitoring (§3) hooks death here.
* **Phase layer (`PHASE_LAYER_SPEC`).** The director is **phase-scoped**: census,
  LOD materialization, routines, and events all carry a phase — never render
  `phase = net` NPCs to a `phase = meat` player. Most events are single-phase; a
  few are deliberate **cross-phase causal** bridges (an EMP frying net nodes) and
  route through the same bus naming both phases.
* **Stealth & detection (`STEALTH_AND_DETECTION_SPEC`).** A hidden target feeds an
  NPC's **graded awareness meter**, which drives a *deterministic* (non-LLM)
  hunt state machine — suspicious → search last-known position (Dijkstra) → alert
  allies (a bus event) → give up → routine. The director hosts that state machine;
  awareness is the cheap, LLM-free signal that makes the population feel watchful.
* **Robots & the police MOB (`ROBOT_SPECIES_AND_MOB_SPEC`).** The director's
  **first MOB consumer**: a security-robot patrol/detect/challenge/restrain state
  machine that exercises this spec end-to-end (routines, LEO response, alert
  propagation, the trust-gated lawful restraint) — deterministically, no LLM.
* **Radio comms (`RADIO_COMMS_SPEC`, 📋 drafted #859).** The colony's primary comms and
  the carrier for §5.1's report link: witness reports, dispatch orders, and the
  base intel-sync all ride radio. Jamming/antenna sabotage/walkie-snatching cut
  the chain. Until it ships, the report step is a magic placeholder.
* **Identity & recognition (`IDENTITY_RECOGNITION_SPEC`) — the BOLO substrate.**
  §5.1's identification runs on `apparent_uid` (presentation hash): disguise/
  re-sleeve defeats a BOLO and resets a wanted record; recognition memory is
  what lets a witness yield a *name*.
* **Crowd system — witness generation.** Crowd level decides whether a crime
  has a witness at all; a witness materializes as a real NPC (§5.1).

## 9 · Build ladder

| Phase | Scope | Notes |
|---|---|---|
| **3 — Event bus & dispatcher** | ✅ **CORE SHIPPED** (#853): `WorldEvent`, `ROLE_RESPONDS_TO`, `find_responders` (nearest-by-travel), `dispatch` (severity-scaled), `travel_to` (the routine-movement primitive too), `@dispatch`. Monitor/resolve + a real event bus still ahead. | The "dispatch system" proper |
| **1 — Population registry & LOD** | 🟡 **security-base slice SHIPPED** (#901): `world/director/population.py` — `@patrol/base` designates the base room (spawn/sync/**respawn**: the heartbeat maintains `db.security_complement`, cycling one alcove replacement per tick; census self-heals — dead units just fall out of the count); one shared `spawn_secbot` factory (a secbot is always "a {finish} **security robot**", #903). Still ahead: the general registry, ephemerals-at-scale, spawn-on-approach LOD, **the anti-small-worlding presentation layer (§10)**. | Needs coordinate proximity (spatial Phase 1 ✅) |
| **2 — Roles & routines** | 🟡 **patrol beats SHIPPED** (#899): `db.post` (assignments return to base) + `db.patrol_beat` loops via the **GLOBAL_SCRIPTS heartbeat** (45s; #908 — hand-created script rows never arm, learned hard); waypoint hook = the security wanted-sweep (**Patrol→Detect by composition**: a flagged face raises a `disturbance` the patroller answers); `@patrol` command family; first live beat = the two-district figure-eight over the Central Span. Still ahead: time-of-day schedules, non-security routines. | Needs spatial Phase 2 ✅ |
| **4 — Deterministic interaction vocabulary** | Templated NPC↔NPC / NPC↔PC exchanges via real commands | Zero-LLM baseline |
| **5 — LLM escalation gate** | Witnessed + salient + budget; generalize bartender gate | Reuses LLM-NPC pipeline |
| **— Parallel —** | Gig/favor loop as events; faction/rep state | Player hook |
| **Reserved** | Mining-incident integration; LEO jurisdictions at scale | Tie to mines (spatial reserved seam) |

The dispatch core (Phase 3) shipped first because it directly proves the spatial
substrate; the population/identity layer (Phase 1) is the next priority because
it's what makes a small literal map read as a large colony (§10).

## 10 · Risks & open questions

* **Small-worlding (the headline design problem, owed a discussion).** The
  colony is *conceptually* large (thousands of inhabitants) but the literal map
  is small (~309 rooms) with few NPCs. If the same handful of NPCs are visibly
  dispatched everywhere, the world reads as a tiny stage with a small recurring
  cast. The **dispatch core is identity-agnostic** — it routes whatever NPCs
  exist; the cure lives in the **population + identity** layer:
  * **Identity scarcity makes the world feel large.** The recognition system
    (`IDENTITY_RECOGNITION_SPEC`) decides whether a player perceives an NPC as a
    *distinct individual* or an *interchangeable type*. Most NPCs must read as
    **anonymous types** ("a security robot", "a dockworker") so the player never
    assembles a small cast list; the few **named persistents** (Sable, Vance)
    are the deliberate, special exceptions recognition memory holds. A small
    object pool can then present as a large populace.
  * **Ephemeral generation over a fixed roster.** Responders/crowd/labour are
    mostly **flash-temp** — spawned with varied presentations on demand and
    despawned after — so the populace is *generated*, not *rostered*.
  * **Materialize over teleport-walk.** A responder trekking 30 rooms across the
    whole map exposes both the geography's smallness and the cast. Prefer
    **distributed standing forces** (precinct/station-local units that walk a
    *believable* short distance) or **off-screen materialization** ("a unit
    rolls up"); reserve the long visible walk for when it adds tension.
  * **Crowd/ambient carries the unseen masses** — the thousands are *felt*
    (density, distant events), not instantiated.
  Open: how anonymous vs. named the population should be; station-based vs.
  roving forces; the walk-vs-materialize rule; how aggressively recognition is
  gated so the same object can recur unrecognised.
* **NPC↔NPC combinatorics.** Even deterministic exchanges can explode if every
  pair interacts every tick. **Lean:** rate-limit interactions per NPC, gate on
  co-presence + a low ambient roll (mirror the bartender ambient cooldown),
  and only render to actual witnesses.
* **LOD materialization consistency.** State must survive the
  virtual↔instantiated round-trip (an NPC mid-route when it dematerializes must
  resume correctly). Off-screen state is the source of truth; objects are a
  projection.
* **LLM budget tuning.** The witnessed+salient+budget gate needs real numbers
  (per-region rate, cooldown, salience threshold) — tune against the live mini's
  single-sidecar ceiling, the same constraint the bartender already lives under.
* **Determinism vs. surprise.** Fully deterministic routines can feel
  mechanical. Reserved: light stochastic variation in routine selection so the
  city isn't a clockwork.
* **Trust/consent timing.** NPC-on-player actions need the consent gate to exist
  before authority NPCs (security bots) can lawfully grab a player. Sequence the
  LEO-force content *after* that gate, or scope early authority NPCs to
  non-coercive actions.
* **Persistence cost.** The registry for a large virtual population must stay
  light (data rows, lazy detail) so the census itself doesn't become the bottleneck.
* **Ownership of corpses/cleanup** between the director and the existing
  death-curtain / decay systems — avoid double-ownership of a dying NPC.
