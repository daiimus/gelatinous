"""The colony breathes people (souls spec §14, owner verdicts 2026-08-19).

Labor AUTO-SEEDS: the population-keeper sweep keeps a small pool of
unemployed residents so a murdered worker's post always has a claimant
eventually — and each new arrival's disposition SCALES WITH POVERTY:
the broke fraction of the living population is the probability the
newcomer steps off the shuttle desperate and carrying steel. The
economy is the crime dial — feed the colony and the streets stay
quiet; let poverty spread and the arrivals get hungry-eyed.
"""

import time
from random import choice, randint, random, choices

from evennia import create_object
from evennia.utils.search import search_object

SEED_TARGET_UNEMPLOYED = 2
SEED_MIN_INTERVAL = 4 * 3600          # at most one arrival per ~4h
BROKE_LINE = 3                        # can't buy the cheapest meal

_PERSONAS = {
    "seeker": {
        "sdesc_keyword": "colonist",
        "desc": ("A colonist between things — clothes clean but going "
                 "thin at the seams, hands that have done several kinds "
                 "of work and would take a new kind tomorrow."),
        "voice": "careful, hopeful",
        "persona": {
            "archetype": "colonist",
            "description": ("A colonist between jobs, clean but "
                            "threadbare, looking for an opening."),
            "personality": (
                "Lost the last work to nothing dramatic — a closed "
                "counter, a short season. Proud enough to hate asking, "
                "practical enough to ask anyway."),
            "manner": ("polite, a little too quick to be useful; asks "
                       "what work a place needs first"),
            "wants": ("steady work, a paid-up ledger, and to stop "
                      "counting tokens twice"),
            "boundaries": ("beg outright; take charity with witnesses; "
                           "badmouth the last employer"),
            "scenario": ("Between jobs in the colony, drifting the "
                         "Brackett lobby, listening for openings."),
        },
        "tokens": 5,
        "stats": lambda: (randint(1, 3), randint(1, 3),
                          randint(1, 3), randint(1, 3)),
    },
    "desperate": {
        "sdesc_keyword": "drifter",
        "desc": ("A colonist worn down past the polite fictions — coat "
                 "seams gone to string, knuckles scarred in the way that "
                 "says the last few meals were arguments. The eyes do "
                 "arithmetic on everyone who passes."),
        "voice": "flat, hungry",
        "persona": {
            "archetype": "colonist",
            "description": ("A hard-worn drifter, coat gone to string, "
                            "watching what everyone carries."),
            "personality": (
                "Ran out of good options a while back and stopped "
                "grieving them. Not cruel — practical the way hunger is "
                "practical."),
            "manner": ("short, flat lines; stands too still; never asks "
                       "for anything twice"),
            "wants": ("a full stomach, tokens enough that tomorrow isn't "
                      "arithmetic, and no trouble that outlives the meal"),
            "boundaries": ("beg; explain themselves; hurt anyone worth "
                           "more alive"),
            "scenario": ("Drifting the colony's streets and lobbies, "
                         "broke and hungry, weighing what people carry."),
        },
        "tokens": 0,
        "stats": lambda: (randint(2, 4), randint(1, 2),
                          randint(1, 3), randint(2, 4)),
    },
}


def poverty_index(souls) -> float:
    """The broke fraction of the living, non-robot population."""
    from world.souls import needs as needs_mod
    living = [s for s in souls
              if s.pk and needs_mod.profile_name(s) != "robot"]
    if not living:
        return 0.0
    broke = sum(1 for s in living
                if int(getattr(s, "tokens", 0) or 0) < BROKE_LINE)
    return broke / len(living)


def unemployed_count(souls) -> int:
    from world.souls import needs as needs_mod
    return sum(1 for s in souls
               if s.pk and s.db.soul_post is None
               and not s.db.soul_lawless
               and needs_mod.profile_name(s) != "robot")


#: the slots an outfit is assembled from, and the body part that
#: proves each one is filled
OUTFIT_SLOTS = (("torso", "chest"), ("legs", "groin"), ("feet", "left_foot"))


def outfit_for(npc, stock, budget=None):
    """Assemble an outfit from `stock`, by preference and budget.

    `stock` is [(proto_key, price, coverage, styles, presentation)].
    Returns the
    proto_keys chosen — one per slot, favouring the wearer's own
    register, spending nothing it doesn't have. Deliberately NOT a
    random draw: a person with taste and a budget picks pieces that go
    together, and only falls back to somebody else's register when
    their own has nothing for that slot (#2122).
    """
    from world import style as style_mod

    wearer = style_mod.style_of_character(npc)
    leaning = style_mod.presentation_of_character(npc)
    purse = int(budget) if budget is not None else None
    chosen, spent, covered = [], 0, set()

    for _slot, proof in OUTFIT_SLOTS:
        if proof in covered:
            continue                     # an earlier piece already covers it
        options = [
            (style_mod.affinity(styles, wearer)
             + style_mod.presentation_affinity(pres, leaning),
             -price, cov, key, price)
            for key, price, cov, styles, pres in stock
            if proof in cov
            and (purse is None or price + spent <= purse)
        ]
        if not options:
            # OBSERVABLE. A slot the budget could not reach used to be
            # dropped with no log line and no fallback, which is
            # indistinguishable from an arrival who is meant to be
            # barefoot. The docstring calls this "taste"; an empty
            # option list is not taste, it is a purse that could not
            # reach the shelf (#2705).
            from evennia.utils import logger
            logger.log_info(
                f"OUTFIT_SLOT_UNFILLED: {npc.key} (#{npc.id}) has "
                f"nothing for {_slot!r} within "
                f"{'no budget' if purse is None else purse - spent} — "
                f"leaving it bare.")
            continue
        best_fit = max(o[0] for o in options)
        # everything that fits them equally well; the tie is where
        # variety lives, not the choice itself
        finalists = [o for o in options if o[0] == best_fit]
        cheapest = max(o[1] for o in finalists)
        finalists = [o for o in finalists if o[1] == cheapest]
        pick = choice(finalists)
        chosen.append(pick[3])
        spent += pick[4]
        covered |= set(pick[2])
    return chosen


def missing_outfit_slots(npc):
    """Which of `OUTFIT_SLOTS` this body has nothing covering.

    Reads `npc.worn_items`, which is keyed by BODY LOCATION — a slot is
    filled when its proof part appears there. NOT a per-item `db.worn`
    flag: that attribute does not exist, there are zero such rows in the
    database, and a probe that read it reported all 78 souls as naked
    (#2705).

    A robot is legitimately bare and is never short a slot.
    """
    from world.souls import needs as needs_mod
    try:
        if needs_mod.profile_name(npc) == "robot":
            return []
    except Exception:  # noqa: BLE001 — unknown profile is not a robot
        pass
    worn = npc.worn_items or {}
    return [(slot, proof) for slot, proof in OUTFIT_SLOTS
            if proof not in worn]


def ensure_outfit_complete(npc):
    """Fill any `OUTFIT_SLOTS` this body is short, off the thrift rail.

    The invariant was declared in this module and consulted by the
    generated-arrival path ALONE. Blueprinted cast is built through
    `world/npcs/blueprints.py`, which never read it, so the rule that a
    colonist wears a torso piece, a leg piece and footwear governed
    procedural residents and not the named cast: twelve named NPCs —
    three mechanics, two vendors, a bartender, a courier — walked the
    colony barefoot, every one of them missing exactly `feet` (#2705).

    NO BUDGET. `outfit_for` is a shopping decision and spends what the
    wearer has; this is the floor under it. A blueprint that authors a
    full wardrobe never reaches here, and one that authors none gets
    dressed rather than shipped naked.

    Returns the slots it filled, so a caller can log them.
    """
    from evennia.prototypes.spawner import spawn
    from evennia.utils import logger

    missing = missing_outfit_slots(npc)
    if not missing:
        return []

    stock = _thrift_stock()
    filled = []
    for slot, proof in missing:
        options = [entry for entry in stock if proof in entry[2]]
        if not options:
            logger.log_info(
                f"OUTFIT_SLOT_UNFILLABLE: nothing on the rail covers "
                f"{proof!r} for {npc.key} (#{npc.id}).")
            continue
        proto_key = choice(options)[0]
        try:
            garment = spawn(proto_key)[0]
        except Exception:  # noqa: BLE001 — a bad proto never blocks a build
            continue
        # MARKED. A blueprint's fidelity check compares what the body
        # wears against what the blueprint authored, and a garment this
        # function added is neither authored nor a drift — it is the
        # floor. Without the mark, `verify_blueprint` reports every
        # invariant-dressed NPC as diverging from its own blueprint.
        garment.db.outfit_invariant = True
        garment.move_to(npc, quiet=True, move_hooks=False)
        # CHECK THE RETURN. `wear_item` returns `(ok, message)` and
        # refuses a garment going on UNDER an already-worn outer layer —
        # the same trap the blueprint wardrobe loop sorts by layer to
        # avoid. A caller that discards the result leaves the refused
        # garment sitting in inventory, and something doing that on a
        # repeating schedule is how one NPC ended up carrying 628
        # unworn pairs of trousers.
        ok, why = npc.wear_item(garment)
        if not ok:
            garment.delete()
            logger.log_info(
                f"OUTFIT_SLOT_REFUSED: {npc.key} (#{npc.id}) could not "
                f"wear {proto_key} for {slot!r}: {why} — discarded "
                f"rather than left in inventory.")
            continue
        filled.append(slot)
    if filled:
        logger.log_info(
            f"OUTFIT_COMPLETED: {npc.key} (#{npc.id}) was short "
            f"{filled} and has been dressed.")
    return filled


def _thrift_stock():
    """What the Community Thrift's rail is carrying, as outfit stock —
    the same donated shelf the colony's poor dress from."""
    from evennia.prototypes.prototypes import search_prototype

    from world import style as style_mod

    rail = next((o for o in search_object("the free rail") if o.pk), None)
    inventory = (rail.db.prototype_inventory or {}) if rail else {}
    if not inventory:
        inventory = {k: 0 for k in ("FLANNEL_SHIRT", "COTTON_TSHIRT",
                                    "CARGO_TROUSERS", "HIGH_TOPS")}
    stock = []
    for proto_key, price in inventory.items():
        hits = search_prototype(proto_key)
        if not hits:
            continue
        proto = hits[0]
        attrs = {a[0]: a[1] for a in (proto.get("attrs") or ())
                 if isinstance(a, (tuple, list)) and len(a) >= 2}
        cov = attrs.get("coverage")
        if not cov or not attrs.get("worn_desc") or attrs.get("provisional"):
            continue
        styles = attrs.get("style") or style_mod.derive_style(
            proto.get("key", ""), attrs.get("desc", ""))
        pres = attrs.get("presentation") or style_mod.derive_presentation(
            proto.get("key", ""))
        stock.append((proto_key, int(price or 0), frozenset(cov),
                      tuple(styles), tuple(pres)))
    return stock


def _dress_arrival(npc):
    """Nobody arrives naked: an outfit off the thrift rail, assembled to
    the arrival's own taste and what little they have."""
    from evennia.prototypes.spawner import spawn

    for proto_key in outfit_for(npc, _thrift_stock(),
                                budget=int(npc.tokens or 0)):
        try:
            garment = spawn(proto_key)[0]
        except Exception:  # noqa: BLE001 — a bad proto never blocks arrival
            continue
        garment.move_to(npc, quiet=True, move_hooks=False)
        npc.wear_item(garment)


def generate_resident(lawless=False):
    """One namebank arrival: cube through the real kiosk, ensouled,
    lawless carrying steel when the colony's poverty called for it."""
    from world import rental
    from world.namebank import (FIRST_NAMES_AMBIGUOUS, FIRST_NAMES_FEMALE,
                                FIRST_NAMES_MALE, LAST_NAMES)
    from world.souls import engine
    from world.souls import needs as needs_mod

    lobby = next((r for r in search_object("The Brackett Arms - Lobby")
                  if r.pk and not r.destination), None)
    kiosk = next(iter(search_object("#5640")), None)
    if lobby is None or kiosk is None:
        return None
    kind = _PERSONAS["desperate" if lawless else "seeker"]
    bank = choice((FIRST_NAMES_MALE, FIRST_NAMES_FEMALE,
                   FIRST_NAMES_AMBIGUOUS))
    first, last = choice(bank), choice(LAST_NAMES)
    name = f"{first} {last}"
    sex = ("male" if bank is FIRST_NAMES_MALE
           else "female" if bank is FIRST_NAMES_FEMALE
           else choice(("male", "female")))
    npc = create_object("typeclasses.llm_npc.LLMNpc", key=name,
                        location=lobby, home=lobby)
    npc.aliases.add([first.lower(), last.lower()])
    npc.db.is_npc = True
    npc.sex = sex
    # The canonical vocabularies, not a hand-written subset of them.
    # Souls used to roll four builds of six and three heights of five,
    # so nobody who arrived this way was ever athletic or heavyset —
    # and "dark" is not a skintone the palette knows, so a quarter of
    # them rendered with no colour at all. Build is load-bearing here:
    # these NPCs carry no job keyword, so build and clothing are what
    # tell them apart (#2148).
    from world.director.civilians import HUMAN_SKINTONES
    from world.identity import BUILDS, HEIGHTS
    npc.height = choice(HEIGHTS)
    npc.build = choice(BUILDS)
    npc.db.skintone = choice(HUMAN_SKINTONES)
    npc.grit, npc.resonance, npc.intellect, npc.motorics = kind["stats"]()
    # A person is not their job (owner ruling): leaving the keyword unset
    # lets the identity system fall back to a person-word from their sex,
    # and build + clothing do the distinguishing. "a rangy man in a
    # company windbreaker" reads as somebody; "a rangy vendor" reads as a
    # function (#2148).
    npc.db.desc = kind["desc"]
    npc.db.voice_description = kind["voice"]
    npc.db.llm_driven = True
    persona = dict(kind["persona"])
    persona["name"] = name
    npc.db.llm_persona = persona
    npc.tokens = kind["tokens"]
    if lawless:
        npc.db.soul_lawless = True
        try:
            from evennia.prototypes.spawner import spawn
            shiv = spawn("shiv")[0]
            shiv.location = npc
            npc.wield_item(shiv, "right")
        except Exception:  # noqa: BLE001 — an unarmed desperate still walks
            pass
    # nobody arrives naked: a style, and an outfit in it. The shuttle
    # used to deliver identical bare strangers who all walked to
    # Cryogenics for the same paper suit (#2122).
    from world import style as style_mod
    npc.db.style = list(style_mod.roll_style(
        role="drifter" if lawless else None))
    # rolled INDEPENDENTLY of sex, deliberately (world.style rule 3)
    npc.db.presents = list(style_mod.roll_presentation())
    # two or three traits, exclusion-safe: the shuttle stops delivering
    # interchangeable strangers (NPC_TRAITS_SPEC §7)
    from world.souls import traits as traits_mod
    npc.db.soul_traits = list(traits_mod.roll())
    # the manifest: who the dead chart said they were, and what it
    # rated them for. Identity-level, so it survives every resleeve.
    from world import manifest as manifest_mod
    npc.db.designation = manifest_mod.roll_designation()
    npc.db.skills = manifest_mod.seed_skills(npc.db.designation)
    # a body, not just a name: souls were the only population that never
    # went through the flavor layer, which is why a random crowd body was
    # better described than the named cast (#2158)
    try:
        from world.mob_flavor import fill_missing_longdescs
        fill_missing_longdescs(npc)
    except Exception:  # noqa: BLE001 — an undescribed arrival still arrives
        pass
    _dress_arrival(npc)

    rental.assign_cube(npc, kiosk)
    home = rental.residence_of(npc)
    engine.ensoul(npc, role="drifter" if lawless else "resident",
                  home=home, post=None, schedule="day",
                  wage_rate=0.02, venue=None)
    if lawless:
        fresh = dict(needs_mod.DEFAULT_NEEDS)
        fresh["hunger"] = 0.70            # arrives already counting meals
        fresh["_at"] = time.time()
        npc.db.soul_needs = fresh
    return npc


def sweep(heartbeat, now=None):
    """The population keeper: one arrival at most per interval, only
    when the unemployed pool runs thin. Disposition rolls against the
    poverty index — the economy is the crime dial."""
    from world.souls import engine

    now = now if now is not None else time.time()
    last = float(heartbeat.db.last_seed or 0.0)
    if now - last < SEED_MIN_INTERVAL:
        return None
    souls = engine.get_souls()
    if unemployed_count(souls) >= SEED_TARGET_UNEMPLOYED:
        return None
    lawless = random() < poverty_index(souls)
    npc = generate_resident(lawless=lawless)
    if npc is not None:
        heartbeat.db.last_seed = now
    return npc
