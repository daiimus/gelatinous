"""Build 025 — even letter spacing, plain garden cap, aligned catwalk.

    evennia shell < scripts/builds/025_marquee_spacing_cap.py
    then foreground reload.

Owner: (1) letters closer/even with a real word gap [sprite]; (2) the
combined garden-cap 'top floor square' looks weird — revert #6963 to
plain garden; (3) catwalk lowered to the roof surface and pushed at
the garden so they read as one architecture [sprite]. Here we swap the
skins: #6963 -> garden, and the flank tiles -> the evenly-spaced
lettered set (z11..z6 = BRACKETT / ARMS).
"""
from evennia.objects.models import ObjectDB


def at(xyz):
    return next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
                 if r.db.xyz == xyz and r.destination is None), None)


ObjectDB.objects.filter(id=6963).first().db.atlas_skin = "garden"   # plain again

LETTERS = {11: "marquee_1", 10: "marquee_2", 9: "marquee_3",
           8: "marquee_4", 7: "marquee_5", 6: "marquee_6"}
n = 0
for z, skin in LETTERS.items():
    c = at((-9, -16, z))
    if c is not None:
        c.db.atlas_skin = skin
        n += 1

print(f"BUILD 025: #6963 -> plain garden; {n} flank tiles reskinned to "
      f"the evenly-spaced BRACKETT ARMS run.")
