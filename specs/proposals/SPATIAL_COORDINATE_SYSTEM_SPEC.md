# Spatial Coordinate System Specification

A unified integer `(X, Y, Z)` coordinate volume laid over the existing
hand-built world. It is the shared backbone for navigation, ranged systems
(vehicle combat / radar), verticality and gravity, NPC dispatch, and, later,
destructible and procedurally-generated space. It is inspired by Evennia's
`XYZGrid` contrib but adopts only its **data model**, not its authoring model.
The code is in `world/spatial` (`coordinates.py`, `pathfind.py`) and the
builder command `@coordseed` (`commands/CmdCoordSeed.py`).

## 1 · Intent — why coordinates, and why now

The game world is hand-authored: rich rooms with five-senses descriptions,
named exits, deliberate non-grid links (`enter bar`, `climb`, jump-across).
That authoring stays. What it lacks is a notion of **where each room is in
space**, and a growing list of systems all want exactly that:

* **GPS minimap** — a device-gated map whose glyphs derive from room *terrain
  type* (street / forest / desert / interior …), rendered with depth (see §8).
* **Ranged systems** — vehicle combat and a radar system need real distance and
  bearing between rooms.
* **NPC dispatch & auto-walk** — responders, couriers, and gangers routing
  across the city via shortest-path.
* **Verticality & gravity** — sky rooms you fall *through* along a vertical
  axis (falling already exists without coordinates, in `world/gravity.py`; see
  §6).
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
   keep their identity and authored descriptions; they merely *gain* a
   coordinate (§4).

### The two sources of truth

| Concern | Source of truth |
|---|---|
| Distance, bearing, altitude, gravity fall-path, minimap placement, proc-gen addressing | **Coordinate volume** (§3) |
| Movement legality, reachability, dispatch routing | **Real exit graph** — coordinates only seed the A\* heuristic (§5) |

Keeping these separate is what makes destruction and tunnelling "just work":
they mutate the exit graph the pathfinder already reads, while coordinates
remain a stable spatial address.

### What we borrow from XYZGrid

Nothing from the contrib is used, and `XYZRoom` is not inherited. Rooms carry
their own `db.xyz` Attribute and a `.xyz` property that reads it (§3). The
contrib's `return_appearance` injects its own minimap, which would fight our
`get_display_desc` sense-layer composition; because the contrib is not used,
that minimap never meets `get_display_desc`. What is kept from `XYZGrid` is
its data model: one `(x, y, z)` per room and a `.xyz` room property.

## 3 · The coordinate model

* **Signed integers** `(x, y, z)`. Origin **`(0, 0, 0)`** at the central ground
  space (Central Span #1005, pinned, §4); the world extrapolates outward and
  downward from there.
* **Axes:** `+X` east / `+Y` north / `+Z` up. Therefore **`Z < 0` =
  the Drifts (mines / sewers)**, **`Z = 0` = ground**, **`Z > 0` = upper levels / sky**.
  A signed origin makes "below ground" literally negative — readable and
  symmetric.
* **One unit = one room step** along a cardinal exit. Visual/described distance
  is irrelevant; adjacency in the exit graph defines the unit.

### Storage

A room's coordinate is a single `room.db.xyz` Attribute holding the
`(x, y, z)` tuple, written and read by `set_xyz` / `get_xyz` / `clear_xyz` in
`world/spatial/coordinates.py`. The `room.xyz` property (`typeclasses/rooms.py`)
is a plain, uncached read of it. Nothing caches the tuple on `ndb` (📋 UNBUILT,
§10).

Spatial queries are not DB-level. `all_coordinate_rooms()` filters `ObjectDB`
on `db_attributes__db_key="xyz"` and decodes every row in Python;
`rooms_within()` walks that whole list on each call (a linear scan, with a
spatial hash as the named escalation, §10). `coordinate_index()` is the one
cell-addressed lookup: one query over `all_coordinate_rooms()` building
`{(x, y, z): room}`, exits skipped (an exit never carries a cell), the later
row winning on a duplicate cell. Build it once per action, not per step (§10).

Rooms without a coordinate are **off-grid** (legitimately — pocket spaces,
limbo, test rooms). Every helper treats a missing coordinate as "not spatially
present" and fails open, never raising.

### Warp exits — the non-Euclidean escape hatch

Coordinates are **authoritative geometry** for the seed walk (whether the walk
overrides hand-placed coordinates is not decided, §10). A cardinal exit whose
direction disagrees with the coordinates of its rooms is a *build bug* (listed
by `@coordseed` and fixed during seeding, §4).

Elevator cars and the crane container are not such links: they are moving
rooms that rewrite their own `db.xyz` as they travel (`typeclasses/elevator.py`;
`CraneCarRoom.move_to_level` in `typeclasses/rooms.py`), and `@coordseed` names
them in its report.

Other deliberate non-Euclidean links — maglev, teleporters, a story warp — are
legitimate. Those carry a **`("warp", "exit_type")` tag**: excluded from
coordinate propagation, ignored by coordinate seeding (`seed_coordinates`),
still fully walkable and still a valid edge for the pathfinder. Radar ignoring
them is 📋 UNBUILT (no issue; no radar exists). The fall in `world/gravity.py`
does not read the tag: it follows a cell's `down` exit whatever its tags. This
is the line between "a bug" and "a deliberate teleporter," and it keeps the
ranged/gravity systems trustworthy. `warp` stays reserved for genuinely
non-Euclidean links; honest split-level geometry uses sloped exits (§4).

## 4 · Seeding coordinates onto the existing world

`@coordseed` assigns coordinates by **walking the exit graph** outward from the
pinned origin room (`seed_coordinates` in `world/spatial/coordinates.py`):

1. Origin room ← `(0, 0, 0)`. The origin is PINNED (#1192): it is the single room
   tagged `coordseed_origin:spatial` (Central Span #1005). Seeding anchors there
   regardless of where the builder stands, so running the command from the
   wrong room can never re-frame every coordinate in the world. The command
   refuses to run when no origin is pinned.
2. Breadth-first over its exits. Each **cardinal** exit (`north`/`n`,
   `south`, `east`, `west`, `up`/`u`, `down`/`d`, and the four diagonals)
   applies its unit delta to the source coordinate and assigns the destination.
3. **Sloped exits (#1192):** an exit tagged `slope_down:exit_type` or
   `slope_up:exit_type` adds a z-delta (−1 or +1, `slope_delta`) on top of the
   cardinal step. This makes split-level architecture (QoC sunken berths, z−1
   behind horizontal south doors) first-class derivable geometry. A missing
   opposite tag on the return exit surfaces as a contradiction.
4. **`warp`-tagged exits are skipped** (no coordinate inferred across them).
5. **Contradiction handling (authoritative):** if a room is reached twice with
   conflicting coordinates, that is a geometry bug in the build (e.g. a "north"
   that doesn't come back "south"). The tool **lists it to the builder** — the
   room the exit leaves, the direction, the destination, the coordinate it
   already has and the one this path expects (up to 40 shown) — and the builder
   corrects the exit, or tags it `warp` if the weirdness is intentional, or
   `slope_down`/`slope_up` if it is honest split-level geometry. Coordinates
   are not silently averaged.

Rooms gain a `db.xyz` Attribute; existing room descriptions are never touched.

### Switches and report

* `/check` — dry run (#3141). It diffs the plan against what is on disk (`plan_diff` in
  `commands/CmdCoordSeed.py`), because the walk's own contradiction list never
  looks at disk.
* `/origin` — pin the current room as the origin (re-pins it).
* `/force` — write even onto occupied cells (#3141). Without it, the command **refuses
  to write** when a room would land on a cell another room already holds.
* `/clear` — preview only: how many rooms would be stripped, how many the walk
  could restore, how many it could not.
* `/clear/confirm` — strip every coordinate.

Switches are matched without regard to case, and an unrecognised switch aborts
and changes nothing. Each run lists rooms whose coordinate would change, rooms
that would land on an occupied cell, any elevator or crane car in the walk, and
the contradictions. The command is locked to Builders or Developers
(`cmd:perm(Builders) or perm(Developers)`).

This is a one-time backfill plus an incremental tool builders run as they
extend the world. Per the design decision: *if we build correctly,
contradictions are rare and each is a real bug worth surfacing.*

The walk does not reach every on-grid room. Rooms placed by hand by
`scripts/builds/*.py` (cisterns, the Boot hull, Brackett's rise, the crane
shaft, the Halcyon) carry coordinates the walk never touches (#3245; who owns
`db.xyz` is not decided, §10).

### Builder audit commands (#1194)

* `@room` — a one-surface profile of the current room: type and crowd-pool
  routing, base and computed crowd, outside, coords, sense coverage, door
  states.
* `@building <prefix>` and `@building/radius [cells]` — a whole-structure audit
  table (every on-grid room within N cells, default 3, for `/radius`); drift
  reads straight off it.

Both are in `commands/CmdBuildTools.py`.

## 5 · Pathfinding & dispatch

A\* over the **live exit graph** (rooms = nodes, exits = edges), in
`world/spatial/pathfind.py`: `find_path`, `find_path_exits`, `path_length`,
`is_reachable`.

* **Edges = real exits, with rules on which ones a walker may use**
  (`_neighbors` in `world/spatial/pathfind.py`): an exit into an air cell
  (`db.is_sky_room is True`) is never an edge, for anyone; a drop (an exit
  flagged `is_edge` but not `is_gap`) is never an edge; a gap is an edge only for
  a traverser with `db.route_taste`, and the travel layer then issues
  `jump across`; when a traverser is given, exits it cannot pass (access locks,
  `door_blocks`) are skipped, so dispatch routes around what an NPC can't open,
  and with no traverser every other exit counts; an elevator car links to every
  floor the traverser may press (`_floor_permitted`), not just the floor it is
  parked at. `warp` exits are ordinary edges.
* **Heuristic = estimated steps from the coordinates**: `max(|dx|, |dy|) + |dz|`
  (a diagonal moves x and y in one step), making A\* fast and directed. Off-grid
  rooms fall back to Dijkstra (zero heuristic) transparently.
* **Edge weights are not flat.** `_route_cost()` weights each step by
  `ROUTE_COST` keyed on `room.db.type` (streets cheap, rooftops dear), scaled by
  the traverser's `db.route_taste`, and floored at 1.0 so the coordinate
  heuristic stays admissible and A\* stays optimal. Hazard avoidance is reserved
  for later.
* **Steps versus cost.** `path_length()` counts flat **steps** (that is what
  "nearest unit" means to dispatch), while the search minimises **cost**, and
  `max_steps` is a budget in steps.

Consumers: NPC movement and reachability checks (`world/director/travel.py`,
`world/director/courier.py`, `world/souls/posts.py`, `world/souls/actions.py`),
and any "is B reachable from A, and how far by travel?" query. Player
**auto-walk** (`goto`-style movement) is 📋 UNBUILT (no issue). Pathfinding
answers *travel* distance; §7 answers *line-of-sight* distance — they are
different and both needed.

## 6 · Verticality & gravity

Gravity lives in **`world/gravity.py`** and is driven by the ROOM, not by
coordinates:

* `Room.at_object_receive` calls `on_enter_air` for every arrival. Anything in a
  cell flagged `db.is_sky_room is True` that cannot stay up
  (`db.stays_aloft is not True`) falls one cell per `FALL_SECONDS_PER_CELL`
  down that cell's `down` exit, by any door — a jump, a throw, a drop, a shove,
  a reconnect. Items fall through the same room hook as bodies.
* The exit's `destination` IS the air cell, and the column of cells below it IS
  the distance. A fall is one real move per cell, one second apart, until the
  next room is not an air cell.
* Damage is `FALL_DAMAGE_PER_STORY` × cells passed, less
  `FALL_LANDING_ABSORBED_CELLS` on a made motorics landing roll (deliberate edge
  descents only), and shared with a grappled companion used as a bodyshield
  (`_land` in `world/gravity.py`).
* A cell with no `down` exit stops the fall cleanly where it is (the parked
  impasse, #3581). The missing columns are world data (#2945).

This is falling as −Z traversal, except that it walks the cell's authored
`down` exit rather than decrementing a coordinate. What this spec adds is the
ability to fall where no `down` exit was authored: a coordinate substrate would
make the column derivable instead of authored (§9, Phase 3).

The proposal for the vertical axis:

* A room declares whether it has a floor. The proposed flag is `db.passable` /
  `db.has_floor` (naming TBD). It must reconcile with `db.is_sky_room` (strict
  `is True`) on rooms and its complement on the moving side, `db.stays_aloft`.
  Both are single predicates: the naming question is open, the shape is not.
* **Falling = −Z traversal:** an unsupported body moves down one room at a time
  through `passable` rooms until it reaches one with a floor (or a landing
  surface). The current sky-room transit is the first concrete case of this
  general rule.
* Flight/lift moves the inverse direction; jump-across stays a horizontal
  special case already handled by `jump`.

The aim is that the live jump/sky-room behaviour keeps working unchanged and
simply becomes *expressible in coordinate terms*, so future vertical content
(rooftops, lift shafts, the Drifts) composes from the same primitive.

### Reading the grid for a combat outcome (#3589)

`ground_below` in `world/gravity.py` reads `coordinate_index()` to find the
highest non-air room in a rooftop's column, so a shot or a look over a parapet
reaches the street. Owner ruling (#3589, recorded 2026-09-16): "Aiming at an
edge typically means aiming at the ground area it drops to because of
sniping". It reads coordinates FIRST, keeping the `down` exit chain only for
off-grid rooms and for columns the grid has nothing seeded under. This is the
first place the grid is read at runtime to decide a **combat outcome** rather
than to draw a map, seed a build, or plan a path.

### 6.1 · Face state — walls, floors, and breaching

"What if someone wants to walk through a wall?" is the question that proves the
two-truths split, so the model names it explicitly. Each room **face** (±X, ±Y,
±Z — the six cardinal neighbours, plus diagonals) is in one of three states,
**derived** from the coordinate volume + exit graph, not stored:

| Face state | Condition | Meaning |
|---|---|---|
| **open** | a room exists at the neighbour coordinate **and** an exit connects to it | a door / hall / the −Z drop you fall through |
| **barrier** | a room exists at the neighbour coordinate **but no exit** does | a **wall** (or, on the −Z face, a **floor** — `has_floor`) |
| **solid** | **no** room at the neighbour coordinate | rock / the unbuilt void |

This unifies walls with the gravity model: **a wall is the horizontal analogue
of a floor** — both are *barrier* faces. On the −Z face, the floor that stops a
fall is any room that is not an air cell (`db.is_sky_room` is not `True`;
`is_sky` in `world/gravity.py`); a separate `has_floor`/`passable` flag is
📋 UNBUILT (no issue), and its naming is open (§10). An X/Y barrier is a wall.
One concept covers walls, floors, and ceilings.

"Through the wall" then decomposes cleanly, and each path is already a seam
elsewhere in this spec:

1. **Breach / destroy** (§8) — flips a **barrier → open** by *adding an exit*
   between the two coordinate-adjacent rooms. The coordinate volume supplies the
   one fact the exit graph can't: *which* room is on the far side to connect to.
   After the breach, walking through is ordinary movement.
2. **Phase / noclip / teleport** — a coordinate-driven move to the neighbour
   coordinate that **bypasses the exit-graph check** (cyber phase-shift, ghosting,
   staff). This is where coordinates express "the room spatially *that-way*"
   independent of connectivity.
3. **Dig into the void** — a **solid** face has nothing beyond; the wall holds
   absolutely. For procedural mines (§8), that absence is the trigger to
   *instantiate* a new room at the neighbour coordinate (tunnel into fresh rock).

Derived face state also throws off free detail: wall-aware destruction targeting
("blow the **east** wall"), correct minimap rendering (walls vs. openings), and
directional sensory leak ("movement through the **north** wall" — audio from a
coordinate-adjacent room with a barrier face). Warp exits (§3) are *not* walls —
they're deliberate non-Euclidean links, excluded from face-state geometry.

## 7 · Ranged systems (parallel consumers)

Distance and bearing are available independent of pathfinding
(`world/spatial/coordinates.py`):

* **`distance(room_a, room_b)`** — straight-line in the volume (line-of-sight /
  signal distance, *not* travel distance). It reads `db.xyz` on each call.
* **`rooms_within(room, n)`** — coordinate ball, for area effects and scans.
* **`bearing(room_a, room_b)`** — direction, for radar contacts and vehicle
  firing arcs.

**Vehicle combat** reads distance bands (engagement ranges) and bearing.
**Radar** enumerates contacts within range and renders them by bearing/altitude.
Both are *parallel* consumers, with no dependency on the pathfinder.

**Two query domains, not one.** Range queries over **rooms** (few, static,
lattice-uniform, point-like) are not the same problem as range queries over
**entities** — vehicles, blast radii, radar contacts — which are *many*,
*moving every tick*, and carry *extent* (footprints, arcs, AoE), often over
non-uniform space (sky, mine networks). The room-layer queries want a simple
spatial hash; the entity-layer queries are where bounding-volume / nearest-
neighbour algorithms (R-tree / BVH / KD-tree) actually earn their keep. See the
**spatial-query implementation** note in §10 for the structure-by-layer call.

## 8 · Reserved seams (future phases — corner-proofed, not built)

Designed-for now so we don't paint into a corner; implemented later.

* **Room destruction / repair.** Mutating a room's exits (blow open a wall, seal
  a door) flips a **face state** (§6.1) — `barrier → open` on breach, the reverse
  on repair — by adding/removing the exit edge; coordinates are unaffected and
  the pathfinder adapts for free. The coordinate volume supplies *which* room the
  breach connects to. Needs a damage-state model on rooms/exits (separate spec).
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
* **Phase layer (the net).** A per-entity **phase** partition rides *alongside*
  `(x, y, z)` — same coordinates, separate co-located realities (meatspace vs the
  net), default-deny with perception windows. Phase is **not** a fourth metric
  axis (no distance/adjacency/gravity); it's a membership tag handled in
  `PHASE_LAYER_SPEC`. Its hooks into this system: range queries (`rooms_within`,
  `slice`, radar) gain a phase filter; exits may be phase-tagged so the A\*
  pathfinder filters edges by phase; `slice()`/`get_display_desc` branch on the
  viewer's phase so the net renders the same volume differently.

## 9 · Build ladder

Phase 1 is the substrate (the coordinate, §3; seeding, §4; the warp tag; the
ranged queries, §7). Phase 2 is the pathfinder (§5). The dispatch system is a
direct consumer of Phase 2 and gets its own spec.

The work ahead:

| Phase | Scope | Unblocks |
|---|---|---|
| **3 — Verticality** | Fall where no `down` exit is authored, by deriving the column from coordinates (#3581, #2945); floor flag naming (§10) | Vertical content without hand-wired columns |
| **— Parallel —** | Vehicle combat + radar (consume Phase 1 distance/bearing) | — |
| **Reserved** | Destruction/repair · procedural mines · GPS/quiverbloom minimap | Pie-in-the-sky roadmap |

Player auto-walk (§5) is 📋 UNBUILT (no issue).

## 10 · Risks & open questions

### Risks and leans

* **Attribute-read cost in hot loops.** `distance()` reads `db.xyz` on each
  call, and `rooms_within()` and `coordinate_index()` query and decode every
  on-grid room on each call. **Lean:** cache `.xyz` on `ndb`, invalidate on move
  (📋 UNBUILT (no issue)); build `coordinate_index()` once per action.
* **Seeding a partially-inconsistent live world.** A backfill surfaces existing
  geometry bugs. That is a feature (they're real), but a run may produce a
  meaningful contradiction log to work through. The open contradictions are
  tracked in #3245.
* **Scipy dependency.** XYZGrid's pathfinder needs `scipy`; our own A\* over the
  exit graph is pure-Python (`heapq`) and avoids the dependency — preferred
  for the Docker image unless profiling says otherwise.
* **Spatial-query implementation — the math, not a dependency.** Range/proximity
  queries hide behind `rooms_within()` / `slice()` (rooms) and a parallel
  entity-query seam (vehicles/radar), so the *structure* is swappable without
  touching callers. Principle: **lift the algorithm, don't take the repo** —
  pure-Python, the lightest structure per query, built only when a profiled query
  is hot. **No runtime dependency is warranted** (candidate survey, 2026-06):
  the pure-Python R-tree libs (`pyrtree`, `rtreelib`) are **2D-only and
  insert-then-query** — no churn, no third axis — which is wrong for our 3D,
  mutating world; and `rtree`/`libspatialindex`, `scipy.cKDTree`, and sklearn are
  native deps we avoid (same discipline as the pure-Python A\* call). By layer:
  * **Room layer / entity broad-phase** — a roll-our-own **3D spatial hash**
    (dict keyed by `(x,y,z)` cells; O(1) churn, 3D-native, ~50 lines; ref:
    pygame `SpatialHashMap`, `dankolbman/spatialpartitioning`). The workhorse.
    Its seam is `coordinate_index()` in `world/spatial/coordinates.py` (§3),
    the one cell-addressed lookup in the game, with four consumers: the air fill
    (`@airfill`, `commands/CmdBuildTools.py`), `CraneCarRoom` in
    `typeclasses/rooms.py` and its caller in `world/director/courier.py`,
    `scripts/builds/030_marlowe_lot_skeleton.py`, and `ground_below` in
    `world/gravity.py` (§6). "Build it once per action, not per step" is the
    contract the hash will inherit. If anything profiles this hash into
    existence, it will be the `ground_below` call site; when it does, there is
    exactly one function to change.
    Caveat: a large-radius range query scans the covering ring of cells — fine
    for small radii; for clustered/sparse volumes (mines, sky) an **octree** is
    the escalation if the hash degrades.
  * **Point nearest-neighbour** (e.g. *dispatch responder selection* — closest
    LEO to an incident) — if it profiles hot, **vendor a ~60-line KD-tree**
    (permissive-licensed reference impls: `Vectorized/Python-KD-Tree`,
    `stefankoegl/kdtree`) rather than add a dependency.
  * **Entity extent / bbox overlap** (radar sweep, firing arc, AoE) — broad-phase
    through the spatial hash, then an exact box test; a full R-tree is overkill at
    our counts. R-tree's edge is extent *and* churn — but no usable pure-Python 3D
    impl exists, so we'd build a small BVH only if profiling ever proves the need.
  * **Pathfinding** uses neither — graph A\* over the exit network (§5),
    pure-Python `heapq`.

### Not decided

* **Who owns `db.xyz` — open (#3245).** Four things write it: the `@coordseed`
  walk, `@airfill`, the build scripts that place vertical geometry by hand, and
  the elevator and crane cars, which rewrite their own coordinate as they move.
  Where a room can be reached both ways, the walk and the hand placement can
  disagree. The owner has not decided whether the walk wins (hand-placed rooms
  get `warp` tags or are excluded from the walk) or hand placement wins (the
  walk skips any coordinate it did not derive itself). Until then, `@coordseed`
  refuses to write when a room would land on an occupied cell, unless `/force`
  is given.
* **Coordinate truth under destruction/tunnelling.** When space is created or
  destroyed at runtime, coordinate assignment must stay collision-free. The
  signed lattice gives unique addresses; the open question is reclamation of
  addresses for destroyed-then-different rebuilt rooms.
* **Floor naming.** Any new floor flag (`db.passable` / `db.has_floor`, §6) must
  reconcile with `db.is_sky_room` (rooms) and `db.stays_aloft` (things that do
  not fall), both read in `world/gravity.py`, so we don't end up with two
  vocabularies for "you fall through this."

## Related documents

* `PHASE_LAYER_SPEC` — the phase partition that rides alongside coordinates (§8).
* `NPC_DISPATCH_AND_SIMULATION_SPEC` — the dispatch system, the first major
  consumer of the pathfinder (§5, §9).
* `VERTICALITY_AND_BUILDINGS_SPEC` — vertical building on the grid.
