# The Atlas

The colony draws itself. `world/mapping.py` exports the coordinate
substrate; everything here renders it. Two renderers share that truth:

- **The live render** (`template3d.html` + `sprites/models.json` +
  `vendor/three.min.js`) is what `gel.monster/atlas` serves to any
  logged-in account (`world/atlas.py:build_atlas3d_html`, embedded in
  the site page by `web/website/views/atlas.py`). Free camera, day and
  night baked in, the cockpit HUD, live 'you are here' beacons.
- **The sprite plate** (`template.html` + `sprites/final/`) is the
  builder's staff instrument — air lattice, jump routes, radio
  coverage live only here. Generated file, never served.

## The builder's plate

```
# regenerate from the live database (inside the game container)
evennia shell < scripts/atlas/generate.py     # writes /tmp/atlas.html
```

## The live-render bake

```
blender --background --python scripts/atlas/sprites/export_models.py
```

Monkeypatches `rig.render` so every sprite scene — classes and heroes —
is captured instead of photographed: joined, subdivided toward bake
resolution, and COMBINED-baked in Cycles into POINT-domain vertex
colors **twice** (the rig's night lights, then a day sky), written to
`sprites/models.json` as parallel `c`/`d` color arrays. The viewer
crossfades them; it runs no lights of its own.

- **models.json is baked art.** Any model or hero change requires this
  rerun alongside the sprite grind, or the live render serves stale
  geometry (the 2D and 3D atlases are baked independently — keep them
  in step when models change).
- **Denoiser OFF for vertex bakes** (it needs pixels; vertices aren't).
- three.js is **vendored and pinned** (r147 UMD — the last build that
  works as a plain script tag; do not "upgrade" it casually).

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
