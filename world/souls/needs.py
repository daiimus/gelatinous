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

#: Profiles make the needs table DATA over one engine (spec §12):
#: need -> (rate_per_min, default_pressure, planner_shape). Shapes are
#: the small set of ways a need gets satisfied — the planner dispatches
#: on them (actions.plan_for).
PROFILES = {
    "human": {
        "hunger": (1.0 / 480.0, 0.25, "buy_consume"),   # 0 -> 1 in 8h
        "rest": (1.0 / 960.0, 0.25, "dwell_home"),      # 16h
        "social": (1.0 / 720.0, 0.25, "dwell_venue"),   # 12h
        "health": (0.0, 0.0, "clinic"),                 # derived (below)
        "safety": (0.0, 0.25, "flee"),                  # event-driven
    },
    "synth": {                       # human shape, durable dials
        "hunger": (1.0 / 960.0, 0.25, "buy_consume"),   # 16h
        "rest": (1.0 / 1440.0, 0.25, "dwell_home"),     # 24h
        "social": (1.0 / 720.0, 0.25, "dwell_venue"),
        "health": (0.0, 0.0, "clinic"),
        "safety": (0.0, 0.25, "flee"),
    },
    "robot": {                       # the battery is the appetite
        "charge": (1.0 / 720.0, 0.15, "dwell_venue"),   # ~12h to critical
        "maintenance": (1.0 / 10080.0, 0.05, "dwell_venue"),  # ~1 week
        "safety": (0.0, 0.0, "flee"),
    },
}

#: legacy aliases — pre-profile souls stored these; human is the shape
DECAY_PER_MIN = {name: spec[0] for name, spec in PROFILES["human"].items()}
DEFAULT_NEEDS = {name: spec[1] for name, spec in PROFILES["human"].items()}


def profile_name(soul):
    """Explicit `soul_profile` wins; else derived from species."""
    explicit = soul.db.soul_profile
    if explicit in PROFILES:
        return explicit
    species = str(soul.db.species or "").lower()
    if "robot" in species:
        return "robot"
    if "synth" in species:
        return "synth"
    return "human"


def profile_of(soul):
    return PROFILES[profile_name(soul)]


def shape_of(soul, need):
    spec = profile_of(soul).get(need)
    return spec[2] if spec else None


def _snapshot(soul, now):
    """The stored snapshot and its age in minutes. Tolerates legacy
    dicts from the pre-derivation engine (no ``_at``, extra ``duty``)."""
    stored = soul.db.soul_needs or {}
    stamped = stored.get("_at") or float(soul.db.soul_last_decay or now)
    minutes = max(0.0, (now - stamped) / 60.0)
    return stored, minutes


def health_pressure(soul):
    """The purest compute-on-read need: derived entirely from the
    medical state the body already carries — no snapshot, no writes,
    and treatment lowers it by actually healing (spec §14 layer 1)."""
    try:
        ms = soul.db.medical_state or {}
        conds = ms.get("conditions") or []
        n = len(conds)
        bleeding = any("bleed" in str((c.get("type") if isinstance(c, dict)
                                       else c) or "").lower()
                       for c in conds)
        return min(1.0, 0.12 * n + (0.35 if bleeding else 0.0))
    except Exception:  # noqa: BLE001 — unreadable body reads as well
        return 0.0


def pressures(soul, now=None):
    """Current derived pressure for every profile need. Pure read."""
    now = now if now is not None else time.time()
    stored, minutes = _snapshot(soul, now)
    out = {
        name: min(1.0, stored.get(name, default) + rate * minutes)
        for name, (rate, default, _shape) in profile_of(soul).items()
    }
    if "health" in out:
        out["health"] = health_pressure(soul)
    return out


def pressure(soul, need, now=None):
    if need == "health":
        return health_pressure(soul)
    now = now if now is not None else time.time()
    stored, minutes = _snapshot(soul, now)
    rate, default, _shape = profile_of(soul).get(need, (0.0, 0.0, None))
    return min(1.0, stored.get(need, default) + rate * minutes)


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
    """Fresh default meters for the soul's profile (ensoul-time)."""
    fresh = {name: default
             for name, (_rate, default, _shape) in profile_of(soul).items()}
    fresh["_at"] = time.time()
    soul.db.soul_needs = fresh
