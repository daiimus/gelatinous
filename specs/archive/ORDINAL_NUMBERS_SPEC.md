# Ordinal Number Support - Implementation Complete

> **Status:** 🗄 Historical — completion record of a shipped feature (natural-language ordinal multimatch). Kept for context.

## Overview
Successfully implemented natural language ordinal number support for multimatch disambiguation in Evennia commands. Players can now use intuitive commands like "get 1st mushroom" instead of "get mushroom-1".

## Features Implemented

### Numeric Ordinals
- 1st, 2nd, 3rd, 4th, 5th, etc.
- Supports any numeric ordinal (21st, 22nd, 23rd, etc.)

### Written Ordinals  
- first, second, third, fourth, fifth, sixth, seventh, eighth, ninth, tenth

### Universal Support
Works with all commands that use Evennia's search system:
- `look first can` (same as `look can-1`)
- `get 2nd mushroom` (same as `get mushroom-2`) 
- `wield third sword` (same as `wield sword-3`)
- `unwield 1st axe` (same as `unwield axe-1`)

## Technical Implementation

### Core Changes

1. **typeclasses/objects.py** - ObjectParent Enhancement
   - Added `ORDINAL_WORDS` dictionary for written ordinals
   - Added `ORDINAL_REGEX` for pattern matching
   - Override `get_search_query_replacement()` method
   - Automatic conversion: "1st mushroom" → "mushroom-1"

2. **commands/CmdInventory.py** - Search Method Updates
   - Updated `_find_item_in_inventory()` to use `caller.search()`
   - Updated `CmdUnwield.func()` to use standard search system
   - Now benefits from ObjectParent ordinal conversion

3. **server/conf/at_search.py** - Enhanced Search Handler
   - Custom search result handler with ordinal-aware messaging
   - Better multimatch error messages for both formats

4. **server/conf/settings.py** - Configuration
   - `SEARCH_AT_RESULT` setting points to custom handler

### Key Technical Details

- **Regex Pattern**: `^(?P<ordinal>(?:\d+(?:st|nd|rd|th)|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth))\s+(?P<rest>.+)$`
- **Conversion Logic**: Extracts ordinal and converts to Evennia's dash-number format
- **Integration Point**: ObjectParent mixin ensures universal application
- **Backward Compatibility**: Existing dash-number format continues to work

> **Note (2026-09-12):** the Regex Pattern above does not exist in the
> code and never did — no combined numeric-or-word pattern with
> `ordinal`/`rest` groups appears in this repo's history, including the
> abandoned `at_search` version. The shipped mechanism is two separate
> pieces in `ObjectParent`:
> 1. `ORDINAL_REGEX = re.compile(r'(?P<number>\d+)(?:st|nd|rd|th)\s+(?P<name>.*)', re.I)`
>    — numeric only, groups named `number`/`name`, no `^`/`$` anchors
>    (`.match` supplies the start anchor).
> 2. A plain `searchdata.split()` with a dict lookup of the first word
>    in `ORDINAL_WORDS`. Word ordinals are not handled by any regex.
>
> **Conversion Logic** and **Backward Compatibility** hold: the two
> branches return `f"{name}-{number}"` and
> `f"{remaining_words}-{number}"` respectively, which is exactly what
> Evennia 6.1's default
> `SEARCH_MULTIMATCH_REGEX = r"^(?P<name>.*?)-(?P<number>[0-9]+)(?P<args>(?:\s.*)?)$"`
> consumes, and this repo does not override that setting. A query
> already in `can-1` form matches neither ordinal branch, so it passes
> through untouched. The split is candidate-aware in Evennia
> (`evennia/objects/manager.py`, `search_object`), which is why the
> `candidates=`-scoped commands below still get ordinals.
>
> **Integration Point** is now only part of the story. Character
> targeting was rerouted by the identity system: the `Character.search`
> override in `typeclasses/characters.py` runs its own ordinal parser,
> `world.search.parse_ordinal`, before this hook is ever reached (this
> hook still handles the item/exit fallback, because the override
> passes the ORIGINAL query down to `super().search`). See the census
> of parsers in the Benefits note below, and
> `specs/IDENTITY_RECOGNITION_SPEC.md` §Target Resolution.

## Testing Results

All test cases pass successfully:

> **Note (2026-09-12):** this records a manual session, not a suite.
> The feature's only test file, `test_ordinals.py`, was committed empty
> (0 bytes) in `bce34765` and deleted in `48bf0963` ("86'd test") four
> minutes before this document was written. Nothing in the repo today
> exercises `ObjectParent.get_search_query_replacement`. The ordinal
> tests that do exist cover the *other* implementations:
> `world/tests/test_identity_search.py` (`parse_ordinal`),
> `world/tests/test_emote.py` (`TestOrdinalCharRefsInEmotes`), and
> `world/tests/test_consumption_rendering.py`
> (`TestOrdinalItemParse`, `drink 2nd mug`);
> `test_the_ordinal_constraint_is_written_down` in
> `world/tests/test_the_vestigial_sweep.py` pins only the comment above
> `ORDINAL_WORDS`, not the behaviour.
>
> Checks 1, 2, 4 and 5 were re-verified by code reading on this date
> and still hold. **Check 3 does not.** A non-ordinal search whose
> FIRST word happens to be an ordinal word IS changed: `get first aid
> kit` is rewritten to a search for `aid kit-1`. See the #2473 note
> under Benefits.
- ✅ Numeric ordinals (1st, 2nd, 3rd, 21st, 22nd, 23rd)
- ✅ Written ordinals (first, second, third, fourth, fifth, tenth)  
- ✅ Non-ordinal searches remain unchanged
- ✅ Integration with look, get, wield, unwield commands
- ✅ Standard Evennia multimatch behavior preserved

## Benefits

1. **Natural Language**: More intuitive command syntax
2. **Universal Application**: Works with all search-based commands
3. **Backward Compatible**: Doesn't break existing functionality
4. **Consistent**: Same ordinal support across all game systems
5. **Extensible**: Easy to add more ordinal words if needed

> **Note (2026-09-12):** benefit 3 has one permanent exception, found
> later and accepted by owner ruling under #2473 (closed as
> *documented*, not fixed). Because the FIRST word of a query is
> unconditionally consumed as a positional index, an item whose own
> name begins with an ordinal word can never be found by its name:
> `get first aid kit` becomes a search for `aid kit-1`. The constraint
> is written up in the comment above `ORDINAL_WORDS` in
> `typeclasses/objects.py` and pinned by
> `test_the_ordinal_constraint_is_written_down` in
> `world/tests/test_the_vestigial_sweep.py`. No prototype in the game
> has such a key or alias today (re-verified 2026-09-12 by scanning
> every prototype `key` and `aliases` value in `world/prototypes.py`);
> name around it, or drop the offending word from `ORDINAL_WORDS`.
>
> Benefit 4 was true when written and is now wrong: ordinals are parsed
> in FOUR independent places with different coverage.
> - `ObjectParent.get_search_query_replacement`
>   (`typeclasses/objects.py`) — items and exits. `first`–`tenth` plus
>   any numeric ordinal. No article strip, no dotted form.
> - `world.search.parse_ordinal` (`world/search.py`) — character
>   identity targeting. Also accepts Evennia's dotted `1.man` form, and
>   via `parse_target_query` strips a leading article first (#2661).
> - `_find_ordinal_char_ref_spans` (`world/emote.py`) — character
>   references inside emote text. **Numeric ordinals only**; word
>   ordinals are refused there deliberately as too ambiguous in
>   free-form prose.
> - `commands/CmdConsumption.py` — not a parser: it reads
>   `caller.ORDINAL_WORDS` only to keep an ordinal glued to its noun
>   before splitting item from target (#2458).
>
> One visible consequence: `get the 1st can` finds nothing while
> `look the 2nd man` works, because #2661 fixed the article order on
> the identity path only. That is unfixed, not accepted — no issue was
> open for the object-side gap as of this date.
>
> Benefit 5 also carries the #2473 cost: each word added to
> `ORDINAL_WORDS` makes one more English word unusable as the first
> word of an item name.

## Usage Examples

```
> get 1st mushroom        # Gets the first mushroom in your inventory
> wield second sword      # Wields the second sword you're carrying  
> look third can          # Examines the third aerosol can in the room
> unwield 2nd axe         # Unwields the second axe you're holding
```

The system seamlessly converts these natural language commands to Evennia's standard multimatch format internally while maintaining full compatibility with existing commands and systems.

> **Note (2026-09-12):** the first example's comment is wrong about
> scope. `get` searches the ROOM, not your inventory — `CmdGet.func`
> calls `_find_item_in_room`, whose candidates are built from
> `caller.location.contents` (`commands/CmdInventory.py`). So
> `get 1st mushroom` takes the first mushroom **on the ground**. The
> other three examples are right: `wield` resolves through
> `_find_item_in_inventory` over `caller.contents`, `unwield` over the
> items in hand, and `look` is Evennia's default command, which reaches
> this hook through `caller.search()`.
>
> Two input forms silently fail for objects, and both are unfixed
> rather than accepted: a leading article breaks the conversion
> (`get the 1st can` finds nothing, while `look the 2nd man` works —
> the identity parser strips articles first, this one never does), and
> Evennia's dotted form (`1.can`) is understood only on the identity
> path. Routing this hook through `world.search.strip_leading_article`
> before its two ordinal attempts would close the first; no issue was
> filed for either as of this date.
