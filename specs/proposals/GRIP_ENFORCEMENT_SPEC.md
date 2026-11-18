# Grip Enforcement (`hands_required`)

A weapon's `hands_required` says how many hands it wants. This spec enforces it: a two-handed weapon swung without a second hand free is under-gripped and loses accuracy. It is never refused. It is the grip half of `MULTI_WEAPON_COMBAT_SPEC.md` (§5; ruling §14 #13); issue #3716.

Owner ruling 2026-10-06 (#3716), verbatim: *"hands_require should have enforcement. Whether it happens now or in the future isn't relevant to me."*

## 0. What was decided before this spec

`CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC.md` §6.1 (decided 2026-06-20) set the shape:

- A weapon's `hands_required` is a **minimum**; the gripping effectors must meet it.
- **Under-gripping** (a two-handed weapon held one-handed) is a **scaled handling penalty, not a flat tier** and not a refusal.
- Two hands on one weapon: the weaker hand drags it (`min`, in `manipulation_hit_factor`).
- Disarm takes one item per success; a two-handed weapon held in two hands disarms as one item.

These four were not re-asked. §6 holds the rulings made for this spec.

## 1. What exists

### Data

- `WEAPON_ATTR_HANDS_REQUIRED` (in `world/combat/constants.py`, beside the other weapon attribute constants) names the attribute; it is read with default 1.
- `typeclasses/items.py` writes `hands_required = 1` on every Item at creation.
- `RANGED_WEAPON_BASE` declares 2, and five long guns inherit it: pump shotgun, break shotgun, bolt rifle, assault rifle, anti-material rifle (the last explicitly).
- The pistols, the SMG, the two arm-guns and the claws override to 1. The fangs declare 0.
- The baseball bat, the staff and the chainsaw are `hands_required` 2 in `world/prototypes.py` (ruling 3), as their banks swing them.
- The long sword and katana stay 1 (hand-and-a-half, one-handed by their prose); the long sword's bank calls it two-handed once. The SMG stays 1 as its prototype says, although its bank shoulders a stock.

Three places read the value:

- the one door, into `WeaponChoice.hands_required` for the roll (`_hands_required` in `world/combat/weapon_choice.py`);
- `Character.wants_two_hands`, for the inventory marker;
- `Character.grip_notes`, for the wield and get notes.

### One object in two slots

No command forms a two-slot grip, but the store can hold one.

- `held_items` is a plain slot→item dict with no constraint, and the `hands` setter merges per key, so one object in two slots is a legal store.
- `wield_item` refuses it ("You're already wielding X in your other hand").
- The one path that forms one by accident: a hand broken in place drops out of the hands view while its item stays in the store; `wield` that item into the other hand, and when the bone heals the object sits in two slots.

**Readers that handle two slots:** the one door builds one option with both slots (`weapon_choice._candidates`); the wheel keys it by its first slot; `manipulation_hit_factor` takes the minimum over the slots; `release_slots` clears every slot holding an object; `move_to` out of the body fires `release_slots` through `at_object_leave`.

**Readers that half-work with two slots:** `inventory`, `look` and the LLM persona list the object once per slot; throw's `remove_from_hand` clears one slot and leaves the other pointing at an object in flight for two seconds; `wrest`'s failure path restores one slot; `free hands` prints a stray "not holding anything" for the second slot.

## 2. Design at a glance: the grip is implicit

A two-handed weapon sits in one hand, as every weapon does. There is no stored grip. At the moment of the swing the game asks one question: is another grasping slot free?

- **Free:** full grip, no penalty.
- **Full or gone:** under-gripped, the penalty applies.

The state is exactly what `inventory` shows. This is what CAPACITY §6.1 said in June ("2H weapon held one-handed, **no free second hand**").

**Overturned intention.** A stored two-slot grip, with `wield rifle` taking both free hands and `wield rifle in left` taking one on purpose, was put to the owner as ruling 5. After the rulings the owner chose the implicit grip instead (2026-10-06, #3716): *"I'm concerned about ruling 5 and the logic. Seems like it'll cause issues with juggling items and it'll be unclear to players."* ... *"Sounds good to me."*

Everything else is unchanged by the grip: wield and get pick hands as before; disarm takes the item; the wheel sees one option; many hands means a spare steadying hand.

### 2.3 Telling the player

- The `inventory` Held line marks a two-handed weapon "(two-handed)". This is the one display change; `look` and the persona are untouched.
- When a wield, a get, or a plate pulled from its carrier fills the last free hand, the line says what it cost, naming the weapon: "The PAM Pathfinder rifle hangs one-handed."
- When the weapon taken is itself two-handed and no second hand is free: "It wants both hands."
- The taken weapon is spoken of first, and each weapon is named once.
- A get that moves a held item to inventory to free a hand speaks only about the taken weapon.

## 3. The cut

`detach_items_to_appendage` (in `typeclasses/items.py`) drops the cut hand's item through a move that clears every slot holding it, then re-reads the store and clears only the cut keys. It does not write back a snapshot taken before the drop: with one object in two slots, a written-back snapshot would leave the surviving slot pointing at an object on the floor. So a surviving slot keeps no ghost. This matters because the grip factor reads the hands view.

## 4. The penalty

`grip_hit_factor(choice, free_slots)` in `world/combat/capacity.py`, beside `manipulation_hit_factor`:

- 1.0 for a natural or integrated weapon, for a weapon wanting one hand, or when the slots held plus the free slots meet the requirement.
- Otherwise `effective = min(required, held + free)`, and the factor is `_piecewise(effective / required, UNDER_GRIP_CURVE)`.
- `UNDER_GRIP_CURVE` anchors are placeholders: `(0, 0.20), (0.5, 0.60), (2/3, 0.80), (1, 1.0)`. So one of two hands gives 0.6 and two of three give 0.8 (ruling 4). They are recorded in `BALANCE_LEDGER.md`.

`process_attack` multiplies the factor into the attacker's effective skill beside manipulation, and logs it in the `ATTACK_CAPACITY` line. A rifle in one healthy hand computes the same manipulation factor as a pistol; only with no free grasping slot elsewhere on the body does `grip_hit_factor` also apply (0.60 for one of two hands).

It is a separate factor. It is not folded into `hit_bonus`, because an akimbo profile replaces that. It is not inside `manipulation_hit_factor`, because that function's override and fail-open paths have nothing to do with a grip.

Ranged and melee alike. The aim verbs peek the same choice and need no change.

## 5. Bodies

- **One hand.** A one-armed body has no second slot, so a two-handed weapon is always under-gripped; nothing is refused (ruling 1). The initiate and aim prose do not change.
- **Broken in place.** A hand broken in place (its metacarpals at 0 HP) drops out of the hands view, so it is no longer a free slot; the factor applies until it heals. The object a broken hand held stays in the store under the hidden slot (pre-existing; not fixed by this spec).
- **Cut.** Cut or break the free hand and the weapon stays where it is, now under-gripped. Cut the holding hand and its item drops, as every held item does. A two-handed weapon in the other hand stays and is under-gripped from then on (ruling 2 falls out of the model). No grip state needs clearing.
- **Three or more hands.** A tail or a third arm is one more slot that may be free: a rifle in one hand and a pistol in the other still have a steadying tail. Extra hands buy readiness, as §11 of the multi-weapon spec promised.
- **Integrated and natural weapons.** Never under-gripped; their requirement is satisfied by their own body (the arm-gun's "flesh hand steadying" is flavour).

## 6. Owner rulings

Decided 2026-10-06 (#3716), owner's words verbatim, asked one per turn:

1. **Penalised, never refused.** The standing decision (CAPACITY §6.1, 2026-06-20) stands: under-gripping is a scaled penalty; a one-armed body still brings a rifle to bear, badly. *"Confirmed."*
2. **A cut hand mid-grip: the weapon stays.** A two-hand weapon stays in the surviving hand, under-gripped, when one gripping hand is cut; the cut's narrative says so (📋 UNBUILT (no issue): no cut line mentions the grip, and whether one is still wanted under the implicit grip is not decided). *"It stays."* (The hand that still holds it holds it, the rule the claws follow.)
3. **Melee two-handers by data.** The baseball bat, the staff and the chainsaw become `hands_required 2`; the long sword and katana stay 1 (hand-and-a-half, one-handed by their prose); the SMG stays 1 as its prototype says. *"Yes."*
4. **The placeholder.** One of two hands → 0.6 on accuracy; two of three → 0.8; recorded in `BALANCE_LEDGER.md` beside the claws' placeholders, nothing tuned. *"Sure."*
5. **Nobody under-grips by choice.** Asked whether `wield rifle` takes both free hands and `wield rifle in left` takes one on purpose: *"Tricky. I think people should only wield in one-hand or under-grip when no other options is present. Reasonable?"* Carried out by the implicit grip (§2): a two-handed weapon is under-gripped exactly when no other hand is free, never by a player's choice; wield and the named-hand form are unchanged.

## 8. Risks

- Reading `hands_required` off every Item means corpses, radios and terminals carry a 1 nobody meant. Nothing filters by tag: the roll reads the value off whatever item the one door picks, an improvised one included, and the marker and the grip notes read it off any held item. A radio never wants two hands only because every Item is written 1 at creation.
- Live objects carry whatever was written at spawn. A melee data change reaches existing objects only through the prototype batch update or a respawn. Census first.

## Unbuilt

- 📋 UNBUILT (no issue): a cut line that mentions the grip when one gripping hand is cut (ruling 2). Whether one is still wanted under the implicit grip is not decided; see below.

## Not decided

- Whether the cut's narrative should still mention the grip under the implicit grip (ruling 2).

## See also

`MULTI_WEAPON_COMBAT_SPEC.md` §4 (the one door), §5 (grip), §6 (the wheel), §11 (many hands); `CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC.md` §6.1; `BALANCE_LEDGER.md`; #3697 (hand-only sever of an arm-gun), #3710 (bank prose sweep).
