"""Build 073 — P4b pilot: the colony's first desperate.

One generated resident seeded at the margin (owner verdicts 2026-08-18:
generated desperates only, lethal allowed, NPC-only marks): broke,
lawless, already hungry. Housed like anyone else — the housing credit
is universal; poverty here is tokens, not walls. When hunger crosses
critical and no counter will feed a soul with empty pockets, the
disposition gate opens and the colony learns what a mugging looks like.

Idempotent: skips if a lawless soul already exists.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/073_souls_p4b_desperate.py
"""

import time
from random import choice, randint

from evennia import create_object
from evennia.utils.search import search_object

from world import rental
from world.namebank import (FIRST_NAMES_AMBIGUOUS, FIRST_NAMES_FEMALE,
                            FIRST_NAMES_MALE, LAST_NAMES)
from world.souls import engine, ensoul
from world.souls import needs as needs_mod

existing = [s for s in engine.get_souls() if s.db.soul_lawless]
if existing:
    print(f"BUILD 073: lawless soul already exists ({existing[0].key}); "
          f"skipped")
else:
    lobby = next((r for r in search_object("The Brackett Arms - Lobby")
                  if r.destination is None), None)
    kiosk = next(iter(search_object("#5640")), None)
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
    npc.grit = randint(2, 4)          # the desperate are hard-worn
    npc.resonance = randint(1, 2)
    npc.intellect = randint(1, 3)
    npc.motorics = randint(2, 4)
    npc.sdesc_keyword = "drifter"
    npc.db.desc = (
        "A colonist worn down past the polite fictions — coat seams gone "
        "to string, knuckles scarred in the way that says the last few "
        "meals were arguments. The eyes do arithmetic on everyone who "
        "passes: what they carry, how they carry it, how fast they walk.")
    npc.db.voice_description = "flat, hungry"
    npc.db.llm_driven = True
    npc.db.llm_persona = {
        "archetype": "colonist",
        "name": name,
        "description": ("A hard-worn drifter, coat gone to string, "
                        "watching what everyone carries."),
        "personality": (
            "Ran out of good options a while back and stopped grieving "
            "them. Not cruel — practical the way hunger is practical. "
            "Would take honest work if any counter would have them; the "
            "counters stopped having them. What's left is arithmetic."),
        "manner": ("short, flat lines; stands too still; never asks for "
                   "anything twice"),
        "wants": ("a full stomach, tokens enough that tomorrow isn't "
                  "arithmetic, and no trouble that outlives the meal"),
        "boundaries": ("beg; explain themselves; hurt anyone worth more "
                       "alive"),
        "scenario": ("Drifting the colony's streets and lobbies, broke "
                     "and hungry, weighing what people carry."),
    }
    npc.tokens = 0                     # the whole point
    npc.db.soul_lawless = True
    ok, msg = rental.assign_cube(npc, kiosk)
    home = rental.residence_of(npc)
    ensoul(npc, role="drifter", home=home, post=None, schedule="day",
           wage_rate=0.02, venue=None)
    fresh = dict(needs_mod.DEFAULT_NEEDS)
    fresh["hunger"] = 0.80             # the clock is already running
    fresh["_at"] = time.time()
    npc.db.soul_needs = fresh
    print(f"BUILD 073: desperate {name} (#{npc.id}) lawless, 0 tokens, "
          f"hunger 0.80, home {home.key if home else 'NONE'} "
          f"kiosk:{'ok' if ok else 'FAILED — ' + msg}")
