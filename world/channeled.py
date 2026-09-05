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


#: Persistent breadcrumb for a channel in flight, so a reload can undo a
#: tell whose `ndb` record died with the process (#2774).
_STRAND_KEY = "channel_strand"


def sweep_stranded_tells() -> int:
    """Clear tells left behind by a reload mid-channel. Returns the count.

    `ndb.channel` dies with the process while `override_place` persists,
    so without this a character caught mid-channel by a reload is
    described by the act forever — `_finish` bails on the missing `ndb`,
    so `_clear` never runs, and `_clear` could not help anyway because
    the record it restores from is gone.

    Restores only where the stranded tell is STILL the thing showing, so
    a placement written after the reload (unconscious, dead) is left
    alone.
    """
    from evennia.objects.models import ObjectDB
    healed = 0
    for obj in ObjectDB.objects.filter(db_attributes__db_key=_STRAND_KEY):
        try:
            strand = obj.attributes.get(_STRAND_KEY)
            if not strand:
                continue
            if getattr(obj, "ndb", None) is not None and channel_of(obj):
                continue          # still running: not stranded
            if obj.override_place == strand.get("tell"):
                obj.override_place = strand.get("prior") or ""
                healed += 1
            obj.attributes.remove(_STRAND_KEY)
        except Exception:  # noqa: BLE001 — one bad row never stops the sweep
            continue
    return healed


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
    prior_place = getattr(actor, "override_place", None)
    actor.ndb.channel = {
        "key": key,
        "started": monotonic(),
        "duration": max(0.1, float(duration)),
        "on_complete": on_complete,
        "on_interrupt": on_interrupt,
        "token": token,
        "prior_place": prior_place,
        # The tell is KEPT so teardown can check it is still the thing
        # it wrote before restoring over it (see `_clear`).
        "tell": tell,
    }
    try:
        actor.override_place = tell   # the act is PUBLIC time — visible tell
        # A CRASH BREADCRUMB, in the persistent tier. `ndb.channel` dies
        # with the process; `override_place` is an AttributeProperty and
        # does not. So a reload mid-channel left the tell on the
        # character with `prior_place` — the only record of what to
        # restore — gone, and no path back short of staff intervention
        # (#2774). This is what `_sweep_stranded_tells` reads at
        # startup.
        actor.attributes.add(_STRAND_KEY, {"tell": tell,
                                           "prior": prior_place or ""})
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
        # Restore ONLY if the tell we wrote is still the thing showing.
        # This overwrote whatever `override_place` held at teardown with
        # the value captured at begin_channel, so anything set DURING
        # the channel was silently reverted — including the unconscious
        # and death placement lines. A character knocked out mid-channel
        # went back to describing the act they were interrupted from
        # (#2774).
        if actor.override_place == chan.get("tell"):
            actor.override_place = chan.get("prior_place")
        actor.attributes.remove(_STRAND_KEY)
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
