"""The signal bus — WSIS P0 (WORLD_STATE_INTELLIGENCE_SYSTEM_SPEC).

Game systems emit signals; the bus keeps a bounded, decaying record of
them per zone and per layer. Everything above it — zone threat scores,
anomaly detection, terminal readouts, intelligence briefs — reads this
and adds nothing to the emitting side.

Why this exists at all, in the owner's framing: **collapse is
legitimate content.** The colony is not propped up, and players and
NPCs are meant to decide what state it ends up in. That only works if
its state is LEGIBLE. The medical collapse of 2026-08-20 ran for hours
in plain sight — both doctors soulless, casualties bleeding out, and
nothing anywhere said so. This is the fix for that class of blindness,
and the first slice of the simulation layer the world spec wants.

Design constraints kept from the souls hardening work:

* **Emitting is nearly free.** One append to an in-process ring, and a
  checkpoint to the heartbeat script every so often. No writes per
  event, no scans, no queries.
* **Signals decay.** A signal's weight halves on a per-layer half-life,
  so the picture is always "lately", never "ever".
* **Nothing here reads back into behaviour.** WSIS observes. If a
  future system wants to ACT on a zone score it may, but the bus never
  pushes.
* **The ring is per-process.** Readers inside the server (commands,
  scripts) see it live; an external `evennia shell` sees only what has
  been checkpointed, which is every heavy signal and every 25th light
  one. That is a property of where the truth lives, not a bug to fix.
"""

import time

#: The seven layers the world spec defines. Each carries its own
#: half-life, because a killing stays relevant longer than a sale.
LAYERS = {
    "security":       {"label": "Security",       "halflife": 3 * 3600},
    "population":     {"label": "Population",     "halflife": 6 * 3600},
    "economy":        {"label": "Economy",        "halflife": 6 * 3600},
    "infrastructure": {"label": "Infrastructure", "halflife": 12 * 3600},
    "environment":    {"label": "Environment",    "halflife": 6 * 3600},
    "faction":        {"label": "Faction",        "halflife": 12 * 3600},
    "cyber":          {"label": "Cyber",          "halflife": 3 * 3600},
}

#: What each known signal means and how hard it lands (0.0-1.0).
#: Unlisted kinds still record, at a middling weight — an unknown
#: signal is better than a silent one.
SIGNALS = {
    # security
    "death":            ("security", 1.00),
    "killing":          ("security", 1.00),
    "assault":          ("security", 0.70),
    "robbery":          ("security", 0.55),
    "casualty":         ("security", 0.45),
    "casualty_untreated": ("security", 0.75),
    # population
    "arrival":          ("population", 0.30),
    "resleeve":         ("population", 0.50),
    "went_hungry":      ("population", 0.35),
    "homeless":         ("population", 0.40),
    "undressed":        ("population", 0.20),
    # economy
    "sale":             ("economy", 0.10),
    "wage_paid":        ("economy", 0.10),
    "till_empty":       ("economy", 0.45),
    "supply_dry":       ("economy", 0.60),
    # infrastructure
    "post_vacant":      ("infrastructure", 0.50),
    "post_unsouled":    ("infrastructure", 0.95),
    "machine_defect":   ("infrastructure", 0.40),
    "travel_stalled":   ("infrastructure", 0.25),
    "plan_faulted":     ("infrastructure", 0.20),
}

#: How many raw signals we keep. Beyond this the oldest fall off; the
#: decay makes them worthless long before that anyway.
RING = 400
#: Checkpoint the ring to disk every N emits (writes are the budget).
CHECKPOINT_EVERY = 25

#: In-process ring: [(stamp, kind, layer, zone, weight, note)].
#: ``None`` until `_load` rehydrates it — distinct from a loaded-and-EMPTY
#: ring, which is the normal state after a flush and on a cold start. A
#: truthiness memo could not tell those apart, so an empty ring re-read the
#: database on every call and the docstring's "once" was false (#2818).
_ring = None
_since_checkpoint = 0


def _heartbeat():
    from evennia import GLOBAL_SCRIPTS
    return getattr(GLOBAL_SCRIPTS, "souls_heartbeat", None)


def _load():
    """Rehydrate the ring after a reload, once."""
    global _ring
    if _ring is not None:
        return _ring
    hb = _heartbeat()
    stored = (hb.db.wsis_ring if hb else None) or []
    _ring = [tuple(entry) for entry in stored]
    return _ring


def _checkpoint(force=False):
    global _since_checkpoint
    _since_checkpoint += 1
    if not force and _since_checkpoint < CHECKPOINT_EVERY:
        return
    _since_checkpoint = 0
    hb = _heartbeat()
    if hb is not None:
        hb.db.wsis_ring = list(_ring[-RING:])


def zone_of(where):
    """The zone a thing is in. Rooms name their own street or building,
    which is the honest granularity for now — the spec's hierarchy
    (zone → sector → region) slots in above this without changing any
    emitting code."""
    if where is None:
        return "the colony"
    room = getattr(where, "location", None) or where
    key = getattr(room, "key", None) or "the colony"
    # "The Brackett Arms - Unit 3C" is the Brackett; "Kaspar Street"
    # is Kaspar Street.
    return key.split(" - ")[0].strip()


def emit(kind, where=None, weight=None, note="", layer=None):
    """Record that something happened. Cheap, and never raises."""
    try:
        known_layer, known_weight = SIGNALS.get(kind, (None, 0.35))
        entry = (time.time(), kind, layer or known_layer or "population",
                 zone_of(where),
                 float(known_weight if weight is None else weight),
                 str(note)[:120])
        ring = _load()
        ring.append(entry)
        if len(ring) > RING:
            del ring[:-RING]
        # heavy signals checkpoint immediately: a death should survive a
        # crash even if forty stalls before it do not
        _checkpoint(force=entry[4] >= 0.7)
    except Exception:  # noqa: BLE001 — observation must never break the world
        pass


def recent(seconds=None, zone=None, layer=None, now=None):
    """Signals still worth reading, newest first, with their decayed
    weight attached."""
    now = now if now is not None else time.time()
    out = []
    for stamp, kind, lay, zne, weight, note in _load():
        if layer and lay != layer:
            continue
        if zone and zne != zone:
            continue
        age = max(0.0, now - stamp)
        if seconds is not None and age > seconds:
            continue
        half = LAYERS.get(lay, {}).get("halflife", 6 * 3600)
        out.append((stamp, kind, lay, zne, weight * (0.5 ** (age / half)),
                    note, age))
    out.sort(key=lambda row: -row[0])
    return out


def pressure(zone=None, layer=None, now=None):
    """Decayed weight for a slice of the world — the raw number every
    score above this is built from. Unbounded on purpose; callers
    decide what 'high' means for them."""
    return sum(row[4] for row in recent(zone=zone, layer=layer, now=now))


def by_layer(zone=None, now=None):
    """{layer: decayed pressure} across every layer that has anything
    to say."""
    out = {}
    for row in recent(zone=zone, now=now):
        out[row[2]] = out.get(row[2], 0.0) + row[4]
    return out


def hot_zones(limit=5, now=None):
    """[(zone, pressure)] — where the colony is loudest right now."""
    tally = {}
    for row in recent(now=now):
        tally[row[3]] = tally.get(row[3], 0.0) + row[4]
    return sorted(tally.items(), key=lambda kv: -kv[1])[:limit]


def counts(kind, seconds=3600, now=None):
    """How many of a thing happened lately — the honest headline
    number, undecayed, for things like deaths per hour."""
    return sum(1 for row in recent(seconds=seconds, now=now)
               if row[1] == kind)


def flush():
    """Force a checkpoint (called by the heartbeat, and at shutdown)."""
    _checkpoint(force=True)
