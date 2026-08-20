"""Build 083 — Ottilie's cart joins the hunger advertisers (#2086).

The butcher's cart predates the souls engine and was missed in the
advertiser conversion, leaving the colony's only swing-shift food
vendor invisible to the planner — a 14:00-06:00 food blackout that
put most of the town in the grim band. Same stamp as builds 048/082.

Idempotent: re-runs re-mirror the same values.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/083_ottilie_cart_advertises.py
"""

from evennia.utils.search import search_object

CART_ID = "#5221"              # a hull-plate food cart, Hammett's Boot - Toe

cart = next(iter(search_object(CART_ID)), None)
if cart is None or not cart.pk:
    print("BUILD 083: cart not found; aborted")
else:
    ads = dict(cart.db.advertises or {})
    ads["hunger"] = 0.9
    cart.db.advertises = ads
    cart.tags.add("advertiser", category="souls")
    print(f"BUILD 083: {cart.key} #{cart.id} advertises hunger "
          f"({cart.location.key}); the swing shift eats again")
