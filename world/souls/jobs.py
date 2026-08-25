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


def _signal(kind, soul, note=""):
    """Tell the bus something happened. Observation only (world.wsis)."""
    try:
        from world import wsis
        wsis.emit(kind, soul.location, note=note or soul.key)
    except Exception:  # noqa: BLE001 — the bus never breaks a job
        pass


def fault(soul, msg):
    # a faulted recovery must release its claim, or the unit can never
    # take another errand (#2282)
    if soul.db.soul_recovering:
        soul.db.soul_recovering = None
    log = soul.db.soul_faults or []
    log.append((time.time(), msg))
    soul.db.soul_faults = log[-FAULT_KEEP:]
    soul.db.soul_job = None
    stop_travel(soul)       # an aborted job must not keep walking its route
    _signal("travel_stalled" if "travel" in msg else "plan_faulted", soul, f"{soul.key}: {msg}")

def _obj(dbid):
    """Indexed PK fetch — the full search stack costs 200x as much
    (262us vs 1.3us measured, hardening spec §1.5)."""
    from evennia.objects.models import ObjectDB
    obj = ObjectDB.objects.get_id(dbid)
    return obj if obj and obj.pk else None


def _conscience(soul, job, where=None):
    """Charge a soul for acting against their nature, or warm them for
    living up to it (NPC_TRAITS_SPEC §4).

    No new meter: guilt is a heavy, slow-fading THOUGHT, and thoughts
    are already mood — which already opens the bottle and the knife.
    So a gentle soul driven to rob starts a spiral that is entirely
    emergent, and every link of it is legible in `@soul`.
    """
    from world.souls import thoughts, traits as traits_mod

    tags = tuple((job or {}).get("ethos") or ())
    if not tags:
        return
    if getattr(soul.ndb, "conscience_charged", None) == id(job):
        return                      # once per deed, not once per tick
    soul.ndb.conscience_charged = id(job)
    place = (where or soul.location)
    place = place.key if place else "somewhere"
    if traits_mod.abhors(soul, tags):
        thoughts.add_thought(soul, "against_my_nature",
                             traits_mod.GUILT_WEIGHT,
                             f"what I did at {place}", wound=True)
    elif traits_mod.relishes(soul, tags):
        thoughts.add_thought(soul, "felt_like_myself",
                             traits_mod.RELISH_WEIGHT,
                             f"an honest hour at {place}")


def _post_placement(soul):
    """The on-shift placement line for this soul's post, if it authored
    one. Looks on the post ROOM's registered fixtures, so a counter can
    say how its keeper stands at it."""
    room = soul.db.soul_post
    if room is None:
        return None
    for obj in getattr(room, "contents", ()):
        line = getattr(obj.db, "post_work_place", None) if obj.db else None
        if line:
            return line
    return getattr(room.db, "post_work_place", None)


def _uses_left(item):
    """Bites remaining in a consumable, or None if it doesn't say."""
    try:
        return item.db.uses_left
    except Exception:  # noqa: BLE001
        return None


def _post_seat(soul):
    """The chair this post's work is done FROM, if it declared one
    (``post_work_seat`` on the furniture).

    Some desks only work seated. `world.radio.seated_base_station` is
    the law — whoever holds the chair holds the voice — so a dispatcher
    who never sits down is a dispatcher who cannot key up at all, and
    nothing in the souls layer was ever putting anyone in a chair
    (#2225)."""
    room = soul.db.soul_post
    if room is None:
        return None
    for obj in getattr(room, "contents", ()) or []:
        if obj.db and getattr(obj.db, "post_work_seat", None) is True:
            return obj
    return None


def _take_the_post(soul):
    """Stand — or sit — visibly at work."""
    line = _post_placement(soul)
    if line and soul.db.temp_place != line:
        soul.db.temp_place = line
        soul.ndb.placed_by_shift = True

    seat = _post_seat(soul)
    if (seat is not None and soul.db.furniture is not seat
            and getattr(seat, "location", None) is soul.location
            and not seat.is_full()):
        # the real command, so occupancy, posture and the room messaging
        # all hold — and somebody squatting the chair keeps it, which is
        # a desk that can't broadcast rather than a bug
        soul.execute_cmd(f"sit on {seat.key}")
        soul.ndb.seated_by_shift = True


def _leave_the_post(soul):
    """Stop standing at work — only clears placement WE set, so a
    player-authored @temp_place is never trampled. Same courtesy for the
    chair: we only stand them up if the shift is what sat them down."""
    if getattr(soul.ndb, "placed_by_shift", False):
        soul.db.temp_place = ""
        soul.ndb.placed_by_shift = False
    if getattr(soul.ndb, "seated_by_shift", False):
        if soul.db.furniture is not None:
            soul.execute_cmd("stand")
        soul.ndb.seated_by_shift = False


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
                # meal over — the eat COMMAND moved the meter (#2074:
                # nutrition rides the substance pipeline, per bite);
                # here we only judge the outcome
                fed = (step.get("start_p", 1.0)
                       - needs_mod.pressure(soul, "hunger"))
                if fed < 0.05:
                    fault(soul, f"{step.get('last_food', 'the meal')} "
                                "didn't nourish (proto missing nutrition?)")
                else:
                    where = (soul.location.key if soul.location
                             else "the street")
                    thoughts.add_thought(
                        soul, "ate_well", 0.15,
                        f"{step.get('last_food', 'a hot meal')} at {where}")
                job["at"] = at + 1
                soul.db.soul_job = job
                return True
            fault(soul, "nothing edible in hand")
            return False
        if not step.get("bites"):
            step["start_p"] = needs_mod.pressure(soul, "hunger")
        step["last_food"] = edible.key
        bites = step.get("bites", 0) + 1
        if bites > 12:
            fault(soul, f"{edible.key} never finishes (uses_left stuck?)")
            return False
        # Say WHICH one, the way a player has to. `eat stew` is fine
        # until you carry a second bowl; then every attempt gets
        # "Multiple items match 'stew'." and the meal never happens.
        # Souls bought a bowl per hunger pang and ate none of them,
        # twenty-three deep — which is also where the memory spam and
        # the permanent crowd at the counter came from (#2244).
        #
        # The command already disambiguates ("first stew", "2nd mug"):
        # the souls layer simply never used the syntax it offers. No
        # auto-picking — one of those bowls could be poisoned, and
        # choosing for the eater is not the parser's business.
        before = _uses_left(edible)
        soul.execute_cmd(f"eat first {edible.key.split()[-1]}")
        # Only count a bite that actually happened. Counting the attempt
        # made twelve refusals look exactly like twelve mouthfuls, and
        # sent the fault off accusing the food's nutrition data.
        if _uses_left(edible) == before and edible.pk:
            fault(soul, f"could not eat {edible.key}")
            return False
        step["bites"] = bites
        soul.db.soul_job = job
        return True

    if do == "consume":
        # the vice run's mouth (#2076): drink/eat the bought ware via
        # the real verb. The dose resets the addiction clock inside
        # apply_substance (record_dose) — no engine-side satisfaction.
        from world.consumables import supports_delivery
        from world.souls import thoughts
        verb = step.get("verb", "drink")
        item = next((o for o in soul.contents
                     if supports_delivery(o, verb)), None)
        if item is None:
            if step.get("sips"):
                where = (soul.location.key if soul.location
                         else "the street")
                thoughts.add_thought(
                    soul, "took_the_edge_off", 0.10,
                    f"{step.get('last_item', 'a drink')} at {where}")
                eased = (step.get("start_p", 1.0)
                         - needs_mod.pressure(soul, "craving"))
                if job.get("goal") == "craving" and eased < 0.05:
                    fault(soul, f"{step.get('last_item', 'the vice')} "
                                "didn't scratch the itch (ware missing "
                                "the substance?)")
                job["at"] = at + 1
                soul.db.soul_job = job
                return True
            fault(soul, f"nothing to {verb} in hand")
            return False
        if not step.get("sips"):
            step["start_p"] = needs_mod.pressure(soul, "craving")
        step["last_item"] = item.key
        sips = step.get("sips", 0) + 1
        if sips > 12:
            fault(soul, f"{item.key} never finishes (uses_left stuck?)")
            return False
        soul.execute_cmd(f"{verb} {item.key.split()[-1]}")
        step["sips"] = sips
        soul.db.soul_job = job
        return True

    if do == "press":
        # push the button, like anyone would (#2104)
        fixture = _obj(step["fixture"])
        if fixture is None or fixture.location != soul.location:
            fault(soul, "the machine isn't here")
            return False
        soul.execute_cmd(f"press {fixture.key.split()[-1]}")
        job["at"] = at + 1
        soul.db.soul_job = job
        return True

    if do == "wear":
        # dress through the real verb, garment by garment, until the
        # soul meets their own modesty (#2104)
        from world.souls import thoughts
        from world.souls.actions import _wearable
        # dress from the skin out; `int(layer or 1)` would promote
        # every layer-0 garment to base and put socks over trousers
        def _rung(g):
            lay = getattr(g, "layer", None)
            return 1 if lay is None else int(lay)

        wearable = sorted((o for o in soul.contents if _wearable(soul, o)),
                          key=_rung)
        if not wearable:
            # shed the paper: real clothes REPLACE the issue rather than
            # layering over it (#2118). The issue TEARS coming off
            # (#2120), so decide BEFORE stripping: only shed it when the
            # real clothes already cover everything modesty asks for.
            # Otherwise the paper stays on and is worn under.
            worn_now = list(dict.fromkeys(
                g for items in (soul.worn_items or {}).values() for g in items))
            paper = [g for g in worn_now if g.attributes.get("provisional")]
            real = [g for g in worn_now if not g.attributes.get("provisional")]
            if paper and real:
                covered_by_real = set()
                for garment in real:
                    covered_by_real |= set(garment.attributes.get("coverage") or ())
                if needs_mod.modesty_of(soul) <= covered_by_real:
                    # safe to lose the paper: strip everything (the issue
                    # perishes on the way off), then re-dress in what's real
                    for garment in sorted(worn_now, key=lambda g: -_rung(g)):
                        soul.remove_item(garment)
                    for garment in sorted((g for g in real if g.pk), key=_rung):
                        soul.wear_item(garment)
            if needs_mod.wardrobe_pressure(soul) >= 1.0:
                fault(soul, "nothing here fit to wear")
                return False
            thoughts.add_thought(soul, "dressed", 0.10,
                                 "decent again, at least")
            job["at"] = at + 1
            soul.db.soul_job = job
            soul.db.soul_job = None
            return False
        soul.execute_cmd(f"wear {wearable[0].key.split()[-1]}")
        rounds = step.get("rounds", 0) + 1
        if rounds > 8:
            fault(soul, f"{wearable[0].key} won't go on")
            return False
        step["rounds"] = rounds
        soul.db.soul_job = job
        return True

    if do == "graze":
        # eat from a serving fixture via the REAL eat verb (#2074) —
        # same membrane, same limitations as a player in the room.
        # The command's nutrition dose moves the meter; we loop until
        # sated (the recluse's plumbed-in meal, spec §12).
        from world.souls import thoughts
        fixture = _obj(step["fixture"])
        if fixture is None or fixture.location != soul.location:
            fault(soul, "the feed fixture is gone")
            return False
        rounds = step.get("rounds", 0) + 1
        if rounds > 12:
            fault(soul, f"{fixture.key} serves but the hunger stays "
                        "(snack entry missing nutrition?)")
            return False
        soul.execute_cmd(f"eat {step['word']} from {fixture.key}")
        step["rounds"] = rounds
        soul.db.soul_job = job
        if needs_mod.pressure(soul, "hunger") <= 0.10:
            where = soul.location.key if soul.location else "somewhere"
            thoughts.add_thought(soul, "ate_well", 0.10,
                                 f"the feed at {where}")
            soul.db.soul_job = None
            return False
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
            if need == "maintenance":
                # the service cycle is also a repair: the newest fault
                # comes back out, and the unit is cleared to earn
                # another one next time it is neglected
                from world.souls import traits as traits_mod
                fixed = traits_mod.clear_defect(soul)
                soul.ndb.wear_charged = None
                if fixed:
                    soul.execute_cmd(
                        f"pose runs a self-test and clears a logged "
                        f"fault: {traits_mod.DEFECTS[fixed]['label']}.")
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

    if do == "hold":
        # TAKE HOLD of a body that cannot resist.
        #
        # Not the mugger's `grapple` step, which guards on
        # can_contest() -- conscious AND unrestrained. A wreck is
        # neither, so that step reads an unresisting body as ALREADY
        # HELD, advances without issuing the command, and the detail
        # walks home dragging nothing, successfully, with no fault
        # raised (#2282). Silent success is the worst failure shape
        # there is, so recovery gets its own step.
        from world.combat.grappling import is_grappled
        from world.director.security import _target_token
        wreck = _obj(step["wreck"])
        if wreck is None:
            fault(soul, "the casualty was gone before it could be lifted")
            return False
        if wreck.location != soul.location:
            fault(soul, "the casualty moved before it could be lifted")
            return False
        if not is_grappled(wreck):
            soul.execute_cmd(f"grapple {_target_token(wreck)}")
        if is_grappled(wreck):
            job["at"] = at + 1
            soul.db.soul_job = job
            return True
        # somebody else has it, or the grab did not take -- try again
        # next beat rather than abandoning a casualty in the street
        return True

    if do == "deliver":
        # Home with it. Let go, and then one of two things.
        from world.director.security import _cmd
        wreck = _obj(step["wreck"])
        soul.execute_cmd("release")
        if wreck is not None:
            uid = getattr(wreck, "id", 0) or 0
            here = getattr(soul.location, "key", "the precinct")
            finished = False
            try:
                finished = bool(wreck.is_dead())
            except Exception:  # noqa: BLE001 — unreadable body: treat as
                finished = False              # repairable, never junk it
            if finished:
                # DESTROYED: take the armament off it before anything
                # else happens to it. A unit's weapon is an augment
                # organ, so an unstripped wreck is a working shotgun
                # nobody is holding (#2284).
                from world.director.disposal import strip_and_junk
                strip_and_junk(soul, wreck)
                _cmd(soul, f"xmit Unit {getattr(soul, 'id', 0) or 0} — "
                           f"{here}. Unit {uid} recovered, not "
                           f"repairable. Armament secured.")
            else:
                # DOWNED: leave it for the bench. The mechanic's own
                # racking behaviour takes it from here.
                _cmd(soul, f"xmit Unit {getattr(soul, 'id', 0) or 0} — "
                           f"{here}. Unit {uid} recovered.")
        soul.db.soul_recovering = None
        soul.db.soul_job = None
        return False

    if do == "collect":
        # Custody starts with a person, not out of thin air. The depot
        # keeper is handed the parcel and hands it on -- so there is a
        # real chain, and a real object that can be taken off her
        # between here and the far end (#2295).
        from world.director.security import _target_token
        clerk = _obj(step["clerk"])
        if clerk is None or clerk.location is not soul.location:
            fault(soul, "nobody at the counter to collect from")
            return False
        parcel = next((o for o in clerk.contents
                       if o.attributes.has("courier_package")), None)
        if parcel is None:
            fault(soul, "the consignment wasn't ready")
            return False
        parcel.move_to(soul, quiet=True, move_hooks=False)
        soul.execute_cmd(f"emote takes the parcel from "
                         f"{_target_token(clerk)} and signs for it.")
        job["at"] = at + 1
        soul.db.soul_job = job
        return True

    if do == "handoff":
        # The far end of a run. `deliver` is the RECOVERY step's name
        # (#2282) and means something else entirely, so the courier's
        # is `handoff`.
        from world.director import courier
        counter = _obj(step["counter"])
        if counter is None or counter.location is not soul.location:
            fault(soul, "the counter wasn't there to hand it to")
            return False
        package = next((o for o in soul.contents
                        if o.attributes.has("courier_package")), None)
        report = courier.hand_over(soul, counter, package)
        # Signed for and filed. The parcel leaves the world here rather
        # than accumulating on a counter forever -- one McGuffin per
        # run, and the run is what mattered.
        if package is not None and package.pk:
            package.delete()
        # courier.hand_over already told the bus; nothing to do here
        # but let the run finish, paid or not.
        job["at"] = at + 1
        soul.db.soul_job = job
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
        _signal("robbery", soul, f"{soul.key} robbed {mark.key}")
        _conscience(soul, job, where=mark.location)
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
            _conscience(soul, job)
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
        # Everything the post asks of whoever holds it: the role's
        # standing upkeep (a medic's par-level restock) and whatever the
        # world put in the inbox since the last beat (a call on the board
        # they are sitting at). Both are the job — answering the radio IS
        # the dispatcher's duty rather than an interruption of it, so it
        # happens inside the shift (SOULS_SALIENCE_SPEC §3.4).
        #
        # The medic restock used to be an `if soul.db.soul_role ==
        # "medic"` branch right here, the one hard-coded exception in an
        # otherwise generic loop (#2236).
        try:
            from world.souls import salience
            salience.do_post_work(soul)
        except Exception:  # noqa: BLE001 — the shift outlives one bad beat
            pass
        # you can SEE who is working: the post's own placement line goes
        # on while the shift is held, so a room tells you who is behind
        # the counter and who is merely standing near it. A person is not
        # their job — but their job is visible while they're doing it
        # (#2148).
        _take_the_post(soul)
        return True

    if do == "linger":
        left = step.get("beats", 3) - 1
        if left <= 0:
            from world.souls import thoughts
            needs_mod.satisfy(soul, "social", 0.7)
            where = soul.location.key if soul.location else "the street"
            _conscience(soul, job)
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
