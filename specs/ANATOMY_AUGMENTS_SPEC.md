# Anatomy Augments Spec — Per-Character Anatomy

**Status:** approved design, implementation phased.  The discussion
that settled every decision below happened 2026-06-11.  First
consumer: the cybernetic tail.

## 0 · The principle: the body is the truth

Today, anatomy questions are answered by **static species tables**:
what organs exist, what can be severed, what can grasp, what renders.
A character's `medical_state.organs` already holds live per-character
organ instances — but half the systems around it still consult the
species table instead of the body in front of them.

After this spec, **a character's actual organs are the runtime
truth; the species table is the starting template** — consulted once
at character creation (and as the fallback for legacy data), then
extended or reduced per character by installs and severance.

What this buys beyond the tail: chrome vs vat-grown biotech is
*theming on the item* — the augment substrate doesn't know the
difference.  Species expansion (synths) is an item-data edit, not a
code change.  And the substrate is the foundation the cyberware era
keeps building on.

## 1 · Settled design decisions

These were decided in discussion and are not open for silent
revision:

1. **First augment: cybernetic tail.**  Humans-only for now, gated
   by a species-compatibility list **on the item** — expanding to
   synths later means editing that list, zero code.
2. **Prehensile from day one.**  The tail joins the character's
   grasping set: it can hold and wield.  This deliberately breaks
   the static `grasping_containers` assumption now rather than
   later.
3. **Full body integration, no capacity contributions in v1.**
   Capacities are normalized floors — an organ can only drag a
   capacity down, never boost past 1.0 — and `moving`/`manipulation`
   have no consumers yet.  Capacity extension waits for consumers
   (same parking decision as the fracture condition).
4. **Augment data lives on the item.**  The item carries its own
   organ spec(s), anchor container, longdesc surface, and species
   list.  No new DB entities, no registry until a second augment
   family demands one.
5. **Existing surgery is the whole interface.**  Install via
   `incise` → `install` → `suture`; removal via `harvest`.  No new
   verbs.  A severed or harvested augment is the existing organ
   item — reinstallable, conditions traveling with it.
6. **Trust/consent stays an open door.**  Installing hardware in
   another character rides the same third-party-surgery door that
   already exists; the future trust/consent system gates it there.
   Nothing in this spec may assume surgeon == patient.

## 2 · Current state: the static reads

The census of species-static reads, and what each means for an
installed tail:

| Read | Where | Per-character today? |
|---|---|---|
| Hit-location selection | `select_hit_location` — `character.longdesc` keys | **Yes** — already the body's surface |
| Location → organ resolution | `get_organ_by_body_location` / `select_target_organ` / `calculate_hit_weights_for_location` / `distribute_damage_to_organs` — static `ORGANS` global | **No** — and this is a live species bug: a rat hit at its tail resolves zero organs from the human table and the damage silently no-ops |
| Organ spec round-trip | `Organ.from_dict` re-derives container/hit_weight/vital from the species table | **No** — a non-species organ restores with container `"unknown"` |
| Install slot check | `CmdInstall` → species organ snapshot ("has no slot for a X") | **No** — augments need the inverse: create the slot |
| Severable containers | `get_species_severable_containers` frozenset | **No** |
| Grasping containers | `hands` property → `get_species_grasping_containers` | **No** |
| Longdesc display order / regions | species `anatomical_display_order` / `anatomical_regions` | **No** — an added key must still render somewhere sane |

`MedicalState.from_dict` already *overlays* persisted organs onto
the species set, and severance already subtracts locations
per-character — the substrate is half-built; this spec finishes it.

## 3 · Mechanics

### 3.1 · Organ spec persistence

`Organ.to_dict` gains `"data": self.data` (the spec dict).
`from_dict` passes it through as the `organ_data` override when
present; legacy snapshots without it fall back to the species lookup
exactly as today.  This is event-driven persistence (save on
meaningful change), not a hot path — the DB-write doctrine is
untouched.

### 3.2 · Per-character organ resolution

Location → organ questions are answered by the character's
`medical_state.organs` (each organ already knows its `container` and
`hit_weight`) wherever a character or medical state is in hand.  The
static `ORGANS` scan remains only as the no-character fallback.
**This fixes the rat-tail combat bug as a side effect** — pin it in
the tests.

This touches the per-attack combat path: per the hot-path rule,
benchmark hit resolution before/after in Phase 1.

### 3.3 · Augment install

Augment items declare (as attrs):

* `augment_organs` — `{organ_name: spec_dict, ...}` full organ
  specs, same shape as a species-table entry
* `augment_container` — the new body location (`"tail"`)
* `augment_anchor` — existing container the surgery opens
  (incision gate), e.g. `"back"` for the tail — you cut where the
  hardware mounts (base of the spine), and the new location grows
  from there
* `augment_longdesc` — `{key, default_desc, display_after}` for the
  rendering surface
* `compatible_species` — `["human"]` (the established cyberware /
  harvest-provenance species gate; one field everywhere)

`CmdInstall` grows an augment branch: species check → incision at
the **anchor** (the slot doesn't exist yet; you cut where it goes) →
create the organ(s) with `organ_data` from the item → add the
longdesc key → persist.  Repeat-install while present is rejected
("already has a tail").

The operate menu reaches the same resolver: augment items list
alongside donor organs in the install picker, picking one records
the chart step at the item's anchor with no location prompt (the
item knows where it mounts), and the chart runner routes execution
to the augment resolver — with the species and incision gates
re-checked there, since chart commencement bypasses the command's
pre-dispatch gates.

### 3.4 · Prehensile grasping

An organ spec may flag `"grasping": true`.  The `hands` property
merges {containers of grasping-flagged organs present on the body}
with the species grasping set, minus severed — the existing
severance subtraction then handles "severed tail drops what it
held" with no new code.

### 3.5 · Severance

A container is severable when it's in the species severable set
**or** any organ at it flags `"severable_container": true` (the
tail's spec does).  The severed-part pipeline already builds from
the character's organs, so the severed tail hits the floor as an
organ item carrying the cybernetic tail — reinstallable, damage and
conditions intact.

### 3.6 · Rendering

The longdesc renderer appends per-character locations missing from
the species display order after their `display_after` hint (or at
the end of their region).  Wound rendering follows
`display_location` as it already does.

## 4 · The cybernetic tail (first consumer)

**Augments mirror flesh organ architecture** (settled 2026-06-11):
the tail location carries a skeletal organ the way a rat's tail
carries `tail_vertebrae`, so every existing treatment surface works
uniformly — a bone-typed cyber organ is splintable ("brace the bent
actuator column"), tourniquetable, severable, with no special
cases.  The same principle governs future *replacement*
cybernetics: a cybernetic hand keeps the canonical slot/organ
structure of the flesh hand (the metacarpals are still there,
structurally) and theming lives in display names and item prose,
never in the slot keys.

Prototype `CYBERNETIC_TAIL`: organ `cybernetic_tailbone` at
container `"tail"` (`"tail"` is already in `LIMB_CONTAINERS` —
tourniquets gate correctly with zero changes), bone-typed, modest
HP, common hit weight, `severable_container`, `grasping`; anchor
`"back"` (the mount bolts to the base of the spine — you incise
where it attaches); `compatible_species ["human"]`.  Future biotech
variants are new prototype text over the same attrs.

## 5 · Phases

* **Phase 1 — substrate refactor** (one PR): organ-spec round-trip
  + per-character location→organ resolution + equivalence tests +
  the rat-tail fix + hit-resolution benchmark.  Pure refactor; no
  behavior change for humans.
* **Phase 2 — augment install** (one PR): `CmdInstall` augment
  branch, longdesc insertion, severable/grasping overlays,
  prehensile `hands` merge, the tail prototype, full test suite.
* **Phase 3 — future, parked**: capacity contributions (waits on
  capacity consumers), synth compatibility (item-data edit),
  biotech theming, implant-specific organ-bound conditions
  ("cyberware-era gold"), new-anatomy movement/emote flavor.

## 6 · Test contract

* **Equivalence**: human hit/damage resolution identical before and
  after the resolution refactor.
* **The rat fix, pinned**: a hit at a rat's tail resolves rat tail
  organs and applies damage.
* **Spec round-trip**: a non-species organ restores container,
  hit_weight, and flags through `to_dict`/`from_dict`; legacy
  snapshots still fall back to species lookup.
* **Install**: species gate (tail rejects on a rat), incision-at-
  anchor gate, slot + longdesc creation, repeat-install rejection.
* **Prehensile**: installed tail appears in `hands`, can hold;
  severance removes it from `hands` and drops held items.
* **Severance round trip**: severed tail is an organ item;
  reinstall restores anatomy, damage and conditions intact.
* **Persistence**: full character round-trip with an installed,
  damaged, bandaged tail.

## 7 · Maintenance contract

* §1 decisions change only by explicit design discussion.
* New anatomy questions MUST be answered from the character's
  organs (or longdesc surface), never by adding a new static
  species read.
* Augment items MUST carry complete organ specs — an augment whose
  organ can't survive a save/load round trip is a bug.
