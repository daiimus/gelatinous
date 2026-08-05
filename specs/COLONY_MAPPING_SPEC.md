# Colony Mapping — the export, the builder's volume, the player's chart

> **Status:** ✅ SHIPPED through §M2.5 — and past it (2026-08-04).
> §M1 export, the sprite atlas, and the website view went live 2026-07-28;
> the *served* atlas has since evolved into a **live 3D render** and is
> player-facing — see **§7 · The atlas as shipped**, which supersedes the
> §M2.5 details below where they differ. The sprite plate survives as the
> builder's generated instrument. §M3 (player chart: vague-not-false,
> visited sets, GMCP) and §M4 (paper maps, decking exposure, planner)
> remain 📋 deferred with their design unchanged.
>
> *Original proposal framing follows.*
> **SCOPE REFOCUS (owner, same day): the v1 consumer is the OWNER alone.**
> The player/builder audience split and everything serving it (vagueness
> dial, visited-sets, GMCP) is deferred to §M3/M4 unchanged; v1 = §M1
> export + §M2 renderer built as a beautiful standalone isometric atlas
> (SimCity/Monument Valley register, not CAD), then a THIN superuser-gated
> website view reusing the same renderer (§M2.5 — Evennia's web extension
> surface is first-class, so the vanilla mandate holds; the renderer must
> stay self-contained so the served page is a shim, not a commitment). The
> colony has a true voxel substrate (`db.xyz`, the spatial layer shipped in
> SPATIAL_COORDINATE_SYSTEM_SPEC) and a day of vertical building proved the
> gap: every build this session began with a hand-written recon script
> rendering ASCII z-slices, because "what is actually at this cell" has no
> tool. This spec turns that improvisation into infrastructure — **one
> canonical export, many renderers** — and defines the two consumers that
> matter now (builder map, player map) plus the ones that matter later
> (the build-planning tool, the decking layer's wayfinding files). Owner
> direction settled in discussion: the player tier is **vague, not false**;
> delivery is **GMCP → Mudlet-class client mappers** (Evennia-native, see
> GMCP_PACKAGES_SPEC); the builder tier is **isometric 3D**, because
> verticality is the game's thesis and the interesting questions are
> columnar.

---

## 0 · Purpose

Three consumers, one truth:

1. **Builders** need the god-view: exact grid occupancy, collisions, open
   columns, air lattice, edge wiring, coverage overlays — the questions
   answered today by throwaway shell scripts, answered tomorrow at a glance.
2. **Players** need a chart, not a database: where have I been, roughly
   what is this district, which way is the Boot — softened to the fidelity
   of a colony that photocopies its maps until the labels smear.
3. **Tools** need a format: the future build-planner, the decking layer
   ("everything is a file" — the colony map IS a file worth stealing), and
   any renderer not yet imagined. Format first keeps all of them cheap.

## 1 · The export (`world/mapping.py`) — build this first

A read-only walker over the coordinate-seeded world producing one
deterministic structure. No game-state mutation, no new attributes, no
Evennia layering — it reads what the substrate already stores.

```
export_map() -> {
  "generated": <caller supplies stamp>,      # exporter itself is pure
  "cells": [
    {"xyz": [x, y, z], "dbref": "#123", "key": "...",
     "type": "street|market|rooftop|sky|tenement|...",
     "flags": ["outside", "sky", "ground"]},   # is_sky_room / is_ground
    ...
  ],
  "links": [
    {"from": "#123", "to": "#456", "key": "north",
     "kind": "walk|edge|gap|fall|door",
     "edge": {"sky_room": ..., "fall_room": ..., "distance": n,
              "damage": n, "difficulty": n} | null,
     "door": {"locked": bool} | null},
    ...
  ],
}
```

Classification rules (all derivable today): `fall` = one-way down exits
from sky cells; `edge`/`gap` from the is_edge/is_gap flags with the §190
flight-plan attributes attached; `door` from is_door with lock state
(never grants — state only). Off-grid rooms are simply absent, which is
itself information the builder view surfaces.

Tests pin: determinism (two exports, same world → identical output),
classification of each link kind, and the flight-plan passthrough.

## 2 · The builder map — isometric volume, generated on demand

A generator script (repo `scripts/`, run like any content script) that
reads the export and writes a **self-contained HTML file**: inline canvas
isometric renderer, no external assets, openable anywhere.

- **Isometric voxels**: rooms as blocks colored by type; air cells
  translucent; sky-transit distinct from solid; z-slice scrubber and a
  full-volume view. Isometric, not free-cam — the questions are columnar
  (what is above this street, does this fall lane clear, where does the
  canyon pinch) and iso answers them without navigation overhead.
- **Overlays, each toggleable** (this is where it earns its keep):
  - *Edges*: bright arcs for edge/gap/fall links, colored by kind —
    the edge audit, drawn.
  - *Open columns*: ground-occupied cells with empty sky above (sky-lane
    and mast-site candidates).
  - *Ground coverage*: `is_ground` cells (fall-termination audit).
  - *Radio coverage*: crisp/fuzzy/static rings per mast from the live
    constants — the Birdhouse's actual footprint drawn on the district.
  - *Collision candidates*: cells adjacent to occupied space (tunnel
    planning).
- **Builder-only artifact**: a generated file, never served by the game.
  Regenerate after builds; stale is fine, truth is one command away.

## 3 · The player map — vague, not false

The chart a colonist could actually hold. Owner doctrine: the colony's
maps do not lie — they are **imprecise**. Districts, not cells; names for
streets and landmarks, smears for everything else.

- **Exploration memory** gates everything: a per-character visited set
  (one attribute, appended on room entry, capped/compacted). You chart
  what your boots have touched. Whether the set survives re-sleeving
  follows the memory doctrine — it is memory, not gear (§5 owner call).
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
  later; nothing else is built for it now.
- **Paper maps as flavor tier (later, cheap)**: branded printed charts
  sold as items — a cartography imprint whose district sheets are
  authored prose-maps (a look-at item rendering a stylized district
  summary), vague by profession. Slots into the shop system as pure
  content; also the natural *hackable/stealable* map artifact when
  decking arrives.

## 3.5 · Art direction (owner-set 2026-07-28): the stamp atlas

The §M2 renderer's final form is an **Inkarnate-style stamp atlas in a
Fallout 1/2 register**: the practical layer (grid truth, hover, z-slice,
route/coverage overlays) is unchanged, but cells render as CUSTOM SPRITES
— a per-type library plus signature multi-cell landmark sprites — with
the procedural boxes as fallback so the library grows incrementally.
Register refined (owner 2026-07-28): **off-world colony —
Alien / Blade Runner** — cassette-futurism industrial vocabulary (hazard
chevrons, stencils, conduit runs, dock stripes, utilitarian signage) under
a sodium-key/teal-rim lighting rig, wet-asphalt speculars, and a darkroom
grade of teal shadows, amber highlights, and neon bloom. Base register
underneath remains pre-rendered-3D grit — hard low key light, brown/rust/olive
palette, sodium-lamp amber, posterize + ordered dither + grain post
(Fallout's look WAS pre-rendered 3D; the vibe is materials and post, not
projection — 2:1 iso stays). Cyan is reserved for DATA overlays only.
Sprite sources, ranked: (1) pre-rendered pipeline — MagicaVoxel/Blender
models at sub-cell detail, one fixed camera + light rig, automated post
chain; regenerable, geometry-true, models shared with the §M4 portrait
plates; (2) local img2img grime pass, ControlNet-locked so geometry
cannot move (finishing, never source); (3) commissioned pixel art for
hero sprites, eventually. **Pilot**: three sprites (street cell,
tenement floor, Boot hull segment) through the full rig, stamped into
the live style study beside procedural cells for an A/B.

## 4 · Downstream consumers (design constraints only, no build)

- **Decking**: the export is the canonical "colony map file" the net
  layer will expose in pieces — wayfinding kiosks, route data, sewer
  charts. Requirement on §1: stable identities and clean layering so a
  *subset* of the export is a meaningful document.
- **Build-planning tool**: the builder renderer's data layer should keep
  render and data separate so a future interactive planner (click a cell,
  propose a tunnel) reuses the export unchanged.

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

## 6 · Phasing

1. **§M1 — the export.** `world/mapping.py` + tests. Pure, deterministic,
   read-only. Unblocks everything else and nothing depends on choices
   still open.
2. **§M2 — the builder volume.** Generator script → self-contained iso
   HTML with the overlay set. Pays for itself the first build it plans.
3. **§M3 — the player chart.** Visited-set attribute + GMCP Room.Info
   emission per the vagueness dial. Mudlet draws the rest.
4. **§M4 — later.** Paper map items; decking exposure; interactive
   planner. Each is a new consumer of §M1, none reopens it.

## 7 · The atlas as shipped (2026-08-04) — the live render

"One export, many renderers" held; the renderers just outgrew the plan.
Two consumers exist today, both fed by `export_map()`:

- **The served atlas** (`/atlas/`, login-only, linked in the account
  dropdown) is a **live 3D render**, embedded in the site page in the
  same plate chrome the sprite atlas wore (`web/templates/website/
  atlas.html` fragment mode; STYLING_SPEC addendum). The stage is a
  three.js orthographic free camera over models captured from the *same
  Blender rig* that shot the sprites: `scripts/atlas/sprites/
  export_models.py` monkeypatches `rig.render`, joins and subdivides
  each scene, and **bakes the full Cycles verdict into vertex colors** —
  twice, once under the rig's night lights and once under a day sky —
  shipped as parallel color attributes that the viewer crossfades. No
  live lights; a post shader carries the darkroom grade at 60fps.
- **Cockpit HUD**: a compass dial (needle tracks the true screen
  direction of north; tap = home reset, which re-centers and fits the
  city flush to the stage from per-cell projection), a translucent
  altitude tape driving the z-slice clipping plane, and a sky-instrument
  toggle (crescent/sun glyph). Rotation is gestural (twist, shift-drag,
  bracket keys). Hover/tap raycasts to the room readout.
- **'You are here'**: `player_positions(account)` rides the logged-in
  account's character positions into the page and a 5-second poll of
  `?feed=here` (same allowlisted path; query strings pass the edge)
  keeps the pulsing beacons honest while you play. Characters without a
  place in the world simply don't report.
- **The builder instrument** is still the §M2/§3.5 sprite plate:
  `scripts/atlas/generate.py` (staff=True) writes the standalone file,
  and the staff overlays — air lattice, jump routes, radio coverage —
  live only there. It is never served.
- **Pipeline discipline**: `models.json` is baked art. Any change to a
  rig model or hero script requires re-running `export_models.py`
  alongside the sprite grind, or the live render serves stale geometry.
  three.js is vendored (r147 UMD, pinned — the last non-ESM build).
