# Colony Mapping — the export, the builder's volume, the player's chart

The colony has a true voxel substrate (`db.xyz`, the spatial layer in
SPATIAL_COORDINATE_SYSTEM_SPEC). Colony mapping is **one canonical export,
many renderers**: one read-only export of that world, and the renderers that
draw it. It exists because "what is actually at this cell" had no tool:
vertical building began with hand-written recon scripts rendering ASCII
z-slices.

Owner direction, settled in discussion: the player tier is **vague, not
false**; its delivery is **GMCP → Mudlet-class client mappers**
(Evennia-native, see GMCP_PACKAGES_SPEC); the builder tier is **isometric
3D**, because verticality is the game's thesis and the interesting questions
are columnar.

---

## 0 · Purpose

Three consumers, one truth:

1. **Builders** need the god-view: exact grid occupancy, collisions, open
   columns, air lattice, edge wiring, coverage overlays — questions that
   throwaway shell scripts answer today, to be answered at a glance.
2. **Players** need a chart, not a database: where have I been, roughly
   what is this district, which way is the Boot — softened to the fidelity
   of a colony that photocopies its maps until the labels smear.
3. **Tools** need a format: the future build-planner, the decking layer
   ("everything is a file" — the colony map IS a file worth stealing), and
   any renderer not yet imagined. Format first keeps all of them cheap.

## 1 · The export (`export_map()` in `world/mapping.py`) — §M1

A read-only walker over the coordinate-seeded world that produces one
deterministic structure: two exports of the same world are identical. It
mutates no game state, adds no attributes and adds no Evennia layering; it
reads what the substrate already stores. Off-grid rooms are simply absent,
which is itself information the builder view surfaces.

The shape every renderer reads:

```
export_map() -> {
  "cells": [
    {"xyz": [x, y, z], "dbref": "#123", "key": "...",
     "type": "street|market|rooftop|sky|tenement|...",
     "skin": "<db.atlas_skin or ''>",
     "flags": ["outside", "sky", "ground"],   # outside / is_sky_room / is_ground
     "crowd": n},   # crowd_base_level; drives the street-life layer in both renderers
    ...
  ],
  "links": [
    {"from": "#123", "to": "#456", "key": "north",
     "kind": "walk|edge|gap|fall|door",
     "edge": {"edge_difficulty": n, "gap_difficulty": n,
              "gap_destination": n}},
    ...
  ],
}
```

### Link kinds

`_link_kind` gives each link one label, most specific first:

1. `door` — the exit has `is_door`.
2. `gap` — the exit has `is_gap`. Tested before `is_edge` because every gap
   also carries `is_edge` (#2789).
3. `edge` — the exit has `is_edge`.
4. `fall` — a `down` or `d` exit out of a sky cell.
5. `walk` — anything else.

Only a literal True counts.

### What a link carries

- **Edge and gap links** carry an `"edge"` key holding their flight-plan
  attributes, copied straight from the exit: exactly `edge_difficulty`,
  `gap_difficulty` and `gap_destination` (ints). Each key appears only when
  that exit attribute is set. The whole `"edge"` key is absent (not null) on
  any other kind of link.
- **No other edge attribute is exported.** `sky_room`, `fall_distance` and
  `fall_damage` were retired (#3579): the exit's destination IS the air
  cell, the column below it IS the distance, and the damage is a constant
  (`FALL_DAMAGE_PER_STORY`), so none of the three has a writer or a reader.
  `fall_room` was retired (#3580) on the owner ruling of 2026-09-16 that a
  fall "would always follow gravity straight down": in a sky room, proceed
  down; the fall ends at the first room that is not a sky room. There is no
  authored landing, so there is nothing for the map to carry. An apron,
  awning or terrace that should catch a fall is a ROOM in the column
  (`is_sky_room` False), never an attribute.
- **Door links carry no lock state** (#2682). A door is typed
  `kind: "door"` and nothing more. The reason: `export_map()` feeds the
  PUBLIC `/atlas/` page, so live lock state let anyone with the URL read
  which doors stood locked (at the time, 470 doors, 348 of them touching
  private residences), joined to room names and coordinates; nothing ever
  read the field. A staff map that wants lock state reads the exits
  directly rather than routing it through this payload.

### Cosmetic skins

`db.atlas_skin = "<class>"` on a room overrides its atlas class in both
renderers WITHOUT touching the gameplay `type` (which drives crowd routing,
exit phrasing and ambience). The export ships it as `skin`; the renderers'
`cls()` honors it first, guarded on the class existing in the model/fill
library. First use: the Brackett seam band — the whole sixth storey wears
the `loggia` glass band as a ring at the old-pour/rebuild seam line
(Build 008), map charm marking a structural truth after the floor
standardized as housing.

## 2 · The builder map — isometric volume, generated on demand (§M2)

`scripts/atlas/generate.py` (staff=True), run like any content script,
reads the export and writes a **self-contained HTML file** from
`scripts/atlas/template.html`: an inline canvas isometric renderer (the
sprite plate), no external assets, openable anywhere.

- **Builder-only artifact**: a generated file, never served by the game.
  Regenerate after builds; stale is fine, truth is one command away.
- **Isometric voxels**: rooms as blocks colored by type; air cells
  translucent; sky-transit distinct from solid; z-slice scrubber and a
  full-volume view. Isometric, not free-cam — the questions are columnar
  (what is above this street, does this fall lane clear, where does the
  canyon pinch) and iso answers them without navigation overhead.
- **Staff toggles** (shown only when the file is generated for staff):
  - *Air lattice*.
  - *Jump routes* (the Edges overlay): arcs for `edge` and `gap` links
    only, all stroked in one cyan. `fall` links are not drawn, and the arcs
    are not colored by kind. An edge arc ends in its air cell; a gap arc
    ends on its far perch (`gap_destination`), not in the air the leap
    passes through (#3643). This is the edge audit, drawn.
  - *Radio coverage*: two rings per mast from the live constants, crisp
    (solid) and full reach (dashed) — the Birdhouse's actual footprint drawn
    on the district.
- **Street life**: a layer for every viewer, not staff-only.
- **Overlays wanted, not built.** Until they exist these audits remain the
  throwaway shell scripts §0 sets out to retire:
  - *Open columns*: ground-occupied cells with empty sky above (sky-lane
    and mast-site candidates). 📋 UNBUILT (no issue)
  - *Ground coverage*: `is_ground` cells. 📋 UNBUILT (no issue; not
    decided whether still wanted: a fall ends at the first room in the
    column that is not a sky room, whatever its `is_ground`).
  - *Collision candidates*: cells adjacent to occupied space (tunnel
    planning). 📋 UNBUILT (no issue)
  - The two shipped toggles are narrower than first described: the Edges
    overlay was described as bright arcs for edge/gap/fall links, colored
    by kind, and radio coverage as crisp/fuzzy/static rings per mast.

## 3 · The player map — vague, not false (📋 UNBUILT, §M3, no issue)

The chart a colonist could actually hold. Owner doctrine: the colony's
maps do not lie — they are **imprecise**. Districts, not cells; names for
streets and landmarks, smears for everything else.

Because the served atlas is public, the player chart's job is not secrecy
but *in-fiction texture*; vague-not-false remains the design.

- **Exploration memory** gates everything: a per-character visited set
  (one attribute, appended on room entry, capped/compacted). You chart
  what your boots have touched. Whether the set survives re-sleeving
  follows the memory doctrine — it is memory, not gear (see §5).
- **Vagueness dial** (what the player tier elides, regardless of client):
  - No coordinates, no dbrefs, no grid exposed.
  - Air cells, sky lattice, and edge wiring: absent. You learn a jump by
    standing on the rim, not by reading a chart.
  - Interiors beyond the entry room: a single labeled block ("The
    Brackett Arms"), not a floor plan.
  - Unvisited adjacent space: present only as the fact of an exit.
- **Delivery: GMCP** (GMCP_PACKAGES_SPEC; Evennia speaks it natively —
  vanilla-aligned). On movement, emit `Room.Info` for the current room:
  stable room identity (hashed, not dbref), name, area/district, exits by
  direction, terrain type. Mudlet-class clients auto-draw the map from
  exactly this, gated to visited rooms by construction (you only ever
  receive rooms you enter). The webclient can consume the same package
  later; nothing else is built for it now. It should speak the MUD mapping
  standards — GMCP Room/Map packages toward Mudlet et al. (owner: "a while
  off", noted so the deferral is a decision, not an omission).

## 3.5 · Art direction (owner-set 2026-07-28): the stamp atlas

The builder renderer's (§M2 sprite plate's) final form is an
**Inkarnate-style stamp atlas in a Fallout 1/2 register**: the practical
layer (grid truth, hover, z-slice, route/coverage overlays) is unchanged, but cells render as CUSTOM SPRITES
— a per-type library plus signature multi-cell landmark sprites — with
the procedural boxes as fallback so the library grows incrementally.

Register refined (owner 2026-07-28): **off-world colony — Alien / Blade
Runner** — cassette-futurism industrial vocabulary (hazard chevrons,
stencils, conduit runs, dock stripes, utilitarian signage) under a
sodium-key/teal-rim lighting rig, wet-asphalt speculars, and a darkroom
grade of teal shadows, amber highlights, and neon bloom. Base register
underneath remains pre-rendered-3D grit — hard low key light,
brown/rust/olive palette, sodium-lamp amber, posterize + ordered dither +
grain post (Fallout's look WAS pre-rendered 3D; the vibe is materials and
post, not projection — 2:1 iso stays). **Cyan is reserved for DATA overlays
only.**

Sprite sources, ranked:

1. Pre-rendered pipeline — MagicaVoxel/Blender models at sub-cell detail,
   one fixed camera + light rig, automated post chain; regenerable,
   geometry-true, models shared with the §M4 portrait plates.
2. Local img2img grime pass, ControlNet-locked so geometry cannot move
   (finishing, never source).
3. Commissioned pixel art for hero sprites, eventually.

**Pilot**: three sprites (street cell, tenement floor, Boot hull segment)
through the full rig, stamped into the live style study beside procedural
cells for an A/B.

## 4 · Downstream consumers (§M4)

Each is a new consumer of the export; none reopens it.

- **Paper maps as flavor tier (later, cheap)** 📋 UNBUILT (§M4, no issue):
  branded printed charts sold as items — a cartography imprint whose
  district sheets are authored prose-maps (a look-at item rendering a
  stylized district summary), vague by profession. Slots into the shop
  system as pure content; also the natural *hackable/stealable* map
  artifact when decking arrives.
- **Decking** (design constraint only, no build): the export is the
  canonical "colony map file" the net layer will expose in pieces —
  wayfinding kiosks, route data, sewer charts. Requirement on the export:
  stable identities and clean layering so a *subset* of the export is a
  meaningful document.
- **Build-planning tool** (design constraint only, no build): the builder
  renderer's data layer should keep render and data separate so a future
  interactive planner (click a cell, propose a tunnel) reuses the export
  unchanged.

Order: §M3, the player chart (visited-set attribute + GMCP `Room.Info`
emission per the vagueness dial; Mudlet draws the rest), then §M4 (paper
map items; decking exposure; interactive planner).

## 5 · Open questions (owner)

- **Visited-set persistence across re-sleeve**: memory doctrine says a
  re-sleeved person keeps their mind — so routes survive death? (Lean:
  yes; it is knowledge, and losing it punishes exploration twice.)
- **District boundaries**: GMCP wants an "area" name per room. Derive
  from existing room naming ("Hammett's Boot - …") or author a district
  table? (Lean: naming-derived with an override table for streets.)
- **The cartography brand** for paper maps, when that tier lands.
- **Builder-map access**: generated-file-only (lean), or eventually an
  admin web page?

## 7 · The atlas as shipped — the live render (§M2.5)

Two consumers read `export_map()`: the builder plate (§2), and the served
atlas.

- **Public.** Evennia's web extension surface is first-class, so serving
  the atlas keeps to the vanilla mandate. The served atlas (`/atlas/`)
  needs no login and is linked as "Colony Atlas" in the account dropdown. It is edge-cached for cookie-less
  visitors, and the plate is cached server-side for 120s. Owner call
  (2026-08-25): the atlas is public, the colony's shop window. Full
  room-name and coordinate exposure is an accepted cost.
- **The render.** A **live 3D render**, embedded in the site page in the
  same plate chrome the sprite atlas wore (`web/templates/website/atlas.html`
  fragment mode; STYLING_SPEC addendum). The stage is a three.js
  orthographic free camera over models captured from the *same Blender rig*
  that shot the sprites: `scripts/atlas/sprites/export_models.py`
  monkeypatches `rig.render`, joins and subdivides each scene, and **bakes
  the full Cycles verdict into vertex colors** — twice, once under the rig's
  night lights and once under a day sky — shipped as parallel color
  attributes that the viewer crossfades. No live lights; a post shader
  carries the darkroom grade at 60fps.
- **Cockpit HUD**: a compass dial (the needle tracks the true screen
  direction of north; tap = home reset, which re-centers and fits the city
  flush to the stage from per-cell projection), a translucent altitude tape
  driving the z-slice clipping plane, and a sky-instrument toggle
  (crescent/sun glyph). Rotation is gestural (twist, shift-drag, bracket
  keys). Hover/tap raycasts to the room readout.
- **'You are here'**: the served page carries no positions. `atlas_view`
  (`web/website/views/atlas.py`) builds it once with `account=None`, caches
  it, and serves the same page to every viewer. In the browser, a 5-second
  poll of `?feed=here` (same allowlisted path; query strings pass the edge)
  returns `player_positions(request.user)`, the grid positions of the
  viewer's own characters, and keeps the pulsing beacons honest while they
  play. Anonymous viewers get none. The poll skips while the tab is hidden
  and stops after three failures in a row. Characters without a place in
  the world simply don't report.
- **Staff overlays are not served.** Air lattice, jump routes and radio
  coverage live only in the builder plate.
- **Pipeline discipline**: `models.json` is baked art. Any change to a rig
  model or hero script requires re-running `export_models.py` alongside the
  sprite grind, or the live render serves stale geometry. three.js is
  vendored (r147 UMD, pinned — the last non-ESM build).

**Overturned intention.** The served atlas was first scoped with the owner
as its only consumer: a thin superuser-gated website view reusing the
builder renderer, kept self-contained so the served page was a shim, not a
commitment. The owner ruled instead (2026-08-25) that the served atlas is
public, with no login.

## Related documents

- SPATIAL_COORDINATE_SYSTEM_SPEC — the `db.xyz` substrate the export reads.
- GMCP_PACKAGES_SPEC — the player chart's delivery.
- STYLING_SPEC — the atlas page chrome (addendum).
