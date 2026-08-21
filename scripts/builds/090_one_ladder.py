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

#: garment key -> its rung on the settled ladder
LADDER = {
    "black developer hoodie": 3,
    "red face bandana": 5,
    "black wig": 1,
    "blond wig": 1,
    "brown wig": 1,
    "blue jeans": 1,
    "black leather combat boots": 5,
    "plate carrier": 2,
    "armored leather jacket": 3,
    "combat helmet": 5,
    "mining helmet": 5,
    "pit boots": 5,
    "work gloves": 5,
    "hi-vis vest": 2,
    "cargo trousers": 1,
    "knit cap": 5,
    "stopped watch": 5,
    "hawker's apron": 4,
    "company coat": 4,
    "heeled boots": 5,
    "flannel shirt": 1,
    "slit skirt": 1,
    "leather trousers": 1,
    "high-top sneakers": 5,
    "creased trousers": 1,
    "pencil skirt": 1,
    "polished oxfords": 5,
    "corporate necktie": 5,
    "surgical scrubs": 4,
    "white lab coat": 4,
    "tox-sealed slicker": 3,
    "grower's rubber apron": 4,
    "rubber waders": 5,
    "shower sandals": 5,
    "quilted house robe": 4,
    "printed head wrap": 5,
    "midnight evening suit": 1,
    "long knit scarf": 5,
    "wide-brimmed hat": 5,
    "pair of Thawn-Harrison slippers": 5
}

moved = 0
for obj in ObjectDB.objects.filter(db_key__in=list(LADDER)):
    target = LADDER.get(obj.key)
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
    if not worn:
        continue
    for garment in worn:
        char.remove_item(garment)
    for garment in sorted(worn, key=lambda g: int(getattr(g, "layer", 1) or 1)):
        ok, msg = char.wear_item(garment)
        if not ok:
            stuck.append(f"{char.key}: {garment.key} ({msg})")
    redressed += 1
print(f"BUILD 090: re-dressed {redressed} characters")
for line in stuck:
    print(f"   COULD NOT RE-WEAR — {line}")
