"""Build 055 — the Greenhaus Verticals: three drone-tended farm towers.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/055_greenhaus_verticals.py
    then a foreground reload.

INTENT (playbook §0): the colony's food engine — three ten-storey
vertical farms filling the empty block north of Braddock, fenced at
street level with NO ground access ever. The block belongs to the
machines; human presence is trespass by parkour. These are the east
side's first high-line anchors.

    The Fungary        x7   fungus and root crops in the low light
    The Leafworks      x9   hydroponic greens
    The Fruiting House x11  the light-hungry trellis crops

Each tower: footprint 1x3 (y-19..-17), levels z0..z9 plus a green roof
at z10 (the Brackett roof-garden register). A stair core runs the
middle cell (y-18) top to bottom; every level opens north and south
onto vegetation platforms whose outer rails are dense with jump edges
into the air columns at x8 and x10 ("In the Air", z1..z10). Ground
between the towers is the fenced Greenhaus lawn — reachable only by
falling in; you leave by climbing a tower and jumping back out.

ENTRY (owner call): a single edge-jump from the Colonial Constabulary
Rooftop (South) at (8,-15,2), across the air over Kaspar street
(8,-16,2), into the western air column. Trespass starts on police
property.

Zero exits touch any street. Re-run-safe. Rollback: delete every room
whose key starts with "The Fungary", "The Leafworks",
"The Fruiting House", or "Greenhaus Grounds", the air cells listed in
AIR, and the constabulary rooftop's south edge.
"""
from evennia import create_object
from evennia.objects.models import ObjectDB
from world.spatial import get_xyz

ROOM_TC = "typeclasses.rooms.Room"
SKY_TC = "typeclasses.rooms.SkyRoom"
EXIT_TC = "typeclasses.exits.Exit"

ALIAS = {"north": ["n"], "south": ["s"], "east": ["e"], "west": ["w"],
         "up": ["u"], "down": ["d"]}

TOWERS = {
    7: ("The Fungary", "fungary"),
    9: ("The Leafworks", "leafworks"),
    11: ("The Fruiting House", "fruiting"),
}

# ── the prose: banded per tower, per kind ──────────────────────────────
FLAVOR = {
    "fungary": {
        "bay": ("Substrate hoppers line the walls, breathing warm damp rot "
                "into the dark. Compression racks squeeze spent logs into "
                "brick fuel; a drone dock's charging rails glow standby-amber "
                "along the ceiling. The floor drains run black with tea-"
                "coloured runoff. Nothing here expects a person."),
        "low": ("Racked grow-logs recede into spore-mist, studded with pale "
                "caps like knuckles pushing through bark. Drip lines tick. "
                "The light is deliberately meagre — a red maintenance dusk "
                "the crop prefers — and the air tastes of cellars and wet "
                "earth. Drone rails overhead run away into the fog."),
        "mid": ("Shelf on shelf of white-capped colonies climb the racks, "
                "misters breathing over them in slow pulses. The spore-haze "
                "is thick enough to soften every edge; railing, rack, and "
                "rail-mounted pruning arms loom out of it as silhouettes. "
                "Somewhere below, a pump swallows."),
        "high": ("The premium tiers: oyster fans and veiled kings under "
                 "glass cloches, each cluster tagged with a Greenhaus lot "
                 "stencil. Up here the mist thins and the wind finds gaps "
                 "in the cladding, carrying the cellar-smell out over the "
                 "street far below."),
        "roof": ("The Fungary's roof green — turf and low sedum over the "
                 "mist plant's condensers, which breathe like sleeping "
                 "animals underfoot. The parapet rail is intermittent at "
                 "best. From here the whole fenced lawn shows between the "
                 "towers, ten storeys down."),
        "core": ("The Fungary's stair core — switchback steel in a concrete "
                 "throat, lit by a vertical service strip. Spore-mist "
                 "creeps in at every landing door and beads on the rail. "
                 "Stencilled tallies count the levels in Greenhaus green."),
    },
    "leafworks": {
        "bay": ("Nutrient tanks stand in ranks, stirred by slow paddles; "
                "the air is all chlorophyll and pump-hum. Coils of gutter "
                "channel wait in racks for the levels above. A drone dock "
                "blinks through its charge cycle beside the intake mains "
                "that run east toward the cistern."),
        "low": ("Hydroponic gutters run wall to wall, dense with seedling "
                "greens — a carpet of new colour the city doesn't otherwise "
                "own. Misters drift. The grow-lamps hold everything in a "
                "pink-white noon that never moves, and the rail edge drops "
                "away into open air."),
        "mid": ("Full heads now — lettuces, mustards, things bred past "
                "their old names — packed gutter to gutter under lamp-banks "
                "that buzz one insect note. Harvest rails overhead end in "
                "empty tool-grips, waiting for the drones. The smell is "
                "green enough to drink."),
        "high": ("Herb tiers: basil, shiso, colony-bred camphor mint, the "
                 "air sharp with all of them at once. The lamps up here are "
                 "kinder, almost golden. Wind worries the gutter-films and "
                 "flicks droplets over the platform rail."),
        "roof": ("The Leafworks' roof green — meadow-seeded turf gone "
                 "pleasantly to seed, the one crop nobody harvests. "
                 "Irrigation heads tick around their arcs. The stair head's "
                 "door bangs softly on its spring, forever."),
        "core": ("The Leafworks' stair core — steel switchbacks washed in "
                 "runoff-green light from the strip. Every landing smells "
                 "of crushed stems; the rail is sticky with resin where "
                 "gloves never wipe it."),
    },
    "fruiting": {
        "bay": ("Trellis frames and coir bales stacked to the ceiling; "
                "crated bee-boxes hum against the north wall, their "
                "occupants leased floor by floor. The drone dock here is "
                "biggest of the three — fruit is heavy — and the floor is "
                "sticky where syrup lines have wept."),
        "low": ("Vine rows on wire, ankle-lit so the fruit sets low: "
                "tomatoes in colony reds, cucurbits swelling in slings. "
                "The warmth is real warmth, the first the street's climate "
                "ever spared. Wires thrum when the wind leans on the "
                "tower."),
        "mid": ("The trellis walls close into corridors of leaf and hanging "
                "fruit — peppers, dwarf stonefruit, something Greenhaus "
                "calls a plum. Bee-drones stitch between blossoms with a "
                "sound like dropped change. Every rail out is festooned "
                "with escaped vine."),
        "high": ("The sugar tiers: melon slings and espaliered citrus under "
                 "the fiercest lamps in the building. The air is dessert. "
                 "Pickers' rails run right to the platform lip and stop at "
                 "nothing but altitude."),
        "roof": ("The Fruiting House roof green — orchard turf around four "
                 "dwarf apples in windbreak cages, fruit netted against a "
                 "theft that has never yet come on foot. The eastern rail "
                 "looks straight down Spillane's steam."),
        "core": ("The Fruiting House stair core — steel treads tacky with "
                 "old syrup, the service strip yellowed warm. Handwritten "
                 "lot tallies climb the wall beside the stencilled ones, "
                 "some crossed out with real venom."),
    },
}

LAWN_DESC = ("Greenhaus turf, machine-mown into surveyor's stripes, running "
             "between the tower feet. The perimeter fence is close-meshed "
             "and topped with a polite, absolute overhang — no gate on any "
             "side, because nothing that belongs here arrives on foot. "
             "Irrigation heads tick. The towers hum above.")

AIR_DESC = ("Open air inside the Greenhaus fence line, crossed by drone "
            "lanes and the smell of whichever crop is winning. The lawn "
            "waits below; platform rails stud the towers on either side.")

CONNECTOR_DESC = ("Open air over Kaspar Street, between the Constabulary's "
                  "roof and the Greenhaus fence line. The farm's western "
                  "air column is one committed leap south.")


def at(xyz):
    return next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
                 if r.destination is None and get_xyz(r) == xyz), None)


def room(tc, key, xyz, desc, rtype, skin, outside):
    r = at(xyz)
    if r is None:
        r = create_object(tc, key=key)
        r.db.xyz = xyz
    r.key = key
    r.db.desc = desc
    r.db.type = rtype
    if skin:
        r.db.atlas_skin = skin
    r.db.outside = outside
    return r


def has_exit(loc, key):
    return any(e.key == key for e in loc.exits)


def link(loc, dest, key, edge=None, gap=None):
    """One exit; edge/gap = difficulty numbers when it's a jump."""
    if loc is None or dest is None or has_exit(loc, key):
        return 0
    e = create_object(EXIT_TC, key=key, aliases=ALIAS.get(key, []),
                      location=loc, destination=dest)
    if edge is not None:
        e.db.is_edge = True
        e.db.edge_difficulty = edge
    if gap is not None:
        e.db.is_gap = True
        e.db.gap_difficulty = gap
    return 1


def band(z):
    if z == 0:
        return "bay"
    if z <= 3:
        return "low"
    if z <= 6:
        return "mid"
    if z <= 9:
        return "high"
    return "roof"


def diff(z):
    """Edge difficulty rises with altitude; the roof is the boldest line."""
    return min(12, 6 + z // 2)


made = exits = 0
R = {}          # (x,y,z) -> room

# ── the towers ─────────────────────────────────────────────────────────
for x, (name, fkey) in TOWERS.items():
    F = FLAVOR[fkey]
    for z in range(0, 11):
        b = band(z)
        if z == 0:
            keys = {(-17): f"{name} - Ground Bay (North)",
                    (-18): f"{name} - Stair Core (Ground)",
                    (-19): f"{name} - Ground Bay (South)"}
        elif z == 10:
            keys = {(-17): f"{name} - Roof Green (North)",
                    (-18): f"{name} - Stair Head (Roof)",
                    (-19): f"{name} - Roof Green (South)"}
        else:
            keys = {(-17): f"{name} - North Platform (Level {z})",
                    (-18): f"{name} - Stair Core (Level {z})",
                    (-19): f"{name} - South Platform (Level {z})"}
        for y, key in keys.items():
            is_core = (y == -18)
            desc = F["core"] if is_core and 0 < z < 10 else F[b]
            if z == 10 and is_core:
                desc = (f"{name}'s stair head — a doghouse of louvred steel "
                        "opening onto the roof green. The door spring has "
                        "opinions.")
            if z == 10:
                skin = "garden_cap" if is_core else "garden"
            elif is_core:
                skin = "farm_core"
            else:
                skin = "farm_tier"
            outside = (not is_core) and z > 0
            r = room(ROOM_TC, key, (x, y, z), desc, "farm", skin, outside)
            R[(x, y, z)] = r
            made += 1

# stair chain + core->platform links
for x in TOWERS:
    for z in range(0, 10):
        exits += link(R[(x, -18, z)], R[(x, -18, z + 1)], "up")
        exits += link(R[(x, -18, z + 1)], R[(x, -18, z)], "down")
    for z in range(0, 11):
        exits += link(R[(x, -18, z)], R[(x, -17, z)], "north")
        exits += link(R[(x, -17, z)], R[(x, -18, z)], "south")
        exits += link(R[(x, -18, z)], R[(x, -19, z)], "south")
        exits += link(R[(x, -19, z)], R[(x, -18, z)], "north")

# ── the air columns (bare SkyRooms; the jump system owns them) ─────────
AIR = [(gx, y, z) for gx in (8, 10) for y in (-17, -18, -19)
       for z in range(1, 11)]
for xyz in AIR:
    r = at(xyz)
    if r is None:
        r = create_object(SKY_TC, key="In the Air")
        r.db.xyz = xyz
        made += 1
    r.key = "In the Air"
    r.db.type = "sky"
    r.db.is_sky_room = True
    r.db.outside = True
    r.db.desc = AIR_DESC
    R[xyz] = r

# platform/roof edges into the air columns. Gap exits need THREE parts
# (canon: the Halcyon crossing): destination=air (jump-off descents),
# gap_destination=the far perch (where jump-across LANDS), sky_room=the
# air (transit). Destination-only wiring strands jumpers in the air.
def _wire_gap(loc, key, far, air):
    for e in loc.exits:
        if e.key == key and e.db.is_gap:
            e.db.gap_destination = far.id
            e.db.sky_room = air.id

for x in TOWERS:
    for z in range(1, 11):
        d = diff(z)
        for y in (-17, -19):
            if x in (7, 9):                      # eastward into a gap
                exits += link(R[(x, y, z)], R[(x + 1, y, z)], "east",
                              edge=d, gap=d)
                _wire_gap(R[(x, y, z)], "east", R[(x + 2, y, z)],
                          R[(x + 1, y, z)])
            if x in (9, 11):                     # westward into a gap
                exits += link(R[(x, y, z)], R[(x - 1, y, z)], "west",
                              edge=d, gap=d)
                _wire_gap(R[(x, y, z)], "west", R[(x - 2, y, z)],
                          R[(x - 1, y, z)])

# ── the lawns ──────────────────────────────────────────────────────────
LAWN = {(8, -17, 0): "Greenhaus Grounds - West Lawn (North)",
        (8, -18, 0): "Greenhaus Grounds - West Lawn",
        (8, -19, 0): "Greenhaus Grounds - West Lawn (South)",
        (10, -17, 0): "Greenhaus Grounds - East Lawn (North)",
        (10, -18, 0): "Greenhaus Grounds - East Lawn",
        (10, -19, 0): "Greenhaus Grounds - East Lawn (South)"}
for xyz, key in LAWN.items():
    R[xyz] = room(ROOM_TC, key, xyz, LAWN_DESC, "garden", "greenlot", True)
    made += 1
for gx in (8, 10):
    for y in (-17, -18):
        exits += link(R[(gx, y, 0)], R[(gx, y - 1, 0)], "south")
        exits += link(R[(gx, y - 1, 0)], R[(gx, y, 0)], "north")
    # lawn <-> tower ground bays and cores (inside the fence, both sides)
    for y in (-17, -18, -19):
        exits += link(R[(gx, y, 0)], R[(gx - 1, y, 0)], "west")
        exits += link(R[(gx - 1, y, 0)], R[(gx, y, 0)], "east")
        exits += link(R[(gx, y, 0)], R[(gx + 1, y, 0)], "east")
        exits += link(R[(gx + 1, y, 0)], R[(gx, y, 0)], "west")

# ── the way in: over the cop shop ──────────────────────────────────────
# entry: a pure DESCENT from the cop roof over the fence, landing by
# gravity on the West Lawn — destination is the farm's own airspace
# (build 060 lesson: a straight south line from the roof has no same-z
# perch, so this cannot be a gap crossing).
constab = next((r for r in ObjectDB.objects.filter(
    db_key="Colonial Constabulary Rooftop (South)")
    if r.destination is None), None)
if constab is not None:
    exits += link(constab, R[(8, -17, 2)], "south", edge=10)

print(f"BUILD 055: Greenhaus Verticals — {made} rooms touched, "
      f"{exits} exits created. Entry: Constabulary roof, south edge.")
