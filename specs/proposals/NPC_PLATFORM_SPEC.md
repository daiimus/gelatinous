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
| 8 | dispatch is a job, not a body seizure | ❌ `is_assigned()` |
| 9 | one scheduler | ❌ 45s + 30s |
| 10 | game fully playable with the LLM off | 🟡 breaker + memory done; `remember`/`feel`/`style`/NPC-`radio` have no deterministic twin |

**1–7 are done: the platform exists and the collapse it was for has
happened.** 8–9 are the director half — dispatch still seizes a body
rather than handing it work, and two schedulers still tick. 10 is the
voice half. Those three are what "unified" still owes. 8–9 are the director half; 10 is the voice half.

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
