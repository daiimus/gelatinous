"""Build 029 — the Halcyon wears its own hull.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/029_halcyon_liner_skin.py
    then a foreground reload.

Owner: the Halcyon currently borrows the Brackett's tenement sprite; it
should read as what it is — a giant pre-fabricated ship component. New
`liner` sprite family (prefab hull modules with corner frames, flange
seams, portholes, teal boot stripe): every Halcyon cell z0-11 swaps
tenement -> liner; the deck-11 north pair carries the registry
(SBL- / 0117); the four sun-deck tiles go liner_deck, with HALCYON /
DAYS painted flat across the screen-row diagonal pair. Data-only;
re-run-safe.
"""
from evennia.objects.models import ObjectDB


def at(xyz):
    return next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
                 if r.db.xyz == xyz and r.destination is None), None)


# ---- 1. every tenement-skinned Halcyon cell -> liner ------------------
hull = 0
for r in ObjectDB.objects.filter(db_key__startswith="The Halcyon"):
    if r.destination is not None:
        continue
    if r.db.atlas_skin == "tenement":
        r.db.atlas_skin = "liner"
        hull += 1

# ---- 2. the registry across the deck-11 north face --------------------
# +y faces at home view; screen-left is the larger x, so SBL- on -6.
REG = {(-6, -14, 10): "liner_reg_a", (-7, -14, 10): "liner_reg_b"}
reg = 0
for xyz, skin in REG.items():
    r = at(xyz)
    if r is not None:
        r.db.atlas_skin = skin
        reg += 1

# ---- 3. the sun deck: painted steel, HALCYON DAYS ---------------------
# (-6,-14) and (-7,-15) sit on the same screen row (the mirrored right
# axis is the (-1,-1) diagonal); HALCYON reads first from screen-left.
DECK = {(-6, -14, 12): "liner_deck_halcyon",
        (-7, -15, 12): "liner_deck_days",
        (-6, -15, 12): "liner_deck",
        (-7, -14, 12): "liner_deck"}
deck = 0
for xyz, skin in DECK.items():
    r = at(xyz)
    if r is not None:
        r.db.atlas_skin = skin
        deck += 1

print(f"BUILD 029: {hull} hull modules -> liner; {reg} registry tiles; "
      f"{deck} sun-deck tiles.")
