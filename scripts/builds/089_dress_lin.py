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
    have = {o.key for o in lin.contents}
    dressed = []
    for gspec in sorted(BLUEPRINTS["vendor_lin"].get("wardrobe", ()),
                        key=lambda g: int(g.get("layer", 1) or 1)):
        if gspec["key"] in have:
            continue
        garment = create_object("typeclasses.items.Item", key=gspec["key"],
                                aliases=gspec.get("aliases"), location=lin,
                                home=lin)
        for attr in ("desc", "worn_desc", "coverage", "layer", "color",
                     "material", "weight", "category"):
            if gspec.get(attr) is not None:
                garment.attributes.add(attr, gspec[attr])
        ok, msg = lin.wear_item(garment)
        dressed.append(f"{gspec['key']}{'' if ok else ' (FAILED: %s)' % msg}")
    # she may be mid-errand to the dispenser; that plan is now moot
    if (lin.db.soul_job or {}).get("goal") == "wardrobe":
        lin.db.soul_job = None
    from world.souls import needs
    print(f"BUILD 089: dressed Lin — {', '.join(dressed) or 'nothing to add'}; "
          f"wardrobe pressure now {needs.wardrobe_pressure(lin)}")
