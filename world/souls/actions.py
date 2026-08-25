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
    return found


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
    return not soul.is_item_worn(obj)


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
        post = soul.db.soul_post
        home = post if getattr(post, "contents", None) is not None \
            else getattr(post, "location", None)
        if dest is None or counter is None or home is None:
            return None
        return {"goal": "run", "at": 0, "steps": [
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
        if needs_mod.shape_of(soul, "hunger") == "graze":
            # sealed-biome feeding (spec §12 recluse, #2074): a serving
            # fixture (db.snacks with nutrition) eaten through the REAL
            # eat verb — the same membrane, gates, and pharmacology a
            # player standing in the room would hit
            for score, fixture, room in _advertisers(soul, "hunger"):
                entry = next(
                    (s for s in (fixture.db.snacks or [])
                     if (s.get("effects") or {}).get("nutrition")), None)
                if entry is None:
                    continue
                word = (entry.get("order_keywords")
                        or (entry.get("name", ""),))[0]
                return {"goal": "hunger", "steps": [
                    {"do": "travel", "room": room.id},
                    {"do": "graze", "fixture": fixture.id, "word": word},
                ], "at": 0}
            return None
        for score, counter, room in _advertisers(soul, "hunger"):
            # regulars know the hours: a shuttered counter isn't worth
            # the walk. Ask the SAME question the shop asks — "is
            # anyone's shift-holder standing here" — rather than the
            # legacy single-keeper mirror, which had souls skipping
            # counters that would have served them and walking to ones
            # that wouldn't (#2142).
            if not _counter_open(counter):
                continue
            wares = _edible_wares(counter)
            if not wares:
                continue
            proto, price = min(wares, key=lambda kv: kv[1])
            from world.souls import traits as traits_mod
            ceiling = traits_mod.dial(soul, "price_ceiling", 1.0)
            if ceiling > 1.0:
                # Open-Valve buys the best they can afford, not the cheapest
                affordable = [w for w in wares
                              if w[1] <= int(soul.tokens or 0)]
                if affordable:
                    proto, price = max(affordable, key=lambda kv: kv[1])
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
        for score, counter, room in _advertisers(soul, "vice"):
            if not _counter_open(counter):
                continue                       # shuttered: cravings wait
            wares = [(price, proto_key, verb)
                     for proto_key, price
                     in (counter.db.prototype_inventory or {}).items()
                     for verb, subs in (_vice_info(proto_key),)
                     if verb and _sub_matches(subs, craved)
                     and _in_stock(counter, proto_key)]
            if not wares:
                continue
            price, proto, verb = min(wares)
            if (soul.tokens or 0) < price:
                continue
            return {"goal": "craving", "steps": [
                {"do": "travel", "room": room.id},
                {"do": "buy", "counter": counter.id, "proto": proto,
                 "price": price},
                {"do": "consume", "verb": verb},
            ], "at": 0}
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
        carried = [o for o in soul.contents if _wearable(soul, o)
                   and not (upgrading and o.attributes.get("provisional"))]
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
        # no reason to still be standing here, so go home (#2148).
        home = soul.db.soul_home
        if home is None or soul.location == home:
            return None
        return {"goal": "off_duty", "steps": [
            {"do": "travel", "room": home.id},
        ], "at": 0}

    if goal_need == "safety":
        # flee: any exit away from the threat room; the real move verb
        return {"goal": "safety", "steps": [{"do": "flee"}], "at": 0}

    return None
