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

import time as _time

from world.spatial import get_xyz

PLAN_DEPTH = 4
AD_CACHE_TTL = 60.0            # advertiser registry changes ~never

_ad_cache = {"at": 0.0, "objs": []}
_edible_memo = {}              # proto_key -> bool (prototypes are static)


def _advertiser_objs():
    """All advertising objects, by indexed tag, cached in-process.
    Build scripts tag advertisers (`advertiser`/souls) when they set
    `db.advertises` — the attribute-key join this replaces is uncached
    and unindexed (hardening spec law #3)."""
    from evennia.utils.search import search_tag

    now = _time.time()
    if now - _ad_cache["at"] > AD_CACHE_TTL:
        _ad_cache["objs"] = [o for o in search_tag(
            "advertiser", category="souls") if o and o.pk]
        _ad_cache["at"] = now
    return _ad_cache["objs"]


def _advertisers(soul, need, radius=30):
    """Advertisers for this need, scored value/(1+distance)."""
    origin = get_xyz(soul.location) if soul.location else None
    found = []
    for obj in _advertiser_objs():
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


def _is_edible_proto(proto_key):
    """Memoized: prototypes are static registry entries."""
    if proto_key not in _edible_memo:
        from evennia.prototypes.prototypes import search_prototype
        hits = search_prototype(proto_key)
        tags = (hits[0].get("tags") or []) if hits else []
        _edible_memo[proto_key] = any(
            len(t) >= 2 and t[0] == "eat" and t[1] == "delivery_method"
            for t in tags if isinstance(t, (tuple, list)))
    return _edible_memo[proto_key]


def _edible_wares(counter):
    """[(proto_key, price)] for wares that can actually be EATEN — a
    counter advertising hunger can still stock drinks (Lin's tea), and
    the planner must not send a hungry soul home with a cup of tea."""
    return [(proto_key, price)
            for proto_key, price in (counter.db.prototype_inventory or {}).items()
            if _is_edible_proto(proto_key)]


def _find_mark(soul, min_tokens=3, radius=30):
    """The predator's eye (spec §3.5): the nearest NPC visibly worth
    robbing — souls AND the director's ambient civilians, whose fat
    100-500 token pockets were invisible to `get_souls()`-only
    iteration (reconciliation finding 2.1: predation looped among the
    destitute while the richest wallets in the game stood unmuggable).
    NPC-only by owner verdict (players are never marks in the pilot);
    robots and security carry nothing worth the shock baton."""
    from evennia.utils.search import search_tag

    from world.souls import engine
    from world.souls import needs as needs_mod

    origin = get_xyz(soul.location) if soul.location else None
    candidates = list(engine.get_souls())
    try:
        candidates += [c for c in search_tag("civilian", category="director")
                       if c]
    except Exception:  # noqa: BLE001 — no ambient layer, souls suffice
        pass
    best = None
    for mark in candidates:
        if mark == soul or not mark.pk or mark.location is None:
            continue
        if not mark.db.is_npc:
            continue
        if needs_mod.profile_name(mark) == "robot" \
                or mark.db.soul_role == "secunit" \
                or getattr(mark.db, "role", None) == "security":
            continue
        if int(getattr(mark, "tokens", 0) or 0) < min_tokens:
            continue
        pos = get_xyz(mark.location)
        dist = (max(abs(origin[0] - pos[0]), abs(origin[1] - pos[1]))
                if origin and pos else radius)
        if dist > radius:
            continue
        if best is None or dist < best[0]:
            best = (dist, mark)
    return best[1] if best else None


def plan_for(soul, goal_need):
    """Return a job dict for the winning goal, or None (-> fault).

    Plans are canonical short chains; each step is a verb executed for
    real by jobs.py. The planner checks preconditions HERE (cash,
    stock, home) so jobs fault rarely and legibly.
    """
    if goal_need == "hunger":
        for score, counter, room in _advertisers(soul, "hunger"):
            # regulars know the hours: a keeper-bound counter whose
            # keeper is off shift is shuttered — don't walk to it
            keeper = counter.db.post_keeper
            if keeper is not None and not (
                    keeper.pk and keeper.location == counter.location):
                continue
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
        # the desperate fallback (spec §2 disposition gates): a LAWLESS
        # soul that cannot afford to eat turns predator — grapple, lift
        # a cut of the mark's tokens, disengage. Lawful souls simply
        # fault here and stay hungry; that difference IS the gate.
        # MOOD makes the gate dynamic (P4b): a bright stretch keeps
        # hands honest one more day — and the resulting went_hungry
        # thoughts darken the mood that eventually opens the knife.
        # Misery is the mechanism, not a modifier.
        if soul.db.soul_lawless:
            from world.souls import thoughts as thoughts_mod
            if thoughts_mod.mood(soul) >= 0.25:
                return None        # not today; hunger will change that
            mark = _find_mark(soul)
            if mark is not None:
                return {"goal": "hunger", "steps": [
                    {"do": "travel", "room": mark.location.id},
                    {"do": "grapple", "mark": mark.id},
                    {"do": "rob", "mark": mark.id, "lifts": 2},
                    {"do": "disengage", "mark": mark.id},
                ], "at": 0}
        return None                            # nothing affordable: fault

    shape = None
    if goal_need not in ("duty", "safety"):
        from world.souls import needs as needs_mod
        shape = needs_mod.shape_of(soul, goal_need)

    if shape == "dwell_home" or goal_need == "rest":
        home = soul.db.soul_home
        if not home:
            return None
        return {"goal": goal_need, "steps": [
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

    if shape == "clinic":
        # the walking wounded self-deliver (spec §14 layer 1): travel to
        # a treatment advertiser and see the doctor. Billing happens in
        # the treat step — triage for the dying is free, healing costs.
        for score, fixture, room in _advertisers(soul, "treatment"):
            return {"goal": goal_need, "steps": [
                {"do": "travel", "room": room.id},
                {"do": "treat", "clinic": fixture.id},
            ], "at": 0}
        return None

    if shape == "dwell_venue":
        # generic dwell need (charge, maintenance, a recluse's line and
        # airwaves): occupy the best advertiser until the meter recovers
        # (spec §12); the FIXTURE authors its own dwell poses
        for score, venue, room in _advertisers(soul, goal_need):
            return {"goal": goal_need, "steps": [
                {"do": "travel", "room": room.id},
                {"do": "dwell", "need": goal_need, "fixture": venue.id},
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
