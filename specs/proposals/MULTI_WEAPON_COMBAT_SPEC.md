# Multi-Weapon Combat Specification

A character can fight with more than one weapon: claws in each hand, two pistols, a pistol and a knife, claws and fangs. This spec covers claws per hand, akimbo profiles by weapon type and count, alternation between held weapons, handguns, the grip, and species with many hands. In short: each hand owns its claws; one function, `choose_weapon`, answers "what weapon" for every gate, attack and line of prose; akimbo pairs are weapon-type data; among the options that can reach, the swing rotates one option per round in a stable hand order; `/nailz` acts on every host; handguns follow the same rule; nothing assumes two hands. It supersedes defect #3571.

## 0. Owner rulings (2026-10-01, verbatim)

On today's claws: *"I just don't like how this is setup. If a hand is severed, where do the claws go? It's kinda wonky."*

On the per-hand model: *"The model is good. For combat, we'd alternate between weapons except for specifically designed Akimbo weapons like cybernetic claws or Tiger Claws which can discern from individual vs Akimbo as part of the design. This could be something we eventually shift to for other weapons like handguns. It does get tricky with the Mr. Hands system though - where someone could hold many, many weapons. So we'll want room to grow and address things but our point of entry will be small."*

*"Messages I agree on. Toggle should do both. We'll also want damage/hit/etc weapon values to be based on if its one or both."*

*"Placeholders are fine. I think you should figure out the alternation and handguns for the spec though. The system should be comprehensively design before we implement the first slice otherwise it might as well be a hallucination."*

Standing rulings this design keeps: active natural cyberweapons take precedence over held weapons (`AUGMENT_ABILITIES_SPEC.md` decision 4, 2026-06-12); a severed limb takes its gear (decision 7); extra grasping limbs buy no extra attacks and no raw damage (the Q2 guardrail in `CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC.md`, 2026-06-20): the manipulator count pays through initiative, loadout readiness and disarm resistance only. The event-triggered bonus attacks (a failed advance or charge) are untouched.

## 1. Why

The Nailz tray seats one ability, `nailz`, into both hands (`flesh_containers` = left and right hand, `world/prototypes.py`). When both hands shared one claw object and one deployed flag, cutting one hand took both hands' claws to the floor while the other hand still read deployed, and reattachment left the other hand with a dead reference (#3571). Combat had no two-weapon concept, and its several weapon resolvers disagreed with each other. Each hand now owns its claws, and one function chooses the weapon.

## 2. Design at a glance

1. **Each hand owns its claws** (§3, §9).
2. **One door for "what weapon"**: `choose_weapon` in `world/combat/weapon_choice.py` (§4).
3. **Akimbo is weapon-type data**: `AKIMBO_PROFILES_BY_TYPE` (§5).
4. **Alternation is the general rule**: one option per round, in a stable hand order; an akimbo group rotates as one option (§6).
5. **Toggle acts on every host** (§8).
6. **Handguns follow the same rule** without new code (§10).
7. **Nothing assumes two hands** (§11).

## 3. Data model

**Organs.** Both hands keep the ability name `nailz`. Each host's `organ.ability_state["nailz"]` = `{deployed, weapon_dbref}` is the truth; nothing copies state from one host to another. `_get_or_spawn_weapon` writes the dbref into the state it is given, so each host spawns its own object: one object per hand. The install loop seats the ability into each `flesh_containers` host.

**Legacy shared references.** A stored body may still have every host of an ability pointing at one object. Every toggle settles this first, over all living hosts whichever are being toggled (a surgical stow passes one): the host whose hand holds the object keeps the reference, otherwise the first in organ order; the others let go (`_disown`, `world/medical/augments.py`). A host that lets go while deployed: a natural weapon spawns its own at once, off-grid and silent, so the hand keeps fighting; an integrated host's hand never held the shared gun, so its deployed flag is cleared, and it gains its own gun on its next deploy. Nothing is deleted.

**Taking an object back.** On deploy, a host's existing object is used as it stands when it is parked off-grid or on the body. One lying on a severed appendage is carried off: the host unlinks it and spawns its own, and chrome reattachment (§9) is what reclaims the carried one (flesh never reattaches, so a flesh hand's carried claws stay with the appendage). One lying anywhere else is taken back. Taking back presumes one owner: severance settles a shared reference (§9), so no deploy reaches into another body's hand. The take-back is a safety net: a hand-only cut leaves integrated hardware to the hardware carry, which folds a surviving arm's gun back inside the arm, parked and retracted, so a deployed forearm gun is never dropped to the floor locked and undroppable (#3697).

**Natural lookup.** `get_active_natural_weapons(char) -> [(host_container, item)]` (`world/medical/augments.py`): living, deployed hosts in organ order, returning only items whose `location` is None (parked in the body). An object lying on a severed appendage is not a weapon anyone fights with.

**Weapon attributes** (read with defaults; never written onto existing items):
- `hit_bonus` (int, default 0): a to-hit term added beside the charge bonus.
- Pairing is not an item attribute: `AKIMBO_PROFILES_BY_TYPE[weapon_type]` = `{count: overrides}`, overrides limited to `damage`, `hit_bonus`, `weapon_type`, `damage_type`. Count 1 is the item's own attributes. Rows: `nailz`, `tiger_claws`, `light_pistol`.

**Constants** in `world/combat/constants.py`: `WEAPON_ATTR_HIT_BONUS`, `WEAPON_ATTR_HANDS_REQUIRED`, `AKIMBO_PROFILE_FIELDS`, `AKIMBO_PROFILES_BY_TYPE`, `NDB_LAST_WEAPON_SLOT`. A one-weapon bank is named by the prototype's `weapon_type`; a pair bank is named by its row in `AKIMBO_PROFILES_BY_TYPE`.

**`NAILZ_CLAWS`** is one hand: five blades, placeholder damage 6, `weapon_type` `nailz`; its pair row in `AKIMBO_PROFILES_BY_TYPE` is `{2: {damage: 9, hit_bonus: 1, weapon_type: "nailz_akimbo"}}`. An owner with both hands fights at damage 9.

**`WeaponChoice`** (frozen dataclass): `items` in slot order, `slots`, `lead_slot` (the host container for a natural weapon, the first grasping slot for a held one; the wheel's key), `hands_required`, `damage`, `hit_bonus`, `damage_type`, `weapon_type`, `is_ranged`, `natural`; `.item = items[0]`; `.akimbo = len(items) > 1`. `None` means unarmed.

## 4. One door: `choose_weapon`

`choose_weapon(char, target=None)` (`world/combat/weapon_choice.py`) returns a `WeaponChoice`. Every gate, every attack and every line of prose asks it. It is a pure peek. Rule order:

1. **Candidates** in slot order: natural options, then held items, de-duplicated by object. An object found in two slots is one option with both slots; no command puts one object in two slots, since the grip is implicit (`GRIP_ENFORCEMENT_SPEC.md` §2).
2. **Real weapons**: if any held item is tagged `weapon`, drop untagged items (the #516 rule). With nothing tagged, keep only the single highest-damage improvised item, so nothing rotates a cigarette.
3. **Range**: with a target not in melee range, ranged options only; with none, keep all so the existing reach message fires.
4. **Natural precedence** (decision 4, applied among the options that can reach): if any deployed natural weapon survived the range step, only naturals count. Ruled 2026-10-03 (§14, ruling 2): at range a held pistol fires while the claws stay out; in melee deployed claws win outright and the knife waits.
5. **Akimbo grouping** (§5).
6. **The wheel** (§6): the next option after the last slot that swung.

`weapon_options()` returns the ordered wheel (§11).

`has_ranged_option(char)` = any real option is ranged (step 3 cannot change that answer, so it takes no target); the "is the weapon ranged" gates use it, so a knife sorting first does not block a pistol. `choose_weapon(char, at_range=True)` is the aiming peek: the option that would fire at range, so the aim, aim-stop and move-while-aiming lines name the gun the gate approved rather than the claws or the heavier blade that would swing in melee; a target aim names `choose_weapon(char, target)`. One helper, `aimed_weapon_name(char, target=None)`, speaks for every aim, stop and move-while-aiming line. It is worked out when the line runs: a stop after melee range changed mid-aim (a retreat) names what would fire now, not what the aim line named. Text only; accepted (review 2026-10-05).

**Callers.** `process_attack` (`world/combat/attack.py`) reads every value from the choice. Forensics takes the first option that can sever (`_blade_in_hand`, `commands/forensics.py`). No other function picks the wielded weapon (No Compat Seams). `find_best_weapon` (`world/combat/utils.py`) is not a wield selector: it is the draw picker over a body's whole inventory (what an NPC pulls when caught off guard, `world/director/civilians.py`, `world/souls/jobs.py`), and it stays separate. Manipulation is the minimum over `choice.slots`; a natural on a grasping host scopes to that hand, Jawz stays body-wide (a head-scoped manipulation fails open to 1.0 in `world/medical/core.py`, a silent buff). No broad `except`.

## 5. Akimbo profiles by deployed count

Grouping runs after the range filter. Members = options of one `weapon_type` that has a row in `AKIMBO_PROFILES_BY_TYPE`, distinct objects, in slot order; n = member count. k = the largest key in that row with k ≤ n. With no such key, or n = 1, members stay single. k members become ONE option: the lead item's attributes overlaid with the row's profile for k (profile fields only). Leftovers regroup by the same rule or rotate singly. Three claws never ride a count-2 profile with the third absorbed. One item is its own values and its own bank. An akimbo group keeps its slot place on the wheel.

**Nailz placeholders:** one hand d6+6, +0 hit, bank `nailz`; both hands d6+9, +1 hit, bank `nailz_akimbo`. A severed or retracted hand drops n to 1 on the next swing with no state to clear.

**To-hit:** `attacker_roll += choice.hit_bonus`, beside the existing +2 charge bonus in `process_attack` (`world/combat/attack.py`). It defaults to 0 and is never written onto items, so no other weapon changes. Damage stays d6 + `choice.damage`; injury type from `choice.damage_type`. Manipulation = min over the group's slots, so the weaker hand drags.

**Grip (`hands_required`, §14 #13).** Every item is written `hands_required` 1 at creation (`typeclasses/items.py`); `choose_weapon` carries the value on `WeaponChoice.hands_required`. It is enforced by the implicit grip of `GRIP_ENFORCEMENT_SPEC.md` (its rulings in §6, the grip model in §2, all 2026-10-06): a two-handed weapon sits in one hand, and a free grasping slot anywhere on the body is its second hand. Effective skill is multiplied by `grip_hit_factor(choice, free_slots)` (`world/combat/capacity.py`), where `free_slots` counts the attacker's empty grasping slots. It is 1.0 unless the choice wants more hands than it holds plus the free slots; then the weapon is under-gripped and the factor lowers the attacker's skill. The swing is never refused. Natural and integrated weapons never under-grip. The wheel sees one option. Prototypes that declare `hands_required` 2: the ranged base (inherited by the long guns), the anti-material rifle, the baseball bat, the staff and the chainsaw.

**Guardrail:** the uplift belongs to a designed pair, which costs a second implant or item. It is one attack and is never paid per surplus limb.

## 6. Alternation

The unit of rotation is an option: one weapon or one akimbo group. Still one scheduled attack per combatant per round (one `_schedule_attack` per combatant in `world/combat/handler.py`), plus the event-triggered bonus attacks. Alternation changes WHICH option swings, never how many.

**Order.** `Character.hands` iterates in the species' `anatomical_display_order` (left hand first), then unlisted slots such as a tail alphabetically (`Character.slot_order`). This is also the default hand for wield, get and disarm, for everyone; there is no dominant hand (§14 #8).

**Cursor.** `NDB_LAST_WEAPON_SLOT` on the attacker holds the lead slot of the last option that swung. Next = the first option whose lead slot sorts after it, wrapping. Unset, or one option: the first. Keyed by slot, so disarm, severance or a new wield self-heals. Cleared in `cleanup_combatant_state` (`world/combat/utils.py`), beside the ndb attributes it already clears, because both `remove_combatant` and the handler's end-of-fight `cleanup_all_combatants` reach it and a fighter still standing when a fight ends never passes through `remove_combatant`; so each fight starts at the first slot and the initiate line names the first swing. Kept on ndb rather than the combat entry because advance and charge resolve inside `at_repeat`, which writes its snapshot back over `db.combatants`; a reload only restarts the wheel.

**Peek vs commit.** Every caller peeks. `process_attack` commits via `note_weapon_used(attacker, choice)` only after the reach and proximity gates pass, so a failed reach does not turn the wheel. Bonus and opportunity attacks are real swings and commit.

Alternation replaces "then highest damage" (`CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC.md` §6.1); range-first stays. Initiate, aim and stop prose peek the same wheel. Accepted text drift (review 2026-10-06): a delayed swing already scheduled at an old target still commits when it lands, so an initiate spoken at a new target in between can name an option the next swing then skips; text only, and the retarget itself is pre-existing behaviour.

## 7. Messages

**Bank pair convention:** the base bank is one weapon; `<type>_akimbo` is the designed pair. Bank = `choice.weapon_type`; the loader needs no change. `COMBAT_MESSAGE_FORMAT_SPEC.md` §Bank pairs holds the authoring rule for pair banks.
- Nailz has its own pair (§14 #10): `nailz` (one hand) and `nailz_akimbo` (both hands). The prototype's `weapon_type` names `nailz`; only the `nailz` row of `AKIMBO_PROFILES_BY_TYPE` names the pair bank. `tiger_claws` and `tiger_claws_akimbo` belong to the held Tiger Claws (§13).
- The `nailz_akimbo` prose suits an implant: no gloves, no belt, no "five blades", no self `{hit_location}`.
- The one-hand `nailz` bank covers all four phases; a missing kill falls to the flat generic line.
- A pair bank's lines may name the lead item with `{item_name}`; the `nailz_akimbo` bank does not.
- All seven weapon-bank reads use `choice.weapon_type` with `item=choice.item`: hit, miss and kill in `world/combat/attack.py`; three initiate reads in `commands/combat/core_actions.py` (aiming-direction, local, and the target's defensive line); the auto-retarget initiate in `world/combat/utils.py`.
- No `{hand}` in combat banks for v1; it would bind all seven sites.
- `get_combat_message` swallows errors, so both claw banks must be tested across all four phases.

**Toggle prose.** Base keys stay the all-hosts prose. The keys `deploy_msg_one`, `retract_msg_one`, `deploy_room_one`, `retract_room_one` (constants beside `CYBERWARE_COMMAND_PREFIX`) are used when exactly one host changed, whatever was dispatched or lives: a surgical stow of one hand, or a body down to one hand (#3700); an ability without them falls back to its base keys. They carry `{hand}`, pre-interpolated before `msg_room_identity`. `deployed_longdesc` is one-hand prose with no `_one` variant: it renders once per chrome location. Room lines stay on `msg_room_identity`.

## 8. Toggle

`/nailz` is one word acting on every living host. Rule: if ANY living host is deployed, retract every deployed host; otherwise deploy every host (§14 #5). One predicate, `is_ability_deployed(char, name)` = any living host deployed; the director's draw and stow paths read it and still reach all-retracted from a mixed state in one toggle. Each per-type toggle acts on ONE host (a natural toggle spawns or reuses that host's object; an integrated toggle seats that host's object in that host's slot); `_dispatch_toggle` loops the hosts and sends one self line and one room line. So two forearm shotgun modules give each arm its own gun.

`stow_abilities_at` dispatches only the hosts at the procedure location (#3360: hardware elsewhere on the body is left alone).

**Readouts.** `list_abilities` names the hands only when they differ; the cyberware status screen shows "both hands" or "left deployed / right retracted"; the sdesc names the first deployed natural weapon's item, in organ order (`get_active_natural_weapons`), not the wheel's peek.

**Other abilities.** Voice and Jawz have one host (the cyber-jaw hardpoint); nothing changes for them. Blindsight can have two hosts (a targeting processor in each cyber arm): it reads as any-deployed and is unaffected in play, but the per-host toggle and the readouts must cover it like the shotgun pair.

## 9. Severance and reattachment

**Severance.** `carry_hardware_to_appendage` (`world/medical/augments.py`) walks the chain's organs, moves each organ's OWN object onto the appendage and marks it retracted. With per-host objects the cut hand takes exactly its own claws. It also settles a legacy shared reference at the cut, by the keeper rule: an object a surviving hand still holds stays with that hand and the limb's entry lets go; otherwise the limb takes the object and every host left on the body that still points at it lets go (as in §3). An object already lying on another character or limb (a stale reference from before cuts settled the share) is theirs: the entry lets go and nothing moves, the same rule the corpse-side twin applies. Either way reattaching the limb to another body cannot leave one object claimed by two. The settle is saved at once, since a combat sever saves nothing afterwards.

The corpse-side twin (`carry_snapshot_hardware_to_appendage`) moves an object onto the appendage unless it lies on a character or on another appendage, where it belongs to whoever got the first limb: then it stays and that snapshot entry drops its reference. The first cut also settles the corpse's snapshot: every other entry recording a dbref this limb's entries carried drops it, so a limb cut later never inherits the claim (a reattached limb's gun sits off-grid, retracted, indistinguishable by location from the corpse's own; nothing else settles a corpse snapshot).

The survivor keeps its object and its deployed flag and drops to the single profile. The location guard in the natural lookup stops a stale reference from fighting with an object on a severed limb. Living sever and the corpse seam are per organ.

**Reattachment** applies to chrome only; flesh never reattaches. `_resolve_install_limb` (`world/medical/procedures.py`) does not delete the object at `weapon_dbref`. It reclaims the object only if `weapon.location` is the appendage being reattached: location set to None, dbref kept, `deployed` False (it comes back retracted; §14 #9). Otherwise it drops the dbref (the object respawns lazily) and touches nothing, so a legacy shared reference cannot steal the survivor's off-grid claws. This happens before `organ_item.delete()`, because Evennia's delete relocates contents: the weapon must leave the appendage first. It also applies to arm-guns (`AUGMENT_ABILITIES_SPEC.md` §8).

A flesh hand's claws are expected to come back only by harvest and reinstall, which is unverified (the install writes no provenance; §15); a new tray seats only the hand that lacks `nailz`.

## 10. Ranged weapons and handguns

Two pistols of different types (`hands_required` 1) are two options. They fire one shot per round: left, right, left. Each shot uses its own damage, its own bank and its own hand's manipulation. Heavy plus light alternate, because two types never pair; average damage falls against always firing the heavy, and that is the stated cost. Two pistols of ONE type that has a row (two light pistols) are one option on the pair row instead, and the bank names the lead pistol.

Range: at range only ranged options rotate, so pistol plus knife fires the pistol every round with no reach line; in melee they alternate (a gun already works point-blank). A deployed arm-gun is a held weapon, not a natural, so it rotates with a pistol: its damage of 20 does not always win, and a mixed loadout loses the guaranteed best swing (a mechanic change).

Aim stays per character and gives no accuracy bonus. Either gun fires under it; aim stop or moving clears it once. Aim and stop prose name the peeked option's item. The ranged gates use `has_ranged_option`.

Akimbo pistols are one row: `light_pistol` → `{2: {damage 16, hit_bonus -1, weapon_type: "light_pistol_akimbo"}}` and that bank; any two light pistols pair whatever their make, and the bank says `{item_name}` for the lead pistol. A pair is ONE attack, never two shots. The heavy pistol, heavy revolver and machine pistol banks are hand-neutral (no two-hand-grip lines).

Out of scope: ammunition (`COMBAT_SYSTEM.md` banner; §14 #13). `hands_required` is enforced by the implicit grip (§5).

## 11. Many hands

Nothing assumes two hands. Slots come from the species' grasping containers; the maximum today is three (human plus the cybernetic tail). The wheel covers every option with no cap, still one attack per round, so with six weapons each swings every sixth round. Extra hands buy readiness and disarm resistance, not damage (Q2).

Akimbo scales by data alone: `{2: ..., 4: ...}` lets four claw hands make one four-claw attack; with only `{2}`, four hands make two alternating pairs and three hands a pair plus a single. Order is defined, not hashed: species display order first, then augment slots alphabetically. A future multi-arm species lists its arm slots in that table.

Natural weapons on non-grasping hosts (Jawz) join the natural wheel with body-wide manipulation. A clawed hand can still wield an item; claws win by precedence. Disarm takes one item per success, in stable order. `weapon_options()` returns the ordered wheel, so a future "k attacks per round" ruling takes the next k options without restructuring.

## 12. Migration (dropped)

A one-shot migration was planned: `split_shared_ability_weapons()` in `world/medical/augments.py`, run once with `@py` at deploy, to split shared references on living bodies, give a second shotgun arm its own gun, refresh install-time ability specs, update existing `NAILZ_CLAWS` objects, and settle cross-body shares (the body whose hand holds the object keeps it, else the body whose host is deployed, else the lower dbref). It was dropped 2026-10-06 (owner: *"Yeah. Clean up is good."*) after a read-only census on live found nothing to migrate: no body with two or more living Nailz hosts or two shotgun arms, no weapon reference shared within a body or recorded on more than one body, no stored limb or head whose snapshot records a weapon, no `carbide blades` object. No one-shot function exists. The live code settles as it goes: a shared reference is resolved on every toggle (§3) and at every cut, living or corpse (§9), and a claw object spawns from the current prototype.

## 13. Slices: content by weapon type (slice 4)

Pairing lives in `AKIMBO_PROFILES_BY_TYPE` (rows `nailz`, `tiger_claws`, `light_pistol`; owner rulings 2026-10-06, §14 #14, #3718). Nailz pairs on its `nailz` row (9/+1, banks `nailz` / `nailz_akimbo`).

- **`TIGER_CLAWS`**: the Voxhaul Tiger claw, a held weapon, one per hand, damage 6, 180 on the weapons rack. Two pair on the `tiger_claws` row (9/+1).
- **Banks:** `tiger_claws` and `tiger_claws_akimbo` (fresh glove prose, 19-23 / 24 lines per phase) and `light_pistol_akimbo` (16 per phase).

## 14. Owner rulings

Decided (slice 1 gates), owner's words verbatim:

- **#6 Akimbo is ONE attack on the pair profile**, never two swings; placeholders 6/+0 for one hand, 9/+1 for both. 2026-10-03: *"Ruling 1 seems fine."*
- **#2 Claws out and a weapon in the other hand.** Reach is checked first; among the options that can reach, deployed claws win outright. So at range a held pistol fires and the claws stay out; in melee the claws swing and the knife waits. 2026-10-03, after *"I agree about avoiding the odd case of claws being chosen at range - so I think we're aligned."* and the question *"So if claws are out and I'm holding a pistol but at range - which would the attack occur with?"* (the pistol): *"Ok. That makes sense."*
- **#5 `/nailz` in a mixed state retracts every host**; otherwise it deploys every host. 2026-10-05: *"Retract both to sync up makes sense."*
- **#9 Reattachment keeps the hand's original claw or gun object**, parked back in the body, retracted. 2026-10-05: *"I concur. Keep it."*
- **#11 Claw accuracy uses the host hand's manipulation**; the fangs stay body-wide. 2026-10-05: *"Per hand makes sense. We want consistency."*
- **#12 Migration keeps deployed claws deployed** (the second object is spawned at once); the second shotgun arm gaining a gun is called out in the migration's counts as a mechanic change. 2026-10-05: *"Your rec is fine. We're still in pre-alpha."* Overtaken: the migration was dropped 2026-10-06 (§12) because the census found nothing to migrate. A toggle settles a legacy share as it goes: a deployed claw host that lets go spawns its own object at once, while a deployed integrated host that lets go is cleared to retracted (`_disown` in `world/medical/augments.py`).

Alternation and handguns (#3707): owner, 2026-10-06, *"Go."*

Decided (slice 2 gates), 2026-10-06, owner's words verbatim:

- **#1 Alternation replaces "then highest damage" among weapons that can reach; range-first stays.** *"Yes. Using a weapon which won't even be in-range to attack makes no sense. Our order of operation is sound."*
- **#3 Nailz and Jawz both out alternate.** *"Alternation seems fine. Maybe in a future state we can have an amalgamation of all cybernetic weapons so someone with a lot of arms can be quite interesting combat-wise."* (The amalgamation is a remark, recorded for later, not a decision.)
- **#4 Bonus and opportunity attacks turn the wheel.** Owner: *"I kinda defer to the easier design. Either is fine."* The easier design is the one door with no special case: every attack, scheduled or not, runs `process_attack`, which asks `choose_weapon` and notes the slot used; the wheel turns on every swing.
- **#7 Only the same `akimbo_family` pairs; heavy and light pistols alternate.** *"Yes, but the important part of this design is being able to assign Akimbo combinations so we can build on the system. Make sense?"* Combinations are data. The intention recorded with this ruling was `akimbo_family` and `akimbo_profiles` on each item, with a later pairing table naming cross-family pairs without touching the door; ruling #14 (2026-10-06, #3718) made the table the only source and retired the item attributes: `AKIMBO_PROFILES_BY_TYPE`, keyed by `weapon_type`. Two pistols of different types still alternate.
- **#8 Rotation follows species display order (left hand first), which is also the default hand for wield, get and disarm; no dominant hand.** *"Species display order is fine. Eventually, we may want to setup dominant hand but that's a lot of complexity for minimal returns."*
- **#10 Nailz gets its own bank pair.** *"They should each get their own messaging pairs. They're distinctly different weapons."* The Nailz banks are `nailz` and `nailz_akimbo` (the prototype's `weapon_type` and the pair profile follow); `tiger_claws` and `tiger_claws_akimbo` are left for the held Tiger Claws.
- **#13 Ammunition stays out.** *"Ammunition, yes, it isn't design yet. Right?"* Right: `COMBAT_SYSTEM.md` lists ammunition as aspirational and not designed, with a standing note not to build it unasked. **`hands_required` enforcement is wanted; when is the builder's call.** Owner, after the ask was written down: *"hands_require should have enforcement. Whether it happens now or in the future isn't relevant to me."* It is enforced by the implicit grip (§5).
- **#14 Akimbo pairs by weapon type; the bank inserts the item's name** (#3718). On the slice-4 draft (the Model 6 pairing with itself; a Voxhaul Tiger claw per hand at Nailz numbers, 180 on the rack; the claws' banks restored from history and the pistol pair bank new; nothing else to build): *"A. I dig it. I think the design would make sense to focus on weapon type akimbo combinations and then just insert the item name. Get me? This creates fewer dedicated pairings initially but covers a wider gauntlet. B. Seems fine. These are just staples. C. Cool. D. Cool."* So: one table keyed by `weapon_type`, the per-item `akimbo_family` / `akimbo_profiles` attributes retired (Nailz moves into the table with the same numbers and banks), `{item_name}` in the pair banks. The claws' banks were written fresh rather than restored: #10 gives each weapon its own prose, and the historical bank is the Nailz pair bank under another name.

Slice 1 close-out, 2026-10-06, owner's words: *"Yeah. Clean up is good."* The migration (§12) is dropped: the census found nothing to migrate. #3699 (the escort usher's identity comparison) is taken next: *"Sure."*

## 15. Risks

- Ordering `Character.hands` sets the default hand for wield, get and disarm for everyone (§6).
- `get` can push a deployed arm-gun out of the first full hand.
- Flesh-hand Nailz harvest and reinstall is unverified (the install writes no provenance).
- `get_combat_message` swallows errors (§7).

## 16. Balance

One-weapon numbers are prototype data, like every other weapon; the pair rows (Nailz 9/+1, Tiger claws 9/+1, two light pistols 16/−1) are the `AKIMBO_PROFILES_BY_TYPE` table in `world/combat/constants.py`. All of them and the `hit_bonus` term are untuned placeholders; `BALANCE_LEDGER.md` records them under "Gaps the ledger is NOT sized against" until the balance pass. The ledger test collects only the annotated constants in that file, so the table needs no ledger row.

## See also

`AUGMENT_ABILITIES_SPEC.md` (decisions 4 and 7, §8), `ANATOMY_AUGMENTS_SPEC.md`, `COMBAT_SYSTEM.md`, `COMBAT_MESSAGE_FORMAT_SPEC.md`, `CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC.md` (§6.1, Q1, Q2), `GRIP_ENFORCEMENT_SPEC.md`, `roadmaps/BALANCE_LEDGER.md`, defect #3571.
