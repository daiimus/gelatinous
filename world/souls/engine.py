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
}


def _in_block(hour, block):
    start, end = block
    if start <= end:
        return start <= hour < end
    return hour >= start or hour < end


# ---------------------------------------------------------------- lifecycle

def ensoul(npc, role="resident", home=None, post=None, schedule="day",
           wage_rate=0.02, venue=None):
    """Give an NPC a soul. `home`/`post` are rooms; `venue` is the
    ShopContainer whose till pays this post's wages (None = treasury)."""
    npc.db.soul_role = role
    npc.db.soul_home = home
    npc.db.soul_post = post
    npc.db.soul_schedule = schedule if schedule in SCHEDULES else "day"
    npc.db.soul_wage_rate = float(wage_rate)
    npc.db.soul_venue = venue
    npc.db.soul_wage_owed = 0.0
    npc.db.soul_needs = dict(needs_mod.DEFAULT_NEEDS)
    npc.db.soul_faults = []
    npc.db.soul_job = None
    npc.db.soul_last_decay = time.time()
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
    from evennia.server.sessionhandler import SESSIONS
    rooms = set()
    for sess in SESSIONS.get_sessions():
        puppet = sess.get_puppet() if hasattr(sess, "get_puppet") else None
        if puppet and puppet.location:
            rooms.add(puppet.location)
    return rooms


def lod_for(soul, player_rooms):
    room = soul.location
    if room is None:
        return "cold"
    if room in player_rooms:
        return "hot"
    from world.spatial import get_xyz
    pos = get_xyz(room)
    if pos:
        for proom in player_rooms:
            ppos = get_xyz(proom)
            if ppos and max(abs(pos[0] - ppos[0]),
                            abs(pos[1] - ppos[1])) <= WARM_RADIUS \
                    and pos[2] == ppos[2]:
                return "warm"
    return "cold"


# ------------------------------------------------------------------ thinking

def _desired_goal(soul, hour):
    """The band tree. Returns (band, need) — lower band wins; None = idle."""
    p = lambda need: needs_mod.pressure(soul, need)
    # band 0: survive
    if p("safety") >= needs_mod.CRITICAL:
        return (0, "safety")
    # band 1: critical body needs
    crit = [(p(n), n) for n in ("hunger", "rest") if p(n) >= needs_mod.CRITICAL]
    if crit:
        return (1, max(crit)[1])
    # band 2: schedule
    sched = SCHEDULES[soul.db.soul_schedule or "day"]
    if soul.db.soul_post and _in_block(hour, sched["work"]):
        return (2, "duty")
    if soul.db.soul_home and _in_block(hour, sched["sleep"]) \
            and p("rest") >= 0.30:
        return (2, "rest")
    # band 3: elevated needs
    soft = [(p(n), n) for n in ("hunger", "rest", "social")
            if p(n) >= needs_mod.SOFT]
    if soft:
        return (3, max(soft)[1])
    return (4, None)


def _goal_band(goal):
    return {"safety": 0, "hunger": 1, "rest": 2, "duty": 2, "social": 3}.get(
        goal, 4)


def think(soul, hour):
    """One decision beat: end lapsed shifts, arbitrate, plan, step."""
    from world.director.security import _in_combat
    from world.director.travel import is_travelling
    if _in_combat(soul):
        return                                       # combat owns the body

    job = soul.db.soul_job
    sched = SCHEDULES[soul.db.soul_schedule or "day"]

    # shift release: work jobs end when the block does — PAYDAY
    if job and job.get("goal") == "duty" and not _in_block(hour, sched["work"]):
        soul.db.soul_job = None
        paid = economy.pay_wage(soul)
        if paid and soul.location:
            soul.execute_cmd("pose pockets the shift's pay.")
        needs_mod.satisfy(soul, "duty", 1.0)
        job = None

    band, desired = _desired_goal(soul, hour)

    if job:
        # interrupt only for a strictly higher band than the running goal
        if desired and band < _goal_band(job.get("goal")):
            soul.db.soul_job = None
        else:
            jobs.step_job(soul)
            return

    if desired is None or is_travelling(soul):
        return
    new_job = actions.plan_for(soul, desired)
    if new_job is None:
        jobs.fault(soul, f"no plan satisfies '{desired}'")
        return
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
            hour = colony_hour()
        except Exception:
            hour = 12
        player_rooms = _player_rooms()
        now = time.time()

        for soul in get_souls():
            if not soul.pk or soul.location is None:
                continue
            # decay by real elapsed time, every beat, every LOD
            last = float(soul.db.soul_last_decay or now)
            minutes = max(0.0, (now - last) / 60.0)
            soul.db.soul_last_decay = now
            needs = needs_mod.tick_decay(soul, minutes)
            # duty pressure is pure schedule: on during your block, off after
            sched = SCHEDULES[soul.db.soul_schedule or "day"]
            on_shift = bool(soul.db.soul_post) and _in_block(
                hour, sched["work"])
            at_post = on_shift and soul.location == soul.db.soul_post
            needs["duty"] = 0.9 if (on_shift and not at_post) else (
                0.0 if not on_shift else needs.get("duty", 0.0))
            soul.db.soul_needs = needs
            # wages accrue per BEAT at post, not per think — LOD must not
            # change what a shift pays
            job = soul.db.soul_job
            if at_post and job and job.get("goal") == "duty":
                soul.db.soul_wage_owed = float(
                    soul.db.soul_wage_owed or 0.0) + float(
                    soul.db.soul_wage_rate or 0.02)

            lod = lod_for(soul, player_rooms)
            soul.ndb.soul_lod = lod
            if beat % THINK_EVERY[lod] == 0:
                try:
                    think(soul, hour)
                except Exception as err:
                    jobs.fault(soul, f"think crashed: {err}")

        if beat % TITHE_EVERY_BEATS == 0:
            economy.run_tithe()
