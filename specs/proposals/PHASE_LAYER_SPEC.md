# Phase Layer Spec — Co-located Realities, the Net, and Perception Windows

This spec designs a **phase** partition: a per-entity membership axis on top of
`(x, y, z)` space. Entities at the *same* coordinates in *different* phases
cannot see, hear, or interact with one another. It is **default-deny**, with
explicit one-way **perception windows** (cameras, ghost eavesdropping, net
surveillance) as a first-class future. The primary driver is **the net /
cyberspace layer** over meatspace. The design generalizes to instancing,
spectator/ghost planes, and private scenes. It depends conceptually on
`SPATIAL_COORDINATE_SYSTEM_SPEC` (phase rides alongside coordinates) and on the
perception system (`world/perception.py`).

📋 Proposal — not implemented. The phase partition itself (`db.phase`,
`co_present`, `PerceptionWindow`, a jack-in path) does not exist. It builds on
the presence gate `can_perceive(looker, target)` and the enumeration choke
`filter_present(looker, entities)` in `world/perception.py`, where the phase
clause goes (§3, §10).

---

## 1 · Intent

### 1.1 · The headline use case — the net

A decker jacks in. Their **consciousness enters the net** — `phase = net` — at
the *same XYZ* their body occupies in `phase = meat`. In the net they perceive
and act among other deckers, ICE, and data-constructs. The meat crowd in the
same room is simply *not there* to them, and they are not there to it. Their
**body remains in meatspace**, slumped and vulnerable. This is the cyberpunk
fantasy the whole feature exists to deliver. It is hard to do with
room-duplication and natural with a phase partition.

### 1.2 · The general potential

The same mechanism — "same place, separate reality" — covers more than the net:

* **Instancing** — parties run a story beat in the same location without
  colliding (`phase = instance_4821`).
* **Spectator / ghost plane** — the dead observe the living (`phase = ghost`),
  with a one-way window *to* the living (§7).
* **Private scenes** — a companion engagement in a booth that co-located patrons
  genuinely cannot perceive (a stronger guarantee than a soundproof flag).
* **Camera feeds & surveillance** — the override seam (§7) that lets one phase
  perceive *into* another through a specific device.

The net is the driver; the design must not be net-only.

---

## 2 · Core model — phase is a partition, not a coordinate

**Phase is a per-entity membership tag**, not a spatial axis. Every character and
object carries a phase (default `0` = **meatspace**). Two entities **co-located
in space but in different phases are mutually imperceptible and
non-interactive** — by default, absolutely.

* **Per-entity, shared room.** The room at `(x, y, z)` exists **once**. Its
  occupants and contents are *partitioned* by phase; the room is never
  duplicated. This preserves the single-coordinate-per-room model, the authored
  sense-descriptions, the exit graph, and dispatch — none of which a
  room-instancing approach could keep intact.
* **Default `phase = 0` → zero regression.** Until something sets a non-zero
  phase, every entity is in meatspace and the world behaves exactly as today.
  Phase is opt-in, like the capacity overrides.
* **Default-deny.** Cross-phase perception/interaction is forbidden unless an
  explicit **perception window** (§7) grants a scoped exception.

### 2.1 · Why it is *not* a fourth coordinate

`X`, `Y`, `Z` carry a **metric** — distance, adjacency, gravity, range, the A\*
heuristic. Phase carries **none**: there is no distance in phase, no
phase-adjacency, no falling along phase. It is an **equivalence class**, not a
position. Filing it next to xyz as "a coordinate" would hand every spatial
helper a meaningless axis. So the honest addressing is:

```
(x, y, z)   — WHERE in space   (metric; the coordinate system)
phase       — WHICH co-located reality (membership; this spec)
```

A `q`-style integer for `(x,y,z,q)` addressing symmetry may be kept if liked;
its *semantics* stay membership. Phase belongs to the **perception /
presence** layer, not the geometry layer.

---

## 3 · The single gate (the make-or-break)

Phasing is maintainable only if every "who/what is here" decision funnels through
**one predicate**. A leak — one enumeration path that forgets phase — lets a
`meat` observer perceive a `net` event, and those bugs are subtle. So the
architecture centers on three functions in `world/perception.py` (beside
`can_see` / `can_hear` / `can_perceive_sense`):

* **`co_present(a, b) -> bool`** (proposed). True if `a` and `b` share a
  reality: same phase, OR a perception window (§7) grants a→b perception.
  Default-deny across phases.
* **`can_perceive(looker, target)`** — the presence gate. Its clause today is
  stealth's `is_hidden_from`; its docstring reserves the slot for the phase
  layer's binary clause. The phase clause goes inside it. It takes no `sense`
  argument and does not join the sense-capacity check (`can_see` / `can_hear` /
  `can_perceive_sense`). The full gate this spec proposes is `co_present` AND
  the sense-capacity check (`can_see` / `can_hear` / …): phase first, then
  perception.
* **`filter_present(looker, entities)`** — the single enumeration choke. It
  returns only the entities `can_perceive` passes. All enumeration is to route
  through it; §3.1 lists the paths that do not.

Evennia's inherited `filter_visible` hook is not part of this gate. The repo
never overrides or calls it; it appears only in the parent-API listing inside
the boilerplate docstring of `typeclasses/objects.py`. There is no stub, and so
no `filter_visible` debt to pay down.

**Phase sits *above* the existing perception gate, not beside it.** First you
must be co-present (or windowed); *then* sight/hearing capacity applies. A blind
decker in the net still can't see net objects; a sighted meat patron still can't
see the net at all.

### 3.1 · Audit — the enumeration choke points

Perception predicates are centralized; enumeration is only partly centralized.
Paths that go through `filter_present` or `can_perceive`:

* identity targeting (`commands/_identity_targeting.py`, through `filter_present`);
* adjacent-room sightings (`get_adjacent_character_sightings` in
  `typeclasses/rooms.py`, through `can_perceive`);
* the LLM PRESENT roster (`typeclasses/llm_npc.py`, through `can_perceive`);
* the pool of every local name search (`Character.get_search_candidates` in
  `typeclasses/characters.py`, which also covers whisper/`to`) (#3637).

Five paths do not, and phasing routes each through `filter_present` /
`co_present`:

| Path | Today | Phase insertion |
|---|---|---|
| **Room display** | `Room.get_display_characters` loops `self.contents`, gated by `obj.access(looker, "view")`, by sight (`can_perceive_sense`) and by stealth through a direct `is_hidden_from` call, not `can_perceive`; `get_display_things` gates by sight and `obj.access(looker, "view")` and skips `db.hidden` objects | route both through `filter_present(looker, …)` (or `can_perceive`) so the phase clause reaches them |
| **Broadcasts — `msg_contents`** | Evennia `msg_contents` → all `.contents` | override `Room.msg_contents` to drop recipients not `co_present` with the source phase |
| **Broadcasts — `msg_room_identity`** | `msg_room_identity` in `world/identity_utils.py` (about 230 call sites outside tests, against about 40 direct `msg_contents` calls) iterates `location.contents` itself and calls `observer.msg()` per observer, never reaching `Room.msg_contents`. Its only recipient filter is `_hears_broadcasts` (connected session or an `at_msg_receive` override) — a cost optimisation, not a perception gate | a phase clause here too; overriding `Room.msg_contents` alone would miss the path the game mostly broadcasts on |
| **Broadcasts — `perceivers`** | `perceivers(location, exclude_set)` in `world/perception.py` picks the recipients for say/`to`, poses and emotes, whispers, radio grilles and clothing broadcasts. It keeps every character-shaped object in `location.contents` (`perceives`) and has no perception gate | a phase clause here too |
| **Combat / proximity** | `world/combat/proximity.py` `establish_proximity` / `is_in_proximity` (an `ndb` set) | a same-phase guard in `establish_proximity` → cross-phase proximity never forms → combat can't target across phase |

Plus the **dispatch director** (`NPC_DISPATCH_AND_SIMULATION_SPEC`): LOD
materialization must be phase-scoped — never render `phase = net` NPCs to a
`phase = meat` player, and vice-versa.

This is a **bounded** surface (five subsystems + the director: room display,
`msg_contents`, `msg_room_identity`, `perceivers`, proximity), not a
whack-a-mole — *provided* all future enumeration is disciplined to go through
`filter_present`. The first build step is the phase clause inside
`can_perceive`, which `filter_present` calls.

---

## 4 · Storage & data model

* **Entity phase** — `db.phase` (default `0`) on characters and objects, mirrored
  to an indexed `("phase", "phase")` **tag** so "all entities in phase N here" is
  a DB-level query (the dispatch director and radar need this). A cached
  `obj.phase` property reads it; an `ndb` cache for hot loops, invalidated on
  change. There is no `.xyz` caching to mirror: `Room.xyz` (`typeclasses/rooms.py`)
  calls `get_xyz` in `world/spatial/coordinates.py` on every access, and nothing
  in `world/spatial/` caches or invalidates; that `ndb` cache is an unbuilt
  "Lean" in `SPATIAL_COORDINATE_SYSTEM_SPEC` §10. The indexed **tag** mirror
  inherits a storage model that spec retreated from (its §3 Storage records storage
  as `db.xyz`, not tags), so `phase` storage needs deciding here rather
  than inherited by analogy (§12).
* **Perception window** — a structured grant (§7), stored on the *device* or the
  *room* that mediates it.
* **Phase is not on the room.** The room is phase-agnostic geometry; only its
  *contents* and its *overlay rendering* (§5.2) are phased.

---

## 5 · The net layer in detail

The net is the first and richest phase. Several net-specific questions the
general model must answer:

### 5.1 · Same rooms, possibly different topology

The net occupies the **same room set / same coordinates** as meat ("exactly the
same room at xyz"). But the net **may carry its own connectivity** — phase-scoped
exits — so a decker can traverse where a body cannot (jump between distant nodes,
pass a meat wall that has no net barrier). So: rooms and coordinates are shared;
**exits may be phase-tagged** (a `meat`-only door, a `net`-only data-conduit).
The pathfinder (`SPATIAL_COORDINATE_SYSTEM_SPEC` §5) gains a phase filter on
edges. It already routes over the real exit graph, so a phased edge is just an
edge the wrong-phase traverser can't see.

### 5.2 · The net renders the same room differently

The room's *geometry* is shared; its *presentation* is phase-specific. Meat sees
the authored five-senses description; the net sees the same space as a neon
wireframe / data-relief. This fits two existing systems: the **sense-layer
composition** (`get_display_desc` composes per-sense layers — add a per-phase
overlay) and the **quiverbloom** aesthetic (`SPATIAL_COORDINATE_SYSTEM_SPEC` §8)
— the net is literally a different rendering of the same coordinate volume.
`get_display_desc(looker)` branches on `looker.phase`.

### 5.3 · Jacking in — the two-body model

When a decker jacks in, the **body stays `phase = meat`** (slumped, vulnerable)
and a **net presence enters `phase = net`** at the same XYZ. Two design options:

* **(A) Single object changes phase** — the whole character moves meat→net; the
  body vanishes. Simple; loses the vulnerable-body tension.
* **(B) Two presences** *(recommended target)* — the body remains a real object
  in meat; a **net-avatar** (a projected presence) acts in the net. This is the
  cyberpunk fantasy: your meat is exposed while you're jacked in. More plumbing
  (whose commands route where; how the two are linked; disconnect on body death),
  but far richer and on-theme. **(A)** is an acceptable v1 simplification if the
  two-body plumbing isn't ready.

**Systemic payoff (B):** a jacked-in body should be a **free-action target** —
someone in meat can frisk, move, or harm the slumped decker while they're away
in the net. The consent predicate does not deliver this on its own.
`can_contest` in `world/consent.py` is `is_conscious(target) and not
is_restrained(target)`. `is_conscious` returns False only on an affirmative
corpse/dead/unconscious medical state (unreadable state defaults to awake), and
`is_restrained` requires a grapple or restraint furniture. A slumped but
medically awake, ungrappled decker therefore reads as **able to contest**. For
the payoff to land, jacking in has to assert an affirmative helplessness state
(an unconscious-equivalent medical flag, or a restraint-equivalent).
`TRUST_AND_CONSENT_SPEC` §8 makes the same inference, so the gap is shared
between the two specs rather than a disagreement.

### 5.4 · Combat in the net

ICE and decker-vs-decker combat run on the *same* combat system, scoped to
`phase = net` by §3.1's proximity guard. No parallel combat engine — phase
filtering is the only addition.

---

## 6 · Objects, corpses, and the environment in phase

* **Objects carry phase** (default meat): a physical crate is `meat`; a
  data-construct is `net`. Picking up / interacting requires co-presence, so a
  decker can't grab a meat crate and a patron can't touch a net icon.
* **The room and its fixtures** are shared geometry; furniture defaults `meat`.
* **Corpses** default `meat`. A "dead" spectator presence is a *phase* state
  (`ghost`), distinct from the physical corpse object.
* **Sensory environment** — crowd, weather, ambient sense-messages
  (`world/perception.py` consumers) are phase-scoped: the net has its own ambient
  layer (data-wind, ICE hum), meat keeps the street crowd.

---

## 7 · Perception windows — the override seam (cameras, ghosts, surveillance)

Default-deny is the baseline; **windows are the deliberate exceptions**, and they
are first-class because cameras/feeds/ghost-eavesdropping are known future needs.

A **PerceptionWindow** is a scoped, directional, one-way grant. Its proposed
shape:

```python
@dataclass
class PerceptionWindow:
    from_phase: int          # the OBSERVER's phase
    to_phase: int            # the phase being perceived INTO
    scope: object            # room / coordinate region the window covers
    senses: frozenset        # {"visual"} for a camera; {"auditory"} for a bug
    direction: str = "one_way"   # observe only; never enables interaction
    source: object | None = None # the device/anchor (camera, ICE tap, séance)
```

* **One-way and perceive-only.** A window lets `from_phase` *perceive* `to_phase`
  within `scope`/`senses`. It **never** grants interaction — you can watch, not
  touch (acting still requires true co-presence). This keeps windows safe by
  construction.
* **It threads through the one gate.** `co_present(a, b)` returns true across
  phases *iff* a window covers `(a.phase → b.phase, b.location, sense)`. No new
  enumeration path — windows are a clause in the predicate everything already
  calls. This is why the single-gate discipline (§3) is non-negotiable: it's what
  makes windows tractable.
* **Examples.**
  * *Hacked camera* — a `net→meat` visual window scoped to the camera's room; a
    decker watches the meat space they've compromised.
  * *Audio bug* — `net→meat` auditory-only window.
  * *Ghost eavesdropping* — a `ghost→meat` window (perhaps always-on for the
    dead, or skill-gated; §12).
  * *Meat security monitor* — a `meat→net`? Usually not; meat rarely perceives
    the net without jacking — but the model permits it for special gear.
* **Mirrors the chrome `*_override` seams.** Like sight/hearing overrides restore
  a capacity without the organ, a window restores a *perception* across a
  partition without true presence. Same philosophy: default-deny, explicit
  scoped grant, fail-closed.

---

## 8 · Interaction with the other specs

* **Spatial coordinate system.** Phase rides *alongside* `(x, y, z)`, never as a
  fourth metric axis. Range queries (`rooms_within`, `slice`, radar) gain a
  **phase filter argument** — a radar in `net` sees only `net` contacts. Exits
  may be phase-tagged (§5.1); the A\* pathfinder filters edges by phase. The
  `slice()` volume query gains phase so the GPS/quiverbloom renderer draws the
  viewer's reality.
* **Dispatch & simulation.** The director is **phase-scoped**: population census,
  LOD materialization, routines, and events all carry a phase. Some events are
  single-phase (a net intrusion); some are **cross-phase causal** (§9) — an EMP
  in meat that fries net nodes.
* **Trust & consent.** Acting across a phase is impossible (windows are
  perceive-only), so consent never spans phases. The jacked-in body (§5.3) is the
  notable interaction: it becomes a free-action target in meat only if jacking in
  sets an affirmative helplessness state (unconscious-equivalent or
  restraint-equivalent); the consent predicate does not deliver it alone (§5.3).
* **Stealth & detection (`STEALTH_AND_DETECTION_SPEC`).** Phase's **graded
  sibling**: phase is binary co-presence, stealth is a per-observer *awareness*
  contest *within* a phase. Both resolve through the same `can_perceive` /
  `filter_present` gate — phase removes you from consequence, stealth only from
  passive notice.
* **Identity & recognition.** A net-avatar has its *own* presentation/sdesc
  (`IDENTITY_RECOGNITION_SPEC`) — you might not know a decker's meat identity from
  their net avatar, and vice-versa. Recognition is per-presentation, so this works
  without special logic; the avatar is just another apparent identity.
* **Perception capacities.** The phase gate is *above* the capacity gate (§3): be
  co-present (or windowed) first, then sight/hearing/etc. apply within.

---

## 9 · Cross-phase causation (reserved)

Default-deny is right for *perception and interaction*, but some effects should
**cross phases deliberately**:

* An **EMP / power surge** in meat that disrupts net nodes co-located there.
* A **building collapse** (room destruction, coordinate spec §8) that should
  sever the net topology riding on those rooms.
* **Body death** in meat that forcibly disconnects the net-avatar (§5.3).

These are **explicit cross-phase causal links**, not perception leaks — modeled
as events that name both phases, routed through the dispatch bus. They are
reserved here so the default-deny gate is never mistaken for "phases can never
affect each other." The seam: an effect may declare `crosses_phase = {from, to}`
and the system honors it as an intentional bridge.

---

## 10 · Build ladder

Every phase below is 📋 Proposal — not implemented.

| Phase | Scope | Notes |
|---|---|---|
| **1 — The gate** | `db.phase` on entities (storage to decide, §4, §12); `co_present` and the phase clause inside the existing `can_perceive` / `filter_present` in `world/perception.py`; route the five choke points (room display, `msg_contents`, `msg_room_identity`, `perceivers`, proximity) + dispatch materialization through it | Default `phase=0` → zero regression |
| **2 — Net presence** | Jack in/out; the two-body model (§5.3); net combat via the proximity guard | (A) single-object as v1 fallback, (B) two-body as target |
| **3 — Net rendering** | Phase-specific `get_display_desc` overlay; phase-tagged exits; net ambient layer; quiverbloom net relief | Reuses sense-layer composition |
| **4 — Perception windows** | The `PerceptionWindow` model; cameras / bugs / ghost eavesdropping; window clause in `co_present` | Default-deny, perceive-only |
| **5 — Cross-phase causation** | Explicit `crosses_phase` effect bridges (EMP, collapse, body-death disconnect) | Reserved; via dispatch bus |

Phase 1 is the whole feasibility bet: if `filter_present` / `can_perceive` cleanly
gates the five choke points (§3.1), everything else is incremental.

---

## 11 · Risks

* **Leak-completeness.** The central risk. Mitigation: one `filter_present`
  choke, a lint/test that flags raw `.contents` enumeration in perception paths,
  and a test suite that asserts no cross-phase leak through say/look/combat/
  emote/crowd. Treat a new enumeration path that bypasses `filter_present` as a
  bug class.
* **Two-body plumbing (§5.3).** The richest part and the most plumbing (open
  points in §12).
* **Performance.** Phase is a cheap int compare, but it multiplies onto every
  enumeration and every spatial query. Bound by the same `ndb` caching as `.xyz`
  (itself unbuilt — see §4); measure on the live box.
* **Griefing / consequence-dodging.** Phase must not become a way to escape
  accountability illegitimately (hiding from a fight by phasing). Phase changes
  are *explicit, gated actions* (jacking in needs a deck + a port), not free
  toggles — and the vulnerable-body model (§5.3) is the cost.
* **Persistence.** Phase survives logout (you log back in where/what you were).
  Net disconnect on link-loss is a deliberate exception.

---

## 12 · Not decided

* **Phase storage (§4).** `db.phase` with an indexed tag mirror, or another
  model; it needs deciding here rather than inherited by analogy from the
  spatial spec.
* **Two-body plumbing (§5.3).** Command routing (which presence does a typed
  command target?), the body↔avatar link, disconnect-on-death, and what the meat
  room shows for a slumped jacked-in body.
* **Phase-tagged exits & the pathfinder.** Confirm the A\* edge filter is a clean
  add (it should be — edges already gate on traversability).
* **Cross-phase causation scope (§9).** Which effects legitimately bridge, and
  who authors that — a curated list, not a general "effects leak" rule.
* **Spectator/ghost defaults.** Is the ghost→living window always-on, skill-
  gated, or item-gated? Tie to the death system.

---

## Related documents

* `SPATIAL_COORDINATE_SYSTEM_SPEC` — coordinates, pathfinder (§5), quiverbloom
  (§8), the `ndb` cache "Lean" (§10).
* `STEALTH_AND_DETECTION_SPEC` — the graded sibling; the source of `can_perceive` /
  `filter_present`.
* `NPC_DISPATCH_AND_SIMULATION_SPEC` — the phase-scoped director.
* `TRUST_AND_CONSENT_SPEC` — the contest predicate (§8).
* `IDENTITY_RECOGNITION_SPEC` — per-presentation recognition.
