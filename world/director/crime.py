"""Crime reporting — instrumented acts raise world events, on a delay.

Crime slice 2 (``NPC_DISPATCH_AND_SIMULATION_SPEC`` §5.2): crimes are
**mechanical acts, not declarations** — combat raises ``assault``; theft
and the rest hook in as their verbs land. This module is the single
funnel between an act and the dispatcher, and it encodes three §5.1
truths:

* **The BOLO is snapshotted at crime time** — what witnesses saw *then*.
  Changing your presentation afterward defeats the match later; the
  report doesn't retroactively improve.
* **The report takes time** (``REPORT_DELAY``): the force learns nothing
  until the report "arrives". Today this delay is the acknowledged
  magic placeholder for the witness→radio chain (slice 3 replaces it
  with a real crowd-gated witness NPC + radio transmission); it already
  functions as a proto **interdiction window** — leave the scene before
  the response rolls.
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

from world.director.dispatch import WorldEvent, raise_event
from world.director.security import build_bolo

#: Seconds between the act and the force learning of it (the report
#: "arriving"). Placeholder for the witness→radio chain; also the proto
#: interdiction window.
REPORT_DELAY = 45.0
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

    Snapshots the BOLO now, debounces per scene, and schedules the
    delayed delivery to the dispatcher. Returns ``True`` if a report was
    actually filed (not debounced/excluded).
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

    event = WorldEvent(
        type=crime_type,
        location=location,
        severity=severity if severity is not None
        else CRIME_SEVERITY.get(crime_type, 1),
        source=perp,
        payload={"bolo": build_bolo(perp)},   # crime-time presentation
    )
    delay(REPORT_DELAY, _deliver, event)
    return True


def _deliver(event: WorldEvent) -> None:
    """The report 'arrives' — hand it to the dispatcher. (Slice 3 puts a
    real witness + radio transmission between the act and this call.)"""
    try:
        raise_event(event)
    except Exception:  # noqa: BLE001 — a broken report must not raise into delay
        pass
