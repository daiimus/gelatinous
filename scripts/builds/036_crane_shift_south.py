"""Build 036 — move the crane one room south; extend the jib.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/036_crane_shift_south.py
    then a foreground reload.

Two fixes:
  (1) The mast base didn't connect to the mast above (a floating gap) —
      the redesigned crane_base sprite now roots the lattice in the pad.
  (2) Move the mast/ladder/cab column from (-1,-18) to (-1,-19) so the
      jib cantilevers TWO cells north to the container (a real tower-crane
      overhang) instead of one. New jib-arm + jib-tip cells carry the boom
      out over the lot to the hook above the container.

Access follows the ladder: its base moves to (-1,-19,1), so the way up is
now EAST off the Ramirez Market rooftop (-2,-19,1) — which connects to the
Urgent Care roof, so the crane stays reachable. Container boarding is
unchanged (still the Urgent Care roof, north side).

Re-run-safe.
"""
from evennia import create_object
from evennia.objects.models import ObjectDB
from world.spatial import get_xyz, set_xyz

SKY_TC = "typeclasses.rooms.SkyRoom"
EXIT_TC = "typeclasses.exits.Exit"


def at(xyz):
    return next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
                 if r.destination is None and get_xyz(r) == xyz), None)


def drop_exit(room, key, dest=None):
    for e in list(room.exits):
        if e.key == key and (dest is None or e.destination == dest):
            e.delete()


def mk_exit(loc, dest, key, aliases=None):
    if loc is None or dest is None or any(e.key == key for e in loc.exits):
        return 0
    create_object(EXIT_TC, key=key, aliases=aliases or [], location=loc,
                  destination=dest)
    return 1


# ---- 1. shift the mast/ladder/cab column -18 -> -19 ------------------
# Move top-down so we never collide with an occupied target cell.
moved = 0
for z in range(17, 0, -1):
    r = at((-1, -18, z))
    if r is not None and get_xyz(r) == (-1, -18, z):
        set_xyz(r, -1, -19, z)
        moved += 1
mast_base = at((-1, -19, 1))            # was the ladder foot
cab = at((-1, -19, 17))

# ---- 2. rewire the ladder entry to the Market rooftop ---------------
uc = at((-2, -18, 1))                   # Kaspar Urgent Care - Rooftop
market = at((-2, -19, 1))               # Ramirez Market rooftop
if mast_base is not None:
    if uc is not None:
        drop_exit(uc, "east", mast_base)
    drop_exit(mast_base, "west")        # old link back to the UC roof
    mk_exit(mast_base, market, "west", ["w"])
    mk_exit(market, mast_base, "east", ["e"])

# ---- 3. the ground: base now at -19, hoarding/yard at -18 -----------
base_g = at((-1, -19, 0))               # was Hoarding
mid_g = at((-1, -18, 0))                # was Yard
if base_g is not None:
    base_g.db.atlas_skin = "crane_base"
    base_g.key = "The Marlowe Lot - Crane Base"
    base_g.db.desc = (
        "The foot of the Boiler Run tower crane — a concrete pad the size "
        "of a room, the mast bolted to it and climbing out of sight. A "
        "dead generator, pallets of block, churned mud. Hoarding walls it "
        "off from Braddock Avenue to the south.")
if mid_g is not None:
    mid_g.db.atlas_skin = "crane_lot"
    mid_g.key = "The Marlowe Lot - Yard"
    mid_g.db.desc = (
        "The open yard under the crane's jib, boxed in by plywood "
        "hoarding — churned mud, stacked material, the long shadow of the "
        "boom overhead swinging its load between the mast and the dig.")

# ---- 4. the jib reaches out: arm over -18, tip over -17 -------------
def ensure_sky(xyz, skin, desc):
    r = at(xyz)
    if r is None:
        r = create_object(SKY_TC, key="In the Air")
        r.db.xyz = xyz
        r.db.type = "sky"
        r.db.is_sky_room = True
        r.db.outside = True
    r.db.atlas_skin = skin
    r.db.desc = desc
    return r


arm = ensure_sky((-1, -18, 17), "crane_jib",
    "High over the lot: the crane's jib, a lattice boom cantilevering out "
    "from the mast, wind singing in the steel. Nothing under it but air.")
tip = ensure_sky((-1, -17, 17), "crane_jibtip",
    "The far end of the crane's jib, right over the container's shaft — the "
    "trolley and sheave, and the hoist cable dropping away to the box below.")

print(f"BUILD 036: moved {moved} mast cells to -19; base #{base_g.id if base_g else '?'}, "
      f"cab #{cab.id if cab else '?'}@{get_xyz(cab) if cab else '?'}; "
      f"jib arm #{arm.id}, tip #{tip.id}; entry via Market #{market.id if market else '?'}.")
