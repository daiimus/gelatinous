"""Build 049 — The Kettle, a worker bathhouse on Pessoa Street.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/049_the_kettle.py
    then a foreground reload.

Frontage massing on the open block north of Pessoa (x-8,-7 × y-11,-10,-9),
one gate off Pessoa at (-7,-12) -> (-7,-11). A bathhouse wearing onsen
bones the prose never names: noren-split door, a bandai counter, wicker
baskets, wash-stations and a great tiled pool fed by a sculpted spout,
a faded mountain mural — all gone to colony rot, the "hot spring" really
the processor's waste heat groaning through a boiler. Six interior cells
wired as a grid; atlas kettle_* skins. Re-run-safe.
"""
from evennia import create_object
from evennia.objects.models import ObjectDB
from world.spatial import get_xyz

ROOM_TC = "typeclasses.rooms.IndoorRoom"
EXIT_TC = "typeclasses.exits.Exit"

# (x, y): (label, atlas_skin, desc)
CELLS = {
    (-7, -11): ("Entrance", "kettle_entrance",
        "A step up off the street and through a split indigo curtain into the "
        "front room, dim and close with old steam. A high worn counter faces "
        "the door — the seat behind it long empty — and a rack of numbered "
        "wooden tokens hangs where shoes are meant to go. The tiles underfoot "
        "are cracked into a map of nowhere. Above the door outside, a board "
        "keeps the ghost of a painted mountain and characters no one reads."),
    (-8, -11): ("Boiler Room", "kettle_boiler",
        "The room nobody's supposed to be in: a groaning heat exchanger the "
        "size of a car, tapped into a fat insulated main that runs off toward "
        "the processor. Pipes sweat and tick, valves weep rust, and the whole "
        "false miracle of the place — hot water, endless — shudders out of it. "
        "No spring under this street. Only the plant's waste heat, praying."),
    (-7, -10): ("Changing Room", "kettle_changing",
        "Wicker baskets in a wall of wooden cubbies, most with someone's folded "
        "clothes still waiting. A bent bathroom scale, a mirror clouded to "
        "milk, a peeling poster of exercises no one does. It smells of "
        "liniment and cheap soap and the warm mineral breath coming through "
        "the far doorway."),
    (-8, -10): ("Cold Plunge", "kettle_plunge",
        "A small deep pool of water cold enough to stop the heart, tucked off "
        "the heat where the brave and the stupid go after the hot bath. A "
        "single wooden bucket, a slick lip of blue tile, and the shock of it "
        "waiting quiet in the dark."),
    (-7, -9): ("Bath Hall", "kettle_hall",
        "The great room, steam to the rafters and the light coming down grey "
        "through a raised roof-lantern high above. A single wide pool holds "
        "still and scalding, its surface skinned with mist; low wash-stations "
        "line the wall — a stool, a bucket, a brass tap gone green — where you "
        "scrub before you soak. Cracked blue tile everywhere, and the endless "
        "soft roar of water."),
    (-8, -9): ("Bath Hall - Mural Wall", "kettle_mural",
        "The far wall of the bath hall, and the reason old-timers still come: "
        "a mural painted the length of it, faded almost to a rumour — a "
        "mountain and a still lake under a sky gone to water-stain, the "
        "pigment ghosted where the steam has licked it for decades. Nobody "
        "remembers where the mountain is meant to be. A carved spout below it "
        "pours hot water into the pool without stopping."),
}
ENTRANCE = (-7, -11)
PESSOA = (-7, -12)
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
        r = create_object(ROOM_TC, key=f"The Kettle - {label}")
        r.db.xyz = (x, y, 0)
        made += 1
    r.key = f"The Kettle - {label}"
    r.db.desc = desc
    r.db.atlas_skin = skin
    r.db.outside = False
    rooms[(x, y)] = r

foot = set(CELLS)
for (x, y) in foot:
    for d, (dx, dy) in DIRS.items():
        n = (x + dx, y + dy)
        if n in foot:
            exits += mk_exit(rooms[(x, y)], rooms[n], d)

pessoa = at((PESSOA[0], PESSOA[1], 0))
assert pessoa is not None, "Pessoa entrance cell (-7,-12,0) missing"
exits += mk_exit(pessoa, rooms[ENTRANCE], "north")
exits += mk_exit(rooms[ENTRANCE], pessoa, "south")

print(f"BUILD 049: The Kettle +{made} cells, {exits} exits; entrance "
      f"#{pessoa.id}(Pessoa) <-> #{rooms[ENTRANCE].id}.")
