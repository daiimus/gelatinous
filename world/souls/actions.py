"""The action library and the shallow planner.

Hybrid architecture (spec §2): the tree picks WHAT (a goal = reduce a
need); this module figures HOW — a backward chain of at most PLAN_DEPTH
actions whose preconditions are resolved against the soul's real state.
Every action executes through real commands in jobs.py; this module
only *selects*.

Disposition gates: an action lists the disposition flags that admit it
to a soul's library at all (spec §2 — lawful souls simply have no
`mug`). Phase 1 ships the lawful library; transgressive actions arrive
with the residents' faction/standing work (owner verdict #2).
"""

from world.spatial import get_xyz

PLAN_DEPTH = 4


def _advertisers(soul, need, radius=30):
    """Grid-scan for venues/objects advertising this need, scored by
    advertised value over distance. Returns [(score, obj), ...]."""
    from evennia.objects.models import ObjectDB

    origin = get_xyz(soul.location) if soul.location else None
    found = []
    for obj in ObjectDB.objects.filter(db_attributes__db_key="advertises"):
        ad = obj.db.advertises or {}
        value = ad.get(need)
        if not value:
            continue
        room = obj.location if obj.location is not None else obj
        pos = get_xyz(room) if room else None
        if origin and pos:
            dist = max(abs(origin[0] - pos[0]), abs(origin[1] - pos[1])) \
                + abs(origin[2] - pos[2])
            if dist > radius:
                continue
        else:
            dist = radius // 2
        found.append((value / (1.0 + dist), obj, room))
    found.sort(key=lambda t: -t[0])
    return found


def _edible_wares(counter):
    """[(proto_key, price)] for wares that can actually be EATEN — a
    counter advertising hunger can still stock drinks (Lin's tea), and
    the planner must not send a hungry soul home with a cup of tea."""
    from evennia.prototypes.prototypes import search_prototype

    wares = []
    for proto_key, price in (counter.db.prototype_inventory or {}).items():
        hits = search_prototype(proto_key)
        tags = (hits[0].get("tags") or []) if hits else []
        if any(len(t) >= 2 and t[0] == "eat" and t[1] == "delivery_method"
               for t in tags if isinstance(t, (tuple, list))):
            wares.append((proto_key, price))
    return wares


def plan_for(soul, goal_need):
    """Return a job dict for the winning goal, or None (-> fault).

    Plans are canonical short chains; each step is a verb executed for
    real by jobs.py. The planner checks preconditions HERE (cash,
    stock, home) so jobs fault rarely and legibly.
    """
    if goal_need == "hunger":
        for score, counter, room in _advertisers(soul, "hunger"):
            wares = _edible_wares(counter)
            if not wares:
                continue
            proto, price = min(wares, key=lambda kv: kv[1])
            if (soul.tokens or 0) < price:
                continue                       # broke: try cheaper advertiser
            return {"goal": "hunger", "steps": [
                {"do": "travel", "room": room.id},
                {"do": "buy", "counter": counter.id, "proto": proto,
                 "price": price},
                {"do": "eat"},
            ], "at": 0}
        return None                            # nothing affordable: fault

    if goal_need == "rest":
        home = soul.db.soul_home
        if not home:
            return None
        return {"goal": "rest", "steps": [
            {"do": "travel", "room": home.id},
            {"do": "sleep"},
        ], "at": 0}

    if goal_need == "social":
        post = soul.db.soul_post
        workplace = soul.db.soul_venue and soul.db.soul_venue.location
        for score, venue, room in _advertisers(soul, "social"):
            # work is not recreation: a soul's own post (or its venue's
            # room) never satisfies social — staff go OUT, so shift
            # boundaries stay legible and third places get traffic
            if room is not None and room in (post, workplace):
                continue
            return {"goal": "social", "steps": [
                {"do": "travel", "room": room.id},
                {"do": "linger", "beats": 4},
            ], "at": 0}
        return None

    if goal_need == "duty":
        post = soul.db.soul_post
        if not post:
            return None
        return {"goal": "duty", "steps": [
            {"do": "travel", "room": post.id},
            {"do": "work"},
        ], "at": 0}

    if goal_need == "safety":
        # flee: any exit away from the threat room; the real move verb
        return {"goal": "safety", "steps": [{"do": "flee"}], "at": 0}

    return None
