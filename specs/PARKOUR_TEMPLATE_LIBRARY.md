# The Parkour Template Library — companion to the Building Playbook

This is the companion to `BUILDING_PLAYBOOK.md` §1.5 (traversal). §0 records
the owner-ruled movement kernel; that part is law. §1–§3 are the layout
doctrine derived from it and the reusable architectural templates that make
the street-to-precipice guarantee *amazing* rather than merely solvable. The
rappel/grapple hook is not built (📋 UNBUILT, no issue); the kernel rulings
exist so every build pre-wires its seams.

---

## 0 · The movement kernel (owner-ruled 2026-08-05)

What a body can do. Templates are derived from these numbers; changing
a number reopens the templates.

- **Jump across**: one cell, ever (including diagonals). Owner-locked:
  multi-cell leaps add complexity for us and the player and are out.
  Motorics roll vs `gap_difficulty` (default 10); failure is a fall
  down the air cell's column, or, where the gap has no air cell, a slip
  in place for one storey's damage (`handle_gap_jump` in
  `commands/combat/jump.py`). The code does not check the span: the leap
  lands wherever `gap_destination` names, so the one-cell rule is kept by
  how things are built.
- **Falls**: gravity walks sky cells to ground at **5 damage/story**.
  Risk therefore scales with height automatically — the same gap is a
  scraped knee at z2 and 70 damage at z14. Fall damage lands on the legs
  first: `apply_fall_damage` in `world/gravity.py` fills the feet, then
  the shins, then the thighs, then the other limbs, then the rest, so a
  long fall smashes the legs before it reaches anything vital. How lethal
  a fall is has not been tuned (`specs/roadmaps/BALANCE_LEDGER.md`).
  How a fall plays out:
  - **One number, every verb.** `FALL_DAMAGE_PER_STORY` (5) × cells
    actually passed, charged by `world/gravity.py` at the bottom of
    whatever column the body fell down. `jump off` and `jump across` both
    use it. No exit carries a damage number.
  - **Two cases have no column**, and the jump verb charges them itself, a
    flat one storey (5) with no landing roll: `jump off` an edge whose
    destination is not an air cell (`handle_edge_descent` in
    `commands/combat/jump.py`), and a missed `jump across` with no air cell
    between the two roofs, where the jumper slips and stays put
    (`handle_fall_failure`).
  - **The fall follows gravity straight down the column**: in a sky room,
    proceed down; the fall ends at the first room that is not a sky room.
    There is no authored landing. An apron, awning or terrace that should
    catch a fall is a ROOM in the column (`is_sky_room` False), never an
    attribute. No fall path reads `fall_room`; it is retired (#3580,
    2026-09-16) with no reader anywhere, the map exporter included.
  - **A missing column stops the fall cleanly.** A cell with no `down`, a
    `down` whose destination no longer resolves, or a column longer than
    `FALL_MAX_CELLS` (30) stops the fall in that cell, with a message and
    no damage. That clean stop is the parked impasse, #3581: it is the
    right behaviour for a column that does not exist, not a fix for the
    column not existing. The colony's highest crossings still hang over air
    cells with no `down` beneath them (📋 UNBUILT, #2945; see §4). Build the
    columns; the code will fall down them.
  - **A fall is a real traversal a watcher can see.** Owner (2026-09-16,
    #3579): "They should traverse the air rooms falling... if I'm flying in
    a room or in a flying vehicle in one of the sky rooms, I'd see someone
    fall past me." One cell per second (`FALL_SECONDS_PER_CELL`), announced
    to the cell left, the cell entered, and every walkable surface beside
    it.
  - **Gravity is a property of the room.** `Room.at_object_receive` calls
    `world.gravity.on_enter_air` for every arrival, so a shove, a drop, a
    throw, a build script or a reconnect into an air cell all fall, not
    just the `jump` flow. Walking into a sky room triggers falling. A
    player typing a direction is refused at the sky block in
    `Exit.at_traverse`, which has no exception at all.
  - **A reload does not strand a faller.** The fall is a persistent
    `db.falling` record and `sweep_airborne` resumes it at boot, so a
    reload mid-fall costs a beat. The one exception is a `jump across`
    inside its single airborne tick; see `specs/JUMP_COMMAND_SPEC.md`'s
    2026-09-16 known-limits addendum.
  - **The seam for the gear tiers**: `db.stays_aloft is True` is the single
    strict predicate gravity asks before it drops anything, so a hook line,
    a paraglider, a jump jet or a flying vehicle each land on that one
    attribute rather than on a new branch in the fall code.
- **The authored surface of an edge or gap** is exactly `is_edge` /
  `edge_difficulty`, plus `is_gap` / `gap_difficulty` / `gap_destination` on
  a gap. The edge's own `destination` is the air cell; `sky_room` is not
  required and no longer exists, and there is no degraded plain-walk
  fallback to guard against. `fall_damage`, `fall_distance` and `sky_room`
  have no runtime reader left; the `fall_damage` still authored on gap exits
  is retired data on every path. `gap_width` is still written by a few
  build scripts and by `CraneContainer._set_door` in `typeclasses/rooms.py`,
  but nothing reads it.
  *Overturned intention (2026-09-16, #3579):* `jump off` used to charge a
  per-exit `exit.db.fall_damage` (default 8, from 5 to 20 on different
  exits) while `jump across` charged 5 per storey; one geometry constant
  replaced both. Owner ruling
  (2026-09-16): "we'll have cyberlegs... parachutes, flight... but
  calculating potential damage based on geometry will always be
  relevant." Geometry is the base; per-exit damage numbers were the thing
  standing in its way.
- **Fire-escape rooms** are `type: "fire escape"` — their own exit-message
  list (exits.py) and ambience category (ROOM_TYPE_POOLS) exist; new room
  types join both registries.
- **Edges**: any edge is a valid hook anchor. **No authored anchor
  points** — exploration is encouraged, not fenced; the *building
  design* does the fencing, never the mechanic.
- **The hook (rappel/grapple), when built** (📋 UNBUILT, no issue): works
  **both directions** — secure a line to an edge or roof (above or below),
  then ascend or descend it. A deployed line **integrates into the room
  descs** of its anchor room, every sky room it threads, and the landing
  room; it is visible infrastructure. A line can be **unhooked —
  potentially while someone is on it.** Gear is **recoverable** (lines are
  valuable, lendable, stealable). Use rolls **Motorics**; failure to
  ascend/descend **burns stamina** (future stat) (📋 UNBUILT, no issue),
  never causes a fall.
- **Range is the gear**: each make/model of hook has its own max line
  length at its own price point (branded, per the world rule). Length
  IS the progression: a cheap line opens the low roofs, the rim-rated
  line is endgame kit. The tier ladder is an owner-priced decision for
  later (see §5); templates below only assume that *short is common and
  long is rare*.

**The verb split this produces** — the load-bearing design fact:

| Verb | Speed | Risk | Gate | Exposure |
|---|---|---|---|---|
| Jump | fast | fall damage (5×height) | Motorics | a moment |
| Hook | slow | stamina only | gear length + Motorics | a visible line others can use or cut |

The "5×height" row holds for both `jump off` and `jump across` over any
wired column, because there is one number.

A jumper who holds someone in a grapple drags them off an edge too.
The held body cushions the landing and takes most of the damage (the
`FALL_BODYSHIELD_*` shares in `world/combat/constants.py`, applied by
`_land_with_bodyshield` in `world/gravity.py` and by the direct-drop
branch of `handle_edge_descent`). A `jump across` lets go of the hold
instead.

Jumping is the free, dangerous, kinetic verb. Hooking is the safe,
paid, social verb. Amazing parkour keeps both honest: every corridor
must be solvable by jumps-plus-built-ascents alone (no pay-to-climb),
and hooks buy *shortcuts, safety, and rescue* — never the only path.

## 1 · Design invariants (the math, applied)

1. **The graph is asymmetric.** Across-and-down is a web; up is
   scarce (built ascents; later, gear). The free route up any corridor
   is a **sawtooth**: climb a shaft (+k stories), flow across/down
   several roofs, climb again. Target rhythm ≈ **1 up-move per 4–6
   across/down-moves**.
2. **Height is the difficulty curve.** Don't inflate `gap_difficulty`
   with altitude — exposure already does it. Tune difficulty for
   *rhythm* (easy flow, one hard beat, rest), and tune *what is
   underneath* for stakes.
   This is enforced arithmetic (#3579). The LANDING roll adds
   `FALL_LANDING_DIFFICULTY_PER_CELL` (2) per storey fallen on top of the
   edge's `edge_difficulty`, so altitude is charged once, automatically,
   in the only roll that altitude should touch. An author who also loads
   altitude into `gap_difficulty` is **double-counting it** — the takeoff
   roll is about the span, the landing roll is about the drop. Keep
   `gap_difficulty` about how far the gap is. An edge that authors no
   `edge_difficulty` rolls against 8 (`FALL_EDGE_DIFFICULTY_DEFAULT`),
   and every `@airfill` edge is bare. Only a `jump off` into an air
   column rolls to land; a shove, a throw, a missed leap or a direct drop
   does not.
3. **Soft-fail low, hard-fail high.** Learning sections route over
   fall interceptors (terraces/awnings 1–2 stories below the gap,
   capping a botch at ≤10 damage). The climax near the rim earns its
   full street-drop exposure.
   The arithmetic (#3579): a 2-storey apron botch is
   `FALL_DAMAGE_PER_STORY` (5) × 2 = **10**, which is exactly the cap
   this invariant asks for, on both verbs, over any wired column. On an
   EDGE descent a made landing roll absorbs
   `FALL_LANDING_ABSORBED_CELLS` (2) storeys — so over an apron at 1–2
   storeys a competent descent is **entirely free**, and the apron
   punishes only the miss. A failed `jump across` never rolls to land,
   so the full 10 stands on a botched leap. That is the intended
   asymmetry: the leap is the risk, the descent is the skill.
4. **Valves are deliberate.** A drop of ≥2 stories is one-way without
   a line. Count them per corridor; each is either an escape route, a
   commitment point, or a mistake.
5. **Branch or confess.** Every plate offers two onward options where
   possible; a dead end is a **prize** (vantage, stash, scene), never
   an accident.
6. **Brevity binds rooftops too.** A roof strip earns its cells: each
   cell is a rung, a choice, or a place two players can meet. Sightline
   prose does the scale; the room count stays lean.
7. **Lines are content.** Because deployed lines thread room descs and
   can be cut, a hook route is a *social event* — leaving a line up is
   a gift or a trap; cutting one is a statement. Build vantages that
   overlook popular anchor edges.

## 1.5 · The Roofscape — the second city (owner vision, 2026-08-05)

The streets are the first city: public, watched, routed by the grid.
**The roofs are the second city**: trespass, direct, diagonal — a
shadow circulation network that begins one story up (the Laundromat
Rooftop datum, z1) and climbs, eventually, all the way to the high
mesh. Crossing the colony without touching the ground is not a stunt;
it is **a milestone in itself** — the player's graduation from the
first city to the second. Everything in this section serves that.

**The mesh, not the ladder.** The roof city is not one plane and not
a stairway — it is a **terraced mesh** of small planes at staggered
heights, stitched by furniture. The law of the mesh:

- Adjacent roofs within **±1 story** are native fabric where they
  TOUCH: walk the join, clamber the step. **Across a street or
  alley, a crossing exists ONLY between EQUAL roofs** (owner law,
  Roof Plan v3): 1:1, bi-directional, no damage — span-1 through an
  air cell with the fall waiting below, the archipelago pattern
  exactly. Unequal faces across a street are not a crossing; where
  connectivity needs one, equalize the buildings.
  **Wiring requirement (#3579): "the fall waiting below" has to actually
  be wired.** A span-1 air cell needs a one-way `down` (key `down`, alias
  `d`) to the next cell, and that chain has to reach something that is
  **not** an air cell — ground, a terrace, an awning, anything solid.
  Without it the crossing still works and the miss still falls, but the
  fall stops dead in the first cell with no floor: no damage, no landing,
  a body hanging in open air. That is the parked impasse (#3581) doing
  the right thing with world data that is missing (#2945). A crossing
  whose column is unbuilt is a crossing with no stakes — build the column
  in the same pass as the gap.
- Steps of **2–3 stories** are bridged by **furniture** (§2.5), never
  by accident: a water-tower ladder, a fire escape, a shed roof.
- Steps **greater than 3** are district boundaries — valves and
  ascent cores (T2/T4); the mesh deliberately breaks there.
- **Edges are preserved at every height.** A roof keeps its full edge
  wiring in all directions at its own level, whatever its neighbors
  do. A taller neighbor doesn't erase the edge — it makes it a wall
  face (hook country). A lower one makes it a drop (one-way, or
  two-way once furniture arrives). No height change ever silently
  deletes a direction.
- **A roof with nothing but edges is a tactical spot, not a trap**
  (owner ruling 2026-09-16, #3583). Combat movement will not carry
  anyone over a drop: `flee`, `advance` and `charge` all refuse an edge
  exit, a gap exit or an exit into air for anyone whose `db.stays_aloft`
  is not `True` (one predicate, `can_leave_by`, in `world/gravity.py`).
  So nobody can be chased onto such a roof and nobody can back off it —
  the only way out is the jump, and the jump costs what fleeing costs —
  the aim contest and the melee disengage roll both, each with an
  opportunity attack waiting on a lost roll (#3583, #3591). A lost roll
  does not stop the jump; only an attack that leaves the jumper dead or
  unconscious does (`pay_the_price_of_leaving` in
  `commands/combat/jump.py`). A jump that cannot happen is refused before
  any roll and costs nothing (#3685): a jumper who is being grappled, who
  is channeling, or whose escortee cannot follow over the edge. A missed
  `jump across` with no air cell under the gap slips in place and sets
  the jumper to skip their next combat round (`handle_fall_failure`).
  Owner: *"It would be
  refused at the edge… Ideally, very few rooftops will exist without
  exits though — so ending up on one where all you can do is jump is a
  tactical challenge."* Read that as a **budget, not a ban**: build the
  edges-only roof deliberately and rarely, as the beat where a corridor
  commits the player, and give every other plate a walkable way off per
  invariant 5. The stakes come free — the drop below is already the
  price — but only if the column beneath it is wired (see the wiring
  requirement above).

**Street width is a design tool.** One cell wide = the roof city can
cross it (span-1 law). Two wide = a wall at roof level. Widen streets
exactly where the second city *should* break; keep alleys one wide
always — **the back alley is the roof city's driveway**, the seam
where fire escapes hang and drainpipes climb.

**The 4X seam: exploration is the progression.** The roof city is
discovered, not given. The atlas stays vague about it (the player
tier never draws routes); **vantage reveals** — climb the water
tower and the quarter's roofscape lays itself out below you; **routes
are knowledge** — "the way across Kaspar without touching ground" is
a thing a character knows, teaches, sells, or dies keeping. The
milestone ladder every quarter should support:

1. **The First Step** — street to any roof, by any furniture.
2. **The Street Cross** — the first air-cell crossing (the
   Laundromat → Market Rooftop line over Braddock).
3. **The Block Run** — around one block, no ground.
4. **The Quarter Run** — a named end-to-end (Braddock to the channel
   bank, say) that the quarter's whole mesh exists to make possible.
5. **The High Line** — first sustained z8+ mesh (the megablock
   gallery/skyway tier).
6. **The Precipice** — the rim, by any corridor. The 4X endgame.

## 1.6 · The difficulty rings (owner-set, 2026-08-05)

Difficulty is geography: two rings per side of the channel, inner and
outer, with the south gentler than the north at every radius.

- **EASY — the south inners** (Old Town, the banks, the works, the
  fringe streets). The learning fabric: 1:1 roof streets, equal
  crossings, aprons under everything, furniture bidirectional, fail
  cost capped low. Where the First Step, Street Cross, and Block Run
  milestones live. **Exception: the Terraformer** — a HARD island in
  the easy ring; the monument plays by its own rules.
- **MEDIUM — the north inners** (bank → podium → high band → spires).
  The same grammar at real exposure, and the first sanctioned
  **toll drops**: across-and-one-down, a bite of damage, no backtrack
  — you pay HP for the shortcut and detour back by furniture. Grapple
  starts earning its price here as convenience, not requirement.
- **HARD — the south crater wall** (the Wall Run, the terraces). The
  inhabited wall: one-way drops routine, 2-3-story steps everywhere
  (furniture mandatory), the grapple as the *backtrack* tool, honest
  exposure above the aprons' reach. Gear-gated in practice, never in
  principle — the cut stair remains the free route.
- **ULTRA — the north crater wall.** The bare wall: no dwellings, no
  resident kindness, no furniture. Long grapple tiers, multi-story
  commitment drops, rim approaches for the 16-20 arena — **paraglider
  country**. The hardest honest traversal in the colony, and it looks
  down on everything.

**The gear ladder maps onto the rings**: bare hands (easy) → short
line (medium) → long line (hard) → **the paraglider** (ultra) — a new
gear class entering the kernel: glide descent with lateral reach, the
escape from pockets that one-way drops create (📋 UNBUILT, no issue).
Its numbers (glide ratio, launch requirements) are an owner call for
when the kit builds (see §5); until then, high builds reserve **launch
points** (a parapet with a wind note) the way roofs reserve anchor
edges — seams now, straps later.

## 2 · The templates

Each: intent → shape → wiring → hook seam → social note. Heights are
relative (z+n from the template's base).

### T1 · The Sawtooth Block — the corridor unit
The repeatable module of an ascent corridor. Four to five buildings:
an **ascent core** building (T2) rising +3 or +4, then a roof chain
stepping level or down — e.g. 4 → 4 → 3 → 2 — with one-cell gaps
between. Wiring: spine exits along each roof strip, gap edges
(difficulty 8–12) between buildings, every open face an edge. The
chain's last roof sits within one story of the next module's core
entrance. **Hook seam**: the core's roof edge is the natural anchor
for a line back down the whole module. **Social**: the core's street
door is the module's convergence point — put a venue in it.

### T2 · The Ascent Core — the free "up"
One building per module carries the climb: external fire-escape,
scaffold stair, or interior stairwell venting onto the roof. It serves
its neighbors, not just itself — within a story of two or more
adjacent roofs. This is where the 1-per-module up-move lives, so make
it *worth walking*: the stairs pass lived-in windows, landings are
sense-rich, the roof door is a place. **Hook seam**: its parapet is
the module's longest clean drop — the premium rappel edge.

### T3 · The Soft-Fail Apron — the net you can stand on
Mid-height fabric under learning gaps: awnings, loading canopies,
terrace bars, laundry decks at 1–2 stories below roof level. A botched
jump lands here (≤10 damage), embarrassed but alive — and the apron is
itself a place (the terrace you crash onto is somebody's evening).
Wiring: the apron is a room with edges up to nothing and a stair or
ladder back to street. **Social**: aprons under popular gaps become
audiences.

### T4 · The Commitment Valve — the one-way door
A deliberate ≥2-story drop separating regions: jump down it freely,
return only via a line or the long way around. Use at corridor
boundaries and escape routes (the getaway that pursuers must *choose*
to follow). Wiring: edge with jump-down; no built return. **Hook
seam**: the valve is where a carried line pays for itself — or where a
pre-hung line waits, until someone cuts it.

### T5 · The Prize Roof — the dead end that's worth it
Reached by the corridor's hardest single beat (its one difficulty-14
gap, its longest exposure). No onward route — the reward is the place:
the best vantage in the quarter, a stash spot, a scene stage, the
rooftop garden (§1.5's solarpunk thread lives well here). One per
corridor is plenty. **Social**: prize roofs are where the city's
secrets change hands.

### T6 · The Skyway Junction — megablock connective tissue
Northside grammar. An enclosed bridge (weatherproof, `outside` false)
meeting a tower's gallery level; the junction room is a funnel — paths
from two blocks and a lift lobby cross in one place. Skyways sit at
consistent gallery heights (pick one or two datum levels per district
so bridges chain). The skyway ROOF is itself a parkour rung — the fast
crowd runs on top of the fabric the slow crowd walks inside, and they
see each other through the glass. **Hook seam**: skyway roofs are
mid-height anchors bridging tower sawteeth.

### T7 · The Wall Terrace Run — the southside geology climb
The crater face as a staircase of inhabited terraces. Terraces stack
at 2–4 story intervals connected by cut stairs, ladders, and — this is
the register — **rappel culture**: the wall fringe is where lines live
permanently, hung by residents, maintained like laundry lines,
watched. The free route zigzags the built stairs; lines cut the
corners. Sloped-exit tags carry the split levels. **Social**: each
terrace is a micro-commons with the whole colony below it; the best
cliff bar in the city belongs here.

### T8 · The Processor Spiral — the industrial ascent
The southern monument's climb: catwalks helixing the cone, alternating
exterior exposure (wind, the view, real fall stakes) with interior
galleries (machine halls, no exposure, sense-rich). Long continuous
ascent broken by service platforms every 3–4 stories — each platform a
valve or a rest, some with work (§1 criteria: the Processor is a gig
magnet). The spiral is the corridor where exposure discipline (§1.3)
peaks: the top turns earn the colony's hardest honest jumps. **Hook
seam**: the spiral's platforms are the rim-rated line's proving
ground.

## 2.5 · The furniture — little nuances that move you

The mesh's connective tissue is furniture, not architecture: cheap,
authored, desc-integrated, each one a small verb. Every piece does
one of four jobs — **on-ramp** (ground/interior → roof), **step**
(roof → roof ±1..2), **crossing** (over a gap), or **apron** (under
one). A build's parkour budget is measured in furniture, and one or
two pieces per building is plenty.

- **F1 · The fire escape** — the workhorse on-ramp. The exemplar is
  **the Brackett fire escape** (landings (-8,-18) z3-z6). Its laws:
  windows are **communal** — they open from each floor's landing/hall,
  never from private units (a unit's security perimeter includes
  everything of its own); exit key `window`, no aliases; the iron works
  both ways; the bottom is a **one-way drop** (ascent from below waits
  for the crank/grapple era, 📋 UNBUILT, no issue); it can end on a ROOF
  or HULL rather than the ground, feeding the second city directly.
  Egress always; ingress is the future hidden-exit mechanic. Copy the
  exemplar, not this paragraph. Copy its rooms and exits, not its East
  Roof edge block: that block still writes the retired `sky_room` /
  `fall_room` / `fall_distance` / `fall_damage` (#3579, #3580), with a
  comment calling `sky_room` required. An edge needs only `is_edge` and
  `edge_difficulty`, and its destination is the air cell.
- **F2 · The water tower** — the step-stone crown. Ladder up a leg,
  tank-top platform +1..+2 above its roof with its own edge set: it
  takes a roof HIGHER without a new building, bridges to the taller
  neighbor the roof itself couldn't reach, and doubles as vantage
  (4X reveal) and hook anchor. The register's favorite silhouette.
- **F3 · The roof hatch / stair head** — the interior on-ramp; the
  free route. Locked or not is a social decision per building.
- **F4 · The shed step** — machine room, HVAC block, stair head, any
  +1 box ON a roof. Splits one roof into two legible levels, each
  with its own edges; the micro-step that lets a z3 plane reach its
  z4 neighbor. The mesh's smallest and most-used rung.
- **F5 · The drainpipe / conduit run** — the grubby on-ramp: alley to
  roof, +2 at most, Motorics-checked where the fire escape is free.
  Where the escape is the front door of the second city, the pipe is
  its window.
- **F6 · The awning / canopy** — apron under a learning gap (T3 at
  furniture scale) and a step: awning → sill → parapet takes a low
  roof from the street with no ironwork at all.
- **F7 · The plank & line** — resident-made crossings: a scaffold
  plank over an alley, boards lashed between parapets. The make-do
  register building its own skyways; narrow, sometimes rated (a roll
  to cross fast), always cuttable — the poor man's deployed line.
- **F8 · The billboard / mast** — +2 vantage and anchor; the sign you
  climb behind, the antenna you shinny. Reveal and rappel points.

**Composition checklist for every new ground build** (this is the
honing — answered at design time, like the playbook's six):

1. **Roof datum**: what height is the roof plate, and is it within
   ±1 of an adjacent roof (native mesh) or furniture-bridged (F2/F4)
   to one? A roof that joins no mesh is an island — say why.
2. **On-ramp**: at least one of F1/F3/F5/F6 — how does the second
   city get ON this building, and does a window meet the escape?
3. **The back**: which face is the alley face, and what hangs there?
4. **Steps**: if a neighbor differs by 2–3, which furniture bridges
   it? If by more, is that break intentional (valve / boundary)?
5. **Edges**: full wiring at the roof's own height, every direction,
   including toward taller walls (future hook country).
6. **The reveal**: from this roof, what does a player *see* — the
   next rung, the quarter, or a secret? Every roof answers with at
   least a sightline; the good ones answer with a route.

## 3 · Composing a corridor

1. Choose the route's character (architecture / geology / industry).
2. Chain **T1 modules** to gain altitude at the sawtooth rhythm;
   place **T2** cores at the module seams.
3. Under every learning gap, a **T3 apron**; between regions, a **T4
   valve**; at the summit approach, the corridor's **T5 prize**.
4. Wire per doctrine (spines, edges incl. diagonals, air deliberate),
   difficulties tuned for rhythm not altitude, then run the **edge
   audit** — and when the analyzer exists, the reachability check:
   street cell to rim cell, jumps-and-built-ascents only, no gear.
5. If the free route fails, the layout is wrong — fix geometry, not
   difficulty numbers.

The analyzer (`export_map` + kernel numbers → reachability overlay on the
atlas; 📋 UNBUILT, no issue) would automate step 4's proof and the parked
global edge audit; until then, corridors are proven by hand against this
checklist.

## 4 · Unbuilt

Each is described where it belongs; this is the index.

- 📋 UNBUILT (no issue) — **the hook (rappel/grapple)**, §0: both
  directions, any edge, lines in room descs, cuttable, recoverable gear,
  Motorics use, failure burns stamina.
- 📋 UNBUILT (no issue) — **stamina**, the future stat a failed hook
  ascent/descent burns, §0.
- 📋 UNBUILT (#2945) — **the missing fall columns**, §0 and §1.5: the
  colony's highest crossings hang over air cells with no `down` beneath
  them, so the one place the fiction promises a death sentence still
  delivers a pause in mid-air.
- 📋 UNBUILT (no issue) — **the paraglider**, §1.6; high builds reserve
  launch points now.
- 📋 UNBUILT (no issue) — **ascent from below a fire escape** (the
  crank/grapple era), §2.5 F1.
- 📋 UNBUILT (no issue) — **the reachability analyzer**, §3.

## 5 · Not decided

- **The hook tier ladder** (§0): the make/model line lengths and their
  prices are an owner-priced decision for later.
- **The paraglider's numbers** (§1.6): glide ratio and launch
  requirements are an owner call for when the kit builds.

## 6 · Related documents

- `specs/BUILDING_PLAYBOOK.md` — §1.5 (traversal), which this document
  serves.
- `specs/JUMP_COMMAND_SPEC.md` — the `jump` verb, including its
  2026-09-16 known-limits addendum.
- `specs/roadmaps/BALANCE_LEDGER.md` — the fall and landing constants and
  their tuning state.
- Code: `world/gravity.py` (the fall, `apply_fall_damage`,
  `_land_with_bodyshield`, `can_leave_by`, `on_enter_air`,
  `sweep_airborne`), `commands/combat/jump.py` (`handle_gap_jump`,
  `handle_edge_descent`, `handle_fall_failure`,
  `pay_the_price_of_leaving`), `world/combat/constants.py` (the `FALL_*`
  constants).
