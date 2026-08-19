"""The souls engine — decay, schedule, arbitration, and the heartbeat.

One persistent `SoulsHeartbeat` script (the patrol-routine idiom) beats
every 30s. Each beat every soul decays by real elapsed time; whether it
also THINKS depends on LOD — hot souls (player in the room) think every
beat, warm souls (player within a few cells) every other beat, cold
souls every sixth (~3 min). A cold soul still lives its whole loop,
just at a coarser cadence.

Thinking is the spec's band tree: survive > critical needs > schedule
duty > elevated needs > idle. The tree only ARBITRATES (picks a goal);
`actions.plan_for` decides how, `jobs.step_job` does it with real
commands. A running job is only interrupted by a strictly higher band.
"""

import time

from evennia import DefaultScript
from evennia.utils.search import search_tag

from world.gametime import colony_hour
from world.souls import actions, economy, jobs
from world.souls import needs as needs_mod

HEARTBEAT_SECONDS = 30
SOUL_TAG = ("soul", "npc_role")
WARM_RADIUS = 5                      # Chebyshev cells to a player = warm
THINK_EVERY = {"hot": 1, "warm": 2, "cold": 6}
TITHE_EVERY_BEATS = 120              # supply tithe sweep: hourly

#: shift blocks by colony hour, [start, end) with midnight wraparound.
SCHEDULES = {
    "day": {"work": (9, 17), "sleep": (0, 7)},
    "night": {"work": (21, 5), "sleep": (9, 16)},
    "vendor": {"work": (10, 22), "sleep": (1, 8)},
}

GOAL_COOLDOWN_SECONDS = 900   # a failed goal rests before it's retried
WAGE_FLUSH_BEATS = 10         # ndb wage accrual checkpoints to db (5 min)


def shift_jitter_hours(soul):
    """Personal schedule offset, ±15 minutes, derived from identity —
    zero storage, stable across reloads. Spreads commutes so a shift
    change is a drift of walkers, not a synchronized column (and not a
    synchronized pathfinding burst — hardening spec §1.5)."""
    return (((soul.id * 7919) % 31) - 15) / 60.0


def soul_hour(soul, hour_f):
    """The colony's fractional hour as THIS soul's schedule feels it."""
    return (hour_f + shift_jitter_hours(soul)) % 24.0


def duty_pressure(soul, hour):
    """Duty is a pure function of schedule + location — never stored.
    0.9 while your shift runs and you are not at your post; else 0.
    `hour` may be fractional and should already be soul-jittered."""
    post = soul.db.soul_post
    if not post:
        return 0.0
    sched = SCHEDULES.get(soul.db.soul_schedule or "day", SCHEDULES["day"])
    if not _in_block(hour, sched["work"]):
        return 0.0
    return 0.0 if soul.location == post else 0.9


def _in_block(hour, block):
    start, end = block
    if start <= end:
        return start <= hour < end
    return hour >= start or hour < end


# ---------------------------------------------------------------- lifecycle

def ensoul(npc, role="resident", home=None, post=None, schedule="day",
           wage_rate=0.02, venue=None, profile=None):
    """Give an NPC a soul. `home`/`post` are rooms; `venue` is the
    ShopContainer whose till pays this post's wages (None = treasury);
    `profile` overrides species-derived needs (spec §12)."""
    if profile:
        npc.db.soul_profile = profile
    npc.db.soul_role = role
    npc.db.soul_home = home
    npc.db.soul_post = post
    npc.db.soul_schedule = schedule if schedule in SCHEDULES else "day"
    npc.db.soul_wage_rate = float(wage_rate)
    npc.db.soul_venue = venue
    npc.db.soul_wage_owed = 0.0
    needs_mod.seed(npc)
    npc.db.soul_faults = []
    npc.db.soul_job = None
    npc.tags.add(SOUL_TAG[0], category=SOUL_TAG[1])
    get_heartbeat()
    return npc


def desoul(npc):
    npc.tags.remove(SOUL_TAG[0], category=SOUL_TAG[1])
    npc.db.soul_job = None


def get_souls():
    return [npc for npc in search_tag(SOUL_TAG[0], category=SOUL_TAG[1])
            if npc]


def get_heartbeat():
    """The heartbeat lives in settings.GLOBAL_SCRIPTS — the server owns
    its creation and arms its timer at every boot. A hand-created script
    row from an external shell never gets its repeat timer armed by the
    running server (the 2026-07-02 lesson, re-learned by this engine)."""
    from evennia import GLOBAL_SCRIPTS
    return getattr(GLOBAL_SCRIPTS, "souls_heartbeat", None)


# ---------------------------------------------------------------------- LOD

def _player_rooms():
    """(room_set, coord_list) for every puppeted location — coords are
    computed ONCE per beat here, never per soul (hardening spec #4)."""
    from evennia.server.sessionhandler import SESSIONS
    from world.spatial import get_xyz
    rooms = set()
    for sess in SESSIONS.get_sessions():
        puppet = sess.get_puppet() if hasattr(sess, "get_puppet") else None
        if puppet and puppet.location:
            rooms.add(puppet.location)
    coords = [pos for pos in (get_xyz(r) for r in rooms) if pos]
    return rooms, coords


def lod_for(soul, player_rooms, player_coords):
    room = soul.location
    if room is None:
        return "cold"
    if room in player_rooms:
        return "hot"
    from world.spatial import get_xyz
    pos = get_xyz(room)
    if pos:
        for ppos in player_coords:
            if max(abs(pos[0] - ppos[0]),
                   abs(pos[1] - ppos[1])) <= WARM_RADIUS \
                    and pos[2] == ppos[2]:
                return "warm"
    return "cold"


# ------------------------------------------------------------------ thinking

def _desired_goal(soul, hour, exclude=()):
    """The band tree. Returns (band, need) — lower band wins; None = idle.
    Bands 1 and 3 iterate the soul's PROFILE needs (spec §12), so a
    robot's critical band is its battery, not a stomach it lacks.
    `exclude` drops goals whose plans are cooling down, so a soul
    blocked on one need falls through to its next-worst instead of
    idling (broke-and-hungry still goes home to SLEEP)."""
    derived = needs_mod.pressures(soul)
    body = [n for n in needs_mod.profile_of(soul)
            if n != "safety" and n not in exclude]
    # band 0: survive
    if derived.get("safety", 0.0) >= needs_mod.CRITICAL:
        return (0, "safety")
    # band 1: critical profile needs — ties break by PROFILE ORDER
    # (hunger before rest before social), never alphabetically: a soul
    # that is starving, exhausted, and lonely at once eats first
    crit = [(derived[n], -i, n) for i, n in enumerate(body)
            if derived[n] >= needs_mod.CRITICAL]
    if crit:
        return (1, max(crit)[2])
    # band 2: schedule
    sched = SCHEDULES[soul.db.soul_schedule or "day"]
    if soul.db.soul_post and "duty" not in exclude \
            and _in_block(hour, sched["work"]):
        return (2, "duty")
    if soul.db.soul_home and "rest" not in exclude \
            and _in_block(hour, sched["sleep"]) \
            and derived.get("rest", 0.0) >= 0.30:
        return (2, "rest")
    # band 3: elevated profile needs (same profile-order tie-break)
    soft = [(derived[n], -i, n) for i, n in enumerate(body)
            if derived[n] >= needs_mod.SOFT]
    if soft:
        return (3, max(soft)[2])
    return (4, None)


def _goal_band(goal):
    return {"safety": 0, "hunger": 1, "rest": 2, "duty": 2, "claim": 2,
            "social": 3}.get(goal, 4)


def think(soul, hour):
    """One decision beat: end lapsed shifts, arbitrate, plan, step."""
    from world.director.assignment import is_assigned
    from world.director.security import _in_combat
    from world.director.travel import is_travelling
    if is_assigned(soul):
        return          # precedence law: combat > assignment > souls
    if _in_combat(soul):
        # combat owns the body — EXCEPT the crime steps, which are
        # designed to run inside it (a grappler auto-yields; the rob
        # happens while the combat round loop holds the restraint). The
        # moment the mark breaks free the step faults and the fight
        # takes over for real.
        job = soul.db.soul_job
        step_do = None
        if job:
            steps = job.get("steps") or []
            at = job.get("at", 0)
            step_do = steps[at].get("do") if at < len(steps) else None
        if step_do in ("grapple", "rob", "disengage"):
            jobs.step_job(soul)
        return

    # discovery (spec §14): every thinking soul scans its room for a
    # downed body and raises the alarm through the same witnessed-radio
    # law as crime — debounced inside, one cheap scan per think
    try:
        from world.director.medical import notice_casualty
        notice_casualty(soul, soul.location)
    except Exception:  # noqa: BLE001 — mercy must not break the beat
        pass

    job = soul.db.soul_job
    sched = SCHEDULES[soul.db.soul_schedule or "day"]

    # shift release: work jobs end when the block does — PAYDAY
    if job and job.get("goal") == "duty" and not _in_block(hour, sched["work"]):
        from world.director.travel import stop_travel
        stop_travel(soul)                # a commute to a lapsed shift ends too
        soul.db.soul_job = None
        paid = economy.pay_wage(soul)
        from world.souls import thoughts
        if paid and soul.location:
            soul.execute_cmd("pose pockets the shift's pay.")
        if float(soul.db.soul_wage_owed or 0.0) >= 1.0:
            thoughts.add_thought(soul, "shift_unpaid", -0.35,
                                 "worked and the till came up short")
        elif paid:
            thoughts.add_thought(soul, "payday", 0.25,
                                 "the shift paid in full")
        job = None

    # goals whose plans recently failed are cooling down — EXCLUDE them
    # from arbitration so the soul falls through to its next-worst need
    # instead of idling on a blocked one (safety never cools)
    now = time.time()
    cooldowns = dict(soul.db.soul_goal_cooldown or {})
    cooling = {g for g, t in cooldowns.items()
               if t > now and g != "safety"}
    band, desired = _desired_goal(soul, hour, exclude=cooling)

    if job:
        # interrupt only for a strictly higher band than the one the
        # running job was PLANNED under — comparing against a static
        # goal->band map desyncs when a goal legitimately arrives at
        # band 1 (critical rest interrupted its own rest job forever,
        # and the sleep step never ran)
        job_band = job.get("band", _goal_band(job.get("goal")))
        if desired and band < job_band:
            from world.director.travel import stop_travel
            stop_travel(soul)            # preemption must actually stop feet
            if job.get("goal") == "duty":
                economy.pay_wage(soul)   # leaving the post still pays out
            soul.db.soul_job = None
        else:
            jobs.step_job(soul)
            return

    if desired is None or is_travelling(soul):
        return
    new_job = actions.plan_for(soul, desired)
    if new_job is None:
        jobs.fault(soul, f"no plan satisfies '{desired}'")
        if desired == "hunger":
            from world.souls import thoughts
            thoughts.add_thought(soul, "went_hungry", -0.25,
                                 "nothing to eat I could reach or afford")
        cooldowns = {g: t for g, t in cooldowns.items() if t > now}
        cooldowns[desired] = now + GOAL_COOLDOWN_SECONDS
        soul.db.soul_goal_cooldown = cooldowns
        return
    new_job["band"] = band          # remembered for interrupt comparisons
    soul.db.soul_job = new_job
    jobs.step_job(soul)


# ----------------------------------------------------------------- heartbeat

class SoulsHeartbeat(DefaultScript):
    """Global ticker for every ensouled NPC. Persistent across reloads."""

    def at_script_creation(self):
        self.key = "souls_heartbeat"
        self.desc = "Souls engine: need decay + LOD-scaled thinking."
        self.interval = HEARTBEAT_SECONDS
        self.persistent = True

    def at_repeat(self):
        beat = int(self.db.beat or 0) + 1
        self.db.beat = beat
        try:
            from world.gametime import colony_now
            t = colony_now()
            hour_f = t.hour + t.minute / 60.0
        except Exception:
            hour_f = 12.0
        player_rooms, player_coords = _player_rooms()
        now = time.time()

        for soul in get_souls():
            # one bad soul must cost one soul, never the rest of the beat
            try:
                self._beat_soul(soul, beat, hour_f, player_rooms,
                                player_coords, now)
            except Exception as err:
                try:
                    jobs.fault(soul, f"beat crashed: {err}")
                except Exception:
                    pass

        # offset by a prime so the sweep never shares a beat with any
        # think cadence multiple
        if beat % TITHE_EVERY_BEATS == 7:
            economy.run_tithe()
        # the vacancy watcher (spec §13) — posts notice their keepers
        from world.souls import posts as posts_mod
        if beat % posts_mod.SWEEP_EVERY_BEATS == 3:
            try:
                posts_mod.sweep(now)
            except Exception:   # noqa: BLE001 — a bad post can't kill beats
                pass
        # the population keeper (spec §14): the colony breathes people —
        # arrivals rate-limited inside, disposition scaled by poverty
        if beat % 120 == 41:
            try:
                from world.souls import population
                arrival = population.sweep(self, now)
                if arrival is not None:
                    from evennia.utils import logger
                    logger.log_info(
                        f"Population keeper: {arrival.key} arrived "
                        f"({'desperate' if arrival.db.soul_lawless else 'seeker'}).")
            except Exception:   # noqa: BLE001 — arrivals can't kill beats
                pass

    def _beat_soul(self, soul, beat, hour_f, player_rooms, player_coords,
                   now):
        """One soul's slice of the beat. Needs derive on read (zero
        writes here); the only periodic write is the wage checkpoint,
        and only for souls actually standing their post. All cadences
        are phase-offset by identity — `beat % N` across a population
        is a thundering herd (hardening spec law #4)."""
        if not soul.pk or soul.location is None:
            return
        shour = soul_hour(soul, hour_f)
        # wages accrue per BEAT at post, not per think — LOD must not
        # change what a shift pays. Accrual rides ndb and checkpoints
        # to db every WAGE_FLUSH_BEATS (a reload costs at most ~5 min
        # of one soul's accrual — hardening spec law #2).
        sched = SCHEDULES.get(soul.db.soul_schedule or "day",
                              SCHEDULES["day"])
        on_shift = bool(soul.db.soul_post) and _in_block(shour, sched["work"])
        at_post = on_shift and soul.location == soul.db.soul_post
        job = soul.db.soul_job
        if at_post and job and job.get("goal") == "duty":
            pending = float(soul.ndb.soul_wage_pending or 0.0) + float(
                soul.db.soul_wage_rate or 0.02)
            if pending and (beat + soul.id) % WAGE_FLUSH_BEATS == 0:
                soul.db.soul_wage_owed = float(
                    soul.db.soul_wage_owed or 0.0) + pending
                pending = 0.0
            soul.ndb.soul_wage_pending = pending

        lod = lod_for(soul, player_rooms, player_coords)
        soul.ndb.soul_lod = lod
        if (beat + soul.id) % THINK_EVERY[lod] == 0:
            try:
                think(soul, shour)
            except Exception as err:
                jobs.fault(soul, f"think crashed: {err}")
