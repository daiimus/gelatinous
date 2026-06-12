# Condition Cadence Spec — Elapsed-Time Rates

**Status:** approved design, implementation phased (issue #501).
Phase 1–2 are the near-term lift; Phase 3 is parked until content
needs it.  The discussion that settled every decision below happened
2026-06-11; the benchmark referenced in §2 ran the same day.

## 0 · The principle: where time lives

Today, time lives **in the tick**: a condition's effects are
per-tick numbers, so the tick interval *is* the game balance.
Changing the clock silently rebalances the game — this is not
hypothetical; see §2.

After this spec, time lives **in the condition**: effects are rates
per minute of real time, and a tick is just a sampling moment.  Each
condition remembers when it was last processed, computes how much
real time has passed, and applies that much effect.

The wage analogy: today conditions are paid per-paycheck, so
changing paycheck frequency changes their salary.  After: they're
paid hourly — pay them weekly, daily, whenever; they earn the same.

What this converts the "how often should X tick?" question into:
**a reaction-window and drama decision, never a balance decision.**
Burning at 30 damage/minute ticked at 60s is one unsurvivable hammer
blow; ticked at 10s it's six pulses with five chances to dive into
the water.  Same total.  The designer chooses the experience; the
math doesn't care.

## 1 · Settled design decisions

These were decided in discussion and are not open for silent
revision:

1. **Rates are per-minute of real time.**  Ticks sample elapsed
   time at any frequency.
2. **Everyone wounded ticks — no lazy evaluation for the living.**
   People and NPCs bleed out whether or not anyone is watching.
   Lazy/catch-up computation lies to the rest of the world in the
   gap (a guard computed-dead at observation was "alive" to every
   other system for the interim).  Lazy evaluation remains valid
   only for state that is a pure function of time, has no side
   effects on other entities, and has a single reader — corpse
   decay qualifies; living creatures never do.
3. **Downtime is capped.**  Reloads and crashes are rare and
   operator-caused; a restart must not bleed anyone out in
   absentia.  Elapsed time is clamped (§4.3) so conditions resume
   at their cadence without billing for server downtime.
4. **The carrier is unchanged**: one `MedicalScript` per wounded
   character.  The 2026-06-11 benchmark (10/100/500/1000 wounded
   characters) showed steady-state ticking is trivially cheap —
   1,000 simultaneous full medical ticks ≈ 50ms — and that the
   real cost axis is DB-write churn, which favors *not* changing
   carriers.  TickerHandler was evaluated (auto-pruning, no
   ScriptDB churn, but O(N²) persistence saves and synchronized
   firing) and shelved; revisit only on operational pain.
5. **Tick frequency may vary per script** (Phase 3): a character's
   medical script may run faster while an urgent condition exists
   and return to baseline after — safe *only because* of decision
   1.
6. **The tactical tier is parked** (Phase 3): in-combat urgent
   conditions will process inside the combat handler's existing
   6-second round (no new scripts, scoped to active fights).
   Elapsed-time rates make the combat↔medical handoff free: the
   next tick simply computes a larger elapsed.  Build when fire /
   severe-bleeding exist as content.
7. **Clock reads go through one indirection** (§4.1) so the future
   in-game time system (#301) can swap in without touching
   conditions.

## 2 · Current state and its evidence

* **Per-tick coupling, demonstrated:** when #465 corrected the
  medical tick from a testing-leftover 12s to the intended 60s,
  infection silently became 5× slower than designed — its
  probability comments still read "25 ticks at 12s intervals."
  Nobody changed infection; they changed the clock.
* **`CONDITION_INTERVALS` is dead config**: a per-condition cadence
  table (6s burning, 12s severe bleeding…) imported once and read
  never — a fossil of the abandoned one-ticker-per-condition
  design.  Deleted in Phase 1.
* **Persisted scripts fossilize config**: scripts store their
  interval at creation; #465's change left pre-existing scripts
  ticking at 12s until they happened to die.  Fixed by hygiene
  rule §6.1.
* **`utils.delay` timers do not survive reload**: a live grenade
  mid-fuse across a reload freezes into a hand-explosion trap.
  Out of scope here; tracked as its own issue (§6.3).

## 3 · Effect taxonomy

Three kinds of per-tick effect exist today; each converts
differently:

| Kind | Example | Conversion |
|---|---|---|
| **Continuous quantity** | bleeding blood loss | `rate_per_minute × elapsed_minutes`, applied fractionally |
| **Integer severity drift** | pain decaying 1/tick | fractional progress accumulator; severity steps when accumulated progress ≥ 1 |
| **Probabilistic event** | infection worsening chance | per-minute hazard `p`; over elapsed `t` minutes, fire with probability `1 − (1 − p)^t` |

Severity values stay integers (the whole condition system keys off
integer severities); only the *progress toward the next step* is
fractional, persisted alongside the condition.

## 4 · Mechanics

### 4.1 · The clock

One function, one place (`world/medical/clock.py` or equivalent):

```python
def elapsed_game_minutes(since: float, now: float | None = None) -> float:
    """Real minutes elapsed since `since`. The single seam where
    the future in-game time system (#301) plugs in."""
```

No condition or script reads `time.time()` for rate math directly.

### 4.2 · The base-class contract

`MedicalCondition` gains:

* `last_processed: float` — wall-clock timestamp, persisted in
  `to_dict()`; defaults to *now* on creation and on legacy
  deserialization (§7).
* `process(character, now=None)` — the only entry point carriers
  call.  Computes `elapsed = min(elapsed_game_minutes(last_processed),
  ELAPSED_CAP_MINUTES)`, calls `tick_effect(character, elapsed)`,
  updates `last_processed`.  Subclasses implement
  `tick_effect(character, elapsed_minutes)` and never touch the
  clock themselves.

The medical script's `at_repeat` switches from calling
`tick_effect(obj)` to `process(obj)`.  The future tactical tier
calls the *same* `process()` from the combat round — that is the
entire handoff.

### 4.3 · The downtime cap

`ELAPSED_CAP_MINUTES = 2 × (MEDICAL_TICK_INTERVAL / 60)` — i.e.
twice the expected sampling gap.  A normal tick sees ~1 minute; a
tick arriving after a 10-minute reload sees 2.  Players lose at
most one extra tick's worth of progression to a restart, never an
absence's worth.  (The cap constant lives with the other medical
constants; the cap is applied in `process()`, nowhere else.)

### 4.4 · Probabilistic events

Per-tick chances become per-minute hazards.  Conversion preserves
the *designed* behavior, not the accidentally-current one:

```python
fire = random.random() < 1 - (1 - p_per_minute) ** elapsed_minutes
```

## 5 · Magnitude conversion table (the re-audit)

The current tick is 60s, so most per-tick values convert 1:1 to
per-minute — **current game feel is preserved** except where the
value was authored for the old 12s tick and is therefore currently
running 5× off its design:

| Constant / behavior | Today (per 60s tick) | Per-minute | Note |
|---|---|---|---|
| `BLOOD_LOSS_PER_SEVERITY` | 0.5–2.5% per tick | same, per minute | 1:1 — authored for 60s.  #507 then made the rate derive from *current* severity (stale-rate fix) and replaced the treated-path truncation with the layered-brakes model: bandage slows to 30%, dressing stops, clotting only at severity ≤5 |
| Bleeding natural clotting (severity −1 chance) | per tick | same hazard per minute | 1:1 |
| Pain decay | 1 severity per tick | 1 per minute | 1:1 |
| Infection: treated improvement | 12% per tick (authored: "12% per 12s tick") | **restored**: `1−(1−0.12)⁵ ≈ 47%` per minute | the 5× drift fix |
| Infection: untreated worsening | granular per-tick chance (authored for "~20min progression" at 12s) | **restored** to the documented ~20-minute progression curve | drift fix |
| Dressing/splint knitting (`_hp_per_tick`) | rating//5 HP per tick | same per minute | 1:1 |
| Addiction craving | already wall-clock (`last_dose_time`) | unchanged | the existing precedent |

Any future constant MUST be authored per-minute with a comment
saying so.

## 6 · Script hygiene rules (the codified doctrine)

1. **Persisted scripts never trust persisted config.**  Every
   script's `at_start` re-asserts tunables (interval, etc.) from
   constants, so config changes propagate to live scripts on the
   next reload.  Applies to `MedicalScript` and
   `DeathProgressionScript` in Phase 2.
2. **Every script declares its lifecycle in its docstring**:
   creation trigger, termination condition, what survives reload.
3. **`utils.delay` is for ephemera only** — a few seconds,
   loss-tolerable (throw flight: acceptable).  Anything that must
   survive a reload uses a Script, a TickerHandler subscription, or
   a persisted deadline timestamp swept at server start.  The
   grenade fuse violates this today and is tracked separately:
   persist the detonation *deadline* on `db`, sweep at
   `at_server_start`, re-arm or detonate overdue.

## 7 · Migration

* Existing persisted conditions lack `last_processed`:
  `from_dict` defaults it to *now* — no retroactive billing at
  upgrade, progression resumes on the next tick.
* `AddictionCondition` is already elapsed-time-based and converges
  without change.
* Persisted scripts with stale intervals are healed by §6.1 on
  their first post-deploy reload.
* `CONDITION_INTERVALS` and its import are deleted; `tick_interval`
  on conditions (already documented "not used directly anymore")
  is retained in serialization for backward compatibility but
  ignored.

## 8 · Phases

* **Phase 1 — the refactor** (one PR): clock indirection, base-class
  `process()`/`last_processed`, condition conversions per §3/§5,
  per-minute constants with the two infection restorations, the
  downtime cap, `CONDITION_INTERVALS` deletion, and the test
  contract (§9).
* **Phase 2 — hygiene** (one PR): `at_start` config re-assertion,
  lifecycle docstrings on all scripts, grenade-deadline issue
  filed.
* **Phase 3 — parked until content exists**: per-script variable
  intervals for urgent conditions; the combat-handler tactical
  tier.  Both become bolt-ons under this design.

## 9 · Test contract

Phase 1 ships with:

* **Equivalence**: N simulated 60s ticks under the new system
  produce the same outcomes as the old per-tick system (within
  probabilistic tolerance) for bleeding, pain, dressing — the
  "current feel is preserved" guarantee.
* **Restoration**: infection improvement/worsening matches its
  *documented* pacing, not the drifted one.
* **Cap**: a tick after simulated long downtime applies at most
  `ELAPSED_CAP_MINUTES` of effect.
* **Granularity-independence**: six 10s ticks ≈ one 60s tick for
  continuous quantities; probabilistic events match in
  distribution.
* **Persistence**: `last_processed` and fractional accumulators
  round-trip `to_dict`/`deserialize_condition`; legacy dicts
  without them default safely.

## 10 · Maintenance contract

* §1 decisions change only by explicit design discussion, not by
  implementation drift.
* New conditions MUST express effects per-minute via
  `tick_effect(character, elapsed_minutes)` and MUST NOT read the
  clock directly.
* New timers MUST be classified under §6.3 (ephemeral vs
  persistent) at introduction.
* This spec supersedes the cadence-related portions of the old
  `CONDITION_INTERVALS` design wherever they conflict.
