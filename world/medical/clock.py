"""The medical clock seam (CONDITION_CADENCE_SPEC §4.1, issue #501).

All condition-rate math reads elapsed time through this one
function.  Today it is wall-clock; when the in-game time system
(#301) arrives, it plugs in here and every condition inherits it
for free.  No condition or script may call ``time.time()`` for rate
math directly.
"""
from __future__ import annotations

import time


def now() -> float:
    """Current clock value (seconds).  The swap point for #301."""
    return time.time()


def elapsed_game_minutes(since: float, current: float | None = None) -> float:
    """Real minutes elapsed since ``since`` (never negative)."""
    if current is None:
        current = now()
    return max(0.0, (current - since) / 60.0)
