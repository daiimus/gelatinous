# Long Description System Specification

> **Status:** ✅ **SHIPPED** — verified against code 2026-08-02.

## Implementation Status: COMPLETED ✅

**Implementation Complete**: All core components implemented and tested.  
**Testing Status**: Fully functional in Evennia server - in-game validation completed.  
**Documentation Status**: Specification updated to reflect current implementation state.

## Overview

The Long Description (longdesc) system provides players with the ability to set detailed descriptions for specific body parts/locations on their characters. These descriptions appear when other players look at their character, creating rich, personalized character appearances.

## Core Principles

1. **Player Agency**: Players control their character's appearance descriptions
2. **Staff Override**: Staff can set longdescs on any character for content moderation
3. **Layered Architecture**: System designed to integrate with future clothing, equipment, and injury systems
4. **Visibility Control**: Only visible body parts show descriptions
5. **Future-Proof**: Foundation for clothing coverage, injuries, cybernetics, tattoos

## Permission System

### Player Access
- **Self-modification only**: Players can only set longdescs on their own characters
- **Public visibility**: Longdescs visible to all players via look command
- **No consent system**: Players responsible for their own descriptions
- **Optional participation**: Players not required to set longdescs

### Staff Override
- **Permission-based access**: Staff with Builder+ permissions can target other characters
- **Same command interface**: Staff use standard commands with character targeting
- **Content moderation**: Staff can modify any character's longdescs
- **Hierarchical permissions**: Uses Evennia's perm() and perm_above() lock functions

## Body Location System

### Supported Locations
The system supports distinct body locations with left/right differentiation and extensibility for additional appendages:

#### Core Body Locations
- `head` - Overall head/skull area
- `face` - Facial features and expressions
- `left_eye` / `right_eye` - Individual eye descriptions for asymmetry
- `left_ear` / `right_ear` - Ear shape, piercings, modifications
- `neck` - Neck area, throat
- `chest` - Chest/torso front
- `back` - Back and shoulder blades
- `abdomen` - Stomach/belly area
- `groin` - Lower torso/hip area

#### Paired Appendages (Left/Right Support)
- `left_arm` / `right_arm` - Individual arm descriptions
- `left_hand` / `right_hand` - Hands, fingers, nails
- `left_thigh` / `right_thigh` - Upper leg descriptions
- `left_shin` / `right_shin` - Lower legs/calves
- `left_foot` / `right_foot` - Feet, toes, stance

#### Extensible Appendage System
The system is designed to support additional appendages beyond standard human anatomy:

- **Additional Arms**: `left_arm_2`, `right_arm_2`, `left_hand_2`, `right_hand_2`
- **Prehensile Tails**: `tail`, `tail_2` (for multiple tails)
- **Extra Legs**: `left_leg_3`, `right_leg_3`, `left_foot_3`, `right_foot_3`
- **Wings**: `left_wing`, `right_wing`
- **Tentacles**: `tentacle_1`, `tentacle_2`, etc.
- **Other**: Any anatomically relevant appendage following naming convention

### Location Constants
Body locations are defined as constants (similar to Mr. Hands system) to ensure:
- Consistent referencing across codebase
- Easy validation and error handling
- Support for non-standard anatomies
- Integration with future systems
- **Auto-creation of defaults** like Mr. Hands system
- **Centralized configuration** in constants file
- **High practical limits** with theoretical unlimited support
- **Anatomy source of truth** - foundation for all body-related systems

#### Constants Structure
Body locations are declared per species in `world/anatomy/species.py`
(`SPECIES_DEFINITIONS[<species>]`: `default_longdesc_locations`,
`anatomical_display_order`, `anatomical_regions`, `pair_keys`,
`longdesc_flex_nouns`) and read through the `get_species_*` helpers there
(`get_species_default_longdesc_locations` and the rest).
`world/combat/constants.py` keeps human-only copies derived from the human
entry (`DEFAULT_LONGDESC_LOCATIONS`, `ANATOMICAL_DISPLAY_ORDER`,
`ANATOMICAL_REGIONS`, `PAIR_MERGE_KEYS`, `LONGDESC_FLEX_NOUNS`) for callers with
no species, plus the limits below. The human values:

```python
# Default human anatomy (auto-created on character creation)
# Head-region order mirrors organic recognition: hair, then eyes, then
# the head and face resolve into view, followed by ears and neck.
DEFAULT_LONGDESC_LOCATIONS = {
    "hair": None,
    "left_eye": None, "right_eye": None, "head": None, "face": None,
    "left_ear": None, "right_ear": None, "neck": None,
    "chest": None, "back": None, "abdomen": None, "groin": None,
    "left_arm": None, "right_arm": None, "left_hand": None, "right_hand": None,
    "left_thigh": None, "right_thigh": None, "left_shin": None, "right_shin": None,
    "left_foot": None, "right_foot": None
}

# Practical limit for total body locations per character
MAX_LONGDESC_LOCATIONS = 50  # Very high, accommodates extensive modifications

# Individual description character limit
MAX_DESCRIPTION_LENGTH = 1000  # Generous limit, allows detailed descriptions

# Paragraph formatting thresholds
PARAGRAPH_BREAK_THRESHOLD = 400  # Characters before automatic paragraph break
REGION_BREAK_PRIORITY = True     # Prefer breaking between anatomical regions

# Valid location validation set (expandable)
VALID_LONGDESC_LOCATIONS = set(DEFAULT_LONGDESC_LOCATIONS.keys())
```

`MAX_LONGDESC_LOCATIONS` is defined but nothing enforces it: 📋 UNBUILT (not decided).

#### Anatomy Validation System
- **Character anatomy source of truth** - longdesc system serves as foundation for all body-related systems
- **Dynamic validation** - only locations present in character's anatomy dictionary are settable
- **Extensible validation** - supports any anatomy configuration (alien, cybernetic, etc.)
- **Error prevention** - prevents setting descriptions for non-existent body parts

#### Schema Drift & Backfill (IMPORTANT)
A character's `longdesc` dict is persisted **once**, at `at_object_creation`,
as the species' default map from `get_species_default_longdesc_locations(species)`
(human when species is unset). There is no automatic migration:
adding (or reordering) a location in a species' default locations does **not**
propagate to already-existing characters. Their stored dict keeps the key set
(and order) it had at creation time.

Consequences for a body that predates a new default location:
- The location is absent from `get_available_locations()`, so it never appears
  in `describe/list`.
- `has_location()` returns `False` for it, so `describe <new_location> "..."`
  is rejected — the player cannot describe a body part they anatomically have.
- `describe/list` groups by region in **dict-insertion order**, so a key added
  out of canonical position can also display out of anatomical order.

**Whenever a species' default locations gain an entry (or the order
changes), run a one-off backfill** to bring existing bodies into sync. The
backfill rebuilds each dict in that species' canonical order, preserving any
set descriptions and keeping extended anatomy (tails, wings, cybernetics) at
the end. It is idempotent (a second pass updates nothing) and never
overwrites set values.

> ⚠️ **This procedure must be SPECIES-AWARE.** An earlier version of this
> section rebuilt every body against `DEFAULT_LONGDESC_LOCATIONS`, which is
> **human-only** — `world/combat/constants.py` derives it from
> `SPECIES_DEFINITIONS["human"]` and points callers at
> `get_species_default_longdesc_locations(species)` for anything else.
>
> Run against `Character.objects.all_family()`, that version injected human
> anatomy into rats: a rat declares 21 locations and shares only **10** with
> a human, so it would gain 12 keys it has no body for — `face`, `hair`,
> `left_arm`, `left_hand`, `left_thigh` and the rest — making
> `has_location("left_hand")` true on a rat. Synthetics and robots are
> unharmed (both derive from human and share all 22), so rats were the whole
> blast radius. The procedure predates the species split and was never
> rescoped (#2445).

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

Unknown or missing species resolve to human, so check the `species` values on
the bodies before running this: a body whose species is not a registered key
gets human anatomy.

Because the rebuild also reorders each dict into canonical order, it doubles
as the fix for `describe/list` showing a backfilled key (e.g. `hair`) out of
position. This procedure was used to propagate the `hair` location (added in
#176) to the 155 pre-existing bodies that lacked it.

## Command Interface

### Primary Command: `describe`

As of the command-merge work (issue #276), the former `@longdesc`,
`@shortdesc`, and Evennia's default `setdesc` are unified into a single
`describe` command (`commands/CmdCharacter.py::CmdDescribe`, `key="describe"`,
**no aliases**). It owns five facets of a character's appearance:

- **Short Description** — the main paragraph (`db.desc`), formerly `setdesc`.
- **Keyword** — the sdesc noun (`sdesc_keyword`), formerly `@shortdesc`.
- **Look Place** — `look_place`, how the character appears in a room by
  default ("standing here.").
- **Temp Place** — `temp_place`, a placement that overrides the look place and
  is cleared when the character leaves the room.
- **Body locations** — per-part longdesc text (the subject of this spec).

`describe` is **not** aliased to `desc` to avoid colliding with Evennia's
builder `@desc`; that decision is deferred.

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

### Command Behavior
- **Validation**: Location must be a key in the character's own `longdesc` (`has_location`), or a pair shorthand of its species
- **Storage**: Description stored in character database
- **Replacement**: New description overwrites existing for that location
- **Removal**: Empty description removes longdesc for location
- **Feedback**: Confirmation of successful setting/removal
- **Self-targeting**: Players can only modify their own longdescs by default
- **Staff override**: Staff with Builder+ permissions can target other characters

### Command Variations
- `describe` - Open the interactive editor menu (self only)
- `describe short <description>` - Set the short description (`db.desc`)
- `describe keyword <word>` - Set the sdesc keyword (`sdesc_keyword`)
- `describe lookplace <text>` - Set the look place; `clear` resets it to "standing here."; no text shows the current value
- `describe tempplace <text>` - Set the temp place; `clear` empties it; no text shows the current value
- `describe <location> "<description>"` - Set one body location
- `describe <location>` - View current description for location
- `describe/list` - List all available body locations for this character
- `describe/clear <location>` - Remove description for location (set to None)
- `describe/clear` - Clear every body-location description at once (no confirmation prompt)

The `keyword`, `short`, `lookplace` and `tempplace` sub-words (`look_place`
and `temp_place` also work) are reserved one-off forms that always
operate on the caller; they are claimed before staff target resolution because
they are neither valid body locations nor plausible character names.

#### Staff Commands (Permission Override)
- `describe <character> <location> "<description>"` - Set longdesc on another character
- `describe <character>` - View all set longdescs on another character
- `describe/clear <character> <location>` - Clear specific location on another character
- `describe/clear <character>` - Clear every body location on another character

### Interactive Editor (EvMenu)

Bare `describe` (acting on self) opens an EvMenu-driven editor instead of
printing a static list. The list is **flat**: the Short Description, Keyword, Look Place and
Temp Place sit above the anatomy slots so a player edits every facet of their appearance
from one place. The flow:

1. **List node** (`node_describe_list`): a one-per-line numbered list whose
   first four rows are fixed and the rest are dynamic body slots. Rows render
   as `N. Label :: value` with the label column aligned so the `::` separators
   line up. The menu is rendered all-white for readability: in this palette
   `|w` is bold white and `|W` is unbold white, so **only the row numbers and
   section headers are bold**; labels, values, and placeholders are unbold
   white. Values are shown unquoted, and slot labels are capitalized for
   display (`left_eye` -> `Left Eye`, `eyes` -> `Eyes`) via
   `_describe_slot_label` — the internal slot strings are unchanged.
   - `1. Short Description :: …` — current `db.desc` (one-line preview, or
     `(empty)`).
   - `2. Keyword :: …` — current `sdesc_keyword`, or the gendered default
     marked `(default)`.
   - `3. Look Place :: …` and `4. Temp Place :: …` — current `look_place`
     (default `standing here.`) and `temp_place` (or `(none)`). Each opens an
     entry node (`node_lookplace_entry`, `node_tempplace_entry`) that takes new
     text, `clear` (the look place resets to `standing here.`, the temp place
     empties) or `back`/blank. It adds a full stop when the text has no end
     punctuation, and rejects text over 200 characters and re-prompts.
   - `5..N` — editable longdesc **slots**, built by `_build_longdesc_slots`:
     - Symmetric pairs collapse to their shorthand (`eyes`, `hands`, ...) so the
       dynamic anatomy reads as a clean, compact list.
     - An asymmetric pair (only one side present) shows that side individually.
     - Non-pair locations show as themselves; extended anatomy is appended after
       the anatomical-order entries.
     - A pair whose two sides currently diverge is flagged (editing it via the
       shorthand sets both sides alike).
   - `x. Exit` closes the menu cleanly.
2. **Short Description node** (`node_describe_short`): shows the current value
   and a live rendered preview (`_process_description_variables` with
   `force_third_person=True`), then accepts new prose. `clear` empties it,
   `back`/blank returns unchanged. No length cap is applied to the short
   description.
3. **Keyword node** (`node_describe_keyword`): a curated 3-column list of the
   keywords valid for the character's grammar gender, with the current keyword
   marked. Selection (by number or name) applies the keyword and **returns to
   the list** (stays in the menu). Custom keywords are set via the one-off
   `describe keyword <word>` command.
4. **Entry node** (`node_longdesc_entry`): shows the slot's current value and a
   token hint, then accepts the new description. `clear` removes it, `back`/blank
   returns unchanged, over-length input is rejected and re-prompts.
5. On save the longdesc fans out to both sides of a pair (or the single
   location) and a **rendered preview** is shown.

The one-off `describe <location> "<description>"` form is retained and shares
the same preview output.

### Rendered Preview

`_render_longdesc_preview` shows how a freshly-set description will read. For a
symmetric pair it renders both the **plural** form (both sides intact) and the
**singular** form (a lone survivor); for a single location it renders the
singular form. Any brace token the resolver does not recognise survives in the
rendered output and is surfaced as an explicit warning, so typos like
`{thier}` are caught at authoring time rather than shipped silently. The
preview fires after both the interactive editor save and the one-off
`describe <location> "..."` command. The preview recognises only the human
pair shorthands (`PAIR_MERGE_KEYS`), so a rat's `forelegs` gets only the
singular line, and its lone-side line has no side word ("eye", not "left eye"),
unlike the real render.


## Implementation Details

### Character Search System
Staff targeting uses `resolve_admin_target` (`commands/_identity_targeting.py`).
It first looks in the caller's room for a character matching what the caller
sees (sdesc or recognised name; a Builder can also match by key). If that finds
nothing, it searches every Character in the game by key. If that global search
finds more than one, the caller is told to be more specific (for example with a
dbref) and nothing is targeted. `CmdDescribe` uses the result only if it has a
`longdesc`; otherwise the command acts on the caller and reads the whole
argument as a location.

### Permission Integration
- Uses Evennia's lock system: `caller.locks.check_lockstring()`
- Permission check: `perm(Builder) or perm_above(Builder)`
- Hierarchical permissions: Developers, Admins automatically included via `perm_above()`
- Graceful fallback: Non-staff users get standard self-targeting behavior

## Integration with Look System

### Character Appearance Display (REDESIGNED ✅)
When a player executes `look <character>`, the system displays a clean, sectioned format:

1. **Character Name + Base Description**: Name and main description on consecutive lines (no blank line between)
2. **Longdesc + Clothing Integration**: Detailed body part descriptions with clothing
3. **Wielded Items Display**: Natural language listing of held items via hands system
4. **Staff Administrative Info**: Comprehensive inventory for Builder+ permissions

#### New Clean Format Example:
```
CharacterName
Base character description appears here immediately after the name with no blank line between.

First paragraph of longdesc and clothing descriptions, automatically formatted based on anatomical regions and character thresholds for natural reading flow.

Second paragraph continues with additional body descriptions and worn items, maintaining smart paragraph breaks between anatomical regions when appropriate.

CharacterName is holding a weapon and an item.

With your administrative visibility, you see: item1 [#123], item2 [#456], weapon [#789], clothing [#012]
```

#### Template Variable System Enhancement ✅
- **Case Sensitivity Support**: Both {They}/{their} and {they}/{their} work properly
- **Third-Person Consistency**: All descriptions use consistent third-person perspective regardless of viewer
- **Pronoun Processing**: Pronoun tokens follow the character's *apparent* gender (`world.identity.get_apparent_gender`): a disguise keyword sets it, and without one it is the real grammar gender. Male and female render he/she; everything else renders singular they (#2462)
- **Grammar Correction**: Eliminates awkward constructions like "You carries himself"

#### Wielded Items Integration ✅
- **Hands System Integration**: Reads the derived `hands` property (species-aware grasping slots backed by `held_items`; #460). A deployed integrated cyber weapon is not listed as held: it renders on its own line as the limb it has become ("<Name>'s shotgun module is their right hand.", `_format_integrated_weapon_line`) and suppresses "is holding nothing". A natural weapon (claws) never appears here and does not suppress "is holding nothing"
- **Natural Language Display**: "drek is holding a light pistol" with proper grammar
- **Multiple Items Support**: "holding a knife, a pistol, and a grenade"; the renderer writes "a" before every item name, whatever its first letter
- **Empty Hands Display**: "drek is holding nothing" for transparency
- **Combat Readiness**: Immediate visibility of character's weapon state

#### Administrative Features ✅
- **Enhanced Staff Visibility**: "With your administrative visibility, you see:" instead of generic "You see:"
- **Comprehensive Inventory**: Shows all character contents with dbrefs for debugging
- **Permission-Based**: Only visible to Builder+ permissions via `check_permstring("Builder")`
- **Redundancy Acceptable**: Wielded items appear in both sections for complete admin information

#### Smart Paragraph Formatting ✅
- **Automatic line breaks**: System adds paragraph breaks when combined longdescs exceed character threshold
- **Readable flow**: Prevents wall-of-text appearance for verbose descriptions  
- **Threshold-based**: Configurable character count triggers paragraph separation (400 characters)
- **Anatomical grouping**: Line breaks respect anatomical regions when possible
- **Region-aware breaking**: 70% threshold for natural anatomical transitions
- **Clothing integration**: Clothing descriptions participate in paragraph formatting system

#### Display Order (Anatomical Head-to-Toe) ✅
1. **Head region**: hair, left_eye, right_eye, head, face, left_ear, right_ear, neck
2. **Torso region**: chest, back, abdomen
3. **Arm region**: left_arm, right_arm, left_hand, right_hand
4. **Leg region**: groin, left_thigh, right_thigh, left_shin, right_shin, left_foot, right_foot
5. **Extended anatomy**: any other key in the character's `longdesc` (tail, wings, an installed augment), in the order it was added

This is the human order. Each species declares its own order and regions in
`world/anatomy/species.py` (a rat has foreleg, hindleg and tail regions).

**Current Implementation**: Uses `_format_longdescs_with_paragraphs()` method with smart breaking logic and anatomical region awareness for natural paragraph flow.

#### Paragraph Break Logic ✅  
- **Character counting**: System tracks cumulative character count as it builds description
- **Smart breaking**: When threshold reached, insert paragraph break before next anatomical region
- **Region respect**: Avoid breaking within anatomical regions when possible
- **Overflow handling**: Within a region, a new paragraph starts before any description that would push the paragraph past 400 characters. At a region boundary, a break happens only if the paragraph already has 280 or more characters, and the 400 check is skipped there
- **Coverage integration**: Only visible descriptions (body longdescs + clothing longdescs) count toward thresholds
- **Writer freedom**: No forced connecting words or narrative structure - writers control their own style
- **Authoring convention**: Locations within a region are joined with single
  spaces; the renderer adds no capitalization or punctuation. Author each
  location as a **complete sentence** (capitalized, period-terminated) so the
  joined output reads as prose — bare fragments run together into a run-on.
- **Constants-driven**: Uses `PARAGRAPH_BREAK_THRESHOLD` and `REGION_BREAK_PRIORITY` (`world/combat/constants.py`) and the species' `anatomical_regions` (`get_species_anatomical_regions`)

#### Paired Longdesc Collapse ✅
Symmetric left/right paired appendages collapse into a single line when their
descriptions are interchangeable, avoiding redundant repetition (e.g. a single
`{Their} {eyes} {are} pale blue.` rendering once as "Their eyes are pale blue."
instead of repeating "Their eye is pale blue." for each side).

**Pairs are derived dynamically** from `left_*` / `right_*` location keys
(union of `longdesc` keys, `coverage_map`, `ANATOMICAL_DISPLAY_ORDER`, and
severed locations), so custom species anatomy (`left_wing` / `right_wing`,
etc.) participates automatically with no hardcoded list.

**Collapse eligibility** — a pair collapses only when **both** sides are
uncovered AND **one** of:
- **Identical longdescs**: both sides hold the same non-empty longdesc string
  (literal equality — WYSIWYG, no normalization), OR
- **Both cleanly severed**: both sides are fully severed (every visible wound
  at the location has stage `severed`) and neither side has a longdesc.

When eligible, the pair renders as one line and the right-side entry is
skipped. Asymmetric coverage (one side clothed), differing prose, or a single
amputated limb all **fail** the identity test and render each side separately.

**Destroyed organs (#350)**: at a location where an organ is destroyed, the
authored longdesc is not shown; the destruction wound is the only description
there. Identical prose does not collapse if either side is destroyed. When both
sides are destroyed by the same kind of injury and neither side is covered,
they render as one plural destruction line (`_build_destroyed_pair_collapse`,
`world.medical.wounds.get_paired_destroyed_description`).

**Verbatim collapse + number tokens** (the system never rewrites player
prose): the identical string is rendered **once, at plural number**, through
`_process_description_variables(..., number="plural")`. Words the author
wrapped in `{braces}` are flexed to plural; everything else renders verbatim.
A lone survivor or single side renders the same string at `number="singular"`.
When a single side renders, a braced pair noun takes the side: `{eyes}` on
`left_eye` reads "left eye", and `{an arm}` on `right_arm` reads "a right arm"
(#341). Non-pair flex nouns (`leg`, `shoulder`, ...) take no side. A
`{they <verb> ...}` token agrees the verb with the person, not the body part
("she walks", "they walk").
This dissolves the old "can we safely pluralize?" failure mode — there is no
heuristic noun-substitution and no `None` fallback; any identical pair
collapses.

Number tokens (see `GRAMMAR_ENGINE_SPEC.md` §Number-Flexing Tokens):
- **Noun** — a braced word whose singular is in the flex-noun vocabulary: the
  pair nouns (`eye`, `ear`, `arm`, `hand`, `thigh`, `shin`, `foot`; derived
  from the species' `pair_keys`) **plus** the species' curated
  `longdesc_flex_nouns` set (human: `leg`, `shoulder`, `hip`, `knee`, …; rat:
  `tail`, `snout`, `whisker`, …). `{eye}`/`{eyes}` flex the noun;
  `{an eye}` additionally drops the article on plural and re-agrees `a`/`an` on
  singular. `LONGDESC_FLEX_NOUNS` is **vocabulary only** — its words are not
  anatomy locations, not pairs, and not `describe` shorthands; extend it freely
  as players find gaps.
- **Verb** — any other braced single word, conjugated to agree with the part:
  plural `{accent}`/`{are}`, singular `{accents}`/`{is}`. Only brace verbs
  whose subject **is** the body part; a main-clause verb agreeing with the
  person-pronoun ("They have …") is left un-braced.
- **Unrecognised** tokens (multi-word non-noun, typos) are left **literal** and
  logged — a stray brace no longer drops the whole substitution (the old
  `str.format` footgun is gone; substitution is now per-token via `re.sub`).

**Authoring convenience — pair shorthand**: `describe <pair> "..."` (where
`<pair>` is a key of the character's species `pair_keys`, from
`get_species_pair_keys`: for humans `eyes`, `ears`, `arms`, `hands`,
`thighs`, `shins`, `feet`; for rats `eyes`, `ears`, `forelegs`, `forepaws`,
`hindlegs`, `hindpaws`) sets, views, and clears **both** sides at once,
guaranteeing the byte-for-byte identity collapse requires. The pair keys are
write-conveniences only — not body locations, not wearable, not render keys.
Set the sides individually to make them differ (e.g. heterochromia).

**Both-severed stumps** render via `world.medical.wounds`
`get_paired_severed_description` using the type-agnostic
`PAIRED_SEVERED_DESCRIPTIONS` templates, with `{location}` filled as
`both <plural>` (e.g. "both hands").

**Wounds do not gate collapse**: a wound on one side does not split the pair —
the merged line renders once and per-side wound sentences continue to append
through the normal wound-layering path. (Collapsing two identical ordinary
per-side wound sentences into "both hands" is 📋 UNBUILT (no issue); only a
pair destroyed on both sides by the same injury collapses, as described under
Destroyed organs above.)

**Implementation**: `_build_paired_longdesc_collapse`,
`_merge_paired_location`, `_get_severed_locations`,
`_substitute_longdesc_tokens`, and `_flex_noun_vocabulary` in
`typeclasses/appearance_mixin.py`, consulted by both passes of
`_get_visible_body_descriptions`; pair shorthand fan-out in
`_expand_longdesc_pair` (`commands/CmdCharacter.py`, used by `CmdDescribe`).

### Visibility Rules ✅
- **Default**: All body locations are visible unless covered by clothing
- **Clothing Coverage**: Worn items hide covered locations and display their own descriptions instead
- **Unset Locations**: A body part with no longdesc shows nothing unless it has a visible wound, which renders on its own. Organ containers the medical state knows but no longdesc names (a socket left after chrome was removed) are visited too, so their wounds show
- **Template Processing**: All visible descriptions processed for third-person perspective consistency

> **Extended 2026-09-16 (#3578) — the visibility rules are not
> character-only.**  Owner ruling: a severed part must display garments
> *"just like it does on a character, mixing the worn descs and longdesc
> where appropriate."*  All four rules above now hold on the three body
> kinds alike — living character, `Corpse`, and `Appendage` /
> `SeveredHead`.  The living character and the severed part read the
> same outermost-first worn stack through one builder,
> `coverage_from_worn_stack` (`typeclasses/clothing_mixin.py`); the
> corpse, which keeps no stack, derives one (`Corpse.worn_stack()`: layer
> orders each location, styled coverage places the garment) and reads it
> through the same builder (#3577).  A
> covered location on a severed part renders the garment's `worn_desc`
> once, in place of the carried longdesc, and the preserved wounds at
> that location are hidden with it — the same "clothing hides what is
> under it" rule, applied to prose that was snapshotted at sever time.
> The part's worn garments leave Evennia's contents line
> (`Appendage.filter_visible`; what it merely carries is still listed)
> and it no longer appends an "It still wears ..." sentence.
>
> Two limits carry over from the corpse path unchanged: the garment
> **prototype's `coverage` list** is the whole of what gets hidden (a
> helmet declaring `["head"]` leaves the `hair` line visible), and a
> carried longdesc prints **verbatim**, so prose written for a living
> body ("He holds his head slightly forward") still reads that way on a
> detached one.

## Data Storage

### Character Database Structure
Following the Mr. Hands AttributeProperty pattern:

```python
# Seeded at character creation with the species' default locations (human shown)
character.db.longdesc = {
    "head": None, "face": "High cheekbones and a defined jawline lend {their} face a rough calm.", 
    "left_eye": "A piercing blue eye glints with flecks of gold.", "right_eye": "A cybernetic replacement glows with a steady red LED.",
    "left_ear": None, "right_ear": None, "neck": None,
    "chest": "Broad shoulders taper to a narrow waist.", 
    "back": None, "abdomen": None, "groin": None,
    "left_arm": None, "right_arm": None,
    "left_hand": "A calloused hand carries dirt under the fingernails.",
    "right_hand": "A prosthetic metal hand ends in intricately engraved fingers.",
    "left_thigh": None, "right_thigh": None,
    "left_shin": None, "right_shin": None,
    "left_foot": None, "right_foot": None,
    # Extended anatomy (when added)
    "tail": "A long, serpentine tail ends in a barbed tip.",
    "left_wing": "A massive feathered wing spreads in midnight black."
}
```

#### Implementation Pattern
```python
# In Character typeclass (typeclasses/characters.py)
longdesc = AttributeProperty(None, category="appearance", autocreate=True)
# at_object_creation seeds it with get_species_default_longdesc_locations(species);
# return_appearance reseeds it the same way if it is ever None.
```

### Storage Principles
- **AttributeProperty Pattern**: Following Mr. Hands system architecture
- **Auto-Creation**: All default locations created with None values on character creation
- **Dictionary Format**: Easy lookup and modification
- **None as Unset**: Only locations with string values are "set" (None = invisible)
- **Persistent Storage**: AttributeProperty handles automatic database persistence
- **Unicode Support**: Full character set support for descriptions

## Layered System Architecture

### Current Layer: Base Longdescs
- Player-set descriptions stored in database
- Direct display when location is visible
- Manual setting via `describe` command

### Future Layer Integration Points

#### Clothing/Equipment Coverage ✅ **COMPLETED**
- Items define coverage areas: `coverage = ["chest", "left_arm", "right_arm"]`
- **Coverage uses same location constants** as longdesc system for consistency
- **Covered longdescs hidden** - base body descriptions not shown when covered
- **Clothing longdescs displayed** - clothing items have their own appearance descriptions
- **Coverage longdescs count toward paragraph thresholds** - clothing descriptions participate in formatting
- **Dynamic styling system** - items support multiple wear states (rolled up, zipped, etc.)
- **Full integration implemented** - clothing system working with longdesc visibility rules

#### Custom Fitting System (Future)
- **Tailor fitting command** for custom clothing adjusted to unique anatomies
- **Adaptive coverage** - clothing automatically maps to available body locations
- **Custom measurements** - items fitted to specific character's appendage configuration
- **Coverage validation** - ensures clothing coverage matches character's anatomy

#### Injury/Medical System
- Wounds append to the location's longdesc (`append_wounds_to_longdesc`); a
  location with no longdesc still shows its wounds
  (`get_standalone_wound_description`); severed and destroyed parts render as
  described under Paired Longdesc Collapse
- Temporary modifications (bandages, casts)
- Permanent modifications (scars, prosthetics)
- Medical condition visibility: a body's dominant symptom (cyanosis, pallor,
  ...) tints every body longdesc in place of the skintone
  (`world.medical.appearance.get_appearance_tint`, CAPACITY_CONSUMERS spec §7.3)

#### Chrome / Inorganic Rendering ✅ **SHIPPED** (anatomy-augments + cyberware arc, #511–#551)
Cybernetic limbs/organs are no longer a future overlay — they render
through a live inorganic layer in `typeclasses/appearance_mixin.py`:

- **Inorganic location detection** — `_location_is_inorganic(location)`
  reads the medical state for an organ whose `display_location` is this
  location and whose data is `inorganic`; organs inside a body cavity are
  ignored, so a cyber heart does not chrome the chest (#2587); chrome locations render in
  `CHROME_DEFAULT_COLOR` (`|=l`, dark steel grey — `world/combat/constants.py`)
  instead of skin tone.
- **Side-aware chassis longdesc** — `{side}` tokens in a chassis
  prototype's `augment_longdesc` resolve at install (a left/right cyber
  arm reads correctly), alongside the existing `{Their}` pronoun flex.
- **Deployed-module expansion** — `_deployed_module_longdesc(location)`
  appends an active module's `deployed_longdesc` (the shotgun arm, the
  Nailz claws) after the base body line.
- **Deployed hand-slot override** — `_deployed_slot_prose(location)`
  replaces a *consumed* hand's longdesc when an integrated weapon folds
  the hand away (`/shotgun` shows the firing socket, not a hand).
- **Stored-at-install policy** — chrome longdesc prose is captured when
  the chassis is installed, not re-rendered each look (a settled design
  call: old installs keep stale prose until re-install; acceptable
  pre-production).

Tattoos / piercings / scar overlays remain future (see Modification
System below).

#### Tattoo / Piercing / Scar Modification System (Future)
- Tattoo system integration
- Body modification descriptions
- Enhancement visibility rules
- Scar overlays (medical `can_scar` hook exists; rendering not wired)

#### Equipment Integration
- Worn equipment affects appearance
- Weapon/tool integration
- Armor and protection display
- Magical item effects

## Technical Implementation Notes

### Validation System
- **Location validation against character's actual anatomy** (anatomy source of truth)
- **Description length limits (1000 characters max per location)**
- **Paragraph formatting validation (400 character break threshold)**
- Content filtering: 📋 UNBUILT (not decided)
- Input sanitization: 📋 UNBUILT (not decided); only the location and the 1000-character limit are checked, and surrounding whitespace is stripped
- **Anatomical order preservation** for display consistency
- **Dynamic anatomy checking** - only allow longdescs for locations character actually possesses

### Performance Considerations
- Efficient dictionary lookups
- **Minimal database queries** (AttributeProperty handles persistence)
- **No caching needed** (Evennia's scale makes real-time assembly efficient)
- Lazy loading of complex descriptions
- **Direct database access** for optimal performance

### Error Handling
- Invalid location handling
- Database storage failures
- Malformed input protection
- Graceful degradation

## Privacy and Content

### Privacy Model
- **No Consent System**: Players responsible for their own descriptions
- **No Censorship**: Player agency in description content
- **Optional Participation**: Players not required to set longdescs
- **Admin Override**: Standard admin moderation capabilities

### Content Guidelines
- Player responsibility for appropriate content
- Standard server rules apply
- Admin tools for content moderation
- Appeal/modification processes

## Future Expansion

### Planned Integrations
1. **Clothing System** ✅ **COMPLETED**: Coverage-based visibility using shared location constants with dynamic styling
2. **Equipment System** 🔄 **READY**: Worn item integration architecture prepared  
3. **Injury System** 🔄 **READY**: Medical condition display hooks established
4. **Modification System** ◐ **PARTIAL**: Chrome/inorganic cybernetic rendering shipped (#511–#551 — see "Chrome / Inorganic Rendering" above); tattoos/piercings/scars still prepared-not-wired
5. **Pronoun System** ✅ **COMPLETED**: Dynamic pronoun integration via brace tokens (`{their}`, `{they}`, `{name}`) resolved by `_process_description_variables`; FuncParser `$pron()` was never adopted (#3442/#3447)
6. **Tailor System** 🔄 **READY**: Custom fitting commands for unique anatomies architecture prepared

### Architectural Considerations
- **Modular Design**: Each layer independent
- **Plugin Architecture**: Easy system addition/removal
- **Configuration Options**: Server-specific customization
- **API Consistency**: Uniform interface across systems

## Testing Requirements

### Unit Tests ✅ COMPLETED
- ✅ **Command parsing and validation** - Syntax validated, in-game testing completed
- ✅ **Database storage and retrieval** - AttributeProperty implementation working
- ✅ **Location constant validation** - Constants consistency verified  
- ✅ **Error condition handling** - Comprehensive validation implemented
- ✅ **Staff targeting functionality** - Permission-based character targeting working
- ✅ **Search system robustness** - Multi-stage search handles various scenarios

### Integration Tests ✅ COMPLETED
- ✅ **Character creation with longdesc defaults** - AttributeProperty auto-creation working
- ✅ **Character appearance system redesign** - Clean sectioned format implemented and tested
- ✅ **Template variable processing** - Case sensitivity support and third-person consistency working
- ✅ **Wielded items display** - Hands system integration with natural language output tested
- ✅ **Permission system integration** - Enhanced admin visibility messaging tested
- ✅ **Paragraph formatting system** - Smart breaking with anatomical regions tested and validated
- ✅ **Clothing integration** - Coverage-based visibility with longdesc hiding tested

### Integration Tests 🧪 PENDING IN-GAME VALIDATION
- 🧪 **Advanced longdesc combinations** - Complex multi-region descriptions with extensive clothing combinations pending broader testing
- 🧪 **Performance under heavy load** - Optimized for Evennia scale, stress testing with many simultaneous descriptions pending
- 🧪 **Extended anatomy support** - Non-standard anatomies (wings, tails, etc.) implementation validated but broader testing pending

### User Acceptance Tests ✅ COMPLETED  
- ✅ **Player workflow validation** - Complete command interface tested and working
- ✅ **Description setting/viewing** - All CRUD operations tested and functional
- ✅ **Character appearance redesign** - Clean sectioned format tested with positive user experience
- ✅ **Template variable processing** - Case sensitivity and perspective consistency tested and working
- ✅ **Wielded items display** - Natural language presentation with proper grammar tested
- ✅ **Integration with existing systems** - Character, clothing, and hands systems integration working
- ✅ **Error message clarity** - Comprehensive user feedback tested and clear
- ✅ **Staff targeting functionality** - Permission-based targeting tested and working
- ✅ **Administrative visibility** - Enhanced staff inventory display tested and functional

## Migration Strategy

### Initial Implementation ✅ COMPLETED
1. ✅ **Body location constants definition** - Added to `world/combat/constants.py`
2. ✅ **`describe` command implementation** - Complete command (`CmdDescribe`) in `commands/CmdCharacter.py`
3. ✅ **Character appearance integration** - `AppearanceMixin` in `typeclasses/appearance_mixin.py`
4. ✅ **Comprehensive testing and validation** - Full in-game testing completed

### Development Migration ✅ COMPLETED
- ✅ **No automatic migration needed** - system is additive to existing descriptions
- ✅ **Existing Character.db.desc preserved** - appears before longdescs with line break
- ✅ **Clean development environment** - new system doesn't affect existing characters
- ✅ **Gradual adoption** - players can adopt longdescs at their own pace

### Production Readiness ✅ COMPLETED
- ✅ **All core functionality tested** - Command interface, permissions, targeting all working
- ✅ **Error handling validated** - Comprehensive error conditions tested
- ✅ **Performance verified** - System runs efficiently in live environment
- ✅ **Staff tools functional** - Admin override capabilities tested and working

### Incremental Enhancement Status
1. **Clothing coverage integration** ✅ **COMPLETED** - Full clothing system implemented and integrated
2. **Equipment system integration** 🔄 **ARCHITECTURE READY** - Integration points prepared
3. **Injury/modification systems** 🔄 **ARCHITECTURE READY** - Integration hooks established  
4. **Advanced features and optimizations** 🔄 **FOUNDATION READY** - Core system stable for extensions

## Success Criteria

### Functional Requirements ✅ COMPLETED
- ✅ **Players can set/view/modify longdescs** - Complete `describe` command suite tested
- ✅ **Descriptions appear in character appearance** - `return_appearance()` integration working
- ✅ **System integrates with existing look command** - Seamless Evennia integration confirmed
- ✅ **Validation prevents invalid inputs** - Comprehensive error handling tested
- ✅ **Staff can moderate content** - Permission-based targeting functional

### Quality Requirements ✅ COMPLETED
- ✅ **Performance impact minimal** - Optimized for Evennia scale, tested functional in live environment
- ✅ **Error handling comprehensive** - Full validation and user feedback systems tested
- ✅ **User interface intuitive** - Discoverable commands with grouped location display working
- ✅ **Code maintainable and extensible** - Mr. Hands pattern compliance, modular design implemented

### Integration Requirements ✅ COMPLETED
- ✅ **Compatible with existing character system** - AttributeProperty integration working
- ✅ **Ready for clothing/equipment integration** - Visibility hooks implemented and tested
- ✅ **Supports future medical/injury systems** - Anatomy source of truth established
- ✅ **Maintains game balance and immersion** - Smart formatting and validation working
- ✅ **Staff moderation functional** - Permission-based override system tested and working

---

## Implementation Details

### Files Modified/Created ✅ COMPLETED

#### 1. Constants System (`world/combat/constants.py`)
**Status**: ✅ **IMPLEMENTED**  
**Added Constants**:
- `DEFAULT_LONGDESC_LOCATIONS` - 22-location default human anatomy dictionary (includes `hair`)
- `MAX_LONGDESC_LOCATIONS` - Practical limit (50 locations), not enforced: 📋 UNBUILT (not decided)  
- `MAX_DESCRIPTION_LENGTH` - Individual description limit (1000 chars)
- `PARAGRAPH_BREAK_THRESHOLD` - Auto-paragraph threshold (400 chars)
- `VALID_LONGDESC_LOCATIONS` - Validation set
- `ANATOMICAL_DISPLAY_ORDER` - Head-to-toe display sequence (head region ordered by organic recognition: hair, eyes, head, face, ears, neck)
- `ANATOMICAL_REGIONS` - Region groupings for smart paragraph breaks

#### 2. Appearance (`typeclasses/appearance_mixin.py`, mixed into Character; `longdesc` and its seeding stay in `typeclasses/characters.py`)
**Status**: ✅ **IMPLEMENTED**  
**Added Methods**:
- `longdesc` AttributeProperty with auto-creation following Mr. Hands pattern
- `at_object_creation()` enhanced for longdesc system initialization
- `get_longdesc_appearance()` - Main appearance assembly with paragraph formatting
- `_get_visible_body_descriptions()` - Visibility filtering with clothing integration hooks
- `_format_longdescs_with_paragraphs()` - Smart paragraph formatting with region awareness
- `_get_anatomical_region()` - Region identification for formatting logic
- `has_location()` - Anatomy validation (anatomy source of truth)
- `get_available_locations()` - Location discovery and listing
- `set_longdesc()` - Description setting with comprehensive validation
- `get_longdesc()` - Description retrieval with error handling
- `return_appearance()` - Integration with Evennia's look system

#### 3. Command System (`commands/CmdCharacter.py`)
**Status**: ✅ **IMPLEMENTED**  
**Complete Command Suite** (`describe`):
- `describe` - Open the interactive editor (lists short desc, keyword, look place, temp place, and every body location; pick a slot, type new text, see an instant preview)
- `describe <location> "<description>"` - Set one body location with validation
- `describe <location>` - View a specific location's description
- `describe/list` - Show available body locations grouped by anatomical regions
- `describe/clear <location>` - Clear a specific location's description
- `describe/clear` - Clear every body-location description at once (no confirmation prompt)
- **Admin Commands**: Staff can target other characters with proper permission checking
- **Comprehensive Validation**: Location existence, description length, anatomy verification
- **User-Friendly Error Messages**: Clear feedback for all error conditions

#### 4. Command Registration (`commands/default_cmdsets.py`)
**Status**: ✅ **IMPLEMENTED**  
- Added import and registration of `CmdDescribe` in `CharacterCmdSet`
- Integrated with existing command structure

### Technical Architecture ✅ IMPLEMENTED

#### Mr. Hands Pattern Compliance
- ✅ **AttributeProperty usage** with auto-creation and persistence
- ✅ **Dictionary-based storage** for dynamic anatomy support  
- ✅ **Constants-driven validation** and configuration
- ✅ **Consistent integration** with existing codebase patterns

#### Performance Optimization
- ✅ **No caching complexity** - appropriate for Evennia scale
- ✅ **Efficient dictionary lookups** for location and description access
- ✅ **Minimal database queries** via AttributeProperty persistence
- ✅ **Real-time assembly** without performance concerns

#### Future Integration Architecture
- ✅ **Clothing coverage hooks** in `_get_visible_body_descriptions()` method
- ✅ **Injury/modification override points** in appearance assembly
- ✅ **Equipment integration preparation** with visibility system
- ✅ **Pronoun system integration points** identified and documented

### Validation & Testing Status

#### Syntax Validation ✅ COMPLETED
- ✅ **All files compile** without Python syntax errors
- ✅ **Import structure validated** - proper dependency management
- ✅ **Constants consistency verified** - 22 locations, 4 regions (human), complete coverage

#### Logic Validation ✅ COMPLETED  
- ✅ **Paragraph breaking logic tested** with sample verbose descriptions
- ✅ **Anatomical ordering verified** - head-to-toe sequence confirmed
- ✅ **Region coverage confirmed** - all default locations properly categorized

#### Ready for Live Testing 🧪 PENDING
- 🧪 **Character creation and longdesc initialization** - Auto-creation on character creation
- 🧪 **`describe` command functionality** - All command variations and switches
- 🧪 **Character appearance integration** - Look command integration via `return_appearance()`
- 🧪 **Error handling and edge cases** - Invalid locations, permission checks, validation

### Usage Examples ✅ IMPLEMENTED

```bash
# Basic description setting
describe face "High cheekbones and a defined jawline lend {their} face a rough calm."
describe left_eye "A piercing blue eye glints with flecks of gold."  
describe right_hand "A prosthetic metal hand ends in intricately engraved fingers."

# Interactive editor (lists short desc, keyword, look place, temp place, and every body location for editing)
describe

# Discovery and management
describe/list           # Show available locations grouped by region
describe face           # View current face description
describe/clear face     # Clear specific location
describe/clear          # Clear every description at once (no confirmation prompt)

# Staff moderation commands  
describe PlayerName face "staff-modified description"
describe/clear PlayerName face
describe/clear PlayerName
```

### Integration with Look System ✅ IMPLEMENTED

**Character Appearance Assembly**:
1. **Base character description** (from `Character.db.desc`)
2. **Line break** for visual separation  
3. **Visible longdescs** in head-to-toe anatomical order
4. **Smart paragraph formatting** at 400-character threshold with region awareness
5. **Future integration points** for clothing, equipment, status effects

**Example Output**:
```
CharacterName
A weathered detective with years of experience etched into every line.

A piercing blue eye glints with flecks of gold. A cybernetic replacement glows with a steady red LED. High cheekbones and a defined jawline lend her face a rough calm. Broad shoulders taper to a narrow waist. A calloused hand carries dirt under the fingernails. A prosthetic metal hand ends in intricately engraved fingers.

CharacterName is holding nothing.
```

### Next Steps for Testing 🧪

1. **Start Evennia server** with implemented changes
2. **Test character creation** - verify longdesc auto-initialization  
3. **Test `describe` commands** - all variations, switches, and edge cases
4. **Test look integration** - verify appearance assembly and formatting
5. **Test admin commands** - staff permissions and character targeting
6. **Validate error handling** - invalid inputs, permission failures
7. **Performance testing** - multiple characters with extensive descriptions

---
