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
from random import choice, randint, random

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
    npc.height = choice(("short", "average", "tall"))
    npc.build = choice(("slight", "lean", "average", "stocky"))
    npc.db.skintone = choice(("pale", "tan", "olive", "dark"))
    npc.grit, npc.resonance, npc.intellect, npc.motorics = kind["stats"]()
    npc.sdesc_keyword = kind["sdesc_keyword"]
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
