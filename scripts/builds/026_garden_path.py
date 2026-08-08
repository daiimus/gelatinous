"""Build 026 — the garden connects the catwalk and the marquee.

    evennia shell < scripts/builds/026_garden_path.py
    then foreground reload.

Owner: the roof garden (#6963) needs to tie the catwalk to the marquee
- a grated service path and a pipe threaded through the greenery. New
garden_path sprite; reskin #6963 onto it. (Marquee window-lightening
and the 6th-floor loggia-band marquee tile are sprite-only, already
baked.)
"""
from evennia.objects.models import ObjectDB
c = ObjectDB.objects.filter(id=6963).first()
c.db.atlas_skin = "garden_path"
print("BUILD 026: #6963 ->", c.db.atlas_skin)
