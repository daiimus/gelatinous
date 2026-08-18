# Souls at Scale — Evennia Core Findings & Hardening Plan

> **Status:** 📋 **Proposal — findings + phased plan (2026-08-18).** Product of a
> source-level dig through Evennia 6.1.0 internals (persistence, scheduling)
> plus an adversarial audit of `world/souls/` against them, before scaling the
> population from 4 souls toward hundreds. §1–§2 are durable knowledge about
> the engine we run on; §3 is the ranked debt register; §4 is the plan; §5 is
> law for every future always-on system. ELABORATES
> [`NPC_NEEDS_AND_GOALS_SPEC`](NPC_NEEDS_AND_GOALS_SPEC.md) (phase 1–2 shipped).

## 1 · How Evennia actually persists (measured against source, v6.1.0)

**Writes are the enemy; reads are almost free.**

- `obj.db.x = value` is a synchronous, immediate DB write on the reactor
  thread: full `to_pickle` walk of the value, then **two** UPDATE statements
  (the value-setter's save plus the handler's), **each in its own
  `atomic()` transaction**. No coalescing or deferral exists anywhere in core.
- Mutating a stored dict in place (`SaverDict[k] = v`) re-serializes the
  **entire** attribute and UPDATEs it — per key. The idiom
  `d = obj.db.needs; d[k] = v; obj.db.needs = d` pays **three** full saves.
- Reads are served from the aggressive per-object attribute cache (no SQL
  after first load) — but `Attribute.value` deliberately never caches the
  deserialized form: every read re-walks `from_pickle`. Cheap, not free.
- `.ndb` is pure in-process memory. Zero DB, lost on reload. It is the
  designed home for high-frequency state that persists only at checkpoints.
- `AttributeProperty(autocreate=True)` **writes to the DB on first read**.
- Tags are the indexed, blessed lookup path (composite index on
  key/category/tagtype/model). `ObjectDB.objects.filter(db_attributes__db_key=…)`
  is an uncached m2m join — never put it on a hot path.
- Core ships SQLite with `synchronous=OFF` (no fsync per commit — the single
  load-bearing perf setting) and **no WAL**. Nothing in core batches
  attribute writes into one transaction; `batch_add` only batches the m2m
  linking. A hand-rolled `transaction.atomic()` around a periodic flush is
  additive and safe.
- The idmapper holds **strong references** — cached objects never GC. The
  maintenance loop considers flushing every 5 min against
  `IDMAPPER_CACHE_MAXSIZE` (default 400 MB); the "flush called more than
  once in 5.0 min" warning means the working set exceeds the cap, not a bug.

## 1.5 · Measured baselines (live container, 2026-08-18)

Microbenchmarked in the game container (Rosetta, SQLite `synchronous=0`,
`journal_mode=delete` — pragmas verified identical on the shell connection):

| Operation | Cost |
|---|---|
| `db` attribute write | **951 µs** |
| SaverDict single-key in-place mutation | 718 µs |
| `.ndb` write / read | **1.3 µs / 1.2 µs** |
| cached `db` dict read (re-unpickle) | 4.8 µs |
| `search_tag` (the per-beat `get_souls`) | 5.6 ms |
| advertiser attribute-join scan | 347 µs (tiny DB today; grows) |
| `search_object("#id")` vs `objects.get_id` | 262 µs vs **1.3 µs** |
| **A\* path, Brackett→Pessoa** | **18 ms** |
| `colony_hour()` | 0.7 µs |

Consequences: (a) the write storm is confirmed — 300 souls × 3 writes/beat
≈ **855 ms of blocked reactor per 30 s**, and `.ndb` is ~700× cheaper, so
P1 compute-on-read is the headline fix; (b) **finding 11 is re-ranked
HIGH** — at 18 ms per path with a re-path every 2 s per walking soul, a
shift-change commute of a couple hundred souls saturates the reactor on
pathfinding alone; path caching (re-path only on move failure) plus
**shift jitter** (each soul carries a personal ±15 min offset on its
schedule blocks — staggers the commute *and* reads better in the fiction)
moves to P2; (c) LLM voice calls verified non-blocking (`requests.post`
inside `run_async`'s thread pool, HTTP only in the thread — the reactor
never waits on the sidecar).

## 2 · How Evennia actually schedules

- Script timers are `ExtendedLoopingCall` on the reactor. `at_repeat` runs
  **synchronously on the main thread**; a long beat blocks every player
  command for its duration. An exception in `at_repeat` is logged and the
  timer survives — but it aborts the rest of that beat's loop body.
- Timers live in `ndb` — only the server process arms them. A script row
  created from an external `evennia shell` never ticks (re-learned #1963);
  `settings.GLOBAL_SCRIPTS` is the canonical owner: adopts by key at boot,
  recreates on settings-hash change, re-arms across reloads.
- For many-object ticking, core idiom is **one coordinator script iterating
  the population** (the combat-handler shape) or TickerHandler buckets (one
  shared timer per interval, per-subscriber error isolation). **Never one
  script per NPC** — no contrib does it, and the framework steers away.
- Core provides **no cooperative-chunking helper** (no `coiterate` use
  anywhere) and **forbids ORM off the main thread** (explicit sqlite3
  warnings on `run_async`). If a beat is too heavy, you chunk it yourself.
- The tutorial mob demonstrates the two blessed load levers: **pace-by-state**
  (tick slower when nothing is happening) and **event-push** (the room calls
  `at_new_arrival` so a slow-ticking mob reacts instantly) — poll less,
  get notified more.
- `utils.delay` is fine for one-shots at scale (one reactor timer each,
  no DB unless `persistent=True` — thousands of *persistent* delays rewrite
  a ServerConfig blob per add: avoid).
- `evennia.utils.gametime` / our `colony_hour()` are pure arithmetic — free
  on any hot path. Evennia ships `dummyrunner` (bot-player stress tool) and
  `evennia --profiler`: the 50-player question is measurable, not
  theoretical.

## 3 · Debt register (adversarial audit of `world/souls/`, ranked)

| # | Sev | Finding | Where |
|---|-----|---------|-------|
| 1 | CRIT | Per-beat write storm: 3–4 UPDATEs per soul per beat (`soul_last_decay`, `soul_needs` written twice, `soul_wage_owed`) — ~900–1200 writes/30s at 300 souls, ~all on unobserved souls | engine.py, needs.py |
| 2 | HIGH | No per-soul phase offset: all cold souls think on `beat % 6 == 0` — LOD *batches* the load instead of spreading it; tithe (120) lands on the same beat | engine.py |
| 3 | HIGH | Decay block unwrapped: one corrupt soul aborts the beat for every soul after it, deterministically, every beat, until admin intervention | engine.py |
| 4 | HIGH | `lod_for` recomputes player-room coords per soul: ~15k `get_xyz` calls/beat at 300×50 | engine.py |
| 5 | MED | Preemption clears the job but never cancels in-flight travel — the soul walks all the way to the abandoned goal before the new one can move it | engine.py, jobs.py |
| 6 | MED | `jobs._obj` runs full `search_object("#id")` per step instead of the indexed `ObjectDB.objects.get_id` | jobs.py |
| 7 | MED | `_advertisers` uncached attribute-join full scan per plan; `_edible_wares` calls `search_prototype` per ware per plan | actions.py |
| 8 | MED | `run_tithe` uses unindexed `icontains` full-table scan, aligned with the burst beat; `get_treasury` re-queries ScriptDB per wage payout | economy.py |
| 9 | LOW | Wage payout truncates fractional accrual (`int(owed)`) — worker underpay, though conservation holds | economy.py |
| 10 | LOW | Goal cooldowns in `ndb` — every reload triggers population-wide re-plan/re-fault churn at the worst moment | engine.py |
| 11 | LOW | Travel re-runs full A* every 2s per walking soul regardless of LOD | director/travel.py |
| 12 | LOW | `@soul` global_search — admin-only, acceptable, leave it | CmdSoul.py |

**Already right (do not churn):** single GLOBAL_SCRIPTS coordinator (core
idiom); `get_souls()` materialized to a list; pk/location guards; `think()`
fault isolation; genuinely closed money loop (no minting/leak, symmetric
transfers); real-elapsed-time decay and per-beat wage accrual (LOD cannot
change outcomes, only cadence); movement through real verbs; travel/LOD
self-heal on reload; the stagger idiom already exists in
`director/routines.py` to copy.

## 4 · Hardening plan (phased, each phase shippable alone)

- **P0 — correctness (small diffs, do first):** wrap the per-soul beat body
  in fault-isolation like `think()` already is (#3); cancel travel whenever
  a job is cleared for preemption/fault (#5); carry the fractional wage
  remainder instead of truncating (#9); persist goal cooldowns to `db` (#10).
- **P1 — kill the write storm (#1):** needs become compute-on-read — store
  `(snapshot, stamped_at)` once, derive pressure lazily in `pressure()` and
  `@soul`; persist only when something *changes* a need (satisfy, think
  transition, duty flip). Fold the duty mutation into the same single write.
  Cold-soul per-beat writes drop from 3–4 to **0**.
- **P2 — spread the load:** phase-offset thinking by identity
  (`(beat + soul.id) % THINK_EVERY[lod]`, the routines.py idiom) (#2);
  de-align the tithe from the think cadence (#8); hoist player-room coord
  computation out of the per-soul loop (#4).
- **P3 — query hygiene:** `get_id` in job steps (#6); tag advertisers and
  tills (`search_tag`, indexed) with a short-TTL in-process cache and a
  per-prototype edibility memo (#7, #8); treasury reference memoized (#8);
  travel caches its path and re-paths only on failure, step delay scaled by
  LOD (#11).
- **P4 — measure, then infra:** `dummyrunner` + `--profiler` baseline at
  current population, again after P1/P2, again with a synthetic 300-soul
  load; only then consider WAL journal mode via `SQLITE3_PRAGMAS` and the
  native arm64 image (drops the Rosetta tax) in gelatinous-infra.

### P4 results — live load test (2026-08-18, post P0–P3)

Run live (owner-sanctioned, pre-alpha): 20 dummyrunner bots (custom
no-dig look/wander profile, plain player perms via `DUMMYRUNNER_MIXIN`)
plus 100 disposable ensouled NPCs seeded to act immediately (70
social-critical walkers, 30 funded hunger-critical buyers). Metrics:
webserver latency through the reactor thread, container CPU, heartbeat
cadence.

| Phase | Reactor latency | CPU |
|---|---|---|
| Baseline (4 souls) | 36–56 ms | 0.1–2% |
| 20 bots | 37–67 ms (one 211 ms account-creation blip) | 5–15% |
| **104 souls + 20 bots** | **36–64 ms — flat, indistinguishable from baseline** | 5–22% peak during the planning/commute wave, settling 5–12% |

Behavior under load: all 70 walkers crossed the city to the Kettle on
cached routes; buyers rang Lin's real till (register 6→27 mid-test);
**zero faults across 100 souls**; the four real residents lived their
loops undisturbed throughout. Verdict: the hardened engine absorbs the
~⅓-of-target population plus a full player load with no measurable
reactor impact — **WAL and the arm64 image are not needed at current
scale** and stay parked until measurements say otherwise.

Operational notes: SQLite locked once during external-shell mass
deletion against the live server (per-object retry with backoff
resolved it — bulk mutations belong in small batches); external-shell
test pokes need a reload to be visible now that nothing rewrites needs
on a timer.

## 5 · Laws for every future always-on system

1. **Never write db attributes on a timer for unobserved entities.**
   Compute-on-read from a stamped snapshot; persist on change.
2. **`.ndb` for hot state, `.db` at checkpoints** — and assume `.ndb` dies
   at every reload; design the recovery path.
3. **Tags for lookup, never attribute-key queries on a hot path.**
4. **Stagger by identity.** Anything keyed `beat % N` across a population is
   a thundering herd; add the entity id to the phase.
5. **Fault-isolate per entity inside any loop over the population.** One bad
   row must cost one entity, not the beat.
6. **One coordinator script per system, owned by `GLOBAL_SCRIPTS`.** Never
   per-entity scripts; never create script rows from an external shell.
7. **Event-push over polling** where a hook exists (`at_new_arrival`-style);
   pace-by-state where it doesn't.
8. **The reactor is the budget.** Every beat is a synchronous slice on the
   only thread; no ORM off-thread, ever. If a slice is too big, shrink or
   chunk it — measure with `--profiler` and `dummyrunner`, don't guess.
