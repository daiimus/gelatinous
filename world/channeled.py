"""Channeled actions — timed, interruptible acts (CHANNELED_ACTIONS_SPEC).

The stillness primitive: an act that occupies its actor for a real duration,
shows a visible tell, and resolves to a full result on completion or a
PARTIAL result on interruption. One channel per character, ndb-backed (a
reload silently kills the act: nothing lands, nothing is spent — costs
deduct at resolution, never up front).

The interrupt taxonomy (spec §2) lives at the call sites, not here:

* FREE   — perception/speech never call into this module.
* BLOCKED— hands/attention verbs call :func:`refuse_if_channeling` and back
           off with a message; the actor exits deliberately via ``stop``
           (:func:`stop_channel`).
* BREAKING — the world's contact seams (damage, grapple, combat enrollment,
           unconsciousness/death, wrest/disarm, forced movement) call
           :func:`interrupt_channel`.
"""

from __future__ import annotations

from time import monotonic
from typing import Any, Callable, Optional

from evennia.utils import delay


def channel_of(actor: Any) -> Optional[dict]:
    """The actor's live channel record, or None. Strictly typed — only a
    dict this module wrote counts (the MagicMock-truthiness lesson: a mock
    actor's auto-attribute must never read as a live channel)."""
    chan = getattr(getattr(actor, "ndb", None), "channel", None)
    return chan if isinstance(chan, dict) else None


def is_channeling(actor: Any) -> Optional[str]:
    """The channel's key ("spraying") when the actor is mid-act, else None."""
    chan = channel_of(actor)
    return chan.get("key") if chan else None


def refuse_if_channeling(actor: Any) -> bool:
    """The BLOCKED-class gate: True (and a refusal message) when the actor is
    mid-channel. Blocked verbs call this first and return — never a silent
    cancel; deliberate exit is the ``stop`` command."""
    key = is_channeling(actor)
    if not key:
        return False
    actor.msg(f"You're busy {key} — 'stop' first.")
    return True


def begin_channel(actor: Any, duration: float, tell: str,
                  on_complete: Callable, on_interrupt: Callable,
                  key: str = "working") -> bool:
    """Begin a channeled act. Refuses (False, with message) if one is
    already running. ``on_complete()`` fires after *duration* seconds;
    ``on_interrupt(fraction)`` fires instead if the act is stopped or
    broken, with the elapsed fraction (0.0–1.0)."""
    if refuse_if_channeling(actor):
        return False
    token = object()   # invalidates the pending completion on interrupt
    actor.ndb.channel = {
        "key": key,
        "started": monotonic(),
        "duration": max(0.1, float(duration)),
        "on_complete": on_complete,
        "on_interrupt": on_interrupt,
        "token": token,
        "prior_place": getattr(actor, "override_place", None),
    }
    try:
        actor.override_place = tell   # the act is PUBLIC time — visible tell
    except Exception:  # noqa: BLE001 — a tell failure never blocks the act
        pass
    delay(duration, _finish, actor, token)
    return True


def _clear(actor: Any) -> Optional[dict]:
    """Tear down the channel state (tell restored). Returns the record."""
    chan = channel_of(actor)
    if not chan:
        return None
    actor.ndb.channel = None
    try:
        actor.override_place = chan.get("prior_place")
    except Exception:  # noqa: BLE001
        pass
    return chan


def _finish(actor: Any, token: object) -> None:
    """Timer landing: complete the act — unless the channel was already
    interrupted (token mismatch) or died with the server (ndb gone)."""
    chan = channel_of(actor)
    if not chan or chan.get("token") is not token:
        return
    chan = _clear(actor)
    try:
        chan["on_complete"]()
    except Exception:  # noqa: BLE001 — a consumer bug never leaks upward
        pass


def stop_channel(actor: Any) -> bool:
    """Voluntary exit (the ``stop`` verb): abort with the current fraction.
    You keep what you finished. Returns True if a channel was stopped."""
    return _interrupt(actor, voluntary=True)


def interrupt_channel(actor: Any, reason: str | None = None) -> bool:
    """BREAKING-class exit: the world made contact (damage, grapple, combat
    enrollment, collapse, wrest, forced movement). Fail-open and cheap when
    the actor isn't channeling — seams may call this unconditionally."""
    return _interrupt(actor, voluntary=False, reason=reason)


def _interrupt(actor: Any, voluntary: bool, reason: str | None = None) -> bool:
    chan = channel_of(actor)
    if not chan:
        return False
    now = monotonic()
    elapsed = now - chan.get("started", now)
    fraction = max(0.0, min(1.0, elapsed / chan["duration"]))
    _clear(actor)
    try:
        chan["on_interrupt"](fraction)
    except Exception:  # noqa: BLE001
        pass
    return True
