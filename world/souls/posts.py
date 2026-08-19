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
        if post.db.post_policy != "successor":
            continue
        if now - float(vacant_since) < int(post.db.post_delay
                                           or DEFAULT_DELAY):
            continue
        room = _post_room(post)
        if any(_in_combat(o) for o in room.contents
               if hasattr(o, "ndb")):
            continue                                # never over a fight
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
