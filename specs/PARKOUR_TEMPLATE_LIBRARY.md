# The Parkour Template Library — companion to the Building Playbook

> **Status:** 🧭 LIVING DOCUMENT (2026-08-05), companion to
> `BUILDING_PLAYBOOK.md` §1.5 (traversal). §0 records the owner-ruled
> movement kernel — that part is law. §1–§3 are the derived layout
> doctrine and the reusable architectural templates for making the
> street-to-precipice guarantee *amazing* rather than merely solvable.
> The rappel/grapple system is **not yet built**; the kernel rulings
> exist so every build from today pre-wires its seams.

---

## 0 · The movement kernel (owner-ruled 2026-08-05)

What a body can do. Templates are derived from these numbers; changing
a number reopens the templates.

- **Jump across**: one cell, ever (including diagonals). Owner-locked:
  multi-cell leaps add complexity for us and the player and are out.
  Motorics roll vs `gap_difficulty` (default 10); failure is a fall.
- **Falls**: gravity walks sky cells to ground at **5 damage/story**.
  Risk therefore scales with height automatically — the same gap is a
  scraped knee at z2 and a death sentence at z14.
- **Field facts (learned building the Brackett escape, 2026-08-06):**
  an edge exit into air REQUIRES `sky_room` (int dbref) or the jump
  silently degrades to a plain walk — the full edge-to-air attr set is
  is_edge / edge_difficulty / sky_room / fall_room / fall_distance /
  fall_damage. WALKING into a sky room never triggers falling (no
  gravity-on-entry hook exists; the fall lives in the `jump` flow
  only). A server reload during the fall delay orphans the jumper in
  the sky room. Fire-escape rooms are `type: "fire escape"` — their
  own exit-message list (exits.py) and ambience category
  (ROOM_TYPE_POOLS) exist; new room types join both registries.
- **Edges**: any edge is a valid hook anchor. **No authored anchor
  points** — exploration is encouraged, not fenced; the *building
  design* does the fencing, never the mechanic.
- **The hook (rappel/grapple), when built**: works **both directions**
  — secure a line to an edge or roof (above or below), then ascend or
  descend it. A deployed line **integrates into the room descs** of
  its anchor room, every sky room it threads, and the landing room; it
  is visible infrastructure. A line can be **unhooked — potentially
  while someone is on it.** Gear is **recoverable** (lines are
  valuable, lendable, stealable). Use rolls **Motorics**; failure to
  ascend/descend **burns stamina** (future stat), never causes a fall.
- **Range is the gear**: each make/model of hook has its own max line
  length at its own price point (branded, per the world rule). Length
  IS the progression: a cheap line opens the low roofs, the rim-rated
  line is endgame kit. Tier ladder is an owner-priced decision later;
  templates below only assume that *short is common and long is rare*.

**The verb split this produces** — the load-bearing design fact:

| Verb | Speed | Risk | Gate | Exposure |
|---|---|---|---|---|
| Jump | fast | fall damage (5×height) | Motorics | a moment |
| Hook | slow | stamina only | gear length + Motorics | a visible line others can use or cut |

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
3. **Soft-fail low, hard-fail high.** Learning sections route over
   fall interceptors (terraces/awnings 1–2 stories below the gap,
   capping a botch at ≤10 damage). The climax near the rim earns its
   full street-drop exposure.
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

- Adjacent roofs within **±1 story** are native fabric: walk the
  join, or jump the gap (span-1, an air cell over the street or
  alley, the fall waiting below — the archipelago pattern exactly).
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
2. **The Street Cross** — the first air-cell crossing (built: the
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
escape from pockets that one-way drops create. Its numbers (glide
ratio, launch requirements) are an owner call for when the kit builds;
until then, high builds reserve **launch points** (a parapet with a
wind note) the way roofs reserve anchor edges — seams now, straps
later.

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

- **F1 · The fire escape** — the workhorse on-ramp, and now a BUILT
  exemplar: **the Brackett fire escape** (landings (-8,-18) z3-z6).
  Its as-built laws: windows are **communal** — they open from each
  floor's landing/hall, never from private units (a unit's security
  perimeter includes everything of its own); exit key `window`, no
  aliases; the iron works both ways; the bottom is a **one-way drop**
  (ascent from below waits for the crank/grapple era); it can end on
  a ROOF or HULL rather than the ground, feeding the second city
  directly. Egress always; ingress is the future hidden-exit
  mechanic. Copy the exemplar, not this paragraph.
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

The future analyzer (`export_map` + kernel numbers → reachability
overlay on the atlas) automates step 4's proof and the parked global
edge audit; until then, corridors are proven by hand against this
checklist.
