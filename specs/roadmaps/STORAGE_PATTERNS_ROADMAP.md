# Storage Patterns Roadmap

> **Status:** 🛣 Roadmap — survey complete; the §5 remediation plan is drafted, not executed.

> Renamed from `STORAGE_PATTERNS_AUDIT_AND_REMEDIATION_SPEC` (2026-06-14).
> A **forward roadmap**: the survey is done, the §5 remediation plan is
> drafted and not yet executed.

**Status**: Survey complete · remediation roadmap drafted · no code
changes yet.

## 0 · The architectural principle

External advice (paraphrased) from a senior Evennia practitioner:

> Forget `ndb`. Keep your data structures light and decoupled from
> Evennia's attributes systems entirely as plain class attributes on
> other class objects. Gives you completely free reads. Only save to
> the backing attribute when something meaningfully changes in a way
> that you would be sad if the game restarted and that change was
> reset. That minimizes writes.

Restated in our terms:

* **Runtime tier**: ordinary Python objects with ordinary class
  attributes. No descriptors, no pickling, no DB round-trip. Reads
  cost a dict lookup.
* **Persistence tier**: `db.X` (or `AttributeProperty`) holds a
  *serialised snapshot* of the runtime object's meaningful state.
  Writes happen only when something would be **lost** at restart and
  that loss would be unacceptable.
* **`ndb`**: legitimate for true scratch state (menu position, queued
  callbacks, one-shot caches), but reach for it deliberately — not as
  "I didn't want to design persistence here." Most of what currently
  sits on `db.X` because we wanted persistence belongs on a plain
  attribute backed by an explicit flush.

The advice's emphasis on *minimising writes* is grounded in Evennia's
actual cost model:

* **Reads** (`x = obj.db.foo`): descriptor lookup → in-process
  Attribute cache. After the first hit, subsequent reads of the
  same attribute on the same object are cheap, but the descriptor
  protocol is still in the path. A plain Python attribute (`x =
  self._foo`) is a dict lookup. The latter is what "free reads"
  refers to — orders of magnitude cheaper at hot-path rates.
* **Writes** (`obj.db.foo = value`): descriptor protocol → pickle
  serialisation → Django ORM write to the `ObjectAttribute`
  table. This is the expensive operation. Most of our writes are
  load-bearing; a non-trivial fraction are not.

`AGENTS.md` is the operational reference for these conventions and
should be read alongside this spec.

## 1 · Why this matters here

Three characteristics of Gelatinous amplify the cost of the
"convenient `db.X`" pattern:

1. **Hot render paths.** `get_display_name` fires on every look,
   every `msg_room_identity` broadcast, every action emote, every
   chart pane render. The call chain reads
   `observer.db.disguise_pierce_cache` *and* writes back on every
   pierce attempt. `grep` finds 497 `get_display_name` /
   `attempt_display_pierce` call sites; most exercise the cache.
2. **Ticker-driven mutation.** `MedicalScript` ticks every 12s
   (`world/medical/script.py:96`) and mutates `_medical_state` in
   place — blood loss, pain accumulation, consciousness drift,
   healing. The script does **not** call `save_medical_state` per
   tick; saves happen at meaningful events only (procedure
   complete, admin change, organ swap, damage application). This
   is already the right shape — preserve it.
3. **Dict-shaped state on `db`.** `db.surgical_state`,
   `db.medical_chart`, `db.diagnose_cache`, `db.wounds_at_death`,
   `db.signature_at_death`. Reads cost a descriptor lookup plus
   a `_SaverDict` proxy (the reason we duck-type
   `isinstance(x, dict)` throughout the medical pipeline). Writes
   round-trip through pickle.

Throughout this spec, "hot" means called on every render, every
combat tick, every action emote — not "called occasionally."

## 2 · Survey methodology

* `grep -rh '\.db\.\w*\s*=' --include='*.py'` — assignment count per
  attribute name (1,200+ hits).
* `grep -rh '\.ndb\.\w*'` — ndb usage (256 hits).
* `grep -c '\.db\.' <file>` — files ranked by db-write density.
* Hand-read of the runtime/persistence boundary for
  `MedicalState`, `surgical_state`, `medical_chart`, the four
  recognition-caches, and the death-snapshot family.

Numbers cited below are from the snapshot taken at audit time and
will drift; the *patterns* are stable.

## 3 · Pattern catalog

### 3.1 · The runtime/persistence split (gold standard)

The exemplar in our codebase is `MedicalState`
(`world/medical/core.py:519` onward):

* Runtime object lives at `self._medical_state` — a plain Python
  attribute on the `Character`. Holds `organs` (dict of `Organ`
  objects), `conditions` (list), `blood_level`, `pain_level`,
  `consciousness`. Reads are free.
* The `@property medical_state` accessor at
  `typeclasses/characters.py:188` lazy-loads from `db.medical_state`
  (the serialised dict) into `_medical_state` on first access via
  `load_medical_state`.
* `save_medical_state` (`world/medical/utils.py:596`) calls
  `to_dict()` and writes the serialised form to `db.medical_state`.
  Call sites: `core.py:879`, `procedures.py:1268`, `items.py:1956`
  and `:2359`, `armor_mixin.py:77`, `CmdAdmin` (7 sites), and the
  damage-application path. **`MedicalScript.at_repeat` does not
  call it** — tick-level changes (blood drip, pain accumulation,
  consciousness drift) are intentionally volatile.

This pattern: runtime tier is canonical, persistence tier is a
snapshot of the runtime, writes happen at named boundaries.

### 3.2 · AttributeProperty (Evennia-native persistent attribute)

92 uses across the codebase, concentrated on `Character`
(`typeclasses/characters.py:86–102`):

* `grit`, `resonance`, `intellect`, `motorics`
* `sex`, `sleeve_uid`, `height`, `build`, `hair_color`,
  `hair_style`, `sdesc_keyword`
* `species`, `recognition_memory`

These are values that:

1. Persist across restarts (chargen state, identity baseline).
2. Are read often but written rarely (e.g. `sleeve_uid` is set
   once at chargen, read every UID computation).
3. Need a default value the descriptor can provide.

`AttributeProperty` is fine here — it's read-cached after first
access and the write rate is near-zero. The only fly in the
ointment is `recognition_memory` (mutated by every unmasking,
remember call, and pierce cache update); whether *that* should
still be an `AttributeProperty` is in §5.

### 3.3 · Per-attribute `db.X` writes (the convenient pattern)

Top writers by count (from `grep` survey):

| attr                   | writes | category                          |
|------------------------|--------|-----------------------------------|
| `height_override`      | 30     | identity (rare event)             |
| `desc`                 | 22     | room/object setup (rare event)    |
| `apparent_uid_at_death`| 22     | death snapshot (one-shot)         |
| `wounds_at_death`      | 21     | death snapshot + harvest mutation |
| `signature_at_death`   | 19     | death snapshot (one-shot)         |
| `longdesc_data`        | 17     | identity baseline (rare event)    |
| `keyword_override`     | 15     | identity (rare event)             |
| `build_override`       | 15     | identity (rare event)             |
| `surgical_state`       | 14     | surgical procedure (per-step)     |
| `combatants`           | 14     | combat handler (per-action)       |
| `removed_organs`       | 13     | harvest mutation                  |
| `sleeve_uid`           | 12     | identity baseline (chargen-only)  |
| `disguise_pierce_cache`| 12     | cache (per-render)                |
| `death_time`           | 12     | death snapshot (one-shot)         |
| `death_cause`          | 12     | death snapshot (one-shot)         |

The interesting partition:

* **Write-once / rare event** (desc, height_override, sleeve_uid,
  death_*): `db.X` is correct. No work to do.
* **Append-mutation** (wounds_at_death, bleeding_incidents on
  BloodPool, removed_organs): each append triggers a full
  serialisation pass. Candidates for batching, but the volumes are
  small (a corpse accumulates 5–10 wound entries, not 5,000).
* **Per-action mutation** (surgical_state, medical_chart,
  combatants): high-frequency writes that don't strictly need
  per-step persistence.
* **Per-render cache** (disguise_pierce_cache,
  forensic_recognition_cache, diagnose_cache,
  autopsy_procedure_cache): the worst category — high read rate,
  meaningful write rate, and every miss writes back. This is the
  primary remediation target.

### 3.4 · The Tag system (boolean flags)

`AGENTS.md` calls this out explicitly: *"For simple booleans,
prefer the Tag system (`obj.tags`) over attributes."* Tags are
indexed at the DB level and don't go through pickle, so they're
the right shape for "is this thing flagged X" queries.

`grep` finds several boolean `db.X = True/False` writes that
should be Tags:

| attr                       | site                              |
|----------------------------|-----------------------------------|
| `db.archived`              | `web/website/views/characters.py`, character archival |
| `db.combat_is_running`     | `world/combat/handler.py` (4 sites) |
| `db.pin_pulled`            | `commands/CmdThrow.py`, `commands/explosion_utils.py` (4 sites) |
| `db.is_infinite`           | `typeclasses/shopkeeper.py` (2 sites) |
| `db.integrate`             | `commands/CmdExplosives.py` |
| `db.head_severed`          | corpse / appendage chain |

Conversion is mechanical (`obj.db.X = True` →
`obj.tags.add("X", category="...")`) but you pay a one-time
audit tax across read sites (`if obj.db.X` →
`if obj.tags.has("X", category="...")`). Worth doing per-flag
on first touch; not worth a sweeping migration PR.

### 3.5 · `ndb` scratch state (transient by design)

256 ndb references. Top users:

| attr                          | uses | rightness                         |
|-------------------------------|------|-----------------------------------|
| `charcreate_data`             | 72   | ✓ chargen menu scratch            |
| `jump_movement_allowed`       | 16   | ✓ transient movement flag         |
| `_operate_target`             | 15   | ✓ EvMenu scratch                  |
| `_operate_pickable`           | 15   | ✓ menu picker scratch             |
| `in_proximity_with`           | 14   | ? combat — could be plain attr    |
| `aiming_at`                   | 11   | ? combat targeting                |
| `aimed_at_by`                 | 10   | ? reverse of above                |
| `_shortdesc_keywords`         | 8    | ✓ rendering scratch               |
| `death_curtain_pending`       | 7    | ✓ one-shot transition state       |
| `sever_task`                  | 6    | ? procedure delay handle          |
| `unconsciousness_pending`     | 3    | ✓ flag                            |

ndb usage is *mostly* appropriate — menu scratch, transition
flags, one-shot timers. The dubious ones are combat-state items
(`aiming_at`, `in_proximity_with`) that need to survive combat
interruption but not a server restart. These could equally be
plain attributes on the actor and behave identically.

The advice's "forget ndb" is rhetorical hyperbole; the real
guidance is **don't put runtime objects on ndb thinking that's
the same as putting them on a plain attribute**. ndb is still a
descriptor, still has overhead, still encourages the same
attribute-soup access pattern.

## 4 · Audit findings — surface by surface

### 4.1 · Identity / recognition

**Good shapes:**
* `get_apparent_uid(char)` (`world/identity.py:914`) — pure
  computation from a 5-tuple signature, no caching. Free reads.
  Called on every render of every character; the perf hit is real
  but the cost is bounded (one tuple hash).
* `signature_at_death` / `apparent_uid_at_death` written once at
  death.

**Problem shape:**
* `observer.db.disguise_pierce_cache`
  (`world/identity.py:1525`) — `dict` keyed on
  `(target.dbref, apparent_uid)`. Read on every
  `attempt_display_pierce` call (which fires from every
  `get_display_name` where the looker doesn't directly know the
  current UID). Written on every cache miss. Currently
  persisted, so a pierce roll cached on day 1 is still valid on
  day 30.
* `recognition_memory` is an `AttributeProperty({}, autocreate=True)`
  mutated by the unmasking pipeline, the remember command, and
  passive recognition. Each mutation is technically a
  descriptor-set, but because the value is a dict (a
  `_SaverDict` in Evennia's wrapper), the in-place mutation is
  caught and persisted. So writes happen on every
  `_broadcast_unmasking` cell B/D event and every `remember`.
  Volumes are low but the pattern is "implicit write on every
  mutation."

**Audit verdict on the pierce cache:** persistence is
load-bearing (prevents Intellect-reroll abuse across sessions),
but the **read-then-write-back pattern on every miss** is the
hot-path cost. See §5.1 for the remediation.

### 4.2 · Medical state

Already covered in §3.1 — exemplar.

The one subtlety: `Organ` objects live inside the in-memory
`MedicalState`. When wound state changes (`organ.wound_stage =
"treated"`, `organ.injury_type = "bullet"`), the change is to
the in-memory tree. The persistence flush happens only when
something calls `save_medical_state`. Currently those flushes
fire on:

* Damage application (the procedure-resolve and combat paths).
* Organ harvest/install (`items.py`).
* Admin overrides (`CmdAdmin`).
* Suturing (`procedures.py:1268` in `_resolve_suture`).

**Question to interrogate:** does every wound-stage mutation
have a flush? `sync_severance_wound_stages` (PR #437) writes
into `wound_data['stage']` on the in-memory snapshot. It does
not directly call `save_medical_state`. The mutation is durable
because the next damage application or procedure will flush.
That's probably fine — but it's worth confirming the worst-case
"restart between two procedures" doesn't lose stump-stage
progression.

### 4.3 · Surgical / chart procedures

`target.db.surgical_state` and `target.db.medical_chart` are the
two primary persistence surfaces.

**`surgical_state` shape:**
```python
{
  "incisions": {<location>: {"opened_at": ts}, ...},
  "active_procedure": {"verb": ..., "actor_dbref": ..., "kwargs": ...},
  "pending_step_result": <chart-runner pickup slot>,
  ...
}
```
Written on every procedure start, every procedure resolution,
every incision open/close, and every chart-runner step
transition. The `pending_step_result` slot we added for autopsy
(PR #449) writes on every chart step completion.

**Risk of losing it on restart:** moderate. An active procedure
(mid-delay) would lose its `_PROCEDURE_COMPLETE_HOOKS` (in-memory
only) regardless, so the chain is already "die on restart" by
design. The open incisions and chart status genuinely should
persist; the active-procedure record arguably should not.

**`medical_chart` shape:**
```python
{
  "version": ..., "authored_by": <dbref>, "status": ...,
  "next_step_id": int, "steps": [<step>, ...],
}
```
Where each step has `{verb, args, status, result, outcome}`.
Written every time `save_chart` is called, which is every
status flip (`commence_chart`, `_advance`, `interrupt_procedure`,
edit-chart actions).

The chart genuinely needs persistence — surgeons hand off charts,
patients survive restarts, etc. But mid-commence writes (running
→ done → status of the next step → running → ...) are happening
3+ times per step transition. Could be a single write per step.

### 4.4 · Combat / handler state

`target.db.combatants` has 14 writes, 80 reads — written every
time an actor joins/leaves combat, read by every targeting
resolution. The handler itself
(`world/combat/handler.py`) is the largest write-frequency
violator (16 db writes). State that should arguably be runtime:

* The combatants list (matters for the current encounter; if
  server restarts mid-combat, what should happen? Probably
  combat ends).
* Proximity tracking (`in_proximity_with` on ndb — already
  transient).
* Aiming relationships (`aiming_at` / `aimed_at_by` on ndb).

The hybrid is reasonable: ndb for the volatile "who is aiming
at whom right now," db for the higher-level "is this character
in a fight" flag. But the handler module itself writes db
heavily and could benefit from a runtime-tier refactor.

### 4.5 · Inventory / clothing / hands

`worn_items` (an `AttributeProperty` dict), `hands` (a derived
`@property` view on the species template — already runtime).

`worn_items` mutations: `wear_item` and `remove_item` mutate
the dict in place. The persistence model relies on
`_SaverDict` catching the in-place change. Each mutation
serialises the entire dict. Volumes are bounded (worn items
per character rarely exceed 20), but every wear/remove cycle
on a busy avatar adds up.

The pattern is acceptable but inelegant; a refactor to "plain
attr + explicit flush on commit" would be marginal win, high
risk.

### 4.6 · Death snapshots

`db.signature_at_death`, `db.apparent_uid_at_death`,
`db.wounds_at_death`, `db.medical_state_at_death`,
`db.removed_organs`, `db.severed_locations`, `db.death_time`,
`db.death_cause`, `db.source_signature`,
`db.source_apparent_uid`, `db.source_corpse_dbref`,
`db.source_species`.

Written:
* Once at death for the snapshot family.
* On every subsequent harvest / sever for the
  `wounds_at_death` and `removed_organs` lists (append-only).

The death-snapshot family is the **textbook right shape** for
`db.X` — write-once, read-many, mandatory persistence. The
post-death append mutations are slightly noisier than ideal but
volumes are tiny (a corpse accumulates 5–10 wound entries).

No action recommended.

### 4.7 · Crowd / room

Rooms have `db.crowd_base_level`, `db.is_sky_room`,
`db.outside`, `db.archived`. All low-volume, all write-rare.

No action recommended.

## 5 · Remediation roadmap

> **Measured deferral (post-audit).** The §5 items below were
> *implemented* against three stacked PRs (#451 / #452 / #453),
> then closed without merging after a Pepsi-challenge profile
> run measured the actual delta on a live build of the game.
>
> Methodology: `evennia shell` running a tight loop of
> `Character.get_display_name(observer)` against real DB
> characters, on both branches (master vs the refactor tip) with
> a clean reload between runs.  20,000 iterations + 200-call
> warmup, wall-clock and cProfile cumulative captured.
>
> | Bench | Master | Refactor | Delta |
> |---|---|---|---|
> | Common-case render (no pierce path) | 174.40 µs / call | 172.96 µs / call | **0.8 %** — noise |
> | Pierce path forced (cache hit) | 97.19 µs / call | 91.64 µs / call | **5.7 %** |
>
> The pierce-path 5.7 % gain is real but at single-digit player
> count comes out to roughly 0.56 ms/sec of CPU — below the
> perception floor.  The maintenance surface — a new
> `world/runtime_caches.py` module with a registry + weakrefs,
> flush hooks wired into `at_server_stop` /
> `at_server_reload_stop`, four migration sites, ~16 updated
> test files — was not justified by that gain at our current
> scale.
>
> **The §5 items below remain accurate as design guidance.**
> They describe the right shape of the changes if/when profiling
> under real load identifies one of these surfaces as a measured
> bottleneck.  Until then they stay deferred — not "TODO,"
> "shelved with reason."
>
> If you arrive here looking for "what should I refactor next,"
> the answer is: *nothing from this section, unless you've
> already profiled and have data that says otherwise.*  Honor
> the measurement; don't second-guess past-you.

Prioritised (when revisited) by
`write_frequency × runtime_cost / refactor_risk`.

### 5.1 · Pierce / forensic / diagnose / autopsy caches (P0)

**Surfaces affected:**
* `observer.db.disguise_pierce_cache`
* `cache_owner.db.forensic_recognition_cache`
* `target.db.diagnose_cache`
* `target.db.autopsy_procedure_cache`

**Problem:** all four follow the same read-on-every-render,
write-on-every-miss shape. The miss rate isn't zero — every new
presentation, every new physician–patient pairing, every fresh
crime-scene examination is a miss.

**Pattern to migrate to:**

```python
# Runtime tier — plain dict on the carrier object
class Character:
    def __init__(self, ...):
        ...
        self._pierce_cache_runtime: dict | None = None

    @property
    def _pierce_cache(self):
        """Lazy-load the persisted cache into a plain runtime
        dict on first read."""
        if self._pierce_cache_runtime is None:
            self._pierce_cache_runtime = (
                dict(self.db.disguise_pierce_cache or {})
            )
        return self._pierce_cache_runtime

    def flush_pierce_cache(self):
        """Push the runtime cache back to db.  Called at:
        - server shutdown hook
        - at_post_unpuppet (player disconnect)
        - explicit invalidation paths that already write
        """
        if self._pierce_cache_runtime is not None:
            self.db.disguise_pierce_cache = (
                dict(self._pierce_cache_runtime)
            )
```

All four caches share the *exact same shape*; we can lift the
pattern into a single mixin (`PersistedCacheMixin`?) or a small
helper module.

**Migration steps:**
1. Add the runtime-cache attribute pattern on `Character`.
2. Rewrite the four `attempt_*_recognition` /
   `attempt_disguise_pierce` / `perform_diagnose` /
   `_resolve_autopsy` call sites to use the runtime dict.
3. Wire the flush into `at_server_shutdown`,
   `at_post_unpuppet`, and any invalidation paths
   (`invalidate_pierce_cache_for_sleeve` already exists).
4. Tests: add a "cache survives restart" integration test that
   forces a flush and reload.

**Risk:** medium. The persistence semantics change subtly —
between flushes, a different connected session won't see
in-memory cache state on this character. For pierce
(per-observer), that's fine (one observer = one session).
For forensic/diagnose/autopsy caches stored on the *target*
(corpse, patient), a second physician examining concurrently
within the same scene won't see a fresh-this-session miss
recorded. Acceptable for the gameplay loop.

**Expected gain:** the largest single win in the codebase.
Removes a `db` write from the inner loop of `get_display_name`.

### 5.2 · `surgical_state` partial separation (P1)

`surgical_state.active_procedure` is in-memory-only by nature
(the procedure callback is stored in `_PROCEDURE_COMPLETE_HOOKS`
which is a module-level dict — process-local). The
"active_procedure" key persisting to db.surgical_state is
already a half-truth that gets cleared on
`interrupt_procedure`.

**Migration:**
* Move `active_procedure` to a plain attribute on the target
  (`self._active_procedure_runtime`).
* Keep `incisions` and `sutured_stumps` on db.surgical_state
  (those are genuinely durable).

**Risk:** low. The active-procedure tracking is already
in-process; this just makes that fact honest.

### 5.3 · `medical_chart` write batching (P1)

`save_chart` is called multiple times per chart-runner
iteration. `commence_chart` → `save_chart` (status flip) →
resolver runs → `_advance` → `save_chart` (mark done +
pending_result) → recursive `commence_chart` → `save_chart`
(next step running). 3+ writes per step.

**Migration:**
* Add an opt-in batching context: `with chart_lib.batch_writes(target):`.
* Inside the context, `save_chart` mutates the in-memory chart
  but does not flush.
* On context exit, single flush.

**Risk:** low if the batching context only wraps known atomic
operations (a single chart commence pass). Higher if we try to
batch across user-input boundaries.

### 5.4 · `recognition_memory` write rationalisation (P2)

Currently every unmasking transition writes to
`recognition_memory` via in-place mutation, which `_SaverDict`
catches. Volumes are small (per-room conscious observers ×
unmasking events) but worth noting.

**Migration:**
* Treat recognition_memory the same as caches — load to
  runtime once per session, flush on disconnect / shutdown.
* This couples with §5.1's mixin if we go that route.

**Risk:** medium. Recognition memory IS the long-term identity
graph. Losing flushes on a crash is more painful than losing
a pierce cache. Need a solid flush hook.

### 5.5 · `wounds_at_death` append-batching (P3, may skip)

Each harvest / sever appends to the list, triggering a full
serialise. Volumes are 5–10 entries lifetime per corpse. The
gain is microscopic.

Recommendation: **skip** unless profiling shows it matters.

### 5.6 · Combat handler write-density (P3)

The combat handler (`world/combat/handler.py`) is dense with
`db.X` writes (16 in the file). Worth a focused audit at some
point, but combat is a hot area that deserves its own
remediation pass rather than being tackled inside this
audit. Out of scope here.

## 6 · Migration patterns / templates

### 6.1 · Plain-attribute runtime tier

```python
class Carrier:
    """Whatever class hosts the data — Character, Corpse, etc."""

    # Plain Python attributes — initialised to None so a missing
    # attribute is unambiguous.  Do NOT use AttributeProperty
    # here; we want the descriptor protocol off the hot path.
    _runtime_cache: dict | None = None

    @property
    def runtime_cache(self) -> dict:
        if self._runtime_cache is None:
            self._runtime_cache = dict(self.db.persisted_cache or {})
        return self._runtime_cache

    def flush_runtime_cache(self) -> None:
        if self._runtime_cache is not None:
            self.db.persisted_cache = dict(self._runtime_cache)
```

### 6.2 · Flush at meaningful events

Hook points worth knowing:

| event                           | typeclass hook              | purpose                            |
|---------------------------------|-----------------------------|------------------------------------|
| Server stop                     | `at_server_shutdown`        | All in-memory caches flush         |
| Player disconnect               | `at_post_unpuppet`          | Per-character runtime flush        |
| Combat end                      | (custom: `_finalize_combat`)| Combatants list, handler state     |
| Procedure complete              | existing `_advance`         | Chart batched write                |
| Death                           | existing death pipeline     | Already a flush boundary           |

### 6.3 · `_SaverDict` literacy

For the *retained* `db.X` paths that hold dicts, remember:

* `isinstance(x, dict)` is `False` even when `x` is a
  `_SaverDict`. Duck-type with `hasattr(x, "get")`.
* In-place mutation (`x["foo"] = bar`) is persisted
  automatically. **Reassigning** (`x = {...}; obj.db.foo = x`)
  also persists.
* `dict(x)` produces a plain dict you can mutate freely
  without triggering persistence; reassign at the end if you
  want the changes to land.

This is already tribal knowledge in the codebase (see
`procedures.py:1258` and the `inspect <blood_pool>` work).
Worth folding into onboarding.

## 7 · Risk register

* **Cache divergence between sessions.** Moving the four
  recognition caches to runtime + flush means concurrent
  sessions on the same character don't see each other's
  cache state in real time. For per-observer caches this is
  fine; for caches stored on the *target* (corpse, patient)
  it's a behaviour change that needs an explicit decision.
* **Flush hooks missing on crash.** A hard process kill
  (OOM, SIGKILL) bypasses `at_server_shutdown`. Anything
  that has not been flushed since the last meaningful event
  is gone. For caches this is benign (re-roll on next read).
  For runtime-tier `surgical_state` it's worth verifying we
  can rebuild from the persisted slice.
* **Migration scope creep.** Each of the four caches is
  identical in shape; tempting to write a single mixin and
  retrofit all of them at once. Resist — ship one cache
  (pierce) end-to-end, watch the playtest for a week, then
  do the others. Pattern is established, work is mechanical.
* **`AttributeProperty` semantics on dicts.** Mutating a
  dict that originated from `AttributeProperty({})` may not
  trigger persistence if Evennia's class-default-instance
  path doesn't return the same `_SaverDict` wrapper.
  `recognition_memory` is the live example. Confirm
  behaviour before assuming it persists in place.

## 8 · What NOT to refactor

* **Death snapshots.** `db.signature_at_death`,
  `db.wounds_at_death`, `db.death_*`. Write-once, read-many,
  mandatory persistence. Leave alone.
* **`MedicalState`'s hybrid pattern.** Already the gold
  standard. Don't second-guess.
* **`AttributeProperty` for chargen-baseline attributes.**
  `sleeve_uid`, `species`, `grit`/`resonance`/`intellect`/`motorics`,
  `sex`, etc. These persist by design and have near-zero
  write rate. Refactoring would add risk for no gain.
* **EvMenu scratch state on ndb.** `_operate_target`,
  `_operate_pickable`, `charcreate_data`. Correct usage of
  ndb — leave alone.
* **`get_apparent_uid`'s no-cache stance.** Adding caching
  would create invalidation hell. The computation is cheap
  and free reads dominate.

## 9 · Suggested PR sequence

1. **Pierce cache runtime tier** — establish the pattern,
   ship it for one cache. Smallest blast radius, biggest
   measurable win.
2. **Forensic + diagnose + autopsy caches** — apply the same
   pattern, possibly extracted into a small mixin or helper.
3. **`surgical_state.active_procedure` runtime-only.**
4. **`medical_chart` write batching.**
5. **Decision point**: recognition_memory runtime tier
   (depends on how the cache work shakes out).

Stage 1 alone is worth doing this quarter; the rest can land
opportunistically.

## 10 · Open questions

1. **Flush hook strategy.** Should `at_server_shutdown` flush
   all runtime caches automatically via a registered-list
   pattern (`runtime_cache_registry`), or should each cache
   wire its own hook? Registered list is cleaner and avoids
   "forgot to register the hook" bugs; per-cache wiring is
   more explicit and grep-able. Lean: registered list, but
   defer the decision to whichever cache lands first.
2. **Perf validation.** No profiling harness in the repo, so
   the wins are theoretical. The shape of the change (descriptor
   protocol + pickle on every miss → dict lookup) is
   independently obvious and shipping blind is defensible.
   Consider lightweight instrumentation (decorator-counter on
   the cache surfaces) if we want to back the claim.
3. **Tick-vs-flush invariants.** The medical script's
   no-save-per-tick policy assumes that any persistence-worthy
   tick-state change (e.g. a wound stage progressing past a
   threshold) is followed by an event-driven flush before
   anything could cause restart-loss. Worth a deliberate audit
   when remediation work begins — particularly around
   `sync_severance_wound_stages` and condition tick effects.

---

**Maintenance contract:**

* §4 (audit findings) is a snapshot of authoring time. Re-run
  the `grep` survey before assuming the numbers are current.
* §5 (remediation roadmap) is **shelved** as of the measured
  deferral above.  Items are not "TODO" — they're documented
  design guidance for an as-yet-unmeasured future.  Don't pick
  them up without fresh profile data.
* §6 (migration patterns) is the part to copy from when
  implementing — treat it as a stable template.

**Discipline rule going forward (added post-deferral):**

* No perf work on this codebase without profile data showing
  the bottleneck.  Architectural cleanups that *don't* claim a
  perf benefit are fine to ship under the usual review; perf
  claims need numbers.
