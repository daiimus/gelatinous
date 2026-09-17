# Jump Command Implementation Specification

> **Status:** 🚧 **PARTIAL** — Phases 1, 2, 2b shipped; **Phase 3 not built**. ~~Verified 2026-08-02~~ ~~re-checked 2026-09-11: 24 claim(s) false~~ **re-checked 2026-09-16: 38 claim(s) false, annotated inline.** Gravity layer #3579 shipped 2026-09-16: falls traverse the column; `sky_room`/`fall_distance`/`fall_damage` retired.
>
> **⚠ Spec-vs-code corrections — the following claims were FALSE when audited:**
> - The header claimed "IMPLEMENTATION COMPLETE ✅". Phase 3 (elevated-position combat bonuses, enhanced aim from edges) has **no code**.
> **FIELD NOTES (2026-08-06, from building the Brackett fire escape):**
> (1) An edge exit whose destination is air MUST carry `sky_room` (int
> dbref) — without it the "graceful degradation" fallback turns the jump
> into a plain walk with no fall and no landing roll.
> _(2026-09-11: half-stale. Since #2944, `handle_edge_descent` REFUSES an
> edge whose destination is a sky room and carries no `sky_room`
> (jump.py:496-524) rather than stranding you. The surviving fallback is
> not a plain walk either — it applies flat `exit.db.fall_damage`, default
> 8 (jump.py:548-551). What it still skips is the landing roll and the
> per-story scaling.)_
> _(2026-09-16: SUPERSEDED — `sky_room` is retired (#3579). An edge's own
> `destination` IS the air cell, the column of cells below it IS the
> distance, and `FALL_DAMAGE_PER_STORY` is the damage; nothing in the
> runtime reads `exit.db.sky_room`, `db.fall_distance` or `db.fall_damage`
> any more. The #2944 refusal went with them: `handle_edge_descent`
> (`commands/combat/jump.py`) now branches only on whether the
> destination is air — air means hand the cell a flight plan
> (`ndb.fall_intent`) and step off, not-air means a one-storey direct
> drop with no roll and no traversal. There is no degraded fallback left
> to fall into, so the field note's warning has no failure mode to warn
> about.)_
> (2) Walking into a
> sky room never triggers falling; the entire fall experience lives in
> this command's flow.
> _(2026-09-16: SUPERSEDED — exactly backwards since #3579. Gravity is a
> property of the ROOM. `Room.at_object_receive`
> (`typeclasses/rooms.py`) calls `world.gravity.on_enter_air` for EVERY
> arrival, and anything in a room flagged `db.is_sky_room is True` that
> cannot stay up starts falling — by any door: a jump, a throw, a drop, a
> shove, a reconnect, a build script. Characters and Items fall; exits do
> not. The fall no longer lives in this command at all — the verb only
> supplies the flight plan. Walking into air is separately refused at the
> sky block in `Exit.at_traverse` (`typeclasses/exits.py`), which now has
> NO exception (see the `ndb.jump_movement_allowed` note below), so "a
> walk into air falls" describes a shove, a drop or a rebuilt column,
> not a player typing a direction.)_
> (3) The landing runs on a delayed callback
> (0.5s/story): a server reload during that window orphans the jumper in
> the sky room — do not reload while players are airborne; hardening
> item: resolve airborne characters at server start.
> **✅ FIXED (#3579, 2026-09-16):** the hardening item shipped, and the
> reload warning is retired with it. A fall is now a persistent
> `db.falling` record — `{cells, origin, edge_difficulty, roll,
> companion, next_step_at}`, the grenade-fuse shape (#505) — and
> `sweep_airborne` (`world/gravity.py`) runs from `at_server_start`
> (`server/conf/at_server_startstop.py`): it resumes every recorded fall
> at its TRUE remaining time, defers a step that came due during the
> outage by 2 s so the world is loaded first, and starts a fall for
> anything found stranded in an air cell that cannot stay up. A
> logged-out faller keeps its record and is resumed by the reconnect
> path. The cadence is no longer 0.5 s/story either: it is
> `FALL_SECONDS_PER_CELL` (1.0 s), and each tick is a real move into the
> next cell rather than a single deferred landing. Owner (2026-09-16):
> 0.5 s "is faster than any beat in the game".
> - ~~No dedicated jump test module exists — only incidental coverage in `test_drop_to_room.py` and `test_build_tools.py`.~~
>   _(2026-09-16: false as of #3579, which shipped seven dedicated modules
>   under `world/tests/`: `test_a_fall_walks_the_column.py` (the traversal
>   and its three audiences), `test_a_fall_lands_on_the_legs.py` and
>   `test_a_fall_finds_the_legs.py` (the feet→shins→thighs fill and the
>   `moving`-capacity predicate behind it), `test_a_leap_is_not_a_fall.py`
>   (the one-tick `ndb.airborne_token`),
>   `test_gravity_catches_you_on_the_way_in.py` (the room hook, for every
>   door), `test_nobody_hangs_across_a_reload.py` (`sweep_airborne`) and
>   `test_edge_jump_never_strands.py` (the bare-cell impasse). An eighth,
>   `test_every_balance_knob_is_in_the_ledger.py`, pins the gravity
>   constants to `specs/roadmaps/BALANCE_LEDGER.md` in both directions.
>   The incidental coverage in `test_drop_to_room.py` and
>   `test_build_tools.py` still exists alongside them.)_

**Status: IMPLEMENTATION COMPLETE** ✅

> _(2026-09-11: STALE — superseded by the status banner at the top of this
> file, which lists this header among the claims that were already FALSE
> when audited on 2026-08-02. The banner flagged it and left it standing,
> so the two lines have contradicted each other ever since. Phase 3 still
> has no code (#1511, open, parked). Left in place per
> annotate-don't-delete; the banner is authoritative.)_  
**Location:** `commands/combat/jump.py` - CmdJump class  
**Integration:** Added to combat cmdset, ready for live testing

## Overview
The `jump` command serves two distinct heroic and tactical functions: **explosive sacrifice** to protect others from blast damage, and **tactical descent** from elevated positions via edge exits. It integrates with existing explosive mechanics and introduces new vertical combat positioning.

## Core Mechanics

### Command Syntax
```
jump on <explosive>           # Heroic sacrifice - absorb explosive damage
jump off <direction> edge     # Tactical descent from elevated position
jump across <direction> edge  # Horizontal leap across gaps at same level
```

### Function 1: Explosive Sacrifice

#### Purpose
**Ultimate heroic action** - absorb ALL explosive damage to completely protect others in proximity.

#### Validation Requirements
1. **Explosive must exist** in current room
2. **Explosive must be armed** (`db.pin_pulled = True`)
3. **Explosive must be counting down** (active timer)
   - _(2026-09-11: neither validation exists. `jump.py:190` — "Always allow
     the heroic leap - false heroics are part of the drama!" Armed state and
     countdown are read at `jump.py:186-188` only to choose which revelation
     branch fires 2.5s later. An unarmed grenade is accepted and answered
     with "...but nothing happens. X wasn't even armed." (`jump.py:428`).)_
4. **Caller can be in or out of combat** (heroic actions transcend combat state)
5. **No proximity requirement** (can jump on explosive from anywhere in room)

#### Timing Mechanics
- **Timer-based window**: Can only jump on explosive while countdown is active
- **Instant execution**: No delay once command is entered
  - _(2026-09-11: false as shipped. `jump.py:194-206` computes a
    `revelation_delay` — 2.5s normally, `remaining_time - 0.3` when the fuse
    is shorter — and `jump.py:433` puts the entire outcome behind
    `delay(revelation_delay, reveal_outcome)`. Only the leap message is
    immediate; the blast, the damage and the dud reveal are all deferred.)_
- **Timer inheritance**: Takes over explosive's remaining countdown
  - _(2026-09-11: only for short fuses. `jump.py:195-206` inherits the
    remaining time ONLY when it is ≤ 2.5s (`remaining_time - 0.3`);
    anything longer is cut to a flat 2.5s, and the original timer is
    cancelled outright at `jump.py:209-225`. A 10s fuse detonates 2.5s
    after the leap, so the hero shortens the countdown rather than
    inheriting it.)_
- **Damage amplification**: Hero takes ALL explosive damage (100% absorption)
- **Complete protection**: Everyone else in proximity takes zero damage

#### Damage Calculation
```
Hero damage = explosive.db.blast_damage + positional_bonus
Others damage = 0 (complete protection)
```

#### Integration with Grenade System
- **Works with all explosive types**: Standard grenades, flashbangs, smoke grenades, etc.
- **Property-driven**: Uses existing `db.blast_damage`, `db.fuse_time` properties
- **Chain reaction prevention**: Hero absorbs damage, explosive doesn't trigger other explosives
- **Timer system**: Integrates with existing countdown mechanics from throw command
- **Proximity positioning**: Hero ends up in proximity to explosive (and inherits ALL its proximity relationships)

### Function 2: Tactical Descent

#### Purpose
**Vertical repositioning** from elevated sniper positions to ground level.

#### Edge Exit System
- **New exit property**: `db.is_edge = True` flag on exits
- **Elevated positioning**: Edge exits represent rooftops, ledges, balconies
- **One-way descent**: Jump down only (climbing back up requires different mechanics)
- **Safe landing**: No fall damage (tactical descent, not accidental fall)
  - _(2026-09-16: false since #3579 — and never true of the shipped code
    either. Stepping off an edge always succeeds; the LANDING is what is
    rolled for, Motorics vs `edge_difficulty` (default
    `FALL_EDGE_DIFFICULTY_DEFAULT` = 8) + `FALL_LANDING_DIFFICULTY_PER_CELL`
    (2) x cells fallen. A make does not zero the damage: it absorbs
    `FALL_LANDING_ABSORBED_CELLS` (2) storeys, so a 1-2 storey tactical
    descent landed well IS free and anything taller is not. A miss pays
    `FALL_DAMAGE_PER_STORY` (5) x every cell passed. The one genuinely
    roll-free case left is a DIRECT DROP — an edge whose destination is not
    air — charged one storey, no roll, no traversal.)_

### Function 3: Horizontal Leap

#### Purpose
**Same-level gap crossing** between buildings, rooftops, or across dangerous terrain.

#### Gap Jump System
- **Gap edge property**: `db.is_gap = True` flag on exits (can combine with `db.is_edge`)
- **Same-level movement**: Horizontal jump between rooms at equal elevation
- **Risk/reward**: Potential for failure and consequences
- **Tactical repositioning**: Quick movement across obstacles

#### Validation Requirements
1. **Edge exit must exist** in current room
2. **Edge must be valid**: `db.is_edge = True` on exit object
3. **Destination must exist**: Exit leads to valid room below
4. **Caller movement allowed**: Standard movement restrictions apply

#### Gap Jump Validation Requirements
1. **Gap exit must exist** in current room
2. **Gap must be valid**: `db.is_gap = True` on exit object  
3. **Destination must exist**: Exit leads to valid room at same level
4. **Jump success check**: General Motorics stat check vs gap difficulty
5. **Caller movement allowed**: Standard movement restrictions apply

#### Tactical Advantages of Edge Positions
- **Elevated combat**: Height advantage for ranged attacks
- **Protected position**: Not adjacent to ground level - prevents melee advancement
- **Sniper mechanics**: Enhanced aim and attack capabilities
- **Observation**: Can look down on ground level (enhanced reconnaissance)
- **Melee immunity**: Ground-level opponents cannot advance for melee attacks

## Technical Implementation

### Technical Infrastructure Notes
- **Timer System**: Evennia timer infrastructure available for countdown/cooldown mechanics
- **Combat Integration**: Existing 6-second combat round timing for standardization
- **Room Customization**: Enhanced `CmdLook` proves room description modification capability
- **Object Properties**: Property-based system (`db.is_edge`, `db.blast_damage`) validated working
- **Exit System**: Standard Evennia exit objects ready for property enhancement

### Explosive Sacrifice Implementation

#### Validation Flow
```
1. Parse "jump on <explosive>" syntax
2. Find explosive object in room
3. Validate explosive is armed and counting down
4. Calculate heroic damage (full blast + bonus)
5. Cancel explosive's normal detonation
6. Apply damage to hero only
7. Announce heroic sacrifice
8. Clean up explosive and timer state
```

#### Timer System Integration
```python
# Pseudo-code for explosive timing
def jump_on_explosive(caller, explosive):
    if not explosive.db.pin_pulled:
        return "The explosive is not armed!"
    
    current_timer = explosive.ndb.countdown_remaining
    if current_timer <= 0:
        return "Too late! The explosive has already detonated!"
    
    # Hero takes all damage
    hero_damage = explosive.db.blast_damage + 10  # heroic bonus damage
    explosive_damage_type = getattr(explosive.db, "damage_type", "laceration")
    apply_damage(caller, hero_damage, location="chest", injury_type=explosive_damage_type)
    
    # Cancel normal explosion
    cancel_explosive_timer(explosive)
    
    # Clean up proximity effects
    clear_explosive_proximity(explosive)
    
    # Heroic announcement
    announce_heroic_sacrifice(caller, explosive)
```

### Edge Exit Implementation

#### Edge Exit Implementation

#### Sky Room System (Pre-existing Architecture)

**Philosophy**: Sky rooms are permanent world features, not temporary objects. This prepares for future XYZ coordinate systems and flying vehicle mechanics.

**Room Lookup Strategy**:

> _(2026-09-11: only strategy 4's inverse ships. Both call sites —
> `jump.py:484` (edge) and `jump.py:723` (gap) — read `exit_obj.db.sky_room`
> as an int dbref and `search_object(f"#{id}")`. There is no tag lookup and
> nothing reads `db.origin_room` / `db.destination_room` anywhere in the
> repo. The only bidirectional behaviour is `get_sky_room_for_gap`
> (`jump.py:947-1004`), whose second try falls back to the
> reverse-direction exit (`jump.py:975-1001`) — on gap FAILURES only, never
> on edge descent. Strategies 1-3 are unbuilt.)_
1. **Tagged rooms**: Sky rooms tagged with `sky_{origin_id}_{destination_id}`
2. **Property-based**: Sky rooms with `db.origin_room` and `db.destination_room` properties
3. **Bidirectional**: Sky rooms that work for both directions of travel
4. **Fallback**: Direct movement if no sky room configured (graceful degradation)

> _(2026-09-16: the whole section is retired by #3579. **No lookup of any
> kind exists** — there is nothing left to look a sky room UP by, because
> the exit's own `destination` IS the air cell. `handle_edge_descent` and
> `handle_gap_jump` (`commands/combat/jump.py`) read `exit.destination`,
> ask `world.gravity.is_sky` whether it is air, and branch; the far perch
> of a gap lives in `gap_destination`, resolved by
> `resolve_gap_destination`. `exit.db.sky_room` is gone from the runtime,
> so strategy 4's "graceful degradation" has no trigger, and
> `get_sky_room_for_gap` — the only bidirectional behaviour the 2026-09-11
> note found — is deleted. The four strategies above are historical
> design, not a menu a builder chooses from.)_

**Fall Room Strategy**:

> _(2026-09-15: strategies 2 and 3 are UNBUILT, and strategy 1 ships only
> for edges. `grep -rn "is_fall_room\|fall_room_"` over every `.py` in the
> repo finds no reader for the `fall_room_{destination_id}` tag or for
> `db.is_fall_room` — nothing but this spec writes or reads them, so a
> builder who follows the Builder Workflow below produces a tag and an
> attribute that no code path consults. The one live `exit.db.fall_room`
> read that decides where a body lands is the **edge**-landing path
> (`handle_edge_fall_and_landing`), and only when the landing roll fails;
> `world/mapping.py` also reads it, as map-export data, for both edge and
> gap exits — so `fall_room` on a gap exit still matters to the map even
> though the jump ignores it. The **gap**-failure path ignores
> `fall_room` entirely and resolves the landing with
> `follow_gravity_to_ground`, walking one-way `down` exits to `db.is_ground`
> per the movement kernel in `specs/PARKOUR_TEMPLATE_LIBRARY.md` §0; the
> helper written for the gap lookup, `get_fall_room_for_gap`, had no callers
> and was deleted in #3392. Strategy 4's soft landing is therefore also
> unbuilt for gaps — gravity, not the intended destination, decides.
> Whether gaps SHOULD honour an authored crash site is an open owner call,
> not a bug to fix from this note.)_
>
> _(2026-09-16 — #3579 answers that owner call and retires the mechanism
> the four strategies describe. **Gravity only.** Owner ruling: "it would
> always follow gravity straight down. Essentially it's checking if it's a
> skyroom and if it is proceeding down." A fall is no longer a lookup that
> produces a destination — it is a traversal. `world/gravity.py`
> re-resolves the cell's `down` exit every tick (by key or by alias `d`, so
> a column the crane rebuilds on every trip still works), moves the body
> one cell per `FALL_SECONDS_PER_CELL`, and lands when the next room is not
> air. The gravity-WALK the 2026-09-15 note describes is gone with it:
> `follow_gravity_to_ground` is deleted, `db.is_ground` no longer decides
> anything about a fall, and so is `handle_edge_fall_and_landing` — the
> last runtime reader of `exit.db.fall_room`. `fall_room` itself SURVIVES
> as world data only: `world/mapping.py` still exports it on edge and gap
> links, and it is scheduled for retirement with **#3580** (the ruling
> quoted above), not with this change. Strategies 2 and 3 remain unbuilt
> and are now unbuildable without reopening that ruling.)_

1. **Exit-specified**: `exit.db.fall_room` points to specific crash site — _built for edges only (failed landing roll); ignored on gap failures_
2. **Tagged rooms**: Fall rooms tagged with `fall_room_{destination_id}` — _UNBUILT, nothing reads this tag_
3. **Dedicated crash sites**: Rooms with `db.is_fall_room = True` near destination — _UNBUILT, nothing reads this attribute_
4. **Fallback**: Use intended destination for soft landing — _gaps fall by gravity to `db.is_ground` instead_

**Future XYZ Integration**:
- Sky rooms become normal traversable rooms at elevated coordinates
- Flying characters/vehicles use regular movement through sky rooms
- Jump mechanics become special case of general aerial movement
- No dynamic creation/deletion required

**Builder Workflow**:

> _(2026-09-16: rewritten to the surviving attribute set (#3579). Retired
> lines are kept below, marked RETIRED with what replaced them, rather
> than deleted — a builder who finds one of these attributes already
> written on a live exit needs to know it is inert, not wonder what it
> did. The load-bearing change: **the column is the flight plan**. An air
> cell needs a `down` exit to the next cell and the bottom cell's `down`
> needs to reach something that is not air; nothing else places a body.)_

```python
# The air cell. The FLAG is the truth (`world.gravity.is_sky` requires a
# literal True); the typeclass is not consulted, so a plain Room flagged
# in place is a legal air cell and a SkyRoom flipped into a catwalk is
# legally walkable.
sky_room = create_object("typeclasses.rooms.Room", key="Sky above Downtown")
sky_room.db.is_sky_room = True
sky_room.db.desc = "You soar through the air between towering buildings..."
# sky_room.tags.add("sky_room", category="room_type")   # RETIRED: no reader
# sky_room.db.origin_room = rooftop_a                   # RETIRED: no reader
# sky_room.db.destination_room = rooftop_b              # RETIRED: no reader

# THE COLUMN IS MANDATORY. Each air cell gets a one-way `down` (key
# "down", alias "d") to the cell beneath it, and the bottom one lands on
# something that is not air. A cell with no `down`, or a `down` whose
# destination no longer resolves, stops the fall cleanly IN that cell
# with a message and no damage — the parked impasse, #3581.
create_object("typeclasses.exits.Exit", key="down", aliases=["d"],
              location=sky_room, destination=cell_below)

# Fall rooms are not a thing any more: the fall lands wherever the column
# ends, and `db.is_ground` no longer decides anything about a fall.
# crash_site.tags.add(f"fall_room_{rooftop_b.id}")  # RETIRED: never had a reader
# crash_site.db.is_fall_room = True                 # RETIRED: never had a reader

# Configure gap exit: destination = the air cell, gap_destination = the
# far perch a MADE leap lands on.
gap_exit.db.is_gap = True
gap_exit.db.gap_difficulty = 10          # omit for GAP_DIFFICULTY_DEFAULT (10)
gap_exit.db.gap_destination = far_roof.id
gap_exit.db.gap_width = "medium"         # descriptive only
# gap_exit.db.fall_room = crash_site     # SURVIVES as map data only (world/mapping.py);
#                                        # no jump or fall path reads it. Retires with #3580.
```

#### Exit Property System

> _(2026-09-16: rewritten to the surviving attribute set (#3579).
> **Geometry is the base and the per-exit damage numbers are retired** —
> owner ruling: "we'll have cyberlegs... parachutes, flight... but
> calculating potential damage based on geometry will always be
> relevant." The exit's destination is the air cell, the column below it
> is the distance, and `FALL_DAMAGE_PER_STORY` is the damage, so
> `sky_room`, `fall_distance` and `fall_damage` have nothing left to say.
> Survivors: `is_edge`, `edge_difficulty`, `is_gap`, `gap_difficulty`,
> `gap_destination`, `gap_width` and `fall_room` — of which `gap_width`
> is descriptive world data with no runtime reader at all, and
> `fall_room` is read only by the map exporter, until #3580 retires it. Retired lines are commented rather than
> deleted so a builder meeting one on a live exit knows it is inert.)_

```python
# Exit object properties for edge designation
exit.db.is_edge = True
exit.db.edge_type = "rooftop"     # Optional categorization
exit.db.edge_difficulty = 8       # Landing-roll base; omit for FALL_EDGE_DIFFICULTY_DEFAULT (8)
# exit.db.fall_damage = 8         # RETIRED (#3579): damage is FALL_DAMAGE_PER_STORY x cells passed

# Gap jump properties (can combine with is_edge)
exit.db.is_gap = True
exit.db.gap_difficulty = 10       # Takeoff roll; omit for GAP_DIFFICULTY_DEFAULT (10)
exit.db.gap_destination = far_roof.id   # REQUIRED: the far perch a made leap lands on
exit.db.gap_width = "medium"      # Descriptive; authored on live gaps, no runtime reader
# exit.db.gap_distance = "wide"   # RETIRED: superseded by gap_width; never had a reader
# exit.db.fall_distance = 2       # RETIRED (#3579): the column below the cell IS the distance
exit.db.fall_room = room_obj      # SURVIVES as map data only (world/mapping.py); retires with #3580

# Sky room properties (pre-existing rooms)
sky_room.db.is_sky_room = True     # The flag, and only a literal True, makes a cell air
# sky_room.db.origin_room = room1          # RETIRED: no reader
# sky_room.db.destination_room = room2     # RETIRED: no reader
# sky_room.tags.add("sky_room", category="room_type")   # RETIRED: no lookup exists

# Anything that must NOT fall carries the one predicate gravity asks:
flier.db.stays_aloft = True        # strict `is True`; the seam for flight / vehicles

# Fall room properties
# RETIRED (#3579), and never built: nothing has ever read `db.is_fall_room`
# or the `fall_room_{id}` tag, and there is no fall-destination lookup left
# to read them. The column decides where a body lands.
# fall_room.db.is_fall_room = True
# fall_room.tags.add(f"fall_room_{destination.id}")

# 3D Room Structure Example (2026-09-16: still the right SHAPE, with the
# bottom of the diagram corrected — the `down` chain is not an escape
# hatch to a designated Fall Room, it is the whole fall, one cell per
# tick, all the way to the first room that is not air):
# Rooftop (origin) --east--> Air cell (transit) --east--> Adjacent Rooftop (destination)
#                                 |
#                               down          <- one cell per FALL_SECONDS_PER_CELL
#                                 |
#                             Air cell
#                                 |
#                               down
#                                 |
#                          Street (not air)   <- lands here; damage charged for cells passed
# Each air cell has corresponding directional exits (east cell has west back to origin);
# those sideways exits are ALSO what the fall announces to — every walkable
# surface beside a cell a body passes through sees it go by.
#
# Future Compatibility: air cells already support flying vehicles/characters —
# `db.stays_aloft is True` is the single predicate gravity asks, and anything
# that answers True sits in the cell and watches other people fall past.
```

#### Jump Descent Flow
```
1. Parse "jump off <direction> edge" syntax
2. Find edge exit in specified direction
3. Validate edge properties
4. Move character to destination room
5. Announce dramatic descent
6. Update character position
```

> _(2026-09-16: steps 4-6 are wrong since #3579 — stepping off an edge
> always succeeds, and the verb's whole job now ends at the air cell.
> `handle_edge_descent` (`commands/combat/jump.py`) parses, finds the
> edge, validates `is_edge` plus a destination, and then **branches on
> whether that destination is air** (`world.gravity.is_sky`). NOT AIR is
> a direct drop: one `move_to`, one storey of `FALL_DAMAGE_PER_STORY`, no
> roll, no traversal, done. AIR writes the flight plan onto
> `ndb.fall_intent` (`edge_difficulty`, `roll=True`), moves into the
> cell, attaches a dragged companion to the leader's fall record, drops
> combat and aim state, announces the departure to the room left — and
> stops. The cell's `at_object_receive` hook starts the fall from there,
> stepping down the column one cell per `FALL_SECONDS_PER_CELL` and
> rolling for the landing at the bottom. Step 6, "update character
> position", is no longer something the verb does at all: the faller's
> position updates once per tick until the column ends.)_

#### Landing and damage placement (#3579, 2026-09-16)

New section — the spec had no account of where fall damage LANDS, only
of how much there was.

**The landing roll** fires on edge descents only (`roll=True` in the
`db.falling` record). Motorics vs `edge_difficulty` (default
`FALL_EDGE_DIFFICULTY_DEFAULT` = 8) + `FALL_LANDING_DIFFICULTY_PER_CELL`
(2) × cells fallen. A **make absorbs `FALL_LANDING_ABSORBED_CELLS` (2)
cells** rather than dividing the damage — owner's shape: skill turns a
fall into a shorter fall, so a two-storey drop landed well is free and a
twelve-storey one is not survivable by skill alone. A **failed leap never
rolls**, and neither does an **item**: things take no damage at all, they
arrive and are heard arriving.

**Damage** is `FALL_DAMAGE_PER_STORY` (5) × effective cells, `blunt`,
charged once at the bottom, and it is **filled from the feet up** —
owner: damage lands "legs -> limbs -> other randomly":

1. **Legs first.** A leg is *every destroyable organ that feeds the
   `moving` capacity* — read off the live organ, so a chrome leg counts
   and a rat fills its hind paws first. Ordered by the species'
   anatomical display order, reversed: feet, then shins, then thighs.
2. **Then the other severable limbs**, excluding the head.
3. **Then random surviving containers** the first two tiers did not
   cover.

Each organ is exhausted before the next; armour on a container softens
the chunk that container receives and the fill **moves on** (a partial
fill under armour is the honest reading, not a re-roll); and the fill
**stops the instant a chunk kills**. The result is the owner's target
shape — a long fall is more survivable than a lethal hit to the chest and
leaves the body wrecked from the ground up.

**Bodyshield** (an edge descent taken while grappling): the shipped
splits are preserved, now as constants — a made landing charges the
victim `FALL_BODYSHIELD_MADE_VICTIM` (0.75) and the grappler
`FALL_BODYSHIELD_MADE_GRAPPLER` (0.25) of the fall; a failed one charges
1.5 and 0.5. Both survivors have their grapple rebuilt in a fresh handler
at the landing room, the grappler yielding.

**Direct drop** (an edge whose destination is not air): one storey of
`FALL_DAMAGE_PER_STORY`, no roll, no traversal — and with a grappled
victim, the made split applied to that one storey.

All eleven constants named above are registered in
`specs/roadmaps/BALANCE_LEDGER.md`, all currently **Tuned? No**.

#### Gap Jump Flow
```
1. Parse "jump across <direction> edge" syntax
2. Find gap exit in specified direction
3. Validate gap properties and difficulty
4. Make jump success roll (Motorics stat vs gap difficulty)
5. On success or tie: Move to destination room (flee-like action, transit through sky)
6. **Check for rigged grenades on landing edge** (new security integration)
7. On failure or critical failure: Fall to failure_room with fall damage
8. Announce jump attempt and outcome
9. Consume combat turn (flee-like timing)
10. Calculate fall damage: rooms_fallen × damage_multiplier
```

> _(2026-09-16: steps 3, 5, 7 and 10 are restated by #3579
> (`handle_gap_jump`, `commands/combat/jump.py`). **Step 3 gains a
> refusal:** a gap whose `gap_destination` no longer resolves to a real
> non-air room is refused ON THE ROOF — "The X gap doesn't lead anywhere
> safe to land." — rather than silently swapped for the air cell (#3559,
> via `resolve_gap_destination`). **Step 4 is unchanged** and is still the
> only roll a gap makes: Motorics vs `gap_difficulty`, default
> `GAP_DIFFICULTY_DEFAULT` (10), rolled at TAKEOFF. **Step 5 is now two
> beats:** a make sets a one-tick `ndb.airborne_token`, moves into the air
> cell, and lands on `gap_destination` one `FALL_SECONDS_PER_CELL` later —
> the leaper is genuinely in the air for a tick and is seen there. **Step
> 7 has no failure_room:** a miss enters the cell with no token, gravity
> takes over, and the body falls down whatever column is under the gap.
> **Step 10's multiplier is gone:** damage is `FALL_DAMAGE_PER_STORY` (5)
> x cells actually passed, charged once at the bottom, and a failed leap
> never rolls to land. Step 6 still happens, in
> `finalize_successful_gap_jump`, on the made branch only.)_

#### Rigged Grenade Integration for Gap Jumps

**New Security Feature**: Gap jumps now integrate with the rigged grenade system to detect and trigger traps when landing on rigged edges.

**Detection Logic**:
1. **Return edge identification**: When landing from a gap jump, identifies the return edge leading back to origin
2. **Direction mapping**: Uses opposite direction mapping (jump north → look for south edge on landing)
3. **Edge matching**: Checks both exit key AND aliases for proper direction matching
4. **Rigged grenade check**: Calls existing `check_rigged_grenade` function on matched edge
5. **Rigger immunity**: Maintains rigger immunity system (can't trigger own traps)

**Technical Implementation**:
```python
# Find return edge by opposite direction
opposite_direction = self.get_opposite_direction(self.direction)

# Check destination contents for matching edge
for obj in destination.contents:
    # Match by key or aliases
    key_matches = obj.key.lower() == opposite_direction
    aliases_match = any(alias.lower() == opposite_direction 
                       for alias in obj.aliases.all())
    
    if ((key_matches or aliases_match) and 
        hasattr(obj.db, 'is_edge') and obj.db.is_edge):
        # Found return edge - check for rigged grenades
        check_rigged_grenade(self.caller, obj)
```

**Integration Points**:
- **Uses existing rigged grenade system**: No new mechanics, leverages CmdThrow rigging
- **Respects rigger immunity**: Riggers cannot trigger their own traps
- **Full explosion sequence**: Pin pull, countdown, proximity, damage, cleanup
- **Edge cleanup**: Automatically cleans up rigged grenades after triggering
- **Debug logging**: Enhanced debug output for troubleshooting edge detection

#### Room Integration
- **Elevated rooms**: Rooms with edge exits have tactical advantage
- **Ground rooms**: Normal rooms accessible via edge descent
- **Sky rooms**: Transit-only spaces for edge/gap movement - **restricted from normal traversal**
- **Fall rooms**: Failure destinations with fall damage based on room count fallen
- **3D connectivity**: Sky rooms have bidirectional exits (east sky has west return)
- **Damage calculation**: Fall damage = rooms fallen × damage multiplier
- **Bidirectional awareness**: People below can potentially see elevated positions
- **Edge visibility**: Edge and gap properties visible in room descriptions (future look framework)
- **Framework building**: Current implementation focuses on mechanics, visibility enhancements later

#### Sky Room Traversal Restrictions

**Philosophy**: Sky rooms are transit-only spaces that cannot be accessed through normal movement commands. This prevents bypassing the gap jump mechanics while maintaining their function as aerial transit zones.

**Restriction Implementation**:

> _(2026-09-16: the exemption is deleted (#3579), and it never gated
> anything. `ndb.jump_movement_allowed` was read in `Exit.at_traverse` —
> but jumps and falls relocate with `move_to`, which never reaches
> `at_traverse`, so the flag guarded a door no jump ever used. The sky
> block in `typeclasses/exits.py` now refuses ALL walking into, out of and
> between air cells with no exception, and gravity works through the room
> hook rather than through the exit. Everything else in this section still
> holds: the block, the visibility filtering, and the three error strings
> below are live.)_

- **Normal movement blocked**: Characters cannot use standard movement commands (n, s, e, w, up, down) to enter or exit sky rooms
- ~~**Jump system exempt**: Jump commands can move through sky rooms using `ndb.jump_movement_allowed` flag~~ — _RETIRED (#3579): the flag is deleted; there is no exemption_
- **Visibility filtering**: Pure sky rooms are hidden from room exit displays (not shown in "Exits:" listing)
- **Edge/gap exception**: Sky rooms that are also edges/gaps are visible but blocked by existing edge/gap restrictions
- **Clear error messages**: Informative feedback when players attempt forbidden movement
- **Gravity system support**: Fall mechanics work normally through sky rooms

**Technical Details**:
```python
# In Exit.at_traverse() - sky room restriction check
current_room_is_sky = getattr(traversing_object.location.db, "is_sky_room", False)
target_room_is_sky = getattr(target_location.db, "is_sky_room", False)
# RETIRED (#3579, 2026-09-16) -- both lines below are gone:
# is_jump_movement = getattr(traversing_object.ndb, "jump_movement_allowed", False)
# if (current_room_is_sky or target_room_is_sky) and not is_jump_movement:

if current_room_is_sky or target_room_is_sky:
    # Block traversal with appropriate error message. No exception: jumps
    # and falls relocate with move_to and never reach at_traverse.
    return

# In Room.get_custom_exit_display() - visibility filtering
destination_is_sky = getattr(exit_obj.destination.db, "is_sky_room", False)
if destination_is_sky and not (is_edge or is_gap):
    continue  # Skip pure sky rooms from exit display
```

**Error Messages**:
- **Entering sky room**: "You cannot enter sky rooms through normal movement! Use jump commands to access aerial transit."
- **Leaving sky room**: "You cannot leave sky rooms through normal movement! You are falling - wait for gravity to take effect."
- **Between sky rooms**: "You cannot traverse between sky rooms! Sky rooms are transit-only spaces."

**Visibility Behavior**:

> _(2026-09-11: there is no "Edges:" section — that shape never shipped.
> `typeclasses/rooms.py:1046-1063` renders prose: "There is an edge to the
> north." / "There are edges to the ..." / "There is a gap to the ...". The
> filtering claim is correct — `rooms.py:926-931` skips exits whose
> destination is a sky room unless the exit is itself an edge or gap. The
> "Exits:" listing named in Restriction Implementation above is prose too
> (`rooms.py:1065-1070`).)_
- **Pure sky rooms**: Completely invisible in room exit listings
- **Sky + edge rooms**: Visible in "Edges:" section, blocked by edge restrictions
- **Sky + gap rooms**: Visible in "Edges:" section, blocked by gap restrictions
- **Result**: Players cannot see or access pure transit sky rooms

**Jump System Integration**:

> _(2026-09-16: all four bullets are retired (#3579). They describe a
> mechanism that was deleted because it never did anything: jumps and
> falls relocate with `move_to`, which does not call `at_traverse`, so no
> jump ever needed the flag and no jump ever set it on a path that
> mattered. The security the last two bullets claim was already provided
> by the block itself. What replaces the integration: the verb hands the
> air cell a flight plan on `ndb.fall_intent` (or a one-tick
> `ndb.airborne_token` for a made leap) and steps off with `move_to`;
> `Room.at_object_receive` -> `world.gravity.on_enter_air` decides what
> happens next, for a jumper and a shoved body alike.)_

- ~~Jump commands temporarily set `ndb.jump_movement_allowed = True` before sky room movement~~ — _RETIRED_
- ~~Flag is cleared immediately after successful movement~~ — _RETIRED_
- ~~Ensures only legitimate jump mechanics can use sky rooms~~ — _RETIRED: the flag gated nothing_
- ~~Maintains security while allowing intended functionality~~ — _RETIRED: the sky block does this unaided_

## Combat Integration

### Explosive Sacrifice Combat Effects

> _(2026-09-11: both of the first two bullets are false as shipped, and
> they repeat claims corrected earlier in this file. "Instant resolution"
> — the outcome is deferred 2.5s (`jump.py:433`; see Timing Mechanics).
> "Combat bypass" — being grappled refuses the sacrifice outright
> (`jump.py:139-149`), and the hero's next round is skipped
> (`jump.py:416`, `NDB_SKIP_ROUND`). "Proximity clearing" and "chain
> reaction prevention" do hold: the explosive is deleted at `jump.py:378`
> after the hero inherits its proximity list (`jump.py:353-361`, fixed in
> #2453).)_
- **Instant resolution**: Not turn-based, immediate heroic action
- **Combat bypass**: Works regardless of combat state
- **Proximity clearing**: Removes explosive threat from all characters
- **Chain reaction prevention**: Stops multiple explosive chains

### Edge Position Combat Advantages
- **Aim bonus**: Enhanced accuracy from elevated position
- **Range advantage**: Extended effective range for attacks
- **Melee immunity**: Ground opponents cannot advance to edge positions (not adjacent)
- **Retreat limitation**: Limited escape routes from elevated position

### Turn-Based Considerations
- **Jump on explosive**: Immediate action, bypasses turn system (heroic emergency action)
- **Jump off edge**: Counts as movement action if in combat (flee-like timing)
- **Jump across gap**: Counts as movement action if in combat (flee-like timing)
- **Position bonuses**: Elevated positions provide combat modifiers

## Room Announcements

> _(2026-09-11: illustrative, not shipped text. Every string below differs
> from the code — e.g. the sacrifice line is "{actor} makes the ultimate
> sacrifice, leaping onto X!" (`jump.py:242-262`), the edge departure is
> "{actor} leaps off the X edge!" (`jump.py:616`), the successful landing is
> "{actor} lands with athletic grace from above!" (`jump.py:1230`). Shipped
> lines are rendered through `msg_room_identity` with `{actor}`/`{victim}`
> refs, so the actor is named per-observer rather than as a fixed name.
> **Defect, not a spec error:** the sacrifice lines interpolate the player's
> raw typed argument (`self.explosive_name`, at `jump.py:246`, `259`, `385`,
> `407`, `421`, `428`) instead of the resolved object's name — `jump on
> gren` announces "...leaping onto gren!".)_

### Explosive Sacrifice Messages
- **Hero message**: "You leap onto the grenade, shielding everyone with your body!"
- **Room message**: "Alice heroically leaps onto the grenade, absorbing the blast!"
- **Outcome message**: "The explosion is muffled beneath Alice's sacrifice - everyone else is safe!"

### Edge Descent Messages
- **Caller message**: "You leap off the rooftop edge, dropping to the street below!"
- **Origin room**: "Alice leaps off the edge, disappearing toward the street below!"
- **Destination room**: "Alice drops down from above, landing dramatically!"

### Gap Jump Messages
- **Success caller**: "You sprint forward and leap across the gap, landing safely!"
- **Success origin**: "Alice takes a running leap across the gap and disappears!"
- **Success destination**: "Alice comes flying across the gap, landing with a roll!"
- **Failure caller**: "You leap toward the gap but fall short, tumbling down!"
- **Failure origin**: "Alice attempts the jump but falls short, disappearing below!"
- **Failure destination**: "Alice crashes down from above, having missed the jump!"

### Fall Announcements — the three-audience model (#3579, 2026-09-16)

A fall is now a sequence of real moves, so it is narrated per CELL rather
than once at the bottom. Owner ruling: *"if I'm flying in a room or in a
flying vehicle in one of the sky rooms, I'd see someone fall past me."*
Every step of `world/gravity.py` announces to three audiences plus the
faller, all through `msg_room_identity` so each watcher resolves the
faller by their own perceived identity (and an item renders through its
own `get_display_name`):

1. **The cell left** — "{actor} drops away beneath you." (an item:
   "tumbles away beneath you.")
2. **The cell entered**, when it is still air — "{actor} falls past you,
   still dropping." (an item: "tumbles past you.") This is the audience
   the ruling is about: anyone who can stay up in that cell sees the body
   go by.
3. **Every walkable surface beside the cell entered** — "{actor} falls
   past the edge to the <direction>." The list is data-driven, not
   authored: `neighbour_surfaces` reads the cell's own non-`down`
   exits whose destination is not air, and the direction is REVERSED with
   `DIRECTION_OPPOSITES` — a body in the cell east of a roof is seen from
   that roof falling past to the east, even though the cell's exit to the
   roof is keyed "west".
4. **The faller** gets one line of their own ("You plummet downward
   through open air."), and a dragged companion gets theirs ("You are
   dragged down through open air.").

The landing then narrates once more, to the landing room and the faller,
and a fall that runs out of column stops with the impasse message instead
(see Edge Descent Errors).

### Message Variations by Context
- **Different explosives**: "Alice dives onto the flashbang!" vs "Alice covers the pipe bomb!"
- **Edge types**: "Alice leaps from the fire escape!" vs "Alice jumps down from the balcony!"
- **Gap types**: "Alice vaults across the alley!" vs "Alice bounds between rooftops!"

## Error Handling

### Explosive Sacrifice Errors

> _(2026-09-11: none of the four strings below is in the code. Shipped:
> `jump.py:158` "You don't see 'X' here."; `jump.py:165` "X is not an
> explosive device." (an object-type check this section omits);
> `jump.py:420-421` "...but X makes only a small 'click' sound. It was a dud
> or the timer expired."; `jump.py:428` "...but nothing happens. X wasn't
> even armed." The last two are delayed OUTCOMES broadcast to the room, not
> refusals — see the Validation Requirements note above.)_
- **Explosive not found**: "You cannot find '<explosive>' to jump on."
- **Explosive not armed**: "The <explosive> is not armed - there's no danger to absorb."
- **Timer expired**: "Too late! The <explosive> has already detonated."
- **No explosive timer**: "The <explosive> is not counting down."

### Edge Descent Errors

> _(2026-09-11: shipped strings differ and one refusal is missing here.
> `find_edge_exit` (`jump.py:700-716`) says "There is no exit to the X."
> (`jump.py:706`) and "The X exit doesn't lead anywhere." (`jump.py:713`);
> `jump.py:472` "The X exit is not an edge you can jump from.";
> `jump.py:477` "The X edge doesn't lead anywhere safe to land.". There is
> no "blocked" refusal at all — walking an edge is blocked instead, in
> `Exit.at_traverse` (`typeclasses/exits.py:115-119`). Missing from this
> list: the #2944 refusal at `jump.py:496-524` — "You lean out over the X
> edge and stop. There's nothing to land on down there — no ledge, no fire
> escape, nothing but air." (`jump.py:520-523`).)_
>
> _(2026-09-16: **the #2944 refusal is gone** (#3579). It existed to catch
> an edge into air with no `sky_room`, and `sky_room` is retired — an edge
> into air is now always legal, because the air cell itself is the
> destination and the column below it is the fall. Stepping off ALWAYS
> succeeds. The failure mode that replaces it happens mid-fall, not at
> the roof: when a cell has no `down` exit, its `down` no longer resolves,
> or `FALL_MAX_CELLS` (30) is exceeded, the fall **stops cleanly in that
> cell** — "You come to a stop in open air. There is nothing beneath you
> here — no ledge, no street, only more sky that nobody has finished.
> Gravity is patient." — with no damage, no crash and no strand
> (`world/gravity.py`, `_strand`). The room sees "{actor} hangs in the
> open air, with nothing beneath." That is the **parked impasse, #3581**:
> the code's answer is deliberate and correct; the missing column below
> the colony's highest crossings is world data (#2945), not a bug in this
> command. The two gap refusals that DO fire at the roof are the
> not-a-gap message and the unresolvable-perch message (#3559).)_
- **No edge exit**: "There is no edge to jump off here."
- **Invalid exit**: "That is not an edge you can jump from."
- **Blocked exit**: "The edge is blocked - you cannot jump off."
- **No destination**: "The edge leads nowhere - jumping would be suicide."

### Gap Jump Errors

> _(2026-09-11: **missed by the 2026-08-02 audit** — none of the five
> strings below ships either. Shipped: `jump.py:706` "There is no exit to
> the X." (there is no gap-specific not-found message); `jump.py:665` "The X
> exit is not a gap you can jump across."; `jump.py:681` "The X gap doesn't
> lead anywhere safe to land.". There is no "blocked gap" refusal and no
> "You cannot attempt that jump right now." — the only movement-side
> refusal is the grapple block at `jump.py:637-640`, "You cannot jump while
> being grappled by X!")_
- **No gap exit**: "There is no gap to jump across here."
- **Invalid gap**: "That is not a gap you can jump across."
- **Blocked gap**: "The gap is blocked - you cannot make the jump."
- **No destination**: "The gap leads nowhere safe to land."
- **Movement restricted**: "You cannot attempt that jump right now."

### Safety Validations
- **Explosive state checking**: Ensure explosive object is in valid state
- **Timer state validation**: Confirm countdown is active and accessible
- **Exit state verification**: Validate edge exit is traversable
- **Character state checks**: Ensure character can perform action

## Architecture Integration Points

### Existing Systems Used
- **Explosive system**: Uses grenade properties and timer mechanics from throw command
- **Room system**: Standard room connectivity and movement
- **Combat handler**: For position-based combat modifiers
- **Damage system**: For heroic damage application

### New Systems Required
- **Edge exit flagging**: Property system for marking edge exits
- **Gap jump system**: Horizontal leap mechanics with success/failure
- **Vertical combat**: Height-based combat advantages
- **Heroic sacrifice**: Damage absorption mechanics
- **Timer cancellation**: Ability to interrupt explosive countdowns
- **Jump skill system**: Stat-based success probability for gap jumps
- **Fall damage calculation**: Distance-based damage (rooms fallen × multiplier)
- **3D room navigation**: Transit-only sky rooms with bidirectional connectivity

### Integration with Throw Command
- **Shared explosive properties**: Uses same `db.blast_damage`, `db.fuse_time` system
- **Timer compatibility**: Works with existing countdown mechanics
- **Proximity system**: Interacts with grenade proximity from throw command
- **Chain reaction handling**: Prevents chain explosions through sacrifice
- **Rigged grenade detection**: Gap jumps check for and trigger rigged grenades on landing edges
- **Direction mapping system**: Uses opposite direction calculation for return edge detection
- **Alias matching**: Enhanced edge detection that checks both exit keys and aliases

## Implementation Priority

### Phase 1: Explosive Sacrifice
- Command parsing for "jump on" syntax
- Explosive object validation and timer checking
- Heroic damage calculation and application
- Timer cancellation and cleanup mechanics

### Phase 2: Edge Exit System
- Exit property system for edge designation
- Command parsing for "jump off" syntax
- Vertical movement mechanics
- Room transition and announcements

### Phase 2b: Gap Jump System  
- Gap exit property system
- Command parsing for "jump across" syntax
- Success/failure mechanics based on stats
- Horizontal movement with risk elements

### Phase 3: Combat Integration
- Elevated position combat bonuses
- Enhanced aim system for edge positions
- Turn-based integration for edge jumping
- Advanced tactical positioning mechanics

## Tactical Scenarios

### Heroic Sacrifice
```
# Live grenade in room, multiple people in proximity
jump on grenade
# Hero takes all blast damage, everyone else unharmed
# Ultimate team protection at personal cost
```

### Sniper Positioning
```
# On rooftop with edge exit
look down        # Observe street below
aim street       # Target ground level
attack bob       # Snipe from elevated position
jump off edge    # Tactical descent when position compromised
```

### Gap Crossing
```
# Rooftop-to-rooftop movement
look across north    # Check destination rooftop
jump across north    # Attempt horizontal leap
# On success: tactical repositioning
# On failure: fall to street level or take damage
```

### Gap Crossing with Rigged Traps
```
# Advanced tactical scenario - rigged edge traps
Player A: rig grenade to s     # Rig the south edge
Player B: jump across n edge   # Jump from opposite direction (north to south)
# Player B lands on south edge and triggers Player A's rigged grenade
# Rigged grenades provide area denial for gap jump landing zones
```

### Coordinated Tactics
```
# Team sniper support
Player A: aim street, attack target (from rooftop)
Player B: advance target (ground level)
Player A: jump off edge (when needed for repositioning)
```

## Design Rationale

### Why Timer-Based Explosive Sacrifice?
- **Tension creation**: Creates dramatic timing pressure
- **Skill requirement**: Must recognize and react to explosive threats
- **Integration consistency**: Uses existing grenade timer system
- **Heroic opportunity**: Limited window makes action more meaningful

### Why One-Way Edge Descent?
- **Tactical asymmetry**: Creates interesting positional advantages
- **Simple mechanics**: Avoids complex climbing systems
- **Dramatic effect**: Jumping down is more dramatic than climbing up
- **Balance consideration**: Prevents easy position abuse

### Why Gap Jumps Have Failure Risk?
- **Skill expression**: Allows character abilities to matter
- **Tactical decision**: Risk/reward for rapid repositioning
- **Dramatic tension**: Success is not guaranteed
- **Balance mechanism**: Prevents gap jumping from being too powerful

### Why Complete Damage Absorption?
- **Ultimate heroism**: Makes sacrifice truly meaningful
- **Clear mechanics**: Binary outcome (hero hurt, others safe)
- **Tactical value**: Completely removes explosive threat
- **Roleplay emphasis**: Encourages heroic character moments

## Implementation Notes & Technical Details

### Direction Mapping System
Gap jump rigged grenade detection uses opposite direction mapping to find return edges:

```python
direction_map = {
    'north': 'south', 'n': 's',
    'south': 'north', 's': 'n', 
    'east': 'west', 'e': 'w',
    'west': 'east', 'w': 'e',
    'northeast': 'southwest', 'ne': 'sw',
    'northwest': 'southeast', 'nw': 'se',
    'southeast': 'northwest', 'se': 'nw',
    'southwest': 'northeast', 'sw': 'ne',
    'up': 'down', 'u': 'd',
    'down': 'up', 'd': 'u'
}
```

### Edge Detection Enhancement
Critical fix implemented for proper edge matching - exits may have different keys and aliases:

```python
# Enhanced matching logic checks both key and aliases
key_matches = obj.key.lower() == opposite_direction
aliases_match = any(alias.lower() == opposite_direction 
                   for alias in obj.aliases.all())

if key_matches or aliases_match:
    # Found matching edge - proceed with rigged grenade check
```

**Why this matters**: Exit with key "south" and alias "s" will match when looking for direction "s", enabling proper rigged grenade detection on landing.

### Origin Room Tracking
Gap jumps now track origin room for proper return edge detection:

```python
def finalize_successful_gap_jump(self, destination, origin_room):
    # Enhanced to accept origin_room parameter for rigged grenade checking
    if origin_room:
        opposite_direction = self.get_opposite_direction(self.direction)
        # Look for edge that leads back to origin_room
```

### Debug Enhancement
Comprehensive debug logging added for troubleshooting edge detection:
- Function entry/exit logging
- Rigged grenade presence detection  
- Rigger immunity checking
- Direction matching results
- Edge detection success/failure

## Future Considerations

### Potential Enhancements
- **Climbing system**: Ways to get back to elevated positions
- **Fall damage**: Variable damage based on edge height
- **Multiple edge types**: Different tactical advantages per edge
- **Explosive shielding**: Partial protection mechanics

### Integration Opportunities
- **Skill system**: Future skills could modify jump effectiveness
- **Equipment system**: Special gear for edge traversal
- **Advanced explosives**: More complex explosive types and interactions
- **Environmental effects**: Weather/conditions affecting jumps
- **Flying mechanics**: Sky rooms naturally support flying vehicles/characters
- **Aerial combat**: Future aerial positioning and combat in sky rooms

## Open Implementation Questions

### Explosive Sacrifice Details
1. **Damage bonus**: How much extra damage should hero take for jumping on explosive?
2. **Death mechanics**: Should heroic sacrifice have special death/injury rules?
3. **Multiple explosives**: Can you jump on multiple explosives simultaneously?
4. **Combat state**: Should explosive sacrifice consume combat turn if in combat?

### Edge Exit Mechanics
1. **Height categories**: Should different edge heights have different effects?
2. **Landing positioning**: Do you land in specific proximity to anyone below?
3. **Equipment effects**: Should gear affect jumping ability or safety?
4. **Observation range**: How far can you see/aim from elevated positions?

### Gap Jump Mechanics
1. **Success calculation**: What stats determine jump success? (Motorics? Athletics?)
2. **Failure consequences**: Damage? Different destination? Equipment loss?
3. **Gap difficulty scaling**: How to categorize gap difficulty (1-5 scale)?
4. **Combat integration**: Can you gap jump while in combat? Turn cost?
5. **Motorics check**: Success on success or tie, failure means falling to fall room

### System Integration
1. **Aim system**: Should elevated positions enhance existing aim mechanics?
2. **Retreat mechanics**: Can you retreat "up" to edges, or only down from them?
3. **Grappling**: Can you grapple someone off an edge?
4. **Throwing**: Do elevated positions affect throw range/accuracy?

## Recommended Design Decisions

Based on the philosophy of heroic action and tactical depth:

1. **Damage bonus**: +10 damage for heroic sacrifice (meaningful cost)
2. **Death mechanics**: Standard death rules (heroism doesn't change lethality)  
3. **Multiple explosives**: One at a time (keeps action focused)
4. **Combat turn**: Bypasses turn system (emergency heroic action)
5. **Height effects**: Binary advantage (simple elevated vs ground)
6. **Landing position**: Random proximity if room occupied
7. **Observation**: Enhanced look/aim range from elevated positions
8. **Retreat direction**: Can retreat to edges, one-way descent only
9. **Gap success**: General Motorics stat check vs gap difficulty (success on success or tie)
10. **Gap failure**: Fall to failure_room with distance-based fall damage (rooms fallen × multiplier)
    _(2026-09-11: half-shipped, and the missing half may be deliberate. The
    distance-based damage is real — `jump.py:887-890` walks
    `follow_gravity_to_ground` and charges 5 per story, which is exactly
    what the owner-ruled movement kernel in
    `specs/PARKOUR_TEMPLATE_LIBRARY.md` §0 prescribes for falls. But
    `exit.db.fall_room` is never consulted on a gap failure: the helper
    written for it, `get_fall_room_for_gap`, had no callers and was deleted
    in #3392 (2026-09-15); the only live `fall_room` read that places a
    body is the edge-landing path in `handle_edge_fall_and_landing`
    (`world/mapping.py` reads it too, as map data). Whether gravity
    should override an authored crash
    site for gaps is an owner call, not a bug to fix from this note — see
    the Fall Room Strategy note above.)_
    _(2026-09-16: the owner call came down with #3579 and the decision is
    restated. **There is no failure_room and no multiplier.** A missed
    gap enters the air cell with no stay-up token; gravity walks the body
    down the cell's `down` chain one cell per `FALL_SECONDS_PER_CELL`;
    damage is `FALL_DAMAGE_PER_STORY` (5) x the cells actually passed,
    charged once when the column ends on something that is not air; and a
    failed leap never rolls to land, so none of it is absorbed. Gravity
    overrides any authored crash site everywhere, not just on gaps —
    `exit.db.fall_room` has no runtime reader left and retires with
    **#3580**. The recommendation's INTENT (distance-based damage rather
    than a flat number) is what shipped; its mechanism is retired.)_
11. **Gap combat**: Counts as movement action if in combat (flee-like timing)
12. **Gap difficulty**: 1-5 scale (trivial to nearly impossible)
13. **Jump syntax**: Uses direction-based syntax (`jump off north edge`, `jump across east edge`)
14. **Proximity inheritance**: Hero inherits ALL proximity relationships from explosive
15. **Framework focus**: Mechanics first, visibility/discovery enhancements in future look system


## Addendum (2026-07-28) — the edge wiring contract

Learned the hard way on the Brackett build; this is the full flight plan a
jump edge needs, or jump.py silently takes a degraded fallback:

- **Transit edge** _(rewritten 2026-09-16 to the #3579 contract; the
  2026-07-28 version required ``sky_room``, ``fall_distance`` and
  ``fall_damage``, all three now retired — the exit's destination IS the
  air cell, the column IS the distance, and
  ``FALL_DAMAGE_PER_STORY`` IS the damage)_: exit ``destination`` = the
  air cell; ``db.is_edge = True``; ``db.edge_difficulty`` optional
  (landing = Motorics vs difficulty + ``FALL_LANDING_DIFFICULTY_PER_CELL``
  × cells, default difficulty ``FALL_EDGE_DIFFICULTY_DEFAULT`` = 8).
  **The column is the rest of the flight plan and it is mandatory**: each
  air cell needs a one-way ``down`` (key ``down`` or alias ``d``) and the
  bottom one must land on something that is not air. There is no
  ``db.is_ground`` terminator any more — "not air" is the terminator. A
  column that runs out mid-air is the parked impasse (#3581): the fall
  stops cleanly in that cell, no damage, no strand.
- **Direct edge** (no open column below, e.g. clearing an oversailing
  plate): destination is simply not an air cell — one storey of
  ``FALL_DAMAGE_PER_STORY``, always lands, no roll, no traversal. _(2026-09-16:
  the old "no ``sky_room`` — flat ``fall_damage``" wording described the
  same case through two retired attributes; the branch is now just "is the
  destination air?".)_
- **Gaps**: ``is_gap`` requires ``gap_destination`` (the far same-level
  surface); omit ``is_gap`` when nothing faces the edge.
- **Named edges**: ``find_edge_exit`` resolves arbitrary exit names —
  "jump off breach edge" beats contorting a vertical drop into a cardinal.
- **Tooling caution**: ``fill_air_cell`` links any adjacent non-sky room
  as if it were a rooftop; as of this addendum it only auto-links
  walkable OUTDOOR neighbors, and interiors are never linked (the B-line
  window-edge incident). Always run the edge audit after an air build.


## Addendum (2026-09-16) — the gravity layer's known limits (#3579)

Recorded, not filed as defects. Each is a thing the layer knowingly does
not do; a reader who meets one in play should recognise it rather than
re-discover it as a bug.

- **A reload during a leap's one tick drops the leaper.** The stay-up
  token a made `jump across` carries is `ndb.airborne_token` — deliberately
  transient, so a far perch that is itself air cannot re-grant it forever.
  A reload inside that single `FALL_SECONDS_PER_CELL` window therefore
  finds a body in an air cell with no token and no record, and
  `sweep_airborne` correctly starts a fall for it. Falls survive a reload;
  a leap in flight does not. The window is one second wide.
- **Pulped legs do not stop anyone walking.** The damage placement fills
  the legs first by design — owner: "more likely to survive a long fall
  but leaving them crippled" — but the `moving` capacity's only consumer
  today is dodge. The crippling is real in the medical readout and
  invisible in movement. Wiring it up is a separate issue (the
  movement-policing substrate, `specs/roadmaps/MEDICAL_SUBSTRATE_READINESS.md`
  Phase 7) if it is wanted; nothing in #3579 depends on it.
- **Fall damage is untuned, and its knock-on is untuned twice over.**
  Every chunk that lands adds pain and, at ≥10 to a container, a bleeding
  condition — and bleeding has never been through a balance pass. So the
  real lethality of a fall is the damage number plus an unknown. All
  eleven gravity constants are registered in
  `specs/roadmaps/BALANCE_LEDGER.md` with "Tuned? No"; do not size a new
  consumer against them.
- **A fall never severs.** It lands as `blunt` damage, so no limb comes
  off however far the body drops. Deliberate — a fall crushes, it does not
  cut — but it means a lethal fall produces an intact corpse.
