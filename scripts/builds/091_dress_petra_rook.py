"""Build 091 — clothes for Petra and the Rook (#2114).

Two more cast members whose blueprints predated the wardrobe key, so
they read as undressed to the Wardrobe need. Petra was standing at
the dispatch console holding two pairs of jeans and wearing neither.

Petra dresses like twenty years at a console: charcoal duty shirt and
trousers, boots polished only on the toes a seated woman can reach,
a single-ear headset bent to a shape only she finds comfortable, and
the grey cardigan regulation never mentioned and therefore never took
away.

The Rook dresses for an audience that will never see her — her own
description says a style for nobody, kept immaculate anyway. Black
silk, sharp crepe trousers, broadcast cans with one cup pushed off an
ear, and shoes chosen for silence, because nothing she wears may ever
reach the microphone.

Idempotent: skips garments they already own.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/091_dress_petra_rook.py
"""

from evennia import create_object

from world.npcs.blueprints import BLUEPRINTS
from world.souls import engine, needs


def _rung(garment):
    lay = getattr(garment, "layer", None)
    return 1 if lay is None else int(lay)


for bp_key, name in (("dispatch_petra", "Petra"), ("dj_rook", "the Rook")):
    who = next((s for s in engine.get_souls() if s.pk and s.key == name), None)
    if who is None:
        print(f"BUILD 091: {name} not found among the souls; skipped")
        continue

    have = {o.key for o in who.contents}
    for gspec in BLUEPRINTS[bp_key].get("wardrobe", ()):
        if gspec["key"] in have:
            continue
        garment = create_object("typeclasses.items.Item", key=gspec["key"],
                                aliases=gspec.get("aliases"), location=who,
                                home=who)
        for attr in ("desc", "worn_desc", "coverage", "layer", "color",
                     "material", "weight", "category", "style"):
            if gspec.get(attr) is not None:
                garment.attributes.add(attr, gspec[attr])

    # strip outermost-first, then dress from the skin out
    worn = list(dict.fromkeys(
        o for items in (who.worn_items or {}).values() for o in items))
    for garment in sorted(worn, key=lambda g: -_rung(g)):
        who.remove_item(garment)
    still_on = {o for items in (who.worn_items or {}).values() for o in items}
    wearable = [o for o in who.contents
                if callable(getattr(o, "is_wearable", None)) and o.is_wearable()]
    # her own clothes outrank whatever she happened to be carrying:
    # Petra was holding two stray pairs of jeans, and at equal rung the
    # jeans won on alphabetical order and blocked her uniform trousers
    own = {g["key"] for g in BLUEPRINTS[bp_key].get("wardrobe", ())}
    dressed = []
    for garment in sorted(wearable, key=lambda g: (_rung(g),
                                                   0 if g.key in own else 1)):
        if garment in still_on:
            continue
        ok, _msg = who.wear_item(garment)
        if ok:
            dressed.append(garment.key)

    if (who.db.soul_job or {}).get("goal") == "wardrobe":
        who.db.soul_job = None
    print(f"BUILD 091: {name} wears {', '.join(dressed)}; "
          f"wardrobe pressure now {needs.wardrobe_pressure(who)}")
