"""Build 002 — Kaspar roof corner repair (owner review findings).

    evennia shell < scripts/builds/002_kaspar_roof_repair.py
    then foreground reload.

Findings (owner, 2026-08-05):
  1. The main Rooftop's north exit (#6074) is an edge to Kaspar Street
     TWO cells away — wired before Rooftop (North) existed at (-2,-17),
     it now jumps through that plate's cell. Geometrically false.
     Fix: delete it; join the two plates with a proper walk pair.
     (Rooftop (North) keeps ITS north edge to the street — that one is
     geometrically true and stays the exemplar.)
  2. The Water Tower had no edges — an incomplete F2. A tower crown
     owes its own edge set: a short hop down onto the roof beside it
     (the gentle way off) and the bold leap past the parapet to the
     street two stories below.
"""
from evennia import create_object
from evennia.objects.models import ObjectDB

EXIT_TC = "typeclasses.exits.Exit"


def by_key(key):
    r = ObjectDB.objects.filter(db_key=key).first()
    assert r, f"missing: {key}"
    return r


def has_exit(room, name):
    return any(e.key == name for e in room.exits)


roof = by_key("Kaspar Urgent Care - Rooftop")
north = by_key("Kaspar Urgent Care - Rooftop (North)")
tower = by_key("Kaspar Urgent Care - Water Tower")
street = None
for r in ObjectDB.objects.filter(db_key="Kaspar Street"):
    if r.attributes.get("xyz") == (-2, -16, 0):
        street = r
assert street, "Kaspar Street cell (-2,-16) not found"

# 1) kill the through-the-plate edge; join the plates
bogus = ObjectDB.objects.filter(id=6074).first()
if bogus and bogus.location == roof and bogus.attributes.get("is_edge"):
    bogus.delete()
    print("deleted bogus edge #6074 (Rooftop north -> street, through the North plate)")
if not has_exit(roof, "north"):
    create_object(EXIT_TC, key="north", aliases=["n"],
                  location=roof, destination=north)
    print("joined: Rooftop north -> Rooftop (North)")
# (north -> south walk already exists: #6099)

# 2) the tower crown earns its edges
if not has_exit(tower, "south"):
    ex = create_object(EXIT_TC, key="south", aliases=["s"],
                       location=tower, destination=roof)
    ex.db.is_edge = True
    ex.db.edge_difficulty = 8          # the gentle hop, one story down
    ex.db.fall_room = roof.id
    ex.db.fall_damage = 5
    ex.db.fall_distance = 1
    print("tower edge: south, down one onto the Rooftop")
if not has_exit(tower, "north"):
    ex = create_object(EXIT_TC, key="north", aliases=["n"],
                       location=tower, destination=street)
    ex.db.is_edge = True
    ex.db.edge_difficulty = 12         # the bold leap past the parapet
    ex.db.fall_room = street.id
    ex.db.fall_damage = 10
    ex.db.fall_distance = 2
    print("tower edge: north, two stories to Kaspar Street")

print("BUILD 002 complete.")
