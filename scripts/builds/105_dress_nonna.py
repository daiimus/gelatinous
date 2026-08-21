"""Build 105 — clothes under Nonna's apron (#2146).

Third time this pattern has surfaced: an authored NPC was given the
one garment their description mentions — an apron — and nothing else,
so the Wardrobe need reads them as undressed and sends a shopkeeper
off to the thrift instead of to her counter. Lin had it, Petra had it,
now Nonna.

Deliberately unremarkable clothes: this is a mechanical gap, not an
invitation to invent a character who has already been written. Work
shirt, trousers, rubber boots — thirty years of the same thing,
chosen so the apron stays the thing you notice.

Idempotent.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/105_dress_nonna.py
"""

from evennia import create_object
from evennia.utils.search import search_object

from world.souls import needs

OWNER = "#8120"

WARDROBE = [
    {"key": "faded green work shirt",
     "aliases": ["shirt", "work shirt"],
     "desc": ("A soft green work shirt with the sleeves turned back to the "
              "elbow, the cuffs gone pale and the collar given up on "
              "entirely. It smells faintly of garlic-weed and brine."),
     "worn_desc": ("A soft |gfaded green|n work shirt, sleeves turned back "
                   "to the elbow and the collar long since given up on"),
     "coverage": ["chest", "back", "abdomen", "left_arm", "right_arm"],
     "layer": 1, "color": "green", "material": "cotton", "weight": 0.5},
    {"key": "heavy canvas trousers",
     "aliases": ["trousers", "canvas trousers"],
     "desc": ("Stiff canvas trousers worn shiny at the knee from decades "
              "of crouching to the low shell-boards, one pocket mended "
              "with a square of a different canvas entirely."),
     "worn_desc": ("Stiff |ycanvas|n trousers gone shiny at the knee, one "
                   "pocket mended with a square that doesn't match"),
     "coverage": ["groin", "left_thigh", "right_thigh",
                  "left_shin", "right_shin"],
     "layer": 1, "color": "sand", "material": "canvas", "weight": 0.7},
    {"key": "short rubber boots",
     "aliases": ["boots", "rubber boots"],
     "desc": ("Ankle-height rubber boots, once black, now the grey-green "
              "of everything that lives in this yard. They are always "
              "damp and she has stopped noticing."),
     "worn_desc": ("Ankle-height |xrubber boots|n gone the grey-green of "
                   "everything that lives in this yard"),
     "coverage": ["left_foot", "right_foot"],
     "layer": 5, "color": "grey-green", "material": "rubber", "weight": 0.9},
]


def _rung(g):
    lay = getattr(g, "layer", None)
    return 1 if lay is None else int(lay)


nonna = next(iter(search_object(OWNER)), None)
if nonna is None:
    print("BUILD 105: Nonna not found; aborted")
else:
    have = {o.key for o in nonna.contents}
    for spec in WARDROBE:
        if spec["key"] in have:
            continue
        g = create_object("typeclasses.items.Item", key=spec["key"],
                          aliases=spec.get("aliases"), location=nonna,
                          home=nonna)
        for attr in ("desc", "worn_desc", "coverage", "layer", "color",
                     "material", "weight"):
            if spec.get(attr) is not None:
                g.attributes.add(attr, spec[attr])

    # strip outermost-first, then dress from the skin out, so the apron
    # ends up back over the top where it belongs
    worn = list(dict.fromkeys(
        o for items in (nonna.worn_items or {}).values() for o in items))
    for g in sorted(worn, key=lambda x: -_rung(x)):
        nonna.remove_item(g)
    wearable = [o for o in nonna.contents
                if callable(getattr(o, "is_wearable", None)) and o.is_wearable()]
    for g in sorted(wearable, key=_rung):
        nonna.wear_item(g)

    if (nonna.db.soul_job or {}).get("goal") == "wardrobe":
        nonna.db.soul_job = None

    worn_now = sorted({o.key for items in (nonna.worn_items or {}).values()
                       for o in items})
    print(f"BUILD 105: Nonna wears {worn_now}; wardrobe pressure now "
          f"{needs.wardrobe_pressure(nonna)}")
