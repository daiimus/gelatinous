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

1. **Audit file — always on.** The message is appended to
   `server/logs/combat_audit.log` by the sink's own serialized
   async writer (`_AuditFileWriter`, #489) — NOT
   `evennia.utils.logger.log_file`, whose handle-recycling races
   in-flight thread writes under burst load and whose errback
   destroys the real error (the `NoneType: None` floods; every
   line a silently dropped write). The writer chains every write
   on one deferred (strict serialization, reactor never blocked),
   rotates timestamped generations inside that chain
   (`CHANNEL_LOG_ROTATE_SIZE`), reports failures with their real
   traceback as `AUDIT_WRITE_FAILED` in the server log, and
   reopens after any failure. **Test processes skip the file
   entirely** — they share `server/logs/` with the live server,
   and their writes both polluted the audit record and triggered
   cross-process rotation races.

2. **Splattercast channel — gated.** Only when
   `settings.SPLATTERCAST_LIVE` is `True`. This is the live in-game
   mirror for active debugging sessions. Default `False`. The
   channel object is resolved once and cached per process
   (`_CHANNEL_CACHE`) — no per-message DB lookup.

```
call site → get_splattercast().msg("PREFIX_STATUS: ...")
                 │
                 ├─ logger.log_file(...)            ← always
                 │     → server/logs/combat_audit.log
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

Rotation produces numbered generations (`combat_audit.log.1`, …)
with no count cap — the size knob controls granularity per file,
not total disk use.  The knob is Evennia's and is shared by
channel logs.

Flip to `True` (and reload) to watch combat live in-game. Leave
`False` in production — the audit file captures everything either
way.

## 5 · Conventions for call sites

* **Never** `ChannelDB.objects.get_channel(...)` for diagnostics.
  Import from `world/combat/debug.py`.
* `world/medical/{core,conditions,utils}.py` import
  `get_splattercast` **function-locally**, not at module level: the
  `world.combat` package `__init__` reaches `world.medical.utils`
  through `handler → attack`, so a module-level import there would be
  circular.
* The audit file is line-oriented `PREFIX_STATUS: message` text.
  Keep messages greppable — lead with a stable uppercase prefix.

## 6 · Relationship to other specs

* `COMBAT_REFACTOR_SPEC.md` predates this and references the old
  per-call-site `get_channel` idiom and a "147 splattercast calls"
  count as part of its decomposition planning. Those references
  describe the *pre-#464* state; this spec supersedes them for the
  diagnostics-routing question.
* Splattercast is intended to eventually go away as a player-facing
  channel; the audit file is the durable mechanism that outlives it.
