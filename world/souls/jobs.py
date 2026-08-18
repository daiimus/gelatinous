"""Job execution — plans become real commands, one step per think.

Every step runs through the same surfaces players use: `travel_to`
walks real exits, `buy` rings the real till, `eat`/`pose` are the real
verbs. A failed step FAULTS the job (visible in `@soul`) and the soul
re-arbitrates next think. No teleports, no db pokes.
"""

import time

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
    """Indexed PK fetch — the full search stack costs 200x as much
    (262us vs 1.3us measured, hardening spec §1.5)."""
    from evennia.objects.models import ObjectDB
    obj = ObjectDB.objects.get_id(dbid)
    return obj if obj and obj.pk else None


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
            def _stalled(npc, _room=room):
                fault(npc, f"travel stalled toward {_room.key} "
                           "(an exit that wouldn't give)")
            if not travel_to(soul, room, on_fail=_stalled):
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
        from world.souls import thoughts
        edible = next((o for o in soul.contents
                       if supports_delivery(o, "eat")), None)
        if edible is None:
            if step.get("bites"):
                needs_mod.satisfy(soul, "hunger", 0.9)   # finished the meal
                where = soul.location.key if soul.location else "the street"
                thoughts.add_thought(
                    soul, "ate_well", 0.15,
                    f"{step.get('last_food', 'a hot meal')} at {where}")
                job["at"] = at + 1
                soul.db.soul_job = job
                return True
            fault(soul, "nothing edible in hand")
            return False
        step["last_food"] = edible.key
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
            from world.souls import thoughts
            soul.ndb.soul_sleeping = False
            soul.execute_cmd("pose stirs, stretches, and rises.")
            thoughts.add_thought(soul, "slept_home", 0.20,
                                 "a night behind my own door")
            soul.db.soul_job = None
            return False
        return True

    if do == "dwell":
        # generic occupy-and-recover (charge, maintenance — spec §12)
        need = step.get("need", "charge")
        if not soul.ndb.soul_dwelling:
            soul.ndb.soul_dwelling = True
            soul.execute_cmd(
                "pose settles into the charging cradle, indicators "
                "pulsing amber." if need == "charge" else
                "pose powers down into a maintenance cycle.")
        needs_mod.satisfy(soul, need, 0.15)     # per think while dwelling
        if needs_mod.pressure(soul, need) <= 0.10:
            soul.ndb.soul_dwelling = False
            soul.execute_cmd(
                "pose disengages from the cradle, indicators green."
                if need == "charge" else
                "pose spins back up, servos re-seated.")
            soul.db.soul_job = None
            return False
        return True

    if do == "claim":
        from world.souls import posts as posts_mod
        post = _obj(step["post"])
        if post is None:
            fault(soul, "the post vanished before the claim")
            return False
        room = post.location if post.location is not None else post
        if soul.location != room:
            fault(soul, "not at the post to claim it")
            return False
        if post.db.post_keeper is not None and \
                post.db.post_keeper.pk and \
                post.db.post_keeper != soul and \
                post.db.post_keeper.location == room:
            fault(soul, "someone already holds this post")
            return False
        posts_mod.do_claim(soul, post)
        soul.execute_cmd("pose steps in behind the post, taking stock "
                         "of the work left undone.")
        soul.db.soul_job = None
        return False

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
            from world.souls import thoughts
            needs_mod.satisfy(soul, "social", 0.7)
            where = soul.location.key if soul.location else "the street"
            thoughts.add_thought(soul, "good_company", 0.10,
                                 f"time among people at {where}")
            job["at"] = at + 1
        else:
            step["beats"] = left
        soul.db.soul_job = job
        return True

    if do == "flee":
        from world.souls import thoughts
        exits = [e for e in (soul.location.exits if soul.location else [])
                 if e.destination and not e.db.is_edge and not e.db.is_gap]
        if not exits:
            fault(soul, "cornered — nowhere to flee")
            return False
        soul.execute_cmd(exits[0].key)
        needs_mod.satisfy(soul, "safety", 0.5)
        thoughts.add_thought(soul, "fled", -0.40, "ran from trouble")
        soul.db.soul_job = None
        return False

    fault(soul, f"unknown step '{do}'")
    return False
