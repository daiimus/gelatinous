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
    if not (counter.db.post_slots or counter.db.post_keeper is not None):
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
        return None
    try:
        from world.perception import can_perceive
        if not can_perceive(soul, tender):
            return None
    except Exception:  # noqa: BLE001 — perception is a filter, not a gate
        pass
    return tender


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
    from. The door used to be chosen by the soul's species profile
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
        from world.consumables import supports_delivery
        if any(supports_delivery(o, "eat") for o in soul.contents):
            return {"goal": "hunger", "steps": [{"do": "eat"}], "at": 0}
        shape = needs_mod.shape_of(soul, "hunger")
        for score, fixture, room in _advertisers(soul, "hunger"):
            steps = _feed_at(soul, fixture, shape)
            if steps:
                return {"goal": "hunger", "at": 0, "steps":
                        [{"do": "travel", "room": room.id}] + steps}
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
        for score, fixture, room in _advertisers(soul, "vice"):
            steps = _indulge_at(soul, fixture, craved)
            if steps:
                return {"goal": "craving", "at": 0, "steps":
                        [{"do": "travel", "room": room.id}] + steps}
        # a broke addict with lawless hands robs for the fix — the same
        # knife, mark, and mood gate as hunger (misery is the mechanism)
        if soul.db.soul_lawless:
            from world.souls import thoughts as thoughts_mod
            if thoughts_mod.mood(soul) >= 0.25:
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
