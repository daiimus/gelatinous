# Souls Salience — letting the world interrupt a soul

Salience is the souls engine's sensory inbox (#2228). The world hands a
soul a **stimulus**; the soul gets one prompt wake that does its post's
inbox work and lets it think, whatever its LOD cadence. Stimuli take no
part in goal arbitration: that is designed and deliberately not wired
(§3.3). The first consumer is dispatch (§4).

The code is `world/souls/salience.py`, built on `world/souls/engine.py`
(band tree, LOD) and `world/souls/jobs.py`.

## 1. The gap

Every goal a soul can form is derived from its own internal state:
needs pressure, the clock, whether it holds a post. `_desired_goal` is
a pure function of the soul. Without the inbox, **nothing in the world
can put something in front of a soul.**

Second, thinking is LOD-gated for cost: hot souls (a player in the
room) think every 30s beat, warm every other, cold every sixth — about
three minutes.

Those two combine badly for any work whose trigger arrives from
*elsewhere*. Dispatch is the clean example: a distress call reaches the
operator by radio from someone who is, by definition, not standing next
to her. Being alone at her desk is exactly what makes her cold. Routed
through the ordinary beat, a shots-fired call would be judged somewhere
between 30 seconds and 3 minutes later, and the units would roll that
late.

There is a third edge: the band tree is `survive > critical needs >
schedule duty > elevated needs > idle`, and a running job is only
interrupted by a strictly lower band number. (Exception, #3796: a soul
standing at a pickup for something it ordered collects it first, unless
the interrupt is survival.) Duty sits *below* critical needs, and with
arbitration unwired (§3.3) the inbox does not change that ordering. What
the inbox does is drain outside the job (§3.4): a hungry dispatcher who
eats *in the chair* judges the call anyway. One whose meal takes her out
of the chair senses nothing at all — that is the §4 ruling, not this
edge.

This is not a dispatch problem. It is the same shape as a scream
through a wall, a fire alarm, a shot fired in the next room, a customer
walking into an empty shop. The souls engine needs a sensory inbox;
§3 is that inbox.

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
Our LOD is exactly such a cost-control mechanism; the inbox (§3) is
its bypass.

## 3. Design

A **stimulus** is something the world hands a soul. Three properties:

| field | meaning |
|---|---|
| `kind` | what happened (`"radio_traffic"`, `"casualty"`, …) |
| `band` | urgency, on the SAME scale as the goal tree (0 = survive) |
| `payload` | opaque dict the handler understands |

### 3.1 The inbox

In `world/souls/salience.py`:

- `notice(soul, kind, band=WORK_BAND, payload=None)` (`WORK_BAND` = 2,
  the band of `duty`) — append to the inbox and schedule one wake on the
  next reactor turn. While a wake is pending, further stimuli join the
  inbox without scheduling another, so a flood of transmissions costs one
  wake, which drains them all. The wake does the post's inbox work and,
  for a soul, then thinks. `notice` never raises; it returns False when
  it cannot accept the stimulus.
- `pending(soul)` / `drain(soul, kind=None)` — read / consume.
- `top_band(soul)` — the lowest (most urgent) band pending.

The inbox lives on `ndb`. A stimulus is a thing that is happening now;
if the server reloads, the moment has passed, and a soul waking to a
queue of stale alarms is worse than one that missed them.

Bounded (`MAX_STIMULI` = 8) — a soul standing next to a busy radio must
not accumulate an unbounded list. Oldest drops first.

### 3.2 Defeating LOD

Two paths, deliberately:

1. **Immediate** — `notice()` schedules the wake (`_think_now`) on
   the next reactor turn (`delay(0, ...)`, not an inline call, so a stimulus raised
   during radio delivery cannot re-enter the delivery loop).
2. **Beat-level backstop** — `_beat_soul` makes a soul think on any
   beat where stimuli are pending, whatever its LOD cadence. That think
   drains the inbox only when it steps the `work` step of the soul's
   `duty` job at its post. A player in the chair has no backstop: for a
   player the wake is the only path.

LOD keeps doing its job: it governs how often a soul thinks *about
itself*. It does not govern how fast the world can reach it.

### 3.3 Arbitration — designed, deliberately NOT wired

The design: the tree computes its normal `(band, goal)`, the inbox
offers `(band, goal)`, the lower band wins, ties to the stimulus — the
world is more urgent than a slowly-rising need at the same band. Every
stimulus carries its band for exactly this, because only the raiser
knows whether it was gunfire or gossip.

**It is not connected**, and shipping it half-connected would be a bug.
Preempting a running job means `plan_for` must know how to satisfy the
stimulus's goal, and no stimulus has one yet: the first consumer's work
is done on the wake itself and needs no goal (§3.4). Synthesising
`"duty"` whenever the inbox outranked an idle tree would march an
off-shift soul to work at three in the morning because somebody keyed a
mic.

So a stimulus takes no part in goal arbitration. Its one power is
**defeating LOD**: the seated occupant's inbox work is done now, and a
soul thinks now, instead of on the LOD cadence. That is the whole of the
reported gap. Preemption lands with the sensor that needs it — a scream
while you are eating — and that sensor brings its goal and its plan
with it.

### 3.4 Doing the work

Most stimuli do not need a goal of their own. Answering the radio *is*
a dispatcher's duty, not an interruption of it. So the default path is:

> stimulus → the wake (`_think_now`, next reactor turn) does the post's
> inbox work at once (`work_stimuli`) for whoever is seated, on shift or
> not, soul or player → then, if the occupant is a soul, it thinks. The
> `work` step of a running `duty` job drains the inbox again as the
> backstop.

The `work` step runs `salience.do_post_work`, which does two things.
First the role's standing upkeep from `ROLE_WORK` (#2236), keyed by
`db.soul_role`: the medic's restock, the courier's runs, the mechanic's
bench service. Each role's upkeep is a registry entry, not a hard-coded
branch in the work step. These run every work beat, stimulus or not.
Then `work_stimuli`, which drains the inbox. Only `radio_traffic` is
handled there, by `_work_radio_traffic`, whatever the occupant's role.

A stimulus that must genuinely preempt (a scream while you are eating)
declares a band low enough to interrupt, and `plan_for` gives it a job.
Not needed by the first consumer; the mechanism is there for the second.

## 4. First consumer: dispatch

Radio delivery already walks every listener it reaches. The sensor
hangs there — `salience.sense_radio(listener, heard, speaker, freq)` —
and fires for whoever is **seated at a powered base station tuned to
the emergency band** (`EMERGENCY_BAND`, 911MHz), soul or player, and
only when they are conscious and can hear. Traffic from an NPC, an
LLM-driven body or a base station never raises work (the loop guard:
witness reports and unit acks already carry their own dispatch). A
board on any other band raises nothing (#2773):

    notice(listener, "radio_traffic", WORK_BAND,
           payload={"speech": <first 400 characters caught>,
                    "speaker": ..., "board": ..., "frequency": ...})

Hanging it off delivery rather than off a device or a typeclass means
it is the *hearing* that senses, which is what a sense is. It also
means the words sensed are the words that were **caught** — degraded
traffic dispatches on the fragments that arrived, not on what was said.

`seated_base_station` is the whole qualification of the person: whoever holds the
chair holds the voice. No post registration, no flag on any NPC, no
typeclass — a relief operator, a successor, or a resleeved keeper is
the dispatcher the moment they sit down.

The dispatch work handler judges the call deterministic first:
`classify_report` reads the words in plain code, and only when it
recognises nothing, and the civic model lane is up (`civic_enabled`),
does the model classify the call. Either verdict goes through
`apply_verdict`, which opens a call record (#2246), raises the event and
rolls units. The outcome (the verdict, how many units went, the units
available, the caller's description of the suspect (#2249)) is stashed
on the occupant as `ndb.dispatch_verdict`, and only then does a soul's
voice (`answer_traffic`) reply. A player has no `answer_traffic` and
replies by speaking. The two-brain law holds: **the souls layer decides
what rolls; the model may read a call the plain reader missed, and
otherwise only says.**

Nobody in the chair means nothing is noticed, nothing is judged, and
nothing rolls. That is the ruling (2026-08-22) made structural rather
than enforced by a check.

The post also constrains speech. `filter_for_duty`, on the NPC transmit
path, runs the line of whoever is seated at an emergency-band board
through `desk_discipline`: no announcing units that did not roll (read
from the stashed `ndb.dispatch_verdict`), no promising to leave the
chair. Everyone else's words pass untouched. The rule hangs on the post,
not on the NPC brain.

## 5. Deliberately out of scope

- **Goal arbitration** — designed, deliberately not wired (§3.3).
- **Sensory stimuli** (a scream heard through a wall, a body seen).
  The inbox is the substrate for these; the sensors are separate work.
- **Player-facing salience.** The inbox serves whoever holds the post, a
  player included, but only to get the post's work done; it never prompts
  a player.

## Related

- `world/souls/engine.py` — band tree, LOD, `_beat_soul`.
- `world/souls/jobs.py` — jobs.
- `world/souls/actions.py` — `plan_for`.
- `world/souls/salience.py` — the inbox, `sense_radio`, `do_post_work`,
  `ROLE_WORK`, `work_stimuli`, `filter_for_duty`.
