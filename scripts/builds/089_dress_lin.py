"""Build 089 — clothes under Auntie Lin's apron (#2110).

Lin predates the blueprint registry, so build 048 gave her an apron
and nothing else. To the wardrobe need that reads as undressed, and
she was on her way to Cryogenics for a paper jumpsuit. Her blueprint
now carries the clothes she has presumably always worn; this puts
them on the woman currently standing at the cart.

Idempotent: skips any garment she already has.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/089_dress_lin.py
"""

from evennia import create_object

from world.npcs.blueprints import BLUEPRINTS
from world.souls import engine

lin = next((s for s in engine.get_souls() if s.pk and s.key == "Auntie Lin"),
           None)
if lin is None:
    print("BUILD 089: Auntie Lin not found among the souls; aborted")
else:
    # 1. create any blueprint garment she doesn't already own
    have = {o.key for o in lin.contents}
    for gspec in BLUEPRINTS["vendor_lin"].get("wardrobe", ()):
        if gspec["key"] in have:
            continue
        garment = create_object("typeclasses.items.Item", key=gspec["key"],
                                aliases=gspec.get("aliases"), location=lin,
                                home=lin)
        for attr in ("desc", "worn_desc", "coverage", "layer", "color",
                     "material", "weight", "category"):
            if gspec.get(attr) is not None:
                garment.attributes.add(attr, gspec[attr])

    # 2. strip: nothing goes on UNDER an already-worn outer layer, which
    #    is why the apron alone blocked her whole base layer
    for garment in list(dict.fromkeys(
            o for items in (lin.worn_items or {}).values() for o in items)):
        lin.remove_item(garment)

    # 3. dress from the skin out, her own clothes ahead of the paper
    #    issue she picked up at Cryogenics (kept, not destroyed — it is
    #    hers now, it just isn't what she wears)
    def _order(g):
        issue = "Thawn-Harrison" in g.key
        return (1 if issue else 0, int(getattr(g, "layer", 1) or 1))

    wearable = [o for o in lin.contents
                if callable(getattr(o, "is_wearable", None)) and o.is_wearable()]
    dressed, spare = [], []
    for garment in sorted(wearable, key=_order):
        ok, _msg = lin.wear_item(garment)
        (dressed if ok else spare).append(garment.key)

    # she may be mid-errand to the dispenser; that plan is now moot
    if (lin.db.soul_job or {}).get("goal") == "wardrobe":
        lin.db.soul_job = None
    from world.souls import needs
    print(f"BUILD 089: Lin wears {', '.join(dressed)}"
          + (f"; carrying spare: {', '.join(spare)}" if spare else "")
          + f"; wardrobe pressure now {needs.wardrobe_pressure(lin)}")
