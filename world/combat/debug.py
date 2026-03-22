"""
Combat Debug & Logging Utilities

Centralised helpers for broadcasting debug messages to the Splattercast
channel.  Every module in the combat package that needs debug output
should import from here rather than creating its own channel lookups.

Extracted from ``world/combat/utils.py`` during Phase 2 refactoring.

Functions:
    debug_broadcast — fire-and-forget message to Splattercast
    get_splattercast — safe channel retrieval (returns ``_NullChannel``
                       when the channel is unavailable)
    log_debug — structured ``PREFIX_ACTION: message (char)`` format
    log_combat_action — higher-level action logger used by commands
"""

from __future__ import annotations

from evennia.comms.models import ChannelDB

from .constants import SPLATTERCAST_CHANNEL


# ------------------------------------------------------------------
# Channel helpers
# ------------------------------------------------------------------

class _NullChannel:
    """No-op channel stand-in when Splattercast is unavailable."""

    def msg(self, *args, **kwargs):  # noqa: D401
        pass


def get_splattercast():
    """
    Safely retrieve the Splattercast debug channel.

    Returns:
        The channel object, or a ``_NullChannel`` stand-in if
        unavailable.
    """
    channel = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
    return channel if channel else _NullChannel()


# ------------------------------------------------------------------
# Broadcasting helpers
# ------------------------------------------------------------------

def debug_broadcast(
    message: str,
    prefix: str = "DEBUG",
    status: str = "INFO",
) -> None:
    """
    Broadcast a debug message to the Splattercast channel.

    Args:
        message: Debug message to broadcast.
        prefix: Prefix for the debug message (e.g. ``"STICKY_GRENADE"``).
        status: Status level (``"INFO"``, ``"SUCCESS"``, ``"ERROR"``, …).
    """
    try:
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        if splattercast:
            formatted_msg = f"{prefix}_{status}: {message}"
            splattercast.msg(formatted_msg)
    except Exception:
        # Fail silently if channel not available
        pass


def log_debug(
    prefix: str,
    action: str,
    message: str,
    character=None,
) -> None:
    """
    Send a standardised debug message to Splattercast.

    Format: ``PREFIX_ACTION: message (character_key)``

    Args:
        prefix: Debug prefix (e.g. ``DEBUG_PREFIX_ATTACK``).
        action: Action type (e.g. ``DEBUG_SUCCESS``).
        message: The debug message.
        character: Optional character for context.
    """
    try:
        splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
        if splattercast:
            char_context = f" ({character.key})" if character else ""
            full_message = f"{prefix}_{action}: {message}{char_context}"
            splattercast.msg(full_message)
    except Exception:
        # Fail silently if channel doesn't exist
        pass


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
