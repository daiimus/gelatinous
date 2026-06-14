# Augment Abilities Spec — Toggled Cyberware

**Status:** approved design, implementation phased.  Settled in
discussion 2026-06-12.  Builds on `ANATOMY_AUGMENTS_SPEC.md` (the
substrate: the body is the truth).  First consumer: the shotgun
arm; the claw/teeth family follows on the same layer.

## 0 · The principle: abilities live on organs

An augment that *does* something (deploys a weapon, extends claws)
declares that ability **in its organ spec**, which the Phase 1
substrate already persists and severs correctly.  Installed means
the ability exists; severed or harvested means it's gone — no
separate registry, no bookkeeping to drift.

The second principle, discovered in the code: **held is wielded.**
Combat's weapon is literally whatever item sits in the `hands`
dict (`get_wielded_weapon` returns the first held item).  So an
integrated weapon that "consumes your hand" needs no new combat
plumbing — deploying it *fills the hand slot with the weapon item*,
which simultaneously makes the hand unusable for holding and makes
the weapon the active weapon.

## 1 · Settled design decisions

1. **One dispatcher command, prefix-keyed.**  `/<ability>` toggles
   (`/shotgun`).  The prefix lives in one constant
   (`CYBERWARE_COMMAND_PREFIX = "/"`); Evennia's parser matches the
   key as a prefix, so swapping to `=` later is a one-line change.
   Bare `/` lists your installed abilities and their states.
2. **Slot-consuming weapons fill the slot.**  Deploy moves a real,
   persistent, character-owned weapon item into the hand slot;
   retract removes it.  The item is locked against drop / give /
   steal and flagged `integrated` (disarm checks the flag) — it is
   bolted to your skeleton.
3. **Deploying auto-drops whatever the hand held** (user decision
   2026-06-12): the hand transforms regardless; the knife clatters
   to the floor.  No confirmation prompt.
4. **Active non-slot cyberweapons take precedence over held
   weapons** (user decision 2026-06-12): claws out means you fight
   with claws, knife in hand or not.  Weapon resolution order:
   active natural cyberweapon > held weapon > fists.  Toggle claws
   off to use the knife.
5. **First consumer: the shotgun arm** — the first *replacement*
   augment.  Acquisition is amputate-first: take the flesh arm off
   (combat or surgical amputation), then mount the gun arm over the
   stump via the existing re-augment path.  Requires the substrate
   to go multi-container (arm + hand), see §3.5.
6. **No ammo in v1.**  Ammo tracking exists nowhere (explicitly
   deferred); the shotgun arm fires forever like every other gun.
   This is the item that will eventually want it — revisit when
   ammo lands.
7. **Severance carries the hardware.**  A severed gun arm takes the
   shotgun with it — deployed (it's in the hand, the existing
   `detach_items_to_appendage` already does this) or retracted
   (folded into the arm; the severance hook moves the linked item
   onto the appendage).  Recoverable by harvest from the appendage,
   not by looting (locks hold).
8. **Theming stays in prose** (ANATOMY_AUGMENTS §4): claws, nailz,
   cyber-teeth, biotech variants are item data over the same
   ability types.

## 2 · Ability declaration

An organ spec (inside the item's `augment_organs`) gains an
`abilities` dict:

```python
"abilities": {
    "shotgun": {
        "type": "integrated_weapon",        # fills the hand slot
        "slot": "right_hand",               # which slot it consumes
        "weapon_prototype": "SHOTGUN_ARM_GUN",
        "deploy_msg": "...", "retract_msg": "...",
    },
    # The claw family (Phase 3):
    # "claws": {"type": "natural_weapon", "weapon_prototype": ...,
    #           "extend_msg": ..., "retract_msg": ...},
}
```

Ability names are the toggle words (`/shotgun`).  Runtime state
(`deployed: bool`, `weapon_dbref`) persists on the organ alongside
`stabilized` / `tourniqueted` — organ-level state, organ-level
round-trip, gone when the organ goes.

## 3 · Mechanics

### 3.1 · The dispatcher

`CmdCyberware`, `key = CYBERWARE_COMMAND_PREFIX`, in the default
cmdset.  Parses the remainder as the ability name, scans the
caller's organs for a matching ability, and dispatches by type.
Unknown name → list what you have.  No installed abilities → "you
have no cyberware to command."

### 3.2 · integrated_weapon toggle

Deploy: spawn the weapon item lazily on first use (prototype from
the ability spec; dbref recorded on the organ), auto-drop whatever
the slot holds (room message — the clatter is public), move the
item to the character, set `held_items[slot]`, organ state
`deployed = True`.  Retract: clear the slot, park the item at
`location = None` (off-grid — not in inventory, because it is
inside your arm), `deployed = False`.

Gates: the slot's anatomy must exist and not be severed; dead or
unconscious characters can't toggle; busy-state (active procedure)
blocks.

### 3.3 · The integrated item

Locked: `get:false()`, `drop:false()`, `give:false()`; flagged
`db.integrated = True` for the disarm path and inventory rendering
("(integrated)").  While deployed it appears held — correct, you
are visibly brandishing an arm-gun.

### 3.4 · natural_weapon precedence (Phase 3, designed now)

`get_wielded_weapon` gains the precedence rule: an organ-active
natural cyberweapon's item profile wins over held items.  Claws
spawn/park the same way; they just never touch `held_items`.

### 3.5 · Multi-container substrate extension

The tail assumed one new container.  The shotgun arm's
`augment_organs` span existing containers (`right_arm` +
`right_hand`), so:

* the already-has gate checks every container its organs declare;
* `augment_longdesc` becomes a list of entries (arm + hand keys
  restored over the stump);
* the anchor is the shoulder-side stump (`right_arm`), incised as
  usual;
* re-augment-over-severed-stump per container (already the rule).

Severance of a replacement augment uses the existing limb chain —
severing the cyber-arm takes the cyber-hand, exactly like flesh.

## 4 · The shotgun arm (first consumer)

`SHOTGUN_ARM` (right-side v1; left variant is data): replacement
organs `cybernetic_humerus` (container `right_arm`, bone-typed
actuator column, the §2 `shotgun` ability) + `cybernetic_metacarpals`
(container `right_hand`, `grasping`); anchor `right_arm`;
`compatible_species ["human"]`.  The gun itself: `SHOTGUN_ARM_GUN`
weapon prototype, shotgun damage profile, `is_ranged`, integrated
locks.  Install story: lose the arm, mount the gun.  The hand works
as a hand until you `/shotgun`.

## 5 · Phases

* **Phase 1 — ability layer**: ability declaration + organ runtime
  state, `CmdCyberware` dispatcher + prefix constant,
  integrated_weapon deploy/retract with auto-drop, item locks +
  disarm flag check, severance hardware-carry hook.
* **Phase 2 — the arm**: multi-container substrate extension
  (§3.5), `SHOTGUN_ARM` + `SHOTGUN_ARM_GUN` prototypes, operate-menu
  parity (the #515 path already routes augment items generically).
* **Phase 3 — the claw family**: natural_weapon type + weapon
  resolution precedence, claws/nailz/teeth prototypes.

## 6 · Test contract

* Toggle round-trip: deploy fills the slot and combat resolves the
  shotgun; retract restores the empty hand; state survives
  persistence round-trip.
* Auto-drop: deploying over a held item drops it to the room.
* Locks: the integrated item refuses drop/give/steal; disarm
  refuses on `integrated`.
* Gates: severed arm can't toggle; the ability vanishes with the
  organ.
* Severance: deployed and retracted both end with the hardware on
  the appendage.
* Multi-container: already-has gate across arm+hand; longdesc keys
  restored over a stump; chain severance intact.
* Precedence (Phase 3): active claws beat a held knife; deactivated
  claws yield to it.

## 7 · Cybernetics architecture — the standard templates

Settled 2026-06-13 after the shotgun arm shipped: **chassis +
module is the standard**; future cybernetics are data over these
five templates, never bespoke systems.  (Originally framed as four;
the #549 sharpening split "ability module" into a hardpoint module
and a distinct flesh-implant tier — see 4 and 5 below.)

1. **Replacement organ** (cyber heart / eye / kidney — the
   low-impact tier).  An organ item carrying its own spec installs
   into the existing slot via the replacement path, which rebuilds
   the organ: **same canonical organ name** (capacity tables key by
   name; theming lives in display prose — the standing principle),
   new spec (`inorganic`, adjusted HP).  **Shipped** (M1):
   `CYBERNETIC_HEART`; harvest writes `organ_spec` onto the item,
   `_resolve_install` rebuilds the slot from it.
2. **Anatomy augment** (the tail): new containers via the augment
   path.  **Shipped.**
3. **Limb chassis** (prosthetic arm / leg): augment over a stump or
   wreckage — and **side-agnostic**: one `CYBER_ARM` prototype
   mounts left or right, the surgeon names the side at install and
   the item's organ/longdesc/anchor templates resolve `{side}`.
   A chassis declares empty **hardpoint** organ slots and stamps
   `prosthetic_frame` on its frame organs (§9).  **Shipped** (M2/M3).
4. **Ability module** (shotgun, teeth/Jawz): an organ item carrying
   spec + ability that seats into a chassis **hardpoint**, inheriting
   its side/slot from the mount; its ability "just does its thing"
   from there.  **A module needs a hardpoint — that is the line**
   (sharpened #549; supersedes the earlier "hardpoint OR compatible
   flesh" framing).  **Harvest is the recovery verb**: a module comes
   out of a severed limb or corpse as the organ item it is.
   **Shipped** (M3): `SHOTGUN_MODULE` (a `CYBER_ARM` forearm
   hardpoint); `JAWZ` (a `CYBER_JAW` jaw hardpoint, #550).
   `CYBER_JAW` is the first **replacement organ that is itself a
   chassis** — it rebuilds the jaw slot (keeping talk/eat) *and*
   carries a `jaw` hardpoint for the bite module.  It installs via the
   replacement path (template 1), is surface-accessible (no cavity
   incision), then the module seats into its hardpoint.

5. **Flesh implant** (Nailz): the sibling tier, **not a module** —
   an ability grafted directly into LIVING anatomy (carbide claws
   into a flesh hand), no hardpoint, no chassis.  The host stays
   flesh and still bleeds; it has no `prosthetic_frame`, so it
   necroses and the limb doesn't reattach (the implant harvests out
   separately).  `module_mount: "flesh"` in code, but conceptually
   it's the implant tier, distinct from a hardpoint module.
   **Shipped** (M4): `NAILZ` + `NAILZ_CLAWS` — carbide claw body
   honed to a **monofilament edge** (the edge is the wire, not the
   claw; corrected #549).

The fused `SHOTGUN_ARM` was retired in favor of `CYBER_ARM`
(side-agnostic chassis, forearm hardpoint) + `SHOTGUN_MODULE`.
Fused all-in-ones may return later as flavor, but the standard
template is modular.

## 8 · Limb reattachment & the prosthetic frame

A severed limb is an `Appendage` carrying a medical snapshot of its
organs.  Two things determine what can be done with it:

* **Reattachment is a property of the FRAME, marked explicitly.**
  Only a limb whose frame was installed as a cybernetic prosthetic
  reattaches.  The chassis stamps `prosthetic_frame: True` on its
  frame organs at install (and the hardpoint-seated module keeps the
  flag); `is_cybernetic_limb()` returns True when **any** organ in
  the severed snapshot carries it.  This is NOT inferred from organ
  content — a limb can be flesh and chrome at once.  A flesh limb,
  even with cyberware implanted in it (Nailz on a flesh hand, a
  lone cyber sub-organ), has no frame: it necroses and does not
  reattach.  Flesh never reattaches; necrosis stands.
* **Components recover regardless of the limb.**  Whether or not the
  whole limb reattaches, its harvestable parts — a seated module, a
  replaceable organ — pull out via `harvest` and reinstall
  elsewhere.  Module-only salvage and whole-limb reattach are both
  valid; surgeon's choice.

**Reattachment is a lossless round-trip apart from two deltas:** the
limb's damage/condition travels with it (HP and wound stage are in
the snapshot and restored as-is — a shot-up arm reattaches shot-up),
and deployed weapons come back **retracted** (the deployed weapon
item does not survive the cut; the module re-spawns it on the next
toggle).  Everything else — chassis, seated module, frame flag,
side, longdesc — is preserved.

Mechanically: an installed prosthetic and its severed appendage are
the **same organs in two states**.  Install (`install <limb> in
<patient>`) and the `operate` chart both route a severed cyber limb
to the `install_limb` resolver, which rebuilds the organs from the
snapshot over a stump (amputate first — any compatible body, so
scavenged chrome bolts on), restores the carried longdesc, and
consumes the appendage.

**Severance narrative (chrome, #551).** The moment a prosthetic limb
comes off narrates as sheared hardware, not bleeding meat.
`get_severance_message(..., material="chrome")` reads a per-location
`CHROME_MESSAGES` bank (arms / hands / tail today), falling back to a
generic `cybernetic` module, then a blood-free generic template.  The
one fork lives in `apply_sever_to_character`, keyed on
`is_cybernetic_limb(appendage)` — the same `prosthetic_frame` marker
as reattachment above — so a flesh limb with cyberware in it still
bleeds.  The head/decapitation beat stays flesh (no cyber skull
exists).  Prose: sheared actuators, snapped cable looms, a coolant
hiss, dead-weight alloy clatter.

## 9 · Chrome rendering

Inorganic body locations render in a dark steel grey
(`CHROME_DEFAULT_COLOR` = `|=l`, `world/combat/constants.py`) rather
than the wearer's skintone — chrome is not flesh.  Coating items will
override this per augment when they exist; until then it is the
bare-metal default.  Limb longdesc is side-aware via the `{side}`
token (resolved at install), and a deployed integrated weapon
expands the limb's longdesc (`deployed_longdesc`) while replacing
the consumed hand's longdesc (`deployed_longdesc_slot`).

## 10 · Maintenance contract

* New toggleable cyberware declares a §2 ability — never a bespoke
  command or a character-level flag.
* The dispatcher prefix changes only via the constant.
* Weapon-resolution precedence (decision 4) changes only by design
  discussion.
