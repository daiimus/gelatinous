"""Build 008 — the seam band (owner: keep the atlas look post-007).

    evennia shell < scripts/builds/008_brackett_seam_band.py
    then foreground reload (mapping.py changed anyway).

Floor 6 standardized as housing but remains the building's seam —
the top of the old pour. The owner liked the glass band the loggia
motif gave the flank, so the look survives as pure map cosmetics:
`db.atlas_skin = "loggia"` on every floor-6 cell wraps the whole
sixth storey in the banded look, a ring at the seam line. atlas_skin
is the new cosmetic override (export_map ships it; both atlases
check it first) — it never touches the gameplay `type`.
"""
from evennia.objects.models import ObjectDB

B = "The Brackett Arms"
stamped = 0
for r in ObjectDB.objects.filter(db_key__contains=B):
    xyz = r.attributes.get("xyz")
    if "Elevator Car" in r.key:
        continue                  # the car carries an xyz; no skin rides it
    if (xyz and xyz[2] == 6 and -11 <= xyz[0] <= -9
            and -20 <= xyz[1] <= -16 and r.destination is None):
        r.db.atlas_skin = "loggia"
        stamped += 1
print(f"BUILD 008: seam band stamped on {stamped} floor-6 cells.")
