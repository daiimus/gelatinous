"""Job execution — plans become real commands, one step per think.

Every step runs through the same surfaces players use: `travel_to`
walks real exits, `buy` rings the real till, `eat`/`pose` are the real
verbs. A failed step FAULTS the job (visible in `@soul`) and the soul
re-arbitrates next think. No teleports, no db pokes.
"""

import time

from evennia.utils.search import search_object
from world.director.travel import is_travelling, stop_travel, travel_to
from world.souls import needs as needs_mod

FAULT_KEEP = 5


def fault(soul, msg):
    log = soul.db.soul_faults or []
    log.append((time.time(), msg))
    soul.db.soul_faults = log[-FAULT_KEEP:]
    soul.db.soul_job = None
    stop_travel(soul)       # an aborted job must not keep walking its route


def _obj(dbid):
    hits = search_object(f"#{dbid}")
    return hits[0] if hits else None


def step_job(soul):
    """Advance the current job by at most one step. Returns True while
    the job continues, False when finished/faulted."""
    job = soul.db.soul_job
    if not job:
        return False
    steps = job.get("steps") or []
    at = job.get("at", 0)
    if at >= len(steps):
        soul.db.soul_job = None
        return False
    step = steps[at]
    do = step.get("do")

    if do == "travel":
        room = _obj(step["room"])
        if room is None:
            fault(soul, "travel target vanished")
            return False
        if soul.location == room:
            job["at"] = at + 1
            soul.db.soul_job = job
            return True
        if not is_travelling(soul):
            if not travel_to(soul, room):
                fault(soul, f"no path to {room.key}")
                return False
        return True                        # walking; check again next think

    if do == "buy":
        counter = _obj(step["counter"])
        if counter is None or counter.location != soul.location:
            fault(soul, "counter gone from room")
            return False
        proto = step["proto"]
        before = set(o.id for o in soul.contents)
        soul.execute_cmd(f"buy {proto} from {counter.key}")
        if not any(o.id not in before for o in soul.contents):
            # bar/cart venues serve ON the counter — take it, real verb
            word = proto.split("_")[-1]
            soul.execute_cmd(f"get {word} from {counter.key}")
        if not any(o.id not in before for o in soul.contents):
            fault(soul, f"buy {proto} yielded nothing (broke? stock?)")
            return False
        job["at"] = at + 1
        soul.db.soul_job = job
        return True

    if do == "eat":
        from world.consumables import supports_delivery
        edible = next((o for o in soul.contents
                       if supports_delivery(o, "eat")), None)
        if edible is None:
            if step.get("bites"):
                needs_mod.satisfy(soul, "hunger", 0.9)   # finished the meal
                job["at"] = at + 1
                soul.db.soul_job = job
                return True
            fault(soul, "nothing edible in hand")
            return False
        bites = step.get("bites", 0) + 1
        if bites > 12:
            fault(soul, f"{edible.key} never finishes (uses_left stuck?)")
            return False
        soul.execute_cmd(f"eat {edible.key.split()[-1]}")
        step["bites"] = bites
        soul.db.soul_job = job
        return True

    if do == "sleep":
        home = soul.db.soul_home
        if home and soul.location != home:
            fault(soul, "not home at sleep step")
            return False
        if not soul.ndb.soul_sleeping:
            soul.ndb.soul_sleeping = True
            soul.execute_cmd("pose settles in for the night.")
        needs_mod.satisfy(soul, "rest", 0.12)   # per think while home
        if needs_mod.pressure(soul, "rest") <= 0.15:
            soul.ndb.soul_sleeping = False
            soul.execute_cmd("pose stirs, stretches, and rises.")
            soul.db.soul_job = None
            return False
        return True

    if do == "work":
        post = soul.db.soul_post
        if post and soul.location != post:
            fault(soul, "not at post at work step")
            return False
        # holding the post IS the work; wages accrue per heartbeat in the
        # engine (LOD-independent) and the schedule releases the job
        return True

    if do == "linger":
        left = step.get("beats", 3) - 1
        if left <= 0:
            needs_mod.satisfy(soul, "social", 0.7)
            job["at"] = at + 1
        else:
            step["beats"] = left
        soul.db.soul_job = job
        return True

    if do == "flee":
        exits = [e for e in (soul.location.exits if soul.location else [])
                 if e.destination and not e.db.is_edge and not e.db.is_gap]
        if not exits:
            fault(soul, "cornered — nowhere to flee")
            return False
        soul.execute_cmd(exits[0].key)
        needs_mod.satisfy(soul, "safety", 0.5)
        soul.db.soul_job = None
        return False

    fault(soul, f"unknown step '{do}'")
    return False
