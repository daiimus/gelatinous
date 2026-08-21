"""Build 092 — the Community Thrift, Southside (#2116).

The shuttered storefront on Kaspar Street has been advertising for a
tenant since before anyone bothered reading the card. Its ghost
outlines — a row of bolted chairs facing where mirrors hung — say it
was a barbershop once: a place that involved sitting still and
trusting somebody. It is that again, differently.

Nobody runs it. Clothes arrive because people leave them and go
because people need them, and the rail never empties, because a
colony that has buried as many as this one always has more coats than
owners.

Mechanically this is where the destitute get dressed: a free
wardrobe advertiser closer to the Brackett than Cryogenics is, so a
broke resident ends up in donated street clothes rather than
Thawn-Harrison paper.

Idempotent.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/092_community_thrift.py
"""

from evennia import create_object
from evennia.utils.search import search_object

ROOM = "#5297"          # Shuttered Storefront, Kaspar Street

#: donated stock — mismatched, unfashionable, free. Deliberately the
#: street/salvage register so the poor read as poor, not as uniformed.
DONATIONS = [
    "FLANNEL_SHIRT", "COTTON_TSHIRT", "THERMAL_SHIRT", "TANK_TOP",
    "CARGO_TROUSERS", "THERMAL_LEGGINGS", "WORK_COVERALLS",
    "BOMBER_JACKET", "DUST_PONCHO", "HOUSE_ROBE",
    "KNIT_CAP", "LONG_SCARF", "HEAD_WRAP", "WIDE_BRIM_HAT",
    "WORK_GLOVES", "HIGH_TOPS", "PIT_BOOTS", "SHOWER_SANDALS",
    # somebody's better days, donated: the bottom of the market still
    # has range, and a soul with taste can find a scrap of it here
    "DRESS_SHIRT", "PENCIL_SKIRT", "SLIT_SKIRT", "MESH_TOP",
]

room = next(iter(search_object(ROOM)), None)
if room is None or not room.pk:
    print("BUILD 092: storefront not found; aborted")
else:
    room.key = "Community Thrift"
    room.db.desc = (
        "The roll-shutter is up for the first time in years and the dust "
        "sheets are gone, though nobody got around to scrubbing the "
        "floor: the ghost outlines are still there, a row of bolted "
        "chairs facing the pale rectangles where mirrors hung. Between "
        "them now runs a long steel rail of donated clothes, sorted by "
        "nothing, sagging in the middle. A bin by the door takes what "
        "you're finished with. The yellowed TO LET card has been turned "
        "over, and on the back somebody has written in marker: TAKE WHAT "
        "YOU NEED. LEAVE WHAT YOU DON'T. There is no counter and nobody "
        "behind it."
    )

    rail = next((o for o in room.contents
                 if o.is_typeclass("typeclasses.shopkeeper.ShopContainer",
                                   exact=False)), None)
    if rail is None:
        rail = create_object("typeclasses.shopkeeper.ShopContainer",
                             key="the free rail", location=room, home=room)
        rail.aliases.add(["rail", "rack", "clothes"])
        rail.locks.add("get:false()")
    rail.db.shop_name = "the Community Thrift"
    rail.db.desc = (
        "A long steel rail bolted between the old mirror mounts, hung "
        "shoulder to shoulder with coats and shirts and work trousers in "
        "every size the colony comes in. Nothing matches. Everything has "
        "been somebody's."
    )
    rail.db.is_infinite = True          # donations always outpace need
    rail.db.register = None             # no till: nothing here is sold
    rail.db.prototype_inventory = {proto: 0 for proto in DONATIONS}
    rail.db.integrate = True
    rail.db.integration_priority = 9
    rail.db.integration_desc = (
        "A long |wsteel rail|n of donated clothes sags between the old "
        "mirror mounts, sorted by nothing."
    )
    ads = dict(rail.db.advertises or {})
    ads["wardrobe"] = 0.95              # beats Cryogenics: free AND kinder
    rail.db.advertises = ads
    rail.tags.add("advertiser", category="souls")

    bin_ = next((o for o in room.contents if "donation" in o.key.lower()), None)
    if bin_ is None:
        bin_ = create_object("typeclasses.items.Item",
                             key="a donation bin", location=room, home=room)
        bin_.aliases.add(["bin", "donations"])
        bin_.locks.add("get:false()")
        bin_.db.desc = (
            "A wheeled laundry bin with the name of a hotel that no "
            "longer exists stencilled on the side, half full of folded "
            "clothes waiting for the rail."
        )
        bin_.db.integrate = True
        bin_.db.integration_priority = 4
        bin_.db.integration_desc = (
            "A wheeled |xdonation bin|n stands inside the door, half full."
        )

    print(f"BUILD 092: {room.key} #{room.id} open — {rail.key} #{rail.id} "
          f"carries {len(DONATIONS)} lines, all free, advertising wardrobe")
