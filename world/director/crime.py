"""Crime reporting — instrumented acts raise world events, on a delay.

Crime slice 2 (``NPC_DISPATCH_AND_SIMULATION_SPEC`` §5.2): crimes are
**mechanical acts, not declarations** — combat raises ``assault``; theft
and the rest hook in as their verbs land. This module is the single
funnel between an act and the dispatcher, and it encodes three §5.1
truths:

* **The BOLO is snapshotted at crime time** — what witnesses saw *then*.
  Changing your presentation afterward defeats the match later; the
  report doesn't retroactively improve.
* **Someone has to see it** (slice 3, ``world/director/witness.py``): the
  crowd gate decides whether a witness exists at all — no witness, **no
  report ever** (an empty alley is free). When one spawns, the report
  window is a *person*: silence them (dead/unconscious) before
  ``WITNESS_REPORT_DELAY`` closes and the force never learns. (The radio
  transmission itself stays magic until ``RADIO_COMMS_SPEC`` builds it.)
* **One report per scene** (``REPORT_DEBOUNCE``, keyed room+type): a
  brawl is one incident, not a report per punch — and the BOLO belongs
  to the *first* aggressor.

Lawful force is excluded: acts by ``role == "security"`` raise nothing
(v1 — the force doesn't report itself).
"""

from __future__ import annotations

import time
from typing import Any

from evennia.utils import delay

from world.director.dispatch import WorldEvent
from world.director.security import build_bolo
from world.director.witness import WITNESS_REPORT_DELAY, spawn_witness, witness_report

#: One report per (room, crime type) within this window.
REPORT_DEBOUNCE = 120.0

#: Crime type → severity (the §5.2 taxonomy ladder; tunable).
CRIME_SEVERITY: dict[str, int] = {
    "shoplifting": 1,
    "vandalism": 1,
    "pickpocketing": 2,
    "mugging": 3,
    "robbery": 4,
    "assault": 3,
    "murder": 5,
    "sabotage": 3,
}

#: (location, crime_type) -> monotonic time of the last report.
_RECENT: dict = {}


def report_crime(crime_type: str, location: Any, perp: Any = None,
                 severity: int | None = None) -> bool:
    """An instrumented act calls this at the moment of commission.

    Debounces per scene, rolls the **crowd-gated witness**, snapshots the
    BOLO now, and hands the report window to the witness. Returns ``True``
    if a witness saw it (a report is *pending* — not yet guaranteed: the
    witness can still be silenced before the window closes).
    """
    if location is None:
        return False
    # Lawful force: the security force doesn't report its own actions (v1).
    if perp is not None and getattr(getattr(perp, "db", None), "role", None) == "security":
        return False
    # One incident per scene per window; the first aggressor owns the BOLO.
    key = (location, crime_type)
    now = time.monotonic()
    last = _RECENT.get(key)
    if last is not None and (now - last) < REPORT_DEBOUNCE:
        return False
    _RECENT[key] = now

    # §5.1: no witness, no report — the empty alley is free. (The scene
    # stays debounced either way: the same brawl doesn't re-roll a witness
    # every swing.)
    witness = spawn_witness(location)
    if witness is None:
        return False

    event = WorldEvent(
        type=crime_type,
        location=location,
        severity=severity if severity is not None
        else CRIME_SEVERITY.get(crime_type, 1),
        source=perp,
        payload={"bolo": build_bolo(perp)},   # crime-time presentation
    )
    delay(WITNESS_REPORT_DELAY, witness_report, witness, event)
    return True
