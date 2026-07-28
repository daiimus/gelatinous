"""Generate the colony atlas (COLONY_MAPPING_SPEC §M2).

Run inside the game's shell (read-only over the DB):

    evennia shell < scripts/atlas/generate.py

Writes a fully self-contained ``/tmp/atlas.html`` — the §M1 export plus
live mast coverage, injected into the approved renderer template. Copy
it wherever you read documents; regenerate any time the world changes.
"""

import base64
import json
import os
import time

from world.mapping import export_map

data = export_map()

# the sprite library: stamp wherever a class has art, box everywhere else
SPRITE_DIR = "scripts/atlas/sprites/final"
sprites = {}
if os.path.isdir(SPRITE_DIR):
    for fname in sorted(os.listdir(SPRITE_DIR)):
        if fname.endswith(".png"):
            with open(os.path.join(SPRITE_DIR, fname), "rb") as f:
                sprites[fname[:-4]] = ("data:image/png;base64,"
                                       + base64.b64encode(f.read()).decode())
anchor_path = "scripts/atlas/sprites/anchors.json"
data["anchor"] = (json.load(open(anchor_path))
                  if os.path.exists(anchor_path) else None)

# landmark heroes: one sprite spanning many cells, suppressing their tiles
lm_path = "scripts/atlas/sprites/landmarks.json"
landmarks = json.load(open(lm_path)) if os.path.exists(lm_path) else []
for lm in landmarks:
    lm["uri"] = sprites.pop(lm["sprite"], None)
data["landmarks"] = [lm for lm in landmarks if lm.get("uri")]
data["sprites"] = sprites

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
      f"{len(sprites)} sprites, "
      f"{len(data['links'])} links, {len(masts)} masts, "
      f"edition {data['edition']}")
