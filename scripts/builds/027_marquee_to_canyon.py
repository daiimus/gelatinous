"""Build 027 — the marquee leaves the flank and hangs in the canyon.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/027_marquee_to_canyon.py
    then a foreground reload.

Owner: move the BRACKETT ARMS marquee off the building's flank and hang
it as a free-floating holo-banner in the canyon airspace directly below
the Kaspar Catwalk — "it's still airspace," so the cells stay sky/fall
rooms and the fall lattice is preserved (extended, in fact: the air
shaft at (-8,-16) topped out at z7 with a z8-11 void under the catwalk;
we fill it with four more SkyRooms so the shaft runs unbroken to the
catwalk). The name reads top-to-bottom z11..z6 with the new floating
`air_marquee_*` sprites. The flank units revert: 6G back to the loggia
band like 6E/6F, 7G-11G back to plain tenement.

Re-run-safe: room creation skips existing cells; skins/reverts are
idempotent.
"""
from evennia import create_object
from evennia.objects.models import ObjectDB

ROOM_TC = "typeclasses.rooms.SkyRoom"
EXIT_TC = "typeclasses.exits.Exit"
COL = (-8, -16)          # the canyon column below the catwalk
FLANK = (-9, -16)        # the Brackett's corner, where the name used to run


def at(xyz):
    return next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
                 if r.db.xyz == xyz and r.destination is None), None)


def has_exit(room, key):
    return any(e.key == key for e in room.exits)


def mk_exit(loc, dest, key):
    if has_exit(loc, key):
        return 0
    create_object(EXIT_TC, key=key, location=loc, destination=dest)
    return 1


made = exits = 0

# ---- 1. extend the air shaft up through the z8-11 void ----------------
# Match the existing "In the Air" SkyRooms (type='sky', is_sky_room=True)
# and chain a 'down' exit into the room below, so the column is one
# unbroken fall shaft from the catwalk (z12) to Kaspar Street (z0).
for z in (8, 9, 10, 11):
    r = at((COL[0], COL[1], z))
    if r is None:
        r = create_object(ROOM_TC, key="In the Air")
        r.db.xyz = (COL[0], COL[1], z)
        r.db.type = "sky"
        r.db.is_sky_room = True
        r.db.outside = True
        made += 1
for z in (8, 9, 10, 11):
    here = at((COL[0], COL[1], z))
    below = at((COL[0], COL[1], z - 1))
    if here and below:
        exits += mk_exit(here, below, "down")

# ---- 2. the name hangs in the canyon, z11 (top) -> z6 (bottom) --------
CANYON = {11: "air_marquee_1", 10: "air_marquee_2", 9: "air_marquee_3",
          8: "air_marquee_4", 7: "air_marquee_5", 6: "air_marquee_6"}
hung = 0
for z, skin in CANYON.items():
    c = at((COL[0], COL[1], z))
    if c is not None:
        c.db.atlas_skin = skin
        hung += 1

# ---- 3. the flank reverts to a plain building face -------------------
# 6G rejoins the loggia band (6E/6F use skin='loggia'); the upper units
# drop the skin entirely and render as ordinary tenement.
reverted = 0
for z in range(6, 12):
    f = at((FLANK[0], FLANK[1], z))
    if f is not None:
        f.db.atlas_skin = "loggia" if z == 6 else None
        reverted += 1

# ---- 4. prose: the sign is a thing hanging in the air now ------------
perch = at((COL[0], COL[1], 12))               # the Kaspar Catwalk
if perch is not None:
    perch.db.desc = (
        "A little maintenance catwalk slung over Kaspar Street between "
        "the Brackett Arms and the Halcyon — a scrap of grating and a "
        "rail, a long drop past it. Hung in the open air just below your "
        "feet, a holo-marquee runs the building's name straight down the "
        "canyon in green slab light: BRACKETT ARMS, letter over letter, "
        "floating on nothing. You cross from the Brackett's roof to the "
        "Halcyon's deck.")
    proj = next((o for o in perch.contents
                 if o.key in ("holo-marquee", "holo-billboard")), None)
    if proj is not None:
        proj.key = "holo-marquee"
        proj.db.desc = (
            "The Brackett Arms' holo-marquee, projected free in the "
            "canyon air below the catwalk — B-R-A-C-K-E-T-T, then "
            "A-R-M-S, each letter a green pane of light hanging over the "
            "drop with nothing behind it. Half the panes flicker; nobody "
            "has serviced a marquee in this colony in a long time.")
        proj.db.integration_desc = (
            "A |gholo-marquee|n hangs in the canyon air below the "
            "catwalk, spelling the building's name letter over letter.")

print(f"BUILD 027: shaft +{made} air rooms, {exits} down-exits; "
      f"{hung} canyon tiles skinned air_marquee_*; {reverted} flank tiles "
      f"reverted (6G->loggia, 7-11G->plain).")
