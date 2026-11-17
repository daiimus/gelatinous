# Clothing System Specification

> **Status:** ✅ **SHIPPED** — verified against code 2026-08-02.
>
> **⚠ Spec-vs-code corrections — the following claims were FALSE when audited:**
> - "Phase 3: Advanced Features 📋 PENDING — layer conflict detection and resolution" is **stale**; it is fully implemented in `clothing_mixin.wear_item`. Staff targeting ships as `CmdDress`/`CmdUndress`. (Precision, 2026-09-11: those two are `cmd:all()` PLAYER verbs gated on trust or incapacity — `CmdDress` and `CmdUndress` in `commands/CmdClothing.py`, both `locks = "cmd:all()"`. No staff-only clothing verb exists, and the `@wear` / `@remove` commands sketched in §Staff Commands were never built.)
> - **"Meaningful transition validation" — style changes requiring both a `coverage_mod` AND a `desc_mod` — was NEVER IMPLEMENTED and must not be.** `can_style_property_to()` checks membership only (`typeclasses/items.py`). 35 of the 60 style states in `world/prototypes.py` would be refused if the rule were enforced, every restore-to-`normal` among them. See §Style Validation and §Key Design Decisions.
> - **`desc_mod` values do not combine.** `get_current_worn_desc()` (`typeclasses/items.py`) returns the FIRST non-empty `desc_mod` in sorted property order and stops, and a `desc_mod` **replaces** the whole `worn_desc`. The combined-sentence examples in §Multi-Property Combination Examples are not what renders. `coverage_mod` values DO combine.

## Implementation Status: CORE COMPLETE ✅

**Design Phase**: Comprehensive specification completed with dynamic styling system  
**Implementation Status**: Core functionality implemented and tested - ready for advanced features  
**Documentation Status**: Complete. Pronoun handling is the grammar engine's `{their}`/`{they}` brace tokens — `$pron()` was found not to work in prototypes (see §Enhanced Features).  
**Testing Status**: Basic clothing system verified working in game environment

## Overview

The Clothing System extends the longdesc foundation to provide wearable items that modify character appearance through coverage-based visibility rules. Clothing items have dynamic styling capabilities allowing players to adjust appearance and coverage through intuitive commands like `rollup`, `unroll`, `zip`, and `unzip`.

## Core Principles

1. **Coverage-Based Visibility**: Clothing hides covered body locations while adding its own descriptions
2. **Dynamic Styling**: Items support multiple style states with meaningful coverage and appearance changes
3. **Layered Architecture**: Multiple clothing items can be worn simultaneously with layering rules
4. **Shared Location Constants**: Uses the same body location system as longdesc for consistency
5. **Appearance Integration**: Seamlessly integrates with existing character appearance system
6. **Roleplay Enhancement**: Style commands provide intuitive roleplay interactions with meaningful feedback
7. **Pronoun Integration**: Clothing descriptions use the grammar engine's `{their}`/`{they}` brace tokens for perspective handling — **not** Evennia's `$pron()` (which doesn't work in prototypes; see §Enhanced Features and `GRAMMAR_ENGINE_SPEC.md`)
8. **Color Immersion**: ANSI color integration for enhanced visual immersion and atmospheric descriptions

## Integration with Longdesc System

### Shared Body Location System
Clothing uses the exact same body location constants as longdesc:
- **Consistent mapping**: Clothing coverage and longdesc locations use identical constants
- **Single source of truth**: body locations come from the species registry (`default_longdesc_locations` in `world/anatomy/species.py`); `world/combat/constants.py` copies the human set
- **No coverage validation**: nothing checks a garment's `coverage` list against the body's locations at runtime; a misspelt location is accepted and covers nothing

### Coverage Rules
- **Hidden longdescs**: When clothing covers a body location, that location's longdesc is not displayed
- **Clothing descriptions**: Worn items contribute their own appearance descriptions
- **Layering order**: Multiple items on same location follow layering rules (outer layers visible)
- **Partial coverage**: Items can cover multiple locations (e.g., shirt covers chest, back, abdomen)

> **Note 2026-09-16 (#3578) — these rules belong to the *body*, not to
> the living character.**  Owner ruling: a severed part must display
> garments *"just like it does on a character, mixing the worn descs and
> longdesc where appropriate."*  Hidden longdescs, clothing descriptions
> and partial coverage are now honoured by three renderers —
> `AppearanceMixin._get_visible_body_descriptions` (living),
> `Corpse._get_preserved_longdesc_descriptions`, and
> `Appendage.return_appearance` (severed limbs and heads).  **Layering
> order is the one rule that does not carry over**: see the builder note
> immediately below.
>
> **One builder, one rule, three sources of the stack (corrected
> 2026-09-17 after the #3578 review; unified by #3577).** "Outermost wins the location" is
> the rule everywhere; the data shape decides how it is read.  A living
> character and a severed part both carry a **worn stack**
> `{location: [garments, outermost first]}` — the character's
> `worn_items`, the part's self-healing `worn_items` ledger, which
> `detach_items_to_appendage` copies in that order and `undress`/`dress`
> maintain — so both read the first entry at each location through the
> module-level **`coverage_from_worn_stack(worn_items)`** in
> `typeclasses/clothing_mixin.py` (`ClothingMixin._build_clothing_coverage_map`
> delegates to it; `Appendage.return_appearance` heals the ledger with
> `worn_garments()` and then reads it).  A `Corpse` keeps **no stack**,
> only the flat `worn_garments()` list (contents filtered by
> `worn_at_death`), so `Corpse.worn_stack()` derives one — the layer
> orders each location, highest outermost, and each garment sits at its
> **current** coverage (`get_current_coverage()`, so a rolled cap does not
> cover the ears it is rolled off) — and the same builder reads it
> (#3577, 2026-09-17).  One rule, one builder, three wearers; only the
> stack's source differs.  The first #3578 cut fed the part's
> flat list to a "later wins" builder; the ledger lists outermost FIRST,
> so that showed the innermost garment and lost the helmet over a
> balaclava entirely — the review caught it.
>
> **What a garment does on a dead body.** It renders its `worn_desc`
> **once**, in place of the covered location's longdesc, and everything
> under it — authored prose *and* preserved wounds — is hidden.  Neither
> a corpse nor a severed part lists what it is WEARING as contents (a
> part still lists what it merely carries — retracted hardware, a thing
> put in a severed hand — through Evennia's own `You see:` line, since
> that line is the only way such contents are found: `Appendage.filter_visible`
> drops worn garments from it, nothing else), and the severed part's
> old "It still wears a bloodstained glove" sentence was deleted with
> `_build_worn_items_line`.  What gets hidden is exactly the garment
> **prototype's `coverage` list** and nothing more — `MINING_HELMET`
> declares `["head"]`, so a severed head wearing one still shows its
> `hair` line — the same binary, location-shaped limit the sheer-garment
> gap below describes.  And a carried longdesc prints verbatim, so prose
> authored for a living body ("He holds his head slightly forward") reads
> the same way on a detached one.  Both are pre-existing corpse
> properties, not new to #3578.

## Clothing Item Architecture

### Wearable Item Class
```python
# Items become clothing simply by having coverage and worn_desc populated
# All functionality implemented in base Item class via AttributeProperty

class Item(ObjectParent, DefaultObject):
    """
    Base item class with optional clothing capabilities.
    Items become wearable when coverage and worn_desc are set.
    """
    
    # Coverage definition - which body locations this item covers (base state)
    # Empty list = not wearable, populated list = clothing item
    coverage = AttributeProperty([], autocreate=True)
    
    # Clothing-specific description that appears when worn (base state)
    # Empty string = not clothing, populated = worn description
    # USES {their}/{they} brace tokens for perspective-aware descriptions
    worn_desc = AttributeProperty("", autocreate=True)
    
    # ANSI color definition for this item
    # Used for atmospheric descriptions and visual immersion
    color = AttributeProperty("", autocreate=True)
    
    # Material type for this item (for future armor/crafting systems)
    # Examples: "leather", "steel", "silk", "kevlar", "titanium"
    material = AttributeProperty("", autocreate=True)
    
    # Layer (higher = outer layer) is a property, not an AttributeProperty:
    # a stored `layer` attribute wins; otherwise world.style.derive_rung
    # reads it from the garment's name ('coat' is 4, 'boots' 5), and a
    # name that matches nothing is layer 1.
    @property
    def layer(self): ...
    
    # Multiple style properties for combination states
    style_properties = AttributeProperty({}, autocreate=True)
    # Structure: {"adjustable": "rolled", "closure": "zipped"}
    
    # Style configurations defining all possible combinations
    style_configs = AttributeProperty({}, autocreate=True)
    # Structure: {
    #     "adjustable": {
    #         "rolled": {"coverage_mod": [...], "desc_mod": "a completely different description when rolled"},
    #         "normal": {"coverage_mod": [], "desc_mod": ""}  # Empty desc_mod = use base worn_desc
    #     },
    #     "closure": {
    #         "zipped": {"coverage_mod": [...], "desc_mod": "a totally different description when zipped"},
    #         "unzipped": {"coverage_mod": [...], "desc_mod": "another unique description when unzipped"}
    #     }
    # }
    
    def is_wearable(self):
        """Check if this item can be worn as clothing"""
        return bool(self.coverage) and bool(self.worn_desc)
```

The disguise attributes (`is_disguise_item`, `disguise_essential`, `disguise_type_id`, `disguise_weight`, `disguise_adjective`, `worn_sdesc_short`) also live on `Item`; see IDENTITY_RECOGNITION_SPEC §Disguise Items.

### Coverage System Design

## Enhanced Features

### Perspective-Aware Descriptions (NOT using $pron())
**Important**: After testing, we discovered that `$pron()` functions are **NOT available in prototypes**. They only work in `msg_contents()` calls during runtime messaging.

> **CORRECTED 2026-08-29 (#2396).** This section used to say worn
> descriptions take **static pronouns** and that "perspective handling occurs
> in `get_current_worn_desc_with_perspective()`, not in the prototype
> definitions" — while the example forty lines below used `{their}` tokens.
> Both conventions were documented, so both got written: of 78 worn
> descriptions, 13 used tokens and 65 did not.
>
> **The code settles it.** `get_current_worn_desc_with_perspective()` ends in:
>
> ```python
> return from_obj._process_description_variables(
>     colored_desc, looker, force_third_person=True)
> ```
>
> That is the SAME token processor longdescs use. So `{their}` is resolved
> against the wearer's gender and renders "his" / "her" / "its"; a literal
> `their` is never touched and renders "their" on everybody. A static pronoun
> is not perspective-neutral — it is simply wrong for any wearer who is not a
> plural.
>
> **The rule:** any pronoun referring to the WEARER is a token — `{their}`,
> `{them}`. A pronoun referring to the GARMENT stays plain prose ("office
> trousers holding their line", "its ripstop fabric"), because the garment's
> number does not change with who is wearing it.
>
> Body-part references may use either `{their} chest` or `the chest`; both
> read correctly. `{their}` is preferred for new work, as in `COMBAT_BOOTS`.
>
> A worn_desc must never assert the WEARER'S history — it is the same string
> on everyone who puts the garment on. History belongs to the garment
> ("ghost-stitching where patches used to live"), not the person.

> **A DISGUISE GARMENT MUST NOT BETRAY ITSELF (2026-08-29).** A wig covers
> `hair` in order to change apparent identity, so its worn description has to
> read as *hair* — not as a wig. Anything that tells the reader the hair is
> artificial ("sits too evenly to have grown there", "moves as one piece")
> defeats the mechanic the item exists for, because that string is what every
> observer sees. The same holds for contacts, masks and anything else on the
> disguise line: describe what it is meant to be taken FOR, never what it
> actually is.
>
> This is the disguise-layer counterpart to the no-wearer-history rule: a
> worn_desc is seen by everyone, so it must not smuggle in knowledge the
> observer has not earned.

### Coverage is binary, and two real garments need it not to be

**Status: 📋 PROPOSAL — the gap is real and demonstrated, the design is not
decided.**

A location is either covered by a garment or it is not. `coverage_mod` can add
or remove a location per style state, but there is no third setting, and two
things in the game already need one:

* **Sheer.** `MESH_TOP` is described as a weave "open enough to read as shadow
  rather than fabric" while its coverage is the entire torso and both arms — so
  it conceals the body completely. The prose promises sheer and the model
  delivers opaque. Cutting its coverage to compensate is worse: it would stop
  registering as clothing on those locations at all, so layering, armour and
  removal-blocking would all mis-handle it.
* **Partial.** A hat sits ON the head and hair shows under the brim. The
  existing convention splits headwear into garments that ENVELOP (balaclava,
  ski mask, hood, wigs — these cover `hair`) and garments that SIT ON
  (helmets, caps, wide-brim hats — these do not), which is a reasonable
  approximation, but `HEAD_WRAP` is genuinely mis-grouped and cannot be fixed
  by moving it between two groups when the truth is "mostly covered".

Both want the same missing idea: **a garment can cover a location without
concealing it.**

Sketch, not a decision — the cheapest shape is likely a per-garment
`sheer` flag (or a per-location set) consulted where the coverage map is
built (`coverage_from_worn_stack`, shared by living bodies, corpses and
severed parts): a sheer garment still registers for layering,
armour and removal rules, but the appearance layer renders the body longdesc
underneath *as well as* the garment rather than instead of it. That keeps the
mechanical meaning of coverage intact and changes only what is shown.

Open questions the owner should settle before anyone builds it: whether sheer
is a property of the garment or of a style state (a coat can be open without
being sheer); whether armour and combat targeting should see through it at all;
and how two sheer layers stack.

### ANSI Color System Integration
A clothing item has one `color` attribute. A `{color}` token in its current worn description is replaced by that colour's ANSI code from `COLOR_DEFINITIONS`:

```python
# Color definitions using Evennia ANSI constants
COLOR_DEFINITIONS = {
    "black": "|=l",       # Black (256-colour dark grey)
    "red": "|r",          # Red  
    "green": "|g",        # Green
    "yellow": "|y",       # Yellow
    "blue": "|b",         # Blue
    "magenta": "|m",      # Magenta
    "cyan": "|c",         # Cyan
    "white": "|w",        # White
    # Bright colors
    "bright_black": "|K", # Dark Gray
    "bright_red": "|R",   # Bright Red
    "bright_green": "|G", # Bright Green
    "bright_yellow": "|Y",# Bright Yellow
    "bright_blue": "|B",  # Bright Blue
    "bright_magenta": "|M", # Bright Magenta
    "bright_cyan": "|C",  # Bright Cyan
    "bright_white": "|W", # Bright White
}

# Example colored clothing prototypes
DEVELOPER_HOODIE = {
    "worn_desc": "A menacing {color}black|n developer hoodie that clings to {their} frame like digital shadow incarnate, command-line text pulsing ominously across {their} chest",
    "color": "black",
    "material": "cotton",
}

BLUE_JEANS = {
    "worn_desc": "Battle-tested {color}denim|n jeans that cling to {their} form with urban authority, {their} faded indigo surface scarred by countless encounters", 
    "color": "blue",
    "material": "denim",
}
```

A colour name that is not in `COLOR_DEFINITIONS` turns the `{color}` token into nothing, so the word shows in the default colour. Most colour names the prototypes use (grey, charcoal, brown, amber, olive and others) are not in the table.

### Color and Material Enhanced Descriptions
`Item._process_color_codes` in `typeclasses/items.py` fills the `{color}` token. It runs on the current worn description (the active `desc_mod`, or `worn_desc`) before pronoun tokens are resolved. `material` is stored on the item, but no worn description reads it.

```python
def _process_color_codes(self, text):
    """Replace {color} in the current worn description with an ANSI code"""
    desc = text
    
    # Replace color placeholders with actual ANSI codes
    if self.color:
        color_ansi = COLOR_DEFINITIONS.get(self.color, "")
        desc = desc.replace("{color}", color_ansi)
    
    return desc

# Example usage in prototypes:
RAINBOW_SOCKS = {
    "worn_desc": "Wildly vibrant rainbow socks that shimmer with {color}prismatic brilliance|n across {their} feet",
    "color": "bright_magenta",
    "material": "synthetic",
}
```

### Coverage System Design

#### Coverage Categories
Following body location constants, clothing items define coverage arrays:

```python
# Example clothing coverage definitions
SHIRT_COVERAGE = ["chest", "back", "abdomen"]
PANTS_COVERAGE = ["groin", "left_thigh", "right_thigh"] 
JACKET_COVERAGE = ["chest", "back", "abdomen", "left_arm", "right_arm"]
GLOVES_COVERAGE = ["left_hand", "right_hand"]
BOOTS_COVERAGE = ["left_foot", "right_foot"]
HAT_COVERAGE = ["head"]
FULL_ROBE_COVERAGE = ["chest", "back", "abdomen", "groin", "left_arm", "right_arm", "left_thigh", "right_thigh"]
```

#### Layering System
Layers run 0 to 5; higher is further out. A garment that sets its own `layer` keeps it; otherwise its name picks the layer from `RUNGS` in `world/style.py`:
- **Layer 0**: underwear, undershirts, socks, stockings, tights
- **Layer 1**: shirts, trousers, skirts, dresses, wigs, watches, scrubs; also any garment whose name matches nothing
- **Layer 2**: vests, hoodies, sweaters, coveralls, masks, balaclavas, respirators, glasses
- **Layer 3**: jackets, blazers, harnesses, hoods, slickers
- **Layer 4**: coats, robes, ponchos, aprons, cloaks
- **Layer 5**: footwear, hats, caps, helmets, gloves, belts, ties, scarves, goggles

Two garments on the same layer at the same location cannot both be worn, a garment cannot go on under one already worn on a higher layer, and a higher layer blocks removal of what is under it.

### Dynamic Styling System

#### Style States
Each clothing item can have multiple wear configurations that modify both coverage and appearance:

**Core Style Commands:**
- `rollup <item>` / `unroll <item>` - the garment's adjustable feature: roll or unroll sleeves, loosen or straighten a tie, raise or lower a hood
- `zip <item>` / `unzip <item>` / `button <item>` / `unbutton <item>` - close or open a worn garment's closure, zipped or buttoned, whichever it declares

**Style Configuration Examples:**
```python
# Jacket with rollable sleeves and zipper
jacket_styles = {
    "adjustable": {
        "normal": {"coverage_mod": [], "desc_mod": ""},
        "rolled": {"coverage_mod": ["-left_arm", "-right_arm"], "desc_mod": "a black leather jacket with sleeves rolled up to the elbows"}
    },
    "closure": {
        "zipped": {"coverage_mod": [], "desc_mod": "a black leather jacket zipped tight against the cold"},
        "unzipped": {"coverage_mod": ["-chest", "-abdomen"], "desc_mod": "a black leather jacket hanging open, brass zipper gleaming"}
    }
}
# Base coverage: ["chest", "back", "abdomen", "left_arm", "right_arm"]

# Hoodie with rollable hood (using rollup command for hood)
hoodie_styles = {
    "adjustable": {
        "normal": {"coverage_mod": [], "desc_mod": ""},
        "rolled": {"coverage_mod": ["+head"], "desc_mod": "a gray hoodie with the hood pulled up, shadowing the face"}
    },
    "closure": {
        "zipped": {"coverage_mod": [], "desc_mod": "a gray hoodie zipped up tight"},
        "unzipped": {"coverage_mod": ["-chest"], "desc_mod": "a gray hoodie hanging open casually"}
    }
}
# Base coverage: ["chest", "back", "abdomen", "left_arm", "right_arm"]
# Commands: "rollup hoodie" pulls hood up, "zip hoodie" zips closure

# Shirt with just rollable sleeves
shirt_styles = {
    "adjustable": {
        "normal": {"coverage_mod": [], "desc_mod": ""},
        "rolled": {"coverage_mod": ["-left_arm", "-right_arm"], "desc_mod": "a cotton shirt with sleeves rolled to the elbows, exposing forearms"}
    }
}
# Only rollup/unroll commands work - zip commands give "no zipper" message

# Boots with just zipper
boot_styles = {
    "closure": {
        "zipped": {"coverage_mod": [], "desc_mod": "black combat boots laced tight and ready"},
        "unzipped": {"coverage_mod": [], "desc_mod": "black combat boots worn loosely, laces dangling"}
    }
}
# Only zip/unzip commands work - rollup commands give "nothing to roll" message
```

#### Multi-Property Combination Examples
Items with multiple style properties create combinatorial states with both functional and visual variety:

```python
# Black leather jacket - demonstrates 4-state combination system
jacket = {
    "coverage": ["chest", "back", "abdomen", "left_arm", "right_arm"],
    "worn_desc": "a black leather jacket",
    "style_configs": {
        "adjustable": {
            "normal": {"coverage_mod": [], "desc_mod": ""},
            "rolled": {"coverage_mod": ["-left_arm", "-right_arm"], "desc_mod": "with sleeves rolled up"}
        },
        "closure": {
            "zipped": {"coverage_mod": [], "desc_mod": "zipped tight against the cold"},
            "unzipped": {"coverage_mod": ["-chest", "-abdomen"], "desc_mod": "hanging open"}
        }
    }
}

# The four possible combinations:
# 1. {"adjustable": "normal", "closure": "zipped"} (default)
#    Coverage: ["chest", "back", "abdomen", "left_arm", "right_arm"]  
#    Description: "a black leather jacket zipped tight against the cold"
#
# 2. {"adjustable": "rolled", "closure": "zipped"}  
#    Coverage: ["chest", "back", "abdomen"]  # arms removed by rollup
#    Description: "a black leather jacket with sleeves rolled up to the elbows, zipped tight"
#
# 3. {"adjustable": "normal", "closure": "unzipped"}
#    Coverage: ["back", "left_arm", "right_arm"]  # chest/abdomen removed by unzip  
#    Description: "a black leather jacket hanging open, brass zipper gleaming"
#
# 4. {"adjustable": "rolled", "closure": "unzipped"}
#    Coverage: ["back"]  # arms removed by rollup, chest/abdomen removed by unzip
#    Description: "a black leather jacket with sleeves rolled up, hanging open with brass zipper gleaming"
```

> **CORRECTED 2026-09-11 (#2445 item 8).** The **coverage** half of this example
> is exactly what ships. `get_current_coverage()` (`typeclasses/items.py`)
> walks every active property in sorted order and applies all of their
> `coverage_mod` lists cumulatively, so combination 4 really does reduce to
> `["back"]`.
>
> The **description** half does not ship. `get_current_worn_desc()`
> (`typeclasses/items.py`) returns the FIRST non-empty `desc_mod` in
> sorted property order and stops. Two consequences:
>
> - `desc_mod` values never concatenate. In combination 4 the code renders the
>   `adjustable`/`rolled` description alone and drops the `closure`/`unzipped`
>   sentence entirely. Sorted order means `adjustable` always outranks
>   `closure`.
> - A `desc_mod` **replaces** the whole `worn_desc`; it is not a suffix. That is
>   what the `style_configs` structure comment in §"Wearable Item Class" at the
>   top of this spec already says (*"Empty desc_mod = use base worn_desc"*), so
>   the fragment-style values used above (`"with sleeves rolled up"`, `"zipped
>   tight against the cold"`, `"hanging open"`) are not how live garments are
>   authored. All 35 non-empty `desc_mod` values in `world/prototypes.py` are
>   complete standalone worn descriptions — see `WORK_COVERALLS`
>   in `world/prototypes.py`.
>
> Authors should therefore write each state's `desc_mod` as a full description
> that reads correctly on its own, and accept that when two properties are both
> off-default only the `adjustable` one narrates. The example above is kept for
> the combinatorial *coverage* reasoning, which is still correct.

#### Style Validation
- **Configuration check**: Commands only work if item has the required style_configs
- **Meaningful transition validation**: none. A style change needs only a state the garment declares; its `coverage_mod` and `desc_mod` may each be empty (see note below)
- **Defensive command validation**: Commands refuse a state the garment does not declare, or the state already current; nothing tests whether a change is meaningful
- **IC failure messages**: "The shirt doesn't have anything to roll up." / "The jacket doesn't have a zipper."
- **State tracking**: Items remember their current style_properties across sessions
- **Layer interaction**: none. A style change re-seats the garment at its new coverage and never refuses on a layer conflict (see note below)

> **CORRECTED 2026-09-11 (#2445 item 8).** Of those six bullets as first written, two are
> honoured as written, one is honoured more narrowly than it reads, and three
> are not honoured at all.
>
> **Honoured.** *Configuration check* — `CmdRollUp.func` and `CmdZip.func` in
> `commands/CmdClothing.py` refuse before any other style check if the garment declares no `adjustable` /
> `closure` entry. *State tracking* — `style_properties` is a persisted
> `AttributeProperty` (`typeclasses/items.py:208`).
>
> **Meaningful transition validation — never shipped, and must not be.**
> `Item.can_style_property_to()` (`typeclasses/items.py`) checks
> membership only, and says why: *"Always allow transitions to valid states -
> the validation is structural, not functional."* The both-populated rule would
> break the shipped wardrobe: of the 60 style states declared in
> `world/prototypes.py`, **35 leave `coverage_mod` and/or `desc_mod` empty, and
> all 24 prototypes that declare `style_configs` carry at least one of them** —
> including every one of the 12 restore-to-`normal` states (`WORK_COVERALLS`), the dust poncho's `unzipped`, which is also its
> DEFAULT state (`DUST_PONCHO`), the
> slicker's `hood_down` (`SEALED_SLICKER`), and the thermal's `rolled`, which
> changes prose without changing coverage (`THERMAL_SHIRT`).
> Under this rule nothing could ever be unrolled, unsnapped, lowered or
> straightened again. This spec's own boot example above (`zipped`/`unzipped`,
> both with an empty `coverage_mod`) fails it too.
>
> **Defensive command validation — honoured, but structurally rather than
> semantically.** The commands refuse a property the garment does not declare
> (the configuration check above), a target state the garment does not declare
> (`_target_style_state` in `commands/CmdClothing.py`, called from both
> commands), and a state that is already current — that last
> one is the only sense in which "a transition with no effect" is prevented.
> Nothing tests whether a change would be *meaningful*. One consequence: the
> `"That wouldn't change anything about the ..."` refusal still present in
> both commands is unreachable, because its target state was read out of
> `style_configs` a few lines earlier, so the guard it sits behind cannot fail.
>
> **IC failure messages — half stale.** The zipper line is verbatim
> (`CmdZip.func`). The sleeve line is not: the rollup refusal
> reads `The <item> doesn't have anything to roll up.`
> (`CmdRollUp.func`) — phrased from the command rather than from
> sleeves, which is what the garment-driven targeting of #2742 requires, since
> `rollup` now also reaches hoods and neckties. `button`/`unbutton` add a
> third: `The <item> doesn't have buttons.` `unroll` on a garment with no
> adjustable feature says `The <item> doesn't have anything to unroll.` A
> garment that declares the property but none of the states the verb can
> reach gets `There's no way to <roll up|unroll|close|open> the <item>.` A
> change to the state already current gets `The <item> is already <state>.`,
> the state reading `rolled up`, `zipped up`, `unbuttoned`, `hood down` and so
> on; `unroll` on a garment that is not rolled says `already straight`.
>
> **Layer interaction — not implemented, and the gap is reachable.** A style
> change never consults layering and never refuses on it. It **re-seats** the
> garment: `set_style_property` calls `Character.refresh_worn_coverage`
> (`Item.set_style_property` → `refresh_worn_coverage` in `typeclasses/clothing_mixin.py`),
> which lifts the item out of `worn_items` everywhere and re-inserts it by
> `layer` at its new coverage — which is what lets the layer beneath surface
> the moment a sleeve rolls (#2398). Layer *conflict* detection remains a
> **wear**-time rule only (`clothing_mixin.wear_item` and
> `clothing_mixin.blocking_garments`). Record this as a gap, not a
> ruling: a state whose `coverage_mod` ADDS a location can seat a garment where
> `wear_item` would have refused it — `hood_up` on the tox-sealed slicker adds
> `+head` at layer 3, the same layer as `HOODIE_HOOD_UP`, and the developer
> hoodie's `rolled` adds `+head` at layer 2, the same layer as `BALACLAVA`.
> Whether a style change should refuse on conflict, or keep re-seating
> silently, is still open; this note describes what runs today.

#### Defensive Validation Logic
> **NOT IMPLEMENTED (#2445 item 8).** `validate_style_transition()` does not
> exist anywhere in the codebase — a repo-wide grep for `validate_style` returns
> nothing. The sketch below was never built, and the both-populated rule at its
> heart is the one corrected immediately above. The validation that did ship is
> split between `Item.can_style_property_to()` (`typeclasses/items.py`) and
> the two style commands (`CmdRollUp.func` and `CmdZip.func` in
> `commands/CmdClothing.py`).
> Kept because it records the reasoning the design started from.

All style commands perform comprehensive validation before executing transitions:

```python
def validate_style_transition(self, property_name, target_state):
    """Comprehensive validation for style transitions"""
    # Check if item supports this style property
    if property_name not in self.style_configs:
        return False, f"The {self.key} doesn't have a {property_name} that can be adjusted."
    
    # Check if target state exists
    if target_state not in self.style_configs[property_name]:
        return False, f"Invalid {property_name} state: {target_state}"
    
    # Check if already in target state
    current_state = self.style_properties.get(property_name, "normal")
    if current_state == target_state:
        return False, f"The {self.key} is already {target_state}."
    
    # Require meaningful changes (both coverage AND description)
    config = self.style_configs[property_name][target_state]
    has_coverage_change = bool(config.get("coverage_mod", []))
    has_desc_change = bool(config.get("desc_mod", "").strip())
    
    if not (has_coverage_change and has_desc_change):
        return False, f"That wouldn't change anything about the {self.key}."
    
    return True, "Valid transition"
```

### Clothing Appearance Integration

#### Worn Description System
Each clothing item has two descriptions:
1. **Item description** (`db.desc`): How it appears when not worn (in inventory, on ground)
2. **Worn description** (`worn_desc`): How it appears when worn on the character

#### Example Integration
**Note**: Clothing descriptions integrate with the existing longdesc paragraph formatting system, using the same smart breaking logic and anatomical region awareness.

**Inventory Integration:**
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

**Default State Convention**: A worn garment with no bracket shows no off-default state. For each style property, the default is the first state the garment declares with both `coverage_mod` and `desc_mod` empty. Only two off-default states are named: `rolled up` (adjustable) and `unzipped` (closure). Other states (buttoned, open, loosened, hood up, zipped) are never shown, and a property that has no state with both fields empty never shows in the bracket.

**Appearance Display:**
```
# Character without clothing
Sterling Hobbs(#216)
A breathing body without an identity. Its eyes flicker, but it does not move.

His face shows weathered features with high cheekbones. His chest displays broad shoulders tapering to a narrow waist.

# Character wearing a jacket (jacket covers chest, back, abdomen)
Sterling Hobbs(#216)  
A breathing body without an identity. Its eyes flicker, but it does not move.

His face shows weathered features with high cheekbones. He wears a worn leather jacket with brass buckles across his torso.

# Character wearing jacket + hat (multiple items with paragraph formatting)
Sterling Hobbs(#216)  
A breathing body without an identity. Its eyes flicker, but it does not move.

He wears a weathered tricorn hat tilted at a rakish angle. His face shows weathered features with high cheekbones.

He wears a worn leather jacket with brass buckles across his torso.
```

## Command Interface

### Naming a garment (#3783)

Every clothing verb names its garment through the one core matcher,
`Character.search`, scoped to the verb's own pool with
`candidates=`. No verb compares typed text to keys itself.

| verb | pool |
|---|---|
| `wear` | the caller's contents (held items included) |
| `remove` / `unwear`, `rollup` / `unroll`, `zip` / `unzip` / `button` / `unbutton` | the caller's worn items |
| `undress <target> <item>` | `target.worn_garments()` (a character, a corpse, a severed part) |

So a garment answers to its key or any alias, exact first, then a
partial name in which each typed word starts a word of the key or an
alias (`coat` finds `Vantage all-weather greatcoat` by its alias;
`remove leather boots` finds `black leather combat boots`; a fragment
from inside a word, `irt` for `shirt`, finds nothing). An ordinal
picks among twins: `remove 2nd shirt`, `zip up second jacket`,
`undress corpse jacket-2` (only the dash form there, because `undress`
splits the target from the item at the last space). The pool is the
worn list itself, so an ordinal counts worn garments only; a worn
garment with no sleeves or no closure is still matched, and gets its
own refusal (`The X doesn't have anything to roll up.`). Several
matches without an ordinal take the first the matcher returns. The
presence gate applies: a garment the caller cannot perceive is not
found. The refusal texts (`You don't have 'X'.`, `You're not wearing
'X'.`, `<target> isn't wearing 'X'.`) are unchanged.

### Primary Commands

#### `wear <item>`
**Purpose**: Wear a clothing item from inventory  
**Syntax**: `wear <item>`  
**Examples**:
```
wear jacket
wear leather boots
wear 2nd shirt
```

#### `remove <item>` / `unwear <item>`
**Purpose**: Remove worn clothing item  
**Syntax**: `remove <item>` or `unwear <item>`  
**Examples**:
```
remove jacket
unwear boots
remove all
```

#### `dress <target> in <item>` / `undress <target> [<item>]`
**Purpose**: Put a garment from your inventory on someone or something, or take one garment or all of them off into your inventory  
**Syntax**: `dress <target> in <item>`, `undress <target>` or `undress <target> <item>`  
Works freely on a target who is unconscious, dead or restrained, and on a severed part. A conscious, free target must have trusted you for the `dress` class (see TRUST_AND_CONSENT_SPEC). Corpses and severed parts can be dressed and undressed.  
**Examples**:
```
dress corpse in jacket
undress corpse
undress corpse jacket-2
```

### Style Commands

#### `rollup <item>` / `unroll <item>`
**Purpose**: Roll sleeves or similar features up/down  
**Syntax**: `rollup <item>` or `unroll <item>`  
**Examples**:
```
rollup shirt
unroll shirt
rollup 2nd jacket
```

#### `zip <item>` / `unzip <item>`
**Purpose**: Close or open a worn garment's closure, zipped or buttoned, whichever it declares  
**Syntax**: `zip <item>`, `unzip <item>`, `button <item>` or `unbutton <item>`  
**Examples**:
```
zip jacket
unzip boots
zip up coat
```

All clothing verbs are refused while you are channelling. Removing armour with a stuck grenade warns you and the room, and the grenade stays on the armour. A single-use garment (issue clothing) tears apart as it comes off and is gone.

### Staff Commands
📋 UNBUILT (not decided). No staff clothing command exists; `dress` and `undress` are the player verbs. The sketch, following the longdesc pattern:
```
@wear <character> <item>     - Force wear item on character
@remove <character> <item>   - Force remove item from character
```

## Coverage and Visibility Logic

### Visibility Algorithm
1. **Get all worn clothing** in layer order (outer to inner)
2. **Build coverage map** of which locations are covered by which items
3. **For each body location** (in anatomical display order):
   - If covered by clothing: Add outermost clothing's worn_desc for that location. Each garment's description appears once, at the first location it shows on in display order; a left/right pair collapses into one line only when neither side is covered
   - If not covered: Add character's longdesc for that location (if set)
4. **Apply paragraph formatting**: Feed all descriptions into existing `_format_longdescs_with_paragraphs()` system
5. **Regional breaking**: Use existing anatomical region logic for smart paragraph breaks
6. **Character thresholds**: Apply same 400-character threshold rules as pure longdescs

### Layer Resolution
When multiple items cover the same location:
- **Highest layer wins**: Outer clothing descriptions override inner clothing
- **Partial visibility**: Inner layers can show through if outer layer has gaps
- **Smart layering**: System prevents logical conflicts (can't wear shirt over jacket)

### Coverage Validation
- **Anatomy checking** 📋 UNBUILT (not decided): wear does not check that the wearer has the locations the item covers
- **Layer conflicts**: Prevent wearing conflicting items in wrong order
- **Slot limits** 📋 UNBUILT (not decided): there is no per-location item count; the only limit is one garment per layer per location

## Data Storage

### Character Clothing Storage
```python
# In Character class
worn_items = AttributeProperty({}, category="clothing", autocreate=True)

# Structure:
{
    "chest": [jacket_obj, shirt_obj],  # Ordered by layer (outer first)
    "head": [hat_obj],
    "left_hand": [glove_obj],
    "right_hand": [glove_obj]
}
```

### Clothing Item Properties
```python
# On the base Item class (typeclasses/items.py)
coverage = AttributeProperty([], autocreate=True)            # Base body locations covered
worn_desc = AttributeProperty("", autocreate=True)           # Base description when worn
# layer is a property, not an AttributeProperty: a stored "layer" attribute wins;
# otherwise it is derived from the garment's name (world.style.derive_rung), else 1.
# Rungs run 0-5 (CLOTHING LAYERS in world/combat/constants.py); higher is further out.
style_properties = AttributeProperty({}, autocreate=True)    # Current style states
style_configs = AttributeProperty({}, autocreate=True)       # Style variations (optional)
```

## Integration Points

### With Longdesc System
- **Shared constants**: Both systems use `world/combat/constants.py` body locations
- **Visibility override**: `_get_visible_body_descriptions()` checks clothing coverage
- **Appearance assembly**: `return_appearance()` combines clothing and longdescs
- **Paragraph formatting**: Clothing descriptions participate in smart formatting

### With Inventory System
- **Wearable detection**: `item.is_wearable()` is true when the item has both `coverage` and `worn_desc`
- **Worn item display**: `inventory` lists worn items under a **Wearing:** heading
- **Style state display**: a worn item that is rolled up or unzipped shows it in brackets, for example `blue jeans (rolled up)`. Only those two are shown, and only when the garment also declares a plain state (empty `coverage_mod` and `desc_mod`) for that property (`CmdInventory._get_style_state_display` in `commands/CmdInventory.py`); states such as `loosened`, `hood_up` or `open` do not appear
- **Transfer rules**: Can't drop worn items, must remove first
- **Unified interface**: Players use standard `inventory` command to see all items including worn status

### With Combat System
- **Armor integration**: Clothing can provide damage reduction
- **Targeting modifiers**: covering a location does not make it harder to hit. Armour does change aim: an attacker with Intellect 3 or more is less likely to aim at a vital location carrying armour rating 4 or more, and more likely to aim at an unarmoured vital one (`select_hit_location` in `world/medical/utils.py`)
- **Equipment visibility**: Combat messages reflect what's visible vs covered

## Technical Implementation

### Clothing Detection Pattern
Instead of separate clothing classes, wearable items are identified by the presence of clothing-specific attributes:

```python
def is_wearable(self):            # Item method, typeclasses/items.py
    """Check if this item can be worn as clothing"""
    return bool(self.coverage) and bool(self.worn_desc)

# Whether an item is worn is asked of the wearer:
# character.is_item_worn(item)    (ClothingMixin, typeclasses/clothing_mixin.py)
```

All clothing functionality is implemented directly in the base `Item` class via AttributeProperty fields. Items become "clothing" simply by having `coverage` and `worn_desc` populated.

### Core Methods

#### Character Methods
```python
def wear_item(self, item):
    """Wear a clothing item, handling layer conflicts and coverage"""
    
def remove_item(self, item):
    """Remove worn clothing item"""
    
def get_worn_items(self, location=None):
    """Get worn items, optionally filtered by location"""
    
def is_location_covered(self, location):
    """Check if body location is covered by clothing"""
    
def get_coverage_description(self, location):
    """Get clothing description for covered location"""

def is_item_worn(self, item):
    """Check if a specific item is currently worn"""

def blocking_garments(self, item):
    """Worn garments that would stop item going on (empty list = it fits).
    wear_item enforces the same rule; souls consult it before choosing."""

def can_wear_now(self, item):
    """Whether item would go on over what is already worn"""
```

#### Item Methods (Clothing Functionality)
```python
def get_current_coverage(self):
    """Get coverage for current combination of style states with improved logic"""
    coverage = list(self.coverage)  # Start with base coverage
    
    if not self.style_configs or not self.style_properties:
        return coverage
    
    # Apply modifications from each active style property in deterministic order
    for property_name in sorted(self.style_properties.keys()):
        property_state = self.style_properties[property_name]
        
        if property_name in self.style_configs:
            property_config = self.style_configs[property_name]
            if property_state in property_config:
                state_config = property_config[property_state]
                coverage_mod = state_config.get("coverage_mod", [])
                
                # Apply coverage modifications
                for mod in coverage_mod:
                    if mod.startswith("+"):
                        # Add location if not already covered
                        location = mod[1:]
                        if location not in coverage:
                            coverage.append(location)
                    elif mod.startswith("-"):
                        # Remove location if currently covered
                        location = mod[1:]
                        if location in coverage:
                            coverage.remove(location)
    
    return coverage

def get_current_worn_desc(self):
    """Get worn description incorporating all active style states with complete replacement"""
    if not self.style_configs or not self.style_properties:
        return f"{self.worn_desc}." if self.worn_desc else ""
    
    # Check if any style property has a desc_mod - if so, use that INSTEAD of base worn_desc
    for property_name in sorted(self.style_properties.keys()):
        property_state = self.style_properties[property_name]
        
        if property_name in self.style_configs:
            property_config = self.style_configs[property_name]
            if property_state in property_config:
                state_config = property_config[property_state]
                desc_mod = state_config.get("desc_mod", "").strip()
                if desc_mod:
                    # desc_mod completely replaces worn_desc - incredibly powerful!
                    return f"{desc_mod}." if not desc_mod.endswith('.') else desc_mod
    
    # No active desc_mod found, use base worn_desc
    return f"{self.worn_desc}." if self.worn_desc else ""

def can_style_property_to(self, property_name, state_name):
    """Check if item can transition specific property to given state"""
    if property_name not in self.style_configs:
        return False
    if state_name not in self.style_configs[property_name]:
        return False
    
    # Membership only: any state the garment declares is allowed.
    # There is no meaningful-transition rule (see §Style Validation).
    return True

def set_style_property(self, property_name, state_name):
    """Set specific style property to given state with validation"""
    if not self.can_style_property_to(property_name, state_name):
        return False
    
    if not self.style_properties:
        self.style_properties = {}
    
    self.style_properties[property_name] = state_name

    # If the item is worn, re-seat its coverage on the wearer so worn_items
    # follows the new style. Done here so every caller (commands, souls,
    # the LLM style tool) gets it.
    wearer = self.location
    if wearer is not None and hasattr(wearer, "refresh_worn_coverage"):
        if wearer.is_item_worn(self):
            wearer.refresh_worn_coverage(self)
    return True

def get_style_property(self, property_name):
    """Get current state of specific style property"""
    return self.style_properties.get(property_name, "normal")

def get_available_style_properties(self):
    """Get all available style properties and their states"""
    return {prop: list(states.keys()) for prop, states in self.style_configs.items()}
```

### Modified Longdesc Integration
```python
def _get_visible_body_descriptions(self):
    """Get all visible descriptions, integrating clothing with existing longdesc system."""
    descriptions = []
    coverage_map = self._build_clothing_coverage_map()
    
    for location in LONGDESC_LOCATIONS:  # Use existing anatomical order
        if location in coverage_map:
            # Location covered by clothing - use outermost item's current worn_desc
            clothing_item = coverage_map[location]
            desc = clothing_item.get_current_worn_desc()  # Uses style-aware description
            if desc:
                descriptions.append(desc)
        else:
            # Location not covered - use character's longdesc if set
            desc = self.longdescs.get(location)
            if desc:
                descriptions.append(desc)
    
    return descriptions

def _build_clothing_coverage_map(self):
    """Map each body location to outermost covering clothing item."""
    coverage = {}
    worn_items = self.get_worn_clothing_by_layer()  # Outer to inner
    
    for item in worn_items:
        # Use current style state coverage, not base coverage
        current_coverage = item.get_current_coverage()
        for location in current_coverage:
            if location not in coverage:  # Only outermost matters for visibility
                coverage[location] = item
    
    return coverage

def return_appearance(self, looker, **kwargs):
    """Enhanced appearance integrating clothing with existing formatting and the {their}/{they} brace-token system."""
    # Get base header (name, description, etc.)
    string = self._get_appearance_header(looker, **kwargs)
    
    # Build combined clothing + longdesc descriptions with pronoun perspective
    body_descriptions = self._get_visible_body_descriptions(looker)
    
    if body_descriptions:
        # Feed into existing paragraph formatting system with brace-token processing
        formatted_body = self._format_longdescs_with_paragraphs(body_descriptions, looker)
        string += f"\n{formatted_body}"
    
    # Continue with rest of appearance (inventory, etc.)
    return string + self._get_appearance_footer(looker, **kwargs)

def _get_visible_body_descriptions(self, looker=None):
    """Get all visible descriptions with pronoun perspective handling."""
    descriptions = []
    coverage_map = self._build_clothing_coverage_map()
    
    for location in LONGDESC_LOCATIONS:
        if location in coverage_map:
            # Location covered by clothing - use current worn_desc with brace-token processing
            clothing_item = coverage_map[location]
            desc = clothing_item.get_current_worn_desc_with_perspective(looker, from_obj=self)
            if desc:
                descriptions.append(desc)
        else:
            # Location not covered - use character's longdesc
            desc = self.longdescs.get(location)
            if desc:
                # Process longdescs through the brace-token system too for consistency
                processed_desc = self._process_description_pronouns(desc, looker)
                descriptions.append(processed_desc)
    
    return descriptions
```

## Enhanced Item Methods

### Pronoun and Color Processing
```python
def get_current_worn_desc_with_perspective(self, looker=None, from_obj=None):
    """Worn text for one looker: style-aware, coloured, brace tokens resolved"""
    if not self.worn_desc:
        return ""
    desc = self._process_color_codes(self.get_current_worn_desc())
    if looker and from_obj and hasattr(from_obj, "_process_description_variables"):
        # The wearer resolves {their}/{they}/... by its APPARENT gender,
        # always in third person, even when the wearer looks at themselves.
        return from_obj._process_description_variables(
            desc, looker, force_third_person=True)
    return desc

def _process_color_codes(self, description):
    """Replace color placeholders with ANSI codes"""
    if not description:
        return description
        
    # Replace color placeholder
    if self.color and "{color}" in description:
        color_code = COLOR_DEFINITIONS.get(self.color, "")
        description = description.replace("{color}", color_code)
        
    return description
```

## Command Implementation

### Wear Command Logic
1. **Find item** in character's inventory
2. **Validate wearability**: refuse if the item lacks `coverage` or `worn_desc`, or is already worn. There is no anatomy check
3. **Check layer conflicts** with currently worn items: refuse if a worn garment at a shared location is on the same layer, or on a higher one (the new item would go under it)
4. **Refuse on a conflict**, naming the garments in the way. Nothing is removed for you
5. **Wear item** and update worn_items storage. A garment held in a hand leaves the hand only now, once the wear is going ahead
6. **Provide feedback**: "You put on a <item>." to the wearer, and a matching line to the room

### Remove Command Logic
1. **Find worn item** by name among the garments worn (or `remove all`)
2. **Warn** if a grenade is stuck to the garment; it stays stuck to it
3. **Validate removal**: refuse if a higher-layer garment over a shared location is still on ("Remove the <item> first.")
4. **Update worn_items** storage. The item never left the inventory, so nothing moves
5. **Run the garment's `at_removed` hook**: single-use issue clothing tears apart and is deleted, and the wearer gets the tear message instead of "You remove..."
6. **Provide feedback**: "You remove a <item>." to the wearer, and a matching line to the room

### Style Command Logic
1. **Find worn item** by name
2. **Determine style property** from command (rollup = adjustable, zip = closure, etc.)
3. **Validate style capability** (item has required style property configured)
4. **Check target state** (rollup sets to "rolled", zip sets to "zipped", etc.)
5. **Validate meaningful transition** (target state has both coverage_mod and desc_mod populated)
6. **Validate layer conflicts** (new combined coverage doesn't conflict with other worn items)
7. **Apply style change** (update specific property in style_properties)
8. **Provide feedback** with style change description

> **CORRECTED 2026-09-11 (#2445 item 8).** Steps 4-6 are not what runs. The
> shipped sequence is 1, 2, 3, then:
>
> 4. **Ask the GARMENT for the target state.** The command no longer names it.
>    `_target_style_state()` (`commands/CmdClothing.py`) walks the
>    command's intent list — `_ADJUST_TO`, `_RESTORE_TO`, `_CLOSE_TO`,
>    `_OPEN_TO` — and takes the first state the garment's own
>    `style_configs` declares; `button`/`unbutton` reverse their list so the
>    buttoned pair is preferred (`CmdZip.func`). So `rollup` can land on
>    `loosened` or `hood_up` and `button` on `buttoned`, which the hard-coded
>    four could never reach (#2742). Prose comes from the STATE, not the
>    command (`_STYLE_PROSE`).
> 5. **Refuse only if the state is already current** (`CmdRollUp.func`, `CmdZip.func`). There is
>    NO meaningful-transition test — see §Style Validation for why enforcing one
>    would break 35 of the 60 declared style states.
> 6. **No layer validation happens here.** Applying the change re-seats the
>    garment's coverage by layer instead (`Character.refresh_worn_coverage`,
>    `typeclasses/clothing_mixin.py`, called from `Item.set_style_property`), which is what lets the layer
>    underneath surface. §Style Validation records the gap this leaves for
>    states that ADD coverage.
>
> Steps 7 and 8 are correct, with one addition: the feedback is a paired
> self-message and `msg_room_identity` broadcast whose observer names are
> snapshotted BEFORE the change, because restyling can move the wearer's sdesc
> (`CmdRollUp.func`, `CmdZip.func` in `commands/CmdClothing.py`).

#### Command to Property Mapping
- `rollup`/`unroll` → `adjustable` property. `rollup` goes to the first of `rolled`, `loosened`, `hood_up` that the garment declares; `unroll` goes to `normal`, or else `hood_down` (could be sleeves, hood, cuffs, pant legs, a tie, etc.)
- `zip`/`unzip`/`button`/`unbutton` → `closure` property. Closing goes to `zipped` or `buttoned`, opening to `unzipped` or `open`; the button verbs try `buttoned`/`open` first (could be zipper, buttons, laces, etc.)
- Each command is fixed to one property; the target state is read from the garment's own `style_configs` (`_target_style_state` in `commands/CmdClothing.py`)
- Items can have one, both, or neither style property configured

#### Style Command Examples
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

A `look` shows one style description at a time: the first non-empty `desc_mod`, in property-name order, replaces the whole `worn_desc`, so two styles never combine in one sentence.

## Future Expansion Points

### Advanced Clothing Features
- **Custom tailoring**: `tailor` command for fitting clothes to unique anatomies
- **Clothing conditions**: Wear states (pristine, worn, tattered, destroyed)
- **Seasonal clothing**: Weather-appropriate clothing bonuses/penalties
- **Cultural clothing**: Faction or region-specific clothing styles

### Equipment Integration
- **Armor system**: Damage reduction and combat modifiers
- **Magical clothing**: Enchantments and special properties
- **Equipment sets**: Bonus effects for wearing complete outfits
- **Ceremonial gear**: Special occasion clothing with social bonuses

### Economic Integration
- **Tailoring profession**: Player-crafted clothing
- **Clothing shops**: NPC vendors with seasonal inventories
- **Repair system**: Clothing maintenance and restoration
- **Fashion system**: Social status and appearance ratings

## Testing Requirements

### Unit Tests ✅ COMPLETED
- ✅ **Command parsing and validation** - wear, remove commands working
- ✅ **Coverage calculation and layer resolution** - Multi-item layering tested
- ✅ **Clothing item creation and property validation** - Style system functional
- ✅ **Integration with character appearance system** - Appearance display working

### Integration Tests ✅ COMPLETED  
- ✅ **Longdesc + clothing visibility interaction** - Coverage hiding longdescs properly
- ✅ **Multi-layer clothing combinations** - Layer resolution working
- ✅ **Third-party clothing** - `dress`/`undress`, consent-gated player verbs (no staff-only clothing verb exists)
- ✅ **Inventory integration with worn item handling** - Worn status display working

### User Acceptance Tests ✅ COMPLETED
- Complete wear/remove workflow validation
- Appearance display with mixed clothing and longdescs
- Layer conflict resolution and user feedback
- Performance with multiple clothing items

## Implementation Checklist

### Phase 1: Core Infrastructure ✅ COMPLETED
- [x] Add clothing attributes to base `Item` class in `typeclasses/items.py`
- [x] Add clothing constants to `world/combat/constants.py`
- [x] Implement Character methods for wearing/removing items
- [x] Create basic `wear` and `remove` commands
- [x] Implement dynamic styling system (style_properties, style_configs)
- [x] Create style commands (`rollup`, `unroll`, `zip`, `unzip`)

### Phase 2: Appearance Integration ✅ COMPLETED
- [x] Modify `_get_visible_body_descriptions()` to check clothing coverage
- [x] Implement clothing description display in appearance
- [x] Add layer resolution logic for overlapping items
- [x] Test appearance assembly with clothing + longdescs

### Phase 3: Advanced Features 📋 PENDING
- [x] Layer conflict detection (`ClothingMixin.wear_item`, `remove_item`, `blocking_garments`): a conflict is refused, never resolved for the player
- [ ] Staff targeting for clothing management (no staff-only clothing verb exists; third-party clothing is the consent-gated `dress`/`undress`)
- [ ] Comprehensive error handling and user feedback
- [ ] Performance optimization and testing

## Design Summary

### Key Design Decisions

**Multi-Property Style System**: Items can have multiple independent style properties (`adjustable`, `closure`) that combine to create rich variation. A jacket can be both rolled up and unzipped simultaneously, creating four distinct states. Coverage combines across properties; descriptions do not: the first non-empty `desc_mod`, in property-name order, replaces the whole `worn_desc`.

**Meaningful Transition Validation**: All style commands require both coverage changes AND description changes. This ensures every player interaction has both functional and visual impact, preventing meaningless commands.

> **CORRECTED 2026-09-11 (#2445 item 8).** This decision was never implemented,
> and the shipped wardrobe rules it out. `can_style_property_to()`
> (`typeclasses/items.py`) admits any state the garment declares —
> *"the validation is structural, not functional"* — and 35 of the 60 style
> states in `world/prototypes.py` would be refused if the rule were enforced,
> spread across all 24 prototypes that declare `style_configs` and taking every
> restore-to-`normal` state with them. The `"That wouldn't change anything
> about the ..."` refusal the commands still carry
> (`CmdRollUp.func`, `CmdZip.func` in `commands/CmdClothing.py`) is therefore unreachable.
>
> The decision that DID ship is close in spirit and worth keeping in mind: a
> style state must be **declared by the garment** to be reachable, and the
> commands read the garment rather than naming states themselves (#2742). The
> paragraph above is preserved because the impulse behind it — no command should
> be a no-op — still governs the authoring guidance, and the commands do refuse
> a change to the state a garment is already in; it simply is not enforced as
> the both-populated rule this paragraph describes. See §Style Validation for
> the full correction.

**Generic Property Naming**: The `adjustable` property covers any rollup/unroll functionality (sleeves, hoods, cuffs, pant legs), making the system flexible and extensible without requiring specific properties for each adjustment type.

**Defensive Command Logic**: Before a change, the style commands check that the garment has the property, that it declares a state for this command, and that it is not already in that state, and say which check failed. There is no meaningful-transition check.

**Combinatorial Coverage Calculation**: Base coverage is modified by all active style properties in deterministic order, allowing complex layering effects and partial coverage scenarios.

**Integration with Longdesc Foundation**: Clothing descriptions participate in the same paragraph formatting system as longdescs, ensuring consistent appearance assembly and leveraging existing smart breaking logic.

## Success Criteria

### Functional Requirements
- Players can wear and remove clothing items seamlessly
- Clothing descriptions appear in character appearance appropriately
- Covered body part longdescs are properly hidden
- Layer conflicts are resolved intuitively
- Staff can manage clothing on other characters

### Integration Requirements
- Clothing system works harmoniously with existing longdesc system
- Character appearance assembly handles mixed clothing and longdescs
- Performance impact remains minimal
- Existing character functionality is preserved

### User Experience Requirements
- Intuitive command interface following established patterns
- Clear feedback on wear/remove actions and conflicts
- Logical layering behavior that matches real-world expectations
- Seamless integration with existing appearance and description systems

---

## Enhanced Prototype Examples

### Developer Hoodie with brace-token and Color Integration
```python
DEVELOPER_HOODIE = {
    "prototype_key": "DEVELOPER_HOODIE",
    "key": "black developer hoodie",
    "aliases": ["hoodie", "sweatshirt"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A menacing black developer hoodie with command-line text across the chest.",
    
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "A menacing {color}black|n developer hoodie that clings to their frame like digital shadow incarnate, green command-line text pulsing ominously across their chest while forbidden terminal incantations glow with quiet menace"),
        ("coverage", ["chest", "back", "abdomen", "left_arm", "right_arm"]),
        ("layer", 3),
        ("color", "black"),
        ("material", "cotton"),
        
        ("style_configs", {
            "adjustable": {
                "normal": {
                    "coverage_mod": [],
                    "desc_mod": ""
                },
                "rolled": {
                    "coverage_mod": ["+head"],
                    "desc_mod": "A menacing {color}black|n developer hoodie with the hood pulled up like digital shadow incarnate, casting their face into mysterious darkness while green command-line text pulses ominously across their chest"
                }
            },
            "closure": {
                "zipped": {
                    "coverage_mod": [],
                    "desc_mod": "A menacing {color}black|n developer hoodie zipped tight against the digital cold, LED matrix patterns cascading across the fabric like endless streams of compiled consciousness"
                },
                "unzipped": {
                    "coverage_mod": ["-chest"],
                    "desc_mod": "A menacing {color}black|n developer hoodie hanging open in calculated carelessness, revealing whatever lies beneath while their forbidden command-line incantations pulse with green malevolence"
                }
            }
        }),
        
        ("style_properties", {
            "adjustable": "normal",
            "closure": "unzipped"
        })
    ],
}
```

### Enhanced Blue Jeans with Pronoun Integration
```python
BLUE_JEANS = {
    "prototype_key": "BLUE_JEANS", 
    "key": "blue jeans",
    "aliases": ["jeans", "pants", "denim"],
    "typeclass": "typeclasses.items.Item",
    "desc": "Classic medium-wash blue jeans with a comfortable fit.",
    
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "Battle-tested {color}denim|n jeans that cling to their form with urban authority, their faded indigo surface scarred by countless encounters with concrete and circumstance"),
        ("coverage", ["groin", "left_thigh", "right_thigh", "left_shin", "right_shin"]),
        ("layer", 2),
        ("color", "blue"),
        ("material", "denim"),
        
        ("style_configs", {
            "adjustable": {
                "normal": {
                    "coverage_mod": [],
                    "desc_mod": ""
                },
                "rolled": {
                    "coverage_mod": ["-left_shin", "-right_shin"],
                    "desc_mod": "Battle-tested {color}denim|n jeans with cuffs deliberately rolled up to mid-calf in street-smart defiance, exposing their scarred ankles and the promise of swift movement"
                }
            },
            "closure": {
                "zipped": {
                    "coverage_mod": [],
                    "desc_mod": ""
                },
                "unzipped": {
                    "coverage_mod": ["-groin"],
                    "desc_mod": "Battle-tested {color}denim|n jeans hanging loose with dangerous nonchalance, their undone fly creating a calculated statement of rebellion"
                }
            }
        }),
        
        ("style_properties", {
            "adjustable": "normal", 
            "closure": "zipped"
        })
    ],
}
```

### Combat Boots with Color and Perspective
```python
COMBAT_BOOTS = {
    "prototype_key": "COMBAT_BOOTS",
    "key": "black leather combat boots", 
    "aliases": ["boots", "combat boots"],
    "typeclass": "typeclasses.items.Item",
    "desc": "Heavy-duty black leather combat boots with steel-reinforced toes.",
    
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "Imposing {color}black leather|n combat boots laced with military precision, their steel-reinforced toes and deep-tread soles speaking of their owner's serious intent while weathered leather tells stories of urban warfare"),
        ("coverage", ["left_foot", "right_foot", "left_shin", "right_shin"]),
        ("layer", 2),
        ("color", "black"),
        ("material", "leather"),
        
        ("style_configs", {
            "closure": {
                "zipped": {  # Laced tight
                    "coverage_mod": [],
                    "desc_mod": ""
                },
                "unzipped": {  # Laces loose
                    "coverage_mod": ["-left_shin", "-right_shin"],
                    "desc_mod": "Imposing {color}black leather|n combat boots with speed-laces hanging in deliberate disarray, their unlaced tongues flopping open to reveal glimpses of tactical readiness beneath the facade of casual indifference"
                }
            }
        }),
        
        ("style_properties", {
            "closure": "zipped"
        })
    ],
}
```

## Implementation Status: Enhanced Features

### Phase 1: Perspective-Aware Descriptions ✅ COMPLETED (Without $pron())
- [x] Base clothing descriptions use `{their}`/`{they}` brace tokens, resolved per looker by the wearer's `_process_description_variables`
- [x] Style descriptions **implemented** without `$pron()` tags (not available in prototypes)
- [x] Character appearance system **implemented** with proper perspective handling in methods
- [x] `get_current_worn_desc_with_perspective()` on Item is what `_get_visible_body_descriptions` uses for each visible garment's text
- [x] Prototype worn descriptions and style `desc_mod`s use the same brace tokens; `$pron()` is not used

### Phase 2: Color & Material System Implementation ✅
- [x] `color` and `material` AttributeProperty added to Item class
- [x] Color placeholder processing in `_process_color_codes()` method
- [x] `get_current_worn_desc_with_perspective()` method enhancement
- [x] Color-enhanced prototype examples in `world/prototypes.py`
- [x] ANSI color constants integration
- [x] Material attribute ready for future armor/crafting systems

### Phase 3: Testing & Refinement 🔄
- [ ] Test pronoun perspective with different character genders
- [ ] Test color placeholder replacement in descriptions
- [ ] Verify color + pronoun integration works together
- [ ] Update existing clothing prototypes with enhanced features
- [ ] Performance testing with complex styled + colored clothing
- [ ] Validate material attribute for future armor/crafting integration

---

**Document Status**: Enhanced with `{their}`/`{they}` brace-token integration, streamlined single-color system, and material attribute for future extensibility
