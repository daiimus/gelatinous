"""Build 020 — fallen antenna: one room + a jumpable gap (owner rework).

    evennia shell < scripts/builds/020_fallen_antenna_gap.py
    then foreground reload.

Owner: the fallen antenna should be ONE room on the Queen's side; the
other cell is the gap/air. So the mast reaches one cell off the Queen
and you LEAP the rest — a stepping stone, not a full catwalk. And this
line is dead straight (all y=-15), unlike the diagonal Brackett jump:
  QoC roof (-3,-15) --walk--> The Fallen Antenna (-4,-15)
    --JUMP west over air (-5,-15)--> Halcyon Sun Deck (Fore) (-6,-15)
The old (-5) walk-room becomes the sky/air gap; the (-4)<->(-6) walk
exits become a reciprocal jump edge.
"""
from evennia import create_object
from evennia.objects.models import ObjectDB

EXIT_TC = "typeclasses.exits.Exit"


def at(xyz):
    return next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
                 if r.db.xyz == xyz and r.destination is None), None)


ant = at((-4, -15, 12))              # The Fallen Antenna (Queen End) -> the one room
air = at((-5, -15, 12))              # (Halcyon End) -> becomes the gap/air
hal = at((-6, -15, 12))              # Halcyon Sun Deck (Fore)
assert ant and air and hal, "missing crossing rooms"

# fall room: the ground under the gap column
fall = next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
             if r.db.xyz and r.db.xyz[0] == -5 and r.db.xyz[1] == -15
             and r.db.xyz[2] == 0 and r.destination is None), None) \
    or at((-4, -15, 0))
assert fall, "no ground fall room under the gap"

# ---- the one fallen-antenna room -------------------------------------
ant.key = "The Fallen Antenna"
ant.db.desc = (
    "The end of the toppled mast, one cell off the Queen's roof: the "
    "lattice runs out here over open air, and the Halcyon's sun deck "
    "stands one leap west across the gap. This is the jumping-off point "
    "— literally. Twelve storeys of nothing under the last rung.")

# ---- the old walk-room becomes the sky gap ---------------------------
air.key = "Kaspar Gap (Queen–Halcyon)"
air.db.type = "sky"
air.db.is_sky_room = True
air.db.is_ground = False
air.db.outside = True
if air.attributes.has("atlas_skin"):
    air.attributes.remove("atlas_skin")
air.db.desc = ("Open air over Kaspar Street between the fallen antenna and "
               "the Halcyon's deck — the half-second a jump lives in.")
air.db.sense_descs = {"tactile": "Nothing. The drop has your full attention.",
                      "atmospheric": "Committed, mid-leap, the street a long "
                                     "way down."}

# ---- rip the walk exits across the gap -------------------------------
for a, b in ((ant, air), (air, ant), (air, hal), (hal, air)):
    for e in list(a.exits):
        if e.destination == b:
            e.delete()


def jump_edge(loc, direction, gap_dest):
    e = ObjectDB.objects.filter(db_location=loc, db_key=direction).first()
    if e is None:
        e = create_object(EXIT_TC, key=direction,
                          aliases=[direction[0]], location=loc, destination=air)
    e.destination = air
    e.db.is_edge = True
    e.db.is_gap = True
    e.db.edge_difficulty = 13
    e.db.gap_difficulty = 11
    e.db.gap_width = "medium"
    e.db.fall_distance = 12
    e.db.fall_damage = 10
    e.db.sky_room = air.id
    e.db.fall_room = fall.id
    e.db.gap_destination = gap_dest.id


# antenna --jump west--> gap --> Halcyon ; Halcyon --jump east--> gap --> antenna
jump_edge(ant, "west", hal)
jump_edge(hal, "east", ant)

print(f"BUILD 020: fallen antenna = 1 room ({ant.db.xyz}); gap/air "
      f"{air.db.xyz}; reciprocal jump (diff 13) to Halcyon; fall -> "
      f"{fall.db.xyz}.")
