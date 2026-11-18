# Clothing System Specification

The clothing system lets a character wear items that change how the body reads. A worn garment hides the longdesc of every body location it covers and shows its own worn description instead. Garments stack in layers, and a garment can have style states (rolled up, zipped, buttoned, hood up) that change both what it covers and how it reads. There are no separate clothing classes: any `Item` (`typeclasses/items.py`) with a `coverage` list and a `worn_desc` is clothing. Third-party clothing is the consent-gated `dress` / `undress` (see TRUST_AND_CONSENT_SPEC).

## Core Principles

1. **Coverage-based visibility**: clothing hides the body locations it covers and adds its own description.
2. **Dynamic styling**: a garment can have several style states, each able to change coverage and appearance.
3. **Layering**: several garments can be worn at once, under layering rules.
4. **Shared locations**: clothing uses the same body locations as longdesc.
5. **Appearance integration**: worn descriptions join the longdescs in the character's appearance.
6. **Roleplay**: style commands are roleplay actions with in-character feedback.
7. **Pronouns**: worn descriptions use the grammar engine's `{their}`/`{they}` brace tokens, **not** Evennia's `$pron()`, which does not work in prototypes; it works only in `msg_contents()` calls during runtime messaging (see §Writing worn descriptions and `GRAMMAR_ENGINE_SPEC.md`).
8. **Colour**: worn descriptions can carry ANSI colour.

## Body locations

- Clothing coverage and longdesc use the same location names.
- The source is the species registry (`default_longdesc_locations` in `world/anatomy/species.py`). `world/combat/constants.py` copies the human set (`DEFAULT_LONGDESC_LOCATIONS`; `CLOTHING_LOCATIONS` is the same set).
- Nothing checks a garment's `coverage` list against the body's locations at runtime. A misspelt location is accepted and covers nothing.

Example coverage lists:

```
shirt:     ["chest", "back", "abdomen"]
trousers:  ["groin", "left_thigh", "right_thigh"]
jacket:    ["chest", "back", "abdomen", "left_arm", "right_arm"]
gloves:    ["left_hand", "right_hand"]
boots:     ["left_foot", "right_foot"]
hat:       ["head"]
full robe: ["chest", "back", "abdomen", "groin", "left_arm", "right_arm", "left_thigh", "right_thigh"]
```

## The clothing item

An item is wearable when it has both `coverage` and `worn_desc` (`Item.is_wearable`). Whether an item is worn is asked of the wearer: `character.is_item_worn(item)` (`ClothingMixin`, `typeclasses/clothing_mixin.py`).

Attributes on `Item`:

| attribute | meaning |
|---|---|
| `coverage` | body locations covered in the base state; empty = not wearable |
| `worn_desc` | the description shown when worn, in the base state; empty = not clothing |
| `color` | one colour name, filled into a `{color}` token (see §Colour) |
| `material` | stored on the item (e.g. leather, steel, silk); no worn description reads it |
| `layer` | a property, not a stored field: see §Layers |
| `style_properties` | the current state of each style property, e.g. `{"adjustable": "rolled", "closure": "zipped"}`; persisted, so a garment keeps its states across sessions |
| `style_configs` | every state the garment declares, per property (optional) |

Each garment has two descriptions: the item description (`db.desc`), shown when it is not worn (inventory, on the ground), and the worn description, shown on the wearer.

The disguise attributes (`is_disguise_item`, `disguise_essential`, `disguise_type_id`, `disguise_weight`, `disguise_adjective`, `worn_sdesc_short`) also live on `Item`; see IDENTITY_RECOGNITION_SPEC §Disguise Items.

### The `style_configs` shape

Authors follow this shape:

```python
"style_configs": {
    "adjustable": {
        "normal": {"coverage_mod": [], "desc_mod": ""},   # empty desc_mod = use base worn_desc
        "rolled": {"coverage_mod": ["-left_arm", "-right_arm"],
                   "desc_mod": "a complete worn description of the garment rolled up"},
    },
    "closure": {
        "zipped":   {"coverage_mod": [], "desc_mod": "a complete worn description when zipped"},
        "unzipped": {"coverage_mod": ["-chest", "-abdomen"],
                     "desc_mod": "a complete worn description when unzipped"},
    },
}
```

- `coverage_mod` entries are `+location` (add) or `-location` (remove).
- A `desc_mod` **replaces** the whole `worn_desc`; it is not a suffix. Write each one as a full description that reads correctly on its own. All non-empty `desc_mod` values in `world/prototypes.py` are written this way — see `WORK_COVERALLS`.
- A state may leave `coverage_mod`, `desc_mod`, or both empty. The thermal shirt's `rolled` (`THERMAL_SHIRT`) changes prose without changing coverage.
- `get_style_property` returns `"normal"` for a property with no current state. `get_available_style_properties` lists each property and its declared states.
- A garment can have one, both, or neither property.

**Generic property naming.** The `adjustable` property covers any roll/unroll feature (sleeves, hoods, cuffs, pant legs, a tie), so no specific property is needed per kind of adjustment. `closure` covers zipper, buttons, laces and the like.

### Current coverage and current description

**Coverage combines.** `Item.get_current_coverage()` starts from the base `coverage` and applies the `coverage_mod` of every active property, in sorted property-name order, cumulatively. A jacket with base coverage `["chest", "back", "abdomen", "left_arm", "right_arm"]`, `rolled` removing both arms and `unzipped` removing chest and abdomen, has four states:

| adjustable | closure | coverage |
|---|---|---|
| normal | zipped | chest, back, abdomen, left_arm, right_arm |
| rolled | zipped | chest, back, abdomen |
| normal | unzipped | back, left_arm, right_arm |
| rolled | unzipped | back |

**Descriptions do not combine.** `Item.get_current_worn_desc()` returns the FIRST non-empty `desc_mod` in sorted property-name order and stops; with none, it returns the base `worn_desc`. A full stop is added to a `desc_mod` that lacks one; the base `worn_desc` always has a full stop appended, so a `worn_desc` should not end with one. So a `look` shows one style description at a time, and when two properties are both off their plain state only the `adjustable` one narrates (it sorts before `closure`). In the fourth jacket state above, the `rolled` description shows alone.

## Writing worn descriptions

**Pronouns are tokens (#2396).** `Item.get_current_worn_desc_with_perspective()` takes the current worn description, fills `{color}`, and passes it to the wearer's `_process_description_variables(..., force_third_person=True)` — the same token processor longdescs use. `{their}` resolves against the wearer's apparent gender and renders "his" / "her" / "its", in third person even when the wearer looks at themselves. A literal `their` is never touched and renders "their" on everybody, so it is wrong for any wearer who is not a plural.

- Any pronoun referring to the WEARER is a token — `{their}`, `{them}`.
- A pronoun referring to the GARMENT stays plain prose ("office trousers holding their line", "its ripstop fabric"), because the garment's number does not change with who wears it.
- Body-part references may use `{their} chest` or `the chest`; both read correctly. `{their}` is preferred for new work, as in `COMBAT_BOOTS`.
- Prototype worn descriptions and style `desc_mod`s use the same tokens; `$pron()` is not used.

**No wearer history.** A worn_desc must never assert the WEARER'S history — it is the same string on everyone who puts the garment on. History belongs to the garment ("ghost-stitching where patches used to live"), not the person.

**A disguise garment must not betray itself (2026-08-29).** A wig covers `hair` in order to change apparent identity, so its worn description has to read as *hair* — not as a wig. Anything that tells the reader the hair is artificial ("sits too evenly to have grown there", "moves as one piece") defeats the mechanic the item exists for, because that string is what every observer sees. The same holds for contacts, masks and anything else on the disguise line: describe what it is meant to be taken FOR, never what it actually is. This is the disguise-layer counterpart to the no-wearer-history rule: a worn_desc is seen by everyone, so it must not smuggle in knowledge the observer has not earned.

### Colour

A garment has one `color` attribute. `Item._process_color_codes` (`typeclasses/items.py`) replaces a `{color}` token in the current worn description (the active `desc_mod`, or `worn_desc`) with that colour's ANSI code from `COLOR_DEFINITIONS`. It runs before pronoun tokens are resolved.

| name | code | name | code |
|---|---|---|---|
| black | `\|=l` (256-colour dark grey) | bright_black | `\|K` |
| red | `\|r` | bright_red | `\|R` |
| green | `\|g` | bright_green | `\|G` |
| yellow | `\|y` | bright_yellow | `\|Y` |
| blue | `\|b` | bright_blue | `\|B` |
| magenta | `\|m` | bright_magenta | `\|M` |
| cyan | `\|c` | bright_cyan | `\|C` |
| white | `\|w` | bright_white | `\|W` |

Example: `"Wildly vibrant rainbow socks that shimmer with {color}prismatic brilliance|n across {their} feet"` with `color` `bright_magenta`.

A colour name not in `COLOR_DEFINITIONS` turns the `{color}` token into nothing, so the word shows in the default colour. Most colour names the prototypes use (grey, charcoal, brown, amber, olive and others) are not in the table.

## Layers

Layers run 0 to 5; higher is further out. `layer` is a property: a stored `layer` attribute wins; otherwise `world.style.derive_rung` picks it from the garment's name, using `RUNGS` in `world/style.py` (the rungs are also listed as CLOTHING LAYERS in `world/combat/constants.py`):

- **Layer 0**: underwear, undershirts, socks, stockings, tights
- **Layer 1**: shirts, trousers, skirts, dresses, wigs, watches, scrubs; also any garment whose name matches nothing
- **Layer 2**: vests, hoodies, sweaters, coveralls, masks, balaclavas, respirators, glasses
- **Layer 3**: jackets, blazers, harnesses, hoods, slickers
- **Layer 4**: coats, robes, ponchos, aprons, cloaks
- **Layer 5**: footwear, hats, caps, helmets, gloves, belts, ties, scarves, goggles

Wear-time rules (`ClothingMixin.wear_item`, `remove_item`, `blocking_garments`):

- Two garments on the same layer at the same location cannot both be worn.
- A garment cannot go on under one already worn on a higher layer at a shared location (no shirt over a jacket).
- A higher layer blocks removal of what is under it.
- A conflict is refused, naming the garments in the way. It is never resolved for the player; nothing is removed for you.
- The only limit at a location is one garment per layer.

`blocking_garments(item)` returns the worn garments that would stop `item` going on (an empty list means it fits); `wear_item` enforces the same rule, and souls consult it before choosing. `can_wear_now(item)` says whether the item would go on over what is already worn.

`get_worn_items(location=None)` returns worn garments, optionally at one location; `is_location_covered(location)` and `get_coverage_description(location)` answer for one location (`ClothingMixin`).

## Worn storage

The character keeps `worn_items` (`category="clothing"`): a dict from location to the garments there, ordered by layer, outermost first.

```python
{
    "chest": [jacket_obj, shirt_obj],
    "head": [hat_obj],
    "left_hand": [glove_obj],
    "right_hand": [glove_obj],
}
```

A style change re-seats the garment: `Item.set_style_property` sets the state and, if the item is worn, calls the wearer's `refresh_worn_coverage` (`typeclasses/clothing_mixin.py`), which lifts the item out of `worn_items` everywhere and re-inserts it by `layer` at its new coverage. That is what lets the layer beneath surface the moment a sleeve rolls (#2398). Because it is done in `set_style_property`, every caller (commands, souls, the LLM style tool) gets it.

## Appearance

### Visibility

1. Take the worn garments, outermost first at each location.
2. Build a coverage map: each location goes to the outermost garment at it, at that garment's current coverage. **Outermost wins the location.**
3. For each body location, in anatomical display order:
   - covered: add the outermost garment's current worn description. Each garment's description appears once, at the first location it shows on in display order;
   - not covered: add the character's longdesc for that location, if set. A left/right pair collapses into one line only when neither side is covered.
4. Format the result with the longdesc paragraph system (`_format_longdescs_with_paragraphs()`): the same anatomical-region paragraph breaks and the same 400-character threshold rules as pure longdescs.

So inner layers show wherever the outer layer leaves a location uncovered, and nothing under the outermost garment at a location shows there.

`AppearanceMixin._get_visible_body_descriptions` builds this for a living character; `return_appearance()` combines it with the rest of the appearance. Longdescs on uncovered locations go through the same brace-token processing.

Example (jacket covering chest, back, abdomen; hat covering head):

```
Sterling Hobbs(#216)
A breathing body without an identity. Its eyes flicker, but it does not move.

He wears a weathered tricorn hat tilted at a rakish angle. His face shows weathered features with high cheekbones.

He wears a worn leather jacket with brass buckles across his torso.
```

Without the jacket, the chest longdesc ("His chest displays broad shoulders tapering to a narrow waist.") shows in its place.

### One builder, three wearers

These rules belong to the *body*, not to the living character. Owner ruling, 2026-09-16 (#3578): a severed part must display garments *"just like it does on a character, mixing the worn descs and longdesc where appropriate."* Three renderers honour hidden longdescs, worn descriptions and partial coverage: `AppearanceMixin._get_visible_body_descriptions` (living), `Corpse._get_preserved_longdesc_descriptions`, and `Appendage.return_appearance` (severed limbs and heads).

"Outermost wins the location" is the rule everywhere; the data shape decides how it is read. All three read the first entry at each location through the module-level **`coverage_from_worn_stack(worn_items)`** in `typeclasses/clothing_mixin.py` (#3577):

- A **living character** carries a worn stack `{location: [garments, outermost first]}` — its `worn_items`. `ClothingMixin._build_clothing_coverage_map` delegates to `coverage_from_worn_stack`.
- A **severed part** carries the same shape: a self-healing `worn_items` ledger, which `detach_items_to_appendage` copies in that order and `undress`/`dress` maintain. `Appendage.return_appearance` heals the ledger with `worn_garments()` and then reads it.
- A **corpse** keeps **no stack**, only the flat `worn_garments()` list (contents filtered by `worn_at_death`), so `Corpse.worn_stack()` derives one: the layer orders each location, highest outermost, and each garment sits at its **current** coverage (`get_current_coverage()`, so a rolled cap does not cover the ears it is rolled off).

### A garment on a dead body

- It renders its `worn_desc` **once**, in place of the covered location's longdesc, and everything under it — authored prose *and* preserved wounds — is hidden.
- Neither a corpse nor a severed part lists what it is WEARING as contents. A part still lists what it merely carries — retracted hardware, a thing put in a severed hand — through Evennia's own `You see:` line, since that line is the only way such contents are found: `Appendage.filter_visible` drops worn garments from it, nothing else. There is no "It still wears …" sentence on a severed part.
- What gets hidden is exactly the garment **prototype's `coverage` list** and nothing more — `MINING_HELMET` declares `["head"]`, so a severed head wearing one still shows its `hair` line. This is the same binary, location-shaped limit described in §Coverage is binary.
- A carried longdesc prints verbatim, so prose authored for a living body ("He holds his head slightly forward") reads the same way on a detached one.

## Commands

### Naming a garment (#3783)

Every clothing verb names its garment through the one core matcher, `Character.search`, scoped to the verb's own pool with `candidates=`. No verb compares typed text to keys itself.

| verb | pool |
|---|---|
| `wear` | the caller's contents (held items included) |
| `remove` / `unwear`, `rollup` / `unroll`, `zip` / `unzip` / `button` / `unbutton` | the caller's worn items |
| `undress <target> <item>` | `target.worn_garments()` (a character, a corpse, a severed part) |

- A garment answers to its key or any alias, exact first, then a partial name in which each typed word starts a word of the key or an alias (`coat` finds `Vantage all-weather greatcoat` by its alias; `remove leather boots` finds `black leather combat boots`). A fragment from inside a word (`irt` for `shirt`) finds nothing.
- An ordinal picks among twins: `remove 2nd shirt`, `zip up second jacket`, `undress corpse jacket-2`. `undress` takes only the dash form, because it splits the target from the item at the last space.
- The pool is the worn list itself, so an ordinal counts worn garments only. A worn garment with no sleeves or no closure is still matched, and gets its own refusal (`The X doesn't have anything to roll up.`).
- Several matches without an ordinal take the first the matcher returns.
- The presence gate applies: a garment the caller cannot perceive is not found.
- Refusals: `You don't have 'X'.`, `You're not wearing 'X'.`, `<target> isn't wearing 'X'.`

### For every clothing verb

- All clothing verbs are refused while you are channelling.
- Removing armour with a stuck grenade warns you and the room, and the grenade stays on the armour.
- A single-use garment (issue clothing) tears apart as it comes off and is gone.

### `wear <item>`

Wears a garment from your inventory. Examples: `wear jacket`, `wear leather boots`, `wear 2nd shirt`.

1. Find the item in your contents (held items included).
2. Refuse if it lacks `coverage` or `worn_desc`, or is already worn. There is no anatomy check.
3. Check layers against what is worn: refuse if a worn garment at a shared location is on the same layer, or on a higher one (the new item would go under it).
4. On a conflict, refuse, naming the garments in the way. Nothing is removed for you.
5. Wear the item and update `worn_items`. A garment held in a hand leaves the hand only now, once the wear is going ahead.
6. Feedback: "You put on a <item>." to the wearer, and a matching line to the room.

### `remove <item>` / `unwear <item>`

Takes off a worn garment. Examples: `remove jacket`, `unwear boots`, `remove all`.

1. Find the worn item by name among the garments worn (or `remove all`).
2. Warn if a grenade is stuck to the garment; it stays stuck to it.
3. Refuse if a higher-layer garment over a shared location is still on ("Remove the <item> first.").
4. Update `worn_items`. The item never left the inventory, so nothing moves.
5. Run the garment's `at_removed` hook: single-use issue clothing tears apart and is deleted, and the wearer gets the tear message instead of "You remove...".
6. Feedback: "You remove a <item>." to the wearer, and a matching line to the room.

A worn item cannot be dropped; it must be removed first.

### `dress <target> in <item>` / `undress <target> [<item>]`

Puts a garment from your inventory on someone or something, or takes one garment or all of them off into your inventory. Syntax: `dress <target> in <item>`, `undress <target>`, `undress <target> <item>`.

- Works freely on a target who is unconscious, dead or restrained, and on a severed part. A conscious, free target must have trusted you for the `dress` class (see TRUST_AND_CONSENT_SPEC).
- Corpses and severed parts can be dressed and undressed.
- `CmdDress` and `CmdUndress` in `commands/CmdClothing.py` are player verbs (`locks = "cmd:all()"`). There is no staff-only clothing verb.

Examples: `dress corpse in jacket`, `undress corpse`, `undress corpse jacket-2`.

### Style commands

- `rollup <item>` / `unroll <item>` → the `adjustable` property: roll or unroll sleeves, loosen or straighten a tie, raise or lower a hood (also cuffs, pant legs). `rollup` goes to the first of `rolled`, `loosened`, `hood_up` that the garment declares; `unroll` goes to `normal`, or else `hood_down`.
- `zip <item>` / `unzip <item>` / `button <item>` / `unbutton <item>` → the `closure` property: close or open a worn garment's closure, zipped or buttoned, whichever it declares (also laces and the like). Closing goes to `zipped` or `buttoned`, opening to `unzipped` or `open`; the button verbs try `buttoned` / `open` first.

Examples: `rollup shirt`, `unroll shirt`, `rollup 2nd jacket`, `zip jacket`, `unzip boots`, `zip up coat`.

Each command is fixed to one property; the target state is read from the garment's own `style_configs`, never named by the command (#2742). In order (`CmdRollUp.func`, `CmdZip.func` in `commands/CmdClothing.py`):

1. Find the worn item by name.
2. Take the property from the command.
3. Refuse if the garment declares no entry for that property.
4. Ask the garment for the target state: `_target_style_state()` walks the command's intent list — `_ADJUST_TO`, `_RESTORE_TO`, `_CLOSE_TO`, `_OPEN_TO` — and takes the first state the garment's `style_configs` declares; `button`/`unbutton` reverse their list so the buttoned pair is preferred. Refuse if none is declared.
5. Refuse if that state is already current. This is the only sense in which a change with no effect is prevented; nothing tests whether a change is meaningful.
6. Apply the change (`Item.set_style_property`), which re-seats the garment's coverage by layer (§Worn storage). No layer check happens here.
7. Feedback: a paired self-message and `msg_room_identity` broadcast, whose observer names are snapshotted BEFORE the change, because restyling can move the wearer's sdesc. The prose comes from the STATE, not the command (`_STYLE_PROSE`).

`Item.can_style_property_to()` checks membership only — any state the garment declares is allowed. Its comment says why: *"Always allow transitions to valid states - the validation is structural, not functional."* A state's `coverage_mod` and `desc_mod` may each be empty. The `"That wouldn't change anything about the ..."` refusal in both commands is unreachable, because its target state was read out of `style_configs` just before.

What the player reads:

```
> rollup jacket
You roll up the leather jacket.

> zip jacket
You zip up the leather jacket.

> unzip jacket
You unzip the leather jacket.

> unroll jacket
You unroll the leather jacket.

> rollup shirt
The shirt doesn't have anything to roll up.

> zip shirt
The shirt doesn't have a zipper.
```

Refusals:

| case | message |
|---|---|
| `rollup`, no adjustable feature | `The <item> doesn't have anything to roll up.` |
| `unroll`, no adjustable feature | `The <item> doesn't have anything to unroll.` |
| `zip` / `unzip`, no closure | `The <item> doesn't have a zipper.` |
| `button` / `unbutton`, no closure | `The <item> doesn't have buttons.` |
| property declared, but none of the states the verb can reach | `There's no way to <roll up\|unroll\|close\|open> the <item>.` |
| state already current | `The <item> is already <state>.` — the state reading `rolled up`, `zipped up`, `unbuttoned`, `hood down` and so on; `unroll` on a garment that is not rolled says `already straight` |

The refusals are phrased from the command, not from sleeves, because `rollup` also reaches hoods and neckties (#2742).

**Style changes and layers.** A style change never consults layering and never refuses on it; layer conflict detection is a **wear**-time rule only (`clothing_mixin.wear_item`, `clothing_mixin.blocking_garments`). This is a gap, not a ruling: a state whose `coverage_mod` ADDS a location can seat a garment where `wear_item` would have refused it. `hood_up` on the tox-sealed slicker adds `+head` at layer 3, the same layer as `HOODIE_HOOD_UP`, and the developer hoodie's `rolled` adds `+head` at layer 2, the same layer as `BALACLAVA`. Whether a style change should refuse is in §Not decided.

**Overturned intention: meaningful-transition validation.** The design once required every style state to carry both a `coverage_mod` and a `desc_mod`, so that no command would be a no-op. It was never built and must not be (2026-09-11, #2445 item 8): of the 60 style states declared in `world/prototypes.py`, 35 leave `coverage_mod` and/or `desc_mod` empty, and all 24 prototypes that declare `style_configs` carry at least one — including every one of the 12 restore-to-`normal` states (`WORK_COVERALLS`), the dust poncho's `unzipped`, which is also its default state (`DUST_PONCHO`), the slicker's `hood_down` (`SEALED_SLICKER`), and the thermal's `rolled` (`THERMAL_SHIRT`). Under that rule nothing could ever be unrolled, unsnapped, lowered or straightened again. What governs instead: a style state must be **declared by the garment** to be reachable, the commands read the garment rather than naming states (#2742), and they refuse a change to the state a garment is already in. The impulse behind the old rule (no command should be a no-op) still governs the authoring guidance; it is simply not enforced as a both-populated rule.

## Inventory

`inventory` lists worn items under a **Wearing:** heading, then **Carrying:** and **Held:**.

```
> inventory
Wearing:
  black leather jacket (rolled up)
  weathered tricorn hat

Carrying:
  steel dagger
  copper coins
  leather pouch

Held:
Nothing is in your left hand.
Nothing is in your right hand.
```

Style state in brackets (`CmdInventory._get_style_state_display` in `commands/CmdInventory.py`):

- For each style property, the default is the first state the garment declares with both `coverage_mod` and `desc_mod` empty. A worn garment with no bracket shows no off-default state.
- Only two off-default states are named: `rolled up` (adjustable) and `unzipped` (closure), e.g. `blue jeans (rolled up)`.
- Other states (buttoned, open, loosened, hood up, zipped) are never shown.
- A property that has no state with both fields empty never shows in the bracket.

## Combat

- Clothing can provide damage reduction (armour).
- Covering a location does not make it harder to hit. Armour does change aim: an attacker with Intellect 3 or more is less likely to aim at a vital location carrying armour rating 4 or more, and more likely to aim at an unarmoured vital one (`select_hit_location` in `world/medical/utils.py`).
- Combat messages reflect what is visible versus covered.

## Coverage is binary, and two real garments need it not to be

📋 PROPOSAL — the gap is real and demonstrated, the design is not decided.

A location is either covered by a garment or it is not. `coverage_mod` can add or remove a location per style state, but there is no third setting, and two things in the game already need one:

* **Sheer.** `MESH_TOP` is described as a weave "open enough to read as shadow rather than fabric" while its coverage is the entire torso and both arms — so it conceals the body completely. The prose promises sheer and the model delivers opaque. Cutting its coverage to compensate is worse: it would stop registering as clothing on those locations at all, so layering, armour and removal-blocking would all mis-handle it.
* **Partial.** A hat sits ON the head and hair shows under the brim. The existing convention splits headwear into garments that ENVELOP (balaclava, ski mask, hood, wigs — these cover `hair`) and garments that SIT ON (helmets, caps, wide-brim hats — these do not), which is a reasonable approximation, but `HEAD_WRAP` is genuinely mis-grouped and cannot be fixed by moving it between two groups when the truth is "mostly covered".

Both want the same missing idea: **a garment can cover a location without concealing it.**

Sketch, not a decision — the cheapest shape is likely a per-garment `sheer` flag (or a per-location set) consulted where the coverage map is built (`coverage_from_worn_stack`, shared by living bodies, corpses and severed parts): a sheer garment still registers for layering, armour and removal rules, but the appearance layer renders the body longdesc underneath *as well as* the garment rather than instead of it. That keeps the mechanical meaning of coverage intact and changes only what is shown. The questions to settle before anyone builds it are in §Not decided.

## Design aims

- Players wear and remove clothing without friction; clothing descriptions appear in the character's appearance, and covered longdescs are hidden.
- An intuitive command interface following established patterns; clear feedback on wear, remove and conflicts; layering that matches real-world expectations.
- The clothing system works with the longdesc system; mixed clothing and longdescs assemble correctly; performance impact stays minimal; existing character behaviour is preserved.
- Staff management of clothing on other characters: see the staff commands under §Unbuilt.

## Unbuilt

- **Staff commands** 📋 UNBUILT (not decided). No staff clothing command exists; `dress` and `undress` are the player verbs. The sketch, following the longdesc pattern:
  ```
  @wear <character> <item>     - Force wear item on character
  @remove <character> <item>   - Force remove item from character
  ```
- **Anatomy checking** 📋 UNBUILT (not decided): wear does not check that the wearer has the locations the item covers.
- **Slot limits** 📋 UNBUILT (not decided): there is no per-location item count; the only limit is one garment per layer per location.
- 📋 UNBUILT (no issue): comprehensive error handling and user feedback; performance optimization.
- 📋 UNBUILT (no issue): update existing clothing prototypes with the enhanced features; validate the `material` attribute for future armour/crafting use.
- 📋 UNBUILT (no issue), testing: pronoun perspective with different character genders; `{color}` replacement; colour and pronouns together; performance with complex styled and coloured clothing.
- Future expansion, 📋 UNBUILT (no issue):
  - **Custom tailoring**: a `tailor` command for fitting clothes to unique anatomies
  - **Clothing conditions**: wear states (pristine, worn, tattered, destroyed)
  - **Seasonal clothing**: weather-appropriate clothing bonuses/penalties
  - **Cultural clothing**: faction or region-specific clothing styles
  - **Magical clothing**: enchantments and special properties
  - **Equipment sets**: bonus effects for wearing complete outfits
  - **Ceremonial gear**: special-occasion clothing with social bonuses
  - **Tailoring profession**: player-crafted clothing
  - **Clothing shops**: NPC vendors with seasonal inventories
  - **Repair system**: clothing maintenance and restoration
  - **Fashion system**: social status and appearance ratings
  - **Crafting**: `material` is kept for future armour/crafting systems

## Not decided

- **Style change on a layer conflict.** Should a style change whose `coverage_mod` adds a location refuse on a layer conflict, as `wear` does, or keep re-seating silently? Today it re-seats (§Style commands).
- **Sheer / partial coverage** (§Coverage is binary): whether sheer is a property of the garment or of a style state (a coat can be open without being sheer); whether armour and combat targeting should see through it at all; and how two sheer layers stack.

## Related documents

- `GRAMMAR_ENGINE_SPEC.md` — the `{their}`/`{they}` brace tokens
- `IDENTITY_RECOGNITION_SPEC.md` §Disguise Items — disguise attributes on `Item`
- `TRUST_AND_CONSENT_SPEC.md` — the `dress` trust class
- Longdesc system — body locations and paragraph formatting this system builds on
