"""Build 012 — fill out the green roof tiles (owner: chart gaps).

    evennia shell < scripts/builds/012_brackett_roof_fill.py
    then foreground reload.

The strip-model roofs left the green sparse on the atlas. Fill them:
  * Roof proper (z16) to a full walkable 3x3 park — 6 new perimeter
    tiles around the existing centre column (the mast base + stair
    bulkhead stay the centre).
  * North communal shelf (z12 y=-16) to its full 3 cells.
  * South derelict shelf (z12 y=-20) to its full 3 cells — still
    SEALED from the tower (internal walk only; air/climb access is
    future), the repeater on its west cell.
All garden-skinned; the variant seeding meshes them into one parklet.
"""
from evennia import create_object
from evennia.objects.models import ObjectDB

ROOM_TC = "typeclasses.rooms.Room"
EXIT_TC = "typeclasses.exits.Exit"
B = "The Brackett Arms"

made_rooms = made_exits = 0


def room_at(key, xyz=None, skin="garden"):
    global made_rooms
    r = ObjectDB.objects.filter(db_key=key).first()
    if r is None:
        assert xyz is not None, f"new room {key} needs xyz"
        r = create_object(ROOM_TC, key=key)
        r.db.xyz = xyz
        made_rooms += 1
    r.db.type = "rooftop"
    r.db.outside = True
    r.db.is_ground = True
    r.db.atlas_skin = skin
    return r


def wire(cells):
    """Bidirectional cardinal exits between adjacent cells in a dict
    of pos->room."""
    global made_exits
    DIRS = [((0, 1), "north", "n"), ((0, -1), "south", "s"),
            ((1, 0), "east", "e"), ((-1, 0), "west", "w")]
    for (x, y), r in cells.items():
        for (dx, dy), key, alias in DIRS:
            nb = cells.get((x + dx, y + dy))
            if nb is not None and not any(e.key == key for e in r.exits):
                create_object(EXIT_TC, key=key, aliases=[alias],
                              location=r, destination=nb)
                made_exits += 1


# ---- 1. roof proper -> full 3x3 park ---------------------------------
ROOF = {
    (-11, -17): "Roof Deck (Northwest)", (-10, -17): "Roof Deck (North)",
    (-9, -17): "Roof Deck (Northeast)", (-11, -18): "Roof Deck (West)",
    (-10, -18): "Roof Deck", (-9, -18): "Roof Deck (East)",
    (-11, -19): "Roof Deck (Southwest)", (-10, -19): "Roof Deck (South)",
    (-9, -19): "Roof Deck (Southeast)",
}
VIEW = {
    (-11, -17): "the northwest, over the corner of Bhavani and Kaspar",
    (-9, -17): "the northeast, over Kaspar Street and the Boot's hull",
    (-11, -18): "the west, straight down Bhavani Corridor",
    (-9, -18): "the east, over the fire-escape iron and the dead Boot",
    (-11, -19): "the southwest, over Bhavani and Braddock",
    (-9, -19): "the southeast, over Braddock Avenue and the Boot",
}
roof = {}
for pos, suffix in ROOF.items():
    roof[pos] = room_at(f"{B} - {suffix}")
for pos, where in VIEW.items():
    r = roof[pos]
    if not r.db.desc:
        r.db.desc = (
            f"A corner of the Brackett's rooftop park, planted green "
            f"over the plated tar and open to {where}. The mast spikes "
            f"from the deck's centre; the wind has the whole colony to "
            f"play with up here.")
wire(roof)

# ---- 2. north communal shelf -> full strip ---------------------------
north = {
    (-11, -16): room_at(f"{B} - Roof Garden (North)", (-11, -16, 12)),
    (-10, -16): room_at(f"{B} - Roof Garden (North Walk)", (-10, -16, 12)),
    (-9, -16): room_at(f"{B} - Roof Garden (North Corner)", (-9, -16, 12)),
}
for pos, extra in (((-10, -16), "the middle of the north garden walk, "
                    "beds and green either hand"),
                   ((-9, -16), "the east corner of the north garden, "
                    "the trellis giving out onto the Boot's flank")):
    r = north[pos]
    if not r.db.desc:
        r.db.desc = (f"The tenants' north roof garden continues here — "
                     f"{extra}, Kaspar Street's roofscape below the "
                     f"parapet.")
wire(north)

# ---- 3. south derelict shelf -> full strip (still sealed) ------------
south = {
    (-11, -20): room_at(f"{B} - Roof Garden (South, Derelict)", (-11, -20, 12)),
    (-10, -20): room_at(f"{B} - Roof Garden (South, Derelict Walk)", (-10, -20, 12)),
    (-9, -20): room_at(f"{B} - Roof Garden (South, Derelict Corner)", (-9, -20, 12)),
}
for pos, extra in (((-10, -20), "the middle of the ruin, beds burst and "
                    "the trellis down"),
                   ((-9, -20), "the east corner, where a collapsed rail "
                    "hangs out over Braddock")):
    r = south[pos]
    if not r.db.desc:
        r.db.desc = (f"The derelict south garden runs on — {extra}. No "
                     f"stair, no ladder; the ways up are still only the "
                     f"ones you bring.")
wire(south)          # internal walk only — NO exit to the tower by design

print(f"BUILD 012: {made_rooms} tiles, {made_exits} exits; roof proper "
      f"now {len(roof)}/9, shelves 3+3.")
