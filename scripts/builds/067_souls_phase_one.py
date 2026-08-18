"""Build 067 — Souls phase 1: advertisements, treasury, first resident.

Wires the world side of the souls engine (NPC_NEEDS_AND_GOALS_SPEC §9
phase 1):

 * venues ADVERTISE the needs they satisfy (hunger on the food
   counters, social on the bar) — the planner's search space;
 * the colony treasury is seeded ONCE (closed loop: treasury -> wages
   -> tills -> supply tithe -> treasury; no minting after this);
 * the first generated resident — a namebank identity ensouled as the
   Brackett Arms caretaker: day shift in the lobby, a real cube claimed
   through the real kiosk board, meals bought at real tills.

Idempotent: ads re-mirror, the treasury seeds only while empty and
unseeded, the resident is created only if no caretaker soul exists.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/067_souls_phase_one.py
"""

from random import choice, randint

from evennia import create_object
from evennia.utils.search import search_object

from typeclasses.shopkeeper import ShopContainer
from world import rental
from world.namebank import (FIRST_NAMES_AMBIGUOUS, FIRST_NAMES_FEMALE,
                            FIRST_NAMES_MALE, LAST_NAMES)
from world.souls import economy, engine, ensoul

TREASURY_SEED = 300

# ---- 1. Advertisements ------------------------------------------------
# Food counters advertise hunger (value ~= how square a meal); the
# planner scores value over distance and checks stock + cash for real.
ADS = []


def _advertise(obj, need, value):
    ads = dict(obj.db.advertises or {})
    ads[need] = value
    obj.db.advertises = ads
    # closed-loop invariant: an advertised counter MUST have a till —
    # shopkeeper.py only credits sales when db.register is initialized,
    # and an uninitialized register makes soul spending vanish from the
    # economy entirely
    if isinstance(obj, ShopContainer) and obj.db.register is None:
        obj.db.register = 0
    where = obj.location.key if obj.location else obj.key
    ADS.append(f"{obj.key} ({where}): {need}={value} "
               f"till={obj.db.register if isinstance(obj, ShopContainer) else '-'}")


counters = [o for o in ShopContainer.objects.all() if o.pk]
for counter in counters:
    key = counter.key.lower()
    if "noodle" in key:
        _advertise(counter, "hunger", 0.8)      # Lin's — the square meal
    elif "shell" in key:
        _advertise(counter, "hunger", 0.5)      # snailery — a snack
    elif "cart" in key:
        _advertise(counter, "hunger", 0.7)      # Ottilie's butcher cart

sable = next(iter(search_object("#3070")), None)
if sable and sable.location:
    _advertise(sable.location, "social", 0.7)   # the bar room itself

# ---- 2. Treasury (seeded once, then closed) ---------------------------
treasury = economy.get_treasury()
if not treasury.db.seeded and int(treasury.db.balance or 0) == 0:
    treasury.db.balance = TREASURY_SEED
    treasury.db.seeded = True
    seeded_msg = f"seeded {TREASURY_SEED}"
else:
    seeded_msg = f"already live at {economy.balance()}"

# ---- 3. The first resident --------------------------------------------
existing = [npc for npc in engine.get_souls()
            if npc.db.soul_role == "caretaker"]
kiosk = next(iter(search_object("#5640")), None)
resident_msg = "caretaker soul already exists; skipped"

if not existing and kiosk and kiosk.location:
    lobby = kiosk.location
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
    npc.build = choice(("wiry", "stocky", "lean"))
    npc.db.skintone = choice(("pale", "tan", "olive", "dark"))
    npc.grit = randint(1, 3)
    npc.resonance = randint(1, 3)
    npc.intellect = randint(1, 3)
    npc.motorics = randint(1, 3)
    npc.sdesc_keyword = "caretaker"
    npc.db.desc = (
        "A colonist in a worn coverall with a ring of building keys and a "
        "push-broom callus, the kind of person a lobby accretes rather than "
        "hires. Eyes that track drips, scuffs, and strangers in that order.")
    npc.db.voice_description = "even, unhurried"
    npc.db.llm_driven = True
    npc.db.llm_persona = {
        "archetype": "colonist",
        "name": name,
        "description": (
            "A colonist in a worn coverall with a ring of building keys, "
            "usually mid-task in the Brackett Arms lobby."),
        "personality": (
            "The Brackett's caretaker — sweeps the lobby, minds the "
            "kiosk queue, knows which doors stick and which tenants "
            "don't. Steady, incurious about other people's business, "
            "proprietary about the building."),
        "manner": ("short practical lines; keeps working while talking; "
                   "calls the building 'she'"),
        "wants": ("the lobby squared away, the rent kiosk unjammed, and "
                  "a hot bowl at Lin's when the shift breaks"),
        "boundaries": ("open a unit for a stranger; badmouth a tenant; "
                       "leave a spill overnight"),
        "scenario": ("On shift in the Brackett Arms lobby, broom or rag "
                     "in hand, between rounds of the halls."),
    }
    npc.tokens = 10                      # walking-around money to first payday

    ok, msg = rental.assign_cube(npc, kiosk)     # the REAL kiosk transaction
    home = rental.residence_of(npc)
    ensoul(npc, role="caretaker", home=home, post=lobby,
           schedule="day", wage_rate=0.02, venue=None)
    resident_msg = (f"{name} (#{npc.id}) sex:{sex} post:{lobby.key} "
                    f"home:{home.key if home else 'NONE'} "
                    f"kiosk:{'ok' if ok else 'FAILED — ' + msg}")
elif not kiosk:
    resident_msg = "kiosk #5640 not found; resident NOT created"

heartbeat = engine.get_heartbeat()

print("BUILD 067: souls phase 1")
for line in ADS:
    print(f"  ad: {line}")
print(f"  treasury: {seeded_msg}")
print(f"  resident: {resident_msg}")
print(f"  heartbeat: {heartbeat.key} #{heartbeat.id} "
      f"interval={heartbeat.interval}s active={heartbeat.is_active}")
print(f"  souls: {[s.key for s in engine.get_souls()]}")
