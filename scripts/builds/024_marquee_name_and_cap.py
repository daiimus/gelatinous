"""Build 024 — the marquee reads BRACKETT ARMS; garden/marquee/catwalk
combine at the cap.

    evennia shell < scripts/builds/024_marquee_name_and_cap.py
    then foreground reload.

Owner: (1) the catwalk is halved (subtle) [sprite]; (2) the #6963 roof
tile combines garden + marquee + catwalk into one comprehensive unit;
(3) the marquee just says BRACKETT ARMS, down the flank, in Monaspace
Xenon. So the sign is the building's own name now, not the terraform
ad. Skins map the six lettered tiles top-to-bottom to spell it.
"""
from evennia.objects.models import ObjectDB


def at(xyz):
    return next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
                 if r.db.xyz == xyz and r.destination is None), None)


# ---- the roof cap: garden + marquee + catwalk in one ------------------
cap = ObjectDB.objects.filter(id=6963).first()          # -9,-16,12
cap.db.atlas_skin = "garden_cap"

# ---- the name reads down the flank (top z11 -> bottom z6) -------------
LETTERS = {11: "marquee_br", 10: "marquee_ac", 9: "marquee_ke",
           8: "marquee_tt", 7: "marquee_ar", 6: "marquee_ms"}
named = 0
for z, skin in LETTERS.items():
    c = at((-9, -16, z))
    if c is not None:
        c.db.atlas_skin = skin
        named += 1

# ---- prose: the marquee is the building's name now -------------------
perch = at((-8, -16, 12))
perch.db.desc = (
    "A little maintenance catwalk slung over Kaspar Street between the "
    "Brackett Arms and the Halcyon — a scrap of grating and a rail, a "
    "long drop past it. Down the Brackett's corner beside you the "
    "building runs its own name in green: BRACKETT ARMS, letter over "
    "letter down the flank in old slab-cut light. You cross from the "
    "Brackett's roof to the Halcyon's deck.")
proj = next((o for o in perch.contents
             if o.key in ("holo-marquee", "holo-billboard")), None)
if proj is not None:
    proj.key = "holo-marquee"
    proj.db.desc = (
        "The head of the Brackett Arms' holo-marquee, bolted to the "
        "corner and spelling the building's name straight down the flank "
        "in Monaspace slab: B-R-A-C-K-E-T-T, then A-R-M-S, each letter a "
        "green pane of light. Half the panes flicker; nobody's fixed a "
        "marquee in this colony in a long time.")
    proj.db.integration_desc = (
        "A |gholo-marquee|n runs the building's name down the Brackett's "
        "corner, letter over letter in green.")

print(f"BUILD 024: roof cap set; {named} lettered marquee tiles "
      f"(BRACKETT ARMS, z11->z6).")
