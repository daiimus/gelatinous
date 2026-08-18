"""Need meters — pressure that rises until satisfied.

Each need is a 0.0–1.0 PRESSURE (0 = content, 1 = desperate), rising at
a per-real-minute rate and dropped by satisfying jobs. Two thresholds
band the think tree: SOFT (worth acting on) and CRITICAL (jumps the
queue). Cash is deliberately NOT a meter — it is the real `tokens`
attribute, a resource the planner checks.
"""

SOFT = 0.55
CRITICAL = 0.85

#: need -> pressure gained per real-world minute (dials, not physics).
#: At these rates: hunger cycles ~3x per real day, rest ~1x, social
#: drifts slowly — tuned for an observable phase-1 loop, not realism.
DECAY_PER_MIN = {
    "hunger": 1.0 / 480.0,     # 0 -> 1 in 8 hours
    "rest": 1.0 / 960.0,       # 0 -> 1 in 16 hours
    "social": 1.0 / 720.0,     # 0 -> 1 in 12 hours
    "duty": 0.0,               # schedule-driven, not time-decayed (see tick)
    "safety": 0.0,             # event-driven only
}

DEFAULT_NEEDS = {name: 0.25 for name in DECAY_PER_MIN}


def tick_decay(soul, minutes):
    """Advance pressures by elapsed real minutes. Duty pressure is set
    by the schedule check in the engine; safety only by events."""
    needs = soul.db.soul_needs or dict(DEFAULT_NEEDS)
    for name, rate in DECAY_PER_MIN.items():
        if rate:
            needs[name] = min(1.0, needs.get(name, 0.0) + rate * minutes)
    soul.db.soul_needs = needs
    return needs


def satisfy(soul, need, amount=1.0):
    """Drop a need's pressure (a meal, a night's sleep, a chat)."""
    needs = soul.db.soul_needs or dict(DEFAULT_NEEDS)
    needs[need] = max(0.0, needs.get(need, 0.0) - amount)
    soul.db.soul_needs = needs


def pressure(soul, need):
    return (soul.db.soul_needs or {}).get(need, 0.0)
