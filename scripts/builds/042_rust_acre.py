"""Build 042 — Rust Acre, an independent scrapyard (street-level skeleton).

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/042_rust_acre.py
    then a foreground reload.

A fenced junkyard filling the open 4x3 block north of Kaspar Street,
west of the Halcyon, across from the Brackett Arms: x -11..-8, y -13..-15
at street level. One gate off Kaspar Street at (-10,-16) -> (-10,-15);
fenced everywhere else (no other exits = the fence). 12 walkable cells
wired as an internal grid. Atlas skins (scrap_*) are assigned now; the
scrapyard sprites bake in the next pass, so until then the cells render
as plain street. Broad strokes only — a proprietor NPC, a crusher, a
dog, findable salvage all come later. Re-run-safe.

Compass: north = +y, east = +x. Name lives on the gate sign + the room
keys; the cell prose says "the yard", so a rename stays cheap.
"""
from evennia import create_object
from evennia.objects.models import ObjectDB
from world.spatial import get_xyz

ROOM_TC = "typeclasses.rooms.Room"
EXIT_TC = "typeclasses.exits.Exit"

# (x, y): (label, atlas_skin, desc)
CELLS = {
    (-11, -13): ("Northwest Corner", "scrap_nw",
        "The northwest corner of the yard, where the fence turns from "
        "Pessoa Street onto Bhavani Corridor. Scrap stacked head-high "
        "against the chain-link — bumpers, a stove, a hull plate gone to "
        "lace with rust. Two streets on the far side of the wire, and no "
        "way through them."),
    (-10, -13): ("North Fence", "scrap_n",
        "The back of the yard along the Pessoa Street fence, chain-link "
        "sagging under the weight of things hung on it to dry or to be "
        "forgotten. Trodden-dirt paths wind between the heaps."),
    (-9, -13): ("Back Lot", "scrap_n",
        "Deep against the north fence, where the piles are oldest — rust "
        "bloomed into the shapes of whatever they used to be. Kaspar "
        "Street's noise barely carries this far back."),
    (-8, -13): ("Northeast Corner", "scrap_ne",
        "The northeast corner, fence hard against open ground to the east. "
        "A drift of shredded sheet-metal and a bathtub full of bolts; the "
        "Halcyon's hull climbs just past the wire to the south."),
    (-11, -14): ("West Fence", "scrap_w",
        "The west run of the yard along Bhavani Corridor — chain-link and a "
        "windbreak of stacked doors. Traffic mutters past on the far side, "
        "indifferent to any of it."),
    (-10, -14): ("The Heap", "scrap_c",
        "The middle of the yard, and the heart of it: the Heap, a slumping "
        "mountain of salvage picked over so many times it has grown its own "
        "paths and overhangs. Everything here ends up here eventually."),
    (-9, -14): ("Middle Yard", "scrap_c",
        "Open trodden ground in the middle of the yard, ringed by heaps "
        "taller than a person. A shopping cart on its side, a car door, and "
        "the flat smell of wet iron over everything."),
    (-8, -14): ("The Halcyon Wall", "scrap_e",
        "The east edge of the yard, the fence running right up against the "
        "Halcyon's flank — the liner's painted steel makes one wall of the "
        "yard for free. Salvage leans against the hull as if it grew there."),
    (-11, -15): ("Southwest Corner", "scrap_sw",
        "The southwest corner, fence meeting fence where Kaspar Street and "
        "Bhavani Corridor cross beyond the wire. A cairn of engine blocks, "
        "greased black, too heavy for anyone to have bothered stealing."),
    (-10, -15): ("Gate", "scrap_gate",
        "The gate — a chain-link panel rolled back on a bad castor, the only "
        "way in or out. Kaspar Street runs past to the south, the Brackett "
        "Arms filling the sky across it. A hand-painted board wired to the "
        "fence reads RUST ACRE, and under it, smaller: WE BUY / WE DON'T ASK."),
    (-9, -15): ("Weighbridge", "scrap_s",
        "Just inside the gate, a battered weighbridge plate set into the dirt "
        "and a scale with a needle that hasn't been honest in years. This is "
        "where deals get weighed, in more senses than one."),
    (-8, -15): ("Southeast Corner", "scrap_se",
        "The southeast corner, hard against the Halcyon and the Kaspar Street "
        "fence. A tower of crushed cubes and a chained dog-run — empty now "
        "but for a gnawed length of chain and a dented dish."),
}
GATE = (-10, -15)
KASPAR = (-10, -16)     # the Kaspar Street cell the gate opens onto
DIRS = {"north": (0, 1), "south": (0, -1), "east": (1, 0), "west": (-1, 0)}
ALIAS = {"north": ["n"], "south": ["s"], "east": ["e"], "west": ["w"]}


def at(xyz):
    return next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
                 if r.destination is None and get_xyz(r) == xyz), None)


def has_exit(room, key):
    return any(e.key == key for e in room.exits)


def mk_exit(loc, dest, key):
    if loc is None or dest is None or has_exit(loc, key):
        return 0
    create_object(EXIT_TC, key=key, aliases=ALIAS.get(key, []), location=loc,
                  destination=dest)
    return 1


made = exits = 0
rooms = {}
for (x, y), (label, skin, desc) in CELLS.items():
    r = at((x, y, 0))
    if r is None:
        r = create_object(ROOM_TC, key=f"Rust Acre - {label}")
        r.db.xyz = (x, y, 0)
        made += 1
    r.key = f"Rust Acre - {label}"
    r.db.type = "street"
    r.db.outside = True
    r.db.is_ground = True
    r.db.desc = desc
    r.db.atlas_skin = skin
    rooms[(x, y)] = r

# internal 4x3 grid — adjacency only, so the perimeter stays fenced
foot = set(CELLS)
for (x, y) in foot:
    for d, (dx, dy) in DIRS.items():
        n = (x + dx, y + dy)
        if n in foot:
            exits += mk_exit(rooms[(x, y)], rooms[n], d)

# the one gate, off Kaspar Street
kaspar = at((KASPAR[0], KASPAR[1], 0))
assert kaspar is not None, "Kaspar Street cell missing at (-10,-16,0)"
exits += mk_exit(kaspar, rooms[GATE], "north")
exits += mk_exit(rooms[GATE], kaspar, "south")

print(f"BUILD 042: Rust Acre +{made} cells, {exits} exits; gate "
      f"#{kaspar.id}(Kaspar St) <-> #{rooms[GATE].id}(Gate).")
