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

from world.radio import (
    active_transmit_radio, comms_organ_frequency, frequency_of, is_powered,
    is_radio, is_scanning,
)

#: Why a handheld is not ready, in the words the audit line uses.
POCKET, OFF, UNTUNED = "pocket", "off", "untuned"


def radio_to_ready(soul):
    """The handheld this soul should ready and why: ``(why, radio)`` with
    ``why`` one of :data:`POCKET` (carried, not in a hand or worn),
    :data:`OFF` (in a hand or worn, switched off) or :data:`UNTUNED`
    (sweeping, or parked on no band); or ``None`` when the soul can
    already transmit -- a working comms organ, or a worn/held/seated set
    that is on and tuned -- or carries no handheld at all.

    With several in a pocket, the one already on and tuned comes first:
    one command instead of two.
    """
    if comms_organ_frequency(soul):
        return None
    tx = active_transmit_radio(soul)
    if tx is not None:
        if not is_powered(tx):
            return (OFF, tx)
        if is_scanning(tx) or not frequency_of(tx):
            return (UNTUNED, tx)
        return None
    carried = [r for r in (getattr(soul, "contents", None) or [])
               if is_radio(r)]
    if not carried:
        return None
    carried.sort(key=lambda r: (not is_powered(r), not frequency_of(r)))
    return (POCKET, carried[0])


def wants_comms(soul) -> bool:
    """Does this soul want its radio ready right now? The band tree's
    question, answered by the one predicate above."""
    return radio_to_ready(soul) is not None
