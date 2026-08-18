# NPC Needs & Goals — the deterministic soul

> **Status:** 📋 **Proposal — design only (2026-08-17, owner-directed:
> "souls over structures").** ELABORATES
> [`NPC_DISPATCH_AND_SIMULATION_SPEC`](NPC_DISPATCH_AND_SIMULATION_SPEC.md)
> §4 (Roles & routines) — that section imagined fixed schedules; this
> replaces the clock with **wants**. Shipped substrate it builds on:
> the director (heartbeat, `travel_to`, assignment/preemption), patrol
> routines, the time system, and the real economy (tills, food, rentals,
> posts). Design lineage is the published games literature: RimWorld's
> need meters + priority think-tree + jobs, The Sims' object
> advertisements, with a HYBRID of RimWorld-style
> goal arbitration and F.E.A.R.-style shallow planning (§2, revised
> 2026-08-17 after owner direction — the planner earns its keep the
> moment NPCs prey on and serve EACH OTHER). No LLM anywhere in the decision
> path — the two-brain split (deterministic will, LLM voice) is law.

## 1 · Intent

Our named NPCs have posts, voices, and reflexes — and no wants. Lin has
stood at her cart since July. A soul is: **needs that decay, goals that
rank, jobs that execute through real commands**. The payoff is not
decoration; it is the economy stirring itself — a hungry colonist walks
to Pessoa and buys a skewer *through the actual till*, a tired one
walks home to an actual cube, a shopkeeper closes up at night and the
street changes character. The city already contains every sink and
source a need system requires; this spec adds the motor.

## 2 · Architecture: hybrid — the tree arbitrates, the planner satisfies

(v2, owner-directed.) Two published architectures, each kept for the
half it is best at:

- **Goal arbitration = the priority tree** (RimWorld's lesson): bands
  (§5) decide WHAT matters now — legible, cheap, one-line explainable.
- **Goal satisfaction = a shallow GOAP planner** (F.E.A.R.'s lesson):
  given the winning goal, backward-chain 2–4 steps over an **action
  library** with preconditions and effects, against the soul's
  *perceived* world state. This is what makes `obtain_cash` resolvable
  as *work a shift* OR *beg* OR *mug the man carrying tokens in a
  private room* — the same goal, different chains, discovered rather
  than authored. No mugging schedules exist; muggings emerge.

**The action library** is the design surface: each action declares
preconditions (world + self), effects, a cost, and a **disposition
gate** — personality knobs (lawfulness, boldness, desperation
threshold) decide which actions exist in a given soul's library at
all. Law-abiding Bob simply has no `mug` action; Ruze does, but its
cost stays prohibitive until hunger and empty pockets discount it.
Desperation as a utility modifier produces the colony's texture for
free: the broke eat worse, then some of them turn predator.

Plan depth is capped (≤4); plan invalidation just re-plans next tick
(cheap at this depth). The `@soul` readout shows the chain and why
each link bound — legibility survives the hybrid.

## 3 · Needs

Per-soul decaying meters, 0.0–1.0, ticked by the LOD clock (§7):

| Need | Decays by | Satisfied by (advertisement tags) | Critical behavior |
|---|---|---|---|
| `hunger` | time | food vendors, owned food items | detour to nearest advertiser |
| `rest` | time awake | home (cube/bunk), flop spots | go home; collapse if ignored |
| `social` | time alone | bars, vendors with keepers, crowds | visit a social advertiser |
| `duty` | time off-post during shift | the NPC's own post | return to post |
| `safety` | violence/threat events | distance from threat | flee/report (dispatch seam) |

`cash` is a **resource, not a meter** — earned at posts (wage tick),
spent at tills. Broke NPCs skip paid satisfiers (the poor eat worse:
emergent, free). Mood/thoughts are Phase 3 (§9) — deliberately NOT v1.

## 3.5 · Souls advertise too — NPC↔NPC interaction

Everything §4 says about venues applies to **souls themselves**: an
on-post bartender advertises thirst/social satisfaction; a doctor
advertises treatment; a companion advertises company; and — to the
right disposition — a soul visibly carrying cash in a quiet room is
an advertisement of another kind. Soul-to-soul jobs are a **two-party
handshake**: the initiator's plan proposes an interaction (buy, chat,
solicit, threaten); the TARGET's own tree accepts, refuses, resists,
or flees based on its state and disposition. Commerce, harassment,
predation, and service solicitation are one mechanism with different
action libraries and consent semantics — and every one of them runs
through real verbs, so the witness/dispatch/heat chain treats NPC-on-
NPC crime exactly like player crime. Players can stumble into,
interrupt, or profit from any of it.

## 3.6 · Posts, shifts, and consequence continuity

The **post** (from the reincarnation spec) is the continuity spine:
a persistent object with SHIFT SLOTS (day/night), independent of any
occupant. Souls hold assignments; `duty` drives the commute. When a
shift-holder dies en route (see the worked example below), nothing
announces it — the post is simply unstaffed, patron jobs FAULT at the
counter, and the truth propagates only through perception: the next
shift arrives and finds the corpse, the absence, or the looted till,
then reacts per its own tree (report on the real 911 band / grieve /
loot / flee). Vacancy detection (the §P2 watcher) eventually
advertises the empty post; some resident's `claim_vacant_post` goal
answers. The bar heals, changed. **Worked example (acceptance test):
Bob's bad night** — commute → mugged by a desperate resident via real
grapple/rob verbs → unstaffed bar faults → night shift discovers →
report → dispatch → corpse lifecycle → succession. Every link is an
NPC perceiving state and running its own tree; no scripts, no
omniscience.

## 3.7 · Gigs are outsourced goals (the organic feed)

The gig system stops being authored content and becomes an EMISSION of
the soul layer: when a soul's goal stays unsatisfiable past a
threshold — its plan faults repeatedly, or no action in its own
library/disposition can close it — and it holds cash or favor to
spend, it **externalizes the goal as a gig**: a posting with the goal's
target state and a bounty derived from its utility pressure. Posts and
factions emit the same way (a vacant post gigs for a temp; a watcher
gigs for an investigation). One murder throws off a whole braid of
work — cover the shift, find out why Bob never showed, walk me home
after dark — none of it written by anyone. Players and OTHER SOULS
are both eligible takers (the two-party handshake again), completing a
gig pays cash AND favor with the emitting soul (who remembers, via the
NPC memory system), and the hiring hall / gig boards are simply where
emissions become visible. This is the favor/rep progression loop
(growth direction) fed by the simulation itself, and the aggregate of
soul-state that gigs surface is the seed of the world-state
intelligence capstone.

## 3.8 · The identity spine — perception, grudges, and the resleeve dodge

Souls perceive through the shipped identity stack
([`IDENTITY_RECOGNITION_SPEC`](../IDENTITY_RECOGNITION_SPEC.md) +
[`NPC_MEMORY_AND_IDENTITY_SPEC`](../NPC_MEMORY_AND_IDENTITY_SPEC.md)):
a witnessed crime is committed by *an apparent identity* (sdesc or a
name the soul chose to assign), never by ground truth — reports, gig
targets, and grudges all carry `apparent_uid` handles. Dossier valence
IS disposition-toward-a-person: it modifies utility (fear raises
flee-weight near your mugger; earned favor discounts prices and opens
solicitations), and P3 thoughts write into the same episodic store the
voice already recalls from. NPC↔NPC gossip (memory spec §6) is how
soul-state propagates socially. And because recognition is
sleeve-based, a criminal who resleeves walks past his victims
unrecognized — grudges cling to the abandoned body. Consequence
evasion by resleeving is an emergent mechanic from day one; the
identity spec's cyberbrain/digital-ID seam is its designed counter.

## 4 · Advertisements — the world tells souls what it offers

Venues and objects already exist; they gain a declaration:

```python
obj.db.advertises = {"hunger": 0.8, "social": 0.3}   # Lin's cart
room.db.advertises = {"rest": 1.0}                    # your own cube
```

Discovery = grid query within a radius, scored by
`need_pressure × advertised_value ÷ (1 + distance)`. New venues become
part of NPC life by adding one attribute — no soul code changes. (The
shipped shop/food/rental/bar systems each get their advertisement in
Phase 1 as data, not code.)

## 5 · The think tree

Priority bands, evaluated top-down each think-tick; first band with an
eligible goal wins; within a band, utility ranks:

1. **Survive** — flee active threat, escape fire/damage (hooks the
   existing combat/dispatch machinery; always preempts).
2. **Critical needs** — any meter past its critical threshold.
3. **Schedule/duty** — shift hours at post (time-system blocks: work /
   social / sleep, per role).
4. **Elevated needs** — meters past their soft threshold, by utility.
5. **Idle color** — wander home range, existing ambient behavior.

Satisfied goals are skipped (a fed soul never evaluates eating). The
current patrol system becomes simply the security role's band-3 duty.

## 6 · Jobs — goals decompose into real commands

A chosen goal emits a **job**: an intent plus target plus a step list,
each step a real command through `execute_cmd` / director `travel_to`
(house law — no teleports, no db pokes: NPCs queue at the till like
anyone, and their purchases ring the same economy):

```
job eat_out(target=Lin's cart):
  travel_to(cart.location) → buy skewer → eat skewer
```

Steps can fail (no stock, no cash, blocked path) → the job **faults**:
recorded on the soul (visible in §8 tooling), goal re-ranked next tick.
Interruption law inherits patrols': assigned/fighting/travelling souls
are not nudged; band-1 preempts everything.

## 7 · LOD — souls cost nothing until watched

Tick rate per soul by player proximity (director-owned, like patrols):

| LOD | Condition | think-tick |
|---|---|---|
| hot | player in room/adjacent | every heartbeat |
| warm | player within N cells | ~4× heartbeat |
| cold | nobody near | ~180s, coarse |

Cold souls still act through real commands (the world stays honest; no
offstage teleporting) — they simply think rarely. Ephemeral crowd
NPCs (the census population) stay out of scope: souls are for the
**named and the persistent**; the crowd remains ambience.

## 8 · Tooling is first-class (ship WITH Phase 1, not after)

`@soul <npc>` — the diagnostic: LOD + tick age, need meters, the full
goal ranking with utilities and skip reasons, current job + step
pointer, recent faults. If a soul misbehaves, this command must answer
why in one screen. A `@soul/all` summary lists every ensouled NPC,
LOD, and current goal — the colony's dance card.

## 9 · Build ladder

1. **Core + one colonist** — needs, advertisements on the shipped
   venues, think tree, jobs, LOD, `@soul`. One generic colonist living
   the loop visibly: post → hungry → Lin's till → eat → home → rest.
2. **Named NPCs, carefully** — shopkeepers gain souls with *anchored
   schedules* (shop hours = duty band), so Lin still reliably feeds the
   street but now closes at night, eats, sleeps, visits Sable.
   (Gameplay change: venues close — owner-gated per NPC.)
3. **Mood & thoughts** — RimWorld-style memory offsets (witnessed a
   corpse, slept rough, ate well) summing to mood; mood modulates
   utility and the LLM voice's register (the voice NARRATES a state it
   did not decide). Feeds the existing RAG memory.
4. **Succession & society** — "claim vacant post" as a goal makes
   posts/reincarnation §P2 emergent; faction duties; crime/witness
   goals unify with the dispatch chain.
5. **Gig emission** — the §3.7 externalization: fault/pressure
   thresholds, bounty derivation, board surfacing, favor payout into
   NPC memory. The Butcher/Ripper hand-built gigs become the FLOOR of
   a system that generates its own.

## 10 · Decisions (owner-ruled 2026-08-17)

1. **The economy is REAL.** Tokens move through real wallets and real
   tills; wages pay out of till revenue where a till exists (which
   incidentally gives venue income — #1515 — its collection path).
   Small denominations; the closed loop is the point.
2. **Every NPC is named.** No anonymous predators. Transgressive
   action libraries follow from purpose / faction / standing — a
   nuanced, per-role assignment with room to grow, not a blanket
   residents-vs-named split. (Tone/frequency dials to be tuned in
   play, per-role.)
3. **Residents are generated with curation**, extending the current
   practice: author ROLES (job, home range, faction, disposition
   envelope), generate named NPCs into them from the namebank, curate,
   release.
4. **First named soul: Auntie Lin** (dealer's choice, owner-delegated)
   — richest persona on the busiest corner; her cart closing at night
   creates the third-shift hunger gap on purpose.
5. **The gig system is personified: BLACKBURN, the fixer** (name from
   the bank, coined by the owner). No gig hall required while building
   is paused — emitted gigs flow through Blackburn's book: souls
   externalize goals to Blackburn; players and souls take work from
   him. His person, post, and manner are design-to-come; the mechanism
   lands with the gig-emission phase.
6. **Souls sleep for real, behind real locks.** Overnight they occupy
   their homes — findable, robbable, murderable — protected by the
   existing door-grant/latch machinery, so burglary costs effort and
   feeds the crime chain honestly.
