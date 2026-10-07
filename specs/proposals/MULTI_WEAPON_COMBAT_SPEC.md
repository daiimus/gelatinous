# Multi-Weapon Combat Specification

> **Status:** 📋 Proposal — designed 2026-10-01; slices 1, 2 and 3 shipped 2026-10-05/06, slice 4 (pairs by weapon type, the Tiger claw, the pistol pair) in review 2026-10-06. Covers claws per hand, akimbo profiles by weapon type and count, alternation between held weapons, handguns, the grip, and species with many hands. The fourteen rulings in §14 were decided 2026-10-03 to 2026-10-06. Supersedes defect #3571 (closed with slice 1).

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
3. **Akimbo is weapon-type data.** `AKIMBO_PROFILES_BY_TYPE` in `world/combat/constants.py` maps a `weapon_type` to profiles keyed by count (owner ruling §14 #14, slice 4; slices 1-3 carried `akimbo_family` and `akimbo_profiles` on each prototype instead). Two items of one type with a row become ONE option with the count-2 profile: one attack, uplifted values, the pair bank with the lead item's name in its lines. One item is its own values and its own bank.
4. **Alternation is the general rule.** Among the options that can reach the target, the swing rotates in a stable hand order, one option per round. Akimbo groups rotate as one option.
5. **Toggle acts on every host.** `/nailz` deploys or retracts every living host at once.
6. **Handguns follow the same rule** without new code: two pistols of different types alternate; two of one type that has a row in `AKIMBO_PROFILES_BY_TYPE` (two light pistols, slice 4) are one attack.
7. **Nothing assumes two hands.** Slots come from the species' grasping containers; order from its display order.

## 3. Data model

**Organs.** Both hands keep the ability name `nailz`. Each host's `organ.ability_state["nailz"]` = `{deployed, weapon_dbref}` is the truth. Delete `_mirror_ability_state` and its eight calls. `_get_or_spawn_weapon` already writes the dbref into the state it is given, so calling it per host yields one object per hand; the install loop that seats the ability into each `flesh_containers` host is unchanged.

**Legacy shared references.** Until the migration (§12) runs, a stored body may still have every host of an ability pointing at one object. Every toggle settles this first, over all living hosts whichever are being toggled (a surgical stow passes one): the host whose hand holds the object keeps the reference, otherwise the first in organ order; the others let go. A host that lets go while deployed: a natural weapon spawns its own at once, off-grid and silent, so the hand keeps fighting; an integrated host's hand never held the shared gun, so its deployed flag (the mirror's word alone) is cleared, and it gains its own gun on its next deploy, as the migration (§12) gives it one up front. Nothing is deleted.

**Taking an object back.** On deploy, a host's existing object is used as it stands when it is parked off-grid or on the body. One lying on a severed appendage is carried off: the host unlinks it and spawns its own, and chrome reattachment (§9) is what reclaims the carried one (flesh never reattaches, so a flesh hand's carried claws stay with the appendage). One lying anywhere else is taken back. Taking back presumes one owner: severance settles a shared reference (§9), so no deploy reaches into another body's hand. The anywhere-else case exists because a hand-only sever drops a deployed forearm gun to the floor, locked and undroppable, while the module still reads deployed, and the body may walk away before the hand is restored (#3697, pre-existing, out of slice 1).

**Natural lookup.** `get_active_natural_weapon` becomes `get_active_natural_weapons(char) -> [(host_container, item)]`: living, deployed hosts in organ order, returning only items whose `location` is None (parked in the body). An object lying on a severed appendage is not a weapon anyone fights with.

**Weapon attributes** (read with defaults; never written onto existing items):
- `hit_bonus` (int, default 0): a to-hit term added beside the charge bonus.
- Pairing is not an item attribute (slice 4): `AKIMBO_PROFILES_BY_TYPE[weapon_type]` = `{count: overrides}`, overrides limited to `damage`, `hit_bonus`, `weapon_type`, `damage_type`. Count 1 is the item's own attributes. Rows: `nailz`, `tiger_claws`, `light_pistol`.

**Constants** in `world/combat/constants.py`: `WEAPON_ATTR_HIT_BONUS`, `AKIMBO_PROFILE_FIELDS`, `AKIMBO_PROFILES_BY_TYPE`, `NDB_LAST_WEAPON_SLOT`. A one-weapon bank is still named by the prototype's `weapon_type`; a pair bank is named by its row in `AKIMBO_PROFILES_BY_TYPE` (slice 4).

**`NAILZ_CLAWS`** becomes one hand: five blades, placeholder damage 6, `weapon_type` `nailz` (was `tiger_claws` until slice 2), its pair row `{2: {damage: 9, hit_bonus: 1, weapon_type: "nailz_akimbo"}}` (on the prototype until slice 4, in `AKIMBO_PROFILES_BY_TYPE` since). An intact owner keeps today's damage 9.

**`WeaponChoice`** (frozen dataclass): `items` in slot order, `slots`, `lead_slot` (the host container for a natural weapon, the first grasping slot for a held one; the wheel's key), `damage`, `hit_bonus`, `damage_type`, `weapon_type`, `is_ranged`, `natural`; `.item = items[0]`; `.akimbo = len(items) > 1`. `None` means unarmed, as today.

## 4. One door: `choose_weapon`

`choose_weapon(char, target=None)` is a pure peek. Rule order:

1. **Candidates** in slot order: natural options, then held items, de-duplicated by object. A future two-slot grip is one option with two slots.
2. **Real weapons**: if any held item is tagged `weapon`, drop untagged items (the #516 rule). With nothing tagged, keep only the single highest-damage improvised item, so nothing rotates a cigarette.
3. **Range**: with a target not in melee range, ranged options only; with none, keep all so the existing reach message fires.
4. **Natural precedence** (decision 4, applied among the options that can reach): if any deployed natural weapon survived the range step, only naturals count. Ruled 2026-10-03 (§14, ruling 2): at range a held pistol fires while the claws stay out; in melee deployed claws win outright and the knife waits. Today natural precedence runs before range, so claws out means claws swing even where they cannot reach, and the reach gate refuses the attack while a loaded gun sits in the other hand.
5. **Akimbo grouping** (§5).
6. **The wheel** (§6; slice 2): the next option after the last slot that swung. Until slice 2, held weapons kept range-then-max and naturals took the first option.

`has_ranged_option(char)` = any real option is ranged (step 3 cannot change that answer, so it takes no target); it replaces the "is the wielded weapon ranged" gates so a knife sorting first no longer blocks a pistol. `choose_weapon(char, at_range=True)` is the aiming peek: the option that would fire at range, so the aim, aim-stop and move-while-aiming lines name the gun the gate approved rather than the claws or the heavier blade that would swing in melee; a target aim names `choose_weapon(char, target)`. One helper, `aimed_weapon_name(char, target=None)`, speaks for every aim, stop and move-while-aiming line. It is worked out when the line runs: a stop after melee range changed mid-aim (a retreat) names what would fire now, not what the aim line named. Text only; accepted (review 2026-10-05).

**Repoint, then delete** (No Compat Seams): the 20 `get_wielded_weapon` sites (`commands/combat/core_actions.py`, `special_actions.py`, `movement.py`, `commands/forensics.py`, `typeclasses/exits.py`, `world/combat/utils.py`), the one `select_weapon_for_engagement` call in `process_attack` (`world/combat/attack.py`), the three `is_wielding_ranged_weapon` sites in `world/combat/movement_resolution.py`, `get_active_natural_weapon` in `typeclasses/characters.py`, and every caller of `get_wielded_weapons` and `find_best_weapon`. `process_attack` reads every value from the choice. Forensics takes the first option that can sever (`_blade_in_hand`). Correction at build time (2026-10-05): `find_best_weapon` is not a wield selector but the draw picker over a body's whole inventory (what an NPC pulls when caught off guard, `world/director/civilians.py`, `world/souls/jobs.py`); it stays. `get_wielded_weapons` had no caller outside the deleted selector. Manipulation is the minimum over `choice.slots`; a natural on a grasping host scopes to that hand, Jawz stays body-wide (a head-scoped manipulation fails open to 1.0 in `world/medical/core.py`, a silent buff). No broad `except`.

## 5. Akimbo profiles by deployed count

Grouping runs after the range filter. Members = options of one `weapon_type` that has a row in `AKIMBO_PROFILES_BY_TYPE`, distinct objects, in slot order; n = member count. k = the largest key in that row with k ≤ n. With no such key, or n = 1, members stay single. k members become ONE option: the lead item's attributes overlaid with the row's profile for k (profile fields only). Leftovers regroup by the same rule or rotate singly. Three claws never ride a count-2 profile with the third absorbed.

**Nailz placeholders:** one hand d6+6, +0 hit, bank `nailz`; both hands d6+9, +1 hit, bank `nailz_akimbo`. A severed or retracted hand drops n to 1 on the next swing with no state to clear.

**To-hit:** `attacker_roll += choice.hit_bonus`, beside the existing +2 charge bonus in `world/combat/attack.py`; defaults to 0, so no other weapon changes. Damage stays d6 + `choice.damage`; injury type from `choice.damage_type`. Manipulation = min over the group's slots, so the weaker hand drags.

**Guardrail:** the uplift belongs to a designed pair, which costs a second implant or item. It is one attack and is never paid per surplus limb.

## 6. Alternation

The unit of rotation is an option: one weapon or one akimbo group. Still one scheduled attack per combatant per round (one `_schedule_attack` per combatant in `world/combat/handler.py`), plus the event-triggered bonus attacks that exist today. Alternation changes WHICH option swings, never how many.

**Order.** `Character.hands` iterates in the species' `anatomical_display_order` (left hand first), then unlisted slots such as a tail alphabetically (`Character.slot_order`, slice 2). Until slice 2 it iterated a set, so the order was salted per process.

**Cursor.** `NDB_LAST_WEAPON_SLOT` on the attacker holds the lead slot of the last option that swung. Next = the first option whose lead slot sorts after it, wrapping. Unset, or one option: the first. Keyed by slot, so disarm, severance or a new wield self-heals. Cleared in `cleanup_combatant_state` (`world/combat/utils.py`), beside the ndb attributes it already clears, because both `remove_combatant` and the handler's end-of-fight `cleanup_all_combatants` reach it and a fighter still standing when a fight ends never passes through `remove_combatant`; so each fight starts at the first slot and the initiate line names the first swing. Kept on ndb rather than the combat entry because advance and charge resolve inside `at_repeat`, which writes its snapshot back over `db.combatants`; a reload only restarts the wheel.

**Peek vs commit.** Every caller peeks. `process_attack` commits via `note_weapon_used(attacker, choice)` only after the reach and proximity gates pass, so a failed reach does not turn the wheel. Bonus and opportunity attacks are real swings and commit.

This replaces "then highest damage" (`CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC.md` §6.1); range-first stays. Initiate, aim and stop prose peek the same wheel. Accepted text drift (review 2026-10-06): a delayed swing already scheduled at an old target still commits when it lands, so an initiate spoken at a new target in between can name an option the next swing then skips; text only, and the retarget itself is pre-existing behaviour.

## 7. Messages

**Bank pair convention:** the base bank is one weapon; `<type>_akimbo` is the designed pair. Bank = `choice.weapon_type`; the loader needs no change.
- Slice 2 (owner ruling §14 #10) renamed the pair to `nailz.py` / `nailz_akimbo.py`; `tiger_claws` and `tiger_claws_akimbo` are left for the held Tiger Claws (slice 4). The slice-1 history: `git mv tiger_claws.py tiger_claws_akimbo.py`: it keeps today's both-hands prose. Fix the implant-contradicting lines (gloves, belt, "five blades", a self `{hit_location}`).
- (slice 1) A new one-hand bank covering all four phases (a missing kill falls to the flat generic line), seeded from the hand-neutral lines.
- Only the `nailz` row of `AKIMBO_PROFILES_BY_TYPE` names the pair bank; the prototype's `weapon_type` names `nailz`.
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

Two pistols of different types (`hands_required` 1) are two options. They fire one shot per round: left, right, left. Each shot uses its own damage, its own bank and its own hand's manipulation. Heavy plus light alternate, because two types never pair; average damage falls against today's always-heavy, and that is the stated cost. Two pistols of ONE type that has a row (two light pistols, slice 4) are one option on the pair row instead, and the bank names the lead pistol.

Range: at range only ranged options rotate, so pistol plus knife fires the pistol every round with no reach line; in melee they alternate (a gun already works point-blank). A deployed arm-gun is a held weapon, not a natural, so it rotates with a pistol; until slice 2 its damage of 20 always won.

Aim stays per character and gives no accuracy bonus. Either gun fires under it; aim stop or moving clears it once. Aim and stop prose name the peeked option's item. The ranged gates use `has_ranged_option`.

Akimbo pistols are one row (slice 4): `light_pistol` → `{2: {damage 16, hit_bonus -1, weapon_type: "light_pistol_akimbo"}}` and that bank; any two light pistols pair whatever their make, and the bank says `{item_name}` for the lead pistol. A pair is ONE attack, never two shots. Slice 2 makes the two-hand-grip lines in the heavy pistol, heavy revolver and machine pistol banks hand-neutral.

Out of scope: ammunition (`COMBAT_SYSTEM.md` banner); `hands_required` enforcement (today it only sets a default).

## 11. Many hands

Nothing assumes two hands. Slots come from the species' grasping containers; the maximum today is three (human plus the cybernetic tail). The wheel covers every option with no cap, still one attack per round, so with six weapons each swings every sixth round. Extra hands buy readiness and disarm resistance, not damage (Q2).

Akimbo scales by data alone: `{2: ..., 4: ...}` lets four claw hands make one four-claw attack; with only `{2}`, four hands make two alternating pairs and three hands a pair plus a single. Order is defined, not hashed: species display order first, then augment slots alphabetically. A future multi-arm species lists its arm slots in that table.

Natural weapons on non-grasping hosts (Jawz) join the natural wheel with body-wide manipulation. A clawed hand can still wield an item; claws win by precedence. Disarm takes one item per success, now in stable order. `weapon_options()` returns the ordered wheel, so a future "k attacks per round" ruling takes the next k options without restructuring.

## 12. Migration

**Dropped 2026-10-06 (owner: *"Yeah. Clean up is good."*).** The read-only census on live, run before any function was written, found nothing to migrate:

| census item (live, 2026-10-06) | count |
|---|---|
| bodies with medical state | 155 |
| ability hosts in all | 8 |
| bodies with two or more living Nailz hosts | 0 |
| bodies with two shotgun arms | 0 |
| weapon references shared within a body | 0 |
| weapon references recorded on more than one body | 0 |
| stored limbs or heads whose snapshot records a weapon | 0 |
| `carbide blades` objects (to update to the one-hand prototype) | 0 |
| Iver Kestrel's ability hosts | 0 |

No one-shot function is written. What the migration would have settled, the live code now settles as it goes: a shared reference is resolved on every toggle (§3) and at every cut, living or corpse (§9), and a claw object spawns from the current prototype. The cross-body rule below stays as the description of what the code does at a cut; nothing stored needed it. The paragraphs that follow are kept as the record of the plan.

The plan was a one-shot `split_shared_ability_weapons()` in `world/medical/augments.py`, run once with `@py` at deploy with owner approval, with its own test and its counts in the PR, deleted in the next PR. Not a boot sweep.

Read-only census first: characters and NPCs with two or more `nailz` hosts; bodies with two shotgun arms; objects whose dbref is recorded on more than one body (a limb reattached before severance settled the share; the per-character pass cannot see these); Iver Kestrel (state captured first and left as found).

For each living character, for each ability with two or more living hosts, in slot order: hosts sharing a dbref keep it on the host whose hand holds the object, otherwise the first, and only if the object sits where it belongs (None for a natural weapon; for an integrated weapon, the character when deployed and None when retracted); the others drop the dbref, and a deployed one spawns its own object now. For natural weapons no player sees a change. For integrated hosts (two shotgun arms) the second arm gains a gun it never had, which seats in that hand and drops what it held: a visible mechanic change, to be labelled as such. A host whose object lies elsewhere (a severed appendage) drops both dbref and deployed. Each Nailz host's install-time ability spec is refreshed from the current `organ_spec`, or old installs lack the `_one` prose and render the old both-hands longdesc twice. Existing `NAILZ_CLAWS` objects are updated with Evennia's `batch_update_objects_with_prototype` after a read-only check that a live object carries the `from_prototype` tag. Snapshots sharing a dbref are counted and left alone.

**Cross-body shares.** A limb cut before cuts settled the share (on master) and reattached to another body leaves one object recorded by two living bodies, and no per-body code can see it; a stored appendage whose snapshot records a dbref a living body also records is the same share waiting to happen (surfaced by the #3696 review, round 7). The census lists both. The settle, across bodies: the body whose hand holds the object keeps it, else the body whose host is deployed, else the lower dbref; the others let go (a deployed natural host spawns its own at once; an integrated host clears its flag). A stored appendage's snapshot drops a dbref a living body keeps, so its reattach spawns fresh. With the migration dropped, this rule is moot for stored data; it remains the rule the cut applies (§9).

## 13. Slices

- **0 (now):** this spec; the ledger gap (§16). No issue.
- **1, claws plus the one door — SHIPPED** (PR A #3696 and #3701 on 2026-10-05, PR B #3702 on 2026-10-06; the migration PR C was dropped after the census, §12; #3695 and #3571 closed): per-host toggle; delete the mirror; per-location stow; `is_ability_deployed` and the director; readouts; `get_active_natural_weapons`; `weapon_choice.py` with grouping; repoint the 20 + 1 + 3 + 1 call sites and delete the five old functions; the hit term; manipulation by slots; the `NAILZ_CLAWS` profiles; the bank split; `_one` prose; reattach keeps the object; the migration. Held weapons keep range-then-max, but gates, initiate and the swing agree. Tests: rewrite `test_one_ability_two_hands.py` (one assertion inverts), `test_weapon_autoprioritizer.py`, `test_combat_manipulation_resolver.py`; add a test that both claw banks resolve all four phases. Specs: `AUGMENT_ABILITIES_SPEC.md` §1/§3/§8, `COMBAT_MESSAGE_FORMAT_SPEC.md`, `CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC.md` §6.1. Play, checked via splattercast: deploy, fight akimbo, sever, fight single, surgical stow, chrome reattach.
- **2, alternation and handguns — SHIPPED** (issue #3707, owner "Go." 2026-10-06; PRs #3709 and #3711 on 2026-10-06): ordered `Character.hands` (`slot_order`); the ndb cursor `NDB_LAST_WEAPON_SLOT`; `note_weapon_used` after the attack gates; the max rule removed; akimbo groups keep their slot place; the Nailz bank rename; disarm order; pistol bank rewrites. Play: two light pistols; pistol plus knife at range and in melee; arm-gun plus pistol; Nailz plus Jawz.
- **3, grip enforcement — SHIPPED (`hands_required`; owner ruling 2026-10-06, §14 #13; the implicit grip of GRIP_ENFORCEMENT_SPEC.md, PR #3717 on 2026-10-06):** a two-handed weapon occupies two grasping slots when wielded; one-handed use is refused or penalised by a ruling to come; the wheel treats the grip as one option (§4 step 1 already allows it). Touches wield, get, disarm and the hands view. Design pass first.
- **4, content by weapon type (issue #3718, owner rulings 2026-10-06, §14 #14):** pairing moves from per-item attributes to `AKIMBO_PROFILES_BY_TYPE` (rows `nailz`, `tiger_claws`, `light_pistol`; Nailz unchanged in play); the `TIGER_CLAWS` prototype (Voxhaul Tiger claw, one per hand, damage 6, weapons rack 180); banks `tiger_claws`, `tiger_claws_akimbo` (fresh glove prose, 19-23 / 24 per phase) and `light_pistol_akimbo` (16 per phase).

## 14. Owner rulings

Decided (slice 1 gates), owner's words verbatim:

- **#6 Akimbo is ONE attack on the pair profile**, never two swings; placeholders 6/+0 for one hand, 9/+1 for both. 2026-10-03: *"Ruling 1 seems fine."*
- **#2 Claws out and a weapon in the other hand.** Reach is checked first; among the options that can reach, deployed claws win outright. So at range a held pistol fires and the claws stay out; in melee the claws swing and the knife waits. 2026-10-03, after *"I agree about avoiding the odd case of claws being chosen at range - so I think we're aligned."* and the question *"So if claws are out and I'm holding a pistol but at range - which would the attack occur with?"* (the pistol): *"Ok. That makes sense."* The §4 order was changed to match.
- **#5 `/nailz` in a mixed state retracts every host**; otherwise it deploys every host. 2026-10-05: *"Retract both to sync up makes sense."*
- **#9 Reattachment keeps the hand's original claw or gun object**, parked back in the body, retracted. 2026-10-05: *"I concur. Keep it."*
- **#11 Claw accuracy uses the host hand's manipulation**; the fangs stay body-wide. 2026-10-05: *"Per hand makes sense. We want consistency."*
- **#12 Migration keeps deployed claws deployed** (the second object is spawned at once); the second shotgun arm gaining a gun is called out in the migration's counts as a mechanic change. 2026-10-05: *"Your rec is fine. We're still in pre-alpha."*

Decided (slice 2 gates), 2026-10-06, owner's words verbatim:

- **#1 Alternation replaces "then highest damage" among weapons that can reach; range-first stays.** *"Yes. Using a weapon which won't even be in-range to attack makes no sense. Our order of operation is sound."*
- **#3 Nailz and Jawz both out alternate.** *"Alternation seems fine. Maybe in a future state we can have an amalgamation of all cybernetic weapons so someone with a lot of arms can be quite interesting combat-wise."* (The amalgamation is a remark, recorded for later, not a decision.)
- **#4 Bonus and opportunity attacks turn the wheel.** Owner: *"I kinda defer to the easier design. Either is fine."* The easier design is the one door with no special case: every attack, scheduled or not, runs `process_attack`, which asks `choose_weapon` and notes the slot used; the wheel turns on every swing.
- **#7 Only the same `akimbo_family` pairs; heavy and light pistols alternate.** *"Yes, but the important part of this design is being able to assign Akimbo combinations so we can build on the system. Make sense?"* Combinations are data: `akimbo_family` and `akimbo_profiles` on the item; a later pairing table may name cross-family pairs without touching the door. (Slice 4, #14, made the table real and retired the item attributes: `AKIMBO_PROFILES_BY_TYPE`, keyed by `weapon_type`.)
- **#8 Rotation follows species display order (left hand first), which is also the default hand for wield, get and disarm; no dominant hand.** *"Species display order is fine. Eventually, we may want to setup dominant hand but that's a lot of complexity for minimal returns."*
- **#10 Nailz gets its own bank pair.** *"They should each get their own messaging pairs. They're distinctly different weapons."* Slice 2 renames the Nailz banks to `nailz` and `nailz_akimbo` (prototype `weapon_type` and the pair profile follow); `tiger_claws` and `tiger_claws_akimbo` are left for the held Tiger Claws.
- **#13 Ammunition stays out.** *"Ammunition, yes, it isn't design yet. Right?"* Right: `COMBAT_SYSTEM.md` lists ammunition as aspirational and not designed, with a standing note not to build it unasked. **`hands_required` enforcement is wanted; when is the builder's call.** Owner, after the ask was written down in §15: *"hands_require should have enforcement. Whether it happens now or in the future isn't relevant to me."* Placed as slice 3 (§13), after alternation.
- **#14 Akimbo pairs by weapon type; the bank inserts the item's name.** On the slice-4 draft (the Model 6 pairing with itself; a Voxhaul Tiger claw per hand at Nailz numbers, 180 on the rack; the claws' banks restored from history and the pistol pair bank new; nothing else to build): *"A. I dig it. I think the design would make sense to focus on weapon type akimbo combinations and then just insert the item name. Get me? This creates fewer dedicated pairings initially but covers a wider gauntlet. B. Seems fine. These are just staples. C. Cool. D. Cool."* So: one table keyed by `weapon_type`, the per-item `akimbo_family` / `akimbo_profiles` attributes retired (Nailz moves into the table with the same numbers and banks), `{item_name}` in the pair banks. The claws' banks were written fresh rather than restored: #10 gives each weapon its own prose, and the historical bank is the Nailz pair bank under another name.

Slice 1 close-out, 2026-10-06, owner's words: *"Yeah. Clean up is good."* The migration (§12) is dropped: the census found nothing to migrate. #3699 (the escort usher's identity comparison) is taken next: *"Sure."*

## 15. Risks

**`hands_required` (open ruling, §14 #13).** Today `hands_required` is written once at item creation (`typeclasses/items.py`, every item gets 1) and two ranged prototypes declare 2; nothing reads it. "Enforcement" would mean: a two-handed weapon occupies two grasping slots when wielded (so a one-armed body cannot bring a rifle to bear, and the other hand cannot hold a knife while it is up), firing or swinging it with one hand is refused or penalised, and the wheel treats the two-slot grip as one option (§4 step 1 already allows that). It touches wield, get, disarm and the hands view, and it is the one-handed-shooter question the owner has not ruled on. Ruled 2026-10-06: enforcement is wanted, timing is the builder's (§14 #13). It is slice 3 (§13): its own design pass first (grip slots, the one-handed penalty or refusal, what a one-armed body can bring to bear), then the build. The design pass is `GRIP_ENFORCEMENT_SPEC.md` (proposal, 2026-10-06); its §6 lists the five rulings to ask. Correction: five prototypes resolve to `hands_required` 2 (the ranged base plus the anti-material rifle, inherited by four long guns), not two.


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

One-weapon numbers stay prototype data, like every other weapon; the pair rows (Nailz 9/+1, Tiger claws 9/+1, two light pistols 16/−1) are the `AKIMBO_PROFILES_BY_TYPE` table in `world/combat/constants.py` since slice 4. All of them and the `hit_bonus` term are untuned placeholders; `BALANCE_LEDGER.md` records them under "Gaps the ledger is NOT sized against" until the balance pass. The ledger test collects only the annotated constants in that file, so the table needs no ledger row.

## See also

`AUGMENT_ABILITIES_SPEC.md` (decisions 4 and 7, §8), `ANATOMY_AUGMENTS_SPEC.md`, `COMBAT_SYSTEM.md`, `COMBAT_MESSAGE_FORMAT_SPEC.md`, `CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC.md` (§6.1, Q1, Q2), `roadmaps/BALANCE_LEDGER.md`, defect #3571.
