"""The souls engine's sensory inbox — letting the world interrupt a soul
(SOULS_SALIENCE_SPEC, #2228).

Every goal a soul could form used to be derived from its own internal
state: needs pressure, the clock, whether it holds a post. `_desired_goal`
is a pure function of the soul, so **nothing in the world could put
anything in front of one**.

Thinking is also LOD-gated for cost: a soul with no player near it
thinks every sixth beat, about three minutes. That is correct for
deciding whether you are hungry. It is catastrophic for work whose
trigger arrives from somewhere else — a distress call reaches the
dispatcher by radio from someone who is, by definition, not standing
next to her, and being alone at her desk is exactly what makes her cold.

F.E.A.R., RimWorld and The Sims all draw the same line: the tick is a
cost-control mechanism for ROUTINE decisions, and salient events bypass
it to force immediate re-evaluation. Sensors write to working memory and
the planner re-plans; a job-override check fires on danger; a fire is a
pushed interaction that preempts the queue. Our LOD is such a mechanism
and simply had no bypass.

A stimulus is what the world hands a soul: a *kind*, a *band* on the
same scale as the goal tree (lower = more urgent), and an opaque
payload. Raising one forces the soul to think on the next reactor turn.

The inbox is `ndb` on purpose. A stimulus is something that is
happening; if the server reloads, the moment has passed, and a soul
waking to a queue of stale alarms is worse than one that missed them.
"""

from evennia.utils.utils import delay

#: Most stimuli a soul carries at once. A soul standing beside a busy
#: radio must not accumulate an unbounded list; the OLDEST drops, because
#: the newest call is the one still happening.
MAX_STIMULI = 8

#: Band of ordinary on-shift work — the same number `_desired_goal`
#: gives "duty", so a work stimulus doesn't preempt the job it belongs
#: to, it just makes the soul think NOW instead of in three minutes.
WORK_BAND = 2


def notice(soul, kind, band=WORK_BAND, payload=None):
    """Hand *soul* something the world just did, and wake it.

    Returns True if the stimulus was accepted. Never raises: a sensor
    that explodes must not break whatever was happening in the world.
    """
    try:
        if soul is None or not getattr(soul, "pk", None):
            return False
        inbox = list(soul.ndb.soul_stimuli or ())
        inbox.append({"kind": str(kind), "band": int(band),
                      "payload": payload or {}})
        soul.ndb.soul_stimuli = inbox[-MAX_STIMULI:]
        # One wake per burst. The emergency band is open and somebody
        # WILL hold the key down; a think per transmission would put the
        # reactor budget in a stranger's hands (hardening spec law #4).
        # A single wake drains the whole inbox, so a flood costs one
        # decision beat rather than one per message.
        if not soul.ndb.soul_wake_pending:
            soul.ndb.soul_wake_pending = True
            # Next reactor turn, NOT inline: a stimulus raised during
            # radio delivery would otherwise re-enter the delivery loop
            # it came from. `_beat_soul` is the backstop.
            delay(0, _think_now, soul)
        return True
    except Exception:  # noqa: BLE001 — a sense never breaks the world
        return False


def pending(soul):
    """Everything waiting, oldest first. Does not consume."""
    try:
        return list(soul.ndb.soul_stimuli or ())
    except Exception:  # noqa: BLE001
        return []


def top_band(soul):
    """The most urgent band waiting, or None."""
    items = pending(soul)
    return min((s["band"] for s in items), default=None)


def drain(soul, kind=None):
    """Take stimuli off the inbox and return them. With *kind*, takes
    only that kind and leaves the rest."""
    try:
        items = list(soul.ndb.soul_stimuli or ())
        if not items:
            return []
        if kind is None:
            soul.ndb.soul_stimuli = None
            return items
        taken = [s for s in items if s.get("kind") == kind]
        soul.ndb.soul_stimuli = [s for s in items
                                 if s.get("kind") != kind] or None
        return taken
    except Exception:  # noqa: BLE001
        return []


def _think_now(soul):
    """Force one decision beat outside the LOD cadence."""
    try:
        soul.ndb.soul_wake_pending = None      # the burst is over
        if not soul.pk or soul.location is None:
            return
        from world.gametime import colony_now
        from world.souls.engine import soul_hour, think
        try:
            t = colony_now()
            hour_f = t.hour + t.minute / 60.0
        except Exception:  # noqa: BLE001
            hour_f = 12.0
        think(soul, soul_hour(soul, hour_f))
    except Exception as err:  # noqa: BLE001
        try:
            from world.souls.jobs import fault
            fault(soul, f"stimulus think crashed: {err}")
        except Exception:  # noqa: BLE001
            pass


# --------------------------------------------------------------- sensors

def sense_radio(listener, speech, speaker, frequency):
    """A transmission landed in earshot of *listener*.

    Only the person SEATED at a base station on that band is working it
    — `seated_base_station` is the law, whoever holds the chair holds
    the voice. That is what makes an unmanned desk do nothing: not a
    check for emptiness, just nobody there to hear it.

    Loop guard: NPC- and device-sourced traffic never raises work.
    Witness reports and unit acks already carry their own dispatch;
    classifying them again would double-roll the same incident.
    """
    try:
        if listener is None or speaker is None or not speech:
            return False
        if not listener.tags.get("soul", category="npc_role"):
            return False
        db = getattr(speaker, "db", None)
        if (getattr(db, "is_npc", None) is True
                or getattr(db, "llm_driven", None) is True
                or getattr(db, "is_base_station", None) is True):
            return False
        from world.radio import frequency_of, same_band, seated_base_station
        board = seated_base_station(listener)
        if board is None or not same_band(frequency_of(board), frequency):
            return False
        return notice(listener, "radio_traffic", WORK_BAND,
                      {"speech": str(speech)[:400], "speaker": speaker,
                       "board": board, "frequency": frequency})
    except Exception:  # noqa: BLE001 — a sense never breaks the net
        return False


# ------------------------------------------------------- what a job forbids

def filter_for_duty(soul, words):
    """What *soul*'s post will not let it say, whatever it meant to say.

    A job constrains speech as well as action: a dispatcher cannot
    announce units that aren't rolling or promise to leave the chair,
    however the words arrived. The constraint belongs to the POST, so
    whoever holds it inherits it and nobody else carries the cost —
    this returns *words* untouched for everyone who isn't on a shift
    that forbids something.

    Kept out of the NPC brain deliberately. Hanging it there made every
    NPC's transmit path ask whether it was a dispatcher.
    """
    try:
        from world.director.dispatch import desk_discipline
        from world.radio import (
            EMERGENCY_BAND, frequency_of, same_band, seated_base_station,
        )
        board = seated_base_station(soul)
        if board is None or not same_band(frequency_of(board),
                                          EMERGENCY_BAND):
            return words
        verdict = soul.ndb.dispatch_verdict
        moved = bool(isinstance(verdict, dict) and verdict.get("dispatched"))
        return desk_discipline(words, units_moved=moved)
    except Exception:  # noqa: BLE001 — never swallow a line by accident
        return words


# ---------------------------------------------------------- work handlers

def work_stimuli(soul):
    """Do the work waiting in *soul*'s inbox, as part of its shift.

    Called from the ``work`` step: answering the radio IS a dispatcher's
    duty, not an interruption of it, so the stimulus doesn't need a goal
    of its own — it just made her think now instead of in three minutes.

    Deterministic throughout. The souls layer decides; the model, if
    there is one, only says (the two-brain law).
    """
    handled = 0
    for stim in drain(soul, "radio_traffic"):
        try:
            if _work_radio_traffic(soul, stim.get("payload") or {}):
                handled += 1
        except Exception as err:  # noqa: BLE001
            try:
                from world.souls.jobs import fault
                fault(soul, f"radio work crashed: {err}")
            except Exception:  # noqa: BLE001
                pass
    return handled


def _work_radio_traffic(soul, payload):
    """Judge a call and roll whatever it deserves.

    Whoever holds the chair does this — there is no flag on anybody and
    no typeclass involved, so a relief operator, a successor, or a
    resleeved keeper all dispatch the moment they sit down (#2228).
    """
    from world.director.dispatch import units_available
    from world.director.radio_report import consider_radio_report

    speaker = payload.get("speaker")
    speech = payload.get("speech")
    board = payload.get("board")

    def _took(verdict, dispatched):
        soul.ndb.dispatch_verdict = {
            "units": units_available(board),
            "verdict": verdict,
            "dispatched": len(dispatched or ()),
        }

    if not consider_radio_report(soul, speaker, speech, on_result=_took):
        _took(None, None)
    return True
