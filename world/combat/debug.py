"""
Combat Audit Logging & Debug Broadcasting

Single sink for combat diagnostics (issue #461).  Every module that
needs combat debug/audit output imports from here rather than doing
its own channel lookups.

Two destinations, one entry point:

* **Audit file** (always on) — every message is appended to
  ``server/logs/combat_audit.log`` via Evennia's async file logger.
  This is the long-term record for investigating player bug reports,
  cheating accusations, and combat disputes.  File writes happen on
  the logger's thread pool, never blocking the reactor.
* **Splattercast channel** (gated) — live in-game broadcast for
  active debugging sessions.  Off by default; enable by setting
  ``SPLATTERCAST_LIVE = True`` in ``server/conf/settings.py``.
  The channel object is cached per process — no per-message DB
  lookup.

``get_splattercast()`` returns a router exposing ``.msg()`` so the
hundreds of existing ``splattercast.msg(...)`` call sites work
unchanged.  The router is always truthy, so ``if splattercast:``
guards also keep working.

Functions:
    get_splattercast — the audit router (always available)
    debug_broadcast — fire-and-forget ``PREFIX_STATUS: message``
    log_debug — structured ``PREFIX_ACTION: message (char)`` format
    log_combat_action — higher-level action logger used by commands
"""

from __future__ import annotations

import os
import sys
import time

from django.conf import settings
from django.core.exceptions import AppRegistryNotReady
from django.db import Error as DatabaseError

from evennia.comms.models import ChannelDB
from evennia.utils import logger

from .constants import SPLATTERCAST_CHANNEL

COMBAT_AUDIT_FILENAME = "combat_audit.log"

#: Test processes share the game dir with the live server; their
#: audit traffic must not touch production logs (it both pollutes
#: them and triggers cross-process rotation races — issue #489).
_UNDER_TEST = "test" in sys.argv


class _AuditFileWriter:
    """Serialized async writer for the combat audit log (#489).

    Replaces ``evennia.utils.logger.log_file`` for audit traffic.
    That helper has two diagnosed failure modes under burst load:
    it closes its cached handle every 500 accesses while deferred
    writes are still in flight (write-after-close), and its errback
    discards the real failure and formats the absent *current*
    exception — the infamous ``NoneType: None`` server-log flood,
    each line a silently dropped write.

    This writer:

    * funnels every write through ONE deferred chain — writes are
      strictly serialized, so no thread ever touches a handle
      another thread (or a close) is using;
    * rotates inside that same chain (timestamped generations, size
      from ``settings.CHANNEL_LOG_ROTATE_SIZE``), so rotation can't
      race a write;
    * reports failures with their REAL traceback to the server log
      (``AUDIT_WRITE_FAILED``) and reopens the handle for the next
      write — one bad write never wedges the stream.
    """

    def __init__(self, filename: str):
        self.filename = filename
        self._handle = None
        self._tail = None  # tail of the serialized write chain

    # -- thread-side (always serialized) ---------------------------

    def _path(self) -> str:
        return os.path.join(settings.LOG_DIR, self.filename)

    def _rotate_size(self) -> int:
        return max(1000, getattr(settings, "CHANNEL_LOG_ROTATE_SIZE", 1000000))

    def _write_sync(self, line: str) -> None:
        if self._handle is None or self._handle.closed:
            self._handle = open(self._path(), "a", encoding="utf-8")
        self._handle.write(line)
        self._handle.flush()
        if self._handle.tell() >= self._rotate_size():
            self._handle.close()
            self._handle = None
            os.replace(self._path(), f"{self._path()}.{int(time.time())}")

    # -- reactor-side ----------------------------------------------

    def _report_failure(self, failure):
        # The whole point of #489: never lose the real traceback.
        logger.log_err(
            f"AUDIT_WRITE_FAILED ({self.filename}): "
            f"{failure.getTraceback()}"
        )
        self._handle = None  # force reopen on the next write
        return None  # consume the failure; the chain continues

    def write(self, message: str) -> None:
        from twisted.internet.defer import succeed
        from twisted.internet.threads import deferToThread

        stamp = time.strftime("%y-%m-%d %H:%M:%S")
        line = f"\n{stamp} [-] {str(message).strip()}"
        if self._tail is None:
            self._tail = succeed(None)
        # Chain: each write starts only after the previous finished —
        # fired callbacks are consumed, so the chain doesn't grow.
        self._tail = self._tail.addCallback(
            lambda _result: deferToThread(self._write_sync, line)
        )
        self._tail.addErrback(self._report_failure)


_AUDIT_WRITER = _AuditFileWriter(COMBAT_AUDIT_FILENAME)

class _NullChannel:
    """No-op message sink.

    Kept for backward compatibility — tests and callers use it as a
    silent stand-in wherever a ``.msg()`` duck-type is expected.
    """

    def msg(self, *args, **kwargs):  # noqa: D401
        pass


# Per-process channel cache — reset naturally on server reload.
# Empty list = not yet resolved; [channel-or-None] once resolved.
_CHANNEL_CACHE: list = []


def _get_live_channel():
    """Return the Splattercast channel, resolved once per process.

    Returns ``None`` (without caching) when the DB / app registry
    isn't ready yet — a legitimate, expected condition during early
    startup — so the next call retries.  Any other failure is a real
    bug and is left to surface.
    """
    if not _CHANNEL_CACHE:
        try:
            _CHANNEL_CACHE.append(
                ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
            )
        except (DatabaseError, AppRegistryNotReady):
            return None
    return _CHANNEL_CACHE[0]


class _AuditRouter:
    """Message sink: audit file always, channel when live.

    Duck-types the one method call sites use (``msg``) so it can
    stand in for the channel object everywhere.
    """

    def msg(self, message, **kwargs):
        # Always-on audit write via the serialized writer (#489) —
        # failures are reported reactor-side with real tracebacks and
        # can never break combat for players.  Test processes skip
        # the file entirely (shared log dir with the live server).
        if not _UNDER_TEST:
            _AUDIT_WRITER.write(message)
        # Opt-in live mirror.  A developer who set SPLATTERCAST_LIVE is
        # in an active debugging session and *wants* failures to
        # surface, so this path is deliberately unguarded.
        if getattr(settings, "SPLATTERCAST_LIVE", False):
            channel = _get_live_channel()
            if channel:
                channel.msg(message, **kwargs)


_ROUTER = _AuditRouter()


def get_splattercast():
    """
    Return the combat audit router.

    Always returns a usable (truthy) object — messages go to the
    audit file unconditionally and to the Splattercast channel when
    ``settings.SPLATTERCAST_LIVE`` is enabled.
    """
    return _ROUTER


# ------------------------------------------------------------------
# Broadcasting helpers
# ------------------------------------------------------------------

def debug_broadcast(
    message: str,
    prefix: str = "DEBUG",
    status: str = "INFO",
) -> None:
    """
    Route a debug message through the audit sink.

    Args:
        message: Debug message to log/broadcast.
        prefix: Prefix for the debug message (e.g. ``"STICKY_GRENADE"``).
        status: Status level (``"INFO"``, ``"SUCCESS"``, ``"ERROR"``, …).
    """
    _ROUTER.msg(f"{prefix}_{status}: {message}")


def log_debug(
    prefix: str,
    action: str,
    message: str,
    character=None,
) -> None:
    """
    Route a standardised debug message through the audit sink.

    Format: ``PREFIX_ACTION: message (character_key)``

    Args:
        prefix: Debug prefix (e.g. ``DEBUG_PREFIX_ATTACK``).
        action: Action type (e.g. ``DEBUG_SUCCESS``).
        message: The debug message.
        character: Optional character for context.
    """
    char_context = f" ({character.key})" if character else ""
    _ROUTER.msg(f"{prefix}_{action}: {message}{char_context}")


def log_combat_action(
    character,
    action_type: str,
    target=None,
    success: bool = True,
    details: str = "",
) -> None:
    """
    Log a combat action with a standardised format.

    Args:
        character: The character performing the action.
        action_type: Type of action (``"attack"``, ``"flee"``, …).
        target: Optional target character.
        success: Whether the action succeeded.
        details: Additional details.
    """
    prefix = f"{action_type.upper()}_CMD"
    action = "SUCCESS" if success else "FAIL"

    target_info = f" on {target.key}" if target else ""
    details_info = f" - {details}" if details else ""

    message = f"{character.key}{target_info}{details_info}"
    log_debug(prefix, action, message)
