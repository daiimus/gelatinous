# NPC Needs & Goals — the deterministic soul

> **Status:** 🟢 **Phases 1–3 SHIPPED & LIVE.** P1 engine 2026-08-17
> (#1961 + fixes #1963/#1965/#1967; build 067). P2 named NPCs
> 2026-08-17/18 (#1973; build 068: Lin ensouled, vendor hours,
> keeper-bound counters, Kettle third place, Eli + Bruce). Scale
> hardening P0–P4 (SOULS_SCALE_HARDENING_SPEC; measured live at 104
> souls, reactor flat). **Spec-P3 (§11–12) 2026-08-18** (#1995 + build
> 070/071: thoughts/mood/RAG feed, profiles human/synth/robot, secbot
> #3258 on the charge loop at the lobby fleet cradle; live-soak fixes:
> patrol yields to soul jobs #1997, thought stack cap #1999,
> profile-order tie-break + loud travel stalls #2001, cooldown
> fall-through #2003, jobs remember their planned band #2005 —
> verified: charge and rest meters recover on the cradle/at home).
> **P4a succession LIVE 2026-08-18** (#2009; build 072: five posts
> registered, vacancy watcher, living-claim — first hire Noel Dudnik
> claimed the Kettle day shift unprompted). Remaining: P4b
> crime/witness + rebuild policies (combat-hardening gated), P5 gig
> emission (backburnered). `world/souls/` (needs/actions/jobs/economy/
> engine) + `@soul` diagnostic + closed treasury/wages/tithe loop; first
> generated resident Martha van Schmidt (#8130) living the caretaker
> loop — Brackett lobby post, Unit 1A via the real kiosk, meals at real
> tills. Remaining ladder: P2 named NPCs (Auntie Lin first), P3
> mood/thoughts, P4 succession, P5 gig emission (backburnered). Design
> sections below are unchanged. ELABORATES
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
   did not decide). Feeds the existing RAG memory. Detailed in §11;
   ships together with §12 heterogeneous profiles (bots/synths).
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
5. **Gig emission is BACKBURNERED** (owner call — clarified from an
   earlier misreading). The §3.7 design and ladder phase 5 stand as
   written, but the gig feed is explicitly deferred: phases 1–4 ship
   without it, and no gig venue, board, or broker is designed until
   the owner brings it forward.
6. **Souls sleep for real, behind real locks.** Overnight they occupy
   their homes — findable, robbable, murderable — protected by the
   existing door-grant/latch machinery, so burglary costs effort and
   feeds the crime chain honestly.

## 11 · Thoughts & mood (spec-P3) — the soul notices its own life

A **thought** is a small record the engine emits when something
happens TO the soul — never on a timer (the zero-write law survives):

    (stamp, key, valence, note)
    ("ate_well",      +0.15, "a skewer off Lin's cart")
    ("slept_home",    +0.20, "a night behind my own door")
    ("payday",        +0.25, "the shift paid in full")
    ("shift_unpaid",  -0.35, "worked and the till came up short")
    ("went_hungry",   -0.25, "nothing to eat I could reach or afford")
    ("fled",          -0.40, "ran from trouble")

Emitters live where the events already are: the eat/sleep/linger job
steps, payday (full vs partial), plan-failure faults, the flee step.
The log is capped (~20); each thought's contribution decays with a
half-life (~6 game-hours), so **mood is DERIVED on read** — the
clamped sum of decayed valences around a neutral center, banded for
display (grim / low / level / bright). No mood attribute exists.

**Consumption, phase-3 scope (deliberately narrow):**

1. `@soul` shows mood band + the decayed thought list — the operator
   sees exactly why a soul feels how it feels.
2. **The RAG feed:** for `llm_driven` souls, a thought worth
   remembering (|valence| ≥ 0.2) also becomes an episodic record via
   the existing embed→`make_record`→`prune` path, written with an
   EMPTY subject — the memory module already treats empty-subject
   records as "general" and surfaces them inside any scoped
   conversation when semantically relevant. Lin grumbles about the
   short till to a regular because retrieval found the thought, not
   because anything scripted her to. The two-brain law holds: the
   thought DECIDED nothing; the voice narrates a state the engine
   produced.
3. **No deterministic behavior modulation yet.** Mood gating utility
   (desperation discounts, snap decisions) belongs to the
   transgressive-library work (§9.4+) — wiring it now would be tuning
   a dial nobody can see the consequences of.

## 12 · Heterogeneous profiles — bots and synths in the same fold

The tree, planner, jobs, LOD and economy are need-agnostic; only the
needs TABLE assumed a human. A **profile** makes that table data:

    profile = { need: (rate_per_min, default, planner_shape) }

Planner **shapes** are the small set of ways a need gets satisfied:
`buy_consume` (advertiser + till + eat), `dwell_home` (travel home +
occupy), `dwell_venue` (travel to advertiser + occupy), `post`
(duty), `flee`. Every existing plan is already one of these; profiles
just choose which needs use which.

- **human** — the shipped table, unchanged.
- **synth** (synthetic humanoid species) — same shape as human,
  different dials: hunger at half rate (durable metabolism), rest
  lighter, social unchanged. A synth resident is a human resident
  with slower appetites, not a special case.
- **robot** (security units et al.) — `charge` (the battery: rises
  toward critical over ~12h, satisfied by `dwell_venue` at anything
  advertising `charge`) and `maintenance` (very slow, same dwell). No
  hunger, no social, no rest, no schedule blocks — duty belongs to
  the director (below). Robots hold no wallets in v1; their upkeep is

  **UPDATED 2026-08-24.** The dispatch console was the first `charge`
  advertiser. It no longer advertises anything: a radio bolted to a
  desk is not a docking point, and a flat unit walking to the
  operator's console to plug into it reads as a bug even though it was
  a decision. Charging is the **Boiler Run fleet cradle** in the
  Constabulary lobby and a second rack on the secure 2nd floor.

  **`maintenance` now advertises NOWHERE, deliberately** (owner ruling,
  2026-08-23). The dwell step's maintenance branch also CLEARS a logged
  defect, so any advertiser lets a unit service itself by leaning on a
  wall fitting — which deletes the job a person is meant to do. Units
  will therefore fault weekly with no plan for maintenance. That fault
  is the vacancy for the three-shift mechanic, not a defect in the
  engine.
  the colony's power bill, not a wage.

Profile resolution: explicit `ensoul(..., profile=)` wins; otherwise
derived from species (`robot` → robot, synthetic → synth, else
human).

**The precedence law (one driver at a time):**

    combat  >  director assignment (dispatch/patrol)  >  souls

The souls engine already yields to combat; it now also yields to
`is_assigned` — exactly as the patrol heartbeat does — so a secbot's
patrols and dispatch responses remain director-owned, and its soul
claims the body only when nothing more urgent does (in practice: a
critical battery walks it to the cradle between assignments). Two
systems never fight over one body.

~~**Companions are excluded** from ensoulment for now: Vesper's agentic
tool loop is its own driver, and the handshake between that loop and
a soul belongs to the §3.5 soul↔soul work, not to phase 3.~~

> **REVERSED — owner ruling 2026-08-28:** *"Vesper/Companions can be
> shift workers too."* There is no LLM-NPC exemption from ensoulment.
>
> The paragraph above was wrong about the shape of the thing: an agentic
> tool loop is not a *driver*, it is a voice that happens to be able to
> act. It read as a driver only because it is the one voice with hands.
> The precedence law has three tiers — combat > director > souls — and
> the LLM appears in none of them, by construction.
>
> Cost while it stood: `world/souls/posts.py::_slot_held` carries a
> branch letting an UNSOULED cast member hold a post by presence, so the
> vacancy watcher would not resleeve a second Vesper while the first was
> standing there (#2132). That branch exists only to support this
> exclusion and goes when she is ensouled.

## 13 · Succession, phase P4a — the post survives its keeper

Converges with [`NPC_POSTS_AND_REINCARNATION_SPEC`](../NPC_POSTS_AND_REINCARNATION_SPEC.md)
§1.2–1.3: that spec's post administration and watcher, with the souls
engine supplying the *successor* the original design had to conjure —
a LIVING resident who claims the vacant post, carrying their own
history and an empty book toward the clientele, exactly what the
generator identity was invented to fake.

**Post records** live on the fixture that IS the post — the counter
for venues, the room for roomed posts: `db.post_role`,
`db.post_schedule`, `db.post_wage_rate`, `db.post_policy`
(`successor` | `none`; `resleave` stays with the reincarnation spec's
§P3), `db.post_delay` (vacancy grace before succession),
`db.post_vacant_since`. Registered posts are tagged
(`post`/souls — the indexed path).

**The vacancy watcher** rides the souls heartbeat (staggered, every
~10 beats): a registered post whose keeper is dead, deleted, or
desouled gets stamped vacant. Once `post_delay` elapses under policy
`successor`, the sweep offers the post to the nearest eligible
unemployed soul (human/synth profile, no post, not mid-job) by
handing it a band-2 claim job — travel there for real, then a `claim`
step that binds post/venue/schedule/wage, re-keeps the counter, and
emits a `new_job` thought. One succession per sweep, never while
combat is live at the post (the reincarnation spec's de-confliction
rule). No candidate? The post stays vacant and visibly closed — the
vacancy IS the content until someone arrives to want it.

**The unemployed pool** is just souls without posts — residents
generated into the colony with a cube and thin pockets. Idle and
social by day, first in line when a counter goes dark. (The fuller
`obtain_cash` arbitration — beg/work/mug — belongs to P4b.)

**Deliberately deferred to P4b (gated on a combat-hardening pass):**
the crime/witness chain (Bob's bad night end-to-end), transgressive
action libraries and disposition gates, mood modulating utility, and
the blueprint-rebuild policies (`resleave`, generator fallback) from
the reincarnation spec's own ladder.

## 14 · The rescue loop & the health economy (P4b counterweights)

Owner-ruled 2026-08-19: lethality is not a dial — it is weapon and
damage, emergent. What was missing when four souls bled out unopposed
was the COUNTERWEIGHT: a downed, bleeding body should be a race, not a
certainty. Three layers, cheapest first, each shippable alone:

**Layer 1 — the health drive (the walking wounded self-deliver).**
A `health` need on human/synth profiles whose pressure is DERIVED from
the medical state already stored (bleeding, conditions, organ damage —
zero writes, the purest compute-on-read need). The Maxwell clinic
advertises `treatment`; a conscious wounded soul walks in like a
hungry one walks to a counter.

**The Maxwell model (owner verdict): triage is free, healing is
billed.** The clinic will always stop fatal bleeding, catch the dying,
and run the existing resleeve pipeline — nobody dies on the doorstep.
Restorative treatment costs tokens, paid into Maxwell's own till
(tagged, tithed, wage-paying — the closed loop's health sector). The
`treat` job step: doctor present (keeper rule), fee affordable → pay,
and the DOCTOR treats through the real verbs (bandage/wound care,
doctor-driven `execute_cmd` — messaging and two-brain law intact);
broke → free triage only if actively dying, else the soul limps off
faulted. THE POOR CARRY THEIR BEATINGS — survival is the floor,
wholeness is a purchase.

**Layer 2 — the field medic (the race).** A generated soul hired into
a `medic` post at Maxwell through the SUCCESSION machinery (the post
starts vacant; the watcher staffs it). Response mirrors dispatch: a
witness of a downed body fires a debounced `medical` report on the
real 911 band; the medic's assignment (assignment > souls, the
precedence law) travels them to the scene; stabilization happens
through the same real verbs, in the field, against the bleed clock.
Distance and witnesses decide outcomes: a back-alley stabbing dies, a
market-street one probably lives. Geography is survival odds.

**Layer 3 — transport (the carry).** Dragging is already emergent from
grapple + movement (owner's standing design), and an unconscious body
cannot contest the hold. A secbot — or the medic — grapples and walks
the stabilized casualty to Maxwell, where the stationary doctors and
the AutoDoc take over. The constabulary is also the ambulance service;
a stranded colony does not get to specialize.

Alongside (same verdict set): labor AUTO-SEEDS (the colony keeps a
small unemployed pool, rate-limited, so vacancies re-staff), and
lawless generation SCALES WITH POVERTY (the broke fraction of the
population is the crime dial — the economy itself governs predation).
