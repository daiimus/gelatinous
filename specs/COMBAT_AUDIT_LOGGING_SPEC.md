# Combat Audit Logging Spec

**Status:** shipped (issues #461 / #464; fail-safe excepts + this
spec under #466).  Describes current behavior; the code in
`world/combat/debug.py` is the source of truth.

## 0 · Purpose

Combat and medical systems emit a large volume of diagnostic
messages — contest rolls, condition transitions, death progression,
explosive resolution, grapple state. Historically these went to an
in-game **Splattercast** channel via a raw
`ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)` lookup at every
call site (~200 of them across 24 files).

That had two problems:

* **No durable record.** The channel is ephemeral — once the
  messages scroll past, they're gone. When a player reports a bug,
  claims another player cheated, or disputes a combat outcome, there
  was nothing to review.
* **Always-on cost.** Every diagnostic did a DB channel lookup and a
  full channel-distribution fan-out to subscribers, on the hot
  combat path, whether or not anyone was listening.

This spec defines the single-sink replacement.

## 1 · The sink

All diagnostics route through one module: `world/combat/debug.py`.
Call sites never touch `ChannelDB` directly. The entry points:

| Function | Use |
|---|---|
| `get_splattercast()` | Returns the audit router (an object with `.msg()`). The backward-compatible entry point — the ~200 migrated `splattercast = get_splattercast(); splattercast.msg(...)` call sites. |
| `debug_broadcast(message, prefix, status)` | Fire-and-forget `PREFIX_STATUS: message`. |
| `log_debug(prefix, action, message, character=None)` | Structured `PREFIX_ACTION: message (char_key)`. |
| `log_combat_action(character, action_type, target, success, details)` | Higher-level action logger used by commands. |

`get_splattercast()` returns a process-wide `_AuditRouter`
singleton. It is **always truthy**, so the legacy `if splattercast:`
guards at call sites keep working, and it duck-types the single
method call sites use (`.msg()`), so it stands in for the channel
object everywhere.

## 2 · Two destinations, one call

Every `.msg()` on the router does up to two things:

1. **Audit file — on, except under a test runner.** The message is appended to
   `server/logs/combat_audit.log` via a **module-owned stdlib
   `logging.handlers.RotatingFileHandler`** (changed #1106, 2026-07-10:
   Evennia's `logger.log_file` recycles its cached handle every 500th
   access on the reactor while queued thread writes still hold it —
   every recycle boundary silently dropped the queue, 7.9k lines
   rendered as `NoneType: None` until #1094 unmasked it). The stdlib
   handler locks per write and rotates safely; writes are buffered
   microsecond appends. This is the
   durable record for investigating bug reports, cheating
   accusations, and combat disputes.
   The write is skipped when `world/audit_guard.under_test()` is true
   (a test runner owns the process), so suite runs never append to the
   production log (#2328). Tests about the write itself patch
   `world.combat.debug._under_test` to return `False`.

2. **Splattercast channel — gated.** Only when
   `settings.SPLATTERCAST_LIVE` is `True`. This is the live in-game
   mirror for active debugging sessions. Default `False`. The
   channel object is resolved once and cached per process
   (`_CHANNEL_CACHE`) — no per-message DB lookup. If the channel
   does not exist when first looked up, that `None` is cached too,
   and the live mirror stays silent until the next reload.

```
call site → get_splattercast().msg("PREFIX_STATUS: ...")
                 │
                 ├─ _get_audit_logger().info(...)   ← always (skipped under a test runner)
                 │     → server/logs/combat_audit.log (RotatingFileHandler, backupCount=100)
                 │
                 └─ if settings.SPLATTERCAST_LIVE:   ← opt-in
                       cached_channel.msg(...)
                          → in-game Splattercast listeners
```

## 3 · Failure handling

The two destinations have deliberately different failure postures,
following the "no broad `except Exception`" convention by catching
only the expected, narrow failure of each:

* **Audit file write** is player-facing-critical: a filesystem
  hiccup must never crash combat for connected players. The `OSError`
  raised by an I/O failure is swallowed; anything else surfaces as a
  real bug.
* **Channel resolution** tolerates the early-startup race only —
  `DatabaseError` / `AppRegistryNotReady` while the DB or app
  registry isn't ready yet returns `None` (uncached, so the next
  call retries). Any other resolution failure surfaces.
* **Channel broadcast** is deliberately **unguarded**. If a developer
  has turned on `SPLATTERCAST_LIVE`, they're in an active debugging
  session and want failures to surface, not be silently eaten.

## 4 · Configuration

```python
# server/conf/settings.py
SPLATTERCAST_LIVE = False           # mirror diagnostics to the channel
CHANNEL_LOG_ROTATE_SIZE = 10_000_000  # audit-log rotation size (10MB)
```

Rotation produces numbered generations (`combat_audit.log.1` …
`combat_audit.log.100`). At most 100 survive and the oldest is
discarded, so at the 10 MB size the log tops out at about 1 GB
(`_get_audit_logger` passes `backupCount=100`). The size setting
`CHANNEL_LOG_ROTATE_SIZE` is Evennia's (1 MB default in
`settings_default.py`), and Evennia's channel logs read it too.

Flip to `True` (and reload) to watch combat live in-game. Leave
`False` in production — the audit file captures everything either
way.

*(2026-09-12: "either way" is about `SPLATTERCAST_LIVE`, which is
still true of it. The file write itself has one exception the
sentence predates — it is skipped under a test runner (#3221); see
§2.)*

## 5 · Conventions for call sites

* **Never** `ChannelDB.objects.get_channel(...)` for diagnostics.
  Import from `world/combat/debug.py`. These names are also
  re-exported from `world/combat/utils.py`, and many call sites
  import them from there.
* `world/medical/{core,conditions,utils}.py` import
  `get_splattercast` **function-locally**, not at module level: the
  `world.combat` package `__init__` reaches `world.medical.utils`
  through `handler → attack`, so a module-level import there would be
  circular.
* The audit file has one message per line, after a timestamp:
  `YY-MM-DD HH:MM:SS [-] PREFIX_STATUS: message` (`debug_broadcast`),
  or `PREFIX_ACTION: message (char_key)` after the timestamp
  (`log_debug`, `log_combat_action`). Keep messages greppable — lead
  with a stable uppercase prefix.

## 6 · Relationship to other specs

* `roadmaps/COMBAT_REFACTOR_SPEC.md` predates this and references the old
  per-call-site `get_channel` idiom and a "147 splattercast calls"
  count as part of its decomposition planning. Those references
  describe the *pre-#464* state; this spec supersedes them for the
  diagnostics-routing question.
* Splattercast is intended to eventually go away as a player-facing
  channel; the audit file is the durable mechanism that outlives it.
