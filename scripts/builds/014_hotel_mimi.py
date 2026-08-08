"""Build 014 — Hotel Mimi, a reclaimed passenger liner (owner-designed).

    evennia shell < scripts/builds/014_hotel_mimi.py
    then foreground reload.

A cruise liner / passenger transport, salvaged and stood on its end
by Kaspar Pawn & Salvage, converted to residences. 12 decks on a 2x2
footprint (x -8/-7, y -15/-14) — the open lots clear to z12:
  Deck 1  (z0)   = the Promenade: lobby + three storefronts (a bar,
                   Flashtemp miner supply, a pharmacy), NO cabins.
  Decks 2-12     = a companionway Landing + three 1-room cabins each
   (z1-z11)        (33 leases), wired like the Brackett (spring-latch
                   DoorExits, residence attrs, its own RentalTerminal).
  Sun Deck (z12) = the top deck, roof at z12 — aligns with the Brackett
                   Roof Garden #6963 for a diagonal jump (wired in 015).
Stairs only (a walk-up); entry off Kaspar Street.
"""
from evennia import create_object
from evennia.objects.models import ObjectDB

ROOM_TC = "typeclasses.rooms.Room"
EXIT_TC = "typeclasses.exits.Exit"
DOOR_TC = "typeclasses.doors.DoorExit"
TERM_TC = "typeclasses.terminals.RentalTerminal"
M = "Hotel Mimi"

STAIR = (-8, -15)                         # SW: promenade/landing column
FLATS = {(-7, -15): "A", (-8, -14): "B", (-7, -14): "C"}
ABBR = {"north": "n", "south": "s", "east": "e", "west": "w",
        "northeast": "ne", "northwest": "nw",
        "southeast": "se", "southwest": "sw"}
OPP = {"north": "south", "south": "north", "east": "west", "west": "east",
       "northeast": "southwest", "southwest": "northeast",
       "northwest": "southeast", "southeast": "northwest"}


def d_name(fr, to):
    dy, dx = to[1] - fr[1], to[0] - fr[0]
    return ("north" if dy > 0 else "south" if dy < 0 else "") + \
           ("east" if dx > 0 else "west" if dx < 0 else "")


made_rooms = made_exits = made_doors = 0


def room_at(key, xyz, rtype=None, outside=False, skin=None, ground=False):
    global made_rooms
    r = ObjectDB.objects.filter(db_key=key).first()
    if r is None:
        r = create_object(ROOM_TC, key=key)
        r.db.xyz = xyz
        made_rooms += 1
    r.db.type = rtype
    r.db.outside = outside
    if ground:
        r.db.is_ground = True
    if skin:
        r.db.atlas_skin = skin
    return r


def mk_exit(loc, dest, key, aliases=None):
    global made_exits
    if any(e.key == key for e in loc.exits):
        return
    create_object(EXIT_TC, key=key, aliases=aliases or [], location=loc,
                  destination=dest)
    made_exits += 1


# exemplar lease door (Brackett Unit 5A hall-side)
ex = next(e for e in ObjectDB.objects.filter(
    db_key="The Brackett Arms - Floor 5 Landing").first().exits if e.key == "5A")
EX_LOCKS = str(ex.locks)
EX_DESC = ex.db.desc
DOOR_ATTRS = {a.key: a.value for a in ex.attributes.all()
              if a.key in ("is_door", "door_closed", "door_locked",
                           "door_autolock", "door_broken")}


def make_door(loc, dest, key, twin_key, aliases):
    global made_doors
    d = create_object(DOOR_TC, key=key, aliases=aliases, location=loc,
                      destination=dest)
    for k, v in DOOR_ATTRS.items():
        d.attributes.add(k, v)
    d.db.access_grants = []
    d.db.door_twin = twin_key
    d.db.desc = EX_DESC
    d.locks.add(EX_LOCKS)
    made_doors += 1
    return d


# ---- Deck 1 (z0): the Promenade + storefronts ------------------------
prom = room_at(f"{M} - Promenade", (-8, -15, 0), "tenement", skin="tenement")
prom.db.desc = (
    "The Mimi's promenade deck, salvaged and stood on end: the passenger "
    "liner's old shopping arcade, now the lobby of a stack of let cabins. "
    "Brass rails gone green, riveted bulkheads, and the ship's name — "
    "MIMI — still raised over the purser's desk, where a rental terminal "
    "now lives. Storefronts open off the arcade; a companionway climbs "
    "into the hull.")
prom.db.sense_descs = {
    "auditory": "The building ticks and settles like a ship at anchor.",
    "olfactory": "Old brass, cold rivets, a ghost of engine oil.",
    "tactile": "Everything underfoot is decking plate, not floor.",
    "atmospheric": "A liner that never made port, made to hold still."}
SHOPS = {
    (-7, -15): (f"{M} - The Wake (Bar)", "bar", "bar",
                "The Wake — the Mimi's former first-class cocktail lounge, "
                "reopened as a bar. Curved banquettes bolted to the hull "
                "camber, a long salvaged bar-back of bottle-glass and "
                "chrome, portholes onto Kaspar Street. It trades on the "
                "liner's dead glamour and doesn't apologise for it."),
    (-8, -14): (f"{M} - Flashtemp Miner Supply", "shop", "shop",
                "Flashtemp Miner Supply — thermal rigs, heated picks, "
                "lamp cells and cold-suit liners racked to the deckhead "
                "for the crews working the ice under the colony. Everything "
                "in Flashtemp orange, everything rated for the cold that "
                "waits down the shafts."),
    (-7, -14): (f"{M} - Greenhaus Pharmacy", "clinic", "medical",
                "A Greenhaus pharmacy fitted into a former purser's office: "
                "a dispensing counter behind mesh, shelves of blister packs "
                "and pressed remedies, the green cross throwing light across "
                "the old ship's plating."),
}
for pos, (key, typ, skin, desc) in SHOPS.items():
    s = room_at(key, (pos[0], pos[1], 0), typ, skin=skin)
    s.db.desc = desc
    d = d_name(STAIR, pos)
    mk_exit(prom, s, d, [ABBR[d]])
    mk_exit(s, prom, OPP[d], [ABBR[OPP[d]]])

# entrance off Kaspar Street (south neighbour of the promenade)
kaspar = next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
               if r.db.xyz == (-8, -16, 0) and r.destination is None), None)
if kaspar is not None:
    mk_exit(prom, kaspar, "south", ["s", "out"])
    mk_exit(kaspar, prom, "north", ["n", "hotel mimi", "mimi"])

# ---- Decks 2-12 (z1-z11): landing + three cabins ---------------------
kiosk_cubes = []
landings = {}
for deck in range(2, 13):
    z = deck - 1
    land = room_at(f"{M} - Deck {deck} Landing", (STAIR[0], STAIR[1], z),
                   "tenement", skin="tenement")
    if not land.db.desc:
        land.db.desc = (
            f"The Deck {deck} companionway landing: a stub of the liner's "
            f"internal corridor, cabin doors to either hand, the stair "
            f"turning on up the hull. Portholes hold the colony {deck-1} "
            f"decks down.")
    landings[deck] = land
    for pos, letter in FLATS.items():
        cab = room_at(f"{M} - Cabin {deck}{letter}", (pos[0], pos[1], z),
                      None, skin="tenement")
        if not cab.db.desc:
            cab.db.desc = (
                f"A former passenger cabin on Deck {deck}: a single berth "
                f"that folds to the bulkhead, a basin, a wet cell behind a "
                f"sliding hatch, and a porthole with the colony framed in "
                f"riveted steel. Small, dry, and yours.")
        cab.db.residence_building = M
        cab.db.residence_origin = "Kaspar Street"
        # spring-latch lease door pair
        d_lu = d_name(STAIR, pos)          # landing -> cabin
        d_ul = OPP[d_lu]                   # cabin -> landing
        if not any(e.key == f"{deck}{letter}" for e in land.exits):
            hall = make_door(land, cab, f"{deck}{letter}", d_ul,
                             ["door", d_lu, ABBR[d_lu]])
            make_door(cab, land, d_ul, f"{deck}{letter}", [ABBR[d_ul]])
            cab.db.cube_door = hall
        kiosk_cubes.append(cab)

# stair chain: promenade -> deck2 -> ... -> deck12
prev = prom
for deck in range(2, 13):
    cur = landings[deck]
    mk_exit(prev, cur, "up", ["u"])
    mk_exit(cur, prev, "down", ["d"])
    prev = cur

# ---- Sun Deck (z12): the roof (2x2), stairs top out ------------------
ROOF = {STAIR: "Sun Deck", (-7, -15): "Sun Deck (Fore)",
        (-8, -14): "Sun Deck (Aft)", (-7, -14): "Sun Deck (Starboard)"}
roof = {}
for pos, suffix in ROOF.items():
    roof[pos] = room_at(f"{M} - {suffix}", (pos[0], pos[1], 12),
                        "rooftop", outside=True, skin="roof", ground=True)
for pos, r in roof.items():
    if not r.db.desc:
        r.db.desc = (
            "The Mimi's sun deck, open to the colony's false sky — the "
            "liner's old lido, plating warped, rails salvaged, the whole "
            "city laid out below. Off the southwest corner the Brackett's "
            "roof garden stands one diagonal leap across the gap.")
# 2x2 roof grid
for pos, r in roof.items():
    for nb_pos, nb in roof.items():
        if abs(pos[0]-nb_pos[0]) + abs(pos[1]-nb_pos[1]) == 1:
            mk_exit(r, nb, d_name(pos, nb_pos), [ABBR[d_name(pos, nb_pos)]])
# stairs top out onto the sun deck (SW corner)
mk_exit(landings[12], roof[STAIR], "up", ["u"])
mk_exit(roof[STAIR], landings[12], "down", ["d"])

# ---- the rental terminal (its own building's kiosk) ------------------
term = next((o for o in prom.contents if o.key == "rental terminal"), None)
if term is None:
    term = create_object(TERM_TC, key="rental terminal", location=prom)
term.db.pressable = True
term.db.rental_terminal = True
term.db.integrate = True
term.db.weight = 0.5
term.db.get_err_msg = "The purser's terminal is bolted to the desk."
term.db.integration_desc = (
    "A |crental terminal|n sunk into the Mimi's old purser's desk lists "
    "the vacant cabins.")
term.db.cubes = kiosk_cubes

print(f"BUILD 014: {made_rooms} rooms, {made_exits} exits, {made_doors} "
      f"door leaves, {len(kiosk_cubes)} cabins on the Mimi terminal.")
