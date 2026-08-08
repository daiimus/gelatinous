"""Build 013 — the mast wears antenna tiles, not the vent-box skin.

    evennia shell < scripts/builds/013_brackett_mast_skins.py
    then reload (atlas reads skins from the DB per request, but the
    running server caches the rooms — reload so the change is served).

Owner: a specific park tile for the antenna base, and a repeating
antenna tile for the mast above. The roof-deck centre (the mast's
foot, in the green park) gets `mast_base`; the three mast-column
cells above it get the repeating `mast` lattice, replacing the reused
`machine` (vent-riser) skin.
"""
from evennia.objects.models import ObjectDB

B = "The Brackett Arms"
SKINS = {
    "Roof Deck": "mast_base",              # (-10,-18,16) foot in the park
    "Antenna Mast (Lower)": "mast",        # z17
    "Antenna Mast (Upper)": "mast",        # z18
    "Antenna Platform": "mast",            # z19 (crown of the lattice)
}
done = 0
for suffix, skin in SKINS.items():
    r = ObjectDB.objects.filter(db_key=f"{B} - {suffix}").first()
    if r is not None:
        r.db.atlas_skin = skin
        done += 1
print(f"BUILD 013: {done} mast cells re-skinned "
      f"(base={SKINS['Roof Deck']}, column=mast).")
