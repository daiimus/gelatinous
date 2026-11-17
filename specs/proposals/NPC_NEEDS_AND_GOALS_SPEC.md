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
> crime/witness + the generator fallback (combat-hardening gated), P5 gig
> emission (backburnered). `world/souls/` (needs/actions/jobs/economy/
> engine) + `@soul` diagnostic + closed treasury/wages/tithe loop; first
> generated resident Martha van Schmidt (#8130) living the caretaker
> loop — Brackett lobby post, Unit 1A via the real kiosk, meals at real
> tills. Design
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

> **What the planner does (`actions.plan_for`).** There is no search.
> Each goal has one authored chain of at most four steps, and the
> planner checks its preconditions (cash, stock, an open counter, a real
> route) before handing it out. A plan that cannot be made, or a job
> that faults, cools that goal for fifteen minutes
> (`engine.GOAL_COOLDOWN_SECONDS`) and the soul turns to its next need.
> There is no `mug` action: a `soul_lawless` soul that cannot afford
> food or its craving, and whose mood is below its `violence_gate` dial,
> falls back to one fixed robbery chain (travel, `grapple`, `rob`,
> `disengage`) against the nearest NPC carrying at least 3 tokens that
> is not a robot or a security unit (`_find_mark`). A soul whose traits
> abhor violence or theft takes that chain only when the need is
> critical (`_permits`). 📋 UNBUILT (not decided): the backward-chaining
> planner over an action library with preconditions, effects and costs,
> and a `@soul` readout of why each link bound.

## 3 · Needs

Per-soul decaying meters, 0.0–1.0, ticked by the LOD clock (§7):

| Need | Decays by | Satisfied by (advertisement tags) | Critical behavior |
|---|---|---|---|
| `hunger` | time | food vendors, owned food items | detour to nearest advertiser |
| `rest` | time awake | home (cube/bunk); flop spots 📋 UNBUILT (no issue) | go home; collapse if ignored 📋 UNBUILT (no issue) |
| `social` | time alone | bars, vendors with keepers, crowds | visit a social advertiser |
| `duty` | time off-post during shift | the NPC's own post | return to post |
| `safety` | violence/threat events 📋 UNBUILT (no issue): nothing raises it yet, so its flee is never chosen | distance from threat | flee/report (dispatch seam) |

`cash` is a **resource, not a meter** — earned at posts (wage tick),
spent at tills. Broke NPCs skip paid satisfiers (the poor eat worse:
emergent, free). Mood/thoughts are Phase 3 (§9) — deliberately NOT v1.

> **PARTLY STALE, checked 2026-09-12 (annotation only).** The table
> above is the v1 shape; §12 calls it "the shipped table, unchanged",
> and it no longer matches `world/souls/needs.py::PROFILES`. Two
> differences. **`duty` is not a meter** — it never decays and holds no
> pressure; duty is the §5 band-2 SCHEDULE goal, read off the shift
> clock (`engine.py` returns `(2, "duty")` for a soul with a post on
> shift), and `needs.py::_snapshot` treats a stored `duty` key as a
> legacy artefact to tolerate. **Four derived needs have since joined
> the human (and synth) profile**, all zero-write and computed on read:
> `craving` (shape `vice`, #2076), `wardrobe` (shape `dress`, #2104),
> `health` (shape `clinic`, §14) and `insurance` (shape `insure`, #3667:
> 0.55, the soft threshold, while no sleeve policy in this body's name is on file, a band-3
> want that walks the soul to the Thawn-Harrison lobby terminal in their
> own time; 0.0 once covered, or for a body with no sleeve signature).
> `cash`-as-a-resource and the broke-skip-paid rule both still hold.
> Thresholds are SOFT 0.55 and CRITICAL 0.85 by default; a soul's traits
> can move each threshold and each decay rate (`traits.dial`:
> `soft:<need>`, `crit:<need>`, `rate:<need>`). With no addiction
> overdue, a mood of −0.25 or lower still gives a craving of 0.60 for a
> drink (`needs.craving_state`, #2076).

> **A soul uses what it carries before it buys more (#2244, #3793).**
> `hunger` and `craving` both check the pockets first and name what
> they found: a soul carrying food plans `eat` on it, and a soul
> carrying a ware with the craved substance plans `consume` on it, with
> no trip and no purchase. Food means what it means on a shelf: the eat
> verb works and the ware carries nutrition. Chewing tobacco is eatable
> and is not a meal.
>
> The meal and the vice run are one loop (`jobs._serve_one`):
>
> - **One ware's worth a run.** The ware is the one the plan names
>   (`step["item"]`: what the pocket check found, or what `buy` or
>   `pickup` just handed over through `jobs._hand_on`), else the first
>   one carried. A run takes that ware's servings, at most
>   `SERVINGS_PER_RUN` (12), and ends. It does not empty the pockets.
> - **It says which one**, as a player must: `eat first stew`,
>   `drink first rotgut`.
> - **A serving counts only if it went down**, measured on everything
>   of that kind the soul carries. A refusal is the fault
>   `could not <verb> <ware>`, at once.
>
> Until #3793 only the meal did the second and third, and the vice run
> left 9,849 full mugs of rotgut in NPC inventories.

> **A soul collects what it ordered (#3796).** At a tended counter the
> soul asks (`order`), the keeper sets the ware down a beat later, and
> the soul takes it (`pickup`). A job standing on its `pickup` step has
> something of its own on the counter. Dropped there, the counter holds
> one more ware than anyone is coming for, and nothing brings that
> count back down: a later pickup takes the oldest match but comes with
> an order of its own, so the surplus rotates and never shrinks, and
> the only thing that clears a counter is a person running `clean`. So
> that step is not abandoned (`jobs.order_outstanding`):
>
> - **The think tree waits one step.** A higher band that would replace
>   the job lets it take the pickup first and interrupts on the next
>   think. The ware goes along in the pocket and is the next meal or
>   the next drink, by the rule above.
> - **The job market waits too.** A soul with an order waiting is not
>   offered a post on that sweep.
> - **Emergencies do not wait.** Fleeing (§5's first band, Survive), a
>   dispatched call (`respond`, which runs at that same band) and a
>   casualty recovery replace the job at once, and the order stays
>   where it was set down. Every band below Survive waits, critical
>   needs included.
> - **The wait is bounded** by the pickup's own patience: three rounds
>   for a ware that never comes, then the fault
>   `ordered <ware> and nothing came`.
>
> What an NPC orders is therefore eaten, carried away, or left for one
> of those three emergencies. Before this, a soul called to its shift
> or its bed between the asking and the reaching left the ware behind:
> sixty bowls of stew stood on one counter on 2026-11-13.
>
> What a PLAYER leaves on a counter is not covered. 📋 UNBUILT: the
> keeper wiping stale orders at shift end is #3797 (parked, with the
> owner's constraint that food carried in from elsewhere is never
> cleared).

> **A keeper eats from their own board, on the house (#3802).** Nobody
> can serve a keeper at their own counter: an order is directed speech
> and a body does not hear itself (#2364), so the planner sends a keeper
> who wants serving somewhere else. For a meal that left the keepers of
> the colony's one free kitchen with nowhere to go. A keeper standing
> their shift at a counter whose board has food on it now makes it
> themselves, the way a player behind the counter does: `prepare`, then
> lift it (`pickup`), then eat. Owner ruling 2026-11-13: the keeper's
> meal is **complimentary**, so the purse is not asked and nothing goes
> through the till; the dish is the cheapest on the board. It happens
> when hunger turns critical, because nothing short of that outranks
> the shift, and the counter keeps serving while they eat. The audit
> log records it as `coin ... amount=0 why=staff_meal`.
>
> Food only. A keeper's DRINK at their own bar is still refused by the
> same rule; they can walk to another bar. And a keeper whose post has
> no food on its board is unchanged: they walk to the nearest open
> seller, as every such keeper already does.

> **Food has a quality, a walk has a cost, and one ration may wait in
> the pocket (#3804).** Owner, 2026-11-13: "A number is probably best for
> graded quality so we can expand/grow as we develop the system", and
> "What I want to avoid is someone deep in the currently non-existent
> mines going like 40+ rooms to a restaurant rather then eating a
> ration."
>
> - **Quality** is a number on the food (`food_quality`, read off the
>   item or its prototype, never off a board entry; a food that declares
>   none is ordinary). It is used twice: to weigh a meal
>   against the ration, and to size the `ate_well` lift when the meal is
>   finished, so better food is felt and a ration is felt less.
> - **The walk.** A meal is worth its quality less a little for every
>   room on the real route to it; the ration in the pocket has no way to
>   go. The soul eats whichever is worth more, and a tie goes to the
>   pocket. Nothing says how far "far" is: the distance at which a soul
>   stops walking moves with what is at the end of it, and closes in by
>   itself as kitchens are built nearer.
> - **The hoard rule is untouched (#3793).** Everything a soul carries
>   is still eaten before anything is bought, EXCEPT one kind of item:
>   food tagged as a ration. Only that may wait. Had all pocket food
>   competed on quality, a stew carried off after an interrupted order
>   could have sat behind better meals for ever while each new
>   interruption added another.
> - **One ration.** A soul carries at most one and goes for another, as
>   an idle errand (`provision`, band 4: walk to a source and `buy`,
>   with no `eat`; the purchase is put away with `unwield` in the same
>   beat, since a shop hands it into the buyer's free hand and a job
>   this low is dropped by anything that arrives between two steps,
>   #3808), only when it has none, has no job running, and
>   there is a source in range that is open, within its purse and has a
>   real route to it. The offer and the plan ask one function
>   (`_ration_source`) in the same think from the same room, so the
>   errand is not offered where it cannot be planned. The route is a
>   pathfind, so a NO is remembered on the body for fifteen minutes,
>   room by room; a yes is acted on at once and never remembered. A source advertises `ration`, not `hunger`: a machine
>   is where a pocket is filled, not a place to eat.
> - **The meal named is the meal eaten.** The verb takes one word, and
>   a ration now sits in the pocket beside the meal just bought. A soul
>   asks for its ware by a word nothing else it carries answers to
>   (`jobs._word_for`), so "a chocolate bar" is not eaten as "a ration
>   bar".
>
> The ration is weighed against the ONE meal the soul would otherwise
> walk to; how a soul picks between two kitchens is unchanged
> (advertised value over distance). Every number lives in
> `world/souls/constants.py` and none has had a balance pass: the review
> is #3805.
>
> **The ration is the Longhaul MRE (#3806).** Owner, 2026-11-13: "Let's
> make a MRE." `longhaul_mre` in `world/prototypes.py`: one sitting of
> three doses (what a bowl of stew feeds), quality 2 against an ordinary
> meal's 5, tagged as a ration. Whether a world SELLS one is world data,
> not code: build 171 stocks it, at 0, in the cigarette machine on
> Bhavani Corridor and has that machine advertise `ration`. Where no
> source is in range the errand is never offered and the mechanic does
> nothing. 📋 UNBUILT: a weight against leaving a post on shift, which
> is what would have a keeper reach for the ration before walking off
> to a kitchen, is in #3805.

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

What the game does so far: a soul buys through the real `order` and
`buy` verbs, and robs through `grapple` and then `pickpocket`; the mark
resists only as far as the grapple contest lets it
(`jobs.step_job`). 📋 UNBUILT (no issue): the target's own tree
answering an approach (accepting, refusing, resisting or fleeing).

## 3.6 · Posts, shifts, and consequence continuity

The **post** (from the reincarnation spec) is the continuity spine:
a persistent object with SHIFT SLOTS (day/swing/night), independent of any
occupant. Souls hold assignments; `duty` drives the commute. When a
shift-holder dies en route (see the worked example below), nothing
announces it — the post is simply unstaffed, patron jobs FAULT at the
counter, and the truth propagates only through perception: the next
shift arrives and finds the corpse, the absence, or the looted till,
then reacts per its own tree (report on the real 911 band / grieve /
loot / flee). The vacancy watcher (§13) stamps the slot dark
and, after the grace period and unless the dead keeper's own sleeve
policy brings them back, hands a `claim` job to the nearest unemployed
soul that can walk there. The bar heals, changed. **Worked example (acceptance test):
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
voice already recalls from. A soul does keep an opinion of each person
by apparent identity (`thoughts.add_opinion`: being attacked writes one,
being thanked nudges one), and the voice reads it. 📋 UNBUILT (no
issue): opinion changing any decision, price or flee weight. NPC↔NPC gossip (memory spec §6) is how
soul-state propagates socially. And because recognition is
sleeve-based, a criminal who resleeves walks past his victims
unrecognized — grudges cling to the abandoned body. Consequence
evasion by resleeving is an emergent mechanic from day one; the
identity spec's cyberbrain/digital-ID seam is its designed counter.

## 3.9 · Comms — a soul keeps its radio ready (2026-10-26, #3777)

A handheld in a pocket receives but cannot transmit; one switched off does
neither. Nothing in the tree knew a radio could be *not ready*, so two souls
answered every call with a refusal (#2585). Owner: "If a radio is off - they
should turn it on. This should organically feed into the GOAP system, more or
less."

- **One predicate, `world/souls/comms.py: radio_to_ready(soul)`** — pure; the
  handheld to ready and why (`pocket`, `off`), or None when the soul can already
  transmit (working comms organ; worn/held/seated set that is on and tuned) or
  carries none — and None for what the body cannot do right now, so the tree
  never plans a job that can only fault: a pocket set with no free hand; a set
  on but on no band (nothing tells a soul its home band yet — next slice); a set
  whose key a twin in sight makes unreachable by the bare `toggle` the body
  types (a player narrows a twin with `2nd ...`; keys carry no dash-digits
  since #3779, so that form works). *What it cannot do, it does not want.* This is the single door for
  any future reason to stay silent (a radio-silence order, hiding, a dead
  battery): a clause here, a test beside it, nothing else changes. Future-proof
  by shape, not by flags (owner, same day).
- **Goal `comms`** — band 4 (idle colour, first) whenever the predicate answers,
  so the set gets taken out and turned on on a quiet beat.
- **A refused call is a reflex, not a goal.** `xmit`'s refusal carries
  `verb="transmit"` beside `type="refusal"`; the body sets `db.soul_comms_pending`
  when there is something to ready, and the next `think` spends one beat on
  `ready_beat` before arbitration — like `notice_casualty` — then carries on with
  whatever it was doing. Not a preemption: a goal that interrupted the running
  job would drop a courier's run or a unit's recovery for a radio (nothing
  re-plans those), and a player mid-errand simply takes the radio out while
  walking. The flag clears itself when nothing is left to ready.
- **`ready_beat`**, shared by the reflex and the idle job — one real command per
  beat: `wield <radio>`, then `toggle <radio> on`; ready when the predicate
  answers None; gives up after three beats in the same state (the idle job then
  faults with the usual cooldown; the reflex just stops).
- **Scripted voices ready their own set.** The courier's crane call
  (`world/director/courier.py: call_the_crane`) already switched the handset on
  and tuned it; it now takes it out of the pocket first, and its evidence check
  reads the hand. A pocketed handset had meant every crane call refused and
  every run faulted.
- Not here: retrying the words a refusal lost; turning a radio off; organs and
  consoles (already ready).

## 4 · Advertisements — the world tells souls what it offers

Venues and objects already exist; they gain a declaration:

```python
obj.db.advertises = {"hunger": 0.8, "social": 0.3}   # Lin's cart
```

Rest is not advertised: a soul sleeps only in its own home
(`db.soul_home`, `actions.plan_for`).

Discovery: every object tagged `advertiser` (category `souls`) whose
`db.advertises` names the need, within 30 cells (the larger of the x and
y differences, plus the level difference), scored
`advertised_value ÷ (1 + distance)`, then kept only if the soul has a
real route to it as itself (`actions._advertisers`, `_reachable_only`).
Need pressure picks the goal, not the venue. A fixture with
`db.advertise_staffed` offers only while a keeper is standing the
running shift there; one with `db.advertise_scope = "room"` serves only
someone in that room or someone whose home it is. New venues become
part of NPC life by adding one attribute — no soul code changes. (The
shipped shop/food/rental/bar systems each get their advertisement in
Phase 1 as data, not code.)

## 5 · The think tree

Priority bands, evaluated top-down each think-tick; first band with an
eligible goal wins; within a band, the highest pressure wins and ties go
by profile order. Band numbers are the code's (`engine._desired_goal`,
`_goal_band`); the lowest wins:

0. **Survive** — flee when `safety` passes its critical threshold, and a
   dispatched call (a `respond` job, planned at this band). Preempts
   everything. 📋 UNBUILT (no issue): nothing raises `safety` yet (§3).
1. **Critical needs** — any profile need past its critical threshold,
   except `wardrobe`.
2. **Schedule** — first, being undressed (`wardrobe` at 1.0); then the
   shift (`on_duty`: the work block of the soul's `day` 06–14, `swing`
   14–22, `night` 22–06 or `always` schedule, plus up to an hour past its
   end covering until the next keeper arrives, `HOLDOVER_HOURS`); then
   sleep (the sleep block, for a soul with a home, once rest is 0.30 or
   more). Each soul reads the clock with its own offset of up to ±15
   minutes (`shift_jitter_hours`). Work handed out inside a shift (a
   courier's run, a unit's recovery) and a post claim also run at this
   band.
3. **Elevated needs** — any profile need past its soft threshold.
4. **Idle** — in order: ready a radio (`comms`), leave the post after the
   shift for a perch or home (`off_duty`), hunt an intruder (security
   units), put a ration in an empty pocket (`provision`), walk the patrol
   beat. Otherwise the soul does nothing.

Satisfied goals are skipped (a fed soul never evaluates eating), and so
is a goal whose plan failed in the last fifteen minutes. Patrol is idle
work: the director supplies the route and the soul walks it (#2373).

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
Interruption law: a soul in combat does not think, except to carry on
its robbery steps. A running job is replaced only by a goal in a
strictly better band than the one it was planned under, and the
replacement stops its feet. Band 0 (Survive, and a dispatched call)
preempts everything. Every band below it holds
one step through an interruption: a soul that has ordered at a counter
collects the order first, and only Survive does not wait for that
(§3, #3796).

## 7 · LOD — souls cost nothing until watched

Think rate per soul by player proximity, computed by the souls heartbeat
(one beat every 30 s, `engine.lod_for`):

| LOD | Condition | think-tick |
|---|---|---|
| hot | a player in the same room | every beat |
| warm | a player within 5 cells on the same level (`WARM_RADIUS`) | every 2nd beat (~60 s) |
| cold | nobody near | every 6th beat (~180 s) |

A soul with a stimulus waiting (`salience.pending`) thinks on the next
beat whatever its LOD.

Cold souls still act through real commands (the world stays honest; no
offstage teleporting) — they simply think rarely. Ephemeral crowd
NPCs (the census population) stay out of scope: souls are for the
**named and the persistent**; the crowd remains ambience.

## 8 · Tooling is first-class (ship WITH Phase 1, not after)

`@soul <npc>` (Builders) — the diagnostic: role, profile, schedule, LOD,
mood and the decayed thoughts, traits, home, post and till, tokens and
wages owed, every need's pressure against the default soft and critical
thresholds, goals cooling down, the running job's goal and step, and the
last faults. If a soul misbehaves, this command must answer why in one
screen. 📋 UNBUILT (no issue): the goal ranking with utilities and skip
reasons, and the tick age. `@soul` alone is a colony dashboard (souls,
posts manned and open, economy, mood, health alarms); `@soul all` lists
every soul's goal, LOD, hunger, rest, tokens, fault count and location,
and raises an error when any soul has the robot profile, which has no
hunger or rest.

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
display (grim / low / level / bright). No mood attribute exists. At most
three thoughts of one key are kept (`STACK_CAP`), so a lasting condition
reads as one misery. A wound (acting against one's own nature, or any
thought recorded as one) fades with a three-day half-life. Mood bands:
bright from +0.25, level from −0.10, low from −0.40, grim below.

**Consumption, phase-3 scope (deliberately narrow):**

1. `@soul` shows mood band + the decayed thought list — the operator
   sees exactly why a soul feels how it feels.
2. **The RAG feed:** for `llm_driven` souls, a thought worth
   remembering (|valence| ≥ 0.2) also becomes an episodic record via
   `world.llm.memory.remember` (an embedding, then deduplicate, store and
   prune; only while the LLM is enabled), so a repeated thought
   strengthens one memory rather than filling the budget with copies,
   written as "I remember: <note>." with an
   EMPTY subject — the memory module already treats empty-subject
   records as "general" and surfaces them inside any scoped
   conversation when semantically relevant. Lin grumbles about the
   short till to a regular because retrieval found the thought, not
   because anything scripted her to. The two-brain law holds: the
   thought DECIDED nothing; the voice narrates a state the engine
   produced.
3. **Mood gates two decisions, and nothing else.** A `soul_lawless`
   soul turns to robbery only while its mood is below its
   `violence_gate` dial (`actions.plan_for`), and a mood of −0.25 or
   lower gives a pull toward a drink with no habit behind it
   (`needs.craving_state`). 📋 UNBUILT (no issue): mood weighing any other
   choice (desperation discounts, snap decisions).

## 12 · Heterogeneous profiles — bots and synths in the same fold

The tree, planner, jobs, LOD and economy are need-agnostic; only the
needs TABLE assumed a human. A **profile** makes that table data:

    profile = { need: (rate_per_min, default, planner_shape) }

Planner **shapes** are the small set of ways a need gets satisfied:
`buy_consume` (advertiser + till + eat), `dwell_home` (travel home +
occupy), `dwell_venue` (travel to advertiser + occupy), `vice` (the
craving), `dress` (wardrobe), `clinic` (health), `insure` (insurance),
`graze` (eat off a serving fixture) and `flee`. Duty has no shape: it is
the schedule band's goal, planned directly (`actions.plan_for`).
Profiles choose which needs use which.

- **human** — the §3 table, with the derived needs listed under it.
- **synth** (synthetic humanoid species) — same shape as human,
  different dials: hunger at half rate (durable metabolism), rest
  lighter, social unchanged. A synth resident is a human resident
  with slower appetites, not a special case.
- **robot** (security units et al.) — `charge` (the battery: rises
  toward critical over ~12h, satisfied by `dwell_venue` at anything
  advertising `charge`) and `maintenance` (very slow, same dwell), and
  `health`, derived from its medical conditions, which sends a unit to
  whatever advertises `repair` rather than `treatment`
  (`needs.CLINIC_SERVICE`, #2262). No hunger, no social, no rest. A
  unit's schedule is `always`: its shift never ends and it never sleeps
  (`engine.SCHEDULES`); its post, dispatched calls, patrol and hunt are
  soul jobs (the precedence law below). Robots hold no wallets in v1; their upkeep is
  the colony's power bill, not a wage.

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

  **Maintenance is now offered by one STAFFED fixture (#2261):** the
  service bench in the Constabulary secure corridor advertises it with
  `db.advertise_staffed`, so it serves only while a mechanic is standing
  the running shift there (`actions._advertisers`). Off shift the need
  has no plan, and that fault is the vacancy.

- **recluse** — every need met inside a sealed home, and given only by
  an explicit profile, never from species. Hunger is eaten with the real
  `eat` verb off a serving fixture (`graze`, #2074), rest is taken at
  home, and social is a `dwell_venue` advertiser that serves only its
  own room (`advertise_scope`, #2096).

Profile resolution: explicit `ensoul(..., profile=)` wins; otherwise
derived from species (`robot` → robot, synthetic → synth, else
human).

**The precedence law (one driver at a time):**

    combat  >  souls

Combat owns the body: a soul in combat does not think, except to carry
on its robbery steps (`grapple`, `rob`, `disengage`), which are made to
run inside a fight (`engine.think`). Otherwise the souls engine drives,
and director work arrives as jobs: a dispatched call is a `respond` job
planned at the Survive band, so nothing outranks it (#2384); a patrol
beat and a hunt are idle-band goals whose route and rules stay in the
director (#2373). Two systems never fight over one body.

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
>
> **DONE, checked 2026-09-12 — it went.**
> `scripts/builds/139_vesper_takes_the_shift.py` ensouled her through
> the ordinary `do_claim` path and removed the branch in the same
> change, as the last piece of the population merge (issue #2362, which
> stays open for the broader ambient-crowd work). `_slot_held` now
> records "a post keeper is a soul" as an invariant, and an unsouled
> keeper is a build error. (A later branch from #2178 lets a SOULED
> keeper with no recorded `soul_post` hold a slot by standing in it —
> the Rook in his own booth — which is a different rule, not this one.)

## 13 · Succession, phase P4a — the post survives its keeper

Converges with [`NPC_POSTS_AND_REINCARNATION_SPEC`](../NPC_POSTS_AND_REINCARNATION_SPEC.md)
§1.2–1.3: that spec's post administration and watcher, with the souls
engine supplying the *successor* the original design had to conjure —
a LIVING resident who claims the vacant post, carrying their own
history and an empty book toward the clientele, exactly what the
generator identity was invented to fake.

**Post records** live on the fixture that IS the post — the counter
for venues, the room for roomed posts: `db.post_role`,
`db.post_wage_rate`, `db.post_policy` (`successor`; any other value
leaves a stranger's slot dark; whether the named keeper returns is their
own sleeve policy's business, #3667), `db.post_delay` (vacancy grace
before succession, six hours by default, `DEFAULT_DELAY`; 0 means at
once), `db.post_slots` (one slot per shift, each with its `keeper` and
`vacant_since`) and `db.post_blueprints` (shift → the named person who
owns it). Registered posts are tagged
(`post`/souls — the indexed path).

**The vacancy watcher** rides the souls heartbeat (staggered, every
~10 beats): a registered post whose keeper is dead, deleted, or
desouled gets stamped vacant. Once `post_delay` elapses, a shift
that names a keeper (`post_blueprints`) first waits on that keeper's own
sleeve policy (`posts._try_resleave`, #3667). Otherwise, under policy
`successor`, the sweep offers the shift down the list of unemployed
souls, nearest first: not a robot, not pinned, with no post, not on a
hunger, flee or claim job, and with no order waiting on a counter
(leisure does not count as busy). The first one who can walk there gets
a band-2 claim job — travel there for real, then a `claim`
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
the crime/witness chain (Bob's bad night end-to-end) and the generator
fallback from the reincarnation spec's own ladder. What the game does
meanwhile: a `soul_lawless` soul that cannot afford food or its craving
robs when its mood is below its `violence_gate` dial (§2); traits that
abhor violence or theft hold until the need is critical, and acting
against them leaves a guilt thought that fades over days
(`jobs._conscience`); a dead keeper with a sleeve policy on file is
brought back (`posts._try_resleave`).

## 14 · The rescue loop & the health economy (P4b counterweights)

Owner-ruled 2026-08-19: lethality is not a dial — it is weapon and
damage, emergent. What was missing when four souls bled out unopposed
was the COUNTERWEIGHT: a downed, bleeding body should be a race, not a
certainty. Three layers, cheapest first, each shippable alone:

**Layer 1 — the health drive (the walking wounded self-deliver).**
A `health` need on human/synth profiles whose pressure is DERIVED from
the stored medical conditions: 0.12 for each condition, plus 0.35 while
any of them is bleeding (`needs.health_pressure`; zero writes, the
purest compute-on-read need). The Maxwell clinic
advertises `treatment`; a conscious wounded soul walks in like a
hungry one walks to a counter.

**The Maxwell model (owner verdict): triage is free, healing is
billed.** The clinic will always stop fatal bleeding, catch the dying,
and run the existing resleeve pipeline — nobody dies on the doorstep.
Restorative treatment costs tokens, paid into Maxwell's own till
(tagged, tithed, wage-paying — the closed loop's health sector). The
`treat` job step: someone in the room holding the doctor job
(`service.job_of`) treats through the real verbs (`world.clinic.treat`,
doctor-driven `execute_cmd` — messaging and two-brain law intact). The
clinic bandages first and bills after: 8 tokens (`TREAT_FEE`) into the
clinic's till, and a painkiller for a soul that paid. A soul that cannot
pay is bandaged free if it is bleeding, and otherwise leaves faulted
with a `turned_away` thought. A clinic with nothing to treat with turns
the soul away without charging. After a visit, `health` is not chosen
again for 30 minutes. THE POOR CARRY THEIR BEATINGS — survival is the floor,
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

## 15 · Pinned souls — frozen in time (owner ruling 2026-09-14, shipped #3507)

A **pinned** soul keeps everything that makes it a person — persona, needs,
memory, the soul tag — but the engine leaves it alone: **no need decay, no
thinking, no planning, no walking.** It stands where it was pinned until a
GM puppets it or a developer tests against it.

Mechanics (`world/souls/engine.py` `pin` / `unpin` / `is_pinned`):
* `pin()` stops any walk (`director.travel.stop_travel`), drops the running
  job, steps away from any counter (`_release_placement`), materializes the
  needs at their current pressure and stamps the clock. While
  `db.soul_pinned` holds, `needs._snapshot` reports **zero elapsed minutes**,
  so every derived pressure reads exactly what it was at the pin.
* The heartbeat's `_beat_soul` returns before wages, wear or thinking;
  `think()` itself returns for a pinned soul (salience and direct callers
  included).
* `unpin()` re-stamps `soul_needs["_at"] = now`: the frozen interval is
  never paid back as a lump of hunger.
* `@pin <npc>` / `@unpin <npc>` (Builders+, `commands/CmdPin.py`) act on
  souls only. A body an account owns, or one holding Builder permissions,
  is refused no matter who asks. `@pin` alone lists the pinned.

**`@spawnmob` makes pinned people (#3506).** `/human` (and a bare
`@spawnmob`) and `/synth` build a whole person the way the colony builds
everyone: the civilian factory's random archetype for the species
(persona, voice, wardrobe, stock — `spawn_civilian(role, here,
drift=False)`: no director tag, no haunts), the shuttle arrival's rolled
personhood (`souls.population.roll_person`: style, presentation, traits,
designation, skills), `ensoul(role=<archetype>, home=None, post=None)` —
**no cube, no job** — then `pin()`. `/blank` is gone; `/rat` and `/robot`
are bodies; `/secbot` is the production factory door. Every spawner writes
species through one helper, `world.anatomy.apply_species`.

