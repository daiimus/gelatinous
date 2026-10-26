"""The comms goal: a soul keeps its radio ready (#3777).

Two souls carried a working handheld in a pocket. A pocket radio
receives but cannot transmit, so every call they took was refused the
way a player's would be (#2585), and nothing in the think tree knew a
radio could be *not ready*. Owner, 2026-10-26: "If a radio is off -
they should turn it on. This should organically feed into the GOAP
system, more or less."

This module is the ONE door. `radio_to_ready` is pure -- it asks, it
never commits -- and it is the single place a reason to stay silent
would plug in later (a radio-silence order, hiding, a dead battery):
a clause here, a test beside it, nothing else in the tree or the
planner changes. Future-proof by shape, not by flags (owner, same day).
"""

import time
from collections.abc import Mapping

from world.radio import (
    active_transmit_radio, comms_organ_frequency, frequency_of, is_powered,
    is_radio,
)


def _now() -> float:
    return time.time()

#: Why a handheld is not ready, in the words the audit line uses.
POCKET, OFF, UNTUNED = "pocket", "off", "untuned"


def _free_hand(soul) -> bool:
    hands = getattr(soul, "hands", None) or {}
    return any(v is None for v in hands.values())


def _only_one_answers(soul, radio, pool=None) -> bool:
    """Would a command naming ``radio.key`` reach exactly this set? `wield`
    searches the inventory and takes the first match; `toggle` searches
    room and inventory and refuses a multimatch; and Evennia's ordinal
    form cannot narrow a key like "AWE Magpie-01 radio" (the -01 reads as
    the ordinal, #3779). A twin in the pool makes the set unreachable by
    any command the body could type, so the predicate does not want it."""
    try:
        if pool is not None:
            found = soul.search(radio.key, candidates=list(pool), quiet=True)
        else:
            found = soul.search(radio.key, quiet=True)
    except Exception:  # noqa: BLE001 — a mock or a bodiless soul
        return True
    found = list(found) if isinstance(found, (list, tuple)) else [found]
    return len([o for o in found if o is not None]) == 1


def radio_to_ready(soul):
    """The handheld this soul should ready and why: ``(why, radio)`` with
    ``why`` :data:`POCKET` (carried, not in a hand or worn) or :data:`OFF`
    (in a hand or worn, switched off); or ``None`` when the soul can
    already transmit -- a working comms organ, or a worn/held/seated set
    that is on and tuned -- or carries no handheld at all.

    Also ``None`` for what the body cannot do right now, so the tree never
    plans a job that can only fault: a pocket set with no free hand; a set
    that is on but on no band (:data:`UNTUNED` -- nothing tells a soul its
    home band yet, the next slice); a set a twin of the same key makes
    unreachable by name. What it cannot do, it does not want.

    With several in a pocket, the one already on and tuned comes first:
    one command instead of two.
    """
    if comms_organ_frequency(soul):
        return None
    tx = active_transmit_radio(soul)
    if tx is not None:
        if not is_powered(tx):
            return (OFF, tx) if _only_one_answers(soul, tx) else None
        return None            # on and tuned, or UNTUNED: nothing to do yet
    contents = list(getattr(soul, "contents", None) or [])
    carried = [r for r in contents if is_radio(r)]
    if not carried or not _free_hand(soul):
        return None
    carried.sort(key=lambda r: (not is_powered(r), not frequency_of(r)))
    chosen = carried[0]
    return (POCKET, chosen) if _only_one_answers(soul, chosen, contents) else None


def wants_comms(soul) -> bool:
    """Does this soul want its radio ready right now? The band tree's
    question, answered by the one predicate above."""
    return radio_to_ready(soul) is not None


#: One real command per beat, three beats per state before giving up.
BEATS_PER_STATE = 3
#: A budget older than this belongs to an earlier episode (an idle job
#: dropped mid-way, a set readied by other means): it starts over. Three
#: beats take ~90 s; nothing legitimate spans five minutes.
BUDGET_WINDOW = 300.0
READY, ACTING, GAVE_UP = "ready", "acting", "gave_up"


def ready_beat(soul):
    """One beat of readying the handheld, as a player would: ``wield`` a
    pocket set, ``toggle ... on`` a dark one. Returns :data:`READY` when
    there is nothing (left) to do, :data:`ACTING` when a command went out
    this beat, :data:`GAVE_UP` when the same state has had
    :data:`BEATS_PER_STATE` commands and still stands (a `wield` the game
    keeps refusing is not retried forever). Shared by the reflex in
    ``engine.think`` (a refused call: one beat, then whatever the body
    was doing) and the idle ``comms`` job, so there is one way to do it."""
    want = radio_to_ready(soul)
    if want is None:
        soul.db.soul_comms_tries = None
        return READY
    why, radio = want
    rid = getattr(radio, "id", None)
    # An Evennia db dict comes back as a _SaverDict: a Mapping, NOT a
    # dict subclass. `isinstance(rec, dict)` would never match a saved
    # record, the count would never pass 1, and a refused wield would
    # repeat every beat with no cap.
    rec = soul.db.soul_comms_tries or {}
    same = (isinstance(rec, Mapping) and rec.get("state") == why
            and rec.get("radio") == rid
            and _now() - float(rec.get("at", 0.0)) < BUDGET_WINDOW)
    n = int(rec.get("n", 0)) if same else 0
    if n >= BEATS_PER_STATE:
        soul.db.soul_comms_tries = None
        return GAVE_UP
    soul.db.soul_comms_tries = {"state": why, "radio": rid, "n": n + 1,
                                "at": _now()}
    if why == POCKET:
        soul.execute_cmd(f"wield {radio.key}")
    else:
        soul.execute_cmd(f"toggle {radio.key} on")
    return ACTING
