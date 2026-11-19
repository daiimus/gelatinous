# The Building Playbook — why we build, how we build, what remains

Not a system spec: the working doctrine for architecting the rest of the
city. §1–§3 are settled law, distilled from practice and from owner calls
across `VERTICALITY_AND_BUILDINGS_SPEC`, `SPATIAL_COORDINATE_SYSTEM_SPEC`
and the builds; they change only when a build teaches us something. §4 is
the ledger of the remaining city and is *meant* to be argued with —
entries marked **candidate** are unsettled until the owner says otherwise.

---

## 1 · What a build must accomplish

The city is the game's largest system, and a build is a systems commit,
not scenery. Before authoring a room, every proposed build answers six
questions. A build may answer "deliberately none" to any of them — but
it answers.

1. **Who works or lives here?** Places are staffed before they are
   described. A venue without a person is a facade; name the post, even
   if the NPC ships later (`NPC_POSTS_AND_REINCARNATION_SPEC` makes
   posts durable). Compare: every venue that *works* — Sable's lounge,
   Vance's clinic, Ottilie's cart, Ezra's shop — is a person first.
2. **What work does it host?** The growth thesis is the gig/freelancer/
   favor loop: progression is favor + gear + rep, not stat leveling.
   A build should create work — a gig board it grounds, a service it
   sells, a favor it can owe — or say why it hosts none.
3. **How does Z figure?** Verticality is the game's thesis and the
   volume is paid for. Every footprint decides its column: floors above,
   basement below, rooftop plate, air cells, or a deliberate refusal
   (single-story by design is a choice, not a default).
4. **What future system does it pre-wire?** The capstone doctrine is
   *build pieces connectable, snap on later* — decking wants towers and
   file-bearing institutions; climbing hooks want faces worth scaling;
   phase layer wants interiors that multiply; radio wants height; the
   Ripper wants a sewer. A build placed well makes a future system
   cheaper; say which one.
5. **What is true here?** Lore constraints bind: Domino's Gambit,
   stranded CY 61, brands on everything sold or made (exceptions:
   handmade, ubiquitous generics, deliberate anti-brands), venues carry
   distinguished proper names (the "Aster register"), interiors are
   surface language never voids, and the colony's maps stay vague-not-
   false. New lore beyond established canon is an owner call.
6. **What does the atlas owe it?** New rooms appear on the live atlas
   free via the export. A new *building class or landmark* owes rig art:
   the sprite scene, the grind, and the `export_models.py` rebake — art
   budget is part of the build estimate, not an afterthought.

## 1.5 · The City Section (owner-set, 2026-08-05)

The architecture of the whole, called out as core requirements. Builds
argue with §4; they do not argue with this section.

**The bowl.** The colony sits in a crater roughly **twenty stories**
deep. The skyline lives inside that envelope: the tallest building
tops out around **sixteen to eighteen** (the height that "feels tall"),
just under the rim. The crater wall is the city's outermost facade and
the honest end of every map. One southwest block already reaches that
envelope: the Brackett has a roof deck at z16 and its antenna platform —
"the highest walkable point of the Brackett" — at z19
(`scripts/builds/011_brackett_crown.py`); the Boiler Run crane's cab sits
at z17 (`scripts/builds/032_crane_operator.py`) and its container rides
z1..z16 (`CraneContainer.MIN_Z`/`MAX_Z` in `typeclasses/rooms.py`).

**The organism.** The colony's purpose is **terraforming; everything
else is an offshoot of it.** The water cycle is the city's skeleton:
**ice mining below** feeds the terraformer; the **central channel** —
the gap the Central Span crosses — works as a large-scale **aquaponics
basin**; the basin feeds **vertical agricultural farms**; cultivation
climbs to **green spaces on the rooftops**. The Atmospheric Processor
makes the air. Every industry, gig, and trade in the colony should
trace to this cycle in at most two steps. Register note: this adds a
**solarpunk thread to the spacepunk/cyberpunk base** — grow-lights,
vine-run conduit, algae glass, planted roofs; growth forcing its way
through the grime is the proof the colony is alive.

**The plan: corridors, not zones.** The city organizes the way cities
organically form — along the routes work travels. **Industrial
corridors**: the freight run from the Landing Pad toward the
Processor's skirt; power down Volta; fab-labor along Riveter's Way.
**Cultural corridors**: each quarter's life concentrates on a main
street — venues cluster on the spine unless there is a reason to hide.
Even distribution is the enemy of role-play; convergence is engineered
at city scale first.

**Northside: the megablocks.** Corporate megablocks/arcologies cluster
north — the high end of the gradient and the corporate vocabulary's
home. They **eat the streets** (street-tunnels: covered street rooms,
no sky, sodium all day) and stitch to each other with **skyways**
(Minneapolis-style enclosed bridges: parkour rungs, weather-free
fabric, and funnels where paths must cross). Interiors obey
**vast-implied, brief-actual**: scale lives in sightlines, not room
count — one atrium gallery with the park ten stories down beats a
hundred corridor rooms. A room exists only if players can meet in it
or it is a rung on a route. The 16–18-story anchor's identity (Thawn
grown upward, or a new name) is an **owner call, pending** (see Not
decided).

**Southside: the wall and the Processor.** The fringes build **into
the crater face** — unorthodox structures, slope-and-terrace geometry
(the sloped-exit tags exist for exactly this), the make-do register at
its extreme, terraces as commons. And the **Atmospheric Processor
dominates the colony** from the plot the street grid was drawn
around: bounded by **Maxwell (north), Pessoa (south), the Spillane
(east), and Riveter's Way (west)** — a 7×7 block, empty since
seeding, **reserved** — with the **main gate at Volta & Riveter's**.
`scripts/planning/cityplan.py` draws it as `zone(11,-5,5,-11)` =
x5..11, y-11..-5. One street off the channel's south bank, so the water
cycle is physically tight: ice below, works in the block, basin across
Maxwell. Industrial-sacred register; plausibly the one silhouette
that reaches the rim.

**Below.** The down-Z layer is real: **ice mines** under the colony
feed the terraformer, and the underground (mines, service galleries,
the sewer the Ripper wants) is a build layer with its own routes, not
a basement afterthought.

**Traversal.** Street-to-precipice is a guaranteed, solvable journey:
**parkour as the common verb, rappelling/climbing as punctuation.**
Two or three **named ascent corridors** carry the guarantee — the
northern architecture climb (roofs and skyways through the
megablocks), the southern geology climb (wall-dwelling terraces), and
the Processor's industrial spiral. The stepping-stone height rule
binds **only along ascent corridors**; elsewhere a build takes
whatever height serves it. The **rim stays empty** — the reward for
twenty stories is wind and the whole colony below — except **one
terminus structure** (a beacon, a dead gantry) marking the top of the
route.

**Culture: vague by design.** No cemented cultures, no named factions
of players. The divides live in the **day-to-day texture** — street
preachers, tradesmen, an accent, an heirloom — drawn from three
ambient forces available to any build: descent from the mission's
org chart (crew, terraformers, corporate, labor, liner passengers who
were never supposed to stay), the Light (faiths of the stranding),
and the sleeve divide (eternalists vs. single-lifers, a line that runs
through families, not districts). Texture, never territory; flavor,
never canon. NPC-run factions remain the only factions.

## 2 · Settled doctrine (the law, with sources)

**The grid** (`proposals/SPATIAL_COORDINATE_SYSTEM_SPEC.md`):
- Coordinates are the data model; **hand-authoring is the authoring
  model**. No `@stack`, no ad-hoc builder commands — floors are rooms,
  stairwells are up/down exit pairs, authored like anything else.
- `@coordseed` seeds from the **pinned origin** (Central Span, the
  `coordseed_origin:spatial` tag) — never re-frame the world from where
  you happen to stand.
- Split levels use **sloped-exit tags** (`@tag <exit> = slope_down:exit_type`
  or `slope_up:exit_type`; the return exit carries the opposite tag),
  so the geometry stays derivable; `warp` is reserved for genuinely
  non-Euclidean links.
- Audit with `@room` (one-surface profile) and `@building <prefix>` /
  `/radius` (whole-structure drift table: type, crowd, coordinates, sense
  layers, doors). Geometry contradictions come from `@coordseed/check`.
  A build is done at **zero geometry contradictions**, not before.

**The vertical doctrine** (owner-set 2026-07-25):
- Open plates — roofs, decks, hull-tops — are **strip rooms tiling
  their footprint**, never one big room.
- **Spine links are plain exits; every other applicable direction,
  including diagonals, is a wired edge.** Air cells are deliberate
  negative space: fall lanes now, flight later.
- **A fall follows the column** (owner ruling 2026-09-16, #3580: "No,
  it would always follow gravity straight down. Essentially it's checking
  if it's a skyroom and if it is proceeding down."). A body in an air
  cell goes down its `down` exits and stops at the first room that is
  not air. There is no authored landing (`fall_room` is retired), so a
  ledge meant to catch a fall must be a room in that column. As built,
  an air cell with no `down` stops the body where it is (#3581).
- **A moving room keeps its doors** (owner ruling 2026-09-21, #3560).
  A lift, a crane car, anything whose doors open onto different places
  at different times has PERMANENT exit objects that are re-pointed per
  position, never deleted and rebuilt: a door that is not lined up is
  shut and hidden (`view`/`search`/`traverse` false, an authored
  `err_traverse`), or an edge over the air where a jump off works and a
  jump across is refused for want of a perch. Things tied to a door -- a
  rigged grenade -- then ride with it. "The exit should always exist as
  an edge working for jump off and only sometimes work for jump across."
  A shut door points at the air behind it as well as locking, because
  combat advance and charge relocate without asking the lock and refuse
  only an air destination. Only the LEAP scales with distance; the
  descent's landing roll is fixed (`DESCENT_DIFFICULTY`). `CraneContainer`
  (`move_to_level`) is the example of the whole rule; `ElevatorCar` shares
  the first half (its `out` exit is re-pointed per floor, and its landing
  doors refuse in `at_traverse` while the car is away, staying visible).
- **Every air build closes with the edge audit** — "edges accountable."
  No unexplained adjacency between a plate and the air beside it. The
  audit is a command, `@airfill/audit <z>` (#3582). It lists every
  walkable surface beside air to its north, south, east or west with no
  edge into it; a surface touching air only diagonally is counted, not
  listed, and does not stop the audit reporting "Clean." (`@airfill`
  never wires a diagonal). It also lists every gap whose far perch is
  missing or not one cell across, and every air cell with no `down`. It
  writes nothing. Paste its output in the build issue. A deliberate
  omission is marked on the room with `db.no_edge = "<reason>"` and the
  audit skips it.
- **The generator stays** (owner ruling 2026-09-16, #3415): `@airfill`
  stamps a roof's way into air as an edge only, and a gap only with a
  computed far perch.
- **"Walkable surface" has one definition, shared** (#3589): `is_surface`
  in `world/gravity.py` — a rooftop (`db.type == "rooftop"`) or any
  outdoor room (`db.outside is True`) that is not itself air.
  `CmdBuildTools` (`@airfill`) imports it from there. The same predicate
  decides what a shot over an edge can reach: an interior straight below
  an air cell reads as an unbuilt roof in the way and the shot finds
  nothing. So a plate that the audit will not link is also a plate nobody
  can snipe onto, by construction. The cell-addressed lookup behind the
  fill is `world.spatial.coordinate_index()`, shared with the crane car,
  the courier and the gravity layer.

**Doors and tenancy** (`proposals/VERTICALITY_AND_BUILDINGS_SPEC.md` §2–§3):
- A door IS the exit, with state; passage requires it open.
- Access is **biometric grants** — no keys, codes, or cards; forgery is
  the attack surface. Unit doors get the spring-latch autolock.
- Rentable units carry `residence_building` + `residence_origin` at
  build time — `memory`'s dossier depends on them.
- B&E is a PvE mechanic (📋 UNBUILT (no issue)): player-rented rooms are
  not burglary targets. Its seam is the door's `door_broken` flag, which
  nothing sets yet.

**The exit graph** (owner-set 2026-08-05): coordinates are truth,
exits are permission. Every room has a grid address, but the exit
graph stays deliberately **sparser than the lattice** — staggered
exits, places a little boxed in, never a door in every direction.
Enclosure is the point: it makes streets legible, gives quarters
mood, and turns wayfinding into exploration ("herding drunk cats so
they aren't dizzy" — the herding is invisible because the coordinates
stay honest). Corollary: the stingy ground graph is what makes the
roof city valuable — the roofs sell the diagonals the streets
withhold. Scope: this governs the STREET fabric; on plates the
vertical doctrine still wires every rim as an edge, because edges are
jumps priced in risk, not corridor exits.

**The room itself** (practice):
- **Five-senses descriptions** are the register — a room ships with its
  sense layers, not "desc now, senses later."
- Room `type` is load-bearing in several places: it routes **crowd-pool**
  ambience and sets the crowd modifier (`room_type_modifiers` in
  `world/crowd/crowd_system.py`), picks the room's **atlas class**,
  decides whether the neighbour glance can see into the room
  (`OPEN_AIR_ROOM_TYPES` in `world/crowd/crowd_messages.py`), sets the
  route cost (`ROUTE_COST` in `world/spatial/pathfind.py`) and a
  witness's role (`world/director/witness.py`), and names the room in a
  neighbour's exit list ("There is a stairwell to the west"). Set it
  deliberately; check each surface.
- The `outside` flag is weather and sky truth — the Toe breach doctrine:
  a hole in the hull means weather comes through it.
- Props are **seasoned, not stewed** — and branded.
- No key a player can target (item, fixture, body) carries a dash followed
  by digits (`Magpie-01`, `DX-15`). Evennia's ordinal form is `name-N`, and
  its parser cuts the name at the first `-N` that a space or the end of the
  line follows, so `2nd AWE Magpie-01 radio` quietly returned the FIRST
  twin (#3779). Write model numbers `DX15`, or leave them to the desc. An
  alias that ENDS in the number (`dx-15`) is safe. Room keys are exempt
  (`R1-02` berths, the `BRM S-2 Crane` cells): nobody picks a room by
  ordinal.

**The vertical city** (Greenhaus arc, builds 055–065, 2026-08-24/25):
- **Structures never stand over walkable cells**; only air crosses a
  street. Landmarks on tall legs with the lane dead-ending beneath are
  the sanctioned exception.
- **Crossings are straight lines** — collinear perch → air → perch,
  verified by query, because a jump's momentum does not turn corners.
- **A gap exit is its `destination` plus three attributes**: the
  `destination` is the air cell (a jump-off goes there and falls down the
  column below it), `is_edge` and `is_gap` are literal `True`, and
  `gap_destination` is the far perch (where a jump-across lands). There
  is no `sky_room` (retired by #3579). A gap with no usable perch is
  refused on the roof; build 060 is the cautionary tale of one-part
  wiring.
- **Demolitions evacuate occupants first**, and every vertical build
  closes with the audits run as queries: overlap, gap wiring,
  collinearity, and the edge audit.
- Every cistern gets a belly with a **pump socket** — rooms wait for
  systems, not the reverse.

## 2.5 · Build 001's laws (learned under review, 2026-08-05)

The first Head Builder arc was reviewed room by room; every verdict is
law:

1. **Audits find anomalies; the owner classifies them.** A sealed
   room may be a prize, an unwired gap may be a security perimeter,
   an "unroofed building" may be open sky. Audit findings reach the
   owner as *classified questions* (anomaly → my reading → proposed
   action) — never as work orders.
2. **No roof above an `outside` room, ever.** Open sky below is
   weather truth. No shared tool checks it: `@room` shows and sets the
   flag (`@room/outside on|off`) and `@building` does not test the
   roof/outside relation, so the builder checks it by hand. Only build
   001's own script ever refused it (`new_roof()` in
   `scripts/builds/001_old_town_roof_skeleton.py`, #1697).
3. **A unit's security perimeter includes its balcony.** Private
   terraces are not roof fabric; nothing public joins them.
4. **Furniture is demand-driven.** A tower, escape, or plank exists
   because the mesh steps there or the fiction demands it — never
   because the exemplar is convenient. Verticality for its own sake
   gets demolished.
5. **Tools serve; they don't steer.** The coordinate instruments,
   airspace finders, and reachability analyzers are for *verification*
   (edge audits, contradiction checks, no-gear proofs) and city-scale
   zoning. They do not generate build tasks. Design intent does.

## 2.6 · Build 003's laws (the fire escape, 2026-08-06)

6. **Narrative picks the room.** Communal fixtures wire from communal
   spaces (every escape window opens from a landing or hall, not a
   tenant's parlor) — adjacency serves the story, never the reverse.
7. **Read the mechanism before wiring against it.** Copying an
   exemplar's attributes is not understanding it: the escape's roof
   edge shipped without `sky_room` and silently degraded to a walk.
   (`sky_room` is retired, #3579: an edge's destination is the air cell
   itself.) Before touching jump/fall/door machinery, read its code path.
8. **Walk it as a player before handing it over.** Mechanism-level
   tests pass things only a player's experience catches (findable
   windows, message registers, ambience). The builder walks the build
   through real command flow before the owner ever sees a dbref list.

## 3 · The session ritual

The shape of a build session, in order. Steps compress for small builds;
none are skipped silently.

0. **The intent brief** — before any geometry: three to five lines on
   *what this place is, who uses it, why it exists, what it enables.*
   Architecture follows the brief; parkour affordances arise from the
   building's own logic (a fire escape exists for fire; the on-ramp
   is a consequence). A build with no brief is the water tower.
1. **Recon** — the live atlas plus `@building`/`@room` over the site.
   Agree the footprint and column on the grid before any digging.
2. **The name pass** — venue proper names, street names, unit numbering.
   Names are design; do them sober, first.
3. **Rooms** — dig, type, `outside`, crowd base, five senses.
4. **Coordinates** — give the new rooms their `xyz`, tag slopes, and run
   `@coordseed/check`: zero contradictions, and no existing room in its
   "would change coordinate" or "OCCUPIED cell" lists. `@coordseed`
   refuses to write while any room would land on an occupied cell,
   unless `/force` is given. Which writer owns `db.xyz` (the seed walk or
   hand placement) is not decided (see Not decided).
5. **The column** — strips, spines, edges, air cells; close with the
   edge audit.
6. **Doors and tenancy** where they apply — grants, latch, residence
   attrs, kiosk wiring.
7. **People and work** — posts named (built now or queued), gig/favor
   hooks grounded, shopkeeper/till wiring where trade happens.
8. **Props** — branded, one seasoning element per cell.
9. **The atlas gate** — verify on the live render; if the build
   introduced a new class or landmark, do the art: rig scene → sprite
   grind → `export_models.py` rebake, in the same arc, not "later."
9.5. **The player walk** — traverse the build end to end through real
   command flow (looks, exits, jumps, messages) as a player would,
   and fix what jars BEFORE delivering the dbref inventory.
10. **Ship** — the deploy cycle, and if a build taught doctrine, the
    playbook and the source spec get the lesson in the same PR.

## 4 · The remaining city — the ledger

**The active program: the SOUTHSIDE** (owner-set 2026-08-11, PR #1946,
closing #1945). The Braddock–Kaspar–Pessoa band and its Spillane
frontier. The program's named list:
- the owner's Constabulary 3×3 complex with holding facility (owner's
  own vision — feeds the future mines). A Colonial Constabulary already
  stands (`ConstabularyRoom` in `typeclasses/rooms.py`, #1110); this item
  is an EXPANSION of that building, and its holding facility is new;
- the Rendering Works on west Pessoa (approved in principle; digester
  underworks ramp = a sealed future sewer mouth);
- the Heat Works on Spillane's scorched west wall (x11, y-9..-11). That
  site falls inside the Atmospheric Processor's reserved 7×7 plot (§1.5);
  an owner call is needed before either is built (see Not decided);
- Pessoa infill: Boiler Run works, House of Selves, laundry, shift-bunks,
  brewery.

The Ripper stays parked until the Southside stands. The UNDERWORKS
remains deliberately unspecced — it will be inspired by what gets built
above it.

What the city still owes us, ranked by how much is already decided.
**Spec'd** items have documents; **named** items exist as owner calls in
banners and memory; **candidates** are unsettled proposals awaiting an
owner verdict — argue with them.

**Spec'd, waiting:**
- **The Ripper's den** (`GIG_RIPPER_SPEC`, pending owner review of §6
  legality + §7): sapient corpses → appraisal → cold-room resale, paid
  disposal. Wants the Brackett basement and a sewer connection —
  which makes it the natural *first customer of the sewer layer*.
- **Clinic completions**: cyberware-install rooms and the clinic's
  remaining sense layers — install space is also decking/chrome-economy
  pre-wiring. The install mechanic itself is in `world/clinic.py`
  (`CLINIC_CYBERWARE`, `parse_medical_request`, `resolve_cyberware`;
  #2354, #3046); what this entry owes is the room, not the capability.

**Named in doctrine, undesigned:**
- **The underground**: the ice mines feeding the terraformer (§1.5),
  plus the service galleries and the sewer the Ripper wants (Brackett
  basement link, paid disposal, B&E underworld, decking texture). One
  down-Z layer, several customers — design it as a layer, not as
  disconnected basements.
- **The water cycle made visible**: the central channel as aquaponics
  basin, vertical farm structures, rooftop green spaces — the
  solarpunk thread (§1.5). Each is a build; together they are the
  colony's metabolism on display.
- **Climbing-hooks content**: the mechanic is **doctrine-ruled**
  (see `PARKOUR_TEMPLATE_LIBRARY.md` §0: both directions, any edge,
  gear-length tiers, deployed lines thread room descs and can be cut,
  failure burns stamina not falls) but not built. The rooftop
  archipelago, the Boot hull, and Thawn's tower faces are the obvious
  first ascents; every build pre-wires the seams per the template
  library.
- **The tower you run up**: decking is explicitly gated on verticality's
  texture — "the corp tower you run up." Thawn-Harrison is the standing
  corp presence and its courtyard/cathedral register is already art;
  whether the run-up tower IS Thawn or a new build is an **owner
  call** (see Not decided).

**Owner-blessed designs awaiting their mechanics (2026-08-05):**
- **The Brackett fire escape, powered** (rough draft buildable NOW;
  full version later): the caged east-face escape (build 003) whose
  counterweighted bottom ladder is up out of reach — egress always,
  ingress only when someone times your entry with their exit, lowers
  the ladder for you, or beats the **control panel/crank at the
  lowest landing** that lowers the ladder and creates the exit — a
  prime hacking surface, with a manual crank/press fallback. Blocked
  on: the powered, hackable control itself (📋 UNBUILT (no issue)).
  Re-pointing an exit at runtime already exists: see §2, "A moving room
  keeps its doors" (`CraneContainer.move_to_level`).
- **The Shipbreaker mobile gantry**: not a fixed catwalk — a crane
  that **rotates and re-aims its arm**, a movable bridge to multiple
  locales, hackable like the ladder-crank. The yard's industry and a
  traversal instrument in one. Blocked on: the same powered, hackable
  control (📋 UNBUILT (no issue)); build nothing fixed in the yard
  meanwhile.
- Both are one future system wearing two clothes: **powered,
  hackable furniture that edits the exit graph at runtime**. When
  decking/hacking design begins, start here.
- **Exit-type refinements (owner go, 2026-08-06)** ride the same
  arc: drop ladders (one-way until worked), auto-closing windows
  (egress that shuts behind you), and decking elements surfaced as
  exit behavior. The fire escape's current exits are the plain-verb
  rough drafts of all three.

**Captured from the architecture sessions (2026-08-06 sweep —
solid ideas that lived only in conversation until then):**
- **The Dark Alley building** — the Dark Alley (a dead-end cell off
  Maxwell at (-8,-5)) is a true alley surrounded by empty lots: it
  was carved ahead of its block. Build a modest 2-3 story rooming
  house/workshop beside it whose back door and escape face the alley
  — the alley-backed F1 in its correct fiction, and the proposed
  proving build for the corrected process.
- **The alley-carving law**: the city has an alley deficit while the
  roofscape needs alleys as its driveways — new ground blocks carve
  their back alleys as part of the block. **Overflow Alley** at
  (13,-15,0) (build 063, PR #1934) is also a true alley:
  `type: "alley"`, outside=True, a walkable dead-end spur off the
  Spillane under Cistern No. 3's legs (`scripts/builds/063_cistern_three_real.py`),
  which `VERTICALITY_AND_BUILDINGS_SPEC` cites as the sanctioned
  landmark-on-legs exception. Shipbreaker Alley does not count: it is
  typed `market`, and build 001 classified it an open-air yard — the
  ruling §2.5 law 2 came from.
- **The heel-void nook** at (-9,-18,0): the one roomless ground cell
  in the Brackett block, boxed between the Boot's heel and the
  tenement's east wall. A genuinely hidden space for when the block
  wants a secret (Ripper-adjacent, perhaps).
- **The east bridge**: the Spillane dead-ends at the channel's south
  bank — continue it across as the city's second crossing (freight
  loop pad↔works; convergence and siege value both).
- **The Wall Run as designed** (elevations reviewed 2026-08-05):
  Brackett + new exterior iron as trailhead → terraces at z7 / z10
  (cut stair) / z9 finger / z13 (**the cliff bar — prize**) / z12
  valve-landing / z16 / z18 → the ONE rim terminus at z20, with the
  Braddock cut-stair as the free route. ~20 rooms; the hard-ring
  exemplar; buildable almost entirely against existing mass. The source
  plate (`scripts/planning/corridors.py`) was drawn against an
  8-storey Brackett and hangs the corridor off a z8 roof (roof(z8) →
  Terrace I(z7)); the Brackett now carries a roof deck at z16 and a mast
  platform at z19, so that z8 roof does not exist and the design needs
  re-deriving before it is built. Re-derive from coordinates, not from
  the plate's E/W captions — those read swapped against game space
  (east = +x since #1690).
- **The Central Channel design sheet** (owner-deferred, "later", but
  the analysis was blessed as interesting): quays are Tolliver/
  Maxwell as-built; raft lanes + clear barge fairway at z-1; racks
  and desc-only bank galleries at z-2; exactly FOUR underwater rooms
  carry the layer (Span Roots x2, Intake Vault west, East Grate);
  **water is the city's soft-fail** (falls ending in the basin land
  safe — the parkour nursery); diving = gear-tiered like hooks.
- **Hidden exits** (owner-named) exist as a general mechanic: an exit
  locked `view:false()` is left out of the exit list, and `search` can
  find it for that searcher alone, against its `db.search_difficulty`
  (default 14; `search_hidden_exits` in `world/stealth.py`). The covert
  on-ramps they were named for, such as climbing in through the
  fire-escape windows, are 📋 UNBUILT (no issue) and ride the same
  future arc as the crank panels and auto-closing windows.

**Candidates (unsettled — owner verdict wanted):**
- **A true market hall**: stalls exist as street props; a roofed market
  venue would host hawker posts, gig-board density, and fence/pawn
  texture (P3 pawn was rejected once — a market revives the question
  only if the owner does).
- **The port**: the Colonial Landing Pad exists as a pad; a working port
  district (freight, customs, the Longhaul/Slowboat brands made flesh)
  would ground the logistics economy and give the pad a reason.
- **The gate-anchor site**: the atlas lore names processor stacks and a
  gate anchor from the terraform mission. As a district it would be the
  colony's one monument to being stranded — high lore risk, high
  payoff, entirely an owner call on what is true there.

## 5 · Fitting it together

The connective tissue, so individual builds sum to a city:

- **Every build feeds the loop**: place → post → work → favor → rep.
  A build that adds rooms without adding work must justify itself as
  connective tissue (streets, air, sewers) or refusal (ruins).
- **Systems snap on later, so seams go in now**: posts before NPCs,
  height before flight, files before decking, faces before climbing.
  The cheap version of a future system is an attribute set today.
- **The atlas is the shared truth**: builds are architected on the live
  render, verified on it, and owe it art when they change its
  vocabulary. If it isn't on the atlas, it didn't happen.
- **Doctrine lives here**: when a build fights the playbook and wins,
  the playbook changes in the same PR. When it fights and loses, the
  build changes. Silence is the only wrong outcome.

## Not decided

- **The Northside anchor** (§1.5): whether the 16–18-story anchor is
  Thawn grown upward or a new name — owner call, pending.
- **The run-up tower** (§4): whether the tower decking runs up IS Thawn
  or a new build — owner call.
- **The Heat Works site** (§4): its given site, (x11, y-9..-11), lies
  inside the Processor's reserved plot (x5..11, y-11..-5). Owner call
  needed before either is built.
- **Who owns `db.xyz`** (§3 step 4): the seed walk or hand placement.
- **The Ripper's den** (§4): `GIG_RIPPER_SPEC` §6 (legality) and §7 are
  pending owner review.
- **The candidates** (§4): market hall, port, gate-anchor site — each
  awaits an owner verdict.
- **Diagonal edges** (§2, the vertical doctrine): should plates wire
  diagonal edges by hand, or should the doctrine drop diagonals to match
  `@airfill` and its audit, which work north, south, east and west only?
- **One-shot build scripts** (§3): should the ritual state that a world
  change is a numbered one-shot script in `scripts/builds/` (dry run
  first, rooms named by dbref and checked against their current key,
  idempotent, run once, then a reload)?
- **Clinic completions** (§4): is the live Maxwell Operating Room the
  cyberware-install room this entry asks for, so that the entry shrinks
  to the remaining sense layers?
- **Diagonals in the air audit** (§2): should `@airfill/audit` count a
  surface that touches air only diagonally as a finding, so that "Clean."
  matches the vertical doctrine, or keep it as an advisory tally beside
  the findings, as #3582 designed it?

## Related documents

- `proposals/SPATIAL_COORDINATE_SYSTEM_SPEC.md` — the grid.
- `proposals/VERTICALITY_AND_BUILDINGS_SPEC.md` — doors, tenancy,
  verticality.
- `PARKOUR_TEMPLATE_LIBRARY.md` — the movement kernel and ascent
  templates, companion to §1.5.
- `NPC_POSTS_AND_REINCARNATION_SPEC.md` — durable posts.
- `proposals/GIG_RIPPER_SPEC.md` — the Ripper's den.
