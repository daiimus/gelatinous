"""Build 019 — the fallen antenna: Queen of Cups <-> Halcyon crossing.

    evennia shell < scripts/builds/019_fallen_antenna_bridge.py
    then foreground reload.

The Queen's mast has toppled westward across the Kaspar gap and now
lies as a walkable lattice bridge to the Halcyon's sun deck — the
parkour line the two z12 towers were too far apart to jump. Along
y=-15 at z12:
  QoC Rack Roof Northwest (-3,-15) [fallen tower base, the mast rooted]
    -> (-4,-15) [span] -> (-5,-15) [span]
    -> Halcyon Sun Deck (Fore) (-6,-15)
Walkable both ways (a catwalk, not a jump). Two custom sprites:
`fallen_tower` on the roof cell, `fallen_span` over the gap cells.
The mast #5081 relocates to the base cell; coverage follows.
"""
from evennia import create_object
from evennia.objects.models import ObjectDB

ROOM_TC = "typeclasses.rooms.Room"
EXIT_TC = "typeclasses.exits.Exit"


def at_xyz(xyz):
    return next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
                 if r.db.xyz == xyz and r.destination is None), None)


def mk_exit(loc, dest, key, alias):
    if any(e.key == key for e in loc.exits):
        return
    create_object(EXIT_TC, key=key, aliases=[alias], location=loc,
                  destination=dest)


qoc = at_xyz((-3, -15, 12))          # QoC Rack Roof Northwest
hal = at_xyz((-6, -15, 12))          # Halcyon Sun Deck (Fore)
assert qoc and hal, "missing bridge endpoints"

# ---- the toppled-tower base on the QoC roof --------------------------
qoc.db.atlas_skin = "fallen_tower"
qoc.db.desc = (
    "The northwest corner of the Queen's roof, where the repeater mast "
    "finally went over — snapped at the root and toppled west, its "
    "lattice now bridging the gap toward the Halcyon's sun deck. People "
    "cross it because it's there. The city is a very long way down "
    "between the rungs.")
qoc.db.sense_descs = {
    "auditory": "Wind singing in the fallen steel; the whole span ticks "
                "and flexes.",
    "tactile": "Rust and cold rivets; the lattice gives under a boot "
               "just enough to remind you what it is.",
    "atmospheric": "A dead antenna made a road. Nobody planned it; "
                   "everybody uses it."}
mast = ObjectDB.objects.filter(id=5081).first()
if mast is not None:
    mast.move_to(qoc, quiet=True, move_hooks=False)

# ---- the span rooms across the gap -----------------------------------
SPAN = {(-4, -15): "The Fallen Antenna (Queen End)",
        (-5, -15): "The Fallen Antenna (Halcyon End)"}
span = {}
for (x, y), name in SPAN.items():
    r = ObjectDB.objects.filter(db_key=name).first()
    if r is None:
        r = create_object(ROOM_TC, key=name)
    r.db.xyz = (x, y, 12)
    r.db.type = "rooftop"
    r.db.outside = True
    r.db.is_ground = True
    r.db.atlas_skin = "fallen_span"
    r.db.desc = (
        "Out on the fallen mast, twelve storeys over Kaspar Street: a "
        "lattice tube wide enough to walk if you don't think about it, "
        "a salvaged plank laid along the top for the ones who do. "
        "Nothing on either hand but air and the drop.")
    r.db.sense_descs = {
        "auditory": "Only wind, and the steel complaining under you.",
        "tactile": "The plank flexes; the rungs are cold through your "
                   "soles.",
        "atmospheric": "Halfway across, committed, the ground irrelevant."}
    span[(x, y)] = r

# ---- wire the walk: QoC -> span -> span -> Halcyon (both ways) --------
q, s1, s2, h = qoc, span[(-4, -15)], span[(-5, -15)], hal
mk_exit(q, s1, "west", "w"); mk_exit(s1, q, "east", "e")
mk_exit(s1, s2, "west", "w"); mk_exit(s2, s1, "east", "e")
mk_exit(s2, h, "west", "w"); mk_exit(h, s2, "east", "e")

print("BUILD 019: fallen antenna laid QoC(-3,-15,12) -> Halcyon(-6,-15,12); "
      f"2 span rooms; mast at {mast.location.db.xyz if mast else '?'}.")
