"""Build 072 — P4a posts: registration, one real vacancy, one seeker.

Registers the standing posts so every current job survives its keeper
(spec §13 / reincarnation spec §1.2): Lin's cart, the shell counter,
the Brackett caretaker room, Eli's night shift on the Kettle hall.
Then the pilot succession: an attendant's station fixture carries a
VACANT day shift at the Kettle (short grace — it's the live pilot),
and a new namebank resident arrives unemployed. The watcher should
introduce them.

Idempotent: registrations re-mirror; station and resident create once.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/072_souls_p4a_posts.py
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
DAY = 24 * 3600


def _soul(name):
    return next((s for s in engine.get_souls() if name in s.key), None)


# ---- 1. Register the standing posts --------------------------------
cart = next(iter(search_object("#7530")), None)
lin = _soul("Auntie Lin")
if cart and lin:
    register_post(cart, role="vendor", schedule="vendor", wage_rate=0.02,
                  policy="successor", delay=3 * DAY, keeper=lin)
    OUT.append(f"post: {cart.key} (vendor, successor, 3d) keeper {lin.key}")

shell = next((o for o in search_object("the shell counter") if o.pk), None)
bruce = _soul("Bruce")
if shell and bruce:
    register_post(shell, role="snail_hand", schedule="day", wage_rate=0.02,
                  policy="successor", delay=DAY, keeper=bruce)
    OUT.append(f"post: {shell.key} (snail_hand, successor, 1d) "
               f"keeper {bruce.key}")

lobby = next((r for r in search_object("The Brackett Arms - Lobby")
              if r.destination is None), None)
martha = _soul("Martha")
if lobby and martha:
    register_post(lobby, role="caretaker", schedule="day", wage_rate=0.02,
                  policy="successor", delay=DAY, keeper=martha)
    OUT.append(f"post: {lobby.key} (caretaker, successor, 1d) "
               f"keeper {martha.key}")

hall = next((r for r in search_object("The Kettle - Bath Hall")
             if r.destination is None), None)
eli = _soul("Eli")
if hall and eli:
    register_post(hall, role="kettle_attendant", schedule="night",
                  wage_rate=0.02, policy="successor", delay=DAY, keeper=eli)
    OUT.append(f"post: {hall.key} (kettle night, successor, 1d) "
               f"keeper {eli.key}")

# ---- 2. The pilot vacancy: Kettle DAY shift ------------------------
station = None
if hall:
    station = next((o for o in hall.contents
                    if "attendant's station" in o.key.lower()), None)
    if station is None:
        station = create_object("typeclasses.items.Item",
                                key="the attendant's station",
                                location=hall, home=hall)
        station.aliases.add(["station", "attendant station"])
        station.db.desc = (
            "A high wooden stool, a shelf of folded rags, a long-handled "
            "brush on its hook, and a slate where the day attendant "
            "chalks the water temperature. The slate is blank and the "
            "stool has been empty long enough to gather a film of "
            "mineral dust.")
        station.locks.add("get:false()")
    register_post(station, role="kettle_attendant", schedule="day",
                  wage_rate=0.02, policy="successor", delay=600)
    station.db.post_vacant_since = 1.0      # long-dark; grace already served
    OUT.append(f"VACANT post: {station.key} (kettle day, grace served)")

# ---- 3. One unemployed resident ------------------------------------
if not any(s.db.soul_post is None and s.db.soul_role == "resident"
           for s in engine.get_souls()):
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
    npc.grit = randint(1, 3)
    npc.resonance = randint(1, 3)
    npc.intellect = randint(1, 3)
    npc.motorics = randint(1, 3)
    npc.sdesc_keyword = "colonist"
    npc.db.desc = (
        "A colonist between things — clothes clean but going thin at the "
        "seams, hands that have done several kinds of work and would take "
        "a new kind tomorrow. Watches doorways the way the recently "
        "unlucky do: for openings.")
    npc.db.voice_description = "careful, hopeful"
    npc.db.llm_driven = True
    npc.db.llm_persona = {
        "archetype": "colonist",
        "name": name,
        "description": ("A colonist between jobs, clean but threadbare, "
                        "looking for an opening."),
        "personality": (
            "Lost the last work to nothing dramatic — a closed counter, a "
            "short season. Proud enough to hate asking, practical enough "
            "to ask anyway. Keeps a mental ledger of every place that "
            "might need hands."),
        "manner": ("polite, a little too quick to be useful; asks what "
                   "work a place needs before asking anything else"),
        "wants": ("steady work, a paid-up ledger, and to stop counting "
                  "tokens twice"),
        "boundaries": ("beg outright; take charity with witnesses; "
                       "badmouth the last employer"),
        "scenario": ("Between jobs in the colony, drifting between the "
                     "Brackett lobby and the third places, listening for "
                     "openings."),
    }
    npc.tokens = 5
    ok, msg = rental.assign_cube(npc, kiosk)
    home = rental.residence_of(npc)
    ensoul(npc, role="resident", home=home, post=None, schedule="day",
           wage_rate=0.02, venue=None)
    OUT.append(f"unemployed: {name} (#{npc.id}) home:"
               f"{home.key if home else 'NONE'} "
               f"kiosk:{'ok' if ok else 'FAILED — ' + msg}")
else:
    OUT.append("unemployed resident already exists; skipped")

print("BUILD 072: souls P4a posts")
for line in OUT:
    print(f"  {line}")
