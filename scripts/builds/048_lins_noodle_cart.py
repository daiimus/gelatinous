"""Build 048 — Auntie Lin's noodle cart on Pessoa Street (full vendor).

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/048_lins_noodle_cart.py
    then a foreground reload.

A working food vendor for the industrial spine, two cells east of the
shrine at (-4,-12): a ShopContainer cart stocked with handmade worker
food (build 048 prototypes), and Auntie Lin, a Shopkeeper NPC — sales
deterministic through the counter, voice through the LLM (live). Re-run-
safe.
"""
from evennia import create_object
from evennia.objects.models import ObjectDB
from world.spatial import get_xyz
from typeclasses.shopkeeper import ShopContainer, Shopkeeper

room = next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
             if r.destination is None and get_xyz(r) == (-4, -12, 0)), None)
assert room is not None, "Pessoa cart cell (-4,-12,0) not found"

room.db.desc = (
    "The street draws in around a noodle cart, its steam a warm smudge under "
    "the lanterns and the industrial haze. A steel counter on bicycle wheels, "
    "a broth pot the size of a drum going day and night, stools chained to the "
    "frame so they don't walk. This is where Pessoa eats between shifts — you "
    "can smell it two blocks off.")
room.db.sense_descs = {
    "olfactory": "Star-scorched broth, chili oil, and coal smoke — the good "
                 "smell of the whole street.",
    "auditory": "The broth's low boil, a ladle knocking the pot, the murmur "
                "of tired people being fed.",
    "atmospheric": "The one warm corner on a cold spine of a street.",
}

# ---- the cart: a ShopContainer stocked with worker food -------------
cart = next((o for o in room.contents if isinstance(o, ShopContainer)), None)
if cart is None:
    cart = create_object(ShopContainer, key="Lin's noodle cart", location=room,
                         home=room)
    cart.aliases.add(["cart", "noodle cart", "counter", "stall"])
cart.db.shop_name = "Lin's"
cart.db.container_type = "cart"
cart.db.markup_percent = 0          # prices set explicitly below
cart.db.is_infinite = True
cart.db.desc = (
    "A steel counter cart, dented and scoured bright at the elbows, a broth "
    "pot bubbling at one end and a bamboo steamer stacked at the other. A "
    "grease-pencil menu is chalked on a board wired to the front: noodles, "
    "buns, skewers, tea — the whole economy of a shift.")
cart.db.integrate = True
cart.db.integration_desc = (
    "A steel |cnoodle cart|n steams at the kerb, its broth pot going and a "
    "chalked menu wired to the front.")
cart.db.purchase_msg_buyer = "Lin ladles up {item} and passes it over — {price}."
cart.db.purchase_msg_room = "{buyer} buys {item} off Lin's cart."
PRICES = {"pessoa_noodles": 6, "pessoa_bun": 4, "pessoa_skewer": 3,
          "pessoa_tea": 2}
for proto, price in PRICES.items():
    cart.add_prototype(proto, price=price)

# ---- Auntie Lin: the Shopkeeper (deterministic sales, LLM voice) ----
lin = next((o for o in room.contents if isinstance(o, Shopkeeper)), None)
if lin is None:
    lin = create_object(Shopkeeper, key="Auntie Lin", location=room, home=room)
    lin.aliases.add(["lin", "auntie", "auntie lin"])
lin.sex = "female"
lin.height = "short"
lin.build = "stocky"
lin.db.skintone = "tan"
lin.sdesc_keyword = "vendor"
lin.db.desc = (
    "A short, solid woman gone grey at the temples, sleeves shoved past the "
    "elbow over forearms roped from thirty years of lifting the pot. A scalded "
    "apron, a ladle she uses like a pointer, and eyes that price you, feed "
    "you, and forgive you the difference in about that order.")
lin.db.voice_description = "warm, smoke-worn"
lin.db.llm_driven = True
lin.db.llm_persona = {
    "archetype": "colonist",
    "name": "Auntie Lin",
    "description": (
        "A short, stocky woman grey at the temples in a scalded apron, ladle "
        "in hand, steam and lantern-light around her."),
    "personality": (
        "Thirty years on the same corner ladling the same broth. Warm the way "
        "a stove is warm — steady, a little smoke-blackened. Remembers every "
        "regular's order and half their troubles, and is dry about both. Feeds "
        "the ones who can't pay this week and remembers that too."),
    "manner": (
        "short warm lines; calls people 'love' or by their order ('noodles, no "
        "chili'); wipes the counter while she talks; the price is the price"),
    "wants": (
        "the broth to never run out, her regulars fed, and one shift where "
        "nobody she knows goes into the processor"),
    "boundaries": (
        "haggle — the price is the price; leave the cart; pretend she can't "
        "see what the street's become"),
    "scenario": (
        "At her noodle cart on Pessoa Street under the lanterns, near the "
        "forgotten saint, feeding the shift crowd. People order, gripe, and "
        "confess over the counter."),
}
apron = next((o for o in lin.contents if "apron" in o.key.lower()), None)
if apron is None:
    apron = create_object("typeclasses.items.Item", key="scalded canvas apron",
                          aliases=["apron"], location=lin, home=lin)
    apron.db.desc = ("A heavy canvas apron scalded pale down the front, pockets "
                     "sagging with a ladle, chalk, and a rag.")
    apron.db.worn_desc = "a scalded canvas apron, pockets sagging"
    apron.db.coverage = ["chest", "abdomen", "left_thigh", "right_thigh"]
    apron.db.layer = 2
    lin.wear_item(apron)

print(f"BUILD 048: cart #{cart.id} wares={list(cart.db.prototype_inventory)}; "
      f"Lin #{lin.id} llm={lin.db.llm_driven} merchant={lin.db.is_merchant}.")
