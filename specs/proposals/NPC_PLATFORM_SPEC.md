# NPC Platform Spec

Every NPC in the colony is one body on one platform. The body is the only
class; the mind (soul), the job and the voice are data layered onto it. The
souls engine drives every souled body, the director hands out work, and no mechanic
lives behind a model turn. This document holds the requirement in the owner's
words, the layers, the laws, the definition the platform is held to, and the
two designs whose reasons cannot be read from the code: why the hunt sits at
band 4, and how dispatch reaches a unit as a job.

## 1 · The requirement, in the owner's words

Owner requirement (2026-08-28): *"one NPC platform with various
sub-components"*, everything built so far connected under **one
hierarchy**. This document exists because that requirement was discussed at
length and never written down, which made "have we met it?" unanswerable. §5
is the definition that answers it.

> *"I feel like our end goal is for everything to be a 'soul-job
> holder'. Why have our NPCs divided, right? **Everything should ride
> the automatic system and *some* NPCs get more of a LLM back hook**."*

> *"We need standardization not unique designed."*

> *"Shouldn't the soul and director be unified?"*

## 2 · The layers

An NPC is **one body** wearing four layers. Three of them are DATA;
only the body is a class.

| layer | what it is | mechanism | composable |
|---|---|---|---|
| **body** | `Character` | typeclass | substrate — medical, identity, hands |
| **mind** | soul | indexed tag + `soul_*` | yes — `ensoul()` / `desoul()` |
| **job** | what you do at a post | `world/service.py` registry, keyed by `post_role` | yes |
| **voice** | persona + brain | `db.llm_driven` + persona seed, code in `LLMNpcMixin` | yes — **optional** |

**The mind is the base. The voice is the hook.** The soul is not an optional
add-on to a voiced NPC; the voice is the optional hook on a souled body, as
the requirement in §1 asks.

## 3 · Laws

1. **One driver per body.** The souls engine drives. The director is a
   *source of work*, not a second walker (#2373). Two things take a body
   away from the souls engine: a fight (while the body is in combat,
   `think()` steps only the crime steps `grapple`, `rob` and `disengage`),
   and pinning (`engine.pin`: a pinned soul does not think and is not
   dispatched; `@spawnmob` makes pinned people).
2. **Competence belongs to the post, not the person.** An ability
   bolted to a typeclass cannot be inherited by whoever takes the shift
   next (`AnsweringFixture`, #2350, #2352).
3. **A post keeper is a soul** (#2362).
4. **Souls decide; the LLM voices.** The two-brain law. No mechanic may
   exist only behind a model turn.
5. **No capability rides a typeclass.** The class says what a body IS,
   never what it can do.

## 4 · The hierarchy

`LLMNpc(LLMNpcMixin, Character)` is the ONLY NPC typeclass; `Character` is
the body under it.

There is no `Bartender`, `Shopkeeper`, `Doctor` or `Butcher` class. What a
role class would hold lives here instead, by kind:

| what | where it lives |
|---|---|
| serving / selling / treating | job handler (`world/bar.py`, `world/shop/service.py`, `world/clinic.py`) |
| `_name_aliases`, `_llm_fallback` | the job record |
| `_run_context_tool` / `_handle_action_tool` | the job's `tools` |
| `_find_bar` / `_find_counter` / `_find_block` | `service.post_for()` |
| receiving a corpse | the job's `on_receive` hook |

## 5 · Definition of done

The platform is held to these ten criteria. The issue beside each is where
it comes from.

| # | criterion | issue |
|---|---|---|
| 1 | competence keyed by `post_role`, not class | #2350/#2352 |
| 2 | job carries aliases, fallback, archetype, tools | #2352 |
| 3 | every NPC is a soul | #2362 |
| 4 | one driver walks a body | #2373 (patrol) |
| 5 | exactly one NPC typeclass | #2378 |
| 6 | no blueprint names a role typeclass | #2378 |
| 7 | no class shadows a job hook | #2377 |
| 8 | dispatch is a job, not a body seizure | #2384 (§7) |
| 9 | one scheduler — the 45s tick drives NOTHING with a soul | #2386 (§5b) |
| 10 | game fully playable with the LLM off | #2390 |

Criterion 3: the ambient crowd is ensouled in stages on purpose
(`scripts/builds/138_ensoul_the_crowd.py`, `LIMIT = 5` per run); #2362 is
the issue that carries it.

Criterion 10: `feel` is retired (#2388, opinion is derived); introductions
are scraped deterministically; `style`, `wield` and `radio` have souls-side
callers. The LLM adds flavour on top, never a mechanic.

The claim the platform is held to: **pull the LLM breaker and the colony
still runs.** Souls still work shifts, eat, drink, dress, patrol, hunt,
respond to dispatch, serve at counters, treat patients, transmit on the
radio, form opinions of the people who are decent or violent toward them,
and learn the names those people give. What is lost is *voice* — the
improvised line, the coined nickname, the turn of phrase. That is the
two-brain law holding: souls decide, the LLM voices.

The entries in §6 are things deliberately NOT unified, not debts against
this definition.

## 5b · Criterion 9 — why the hunt sits at band 4

Recorded because the reasoning is not obvious and the next person will
reasonably think it is wrong.

The hunt is a souls goal, not a director tick, offered at **band 4, above
patrol**. Band 4 is offered in this order in `_desired_goal`: `comms` (take
out and switch on a pocketed or switched-off radio), `off_duty` (leave the
post after the shift), `hunt`, `provision` (an errand for a ration, kept
under the hunt so a unit never leaves an intruder for a snack), then
`patrol`.

Band 4 looks far too low for a security response — below hunger, below
duty. It is not a judgement that hunting matters less than eating. **It is
where the hunt already sat** when `tick_hunt` ran on the 45s director tick:
`is_patrol_idle` returned False whenever `soul_job` was set, so a unit that
was on duty, in combat, travelling or mid-conversation never hunted. Only a
genuinely idle unit did. Band 4 reproduces that exactly; moving the hunt
changed *who drives the body*, nothing else. Re-banding a security behaviour
while claiming to unify schedulers would have been a design change smuggled
in under a refactor — the kind that is invisible in a diff and shows up in
play weeks later.

If the colony later wants a guard to abandon its post for an intruder, that
is a real decision about how security behaves, and it is one line in
`_desired_goal`.

`wants_hunt` is deliberately PURE. The band tree must ask whether a unit
wants to hunt before deciding whether that outranks what it is doing, and
`tick_hunt` cannot answer without emoting and seeding state — merely
*considering* a hunt would start one.

`routines.tick_npc` never moves a souled body: it returns `souls`, or
`none`/`skip` before that check is reached. What the 45s tick still does is
maintenance sweeps.

## 6 · Deliberately not unified

- **`db.role` vs `soul_role`** mean *background* and *occupation* — a
  ganger who tends a bar is both. Whether they stay apart is not decided
  (see Not decided).
- **`soul_post` is overloaded**: "the slot I hold" for keepers, "where
  I am based" for the courier and the units. Build 141 needed a narrow
  guard purely to navigate this. It wants two names.

## 7 · Criterion 8 — dispatch as work, not seizure

`world/director/security.py` and `world/souls/jobs.py` cite this section in
their comments.

**The rule.** `dispatch.dispatch()` calls `assignment.assign()`. For a souled
responder, `assign()` does not seize the body; it writes a band-0 `respond`
job to the soul (#2384), whose steps are, in order: `travel` to the event's
room, `respond`, `travel` back to the post, `stand_down`.

The `respond` step (in `jobs.step_job()`) runs the arrival handler on first
entry (`assignment.run_arrival`; for security that is
`security.security_arrival`: scan, match, act), then the role's watch handler on each later
beat (`assignment.run_watch`; for security that is `security.watch_once`, a
tick-once watch, #2383). `think()` has no assignment early return: a
dispatched unit's mind stays on for the whole call.

Band 0 outranks everything, so the unit does not wander off a call, but it is
*arbitrated* rather than silenced, so a band-0 safety need can still reach it
and a dead unit's job clears like any other. A silence switch is a boolean
where a band belongs, and it has already cost once: nothing cleared it on
death, so a wrecked unit's soul stayed asleep permanently, even after repair
(#2255).

The module-level `_ACTIVE` dict in `assignment` stays. It is the finite-pool
bookkeeping that makes "overwhelm the force" a real tactic, but it is not a
silence switch.

An unsouled responder still gets the old path: `assign()` starts its travel
with `travel_to(..., on_arrive=_on_scene)`, and its watch is the
`delay`-chained `security._watch_tick`. `world/director/assignment.py` annotates this fallback as a state
"nothing in the colony currently is".

**Risks.** This is the crime-response chain and it is combat-adjacent
(`_engage` issues real `attack` commands). The failure mode is SILENT:
crimes simply go unanswered, and nothing shouts. Pin new behaviour with new
tests.

## Not decided

- **`db.role` vs `soul_role`.** Reading them as *background* and
  *occupation* looks correct, but it has never been decided on purpose;
  decide it before merging them.
- **Holographic merchants.** Are the holographic merchant prototypes in
  `world/prototypes.py` (a plain `Character` with no soul) an intended
  exception to "exactly one NPC typeclass" and "every NPC is a soul", or
  should they be retired or converted?
