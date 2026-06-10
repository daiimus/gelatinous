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

from django.conf import settings

from evennia.comms.models import ChannelDB
from evennia.utils import logger

from .constants import SPLATTERCAST_CHANNEL

COMBAT_AUDIT_FILENAME = "combat_audit.log"

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
    """Return the Splattercast channel, resolved once per process."""
    if not _CHANNEL_CACHE:
        try:
            _CHANNEL_CACHE.append(
                ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
            )
        except Exception:
            # DB not ready (early startup) — retry next call.
            return None
    return _CHANNEL_CACHE[0]


class _AuditRouter:
    """Message sink: audit file always, channel when live.

    Duck-types the one method call sites use (``msg``) so it can
    stand in for the channel object everywhere.
    """

    def msg(self, message, **kwargs):
        try:
            logger.log_file(str(message), filename=COMBAT_AUDIT_FILENAME)
        except Exception:
            # Auditing must never take combat down with it.
            pass
        if getattr(settings, "SPLATTERCAST_LIVE", False):
            channel = _get_live_channel()
            if channel:
                try:
                    channel.msg(message, **kwargs)
                except Exception:
                    pass


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
