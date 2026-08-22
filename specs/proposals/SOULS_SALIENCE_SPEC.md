# Souls Salience — letting the world interrupt a soul

**Status:** proposed 2026-08-22, building now (#2228)
**Depends on:** `world/souls/engine.py` (band tree, LOD), `world/souls/jobs.py`

---

## 1. The gap

Every goal a soul can form is derived from its own internal state:
needs pressure, the clock, whether it holds a post. `_desired_goal` is
a pure function of the soul. **Nothing in the world can put something
in front of a soul.**

Second, thinking is LOD-gated for cost: hot souls (a player in the
room) think every 30s beat, warm every other, cold every sixth — about
three minutes.

Those two combine badly for any work whose trigger arrives from
*elsewhere*. Dispatch is the clean example: a distress call reaches the
operator by radio from someone who is, by definition, not standing next
to her. Being alone at her desk is exactly what makes her cold. Routed
through the ordinary beat, a shots-fired call is judged somewhere
between 30 seconds and 3 minutes later, and the units roll that late.

There is a third edge: the band tree is `survive > critical needs >
schedule duty > elevated needs > idle`, and a running job is only
interrupted by a strictly lower band number. Duty sits *below* critical
needs, so a hungry dispatcher mid-meal lets the emergency band ring.

This is not a dispatch problem. It is the same shape as a scream
through a wall, a fire alarm, a shot fired in the next room, a customer
walking into an empty shop. The souls engine has no sensory inbox.

## 2. How the reference implementations handle it

All three separate **routine cadence** from **event response**, and
none of them rely on the tick for emergencies.

**F.E.A.R.** (Orkin's GOAP) — each AI has *sensors* writing into
*working memory*. Sensors that can be event-driven are: damage, sound,
a body seen. They push a fact into working memory the moment it
happens. The planner re-evaluates when working memory changes, not on
a fixed slow poll. Polling is reserved for things that genuinely must
be sampled (line of sight).

**RimWorld** — pawns walk a `ThinkTree` when their current job ends,
*plus* explicit job-override checks fired by events (danger, a downed
colonist, incapacitation). The tree walk is the routine; the override
call is the interrupt.

**The Sims** — routine is utility scoring against nearby "smart object"
advertisements on a tick. Emergencies (fire, burglar) are *pushed
interactions* that preempt the action queue outright.

The shared pattern: **the tick is a cost-control mechanism for routine
decisions; salient events bypass it and force immediate re-evaluation.**
Our LOD is exactly such a cost-control mechanism, and it currently has
no bypass. That is the whole of the gap.

## 3. Design

A **stimulus** is something the world hands a soul. Three properties:

| field | meaning |
|---|---|
| `kind` | what happened (`"radio_traffic"`, `"casualty"`, …) |
| `band` | urgency, on the SAME scale as the goal tree (0 = survive) |
| `payload` | opaque dict the handler understands |

### 3.1 The inbox

`world/souls/salience.py`:

- `notice(soul, kind, band, payload=None)` — append to the soul's
  inbox and **force a think on the next reactor turn**.
- `pending(soul)` / `drain(soul, kind=None)` — read / consume.
- `top_band(soul)` — the lowest (most urgent) band pending.

The inbox lives on `ndb`. A stimulus is a thing that is happening now;
if the server reloads, the moment has passed, and a soul waking to a
queue of stale alarms is worse than one that missed them.

Bounded (`MAX_STIMULI`) — a soul standing next to a busy radio must
not accumulate an unbounded list. Oldest drops first.

### 3.2 Defeating LOD

Two paths, deliberately:

1. **Immediate** — `notice()` schedules `think()` on the next reactor
   turn (`delay(0, ...)`, not an inline call, so a stimulus raised
   during radio delivery cannot re-enter the delivery loop).
2. **Beat-level backstop** — `_beat_soul` thinks when stimuli are
   pending regardless of the LOD cadence. This catches anything the
   immediate path dropped, and caps worst-case latency at one beat.

LOD keeps doing its job: it governs how often a soul thinks *about
itself*. It no longer governs how fast the world can reach it.

### 3.3 Arbitration — designed, deliberately NOT wired

The intent: the tree computes its normal `(band, goal)`, the inbox
offers `(band, goal)`, the lower band wins, ties to the stimulus — the
world is more urgent than a slowly-rising need at the same band. Every
stimulus carries its band for exactly this, because only the raiser
knows whether it was gunfire or gossip.

**It is not connected**, and shipping it half-connected would be a bug.
Preempting a running job means `plan_for` must know how to satisfy the
stimulus's goal, and no stimulus has one yet: the first consumer's work
happens *inside* the shift it belongs to (§3.4). A first draft of this
synthesised `"duty"` whenever the inbox outranked an idle tree, which
would have marched an off-shift soul to work at three in the morning
because somebody keyed a mic.

So today a stimulus has exactly one power: **defeating LOD**. That is
the whole of the reported gap. Preemption lands with the sensor that
needs it — a scream while you are eating — and that sensor brings its
goal and its plan with it.

### 3.4 Doing the work

Most stimuli do not need a goal of their own. Answering the radio *is*
a dispatcher's duty, not an interruption of it. So the default path is:

> stimulus forces a think → the running `duty` job survives arbitration
> → `step_job` runs its `work` step → the work step **drains the inbox**
> through a role handler.

That keeps the job model intact and gives the role handlers a real
home. `restock_medic` — bolted into the work step as a special case
before GOAP existed — becomes one of these, rather than the only one.

A stimulus that must genuinely preempt (a scream while you are eating)
declares a band low enough to interrupt, and `plan_for` gives it a job.
Not needed by the first consumer; the mechanism is there for the second.

## 4. First consumer: dispatch

Radio delivery already walks every listener it reaches. The sensor
hangs there — `salience.sense_radio(listener, heard, speaker, freq)` —
and fires only for a soul who is **seated at a base station on that
band**:

    notice(listener, "radio_traffic", WORK_BAND,
           payload={"speech": ..., "speaker": ..., "board": ...})

Hanging it off delivery rather than off a device or a typeclass means
it is the *hearing* that senses, which is what a sense is. It also
means the words sensed are the words that were **caught** — degraded
traffic dispatches on the fragments that arrived, not on what was said.

`seated_base_station` is the whole qualification: whoever holds the
chair holds the voice. No post registration, no flag on any NPC, no
typeclass — a relief operator, a successor, or a resleeved keeper is
the dispatcher the moment they sit down.

The dispatch work handler judges the call deterministically
(`classify_report` → `apply_verdict`) and stashes the outcome for the
voice to narrate. The two-brain law holds: **the souls layer decides,
the model only says.**

Nobody in the chair means nothing is noticed, nothing is judged, and
nothing rolls. That is the ruling (2026-08-22) made structural rather
than enforced by a check.

## 5. Deliberately out of scope

- **Folding `restock_medic` into the handler registry.** It should
  happen; it is a behaviour-neutral refactor and belongs in its own
  change.
- **Sensory stimuli** (a scream heard through a wall, a body seen).
  The inbox is the substrate for these; the sensors are separate work.
- **Player-facing salience.** This is an NPC mechanism.
