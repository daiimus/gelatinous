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
> jump/fall gravity §6).

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
* **Lift/elevator** — v1 is a **warp exit** (spatial §3's non-Euclidean
  escape hatch): `enter lift` at the lobby, exit at the chosen floor.
  Simplest shippable form: one exit per served floor from a small lift-car
  room ("press 3"). A scheduled/moving car is flavour we can add later
  without changing the topology. **Design call:** lifts are where access
  control meets construction (keycard floors) — the lift exit takes the same
  lock seam as doors (§2.4), so a corp tower's executive floor is just a
  locked lift exit.
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

### 1.4 · Builder authoring — `@stack`

Hand-digging N floors with coordinates is error-prone. One builder command
covers 90% of construction:

```
@stack <building name> = <floors>[, <footprint room>]
```

Creates `<floors>` rooms straight up from the footprint room's coordinates,
links them with a stairwell chain, names them ("Aster Hotel — Third Floor"),
seeds coordinates, flags the top room `is_rooftop`. Builders then decorate
rooms individually as always (the spatial spec's stance: coordinates are the
data model, hand-authoring stays the authoring model). Lifts, doors, and
room splits (multiple rooms per floor) are manual follow-ups.

---

## 2 · Layer 2 — doors

**A door is an exit with state.** In face-state terms: today an exit edge is
permanently *open* and a missing edge is permanently *barrier*; a door is an
edge that can be **either, at runtime** — the first operable face.

### 2.1 · The state model

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

### 2.2 · Keys, codes, and access-as-record

Two access forms, deliberately both:

* **Physical key** — an object; possession is access. Stealable, copyable
  (later), loanable — all the emergent play of a thing in a hand.
* **Keycode** — a fact: the door stores a grant list / code, access checked
  against the character (or a carried keycard object). **This is the decking
  seam**: a keycode is *a record on a device*, exactly the "everything is a
  file" thesis in physical form. When decking arrives, door grants are
  readable/falsifiable/erasable files. Until then they're just attributes —
  but shaped as records from day one (grant entries: who/until-when/issued-by)
  so the future hack has something honest to hack.

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

### 2.4 · The breach seam (reserved, not built)

Forcing a door = the face-state flip the spatial spec reserves for
destruction: `locked → open (broken)`. A broken door can't re-close until
repaired. Needs the damage-state model the spatial spec already defers;
this spec just requires the door state enum to include `broken` so the
future breach has a landing slot. Lockpicking likewise reserved (skill
system is parked by explicit user decision).

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
  150 tokens. Room 304. The kiosk spits out a keycard.
```

* Payment in **tokens** — the first real sink; prices finally mean something
  (mugging pockets ↔ paying rent closes an actual loop).
* The grant: a **keycard object** (physical form, stealable — that's a
  feature: room invasion via pickpocket is exactly the game) carrying the
  code; the door's grant record carries the expiry.
* **Expiry**: at lease end the door's grant lapses (record-driven, checked
  at the door — no sweeper needed to *enforce*). A housekeeping sweep
  (director-side, like the population upkeep pattern) later resets expired
  rooms: unclaimed possessions to a lost-and-found bin behind the desk
  (nothing silently deleted), door re-locked, room re-listed.

### 3.2 · What a rented room IS

* **Private** — closed/locked door = real perception privacy (§2.3). The
  first place a character can sleep/log out with stakes lowered, stage a
  scene, or stash goods.
* **Not a vault** — storage is only as safe as the door. Breach/theft paths
  stay open by design (crime playground, not player housing entitlement).
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

1. **Lift v1** — warp-exit-per-floor (simple, shippable) vs. a moving car
   (flavourful, stateful). Proposal assumes warp-exit v1.
2. **Sky-room interplay** — do building interiors above z=0 need `passable`
   /floor semantics per spatial §6 generalization *now* (breach a floor →
   fall through), or defer floor-breaching entirely? Proposal: defer;
   floors are implicit barriers until the destruction spec.
3. **Door sound model** — muffled-existence-only (proposed) vs. Resonance
   /perception checks to make out words through doors (richer, more code).
4. **Keycard vs. attribute grant for players** — proposal ships BOTH (card
   carries the code; door records the grant) — confirm the theft-of-keycard
   consequence is wanted (stolen card = access until expiry, no re-issue v1).
5. **Pricing** — 50 tokens/night against 100–500-token pockets: is one
   mugging ≈ one-to-three nights the intended economy scale?
6. **Naming** — "The Aster" is a placeholder; the hotel wants a real name
   (and a brand, per the AWE/PAM naming schema).
