"""Build 074 — Maxwell's health economy (spec §14, layers 1 + 2 staffing).

The clinic learns to charge: a Thawn-Harrison billing terminal in the
front room carries the till (tagged — tithed, wage-paying) and
advertises `treatment` so the walking wounded self-deliver. A `medic`
post registers on the terminal, VACANT with grace served — the
succession watcher hires the next unemployed soul into it, and one
namebank resident arrives looking for exactly that kind of work.

Idempotent: terminal/ads re-mirror; post re-registers; the resident
seeds only if no unemployed soul exists.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/074_maxwell_health_economy.py
"""

from random import choice, randint

from evennia import create_object
from evennia.utils.search import search_object

from world import rental
from world.namebank import (FIRST_NAMES_AMBIGUOUS, FIRST_NAMES_FEMALE,
                            FIRST_NAMES_MALE, LAST_NAMES)
from world.souls import engine, ensoul
from world.souls.posts import register_post

OUT = []
front = next((r for r in search_object("Maxwell Medical Clinic")
              if r.pk and not r.destination
              and r.key == "Maxwell Medical Clinic"), None)

if front is None:
    print("BUILD 074: clinic front room not found; aborted")
else:
    terminal = next((o for o in front.contents
                     if "billing terminal" in o.key.lower()), None)
    if terminal is None:
        terminal = create_object("typeclasses.items.Item",
                                 key="a Thawn-Harrison billing terminal",
                                 location=front, home=front)
        terminal.aliases.add(["terminal", "billing", "desk"])
        terminal.db.desc = (
            "A wall-mounted slab of medical-white enamel with a token slot "
            "worn silver and a screen that itemizes mercy: TRIAGE — NO "
            "CHARGE. TREATMENT — POSTED RATES. The Thawn-Harrison crest "
            "sits above a smaller line of type: YOUR RECOVERY IS OUR "
            "BUSINESS.")
        terminal.locks.add("get:false()")
    terminal.db.register = int(terminal.db.register or 0)
    ads = dict(terminal.db.advertises or {})
    ads["treatment"] = 0.9
    terminal.db.advertises = ads
    terminal.tags.add("advertiser", category="souls")
    terminal.tags.add("till", category="souls")
    OUT.append(f"billing terminal (#{terminal.id}) @ {front.key} "
               f"register={terminal.db.register}")

    register_post(terminal, role="medic", schedule="day", wage_rate=0.02,
                  policy="successor", delay=600)
    if not (terminal.db.post_keeper and terminal.db.post_keeper.pk):
        terminal.db.post_vacant_since = 1.0     # grace served: hire now
    OUT.append("medic post registered (vacant, grace served)")

    if not any(s.db.soul_post is None and not s.db.soul_lawless
               for s in engine.get_souls() if s.pk):
        kiosk = next(iter(search_object("#5640")), None)
        lobby = next((r for r in search_object("The Brackett Arms - Lobby")
                      if r.destination is None), None)
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
        npc.grit = randint(1, 3)
        npc.resonance = randint(1, 3)
        npc.intellect = randint(2, 4)      # steady hands want a head
        npc.motorics = randint(2, 4)
        npc.sdesc_keyword = "colonist"
        npc.db.desc = (
            "A colonist with careful hands and a habit of watching how "
            "people move — for a limp, a guard, a wince. The kind of "
            "steady that gets volunteered for things.")
        npc.db.voice_description = "calm, deliberate"
        npc.db.llm_driven = True
        npc.db.llm_persona = {
            "archetype": "colonist",
            "name": name,
            "description": ("A steady-handed colonist between jobs, "
                            "watching how people carry themselves."),
            "personality": (
                "Patched people up on a hauler crew once and never quite "
                "put it down. Between jobs, methodical, unbothered by "
                "blood, bothered by waste. Looking for work that means "
                "something."),
            "manner": ("calm short sentences; looks at your hands and "
                       "gait before your face"),
            "wants": ("steady work with their hands, preferably the kind "
                      "that leaves people better than it found them"),
            "boundaries": ("panic; gossip about what a body told them; "
                           "work for free twice"),
            "scenario": ("Between jobs in the colony, drifting the "
                         "Brackett lobby, listening for openings."),
        }
        npc.tokens = 5
        ok, msg = rental.assign_cube(npc, kiosk)
        home = rental.residence_of(npc)
        ensoul(npc, role="resident", home=home, post=None, schedule="day",
               wage_rate=0.02, venue=None)
        OUT.append(f"seeker: {name} (#{npc.id}) home:"
                   f"{home.key if home else 'NONE'} "
                   f"kiosk:{'ok' if ok else 'FAILED — ' + msg}")
    else:
        OUT.append("unemployed soul already exists; no seeker generated")

    print("BUILD 074: Maxwell health economy")
    for line in OUT:
        print(f"  {line}")
