# Condition Cadence Spec — Elapsed-Time Rates

Medical conditions apply their effects as rates per minute of real time.
A tick is only a sampling moment: each condition remembers when it was
last processed, computes how much real time has passed, and applies that
much effect. The design was settled in discussion on 2026-06-11 (issue
#501).

## 0 · The principle: where time lives

Time lives **in the condition**, not in the tick. If effects were per-tick
numbers, the tick interval would be the game balance, and changing the
clock would silently rebalance the game. This happened: when #465
corrected the medical tick from a testing-leftover 12s to the intended
60s, infection silently became 5× slower than designed — its probability
comments still read "25 ticks at 12s intervals." Nobody changed
infection; they changed the clock.

The wage analogy: per-tick conditions are paid per paycheck, so changing
paycheck frequency changes their salary. Elapsed-time conditions are paid
hourly — pay them weekly, daily, whenever; they earn the same.

So "how often should X tick?" is **a reaction-window and drama decision,
never a balance decision.** Burning at 30 damage/minute ticked at 60s is
one unsurvivable hammer blow; ticked at 10s it is six pulses with five
chances to dive into the water. Same total. The designer chooses the
experience; the math doesn't care.

## 1 · Settled design decisions

These were decided in discussion (2026-06-11) and are not open for silent
revision. They change only by explicit design discussion, not by
implementation drift.

1. **Rates are per minute of real time.** Ticks sample elapsed time at
   any frequency.
2. **Everyone wounded ticks — no lazy evaluation for the living.** People
   and NPCs bleed out whether or not anyone is watching. Lazy/catch-up
   computation lies to the rest of the world in the gap (a guard
   computed-dead at observation was "alive" to every other system for the
   interim). Lazy evaluation is valid only for state that is a pure
   function of time, has no side effects on other entities, and has a
   single reader — corpse decay qualifies; living creatures never do.
3. **Downtime is capped.** Reloads and crashes are rare and
   operator-caused; a restart must not bleed anyone out in absentia.
   Elapsed time is clamped (§4.3) so conditions resume at their cadence
   without billing for server downtime.
4. **The carrier is one `MedicalScript` per wounded character.** The
   2026-06-11 benchmark (10/100/500/1000 wounded characters, condition
   math alone) showed steady-state ticking is cheap — 1,000 simultaneous
   full medical ticks ≈ 50ms — and that the real cost axis is DB-write
   churn, which favored not changing carriers. TickerHandler was
   evaluated (auto-pruning, no ScriptDB churn, but O(N²) persistence
   saves and synchronized firing) and shelved, to be revisited only on
   operational pain. On 2026-09-09 that pain arrived, and the decision
   was made to replace this carrier with a single global
   `medical_heartbeat`, 📋 UNBUILT (#3076, §12). Until it exists the game
   runs one `MedicalScript` per wounded character.
5. **Tick frequency may vary per script** (Phase 3, 📋 UNBUILT, parked;
   §12): a character's medical script may run faster while an urgent
   condition exists and return to baseline after — safe *only because*
   of decision 1.
6. **The tactical tier is parked** (Phase 3, 📋 UNBUILT; §12): in-combat
   urgent conditions will process inside the combat handler's existing
   6-second round (no new scripts, scoped to active fights).
   Elapsed-time rates make the combat↔medical handoff free: the next tick
   simply computes a larger elapsed. Build when fire / severe bleeding
   exist as content.
7. **Clock reads go through one indirection** (§4.1) so the future
   in-game time system (#301) can swap in without touching conditions.

## 3 · Effect taxonomy

Three kinds of effect exist; each is computed differently:

| Kind | Example | Computation |
|---|---|---|
| **Continuous quantity** | bleeding blood loss | `rate_per_minute × elapsed_minutes`, applied fractionally |
| **Continuous integer quantity** | dressing healing (HP) | fractional progress kept on the organ (`dressing_progress`); whole HP is applied once it reaches ≥ 1 |
| **Probabilistic event** | infection worsening chance; pain fading one severity | per-minute hazard `p`; over elapsed `t` minutes, fire with probability `1 − (1 − p)^t` |

Severity values stay integers (the whole condition system keys off
integer severities) and change one step at a time when a per-minute
hazard fires (§4.4); conditions keep no fractional progress. The one
fractional accumulator is dressing healing, kept on the organ
(`Organ.dressing_progress`).

## 4 · Mechanics

### 4.1 · The clock

`world/medical/clock.py` is the one clock module. `now()` returns the
current clock value in seconds and is the swap point for #301.
`elapsed_game_minutes(since, current=None)` returns the real minutes
elapsed since `since`, never negative.

No condition or script reads `time.time()` for rate math directly.

### 4.2 · The base-class contract

`MedicalCondition` (`world/medical/conditions.py`) carries:

* `last_processed` — a wall-clock timestamp, persisted in `to_dict()`;
  it defaults to *now* on creation and when a persisted condition
  without it is loaded (§7).
* `process(character, current=None)` — the only entry point carriers
  call. It computes `elapsed = min(elapsed_game_minutes(last_processed,
  current), ELAPSED_CAP_MINUTES)`, sets `last_processed` to `current`,
  then calls `tick_effect(character, elapsed)` when elapsed > 0.
  Subclasses implement `tick_effect(character, elapsed_minutes)` and
  never touch the clock themselves.

The medical script's `at_repeat` calls `process(obj)` on each condition.
After applying conditions and healing, `at_repeat` saves the medical
state (`save_medical_state`, #2418) before it checks whether to stop, so
`last_processed`, severities, blood level and `dressing_progress` survive
a reload. A tick that ends in death returns before this save. Saving only
on change, with a bounded checkpoint, is part of the 📋 UNBUILT carrier
(#3076). The future tactical tier calls the *same* `process()` from the
combat round — that is the entire handoff.

### 4.3 · The downtime cap

`ELAPSED_CAP_MINUTES = 2 × (MEDICAL_TICK_INTERVAL / 60)` — twice the
expected sampling gap. A normal tick sees ~1 minute; a tick arriving
after a 10-minute reload sees 2. Players lose at most one extra tick's
worth of progression to a restart, never an absence's worth.

The cap constant lives with the other medical constants
(`world/medical/constants.py`). It is applied in two places:
`MedicalCondition.process()` for conditions, and `MedicalScript.at_repeat`
for dressing healing, which keeps its own marker on `ndb`
(`last_heal_process`) that a reload resets to now.

### 4.4 · Probabilistic events

Chances are per-minute hazards. A conversion from a per-tick chance
preserves the *designed* behavior, not the accidentally-current one.
`hazard_fires` in `world/medical/conditions.py` samples a hazard over the
elapsed window (fires with probability `1 − (1 − p)^t`) and caps `p` at
0.95.

## 5 · Magnitude conversion table

The tick is 60s, so most per-tick values carried over 1:1 to per-minute
and game feel is preserved. Values that were authored for the old 12s tick
were running 5× off their design and are restored to the designed pacing:

| Constant / behavior | Per 60s tick | Per minute | Note |
|---|---|---|---|
| `BLOOD_LOSS_PER_SEVERITY` | 0.5–10% (severity 1–10) | same, per minute | 1:1 — authored for 60s. The rate derives from *current* severity, and treatment follows the layered-brakes model (#507): bandage slows to 30%, dressing stops, clotting only at severity ≤5 |
| Bleeding natural clotting (severity −1 chance) | per tick | `BLEEDING_CLOT_HAZARD_PER_MINUTE = 0.10`, only at severity ≤ `BLEEDING_SELF_CLOT_MAX_SEVERITY` (5), doubled when bandaged (#507) | 1:1 |
| Pain decay | 20% chance per tick | `PAIN_DECAY_HAZARD_PER_MINUTE = 0.20` | 1:1 |
| Infection: treated improvement | 12% per tick (authored: "12% per 12s tick") | `INFECTION_IMPROVE_HAZARD_PER_MINUTE = 0.07` (`1−(1−0.07)⁵ ≈ 30%` per five minutes, the original "improves every ~5 minutes" design) | the 5× drift fix. It is still a balance knob; no medical balance pass has run, so the owner has not confirmed this pacing |
| Infection: untreated worsening | granular per-tick chance (authored for "~20min progression" at 12s) | **restored** to the documented ~20-minute progression curve | drift fix |
| Infection × blood filtration | — | heal hazard × max(0.25, filtration); worsen hazard × (1 + (1 − filtration)) | CAPACITY_CONSUMERS §7.1; `BLOOD_FILTRATION_HEAL_FLOOR`, `BLOOD_FILTRATION_WORSEN_SLOPE` |
| Consciousness suppression recovery | — | `CONSCIOUSNESS_RECOVERY_HAZARD_PER_MINUTE`: knockout 0.25, sedative 0.50, anesthesia 0.10, trauma 0.20 | authored per minute |
| Renal failure progression | — | `RENAL_FAILURE_PROGRESSION_PER_MINUTE = 0.15` | authored per minute |
| Dressing/splint knitting (`_hp_per_tick`) | rating//5 HP per tick | same per minute | 1:1 |
| Addiction craving | onset wall-clock (`last_dose_time`) | onset unchanged; prose at once when overdue, then every ~5 real minutes | prose cadence is elapsed-time (#501) |

Any future constant MUST be authored per minute with a comment saying so.

## 6 · Script hygiene rules (the codified doctrine)

1. **Persisted scripts never trust persisted config.** Scripts store
   their interval at creation, so a changed constant would otherwise
   leave pre-existing scripts ticking at the old value until they died.
   Every script's `at_start` re-asserts tunables (interval, etc.) from
   constants, so config changes propagate to live scripts on the next
   reload. This applies to `MedicalScript` and `DeathProgressionScript`.
2. **Every script declares its lifecycle in its docstring**: creation
   trigger, termination condition, what survives reload.
3. **`utils.delay` is for ephemera only** — a few seconds, loss-tolerable
   (throw flight: acceptable). `utils.delay` timers do not survive a
   reload. Anything that must survive a reload uses a Script, a
   TickerHandler subscription, or a persisted deadline timestamp swept at
   server start. The grenade fuse follows this rule (#505): both ticker
   starters persist `db.detonation_deadline`; `sweep_armed_grenades` in
   `commands/explosion_utils.py`, run at server start, re-arms a live
   fuse for the time it has left or detonates an overdue one; duds and
   defuses clear the deadline.
4. **`MedicalScript` and `DeathProgressionScript` re-arm at server
   start.** A Script's timer is
   `ndb._task`; Evennia's `_pause_task` records `db._paused_time` only if
   a task exists, and `_unpause_task` re-arms only if it is set, so any
   unclean shutdown leaves a per-object script permanently inert.
   `GLOBAL_SCRIPTS` are immune (re-armed from settings every boot).
   `MedicalScript.at_server_start` (Evennia's own hook, idempotent
   `start()`) re-arms the script, but only one whose `db_is_active` is
   true, so a medical script stopped and kept at death stays stopped.
   `DeathProgressionScript.at_server_start` has the same re-arm (#3075).
   This is a stopgap until the `medical_heartbeat` carrier (#3076, §12)
   exists.

## 7 · Migration: persistence and legacy data

* A persisted condition without `last_processed` gets *now* from
  `from_dict` — no retroactive billing; progression resumes on the next
  tick.
* `last_processed` is written by `MedicalCondition.to_dict` and restored
  with a safe default by `MedicalCondition.from_dict` and every subclass
  override.
* Conditions carry no fractional accumulator, so there is nothing else
  for `deserialize_condition` to round-trip. The one real accumulator,
  `organ.dressing_progress`, round-trips through the organ serializer
  (`Organ.to_dict` / `Organ.from_dict` in `world/medical/core.py`).
* `tick_interval` on conditions is retained in serialization for backward
  compatibility but ignored.
* `AddictionCondition` craving onset is elapsed-time-based
  (`last_dose_time`); its craving prose also runs on elapsed time (#501).
* Persisted scripts with stale intervals are healed by §6.1 on their next
  reload.

## 9 · Test contract

The cadence tests (`world/tests/test_condition_cadence.py`) must cover:

* **Equivalence**: N simulated 60s ticks produce the same outcomes as
  the per-tick model (within probabilistic tolerance) for bleeding, pain,
  dressing — the "current feel is preserved" guarantee.
* **Restoration**: infection improvement/worsening matches its
  *documented* pacing, not the drifted one; the improvement hazard's
  `1−(1−p)⁵` is pinned between 0.25 and 0.35
  (`TestInfectionRestoration.test_documented_pacing_constants`).
* **Cap**: a tick after simulated long downtime applies at most
  `ELAPSED_CAP_MINUTES` of effect.
* **Granularity-independence**: six 10s ticks ≈ one 60s tick for
  continuous quantities; probabilistic events match in distribution.
* **Persistence**: `last_processed` round-trips `to_dict` /
  `deserialize_condition`, and legacy dicts without it default safely
  (`TestPersistence`).

## 10 · Maintenance contract

* §1 decisions change only by explicit design discussion, not by
  implementation drift.
* New conditions MUST express effects per minute via
  `tick_effect(character, elapsed_minutes)` and MUST NOT read the clock
  directly.
* New timers MUST be classified under §6.3 (ephemeral vs persistent) at
  introduction.
* This spec supersedes the cadence-related portions of the old
  `CONDITION_INTERVALS` per-condition cadence design wherever they
  conflict.

## 11 · Blood-pool writes

Blood-pool write-on-threshold runs in the current carrier (#3077): pool
volume is kept in memory and written to the room's pool every
`BLOOD_POOL_FLUSH_TICKS` ticks, or at once when a player is in the room,
the pool's description would change, the bleeder moves, or the script
stops. It carries over to the heartbeat unchanged.

## 12 · Unbuilt

### Phase 3 carrier — global `medical_heartbeat` · 📋 UNBUILT (#3076)

Decided 2026-09-09, when the operational pain named in decision §1.4
arrived: eight per-object `MedicalScript` rows were found
`db_is_active=True` with no timer, stale 9–77 days, four holding
sedations that should have cleared in minutes. The root cause is
Evennia's script lifecycle (§6.4), not this code.

An in-process benchmark on 2026-09-09 superseded the 2026-06-11 figures
in §1.4 (those measured the condition math alone):

| | per body per tick |
|---|---|
| pain + suppression (long injury) | 6.5 ms, 2 attribute writes |
| bleeding | 25.1 ms, 6 writes — 72% is `_create_blood_pool` |
| wound + save + `scripts.add` | 7.5 ms |
| TickerHandler `add()` at N=1000 | 25 ms each; a 1000-burst = 13.9 s |

At 1,000 wounded bodies the current carrier costs 11–42% of the reactor,
and scripts created in one combat round are phase-aligned, so a
bloodbath is a spike every interval. TickerHandler is O(N) per add and
wrong for bursts.

**Decision: the Phase 3 carrier is a single `GLOBAL_SCRIPTS`
`medical_heartbeat` on the souls-engine pattern** — tag-indexed bodies,
`(beat + id) % SHARDS` phase offset, write-on-change with bounded
checkpoint, LOD on side effects only (the math is never LOD-scaled: a
body no player can see still bleeds out on schedule). Crash-safe by
construction. Not the ORM: a tag index answers the only question the
heartbeat asks.

### Phase 3 — per-script variable intervals · 📋 UNBUILT, parked until content exists (no issue)

Per-script variable intervals for urgent conditions (§1.5). A bolt-on
under this design.

### Phase 3 — combat-handler tactical tier · 📋 UNBUILT, parked until content exists (no issue)

Urgent in-combat conditions processed inside the combat round (§1.6),
calling the same `process()`. A bolt-on under this design.

### Test for the `dressing_progress` round-trip · 📋 UNBUILT (no issue)

No test in the repo asserts the `organ.dressing_progress` round-trip,
although the module docstring of `test_condition_cadence.py` advertises
it. The round-trip code is correct where it lives; the missing coverage
is a test gap.

## Related

* CAPACITY_CONSUMERS spec §7.1 — blood filtration and the infection
  course.
* In-game time system (#301) — plugs in at `clock.now()`.
