# Grip Enforcement (`hands_required`)

> **Status:** 📋 Proposal — designed 2026-10-06 from a read-only map of the tree; the five rulings decided the same day (§6); the grip model changed to the implicit one the same evening on the owner's concern (§2); in build as #3716. Slice 3 of `MULTI_WEAPON_COMBAT_SPEC.md` (§13, §15). Owner ruling 2026-10-06, verbatim: *"hands_require should have enforcement. Whether it happens now or in the future isn't relevant to me."*

## 0. What is already decided

`CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC.md` §6.1 (decided 2026-06-20) settled the shape before this proposal:

- A weapon's `hands_required` is a **minimum**; the gripping effectors must meet it.
- **Under-gripping** (a two-handed weapon held one-handed) is a **scaled handling penalty, not a flat tier** and not a refusal.
- Two hands on one weapon: the weaker hand drags it (`min`, already shipped in `manipulation_hit_factor`).
- Disarm takes one item per success; a two-handed weapon held in two hands disarms as one item.

This proposal builds on those four sentences. §6 lists what still needs the owner's word.

## 1. What exists today

- **The attribute reads nothing.** `typeclasses/items.py` writes `hands_required = 1` on every Item at creation; `RANGED_WEAPON_BASE` declares 2 and five long guns inherit it (pump shotgun, break shotgun, bolt rifle, assault rifle, anti-material rifle, the last explicitly); the pistols, the SMG, the two arm-guns and the claws override to 1; the fangs declare 0. No code reads the value. `TENNIS_RACKET` declares a stray `"hands": 1` that nothing reads either.
- **No melee weapon is two-handed in data**, while the banks say otherwise for the baseball bat ("a two-handed grip"), the staff ("in both hands") and, by nature, the chainsaw; the long sword's bank calls it two-handed once (a hand-and-a-half weapon); the SMG's prototype says one-handed while its bank shoulders a stock.
- **A two-slot grip is storable but unreachable.** `held_items` is a plain slot→item dict with no constraint, and the `hands` setter merges per key, so one object in two slots is a legal store. `wield_item` refuses it ("You're already wielding X in your other hand"), and no command forms one. The one path that forms one by accident: a hand broken in place (its metacarpals at 0 HP) drops out of the hands view while its item stays in the store; `wield` that item into the other hand, and when the bone heals the object sits in two slots.
- **Readers that already handle two slots:** the one door builds one option with both slots (`weapon_choice._candidates`), the wheel keys it by its first slot, `manipulation_hit_factor` takes the minimum over the slots, `release_slots` clears every slot holding an object, and `move_to` out of the body fires `release_slots` through `at_object_leave`.
- **Readers that would half-work with two slots:** `inventory`, `look` and the LLM persona list the object once per slot; throw's `remove_from_hand` clears one slot and leaves the other pointing at an object in flight for two seconds; `wrest`'s failure path restores one slot; `free hands` prints a stray "not holding anything" for the second slot.
- **One latent bug a two-slot grip would hit at the cut:** `detach_items_to_appendage` snapshots the store, drops the cut hand's item (which clears every slot through the move hook), then writes the stale snapshot back, so the surviving hand would point at an object lying on the floor. Reachable today only through the broken-hand path above.
- **Under-gripping costs nothing:** a rifle in one healthy hand computes the same manipulation factor as a pistol, and a proper two-hand grip can only cost (the weaker hand drags). The incentive is backwards.

## 2. Design at a glance

**The grip is implicit.** A two-handed weapon sits in one hand, as every weapon does today; there is no stored grip. At the moment of the swing the game asks one question: is another grasping slot free? Free, full grip, no penalty. Full or gone, under-gripped, the penalty. The state is exactly what `inventory` shows. This is what CAPACITY §6.1 said in June ("2H weapon held one-handed, **no free second hand**"), and the owner chose it over a stored two-slot grip after the rulings: *"I'm concerned about ruling 5 and the logic. Seems like it'll cause issues with juggling items and it'll be unclear to players."* ... *"Sounds good to me."*

1. **Data.** `WEAPON_ATTR_HANDS_REQUIRED` beside the other weapon attribute constants; read with default 1; the bat, the staff and the chainsaw gain `hands_required 2` (ruling 3); `TENNIS_RACKET`'s stray `hands` key goes.
2. **The penalty.** `WeaponChoice` carries `hands_required`. `grip_hit_factor(choice, free_slots)` in `world/combat/capacity.py` beside `manipulation_hit_factor`: 1.0 for a natural or integrated weapon, for a weapon wanting one hand, or when the slots held plus the free slots meet the requirement; otherwise the placeholder curve by effective hands over required (1 of 2 → 0.6, 2 of 3 → 0.8; ruling 4). `process_attack` multiplies it into the attacker's effective skill beside manipulation and logs it in the `ATTACK_CAPACITY` line.
3. **Telling the player.** The `inventory` Held line marks a two-handed weapon "(two-handed)". When a wield or a get fills the last free hand, the line says what it cost: "The bolt-action rifle hangs one-handed." When the weapon taken is itself two-handed and no second hand is free: "It wants both hands."
4. **Hands come and go** (ruling 2, "It stays"). Cut or break the free hand and the weapon stays where it is, now under-gripped; cut the holding hand and it drops, as every held item does. No state to clear.
5. **Everything else is unchanged.** Wield and get pick hands as today; disarm takes the item; the wheel sees one option; many hands means a spare steadying hand.

## 3. The cut's stale write-back

`detach_items_to_appendage` drops the cut hand's item through a move that clears every slot holding it, then writes a snapshot taken before the drop back into the store. With one object in two slots (reachable today through the broken-hand path, §1) the surviving slot would point at an object on the floor. The store is re-read after the drops and only the cut keys are cleared. Fixed first, with its own test, because the grip factor reads the hands view.

## 4. The penalty in detail

- `grip_hit_factor(choice, free_slots)`: `effective = min(required, held + free)`; below the requirement, `_piecewise(effective / required, UNDER_GRIP_CURVE)` with the placeholder anchors `(0, 0.20), (0.5, 0.60), (2/3, 0.80), (1, 1.0)`; recorded in `BALANCE_LEDGER.md`.
- A separate factor, not folded into `hit_bonus` (an akimbo profile replaces that) and not inside `manipulation_hit_factor` (its override and fail-open paths have nothing to do with a grip).
- Ranged and melee alike. The aim verbs peek the same choice and need no change.

## 5. Bodies

- **One hand.** A one-armed body has no second slot, so a two-handed weapon is always under-gripped; nothing is refused (ruling 1). The initiate and aim prose do not change.
- **Broken in place.** The hand drops out of the view, so it is no longer a free slot; the factor applies until it heals. The object a broken hand held stays in the store under the hidden slot (pre-existing; not fixed here).
- **Cut.** The cut hand's item drops as today; a two-handed weapon in the other hand stays and is under-gripped from then on (ruling 2 falls out of the model).
- **Three or more hands.** A tail or a third arm is one more slot that may be free: a rifle in one hand and a pistol in the other still have a steadying tail. Extra hands buy readiness, as §11 of the multi-weapon spec promised.
- **Integrated and natural weapons.** Never under-gripped; their requirement is satisfied by their own body (the arm-gun's "flesh hand steadying" is flavour).

## 6. Owner rulings

Decided 2026-10-06, owner's words verbatim, asked one per turn:

1. **Penalised, never refused.** The standing decision (CAPACITY §6.1, 2026-06-20) stands: under-gripping is a scaled penalty; a one-armed body still brings a rifle to bear, badly. *"Confirmed."*
2. **A cut hand mid-grip: the weapon stays.** A two-hand weapon stays in the surviving hand, under-gripped, when one gripping hand is cut; the cut's narrative says so. *"It stays."* (The hand that still holds it holds it, the rule the claws follow.)
3. **Melee two-handers by data.** The baseball bat, the staff and the chainsaw become `hands_required 2`; the long sword and katana stay 1 (hand-and-a-half, one-handed by their prose); the SMG stays 1 as its prototype says. *"Yes."*
4. **The placeholder.** One of two hands → 0.6 on accuracy; two of three → 0.8; recorded in `BALANCE_LEDGER.md` beside the claws' placeholders, nothing tuned. *"Sure."*
5. **Nobody under-grips by choice.** Asked whether `wield rifle` takes both free hands and `wield rifle in left` takes one on purpose: *"Tricky. I think people should only wield in one-hand or under-grip when no other options is present. Reasonable?"* Carried out by the implicit grip (§2): a two-handed weapon is under-gripped exactly when no other hand is free, never by a player's choice; wield and the named-hand form are unchanged.

Decided before this proposal and not re-asked: the minimum, the scaled penalty, the weaker hand drags, disarm takes the whole weapon.

## 7. Slices

- **3, one issue (#3716):** the constant and reads; `TENNIS_RACKET`; bat, staff, chainsaw to 2; `WeaponChoice.hands_required`; `grip_hit_factor` in the roll with its audit line; the inventory marker; the wield and get notices; the stale write-back fixed first. Tests: the factor by hands (free, full, gone, one-hander, natural, integrated, two of three); the roll with and without a free hand; the marker; the notices; the data; the cut leaves no ghost in the surviving slot. Play: a rifle with a free hand (no grip line in the audit), with a bottle in the other hand (0.60), on a one-armed body (0.60); the inventory marker; the notice.

## 8. Risks

- Reading `hands_required` off every Item means corpses, radios and terminals carry a 1 nobody meant; the reads are guarded by the weapon tag path (the door's real-weapon filter) so a radio in hand never counts.
- Live objects carry whatever was written at spawn; a melee data change (3b) reaches existing objects only through the prototype batch update or a respawn. Census first.
- The inventory marker is the one display change; `look` and the persona are untouched.

## See also

`MULTI_WEAPON_COMBAT_SPEC.md` §4 (the one door), §6 (the wheel), §11 (many hands), §13, §15; `CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC.md` §6.1; `BALANCE_LEDGER.md`; #3697 (hand-only sever of an arm-gun), #3710 (bank prose sweep).
