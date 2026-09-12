# Phase Layer Spec — Co-located Realities, the Net, and Perception Windows

> **Status:** 📋 Proposal — not implemented. Designs a **phase** partition: a
> per-entity membership axis on top of `(x, y, z)` space such that entities at
> the *same* coordinates in *different* phases cannot see, hear, or interact with
> one another — **default-deny**, with explicit one-way **perception windows**
> (cameras, ghost eavesdropping, net surveillance) as a first-class future.
> Primary driver: **the net / cyberspace layer** over meatspace. Generalizes to
> instancing, spectator/ghost planes, and private scenes. Depends conceptually on
> `SPATIAL_COORDINATE_SYSTEM_SPEC` (phase rides alongside coordinates) and the
> perception system (`world/perception.py`).
>
> **Note (2026-09-12):** still true of the phase partition itself — no `db.phase`,
> no `co_present`, no `PerceptionWindow`, no jack-in path anywhere in the code.
> But part of Phase 1's gate landed meanwhile *from the stealth side*:
> `world/perception.py` now carries `can_perceive(looker, target)` and the single
> enumeration choke `filter_present(looker, entities)`
> (`STEALTH_AND_DETECTION_SPEC` Phase 3, shipped 2026-07-03), awaiting only the
> phase clause. See the dated notes in §3, §3.1, §4, §5.3 and §10.

---

## 1 · Intent

### 1.1 · The headline use case — the net

A decker jacks in. Their **consciousness enters the net** — `phase = net` — at
the *same XYZ* their body occupies in `phase = meat`. In the net they perceive
and act among other deckers, ICE, and data-constructs; the meat crowd in the
same room is simply *not there* to them, and they are not there to it. Their
**body remains in meatspace**, slumped and vulnerable. This is the cyberpunk
fantasy the whole feature exists to deliver, and it's hard to do with
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
  occupants and contents are *partitioned* by phase; we never duplicate the room.
  This preserves the single-coordinate-per-room model, the authored
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

You may keep a `q`-style integer for `(x,y,z,q)` addressing symmetry if you like
it; just hold its *semantics* as membership. Phase belongs to the **perception /
presence** layer, not the geometry layer.

---

## 3 · The single gate (the make-or-break)

Phasing is maintainable only if every "who/what is here" decision funnels through
**one predicate**. A leak — one enumeration path that forgets phase — lets a
`meat` observer perceive a `net` event, and those bugs are subtle. So the
architecture centers on:

```python
# world/perception.py  (joins can_see / can_hear / can_perceive_sense)

def co_present(a, b) -> bool:
    """True if a and b share a reality: same phase, OR a perception window
    (§7) grants a→b perception. Default-deny across phases."""

def can_perceive(observer, target, sense="visual") -> bool:
    """The full gate: co_present(observer, target) AND the sense-capacity
    check (can_see / can_hear / …). Phase first, then perception."""

def filter_present(observer, candidates) -> list:
    """The enumeration filter the codebase already gestured at (the phantom
    `filter_visible` in typeclasses/objects.py:166, never implemented).
    Returns only candidates co_present with observer. Build it here; route
    all enumeration through it."""
```

> **Note (2026-09-12) — two of these three already exist.**
> `world/perception.py:can_perceive(looker, target)` is the shipped presence gate
> (its clause today is stealth's `is_hidden_from`; it takes no `sense` argument
> and does not join the sense-capacity check this block describes) and
> `world/perception.py:filter_present(looker, entities)` is the shipped
> enumeration choke — both built by `STEALTH_AND_DETECTION_SPEC` Phase 3
> (2026-07-03), whose docstrings already reserve the slot for "the phase layer's
> binary clause". Only `co_present` is absent. Also: `filter_visible` is **not** a
> phantom — it is a real inherited Evennia method
> (`evennia/objects/objects.py:1614`, verified against the live 6.1.0 checkout),
> and the only occurrence in this repo is the parent-API listing inside the
> boilerplate docstring of `typeclasses/objects.py` (line 225 today, not 166),
> which the repo never overrides or calls. There is no stub, and so no "latent
> `filter_visible` debt" to pay down — only Evennia's hook going unused.

**Phase sits *above* the existing perception gate, not beside it.** First you
must be co-present (or windowed); *then* sight/hearing capacity applies. A blind
decker in the net still can't see net objects; a sighted meat patron still can't
see the net at all.

### 3.1 · Audit — the three enumeration choke points

Perception predicates are centralized; **enumeration is not** (verified
2026-06 — **partly stale as of 2026-09-12; see the note under the table**).
Phasing routes each path through `filter_present` / `co_present`:

| Path | Today | Phase insertion |
|---|---|---|
| **Room display** | `Room.get_display_characters` / `get_display_things` loop `self.contents` gated by `obj.access(looker, "view")` | filter contents through `filter_present(looker, …)` |
| **Broadcasts** | Evennia `msg_contents` → all `.contents` | override `Room.msg_contents` to drop recipients not `co_present` with the source phase |
| **Combat / proximity** | `world/combat/proximity.py` `establish_proximity` / `is_in_proximity` (an `ndb` set) | a same-phase guard in `establish_proximity` → cross-phase proximity never forms → combat can't target across phase |

> **Note (2026-09-12).** Two corrections to the audit above.
>
> 1. **Enumeration is now partly centralized.** `filter_present` landed in
>    2026-07 and these paths route through it: identity targeting
>    (`commands/_identity_targeting.py`), whisper/`to`
>    (`commands/CmdCommunication.py`), adjacent-room sightings and the LLM
>    PRESENT roster (`typeclasses/characters.py`). The three rows above are still
>    un-routed, so their insertion points stand — the helper simply already
>    exists to insert into.
> 2. **The Broadcasts row names the wrong seam.** Overriding `Room.msg_contents`
>    would miss the path the game actually broadcasts on:
>    `world/identity_utils.py:msg_room_identity` (~461 call sites, against ~47
>    direct `msg_contents` calls) iterates `location.contents` itself and calls
>    `observer.msg()` per observer, never reaching `Room.msg_contents`. Its only
>    recipient filter is `_hears_broadcasts` (connected session or an
>    `at_msg_receive` override) — a cost optimisation, not a perception gate. A
>    phase clause has to go there too, which makes this a bounded surface of
>    **four** subsystems + the director, not three.

Plus the **dispatch director** (`NPC_DISPATCH_AND_SIMULATION_SPEC`): LOD
materialization must be phase-scoped — never render `phase = net` NPCs to a
`phase = meat` player, and vice-versa.

This is a **bounded** surface (three subsystems + the director), not a
whack-a-mole — *provided* all future enumeration is disciplined to go through
`filter_present`. Establishing that helper is therefore the first build step, and
it pays down the latent `filter_visible` debt at the same time.

---

## 4 · Storage & data model

* **Entity phase** — `db.phase` (default `0`) on characters and objects, mirrored
  to an indexed `("phase", "phase")` **tag** so "all entities in phase N here" is
  a DB-level query (the dispatch director and radar need this). A cached
  `obj.phase` property reads it; `ndb` cache for hot loops, invalidated on change
  (mirrors the `.xyz` caching call).
  *Note (2026-09-12):* there is no `.xyz` caching to mirror — `Room.xyz`
  (`typeclasses/rooms.py`) calls `world/spatial/coordinates.py:get_xyz` on every
  access, and nothing in `world/spatial/` caches or invalidates; the `ndb` cache
  is a still-unbuilt "Lean" in `SPATIAL_COORDINATE_SYSTEM_SPEC` §10. The indexed
  **tag** mirror above also inherits a storage model that spec retreated from:
  its §9 ladder records "Storage is `db.xyz`, not tags — see §10", so `phase`
  storage needs deciding here rather than inherited by analogy.
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
edges — it already routes over the real exit graph, so a phased edge is just an
edge the wrong-phase traverser can't see.

### 5.2 · The net renders the same room differently

The room's *geometry* is shared; its *presentation* is phase-specific. Meat sees
the authored five-senses description; the net sees the same space as a neon
wireframe / data-relief. This is a natural fit for two systems we already have:
the **sense-layer composition** (`get_display_desc` already composes per-sense
layers — add a per-phase overlay) and the **quiverbloom** aesthetic
(`SPATIAL_COORDINATE_SYSTEM_SPEC` §8) — the net is literally a different
rendering of the same coordinate volume. `get_display_desc(looker)` branches on
`looker.phase`.

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

**Systemic payoff (B):** a jacked-in body is effectively unable to resist →
under `TRUST_AND_CONSENT_SPEC`'s contest predicate (`conscious AND unrestrained`)
it reads as a **free-action target**: someone in meat can frisk, move, or harm
the slumped decker while they're away in the net. Emergent, on-theme, and it
falls out of systems we've already specced — no special case needed.

> **Note (2026-09-12):** the built predicate does not deliver this on its own.
> `world/consent.py:can_contest` is `is_conscious(target) and not
> is_restrained(target)`; `is_conscious` returns False only on an affirmative
> corpse/dead/unconscious medical state (unreadable state defaults to awake) and
> `is_restrained` requires a grapple or restraint furniture. A slumped-but-
> medically-awake, ungrappled decker therefore reads as **able to contest** —
> not a free-action target. Jacking in has to assert an affirmative helplessness
> state (an unconscious-equivalent medical flag, or a restraint-equivalent) for
> the payoff to land. `TRUST_AND_CONSENT_SPEC` §8 repeats the same inference, so
> the gap is shared between the two specs rather than a disagreement.

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

A **PerceptionWindow** is a scoped, directional, one-way grant:

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
    dead, or skill-gated).
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
  notable interaction: it's a free-action target in meat while its owner is away.
* **Stealth & detection (`STEALTH_AND_DETECTION_SPEC`).** Phase's **graded
  sibling**: phase is binary co-presence, stealth is a per-observer *awareness*
  contest *within* a phase. Both resolve through the same `can_perceive` /
  `filter_present` gate — phase removes you from consequence, stealth only from
  passive notice.
* **Identity & recognition.** A net-avatar has its *own* presentation/sdesc
  (`IDENTITY_RECOGNITION_SPEC`) — you might not know a decker's meat identity from
  their net avatar, and vice-versa. Recognition is per-presentation, so this works
  without special logic; the avatar is just another apparent identity.
* **Perception capacities.** Phase gate is *above* the capacity gate (§3): be
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
as events that name both phases, routed through the dispatch bus. Reserved here
so the default-deny gate is never mistaken for "phases can never affect each
other." The seam: an effect may declare `crosses_phase = {from, to}` and the
system honors it as an intentional bridge.

---

## 10 · Build ladder

| Phase | Scope | Notes |
|---|---|---|
| **1 — The gate** | `db.phase` (+ tag) on entities; `co_present` / `can_perceive` / `filter_present` in `world/perception.py`; route the three choke points (room display, `msg_contents`, proximity) + dispatch materialization through it | Default `phase=0` → zero regression; pays down the `filter_visible` debt |
| **2 — Net presence** | Jack in/out; the two-body model (§5.3); net combat via the proximity guard | (A) single-object as v1 fallback, (B) two-body as target |
| **3 — Net rendering** | Phase-specific `get_display_desc` overlay; phase-tagged exits; net ambient layer; quiverbloom net relief | Reuses sense-layer composition |
| **4 — Perception windows** | The `PerceptionWindow` model; cameras / bugs / ghost eavesdropping; window clause in `co_present` | Default-deny, perceive-only |
| **5 — Cross-phase causation** | Explicit `crosses_phase` effect bridges (EMP, collapse, body-death disconnect) | Reserved; via dispatch bus |

> **Note (2026-09-12):** Phase 1 is partly done — from the stealth side.
> `can_perceive` and `filter_present` exist in `world/perception.py` and about a
> dozen enumeration paths route through them. What Phase 1 still owes: `db.phase`
> (plus the storage decision, §4 note), `co_present`, the phase clause inside
> `can_perceive`, and **four** insertions — room display, `msg_contents`,
> `msg_room_identity` (§3.1 note), proximity — plus director materialization. The
> `filter_visible` line in the Notes column is void: that method is real Evennia
> code, not a debt (§3 note).

Phase 1 is the whole feasibility bet: if `filter_present` cleanly gates the three
choke points, everything else is incremental.

---

## 11 · Risks & open questions

* **Leak-completeness.** The central risk. Mitigation: one `filter_present`
  choke, a lint/test that flags raw `.contents` enumeration in perception paths,
  and a test suite that asserts no cross-phase leak through say/look/combat/
  emote/crowd. Treat a new enumeration path that bypasses `filter_present` as a
  bug class.
* **Two-body plumbing (§5.3).** Command routing (which presence does a typed
  command target?), the body↔avatar link, disconnect-on-death, and what the meat
  room shows for a slumped jacked-in body. The richest part and the most plumbing.
* **Phase-tagged exits & the pathfinder.** Confirm the A\* edge filter is a clean
  add (it should be — edges already gate on traversability).
* **Performance.** Phase is a cheap int compare, but it multiplies onto every
  enumeration and every spatial query. Bound by the same `ndb` caching as `.xyz` (itself unbuilt — see the §4 note);
  measure on the live box.
* **Griefing / consequence-dodging.** Phase must not become a way to escape
  accountability illegitimately (hiding from a fight by phasing). Phase changes
  are *explicit, gated actions* (jacking in needs a deck + a port), not free
  toggles — and the vulnerable-body model (§5.3) is the cost.
* **Cross-phase causation scope (§9).** Which effects legitimately bridge, and
  who authors that — a curated list, not a general "effects leak" rule.
* **Spectator/ghost defaults.** Is the ghost→living window always-on, skill-
  gated, or item-gated? Tie to the death system.
* **Persistence.** Phase survives logout (you log back in where/what you were).
  Net disconnect on link-loss is a deliberate exception.
