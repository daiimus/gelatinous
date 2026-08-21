"""Build 090 — one clothing ladder (#2112).

Layers only ever mattered per body part, so the colony's ad-hoc
numbering was mostly harmless — but a name-driven convention needs
the rungs to mean the same thing everywhere. This moves every
already-spawned garment onto the settled ladder (skin 0, base 1,
mid 2, shell 3, outer 4, accessories 5), then re-dresses anyone whose
outfit would now conflict.

Plates are untouched: they were never on the ladder. They live in a
carrier's plate_slots, an accoutrement rather than a garment.

The visible win: a plate carrier drops from coat height to the vest
rung, so a longcoat finally goes over armour.

Idempotent: garments already on the right rung are skipped.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/090_one_ladder.py
"""

from evennia.objects.models import ObjectDB


import re

#: the convention itself: a garment's NAME places it on the ladder.
#: Checked most-specific rung first so "labcoat" beats "coat".
RUNGS = {
    0: ["bra", "briefs", "boxers", "panties", "thong", "g-string",
        "underwear", "undershirt", "sock", "socks", "stocking",
        "stockings", "tights"],
    5: ["boot", "boots", "shoe", "shoes", "sneaker", "sneakers", "oxford",
        "oxfords", "wader", "waders", "sandal", "sandals", "loafer",
        "heel", "heels", "slipper", "slippers", "clog", "clogs", "belt",
        "tie", "necktie", "scarf", "shawl", "bandana", "bandanna",
        "armband", "badge", "glove", "gloves", "hat", "cap", "helmet",
        "choker", "garter", "garters", "watch", "chrono", "wrap",
        "collar", "earpiece", "goggles"],
    4: ["coat", "labcoat", "trench", "overcoat", "topcoat", "greatcoat",
        "duster", "robe", "apron", "scrubs", "coverall", "parka",
        "bathrobe", "cloak", "poncho"],
    3: ["jacket", "windbreaker", "blazer", "harness", "hood", "slicker",
        "cut"],
    2: ["vest", "waistcoat", "hoodie", "sweater", "jumper", "cardigan",
        "glasses", "sunglasses", "shades", "mirrorshades", "mask",
        "respirator", "rebreather", "balaclava", "carrier", "lenses"],
    1: ["shirt", "tee", "t-shirt", "tshirt", "blouse", "henley", "tank",
        "top", "trousers", "pants", "jeans", "skirt", "dress", "jumpsuit",
        "leggings", "suit", "wig", "bodysuit", "slip"],
}


def rung_for(key):
    low = (key or "").lower()
    for layer in (0, 5, 4, 3, 2, 1):
        for word in RUNGS[layer]:
            if re.search(r"\b" + re.escape(word), low):
                return layer
    return None            # unrecognised: leave whatever it has


moved = 0
for obj in ObjectDB.objects.all():
    cov = obj.attributes.get("coverage") if obj.attributes.has("coverage") else None
    if not cov or not obj.attributes.get("worn_desc"):
        continue                          # not a garment
    target = rung_for(obj.key)
    if target is None or obj.attributes.get("layer") == target:
        continue
    obj.attributes.add("layer", target)
    moved += 1
print(f"BUILD 090: {moved} spawned garments moved onto the ladder")

# re-dress anyone the change could have tangled: strip, then wear from
# the skin out, exactly the order build_npc uses on a fresh body
redressed, stuck = 0, []
for char in ObjectDB.objects.filter(
        db_typeclass_path__icontains="characters.Character"):
    worn = list(dict.fromkeys(
        o for items in (char.worn_items or {}).values() for o in items))
    # also pick up anything wearable they're carrying but not wearing —
    # a garment can be left in hand by a tangled re-dress, and an
    # archived sleeve simply has nothing to put on
    spare = [o for o in char.contents
             if callable(getattr(o, "is_wearable", None)) and o.is_wearable()
             and not char.is_item_worn(o)]
    if not worn and not spare:
        continue
    # strip OUTERMOST first — an inner garment cannot come off while
    # something covers it, and a failed removal leaves the item worn to
    # collide with itself on the way back on
    for garment in sorted(worn, key=lambda g: -int(getattr(g, "layer", 1) or 1)):
        char.remove_item(garment)
    still_on = {o for items in (char.worn_items or {}).values() for o in items}
    for garment in sorted(worn + spare,
                          key=lambda g: int(getattr(g, "layer", 1) or 1)):
        if garment in still_on:
            continue                      # never came off; leave it be
        ok, msg = char.wear_item(garment)
        if not ok and garment in worn:
            # only a garment they HAD on is a failure; a spare that
            # doesn't fit (a second pair of boots) is just a spare
            stuck.append(f"{char.key}: {garment.key} ({msg})")
    redressed += 1
print(f"BUILD 090: re-dressed {redressed} characters")
for line in stuck:
    print(f"   COULD NOT RE-WEAR — {line}")
