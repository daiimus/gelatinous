"""Build 017 — shift The Halcyon one cell east, onto Kaspar's Salvage.

    evennia shell < scripts/builds/017_halcyon_shift_onto_kaspar.py
    then foreground reload.

Owner: the two buildings read too close — move the WHOLE Halcyon one
cell east so the hull stands ON TOP of Kaspar Pawn & Salvage (one
stacked structure). The jump survives: roof -> one air room -> landing
tolerates the wider (knight's-move) gap, since the air cell at
(-8,-16,12) still touches both the new sun-deck corner (-7,-15) and
#6963 (-9,-16). Longer leap, so difficulty bumps.

Exits are object-referenced, so the internal structure rides along
with the xyz shift; only the external hooks (street entrance, jump
edge) and two collisions need hands.
"""
from evennia import create_object
from evennia.objects.models import ObjectDB

EXIT_TC = "typeclasses.exits.Exit"
H = "The Halcyon"


def at_xyz(xyz):
    return next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
                 if r.db.xyz == xyz and r.destination is None), None)


def scrap(room):
    if room is None:
        return
    for e in list(room.exits):
        e.delete()
    for e in ObjectDB.objects.filter(db_destination=room):
        e.delete()
    room.delete()


# ---- 1. clear the two collisions -------------------------------------
scrap(ObjectDB.objects.filter(db_key="Kaspar Pawn & Salvage - Back Lot").first())
scrap(ObjectDB.objects.filter(id=6044).first())    # pawn rooftop -> under hull now

# ---- 2. shift every Halcyon room +1 x --------------------------------
shifted = 0
for r in ObjectDB.objects.filter(db_key__startswith=f"{H} - "):
    x, y, z = r.db.xyz
    r.db.xyz = (x + 1, y, z)
    shifted += 1

# ---- 3. re-point the promenade's street entrance ---------------------
prom = ObjectDB.objects.filter(db_key=f"{H} - Promenade").first()   # now (-7,-15,0)
old_k = at_xyz((-8, -16, 0))
new_k = at_xyz((-7, -16, 0))
for e in list(prom.exits):
    if e.destination == old_k:
        e.delete()
if old_k:
    for e in list(old_k.exits):
        if e.destination == prom:
            e.delete()
if new_k and not any(e.key == "south" for e in prom.exits):
    create_object(EXIT_TC, key="south", aliases=["s", "out"],
                  location=prom, destination=new_k)
    create_object(EXIT_TC, key="north", aliases=["n", "the halcyon", "halcyon"],
                  location=new_k, destination=prom)

# ---- 4. re-tune the jump for the wider gap ---------------------------
sun = ObjectDB.objects.filter(db_key=f"{H} - Sun Deck").first()     # now (-7,-15,12)
for e in sun.exits:
    if e.attributes.get("is_edge"):
        e.db.edge_difficulty = 15         # longer leap
        e.db.gap_width = "wide"
gar = ObjectDB.objects.filter(id=6963).first()
for e in gar.exits:
    if e.attributes.get("is_edge"):
        e.key = "east"                    # #6963 -> air is due west... land is NE; face east into the gap
        e.aliases.clear()
        e.aliases.add("e")
        e.db.edge_difficulty = 15
        e.db.gap_width = "wide"

sun_xyz = sun.db.xyz
print(f"BUILD 017: shifted {shifted} Halcyon rooms onto Kaspar's; "
      f"sun deck now {sun_xyz}; entrance re-pointed; jump re-tuned.")
