# Multi-Weapon Combat Specification

> **Status:** 📋 Proposal — designed 2026-10-01, nothing built. Covers claws per hand, akimbo profiles by deployed count, alternation between held weapons, handguns, and species with many hands. The six rulings that gate slice 1 (claws) were decided 2026-10-03 to 2026-10-05 (§14); the seven that gate slice 2 are open. Supersedes defect #3571 when slice 1 ships.

## 0. Owner rulings (2026-10-01, verbatim)

On today's claws: *"I just don't like how this is setup. If a hand is severed, where do the claws go? It's kinda wonky."*

On the per-hand model: *"The model is good. For combat, we'd alternate between weapons except for specifically designed Akimbo weapons like cybernetic claws or Tiger Claws which can discern from individual vs Akimbo as part of the design. This could be something we eventually shift to for other weapons like handguns. It does get tricky with the Mr. Hands system though - where someone could hold many, many weapons. So we'll want room to grow and address things but our point of entry will be small."*

*"Messages I agree on. Toggle should do both. We'll also want damage/hit/etc weapon values to be based on if its one or both."*

*"Placeholders are fine. I think you should figure out the alternation and handguns for the spec though. The system should be comprehensively design before we implement the first slice otherwise it might as well be a hallucination."*

Standing rulings this design keeps: active natural cyberweapons take precedence over held weapons (`AUGMENT_ABILITIES_SPEC.md` decision 4, 2026-06-12); a severed limb takes its gear (decision 7); extra grasping limbs buy no extra attacks and no raw damage (the Q2 guardrail in `CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC.md`, 2026-06-20): the manipulator count pays through initiative, loadout readiness and disarm resistance only. The event-triggered bonus attacks that exist today (a failed advance or charge) are untouched.

## 1. Why: how the claws stand today

- The Nailz tray seats ONE ability, `nailz`, into both hands (`flesh_containers` = left and right hand, `world/prototypes.py`). Each host organ keeps its own `ability_state["nailz"]`, but `_mirror_ability_state` (`world/medical/augments.py`) copies `deployed` and `weapon_dbref` into every host, so both hands point at one `NAILZ_CLAWS` object and one deployed flag. The mirror is called from eight sites in the toggle paths.
- `get_active_natural_weapon` returns the first deployed host's weapon by dbref and never asks where that object is.
- Severance (`carry_hardware_to_appendage`) moves each organ's weapon onto the severed appendage and marks that organ retracted. With one shared object, the cut hand takes BOTH hands' claws to the floor while the other hand still reads deployed and still fights with an object lying in a severed hand.
- Reattachment (`_resolve_install_limb`, `world/medical/procedures.py`) deletes the object at the limb's `weapon_dbref` and resets only that limb's snapshot. The other hand keeps a dead reference: claws render deployed, combat swings fists, one toggle heals it (#3571).
- Combat has no two-weapon concept. `get_wielded_weapon` (`world/combat/utils.py`) returns one weapon: naturals first, then the first tagged weapon in hand, then the first held item of any kind; `select_weapon_for_engagement` (defined beside it in `utils.py`, called once from `process_attack` in `world/combat/attack.py`) applies range-then-highest-damage. There are 20 `get_wielded_weapon` call sites across six files, three `is_wielding_ranged_weapon` sites and three `get_active_natural_weapon` callers, plus `get_wielded_weapons` and `find_best_weapon` in `utils.py`. The resolvers already disagree with each other.
- The claws use the `tiger_claws` message bank (`world/combat/messages/tiger_claws.py`), whose prose assumes both hands and, in places, gloves and a belt that an implant does not have.

## 2. Design at a glance

1. **Each hand owns its claws.** Every host organ's `ability_state` is authoritative; the mirror is deleted; each host spawns its own weapon object. Severance takes exactly that hand's claws; reattachment keeps the object it finds on the appendage.
2. **One door for "what weapon".** `choose_weapon(char, target=None)` in a new `world/combat/weapon_choice.py` returns a `WeaponChoice` and replaces the six selection functions: `get_wielded_weapon`, `get_wielded_weapons`, `is_wielding_ranged_weapon`, `select_weapon_for_engagement` and `find_best_weapon` in `world/combat/utils.py`, and `get_active_natural_weapon` in `world/medical/augments.py`. Every gate, every attack and every line of prose asks it.
3. **Akimbo is weapon data.** A prototype declares an `akimbo_family` and `akimbo_profiles` keyed by deployed count. Two claws become ONE option with the count-2 profile: one attack, uplifted values, the akimbo bank. One claw is the item's own values and the one-hand bank.
4. **Alternation is the general rule.** Among the options that can reach the target, the swing rotates in a stable hand order, one option per round. Akimbo groups rotate as one option.
5. **Toggle acts on every host.** `/nailz` deploys or retracts every living host at once.
6. **Handguns follow the same rule** without new code: two pistols alternate; akimbo pistols are later data.
7. **Nothing assumes two hands.** Slots come from the species' grasping containers; order from its display order.

## 3. Data model

**Organs.** Both hands keep the ability name `nailz`. Each host's `organ.ability_state["nailz"]` = `{deployed, weapon_dbref}` is the truth. Delete `_mirror_ability_state` and its eight calls. `_get_or_spawn_weapon` already writes the dbref into the state it is given, so calling it per host yields one object per hand; the install loop that seats the ability into each `flesh_containers` host is unchanged.

**Legacy shared references.** Until the migration (§12) runs, a stored body may still have every host of an ability pointing at one object. Every toggle settles this first, over all living hosts whichever are being toggled (a surgical stow passes one): the host whose hand holds the object keeps the reference, otherwise the first in organ order; the others let go. A host that lets go while deployed: a natural weapon spawns its own at once, off-grid and silent, so the hand keeps fighting; an integrated host's hand never held the shared gun, so its deployed flag (the mirror's word alone) is cleared, and it gains its own gun on its next deploy, as the migration (§12) gives it one up front. Nothing is deleted.

**Taking an object back.** On deploy, a host's existing object is used as it stands when it is parked off-grid or on the body. One lying on a severed appendage is carried off: the host unlinks it and spawns its own, and chrome reattachment (§9) is what reclaims the carried one (flesh never reattaches, so a flesh hand's carried claws stay with the appendage). One lying anywhere else is taken back. Taking back presumes one owner: severance settles a shared reference (§9), so no deploy reaches into another body's hand. The anywhere-else case exists because a hand-only sever drops a deployed forearm gun to the floor, locked and undroppable, while the module still reads deployed, and the body may walk away before the hand is restored (#3697, pre-existing, out of slice 1).

**Natural lookup.** `get_active_natural_weapon` becomes `get_active_natural_weapons(char) -> [(host_container, item)]`: living, deployed hosts in organ order, returning only items whose `location` is None (parked in the body). An object lying on a severed appendage is not a weapon anyone fights with.

**Weapon attributes** (read with defaults; never written onto existing items):
- `hit_bonus` (int, default 0): a to-hit term added beside the charge bonus.
- `akimbo_family` (str): members of one family may group.
- `akimbo_profiles` (`{count: overrides}`): overrides limited to `damage`, `hit_bonus`, `weapon_type`, `damage_type`. Count 1 is the item's own attributes.

**Constants** in `world/combat/constants.py`: `WEAPON_ATTR_HIT_BONUS`, `WEAPON_ATTR_AKIMBO_FAMILY`, `WEAPON_ATTR_AKIMBO_PROFILES`, `AKIMBO_PROFILE_FIELDS`, `NDB_LAST_WEAPON_SLOT`. Bank names stay prototype data like every `weapon_type`.

**`NAILZ_CLAWS`** becomes one hand: five blades, placeholder damage 6, `weapon_type` `tiger_claws`, `akimbo_family` `nailz`, `akimbo_profiles {2: {damage: 9, hit_bonus: 1, weapon_type: "tiger_claws_akimbo"}}`. An intact owner keeps today's damage 9.

**`WeaponChoice`** (frozen dataclass): `items` in slot order, `slots`, `damage`, `hit_bonus`, `damage_type`, `weapon_type`, `is_ranged`; `.item = items[0]`; `.akimbo = len(items) > 1`. `None` means unarmed, as today.

## 4. One door: `choose_weapon`

`choose_weapon(char, target=None)` is a pure peek. Rule order:

1. **Candidates** in slot order: natural options, then held items, de-duplicated by object. A future two-slot grip is one option with two slots.
2. **Real weapons**: if any held item is tagged `weapon`, drop untagged items (the #516 rule). With nothing tagged, keep only the single highest-damage improvised item, so nothing rotates a cigarette.
3. **Range**: with a target not in melee range, ranged options only; with none, keep all so the existing reach message fires.
4. **Natural precedence** (decision 4, applied among the options that can reach): if any deployed natural weapon survived the range step, only naturals count. Ruled 2026-10-03 (§14, ruling 2): at range a held pistol fires while the claws stay out; in melee deployed claws win outright and the knife waits. Today natural precedence runs before range, so claws out means claws swing even where they cannot reach, and the reach gate refuses the attack while a loaded gun sits in the other hand.
5. **Akimbo grouping** (§5).
6. **Rotation** (§6; slice 2). In slice 1 held weapons keep range-then-max and naturals take the first option.

`has_ranged_option(char)` = any option is ranged after step 3; it replaces the "is the wielded weapon ranged" gates so a knife sorting first no longer blocks a pistol.

**Repoint, then delete** (No Compat Seams): the 20 `get_wielded_weapon` sites (`commands/combat/core_actions.py`, `special_actions.py`, `movement.py`, `commands/forensics.py`, `typeclasses/exits.py`, `world/combat/utils.py`), the one `select_weapon_for_engagement` call in `process_attack` (`world/combat/attack.py`), the three `is_wielding_ranged_weapon` sites in `world/combat/movement_resolution.py`, `get_active_natural_weapon` in `typeclasses/characters.py`, and every caller of `get_wielded_weapons` and `find_best_weapon`. `process_attack` reads every value from the choice. Forensics takes the first option that can sever (`_blade_in_hand`). Correction at build time (2026-10-05): `find_best_weapon` is not a wield selector but the draw picker over a body's whole inventory (what an NPC pulls when caught off guard, `world/director/civilians.py`, `world/souls/jobs.py`); it stays. `get_wielded_weapons` had no caller outside the deleted selector. Manipulation is the minimum over `choice.slots`; a natural on a grasping host scopes to that hand, Jawz stays body-wide (a head-scoped manipulation fails open to 1.0 in `world/medical/core.py`, a silent buff). No broad `except`.

## 5. Akimbo profiles by deployed count

Grouping runs after the range filter. Members = options sharing an `akimbo_family`, distinct objects, in slot order; n = member count. k = the largest key in `akimbo_profiles` with k ≤ n. With no such key, or n = 1, members stay single. k members become ONE option: the lead item's attributes overlaid with `akimbo_profiles[k]` (profile fields only). Leftovers regroup by the same rule or rotate singly. Three claws never ride a count-2 profile with the third absorbed.

**Nailz placeholders:** one hand d6+6, +0 hit, bank `tiger_claws`; both hands d6+9, +1 hit, bank `tiger_claws_akimbo`. A severed or retracted hand drops n to 1 on the next swing with no state to clear.

**To-hit:** `attacker_roll += choice.hit_bonus`, beside the existing +2 charge bonus in `world/combat/attack.py`; defaults to 0, so no other weapon changes. Damage stays d6 + `choice.damage`; injury type from `choice.damage_type`. Manipulation = min over the group's slots, so the weaker hand drags.

**Guardrail:** the uplift belongs to a designed pair, which costs a second implant or item. It is one attack and is never paid per surplus limb.

## 6. Alternation

The unit of rotation is an option: one weapon or one akimbo group. Still one scheduled attack per combatant per round (one `_schedule_attack` per combatant in `world/combat/handler.py`), plus the event-triggered bonus attacks that exist today. Alternation changes WHICH option swings, never how many.

**Order.** `Character.hands` iterates in the species' `anatomical_display_order` (left hand first), then unlisted slots such as a tail alphabetically. Today it iterates a set, so the order is salted.

**Cursor.** `NDB_LAST_WEAPON_SLOT` on the attacker holds the lead slot of the last option that swung. Next = the first option whose lead slot sorts after it, wrapping. Unset, or one option: the first. Keyed by slot, so disarm, severance or a new wield self-heals. Cleared in `cleanup_combatant_state` (`world/combat/utils.py`), beside the ndb attributes it already clears, because both `remove_combatant` and the handler's end-of-fight `cleanup_all_combatants` reach it and a fighter still standing when a fight ends never passes through `remove_combatant`; so each fight starts at the first slot and the initiate line names the first swing. Kept on ndb rather than the combat entry because advance and charge resolve inside `at_repeat`, which writes its snapshot back over `db.combatants`; a reload only restarts the wheel.

**Peek vs commit.** Every caller peeks. `process_attack` commits via `note_weapon_used(attacker, choice)` only after the reach and proximity gates pass, so a failed reach does not turn the wheel. Bonus and opportunity attacks are real swings and commit.

This replaces "then highest damage" (`CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC.md` §6.1); range-first stays. Initiate, aim and stop prose peek the same wheel.

## 7. Messages

**Bank pair convention:** the base bank is one weapon; `<type>_akimbo` is the designed pair. Bank = `choice.weapon_type`; the loader needs no change.
- `git mv tiger_claws.py tiger_claws_akimbo.py`: it keeps today's both-hands prose. Fix the implant-contradicting lines (gloves, belt, "five blades", a self `{hit_location}`).
- Write a new one-hand `tiger_claws.py` covering all four phases (a missing kill falls to the flat generic line), seeded from the hand-neutral lines.
- Only the two `NAILZ_CLAWS` prototype attributes name the bank.
- All seven weapon-bank reads use `choice.weapon_type` with `item=choice.item`: hit, miss and kill in `world/combat/attack.py`; three initiate reads in `commands/combat/core_actions.py` (aiming-direction, local, and the target's defensive line); the auto-retarget initiate in `world/combat/utils.py`.
- No `{hand}` in combat banks for v1; it would bind all seven sites.

**Toggle prose.** Base keys stay the all-hosts prose. New keys `deploy_msg_one`, `retract_msg_one`, `deploy_room_one`, `retract_room_one` (constants beside `CYBERWARE_COMMAND_PREFIX`), used when exactly one host changed, whatever was dispatched or lives: a surgical stow of one hand, or a body down to one hand (#3700); an ability without them falls back to its base keys. They carry `{hand}`, pre-interpolated before `msg_room_identity`. `deployed_longdesc` is rewritten as one-hand prose with no `_one` variant: it already renders once per chrome location. Room lines stay on `msg_room_identity`.

`COMBAT_MESSAGE_FORMAT_SPEC.md` gains a bank-pair section when slice 1 ships.

## 8. Toggle

`/nailz` stays one word acting on every living host. Rule: if ANY living host is deployed, retract every deployed host; otherwise deploy every host. One predicate, `is_ability_deployed(char, name)` = any living host deployed; the director's draw and stow paths read it and still reach all-retracted from a mixed state in one toggle. Each per-type toggle acts on ONE host (a natural toggle spawns or reuses that host's object; an integrated toggle seats that host's object in that host's slot); `_dispatch_toggle` loops the hosts and sends one self line and one room line.

This fixes a latent bug: two forearm shotgun modules mirror one `weapon_dbref`, so the second arm never gets a gun.

`stow_abilities_at` dispatches only the hosts at the procedure location (#3360: hardware elsewhere on the body is left alone); today it retracts both hands. Readouts: `list_abilities` names the hands only when they differ; the cyberware status screen shows "both hands" or "left deployed / right retracted"; the sdesc names the peeked natural option's item. Voice and Jawz have one host (the cyber-jaw hardpoint); nothing changes for them. Blindsight can have two hosts (a targeting processor in each cyber arm): it reads as any-deployed and is unaffected in play, but the per-host toggle and the readouts must cover it like the shotgun pair.

## 9. Severance and reattachment

**Severance.** `carry_hardware_to_appendage` walks the chain's organs, moves each organ's OWN object onto the appendage and marks it retracted. With per-host objects the cut hand takes exactly its own claws. It also settles a legacy shared reference at the cut, by the keeper rule: an object a surviving hand still holds stays with that hand and the limb's entry lets go; otherwise the limb takes the object and every host left on the body that still points at it lets go (as in §3). An object already lying on another character or limb (a stale reference from before cuts settled the share) is theirs: the entry lets go and nothing moves, the same rule the corpse-side twin applies. Either way reattaching the limb to another body cannot leave one object claimed by two. The settle is saved at once, since a combat sever saves nothing afterwards. The corpse-side twin (`carry_snapshot_hardware_to_appendage`) moves an object onto the appendage unless it lies on a character or on another appendage, where it belongs to whoever got the first limb: then it stays and that snapshot entry drops its reference. The first cut also settles the corpse's snapshot: every other entry recording a dbref this limb's entries carried drops it, so a limb cut later never inherits the claim (a reattached limb's gun sits off-grid, retracted, indistinguishable by location from the corpse's own; the migration leaves corpse snapshots alone, §12). The survivor keeps its object and its deployed flag and drops to the single profile. The location guard in the natural lookup stops a stale reference from fighting with an object on a severed limb. Living sever and the corpse seam are already per organ.

**Reattachment** applies to chrome only; flesh never reattaches. `_resolve_install_limb` stops deleting the object at `weapon_dbref`. It reclaims the object only if `weapon.location` is the appendage being reattached: location set to None, dbref kept, `deployed` False (it comes back retracted). Otherwise it drops the dbref (the object respawns lazily) and touches nothing, so a legacy shared reference cannot steal the survivor's off-grid claws. This happens before `organ_item.delete()`, because Evennia's delete relocates contents. It also applies to arm-guns; `AUGMENT_ABILITIES_SPEC.md` §8 ("the deployed weapon item does not survive the cut") is rewritten with slice 1.

A flesh hand's claws are expected to come back only by harvest and reinstall, which is unverified (§15); a new tray seats only the hand that lacks `nailz`.

## 10. Ranged weapons and handguns

Two pistols (`hands_required` 1) are two options. They fire one shot per round: left, right, left. Each shot uses its own damage, its own bank and its own hand's manipulation. Heavy plus light alternate, because different families never pair; average damage falls against today's always-heavy, and that is the stated cost.

Range: at range only ranged options rotate, so pistol plus knife fires the pistol every round with no reach line; in melee they alternate (a gun already works point-blank). A deployed arm-gun is a held weapon, not a natural, so it rotates with a pistol; today its damage of 20 always wins.

Aim stays per character and gives no accuracy bonus. Either gun fires under it; aim stop or moving clears it once. Aim and stop prose name the peeked option's item. The ranged gates use `has_ranged_option`.

Akimbo pistols later are data only: `akimbo_family`, `akimbo_profiles {2: {...weapon_type: "light_pistol_akimbo"}}`, and that bank. A pair is ONE attack, never two shots. Slice 2 makes the two-hand-grip lines in the heavy pistol, heavy revolver and machine pistol banks hand-neutral.

Out of scope: ammunition (`COMBAT_SYSTEM.md` banner); `hands_required` enforcement (today it only sets a default).

## 11. Many hands

Nothing assumes two hands. Slots come from the species' grasping containers; the maximum today is three (human plus the cybernetic tail). The wheel covers every option with no cap, still one attack per round, so with six weapons each swings every sixth round. Extra hands buy readiness and disarm resistance, not damage (Q2).

Akimbo scales by data alone: `{2: ..., 4: ...}` lets four claw hands make one four-claw attack; with only `{2}`, four hands make two alternating pairs and three hands a pair plus a single. Order is defined, not hashed: species display order first, then augment slots alphabetically. A future multi-arm species lists its arm slots in that table.

Natural weapons on non-grasping hosts (Jawz) join the natural wheel with body-wide manipulation. A clawed hand can still wield an item; claws win by precedence. Disarm takes one item per success, now in stable order. `weapon_options()` returns the ordered wheel, so a future "k attacks per round" ruling takes the next k options without restructuring.

## 12. Migration

A one-shot `split_shared_ability_weapons()` in `world/medical/augments.py`, run once with `@py` at deploy with owner approval, with its own test and its counts in the PR, deleted in the next PR. Not a boot sweep.

Read-only census first: characters and NPCs with two or more `nailz` hosts; bodies with two shotgun arms; objects whose dbref is recorded on more than one body (a limb reattached before severance settled the share; the per-character pass cannot see these); Iver Kestrel (state captured first and left as found).

For each living character, for each ability with two or more living hosts, in slot order: hosts sharing a dbref keep it on the host whose hand holds the object, otherwise the first, and only if the object sits where it belongs (None for a natural weapon; for an integrated weapon, the character when deployed and None when retracted); the others drop the dbref, and a deployed one spawns its own object now. For natural weapons no player sees a change. For integrated hosts (two shotgun arms) the second arm gains a gun it never had, which seats in that hand and drops what it held: a visible mechanic change, to be labelled as such. A host whose object lies elsewhere (a severed appendage) drops both dbref and deployed. Each Nailz host's install-time ability spec is refreshed from the current `organ_spec`, or old installs lack the `_one` prose and render the old both-hands longdesc twice. Existing `NAILZ_CLAWS` objects are updated with Evennia's `batch_update_objects_with_prototype` after a read-only check that a live object carries the `from_prototype` tag. Snapshots sharing a dbref are counted and left alone.

**Cross-body shares.** A limb cut before cuts settled the share (on master) and reattached to another body leaves one object recorded by two living bodies, and no per-body code can see it; a stored appendage whose snapshot records a dbref a living body also records is the same share waiting to happen (surfaced by the #3696 review, round 7). The census lists both. The settle, across bodies: the body whose hand holds the object keeps it, else the body whose host is deployed, else the lower dbref; the others let go (a deployed natural host spawns its own at once; an integrated host clears its flag). A stored appendage's snapshot drops a dbref a living body keeps, so its reattach spawns fresh. OPEN: this cross-body rule needs the owner's go with PR C.

## 13. Slices

- **0 (now):** this spec; the ledger gap (§16). No issue.
- **1, claws plus the one door** (issue first; PR A #3696 shipped 2026-10-05; PR B is the one door; PR C the migration follows): per-host toggle; delete the mirror; per-location stow; `is_ability_deployed` and the director; readouts; `get_active_natural_weapons`; `weapon_choice.py` with grouping; repoint the 20 + 1 + 3 + 1 call sites and delete the five old functions; the hit term; manipulation by slots; the `NAILZ_CLAWS` profiles; the bank split; `_one` prose; reattach keeps the object; the migration. Held weapons keep range-then-max, but gates, initiate and the swing agree. Tests: rewrite `test_one_ability_two_hands.py` (one assertion inverts), `test_weapon_autoprioritizer.py`, `test_combat_manipulation_resolver.py`; add a test that both claw banks resolve all four phases. Specs: `AUGMENT_ABILITIES_SPEC.md` §1/§3/§8, `COMBAT_MESSAGE_FORMAT_SPEC.md`, `CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC.md` §6.1. Play, checked via splattercast: deploy, fight akimbo, sever, fight single, surgical stow, chrome reattach.
- **2, alternation and handguns:** ordered `Character.hands`; the ndb cursor; `note_weapon_used`; the max rule removed; disarm order; pistol bank rewrites. Play: two light pistols; pistol plus knife at range and in melee; arm-gun plus pistol; Nailz plus Jawz.
- **3, owner-gated content:** akimbo pistol models; a branded held Tiger Claws pair.

## 14. Owner rulings

Decided (slice 1 gates), owner's words verbatim:

- **#6 Akimbo is ONE attack on the pair profile**, never two swings; placeholders 6/+0 for one hand, 9/+1 for both. 2026-10-03: *"Ruling 1 seems fine."*
- **#2 Claws out and a weapon in the other hand.** Reach is checked first; among the options that can reach, deployed claws win outright. So at range a held pistol fires and the claws stay out; in melee the claws swing and the knife waits. 2026-10-03, after *"I agree about avoiding the odd case of claws being chosen at range - so I think we're aligned."* and the question *"So if claws are out and I'm holding a pistol but at range - which would the attack occur with?"* (the pistol): *"Ok. That makes sense."* The §4 order was changed to match.
- **#5 `/nailz` in a mixed state retracts every host**; otherwise it deploys every host. 2026-10-05: *"Retract both to sync up makes sense."*
- **#9 Reattachment keeps the hand's original claw or gun object**, parked back in the body, retracted. 2026-10-05: *"I concur. Keep it."*
- **#11 Claw accuracy uses the host hand's manipulation**; the fangs stay body-wide. 2026-10-05: *"Per hand makes sense. We want consistency."*
- **#12 Migration keeps deployed claws deployed** (the second object is spawned at once); the second shotgun arm gaining a gun is called out in the migration's counts as a mechanic change. 2026-10-05: *"Your rec is fine. We're still in pre-alpha."*

Open (slice 2 gates):

1. Alternation replaces "then highest damage" among weapons that can reach; range-first stays. Yes or no?
3. Nailz and Jawz both out: alternate, or a fixed precedence, and which?
4. Do bonus and opportunity attacks turn the wheel? Yes or no?
7. Only the same `akimbo_family` pairs, so heavy and light pistols alternate. Yes or no?
8. Rotation order follows species display order (left hand first), which also becomes the default hand for wield, get and disarm. Yes, or add a dominant hand?
10. Nailz shares `tiger_claws` and `tiger_claws_akimbo` with a future held Tiger Claws, or gets its own pair?
13. Ammunition and `hands_required` enforcement stay out. Yes or no?

## 15. Risks

- Slice 1 repoints about 25 call sites; every gate and prose path needs play testing; the suite takes about 53 minutes.
- Ordering `Character.hands` changes the default hand for wield, get and disarm for everyone.
- `hit_bonus` is a new term on every roll; it must default to 0 and never be written onto items.
- `get_combat_message` swallows errors; test both claw banks across all four phases.
- The weapon must leave the appendage before `organ_item.delete()`.
- Bodies with two shotgun arms change (two guns); take the census first.
- Mixed loadouts lose the guaranteed best swing (arm-gun 20 versus pistol); label it a mechanic change.
- Flesh-hand Nailz harvest and reinstall is unverified (the install writes no provenance).
- Legacy corpse snapshots sharing a dbref move the one shared object onto each limb as it is cut, so it ends on the last limb cut and the first loses it.
- `get` can push a deployed arm-gun out of the first full hand.
- A missed spec refresh leaves the both-hands longdesc rendering twice on chrome hands.
- Evennia treats module-level dicts in `world/prototypes.py` as prototypes; keep profiles inline (unverified against the Evennia source, which is not in this repo).

## 16. Balance

All weapon numbers stay prototype data, like every other weapon. The placeholders (one hand 6/+0, both hands 9/+1) and the new `hit_bonus` term are untuned; `BALANCE_LEDGER.md` records them under "Gaps the ledger is NOT sized against" until the balance pass. The ledger test reads only `world/combat/constants.py`, so no ledger row is required for prototype data.

## See also

`AUGMENT_ABILITIES_SPEC.md` (decisions 4 and 7, §8), `ANATOMY_AUGMENTS_SPEC.md`, `COMBAT_SYSTEM.md`, `COMBAT_MESSAGE_FORMAT_SPEC.md`, `CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC.md` (§6.1, Q1, Q2), `roadmaps/BALANCE_LEDGER.md`, defect #3571.
