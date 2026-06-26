# Spatial Coordinate System Specification

> **Status:** 📋 Proposal — not implemented. Designs a unified integer
> `(X, Y, Z)` coordinate volume laid over the existing hand-built world, as
> the shared backbone for navigation, ranged systems (vehicle combat / radar),
> verticality & gravity, NPC dispatch, and — later — destructible and
> procedurally-generated space. Inspired by Evennia's `XYZGrid` contrib but
> deliberately adopting only its **data model**, not its authoring model.

## 1 · Intent — why coordinates, and why now

The game world is hand-authored: rich rooms (246 with five-senses
descriptions), named exits, deliberate non-grid links (`enter bar`, `climb`,
jump-across). That authoring stays. What it lacks is a notion of **where each
room is in space** — and a growing list of systems all want exactly that:

* **GPS minimap** — a device-gated map whose glyphs derive from room *terrain
  type* (street / forest / desert / interior …), rendered with depth (see §8).
* **Ranged systems** — vehicle combat and a radar system need real distance and
  bearing between rooms.
* **NPC dispatch & auto-walk** — responders, couriers, and gangers routing
  across the city via shortest-path.
* **Verticality & gravity** — sky rooms you fall *through* along a vertical
  axis (the `jump` command already models a first version — see §6).
* **Pie-in-the-sky** — room destruction/repair and procedurally-generated mines
  that can be blown open and tunnelled.

Every one of these reduces to two primitives: **a coordinate per room** and **a
shortest path between rooms**. This spec builds those two primitives once, so
each system above is a thin consumer rather than a bespoke reinvention. *This is
the backbone for a lot of the roadmap — it is designed to be built on, not
finished.*

## 2 · Design stance — data model, not authoring model

Evennia's `XYZGrid` contrib is the obvious reference, but its core proposition
is **authoring the world as external ASCII maps** that `evennia xyzgrid spawn`
batch-generates into rooms. That is the *inverse* of how this game is built and
would collide with our authored content. We therefore **reject the authoring
pipeline** and lift only the substrate.

Three `XYZGrid` assumptions are explicitly overturned by our intent:

1. **Z is a real integer altitude, not a map name.** `XYZGrid` makes `Z` a
   string map-id and pathfinds per-map-island, never crossing `Z`. We want one
   continuous volume with sky rooms you fall through. → **one world, integer Z,
   no map-transition nodes.**
2. **Pathfinding runs over the real exit graph, not the coordinate lattice.**
   Our world has non-cardinal exits, locked doors, and (future) collapsed
   tunnels. Routing over coordinates would send NPCs through walls. → **A\* over
   the live exit network, with coordinates supplying only the distance
   heuristic** (§5).
3. **Coordinates are retrofitted onto existing rooms, never regenerated.** Rooms
   keep their identity and authored descriptions; they merely *gain* coordinate
   tags (§4).

### The two sources of truth

| Concern | Source of truth |
|---|---|
| Distance, bearing, altitude, gravity fall-path, minimap placement, proc-gen addressing | **Coordinate volume** (§3) |
| Movement legality, reachability, dispatch routing | **Real exit graph** — coordinates only seed the A\* heuristic (§5) |

Keeping these separate is what makes destruction and tunnelling "just work":
they mutate the exit graph the pathfinder already reads, while coordinates
remain a stable spatial address.

### What we borrow from XYZGrid

The coordinate **tag scheme** (categories `room_x_coordinate`,
`room_y_coordinate`, `room_z_coordinate`) and the `.xyz` room property — so
coordinate lookups are DB-indexed and a future builder could interoperate with
contrib tooling. We do **not** inherit `XYZRoom` wholesale: its
`return_appearance` injects the contrib minimap and would fight our
`get_display_desc` sense-layer composition. We take the tag/query mixin, not the
display. (Open question §10.)

## 3 · The coordinate model

* **Signed integers** `(x, y, z)`. Origin **`(0, 0, 0)`** at the central ground
  space; the world extrapolates outward and downward from there.
* **Axes:** `+X` east / `+Y` north / `+Z` up. Therefore **`Z < 0` =
  undercity / mines**, **`Z = 0` = ground**, **`Z > 0` = upper levels / sky**.
  A signed origin makes "below ground" literally negative — readable and
  symmetric.
* **One unit = one room step** along a cardinal exit. Visual/described distance
  is irrelevant; adjacency in the exit graph defines the unit.

### Storage

Coordinates live as **indexed tags** (the XYZGrid scheme) so spatial queries
(`all rooms at z = -1`, `rooms in this x/y box`) are DB-level and cheap. A
cached `room.xyz -> (x, y, z)` property reads them for math; hot consumers
(combat/radar) may cache the tuple on `ndb`. Tags are the truth; the property is
the convenience.

Rooms without coordinate tags are **off-grid** (legitimately — pocket spaces,
limbo, test rooms). Every helper treats a missing coordinate as "not spatially
present" and fails open, never raising.

### Warp exits — the non-Euclidean escape hatch

Coordinates are **authoritative geometry**: a cardinal exit whose direction
disagrees with the coordinates of its rooms is a *build bug* (logged and fixed
during seeding, §4). But deliberate non-Euclidean links — elevators, maglev,
teleporters, a story warp — are legitimate. Those carry a
**`("warp", "exit_type")` tag**: excluded from coordinate propagation, ignored
by radar/gravity geometry, still fully walkable and still a valid edge for the
dispatch pathfinder. This is the line between "a bug" and "a deliberate
teleporter," and it keeps the ranged/gravity systems trustworthy.

## 4 · Seeding coordinates onto the existing world

A builder tool (`@coordseed`, staff-locked) assigns coordinates by **walking the
exit graph** outward from a chosen origin room:

1. Origin room ← `(0, 0, 0)`.
2. Breadth-first over its exits. Each **cardinal** exit (`north`/`n`,
   `south`, `east`, `west`, `up`/`u`, `down`/`d`, and the four diagonals)
   applies its unit delta to the source coordinate and assigns the destination.
3. **`warp`-tagged exits are skipped** (no coordinate inferred across them).
4. **Contradiction handling (authoritative):** if a room is reached twice with
   conflicting coordinates, that is a geometry bug in the build (e.g. a "north"
   that doesn't come back "south"). The tool **logs it** — room, the two paths,
   the conflicting coordinates — and the builder corrects the exit (or tags it
   `warp` if the weirdness is intentional). Coordinates are not silently
   averaged.

This is a one-time backfill plus an incremental tool builders run as they extend
the world. Per the design decision: *if we build correctly, contradictions are
rare and each is a real bug worth surfacing.* Existing room descriptions are
never touched — rooms only gain tags.

## 5 · Pathfinding & dispatch

A\*/Dijkstra over the **live exit graph** (rooms = nodes, exits = edges), in a
new `world/spatial/pathfind.py`:

* **Edges = real exits**, so locked doors, `warp` links, and (future) collapsed
  tunnels are honoured automatically — connectivity always reflects the world as
  it actually is.
* **Heuristic = coordinate straight-line distance** (Manhattan or Euclidean),
  making A\* fast and directed. Off-grid rooms fall back to Dijkstra (zero
  heuristic) transparently.
* **Edge weights** default to 1 per step; reserved for terrain cost, hazard
  avoidance, and lock/traversal penalties later.

Consumers: the **NPC dispatch system** (route an NPC toward an event/target),
**auto-walk** (`goto`/`path` style player movement), and any "is B reachable
from A, and how far by travel?" query. Pathfinding answers *travel* distance;
§7 answers *line-of-sight* distance — they are different and both needed.

## 6 · Verticality & gravity

Gravity is **already partially built** in `commands/combat/jump.py`
(`apply_gravity_to_items`, exit `db.sky_room` / `db.fall_damage`, edge-jump
vertical descent). This spec **generalizes that existing mechanic onto the Z
axis** rather than inventing a parallel one:

* A room declares whether it has a floor — proposed `db.passable` /
  `db.has_floor` (naming TBD; reconcile with the current `sky_room` flagging).
* **Falling = −Z traversal:** an unsupported body moves down one room at a time
  through `passable` rooms until it reaches one with a floor (or a landing
  surface), accruing the existing `fall_damage`. The current sky-room transit
  becomes the first concrete case of this general rule.
* Flight/lift moves the inverse direction; jump-across stays a horizontal
  special case already handled by `jump`.

The aim is that the live jump/sky-room behaviour keeps working unchanged and
simply becomes *expressible in coordinate terms*, so future vertical content
(rooftops, lift shafts, the undercity) composes from the same primitive.

## 7 · Ranged systems (parallel consumers)

Once §3 lands, distance/bearing are available independent of pathfinding:

* **`distance(room_a, room_b)`** — straight-line in the volume (line-of-sight /
  signal distance, *not* travel distance).
* **`rooms_within(room, n)`** — coordinate ball, for area effects and scans.
* **bearing/direction** — for radar contacts and vehicle firing arcs.

**Vehicle combat** reads distance bands (engagement ranges) and bearing.
**Radar** enumerates contacts within range and renders them by bearing/altitude.
Both are *parallel* consumers — unblocked the moment the substrate exists, with
no dependency on the pathfinder.

## 8 · Reserved seams (future phases — corner-proofed, not built)

Designed-for now so we don't paint into a corner; implemented later.

* **Room destruction / repair.** Mutating a room's exits (blow open a wall, seal
  a door) changes the exit graph → the pathfinder adapts for free; coordinates
  are unaffected. Repair restores edges. Needs a damage-state model on
  rooms/exits (separate spec).
* **Procedural mines.** Coordinates become the **addressing scheme for space
  that doesn't exist yet**: tunnelling at `(x, y, z)` instantiates the room on
  demand at that address and links it to its neighbour. The signed integer
  volume is exactly the lattice this needs.
* **GPS minimap (quiverbloom render).** Device-gated (a GPS item, not always-on)
  and **perception-gated** (a blind character does not get an ASCII map dumped
  on them — routes through the perception system like every other visual layer).
  The display is **terrain-driven**, not hand-drawn: each room's glyph derives
  from its terrain/room type. The target aesthetic is a
  [quiverbloom](https://github.com/csnje/wasm-quiverbloom)-style point-field —
  a dense cloud of text glyphs where depth reads through density/brightness,
  driven by *terrain shape* instead of motion — for a 3D-esque relief rather
  than a flat tile grid.
  * **Substrate obligation:** expose a **volume-slice query** —
    `slice(center, radius, z_range) -> [(x, y, z, terrain_type, occupancy)]` —
    so a future renderer can project the cloud without reaching into room
    internals. That query is the only thing this spec owes the minimap; the
    renderer itself is a separate display spec.

## 9 · Build ladder

| Phase | Scope | Unblocks |
|---|---|---|
| **1 — Substrate** | Coordinate tags + `.xyz` property + `distance`/`rooms_within` + `@coordseed` seeding tool + warp-exit tag | Ranged systems; everything downstream |
| **2 — Pathfinder** | A\* over exit graph w/ coordinate heuristic (`world/spatial/pathfind.py`) | NPC dispatch; auto-walk |
| **3 — Verticality** | Generalize jump/sky-room gravity onto Z; `passable`/floor flags | Vertical content; falling |
| **— Parallel —** | Vehicle combat + radar (consume Phase 1 distance/bearing) | — |
| **Reserved** | Destruction/repair · procedural mines · GPS/quiverbloom minimap | Pie-in-the-sky roadmap |

Phases 1–2 are the shippable, testable core. The dispatch system is a direct
consumer of Phase 2 and gets its own spec.

## 10 · Risks & open questions

* **`XYZRoom` inheritance vs. lightweight mixin.** Inheriting the contrib room
  pulls in `return_appearance` (its minimap) which collides with
  `get_display_desc`. **Lean:** lift only the coordinate-tag/query mixin + `.xyz`
  property; do not inherit the display. Confirm before Phase 1.
* **Coordinate truth under destruction/tunnelling.** When space is created or
  destroyed at runtime, coordinate assignment must stay collision-free. The
  signed lattice gives unique addresses; the open question is reclamation of
  addresses for destroyed-then-different rebuilt rooms.
* **Tag-read cost in hot loops.** Distance math in combat/radar shouldn't hit
  the tag store per call. **Lean:** cache `.xyz` on `ndb`, invalidate on move.
* **Seeding a partially-inconsistent live world.** The first backfill will
  surface existing geometry bugs. That is a feature (they're real), but the
  initial run may produce a meaningful contradiction log to work through.
* **`passable`/`has_floor` naming** must reconcile with the existing `sky_room`
  flagging in `jump.py` so we don't end up with two vocabularies for "you fall
  through this."
* **Scipy dependency.** XYZGrid's pathfinder needs `scipy`; our own A\* over the
  exit graph can be pure-Python (`heapq`) and avoid the dependency — preferred
  for the Docker image unless profiling says otherwise.
