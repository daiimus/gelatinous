# NPC Dispatch & World Simulation Specification

The **director** (`world/director/`) is a hardcoded, deterministic
world-simulation engine. It manages the NPC population (spawn / despawn /
routine / death) and **dispatches** NPCs in response to world events, routing
them through the spatial pathfinder. The LLM-NPC puppeting layer brings
selected NPCs to life **only when a player is there to witness it and the
moment is worth the cost.** It is built on `SPATIAL_COORDINATE_SYSTEM_SPEC`
(the coordinate volume and the A\* pathfinder).

The souls system ([`NPC_NEEDS_AND_GOALS_SPEC`](NPC_NEEDS_AND_GOALS_SPEC.md))
absorbed and superseded parts of this design. Where it did, the section says
so.

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
| **Abstract** | No player anywhere near (off-screen) | ~zero — level of detail is per-object throttled thinking (souls); cold souls stay instantiated (§3) |
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
ephemeral. 📋 UNBUILT (no issue) as a general registry;
`world/director/population.py` holds the security base complement and the
civilian pool.

* **Persistent NPCs** — named, durable citizens (Sable the bartender, Doctor
  Vance, companions). They have stable identity, recognition memory, voice.
* **Ephemeral / flash-temp NPCs** — spawned for a shift, a gig, or an event
  (a flash-temp mining crew, a LEO response squad) and **despawned** when the
  reason ends. The bulk of the visible population is ephemeral.

**Population doctrine.** **DECIDED (owner, 2026-08-28): ABSORPTION — every
NPC gets a soul.** There is no permanent thin tier. Sequenced after the role
model is unified, so the ambient population is not merged into a shape that is
about to change. The souls and the ambient civilian layer (§4) both run
today.

**The security base** (#901). `@patrol/base` designates the base room, where
units spawn, sync and **respawn**. The heartbeat maintains
`db.security_complement`, cycling one alcove replacement per tick. The census
self-heals: dead units just fall out of the count. One shared `spawn_secbot`
factory makes every unit; a secbot is always "a {finish} **security robot**"
(#903).

**Level of detail.** Off-screen cost is bounded by per-object throttled
thinking (the souls engine). Cold souls stay instantiated; the city's objects
are not virtualized.

*Overturned intention:* this spec designed a **spawn-on-approach** LOD —
off-screen population as a virtual row of state in the registry, materializing
as real objects when a player enters or nears a region (via the coordinate
proximity query) and dematerializing after the last player leaves and a grace
period passes, to bound object count and tick cost to where players are. The
souls reconciliation (2026-08-20) abandoned spawn-on-approach and
virtualization in favour of per-object throttled thinking.

**Death & lifecycle monitoring.** The director subscribes to the medical/death
system (death-curtain hooks). An NPC death is itself a **world event** (§5): a
murder may summon LEO; a mining death may trigger S&R; a flash-temp's death just
updates the census and schedules cleanup. The director owns despawn, corpse
handling hand-off, and any respawn/replacement cadence — so the world neither
leaks corpses nor depopulates permanently. 📋 UNBUILT (no issue): a death
raises no event (§5, §5.2). What exists: a responder that dies holding a call
has its call closed `unit_lost` (§5), and the security census self-heals
(above).

## 4 · Roles & routines

Each NPC has a **role** defining its spawn rules, schedule, event
subscriptions, and jurisdiction. Roles are data-authored, not hardcoded per-NPC.

📋 UNBUILT (no issue) as written. A role is the string `db.role` (dispatch
roles `security` and `medic`); civilian roles are data in `CIVILIAN_ROLES`
(`world/director/civilians.py`). The role record this spec wants carries:

* `id` — "miner", "bartender", "security_bot", "ganger";
* `faction` — NPC-only factions (see growth direction), or none;
* `routine` — schedule key → deterministic behavior;
* `responds_to` — event types this role is dispatched for;
* `jurisdiction` — region/zone scoping for response eligibility, or none;
* `persistence` — "persistent" | "ephemeral";
* `llm_persona` — if set, eligible for LLM narration when salient.

**Routines** are deterministic behavior — a state machine / lightweight behavior
tree driven by the time system and the NPC's role: a miner cycles shaft → break
→ home; a shift change routes a worker to the bar for a drink; a security bot
patrols a beat. Routines move NPCs via the **pathfinder** (§5 of the coordinate
spec) and act via real commands. No LLM required for any of it.

For souls this section is SUPERSEDED: souls run on wants, not clocks (the
tripartite 8h shift system). It still runs as written for the ambient civilian
layer.

**Patrol beats** (#899). A unit has a `db.post` (assignments return to base)
and a `db.patrol_beat` it loops. `director_routines` is a GLOBAL_SCRIPTS
heartbeat at 45s (#908 — hand-created script rows never arm). It owns what a
beat IS: route, stagger, cadence, waypoint hook, complement respawn.

* A souled body's beat is a band-4 souls goal (`world/souls/actions.py`
  `_patrol_plan`), walked by the 30s `souls_heartbeat`. `routines.tick_npc`
  returns `souls` for a souled body and walks only an unsouled one. One driver
  per body: two schedulers reading each other's attributes over the same
  bodies was a bug (#2373).
* The waypoint hook is `routines.at_waypoint`, role-branched. Security runs
  the wanted-sweep (**Patrol→Detect by composition**: a flagged face raises a
  `disturbance` the patroller answers). A civilian gets a role-authored
  ambient beat (`civilians.ambient_beat`).
* A souled body reaches the hook through the souls `patrol_mark` step
  (#2373). An unsouled one — which every freshly spawned civilian still is —
  reaches it from the 45s tick.
* The `@patrol` command family manages beats.

**The ambient civilian layer** (`world/director/civilians.py`). Haunts are
sampled around wherever the civilian appears and walked at a slower
`patrol_cadence`, with a role-authored `ambient_beat` at every stop. The
heartbeat loop owns the census.

**Time of day** is the souls tripartite 8h clock: `SCHEDULES` day/swing/night
plus `on_duty`/`soul_hour` (`world/souls/engine.py`) and `current_shift`
(`world/souls/posts.py`) — WANTS against a clock, not routine schedules.

## 5 · The event bus & dispatch

The heart of "both layers." Dispatch and the crime chain are shared by both
population layers: souls route NPC-on-NPC crime through the same
witness/BOLO machinery, and a `medical` event type rides the same bus (the
rescue loop).

**Events** are typed, located, and weighted. `WorldEvent`
(`world/director/dispatch.py`, beside the dispatcher it feeds) carries a
`type`, a `location` (a room, which carries coordinates for distance and
routing), a `severity` (drives responder count and LLM salience), a `source`
(the instigator: a PC, an NPC, a system tick) and a `payload` of event-specific
detail.

Events are raised by the world: combat (assault), the mining system (incident),
the time system (shift change), the medical system (death), the gig system
(task posted). They land on a bus the **dispatcher** consumes.

The types raised: `assault`, `vandalism`, `sabotage`, `pickpocketing` (the
instrumented acts, through `report_crime`); `assault`, `disturbance`, `fire`,
`medical` and `crime` (player radio calls, `radio_report.apply_verdict`);
`medical` (a downed body a soul notices, called in by a crowd witness);
`disturbance` (a patrol wanted-flag, a hunt reacquire, an explosion).
`raise_event` (`world/director/dispatch.py`) logs the incident and hands it
straight to `dispatch`. 📋 UNBUILT (no issue): `mining_incident`,
`shift_change`, `death` and `gig` events, and a real bus.

**Deterministic first** (#2222, #2238): plain-code word matching classifies
before the model is asked, and the reply is CAUSED by the verdict rather than
raced against it.

### The dispatcher (`world/director/dispatch.py`)

1. **Match** — every Character whose `db.role` or `db.soul_role` responds to
   the event type (`ROLE_RESPONDS_TO`), minus the instigator, pinned souls,
   units that cannot hear the emergency band (`hears_emergency_band`) and units
   the dispatch order cannot reach by radio (`order_reaches`); ranked by travel
   steps (`path_length`) by `find_responders`. 📋 UNBUILT (no issue):
   `jurisdiction`.
2. **Select** — pick responder count from `severity`; nearest-first by travel
   path. Materialize a flash-temp squad if no standing responders exist (a LEO
   van rolls in; an S&R crew is deployed). 📋 UNBUILT (no issue): flash-temp
   materialization (the population layer).
3. **Route** — A\* over the real exit graph (coordinate spec §5) toward the
   event; respects locks, warps, and collapsed tunnels automatically.
4. **Monitor** — track arrival, resolution, and casualties; a responder death
   re-enters the bus as a new event. A responder that dies holding a call
   has its call closed `unit_lost`, silently: a destroyed unit does not
   transmit (`release_on_death`, `security_death`). A critically damaged unit
   radios one mayday and holds the scene (`_mayday`). 📋 UNBUILT (no issue): a
   responder death raising a new event.
5. **Resolve** — on completion, return standing NPCs to routine; despawn the
   flash-temp squad after a grace period. Linger → return-to-post runs (#863).
   📋 UNBUILT (no issue): flash-temp despawn (the population layer).

**The assignment lifecycle** (#863, `world/director/assignment.py`): en route
→ on-scene (role-keyed `ARRIVAL_HANDLERS`) → linger → return-to-post.
Committed responders skip other incidents: the finite pool is real.

A dispatched responder is driven by the souls engine, not seized by the
director. `assign` (`world/director/assignment.py`) writes a band-0 `respond`
job: travel to the scene, run the role's arrival handler, watch once per beat,
travel back to post, stand down. Band 0 outranks every other goal, so a unit
does not leave a call. `travel_to` (pathfinder-driven movement via real exit
commands, also the routine-movement primitive) is used only for a responder
with no soul.

Dispatch is the bridge between the **simulation** (who exists, where, doing
what) and the **spatial system** (how they get there). It is fully
deterministic; the LLM enters only if step 4 puts a responder in front of a
player during a salient beat.

### The receipt is the units' voices

The receipt is the UNITS' voices (2026-07-11, user call — the console
restating the operator's ack was an echo). Each dispatched responder keys up
its own staggered 'Unit <id> responding — <where>.' through the real `xmit`
verb and its comms organ (a wrecked organ or a downed unit = honest silence).
The drained-pool 'No units available' stays dispatch's announcement. With
nobody at the desk, the drained-pool line is not sent.

### Reachability: dispatch orders are radio traffic

* **Hearing** — `world.radio.hears_emergency_band` (a comms organ, or a
  powered carried radio on 911MHz). A deafened unit (shot ear, snatched
  walkie) stands at post, never rolls, and drops off Petra's 'units on the
  line'. Ear-sniping neutralizes without destroying.
* **Order range** (#1208) — `world.radio.order_reaches`. The dispatch ORDER
  itself is radio traffic: the console transmits at mast-backed reach (a
  wrecked mast = walkie range), repeaters regenerate command one hop, the
  unit's ears extend the link (reciprocity), and only clear/fuzzy grades move
  a unit (static/gone don't parse). A switched-off console fails CLOSED (the
  spec's physical gate); no authored console, or an off-grid room, fails open.
* Both gates apply to `find_responders` and to the desk's availability count
  (`units_available`, `world/director/dispatch.py`).
* The full sabotage chain: wreck the mast → distant witnesses can't report in
  AND distant units can't be commanded — the colony's law shrinks to walkie
  radius around the station until someone repairs the steel.

### Player radio calls on 911MHz

**No operator, no dispatch for player radio calls.** A call on 911MHz is
judged only by whoever sits at the powered console
(`world.radio.seated_base_station`). The console does not speak and does not
dispatch: it is a radio bolted to a desk, and everything it does belongs to
the person in the chair (#2223, #2228). Witness reports, a unit on the scene,
patrol and hunt flags and explosions raise their event directly and roll units
whether or not anyone is at the desk.

* **Classification.** Player traffic is classified first by plain-code word
  matching (`classify_report`, `world/director/radio_report.py`). The civic
  lane's structured verdict (constrained decoding) is asked only for traffic no
  word matched, and only when the lane is enabled (it is off unless
  `CIVIC_LLM_ENABLED` is set: `CIVIC_LLM_*` settings, `client.civic_enabled`;
  plain-code matching works without it).
* **Classifier judgment** (#1180): a reasoning-first schema — a required
  leading `event_summary` forces the model to articulate what is physically
  happening before judging (field order = generation order under constrained
  decoding); an emergency-in-progress bar with per-enum definitions; few-shot
  exemplars covering the observed failures (gossip/'drinking all the recyc',
  wordplay/'fire that boils tea', requests). Failure at any layer = silence.
* **Raising the event.** A CONFIRMED report raises a real `WorldEvent`:
  a two-signal gate (report flag AND type enum agree), plain-code location
  resolution against room names (fallback: the caller's room), a 120s scene
  debounce, and severity per the frugal ladder (§5.2).
* **The caller is UNVERIFIED by design**: false reports drain the finite pool
  (swatting is a mechanic).
* NPC/witness traffic never re-classifies (no double dispatch).

**The dispatcher at the desk.** `world/souls/salience.py` senses; whoever
holds the chair judges and answers. Her reply is grounded in the verdict for
the call she is answering — the operator's prompt line from that verdict
(`ndb.dispatch_verdict`, `_dispatch_board_line`) — not in the call ledger.
`world.director.dispatch.desk_discipline`, applied by
`salience.filter_for_duty`, backstops what she says: a units-moving claim is
struck (units own the announcement; a true claim becomes the bare 'Dispatch
copies.'), and so is a promise to leave the desk ('I'll be there in a minute' —
she never leaves the desk; 'I'd really like to' survives: wanting is flirt,
arriving is a lie). A struck line is replaced from `DESK_FALLBACK_LINES`.
Her register holds the desk doctrine ('chained to this desk — never promise
to go anywhere, meet anyone, or bring anything'), and idle chatter gets one
dry human line before it is moved off the channel (#1174).

**The answering cooldown.** `AnsweringFixture` (`typeclasses/items.py`)
carries `ANSWER_COOLDOWN` at 4.0s (#2216), for conversational rhythm (#1174,
user: interlopers get to vibe with dispatch).

**EMERGENT (unscripted, keep):** secbots are LLMNpc — `_hear_radio` band
comprehension means units editorialize in persona ('Request oversight on
unauthorized use of 911MHz' after a swatting spree).

### A report is a CALL (`world/director/calls.py`, #2246)

A call is a persistent record on the `ServerConfig` ledger carrying the
caller's verbatim words, the place they named, what they said about the
person, which units rolled, and a status. It outlives a reload. Responders
close it through the `call_id` in the event payload:

* `detained` — a high match held;
* `checked` — a lookalike questioned;
* `unfounded` — nothing found; the unit says so on the air (#2256);
* `unit_lost` — the responder destroyed; said nowhere on air.

Each call stores the caller's voice UID (`calls._voice_of`). Nothing reads the
ledger back.

📋 UNBUILT (no issue): anything that counts strikes against the caller's
voice UID — false-report consequences via a voice-UID strike record (voice
signatures, 'finds nothing' scene logs and the BOLO all exist; a voice
modulator = counter-tradecraft).

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
  no report). When there is one, the witness **spawns as an actual NPC**, a
  flash-temp ephemeral (#873) — so a PC can interdict them: intimidate, bribe,
  harm, or kill the witness before the report goes out. A witness flees to
  cower via director travel (#888). Multiple witnesses **corroborate** (sharpen
  the BOLO) or **conflict** — and witnesses **can mislead** (a false
  description sends the force after the wrong profile; manipulating witnesses
  is play). 📋 UNBUILT (no issue): one scene yields at most one witness, and a
  witness's description is always accurate. A witness may refuse to report
  (`report_posture` "never") or call it in at twice the speed ("fast").
* **Combat raises the crime itself** (#871): a 45s witness window, a per-scene
  debounce, and a BOLO taken at crime time.
* **Reports travel by radio** (`RADIO_COMMS_SPEC`, the colony's primary comms;
  `world/radio.py`). No transmission → the force never learns. Disrupting comms
  is a first-class criminal avenue: snatch the walkie from a witness's hand,
  break the rooftop antenna, jam the band (📋 UNBUILT (no issue)). There are no
  magic radios on the crime chain:
  * the witness spawns carrying a real `WALKIE_TALKIE` on 911MHz, calls ride it
    via wield/xmit, and `witness_report` gates on it (#1009/#1020);
  * a caught theft routes through `report_crime`'s crowd-gated witness;
  * patrol wanted-flags and hunt challenges key the unit's comms organ on
    911MHz (xmit fallback) before the deterministic raise — the security net is
    audible to anyone tuned in;
  * explosions stay direct: a detonation is its own broadcast.
* **The BOLO is a perception-graded descriptor, not a handle** (`build_bolo` /
  `match_bolo`, #867; provenance #2247). What the event carries is *what
  witnesses saw*, and the BOLO says how it was learned. Only a security unit on
  the scene passes the perp's `apparent_uid` (the identity system's
  presentation hash), and only that can produce a high-confidence match. A
  `uid` is a presentation hash and may only travel machine-to-machine, because
  nobody says a hex digest out loud. A human witness passes what anyone could
  describe: height, build, and the colour and garment of what they wore — an
  accurate silhouette. A radio caller passes whatever words they used. Either
  one gives at most a low-confidence match. Clothing is matched too.
  📋 UNBUILT (no issue): a witness who *recognised* the perp giving a name.
  On scene, a responder **scans who it can currently perceive**
  (perception-gated — stealth/blindness apply; a blind bot scans nothing) and
  matches against the BOLO. Consequences fall out of the identity system for
  free: **flight** (not present), **disguise/re-sleeve** (UID changes → BOLO
  stale), **blending** (a coarse descriptor matches many → ambiguity),
  **looking generic is cover**. `is_the_right_person()`
  (`world/director/security.py`) keeps the game's truth separate from the
  robot's belief.
* **Mistaken identity is intended.** Matching yields a **confidence**, and
  action is **tiered**: high confidence → detain; low confidence → challenge /
  question / observe (friction, not instant injustice). A coarse BOLO can put
  an innocent lookalike in the hot seat — and a smart perp exploits that.
  On scene (`world/director/security.py` `security_arrival`, `watch_once`): a
  matched or wanted suspect who is already fighting is not detained; the unit
  deploys its arm gun and attacks, once per call. Otherwise high confidence
  means a challenge and a hold at aim (`_aim_lock`) — a non-coercive
  detainment that closes the call `detained` — low confidence means
  questioning, and no match means the unit logs the scene. A face on the
  force-wide wanted record is challenged even when the current call is about
  something else. Coercive restraint is unbuilt (§6).
* **Intel is hybrid and syncs at base** (#876). A bot's identifications are
  **per-bot** knowledge until it **returns to base and syncs** (on
  return-to-post), only then joining the force-wide wanted record. The force
  knows your face *eventually*; a given bot still has to *see* you (per-bot
  perception always gates action). The sync latency is an exploitable window;
  the base is a meaningful place (and target). Repeat offenders accumulate a
  record keyed to `apparent_uid` — which a re-sleeve or disguise resets (a
  clean face costs something).
* **Attention & triage are bounded.** A responder continuously triages its
  assigned event against what it *perceives en route* — an armed individual, an
  active assault, graffiti-in-progress — by severity × immediacy × proximity.
  It can be **preempted / distracted** (bait play). 📋 UNBUILT (no issue):
  en-route triage and preemption; a unit on a call finishes it. At the force
  level, **capacity is finite** (a configured pool of security bots +
  deployment dynamics, later): multiple incidents force allocation, some go
  unanswered — **overwhelming the force is an intended heist tactic**.
* **The no-trace window.** A skilled criminal can render witnesses inert —
  *including security bots* (they are perceivers, not oracles) — before acting:
  gas, blackout, EMP. Ties to the cross-phase EMP seam (`PHASE_LAYER_SPEC` §9)
  and the robot chassis (an EMP'd bot saw nothing, reports nothing). No
  perceiver → no chain → no consequence. 📋 UNBUILT (no issue): reserved as a
  seam.

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
only question is whether you were *seen*. The theft verbs are `steal` and
`pickpocket` (`commands/CmdTheft.py`, `STEALTH_AND_DETECTION_SPEC` §6.2) and
`frisk`.

| Crime | The act | Severity = units sent (`CRIME_SEVERITY`) | How the force learns |
|---|---|---|---|
| Shoplifting | stealth-take from a shop | 1 | often never; stocktake shrinkage later (no BOLO). 📋 UNBUILT (no issue): no act raises this type, and there is no stocktake |
| Vandalism | graffiti on property | 1 | witnessed-in-the-act only |
| Pickpocketing | `pickpocket` / `steal` | 1 | only a failed lift is noticed: the victim and onlookers who can see the thief go Alert, and a crowd-gated witness may call in a theft with no BOLO (a sourceless incident the hunt reads); a clean lift is never reported |
| Mugging | threaten/grapple → frisk → steal | 2 | **the victim reports** (if alive, conscious, able). 📋 UNBUILT (no issue): no act raises this type |
| Armed robbery | wielded weapon + take (shop/NPC) | 2 | victim + crowd witnesses; good BOLO. 📋 UNBUILT (no issue): no act raises this type |
| Assault | combat on an unwilling target | 2 | loud — crowd-gated witnesses |
| Murder | death | 3 | **discovered via the corpse** → forensic BOLO off `signature_at_death` (`world/forensics.py`). 📋 UNBUILT (no issue): a death raises no event and nothing reads `signature_at_death` into a BOLO; a killing is reported, if at all, as the assault that led to it |
| Sabotage | `sabotage <structure>` (a long, visible act) | 1 | witnessed at commission: crowd-gated witness and BOLO, if a report can still reach anyone |

Severity is the number of units `dispatch` sends (at least one). The values
are `CRIME_SEVERITY` in `world/director/crime.py`. The table's "Armed robbery"
is keyed `robbery`.

**The frugal ladder** (#1182, user call: violence and explosions are what call
in more units). Radio calls: assault 2, all other radio reports 1. Witnessed
crimes: murder 3; assault, mugging and robbery 2; all nonviolent, including
sabotage, 1. Explosions and engaged-unit backup: 2.

**Three report paths** (what actually varies per crime):
1. **Witnessed at commission** — the §5.1 chain as designed (loud crimes).
2. **Victim-reports** — the victim *is* the witness; everything in §5.1 applies
   to them (silence, snatch the walkie, intimidate). A mugging done right
   leaves a victim who *chooses* not to report. 📋 UNBUILT (no issue): every
   report comes from a spawned crowd witness or a unit on the scene, never
   the victim.
3. **Discovered later** — 📋 UNBUILT (no issue): nothing raises an event off
   evidence. Quiet crimes raise events off the *evidence*:
   stocktake shrinkage (no BOLO), a found corpse (**forensic BOLO** — degraded,
   cold-trail), a district gone radio-dark. Note the grim emergent truth:
   unwitnessed murder is *quieter* than assault — finishing the job silences
   the best witness. Intended.

**NPC victims** (what makes mugging/robbery real):
* **Pockets** — civilians spawn with **100–500 tokens**
  (`world/director/civilians.py` `TOKEN_RANGE = (100, 500)`), set as the
  reference scale: worth mugging, not farming. Prices are real now: food/drink
  prototypes carry `value` 2–12, butchery pays 1–5 per cut, bar recipes charge,
  and `world/souls/population.py` defines `BROKE_LINE = 3` as the cheapest
  meal. 100–500 has not been through the balance pass.
* **Reactions** — comply / flee / resist, **role-weighted for now** (a laborer
  complies, a ganger resists, a shopkeeper raises the alarm). Future: a
  **nature/demeanor/traits axis** on NPCs informs both these deterministic
  reactions *and* the LLM persona when one is puppeted — one personality
  substrate, two consumers.

  **Escalation ladder:** reactions are stateful (`ndb.reaction_stage`), not a
  stateless one-shot — continued violence climbs: **comply → flee**
  (surrender answered with violence is off the table; the rung persists, so a
  beaten hawker never re-offers hands-up), **flee → resist when armed** (the
  *cornered rat*: a scavver denied an exit turns and draws; unarmed keeps
  retrying the run), **resist is terminal** (no re-reaction, no spam — no
  repeated emote every swing). Dialogue is NEVER scripted: for LLM NPCs the
  attack + their own mechanical response is *observed into the action buffer*
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
  📋 UNBUILT (no issue): a victim never reports; a failed theft is called in
  by a spawned crowd witness.

**Heat — the spatio-temporal crime map.** 📋 UNBUILT (no issue; OPEN, a
natural WSIS bridge). Crimes accumulate **heat** at their
coordinates over time (decaying), and heat **dictates patrol allocation**:
hot districts draw patrols, quiet ones thin out. Getting away with quiet crime
is consequence-*free for you* but raises district heat — the world responds to
patterns, not just incidents. **Except where it deliberately doesn't:** certain
areas are **purposefully under-patrolled due to special interests** — a
per-district patrol bias the heat system honors (gang arrangements, corporate
carve-outs). Corruption is data, not lore; discovering *which* districts are
cold-by-design is player knowledge worth having.

## 6 · Interaction & the LLM escalation gate

The hardest part, by your call, is **NPC↔NPC interaction** — and the answer is
to make the *default* free.

* **Deterministic interaction vocabulary** — templated exchanges keyed by the
  role pair + context, rendered through real `pose`/`say`/`emote` commands:
  two gangers posture; a miner orders from the bartender; a security bot
  challenges a loiterer. Cheap, on-brand, and visible. This is what "the
  simulation does its thing" looks like on-screen with zero model cost.
  📋 UNBUILT (no issue).
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

  The generalized gate is OPEN: only the inherited bartender/dispatch gates
  exist. 📋 UNBUILT (no issue).
* When the gate opens, narration uses the existing LLM-NPC pipeline
  (`build_persona`, `execute_cmd`) — the director chooses *that this NPC speaks
  now*; the LLM chooses *what it says*; the NPC says it through the real command.
  Souls add a STATE line (mood + where-and-what) to voiced turns.

**Third-party action safety.** When a dispatched NPC acts **on a player**
(a security bot restrains, a companion touches, a ganger shoves), that action
must route through the **trust/consent gate** (`world/consent.py` —
`check_consent` / `can_contest` / `is_restrained` — plus the `trust`/`distrust`
commands; `TRUST_AND_CONSENT_SPEC`, flagged SUPER IMPORTANT). The director must
not paint this into a corner: NPC-initiated actions targeting able-to-resist
players are subject to the same consent rules as player-initiated ones.
Reserve the seam now. Units today are non-coercive: they challenge and hold
at aim (`world/director/security.py` `_aim_lock`). 📋 UNBUILT (no issue):
coercive restraint. It is no longer waiting on the consent gate, which
exists.

## 7 · Worked examples

* **Assault → LEO response.** Combat raises `assault` at a room. Dispatcher
  matches `security` units by travel distance (📋 UNBUILT (no issue):
  jurisdiction, and materializing a squad if none stand nearby), routes them
  via A\* to the scene, monitors. If a player is present when they arrive and
  severity is high, the dispatcher (LEO) may get an LLM line ("Hands where I
  can see them"); otherwise it acts on templated commands.
* **Mining incident → S&R.** Mining system raises `mining_incident` (a collapse,
  a death) deep at `Z < 0`. Dispatcher deploys a flash-temp S&R crew, routes
  them down through the vertical Drifts rooms, runs the rescue
  deterministically; despawns the crew after. Mining S&R is OPEN.
* **Shift change → a drink.** Time system raises `shift_change`. A worker's
  routine reroutes to the bar; they order from Sable via the deterministic
  vocabulary. If a player is at the bar, the director *may* escalate the
  exchange to the LLM — usually it stays templated. For souls, shift-change
  examples are superseded by wants (§4).

## 8 · Integration seams

* **Spatial coordinate system (dependency).** Proximity (`rooms_within`),
  distance, and the A\* dispatch routing all come from
  `SPATIAL_COORDINATE_SYSTEM_SPEC`. The director is its first major consumer.
* **LLM Gamemaster.** This spec is the *when/why* an NPC acts; that spec is the
  *what it says*. Sable, Vance, and companions become director-managed citizens
  whose existing LLM behavior is now budgeted and scheduled by the director.
* **Souls (`NPC_NEEDS_AND_GOALS_SPEC`).** Souls drive dispatched responders
  (§5), own routines for souled bodies (§4), and share the crime chain (§5).
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
* **Radio comms (`RADIO_COMMS_SPEC`, `world/radio.py`).** The colony's primary
  comms and the carrier for §5.1's report link: witness reports, dispatch
  orders (`order_reaches` gates `find_responders`, §5), and the base intel-sync
  all ride radio. Range/antennae and mast repeaters set reach. Jamming
  (📋 UNBUILT (no issue))/antenna sabotage/walkie-snatching cut the chain.
* **Identity & recognition (`IDENTITY_RECOGNITION_SPEC`) — the BOLO substrate.**
  §5.1's identification runs on `apparent_uid` (presentation hash): disguise/
  re-sleeve defeats a BOLO and resets a wanted record; recognition memory is
  what lets a witness yield a *name* (📋 UNBUILT (no issue): no BOLO carries a
  name).
* **Crowd system — witness generation.** Crowd level decides whether a crime
  has a witness at all; a witness materializes as a real NPC (§5.1).

## Superseded: the console's voice

*Overturned intention (2026-07-11 → 2026-08-23/24, #2223, #2228).* The
console was built to classify, speak and dispatch (2026-07-11, user: 'Copy.
Coffee. Units rolling.'). The ruling moved the voice to the person in the
chair: the console is a radio bolted to a desk. `_clean_reply`,
`CHATTER_LINES` and `[CONTEXT]` are gone; the units-claim and presence
backstops are `desk_discipline`, `FALLBACK_LINE` became `DESK_FALLBACK_LINES`,
`ANSWER_COOLDOWN` moved to `AnsweringFixture`, and the civic lane remains as
the classifier's fallback (§5).

## Unbuilt

Beyond the 📋 UNBUILT items marked in place above:

* **Population registry & presentation layer** — 📋 UNBUILT (no issue): the general
  registry, ephemerals-at-scale, and **the anti-small-worlding presentation
  layer (§10)**. Needs coordinate proximity. This is the next priority, because
  it's what makes a small literal map read as a large colony (§10).
* **Deterministic interaction vocabulary** — 📋 UNBUILT (no issue): templated
  NPC↔NPC / NPC↔PC exchanges via real commands; the zero-LLM baseline (§6).
* **LLM escalation gate** — 📋 UNBUILT (no issue): witnessed + salient +
  budget; generalize the bartender gate; reuses the LLM-NPC pipeline (§6).
* **In parallel** — 📋 UNBUILT (no issue): the gig/favor loop as events;
  faction/rep state (the player hook).
* **Reserved** — 📋 UNBUILT (no issue): mining-incident integration; LEO
  jurisdictions at scale (tie to mines, the spatial reserved seam).
* **WSIS** remains unbuilt and must eventually fuse both population layers, or
  the doctrine must collapse them.

## 10 · Risks & not decided

* **Small-worlding (the headline design problem, owed a discussion).** The
  colony is *conceptually* large (thousands of inhabitants) but the literal map
  is small (about 1070 rooms, per `WORLD_STATE_INTELLIGENCE_SYSTEM_SPEC`) with
  few NPCs. If the same handful of NPCs are visibly dispatched everywhere, the
  world reads as a tiny stage with a small recurring cast. The **dispatch core
  is identity-agnostic** — it routes whatever NPCs exist; the cure lives in the
  **population + identity** layer. Two cures now coexist: anonymous civilians
  (this spec) AND named persistent souls (souls spec decision #2);
  reconciliation fixes (#2063) made predators see both layers and partitioned
  the racing post-watchers.
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
* **Wealth scales.** Still open: unifying the two wealth scales (civilians
  100–500 vs souls' earned wages).
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
* **Persistence cost.** The registry for a large virtual population must stay
  light (data rows, lazy detail) so the census itself doesn't become the
  bottleneck.
* **Ownership of corpses/cleanup** between the director and the existing
  death-curtain / decay systems — avoid double-ownership of a dying NPC.
