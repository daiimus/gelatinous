# Augment Abilities Spec — Toggled Cyberware

Toggled cyberware: augments that *do* something (deploy a weapon,
extend claws, modulate a voice) and the player switches on and off.
The design was settled in discussion 2026-06-12.  It builds on
`ANATOMY_AUGMENTS_SPEC.md` (the substrate: the body is the truth).  The
first consumer is the shotgun arm; the claw/teeth family (`NAILZ`,
`JAWZ`) uses the same layer.  This spec also holds the cybernetics
templates (§7), limb reattachment (§8) and chrome rendering (§9).

## 0 · The principle: abilities live on organs

An augment that does something declares that ability **in its organ
spec**, which the substrate persists and severs correctly.  Installed
means the ability exists; severed or harvested means it is gone — no
separate registry, no bookkeeping to drift.

The second principle: **held is wielded.**  Combat's weapon is whatever
item sits in the `hands` dict (the one door,
`world/combat/weapon_choice.py` `choose_weapon`, reads the hands;
MULTI_WEAPON_COMBAT_SPEC §4).  So an integrated weapon that "consumes
your hand" needs no new combat plumbing — deploying it *fills the hand
slot with the weapon item*, which at once makes the hand unusable for
holding and makes the weapon the active weapon.

## 1 · Settled design decisions

1. **One dispatcher command, prefix-keyed.**  `/<ability>` toggles
   (`/shotgun`).  The prefix lives in one constant
   (`CYBERWARE_COMMAND_PREFIX = "/"`); Evennia's parser matches the
   key as a prefix, so swapping to `=` later is a one-line change.
   Bare `/` lists your installed abilities and their states.
   `/system` is reserved: it prints the full cyberware diagnostic
   (`render_system`) instead of toggling.
2. **Slot-consuming weapons fill the slot.**  Deploy moves a real,
   persistent, character-owned weapon item into the hand slot;
   retract removes it.  The item is locked against drop / give and
   flagged `integrated`; disarm, wrest, throw and steal check the flag
   (steal checks it because its lift moves an item quietly without
   reading the lock, #3698) — it is bolted to your skeleton.
3. **Deploying auto-drops whatever the hand held** (user decision
   2026-06-12): the hand transforms regardless; the knife clatters
   to the floor.  No confirmation prompt.
4. **Active non-slot cyberweapons take precedence over held
   weapons** (user decision 2026-06-12), among the options that can
   reach (owner ruling 2026-10-03, MULTI_WEAPON_COMBAT_SPEC §4, §14
   ruling 2): in melee, claws out means you fight with claws, knife in
   hand or not; at range a held pistol fires while the claws stay out.
   Resolution order (`choose_weapon`): tagged weapons push untagged
   held items aside (with nothing tagged, only the hardest-hitting
   improvised item stays), then the range filter, then deployed
   natural cyberweapons over held weapons, then akimbo grouping, then
   the wheel (one option per attack, in slot order); fists when
   nothing is left (MULTI_WEAPON_COMBAT_SPEC §4-§6).  Toggle claws off
   to use the knife in melee.
5. **First consumer: the shotgun arm** — the first *replacement*
   augment.  Acquisition is amputate-first: take the flesh arm off
   (combat or surgical amputation), then mount a `CYBER_ARM` over the
   stump via the existing re-augment path and seat a `SHOTGUN_MODULE`
   in its forearm hardpoint.  This needs the multi-container substrate
   (arm + hand), §3.5.
6. **No ammo.**  Ammo tracking is explicitly deferred; the shotgun arm
   fires forever like every other gun.  This is the item that will
   eventually want ammo — revisit when ammo lands (see Unbuilt).
7. **Severance carries the hardware.**  A severed gun arm takes the
   shotgun with it — deployed (it is in the hand; the cut leaves
   integrated hardware where it lies, never on the floor, and the
   severance hook moves it onto the appendage, #3697) or retracted
   (folded into the arm; the same hook moves the linked item onto the
   appendage).  Recoverable by harvest from the appendage, not by
   looting (locks hold).  A HAND cut off a surviving gun arm instead
   folds the deployed gun back inside the arm (`location=None`,
   `deployed` False): nothing lies on the floor or the hand, and the
   next toggle is a deploy, refused until the hand is restored.
   Death parks every deployed weapon back inside the body
   (`park_all_hardware`: `location=None`, `deployed` False) before
   the corpse is made.  A limb cut off a corpse takes its hardware
   the same way, recorded retracted
   (`carry_snapshot_hardware_to_appendage`).  Harvesting a module or
   organ parks its weapon first (`park_organ_hardware`).
8. **Theming stays in prose** (ANATOMY_AUGMENTS §4): claws, nailz,
   cyber-teeth, biotech variants are item data over the same
   ability types.

## 2 · Ability declaration

An organ spec (inside the item's `augment_organs`) carries an
`abilities` dict:

```python
"abilities": {
    "shotgun": {
        "type": "integrated_weapon",        # fills the hand slot
        "slot": "{side}_hand",              # which slot it consumes (side resolved at install)
        "weapon_prototype": "SHOTGUN_ARM_GUN",
        "deploy_msg": "...", "retract_msg": "...",
    },
    # A natural weapon (NAILZ, on a hand organ):
    "nailz": {
        "type": "natural_weapon",          # off-grid, never in a hand
        "weapon_prototype": "NAILZ_CLAWS",
        "deploy_msg": "...", "retract_msg": "...",
        "deploy_room": "...", "retract_room": "...",
    },
}
```

Ability types (`_TOGGLERS` in `world/medical/augments.py`):
`integrated_weapon` (fills a hand slot), `natural_weapon` (an off-grid
weapon that never touches the hands), `voice_modulator` (`/modulate`,
`VOICE_MODULATOR`) and `blindsight` (`/blindsight`,
`TARGETING_PROCESSOR`).  The last two are covert: no room line.  Prose
keys: `deploy_msg`, `retract_msg`, `deploy_room`, `retract_room`, their
`_one` variants, `deployed_longdesc` and `deployed_longdesc_slot`;
without them a toggle uses its type's default prose.

Ability names are the toggle words (`/shotgun`).  Runtime state
(`deployed: bool`, `weapon_dbref`) persists on the organ alongside
`stabilized` / `tourniqueted` — organ-level state, organ-level
round-trip, gone when the organ goes.

An ability may live on several organs: one `NAILZ` tray seats into
both hands.  Each host keeps its own state and its own weapon item.
`/<ability>` acts on every living host: if any host is deployed, all
retract; otherwise all deploy (owner ruling 2026-10-05,
MULTI_WEAPON_COMBAT_SPEC §14 #5).  One self line and one room line
are spoken for the whole toggle; when exactly one host changed (a
surgical stow, a body down to one hand), the `_one` keys
(`deploy_msg_one`, `retract_msg_one`, `deploy_room_one`,
`retract_room_one`, with `{hand}`) are used, falling back to the base
keys.  The bare `/` listing shows each hand's state when they differ.

## 3 · Mechanics

### 3.1 · The dispatcher

`CmdCyberware`, `key = CYBERWARE_COMMAND_PREFIX`, in the default
cmdset.  It parses the remainder as the ability name, scans the
caller's organs for a matching ability, and dispatches by type.
Unknown name → list what you have.  No installed abilities → "you
have no cyberware to command."  `/system` is handled before the
ability lookup and prints `world.medical.cyberware_status.render_system`,
so no ability can be named `system`.

### 3.2 · integrated_weapon toggle

Deploy: spawn the weapon item lazily on first use (prototype from
the ability spec; dbref recorded on the organ), auto-drop whatever
the slot holds (room message — the clatter is public), move the
item to the character, set `held_items[slot]`, organ state
`deployed = True`.  Retract: clear the slot, park the item at
`location = None` (off-grid — not in inventory, because it is
inside your arm), `deployed = False`.

Gates, all in `toggle_ability` (`world/medical/augments.py`): the
slot's anatomy must exist and not be severed (an organ at 0 HP offers
no ability: `iter_abilities` skips it); dead or unconscious
characters can't toggle; busy-state blocks.

Ruled 2026-09-13 (#3360):

1. **Busy gate.**  No toggles while a procedure is active on the body
   (`world.medical.procedures.is_procedure_active`, the helper the
   surgical verbs use through `_reject_if_busy`,
   `commands/CmdSurgical.py`).
2. **The first element of any procedure stows the hardware at the
   cut**: `start_procedure` calls `stow_abilities_at(target, location)`,
   which retracts every deployed ability hosted at that location
   through the normal retract path (hands restored, room told).
   Hardware elsewhere on the body is left alone — a leg operation does
   not switch off a voice modulator.
3. **No channeled-act gate, by ruling**: a shotgun arm must deploy the
   moment combat starts, and sensory hardware (night vision, thermal)
   is designed to be used whenever; `refuse_if_channeling`
   (`world/channeled.py`, the house BLOCKED-class gate, which by design
   lives at its call sites) is intentionally not consulted here.

### 3.3 · The integrated item

Locked: `get:false()`, `drop:false()`, `give:false()`; flagged
`db.integrated = True` (both set by `_get_or_spawn_weapon`), which
disarm, wrest, give, drop, throw and steal check (steal's
reachable-inventory filter refuses an `integrated` item, #3698).  A
deployed integrated weapon reads as body, not as a held item:
`inventory` shows "A <weapon> is your <hand>.", and
`return_appearance` leaves it out of the wielded list and gives it its
own line ("<name>'s <weapon> is their <hand>.").  No "(integrated)"
label is shown.

### 3.4 · natural_weapon precedence

Natural precedence lives in the one door, `choose_weapon` in
`world/combat/weapon_choice.py`.  It lists `get_active_natural_weapons`
(every deployed host, its own object) as candidates, applies the range
filter, then natural precedence, then akimbo grouping (full order in
decision 4).  An organ-active natural cyberweapon wins over held items
among the options that can reach.  Every reader of the wielded weapon
(the swing, the gates, the initiate prose, the aim verbs, the sever
verb, the flee check) asks `choose_weapon`.

Claws spawn/park the same way as an integrated weapon; they just never
touch `held_items`.  Each Nailz hand owns one `NAILZ_CLAWS` (d6+6, +0
to hit, bank `nailz`); both out group into ONE attack on the `nailz`
row of `AKIMBO_PROFILES_BY_TYPE` (d6+9, +1, `nailz_akimbo`) —
placeholders, BALANCE_LEDGER.md.  Owner ruling 2026-10-06: Nailz has
its own pair; the held Voxhaul Tiger claw has
`tiger_claws` / `tiger_claws_akimbo`.  (Nailz used the `tiger_claws`
banks before that ruling.)

### 3.5 · Multi-container substrate extension

The substrate was built for the tail (an anatomy augment), which adds
one new container; a limb chassis's `augment_organs` span existing
containers (`CYBER_ARM`: `{side}_arm` + `{side}_hand`), so:

* the already-has gate checks every container its organs declare;
* `augment_longdesc` is a list of entries (arm + hand keys restored
  over the stump);
* the anchor is the shoulder-side stump (`{side}_arm`), incised as
  usual;
* re-augment-over-severed-stump works per container (the standing
  rule).

Severance of a replacement augment uses the existing limb chain —
severing the cyber-arm takes the cyber-hand, exactly like flesh.

## 4 · The shotgun arm (first consumer)

The shotgun is `SHOTGUN_MODULE`, a forearm-hardpoint module that
seats into a `CYBER_ARM` chassis on either side (§7, template 4);
`compatible_species ["human"]`.  Its `shotgun` ability is an
`integrated_weapon` with slot `{side}_hand` (resolved at install).
The gun itself: `SHOTGUN_ARM_GUN` weapon prototype (ranged,
`cybernetic_shotgun` weapon type, integrated locks).  Install story:
amputate the arm, mount `CYBER_ARM` over the stump, seat the module
in its forearm hardpoint.  The operate menu routes augment items
through the same generic path (#515).  The hand works as a hand until
you `/shotgun`.

## 6 · Test contract

* Toggle round-trip: deploy fills the slot and combat resolves the
  shotgun; retract restores the empty hand; state survives
  persistence round-trip.
* Auto-drop: deploying over a held item drops it to the room.
* Locks: the integrated item refuses drop/give; disarm, wrest, throw
  and steal's reachable-inventory filter refuse on `integrated` (#3698).
* Gates: severed arm can't toggle; the ability vanishes with the
  organ.
* Severance: deployed and retracted both end with the hardware on
  the appendage; a hand-only cut folds a surviving arm's gun back
  inside the arm (#3697).
* Multi-container: already-has gate across arm+hand; longdesc keys
  restored over a stump; chain severance intact.
* Precedence: active claws beat a held knife; deactivated claws yield
  to it.

## 7 · Cybernetics architecture — the standard templates

Settled 2026-06-13: **chassis + module is the standard**; future
cybernetics are data over these five templates, never bespoke
systems.  (Originally framed as four; the #549 sharpening split
"ability module" into a hardpoint module and a distinct flesh-implant
tier — see 4 and 5 below.)

1. **Replacement organ** (cyber heart / eye / kidney — the
   low-impact tier).  An organ item carrying its own spec installs
   into the existing slot via the replacement path, which rebuilds
   the organ: **same canonical organ name** (capacity tables key by
   name; theming lives in display prose — the standing principle),
   new spec (`inorganic`, adjusted HP).  Example:
   `CYBERNETIC_HEART`; harvest writes `organ_spec` onto the item, and
   `_resolve_install` rebuilds the slot from it.
2. **Anatomy augment** (the tail): new containers via the augment
   path.
3. **Limb chassis** (prosthetic arm / leg): augment over a stump or
   wreckage — and **side-agnostic**: one `CYBER_ARM` prototype
   mounts left or right, the surgeon names the side at install and
   the item's organ/longdesc/anchor templates resolve `{side}`.
   A chassis declares empty **hardpoint** organ slots and stamps
   `prosthetic_frame` on its frame organs (§8).
4. **Ability module** (shotgun, teeth/Jawz): an organ item carrying
   spec + ability that seats into a chassis **hardpoint**, inheriting
   its side/slot from the mount; its ability "just does its thing"
   from there.  **A module needs a hardpoint — that is the line**
   (sharpened #549; this replaced the earlier "hardpoint OR compatible
   flesh" framing).  **Harvest is the recovery verb**: a module comes
   out of a severed limb or corpse as the organ item it is.
   Examples: `SHOTGUN_MODULE` (a `CYBER_ARM` forearm hardpoint);
   `JAWZ` (a `CYBER_JAW` jaw hardpoint, #550).
   `CYBER_JAW` is the first **replacement organ that is itself a
   chassis** — it rebuilds the jaw slot (keeping talk/eat) *and*
   carries a `jaw` hardpoint for the bite module.  It installs via the
   replacement path (template 1), is surface-accessible (no cavity
   incision), then the module seats into its hardpoint.
5. **Flesh implant** (Nailz): the sibling tier, **not a module** —
   an ability grafted directly into LIVING anatomy (carbide claws
   into a hand), no hardpoint, no chassis.  One `NAILZ` tray
   implants into both hands (`flesh_containers`), skipping a hand
   that already carries it or has no living organ.  The host may be
   a flesh hand or a `CYBER_ARM` hand; a chrome host stays chrome and
   keeps its frame.  A flesh host stays flesh and still bleeds; it has
   no `prosthetic_frame`, so it necroses and the limb doesn't reattach
   (the implant harvests out separately).  `module_mount: "flesh"` in
   code, but conceptually it is the implant tier, distinct from a
   hardpoint module.  Example: `NAILZ` + `NAILZ_CLAWS` — carbide claw
   body honed to a **monofilament edge** (the edge is the wire, not
   the claw; #549).

The standard template is modular: `CYBER_ARM` (side-agnostic chassis,
forearm hardpoint) + `SHOTGUN_MODULE`.  The fused `SHOTGUN_ARM` was
retired in favour of it.  Fused all-in-ones may return later as
flavor.

Other consumers of the templates: `TARGETING_PROCESSOR` (forearm
module, `/blindsight`) and `VOICE_MODULATOR` (jaw module,
`/modulate`), template 4; `CYBER_LEG` (limb chassis), template 3; the
cyber eyes, ears and kidneys (`CYBER_LEFT_EYE` and its siblings),
template 1.  `ROBOT_SHOTGUN_MODULE` (deploying `ROBOT_ARM_GUN`) is the
robot-frame shotgun module; secbots are fitted with its spec at spawn
(`world/director/population.py`).

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
and deployed weapons come back **retracted** (the weapon item travels
with the severed limb and comes back with it: reattachment reclaims an
object lying on the appendage, parked and retracted, and the module
re-spawns one only if it is gone — MULTI_WEAPON_COMBAT_SPEC §9,
2026-10-05).  Everything else — chassis, seated module, frame flag,
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
`CHROME_MESSAGES` bank (arms / hands / tail), falling back to a
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
than the wearer's skintone — chrome is not flesh.  This is the
bare-metal default; coating items that override it per augment are
unbuilt (see Unbuilt).  Limb longdesc is side-aware via the `{side}`
token (resolved at install), and a deployed integrated weapon
expands the limb's longdesc (`deployed_longdesc`) while replacing
the consumed hand's longdesc (`deployed_longdesc_slot`).  Both
render only at chrome (inorganic) locations
(`_render_body_longdesc`), so a natural weapon's `deployed_longdesc`
on a flesh hand (Nailz) does not show.

## 10 · Maintenance contract

* New toggleable cyberware declares a §2 ability — never a bespoke
  command or a character-level flag.
* The dispatcher prefix changes only via the constant.
* Weapon-resolution precedence (decision 4) changes only by design
  discussion.

## Unbuilt

* 📋 UNBUILT (no issue) — **Ammo for the shotgun arm** (decision 6).
  Ammo tracking is deferred everywhere; the shotgun arm is the item
  that will eventually want it.
* 📋 UNBUILT (no issue) — **Coating items** (§9) that override the
  chrome colour per augment.

## Related documents

* `ANATOMY_AUGMENTS_SPEC.md` — the augment substrate.
* `proposals/MULTI_WEAPON_COMBAT_SPEC.md` — the one door
  (`choose_weapon`), akimbo grouping, per-host toggles, reattachment
  of the weapon object.
* `roadmaps/BALANCE_LEDGER.md` — the placeholder claw numbers.
