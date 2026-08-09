"""Build 030 — the Marlowe Lot construction site (skeleton).

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/030_marlowe_lot_skeleton.py
    then a foreground reload.

Phase 1 of the crane build: the static bones only. A fenced lot on the
empty x=-1 column wedged between South Marlowe Street, Kaspar Urgent
Care and Ramirez — a Boiler Run tower crane rising over it, a ladder up
its mast from the Urgent Care roof to an operator's cab at the 18th
floor, and a Longhaul shipping container hung from the jib, parked at
the 2nd floor for now. The container is an ordinary Room here; Phase 2
retypes it into the moving elevator/edge. No radio, no operator, no
jump edges yet.

FLOOR MAP (house convention floor = z+1):
  2nd floor  = z1   (Urgent Care roof level, container park / boarding)
  13th floor = z12  (Queen of Cups rack-roof level, the safe crossing)
  17th floor = z16  (container ceiling of travel)
  18th floor = z17  (operator's cab)

Re-run-safe: rooms/exits skip if already present.
"""
from evennia import create_object
from evennia.objects.models import ObjectDB

ROOM_TC = "typeclasses.rooms.Room"
SKY_TC = "typeclasses.rooms.SkyRoom"
EXIT_TC = "typeclasses.exits.Exit"

MAST = -1, -18          # the crane tower / ladder column
CONT = -1, -17          # the container's column (parked here)
LOT = -1                # x of the whole site


def at(xyz):
    return next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
                 if r.db.xyz == xyz and r.destination is None), None)


def has_exit(room, key):
    return any(e.key == key for e in room.exits)


def mk_exit(loc, dest, key, aliases=None):
    if loc is None or dest is None or has_exit(loc, key):
        return 0
    create_object(EXIT_TC, key=key, aliases=aliases or [], location=loc,
                  destination=dest)
    return 1


def ensure(xyz, key, tc=ROOM_TC, **attrs):
    r = at(xyz)
    if r is not None:
        return r, False
    r = create_object(tc, key=key)
    r.db.xyz = xyz
    for k, v in attrs.items():
        setattr(r.db, k, v)
    return r, True


made = exits = 0

# ---- 1. the fenced lot at street level (z0) --------------------------
lot_cells = {
    (LOT, -19, 0): ("The Marlowe Lot - Hoarding",
        "The street edge of a construction lot, chained off behind "
        "plywood hoarding gone soft with damp and layered in torn "
        "permits. Through a gap you can see the yard: churned mud, "
        "rebar cages, a Boiler Run tower crane climbing out of it. No "
        "way in from here — the gate's welded."),
    (LOT, -18, 0): ("The Marlowe Lot - Yard",
        "The heart of the lot, directly under the crane. The tower's "
        "foot is bolted to a concrete pad the size of a room, the ladder "
        "running up its spine into the dark. Pallets of block and a "
        "generator that hasn't turned over in a while. Everything is "
        "stamped BOILER RUN."),
    (LOT, -17, 0): ("The Marlowe Lot - Foundation",
        "The dig — a poured foundation bristling with upright rebar, "
        "waiting on a structure that never came. Straight up, the "
        "container sways on its cable. A bad place to land."),
}
lot = {}
for xyz, (key, desc) in lot_cells.items():
    r, new = ensure(xyz, key, type="street", outside=True, is_ground=True,
                    desc=desc)
    lot[xyz] = r
    made += new
# fence the lot together (walkable yard <-> hoarding <-> foundation)
exits += mk_exit(lot[(LOT, -18, 0)], lot[(LOT, -19, 0)], "south", ["s"])
exits += mk_exit(lot[(LOT, -19, 0)], lot[(LOT, -18, 0)], "north", ["n"])
exits += mk_exit(lot[(LOT, -18, 0)], lot[(LOT, -17, 0)], "north", ["n"])
exits += mk_exit(lot[(LOT, -17, 0)], lot[(LOT, -18, 0)], "south", ["s"])

# ---- 2. the mast ladder, z1..z17 -------------------------------------
# z1 = base (entered east off the Urgent Care roof); z17 = operator cab.
mast = {}
for z in range(1, 18):
    if z == 17:
        key = "Boiler Run Crane - Operator's Cab"
        desc = ("The crane cab at the top of the mast, eighteen floors up "
                "on a swaying steel stalk — a cracked vinyl chair, a bank "
                "of levers worn to bare metal, and a long window over the "
                "whole lot. From here the jib reaches out over the dig and "
                "the container hangs off its end. A radio sits in the "
                "console, tuned to the crane's own channel.")
        typ = "rooftop"
    else:
        key = f"Boiler Run Crane - Mast (Deck {z + 1})"
        desc = ("A caged rung landing on the crane mast, wind humming "
                "through the lattice. The ladder goes up and down; the "
                "lot drops away below. Bolted steel, Boiler Run yellow "
                "gone chalky.")
        typ = "rooftop"
    r, new = ensure((MAST[0], MAST[1], z), key, type=typ, outside=True,
                    is_ground=False, desc=desc)
    mast[z] = r
    made += new
# ladder up/down chain
for z in range(1, 17):
    exits += mk_exit(mast[z], mast[z + 1], "up", ["u"])
    exits += mk_exit(mast[z + 1], mast[z], "down", ["d"])

# ---- 3. the only way in: east off the Urgent Care roof ---------------
uc_roof = at((-2, -18, 1))              # Kaspar Urgent Care - Rooftop
assert uc_roof is not None, "Urgent Care rooftop missing at (-2,-18,1)"
exits += mk_exit(uc_roof, mast[1], "east", ["e"])
exits += mk_exit(mast[1], uc_roof, "west", ["w"])

# ---- 4. the container, parked at the 2nd floor (z1) ------------------
# An ordinary Room for now; Phase 2 retypes it to the moving crane car.
container, new = ensure((CONT[0], CONT[1], 1), "Longhaul Container (Crane)",
    type="rooftop", outside=True, is_ground=False,
    desc=("A battered Longhaul shipping container slung level on the "
          "crane's cable, doors chained open into a steel box you can "
          "stand in. Rust streaks, a faded sailing-ship logo, the smell "
          "of cold metal. Right now it sits at the 2nd floor, its open "
          "end level with the Urgent Care roof to the west."))
made += new
# boarding: west <-> Urgent Care roof (North) at the 2nd floor
uc_roof_n = at((-2, -17, 1))            # Kaspar Urgent Care - Rooftop (North)
assert uc_roof_n is not None, "Urgent Care rooftop (north) missing at (-2,-17,1)"
exits += mk_exit(container, uc_roof_n, "west", ["w"])
exits += mk_exit(uc_roof_n, container, "east", ["e"])

# ---- 5. transit + fall rooms for the future jump edge ----------------
# The half-second of the leap toward the Queen of Cups, and the pit you
# hit if you miss. Placed now so Phase 2 only has to wire the exit.
sky, new = ensure((0, -17, 12), "In the Air", tc=SKY_TC,
    type="sky", outside=True, is_ground=False, is_sky_room=True,
    desc=("Open air over the construction lot, high as the Queen of Cups' "
          "rack roof. The container swings somewhere below or beside you; "
          "the dig waits at the bottom."))
made += new
foundation = lot[(LOT, -17, 0)]        # the rebar pit == fall room

print(f"BUILD 030: +{made} rooms, {exits} exits. "
      f"lot z0 x3, mast z1-17 ({mast[1].id}..{mast[17].id}), "
      f"container #{container.id}@z1, sky #{sky.id}, fall #{foundation.id}.")
