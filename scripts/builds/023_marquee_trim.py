"""Build 023 — trim the marquee run to the top 6 floors.

    evennia shell < scripts/builds/023_marquee_trim.py
    then foreground reload.

Owner: shorten the sign from the whole flank to ~5-6 tiles. Keep the
marquee on the Brackett's NE corner at z6-11 (6 tiles, just under the
#6963 crossing); revert z1-5 to the plain tenement face.
"""
from evennia.objects.models import ObjectDB


def at(xyz):
    return next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
                 if r.db.xyz == xyz and r.destination is None), None)


reverted = 0
for z in range(1, 6):                      # z1-5 back to tenement
    c = at((-9, -16, z))
    if c is not None and c.attributes.get("atlas_skin") == "marquee":
        c.attributes.remove("atlas_skin")  # -> SKINS "The Brackett Arms" -> tenement
        reverted += 1
kept = sum(1 for z in range(6, 12)
           if (lambda c: c and c.attributes.get("atlas_skin") == "marquee")(at((-9, -16, z))))
print(f"BUILD 023: reverted {reverted} lower cells; marquee kept on "
      f"{kept} tiles (z6-11).")
