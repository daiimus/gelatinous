# Verticality & Buildings Spec — floors, doors, and tenancy

> **Status:** 📋 **PROPOSAL (2026-07-05) — design only, nothing built.** The
> arc that unlocks **radio Phase 2** (rooftop antennae, height-based range)
> and, downstream, decking's verticality gate. Three layers, each
> independently shippable, dependency-ordered: **§1 vertical construction**
> (floors, stairs, lifts, rooftops) → **§2 doors** (operable, lockable
> barrier faces) → **§3 tenancy** (the hotel/rental kiosk — the first real
> token sink and the first player-held private space). Radio P2 needs only
> §1 + rooftops; §2–§3 can trail without blocking it. Builds directly on
> [`SPATIAL_COORDINATE_SYSTEM_SPEC`](SPATIAL_COORDINATE_SYSTEM_SPEC.md)
> (Phases 1–2 LIVE: the (X,Y,Z) volume, A\* pathing, face-state model §6.1,
> jump/fall gravity §6). **Design pass 2026-07-05 (user calls):** no `@stack`
> builder command (floors are just up/down exits, hand-authored); access is
> **BIOMETRIC, not keys/codes/cards** (grants are files; forgery is the
> attack — §2.2); **B&E is a PvE mechanic** (player-rented rooms are not
> player-burglary targets — §3.2); venues carry distinguished proper names
> ("The Aster" register — and the bar should be named in the same pass).

---

## 0 · Why, and what already exists

The colony is flat. 309 rooms sit almost entirely at `z=0` of a coordinate
volume that has carried a Z axis since spatial Phase 1 — the vertical
dimension is *paid for and unused*. Meanwhile three systems are queued behind
it:

* **Radio Phase 2** — range/coverage wants antennae with *height*; a rooftop
  transmitter should out-reach a street-level walkie.
* **Decking** — explicitly gated on the phase layer **+ verticality**
  (high-rises are the setting's texture: the corp tower you run *up*).
* **The living city** — buildings with interiors multiply authorable space
  without sprawling the street map, and private rooms create the stakes
  (safety, storage, scenes) that a persistent criminal playground needs.

**Already live, reused not reinvented:**

| Primitive | Where | State |
|---|---|---|
| Integer (X,Y,Z) volume, `get_xyz`, `rooms_within`, A\* | `world/spatial` | ✅ live |
| Face-state model (open / barrier / solid per room face) | spatial spec §6.1 | ✅ designed, derived not stored |
| Gravity: sky rooms, `fall_damage`, edge-jump descent | `commands/combat/jump.py`, `Exit.at_traverse` | ✅ live (to be generalized per spatial §6) |
| Exit traversal hooks (blocks, aim-lock, proximity cleanup) | `typeclasses/exits.py` | ✅ live — doors extend this class |
| Kiosk/vendor pattern (`ShopContainer`, prototype inventory) | `typeclasses/shopkeeper.py` | ✅ live — tenancy kiosk mirrors it |
| Token pockets on NPCs/players | dispatch spec §5.2 | ✅ live (but nothing to *spend* on — everything is priced 0) |

---

## 1 · Layer 1 — vertical construction

**A floor is just a room at `z+1` connected by the right kind of exit.** No
new room typeclass; verticality is authoring + two exit idioms + one builder
convenience.

### 1.1 · Stairs & shafts

* **Stairwell** — a plain exit pair (`up`/`down` aliases) between `(x,y,z)`
  and `(x,y,z±1)`. Nothing new mechanically; the A\* pathfinder already walks
  any exit edge, so NPC dispatch/pursuit climbs stairs for free.
* **Lift/elevator — THE CAR MODEL (DECIDED 2026-07-10, supersedes the
  warp-exit v1; resolves open question 1).** A real elevator is three
  parts:
  1. **Landings** — the ordinary rooms the doors open onto, one per
     served floor (the Constabulary prototype: the LOBBY #4936 and the
     2F SECURE CORRIDOR #4960 — the doors sit in their east walls). Each
     landing has an `elevator` exit whose destination is always THE CAR —
     but traversal is gated on the car being AT that floor ("The doors
     are shut. Press the call button."). **The SHAFT is real too
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
     mid-travel ("The car is moving.").
  3. **The CONTROLLER** — script state: `floors` (ordered landings),
     `current`, `moving`. `press <floor>` inside the car; a **call
     button object at each landing** (`press call`) summons it. Motion is
     script-timed (~6s per floor + door dwell), with door messages at both
     ends and in the car. The car's position is honest world-state: you
     can miss it, hold it, or corner someone in it.

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
* **Ladders/fire escapes** — stairwell idiom with different messaging;
  candidate for `climb`-gated traversal (existing climb verb) so they're
  slower/riskier under pursuit.

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
`db.is_rooftop = True`, edge exits eligible for the existing jump/fall
system (jumping between adjacent rooftops = the edge-jump mechanic pointed
at `z>0` — it already handles descent and fall damage; the -Z chain through
`passable` sky rooms is spatial §6's generalization, built here as its first
consumer).

Radio P2's seam: an **antenna is an object placed in a rooftop room**, and
its effective height is simply `room.xyz[2]`. The range model (P2's problem,
not this spec's) reads height off coordinates; this spec only owes it
rooftops that *have* correct Z.

### 1.4 · Builder authoring — plain exits, by hand

**Decided (2026-07-05): no `@stack` command.** A floor is a room and a
stairwell is an up/down exit pair — builders author them exactly like any
other room and exit, seeding coordinates with the existing `@coordseed`
flow. The spatial spec's stance holds: coordinates are the data model,
hand-authoring is the authoring model, and vertical construction needs no
special tooling.

---

## 2 · Layer 2 — doors

**A door is an exit with state.** In face-state terms: today an exit edge is
permanently *open* and a missing edge is permanently *barrier*; a door is an
edge that can be **either, at runtime** — the first operable face.

### 2.1 · The state model — ✅ SHIPPED 2026-07-10 (§2.1 + §2.2; the
door IS the exit, per user call). `typeclasses/doors.py DoorExit`
(mirrored pair, open/closed/locked, broken seam reserved; passage
requires the door OPEN — open/close are explicit verbs, walking never
changes state, refined 2026-07-10 per user), player verbs
`open/close/lock/unlock/knock`, builder `@door` (+/grant /revoke /list
/force), **`memory` renders an @stats-format MNEMONIC RECALL REPORT (2026-07-11): KNOWN ASSOCIATES + REGISTERED RESIDENCE dossier — unit, building/vehicle name (`cube.db.residence_building`), street/port of origin (`cube.db.residence_origin`), registration age, live relocation-handover window; builders MUST set both residence attrs on new cubes**, **`db.door_autolock` spring latch (2026-07-11, user call:
closing re-engages the lock, no grant needed — anyone can RESTORE
security, only granted sleeves can remove it; cube doors ship with
it)**, grant files in `world/access.py`, pathfinder blocked-edge
filter live in `world/spatial/pathfind.py`, and the elevator's
`db.floor_locks` consumes the same grant model. §2.3 sound-muffling
awaits a cross-room sound layer (none exists yet — closed doors are
already the gate when it lands); §2.4 breach stays reserved.
Follow-on owed: **NPCs learn the `open` verb** — refines the
pathfinder's any-not-open-door blocked edge back to a grant check and
lets granted NPCs (Petra) badge into their own offices; the seam is
commented in `DoorExit.door_blocks`.

`DoorExit(Exit)` with a mirrored twin (Evennia exits are one-way; a door is
the *pair*, state shared so both sides agree):

| State | Traversal | Sight/sound through |
|---|---|---|
| **open** | free | full (an open doorway) |
| **closed** | blocked (politely: "the door is closed") | muffled sound only (§2.3) |
| **locked** | blocked | as closed |

Commands, all real player verbs: `open/close <door>`, `lock/unlock <door>`
(needs the key/code), `knock <door>` (heard on the far side, attributed by
sound only). NPCs use the same verbs (the level-playing-field mandate) —
which means dispatch/pursuit must *fail politely* at a locked door rather
than path through it: the A\* pathfinder treats **locked doors as blocked
edges for NPCs without the key** (a per-traverser edge filter, same seam the
phase layer already reserves in spatial §8).

### 2.2 · Biometric access — everything is a file (DECIDED 2026-07-05)

**No keys, no codes, no cards.** Players shouldn't have to memorize
combinations or retain key items; the colony's locks read **biometrics**.

* **The biometric IS the sleeve.** The identity system already carries the
  canonical body signature (`sleeve_uid` / the identity-signature spine) —
  a door doesn't need new sensing, it needs a *read* of the identity the
  game already tracks. Present at the door; the lock checks your sleeve
  against its grant file.
* **The grant is a FILE on the lock** — entries of
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
Speech/sound: muffled (existence, not content — "muffled voices beyond the
door"), consistent with the hearing rails. Sight: none. This is what makes a
rented room *private* — and it must integrate with the five-senses room
layers and the whisper/say pipeline rather than bolt on a special case.
(Follow/escort: a closed door breaks the follow chain politely — the door
question the trust spec deferred.)

### 2.5 · Cube hotels & the housing guarantee — ✅ SHIPPED 2026-07-11 (user design)

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
  `press`. Terminals are the decking substrate's physical layer —
  when the net lands, the buttons stay and the records become files.
* **Relocation window** (`world/rental.py RELOCATION_WINDOW`, 48h):
  claiming elsewhere vacates the old cube immediately but its door
  answers the mover's sleeve for the window — time to move your
  things — then fails closed on its own (`world.access` honours
  `until`). A vacated cube stays OFF the market until the window
  fully expires: no tenant overlaps.
* **First install: the Queen of Cups** (Pessoa Street, lobby #1917,
  stairwell column at (-2,-14,z)): per level a RACK room tunneled
  south of the stairwell with cubes w/sw/s/se/e named `R<level>-0<n>`
  (w=01 … e=05). Ground rack carries the full
  five too (user call): R0-02/03/04 sit **half-sunk below street
  grade at z=-1**, their berths directly under Kaspar Street's
  sidewalk — the grid stays honest, no cell overlap. **25 cubes**
  total. Rooms typed `cube hotel` (crowd modifier
  pre-existing). Belongings left after an expired window are the next
  tenant's problem/prize — flophouse rules.

### 2.4 · The breach seam (MASTS SHIPPED 2026-07-11 #1164 — `sabotage`/`repair` channeled verbs on `db.breachable` structures; door-forcing stays reserved by user call: masts were the point, doors are a different fantasy)

Forcing a door = the face-state flip the spatial spec reserves for
destruction: `locked → open (broken)`. A broken door can't re-close until
repaired. Needs the damage-state model the spatial spec already defers;
this spec just requires the door state enum to include `broken` so the
future breach has a landing slot. Lockpicking-analogues (biometric
spoofing hardware, forced-entry tools) likewise reserved. Per §3.2,
breach targeting is **PvE-directed**: NPC doors are breachable, player
tenants' doors are not (v1).

---

## 3 · Layer 3 — tenancy: the hotel / rental kiosk

**A lease is a timed keycode grant sold by a machine.** Composes §1 + §2;
adds no new mechanics beyond time.

### 3.1 · The kiosk

A `RentalKiosk` in the hotel lobby — the AutoDoc/vendor interaction pattern
(menu-driven, tokens in, service out):

```
> use kiosk
  THE ASTER — ROOMS BY THE NIGHT
  1. Single room — 50 tokens/night
  2. ... (rooms currently available)
> rent 1 for 3 nights
  150 tokens. The kiosk scans you. Room 304 knows your body now.
```

* Payment in **tokens** — the first real sink; prices finally mean something
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
* **Not permanent** — leases lapse; long-term housing is a later, separate
  decision (this kiosk deliberately rents by the night to stay small).

### 3.3 · NPC tenancy (seam)

Civilian NPCs renting rooms (the director paying tokens into the same kiosk)
would make hotels *alive* and give burglary targets — deferred, but the
kiosk API (`lease(room, who, nights)`) is written NPC-agnostic so the
director can call it later without changes.

---

## 4 · What this unlocks (consumers, not obligations)

* **Radio Phase 2** — rooftop antennae with honest heights (§1.3); range
  model reads Z. The *only* hard dependency this spec owes radio.
* **Decking** — verticality gate satisfied; door keycodes become the first
  physical files (§2.2).
* **Stealth/crime** — locked doors, break-ins, rooftop approaches, fire
  escapes; heat/witness system gains interior/exterior texture.
* **Trust/consent** — private space makes consent boundaries spatial
  (invite into room ↔ trust gate), the interplay the trust spec anticipated.
* **Economy** — first token sink; pockets → rent → meaning.

---

## 5 · Build ladder (each rung shippable, in order)

1. **§1 construction**: `@stack`, stairwell idiom, rooftop flag, one real
   building authored (the hotel shell, undoored) + rooftop. *(Unblocks radio
   P2 immediately.)*
2. **§2 doors**: `DoorExit` + verbs + key/code grants + perception gating +
   NPC pathfinder edge filter. Retrofit the hotel.
3. **§3 kiosk**: lease flow, keycard, expiry, housekeeping sweep. The Aster
   opens for business.
4. *(Later, other specs)*: breach/lockpick, moving lift cars, NPC tenancy,
   long-term housing, radio P2 range model itself.

---

## 6 · Open questions (user calls wanted before build)

1. ~~Lift v1~~ — **RESOLVED (2026-07-10): the moving CAR** (user call,
   §1.1) — landings + car room + controller; first install is the
   Constabulary shaft (alcove #4939 ↔ 2F landing #4957).
2. **Sky-room interplay** — do building interiors above z=0 need `passable`
   /floor semantics per spatial §6 generalization *now* (breach a floor →
   fall through), or defer floor-breaching entirely? Proposal: defer;
   floors are implicit barriers until the destruction spec.
3. ~~Door sound model~~ — **RESOLVED (2026-07-05): muffled-existence-only,
   full stop.** A closed door leaks the fact of sound, never content; no
   perception checks, no listen-at-door verb in this spec. Eavesdropping
   arrives later as **chrome**: a cybernetic-ear **sound-amplification
   module** granting `/listen` at adjacent exits (doors included) — the
   existing augment grammar (CYBER_EAR hardpoint + module ability, the
   JAWZ//blindsight pattern), belonging to the augments spec, not this one.
4. ~~Keycard vs. attribute grant~~ — **RESOLVED (2026-07-05): biometric
   only** (§2.2). No items, no memorized codes; forgery is the attack.
5. **Pricing** — 50 tokens/night against 100–500-token pockets: is one
   mugging ≈ one-to-three nights the intended economy scale?
6. ~~Naming~~ — **RESOLVED (2026-07-05): venues carry distinguished proper
   names** in "The Aster" register (NOT the AWE/PAM gear-brand schema —
   that's for manufactured goods). The hotel keeps a name of this shape,
   and **the bar should receive its proper name in the same pass**.
7. **B&E scope** — decided PvE-directed for v1 (§3.2), user on the fence
   long-term; revisit after tenancy plays.
