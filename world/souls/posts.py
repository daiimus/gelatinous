"""Posts & succession (spec §13) — the post survives its keeper.

A post record lives on the fixture that IS the post: the counter for
venues, the room for roomed posts. The vacancy watcher rides the souls
heartbeat; a dead/deleted/desouled keeper stamps the post vacant, and
once the grace elapses under policy `successor`, the nearest eligible
unemployed soul is handed a claim job — it walks there for real and
takes the work. No candidate: the post stays visibly dark, and the
vacancy is the content.
"""

import time

from evennia.utils.search import search_tag

POST_TAG = ("post", "souls")
SWEEP_EVERY_BEATS = 10
DEFAULT_DELAY = 6 * 3600          # vacancy grace before succession
RESLEAVE_PREMIUM = 40             # what the insurer's till pays Maxwell
RESLEAVE_GAP = 5400               # the last ~90min never made the backup


def register_post(fixture, role, schedule="day", wage_rate=0.02,
                  policy="successor", delay=DEFAULT_DELAY, keeper=None):
    """Make *fixture* (counter or room) an administrative post."""
    fixture.db.post_role = role
    fixture.db.post_schedule = schedule
    fixture.db.post_wage_rate = float(wage_rate)
    fixture.db.post_policy = policy
    fixture.db.post_delay = int(delay)
    fixture.db.post_vacant_since = None
    if keeper is not None:
        fixture.db.post_keeper = keeper
    fixture.tags.add(POST_TAG[0], category=POST_TAG[1])
    return fixture


def get_posts():
    return [p for p in search_tag(POST_TAG[0], category=POST_TAG[1]) if p]


def _post_room(post):
    return post.location if post.location is not None else post


def _keeper_holds(post, keeper):
    """Is this keeper alive, souled, and still bound to this post?"""
    if keeper is None or not keeper.pk:
        return False
    room = _post_room(post)
    return keeper.db.soul_post == room or post.db.post_keeper == keeper


def _eligible_candidates(room):
    """Unemployed souls, nearest first — human-shaped, idle, alive."""
    from world.souls import engine
    from world.souls import needs as needs_mod
    from world.spatial import get_xyz

    origin = get_xyz(room)
    out = []
    for soul in engine.get_souls():
        if not soul.pk or soul.location is None:
            continue
        if soul.db.soul_post is not None or soul.db.soul_job:
            continue
        if needs_mod.profile_name(soul) == "robot":
            continue
        pos = get_xyz(soul.location)
        dist = (max(abs(origin[0] - pos[0]), abs(origin[1] - pos[1]))
                if origin and pos else 999)
        out.append((dist, soul.id, soul))
    out.sort()
    return [s for _, _, s in out]


def _try_resleave(post, room, now) -> bool:
    """The insurance pays out (spec §P3, owner verdicts 2026-08-19):
    rebuild the keeper from their blueprint, restore the estate MINUS
    the death gap (the last ~90 minutes never made the backup — murder
    stays a mystery), and debit the insurer's till a REAL premium paid
    to Maxwell. A till that can't afford it keeps earning — a cart can
    sell noodles toward its own keeper's resurrection."""
    from evennia.utils.search import search_object

    bp_key = post.db.post_blueprint
    if not bp_key:
        return False
    till = post if post.db.register is not None else post.db.post_insurer
    if till is None or int(till.db.register or 0) < RESLEAVE_PREMIUM:
        return False
    from world.npcs.blueprints import build_npc
    try:
        npc = build_npc(bp_key, room)
    except Exception:  # noqa: BLE001 — a broken blueprint must not loop-spawn
        return False
    npc.db.is_npc = True
    # the premium moves for real: insurer till -> Maxwell's terminal
    till.db.register = int(till.db.register or 0) - RESLEAVE_PREMIUM
    provider = next((o for o in search_object("a Thawn-Harrison billing "
                                              "terminal") if o.pk), None)
    if provider is not None:
        provider.db.register = int(provider.db.register or 0) \
            + RESLEAVE_PREMIUM

    # the estate returns, minus the gap
    snap = post.db.post_memory_snapshot
    if snap:
        died = float(snap.get("died_at") or now)
        cutoff = died - RESLEAVE_GAP
        npc.db.llm_memories = [
            r for r in (snap.get("memories") or [])
            if float(r.get("created", 0) or 0) < cutoff]
        npc.db.llm_dossiers = dict(snap.get("dossiers") or {})
        npc.db.soul_thoughts = [
            t for t in (snap.get("thoughts") or [])
            if float(t[0]) < cutoff]

    # a life again: housing through the real kiosk, then the soul
    try:
        from world import rental
        kiosk = next(iter(search_object("#5640")), None)
        if kiosk is not None:
            rental.assign_cube(npc, kiosk)
        home = rental.residence_of(npc)
    except Exception:  # noqa: BLE001 — homeless but alive beats neither
        home = None
    from world.souls import engine
    engine.ensoul(npc, role=post.db.post_role or "worker", home=home,
                  post=room, schedule=post.db.post_schedule or "day",
                  wage_rate=float(post.db.post_wage_rate or 0.02),
                  venue=post if post.db.register is not None else None)
    from world.souls import thoughts as thoughts_mod
    thoughts_mod.add_thought(
        npc, "resleeved", -0.50,
        "woke in a new sleeve; the last hours before the dark are "
        "simply gone")
    post.db.post_keeper = npc
    post.db.post_vacant_since = None
    npc.execute_cmd("emote is back at the post, moving like the week "
                    "never happened.")
    return True


def snapshot_estate(character) -> bool:
    """At death, a post-holder's memories become the post's property
    (reincarnation spec §2): episodic memories, dossiers, and thoughts
    copied onto the post fixture BEFORE the corpse machinery deletes
    the body. Taken for EVERY keeper regardless of policy — the estate
    is kept even if nobody ever pays to restore it (a successor never
    reads it; a resleave restores it minus the death gap; at worst it
    is archaeology)."""
    import time as _time

    from evennia.utils.dbserialize import deserialize

    post = next((p for p in get_posts()
                 if p.db.post_keeper == character), None)
    if post is None:
        return False
    post.db.post_memory_snapshot = {
        "name": character.key,
        "died_at": _time.time(),
        "memories": deserialize(character.db.llm_memories) or [],
        "dossiers": deserialize(character.db.llm_dossiers) or {},
        "thoughts": deserialize(character.db.soul_thoughts) or [],
    }
    return True


def sweep(now=None):
    """One vacancy pass: stamp newly-vacant posts; run succession on
    posts whose grace has elapsed. One succession per sweep (the
    reincarnation spec's de-confliction rule)."""
    from world.director.security import _in_combat

    now = now if now is not None else time.time()
    for post in get_posts():
        keeper = post.db.post_keeper
        vacant_since = post.db.post_vacant_since
        if _keeper_holds(post, keeper):
            if vacant_since is not None:
                post.db.post_vacant_since = None    # re-manned
            continue
        if vacant_since is None:
            post.db.post_vacant_since = now         # newly dark
            continue
        if now - float(vacant_since) < int(post.db.post_delay
                                           or DEFAULT_DELAY):
            continue
        room = _post_room(post)
        if any(_in_combat(o) for o in room.contents
               if hasattr(o, "ndb")):
            continue                                # never over a fight
        policy = post.db.post_policy
        if policy == "resleave":
            if _try_resleave(post, room, now):
                return                              # one per sweep
            continue        # can't afford yet: the till keeps earning
        if policy != "successor":
            continue
        candidates = _eligible_candidates(room)
        if not candidates:
            continue                                # vacancy is content
        _offer(candidates[0], post, room)
        return                                      # one per sweep


def _offer(soul, post, room):
    """Hand the claim job: walk there for real, then take the work.
    Goal is "claim", NOT "duty" — the shift-release logic clears duty
    jobs outside work hours, which ate every after-hours job offer
    (you take the job tonight; you start in the morning)."""
    soul.db.soul_job = {
        "goal": "claim", "band": 2, "at": 0,
        "steps": [
            {"do": "travel", "room": room.id},
            {"do": "claim", "post": post.id},
        ],
    }


def do_claim(soul, post):
    """The claim step's business: bind soul to post (jobs.py calls)."""
    from world.souls import thoughts

    room = _post_room(post)
    soul.db.soul_post = room
    soul.db.soul_role = post.db.post_role or "worker"
    soul.db.soul_schedule = post.db.post_schedule or "day"
    soul.db.soul_wage_rate = float(post.db.post_wage_rate or 0.02)
    # any till-bearer pays wages from itself (the check is "has a
    # register", not "is a shop" — the clinic's billing terminal is a
    # plain fixture with a till); till-less fixtures are treasury posts
    soul.db.soul_venue = post if post.db.register is not None else None
    post.db.post_keeper = soul
    post.db.post_vacant_since = None
    thoughts.add_thought(soul, "new_job", 0.30,
                         f"picked up the {soul.db.soul_role} work at "
                         f"{room.key}")
