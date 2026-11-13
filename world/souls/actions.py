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
from typing import Any, Optional

from world.souls import constants
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
        _reconcile_advertiser_tags(_ad_cache["objs"])
        _ad_cache["at"] = now
    return _ad_cache["objs"]


def _reconcile_advertiser_tags(tagged):
    """Adopt any advertiser that has the ATTRIBUTE but not the TAG.

    The tag is the index (hardening spec law 3: never an attribute-key
    query on a hot path) and nothing reconciled the two, so a fixture
    with `db.advertises` and no tag was SILENTLY INVISIBLE to the
    planner rather than merely slow to find. A purpose-built charging
    rack sat dead since the day it was built for exactly that reason —
    `scripts/builds/121_the_charging_rack.py` sets the attribute and is
    the one advertiser build that never calls `tags.add`, and the
    backfill migration ran before it (#2697).

    It survived because the loss is a LOCATION, not a behaviour: a
    second charge advertiser is reachable from every unit, so nothing
    faulted and no alarm sounded.

    An advertiser attribute without the tag is always a build error, so
    this adopts rather than merely warning — one attribute query per
    cache expiry, not per call, which is what keeps law 3 satisfied.
    """
    from evennia.objects.models import ObjectDB
    from evennia.utils import logger
    try:
        known = {o.id for o in tagged}
        strays = [o for o in ObjectDB.objects.filter(
            db_attributes__db_key="advertises").distinct()
            if o.pk and o.id not in known and o.db.advertises]
        for obj in strays:
            obj.tags.add("advertiser", category="souls")
            tagged.append(obj)
            logger.log_warn(
                f"advertiser tag missing on #{obj.id} {obj.key!r} "
                f"({dict(obj.db.advertises or {})}) — adopted. The build "
                f"that created it should tag it too.")
    except Exception:  # noqa: BLE001 — a broken sweep never blocks planning
        pass


def _advertisers(soul, need, radius=30, reachable=True):
    """Advertisers for this need, scored value/(1+distance), and
    filtered to the ones this soul can actually get to."""
    origin = get_xyz(soul.location) if soul.location else None
    found = []
    for obj in _advertiser_objs():
        ad = obj.db.advertises or {}
        value = ad.get(need)
        if not value:
            continue
        room = obj.location if obj.location is not None else obj
        # A STAFFED advertiser only offers what it offers while somebody
        # is standing their shift at it (#2261). Some work is a person's
        # to do: a repair bench that served an empty room would let a
        # machine fix itself by leaning on it, which deletes the job.
        # Off shift, the need simply has no plan — and that absence is
        # what a vacancy is supposed to feel like.
        if obj.db.advertise_staffed:
            try:
                from world.souls.posts import any_keeper_present
                if not any_keeper_present(obj):
                    continue
            except Exception:  # noqa: BLE001 — unreadable post = unstaffed
                continue
        if obj.db.advertise_scope == "room" and soul.location != room \
                and soul.db.soul_home != room:
            # a sealed biome serves only its resident (#2096): the
            # Rook's chair must not summon the colony to a room with
            # no door
            continue
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
    return _reachable_only(soul, found) if reachable else found


#: How many usable advertisers a caller ever needs. Callers take the
#: best that works, so pathfinding the whole list is waste -- this
#: bounds the cost to a handful of A* runs on the rare beat a soul
#: actually picks a new goal.
MAX_REACHABLE = 3


def _reachable_only(soul, scored):
    """Drop advertisers this soul has no route to.

    Scoring is `value / (1 + straight-line distance)` -- it never
    consults the route graph, so the winner could be behind a locked
    door, up a lift the soul may not ride, or in a sealed room. The
    MOVEMENT layer is careful about all of this: travel calls lifts,
    presses floor buttons and opens doors through real commands, and
    the pathfinder already filters on `access(traverser, "traverse")`
    and `door_blocks`. SELECTION was the half that never asked (#2316).

    Live consequence before this: the Community Thrift's free rail
    advertised the best clothing in the colony from behind a padlocked
    roll-shutter, and every soul who needed clothes planned a trip to
    it, failed to path, faulted, and tried again on the next think.

    Asked with the soul as traverser, so it is THEIR reachability -- a
    door they cannot open and a gap only a roof-runner would cross are
    both answered for the individual, not in general.
    """
    if not scored:
        return scored
    here = getattr(soul, "location", None)
    if here is None:
        return scored
    from world.spatial.pathfind import find_path
    out = []
    for entry in scored:
        room = entry[2]
        if room is here:
            out.append(entry)                 # already standing in it
        else:
            try:
                if find_path(here, room, traverser=soul):
                    out.append(entry)
            except Exception:  # noqa: BLE001 — an unroutable question
                pass            # is a no, and never breaks planning
        if len(out) >= MAX_REACHABLE:
            break
    return out


def _counter_open(counter):
    """Will this counter actually serve? One question, asked the same
    way the shop itself asks it (souls.posts.any_keeper_present), so
    the planner and the till can never disagree about whether a place
    is open."""
    from world.souls.posts import is_bound
    if not is_bound(counter):
        return True                    # no binding: the vending tier
    if counter.db.self_serve:
        return True
    from world.souls.posts import any_keeper_present
    return any_keeper_present(counter)


def _is_edible_proto(proto_key):
    """Memoized: prototypes are static registry entries.

    Edible = the eat verb works AND the food nourishes (#2074: hunger
    is pharmacology — drink_effects carries a nutrition dose). The tag
    alone admitted chewing tobacco, which is eatable but not food."""
    if proto_key not in _edible_memo:
        from evennia.prototypes.prototypes import search_prototype
        hits = search_prototype(proto_key)
        tags = (hits[0].get("tags") or []) if hits else []
        eatable = any(
            len(t) >= 2 and t[0] == "eat" and t[1] == "delivery_method"
            for t in tags if isinstance(t, (tuple, list)))
        attrs = (hits[0].get("attrs") or []) if hits else []
        effects = next((a[1] for a in attrs
                        if isinstance(a, (tuple, list)) and a
                        and a[0] == "drink_effects"), None)
        _edible_memo[proto_key] = bool(
            eatable and (effects or {}).get("nutrition"))
    return _edible_memo[proto_key]


def _in_stock(counter, proto_key):
    """Limited shops sell only what was actually stocked (the butcher
    COOKS her inventory; nothing spawns from thin air) — the planner
    must not walk a hungry soul to an empty shelf (#2090). Infinite
    shops (the default) always pass."""
    if getattr(counter.db, "is_infinite", True) is not False:
        return True
    return int((counter.db.item_inventory or {}).get(proto_key, 0) or 0) > 0


def _edible_wares(counter):
    """[(proto_key, price)] for wares that can actually be EATEN — a
    counter advertising hunger can still stock drinks (Lin's tea), and
    the planner must not send a hungry soul home with a cup of tea —
    and that are actually IN STOCK (#2090)."""
    return [(proto_key, price)
            for proto_key, price in (counter.db.prototype_inventory or {}).items()
            if _is_edible_proto(proto_key) and _in_stock(counter, proto_key)]


def _board_of(fixture):
    """The MENU a tender serves off this fixture, [] if it has none.

    A board is what separates a place that serves you from a place that
    sells to you. Shops have a shelf (`prototype_inventory`); bars and
    restaurants have this."""
    return list(getattr(fixture.db, "menu", None) or [])


def _order_word(entry):
    """The single word a soul says to ask for a board entry."""
    keywords = entry.get("order_keywords") or (entry.get("name", ""),)
    return next((k for k in keywords if k), entry.get("name", ""))


def _board_food(fixture):
    """[(entry, price)] for board entries that actually NOURISH.

    Asked of the plated prototype where there is one — the same question
    `_edible_wares` asks of a shelf, so a dish cannot be food on the
    board and not food in the hand — else of the recipe's own dose. A
    bar's drinks and its free snacks both fail this, which is why a
    hungry soul walks past a counter that only pours."""
    out = []
    for entry in _board_of(fixture):
        proto = entry.get("proto")
        nourishes = (_is_edible_proto(proto) if proto
                     else bool((entry.get("effects") or {}).get("nutrition")))
        if nourishes:
            out.append((entry, int(entry.get("price", 0) or 0)))
    return out


def _board_vice(fixture, craved):
    """[((entry, verb), price)] for board entries carrying the craved
    substance. A plated dish answers through the prototype registry; a
    mixed drink carries its dose inline, on the recipe."""
    out = []
    for entry in _board_of(fixture):
        proto = entry.get("proto")
        if proto:
            verb, subs = _vice_info(proto)
        else:
            verb, subs = "drink", frozenset(entry.get("effects") or {})
        if verb and _sub_matches(subs, craved):
            out.append(((entry, verb), int(entry.get("price", 0) or 0)))
    return out


def _pick_ware(soul, pairs):
    """Which of these a soul reaches for, or None if none is affordable.

    The cheapest thing that does the job, unless an Open-Valve price
    ceiling says otherwise — that soul buys the best they can afford
    rather than the least they can get away with. Shared by every door
    so the shelf, the board and the cart all read a wallet the same
    way; it used to be written out once per door, which is exactly how
    doors drift apart."""
    purse = int(soul.tokens or 0)
    affordable = [pair for pair in pairs if pair[1] <= purse]
    if not affordable:
        return None
    from world.souls import traits as traits_mod
    if traits_mod.dial(soul, "price_ceiling", 1.0) > 1.0:
        return max(affordable, key=lambda pair: pair[1])
    return min(affordable, key=lambda pair: pair[1])


def _tender_for(soul, fixture):
    """The tender a soul could order from here, or None. Wraps the shared
    reading so the planner and the `order` command agree about who is
    working — and refuses a tender the soul cannot see, because you
    cannot order from someone you have no idea is there."""
    from world.bar import tender_at
    tender = tender_at(fixture)
    if tender is None:
        return None
    if tender is soul:
        # YOU CANNOT BE SERVED BY YOURSELF. `at_msg_receive` drops a
        # message whose speaker is the receiver, so a keeper ordering at
        # their own post spoke into the void, waited, and faulted —
        # Sable ordering at the Helix while tending the Helix (#2364).
        # Falling through sends her somewhere she can actually be served.
        # A keeper's own MEAL does not come through here: `_feed_at`
        # asks `_works` first and has them prepare it (#3802).
        return None
    try:
        from world.perception import can_perceive
        if not can_perceive(soul, tender):
            return None
    except Exception:  # noqa: BLE001 — perception is a filter, not a gate
        pass
    return tender


def _works(soul, fixture) -> bool:
    """Is this soul the one working this counter right now?

    The other half of `_tender_for`'s "you cannot be served by
    yourself": the keeper is the one person who does not need serving.
    Asked the way the counter asks it, so the planner and the `prepare`
    command cannot disagree about who is behind it."""
    from world.bar import tender_at
    if tender_at(fixture) is not soul:
        return False
    is_bartender = getattr(fixture, "is_bartender", None)
    return bool(callable(is_bartender) and is_bartender(soul))


_vice_memo = {}                # proto_key -> (verb or None, substances)


def _vice_info(proto_key):
    """(consume_verb, frozenset of substance ids) for a ware (#2076).

    Memoized like the edible check. Verb preference drink > eat;
    smoke-only wares return verb None — lighting is a real dependency
    a v1 addict doesn't manage (same limitations as players: no
    lighter, no smoke)."""
    if proto_key not in _vice_memo:
        from evennia.prototypes.prototypes import search_prototype
        hits = search_prototype(proto_key)
        tags = (hits[0].get("tags") or []) if hits else []
        deliveries = {t[0] for t in tags
                      if isinstance(t, (tuple, list)) and len(t) >= 2
                      and t[1] == "delivery_method"}
        attrs = (hits[0].get("attrs") or []) if hits else []
        effects = next((a[1] for a in attrs
                        if isinstance(a, (tuple, list)) and a
                        and a[0] == "drink_effects"), None) or {}
        subs = set(effects)
        single = next((a[1] for a in attrs
                       if isinstance(a, (tuple, list)) and a
                       and a[0] == "substance"), None)
        if single:
            subs.add(single)
        verb = ("drink" if "drink" in deliveries
                else "eat" if "eat" in deliveries else None)
        _vice_memo[proto_key] = (verb, frozenset(subs))
    return _vice_memo[proto_key]


def _sub_matches(subs, craved):
    """Exact substance match, widened to the tobacco family — the
    addiction is to the leaf, not the brand."""
    if craved in subs:
        return True
    return craved.startswith("tobacco") and any(
        s.startswith("tobacco") for s in subs)


def _carried_doses(obj: Any) -> dict:
    """{substance: doses} a carried ware delivers, read the way the
    consumption commands read it: a recipe or a dish carries a
    `db.drink_effects` map (possibly empty), anything else names one
    `db.substance`."""
    effects = obj.db.drink_effects
    if effects is not None:
        return dict(effects)
    return {obj.db.substance: 1} if obj.db.substance else {}


def _carried_food(soul: Any) -> Optional[Any]:
    """Something already in the soul's pockets that is FOOD, or None.

    The same test a shelf ware has to pass (`_is_edible_proto`): the eat
    verb works AND it nourishes. The tag alone admits chewing tobacco,
    which is eatable but not food, and a meal is one ware: a soul that
    sat down to a plug would chew it, fault that it did not nourish, and
    leave the stew beside it uneaten.

    A RATION is not this. It is the one food allowed to wait in a
    pocket (`_carried_rations`), and counting it here would have every
    soul eat its ration at the first pang and never reach a kitchen
    again. Everything else carried is still eaten before anything is
    bought, which is the rule that ended the hoard (#3793).
    """
    from world.consumables import supports_delivery
    for obj in soul.contents:
        if (supports_delivery(obj, "eat")
                and _carried_doses(obj).get("nutrition")
                and not _is_ration(obj)):
            return obj
    return None


def _is_ration(obj: Any) -> bool:
    """Does this food KEEP: may it wait in a pocket (#3804)?"""
    key, category = constants.RATION_TAG
    return bool(obj.tags.has(key, category=category))


def _carried_rations(soul: Any) -> list:
    """The rations in a soul's pockets that would actually feed it."""
    from world.consumables import supports_delivery
    return [obj for obj in soul.contents
            if _is_ration(obj) and supports_delivery(obj, "eat")
            and _carried_doses(obj).get("nutrition")]


def food_quality(obj: Any) -> float:
    """How good this food is, as a number (#3804). A food that declares
    none is ordinary (`constants.FOOD_QUALITY_DEFAULT`)."""
    return _as_quality(obj.attributes.get(constants.FOOD_QUALITY_ATTR))


def _as_quality(value: Any) -> float:
    """A declared quality as a number, or the default if it is not one."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return constants.FOOD_QUALITY_DEFAULT


_proto_food_memo = {}          # proto_key -> (quality or None, is ration)


def _proto_food(proto_key: Any) -> tuple:
    """(declared quality or None, is a ration) for a prototype.

    Memoized like `_is_edible_proto`: prototypes are static registry
    entries. Read off the prototype because the planner has to weigh a
    dish before anybody has made it."""
    if proto_key not in _proto_food_memo:
        from evennia.prototypes.prototypes import search_prototype
        hits = search_prototype(proto_key) if proto_key else []
        attrs = (hits[0].get("attrs") or []) if hits else []
        tags = (hits[0].get("tags") or []) if hits else []
        quality = next((a[1] for a in attrs
                        if isinstance(a, (tuple, list)) and len(a) >= 2
                        and a[0] == constants.FOOD_QUALITY_ATTR), None)
        key, category = constants.RATION_TAG
        ration = any(len(t) >= 2 and t[0] == key and t[1] == category
                     for t in tags if isinstance(t, (tuple, list)))
        _proto_food_memo[proto_key] = (quality, ration)
    return _proto_food_memo[proto_key]


def _meal_quality(fixture: Any, steps: list) -> float:
    """The quality of the food a feeding plan would end in.

    Read off the PROTOTYPE, because that is what the eater will hold:
    a shelf plan names it, and a board plan names an entry that is
    plated from one. An entry mixed on the spot, and a serving
    fixture's snack, have no prototype and are ordinary. The number is
    deliberately not taken from the board entry itself: nothing would
    carry it onto the dish, and the walk would be weighed on one
    figure and the meal felt on another."""
    for step in steps or []:
        if step.get("proto"):
            return _as_quality(_proto_food(step["proto"])[0])
        want = step.get("want")
        if want:
            entry = next((e for e in _board_of(fixture)
                          if e.get("name") == want), None)
            if entry is not None and entry.get("proto"):
                return _as_quality(_proto_food(entry["proto"])[0])
            return constants.FOOD_QUALITY_DEFAULT
    return constants.FOOD_QUALITY_DEFAULT


def _ration_beats(soul: Any, ration: Any, fixture: Any, room: Any,
                  steps: list) -> bool:
    """Is the ration in the pocket worth more than this meal after the
    walk to it?

    A meal is worth its quality less a little for every room on the
    way; the ration has no way to go. So there is no "far": the
    distance at which a soul stops walking moves with what is at the
    end of it and with what it is carrying, and closes in by itself as
    kitchens are built nearer (#3804). The route is the real one, the
    same the feet will take. A tie goes to the pocket."""
    from world.spatial.pathfind import path_length
    here = getattr(soul, "location", None)
    rooms = 0 if (here is None or room is here) else path_length(
        here, room, traverser=soul)
    if rooms is None:
        return True                  # no way there after all
    worth = (_meal_quality(fixture, steps)
             - constants.FOOD_WALK_COST_PER_ROOM * rooms)
    return food_quality(ration) >= worth


def _ration_wares(counter: Any) -> list:
    """[(proto_key, price)] for the rations a shelf has in stock."""
    return [(proto_key, price)
            for proto_key, price in (counter.db.prototype_inventory or {}).items()
            if _proto_food(proto_key)[1] and _is_edible_proto(proto_key)
            and _in_stock(counter, proto_key)]


def _purse(soul: Any) -> int:
    """What a soul can spend. `tokens` is a property of the game's
    Character, not an Attribute; a body without one has an empty purse,
    as the till reads it."""
    return int(getattr(soul, "tokens", 0) or 0)


def _ration_on_offer(soul: Any, fixture: Any) -> Optional[tuple]:
    """(proto_key, price) for the ration this soul would take from this
    shelf, the cheapest it can pay for, or None: shut, out, or dear."""
    if not _counter_open(fixture):
        return None
    purse = _purse(soul)
    within = [pair for pair in _ration_wares(fixture) if pair[1] <= purse]
    return min(within, key=lambda pair: pair[1]) if within else None


def _ration_source(soul: Any) -> Optional[tuple]:
    """(fixture, room, proto_key, price) for the ration this soul would
    go and buy, or None. ONE reading, for the offer and for the plan:
    a source the soul has a real route to (`_advertisers` asks the
    pathfinder), that is open, with a ration it can pay for."""
    for _score, fixture, room in _advertisers(soul, constants.RATION_ADVERT):
        pick = _ration_on_offer(soul, fixture)
        if pick is not None:
            return fixture, room, pick[0], pick[1]
    return None


def wants_ration(soul: Any) -> bool:
    """Should this soul go and put a ration in its pocket, NOW?

    Only a body that eats bought food, only on a quiet beat, only while
    it carries fewer than it may, and only when there is one to be had:
    a source in range, open, within its purse, and with a real route to
    it. All of that is asked HERE, not left for the plan to fail on. A
    goal offered where it cannot be planned faults, cools for fifteen
    minutes and is offered again, for ever, and a machine behind a door
    a soul cannot open is exactly such a place (#2316 was the same loop
    for clothes).

    A QUIET BEAT means no job running. The band tree is consulted on
    every think, a job in hand or not, but an idle errand never
    replaces a job, so asking a busy soul only produced an answer for
    wherever its job had walked it to, to be spent somewhere else. An
    idle soul is planned for in the same think it is asked in, from the
    room it is standing in, and the offer and the plan ask one function
    (`_ration_source`), so they cannot disagree.

    Asked on every idle think of every soul, so in order of cost. The
    straight-line pass is arithmetic and ends it for anybody out of
    range, which today is everybody. Only then the route, which is a
    pathfind. A NO is remembered, for this room, for
    `RATION_ROUTE_RECHECK_SECONDS`; a yes is never remembered, because
    a yes is acted on at once."""
    from world.souls import needs as needs_mod
    if soul.db.soul_job:
        return False
    if "hunger" not in needs_mod.profile_of(soul) \
            or needs_mod.shape_of(soul, "hunger") != "buy_consume":
        return False
    if len(_carried_rations(soul)) >= constants.RATION_CARRY_MAX:
        return False
    if not any(_ration_on_offer(soul, fixture) is not None
               for _score, fixture, _room in _advertisers(
                   soul, constants.RATION_ADVERT, reachable=False)):
        return False
    if _no_ration_route_from_here(soul):
        return False
    if _ration_source(soul) is None:
        _remember_no_ration_route(soul)
        return False
    return True


def _room_id(soul: Any) -> Optional[int]:
    room = getattr(soul, "location", None)
    return room.id if room is not None else None


def _no_ration_route_from_here(soul: Any) -> bool:
    """Was this soul told, lately and in this room, that it has no
    route to a ration?"""
    told = soul.ndb.ration_no_route or {}       # {room id: good until}
    return told.get(_room_id(soul), 0.0) > _time.time()


def _remember_no_ration_route(soul: Any) -> None:
    """Do not ask the pathfinder again from this room for a while.

    One entry a room, not one for the soul: a soul on a beat stands
    idle at every stop of it, and a single remembered room was
    overwritten at each, so it paid for the pathfind again at every
    stop for as long as the door stayed shut. Stale rooms are dropped
    on each write, which bounds it by the rooms one soul can stand
    idle in inside the recheck time."""
    now = _time.time()
    told = {room: until
            for room, until in (soul.ndb.ration_no_route or {}).items()
            if until > now}
    told[_room_id(soul)] = now + constants.RATION_ROUTE_RECHECK_SECONDS
    soul.ndb.ration_no_route = told


def _carried_vice(soul: Any, craved: str) -> Optional[tuple]:
    """(ware, verb) for something already in the soul's pockets that
    answers this craving, or None.

    Verb preference drink > eat and no smoking, as for a ware on a shelf
    (`_vice_info`).
    """
    from world.consumables import supports_delivery
    for verb in ("drink", "eat"):
        for obj in soul.contents:
            if (supports_delivery(obj, verb)
                    and _sub_matches(set(_carried_doses(obj)), craved)):
                return obj, verb
    return None


_wear_memo = {}                # proto_key -> frozenset coverage or None


def _proto_coverage(proto_key):
    """What this ware would cover, or None if it isn't clothing.
    Memoized; a garment needs BOTH coverage and a worn_desc, the same
    pair is_wearable() demands of a real object (#2104)."""
    if proto_key not in _wear_memo:
        from evennia.prototypes.prototypes import search_prototype
        hits = search_prototype(proto_key)
        attrs = (hits[0].get("attrs") or []) if hits else []
        got = {a[0]: a[1] for a in attrs
               if isinstance(a, (tuple, list)) and len(a) >= 2}
        cov = got.get("coverage")
        _wear_memo[proto_key] = (frozenset(cov)
                                 if cov and got.get("worn_desc") else None)
    return _wear_memo[proto_key]


def _is_wearable_proto(proto_key):
    return _proto_coverage(proto_key) is not None


_style_memo = {}


def _proto_affinity(proto_key, soul):
    """How much this ware reads as this soul (world.style)."""
    from world import style as style_mod

    if proto_key not in _style_memo:
        from evennia.prototypes.prototypes import search_prototype
        hits = search_prototype(proto_key)
        proto = hits[0] if hits else {}
        attrs = {a[0]: a[1] for a in (proto.get("attrs") or ())
                 if isinstance(a, (tuple, list)) and len(a) >= 2}
        _style_memo[proto_key] = (
            tuple(attrs.get("style")
                  or style_mod.derive_style(proto.get("key", ""),
                                            attrs.get("desc", ""))),
            tuple(attrs.get("presentation")
                  or style_mod.derive_presentation(proto.get("key", ""))),
        )
    styles, pres = _style_memo[proto_key]
    return (style_mod.affinity(styles, style_mod.style_of_character(soul))
            + style_mod.presentation_affinity(
                pres, style_mod.presentation_of_character(soul)))


_prov_memo = {}


def _is_provisional_proto(proto_key):
    """Issue clothing — the paper a sleeve wakes up in."""
    if proto_key not in _prov_memo:
        from evennia.prototypes.prototypes import search_prototype
        hits = search_prototype(proto_key)
        attrs = (hits[0].get("attrs") or []) if hits else []
        got = {a[0]: a[1] for a in attrs
               if isinstance(a, (tuple, list)) and len(a) >= 2}
        _prov_memo[proto_key] = bool(got.get("provisional"))
    return _prov_memo[proto_key]


def _uncovered(soul):
    """The modesty parts this soul still needs covered."""
    from world.souls import needs as needs_mod
    covered = getattr(soul, "is_location_covered", None)
    if not callable(covered):
        return set()
    return {part for part in needs_mod.modesty_of(soul) if not covered(part)}


def _wearable(soul, obj):
    """Carried, wearable by the clothing system's own reckoning, and
    not already on. `is_wearable` wants coverage AND a worn_desc — an
    item with coverage alone can never be worn, and a planner that
    ignored that would loop on it forever."""
    check = getattr(obj, "is_wearable", None)
    if not callable(check) or not check():
        return False
    if soul.is_item_worn(obj):
        return False
    # ...and it has to actually GO ON. A layer-0 garment cannot be put
    # on over what is already worn, so picking one meant issuing a
    # command that could only ever be refused (#2337). The rule lives
    # in clothing_mixin; this asks rather than re-deriving it.
    ask = getattr(soul, "can_wear_now", None)
    if callable(ask):
        try:
            return bool(ask(obj))
        except Exception:  # noqa: BLE001 — unanswerable means don't pick it
            return False
    return True


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


def _under_duress(soul, need):
    """Is this need desperate enough to override a soul's nature?

    The conscience rule (NPC_TRAITS_SPEC §4): a plan a soul abhors is
    only reachable at CRITICAL, never at merely soft. A gentle soul
    who is hungry goes to bed hungry; the same soul starving finally
    pulls the knife — and the gap between those thresholds IS the
    personality.
    """
    from world.souls import needs as needs_mod
    return needs_mod.pressure(soul, need) >= needs_mod.critical_for(soul, need)


def _permits(soul, need, tags):
    """May this soul take a plan carrying `tags` right now?"""
    from world.souls import traits as traits_mod
    if not traits_mod.abhors(soul, tags):
        return True
    return _under_duress(soul, need)


#: Where a recovered unit is taken. Tag-driven so a builder can move
#: the precinct without editing code; falls back to the soul's own
#: post, which for a unit is where it charges anyway.
RECOVERY_TAG = ("recovery_bay", "security")


def _obj_by_id(dbid):
    """Indexed fetch, matching jobs.py's `_obj`."""
    if not dbid:
        return None
    from evennia.objects.models import ObjectDB
    obj = ObjectDB.objects.get_id(dbid)
    return obj if obj and obj.pk else None


def recovery_bay(soul):
    """The room a recovered casualty is delivered to."""
    from evennia.utils.search import search_tag
    rooms = [r for r in search_tag(*RECOVERY_TAG) if r and r.pk]
    if rooms:
        return rooms[0]
    return soul.db.soul_post or soul.db.soul_home


def _feed_at(soul, fixture, shape):
    """The steps that would feed this soul AT THIS FIXTURE, or None.

    Three doors, and the VENUE decides which one opens: a tended board
    is ORDERED from, a serving fixture is GRAZED, a shelf is BOUGHT
    from. The one soul a tended board cannot serve is its own keeper,
    who PREPARES a dish instead (#3802). The door used to be chosen by the soul's species profile
    instead, which is how sixteen colonists could stand in a restaurant
    and starve — only a recluse knew how to be served, and only a shelf
    would sell to anybody (#2342).

    `shape` still narrows it: a recluse grazes and does nothing else.
    Their food is plumbed into the seal, and walking to a counter is the
    one thing their story doesn't allow.
    """
    if shape != "graze":
        board = _board_food(fixture)
        # Ask the SAME question the till asks — "is anyone's shift-holder
        # standing here" — so the planner and the counter can never
        # disagree about whether a place is open (#2142).
        if board and _counter_open(fixture):
            if _works(soul, fixture):
                # THE KEEPER EATS FROM THEIR OWN BOARD, ON THE HOUSE
                # (owner ruling 2026-11-13, #3802). `_tender_for` sends a
                # keeper elsewhere because nobody can serve them here;
                # for the keepers of the colony's one free kitchen there
                # was no elsewhere, and they stood behind the stew at
                # maximum hunger for hours of every shift. They do what
                # a player behind the counter does: `prepare` it, lift
                # it, eat it. Complimentary, so the purse is not asked;
                # the house staple, so the cheapest thing on the board.
                entry, _price = min(board, key=lambda pair: pair[1])
                return [
                    {"do": "prepare", "counter": fixture.id,
                     "word": _order_word(entry),
                     "want": entry.get("name", "")},
                    {"do": "pickup", "counter": fixture.id, "verb": "eat",
                     "want": entry.get("name", "")},
                    {"do": "eat"},
                ]
            tender = _tender_for(soul, fixture)
            pick = _pick_ware(soul, board) if tender is not None else None
            if pick is not None:
                entry, _price = pick
                return [
                    {"do": "order", "counter": fixture.id,
                     "tender": tender.id, "word": _order_word(entry),
                     "want": entry.get("name", "")},
                    {"do": "pickup", "counter": fixture.id, "verb": "eat",
                     "want": entry.get("name", "")},
                    {"do": "eat"},
                ]
    # sealed-biome feeding (spec §12 recluse, #2074): a serving fixture
    # (db.snacks with nutrition) eaten through the REAL eat verb — the
    # same membrane, gates and pharmacology a player in the room hits
    entry = next((s for s in (fixture.db.snacks or [])
                  if (s.get("effects") or {}).get("nutrition")), None)
    if entry is not None:
        return [{"do": "graze", "fixture": fixture.id,
                 "word": _order_word(entry)}]
    if shape == "graze":
        return None
    if not _counter_open(fixture):
        return None      # regulars know the hours: a shuttered counter
                         # isn't worth the walk
    pick = _pick_ware(soul, _edible_wares(fixture))
    if pick is None:
        return None
    proto, price = pick
    return [
        {"do": "buy", "counter": fixture.id, "proto": proto, "price": price},
        {"do": "eat"},
    ]


def _indulge_at(soul, fixture, craved):
    """The steps that would answer this craving AT THIS FIXTURE, or None.

    The same two doors as food, chosen the same way. A bar is where a
    drink comes from, and until now the addicts of this colony could
    only buy bottles off a shop shelf — nobody could pour them one."""
    board = _board_vice(fixture, craved)
    if board and _counter_open(fixture):
        tender = _tender_for(soul, fixture)
        pick = _pick_ware(soul, board) if tender is not None else None
        if pick is not None:
            (entry, verb), _price = pick
            return [
                {"do": "order", "counter": fixture.id, "tender": tender.id,
                 "word": _order_word(entry), "want": entry.get("name", "")},
                {"do": "pickup", "counter": fixture.id, "verb": verb,
                 "want": entry.get("name", "")},
                {"do": "consume", "verb": verb},
            ]
    if not _counter_open(fixture):
        return None                        # shuttered: cravings wait
    wares = [((proto_key, verb), price)
             for proto_key, price
             in (fixture.db.prototype_inventory or {}).items()
             for verb, subs in (_vice_info(proto_key),)
             if verb and _sub_matches(subs, craved)
             and _in_stock(fixture, proto_key)]
    pick = _pick_ware(soul, wares)
    if pick is None:
        return None
    (proto, verb), price = pick
    return [
        {"do": "buy", "counter": fixture.id, "proto": proto, "price": price},
        {"do": "consume", "verb": verb},
    ]


def _patrol_plan(soul):
    """Walk the next stop on this soul's beat, then work the waypoint.

    The route, the stagger and the waypoint behaviour all stay in the
    director — it owns what a beat IS and what happens at a stop. Souls
    owns the feet. That split is the whole point: one driver, and the
    director demoted to a source of work (#2373)."""
    from world.director.routines import cadence_taken, next_waypoint
    waypoint, _idx = next_waypoint(soul)
    if waypoint is None:
        return None
    # The plan is being ADOPTED — this is the beat the patrol is
    # actually spent on, and the only correct moment to consume the
    # cadence (#2804).
    cadence_taken(soul)
    if soul.location == waypoint:
        return {"goal": "patrol", "at": 0,
                "steps": [{"do": "patrol_mark"}]}
    return {"goal": "patrol", "at": 0, "steps": [
        {"do": "travel", "room": waypoint.id},
        {"do": "patrol_mark"},
    ]}


def _hunt_plan(soul):
    """One beat of the hunt.

    Deliberately a SINGLE step rather than a chain: `tick_hunt` is
    already a state machine holding its own progress on `ndb.hunt` (the
    target, the sweep budget, the rooms already swept). A multi-step
    plan would be a second place tracking the same thing, and the two
    would drift. Souls supplies the beat; the director keeps every rule
    about what a hunt IS — the same split patrol got (#2373)."""
    return {"goal": "hunt", "at": 0, "steps": [{"do": "hunt"}]}


def plan_for(soul, goal_need):
    """Return a job dict for the winning goal, or None (-> fault).

    Plans are canonical short chains; each step is a verb executed for
    real by jobs.py. The planner checks preconditions HERE (cash,
    stock, home) so jobs fault rarely and legibly.
    """
    if goal_need == "run":
        # A courier run: cross the city, hand it over, come home. The
        # package is spawned by the work handler before the job starts,
        # so a run that faults leaves her holding it -- which reads
        # correctly and gets handed over on the next attempt (#2258).
        dest = _obj_by_id(soul.db.soul_run_to)
        counter = _obj_by_id(soul.db.soul_run_counter)
        clerk = _obj_by_id(soul.db.soul_run_clerk)
        post = soul.db.soul_post
        home = post if getattr(post, "contents", None) is not None \
            else getattr(post, "location", None)
        if dest is None or counter is None or clerk is None or home is None:
            return None
        return {"goal": "run", "at": 0, "steps": [
            {"do": "collect", "clerk": clerk.id},
            {"do": "travel", "room": dest.id},
            {"do": "handoff", "counter": counter.id},
            {"do": "travel", "room": home.id},
        ]}

    if goal_need == "recover":
        # The force recovers its own (owner ruling 2026-08-24). A
        # second unit leaves its patrol, takes hold of the casualty and
        # drags it home -- so a downed unit visibly thins the streets
        # while it happens, which is the cost that makes it matter.
        #
        # Dragging is emergent: hold it, then walk. There is no drag
        # command and there should not be one.
        wreck = _obj_by_id(soul.db.soul_recovering)
        if wreck is None or not wreck.pk:
            return None
        bay = recovery_bay(soul)
        if bay is None:
            return None
        return {"goal": "recover", "at": 0, "steps": [
            {"do": "hold", "wreck": wreck.id},
            {"do": "travel", "room": bay.id},
            {"do": "deliver", "wreck": wreck.id},
        ]}

    if goal_need == "patrol":
        return _patrol_plan(soul)

    if goal_need == "comms":
        # Ready the carried handheld (#3777). A single step that re-asks
        # the one predicate each beat and issues one real command --
        # `wield`, then `toggle ... on` -- until it answers None; the
        # verb faults legibly ("hands full", "no band") rather than
        # this planner guessing at them.
        from world.souls.comms import radio_to_ready
        if radio_to_ready(soul) is None:
            return None
        return {"goal": "comms", "at": 0, "steps": [{"do": "ready_radio"}]}

    if goal_need == "hunt":
        return _hunt_plan(soul)

    if goal_need == "hunger":
        from world.souls import needs as needs_mod
        # CHECK YOUR POCKETS FIRST. Somebody who is already carrying
        # food eats that before walking across the colony to buy more —
        # the saved chocolate bar, last night's leftovers, the bowl they
        # didn't finish. Obvious for a person, and it was missing, which
        # is how souls came to carry thirty-odd bowls of the same stew:
        # every hunger pang planned a fresh purchase and nothing ever
        # looked in a pocket (#2244).
        food = _carried_food(soul)
        if food is not None:
            return {"goal": "hunger", "at": 0,
                    "steps": [{"do": "eat", "item": food.id}]}
        shape = needs_mod.shape_of(soul, "hunger")
        # THE RATION WAITS (#3804). It was passed over just above so a
        # soul still walks to a kitchen; here it is weighed against the
        # one meal that soul would otherwise walk to, and eaten when the
        # walk is not worth it or there is nowhere to walk.
        ration = next(iter(_carried_rations(soul)), None)
        for score, fixture, room in _advertisers(soul, "hunger"):
            steps = _feed_at(soul, fixture, shape)
            if steps:
                if ration is not None and _ration_beats(
                        soul, ration, fixture, room, steps):
                    break
                return {"goal": "hunger", "at": 0, "steps":
                        [{"do": "travel", "room": room.id}] + steps}
        if ration is not None:
            return {"goal": "hunger", "at": 0,
                    "steps": [{"do": "eat", "item": ration.id}]}
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
            from world.souls import traits as traits_mod
            gate = traits_mod.dial(soul, "violence_gate", 0.25)
            if thoughts_mod.mood(soul) >= gate:
                return None        # not today; hunger will change that
            if not _permits(soul, "hunger", ("violence", "theft")):
                return None        # not while there's any other way
            mark = _find_mark(soul)
            if mark is not None:
                return {"goal": "hunger", "ethos": ("violence", "theft"),
                        "steps": [
                    {"do": "travel", "room": mark.location.id},
                    {"do": "grapple", "mark": mark.id},
                    {"do": "rob", "mark": mark.id, "lifts": 2},
                    {"do": "disengage", "mark": mark.id},
                ], "at": 0}
        try:
            from world import wsis
            wsis.emit("went_hungry", soul.location, note=soul.key)
        except Exception:  # noqa: BLE001
            pass
        return None                            # nothing affordable: fault

    if goal_need == "craving":
        # the vice run (#2076): buy the cheapest ware carrying the
        # craved substance and consume it through the real verb. The
        # dose resets the addiction clock inside apply_substance —
        # the engine never satisfies craving directly (#2074 law).
        from world.souls import needs as needs_mod
        _p, craved = needs_mod.craving_state(soul)
        craved = craved or "alcohol"   # pre-habit misery reaches for drink
        if not _permits(soul, "craving", ("indulgence",)):
            return None                # they know what it costs
        # CHECK YOUR POCKETS FIRST, as hunger does above. The meal got
        # this in #2244 and the vice run did not, so every craving
        # planned a fresh purchase past the undrunk mug already in the
        # coat (#3793).
        carried = _carried_vice(soul, craved)
        if carried:
            ware, verb = carried
            return {"goal": "craving", "at": 0, "steps": [
                {"do": "consume", "verb": verb, "item": ware.id}]}
        for score, fixture, room in _advertisers(soul, "vice"):
            steps = _indulge_at(soul, fixture, craved)
            if steps:
                return {"goal": "craving", "at": 0, "steps":
                        [{"do": "travel", "room": room.id}] + steps}
        # a broke addict with lawless hands robs for the fix — the same
        # knife, mark, and mood gate as hunger (misery is the mechanism)
        if soul.db.soul_lawless:
            from world.souls import thoughts as thoughts_mod
            from world.souls import traits as traits_mod
            # READ THE DIAL, as the hunger gate above does. This
            # hardcoded 0.25 -- the dial's DEFAULT -- under a comment
            # claiming "the same ... mood gate as hunger". The tell was
            # that this branch did not import `traits_mod` at all: the
            # dial was not dropped mid-expression, it was never
            # consulted here (#2704).
            #
            # Live, 5 of 80 souls carry a tuned value (two at 0.45,
            # three at 0.05), so those five were gated one way by
            # hunger and another by craving.
            gate = traits_mod.dial(soul, "violence_gate", 0.25)
            if thoughts_mod.mood(soul) >= gate:
                return None
            if not _permits(soul, "craving", ("violence", "theft")):
                return None
            mark = _find_mark(soul)
            if mark is not None:
                return {"goal": "craving", "ethos": ("violence", "theft"),
                        "steps": [
                    {"do": "travel", "room": mark.location.id},
                    {"do": "grapple", "mark": mark.id},
                    {"do": "rob", "mark": mark.id, "lifts": 2},
                    {"do": "disengage", "mark": mark.id},
                ], "at": 0}
        return None

    if goal_need == "wardrobe":
        # get dressed (#2104). Cheapest first: wear what you already
        # carry; failing that, walk to an issue dispenser and press it.
        # Buying clothes at a shop is the obvious third branch and is
        # deliberately not here yet — the colony's free issue covers
        # the case that actually occurs (waking up with nothing).
        from world.souls import needs as needs_mod
        upgrading = needs_mod.wardrobe_pressure(soul) < 1.0
        # Only clothes that COVER SOMETHING STILL BARE count as
        # "already carried". Any wearable used to qualify, so a spare
        # pair of trousers stopped a soul ever going shopping -- Bianca
        # Morgan owned two pairs of jeans, needed a chest layer, and
        # spent hours trying to put the second pair on over the first
        # (#2329). The shop branch below already picks by missing
        # coverage; this one was the only place that did not.
        still_bare = _uncovered(soul)
        carried = [o for o in soul.contents if _wearable(soul, o)
                   and not (upgrading and o.attributes.get("provisional"))
                   and (not still_bare
                        or (set(o.attributes.get("coverage") or ())
                            & still_bare))]
        if carried:
            return {"goal": "wardrobe", "steps": [
                {"do": "wear"},
            ], "at": 0}
        for score, fixture, room in _advertisers(soul, "wardrobe"):
            inv = fixture.db.prototype_inventory or {}
            if inv:
                # a shop (or a free rail): take the garment that most
                # covers what you still need covered, cheapest among
                # equals — buying a jacket while bare-legged is how a
                # soul ends up naked in a coat (#2116)
                if not _counter_open(fixture):
                    continue
                missing = _uncovered(soul)
                wares = []
                for proto_key, price in inv.items():
                    cov = _proto_coverage(proto_key)
                    if cov is None or not _in_stock(fixture, proto_key):
                        continue
                    if price > int(soul.tokens or 0):
                        continue
                    if upgrading and _is_provisional_proto(proto_key):
                        continue      # more paper is not an upgrade
                    # replacing the issue: any real garment is progress
                    gain = len(cov & missing) if missing else len(cov)
                    # among equals, dress like yourself (#2122)
                    fit = _proto_affinity(proto_key, soul)
                    wares.append((-gain, -fit, price, proto_key))
                helpful = [w for w in wares if w[0] < 0]
                # DON'T BUY WHAT YOU ALREADY OWN AND CANNOT WEAR. The
                # planner refuses to PICK a garment `can_wear_now` says
                # no to (#2337), which empties `carried` and drops
                # straight through to here — so a soul whose only gap
                # is under something already worn bought a fresh copy
                # of the identical garment every planning cycle. #6106
                # Sam Fukuda accumulated 628 pairs of trousers that
                # way, ids 9811 to 16850, one per cycle, none ever worn
                # (#3169).
                #
                # A gap this soul is ALREADY carrying a garment for is
                # not a gap shopping can close. Faulting is the honest
                # answer, and the wear step now tries to re-layer
                # before it gets here.
                owned = set()
                for held in soul.contents:
                    check = getattr(held, "is_wearable", None)
                    if not callable(check) or not check():
                        continue
                    if soul.is_item_worn(held):
                        continue
                    owned |= set(held.attributes.get("coverage") or ())
                if owned:
                    helpful = [
                        w for w in helpful
                        if (_proto_coverage(w[3]) or set()) & (missing - owned)
                    ]
                if not helpful:
                    continue      # nothing here closes the gap
                _score, _fit, price, proto = min(helpful)
                return {"goal": "wardrobe", "steps": [
                    {"do": "travel", "room": room.id},
                    {"do": "buy", "counter": fixture.id, "proto": proto,
                     "price": price},
                    {"do": "wear"},
                ], "at": 0}
            if upgrading:
                continue          # the issue machine has nothing to add
            # a dispenser: press it and get dressed
            return {"goal": "wardrobe", "steps": [
                {"do": "travel", "room": room.id},
                {"do": "press", "fixture": fixture.id},
                {"do": "wear"},
            ], "at": 0}
        return None

    if goal_need == "insurance":
        # Walk to the sleeve-policy terminal and buy one, in person: the
        # machine samples the presser (#3667). Found by its index tag,
        # not by advertiser radius: the lobby is a long walk from the
        # Brackett, and the need is worth the walk.
        from evennia.utils.search import search_tag
        from typeclasses.terminals import InsuranceTerminal
        terminals = [t for t in search_tag("insurance_terminal", category="machines")
                     if t and t.pk and t.location is not None]
        if not terminals:
            return None
        term = terminals[0]
        return {"goal": "insurance", "steps": [
            {"do": "travel", "room": term.location.id},
            {"do": "press", "fixture": term.id,
             "button": InsuranceTerminal.BUY_BUTTON},
            {"do": "insured"},
        ], "at": 0}

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
            return {"goal": "social", "ethos": ("revelry",), "steps": [
                {"do": "travel", "room": room.id},
                {"do": "linger", "beats": 4},
            ], "at": 0}
        return None

    if shape == "clinic":
        # the walking wounded self-deliver (spec §14 layer 1): travel to
        # a treatment advertiser and see the doctor. Billing happens in
        # the treat step — triage for the dying is free, healing costs.
        # people to a doctor, machines to a bench — same need, same
        # shape, different door (#2262)
        from world.souls import needs as _needs
        for score, fixture, room in _advertisers(
                soul, _needs.clinic_service(soul)):
            return {"goal": goal_need, "ethos": ("care",), "steps": [
                {"do": "travel", "room": room.id},
                {"do": "treat", "clinic": fixture.id},
            ], "at": 0}
        return None

    if shape == "dwell_venue":
        # generic dwell need (charge, maintenance, a recluse's line and
        # airwaves): occupy the best advertiser until the meter recovers
        # (spec §12); the FIXTURE authors its own dwell poses
        for score, venue, room in _advertisers(soul, goal_need):
            return {"goal": goal_need, "ethos": ("solitude",), "steps": [
                {"do": "travel", "room": room.id},
                {"do": "dwell", "need": goal_need, "fixture": venue.id},
            ], "at": 0}
        return None

    if goal_need == "duty":
        post = soul.db.soul_post
        if not post:
            return None
        return {"goal": "duty", "ethos": ("toil",), "steps": [
            {"do": "travel", "room": post.id},
            {"do": "work"},
        ], "at": 0}

    if goal_need == "provision":
        # Put a ration in the pocket (#3804): walk to a source, buy one,
        # and do NOT eat it. `wants_ration` asked the same question of
        # the same function (`_ration_source`) before offering this.
        if len(_carried_rations(soul)) >= constants.RATION_CARRY_MAX:
            return None
        source = _ration_source(soul)
        if source is None:
            # the world moved between the offer and the plan: do not be
            # offered again from here until the route is asked afresh
            _remember_no_ration_route(soul)
            return None
        fixture, room, proto, price = source
        # ...to KEEP (#3808). A shop hands a purchase into the buyer's
        # free hand, which is right for a meal about to be eaten and
        # wrong for something bought to be kept: the soul would walk
        # about holding its ration for days, with one hand fewer for
        # its radio. `keep` has the `buy` step put it away in the same
        # beat. Not a step of its own: this is the lowest band there
        # is, so anything arriving between two steps drops the job, and
        # a soul already carrying its ration is never sent on the
        # errand again to finish it.
        return {"goal": "provision", "at": 0, "steps": [
            {"do": "travel", "room": room.id},
            {"do": "buy", "counter": fixture.id, "proto": proto,
             "price": price, "keep": True},
        ]}

    if goal_need == "off_duty":
        # not a need — an absence of one. The shift is over and there is
        # no reason to still be standing here, so go somewhere (#2148).
        #
        # A PERCH, if the soul keeps one, beats home. This is the gap
        # off_duty was built for — the hours between the end of a shift
        # and the start of sleep — and for some people that gap is not
        # spent indoors. A rabbit sits on a roof and watches the
        # street; when rest finally bites, the band tree outranks this
        # and sends her home to bed like everyone else (#2299).
        perch = soul.db.soul_perch
        where = perch if perch is not None and perch.pk else soul.db.soul_home
        if where is None or soul.location == where:
            return None
        return {"goal": "off_duty", "steps": [
            {"do": "travel", "room": where.id},
        ], "at": 0}

    if goal_need == "safety":
        # flee: any exit away from the threat room; the real move verb
        return {"goal": "safety", "steps": [{"do": "flee"}], "at": 0}

    return None
