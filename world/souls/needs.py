"""Need meters — pressure that rises until satisfied, derived on read.

Each need is a 0.0–1.0 PRESSURE (0 = content, 1 = desperate). Pressure
is a pure function of elapsed real time, so it is never written on a
timer: the soul stores one snapshot dict (with its timestamp packed in
under ``_at``) and every read derives the current value as
``snapshot + rate * elapsed``. The snapshot is rewritten only when an
EVENT changes a need — a meal, sleep progress, a fright. A soul nobody
feeds or frightens costs zero writes, forever (hardening spec §4 P1,
law #1).

Two thresholds band the think tree: SOFT (worth acting on) and
CRITICAL (jumps the queue). Cash is deliberately NOT a meter — it is
the real `tokens` attribute, a resource the planner checks. Duty is
not stored at all: it is a pure function of schedule/hour/location,
computed by the engine (`duty_pressure`).
"""

import time

SOFT = 0.55
CRITICAL = 0.85

#: need -> pressure gained per real-world minute (dials, not physics).
#: At these rates: hunger cycles ~3x per real day, rest ~1x, social
#: drifts slowly — tuned for an observable loop, not realism.
DECAY_PER_MIN = {
    "hunger": 1.0 / 480.0,     # 0 -> 1 in 8 hours
    "rest": 1.0 / 960.0,       # 0 -> 1 in 16 hours
    "social": 1.0 / 720.0,     # 0 -> 1 in 12 hours
    "safety": 0.0,             # event-driven only
}

DEFAULT_NEEDS = {name: 0.25 for name in DECAY_PER_MIN}


def _snapshot(soul, now):
    """The stored snapshot and its age in minutes. Tolerates legacy
    dicts from the pre-derivation engine (no ``_at``, extra ``duty``)."""
    stored = soul.db.soul_needs or {}
    stamped = stored.get("_at") or float(soul.db.soul_last_decay or now)
    minutes = max(0.0, (now - stamped) / 60.0)
    return stored, minutes


def pressures(soul, now=None):
    """Current derived pressure for every need. Pure read — no writes."""
    now = now if now is not None else time.time()
    stored, minutes = _snapshot(soul, now)
    return {
        name: min(1.0, stored.get(name, DEFAULT_NEEDS[name]) + rate * minutes)
        for name, rate in DECAY_PER_MIN.items()
    }


def pressure(soul, need, now=None):
    now = now if now is not None else time.time()
    stored, minutes = _snapshot(soul, now)
    rate = DECAY_PER_MIN.get(need, 0.0)
    return min(1.0, stored.get(need, DEFAULT_NEEDS.get(need, 0.0))
               + rate * minutes)


def satisfy(soul, need, amount=1.0):
    """Drop a need's pressure (a meal, a night's sleep, a chat).

    Materializes ALL needs at their current derived values, applies the
    change, and writes the snapshot back with a fresh stamp — one
    attribute write per event, and the only write path in this module.
    """
    now = time.time()
    fresh = pressures(soul, now)
    fresh[need] = max(0.0, fresh.get(need, 0.0) - amount)
    fresh["_at"] = now
    soul.db.soul_needs = fresh


def seed(soul):
    """Fresh default meters (ensoul-time)."""
    fresh = dict(DEFAULT_NEEDS)
    fresh["_at"] = time.time()
    soul.db.soul_needs = fresh
