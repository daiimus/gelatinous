"""Generate the colony atlas (COLONY_MAPPING_SPEC §M2).

Run inside the game's shell (read-only over the DB):

    evennia shell < scripts/atlas/generate.py

Writes a fully self-contained ``/tmp/atlas.html`` — the §M1 export plus
live mast coverage, injected into the approved renderer template. Copy
it wherever you read documents; regenerate any time the world changes.
"""

import json
import time

from world.mapping import export_map

data = export_map()

# live radio coverage annotations — the masts speak from their steel
masts = []
try:
    from world.radio import (_all_powered_radios, _antenna_site,
                             _effective_tx_range, _grid_room)
    from world.spatial import get_xyz
    for radio in _all_powered_radios():
        if radio.db.is_base_station is not True:
            continue
        site = _antenna_site(radio)
        if site is None:
            room = _grid_room(radio)
            site = get_xyz(room) if room is not None else None
        if site is None:
            continue
        reach = _effective_tx_range(radio, site)
        masts.append({"x": site[0], "y": site[1], "name": radio.key,
                      "freq": str(radio.db.frequency or ""),
                      "crisp": round(0.7 * reach, 1),
                      "reach": round(reach, 1)})
except Exception as err:  # noqa: BLE001 — coverage is annotation, not truth
    print(f"mast annotation skipped: {err}")
data["masts"] = sorted(masts, key=lambda m: m["name"])
data["edition"] = time.strftime("%Y-%m-%d %H:%M")

template = open("scripts/atlas/template.html").read()
out = template.replace("/*__DATA__*/null", json.dumps(data))
with open("/tmp/atlas.html", "w") as f:
    f.write(out)
print(f"atlas written: /tmp/atlas.html — {len(data['cells'])} cells, "
      f"{len(data['links'])} links, {len(masts)} masts, "
      f"edition {data['edition']}")
