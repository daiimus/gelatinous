# Jump Command Implementation Specification

`jump` does two things. It lets a hero throw themselves on an explosive to
shield everyone else from the blast, and it moves a body over the edge of a
height: down off an edge, or across a gap to a perch at the same level.
What happens after a body leaves the roof belongs to gravity, which is a
property of the air cell, not of the command. The verb lives in
`commands/combat/jump.py` (`CmdJump`), in the combat cmdset
(`commands/combat/cmdset_combat.py`). Gravity lives in `world/gravity.py`.

## Command syntax

```
jump on <explosive>           # Heroic sacrifice - absorb explosive damage
jump off <direction> edge     # Descent from a height
jump across <direction> edge  # Leap across a gap to a perch at the same level
```

`find_edge_exit` resolves any exit name, not only a compass direction:
`jump off breach edge` works, and is better than forcing a vertical drop
onto a cardinal.

The room lines (the sacrifice, the edge departure, the landing) go through
`msg_room_identity` with `{actor}`/`{victim}` refs, so each watcher sees the
actor by their own perceived identity.

## Jump on: explosive sacrifice

The hero takes the whole blast so that nobody else does.

### What the verb checks, in order

1. Someone holds the caller in a grapple: refused ("You cannot perform
   heroic sacrifices while being grappled by X!"). Being in combat is no
   bar; only the grapple is.
2. The object is looked for anywhere in the room; there is no proximity
   requirement. Not found: "You don't see 'X' here."
3. The object is not `db.is_explosive`: "X is not an explosive device."
4. Another hero has already claimed it: refused ("X is already being
   heroically tackled by Y!").

Nothing is refused for being unarmed, a dud or out of time. Any explosive
is accepted, armed or not; whether it was live is revealed when the outcome
lands. The reason, in `handle_explosive_sacrifice`: false heroics are part
of the drama.

### What happens

1. If the fuse is live (armed and counting down), it is stopped at once
   (`stop_grenade_fuse`).
2. The leap is announced at once: "{actor} makes the ultimate sacrifice,
   leaping onto X!" The explosive is named as the search found it, with
   its article, not as the player typed it: `jump on gren` announces
   "...leaping onto the grenade!" (#3354).
3. The outcome lands after a reveal delay: 2.5 s; or, when the fuse has
   2.5 s or less left, its remaining time minus 0.3 s, but never less than
   0.5 s. A 10 s fuse therefore goes off 2.5 s after the leap: the hero
   shortens the countdown, and does not inherit it.
4. The outcome (`reveal_outcome`):
   - **Live:** the hero takes the damage (or the held victim does; see
     Human shield). The hero takes on ALL of the explosive's proximity
     relationships, the explosive is deleted, and the hero skips their next
     combat round (`NDB_SKIP_ROUND`).
   - **Armed but not counting down:** "...but X makes only a small 'click'
     sound. It was a dud or the timer expired." It costs nothing.
   - **Not armed:** "...but nothing happens. X wasn't even armed." It costs
     nothing.

The dud and unarmed lines are outcomes told to the room, not refusals.

### Damage

```
Hero damage   = explosive.db.blast_damage (10 if unset), to the chest,
                of explosive.db.damage_type (default "blast"); no bonus
Others damage = 0 (complete protection)
Human shield  = the held victim takes 2 x blast_damage; the hero takes 0
```

Everyone else in proximity takes nothing. The explosive is gone, so it
cannot set off other explosives: the hero stops a chain reaction.

**Human shield.** If the hero is holding someone in a grapple in the same
room, the room is told the hero leapt "while still holding" them, and the
held victim takes the blast instead: twice `blast_damage`, to the chest,
while the hero takes none. The hero is told if the blast killed the victim,
and the grapple breaks after the blast (the `release_blast` beat). The 2×
and 0 shares are fixed numbers in `reveal_outcome`
(`handle_explosive_sacrifice`).

### Shared with the grenade system

The sacrifice reads the same properties the throw command uses:
`db.is_explosive`, `db.pin_pulled`, `db.blast_damage`, `db.damage_type`,
and the live countdown `ndb.countdown_remaining` that pulling the pin
starts from `db.fuse_time`. It works on every explosive type (standard
grenades, flashbangs, smoke grenades and so on), since it reads only these
properties.

## The world a jump moves through

### Air cells

- A room is air when its `db.is_sky_room` is a literal `True`
  (`world.gravity.is_sky`). The flag is the truth; the typeclass is not
  consulted. A plain Room flagged in place is a legal air cell, and a
  SkyRoom flipped into a catwalk is legally walkable.
- Sky rooms are permanent world features, not temporary objects. No
  dynamic creation or deletion is needed. This prepares for coordinates and
  for flying vehicles.
- **The column is mandatory.** Each air cell needs a one-way `down` exit
  (key `down` or alias `d`) to the cell beneath it, and the bottom cell's
  `down` must reach something that is not air. "Not air" is the only
  terminator; `db.is_ground` decides nothing about a fall. Nothing else
  places a falling body.
- An apron, awning or terrace that should catch a fall is a ROOM in the
  column (`is_sky_room` False), never an attribute.
- Each air cell also has sideways exits to its neighbours (the cell east of
  a roof has a `west` back to it). Those sideways exits are also what a
  fall announces to.

```
Rooftop (origin) --east--> Air cell (transit) --east--> Adjacent Rooftop (destination)
                                |
                              down          <- one cell per FALL_SECONDS_PER_CELL
                                |
                            Air cell
                                |
                              down
                                |
                         Street (not air)   <- lands here; damage charged for cells passed
```

### Edge and gap exits

Edge exits represent rooftops, ledges and balconies.

An edge exit's own `destination` is the air cell (or, for a direct drop,
the room below). The column below that cell is the distance of the fall.

| attribute | on | meaning |
|---|---|---|
| `db.is_edge = True` | exit | an edge you can `jump off` |
| `db.edge_difficulty` | edge | base of the landing roll; omit for `FALL_EDGE_DIFFICULTY_DEFAULT` (8) |
| `db.edge_type` | edge | descriptive only; no runtime reader |
| `db.is_gap = True` | exit | a gap you can `jump across`; can combine with `is_edge` |
| `db.gap_difficulty` | gap | the takeoff roll; omit for `GAP_DIFFICULTY_DEFAULT` (10) |
| `db.gap_destination` | gap | REQUIRED: the id of the far perch a made leap lands on |
| `db.gap_width` | gap | descriptive world data, authored on live gaps; no runtime reader |
| `db.stays_aloft = True` | anything | the one predicate gravity asks (strict `is True`): it does not fall, and sits in the cell watching others fall past. The seam for flight and vehicles |

Example of the shape an author follows:

```python
gap_exit.db.is_gap = True
gap_exit.db.gap_difficulty = 10          # omit for GAP_DIFFICULTY_DEFAULT (10)
gap_exit.db.gap_destination = far_roof.id
gap_exit.db.gap_width = "medium"         # descriptive only
```

**Inert attributes.** These have no reader anywhere, the map exporter
included. A builder who meets one on a live exit or room should know it
does nothing: `exit.db.sky_room`, `exit.db.fall_distance`,
`exit.db.fall_damage`, `exit.db.fall_room`, `exit.db.gap_distance`
(superseded by `gap_width`), `sky_room.db.origin_room`,
`sky_room.db.destination_room`, the `sky_room` tag (category `room_type`),
`db.is_fall_room` and the `fall_room_{id}` tag. There is no lookup of sky
rooms or fall rooms of any kind. `world/mapping.py` copies only
`edge_difficulty`, `gap_difficulty` and `gap_destination` onto an edge or
gap link.

**Strict and loose readers.** The movement gates require a literal `True`
on `is_edge` and `is_gap`: `can_leave_by`, the jump verbs' edge and gap
checks (`exit_obj.db.is_edge is not True`) and `Exit.at_traverse`'s edge
and gap block. A truthy-but-not-`True` attribute left by an old build
script therefore cannot be an edge in one gate and a plain exit in another.
Three readers are not strict: the gap landing's search for the return edge
(`finalize_successful_gap_jump`, a truthy `is_edge`), the exit's look
descriptions in `typeclasses/exits.py`, and `Exit.at_traverse`'s sky-room
block, which reads `is_sky_room` truthily where `world.gravity.is_sky`
wants a literal `True`.

### Wiring contract for builders

- **Transit edge:** exit `destination` = the air cell; `db.is_edge = True`;
  `db.edge_difficulty` optional. The column below is the rest of the flight
  plan, and it is mandatory (see Air cells). A column that runs out mid-air
  is the parked impasse (#3581): the fall stops cleanly in that cell, with
  no damage and no strand.
- **Direct edge** (no open column below, for example clearing an
  oversailing plate): the destination is simply not an air cell. One storey
  of `FALL_DAMAGE_PER_STORY`, always lands, no roll, no traversal.
- **Gaps:** `is_gap` requires `gap_destination` (the far surface at the
  same level). Omit `is_gap` when nothing faces the edge.
- **Named edges:** any exit name works (see Command syntax).
- **Air fill tooling:** `fill_air_cell` links only walkable OUTDOOR
  neighbours; interiors are never linked. It stamps a roof's way into air as
  `is_edge` only, and adds `is_gap` + `gap_destination` only when another
  walkable surface stands exactly one cell across; it never generates a gap
  with no perch (#3415, #3582). Always run the edge audit after an air
  build: `@airfill/audit <z>`, read-only, reports surfaces beside air with
  no edge, gaps whose perch is missing or not one cell across, and bare
  cells. The 69 cells generated before this rule still carry `is_gap`
  without a perch; the owner chose not to run a re-stamp pass, so those
  exits stay refused at the roof until one is run.

### Seeing edges, and walking into air

- Edges and gaps are named in the room's exit prose: "There is an edge to
  the north." / "There are edges to the ..." / "There is a gap to the
  east." An exit that is both an edge and a gap is listed as an edge.
- An exit whose destination is air is hidden from the exit prose unless it
  is itself an edge or a gap (`get_custom_exit_display`). Players cannot
  see a pure transit cell. Inside an air cell no exits are listed at all.
- Walking into, out of or between air cells is refused, with no exception,
  by the sky block in `Exit.at_traverse` (`typeclasses/exits.py`). This
  stops anyone walking around the gap jump. Jumps and falls relocate with
  `move_to`, which never reaches `at_traverse`, so the block does not touch
  them. An edge or gap exit that leads into air is visible, but walking it
  is refused by the edge and gap restrictions in `Exit.at_traverse`; there
  is no separate "blocked edge" refusal in the jump verbs. The sky
  block's refusals:
  - Entering: "You cannot enter sky rooms through normal movement! Use jump
    commands to access aerial transit."
  - Leaving: "You cannot leave sky rooms through normal movement! You are
    falling - wait for gravity to take effect."
  - Between: "You cannot traverse between sky rooms! Sky rooms are
    transit-only spaces."

### The crane (#3560)

Owner ruling (#3560, 2026-09-21): "the exit should always exist as an edge
working for jump off and only sometimes work for jump across."

- `CraneContainer` keeps four permanent doors, and `move_to_level` points
  each at what lies beyond it.
- The car's `west` is the walk-off at the dock, and SHUT aloft (no room
  west of the column).
- The car's `north` is the leap toward the Queen's roof aloft, and shut at
  the dock (the rack's wall). It opens onto the shaft air at the car's
  level (#3643), so a made leap carries on to the Queen's roof, and a miss
  or a jump off falls down the cable into the dig.
- A shut door carries `view:false();search:false();traverse:false()` and an
  authored `err_traverse`: it leaves the exit prose, `jump` finds no exit
  that way, and the walk is refused in words. A shut door points at the
  shaft air behind it, so `advance` and `charge` refuse it too.
- The Urgent Care roof's `east` is the walk onto the docked car. Otherwise
  it is an edge into the shaft's dock-level cell, with a jump across onto
  the car at the distance difficulty.
- The Queen's roof `south` is the hop onto the level car. Otherwise it is
  an edge into the shaft cell at the roof's height; a jump across onto the
  car when aloft; and refused ("doesn't lead anywhere safe to land",
  #3559) while the car is docked.
- Only the leap scales with distance. Every crane edge's landing roll is
  the fixed `DESCENT_DIFFICULTY` 8.
- The shaft is wired `down` from z16 to z1, to the Foundation.

## Jump off: edge descent

Stepping off an edge always succeeds; the LANDING is what is rolled for.
The verb's job ends at the air cell (`handle_edge_descent`).

1. Someone holds the jumper in a grapple: "You cannot jump while being
   grappled by X!"
2. The exit is found (`find_edge_exit`): "There is no exit to the X." /
   "The X exit doesn't lead anywhere."
3. It is not an edge (`is_edge` not literally `True`): "The X exit is not
   an edge you can jump from." It has no destination: "The X edge doesn't
   lead anywhere safe to land."
4. The jumper's own gates, at no cost (`refused_at_the_threshold`; see
   Fights at the edge): a channel, or an escortee who cannot be walked over
   the edge.
5. In a fight, leaving pays flee's price (`pay_the_price_of_leaving`; see
   Fights at the edge).
6. The verb branches on whether the destination is air
   (`world.gravity.is_sky`):
   - **Not air: a direct drop.** One `move_to`, one storey of
     `FALL_DAMAGE_PER_STORY`, no roll, no traversal, done. With a grappled
     victim, the made bodyshield split is applied to that one storey.
   - **Air.** The verb writes the flight plan onto `ndb.fall_intent`
     (`edge_difficulty`, `roll=True`), moves the jumper into the cell,
     attaches a dragged companion to the leader's fall record, drops combat
     and aim state, announces the departure to the room left ("{actor}
     leaps off the X edge!"), and stops. The cell's `at_object_receive`
     hook starts the fall (see Gravity).

Nothing below an edge refuses the step: an edge into air is always legal,
because the air cell is the destination and the column below is the fall.
The failure mode is mid-fall (the impasse, below), not at the roof.

A jumper holding someone in a grapple drags them over the edge (see
Bodyshield under Gravity). Only an edge descent drags a held victim.

## Jump across: gap jump

`handle_gap_jump`. A gap exit's destination is the air cell; the far perch
is `gap_destination`.

1. Someone holds the jumper in a grapple: "You cannot jump while being
   grappled by X!"
2. The exit is found (`find_edge_exit`): "There is no exit to the X." There
   is no gap-specific not-found message.
3. It is not a gap: "The X exit is not a gap you can jump across."
4. The far perch must resolve: `gap_destination` (or the exit's own
   destination when that is not air) must be a real room that is not air
   (`gap_destination` in `world/gravity.py`). Otherwise the jump is refused
   ON THE ROOF: "The X gap doesn't lead anywhere safe to land." (#3559). It
   is never silently swapped for the air cell.
5. The jumper's own gates, at no cost (`refused_at_the_threshold`): a
   channel, or an escortee who cannot be walked to the gap. A jumper
   refused here never rolls, so never slips in place.
6. In a fight, leaving pays flee's price (see Fights at the edge). After
   the price, a march of the held victim ends (#3684), so a jumper the
   price cuts down keeps it.
7. The takeoff roll, the only roll a gap makes: Motorics (`standard_roll`)
   vs `gap_difficulty`, default `GAP_DIFFICULTY_DEFAULT` (10). Success on a
   success or a tie.
8. **Made.** A one-tick `ndb.airborne_token` is set, the jumper moves into
   the air cell, and lands on `gap_destination` one `FALL_SECONDS_PER_CELL`
   later. The leaper is genuinely in the air for a tick and is seen there.
   `finalize_successful_gap_jump` then checks the landing edge for rigged
   grenades (below). A made leap costs no round.
9. **Missed.** The jumper enters the cell with no token, and gravity takes
   over: the body falls down whatever column is under the gap. A failed
   leap never rolls to land, so none of the damage is absorbed. Damage is
   `FALL_DAMAGE_PER_STORY` (5) × cells actually passed, charged once at the
   bottom. A miss costs the next round, on landing.

**A gap with no air between the surfaces** (its exit leads straight to a
room that is not air): a made leap moves the jumper to the perch at once. A
miss does not fall: the jumper slips in place on the roof, takes one storey
of `FALL_DAMAGE_PER_STORY`, and loses the next round at once
(`handle_fall_failure`).

**A held victim never goes along.** A gap jumper holding someone in a
grapple lets go. The hold breaks only once the leap is real (after the
jumper's move has happened, or on a slip in place; a refused move keeps
it), the victim stays on the roof, and the `release_jump` beat is spoken
there (`let_go_for_the_leap`, #3684).

### Rigged grenades on the landing edge

A made gap jump checks the edge it lands beside for a rigged grenade
(`finalize_successful_gap_jump`):

1. It finds the return edge: an exit in the landing room whose key or any
   alias matches the opposite of the direction jumped, using
   `DIRECTION_OPPOSITES` (`world/gravity.py`, the same table the fall
   announcements use). Jump north, look for south. An exit keyed "south"
   with alias "s" matches when looking for "s". The exit must carry
   `is_edge` (read truthily).
2. It calls the existing `check_rigged_grenade` (`commands/explosion_utils.py`)
   on that edge. There are no new mechanics: rigging is CmdThrow's. A rigger
   cannot trigger their own trap. A triggered grenade runs the full
   explosion sequence (pin pull, countdown, proximity, damage, cleanup) and
   is cleaned up off the edge.

Rigged grenades therefore give area denial over a gap's landing zone:

```
Player A: rig grenade to s     # Rig the south edge
Player B: jump across n edge   # Jump from opposite direction (north to south)
# Player B lands on south edge and triggers Player A's rigged grenade
```

**Logging.** The gap landing logs `JUMP_GAP_SUCCESS` to splattercast, and
`JUMP_GAP_DEBUG` when no origin room is known. `check_rigged_grenade` logs
nothing when there is no rigged grenade or the jumper is its rigger, and
nothing logs the direction match.

## Gravity: how a fall runs

Gravity is a property of the ROOM. `Room.at_object_receive`
(`typeclasses/rooms.py`) calls `world.gravity.on_enter_air` for EVERY
arrival. Anything in an air cell that cannot stay up starts falling, by any
door: a jump, a throw, a drop, a shove, a reconnect, a build script.
Characters and Items fall; exits do not. The jump verb only supplies the
flight plan (`ndb.fall_intent`, or `ndb.airborne_token` for a made leap).
Since walking into air is refused, "a walk into air falls" means a shove, a
drop or a rebuilt column, not a player typing a direction.

Owner ruling (#3579, 2026-09-16): "it would always follow gravity straight
down. Essentially it's checking if it's a skyroom and if it is proceeding
down."

### The traversal

- A fall is a persistent `db.falling` record, `{cells, origin,
  edge_difficulty, roll, companion, next_step_at}` (the grenade-fuse shape,
  #505).
- Each tick, `world/gravity.py` re-resolves the cell's `down` exit (by key
  or by alias `d`, so a column the crane rebuilds still works) and makes a
  real move into the next cell, one cell per `FALL_SECONDS_PER_CELL`
  (1.0 s). The body lands when the next room is not air. There is no
  authored landing.
- **The impasse (#3581).** When a cell has no `down`, or its `down` no
  longer resolves, the fall stops cleanly in that cell, with no damage, no
  crash and no strand (`_strand`). The faller reads: "You come to a stop in
  open air. There is nothing beneath you here — no ledge, no street, only
  more sky that nobody has finished. Gravity is patient." The room sees
  "{actor} hangs in the open air, with nothing beneath." The code's answer
  is deliberate and correct; the missing column below the colony's highest
  crossings is world data (#2945), not a bug in this command.
- When `FALL_MAX_CELLS` (30) is reached, or a step is refused or fails, the
  fall also stops with no damage. The faller reads "Something arrests your
  fall, and you hang in the open air." and the room "{actor} hangs in the
  open air."
- **Across a reload.** `sweep_airborne` (`world/gravity.py`) runs from
  `at_server_start` (`server/conf/at_server_startstop.py`). It resumes
  every recorded fall at its TRUE remaining time, defers a step that came
  due during the outage by 2 s so the world is loaded first, and starts a
  fall for any body or item found in an air cell with no fall record that
  cannot stay up and has a `down` exit to fall through. A body parked at a
  bare cell (#3581) is left where it is. A logged-out faller keeps its
  record and is resumed by the reconnect path.

The cadence is 1.0 s per cell. Owner (2026-09-16), on 0.5 s per storey:
"is faster than any beat in the game".

### The landing roll

It fires on edge descents only (`roll=True` in the `db.falling` record).
Motorics vs `edge_difficulty` (default `FALL_EDGE_DIFFICULTY_DEFAULT` = 8)
+ `FALL_LANDING_DIFFICULTY_PER_CELL` (2) × cells fallen.

A **make absorbs `FALL_LANDING_ABSORBED_CELLS` (2) cells** rather than
dividing the damage. Owner's shape: skill turns a fall into a shorter fall,
so a two-storey drop landed well is free and a twelve-storey one is not
survivable by skill alone. A one- or two-storey descent landed well is
free; anything taller is not. A miss pays `FALL_DAMAGE_PER_STORY` (5) ×
every cell passed.

A **failed leap never rolls**, and neither does an **item**: things take no
damage at all; they arrive and are heard arriving. A thing whose fall ends,
landed or stopped in the air, loses any hiding place it had
(`_forget_stash`, #3773): it lies in plain sight where it was heard to stop.

### Damage and where it lands

Owner ruling (#3579, 2026-09-16): "we'll have cyberlegs... parachutes, flight... but
calculating potential damage based on geometry will always be relevant."
Geometry is the base: the column is the distance and
`FALL_DAMAGE_PER_STORY` is the damage. This is what the owner-ruled
movement kernel (`specs/PARKOUR_TEMPLATE_LIBRARY.md` §0) prescribes for
falls.

Damage is `FALL_DAMAGE_PER_STORY` (5) × effective cells, `blunt`, charged
once at the bottom. It is **filled from the feet up**. Owner: damage lands
"legs -> limbs -> other randomly":

1. **Legs first.** A leg is *every destroyable organ that feeds the
   `moving` capacity*, read off the live organ, so a chrome leg counts and
   a rat fills its hind paws first. Ordered by the species' anatomical
   display order, reversed: feet, then shins, then thighs.
2. **Then the other severable limbs**, excluding the head.
3. **Then random surviving containers** the first two tiers did not cover.

Each organ is exhausted before the next. Armour on a container softens the
chunk that container receives, and the fill **moves on** (a partial fill
under armour is the honest reading, not a re-roll). The fill **stops the
instant a chunk kills**. The result is the owner's target shape: a long
fall is more survivable than a lethal hit to the chest, and leaves the body
wrecked from the ground up.

### Bodyshield

An edge descent taken while grappling drags the victim. A made landing
charges the victim `FALL_BODYSHIELD_MADE_VICTIM` (0.75) and the grappler
`FALL_BODYSHIELD_MADE_GRAPPLER` (0.25) of the fall; a failed one charges
`FALL_BODYSHIELD_FAILED_VICTIM` (1.5) and `FALL_BODYSHIELD_FAILED_GRAPPLER`
(0.5). Both survivors have their grapple rebuilt in a fresh handler at the
landing room, the grappler yielding. A direct drop applies the made split
to its one storey.

### Fall announcements: the three audiences

Owner ruling (#3579, 2026-09-16): "if I'm flying in a room or in a flying
vehicle in one of the sky rooms, I'd see someone fall past me."

A fall is narrated per CELL. Every step announces to three audiences plus
the faller, through `msg_room_identity`, so each watcher sees the faller by
their own perceived identity (an item renders through its own
`get_display_name`):

1. **The cell left:** "{actor} drops away beneath you." (an item: "tumbles
   away beneath you.")
2. **The cell entered**, when it is still air: "{actor} falls past you,
   still dropping." (an item: "tumbles past you.") Anyone who can stay up
   in that cell sees the body go by.
3. **Every walkable surface beside the cell entered:** "{actor} falls past
   the edge to the <direction>." The list is data-driven, not authored:
   `neighbour_surfaces` reads the cell's own non-`down` exits whose
   destination is not air, and the direction is REVERSED with
   `DIRECTION_OPPOSITES`. A body in the cell east of a roof is seen from
   that roof falling past to the east, even though the cell's exit to the
   roof is keyed "west".
4. **The faller** gets a line of their own ("You plummet downward through
   open air."), and a dragged companion gets theirs ("You are dragged down
   through open air."), **on top of** each cell's full description. Every
   step is a real move, so Evennia's arrival look fires in every air cell:
   the faller reads the cell's prose, its weather and whoever is hovering
   in it on the way past. This is by design: owner ruling on #3585
   (2026-09-16), "I don't think that's a bug."

The landing narrates once more, to the landing room and the faller:
"{actor} lands with athletic grace from above!" or "{actor} crashes down
from above with a bone-jarring impact!" (`_land`). A fall that runs out of
column stops with the impasse message instead.

## Fights at the edge (#3583, 2026-09-16)

Two owner rulings: one about who may cross an edge, and one about what it
costs to cross it while someone is fighting you.

### 1. Refused at the edge

`flee`, `advance` and `charge` never take an edge exit, a gap exit, or an
exit into an air cell. One predicate answers for all three:
`can_leave_by(mover, exit)` in `world/gravity.py`. It fails any exit
carrying `db.is_edge` or `db.is_gap`, or whose destination is air, unless
the mover's `db.stays_aloft is True`. It lives in the gravity module
because it is the same question gravity asks everywhere else. It is asked
at the command rather than at the exit because combat movement relocates
with `move_to` and never reaches `Exit.at_traverse`.

- `advance` and `charge` keep the rejected exit so they can name it: "The
  only way to X is over the N edge -- that is a jump, not an advance."
  (`charge` ends "not a charge.")
- `advance` asks this before it rolls the grapple drag-resist contest, so a
  grappler who cannot go that way never drags their victim into a doomed
  roll.
- NPC souls ask it too: `world/souls/jobs.py`'s flee job reports "cornered
  — nowhere to flee".
- `retreat` only makes distance in the same room.

So no melee approach reaches a roof whose only links are such exits: a
ground-level opponent cannot advance up onto it, because the only exit
between the two rooms is a thing you jump off. The same predicate limits
the retreat: on a roof with nothing but edges, the escape route is the
jump, and the jump has a price.

> Owner: *"It would be refused at the edge… Ideally, very few rooftops
> will exist without exits though — so ending up on one where all you can
> do is jump is a tactical challenge."*

A rooftop whose only ways out are edges is a **designed predicament**, not
a dead end: you cannot be chased onto it, you cannot back off it, and
leaving is a deliberate act with a price. The building doctrine that keeps
such rooms rare is `specs/PARKOUR_TEMPLATE_LIBRARY.md` §1.5.

### The jumper's own gates come first (#3685)

Owner, 2026-09-29, on #3685: "That makes sense."

`refused_at_the_threshold` runs, before any price, the two gates
`Character.at_pre_move` would refuse the move on: a channel
(`refuse_if_channeling`, which speaks its own line) and an escortee the
usher would walk at an edge, a gap or a way into air (the real
`usher_escortee`, which refuses and speaks). A jump that cannot happen
costs nothing: no aim contest, no disengage roll, no free shot at a body
that never leaves the roof.

- A walk through a plain door beside the drop can still be refused inside
  the move for a reason nothing predicts (a lock); that one is still paid
  for.
- A channeling or escort-barred gap jumper never rolls, so never slips in
  place.
- A hidden jumper stopped at the threshold by a barred escort keeps their
  concealment, as a channeling one does, since no move was tried.

### 2. Jumping away in a fight pays flee's price, both halves

`pay_the_price_of_leaving` (`commands/combat/jump.py`) charges what fleeing
charges, through the same code, so the two verbs cannot drift apart. The
reason: a jump that only left the combat handler, with no contest and no
opportunity attack, was strictly the best escape in the game, since `flee`
rolls for it and can be punished. Both `jump off` and `jump across` pay it.

- **The aim contest** (#3583): `break_aim_lock(caller, *, bonus=0,
  label=None)`, Motorics vs Motorics, two `standard_roll`s, the jumper's
  roll plus the bold-move bonus. A won roll frees the jumper; a lost roll
  hands the aimer their opportunity attack.
- **The melee disengage roll** (#3591): flee's Part 2, shared as
  `roll_to_disengage(caller, handler, *, bonus=0, label=None)` in
  `commands/combat/movement.py`. Motorics against the best-Motorics
  opponent targeting the jumper, ties to the blocker, the bonus again on
  the jumper's roll. A lost roll hands the blocker their opportunity
  attack: "X catches you as you break for the edge!" Without it, in a
  melee brawl with nobody aiming, a jump would cost nothing, and since flee
  is refused at the edge, a melee opponent on an edges-only roof would have
  no way to punish the departure.
- **The shot lands before the jumper leaves** (#3593). Both losses run the
  shared `opportunity_attack(attacker, target, *, immediate=False)`, which
  issues a real `attack` against the RESOLVED target (#1002). For a jump it
  runs with `immediate=True`, which finishes the shot through
  `world.combat.utils.resolve_bonus_attack(handler, attacker, target)`: the
  same helper that hands a ranged defender an immediate attack when an
  advance or a charge at them fails. It does the combat-entry lookup and
  the `process_attack` itself, with its own guards (a dead or unconscious
  target, melee reach, proximity). One immediate-attack implementation,
  three doors: a failed advance, a failed charge, and a jumper who lost a
  leaving contest. `break_aim_lock` forwards the flag as
  `immediate_attack`, and the jump verbs pass True on both halves. The
  reason: `CmdAttack.func` only ENROLS (it puts the attacker in the handler
  with the target and prints the weapon's initiate line) and the shot fires
  on the handler's next round. That is enough for a blocked fleer, who is
  still standing there; a jumper is out of the handler and off the roof
  inside the same command. Flee is unchanged.
- The jump passes `label="JUMP_AWAY"` to both rolls, so the splattercast
  lines read `JUMP_AWAY_` rather than `FLEE_`.
- **The jump goes regardless:** "You throw yourself at the edge
  regardless." Only an opportunity attack that leaves the jumper dead or
  unconscious stops it. Paying the price never refuses the jump and never
  costs a round.
- Each roll happens only if there is someone to roll against: no aimer, no
  aim contest; no combat handler or nobody targeting the jumper, no
  disengage roll. Jumping out of an empty room costs nothing, and the
  "regardless" line prints only when something was actually paid.

> Owner: *"I agree with 2, however, the difficulty should be half or
> there should be a bonus. It's a bold move."*

`JUMP_AWAY_BONUS` is 20, `#: BALANCE:`-tagged, with a row in
`specs/roadmaps/BALANCE_LEDGER.md` under "Fights at the edge (#3583)",
**Tuned? No**. It is charged twice per departure, once on each roll, which
is the first thing the balance pass should look at.

The two verbs differ only in the consequence of a loss, which is the point
of the ruling:

| | lost aim contest | lost disengage roll |
|---|---|---|
| `flee` | aimer's opportunity attack (next round), and the flee ends there | **blocked**, and `NDB_SKIP_ROUND` |
| `jump off` / `jump across` | aimer's opportunity attack (**immediate**), jump continues | blocker's opportunity attack (**immediate**), **jump continues** |

Both leaving contests come first, at the point of leaving. `jump across`
then rolls its takeoff, Motorics vs `gap_difficulty`, which is a separate
roll.

### Rounds

- **Jump on explosive:** the leap is announced at once and the outcome
  lands about 2.5 s later; a live sacrifice costs the hero their next
  round; a dud or unarmed explosive costs nothing; refused while grappled.
- **Jump off / jump across:** leaving pays flee's price, which never costs
  a round. A missed gap leap costs the next round; a made one does not.
- `aim` grants no accuracy at all (owner ruling #3355, see
  `COMBAT_SYSTEM.md`), and no code reads elevation in the to-hit roll.

## Aiming over an edge (#3589)

> Owner, 2026-09-16: *"Aiming at an edge typically means aiming at the ground area it
> drops to because of sniping. Rooftop to street for example."* And:
> *"We also have the coordinate system which can be applicable."*

An edge exit leads into an air cell, and nobody stands in the air. Three
predicates in `world/gravity.py` make a shot or a look through an edge
reach the ground:

- **`is_surface(room)`**: a rooftop (`db.type == "rooftop"`) or any outdoor
  room (`db.outside is True`) that is not itself air: somewhere a body can
  stand beside the sky. The builder's air fill imports it from gravity, so
  "what counts as a surface?" has exactly one answer for the builder and
  for the shooter.
- **`ground_below(cell)`**: what is under `cell`, by geometry, without
  moving anyone: **the highest non-air room in the same column below it**.
  No cell limit and no floor at z=0; a column over the Drifts resolves
  downward past zero. On the grid the answer comes from `world/spatial`'s
  `coordinate_index()`; with nothing seeded below, or off the grid
  entirely, it falls back to the `down` chain the fall itself walks. It
  answers `None` in two cases: nothing solid below at all, and, **the
  occlusion rule**, a room straight below that is not a surface. An
  interior under an air cell means an unbuilt roof is in the way, so there
  is nothing to hit: you are looking at the top of a building whose roof
  nobody has made yet, not through it.
- **`room_through(exit_obj)`**: the room a shot, a look or a throw through
  this exit is really aimed at. A **gap** resolves to its far perch
  (`gap_destination`); an **edge, or any exit into air**, resolves to
  `ground_below(destination)`; anything else is just its destination. A
  **gap with no perch is aimed like an edge**: the leap refuses it (#3559)
  and the shot drops to whatever is under it.

Geometry first is the point of the ruling's second half. The grid answers
what is under a parapet whether or not anyone wired a column of `down`
exits; the exits are the fallback, not the source of truth.

| Where | Behaviour |
|---|---|
| Directional attack (`commands/combat/core_actions.py`) | Fires into `room_through(exit)`. `None` refuses the shot: "You are aiming `<dir>`, but there's nothing down there to hit." |
| Aiming look (`typeclasses/rooms.py` `return_appearance`) | Renders the ground below rather than the air cell, and composes that room's own layers (graffiti, weather, `@integrate` content). |
| Aimed `look <target>` (`commands/CmdLook.py`, through `Room.aimed_room_for`) | Finds a person (by description) or a thing in the room the aim really reaches, before searching the looker's own reach. |
| Throw, the **`at`** form (`CmdThrow.find_target`) | Resolves the aimed room through `room_through(find_throw_exit(aim))`, so `throw grenade at thug` finds the thug on the street below and the object flies to the **target's** room. |

Both look paths fall back to the air cell when `room_through` answers
`None`, so a bare column still renders something rather than erroring;
only the attack refuses.

**Reconnaissance is through an aim only.** Over an edge, the aim shows the
ground below; over a gap, the far perch; with nothing open below (such as
an interior), the air cell itself. There is no `look <direction>` verb:
the aimed view is rendered by `Room.return_appearance` off
`ndb.aiming_direction`, which only `aim` sets, so you aim first and look
second. `aim` takes a DIRECTION (`aim north`) or a target, not a room name.
The reach is one exit, as it is everywhere else.

**Throw is split, deliberately.** The `at` form reaches through the edge;
the **directional** forms (`throw grenade east`) still fly into the exit's
own destination, the air cell, and gravity carries the object down the
column from there (#3579). Target reach and flight room are two different
questions: a grenade thrown at someone below should land where they are,
and a grenade thrown over a parapet at nothing in particular should fall.

**Deliberately not repointed**, recorded so the next reader does not file
them as misses:

- **Flee's pre-check.** Edges are not flee options at all (#3583), so there
  is nothing for it to resolve.
- **Adjacent sightings.** Look prose about neighbouring rooms, not the
  ruling.

**The aim reaches downward only.** Street → roof is 📋 UNBUILT (#1511),
with Phase 3: there is no exit to aim up through and no line-of-sight
concept to stand in for one.

**Two exposures the adversarial review named; owner rulings 2026-09-16:**

- **The aimed room widens no search (#3596, #3761).**
  `Character.get_search_candidates` adds nothing from the aimed room. The
  commands that reach the aimed room name it themselves: the aim view
  (`Room.return_appearance`), `look <target>` (`commands/CmdLook.py`, which
  tries a person by description, then a thing, in the aimed room before the
  looker's own reach), `attack` and `throw ... at`. `put`, `scan`,
  `diagnose`, `tune`, `remember`, `to`, `whisper` and targeted emotes reach
  only the room the character stands in. This follows the owner's rulings
  of 2026-10-24 on the audit recorded on #3596. When the widening was first
  found, owner 2026-09-16: *"Document this as an issue. We'll need to
  address this somehow."*
- **The target answers without the shooter's constraints, BY DESIGN.**
  The attack command enrols the victim with the shooter as their target
  (`commands/combat/core_actions.py`, `add_combatant(target,
  target=caller)`), so from the next round the street target's own attack
  resolves against the roof: with a ranged weapon it fires, needing neither
  an aim nor an exit. Owner: *"This is by design. Automagic self-defense
  and the perk of carrying a gun."* With a melee weapon nothing lands:
  `process_attack` refuses a melee attack across rooms every round (*"You
  can't reach … from here."*), `advance` finds no exit to the roof (*"You
  cannot find a way to …"*) and `charge` likewise (*"There is no clear path
  to charge at …"*). The unbuilt upward aim constrains who can *open*; the
  gun decides who can *answer*. `flee` still works for the target: no
  aim-break contest (a directional aim marks nobody), no ranged-exit
  pre-check (no street exit leads to the roof), but the disengage roll is
  against every opponent targeting them wherever they stand, the rooftop
  shooter included: **suppressive fire, by design** (owner 2026-09-16:
  *"It would be suppressive fire pinning someone down"*; the pin is the
  constant attacking, not the ammunition; see `COMBAT_SYSTEM.md`,
  `roll_to_disengage`).

**The one place a shot and a fall disagree, by design.** Geometry wins
over wiring: a bare column (#3581) still resolves the shot to the seeded
street below, while the fall down that same column parks in the first cell
with no `down`. You can shoot someone in a street you cannot fall to. That
holds until the airspace is built (#2945): the geometry is right ahead of
the world data, not two answers to one question.

## Tactical scenarios

```
# Heroic sacrifice: live grenade in room, several people in proximity
jump on grenade
# Hero takes all blast damage, everyone else unharmed.
# A hero holding someone in a grapple uses them as the shield: they take
# double, the hero none, and the hold breaks.

# Sniper positioning: on a rooftop with an edge exit to the north
aim north        # aim through the edge
look             # shows the ground the edge drops to
attack bob       # fires into that ground
jump off north edge   # descent when the position is compromised

# Gap crossing: rooftop to rooftop
aim north        # then `look` shows the far perch
jump across north
# On success: repositioned on the far roof.
# On failure: fall down the column under the gap, or slip in place.

# Coordinated tactics
Player A: aim <direction>, attack target (from rooftop)
Player B: advance target (ground level)
Player A: jump off edge (when needed for repositioning)
```

## Numbers

| constant | value | sets |
|---|---|---|
| `FALL_DAMAGE_PER_STORY` | 5 | damage per cell passed; one storey for a direct drop or a slip in place |
| `FALL_EDGE_DIFFICULTY_DEFAULT` | 8 | landing-roll base when an edge sets no `edge_difficulty` |
| `FALL_LANDING_DIFFICULTY_PER_CELL` | 2 | added to the landing roll per cell fallen |
| `FALL_LANDING_ABSORBED_CELLS` | 2 | cells a made landing absorbs |
| `FALL_SECONDS_PER_CELL` | 1.0 | one fall step; also the length of a made leap's tick |
| `FALL_MAX_CELLS` | 30 | a fall stops, undamaged, after this many cells |
| `GAP_DIFFICULTY_DEFAULT` | 10 | takeoff roll when a gap sets no `gap_difficulty` |
| `FALL_BODYSHIELD_MADE_VICTIM` / `_GRAPPLER` | 0.75 / 0.25 | shares of the fall on a made landing |
| `FALL_BODYSHIELD_FAILED_VICTIM` / `_GRAPPLER` | 1.5 / 0.5 | shares of the fall on a failed landing |
| `JUMP_AWAY_BONUS` | 20 | added to the jumper's roll in each leaving contest |
| `CraneContainer.DESCENT_DIFFICULTY` | 8 | every crane edge's landing roll |
| sacrifice reveal delay | 2.5 s | or the fuse's remaining time minus 0.3 s (at least 0.5 s) when 2.5 s or less is left |
| sacrifice default damage | 10 | when the explosive sets no `blast_damage` |

All eleven gravity constants (the `FALL_*` ones, `GAP_DIFFICULTY_DEFAULT`)
are registered in `specs/roadmaps/BALANCE_LEDGER.md`, all **Tuned? No**.

## Design rationale

**Why explosive sacrifice.** It creates dramatic timing pressure; the
player must recognise and react to an explosive threat; it uses the
existing grenade timer system; and the limited window makes the action
more meaningful.

**Why one-way edge descent.** Jumping down only (climbing back up would
need different mechanics). It creates interesting positional asymmetry,
avoids complex climbing systems, is more dramatic than climbing up, and
prevents easy position abuse.

**Why gap jumps can fail.** Character abilities matter; rapid
repositioning is a risk/reward decision; success is not guaranteed; it
keeps gap jumping from being too powerful.

**Why complete damage absorption.** It makes the sacrifice truly
meaningful; the outcome is binary (hero hurt, others safe); it removes the
explosive threat completely; it encourages heroic character moments.

## Addendum (2026-09-16): the gravity layer's known limits (#3579)

Recorded, not filed as defects. Each is a thing the layer knowingly does
not do; a reader who meets one in play should recognise it rather than
re-discover it as a bug.

- **A reload during a leap's one tick drops the leaper.** The stay-up token
  a made `jump across` carries is `ndb.airborne_token`, deliberately
  transient, so a far perch that is itself air cannot re-grant it forever.
  A reload inside that single `FALL_SECONDS_PER_CELL` window finds a body
  in an air cell with no token and no record, and `sweep_airborne`
  correctly starts a fall for it. Falls survive a reload; a leap in flight
  does not. The window is one second wide.
- **Pulped legs do not stop anyone walking.** The damage placement fills
  the legs first by design (owner: "more likely to survive a long fall but
  leaving them crippled"), but the `moving` capacity's only consumer today
  is dodge. The crippling is real in the medical readout and invisible in
  movement. Wiring it up is a separate issue (the movement-policing
  substrate, `specs/roadmaps/MEDICAL_SUBSTRATE_READINESS.md` Phase 7) if it
  is wanted; nothing in #3579 depends on it.
- **Fall damage is untuned, and its knock-on is untuned twice over.** Every
  chunk that lands adds pain and, at ≥10 to a container, a bleeding
  condition, and bleeding has never been through a balance pass. So the
  real lethality of a fall is the damage number plus an unknown. Do not
  size a new consumer against the gravity constants.
- **A fall never severs.** It lands as `blunt` damage, so no limb comes off
  however far the body drops. Deliberate (a fall crushes, it does not
  cut), but a lethal fall produces an intact corpse.

## Intentions a ruling replaced

- **Fall rooms and sky-room lookups.** This spec once intended a fall to
  land in an authored place: four sky-room lookup strategies (tagged rooms,
  `origin_room`/`destination_room` properties, bidirectional rooms, a
  direct-move fallback), four fall-room strategies (`exit.db.fall_room`, a
  `fall_room_{id}` tag, `db.is_fall_room` crash sites, a soft landing at
  the intended destination), and a missed gap falling to a `failure_room`
  for rooms fallen × a multiplier. Ruled instead (#3579, 2026-09-16):
  gravity only, quoted under Gravity; `fall_room` retired with #3580. The
  intent of distance-based damage stands; the mechanism does not. The
  tag and crash-site strategies cannot be built without reopening that
  ruling.
- **Safe landing.** This spec once intended a tactical descent to take no
  fall damage. Since #3579 the landing is rolled, and only a made landing
  of two storeys or fewer is free.
- **Retreat to edges** (recommended "can retreat to edges, one-way descent
  only"): superseded by the #3583 ruling, "refused at the edge".
- **Jumping in combat as flee-like timing** (recommended "counts as
  movement action if in combat"): superseded by #3583 and #3591; a jump
  pays both halves of flee's price.
- **The jump exemption from the sky block** (`ndb.jump_movement_allowed`):
  retired with #3579. It never gated anything, since jumps relocate with
  `move_to`; the sky block refuses all walking unaided.

## Unbuilt

- **Phase 3, elevated-position combat — 📋 UNBUILT (#1511).** Height
  advantage for ranged attacks (an aim bonus from an elevated position);
  extended effective range; enhanced aim and attack capabilities from
  edges (sniper mechanics); position-based combat modifiers in the combat
  handler; advanced tactical positioning mechanics; and seeing or aiming
  at a roof from the street.
- **Walking through air while aloft — 📋 UNBUILT (no issue).** The sky
  block in `Exit.at_traverse` refuses every walker, `stays_aloft` or not.
- **Message variations by context — 📋 UNBUILT (no issue).** The lines do
  not vary by explosive, edge or gap type; each verb has one fixed set.
  Wanted:
  - Different explosives: "Alice dives onto the flashbang!" vs "Alice
    covers the pipe bomb!"
  - Edge types: "Alice leaps from the fire escape!" vs "Alice jumps down
    from the balcony!"
  - Gap types: "Alice vaults across the alley!" vs "Alice bounds between
    rooftops!"
- **`look across <direction>` — 📋 UNBUILT (no issue).** There is no
  `look across`; `aim <direction>`, then `look`, shows the far perch.
- **Landing position — 📋 UNBUILT (not decided).** Recommended: random
  proximity if the room is occupied. Today a landing clears proximity and
  sets none.
- **Observation range — 📋 UNBUILT (not decided).** Recommended: enhanced
  look/aim range from elevated positions. Today, from a height, aim and
  look reach only the room below an edge (#3589); nothing extends their
  range.

### Future considerations

- Sky rooms become normal traversable rooms at elevated coordinates;
  flying characters and vehicles use regular movement through them; jump
  mechanics become a special case of general aerial movement; aerial
  positioning and combat in sky rooms.
- A climbing system: ways to get back up to elevated positions.
- Multiple edge types with different tactical advantages.
- Explosive shielding: partial protection mechanics.
- Framework focus (recommended): mechanics first; visibility and discovery
  enhancements belong to a future look system.
- Skills that modify jump effectiveness; special gear for edge traversal;
  more complex explosive types and interactions; weather and conditions
  affecting jumps.

## Not decided

Open questions, with the spec's recommendation where it gave one. A
recommendation is not a ruling.

**Explosive sacrifice**

1. Damage bonus: how much extra damage should the hero take? Recommended:
   +10 (meaningful cost). Today: no bonus.
2. Death mechanics: should a sacrifice have special death/injury rules?
   Recommended: standard death rules (heroism doesn't change lethality).
3. Multiple explosives: can you jump on several at once? Recommended: one
   at a time (keeps the action focused).
4. Combat state: should a sacrifice consume the combat turn? Recommended:
   bypass the turn system (emergency heroic action). Today: a real
   sacrifice skips the hero's next round; a dud or unarmed explosive costs
   nothing.

**Edges**

1. Height categories: should different edge heights have different
   effects? Recommended: a binary advantage (simple elevated vs ground).
2. Landing positioning: do you land in proximity to anyone below? (See
   Landing position under Unbuilt.)
3. Equipment effects: should gear affect jumping ability or safety?
4. Observation range: how far can you see or aim from a height? (See
   Observation range under Unbuilt.)

**Gaps**

1. Success calculation: what stats determine jump success? Today:
   Motorics, a `standard_roll` against the gap's difficulty, success on a
   tie.
2. Gap difficulty scaling: recommended a 1-5 scale (trivial to nearly
   impossible). Today: no scale; `gap_difficulty` is a number the roll must
   meet, default 10, untuned.

**System**

1. Aim system: should elevated positions enhance aim? (Phase 3, #1511.)
2. Grappling: can you grapple someone off an edge? Today: `jump off` while
   holding someone drags them over the edge with you; `jump across` lets
   go of them.
3. Throwing: do elevated positions affect throw range or accuracy?
4. Rigged edges on a jump off: should stepping off an edge rigged with a
   grenade into the air spring the trap (as walking the edge does, and as a
   direct drop does), or should jumping into the air pass an edge trap by?
   Today it passes it by.

## Related documents

- `specs/COMBAT_SYSTEM.md`: flee, `roll_to_disengage`, aim (#3355).
- `specs/PARKOUR_TEMPLATE_LIBRARY.md`: the movement kernel (§0) and the
  doctrine that keeps edges-only rooftops rare (§1.5).
- `specs/roadmaps/BALANCE_LEDGER.md`: the gravity constants and
  `JUMP_AWAY_BONUS`.
- `specs/roadmaps/MEDICAL_SUBSTRATE_READINESS.md`: Phase 7, the
  movement-policing substrate.
