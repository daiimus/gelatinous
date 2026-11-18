# Long Description System Specification

## Overview

The Long Description (longdesc) system lets players set detailed descriptions for specific body parts/locations on their characters. These descriptions appear when other players look at the character, building a rich, personalized appearance. The `describe` command sets them; `return_appearance` in `typeclasses/appearance_mixin.py` assembles them, with clothing, wounds and chrome, when someone looks.

## Core Principles

1. **Player Agency**: Players control their character's appearance descriptions.
2. **Staff Override**: Staff can set longdescs on any character for content moderation.
3. **Layered Architecture**: The system is designed to integrate with clothing, equipment and injury systems.
4. **Visibility Control**: Only visible body parts show descriptions.
5. **Future-Proof**: The foundation for clothing coverage, injuries, cybernetics, tattoos.

## Permission System

### Player Access
- **Self-modification only**: Players can only set longdescs on their own characters.
- **Public visibility**: Longdescs are visible to all players via `look`.
- **No consent system**: Players are responsible for their own descriptions.
- **Optional participation**: Players are not required to set longdescs.

### Staff Override
- **Permission-based access**: Staff with Builder+ permissions can target other characters.
- **Same command interface**: Staff use the standard commands with a character target.
- **Content moderation**: Staff can modify any character's longdescs.
- **Hierarchical permissions**: The check is Evennia's lock system, `caller.locks.check_lockstring()` with `perm(Builder) or perm_above(Builder)`, so Developers and Admins are included through `perm_above()`.
- **Graceful fallback**: Non-staff users get the standard self-targeting behaviour.

## Body Location System

### Locations

Body locations are declared per species in `world/anatomy/species.py` (`SPECIES_DEFINITIONS[<species>]`: `default_longdesc_locations`, `anatomical_display_order`, `anatomical_regions`, `pair_keys`, `longdesc_flex_nouns`) and read through the `get_species_*` helpers there (`get_species_default_longdesc_locations` and the rest). `world/combat/constants.py` keeps human-only copies derived from the human entry (`DEFAULT_LONGDESC_LOCATIONS`, `ANATOMICAL_DISPLAY_ORDER`, `ANATOMICAL_REGIONS`, `PAIR_MERGE_KEYS`, `LONGDESC_FLEX_NOUNS`) for callers with no species, plus the limits below.

The human default anatomy is 22 locations, created on every new human character, in this order. Head-region order mirrors organic recognition: hair, then eyes, then the head and face resolve into view, followed by ears and neck.

| location | covers |
|---|---|
| `hair` | |
| `left_eye` / `right_eye` | individual eyes, for asymmetry |
| `head` | overall head/skull area |
| `face` | facial features and expressions |
| `left_ear` / `right_ear` | ear shape, piercings, modifications |
| `neck` | neck area, throat |
| `chest` | chest/torso front |
| `back` | back and shoulder blades |
| `abdomen` | stomach/belly area |
| `groin` | lower torso/hip area |
| `left_arm` / `right_arm` | individual arms |
| `left_hand` / `right_hand` | hands, fingers, nails |
| `left_thigh` / `right_thigh` | upper legs |
| `left_shin` / `right_shin` | lower legs/calves |
| `left_foot` / `right_foot` | feet, toes, stance |

Each species declares its own set; a rat declares 21 locations and shares only 10 with a human. Synthetics and robots derive from human and share all 22.

Locations are named constants (like the Mr. Hands system) so references stay consistent across the codebase, validation is simple, non-standard anatomies are supported, defaults are auto-created, configuration is centralized, and the anatomy is the source of truth for every body-related system. Practical limits are high; in principle the number of locations is unlimited.

### Limits (`world/combat/constants.py`)

| constant | value | meaning |
|---|---|---|
| `MAX_DESCRIPTION_LENGTH` | 1000 | characters per location description |
| `PARAGRAPH_BREAK_THRESHOLD` | 400 | characters before an automatic paragraph break |
| `REGION_BREAK_PRIORITY` | `True` | prefer breaking between anatomical regions |
| `MAX_LONGDESC_LOCATIONS` | 50 | practical limit on total locations per character; nothing enforces it (see Unbuilt) |
| `VALID_LONGDESC_LOCATIONS` | the keys of `DEFAULT_LONGDESC_LOCATIONS` | human validation set |

### Extended anatomy

The system supports appendages beyond standard human anatomy, following this naming convention:

- **Additional arms**: `left_arm_2`, `right_arm_2`, `left_hand_2`, `right_hand_2`
- **Prehensile tails**: `tail`, `tail_2` (for multiple tails)
- **Extra legs**: `left_leg_3`, `right_leg_3`, `left_foot_3`, `right_foot_3`
- **Wings**: `left_wing`, `right_wing`
- **Tentacles**: `tentacle_1`, `tentacle_2`, etc.
- **Other**: any anatomically relevant appendage following the convention.

### Anatomy validation

A location is settable only if it is a key in the character's own `longdesc` dict (`has_location`), or a pair shorthand of its species. This works for any anatomy (alien, cybernetic, etc.) and prevents describing a body part the character does not have.

### Schema drift and backfill (IMPORTANT)

A character's `longdesc` dict is written **once**, at `at_object_creation`, as the species' default map from `get_species_default_longdesc_locations(species)` (human when species is unset). There is no automatic migration: adding (or reordering) a location in a species' default locations does **not** reach already-existing characters. Their stored dict keeps the key set (and order) it had at creation.

For a body that predates a new default location:
- The location is absent from `get_available_locations()`, so it never appears in `describe/list`.
- `has_location()` returns `False` for it, so `describe <new_location> "..."` is rejected: the player cannot describe a body part they anatomically have.
- `describe/list` groups by region in **dict-insertion order**, so a key added out of canonical position also displays out of anatomical order.

**Whenever a species' default locations gain an entry (or the order changes), run a one-off backfill** to bring existing bodies into sync. The backfill rebuilds each dict in that species' canonical order, preserves any set descriptions, and keeps extended anatomy (tails, wings, cybernetics) at the end. It is idempotent (a second pass updates nothing) and never overwrites set values. Because it reorders each dict into canonical order, it also fixes `describe/list` showing a backfilled key (e.g. `hair`) out of position.

**The backfill must be species-aware.** `DEFAULT_LONGDESC_LOCATIONS` is **human-only**: `world/combat/constants.py` derives it from `SPECIES_DEFINITIONS["human"]` and points callers at `get_species_default_longdesc_locations(species)` for anything else. Rebuilding every body against it injects human anatomy into rats: a rat would gain 12 keys it has no body for (`face`, `hair`, `left_arm`, `left_hand`, `left_thigh` and the rest), making `has_location("left_hand")` true on a rat (#2445).

```python
# Run via `evennia shell`, then `evennia reload` to flush the server's
# in-memory object cache so post-reload reads come fresh from the DB.
from typeclasses.characters import Character
from world.anatomy import get_species_default_longdesc_locations

updated = 0
for c in Character.objects.all_family():
    # PER SPECIES -- never the human-only DEFAULT_LONGDESC_LOCATIONS.
    D = get_species_default_longdesc_locations(getattr(c.db, "species", None)) or {}
    if not D:
        continue                           # never taken: unknown/None species resolve to human
    cur = c.longdesc or {}
    rebuilt = {k: cur.get(k) for k in D}   # canonical order + backfill missing as None
    for k, v in cur.items():               # preserve extended anatomy
        if k not in rebuilt:
            rebuilt[k] = v
    if rebuilt != cur:
        c.longdesc = rebuilt
        updated += 1
print(f"Updated {updated} characters")
```

Unknown or missing species resolve to human, so check the `species` values on the bodies before running this: a body whose species is not a registered key gets human anatomy.

## Command Interface

### `describe`

`describe` (`commands/CmdCharacter.py::CmdDescribe`, `key="describe"`, **no aliases**, registered in `CharacterCmdSet` in `commands/default_cmdsets.py`) covers what `@longdesc`, `@shortdesc` and Evennia's default `setdesc` did (#276). It owns five facets of a character's appearance:

- **Short Description**: the main paragraph (`db.desc`).
- **Keyword**: the sdesc noun (`sdesc_keyword`).
- **Look Place**: `look_place`, how the character appears in a room by default ("standing here.").
- **Temp Place**: `temp_place`, a placement that overrides the look place and is cleared when the character leaves the room.
- **Body locations**: per-part longdesc text (the subject of this spec).

`describe` is **not** aliased to `desc`, to avoid colliding with Evennia's builder `@desc` (see Not decided).

**Syntax**: `describe <location> "<description>"`

**Examples**:
```
describe face "High cheekbones and a defined jawline lend {their} face a rough calm."
describe left_eye "A piercing blue eye glints with flecks of gold."
describe right_eye "A cybernetic replacement glows with a steady red LED."
describe left_hand "A calloused hand carries dirt under the fingernails."
describe right_hand "A prosthetic metal hand ends in intricately engraved fingers."
describe chest "Broad shoulders taper to a narrow waist."
describe tail "A long, serpentine tail ends in a barbed tip."
describe left_wing "A massive feathered wing spreads in midnight black."
```

### Command behaviour
- **Validation**: The location must be a key in the character's own `longdesc` (`has_location`), or a pair shorthand of its species. The description may be at most 1000 characters. Surrounding whitespace is stripped.
- **Storage**: The description is stored on the character.
- **Replacement**: A new description overwrites the existing one for that location.
- **Removal**: An empty description removes the longdesc for the location.
- **Feedback**: The player is told the setting or removal succeeded.
- **Self-targeting**: Players can only modify their own longdescs by default.
- **Staff override**: Staff with Builder+ permissions can target other characters.

### Command variations
- `describe` - Open the interactive editor menu (self only).
- `describe short <description>` - Set the short description (`db.desc`).
- `describe keyword <word>` - Set the sdesc keyword (`sdesc_keyword`).
- `describe lookplace <text>` - Set the look place; `clear` resets it to "standing here."; no text shows the current value.
- `describe tempplace <text>` - Set the temp place; `clear` empties it; no text shows the current value.
- `describe <location> "<description>"` - Set one body location.
- `describe <location>` - View the current description for a location.
- `describe/list` - List all available body locations for this character, grouped by anatomical region.
- `describe/clear <location>` - Remove the description for a location (set to None).
- `describe/clear` - Clear every body-location description at once (no confirmation prompt).

The `keyword`, `short`, `lookplace` and `tempplace` sub-words (`look_place` and `temp_place` also work) are reserved one-off forms that always operate on the caller. They are claimed before staff target resolution because they are neither valid body locations nor plausible character names.

### Staff commands (permission override)
- `describe <character> <location> "<description>"` - Set a longdesc on another character.
- `describe <character>` - View all set longdescs on another character.
- `describe/clear <character> <location>` - Clear a specific location on another character.
- `describe/clear <character>` - Clear every body location on another character.

### Staff target search

Staff targeting uses `resolve_admin_target` (`commands/_identity_targeting.py`). It first looks in the caller's room for a character matching what the caller sees (sdesc or recognised name; a Builder can also match by key). If that finds nothing, it searches every Character in the game by key. If that global search finds more than one, the caller is told to be more specific (for example with a dbref) and nothing is targeted. `CmdDescribe` uses the result only if it has a `longdesc`; otherwise the command acts on the caller and reads the whole argument as a location.

### Interactive editor (EvMenu)

Bare `describe` (acting on self) opens an EvMenu editor instead of printing a static list. The list is **flat**: the Short Description, Keyword, Look Place and Temp Place sit above the anatomy slots, so a player edits every facet of their appearance from one place. The flow:

1. **List node** (`node_describe_list`): a one-per-line numbered list whose first four rows are fixed and the rest are dynamic body slots. Rows render as `N. Label :: value` with the label column aligned so the `::` separators line up. The menu is rendered all-white for readability: in this palette `|w` is bold white and `|W` is unbold white, so **only the row numbers and section headers are bold**; labels, values and placeholders are unbold white. Values are shown unquoted, and slot labels are capitalized for display (`left_eye` -> `Left Eye`, `eyes` -> `Eyes`) by `_describe_slot_label`; the internal slot strings are unchanged.
   - `1. Short Description :: …` — current `db.desc` (one-line preview, or `(empty)`).
   - `2. Keyword :: …` — current `sdesc_keyword`, or the gendered default marked `(default)`.
   - `3. Look Place :: …` and `4. Temp Place :: …` — current `look_place` (default `standing here.`) and `temp_place` (or `(none)`). Each opens an entry node (`node_lookplace_entry`, `node_tempplace_entry`) that takes new text, `clear` (the look place resets to `standing here.`, the temp place empties) or `back`/blank. It adds a full stop when the text has no end punctuation, and rejects text over 200 characters and re-prompts.
   - `5..N` — editable longdesc **slots**, built by `_build_longdesc_slots`:
     - Symmetric pairs collapse to their shorthand (`eyes`, `hands`, ...) so the dynamic anatomy reads as a clean, compact list.
     - An asymmetric pair (only one side present) shows that side individually.
     - Non-pair locations show as themselves; extended anatomy is appended after the anatomical-order entries.
     - A pair whose two sides currently diverge is flagged (editing it via the shorthand sets both sides alike).
   - `x. Exit` closes the menu cleanly.
2. **Short Description node** (`node_describe_short`): shows the current value and a live rendered preview (`_process_description_variables` with `force_third_person=True`), then accepts new prose. `clear` empties it; `back`/blank returns unchanged. No length cap is applied to the short description.
3. **Keyword node** (`node_describe_keyword`): a curated 3-column list of the keywords valid for the character's grammar gender, with the current keyword marked. Selection (by number or name) applies the keyword and **returns to the list** (stays in the menu). Custom keywords are set with the one-off `describe keyword <word>` command.
4. **Entry node** (`node_longdesc_entry`): shows the slot's current value and a token hint, then accepts the new description. `clear` removes it, `back`/blank returns unchanged, over-length input is rejected and re-prompts.
5. On save the longdesc fans out to both sides of a pair (or the single location) and a **rendered preview** is shown.

The one-off `describe <location> "<description>"` form shares the same preview output.

### Rendered preview

`_render_longdesc_preview` shows how a freshly set description will read. For a symmetric pair it renders both the **plural** form (both sides intact) and the **singular** form (a lone survivor); for a single location it renders the singular form. Any brace token the resolver does not recognise survives in the rendered output and is surfaced as an explicit warning, so typos like `{thier}` are caught at authoring time rather than shipped silently. The preview fires after both the interactive editor save and the one-off `describe <location> "..."` command. The preview recognises only the human pair shorthands (`PAIR_MERGE_KEYS`), so a rat's `forelegs` gets only the singular line, and its lone-side line has no side word ("eye", not "left eye"), unlike the real render.

## Look: character appearance

When a player looks at a character, `return_appearance` (`typeclasses/appearance_mixin.py`) builds these sections, separated by blank lines:

1. **Name and base description**: the name, and the main description (`db.desc`) on the next line, with no blank line between.
2. **Longdescs and clothing**: the visible body and clothing descriptions in head-to-toe anatomical order, split into paragraphs (`get_longdesc_appearance`, `_get_visible_body_descriptions`, `_format_longdescs_with_paragraphs`).
3. **Held items**: a natural-language list of what the character holds, via the hands system.
4. **Staff administrative info**: a full inventory, for Builder+ only.

If a character's `longdesc` is None when looked at, `return_appearance` reseeds it with the species' default locations.

Format:
```
CharacterName
Base character description appears here immediately after the name with no blank line between.

First paragraph of longdesc and clothing descriptions, automatically formatted based on anatomical regions and character thresholds for natural reading flow.

Second paragraph continues with additional body descriptions and worn items, maintaining smart paragraph breaks between anatomical regions when appropriate.

CharacterName is holding a weapon and a item.

With your administrative visibility, you see: item1 [#123], item2 [#456], weapon [#789], clothing [#012]
```

Example:
```
CharacterName
A weathered detective with years of experience etched into every line.

A piercing blue eye glints with flecks of gold. A cybernetic replacement glows with a steady red LED. High cheekbones and a defined jawline lend her face a rough calm. Broad shoulders taper to a narrow waist. A calloused hand carries dirt under the fingernails. A prosthetic metal hand ends in intricately engraved fingers.

CharacterName is holding nothing.
```

### Template variables and pronouns
- **Case sensitivity**: Both `{They}`/`{their}` and `{they}`/`{their}` work.
- **Third-person consistency**: All descriptions use third person regardless of viewer, so there are no constructions like "You carries himself".
- **Pronouns**: Pronoun tokens follow the character's *apparent* gender (`world.identity.get_apparent_gender`): a disguise keyword sets it, and without one it is the real grammar gender. Male and female render he/she; everything else renders singular they (#2462).
- Brace tokens (`{their}`, `{they}`, `{name}`) are resolved by `_process_description_variables`. FuncParser `$pron()` is not used (#3442/#3447).

### Held items
- **Hands system**: Reads the derived `hands` property (species-aware grasping slots backed by `held_items`; #460).
- **Natural language**: "drek is holding a light pistol"; several items read "holding a knife, a pistol, and a grenade". The renderer writes "a" before every item name, whatever its first letter.
- **Empty hands**: "drek is holding nothing", for transparency, so a character's weapon state is visible at once.
- **Integrated cyber weapon**: A deployed integrated cyber weapon is not listed as held. It renders on its own line as the limb it has become ("<Name>'s shotgun module is their right hand.", `_format_integrated_weapon_line`) and suppresses "is holding nothing".
- **Natural weapon**: A natural weapon (claws) never appears here and does not suppress "is holding nothing".

### Staff view
- Staff read "With your administrative visibility, you see:" followed by all the character's contents with dbrefs, for debugging.
- Shown only to Builder+, checked with `check_permstring("Builder")`.
- Held items appear in both the held line and this list; the redundancy is acceptable, for complete admin information.

### Display order (anatomical head-to-toe)
1. **Head region**: hair, left_eye, right_eye, head, face, left_ear, right_ear, neck
2. **Torso region**: chest, back, abdomen
3. **Arm region**: left_arm, right_arm, left_hand, right_hand
4. **Leg region**: groin, left_thigh, right_thigh, left_shin, right_shin, left_foot, right_foot
5. **Extended anatomy**: any other key in the character's `longdesc` (tail, wings, an installed augment), in the order it was added

This is the human order. Each species declares its own order and regions in `world/anatomy/species.py` (a rat has foreleg, hindleg and tail regions).

### Paragraph breaks
`_format_longdescs_with_paragraphs` (with `_get_anatomical_region`) splits the visible descriptions so verbose descriptions do not become a wall of text:
- **Character counting**: The system tracks the cumulative character count as it builds the description.
- **Within a region**: A new paragraph starts before any description that would push the paragraph past 400 characters.
- **At a region boundary**: A break happens only if the paragraph already has 280 or more characters (70% of the threshold), and the 400 check is skipped there. Breaks avoid falling inside a region when possible.
- **What counts**: Only visible descriptions (body longdescs and clothing longdescs) count toward the thresholds.
- **Writer freedom**: No forced connecting words or narrative structure; writers control their own style.
- **Authoring convention**: Locations within a region are joined with single spaces; the renderer adds no capitalization or punctuation. Author each location as a **complete sentence** (capitalized, period-terminated) so the joined output reads as prose; bare fragments run together into a run-on.
- **Constants**: `PARAGRAPH_BREAK_THRESHOLD` and `REGION_BREAK_PRIORITY` (`world/combat/constants.py`) and the species' `anatomical_regions` (`get_species_anatomical_regions`).

### Paired longdesc collapse
Symmetric left/right pairs collapse into a single line when their descriptions are interchangeable, avoiding repetition (a single `{Their} {eyes} {are} pale blue.` renders once as "Their eyes are pale blue." instead of "Their eye is pale blue." for each side).

**Pairs are derived dynamically** from `left_*` / `right_*` location keys (the union of `longdesc` keys, `coverage_map`, `ANATOMICAL_DISPLAY_ORDER`, and severed locations), so custom species anatomy (`left_wing` / `right_wing`, etc.) takes part automatically with no hardcoded list.

**Collapse eligibility**: a pair collapses only when **both** sides are uncovered AND **one** of:
- **Identical longdescs**: both sides hold the same non-empty longdesc string (literal equality, WYSIWYG, no normalization), OR
- **Both cleanly severed**: both sides are fully severed (every visible wound at the location has stage `severed`) and neither side has a longdesc.

When eligible, the pair renders as one line and the right-side entry is skipped. Asymmetric coverage (one side clothed), differing prose, or a single amputated limb all **fail** the identity test and render each side separately.

**Destroyed organs (#350)**: at a location where an organ is destroyed, the authored longdesc is not shown; the destruction wound is the only description there. Identical prose does not collapse if either side is destroyed. When both sides are destroyed by the same kind of injury and neither side is covered, they render as one plural destruction line (`_build_destroyed_pair_collapse`, `world.medical.wounds.get_paired_destroyed_description`).

**Both-severed stumps** render via `world.medical.wounds` `get_paired_severed_description` using the type-agnostic `PAIRED_SEVERED_DESCRIPTIONS` templates, with `{location}` filled as `both <plural>` (e.g. "both hands").

**Wounds do not gate collapse**: a wound on one side does not split the pair; the merged line renders once and per-side wound sentences append through the normal wound-layering path. Only a pair destroyed on both sides by the same injury collapses its wound lines (see Destroyed organs above); collapsing two identical ordinary per-side wound sentences into "both hands" is unbuilt (see Unbuilt).

**Verbatim collapse and number tokens** (the system never rewrites player prose): the identical string is rendered **once, at plural number**, through `_process_description_variables(..., number="plural")`. Words the author wrapped in `{braces}` are flexed to plural; everything else renders verbatim. A lone survivor or single side renders the same string at `number="singular"`. When a single side renders, a braced pair noun takes the side: `{eyes}` on `left_eye` reads "left eye", and `{an arm}` on `right_arm` reads "a right arm" (#341). Non-pair flex nouns (`leg`, `shoulder`, ...) take no side. A `{they <verb> ...}` token agrees the verb with the person, not the body part ("she walks", "they walk"). There is no heuristic noun substitution and no `None` fallback; any identical pair collapses.

Number tokens (see `GRAMMAR_ENGINE_SPEC.md` §Number-Flexing Tokens):
- **Noun**: a braced word whose singular is in the flex-noun vocabulary: the pair nouns (`eye`, `ear`, `arm`, `hand`, `thigh`, `shin`, `foot`; derived from the species' `pair_keys`) **plus** the species' curated `longdesc_flex_nouns` set (human: `leg`, `shoulder`, `hip`, `knee`, …; rat: `tail`, `snout`, `whisker`, …). `{eye}`/`{eyes}` flex the noun; `{an eye}` also drops the article on plural and re-agrees `a`/`an` on singular. `LONGDESC_FLEX_NOUNS` is **vocabulary only**: its words are not anatomy locations, not pairs, and not `describe` shorthands; extend it freely as players find gaps.
- **Verb**: any other braced single word, conjugated to agree with the part: plural `{accent}`/`{are}`, singular `{accents}`/`{is}`. Only brace verbs whose subject **is** the body part; a main-clause verb agreeing with the person-pronoun ("They have …") is left un-braced.
- **Unrecognised** tokens (multi-word non-noun, typos) are left **literal** and logged. Substitution is per token (`re.sub`), so a stray brace does not drop the rest of the substitution.

**Pair shorthand (authoring convenience)**: `describe <pair> "..."` (where `<pair>` is a key of the character's species `pair_keys`, from `get_species_pair_keys`: for humans `eyes`, `ears`, `arms`, `hands`, `thighs`, `shins`, `feet`; for rats `eyes`, `ears`, `forelegs`, `forepaws`, `hindlegs`, `hindpaws`) sets, views and clears **both** sides at once, guaranteeing the byte-for-byte identity collapse requires. The pair keys are write-conveniences only: not body locations, not wearable, not render keys. Set the sides individually to make them differ (e.g. heterochromia).

**Where it lives**: `_build_paired_longdesc_collapse`, `_merge_paired_location`, `_get_severed_locations`, `_substitute_longdesc_tokens` and `_flex_noun_vocabulary` in `typeclasses/appearance_mixin.py`, consulted by both passes of `_get_visible_body_descriptions`; pair shorthand fan-out in `_expand_longdesc_pair` (`commands/CmdCharacter.py`, used by `CmdDescribe`).

### Visibility rules
- **Default**: All body locations are visible unless covered by clothing.
- **Clothing coverage**: Worn items hide covered locations and display their own descriptions instead.
- **Unset locations**: A body part with no longdesc shows nothing unless it has a visible wound, which renders on its own. Organ containers the medical state knows but no longdesc names (a socket left after chrome was removed) are visited too, so their wounds show.
- **Template processing**: All visible descriptions are processed for third-person consistency.

**These rules hold on all three body kinds**: living character, `Corpse`, and `Appendage` / `SeveredHead` (#3578). Owner ruling, 2026-09-16 (#3578): a severed part must display garments *"just like it does on a character, mixing the worn descs and longdesc where appropriate."*

- The living character and the severed part read the same outermost-first worn stack through one builder, `coverage_from_worn_stack` (`typeclasses/clothing_mixin.py`). The corpse, which keeps no stack, derives one (`Corpse.worn_stack()`: layer orders each location, styled coverage places the garment) and reads it through the same builder (#3577).
- A covered location on a severed part renders the garment's `worn_desc` once, in place of the carried longdesc, and the preserved wounds at that location are hidden with it: the same "clothing hides what is under it" rule, applied to prose that was snapshotted at sever time.
- The part's worn garments leave Evennia's contents line (`Appendage.filter_visible`; what it merely carries is still listed), and it appends no "It still wears ..." sentence.
- Two limits hold on the corpse and severed-part paths: the garment **prototype's `coverage` list** is the whole of what gets hidden (a helmet declaring `["head"]` leaves the `hair` line visible), and a carried longdesc prints **verbatim**, so prose written for a living body ("He holds his head slightly forward") still reads that way on a detached one.

## Data Storage

`longdesc` is an AttributeProperty on the Character typeclass (`typeclasses/characters.py`), `AttributeProperty(None, category="appearance", autocreate=True)`, following the Mr. Hands AttributeProperty pattern. `at_object_creation` seeds it with `get_species_default_longdesc_locations(species)`; `return_appearance` reseeds it the same way if it is ever None.

- **Dictionary format**: location key -> description string or None, for easy lookup and modification. Extended anatomy keys sit after the defaults.
- **Auto-creation**: All default locations are created with None values on character creation.
- **None as unset**: Only locations with string values are "set" (None = invisible).
- **Persistence**: AttributeProperty handles database persistence.
- **Unicode**: Descriptions support the full character set.
- `Character.db.desc` (the short description) is separate and appears before the longdescs.

The appearance methods (`get_longdesc_appearance`, `_get_visible_body_descriptions`, `_format_longdescs_with_paragraphs`, `_get_anatomical_region`, `has_location`, `get_available_locations`, `set_longdesc`, `get_longdesc`, `return_appearance`) live in `AppearanceMixin` (`typeclasses/appearance_mixin.py`), mixed into Character.

**Performance**: Appearance is assembled in real time on every look, with no caching; Evennia's scale makes this efficient.

## Layers

Each layer is independent (modular design), with a uniform interface across systems.

### Base longdescs
Player-set descriptions stored on the character, displayed directly when the location is visible, set with `describe`.

### Clothing / equipment coverage
- Items define coverage areas: `coverage = ["chest", "left_arm", "right_arm"]`.
- **Coverage uses the same location constants** as the longdesc system.
- **Covered longdescs are hidden**: base body descriptions are not shown when covered.
- **Clothing longdescs are displayed**: clothing items have their own appearance descriptions.
- **Clothing descriptions count toward paragraph thresholds.**
- **Dynamic styling**: items support multiple wear states (rolled up, zipped, etc.).

### Injury / medical
- Wounds append to the location's longdesc (`append_wounds_to_longdesc`); a location with no longdesc still shows its wounds (`get_standalone_wound_description`); severed and destroyed parts render as described under Paired longdesc collapse.
- Temporary modifications (bandages, casts).
- Permanent modifications (scars, prosthetics).
- Medical condition visibility: a body's dominant symptom (cyanosis, pallor, ...) tints every body longdesc in place of the skintone (`world.medical.appearance.get_appearance_tint`, CAPACITY_CONSUMERS spec §7.3).

### Chrome / inorganic rendering (#511–#551)
Cybernetic limbs and organs render through an inorganic layer in `typeclasses/appearance_mixin.py`:

- **Inorganic location detection**: `_location_is_inorganic(location)` reads the medical state for an organ whose `display_location` is this location and whose data is `inorganic`. Organs inside a body cavity are ignored, so a cyber heart does not chrome the chest (#2587). Chrome locations render in `CHROME_DEFAULT_COLOR` (`|=l`, dark steel grey, `world/combat/constants.py`) instead of skin tone.
- **Side-aware chassis longdesc**: `{side}` tokens in a chassis prototype's `augment_longdesc` resolve at install (a left/right cyber arm reads correctly), alongside the `{Their}` pronoun flex.
- **Deployed-module expansion**: `_deployed_module_longdesc(location)` appends an active module's `deployed_longdesc` (the shotgun arm, the Nailz claws) after the base body line.
- **Deployed hand-slot override**: `_deployed_slot_prose(location)` replaces a *consumed* hand's longdesc when an integrated weapon folds the hand away (`/shotgun` shows the firing socket, not a hand).
- **Stored at install**: chrome longdesc prose is captured when the chassis is installed, not re-rendered on each look. This is a settled design call: old installs keep stale prose until re-install, which is acceptable pre-production.

### Equipment integration
- Worn equipment affects appearance.
- Weapon/tool integration.
- Armor and protection display.
- Magical item effects.

## Privacy and Content

### Privacy model
- **No consent system**: Players are responsible for their own descriptions.
- **No censorship**: Player agency in description content.
- **Optional participation**: Players are not required to set longdescs.
- **Admin override**: Standard admin moderation capabilities.

### Content guidelines
- Player responsibility for appropriate content.
- Standard server rules apply.
- Admin tools for content moderation.
- Appeal/modification processes.

## Unbuilt

- **Location limit**: `MAX_LONGDESC_LOCATIONS` (50) is defined but nothing enforces it. 📋 UNBUILT (not decided)
- **Content filtering** of descriptions. 📋 UNBUILT (not decided)
- **Input sanitization**: only the location and the 1000-character limit are checked, and surrounding whitespace is stripped. 📋 UNBUILT (not decided)
- **Collapsing identical per-side wound sentences**: two identical ordinary per-side wound sentences rendering as one "both hands" line. 📋 UNBUILT (no issue)
- **Custom fitting (tailor)** 📋 UNBUILT:
  - a tailor fitting command for custom clothing adjusted to unique anatomies;
  - adaptive coverage: clothing automatically maps to available body locations;
  - custom measurements: items fitted to a specific character's appendage configuration;
  - coverage validation: clothing coverage matches the character's anatomy.
- **Tattoo / piercing / scar modification** 📋 UNBUILT:
  - tattoo system integration;
  - body modification descriptions;
  - enhancement visibility rules;
  - scar overlays (the medical `can_scar` hook exists; rendering is not wired).

## Not decided

- Whether `describe` gets a `desc` alias. It has none, to avoid colliding with Evennia's builder `@desc`; the decision is deferred.

## Related documents

- `GRAMMAR_ENGINE_SPEC.md` §Number-Flexing Tokens — brace tokens and number flexing.
- CAPACITY_CONSUMERS spec §7.3 — appearance tint from medical symptoms.
