# Grip Enforcement (`hands_required`)

> **Status:** 📋 Proposal — designed 2026-10-06 from a read-only map of the tree; the five rulings decided the same day (§6); nothing built. Slice 3 of `MULTI_WEAPON_COMBAT_SPEC.md` (§13, §15). Owner ruling 2026-10-06, verbatim: *"hands_require should have enforcement. Whether it happens now or in the future isn't relevant to me."*

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

1. **Data.** `WEAPON_ATTR_HANDS_REQUIRED` beside the other weapon attribute constants; read with default 1; prototypes gain `hands_required` where their banks already say two hands (§6, ruling 3). `TENNIS_RACKET`'s stray key is fixed.
2. **The grip.** `wield <weapon>` takes as many free grasping slots as the weapon requires, up to what is free, in the body's slot order; with fewer free slots than required it takes what it can and the wield line says so (ruling 5: nobody under-grips by choice). `wield <weapon> in <hand>` names the leading hand; a two-hander still takes a second free hand when one exists. Wielding a weapon already in hand adds a free slot to its grip instead of refusing. One object in several slots is one entry in `inventory`, `look` and the persona, marked "(both hands)" or "(all N hands)".
3. **The penalty.** `WeaponChoice` gains `hands_required` and `grip` (slots held); `process_attack` multiplies the attacker's effective skill by a **grip factor** when `grip < hands_required`, a separate term beside manipulation so it survives the manipulation override and the fail-open paths. Placeholder: one of two hands → 0.6; recorded in `BALANCE_LEDGER.md`. A natural weapon and an integrated weapon are never under-gripped (their requirement is their own body).
4. **Hands come and go.** The grip is whatever slots hold the object when the swing happens, so a hand broken in place or healed changes the factor with no state to clear. What a cut does to a two-hand grip is ruling 2 (§6).
5. **Everything else reads the view.** Free-hand pickers (get, give, catch, armor, shops) see no free slot while both are gripped: "hands full" as today. Disarm takes the whole weapon (decided). The wheel sees one option (shipped). Surplus-limb initiative counts free grasping limbs as today.
6. **Prose, v1.** One line at wield time for an under-grip ("You take the rifle in one hand; it wants two."); the `(both hands)` marker; no bank changes.

## 3. The grip in detail

**Forming it.** `CmdWield` resolves the weapon, reads `hands_required` (default 1), lists free slots in `slot_order`, and calls `wield_item(item, hands=[...])` with up to `hands_required` of them. With a named hand, that slot first and then the next free slots up to the requirement (ruling 5). With zero free slots, the current refusal.

**Growing it.** `wield rifle` while the rifle is already held in one slot and another is free adds the free slot. The refusal "already wielding X" remains only when no slot is free.

**Breaking it.** Any move of the object out of the body clears every slot (`release_slots`, shipped). `unwield`, `drop`, `give`, `throw`, `wrest` and death already end there; throw's `remove_from_hand` and wrest's restore are made to clear and restore every slot the grip had. `detach_items_to_appendage` re-reads the store after each drop instead of writing a stale snapshot back (the latent bug in §1, fixed first and on its own).

**Showing it.** `inventory` Held, `look` and the LLM persona group slots by object: "a bolt-action rifle (both hands)". `list_held_items` follows.

## 4. The penalty in detail

- `grip_hit_factor(choice)` in `world/combat/capacity.py` beside `manipulation_hit_factor`: `1.0` when `choice.natural`, when `hands_required <= 1`, or when `len(choice.slots) >= hands_required`; otherwise the placeholder curve by `held / required` (1/2 → 0.6; 2/3 → 0.8 for a future three-hand weapon). `process_attack`: `effective_skill = motorics × sight × manipulation × grip`, logged to splattercast as `ATTACK_CAPACITY ... grip 0.60` when below one.
- Not folded into `hit_bonus`: an akimbo profile replaces `hit_bonus`, and the manipulation override would null a grip penalty that has nothing to do with chrome.
- Ranged and melee alike; the aim verbs peek the same choice and need no change.

## 5. Bodies

- **One hand.** A one-armed body wields a rifle under-gripped and fights at the factor; nothing is refused (ruling 1 confirms or overturns). The initiate and aim prose do not change.
- **Broken in place.** The hand drops out of the view, the object stays in the store under the hidden slot; the view-side grip shrinks, the factor applies, and heal restores it. Pre-existing and now paid for, not fixed here.
- **Cut.** Today the cut hand's item drops and the whole grip ends. Ruled (2): a two-hand grip stays in the surviving hand, under-gripped; only a one-slot grip's item drops with its hand.
- **Three or more hands.** A tail or a third arm is one more free slot; a two-hand weapon takes two in slot order and the rest stay free; a four-armed body can grip a rifle and still draw a pistol.
- **Integrated and natural weapons.** Never under-gripped; their requirement is satisfied by their own body (the arm-gun's "flesh hand steadying" is flavour).

## 6. Owner rulings

Decided 2026-10-06, owner's words verbatim, asked one per turn:

1. **Penalised, never refused.** The standing decision (CAPACITY §6.1, 2026-06-20) stands: under-gripping is a scaled penalty; a one-armed body still brings a rifle to bear, badly. *"Confirmed."*
2. **A cut hand mid-grip: the weapon stays.** A two-hand weapon stays in the surviving hand, under-gripped, when one gripping hand is cut; the cut's narrative says so. *"It stays."* (The hand that still holds it holds it, the rule the claws follow.)
3. **Melee two-handers by data.** The baseball bat, the staff and the chainsaw become `hands_required 2`; the long sword and katana stay 1 (hand-and-a-half, one-handed by their prose); the SMG stays 1 as its prototype says. *"Yes."*
4. **The placeholder.** One of two hands → 0.6 on accuracy; two of three → 0.8; recorded in `BALANCE_LEDGER.md` beside the claws' placeholders, nothing tuned. *"Sure."*
5. **Nobody under-grips by choice.** Asked whether `wield rifle` takes both free hands and `wield rifle in left` takes one on purpose: *"Tricky. I think people should only wield in one-hand or under-grip when no other options is present. Reasonable?"* So: a two-handed weapon takes both hands whenever two are free, even when a hand is named (the named hand leads); it is held one-handed only when no second free hand exists, because the other hand is full or gone. The named-hand form keeps its meaning for one-handed weapons.

Decided before this proposal and not re-asked: the minimum, the scaled penalty, the weaker hand drags, disarm takes the whole weapon.

## 7. Slices

- **3a, the grip and the penalty** (one issue): the constant and reads; `TENNIS_RACKET`; `wield_item(hands=...)` and `CmdWield` taking up to `hands_required` free slots, growing a grip, the named-hand form; grouped display in `inventory`, `look`, the persona; throw and wrest clearing and restoring every slot; the stale write-back in `detach_items_to_appendage` fixed first and tested; `WeaponChoice.hands_required` and `grip`; `grip_hit_factor` in the roll with its splattercast line; the wield-time line. Tests: a rifle takes two hands; a named hand takes one; a second wield grows the grip; one display line per object; the factor by held/required; natural and integrated never penalised; the cut leaves no ghost in the surviving slot. Play: wield a rifle one- and two-handed and read the audit factor; sever one hand of a two-hand grip.
- **3b, melee data** (ruled): bat, staff, chainsaw to 2; their banks already agree.
- **3c, the cut** (ruled: it stays): `detach_items_to_appendage` drops only a one-slot grip's item; a multi-slot grip loses the cut slot and keeps the rest, with its narrative line.

## 8. Risks

- Reading `hands_required` off every Item means corpses, radios and terminals carry a 1 nobody meant; the reads are guarded by the weapon tag path (the door's real-weapon filter) so a radio in hand never counts.
- Live objects carry whatever was written at spawn; a melee data change (3b) reaches existing objects only through the prototype batch update or a respawn. Census first.
- The grouped display touches `look`, `inventory` and the persona; a stray double listing would be visible at once in play.

## See also

`MULTI_WEAPON_COMBAT_SPEC.md` §4 (the one door), §6 (the wheel), §11 (many hands), §13, §15; `CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC.md` §6.1; `BALANCE_LEDGER.md`; #3697 (hand-only sever of an arm-gun), #3710 (bank prose sweep).
