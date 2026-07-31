"""Ambient broadcasters — scheduled on-air segments (the Rook's P2).

An NPC flagged ``db.ambient_broadcaster`` cuts an unprompted segment on
the director heartbeat cadence: every ``db.broadcast_interval`` seconds
(default 30 minutes), jittered so the station never feels metronomic.
The cue hands the model only what the world actually knows — the hour,
the weather — and whatever the band gave the NPC's observation buffer;
the segment airs through the NPC's real transmit device or not at all.
"""

import random
import time

from evennia.objects.models import ObjectDB

#: Seconds between segments when the NPC doesn't set its own cadence.
DEFAULT_INTERVAL = 1800


def _due(npc, now):
    """Fire only past the stored deadline; a first sighting schedules
    ahead instead of firing on boot (a reload isn't a cue)."""
    nxt = npc.db.next_broadcast_at
    if nxt is None:
        interval = float(npc.db.broadcast_interval or DEFAULT_INTERVAL)
        npc.db.next_broadcast_at = now + interval * random.uniform(0.2, 1.0)
        return False
    return now >= float(nxt)


def _cue():
    """The station clock: hour and weather from the live systems, with a
    real-clock fallback — the cue never invents more than the world knows."""
    period, weather = None, None
    try:
        from world.weather import time_system, weather_system
        period = time_system.get_current_time_period()
        weather = weather_system.get_current_weather()
    except Exception:  # noqa: BLE001 — a broken clock still runs a station
        pass
    if not period:
        # Fallback path — still the COLONY hour, not the container's UTC.
        # This is the seam the weather system reads from too.
        from world.gametime import colony_hour
        hour = colony_hour()
        period = ("the small hours" if hour < 5 else
                  "morning" if hour < 12 else
                  "afternoon" if hour < 18 else "night")
    line = f"It is {period} in the colony"
    if weather:
        line += f"; the weather is {weather}"
    return line + (". Recent band traffic, if any, appears above — "
                   "there may be none.")


def maintain_broadcasts(now=None):
    """One heartbeat sweep over every flagged broadcaster. Never raises;
    each NPC is isolated so one broken station can't stall the beats."""
    now = now if now is not None else time.time()
    for npc in ObjectDB.objects.filter(
            db_attributes__db_key="ambient_broadcaster"):
        try:
            if npc.db.ambient_broadcaster is not True:
                continue
            if not npc.db.llm_driven or not _due(npc, now):
                continue
            interval = float(npc.db.broadcast_interval or DEFAULT_INTERVAL)
            npc.db.next_broadcast_at = now + interval * random.uniform(
                0.75, 1.25)
            npc.llm_broadcast(_cue())
        except Exception:  # noqa: BLE001 — one station never stalls the sweep
            continue
