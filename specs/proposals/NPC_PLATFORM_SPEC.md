# NPC Platform Spec

> 🟡 **PROPOSAL — the target hierarchy, and how far it has been built.**
> Owner requirement (2026-08-28): *"one NPC platform with various
> sub-components"*, everything built so far connected under **one
> hierarchy**. This document exists because that requirement was
> discussed at length and never written down, which made "have we met
> it?" unanswerable. §5 is the checklist that answers it.

## 1 · The requirement, in the owner's words

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
| **mind** | soul | indexed tag + `soul_*` | ✅ `ensoul()` / `desoul()` |
| **job** | what you do at a post | `world/service.py` registry, keyed by `post_role` | ✅ |
| **voice** | persona + brain | `db.llm_driven` + persona seed, code in `LLMNpcMixin` | ✅ **optional** |

**The inversion that mattered.** The code used to have this backwards:
every NPC class was `(LLMNpcMixin, Character)`, so the *voice* was the
base and the *soul* was the optional add-on — the exact reverse of the
requirement. The mind is the base. The voice is the hook.

## 3 · Laws

1. **One driver per body.** The souls engine drives. The director is a
   *source of work*, not a second walker (#2373).
2. **Competence belongs to the post, not the person.** An ability
   bolted to a typeclass cannot be inherited by whoever takes the shift
   next (`AnsweringFixture`, #2350, #2352).
3. **A post keeper is a soul** (#2362).
4. **Souls decide; the LLM voices.** The two-brain law. No mechanic may
   exist only behind a model turn.
5. **No capability rides a typeclass.** The class says what a body IS,
   never what it can do.

## 4 · Target hierarchy

```
Character                     the body
└── LLMNpc(LLMNpcMixin, Character)      ← the ONLY NPC typeclass
```

`Bartender`, `Shopkeeper`, `Doctor` and `Butcher` do not exist. What
they held moves by kind:

| what it was | where it goes |
|---|---|
| serving / selling / treating | job handler (`world/bar.py`, `world/shop/service.py`, `world/clinic.py`) |
| `_name_aliases`, `_llm_fallback` | the job record |
| `_run_context_tool` / `_handle_action_tool` | the job's `tools` |
| `_find_bar` / `_find_counter` / `_find_block` | `service.post_for()` |
| receiving a corpse | the job's `on_receive` hook |

## 5 · Definition of done — the checklist

| # | criterion | state |
|---|---|---|
| 1 | competence keyed by `post_role`, not class | ✅ #2350/#2352 |
| 2 | job carries aliases, fallback, archetype, tools | ✅ #2352 |
| 3 | every NPC is a soul | ✅ #2362 |
| 4 | one driver walks a body | ✅ #2373 (patrol) |
| 5 | exactly one NPC typeclass | ✅ #2378 |
| 6 | no blueprint names a role typeclass | ✅ #2378 |
| 7 | no class shadows a job hook | ✅ #2377 |
| 8 | dispatch is a job, not a body seizure | ✅ #2384 |
| 9 | one scheduler | ✅ #2386 — the 45s tick drives NOTHING with a soul |
| 10 | game fully playable with the LLM off | ✅ #2390 — `feel` retired (#2388, opinion is derived); introductions scraped deterministically; `style`/`wield`/`radio` already had souls-side callers. The LLM adds flavour on top, never a mechanic |

**ALL TEN ARE DONE (2026-08-29).** The platform exists, the collapse it was
for has happened, the director hands out work instead of seizing bodies, one
scheduler drives every body, and no mechanic lives behind a model turn.

What that means concretely, and the claim worth holding the work to: **pull
the LLM breaker and the colony still runs.** Souls still work shifts, eat,
drink, dress, patrol, hunt, respond to dispatch, serve at counters, treat
patients, transmit on the radio, form opinions of the people who are decent or
violent toward them, and learn the names those people give. What is lost is
*voice* — the improvised line, the coined nickname, the turn of phrase. That
is the two-brain law holding: souls decide, the LLM voices.

The remaining entries in §6 are things deliberately NOT unified, not debts
against this checklist.

## 5b · Criterion 9 — why the hunt sits at band 4

Recorded because the reasoning is not obvious and the next person will
reasonably think it is wrong.

`tick_hunt` came off the 45s director tick and became a souls goal, offered at
**band 4, above patrol**. Band 4 looks far too low for a security response —
below hunger, below duty. It is not a judgement that hunting matters less than
eating. **It is where the hunt already sat.**

`is_patrol_idle` returned False whenever `soul_job` was set, so a unit that was
on duty, in combat, travelling or mid-conversation never hunted. Only a
genuinely idle unit did. Band 4 reproduces that exactly, and the merge changes
*who drives the body*, nothing else. Re-banding a security behaviour while
claiming to unify schedulers would have been a design change smuggled in under
a refactor — the kind that is invisible in a diff and shows up in play weeks
later.

If the colony later wants a guard to abandon its post for an intruder, that is a
real decision about how security behaves, and it is one line in `_desired_goal`.

`wants_hunt` is deliberately PURE. The band tree must ask whether a unit wants
to hunt before deciding whether that outranks what it is doing, and `tick_hunt`
cannot answer without emoting and seeding state — merely *considering* a hunt
would have started one.

## 6 · Deliberately not unified

- **`db.role` vs `soul_role`** now mean *background* and *occupation* —
  a ganger who tends a bar is both. That reads correct, but it has
  never been decided on purpose; decide it before merging them.
- **`soul_post` is overloaded**: "the slot I hold" for keepers, "where
  I am based" for the courier and the units. Build 141 needed a narrow
  guard purely to navigate this. It wants two names.

## 7 · Criterion 8 — dispatch as work, not seizure

The last real split, designed here rather than half-started.

**Today.** `dispatch.dispatch()` calls `assignment.assign()`, which
records the responder in a module-level `_ACTIVE` dict and starts its
own travel with `on_arrive=_on_scene`. `security_arrival` then drives
the body — `aim`, `attack`, `emote`, `xmit` — and holds it there with a
`delay`-chained `_watch_tick`. Meanwhile `souls.think()` opens with:

```python
if is_assigned(soul):
    return          # precedence law: combat > assignment > souls
```

So a dispatched unit's mind is **switched off for the whole call**. That
is a boolean where a band belongs, and it has already cost once: nothing
cleared the assignment on death, so a wrecked unit's soul stayed asleep
permanently, even after repair (#2255).

**Target.** `assign()` hands the soul a JOB instead of seizing it:

```python
{"goal": "respond", "band": 0, "at": 0, "steps": [
    {"do": "travel",  "room": event.location.id},
    {"do": "respond", "event": ...},      # arrival handler, then the
    {"do": "travel",  "room": post.id},   # watch ticked per beat
]}
```

Band 0 outranks everything, so the unit does not wander off a call — the
behaviour `is_assigned` was protecting — but it is *arbitrated* rather
than silenced, so a band-0 safety need can still reach it and a dead
unit's job clears like any other.

**Order, smallest verifiable step first.**

1. `security._watch_tick` becomes tick-once rather than `delay`-chained.
   Behaviour identical; only the caller changes.
2. New `respond` step in `jobs.py`: runs the arrival handler on first
   entry, `_watch_tick` on each later beat.
3. `assign()` writes the job instead of starting travel. `_ACTIVE` stays
   — it is the finite-pool bookkeeping that makes "overwhelm the force"
   a real tactic — but stops being a silence switch.
4. Delete the `is_assigned` early return from `think()`.

**Risks.** This is the crime-response chain and it is combat-adjacent
(`_engage` issues real `attack` commands). `test_director_security`
carries three pre-existing baseline failures, so that file cannot be a
clean signal — pin new behaviour with new tests. The failure mode is
SILENT: crimes simply go unanswered, and nothing shouts.

**Criterion 9 follows from it.** Once dispatch is a job, the only thing
the 45s tick still DRIVES is the hunt; the rest is maintenance sweeps.
Move the hunt to a souls goal the way patrol went, and the two
schedulers can merge.
