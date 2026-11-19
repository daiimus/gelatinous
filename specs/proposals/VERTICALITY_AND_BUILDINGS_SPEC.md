# Verticality & Buildings Spec — floors, doors, and tenancy

How the colony goes up and goes indoors: floors, lifts, rooftops and air
cells (§1), doors with biometric locks (§2), and tenancy — permanent cube
housing (§2.5) and a paid, nightly hotel kiosk (§3). The arc unlocks **radio
Phase 2** (rooftop antennae, height-based range) and, downstream, decking's
verticality gate. The three layers are dependency-ordered: **§1 vertical
construction** (floors, stairs, lifts, rooftops) → **§2 doors** (operable,
lockable barrier faces) → **§3 tenancy** (the hotel/rental kiosk — paid,
nightly rooms beside the permanent cube housing of §2.5). Each layer can be
built on its own. Radio P2 needs only §1 + rooftops; §2–§3 can trail without
blocking it.

This builds directly on
[`SPATIAL_COORDINATE_SYSTEM_SPEC`](SPATIAL_COORDINATE_SYSTEM_SPEC.md): the
(X,Y,Z) volume, A\* pathing, the face-state model (§6.1), and jump/fall
gravity (§6).

**Design pass 2026-07-05 (user calls):** no `@stack` builder command (floors
are just up/down exits, hand-authored — §1.4); access is **BIOMETRIC, not
keys/codes/cards** (grants are files; forgery is the attack — §2.2); **B&E is
a PvE mechanic** (player-rented rooms are not player-burglary targets —
§3.2); venues carry distinguished proper names (see Venue names).

---

## 0 · Why, and what it builds on

The coordinate volume has carried a Z axis since spatial Phase 1. Three
systems are queued behind the vertical dimension:

* **Radio Phase 2** — range/coverage wants antennae with *height*; a rooftop
  transmitter should out-reach a street-level walkie.
* **Decking** — explicitly gated on the phase layer **+ verticality**
  (high-rises are the setting's texture: the corp tower you run *up*).
* **The living city** — buildings with interiors multiply authorable space
  without sprawling the street map, and private rooms create the stakes
  (safety, storage, scenes) that a persistent criminal playground needs.

**Primitives reused, not reinvented:**

| Primitive | Where | Notes |
|---|---|---|
| Integer (X,Y,Z) volume, `get_xyz`, `rooms_within`, A\* | `world/spatial` | |
| Face-state model (open / barrier / solid per room face) | spatial spec §6.1 | derived, not stored |
| Gravity: air cells, per-cell falling, edge-jump descent | `world/gravity.py` via `Room.at_object_receive`; `commands/combat/jump.py` (the verbs); `Exit.at_traverse` (the sky block) | see below |
| Exit traversal hooks (blocks, aim-lock, proximity cleanup) | `typeclasses/exits.py` | doors extend this class |
| Kiosk/vendor pattern (`ShopContainer`, prototype inventory) | `typeclasses/shopkeeper.py` | the tenancy kiosk mirrors it |
| Token pockets on NPCs/players | dispatch spec §5.2 | prices are real (below) |

**Gravity is a property of the ROOM, not of the verb (#3579).**
`Room.at_object_receive` calls `world.gravity.on_enter_air` for every
arrival. Anything in a cell flagged `db.is_sky_room is True` that cannot stay
up (`db.stays_aloft is not True`) falls one cell per `FALL_SECONDS_PER_CELL`
down the cell's `down` chain, whichever door it came in by. Damage is
`FALL_DAMAGE_PER_STORY` × cells actually passed. `fall_damage`, `sky_room`
and `fall_distance` are retired. Falling IS −Z traversal; what is still
missing is the coordinate expression of it.

**Prices are real.** `world/shop/service.py` reads `get_price` and sweeps
tokens into a till; Auntie Lin's cart sells at 2–6 tokens, and the Butcher
and the snailery run the same loop.

---

## 1 · Layer 1 — vertical construction

**A floor is just a room at `z+1` connected by the right kind of exit.** No
new room typeclass; verticality is authoring + two exit idioms + one builder
convenience.

### 1.1 · Stairs & shafts

* **Stairwell** — a plain exit pair (`up`/`down` aliases) between `(x,y,z)`
  and `(x,y,z±1)`. Nothing new mechanically; the A\* pathfinder already walks
  any exit edge, so NPC dispatch/pursuit climbs stairs for free. A stair
  room is typed `stairwell` (#3757): crowd prose treats it like the
  tenement around it, and the glance from a neighbouring room looks into it
  (#3759). An `up` or `down` exit reads without "to the" ("continues up (u)
  and down (d)").
* **Lift/elevator — THE CAR MODEL (DECIDED 2026-07-10, user call).** It
  replaces the warp-exit-per-floor v1 the spec first proposed. Code:
  `typeclasses/elevator.py` — `ElevatorCar`, `ElevatorDoorExit`, landing call
  buttons via `press`/`call`, `db.shaft_xy`, and `db.floor_locks` consumed by
  `_floor_permitted` and the pathfinder. A real elevator is three parts:
  1. **Landings** — the ordinary rooms the doors open onto, one per
     served floor (the Constabulary prototype: the LOBBY #4936 and the
     2F SECURE CORRIDOR #4960 — the doors sit in their east walls). Each
     landing has an `elevator` exit whose destination is always THE CAR —
     but traversal is gated on the car being AT that floor ("The elevator
     doors are shut. Press the call button."). **The SHAFT is real too
     (refined 2026-07-10, user call):** a stacked column of sealed rooms
     (#4939/#4957 at (9,-18,z), joined up/down) that the car physically
     occupies — `db.shaft_xy` parks the car's grid position at
     (shaft_x, shaft_y, landing_z), never in a landing's cell. No
     pedestrian exits touch the shaft; prying the doors to reach it is
     future B&E texture. Shaft rooms carry their OWN room type
     (`ShaftRoom`, `db.type="shaft"` — decided 2026-07-10): building-
     agnostic for every future lift, "The shaft continues down" prose,
     and the anchor for future climb/fall/car-hazard mechanics.
  2. **The CAR** — a real room. Passengers stand in it, talk in it, fight
     in it — a moving room where scenes happen. Its single `out` exit is
     **re-pointed by the controller** to the current landing; it refuses
     mid-travel ("The car is moving. Best wait for the doors.").
  3. **The CONTROLLER** is the car itself: attributes on `ElevatorCar`
     (`db.floors` as ordered [landing, label] pairs, `db.current_floor`,
     `db.moving`, `db.target_floor`, `db.call_queue`). `press <floor>` inside
     the car; a **call button object at each landing** (`press call`)
     summons it. Travel is timed with `delay` (3 s of doors plus 6 s per
     floor); a ride caught by a reload ends where it was headed (`at_init`),
     with door messages at both ends and in the car. The car's position is
     honest world-state: you can miss it, hold it, or corner someone in it.
     A press while the car is moving lights the button and joins a queue:
     first in, first served, duplicates dropped, kept across a reload. The
     car stands open 5 s at each stop before serving the next. The car
     itself refuses anyone stepping in from a landing it is not docked at,
     whatever exit leads in (`ElevatorCar.at_pre_object_receive`). `call`
     at a landing and `press <floor>` in the car are the verbs NPC travel
     uses too, and the pathfinder routes a rider only to floors their
     sleeve may press. If a `floor_locks` key matches no floor label, the
     car refuses every floor not listed in `floor_locks` until the labels
     and keys agree (`_floor_permitted`).

  **Why this over the alternatives** (warp-exit-per-floor, or a bare
  timed exit): only the car model makes the elevator's whereabouts a fact
  in the world — sabotage, ambushes, and "hold the door" all need the car
  to be somewhere. No channeled action is needed: the CAR moves, not the
  actor (riders stay free).

  **Security seam:** per-floor access rides the §2.2 biometric model — a
  secured floor's button checks the presser's sleeve against a grant file
  (the 2F landing's amber reader is the fiction already in place).
  Sabotage seams reserved: cut power = car stuck; the grant file =
  decking. Call buttons are vandalizable objects.

  **The crane car** (`typeclasses/rooms.py` `CraneContainer`, the Boiler
  Run crane) is a second moving-room lift, open to the air: a room typed
  `rooftop` that its operator moves up and down one grid column through
  `move_to_level`. Its four doors are permanent; what lies beyond each one
  changes with the car's height (#3560).
* **Ladders/fire escapes** — stairwell idiom with different messaging;
  candidate for `climb`-gated traversal so they're slower/riskier under
  pursuit. There is no `climb` command and no exit keyed `climb`; nothing
  gates on climbing yet. Climbing hooks are the named next mechanic (four
  decisions defer to it).

### 1.2 · Interior ↔ exterior seam

A building's ground floor connects to the street by an ordinary exit (`enter
the Aster Hotel`). Interior rooms are full rooms — five-senses layers,
weather *excluded* (interior flag already exists via room typeclass
behaviour), crowd optional. Coordinates continue *through* the building:
the lobby at `(12,4,0)`, third floor at `(12,4,3)`. The face-state model
(spatial §6.1) then gives every interior wall/floor for free — which is what
makes future breaching (blow a hole in the hotel wall) a flip of one edge,
not a rebuild.

### 1.3 · Rooftops — what radio P2 actually needs

The top of every stack is a **rooftop room**: exterior (weather applies),
marked `db.outside = True` + `db.type = "rooftop"` (the `SkyRoom` docstring
in `typeclasses/rooms.py` states the rule; nothing reads a `db.is_rooftop`
flag, so setting one does nothing), edge exits eligible for the existing
jump/fall system. Jumping between adjacent rooftops is the edge-jump mechanic
pointed at `z>0` — it already handles descent and fall damage; the −Z chain
is `world/gravity.py`: anything that arrives in a room flagged
`db.is_sky_room` and cannot stay up falls down each air cell's `down` exit,
one cell per tick.

Radio P2's seam: an **antenna is an object placed in a rooftop room**, and
its effective height is simply `room.xyz[2]`. The range model (P2's problem,
not this spec's) reads height off coordinates; this spec only owes it
rooftops that *have* correct Z. The radio range model is `world/radio.py`,
which adds reach per z-level of the transmitting room.

### 1.4 · Builder authoring — plain exits, by hand

**Decided (2026-07-05): no `@stack` command.** A floor is a room and a
stairwell is an up/down exit pair — builders author them exactly like any
other room and exit, seeding coordinates with the existing `@coordseed`
flow. The spatial spec's stance holds: coordinates are the data model,
hand-authoring is the authoring model, and vertical construction needs no
special tooling.

### 1.5 · Air cells, edges and gaps

**VERTICAL DOCTRINE (2026-07-25, owner-set):**

* Open plates (roofs/decks) are STRIP rooms tiling their footprint.
* Spine links are plain exits, and every other applicable direction (incl.
  diagonals) is a wired EDGE.
* Air cells are deliberate negative space (fall lanes, future flight).
* Every air build ends with the edge audit ("edges accountable").

**`@airfill` (2026-07-13, #1210 — the parkour substrate)** generates aerial
transit cells over the colony from the hand-proven 'In the Air' #190 atom:

* each cell is a `SkyRoom` (jump-only, no exit display, civilians excluded,
  crowd 0) with a one-way `down` fall edge;
* plain exits run from the cell onto adjacent rooftops;
* an `is_edge` exit runs from each rooftop into the cell; it is also
  `is_gap`, with its `gap_destination` written, only where another walkable
  surface stands exactly one cell across.

Links run north, south, east and west only; the lattice never links
diagonals. Eligibility: empty cell, ≥1 NON-sky same-z neighbour (sky never
seeds — re-runs can't balloon), occupied cell directly below (gravity needs
a delivery address). `/check` dry-runs; bounding box limits; 300-cell safety
cap; never stomps authored exits. Build up, then `@airfill <z>` stitches the
sky.

**The edge audit** is `@airfill/audit <z>` (`commands/CmdBuildTools.py`),
read-only. It lists:

* walkable surfaces beside air with no edge into it (north, south, east and
  west only);
* gaps whose far perch is missing, not a walkable surface, or not one cell
  across;
* air cells with no `down`.

A room carrying `db.no_edge = "<reason>"` is a deliberate omission and the
audit skips it.

**GREENHAUS DOCTRINE (2026-08-24/25, builds 055–065 — the farm towers, air
lattice, and cistern saga; owner-ratified):**

1. **Structures never stand over walkable cells** — only AIR crosses a
   street (the Kaspar-connector idiom). Landmarks on tall legs with a lane
   beneath are the sanctioned exception (Overflow Alley under Cistern
   No. 3).
2. **Gap crossings must be straight collinear lines** — a jump's momentum
   goes straight; perch → air → far-perch must satisfy
   `perch+Δ == air && air+Δ == far-perch` (diagonals included).
3. **A gap exit carries two parts** (canon: the Halcyon↔Antenna crossing):
   `destination` = the air cell (jump-off descents), `db.gap_destination` =
   the far perch (where jump-across LANDS). Nothing reads `db.sky_room`
   (#3579). A gap with no perch is refused on the roof
   (`commands/combat/jump.py`), so it is a build error, and
   `@airfill/audit` reports it.
4. Air columns are bare `SkyRoom`s; a pure descent entry is `is_edge` only,
   its destination the airspace whose fall line lands where you intend (the
   Constabulary entry falls to the West Lawn INSIDE the fence).
5. Demolitions EVACUATE occupants first; audits are queries, not eyeballs
   (overlap: room z>0, type≠sky, over z0 type ∈ {market,street,alley}; gap
   wiring: is_gap without gap_destination pointing at a sky destination =
   broken).

---

## 2 · Layer 2 — doors

**A door is an exit with state.** In face-state terms: an exit edge is
permanently *open* and a missing edge is permanently *barrier*; a door is an
edge that can be **either, at runtime** — the first operable face.

### 2.1 · The state model

**The door IS the exit (user call, 2026-07-10).** `typeclasses/doors.py`
`DoorExit(Exit)` with a mirrored twin (Evennia exits are one-way; a door is
the *pair*, state shared so both sides agree): open/closed/locked, with a
`broken` seam reserved (§2.4). Passage requires the door OPEN — open/close
are explicit verbs, and walking never changes state (refined 2026-07-10 per
user).

| State | Traversal | Sight/sound through |
|---|---|---|
| **open** | free | full (an open doorway) |
| **closed** | blocked (politely: "the door is closed") | muffled sound only (§2.3; 📋 UNBUILT (no issue)) |
| **locked** | blocked | as closed |

Commands, all real player verbs: `open/close <door>`, `lock/unlock <door>`
(your sleeve must be on the door's grant file, §2.2), `knock <door>` (heard on
the far side, attributed by sound only). The builder command is `@door`:
`/grant`, `/revoke` and `/list` manage the grant file; `/lock`, `/unlock`,
`/open` and `/close` force the door's state.

**Spring latch — `db.door_autolock` (2026-07-11, user call):** closing
re-engages the lock, no grant needed — anyone can RESTORE security, only
granted sleeves can remove it. Cube doors ship with it.

**NPCs use the same verbs** (the level-playing-field mandate) — which means
dispatch/pursuit must *fail politely* at a locked door rather than path
through it. The A\* pathfinder treats **locked doors as blocked edges for any
traverser whose sleeve is not granted** (`DoorExit.door_blocks` in
`typeclasses/doors.py`, a per-traverser edge filter that the pathfinder in
`world/spatial/pathfind.py` consults, the same seam the phase layer already
reserves in spatial §8). `door_blocks` is the grant
check: open passes; closed-unlocked passes anyone; locked passes granted
sleeves only. A closed but unlocked door stays passable because the travel
layer issues the REAL `open` verb before stepping through it en route (NPCs
learned `open`, 2026-07-12) — reader flashes, room messages, and grant checks
all apply; a bounce re-pathfinds next tick. Security units hold grants on the
Constabulary's own doors.

Grant files live in `world/access.py`; the elevator's `db.floor_locks`
consumes the same grant model (§1.1).

### 2.2 · Biometric access — everything is a file (DECIDED 2026-07-05)

**No keys, no codes, no cards.** Players shouldn't have to memorize
combinations or retain key items; the colony's locks read **biometrics**.
No items, no memorized codes; forgery is the attack.

* **The biometric IS the sleeve.** The identity system already carries the
  canonical body signature (`sleeve_uid` / the identity-signature spine) —
  a door doesn't need new sensing, it needs a *read* of the identity the
  game already tracks. Present at the door; the lock checks your sleeve
  against its grant file.
* **The grant is a FILE on the lock** (`db.access_grants`) — entries of
  `{sleeve, until, issued_by}`. Readable, falsifiable, erasable when
  decking arrives; honest attributes until then. The lock is the first
  everyday device whose behaviour is entirely record-driven.
* **The personal credential is a FILE on the cyberbrain** — the roadmap
  already marks cyberbrains as hackable/transferable/wipeable memory
  stores (NPC_MEMORY_AND_IDENTITY_SPEC affordances); an access credential
  is the first mundane thing worth storing there.
* **The attack is FORGERY, not theft.** You don't steal a key — you present
  **someone else's biometrics**: spoofing a sleeve signature rides the
  identity/disguise machinery (a deep-enough disguise, a harvested
  credential, or — later — a decked falsification of the grant file
  itself). Depth and counterplay belong to the identity and decking specs;
  this spec only owes them a lock that checks a signature against a record.

Locks live on the DOOR, not the room, so one room can have a locked front
door and an openable window-exit (breach-in-waiting).

### 2.3 · Privacy is perception-gated, honestly

A closed door actually *does something*: room broadcast stops crossing it.
Sight is gated: a closed door hides the far room from `look <dir>` and from
the room's glance (`DoorExit.blocks_sight`). 📋 UNBUILT (no issue): muffled
sound. No sound crosses between rooms yet, so there is nothing for a door to
muffle; when a cross-room sound layer lands, a closed door is its gate.
Speech/sound: muffled (existence, not content — "muffled voices beyond the
door"), consistent with the hearing rails. Sight: none. This is what makes a
rented room *private* — and it must integrate with the five-senses room
layers and the whisper/say pipeline rather than bolt on a special case.
(Follow/escort: a closed door breaks the follow chain politely — the door
question the trust spec deferred.)

**Door sound model — DECIDED (2026-07-05): muffled-existence-only, full
stop.** A closed door leaks the fact of sound, never content; no perception
checks, no listen-at-door verb in this spec. Eavesdropping arrives later as
**chrome**: a cybernetic-ear **sound-amplification module** granting
`/listen` at adjacent exits (doors included) — the existing augment grammar
(CYBER_EAR hardpoint + module ability, the JAWZ//blindsight pattern),
belonging to the augments spec, not this one.

### 2.4 · The breach seam

**Masts are breachable (2026-07-11, #1164):** `sabotage`/`repair` channeled
verbs act on `db.breachable` structures. **Door-forcing stays reserved by
user call: masts were the point, doors are a different fantasy.**

Forcing a door = the face-state flip the spatial spec reserves for
destruction: `locked → open (broken)`. A broken door can't re-close until
repaired. Needs the damage-state model the spatial spec already defers;
this spec just requires the door state enum to include `broken` so the
future breach has a landing slot. Lockpicking-analogues (biometric
spoofing hardware, forced-entry tools) likewise reserved. Per §3.2,
breach targeting is **PvE-directed**: NPC doors are breachable, player
tenants' doors are not (v1).

### 2.5 · Cube hotels & the housing guarantee (user design, 2026-07-11)

**The rental credit:** every person carries ONE — it *guarantees* one
**permanent residence**. Not money; a right. Claiming spends nothing.

* **The tenancy IS the grant file** (§2.2): permanent residence = a
  grant with `until=None` on the cube's DoorExit; the resident's
  sleeve opens/locks/unlocks it like any granted door. No new lock
  machinery. `cube.db.resident` = occupancy record;
  `char.db.residence` = the credit's spend.
* **Rental terminal** (`typeclasses/terminals.py RentalTerminal`,
  aliases `kiosk`, `db.cubes`): operated through the PRESS grammar
  (user call 2026-07-11 — one interaction language for every machine):
  `press kiosk` = status/vacancies, `press rent on kiosk` = register,
  `press confirm on kiosk` = complete a relocation. `push` aliases
  `press`. `press rent <unit> on kiosk` claims a named unit (`3B`,
  `R0-01`); the board prints labels the kiosk accepts back
  (`world/rental.py` `unit_label`, `unit_matches`). Any claim that changes
  an existing registration, including a move to another unit on the same
  board, asks for `press confirm [<unit>] on kiosk`. A tenant who is
  deleted, or an archived husk, loses the cube the moment anyone asks
  after it (`_prune_dead_tenancy`). Looking at a unit's corridor-side door
  shows its tenancy: "Occupied.", "Vacant." or "Being vacated."
  (`DoorExit._residence_status`). Terminals are the decking substrate's
  physical layer — when the net lands, the buttons stay and the records
  become files.
* **Relocation window** (`world/rental.py RELOCATION_WINDOW`, 48h):
  claiming elsewhere vacates the old cube immediately but its door
  answers the mover's sleeve for the window — time to move your
  things — then fails closed on its own (`world.access` honours
  `until`). A vacated cube stays OFF the market until the window
  fully expires: no tenant overlaps.
* **`memory`** renders an @stats-format MNEMONIC RECALL REPORT
  (2026-07-11): KNOWN ASSOCIATES + REGISTERED RESIDENCE dossier — unit,
  building/vehicle name (`cube.db.residence_building`), street/port of
  origin (`cube.db.residence_origin`), registration age, live
  relocation-handover window. **Builders MUST set both residence attrs on
  new cubes.**
* **First install: the Queen of Cups** (Pessoa Street, lobby #1917,
  stairwell column at (-2,-14,z)): per level a RACK room tunneled
  south of the stairwell with cubes w/sw/s/se/e named `R<level>-0<n>`
  (w=01 … e=05). Ground rack carries the full five too (user call):
  R0-02/03/04 sit **half-sunk below street grade at z=-1**, their berths
  directly under Kaspar Street's sidewalk — the grid stays honest, no cell
  overlap. The Queen stands to z12 with Racks 0–11: **60 cubes** on the
  terminal (#1774). Rooms typed `cube hotel` (crowd modifier
  pre-existing). Belongings left after an expired window are the next
  tenant's problem/prize — flophouse rules.
* **The Brackett Arms** runs leases with a pick-your-unit kiosk; the whole
  upper tower has doors and leases, about 134 (#1754).

---

## 3 · Layer 3 — tenancy: the hotel / rental kiosk — 📋 UNBUILT (no issue)

**A lease is a timed biometric grant sold by a machine.** Composes §1 + §2;
adds no new mechanics beyond time. The by-the-night, token-priced hotel
tenancy this layer proposes is unbuilt.

*Overturned interface:* the first sketch had a "keycode" grant and the typed
commands `use kiosk` / `rent 1 for 3 nights`. Biometric-only access (§2.2,
decided 2026-07-05) and the `press` grammar (§2.5, user call 2026-07-11 — one
interaction language for every machine) replace both. `commands/CmdGraffiti.py`
owns `press`/`push`/`call`; `RentalTerminal` is driven through `at_press`.

### 3.1 · The kiosk

A `RentalKiosk` in the hotel lobby — the AutoDoc/vendor interaction pattern
(menu-driven, tokens in, service out). What the kiosk shows:

```
  THE ASTER — ROOMS BY THE NIGHT
  1. Single room — 50 tokens/night
  2. ... (rooms currently available)

  150 tokens. The kiosk scans you. Room 304 knows your body now.
```

(150 tokens = three nights at 50.)

* Payment in **tokens** — a recurring sink beside shop prices
  (mugging pockets ↔ paying rent closes an actual loop).
* The grant: the kiosk **enrolls your biometric** (§2.2) — writes a
  `{sleeve, until, issued_by}` entry to the room's lock file. Nothing to
  carry, nothing to memorize; the kiosk reads the sleeve standing at it,
  same as the door will.
* **Expiry**: at lease end the lock's grant lapses (record-driven, checked
  at the door — no sweeper needed to *enforce*). A housekeeping sweep
  (director-side, like the population upkeep pattern) later resets expired
  rooms: unclaimed possessions to a lost-and-found bin behind the desk
  (nothing silently deleted), door re-locked, room re-listed.

### 3.2 · What a rented room IS

* **Private** — closed/locked door = real perception privacy (§2.3). The
  first place a character can sleep/log out with stakes lowered, stage a
  scene, or stash goods.
* **B&E is a PvE mechanic (DECIDED 2026-07-05, revisitable).** Breaking
  and entering points at **NPC-held spaces** — corp floors, NPC apartments,
  the hotel's *other* rooms — not at player tenants: a player's rented room
  is not a target other players can breach in v1. (User is on the fence
  long-term; the mechanics don't preclude flipping this later — it's a
  target-eligibility rule, not an architecture.) A rented room is therefore
  genuinely safe storage against other players, while the world's NPC
  interiors become the burglary playground.
* **Not permanent** — a nightly lease lapses. Permanent housing is the
  housing guarantee (§2.5): one cube per person, claimed free. This kiosk
  would add paid, short-stay rooms beside it.

### 3.3 · NPC tenancy (seam)

Civilian NPCs renting rooms (the director paying tokens into the same kiosk)
would make hotels *alive* and give burglary targets — deferred, but the
kiosk API (`lease(room, who, nights)`) is written NPC-agnostic so the
director can call it later without changes.

---

## 4 · What this unlocks (consumers, not obligations)

* **Radio Phase 2** — rooftop antennae with honest heights (§1.3); range
  model reads Z. The *only* hard dependency this spec owes radio.
* **Decking** — verticality gate satisfied; a door's grant file
  (`db.access_grants`, §2.2) is the first record decking can forge or erase.
* **Stealth/crime** — locked doors, break-ins, rooftop approaches, fire
  escapes; heat/witness system gains interior/exterior texture.
* **Trust/consent** — private space makes consent boundaries spatial
  (invite into room ↔ trust gate), the interplay the trust spec anticipated.
* **Economy** — rent would be a recurring token sink beside shop prices;
  pockets → rent → meaning.

---

## Venue names (DECIDED 2026-07-05)

Venues carry distinguished proper names in "The Aster" register (NOT the
AWE/PAM gear-brand schema — that's for manufactured goods). The hotel keeps a
name of this shape, and **the bar should receive its proper name in the same
pass**.

---

## 5 · Unbuilt, in order

1. **§2.3 sound gating** — muffled sound through a closed door. 📋 UNBUILT
   (no issue); waits on a cross-room sound layer.
2. **§3 kiosk**: lease flow, expiry, housekeeping sweep. The Aster opens for
   business. 📋 UNBUILT (no issue).
3. *(Later, other specs)*: breach/lockpick (§2.4, reserved), NPC tenancy
   (§3.3, deferred).

Also reserved or future, where they stand: climbing hooks (§1.1, the named
next mechanic); prying the lift doors into the shaft, and climb/fall/car
hazards in the shaft (§1.1); lift sabotage — cut power, the grant file as a
decking target, vandalized call buttons (§1.1); eavesdropping chrome (§2.3,
augments spec); the coordinate expression of falling (§0).

---

## 6 · Open questions — not decided

* **Sky-room interplay** — do building interiors above z=0 need `passable`
  /floor semantics per spatial §6 generalization *now* (breach a floor →
  fall through), or defer floor-breaching entirely? Proposal: defer;
  floors are implicit barriers until the destruction spec.
* **Pricing** — 50 tokens/night against 100–500-token pockets: is one
  mugging ≈ one-to-three nights the intended economy scale?
* **B&E scope** — decided PvE-directed for v1 (§3.2), user on the fence
  long-term; revisit after tenancy plays.
* **Diagonal edges** — should diagonal neighbours of an air cell get wired
  edges, as the 2026-07-25 vertical doctrine says, or does the lattice stay
  north/south/east/west only, as `@airfill` and its audit build it?

---

## Related documents

* [`SPATIAL_COORDINATE_SYSTEM_SPEC`](SPATIAL_COORDINATE_SYSTEM_SPEC.md) —
  the volume, face-state model (§6.1), gravity (§6), phase-layer seam (§8).
* NPC_MEMORY_AND_IDENTITY_SPEC — cyberbrain memory stores (§2.2).
* The trust, identity, decking, augments and destruction specs — the
  consumers named in §2.2, §2.3, §2.4 and §4.
