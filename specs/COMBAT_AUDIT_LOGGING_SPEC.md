# Combat Audit Logging Spec

Combat and medical systems emit a large volume of diagnostic messages:
contest rolls, condition transitions, death progression, explosive
resolution, grapple state. Every one of them goes through a single sink,
`world/combat/debug.py` (#461, #464; failure handling #466). The sink
writes each message to a durable audit file and, only when switched on,
mirrors it to the in-game **Splattercast** channel. The code in
`world/combat/debug.py` is the source of truth.

Why one sink: the channel is ephemeral. Once messages scroll past they
are gone, and when a player reports a bug, claims another player cheated,
or disputes a combat outcome, there must be a record to review. And a
channel lookup plus a full channel fan-out to subscribers on every
diagnostic is a cost on the hot combat path whether or not anyone is
listening.

## 1 · The sink

Call sites never touch `ChannelDB` directly. The entry points:

| Function | Use |
|---|---|
| `get_splattercast()` | Returns the audit router (an object with `.msg()`). Used by the call sites written as `splattercast = get_splattercast(); splattercast.msg(...)` (about 200 of them). |
| `debug_broadcast(message, prefix, status)` | Fire-and-forget `PREFIX_STATUS: message`. |
| `log_debug(prefix, action, message, character=None)` | Structured `PREFIX_ACTION: message (char_key)`. |
| `log_combat_action(character, action_type, target, success, details)` | Higher-level action logger used by commands. |

`get_splattercast()` returns a process-wide `_AuditRouter` singleton. It
is **always truthy**, so `if splattercast:` guards at call sites keep
working, and it duck-types the one method call sites use (`.msg()`), so it
stands in for the channel object everywhere.

## 2 · Two destinations, one call

Every `.msg()` on the router does up to two things.

1. **Audit file: on, except under a test runner.** The message is
   appended to `server/logs/combat_audit.log` through a module-owned
   stdlib `logging.handlers.RotatingFileHandler` (built by
   `_get_audit_logger`, #1106). The stdlib handler locks per write and
   rotates safely; writes are buffered microsecond appends. Evennia's
   `logger.log_file` is not used because it recycles its cached handle
   every 500th access on the reactor while queued thread writes still
   hold it, which drops the queued writes. This file is the durable
   record for investigating bug reports, cheating accusations and combat
   disputes.
   The write is skipped when `world/audit_guard.under_test()` is true (a
   test runner owns the process), so suite runs never append to the
   production log (#2328). Tests about the write itself patch
   `world.combat.debug._under_test` to return `False`.

2. **Splattercast channel: gated.** Only when `settings.SPLATTERCAST_LIVE`
   is `True`. This is the live in-game mirror for active debugging
   sessions. Default `False`. The channel object is resolved once and
   cached per process (`_CHANNEL_CACHE`), so there is no per-message DB
   lookup. If the channel does not exist when first looked up, that
   `None` is cached too, and the live mirror
   stays silent until the next reload.

## 3 · Failure handling

The two destinations have deliberately different failure postures. Each
follows the "no broad `except Exception`" convention by catching only its
own expected, narrow failure.

* **Audit file write** is player-facing-critical: a filesystem hiccup must
  never crash combat for connected players. The `OSError` raised by an
  I/O failure is swallowed; anything else surfaces as a real bug.
* **Channel resolution** tolerates the early-startup race only:
  `DatabaseError` / `AppRegistryNotReady` while the DB or app registry is
  not ready yet returns `None` (uncached, so the next call retries). Any
  other resolution failure surfaces.
* **Channel broadcast** is deliberately **unguarded**. A developer who has
  turned on `SPLATTERCAST_LIVE` is in an active debugging session and
  wants failures to surface, not be silently eaten.

## 4 · Configuration

Both settings live in `server/conf/settings.py`:

| Setting | Value | Effect |
|---|---|---|
| `SPLATTERCAST_LIVE` | `False` | Mirror diagnostics to the channel. |
| `CHANNEL_LOG_ROTATE_SIZE` | `10_000_000` (10 MB) | Audit-log rotation size. |

Rotation produces numbered generations (`combat_audit.log.1` …
`combat_audit.log.100`). At most 100 survive and the oldest is discarded,
so at the 10 MB size the log tops out at about 1 GB (`_get_audit_logger`
passes `backupCount=100`). `CHANNEL_LOG_ROTATE_SIZE` is Evennia's setting
(1 MB default in `settings_default.py`), and Evennia's channel logs read
it too.

Flip `SPLATTERCAST_LIVE` to `True` (and reload) to watch combat live
in-game. Leave it `False` in production: whichever way it is set, the
audit file captures everything (outside a test runner, §2).

## 5 · Conventions for call sites

* **Never** `ChannelDB.objects.get_channel(...)` for diagnostics. Import
  from `world/combat/debug.py`. These names are also re-exported from
  `world/combat/utils.py`, and many call sites import them from there.
* `world/medical/{core,conditions,utils}.py` import `get_splattercast`
  **function-locally**, not at module level: the `world.combat` package
  `__init__` reaches `world.medical.utils` through `handler → attack`, so
  a module-level import there would be circular.
* The audit file has one message per line, after a timestamp:
  `YY-MM-DD HH:MM:SS [-] PREFIX_STATUS: message` (`debug_broadcast`), or
  `PREFIX_ACTION: message (char_key)` after the timestamp (`log_debug`,
  `log_combat_action`). Keep messages greppable: lead with a stable
  uppercase prefix.

## 6 · Relationship to other specs

* `roadmaps/COMBAT_REFACTOR_SPEC.md` predates this spec and references the
  old per-call-site `get_channel` idiom and a "147 splattercast calls" count as part of its
  decomposition planning. Those references describe the state before
  #464; this spec supersedes them for the diagnostics-routing question.
* Splattercast is intended to eventually go away as a player-facing
  channel; the audit file is the durable mechanism that outlives it.

## 7 · Not decided

* Should the `world/combat/utils.py` re-export of the combat debug names
  stay as a sanctioned import path, or should callers move to
  `world/combat/debug.py` and the re-export be deleted?
