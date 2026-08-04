# The Atlas

The colony draws itself. `world/mapping.py` exports the coordinate
substrate; everything here renders it.

## Running it

```
# regenerate the map from the live database (inside the game container)
evennia shell < scripts/atlas/generate.py     # writes /tmp/atlas.html
```

The same builder serves `gel.monster/atlas` live to superusers
(`web/website/views/atlas.py`), so the served page is never stale. The
file version is for reading offline.

## The sprite pipeline

Requires **Blender** (headless) and **Pillow**:

```
brew install --cask blender
python3 -m venv .venv && .venv/bin/pip install pillow

BL=/Applications/Blender.app/Contents/MacOS/Blender
$BL --background --python scripts/atlas/sprites/rig.py             # class sprites
$BL --background --python scripts/atlas/sprites/landmark_boot.py   # heroes
$BL --background --python scripts/atlas/sprites/calibrate.py       # axis markers
.venv/bin/python scripts/atlas/sprites/post.py                     # the darkroom
.venv/bin/python scripts/atlas/sprites/measure.py                  # anchors.json
.venv/bin/python scripts/atlas/sprites/measure_landmarks.py        # hero origins
```

`raw/` is gitignored; `final/` is the library the generator embeds.

## Conventions that matter

- **The projection is a MIRRORED isometric** — no physical camera makes
  it. The rig shoots from the true northeast viewer and the darkroom
  flips horizontally; together they land on the atlas basis. Never
  "fix" one without the other.
- **Visible faces are NORTH and EAST.** Decoration on south or west
  faces renders into the void.
- **Naming**: `<class>_<orientation>_<variant>.png` — orientation before
  variant (`street_ew_1`). Any `_<n>` suffix joins that class's variant
  pool, picked per cell by seeded hash.
- **The px/unit invariant**: every render — class sprite or hero —
  keeps `ortho = 2.6 * RES / 512`. The template stamps landmarks at
  `size * SPR_SCALE` (the base rig's pixels-per-world-unit), so a hero
  that needs a wider frame buys it with RESOLUTION, never by widening
  the ortho base; changing the base renders the art at the wrong scale
  on the map.
- **Landmarks self-calibrate**: each hero script renders its own origin
  marker under its own camera; `measure_landmarks.py` writes the
  measured origin into `landmarks.json`. Never derive a hero's origin
  from the base rig's.
- **Fewer shapes win.** At 40 pixels a small box becomes a "what is
  that". Build heroes from a handful of big honest forms and let
  material glow do the detail.
- **Aesthetics over fiction fidelity.** A landmark must read as an
  identifiable object; interior truths (seams, breaches) are surface
  language, not voids. The overlays carry the real data.
- **Seasoning, not stew**: one ambient element per cell, ever —
  vehicle in the lane, prop at the curb, or crowd at the curb.
- **QA by looking.** The rendered PNGs are readable — inspect
  `final/*.png` directly instead of guessing at geometry.
