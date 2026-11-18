# Anatomy Augments Spec — Per-Character Anatomy

A character's anatomy is read from the character's own body, not from
the species table. The species table is the starting template; installs
and severance extend or reduce it per character. Augments (chrome, and
later vat-grown biotech) are items that carry their own anatomy and are
installed through the existing surgery verbs. The design was settled in
discussion on 2026-06-11. First consumer: the cybernetic tail.

## 0 · The principle: the body is the truth

**A character's actual organs are the runtime truth; the species table
is the starting template** — consulted once at character creation (and
as the fallback for legacy data), then extended or reduced per character
by installs and severance. `medical_state.organs` holds the live
per-character organ instances, and anatomy questions (what organs
exist, what can be severed, what can grasp, what renders) are answered
from them wherever a character is in hand.

What this buys beyond the tail: chrome vs vat-grown biotech is
*theming on the item* — the augment substrate doesn't know the
difference. Species expansion (synths) is an item-data edit, not a
code change. And the substrate is the foundation the cyberware era
keeps building on.

## 1 · Settled design decisions

These were decided in discussion (2026-06-11) and are not open for
silent revision:

1. **First augment: cybernetic tail.** Humans-only for now, gated
   by a species-compatibility list **on the item** — expanding to
   synths later means editing that list, zero code.
2. **Prehensile from day one.** The tail joins the character's
   grasping set: it can hold and wield. This deliberately breaks
   the static `grasping_containers` assumption.
3. **Full body integration, no capacity contributions in v1.**
   Capacities are normalized floors — an organ can only drag a
   capacity down, never boost past 1.0. Capacity extension waits for
   consumers (same parking decision as the fracture condition).
   Overturned in part: the decision rested on `moving` /
   `manipulation` having no consumers; they now have consumers
   (`CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC`; see
   `MedicalState.calculate_capacity_scoped`), and replacement augments
   contribute — CYBER_ARM and CYBER_LEG declare their organs under the
   canonical species names (`{side}_humerus`, `{side}_femur`, …), which
   are exactly the names the species capacity tables list, so chrome
   limb HP feeds `calculate_body_capacity` directly. What stays parked
   is capacity **extension** for anatomy the species table never
   declared: the capacity organ list is species-static, so the cyber
   tail contributes nothing (§5).
4. **Augment data lives on the item.** The item carries its own
   organ spec(s), anchor container, longdesc surface, and species
   list. No new DB entities, no registry until a second augment
   family demands one.
5. **Existing surgery is the whole interface.** Install via
   `incise` → `install` → `suture`; removal via `harvest`. No new
   verbs. A harvested augment is the existing organ item —
   reinstallable, conditions traveling with it. A severed augment is an
   Appendage carrying the organ snapshot; it reattaches whole when its
   frame carries `prosthetic_frame` (§3.5, §3.10).
6. **Trust/consent stays an open door.** Installing hardware in
   another character rides the same third-party-surgery door as any
   surgery, and trust/consent gates it there: the typed surgical verbs
   call `check_consent(caller, target, "heal")` before cutting
   (`commands/CmdSurgical.py`), so installing hardware in a conscious
   character who can contest requires their trust. The `operate`
   charting door finds its patient through the same `_resolve_target`,
   so every surgical door asks for `heal` trust (see
   `TRUST_AND_CONSENT_SPEC`). Nothing in this spec may assume
   surgeon == patient.

## 2 · Where anatomy is read

Each of these reads goes through the character's body (the static
table remains only as the no-character / legacy fallback, §3.2):

| Read | Where | Per-character |
|---|---|---|
| Hit-location selection | `select_hit_location` — `character.longdesc` keys | Yes — the body's surface |
| Location → organ resolution | `get_organ_by_body_location` / `select_target_organ` / `calculate_hit_weights_for_location` / `distribute_damage_to_organs` (`world/medical/utils.py`) | Yes — §3.2 |
| Organ spec round-trip | `Organ.to_dict` / `from_dict` | Yes — §3.1 |
| Install slot check | `CmdInstall` augment branch (`commands/CmdSurgical.py`) creates the slot | Yes — §3.3 |
| Severable containers | `MedicalState.location_severable_by_organ`; on corpses and severed parts `world/medical/removable.py` | Yes — §3.5 |
| Grasping containers | `Character.grasping_containers` / `hands` | Yes — §3.4 |
| Longdesc display order / regions | `typeclasses/appearance_mixin.py`; corpse renderer `typeclasses/corpse.py` | Yes — §3.6 |

No static species-only read of severability exists. Reading location →
organ from the static `ORGANS` global was a live species bug: a rat hit
at its tail resolved zero organs from the human table and the damage
silently no-opped (§3.2 fixes it).

**Loading a body.** `MedicalState.from_dict` builds the body from the
saved snapshot and adds a species-template organ back only when it is
neither present nor recorded removed. Absence is recorded in
`MedicalState.removed_organs`, written by `remove_organ` (the single
deletion door, used by augment install and reattach) and persisted by
`to_dict` as the names still absent. So an organ added to the species
table after a body was saved (`cervical_spine`, `nose`) still reaches
that body, and an organ removed on purpose never comes back at full HP
on load (#3400). Harvest and severance tombstones (0 HP) are unaffected.
A new sleeve (`reset_body_preserving_augments`) starts with an empty
list.

## 3 · Mechanics

### 3.1 · Organ spec persistence

`Organ.to_dict` includes `"data": self.data` (the spec dict).
`from_dict` passes it through as the `organ_data` override when
present; legacy snapshots without it fall back to the species lookup.
A non-species organ therefore restores its container, hit_weight and
flags. This is event-driven persistence (save on meaningful change),
not a hot path — the DB-write doctrine is untouched.

### 3.2 · Per-character organ resolution

Location → organ questions are answered by the character's
`medical_state.organs` (each organ knows its `container` and
`hit_weight`) wherever a character or medical state is in hand. The
static `ORGANS` scan remains only as the no-character fallback. This is
what makes a hit at a rat's tail resolve rat tail organs and apply
damage.

This sits on the per-attack combat path, so the hot-path rule applies.

### 3.3 · Augment install

Augment items declare (as attrs):

* `augment_organs` — `{organ_name: spec_dict, ...}` full organ
  specs, same shape as a species-table entry
* `augment_container` — the new body location (`"tail"`)
* `augment_anchor` — existing container the surgery opens
  (incision gate), e.g. `"back"` for the tail — you cut where the
  hardware mounts (base of the spine), and the new location grows
  from there
* `augment_longdesc` — one `{key, default_desc, display_after}` entry,
  or a list of them, for the rendering surface; a key the body already
  has gets its prose replaced. Side-agnostic items write `{side}` in
  their declaration, resolved from the side the surgeon names at
  install (`resolve_augment_declaration`)
* `compatible_species` — `["human"]` (the established cyberware /
  harvest-provenance species gate; one field everywhere)

`CmdInstall`'s augment branch runs: species check → incision at
the **anchor** (the slot doesn't exist yet; you cut where it goes) →
create the organ(s) with `organ_data` from the item → add the
longdesc key → persist. Install is refused while any living organ
(HP above 0) sits at a container the augment declares ("… still has a
living tail — the cybernetic tail mounts over a stump or wreckage, not
living anatomy."). A stump or destroyed remains admit the mount, and
the install clears them through `remove_organ`. A repeat install is
refused.

The operate menu reaches the same resolver: augment items list
alongside donor organs in the install picker, picking one records
the chart step at the item's anchor with no location prompt (the
item knows where it mounts), and the chart runner routes execution
to the augment resolver (`_resolve_install_augment`,
`world/medical/procedures.py`) — with the species and incision gates
re-checked there, since chart commencement bypasses the command's
pre-dispatch gates.

Install into a non-living body: see the chrome-removal rulings, ruling 5.

### 3.4 · Prehensile grasping

An organ spec may flag `"grasping": true`. The `hands` property
merges {containers of grasping-flagged organs present on the body}
with the species grasping set, minus severed. Severing the tail
therefore removes it from `hands`, and it drops what it held.

**Grasping requires functional anatomy:** a hand slot only grips when
it has a living organ at its container. Chain severance suppresses a
downstream wound (one wound at the cut point), so the wound-derived
severed set alone would miss a hand attached to a severed arm. The
`hands` property also drops any container whose organs are all
tombstoned (severed / harvested / pulped). A crushed-but-attached
hand can't grip either.

### 3.5 · Severance

A container is severable when it's in the species severable set
**or** any organ at it flags `"severable_container": true` (the
tail's spec does). The rule holds on living bodies, corpses and
severed parts alike: `removable.container_is_severable` /
`severable_containers` read it from the snapshot. The severed-part
pipeline builds from the character's organs, so the severed tail hits
the floor as an **Appendage** carrying the organ snapshot of the
cybernetic tail (`AUGMENT_ABILITIES_SPEC` §8), damage and conditions
intact. It reattaches via `install_limb` (§3.10).

### 3.6 · Rendering

The living longdesc renderer (`typeclasses/appearance_mixin.py`)
renders the species display order first, then every longdesc key not
in it, then every container the medical state knows that is still
missing. An augment location therefore renders after the **whole**
species order: the tail, whose hint is `display_after: "back"`, renders
after the feet, not after the back line. `display_after` is honoured
only at install time, where `_resolve_install_augment` inserts the key
into `character.longdesc` at that position; that ordering then holds
only among other extra keys. The design recorded 2026-06-11 placed an
added location after its `display_after` hint (or at the end of its
region) at render; honouring the hint at render is a code change, not a
spec change.

The Appendage renderer and the corpse renderer also append extras: the
corpse renderer (`typeclasses/corpse.py`) adds every container in the
death snapshot and every location a preserved wound names after the
species order (#3379), so a corpse renders an augment location. The
Appendage extras pass walks its garment coverage-map keys as well as
its longdesc keys, so a garment worn on an added-anatomy location
renders too (#3578). Wound rendering follows `display_location`.

**Chrome rendering:** a body location whose organs are `inorganic`
renders in the dark steel grey that matches the clothing palette's
black (`CHROME_DEFAULT_COLOR = "|=l"`, `world/combat/constants.py`;
#545) instead of the wearer's skintone — chrome is not flesh. Limb
longdesc is side-aware via the `{side}` token (resolved at install).
A deployed integrated weapon expands the limb's longdesc and
replaces the consumed hand's — see `AUGMENT_ABILITIES_SPEC` §9.

### 3.7 · The body is the single truth (the anatomy-truth standard)

The character's `organs` dict is the **only** source of present
anatomy; nothing auto-creates. `get_organ` returns existing-or-`None`
— it never lazily creates from the species table (lazy creation is a
zombie-organ factory: capacity math iterating species lists by name
would resurrect install-deleted flesh organs at full HP). Absence is
meaningful, and it is **recorded**: `MedicalState.removed_organs`
(written by `remove_organ`) holds the names taken out of this body on
purpose, so the loader can tell a deliberate absence from a
species-table organ the body predates (the latter is added back on
load; the former never is; §2, #3400). Harvest keeps a separate
record, `db.removed_organs` on the body: a harvested organ stays in the
organs dict at 0 HP with `injury_type` set to `"harvested"`, and
`MedicalState.organ_is_gone` reads either marker, so no healing path
regrows it. An install clears the body record
(`procedures._clear_removed_record`).

Severed organs persist as **0-HP `"severed"` tombstones** — they
ARE the stump, and they are load-bearing: wound rendering, the
`hands` functional gate (§3.4), capacity loss, and the re-augment
"stump or wreckage" gate all read them. Augment / reattach installs
clear tombstones at their containers when new anatomy takes the
slot. Capacity math skips absent organs — a mounted replacement
implicitly restores capacity; a bare stump keeps dragging it down
via its tombstone.

### 3.8 · Inorganic organs

An organ spec flag `"inorganic": true` marks chrome. Damage to an
inorganic organ yields **pain only** — no bleeding, no infection
(chrome doesn't hemorrhage or go septic; pain is neural feedback
from the graft). Severed inorganic parts get cybernetic part prose
and a `"cybernetic <part>"` name instead of flesh ("muscle firm…
cartilage"). A robot or synth limb keeps its species name (#3362): the
`"cybernetic <part>"` name is for chrome on a flesh body. A harvested
chrome organ takes the item name it was installed under
(`chrome_provenance`, #3489; see the chrome-removal rulings, ruling 3).

The **severance moment** is forked too (#551): a prosthetic limb's
detachment narrates as sheared hardware, not bleeding meat.
`get_severance_message(..., material="chrome")` routes to a
per-location `CHROME_MESSAGES` bank (then a generic `cybernetic`
fallback module). The fork keys on `is_cybernetic_limb` — the same
`prosthetic_frame` marker as reattachment (§3.10) — so a flesh limb
with cyberware implanted in it still bleeds. See
`AUGMENT_ABILITIES_SPEC` §8.

### 3.9 · Heal & reset

`MedicalState.full_heal()` (the `@heal` backend) restores
**present anatomy only** — tombstones are absence records, not
injuries, so healing never regrows a severed limb or resurrects a
harvested-out module (which would duplicate its ability). It
preserves cyberware toggle state (a deployed gun is not an injury).
`@resetmedical` rebuilds flesh from the current species table but
**preserves installed augments** via `is_augment_organ()` (no
species-table entry, or `inorganic` / `abilities` / `hardpoint` /
`module_type` markers) — a wholesale nuke would erase every
installed limb, tail, heart, and module.

### 3.10 · Reattachment & the prosthetic frame

Reattaching a whole severed limb is gated on an explicit
`"prosthetic_frame": true` marker stamped on a chassis's frame
organs at install — never inferred from organ content. Flesh never
reattaches (necrosis), even with cyberware implanted in it; only a
prosthetic frame bolts back on. `install` reattaches a severed
prosthetic-frame part whole through the limb path
(`_resolve_install_limb`), damage and conditions intact. Full mechanics
in `AUGMENT_ABILITIES_SPEC` §8.

## 4 · The cybernetic tail (first consumer)

**Augments mirror flesh organ architecture** (settled 2026-06-11):
the tail location carries a skeletal organ the way a rat's tail
carries `tail_vertebrae`, so every existing treatment surface works
uniformly — a bone-typed cyber organ is splintable ("brace the bent
actuator column"), tourniquetable, severable, with no special
cases. The same principle governs *replacement* cybernetics: a
cybernetic hand keeps the canonical slot/organ structure of the flesh
hand (the metacarpals are still there, structurally) and theming lives
in display names and item prose, never in the slot keys.

Prototype `CYBERNETIC_TAIL`: organ `cybernetic_tailbone` at
container `"tail"` (`"tail"` is in `LIMB_CONTAINERS`, so tourniquets
gate correctly), bone-typed, modest HP, common hit weight,
`severable_container`, `grasping`, `inorganic` (chrome: pain only,
steel-grey render, §3.8) and `prosthetic_frame` (a severed tail shears
as hardware and reattaches whole, §3.10); anchor `"back"` (the mount
bolts to the base of the spine — you incise where it attaches);
`compatible_species ["human"]`. Future biotech variants are new
prototype text over the same attrs.

The chassis+module cyberware standard built on this substrate lives in
`AUGMENT_ABILITIES_SPEC` §7.

## Chrome removal (owner rulings 2026-09-13/14)

1. **Anything installed can be uninstalled.** One predicate answers
   "what can come off this body" for every door --
   `world/medical/removable.py` (`can_harvest_organ` /
   `harvestable_organs` / `container_is_severable` /
   `severable_containers`), read by the typed `harvest`, the `operate`
   chart, `_resolve_harvest` itself (so a chart step cannot bypass it),
   and all three corpse severance gates in `commands/forensics.py`.
   Harvest = the species harvest axis OR a grafted augment; severable =
   the species set OR any organ at the container flagging
   `severable_container` -- from the SNAPSHOT, so corpses and severed
   parts answer like the living (#3380, #3381).
2. **Robots are robots.** Native anatomy is whatever the body's OWN
   species table declares -- a robot's arm bone is robot anatomy, not
   chrome, even though it is inorganic. `is_grafted` treats an organ as
   chrome only when the table does not know it (tail, hardpoint,
   module) or when it carries augment markers the table's own entry
   lacks (a cyber humerus on a human). Robot parts are gated behind the
   robot species; the **junkyard salvager** (future) handles them, not
   the Ripper.
3. **Chrome doesn't rot.** A skeletal body still yields its grafted
   inorganic parts; only flesh is gone.
   - **Harvested chrome comes back as itself (#3489):** every install
     door (`_resolve_install`, `_resolve_install_module`,
     `_resolve_install_augment`) stamps the ITEM's identity into the
     organ spec as `chrome_provenance` -- key, desc, `from_prototype`
     tag, `compatible_species`, `value`/`brand`, and the flesh-mount
     fields (`module_mount`, `flesh_containers`, `flesh_organ`).
     `_configure_harvested_item` (the one stamping site behind both
     harvest doors and `strip`) reads it back for any organ
     `is_grafted` says is chrome: no decay prefix, condition from the
     part's OWN HP (66% of max or more pristine, else damaged), the
     original name/prose (falling back to "cybernetic <part>" with the
     severance-bank prose for pre-provenance installs), the original
     compatibility list restored, value and prototype tag restored for
     appraisal, and every resolved side word re-templated to `{side}`
     so a module pulled from a left arm seats correctly on a right one.
     Flesh organs are untouched: species-named, decay-prefixed,
     single-species.
   - **The prose comes down with the chrome (#3491):** the augment
     install records the longdesc keys it surfaced
     (`augment_longdesc_keys`) on each organ it adds, and
     `_mark_organ_removed` drops a key once the location it names has
     no live organ left -- on the living body's `longdesc` and on a
     corpse's `longdesc_data`. An install with no recorded keys (made
     before #3491) has its container key dropped only when that
     container is an added location the species table never lists (the
     tail); native prose (a cyber arm over a stump) is never touched by
     guesswork. With the prose gone the surgery mark still shows: the
     living renderer (`AppearanceMixin._get_visible_body_descriptions`)
     walks every container the medical state knows after the species
     order, so a location with no longdesc key renders its wounds
     through the standalone-wound path (#3493, the living half of
     #3379).
   - **Organic harvested organs carry a harvest timestamp (#3498):**
     `_configure_harvested_item` stamps
     `db.harvested_at = world.gametime.stamp()` (real POSIX seconds,
     subtract with `since`) on every non-grafted harvest -- both doors
     and `strip` -- and `Organ.at_object_creation` declares the field as
     `None`. Chrome is never stamped. **No consumer yet:** the
     viability / refrigeration gate is a recorded gap in
     GIG_RIPPER_SPEC §6 whose prerequisite is this stamp plus the
     untuned decay pass.
4. **Chrome stays on your corpse; you re-sleeve as a flesh bag.** Death
   costs you your augments -- that is what the secondhand market is
   priced on. **Its hardware stays with it (#3486, #3487, #3496):** the
   corpse factory calls `park_all_hardware` BEFORE the medical snapshot
   and the contents sweep, so a weapon deployed at the moment of death
   folds back inside the arm (`location=None`, dbref kept on the
   organ's `ability_state`) instead of landing locked and undroppable
   in the corpse; and every corpse-sever door -- the typed `sever`, the
   amputate chart, and the corpse-side head spawn in
   `typeclasses/death_progression.py` (used only when no head was
   spawned at the killing blow) -- lands on
   `Appendage.configure_from_sever` /
   `SeveredHead.configure_from_sever`, where
   `carry_snapshot_hardware_to_appendage` moves the parked weapon onto
   the severed part and records it retracted. One seam, not one per
   caller. A combat decapitation normally spawns the head at the
   killing blow, while the body is still alive
   (`spawn_severed_head_for_living` →
   `SeveredHead.configure_from_living_decap`), and that path does not
   carry hardware onto the head.
5. **Install into a non-living body makes sense only for robots and
   maybe bioroids -- they can be rebuilt.** Organics: living targets
   only (the #2455 decision stands). Every install door refuses a
   target with no medical state. 📋 UNBUILT (no issue): install into a
   non-living robot or bioroid body.

## 5 · Unbuilt

Phase 3 — future, parked:

* Capacity contributions (parked; the original blocker, no capacity
  consumers, no longer applies — the parking holds because the work is
  not done). What is still unbuilt is capacity **extension** — added
  anatomy such as the tail contributing to, or introducing, a capacity
  the species table never declared (§1 decision 3).
  `specs/roadmaps/MEDICAL_SUBSTRATE_ROADMAP.md` records it as an
  un-catalogued substrate concern to fold into movement-policing /
  senses / equipment-handling when those are scoped, and
  `specs/roadmaps/MEDICAL_SUBSTRATE_READINESS.md` owns the row.
* Synth compatibility (item-data edit).
* Biotech theming.
* Implant-specific organ-bound conditions ("cyberware-era gold").
* New-anatomy movement/emote flavor.

Elsewhere in this document:

* 📋 UNBUILT (no issue): install into a non-living robot or bioroid body
  (chrome-removal ruling 5).
* The junkyard salvager for robot parts (future; chrome-removal
  ruling 2).
* The viability / refrigeration gate that would consume `harvested_at`
  is a recorded gap in GIG_RIPPER_SPEC §6 (chrome-removal ruling 3).

## 6 · Test contract

These must hold:

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
* **Severance round trip**: the severed tail is an Appendage carrying
  the organ snapshot; `install` reattaches it whole through the limb
  path (`_resolve_install_limb`), damage and conditions intact.
* **Persistence**: full character round-trip with an installed,
  damaged, bandaged tail.

## 7 · Maintenance contract

* §1 decisions change only by explicit design discussion.
* New anatomy questions MUST be answered from the character's
  organs (or longdesc surface), never by adding a new static
  species read.
* Augment items MUST carry complete organ specs — an augment whose
  organ can't survive a save/load round trip is a bug.

## Not decided

* Whether Phase 3 (§5) should now be re-scoped to the narrower capacity
  **extension** item is an owner call.

## Related documents

* `AUGMENT_ABILITIES_SPEC.md` — chassis+module standard (§7),
  severance, reattachment and the prosthetic frame (§8), deployed-weapon
  rendering (§9).
* `CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC.md` — capacity consumers.
* `TRUST_AND_CONSENT_SPEC.md` — the consent gate on surgery.
* `LONGDESC_SYSTEM_SPEC.md` — longdesc rendering and chrome colour.
* `proposals/GIG_RIPPER_SPEC.md` §6 — the harvested-organ viability gap.
* `roadmaps/MEDICAL_SUBSTRATE_READINESS.md`,
  `roadmaps/MEDICAL_SUBSTRATE_ROADMAP.md` — capacity extension.
