"""Build 016 — Hotel Mimi becomes The Halcyon; ground floor reworked.

    evennia shell < scripts/builds/016_halcyon_rename_ground.py
    then foreground reload.

Owner rulings:
  * Rename throughout: Hotel Mimi -> The Halcyon (rooms, terminal,
    residence tags, the jump-edge sky cell). PSL *Halcyon*, a Slowboat
    Interstellar liner, hull SBL-0117, colony-transport bones. Her full
    registered name HALCYON DAYS is painted across the sun deck.
  * Ground floor: too close to Kaspar Pawn & Salvage. Scrap the three
    Halcyon storefronts. Promenade keeps the lobby/stair; the north two
    cells become ground cabins (1B, 1C, leased); the corner against the
    pawn shop (-7,-15) becomes KASPAR SALVAGE — its own place, an exit
    to the pawn shop, NO exit into the Halcyon (connected, not walkable
    between).
"""
from evennia import create_object
from evennia.objects.models import ObjectDB

EXIT_TC = "typeclasses.exits.Exit"
DOOR_TC = "typeclasses.doors.DoorExit"
OLD, NEW = "Hotel Mimi", "The Halcyon"


def at_xyz(xyz):
    return next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
                 if r.db.xyz == xyz and r.destination is None), None)


def drop_exits_between(a, b):
    for e in list(a.exits):
        if e.destination == b:
            e.delete()
    for e in list(b.exits):
        if e.destination == a:
            e.delete()


# ---- 1. bulk rename Hotel Mimi -> The Halcyon ------------------------
renamed = 0
for r in ObjectDB.objects.filter(db_key__startswith=f"{OLD} - "):
    r.key = r.key.replace(OLD, NEW, 1)
    if r.attributes.get("residence_building") == OLD:
        r.db.residence_building = NEW
    renamed += 1
sky = ObjectDB.objects.filter(db_key__icontains="Kaspar Gap").first()
if sky is not None:
    sky.key = "Kaspar Gap (Halcyon–Brackett)"

# ---- exemplar lease door ---------------------------------------------
ex = next(e for e in ObjectDB.objects.filter(
    db_key="The Brackett Arms - Floor 5 Landing").first().exits if e.key == "5A")
EX_LOCKS, EX_DESC = str(ex.locks), ex.db.desc
D_ATTRS = {a.key: a.value for a in ex.attributes.all()
           if a.key in ("is_door", "door_closed", "door_locked",
                        "door_autolock", "door_broken")}


def make_door(loc, dest, key, twin, aliases):
    d = create_object(DOOR_TC, key=key, aliases=aliases, location=loc,
                      destination=dest)
    for k, v in D_ATTRS.items():
        d.attributes.add(k, v)
    d.db.access_grants = []
    d.db.door_twin = twin
    d.db.desc = EX_DESC
    d.locks.add(EX_LOCKS)
    return d


# ---- 2. ground rework ------------------------------------------------
prom = at_xyz((-8, -15, 0))
prom.db.desc = (
    "The Halcyon's promenade deck, salvaged and stood on end: the old "
    "Slowboat liner's grand entry hall, brass gone green, riveted "
    "bulkheads, the ship's name — THE HALCYON — raised over the purser's "
    "desk where a rental terminal now lives. A companionway climbs into "
    "the hull; behind the desk the plating still stencils a struck-out "
    "colony-transport hull number in orange. Cabin doors open off the "
    "hall.")

# 2a. north cells -> ground cabins 1B, 1C (leased)
GROUND_CABS = {(-8, -14, 0): ("1B", "north", "south"),
               (-7, -14, 0): ("1C", "northeast", "southwest")}
ABBR = {"north": "n", "south": "s", "east": "e", "west": "w",
        "northeast": "ne", "southwest": "sw"}
for xyz, (label, d_pc, d_cp) in GROUND_CABS.items():
    cab = at_xyz(xyz)
    cab.key = f"{NEW} - Cabin {label}"
    cab.db.type = None
    cab.db.atlas_skin = "tenement"
    cab.db.desc = (
        "A cabin on the promenade deck of the Halcyon: a fold-down berth, "
        "a basin, a wet cell behind a sliding hatch, and a porthole onto "
        "Kaspar's yard. Ground-level and cheap for it, but dry and yours.")
    cab.attributes.remove("sense_descs") if cab.attributes.has("sense_descs") else None
    cab.db.residence_building = NEW
    cab.db.residence_origin = "Kaspar Street"
    drop_exits_between(prom, cab)
    hall = make_door(prom, cab, label, d_cp, ["door", d_pc, ABBR[d_pc]])
    make_door(cab, prom, d_cp, label, [ABBR[d_cp]])
    cab.db.cube_door = hall

# 2b. corner cell -> Kaspar Salvage (its own; no exit into the Halcyon)
salv = at_xyz((-7, -15, 0))
drop_exits_between(prom, salv)                    # sever from the Halcyon
salv.key = "Kaspar Pawn & Salvage - Back Lot"
salv.db.type = "shop"
salv.db.atlas_skin = "shop"
salv.db.desc = (
    "The back lot of Kaspar Pawn & Salvage, worked into the foot of the "
    "Halcyon's hull: salvage stacked to the deckhead, cable drums and "
    "stripped fittings, a roll-door onto the shop proper. The liner "
    "rises eleven decks overhead; none of it opens down into here.")
for a in ("residence_building", "residence_origin", "cube_door"):
    if salv.attributes.has(a):
        salv.attributes.remove(a)
pawn = ObjectDB.objects.filter(id=5157).first()   # Kaspar Pawn & Salvage
if pawn is not None:
    if not any(e.key == "east" for e in salv.exits):
        create_object(EXIT_TC, key="east", aliases=["e"], location=salv,
                      destination=pawn)
    if not any(e.destination == salv for e in pawn.exits):
        create_object(EXIT_TC, key="west", aliases=["w", "back lot"],
                      location=pawn, destination=salv)

# ---- 3. HALCYON DAYS on the sun deck ---------------------------------
sun = at_xyz((-8, -15, 12))
if sun is not None:
    sun.db.desc = (
        "The Halcyon's sun deck, open to the colony's false sky — the "
        "liner's old lido, plating warped and rails salvaged. Painted "
        "vast across the deck in colonisation-era serif, bleached but "
        "legible from the towers around: HALCYON DAYS. Off the southwest "
        "corner the Brackett's roof garden stands one diagonal leap "
        "across the gap.")

# ---- 4. terminal + cube list -----------------------------------------
term = next((o for o in prom.contents if o.key == "rental terminal"), None)
if term is not None:
    term.db.integration_desc = (
        "A |crental terminal|n sunk into the Halcyon's old purser's desk "
        "lists the vacant cabins.")
    term.db.get_err_msg = "The purser's terminal is bolted to the desk."
    cubes = [r for r in ObjectDB.objects.filter(db_key__startswith=f"{NEW} - Cabin ")
             if r.attributes.get("residence_building") == NEW]
    term.db.cubes = cubes

print(f"BUILD 016: renamed {renamed} rooms Mimi->Halcyon; ground = "
      f"promenade + 2 cabins + Kaspar Salvage (sealed from hotel); "
      f"terminal now {len(term.db.cubes) if term else '?'} cabins.")
