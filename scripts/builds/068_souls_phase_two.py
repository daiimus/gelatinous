"""Build 068 — Souls phase 2: Auntie Lin ensouled + two more residents.

Owner verdicts (2026-08-17): Lin lives in a Brackett cube claimed
through the real kiosk; the cart runs a long vendor day (10:00-22:00 —
binding `post_keeper` makes the counter CLOSE whenever she isn't
behind it, so the small-hours hunger gap emerges rather than being
scripted); the Kettle bath hall becomes the south side's advertised
third place; and two more namebank residents join her — a night-shift
Kettle attendant (treasury-paid) and a snailery hand (paid from the
shell counter's till, which is now bound to them the same way).

Idempotent: bindings and ads re-mirror; each resident is created only
if no soul with that role exists.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/068_souls_phase_two.py
"""

from random import choice, randint

from evennia import create_object
from evennia.utils.search import search_object

from typeclasses.shopkeeper import Shopkeeper
from world import rental
from world.namebank import (FIRST_NAMES_AMBIGUOUS, FIRST_NAMES_FEMALE,
                            FIRST_NAMES_MALE, LAST_NAMES)
from world.souls import engine, ensoul

OUT = []
kiosk = next(iter(search_object("#5640")), None)


def _pick_identity():
    bank = choice((FIRST_NAMES_MALE, FIRST_NAMES_FEMALE,
                   FIRST_NAMES_AMBIGUOUS))
    first, last = choice(bank), choice(LAST_NAMES)
    sex = ("male" if bank is FIRST_NAMES_MALE
           else "female" if bank is FIRST_NAMES_FEMALE
           else choice(("male", "female")))
    return first, last, sex


def _make_resident(role, post, desc, voice, persona, schedule, venue=None):
    """A generated-with-curation colonist: namebank identity, real cube
    via the kiosk board, ensouled into the authored role."""
    first, last, sex = _pick_identity()
    name = f"{first} {last}"
    npc = create_object("typeclasses.llm_npc.LLMNpc", key=name,
                        location=post, home=post)
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
    npc.sdesc_keyword = role.split("_")[-1]
    npc.db.desc = desc
    npc.db.voice_description = voice
    npc.db.llm_driven = True
    persona = dict(persona)
    persona["name"] = name
    npc.db.llm_persona = persona
    npc.tokens = 10
    ok, msg = rental.assign_cube(npc, kiosk)
    home = rental.residence_of(npc)
    ensoul(npc, role=role, home=home, post=post, schedule=schedule,
           wage_rate=0.02, venue=venue)
    OUT.append(f"{role}: {name} (#{npc.id}) post:{post.key} "
               f"home:{home.key if home else 'NONE'} "
               f"kiosk:{'ok' if ok else 'FAILED — ' + msg}")
    return npc


existing_roles = {npc.db.soul_role for npc in engine.get_souls()}

# ---- 1. The Kettle advertises social -------------------------------
kettle_hall = next((r for r in search_object("The Kettle - Bath Hall")
                    if r.destination is None), None)
if kettle_hall:
    ads = dict(kettle_hall.db.advertises or {})
    ads["social"] = 0.6
    kettle_hall.db.advertises = ads
    OUT.append(f"ad: {kettle_hall.key}: social=0.6")

# ---- 2. Auntie Lin: ensouled, cart bound to her --------------------
cart = next(iter(search_object("#7530")), None)
lin = next((o for o in (cart.location.contents if cart else [])
            if isinstance(o, Shopkeeper)), None)
if lin and cart and "vendor" not in existing_roles:
    cart.db.post_keeper = lin
    cart.db.post_closed_msg = (
        "The cart is shuttered — coals banked, ladle hung, the tarp "
        "lashed down. Lin's hours are Lin's hours.")
    if lin.tokens is None or lin.tokens == 0:
        lin.tokens = 10
    ok, msg = rental.assign_cube(lin, kiosk)
    home = rental.residence_of(lin)
    ensoul(lin, role="vendor", home=home, post=cart.location,
           schedule="vendor", wage_rate=0.02, venue=cart)
    OUT.append(f"vendor: Auntie Lin (#{lin.id}) post:{cart.location.key} "
               f"home:{home.key if home else 'NONE'} "
               f"kiosk:{'ok' if ok else 'FAILED — ' + msg} "
               f"cart bound + closed-msg set")
elif "vendor" in existing_roles:
    OUT.append("vendor: soul already exists; skipped")

# ---- 3. Kettle attendant (night shift, treasury-paid) --------------
if kettle_hall and "kettle_attendant" not in existing_roles:
    _make_resident(
        role="kettle_attendant",
        post=kettle_hall,
        schedule="night",
        desc=("A colonist gone permanently pink at the collar from steam, "
              "sleeves rolled, a long-handled brush and a wad of rags at "
              "the belt. Moves through the fog like it isn't there."),
        voice="soft, steam-flattened",
        persona={
            "archetype": "colonist",
            "description": ("A steam-pinked attendant of the Kettle bath "
                            "hall, brush in hand, half-seen in the fog."),
            "personality": (
                "Keeps the Kettle through the night shift — skims the "
                "water, chases the mould, minds the quiet. Believes hot "
                "water is the last civic institution left and acts "
                "accordingly. Unhurried; hears a lot and repeats little."),
            "manner": ("low voice under the pipe-noise; short lines; "
                       "never stops working the brush"),
            "wants": ("the water clear, the boiler behaving, and the "
                      "night crowd soaking in peace"),
            "boundaries": ("let anyone foul the water; discuss what the "
                           "regulars say in the steam; touch the boiler "
                           "room politics"),
            "scenario": ("On night shift in the Kettle bath hall, tending "
                         "the water while the colony's late crowd soaks."),
        })

# ---- 4. Snailery hand (day shift, paid from the shell counter) -----
shell = next((o for o in search_object("the shell counter") if o.pk), None)
if shell and "snail_hand" not in existing_roles:
    hand = _make_resident(
        role="snail_hand",
        post=shell.location,
        schedule="day",
        venue=shell,
        desc=("A colonist in a rubberized apron slick to the elbow, "
              "fingers nicked from a thousand shells. Smells of brine, "
              "garlic-weed, and the damp dark of the growing racks."),
        voice="flat, unbothered",
        persona={
            "archetype": "colonist",
            "description": ("A brine-slick hand from the Escallier "
                            "snailery, apron to the elbow."),
            "personality": (
                "Works the racks and the shell counter at the Escallier "
                "snailery. Matter-of-fact about eating snails to a degree "
                "some find upsetting. Proud of the stock the way a farmer "
                "is proud — impersonally, completely."),
            "manner": ("blunt short answers; wipes hands on the apron "
                       "before pointing at anything; quotes prices flat"),
            "wants": ("the racks damp, the counter moving, and nobody "
                      "poking the breeding stock"),
            "boundaries": ("apologize for the product; haggle; let anyone "
                           "in the back rooms"),
            "scenario": ("Behind the shell counter in the snailery yard, "
                         "between rounds of the growing racks."),
        })
    shell.db.post_keeper = hand
    shell.db.post_closed_msg = (
        "The shell counter is bare and wiped down — the hand's off shift, "
        "and the racks keep their own hours.")
    OUT.append("shell counter bound to snail_hand + closed-msg set")

print("BUILD 068: souls phase 2")
for line in OUT:
    print(f"  {line}")
print(f"  souls now: {[(s.key, s.db.soul_role) for s in engine.get_souls()]}")
