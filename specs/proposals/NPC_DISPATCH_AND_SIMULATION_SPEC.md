# NPC Dispatch & World Simulation Specification

> **Status:** 📋 Proposal — not implemented. Designs the **director**: a
> hardcoded, deterministic world-simulation engine that manages the NPC
> population (spawn / despawn / routine / death) and **dispatches** them in
> response to world events — routing them through the spatial pathfinder. The
> LLM-NPC puppeting layer brings selected NPCs to life **only when a player is
> there to witness it and the moment is worth the cost.** Depends on
> `SPATIAL_COORDINATE_SYSTEM_SPEC` (traversal, proximity, routing).

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
   re-enters the bus as a new event.
5. **Resolve** — on completion, return standing NPCs to routine; despawn the
   flash-temp squad after a grace period.

Dispatch is the bridge between the **simulation** (who exists, where, doing
what) and the **spatial system** (how they get there). It is fully
deterministic; the LLM enters only if step 4 puts a responder in front of a
player during a salient beat.

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
  them down through the vertical/undercity rooms, runs the rescue
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

## 9 · Build ladder

| Phase | Scope | Notes |
|---|---|---|
| **1 — Population registry & LOD** | Census, persistent vs ephemeral, spawn-on-approach / despawn-on-leave | Needs coordinate proximity (spatial Phase 1) |
| **2 — Roles & routines** | Role data model, deterministic schedules, routine movement via pathfinder | Needs spatial Phase 2 |
| **3 — Event bus & dispatcher** | Events, matching, selection, routing, monitor, resolve | The "dispatch system" proper |
| **4 — Deterministic interaction vocabulary** | Templated NPC↔NPC / NPC↔PC exchanges via real commands | Zero-LLM baseline |
| **5 — LLM escalation gate** | Witnessed + salient + budget; generalize bartender gate | Reuses LLM-NPC pipeline |
| **— Parallel —** | Gig/favor loop as events; faction/rep state | Player hook |
| **Reserved** | Mining-incident integration; LEO jurisdictions at scale | Tie to mines (spatial reserved seam) |

Phases 1–3 are the deterministic simulation core and are worth shipping before
any LLM escalation exists — the world should feel alive on rules alone.

## 10 · Risks & open questions

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
