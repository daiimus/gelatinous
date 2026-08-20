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
        # generic occupy-and-recover (charge, maintenance, a recluse's
        # line and airwaves — spec §12). The FIXTURE authors its own
        # poses (db.dwell_pose_in/out) so the world writes the flavor;
        # the cradle defaults cover unauthored fixtures.
        need = step.get("need", "charge")
        fixture = _obj(step["fixture"]) if step.get("fixture") else None
        pose_in = (getattr(fixture.db, "dwell_pose_in", None)
                   if fixture else None) or (
            "settles into the charging cradle, indicators pulsing amber."
            if need == "charge" else
            "powers down into a maintenance cycle.")
        pose_out = (getattr(fixture.db, "dwell_pose_out", None)
                    if fixture else None) or (
            "disengages from the cradle, indicators green."
            if need == "charge" else
            "spins back up, servos re-seated.")
        if not soul.ndb.soul_dwelling:
            soul.ndb.soul_dwelling = True
            soul.execute_cmd(f"pose {pose_in}")
        needs_mod.satisfy(soul, need, 0.15)     # per think while dwelling
        if needs_mod.pressure(soul, need) <= 0.10:
            soul.ndb.soul_dwelling = False
            soul.execute_cmd(f"pose {pose_out}")
            soul.db.soul_job = None
            return False
        return True

    if do == "grapple":
        from world.consent import can_contest
        from world.director.security import _target_token
        mark = _obj(step["mark"])
        if mark is None or mark.location != soul.location:
            fault(soul, "the mark slipped away")
            return False
        if can_contest(mark):
            soul.execute_cmd(f"grapple {_target_token(mark)}")
        if not can_contest(mark):
            # held OR beaten down — either way the pockets are open
            job["at"] = at + 1
            soul.db.soul_job = job
        # a failed contest means a FIGHT owns the mugger now — the job
        # holds this step and retries when combat releases the body
        return True

    if do == "rob":
        from world.consent import can_contest
        from world.director.security import _target_token
        from world.souls import thoughts
        mark = _obj(step["mark"])
        if mark is None or mark.location != soul.location:
            fault(soul, "the mark got away mid-rob")
            return False
        if can_contest(mark):
            # neither held nor down — the free-loot window closed
            fault(soul, "the mark broke free before the take")
            return False
        before = int(soul.tokens or 0)
        soul.execute_cmd(f"pickpocket {_target_token(mark)}")
        step["took"] = step.get("took", 0) + max(
            0, int(soul.tokens or 0) - before)
        step["lifts"] = step.get("lifts", 2) - 1
        if step["lifts"] <= 0 or step["took"] >= 5 \
                or int(getattr(mark, "tokens", 0) or 0) <= 0:
            where = soul.location.key if soul.location else "the street"
            thoughts.add_thought(
                soul, "mugged_someone", -0.20,
                f"took {step['took']} tokens off someone at {where}")
            thoughts.add_thought(
                mark, "was_mugged", -0.45,
                f"held down and robbed at {where}")
            job["at"] = at + 1
        soul.db.soul_job = job
        return True

    if do == "disengage":
        from world.combat.utils import find_character_handler
        from world.director.security import _target_token
        soul.execute_cmd("release")
        soul.execute_cmd("flee")
        handler = find_character_handler(soul)
        if handler is not None:
            # the getaway failed — the mark's retaliation keeps the fight
            # alive and a yielding mugger is just a punching bag. The
            # lethal verdict applies: stop yielding, fight it out, and
            # let the combat engine decide who walks away.
            mark = _obj(step.get("mark", 0)) if step.get("mark") else None
            if mark is not None and mark.location == soul.location:
                from world.combat.utils import find_best_weapon
                best = find_best_weapon(soul)
                if best is not None:
                    soul.execute_cmd(f"wield {best.key}")
                soul.execute_cmd(f"attack {_target_token(mark)}")
        soul.db.soul_job = None
        return False

    if do == "treat":
        # Maxwell's model (spec §14): the doctor treats through real
        # verbs and bottomless clinic stock; healing is BILLED into the
        # clinic till, but active bleeding is triaged free — nobody
        # dies on the doorstep, the broke just limp off unhealed.
        import time as _time

        from typeclasses.clinic import Doctor
        from world.souls import needs as needs_mod
        from world.souls import thoughts

        TREAT_FEE = 8
        terminal = _obj(step["clinic"])
        if terminal is None or terminal.location != soul.location:
            fault(soul, "the clinic desk is gone")
            return False
        doctor = next((o for o in soul.location.contents
                       if isinstance(o, Doctor) and o.pk), None)
        if doctor is None:
            fault(soul, "no doctor on the floor")
            return False
        bleeding = any(
            "bleed" in str((c.get("type") if isinstance(c, dict) else c)
                           or "").lower()
            for c in ((soul.db.medical_state or {}).get("conditions") or []))
        paid = False
        if int(soul.tokens or 0) >= TREAT_FEE:
            soul.tokens = int(soul.tokens or 0) - TREAT_FEE
            terminal.db.register = int(terminal.db.register or 0) + TREAT_FEE
            paid = True
        elif not bleeding:
            fault(soul, "couldn't afford the doctor")
            thoughts.add_thought(soul, "turned_away", -0.30,
                                 "too broke for the clinic; walked out "
                                 "still hurting")
            return False
        doctor._treat(soul, "bandage")
        if paid:
            doctor._treat(soul, "painkiller")
            thoughts.add_thought(soul, "patched_up", 0.20,
                                 "paid the clinic and got put back together")
        else:
            thoughts.add_thought(soul, "triaged", 0.05,
                                 "the clinic stopped the bleeding and "
                                 "showed me the door")
        # one visit per cooldown window — healing lands over the medical
        # ticks, and pressure derives from the body, not a meter
        cooldowns = dict(soul.db.soul_goal_cooldown or {})
        cooldowns["health"] = _time.time() + 1800
        soul.db.soul_goal_cooldown = cooldowns
        soul.db.soul_job = None
        return False

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
        posts_mod.do_claim(soul, post, step.get("shift", "day"))
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
        if soul.db.soul_role == "medic":
            try:
                from world.director.medical import restock_medic
                restock_medic(soul)   # par-level loose supplies at post
            except Exception:  # noqa: BLE001 — restock is best-effort
                pass
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
