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
