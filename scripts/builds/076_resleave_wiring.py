"""Build 076 — resleave wiring: blueprints attach to their posts.

Lin's cart learns which blueprint rebuilds its keeper (vendor_lin —
her policy stays whatever the owner rules; attaching the recipe is
harmless data). The premium's destination is Maxwell's billing
terminal, found by key at resleave time — nothing to wire there.

Idempotent: attribute re-mirrors.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/076_resleave_wiring.py
"""

from evennia.utils.search import search_object

cart = next(iter(search_object("#7530")), None)
if cart is None:
    print("BUILD 076: cart not found; aborted")
else:
    cart.db.post_blueprint = "vendor_lin"
    print(f"BUILD 076: {cart.key} post_blueprint=vendor_lin "
          f"(policy stays {cart.db.post_policy!r} pending owner roster)")
