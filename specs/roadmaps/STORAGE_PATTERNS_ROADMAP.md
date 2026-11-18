# Storage Patterns Roadmap

How the game stores state, and the order to change it if profiling ever
shows a storage surface is a bottleneck. There are four tiers: plain Python
attributes (runtime), `db.X` / `AttributeProperty` (persistence), `ndb`
(scratch) and Tags (boolean flags). Most of this file is reference: the
principle, the pattern catalog, the findings surface by surface, and the
template to copy from. The remediation sequence is shelved; see "What comes
next".

`AGENTS.md` is the operational reference for these conventions and should be
read alongside this file.

## The architectural principle

External advice (paraphrased) from a senior Evennia practitioner:

> Forget `ndb`. Keep your data structures light and decoupled from
> Evennia's attributes systems entirely as plain class attributes on
> other class objects. Gives you completely free reads. Only save to
> the backing attribute when something meaningfully changes in a way
> that you would be sad if the game restarted and that change was
> reset. That minimizes writes.

Restated in our terms:

* **Runtime tier**: ordinary Python objects with ordinary class
  attributes. No descriptors, no pickling, no DB round-trip. Reads cost a
  dict lookup.
* **Persistence tier**: `db.X` (or `AttributeProperty`) holds a
  *serialised snapshot* of the runtime object's meaningful state. Writes
  happen only when something would be **lost** at restart and that loss
  would be unacceptable.
* **`ndb`**: legitimate for true scratch state (menu position, queued
  callbacks, one-shot caches), but reach for it deliberately, not as "I
  didn't want to design persistence here." Most of what sits on `db.X`
  because we wanted persistence belongs on a plain attribute backed by an
  explicit flush.

"Forget ndb" is rhetorical hyperbole. The real guidance is **don't put
runtime objects on ndb thinking that's the same as putting them on a plain
attribute**. ndb is still a descriptor, still has overhead, and still
encourages the same attribute-soup access pattern.

The emphasis on *minimising writes* rests on Evennia's cost model:

* **Reads** (`x = obj.db.foo`): descriptor lookup, then the in-process
  Attribute cache. After the first hit, later reads of the same attribute
  on the same object are cheap, but the descriptor protocol is still in the
  path. A plain Python attribute (`x = self._foo`) is a dict lookup. That
  is what "free reads" means: orders of magnitude cheaper at hot-path rates.
* **Writes** (`obj.db.foo = value`): descriptor protocol, pickle
  serialisation, then a Django ORM write to the `ObjectAttribute` table.
  This is the expensive operation. Most of our writes are load-bearing; a
  non-trivial fraction are not.

## Why this matters here

Three characteristics of Gelatinous amplify the cost of the "convenient
`db.X`" pattern. Throughout this file, "hot" means called on every render,
every combat tick, every action emote, not "called occasionally."

1. **Hot render paths.** `get_display_name` fires on every look, every
   `msg_room_identity` broadcast, every action emote, every chart pane
   render. The chain reads `observer.db.disguise_pierce_cache` and writes
   back on every cache *miss*: `attempt_disguise_pierce`
   (`world/identity.py`) reads the cache and returns early on a hit; the
   write is reached only after the opposed roll. `attempt_display_pierce`
   reaches the cache only through `attempt_disguise_pierce`. The read is on
   the hot path. `grep` finds 497 `get_display_name` /
   `attempt_display_pierce` call sites; most exercise the cache.
2. **Ticker-driven mutation.** `MedicalScript` ticks every 60 s
   (`MEDICAL_TICK_INTERVAL`) and mutates `_medical_state` in place: blood
   loss, pain accumulation, consciousness drift, healing. Its `at_repeat`
   calls `save_medical_state` at the end of every tick, unconditionally
   (#2418): without that, a reload undid bleeding and lost dressings. A
   tick-state change is therefore lost on restart only if the restart falls
   inside that tick. Other saves happen at events (procedure complete, admin
   change, organ swap, damage application).
3. **Dict-shaped state on `db`.** `db.surgical_state`, `db.medical_chart`,
   `db.diagnose_cache`, `db.wounds_at_death`, `db.signature_at_death`.
   Reads cost a descriptor lookup plus a `_SaverDict` proxy (the reason the
   medical pipeline duck-types instead of using `isinstance(x, dict)`).
   Writes round-trip through pickle.

## Survey method

* `grep -rh '\.db\.\w*\s*=' --include='*.py'`: assignment count per
  attribute name (1,200+ hits).
* `grep -rh '\.ndb\.\w*'`: ndb usage (256 hits).
* `grep -c '\.db\.' <file>`: files ranked by db-write density.
* A hand-read of the runtime/persistence boundary for `MedicalState`,
  `surgical_state`, `medical_chart`, the four recognition caches, and the
  death-snapshot family.

The counts in this file are a snapshot from the survey and drift; the
patterns are stable. Re-run the `grep` survey before assuming a number is
current.

## Pattern catalog

### The runtime/persistence split (gold standard)

The exemplar is `MedicalState` (`world/medical/core.py`):

* The runtime object lives at `self._medical_state`, a plain Python
  attribute on the `Character`. It holds `organs` (dict of `Organ`
  objects), `conditions` (list), `blood_level`, `pain_level`,
  `consciousness`. Reads are free.
* The `medical_state` property in `typeclasses/characters.py` lazy-loads
  from `db.medical_state` (the serialised dict) into `_medical_state` on
  first access, via `load_medical_state`.
* `save_medical_state` (`world/medical/utils.py`) calls `to_dict()` and
  writes the serialised form to `db.medical_state`. It is called from many
  places (grep `save_medical_state` for the current set): the medical tick
  (`MedicalScript.at_repeat`, every tick), treatments, procedures, augments,
  substances, NPC spawn (`world/director/population.py`), soul posts
  (`world/souls/posts.py`), armor, items, characters, and three `CmdAdmin`
  paths.

The pattern: the runtime tier is canonical, the persistence tier is a
snapshot of it, and writes happen at named boundaries.

### AttributeProperty (Evennia-native persistent attribute)

92 uses, concentrated on `Character` (`typeclasses/characters.py`):

* `grit`, `resonance`, `intellect`, `motorics`
* `sex`, `sleeve_uid`, `height`, `build`, `hair_color`, `hair_style`,
  `sdesc_keyword`
* `recognition_memory`, `voice_memory`

`species` is not an `AttributeProperty`: it is a property over `db.species`
(#2205).

These are values that:

1. Persist across restarts (chargen state, identity baseline).
2. Are read often but written rarely (e.g. `sleeve_uid` is set once at
   chargen and read on every UID computation).
3. Need a default value the descriptor can provide.

`AttributeProperty` is fine here: it is read-cached after first access and
the write rate is near zero. The exception is `recognition_memory`
(mutated by every unmasking, remember call and pierce cache update); whether
it should stay an `AttributeProperty` is item 5 under "What comes next".

### Per-attribute `db.X` writes (the convenient pattern)

Top writers by count (from the `grep` survey):

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

The partition:

* **Write-once / rare event** (desc, height_override, sleeve_uid,
  death_*): `db.X` is correct. No work to do.
* **Append-mutation** (wounds_at_death, bleeding_incidents on BloodPool,
  removed_organs): each append triggers a full serialisation pass.
  Candidates for batching, but the volumes are small (a corpse accumulates
  5–10 wound entries, not 5,000).
* **Per-action mutation** (surgical_state, medical_chart, combatants):
  high-frequency writes that don't strictly need per-step persistence.
* **Per-render cache** (disguise_pierce_cache, forensic_recognition_cache,
  diagnose_cache, autopsy_procedure_cache): the worst category. High read
  rate, meaningful write rate, and every miss writes back. This is the
  primary remediation target.

### The Tag system (boolean flags)

`AGENTS.md` says: *"For simple booleans, prefer the Tag system
(`obj.tags`) over attributes."* Tags are indexed at the DB level and don't
go through pickle, so they're the right shape for "is this thing flagged X"
queries.

Boolean `db.X = True/False` writes that should be Tags, all still `db`
attributes:

| attr               | written in                        |
|--------------------|-----------------------------------|
| `db.combat_is_running` | `world/combat/handler.py` (4 sites) |
| `db.pin_pulled`    | `commands/CmdThrow.py`, `commands/explosion_utils.py` (4 sites), `commands/CmdExplosives.py`; read in `commands/combat/jump.py` |
| `db.is_infinite`   | `typeclasses/shopkeeper.py` (2 sites), `typeclasses/butcher.py`, build scripts |
| `db.integrate`     | `commands/CmdExplosives.py`, `typeclasses/objects.py`, `typeclasses/bar.py`, `typeclasses/lockers.py`, `typeclasses/butcher.py`, many build scripts |
| `db.head_severed`  | `typeclasses/corpse.py`, `typeclasses/items.py` (corpse / appendage chain) |

Conversion is mechanical (`obj.db.X = True` →
`obj.tags.add("X", category="...")`) but it carries a one-time audit tax
across read sites (`if obj.db.X` → `if obj.tags.has("X", category="...")`).
`integrate` is written most widely, so its audit tax is the largest of the
five. Worth doing per flag on first touch; not worth a sweeping migration
PR.

`archived` is the one flag with a Tag, and it is not a mechanical
conversion. The Tag is the query index: added in `archive_character`, read
in `is_archived`, cleared in `unarchive_character`, and queried in one pass
in `typeclasses/accounts.py`. `db.archived` is deliberately kept as the
display/audit record and as the fallback for sleeves archived before the
Tag existed (comment in `archive_character`). `Character.archive_character`
and `unarchive_character` keep both stores in sync; the one other writer,
the failed-return undo in `world/souls/posts.py`, sets both by hand.
`web/website/views/characters.py` is a caller, not a writer: it calls
`character.archive_character(reason="manual", owner=request.user)` and
`old_character.unarchive_character()` (after reading `db.archived`).

### `ndb` scratch state (transient by design)

256 ndb references (counted before #3579 removed `jump_movement_allowed`;
not re-counted). Top users:

| attr                          | uses | rightness                         |
|-------------------------------|------|-----------------------------------|
| `charcreate_data`             | 72   | ✓ chargen menu scratch            |
| `_operate_target`             | 15   | ✓ EvMenu scratch                  |
| `_operate_pickable`           | 15   | ✓ menu picker scratch             |
| `in_proximity_with`           | 14   | ? combat — could be plain attr    |
| `aiming_at`                   | 11   | ? combat targeting                |
| `aimed_at_by`                 | 10   | ? reverse of above                |
| `_shortdesc_keywords`         | 8    | ✓ rendering scratch               |
| `death_curtain_pending`       | 7    | ✓ one-shot transition state       |
| `sever_task`                  | 6    | ? procedure delay handle          |
| `unconsciousness_pending`     | 3    | ✓ flag                            |

ndb usage is mostly appropriate: menu scratch, transition flags, one-shot
timers. The dubious ones are combat-state items (`aiming_at`,
`in_proximity_with`) that need to survive combat interruption but not a
server restart. These could equally be plain attributes on the actor and
behave identically.

Falling shows the split this section argues for (#3579). Jumps and falls
relocate with `move_to`, which never reaches `Exit.at_traverse`; the sky
block refuses all walking with no exception, and falling is driven by
`world/gravity.py` off `Room.at_object_receive`. Two ndb keys are
deliberately transient: `ndb.airborne_token` (a leap's one-tick stay-up
grant, so a far perch that is itself air cannot re-grant it forever) and
`ndb.fall_intent` (the verb's flight plan, consumed by the arriving room's
hook). The durable half of a fall is a `db.falling` attribute, swept at
boot.

## Findings, surface by surface

### Identity / recognition

**Good shapes:**

* `get_apparent_uid(char)` (`world/identity.py`) is computed with no
  caching, and is called on every render of every character. Its
  per-call cost is not trivial: it reads three descriptor-backed attributes
  (`db.height_override`, `db.build_override`, `db.keyword_override`, in
  `get_identity_signature`), calls `get_essential_item_type_ids`, which
  walks `get_worn_items()` (`typeclasses/clothing_mixin.py`, itself reading
  the `worn_items` AttributeProperty) and inspects two attributes per worn
  item, then `repr()`s the 5-tuple signature and runs `blake2b` over it.
  None of that is a plain-dict read, and it scales with worn-item count. It
  is deliberately uncached despite that cost, because invalidation would be
  hell (see "What not to refactor").
* `signature_at_death` / `apparent_uid_at_death` are written once at death.

**Problem shapes:**

* `observer.db.disguise_pierce_cache` (`world/identity.py`,
  `attempt_disguise_pierce`): a `dict` keyed on
  `(target.dbref, apparent_uid)`. Read on every `attempt_display_pierce`
  call (which fires from every `get_display_name` where the looker doesn't
  directly know the current UID). Written on every cache miss. It is
  persisted, so a pierce roll cached on day 1 is still valid on day 30.
* `recognition_memory` is an `AttributeProperty({}, autocreate=True)`
  mutated by the unmasking pipeline, the remember command, and passive
  recognition. Each mutation is technically a descriptor-set, but because
  the value is a dict (a `_SaverDict` in Evennia's wrapper), the in-place
  mutation is caught and persisted. So writes happen on every
  `_broadcast_unmasking` cell B/D event and every `remember`. Volumes are
  low but the pattern is "implicit write on every mutation."

**Verdict on the pierce cache:** persistence is load-bearing (it prevents
Intellect-reroll abuse across sessions), but the read-then-write-back on
every miss is the hot-path cost. See item 1 under "What comes next".

### Medical state

The exemplar (see the pattern catalog). `Organ` objects live inside the
in-memory `MedicalState`. When wound state changes
(`organ.wound_stage = "treated"`, `organ.injury_type = "bullet"`), the
change is to the in-memory tree, and it persists only when something calls
`save_medical_state`. Those flushes fire on, among others (grep
`save_medical_state` for the full set):

* Every medical tick (`MedicalScript.at_repeat`).
* Damage application (the procedure-resolve and combat paths).
* Organ harvest/install (`items.py`).
* Admin overrides (`CmdAdmin`).
* Suturing: `_resolve_suture` flushes through `apply_vital_consequences`
  (`world/medical/procedures.py`).

**Question to interrogate:** does every wound-stage mutation have a flush?
`sync_severance_wound_stages` (#437) needs none: it does not touch
`MedicalState`. It writes the refreshed stages straight back to
`corpse.db.wounds_at_death`, so they persist at once.

### Surgical / chart procedures

`target.db.surgical_state` and `target.db.medical_chart` are the two
primary persistence surfaces.

**`surgical_state`** (lazy-initialised by `_state` in
`world/medical/procedures.py`) holds `incisions` (per location, when it was
opened), `active_procedure` (the verb, the actor's dbref and the kwargs),
and `pending_step_result` (the chart runner's pickup slot). It is written on
every procedure start, every procedure resolution, every incision
open/close, and chart-runner step transitions. The `pending_step_result`
slot (autopsy, #449) is written by `_resolve_autopsy` and cleared by the
chart runner's `_advance` when it moves the result onto the step.
`sutured_stumps` is not inside `surgical_state`: it is its own top-level
attribute, written in `_resolve_suture` (`target.db.sutured_stumps`) and
read through `normalize_sutured_stumps` (`world/medical/severance.py`).

**Risk of losing it on restart:** moderate. An active procedure (mid-delay)
loses its `_PROCEDURE_COMPLETE_HOOKS` entry (in-memory only) regardless, so
the chain already dies on restart by design. The open incisions and chart
status genuinely should persist; the active-procedure record arguably
should not.

**`medical_chart`** holds a version, `authored_by` (a dbref), a status,
`next_step_id` (int) and a list of steps; each step has `verb`, `args`,
`status`, `result` and `outcome`. It is written every time `save_chart`
(`world/medical/charts.py`) is called, which is every status flip
(`commence_chart`, `_advance`, `interrupt_procedure`, edit-chart actions).

The chart genuinely needs persistence: surgeons hand off charts, patients
survive restarts. But mid-commence writes (running → done → status of the
next step → running → ...) happen 3+ times per step transition. It could be
a single write per step.

### Combat / handler state

`target.db.combatants` has 14 writes and 80 reads: written every time an
actor joins or leaves combat, read by every targeting resolution. The
handler (`world/combat/handler.py`) is the largest write-frequency violator
(16 db writes). State that should arguably be runtime:

* The combatants list (it matters for the current encounter; if the server
  restarts mid-combat, what should happen? Probably combat ends).
* Proximity tracking (`in_proximity_with` on ndb, already transient).
* Aiming relationships (`aiming_at` / `aimed_at_by` on ndb).

The hybrid is reasonable: ndb for the volatile "who is aiming at whom right
now," db for the higher-level "is this character in a fight" flag. But the
handler module itself writes db heavily and could benefit from a
runtime-tier refactor.

### Inventory / clothing / hands

`worn_items` is an `AttributeProperty` dict; `hands` is a derived property
view on the species template, already runtime.

`wear_item` and `remove_item` mutate `worn_items` in place, and persistence
relies on `_SaverDict` catching the change. Each mutation serialises the
whole dict. Volumes are bounded (worn items per character rarely exceed
20), but every wear/remove cycle on a busy avatar adds up. The pattern is
acceptable but inelegant; a refactor to "plain attr + explicit flush on
commit" would be a marginal win at high risk.

### Death snapshots

`db.signature_at_death`, `db.apparent_uid_at_death`, `db.wounds_at_death`,
`db.medical_state_at_death`, `db.removed_organs`, `db.severed_locations`,
`db.death_time`, `db.death_cause`, `db.source_signature`,
`db.source_apparent_uid`, `db.source_corpse_dbref`, `db.source_species`.

Written once at death for the snapshot family, and on every later harvest /
sever for the `wounds_at_death` and `removed_organs` lists (append-only).

This is the textbook right shape for `db.X`: write-once, read-many,
mandatory persistence. The post-death appends are slightly noisier than
ideal but volumes are tiny (a corpse accumulates 5–10 wound entries). No
action recommended.

### Crowd / room

Rooms have `db.crowd_base_level`, `db.is_sky_room`, `db.outside`. All
low-volume, all write-rare. No action recommended.

## What comes next

**Sequencing rule: shelved until measured.** Do not start this sequence
without profile data showing one of these surfaces is a bottleneck; if that
happens, this is the order. The items are not "TODO": they are design
guidance for an as-yet-unmeasured future, "shelved with reason." If you
arrive here looking for what to refactor next, the answer is nothing from
this section unless you already have profile data that says otherwise.
Honor the measurement.

**The reason.** The items were implemented in three stacked PRs (#451,
#452, #453) and closed without merging after a profile run measured the
delta on a live build: `evennia shell` running a tight loop of
`Character.get_display_name(observer)` against real DB characters, on
master and on the refactor tip, with a clean reload between runs; 20,000
iterations after a 200-call warmup, wall-clock and cProfile cumulative
captured.

| Bench | Master | Refactor | Delta |
|---|---|---|---|
| Common-case render (no pierce path) | 174.40 µs / call | 172.96 µs / call | **0.8 %** — noise |
| Pierce path forced (cache hit) | 97.19 µs / call | 91.64 µs / call | **5.7 %** |

The pierce-path 5.7 % gain is real, but at single-digit player count it
comes to roughly 0.56 ms/sec of CPU, below the perception floor. The
maintenance surface (a new `world/runtime_caches.py` module with a registry
and weakrefs, flush hooks wired into the server-level `at_server_stop` /
`at_server_reload_stop`, four migration sites, ~16 updated test files) was
not justified by that gain at our current scale.

When revisited, prioritise by
`write_frequency × runtime_cost / refactor_risk`. The order:

1. **Pierce cache runtime tier.** 📋 UNBUILT (no issue). Establish the
   pattern and ship it for one cache. Smallest blast radius; the measured
   gain was 5.7 % on the pierce path.
2. **Forensic + diagnose + autopsy caches.** 📋 UNBUILT (no issue). Apply
   the same pattern, possibly extracted into a small mixin or helper.
3. **`surgical_state.active_procedure` runtime-only.** 📋 UNBUILT (no
   issue).
4. **`medical_chart` write batching.** 📋 UNBUILT (no issue).
5. **Decision point: `recognition_memory` runtime tier.** 📋 UNBUILT (no
   issue). Depends on how the cache work shakes out.

The risk register advises shipping the pierce cache end-to-end before the
others; see "Migration scope creep".

### 1–2 · Pierce / forensic / diagnose / autopsy caches (P0)

**Surfaces:**

* `observer.db.disguise_pierce_cache`
* `cache_owner.db.forensic_recognition_cache`
* `target.db.diagnose_cache`
* `target.db.autopsy_procedure_cache`

**Problem:** all four have the same read-on-every-render,
write-on-every-miss shape. The miss rate isn't zero: every new
presentation, every new physician–patient pairing, every fresh crime-scene
examination is a miss.

**Pattern to migrate to:** the plain-attribute runtime tier (template under
"Migration patterns"). A plain runtime dict on the carrier object,
lazy-loaded from the persisted `db` cache on first read, and pushed back to
`db` by a flush method called at server shutdown, at `at_post_unpuppet`
(player disconnect), and on explicit invalidation paths that already write.
For the pierce cache: `_pierce_cache_runtime` (the runtime dict), the
`_pierce_cache` lazy-load property, and `flush_pierce_cache`. All four
caches share the exact same shape, so the pattern can be lifted into a
single mixin (`PersistedCacheMixin`?) or a small helper module.

**Migration steps:**

1. Add the runtime-cache attribute pattern on `Character`.
2. Rewrite the four `attempt_forensic_recognition` /
   `attempt_disguise_pierce` / `perform_diagnose` / `_resolve_autopsy`
   call sites to use the runtime dict. The forensic cache is also kept
   under per-UID names (`forensic_recognition_cache_<uid>`, passed from
   `commands/forensics.py`).
3. Wire the flush into `at_server_shutdown`, `at_post_unpuppet`, and any
   invalidation paths (`world.identity.erase_look` drops the won
   see-through verdicts that rest on a forgotten name; lost verdicts stay,
   so a roll cannot be bought again, #3817/#3825).
4. Tests: add a "cache survives restart" integration test that forces a
   flush and reload.

**Risk:** medium. The persistence semantics change subtly: between
flushes, a different connected session won't see in-memory cache state on
this character. For pierce (per-observer), that's fine (one observer = one
session). For forensic/diagnose/autopsy caches stored on the *target*
(corpse, patient), a second physician examining concurrently within the
same scene won't see a fresh-this-session miss recorded. Whether that is
acceptable is not decided (see "Not decided" #3).

**Expected gain (measured):** 0.8 % on a common render and 5.7 % when the
pierce path runs. The write happens only on a cache miss.

### 3 · `surgical_state` partial separation (P1)

`active_procedure` is in-memory-only by nature: the procedure callback is
stored in `_PROCEDURE_COMPLETE_HOOKS`, a module-level dict (process-local).
The `active_procedure` key persisting to `db.surgical_state` is already a
half-truth that gets cleared on `interrupt_procedure`.

**Migration:**

* Move `active_procedure` to a plain attribute on the target
  (`self._active_procedure_runtime`).
* Keep `incisions` on `db.surgical_state` (genuinely durable).
  `sutured_stumps` is a separate attribute and needs no change either way.

**Risk:** low. The active-procedure tracking is already in-process; this
makes that fact honest.

### 4 · `medical_chart` write batching (P1)

`save_chart` is called several times per chart-runner iteration:
`commence_chart` → `save_chart` (status flip) → resolver runs → `_advance`
→ `save_chart` (mark done + pending result) → recursive `commence_chart` →
`save_chart` (next step running). 3+ writes per step.

**Migration:**

* Add an opt-in batching context: `with chart_lib.batch_writes(target):`.
* Inside the context, `save_chart` mutates the in-memory chart but does not
  flush.
* On context exit, a single flush.

**Risk:** low if the batching context wraps only known atomic operations (a
single chart commence pass). Higher if it batches across user-input
boundaries.

### 5 · `recognition_memory` write rationalisation (P2)

Every unmasking transition writes to `recognition_memory` through in-place
mutation, which `_SaverDict` catches. Volumes are small (per-room conscious
observers × unmasking events) but worth noting.

**Migration:**

* Treat `recognition_memory` the same as the caches: load to runtime once
  per session, flush on disconnect / shutdown.
* This couples with the cache mixin if that route is taken.

**Risk:** medium. Recognition memory IS the long-term identity graph.
Losing flushes on a crash is more painful than losing a pierce cache. It
needs a solid flush hook.

### Not in the sequence

* **`wounds_at_death` append-batching (P3, may skip).** Each harvest /
  sever appends to the list, triggering a full serialise. Volumes are 5–10
  entries lifetime per corpse; the gain is microscopic. Recommendation:
  **skip** unless profiling shows it matters.
* **Combat handler write-density (P3).** The combat handler
  (`world/combat/handler.py`) is dense with `db.X` writes (16 in the file).
  Worth a focused audit at some point, but combat is a hot area that
  deserves its own remediation pass. Out of scope here.

## Migration patterns

This is the part to copy from when implementing; treat it as a stable
template.

### Plain-attribute runtime tier

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

### Flush at meaningful events

| event                           | hook                        | purpose                            |
|---------------------------------|-----------------------------|------------------------------------|
| Server stop                     | `at_server_shutdown`        | All in-memory caches flush         |
| Player disconnect               | `at_post_unpuppet`          | Per-character runtime flush        |
| Combat end                      | `CombatHandler.stop_combat_logic` (`world/combat/handler.py`); per-combatant cleanup in `_cleanup_all_combatants` / `_cleanup_combatant_state` | Combatants list, handler state |
| Procedure complete              | existing `_advance`         | Chart batched write                |
| Death                           | existing death pipeline     | Already a flush boundary           |

`at_server_shutdown` is the object-level hook. `at_server_stop` /
`at_server_reload_stop` are the server-level hooks
(`server/conf/at_server_startstop.py`).

### `_SaverDict` literacy

For the `db.X` paths that hold dicts:

* `isinstance(x, dict)` is `False` even when `x` is a `_SaverDict`.
  Duck-type with `hasattr(x, "get")`.
* In-place mutation (`x["foo"] = bar`) is persisted automatically.
  **Reassigning** (`x = {...}; obj.db.foo = x`) also persists.
* `dict(x)` produces a plain dict you can mutate freely without triggering
  persistence; reassign at the end if you want the changes to land.

This is already tribal knowledge in the codebase (see `organs_at_location`
in `world/medical/procedures.py` and the `inspect <blood_pool>` work).
Worth folding into onboarding.

## Risk register

* **Flush hooks missing on crash.** A hard process kill (OOM, SIGKILL)
  bypasses `at_server_shutdown`. Anything not flushed since the last
  meaningful event is gone. For caches this is benign (re-roll on next
  read). For runtime-tier `surgical_state` it's worth verifying it can be
  rebuilt from the persisted slice.
* **Migration scope creep.** The four caches are identical in shape, so it
  is tempting to write a single mixin and retrofit all of them at once.
  Resist: ship one cache (pierce) end-to-end, watch the playtest for a
  week, then do the others. The pattern is established; the work is
  mechanical.
* **`AttributeProperty` semantics on dicts.** Mutating a dict that
  originated from `AttributeProperty({})` may not trigger persistence if
  Evennia's class-default-instance path doesn't return the same
  `_SaverDict` wrapper. `recognition_memory` is the live example. Confirm
  behaviour before assuming it persists in place.
* **Cache divergence between sessions.** See "Not decided".

## What not to refactor

* **Death snapshots.** `db.signature_at_death`, `db.wounds_at_death`,
  `db.death_*`. Write-once, read-many, mandatory persistence. Leave alone.
* **`MedicalState`'s hybrid pattern.** Already the gold standard. Don't
  second-guess.
* **`AttributeProperty` for chargen-baseline attributes.** `sleeve_uid`,
  `grit`/`resonance`/`intellect`/`motorics`, `sex`, etc. These persist by
  design and have near-zero write rate. Refactoring would add risk for no
  gain.
* **EvMenu scratch state on ndb.** `_operate_target`, `_operate_pickable`,
  `charcreate_data`. Correct usage of ndb; leave alone.
* **`get_apparent_uid`'s no-cache stance.** Adding caching would create
  invalidation hell. The per-render cost is real (db reads, a worn-items
  walk, a blake2b hash), but it stays uncached on purpose.

## Discipline rule

* No perf work on this codebase without profile data showing the
  bottleneck. Architectural cleanups that *don't* claim a perf benefit are
  fine to ship under the usual review; perf claims need numbers.

## Not decided

1. **Flush hook strategy.** Should `at_server_shutdown` flush all runtime
   caches automatically via a registered-list pattern
   (`runtime_cache_registry`), or should each cache wire its own hook? A
   registered list is cleaner and avoids "forgot to register the hook"
   bugs; per-cache wiring is more explicit and grep-able. Lean: registered
   list, but defer the decision to whichever cache lands first.
2. **Perf validation.** There is no committed profiling harness
   (`grep -rl "cProfile\|pstats\|timeit\|perf_counter" --include='*.py'`
   returns nothing), and the suggested lightweight instrumentation (a
   decorator-counter on the cache surfaces) was never built. Wins on this
   codebase are not theoretical: measured passes have been run ad hoc
   through `evennia shell` (the profile at the head of "What comes next";
   #462 / #465's `get_display_name` profile, which led to a change in
   `world/grammar.py`, `MedicalState._cached_is_dead`
   (`world/medical/core.py`) and the session-gated broadcast; and #3077's
   bleeding-tick profile, where a blood-pool flush was 72 % of the tick,
   which led to `BLOOD_POOL_FLUSH_TICKS` (`world/medical/constants.py`,
   consumed in `world/medical/script.py`)). Shipping blind is not
   defensible; see the discipline rule. The standing gap is that every one
   of those profiles was thrown away after use; nothing is repeatable.
   Not decided: whether to build a repeatable profiling harness or that
   instrumentation.
3. **Cache divergence between sessions.** Moving the four recognition
   caches to runtime + flush means concurrent sessions on the same
   character don't see each other's cache state in real time. For
   per-observer caches this is fine; for caches stored on the *target*
   (corpse, patient) it's a behaviour change that needs an explicit
   decision.
