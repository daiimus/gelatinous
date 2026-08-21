"""Build 095 — everyone dresses in some register (#2122).

Style is what turns dressing into a lookup instead of an authored
list. The cast gets theirs written down; everyone else rolls one off
their role, which is the best signal the colony has until the
manifest's departments land.

Garments do NOT need stamping — style derives from the name on read,
so a garment authored tomorrow is sorted the moment it exists.

Idempotent: never overwrites a style already set.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/095_colony_style.py
"""

from world import style as style_mod
from world.souls import engine

#: the cast, by hand — their looks are authored, so their registers
#: should be too
CAST = {
    "Sable Vane": ["shine"],
    "Delphine Marchetti": ["shine", "salvage"],
    "the Rook": ["shine"],
    "Vesper": ["shine"],
    "Bellows": ["street", "salvage"],
    "Auntie Lin": ["workwear", "street"],
    "Ottilie Krug": ["workwear"],
    "Nikolai Kasparov": ["clinical"],
    "Marta Okoye": ["clinical"],
    "Petra": ["uniform"],
    "Ezra Vantomme": ["uniform", "street"],
    "Sully": ["salvage", "street"],
    "Jordan Esparza": ["workwear"],
    "Ossie": ["workwear"],
}

authored = rolled = kept = 0
for soul in engine.get_souls():
    if not soul.pk:
        continue
    if soul.db.style:
        kept += 1
        continue
    if soul.key in CAST:
        soul.db.style = list(CAST[soul.key])
        authored += 1
    else:
        soul.db.style = list(style_mod.roll_style(role=soul.db.soul_role))
        rolled += 1

print(f"BUILD 095: {authored} cast styles authored, {rolled} rolled from "
      f"role, {kept} already had one")
for soul in sorted(engine.get_souls(), key=lambda s: s.key):
    if soul.pk:
        print(f"    {soul.key:<28}{soul.db.style}")
