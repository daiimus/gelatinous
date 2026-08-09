"""Build 046 — de-tile the Queen's rack roof and the Halcyon sun deck.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/046_roof_detile.py
    then a foreground reload.

Owner: the Queen of Cups rooftop shouldn't repeat, and the Halcyon deck
should read as one consistent roof with an outer railing, not tiles.

  Queen's rack roof — a bespoke sprite per cell (the NW keeps its fallen
  mast); parapets only on outer edges.
  Halcyon sun deck — one consistent teal plating, a ship's railing on the
  outer perimeter only, HALCYON DAYS kept.

Data-only, re-run-safe.
"""
from evennia.objects.models import ObjectDB
from world.spatial import get_xyz

SKINS = {
    # Queen of Cups rack roof (NW #7282 already fallen_tower — untouched)
    (-3, -16, 12): "rack_sw", (-2, -16, 12): "rack_s", (-1, -16, 12): "rack_se",
    (-2, -15, 12): "rack_n", (-1, -15, 12): "rack_ne", (-2, -14, 12): "rack_crown",
    # Halcyon sun deck (2x2), railing on the perimeter
    (-7, -15, 12): "hdeck_sw", (-6, -15, 12): "hdeck_se",
    (-7, -14, 12): "hdeck_nw", (-6, -14, 12): "hdeck_ne",
}


def at(xyz):
    return next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
                 if r.destination is None and get_xyz(r) == xyz), None)


n = 0
for xyz, skin in SKINS.items():
    r = at(xyz)
    if r is not None:
        r.db.atlas_skin = skin
        n += 1

print(f"BUILD 046: {n} roof cells reskinned (Queen's rack + Halcyon deck).")
