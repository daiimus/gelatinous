"""Build 066 — the Escallier Snailery: ESCARGOT FOR ALL.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/066_escallier_snailery.py
    then a foreground reload.

INTENT (playbook §0): the colony's humblest protein, farmed the humblest
way — a three-generation family snailery on Pessoa's north side,
directly behind Auntie Lin's cart (her supplier lives over the back
fence). Damp shell-boards in a sweating shed, a counter in the yard,
and the family creed painted over the gate: ESCARGOT FOR ALL. The
snailery is deliberately UNBRANDED — the handmade exception to the
brand rule, standing beside the Greenhaus empire on purpose. Ties: food
chain to Lin/Ottilie/Sable; damp-underworld adjacency for the future
Underworks ("the best snails come from below").

    Pessoa (-5,-12) --north--> Yard (-5,-11) --east--> Shell Shed (-4,-11)

Vendor per the Lin recipe (build 048): ShopContainer counter +
Shopkeeper Nonna Escallier (deterministic sales, LLM voice). Re-run-safe.
"""
from evennia import create_object
from evennia.objects.models import ObjectDB
from world.spatial import get_xyz
from typeclasses.shopkeeper import ShopContainer, Shopkeeper

ROOM_TC = "typeclasses.rooms.Room"
EXIT_TC = "typeclasses.exits.Exit"
ALIAS = {"north": ["n"], "south": ["s"], "east": ["e"], "west": ["w"]}


def at(xyz):
    return next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
                 if r.destination is None and get_xyz(r) == xyz), None)


def link(loc, dest, key):
    if loc is None or dest is None or any(e.key == key for e in loc.exits):
        return 0
    create_object(EXIT_TC, key=key, aliases=ALIAS.get(key, []),
                  location=loc, destination=dest)
    return 1


made = exits = 0

yard = at((-5, -11, 0))
if yard is None:
    yard = create_object(ROOM_TC, key="Escallier Snailery - Yard")
    yard.db.xyz = (-5, -11, 0)
    made += 1
yard.key = "Escallier Snailery - Yard"
yard.db.type = "shop"
yard.db.outside = True
yard.db.desc = (
    "A cramped yard off Pessoa's spine, fenced in salvaged grating gone "
    "furry with moss — the only place on the street where the damp is a "
    "crop. Over the gate, on a plank repainted so many times the letters "
    "stand proud of the wood: ESCARGOT FOR ALL. A zinc counter faces the "
    "street under a tarp awning, crates of straw and jars stacked behind "
    "it, and the shell shed sweats quietly at the back. Somewhere beyond "
    "the fence, Auntie Lin's broth pot answers the smell in kind.")
yard.db.sense_descs = {
    "olfactory": "Wet stone, straw, garlic-weed, and under it the clean "
                 "mineral smell of a great many contented snails.",
    "auditory": "Rain-tick of condensation off the tarp, a radio murmuring "
                "in the shed, the faint ceramic click of shells.",
    "atmospheric": "The one corner of Pessoa where the damp feels farmed "
                   "instead of endured.",
}

shed = at((-4, -11, 0))
if shed is None:
    shed = create_object(ROOM_TC, key="Escallier Snailery - Shell Shed")
    shed.db.xyz = (-4, -11, 0)
    made += 1
shed.key = "Escallier Snailery - Shell Shed"
shed.db.type = "shop"
shed.db.outside = False
shed.db.desc = (
    "Dark, warm, and dripping on purpose. Shell-boards rack floor to "
    "ceiling in slow tiers, each one freckled with snails the size of a "
    "baby's fist working their territories of greens and trim — the "
    "vegetable ends of half the street's kitchens come here to be "
    "finished. Drip lines tick along the rafters; a generational ledger "
    "of harvests is pencilled straight onto the doorframe, the oldest "
    "entries gone soft as the wood. Three stools, one lamp, no hurry.")
shed.db.sense_descs = {
    "olfactory": "Deep green damp — cut stems, wet chalk, and the butter "
                 "smell of the grill-pan resting by the door.",
    "auditory": "Drip, click, drip. The loudest thing in the room is the "
                "lamp filament.",
    "tactile": "Every surface is faintly, honestly wet.",
    "atmospheric": "A cellar's peace, one storey above the street.",
}

pessoa = at((-5, -12, 0))
exits += link(pessoa, yard, "north")
exits += link(yard, pessoa, "south")
exits += link(yard, shed, "east")
exits += link(shed, yard, "west")

# ---- the counter: a ShopContainer per the Lin recipe -----------------
counter = next((o for o in yard.contents if isinstance(o, ShopContainer)),
               None)
if counter is None:
    counter = create_object(ShopContainer, key="the shell counter",
                            location=yard, home=yard)
    counter.aliases.add(["counter", "shell counter", "stall"])
counter.db.shop_name = "Escallier Snailery"
counter.db.container_type = "cart"
counter.db.markup_percent = 0
counter.db.is_infinite = True
counter.db.desc = (
    "A zinc-topped counter scrubbed to a dull shine, a hand-lettered "
    "price slate propped against a crate of straw, and a grill-pan at "
    "one end that has known ten thousand snails. The family creed is "
    "burned into the counter's edge in poker-work: ESCARGOT FOR ALL.")
counter.db.integrate = True
counter.db.integration_desc = (
    "A zinc |cshell counter|n stands under a tarp awning, its price "
    "slate chalked and its grill-pan warm.")
counter.db.purchase_msg_buyer = ("Nonna Escallier hands over {item} like a "
                                 "blessing — {price}.")
counter.db.purchase_msg_room = ("{buyer} buys {item} at the Escallier "
                                "counter.")
for proto, price in (("snail_skewer", 3), ("snail_jar", 5)):
    counter.add_prototype(proto, price=price)

# ---- Nonna Escallier: the Shopkeeper ---------------------------------
nonna = next((o for o in yard.contents if isinstance(o, Shopkeeper)), None)
if nonna is None:
    nonna = create_object(Shopkeeper, key="Nonna Escallier", location=yard,
                          home=yard)
    nonna.aliases.add(["nonna", "escallier"])
nonna.sex = "female"
nonna.height = "short"
nonna.build = "wiry"
nonna.db.skintone = "olive"
nonna.sdesc_keyword = "snail-keeper"
nonna.db.desc = (
    "A small wiry woman of indeterminate great age in a brine-stiff "
    "rubber apron, silver hair pinned up with what is unmistakably a "
    "skewer wire. Her hands are pale and water-wrinkled to the wrist, "
    "permanent as a tide line, and her eyes do the arithmetic of you at "
    "a glance — hungry, broke, or both — and soften either way.")
nonna.db.voice_description = "papery, amused, unhurried"
nonna.db.llm_driven = True
nonna.db.llm_persona = {
    "archetype": "colonist",
    "name": "Nonna Escallier",
    "description": (
        "A tiny ancient woman in a brine-stiff rubber apron behind a zinc "
        "counter, a moss-furred yard and a sweating shell shed behind her."),
    "personality": (
        "Third-generation snail farmer; her grandmother raised the first "
        "boards off vegetable trim when the colony was starving and refused "
        "to ever charge more than a shift-worker could pay — the creed over "
        "the gate is the family's whole politics. Patient the way farming "
        "the slowest livestock in the colony teaches. Thinks the big green "
        "towers are clever and soulless. Feeds Lin's pot at a neighbour's "
        "price and knows every kitchen on the street by its trimmings."),
    "manner": (
        "papery, amused; calls everyone 'tesoro'; taps the poker-work creed "
        "when anyone questions a price — downward or upward; will explain "
        "snails at length to anyone who stands still"),
    "wants": (
        "the boards full, the creed kept, a fourth generation someday, and "
        "for nobody on Pessoa to go to bed proteinless"),
    "boundaries": (
        "sell the snailery; raise prices past a worker's pocket; hurry a "
        "snail or a customer; discuss what she pays Lin — family business"),
    "scenario": (
        "At the zinc counter in her yard off Pessoa Street, grill-pan warm, "
        "the shed clicking softly behind her, feeding the shift crowd their "
        "cheapest luxury."),
}
apron = next((o for o in nonna.contents if "apron" in o.key.lower()), None)
if apron is None:
    apron = create_object("typeclasses.items.Item",
                          key="brine-stiff rubber apron", aliases=["apron"],
                          location=nonna, home=nonna)
    apron.db.desc = ("A rubber apron gone stiff and pale with old brine, "
                     "its front pocket holding a shell-knife, chalk, and a "
                     "heel of bread for the boards.")
    apron.db.worn_desc = "a brine-stiff rubber apron"
    apron.db.coverage = ["chest", "abdomen", "left_thigh", "right_thigh"]
    apron.db.layer = 2
    nonna.wear_item(apron)

print(f"BUILD 066: Escallier Snailery — {made} rooms, {exits} exits; "
      f"counter #{counter.id} wares={list(counter.db.prototype_inventory)}; "
      f"Nonna #{nonna.id} llm={nonna.db.llm_driven}. ESCARGOT FOR ALL.")
