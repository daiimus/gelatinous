# Enhanced Look Command System Specification

> **Status:** 🚧 **PARTIAL** — features 1-12 shipped; **§13 Ambient Message System not built**. ~~Verified 2026-08-02~~ **re-checked 2026-09-11: 28 claim(s) false, annotated inline**.
>
> **⚠ Spec-vs-code corrections — the following claims were FALSE when audited:**
> - The header's "Implementation Status: COMPLETED ✅" contradicted its own "12/13 Features Complete". 12/13 is correct.
> - **§Sensory Focus Commands (`listen`, `smell`, `feel`) do not exist and will not be built** (owner decision, 2026-08-03): `look` is the time-tested MUD verb and already surfaces every sense layer the room carries, perception-gated. Separate per-sense verbs would be syntax for its own sake. The section is retained as history, not as a plan.
> - §13 Ambient Message System is confirmed unbuilt — no ticker or interval script emits atmospheric messages; the pools are pulled at `look` time only.
> - Crowd-aware directional look **is** built (`Exit._get_exit_character_display` in `typeclasses/exits.py`), contrary to earlier notes.

## Overview

The enhanced look command system assembles rich, dynamic environmental descriptions through component-based sensory integration. The system builds upon the existing `return_appearance` method, combining sensory categories with modular description components that automatically assemble into cohesive room narratives.

## Implementation Progress: 12/13 Features Complete (92%)

**✅ Completed Systems (12):**
1. Character Placement System
2. Room Section Spacing  
3. Natural Language Items
4. Smart Exit System
5. Room AttributeProperty System
6. Exit Display Enhancements
7. @integrate Object System
8. Weather System (228 combinations)
9. Crowd System (4 intensity levels)
10. Adjacent Room Character Visibility
11. Exit Examination Enhancement
12. Directional Look Character Display Enhancement

**✅ All Core Features Complete**

## Implementation Status: COMPLETED ✅

**All Features Implemented (✅):**

> **CORRECTION 2026-09-11:** as the header note says, 12/13 is the right figure — §13 is
> unbuilt. This heading, "✅ All Core Features Complete" above it, "Implementation Complete ✅"
> below, and "Implementation Status: COMPLETED ✅" are four restatements of the same
> overclaim; the header note names only the last of them.

### 1. Character Placement System
- **Natural Language Positioning**: Implemented `@temp_place`, `@look_place`, `@override_place` commands
  - **CORRECTION 2026-09-11: there is no `@override_place` command, and no sign there ever was.**
    Two of the three are commands — `CmdLookPlace` and `CmdTempPlace`
    (`commands/CmdCharacter.py`; registered in `commands/default_cmdsets.py`).
    `override_place` is an `AttributeProperty` (`typeclasses/characters.py`, category
    `description`) that only the game writes: aiming and showdown
    (`commands/combat/special_actions.py`, `commands/combat/core_actions.py`; cleared on
    movement and when the aim stops), combat entry ("locked in combat.",
    `world/combat/utils.py`), channeled acts (`world/channeled.py`), unconsciousness and
    death (`typeclasses/characters.py`) and one admin cleanup (`commands/CmdAdmin.py`). It
    is the top of the stored placement hierarchy, not a player-settable field. The stealth
    "lurking" line is not stored: `Room.get_display_characters` applies it at render time,
    above `override_place`. The hierarchy bullet below is correct.
- **Hierarchy**: `override_place` > `temp_place` > `look_place` > "standing here." (`Room.get_display_characters`). Above all of them, a hidden character who is still seen reads with the stealth lurking line (`world.stealth.lurk_placement`: "lurking in the shadows.", or a nervous face in the crowd when the room is busy). `{aim_target}` in a placement becomes the target's name, or "aiming carefully." when the target is gone. Characters with the same placement share one sentence.

**Example Implementation:**

**Component Assembly Example:**
```
Base Room: "Large intersection where Sinn crosses Knife"
+ ✅ Weather Integration: "cool evening air carries hints of exhaust and distant cooking, while the soft murmur of traffic drifts from the main thoroughfare"
+ Crowd (moderate): "foot traffic starting to get heavy but personal space"
+ @integrate Vehicles: "bullet-ridden vehicles pass through on drive-bys" (📋 UNBUILT (no issue): no vehicle objects exist)
+ @integrate Graffiti: "walls daubed with colorful graffiti"
+ Traditional Objects: "You see a flyer [Nyrek the Unwired]"
+ Smart Exits: "street to the south/west/east" (intersection detected)
= Final assembled description with integrated weather system
```

**Actual Weather System Output:**
```
Braddock Avenue
Tall, grim-faced tenement buildings flank the way here, seeming to lean in 
towards each other and restricting overhead light. |wCool evening air carries 
hints of exhaust and distant cooking, while the soft murmur of traffic drifts 
from the main thoroughfare.|n

Kathy Cohen-Gold is doing a handstand. Nick Kramer is in a full-split.

The street continues to the west (w) and east (e).
```

**Weather Integration Details:**
- Weather text appears with |w (bold white) formatting in room description
- Weather shows only in rooms with `outside` set. Each look shows one line from each of two different senses the looker can perceive (three if their perception is reduced), drawn at random from the current weather+time pool. Rooms whose type has an entry in `ROOM_TYPE_POOLS` (`fire escape` is the one entry) get that type's lines mixed into the draw (`WeatherSystem.get_weather_contributions`)
- Appended to the first line of the room description, after any @integrate content
- All **19** weather types covered
  - **CORRECTION 2026-09-11, two errors in one line.** (1) The count is **19**, not 17 —
    `WEATHER_INTENSITY` (`world/weather/weather_messages.py:37-64`) defines 19 keys: 3 mild,
    5 moderate, 9 intense, 2 extreme. That is also what §8's own "Comprehensive Coverage"
    bullet and §8b say; every "17 weather types" elsewhere in this spec is stale.
    (2) "intensity-appropriate message complexity" is **not true of the shipped pools** —
    measured, line length does not vary with intensity at all (mild 8.58 words mean,
    moderate 8.34, intense 8.32, extreme 8.65; longest line in the whole corpus 13 words).
    See the correction under **Weather Types Implemented** below.
  - *(Editorial, 2026-09-11: this line used to end in the orphaned tail of §1's
    "Hierarchy" bullet — `verride_place` > `@temp_place` > ...` — the other half of a
    mis-paste. The tail has been restored to its own bullet under §1; no text was lost.)*
- **Character Commands**: `CmdLookPlace` and `CmdTempPlace` classes in `commands/CmdCharacter.py`
- **Natural Language Output**: Characters show with placement descriptions like "Kathy Cohen-Gold is doing a handstand. Nick Kramer is in a full-split."
- **Names**: names in these examples assume the looker knows the people. A stranger is shown by short description ("A lanky man in a Black Trenchcoat is doing a handstand."), from `Character.get_display_name`

### 2. Room Section Spacing  
- **Proper Line Breaks**: Added conditional spacing between room description, items, characters, and exits
- **Template Integration**: Modified `appearance_template` and `format_appearance()` method
- **Clean Visual Flow**: Empty sections don't create extra spacing

### 3. Natural Language Items
- **Grammar-Aware Display**: "You see a chainsaw, frag grenade, and baseball bat" with proper conjunctions
  - **CORRECTION 2026-09-11:** the renderer articles *every* singleton, so the actual output is
    "You see a chainsaw, a frag grenade, and a baseball bat." (`Room.get_display_things`).
    Two behaviours this section never documented: identical items stack behind spelled-out
    quantity words up to fifty, and above fifty a profane euphemism is chosen at
    random ("a shitload of ...").
- **Smart Pluralization**: Handles single items vs. multiple items correctly
- **Integration**: Modified `get_display_things()` method for natural language output

### 4. Smart Exit System  
- **Room Type Detection**: Implemented `room.type` AttributeProperty with autocreate
- **Intelligent Grouping**: Groups exits by destination type and street analysis
- **Natural Language**: "The street continues to the west (w) and east (e)" instead of repetitive descriptions
- **Destination Analysis**: Analyzes destination room exit counts to determine street types (dead-end, continues, intersection)
- **Combined Descriptions**: Groups similar exit types together for cleaner output

### 5. Room AttributeProperty System
- **Type Attribute**: `room.type` for room classification (`street`, `corner store`, etc.)
- **Sky Room Detection**: `room.is_sky_room` for aerial navigation
- **Custom Descriptions**: `room.desc` AttributeProperty for rich room descriptions
- **Outside**: `room.outside` – weather shows only in rooms with it set, and the exit look's weather framing needs it on this room or the destination
- **Sense layers**: `room.sense_descs` – optional auditory/olfactory/tactile/atmospheric layers after the visual `desc`, each shown only to a looker with that sense
- **Crowd base**: `room.crowd_base_level` – the crowd base; 0 means no crowd line
- **Auto-Creation**: All attributes use `autocreate=True` for seamless integration

### 6. Exit Display Enhancements
- **Alias Integration**: Shows the exit's key and its shortest alias in parentheses: "north (n)", "elevator (in)" (`Room.get_custom_exit_display`)
- **Up and down are not compass points (#3755, 2026-10-23).** Every footer sentence put the
  exit key after "to the", so a vertical exit read "The fire escape continues to the up (u)
  and down (d)." (Brackett fire escape, Halcyon companionways) and, once #3753 let the glance
  into the Greenhaus towers, "You see a lone figure to the up." Owner: "Up and down are very
  common exit names - so we should probably account for them." Every group now renders
  through `Room.format_exit_phrases`: compass and named exits behind one "to the", and exits
  keyed `up`/`down` (`typeclasses.rooms.VERTICAL_EXITS`) as a phrase of their own with no
  preposition, "up"/"down" in a "continues" sentence and "above"/"below" in a "there is"
  sentence or the glance:

  | sentence | reads |
  |---|---|
  | continues | The fire escape continues up (u) and down (d). |
  | continues, mixed | The tenement continues to the southeast (se). It continues up (u) and down (d). |
  | there is | There is a fire escape above (u). |
  | there are | There are exits above (u) and below (d). |
  | there is, mixed | There is an exit to the north (n). There are exits above (u) and below (d). |
  | glance | You see a lone figure above. |
  | glance, crowd | You see a crowd below. |

  A group holding both kinds gets two sentences, compass first (`Room.format_exit_phrases`
  returns one phrase per kind; `continues_sentences` writes "It continues ..." for the
  second), so the "and" never doubles. The review of PR #3756 found the joined form
  ("to the southeast (se), and up (u) and down (d)") in 42 live rooms, the 15 Brackett
  stairwells and 27 Greenhaus stair cores; owner, shown both: "That's fine" to the split.
  The exit's key decides, so `hatch`, `breach` and
  `drop` (the three live exits that merely answer to `down`) stay named exits. Named exits
  ("to the window", "to the 3B") keep "to the" by the same ruling: "The others can be put
  off for now. I don't take issue with them." Tests:
  `world/tests/test_up_and_down_are_not_compass_points.py`.
- **Edge/Gap Support**: Integrates edges and gaps into natural language flow
- **Fallback Handling**: Generic exit format for unknown destination types
- **Bug Fixes**: Resolved AliasHandler indexing issues with proper `.all()` method usage

### 7. @integrate Object System
- **Sensory Integration**: Objects contribute to room description via sensory categories
- **Priority System**: Integration priority controls display order (lower = first)
- **Flying Object Integration**: Flying objects automatically integrated with priority
- **Sensory Contributions**: Objects use `sensory_contributions` dict for rich integration
- **Fallback System**: `integration_desc` and `integration_fallback` for simple integration
- **Which objects**: only Items, graffiti, blood pools, shop containers and furniture can integrate, by setting the `integrate` attribute (`db.integrate`); there is no `@integrate` command, and any other object with `integrate` set stays in the object list. An object may define `refresh_integration_desc()` to update its line before it is read (blood pools age this way). The last fallback is "{key} is here".
- **Enhanced Object Display**: Objects woven into narrative instead of listed separately

### 8. Directional Look Character Display Enhancement
- **Crowd-Aware Descriptions**: Character displays adapt based on destination room crowd levels
- **Atmospheric Integration**: Weather context and stylized descriptions matching noir aesthetic
- **Dynamic Presentation**: Characters presented with crowd context rather than generic format
- **Natural Directional Flow**: Proper directional phrasing with crowd-appropriate language
- **Scaling Format**: Graceful handling of any number of characters with proper grammar

## Current Implementation

**Existing Features:**
- Basic room description with name and desc
- ✅ **Enhanced Character Display**: Natural language character positioning via AttributeProperty system
- ✅ **Smart Exit Categorization**: Intelligent destination analysis and grouping
- ✅ **Natural Language Items**: Grammar-aware item display with conjunctions  
- ✅ **Section Spacing**: Proper line breaks between room sections
- Flying object integration for throw mechanics
- ✅ **Room AttributeProperties**: type, is_sky_room, desc with autocreate
- Sky room filtering for exit display

**Current `return_appearance` Method:**
- Uses appearance template with header/name/desc/characters/things/footer
- ✅ **Enhanced Character Display**: Uses `get_display_characters()` for natural language positioning
- ✅ **Natural Language Items**: Uses `get_display_things()` for grammar-aware display
- ✅ **Conditional Spacing**: `format_appearance()` adds proper line breaks between sections
- ✅ **@integrate Object System**: Uses `get_integrated_objects_content()` to weave objects into room descriptions
- Adds flying objects during throw mechanics
- ✅ **Smart Exit Display**: Delegates to `get_custom_exit_display()` with intelligent grouping
- Filters sky room exits unless they're edges/gaps
- ✅ **Weather System Integration**: Integrates weather directly into room description via `weather_system.get_weather_contributions()`

**Implementation Complete ✅**

### 8. Weather System ✅
- ✅ **Dynamic Message Pools**: Weather-based sensory descriptions using combat message architecture
- ✅ **Environmental Integration**: Weather effects integrated into room descriptions via `return_appearance`
- ✅ **Sensory Categories**: Visual, auditory, olfactory, tactile, atmospheric weather contributions
- ✅ **Intensity-Based Messages**: Weather types scaled by intensity (mild/moderate/intense/extreme)
  - **CORRECTION 2026-09-11: the tier vocabulary shipped, the scaling did not.**
    `WEATHER_INTENSITY` assigns every weather a tier, but nothing reads that tier to shape
    a message; measured line lengths are flat across all four tiers (see the correction
    under **Weather Types Implemented** above). The ✅ belongs to the vocabulary only.
- ✅ **Time Period Variations**: Weather messages vary by time of day for atmospheric consistency
- **Comprehensive Coverage**: All 19 weather types from `WEATHER_INTENSITY` mapping implemented
- **Style**: observational ambience (see the module docstring of `world/weather/weather_messages.py`); no intensity scaling
- **Formatting Integration**: Weather text displayed with |w (bold white) formatting
- **Message Pool Architecture**: Extensive message pools following combat system patterns
- **Grounded Descriptions**: Weather lines are ambience grounded in the colony's texture (crater rim, channel, prefab roofs), each standing alone (module docstring of `world/weather/weather_messages.py`); `ROOM_TYPE_POOLS` adds lines for specific kinds of place

**Weather Types Implemented:**

> **CORRECTION 2026-09-11 — the word-count bands below are false, and there is no
> intensity scaling at all.** Measured over the whole generated corpus (228 pools,
> 3,192 lines), words per line by intensity tier: mild mean 8.58 (max 13), moderate
> 8.34 (max 12), intense 8.32 (max 13), extreme 8.65 (max 12). **Zero lines reach 16
> words and zero reach 20**, so "12-16", "16-20" and "20+" describe prose that does not
> exist, and extreme is no longer than mild. The pools were re-authored to one uniform
> ambience register — `world/weather/weather_messages.py`'s module docstring states the
> authoring principles and says nothing about length-by-intensity. `WEATHER_INTENSITY`
> has **no message-length consumer anywhere**: its readers are `WeatherSystem.set_weather`
> (validation), `WeatherSystem.get_weather_intensity()` (read only by the `@weather` admin
> command), the `@weather` admin listing in `commands/CmdAdmin.py`, and two tests, one of
> which pins `CrowdSystem.weather_modifiers` to its keys.
> The stale claim is repeated at §8 "Intensity-Based Messages", §4 "Intensity Scaling",
> "Intensity-Based Scaling", and the Integration Points summary. The type-to-tier
> groupings themselves are still correct.
- **Mild Intensity**: clear, overcast, windy (8-12 word messages)
- **Moderate Intensity**: fog, rain, soft_snow, foggy_rain, light_rain (12-16 word messages) 
- **Intense Intensity**: dry_thunderstorm, rainy_thunderstorm, hard_snow, blizzard, gray_pall, tox_rain, sandstorm, blind_fog, heavy_fog (16-20 word messages)
- **Extreme Intensity**: flashstorm, torrential_rain (20+ word epic messages)

**Technical Implementation:**
- Message pools in `world/weather/weather_messages.py` with 5 sense categories per pool (visual, auditory, olfactory, tactile, atmospheric); visual is gated on sight, auditory on hearing, olfactory on smell, and tactile and atmospheric always show
- Integration via `world/weather/weather_system.py` with proper |w formatting
- Room integration through modified `return_appearance()` method in `typeclasses/rooms.py`
- Weather is appended to the first line of the room description, after any @integrate content and before the object listing, characters and exits (`Room._compose_room_layers`)

#### 8b. The weather DRIVER is UNBUILT — the ✅ above is the rendering layer only

Everything ticked in §8 is what happens *once a weather is set*. **Nothing
sets one.** Owner ruling, 2026-09-08 (#3028, raised from the audit as
#2446 §4):

> "This isn't done. Ultimately, there will be elements of the game like
> mining, the terraformer, electrical usage, etc. and maybe even
> pseudo-weather patterns that are seasonal but they'll all influence
> the system. Weather isn't fully wired in yet."

**Current state, measured:**
- `WeatherSystem` is a bare module-global instance (`world/weather/__init__.py`)
  holding `current_weather` in memory, initialised to `"clear"`.
- `set_weather` has exactly one caller: the `@weather` admin command.
- Nothing advances weather on a clock. There is no ticker and no progression.
- So the colony runs permanently `clear` unless a builder sets it by hand,
  and reverts at the next reload — which is every deploy.
- 19 weather types and ~3,200 authored message lines across region and
  time-of-day pools are therefore effectively unreachable in play.

**This is a known gap, not a defect.** Do not "fix" it by adding
persistence or a random weather ticker; both would pre-empt the design.

**Prerequisites, per the ruling** — weather is meant to be an OUTPUT of
colony systems, not an independent generator. It is gated on:
- mining,
- the terraformer,
- electrical usage,
- seasonal pseudo-weather patterns.

Until those exist there is nothing for a weather driver to read. Consumers
of weather (crowd density, and through it `world/director/witness.py` and
`world/stealth.py`) should be understood as wired-but-unfed.

**Related balance note:** `CrowdSystem.weather_modifiers` was corrected in
#3027 to match the `WEATHER_INTENSITY` vocabulary, with a set-equality test
pinning the two. Its magnitudes are shaped-right, not tuned — no system in
this game has had its balance pass.

### 9. Crowd System ✅ 
- **Population Density**: Crowd levels affecting room atmosphere based on room type, weather, and character presence
- **Dynamic Descriptions**: Crowd-based sensory messages with 4 intensity levels (sparse/moderate/heavy/packed)
- **Activity Integration**: Crowd noise, movement, and presence effects integrated into room descriptions
- **Weather Integration**: Weather conditions affect crowd levels (rain reduces, clear weather increases)
- **Message Pool Architecture**: Following weather system patterns with sensory categories and random selection
- **Crowd level** (`CrowdSystem.calculate_crowd_level`): `crowd_base_level` + room-type modifier + 0.5 per body in the room (NPCs and hidden characters count) + weather modifier + colony-hour modifier (`time_modifiers`), rounded, never below 0; a `sky` room is always 0. `crowd_base_level` 0 means no crowd line ever (the builder's off switch). The message pool is chosen by room type (`crowd_profile_for_room_type`: default street, interior, shop, market, nightclub, constabulary, residential; sky is empty). The same level drives witness chance (`world/director/witness.py`) and the stealth concealment bonus (`world/stealth.py`).

**Technical Implementation:**
- Message pools in `world/crowd/crowd_messages.py` with visual, auditory, olfactory, tactile and atmospheric lines; one sense the looker can perceive is picked at random, then one line from it
- Integration via `world/crowd/crowd_system.py` with |w (bold white) formatting  
- Room integration through modified `get_display_characters()` method in `typeclasses/rooms.py`
- Crowd messages appear before character listings with environmental context

### 10. Adjacent Room Character Visibility ✅
- **Spatial Awareness**: Detect characters in adjacent rooms through exits
- **Simple Detection**: No complex visibility logic - encourages interaction and chase scenes
  - **SUPERSEDED 2026-09-11 — there are now three gates on this walker**, added after this
    was written and all deliberate: (1) it returns "" outright for a looker who cannot see
    (`can_perceive_sense(looker, "visual")`, `Room.get_adjacent_character_sightings`, #2793);
    (2) it walks `_visible_exits(looker)` rather than raw `self.exits`, so a `view:false()`
    secret exit is never named in the prose (#2588); and (3) each counted character
    must pass `can_perceive(looker, obj)`, the stealth presence gate (stealth
    spec §7 — no leak through the doorway glance). The "encourages interaction and chase
    scenes" intent survives; "no complex visibility logic" does not.
  - **Fourth gate, 2026-10-12 (#3750): door state.** The walker skips any exit whose
    `blocks_sight()` is true: a closed `DoorExit` (a broken one hangs open), a landing's
    elevator door while the car is elsewhere, the car's `out` while it moves. Before this
    the corridor outside a sealed door still said "You see a lone figure to the south."
    while `look south` showed only the door. `Exit.blocks_sight()` is the one predicate;
    the exit look's far-room people (`Exit.get_display_desc`) ask it too. Secret exits (2)
    and hidden people (3) remain their own gates.
  - **Fifth gate, 2026-10-17 (#3753): a sightline into open ground.** The walker skips a
    destination whose `type` is not in `world.crowd.crowd_messages.OPEN_AIR_ROOM_TYPES`
    (street, alley, market, bridge, rooftop, courtyard, balcony, fire escape, farm, hull,
    garden, agridome, stairwell; `room_type_is_open_air`). The list is the room types you
    can see into from next door, so a pursuer sees where someone went and a crowd can hide
    them (#3759, 2026-10-24); it is not a list of outdoor rooms, whatever its name says.
    Owner: "Streets, sure. Cubes? Not so much." / "I think it makes
    more sense for us to have room types...which I think we already do. It's a very standard
    mud design." The word is the whole test, so two words take in more than open ground:
    `market` covers the open-air Shipbreaker yard and the covered galleries (`MarketRoom`,
    `outside=False`) alike, `farm` covers the Greenhaus growing platforms and their 6 ground
    bays (`outside=False`), and `stairwell` covers the 17 Brackett stairs and the 33
    Greenhaus stairways (typed by build 170, #3757), so a figure on the stairs shows from
    the platform or landing beside them and from the flight above or below ("You see a lone
    figure above.", #3755). For one deploy, build 170 to #3759, `stairwell` was off the list
    and the platforms went dark. Any
    other type -- a rented unit, a tenement hall, the
    constabulary -- is never glanced into, open door or not, and an untyped room is treated
    the same. `look <door>` through an open door is its own renderer and still shows who is
    inside. Farm, hull, garden and agridome joined the list on 2026-10-19 (owner: "I feel like
    those types should allow 'glance'"); every room of those four types has crowd base 0 on
    live, so the glance into them always names figures and never a crowd. In play on
    2026-10-19: `garden` is the six Greenhaus lawns; no exit leads into any of the nine `hull`
    rooms, so that word changes nothing yet; the five `agridome` rooms include the Pre-Fab
    Agridome airlock, where a keeper stands, so Kaspar Street reads "You see a lone figure to
    the south." `sky` is not listed: nobody stands in the air. No room was retyped for this: the Brackett and Halcyon units stay untyped. Two
    rooms are never glanced from or into (review of #3753): a sky cell, which shows no exits
    and so names no directions either (a faller passing a populated roof would otherwise read
    "You see a lone figure to the east." in every cell; a drag-fall pair already did), and the
    room the looker stands in, since the aim view renders the far room and its exit back
    reported the shooter's own company ("You see a lone figure to the south.", the friend
    beside you) whenever the far room was occupied, and with the glance rendering alone would
    have done so for an empty one too. The far room's own glance into its other neighbours
    does render in the aim view, like the rest of that room; until #3753 it did so only when
    someone stood in the far room.
  - **Sixth gate, 2026-10-17 (#3753): the far crowd.** Owner: "I think open air should be a
    combination of room types and crowd size.", then "1." on: room type says the far room is
    open air, its crowd size says what you can make out. Heavy or packed
    (`crowd_system.crowd_hides_figures`: the level the room's own crowd line reads, and silent
    at base 0 -- the default, and the builder's off switch -- however many stand there) the
    glance reports the crowd and no figures -- "You see a crowd to the west." / "You see
    crowds to the north and south." -- and thinner, the lone-figure / group sentences as
    before. The level counts hidden bodies like any other (#2497), so a hider can tip a far
    street from moderate to heavy and switch the crowd sentence on; that is the density the
    hider blends into. `look <direction>` reads the same level for its crowd wording only when
    someone visible stands beyond, so with nobody visible there the crowd sentence is the one
    line from next door that shows the density moved; it names no one, and anyone standing in
    that street reads the same tier from its own crowd line (round-4 review). Unlike the glance and the crowd line, `look <direction>` does not honour base 0: `Exit._get_exit_character_display` words the far room by its raw `calculate_crowd_level`, so a base-0 room with enough people in it reads as a crowd there while its own crowd line stays silent. Live census
    2026-10-17,
    taken with the people then present and under clear skies (each body adds 0.5, so any
    open-air room with a base above 0 reads heavy once enough gather; rain and worse pull
    every level down): 48 streets and 9 markets reached heavy at the shift-change peaks, no
    other open-air room did, and at night none.
  - **Renders alone since #3753.** `get_display_characters` ran the glance below its
    empty-room return (2025-08-15, older than the glance itself), so a looker with nobody
    else in the room was never told who stood beyond the open doorway. The glance now runs
    before that return and joins the crowd line and the suspicion cue. Alone, those three
    share one paragraph as they always did with company; until #3753 the crowd line and the
    cue stood on two lines for a looker alone. `format_appearance` now places its blank lines
    by position (footer, characters, things counted from the end of the render) instead of
    matching text, so a description authored over several lines gets its blank line too, and
    an undescribed room with nothing on the floor and nobody shown runs its exits directly
    under "You see nothing special." (the old prefix match padded that line as a things line).
- **Natural Language**: "You see a lone figure to the south" (1 character), "You see a group of people standing to the east" (2+ characters), or "You see a crowd to the west" (heavy or packed over there, whoever is in it)  
- **Integration**: Appears after local characters as part of character display section
- **Performance Optimized**: Lightweight scanning of adjacent room contents on look command

**Technical Implementation:**
- Simple adjacent room scanning via `get_adjacent_character_sightings()` method
- Character counting and direction reporting through existing exit system
- Integration into `get_display_characters()` method following established patterns
- Natural language output matching existing "You see X" formatting

### 11. Exit Examination Enhancement ✅
- **Atmospheric Exit Descriptions**: Replaced generic "This is an exit." with immersive descriptions
- **Contextual Analysis**: Analyzes destination properties, exit types, and directional context  
- **Weather Integration**: weather framing ("Through the steady rain, ...") is added only to the street-shape sentence, only when this room or the destination is `outside`, and never in clear weather (`Exit._get_weather_context`)
- **Edge/Gap Support**: Specialized descriptions for edge and gap exits requiring jump commands
- **Street Context Analysis**: Analyzes destination room layout for dead-end/intersection/continuing street descriptions
- **Directional Defaults**: Noir-aesthetic atmospheric descriptions based on cardinal directions
- **Order of the atmospheric line** (`Exit._get_atmospheric_description`): edge and gap together, edge, gap, a sky destination ("The opening leads into open air, where gravity makes the rules."), a street destination's shape, a `fire escape` destination (its own lines keyed by exit: window, up, down, drop, else a default), the direction defaults (compass points, up, down, in, out), and last "The passage stretches into shadows and uncertainty." A blind looker is told only the exit's kind, or "A passageway leading elsewhere." `{time}` tokens are rendered. A looker who is aiming is told "You cannot see any further." instead.
- **Far-room people**: names the characters in the room the exit leads to, unless the exit blocks sight (a shut door). Hidden characters are left out, and a blind looker gets no names (`Exit._get_exit_character_display`).
- **Aiming Restrictions**: Blocks exit examination when character is aiming (maintains combat focus)
- **Residence doors (2026-10-13, #3508)**: looking at a unit's corridor-side door, the one the
  rental build registered as `cube.db.cube_door`, ends with the tenancy word: `Occupied.` for a
  live resident, `Vacant.` when the unit can be claimed, `Being vacated.` while a mover's
  48-hour relocation window holds it off the market (`world.rental.residence_status`,
  `DoorExit._residence_status`). Open or closed, sighted lookers only; the unit's own door
  leading out says nothing. The look is the touch that prunes a dead tenancy, so a unit whose
  tenant was deleted reads Vacant the moment anyone looks at its door.
- **Custom Description Support**: an exit's authored desc is shown first and the atmospheric line follows it; it does not replace it. A closed door (`DoorExit`) shows only its own desc and "It is closed." or "It is sealed; ..."
- **Fallback System**: Graceful degradation with atmospheric fallbacks for edge cases

**Technical Implementation:**
- Custom `get_display_desc()` method in Exit class overriding DefaultExit behavior
- Weather framing only on the street-shape sentence (`Exit._analyze_street_context`), as above  
- Street type analysis using destination room exit counting and type classification
- Specialized handling for edge/gap exits, sky rooms, and custom room types
- Character display using the destination room's contents (`Exit._get_exit_character_display`)
- Aiming system integration prevents exit examination during combat focus
- Weather context integration: "Through the steady rain, the street stretches eastward..."

**Integration Points:**
- **Distinct from Directional Looking**: Exit examination focuses on passage itself vs. adjacent room contents
- **Weather System Integration**: Leverages existing weather system for atmospheric context
- **Edge/Gap Mechanics**: Works with jump command system restrictions and specialized descriptions
- **Aiming System Integration**: Respects combat focus limitations preventing exit examination
- **Room Type System**: Utilizes existing room.type AttributeProperty for street analysis

### 12. Directional Look Character Display Enhancement ✅
- **Crowd-Aware Character Descriptions**: Character displays in directional looks adapt based on destination room crowd levels
- **Weather Integration**: Weather context appears only in the street-shape sentence, for an outside room or destination and any weather but clear ("Through the gentle snowfall, the street stretches westward...")
- **Stylized Descriptions**: Atmospheric descriptions matching game's noir aesthetic
- **Dynamic Character Presentation**: Characters presented with crowd context rather than generic "standing here" format
- **Natural Language Flow**: Proper directional phrasing ("To the west you see..." / "To the north you can see...")
- **Direction words**: only the four compass keys north, south, east and west get "To the ..."; any other exit key is capitalised as given ("Northeast you see ...", "Up you see ..."), without the "above"/"below" phrasing the footer and the glance use

**Crowd Level Integration:**
- **Heavy/Packed Crowds (Level 3+)**: "To the west you can see a bustling crowd of people going about their business, amidst them John Wilson."
- **Moderate Crowds (Level 2)**: "To the west you see figures moving through the urban maze, among them Juan and Maria."
- **Sparse Crowds (Level 1)**: "To the west you catch glimpses of movement in the shadows, including Juan."
- **Empty Areas (Level 0)**: "To the west you see Juan."

**Technical Implementation:**
- Integrated with existing crowd system via `crowd_system.calculate_crowd_level()`
- Weather framing from `Exit._get_weather_context`, on the street-shape sentence only
- Directional context detection using exit key analysis
- Graceful scaling for any number of characters with proper grammar
- Maintains existing character display functionality while enhancing atmospheric presentation

**Example Outputs:**
```
# Heavy crowd with weather:
"Through the gentle snowfall, the street stretches westward through the urban canyon, where scattered streetlight illuminates the continuing path between deteriorating storefronts. To the west you can see a bustling crowd of people going about their business, amidst them Janice Burns and Dean Keith."

# Moderate crowd, no weather:
"The street stretches eastward through the urban canyon, where scattered streetlight illuminates the continuing path between deteriorating storefronts. To the east you see figures moving through the urban maze, among them Sterling Hobbs and Charlene Fisk."

# Sparse crowd:
"To the north you catch glimpses of movement in the shadows, including Maria Santos."

# Empty area:
"To the south you see Juan Rodriguez."
```

### 13. Ambient Message System (🚧)
- **Periodic Atmospheric Messages**: Random yet informed frequency ambient messages
- **Contextual Integration**: Messages draw from contributing room factors (weather, crowd, etc.)
- **Dynamic Environmental Feedback**: Continuous atmospheric presence without player action
- **Sensory Immersion**: Brief flavor text that maintains environmental awareness

**Ambient Message Concept:**
Ambient messages appear at random intervals (every 2-5 minutes) to players in a room, providing brief atmospheric updates that reflect current environmental conditions. These messages are informed by the same systems that power the look command - weather, crowd levels, time of day, and room characteristics.

**Example Ambient Messages:**
- Weather-based: "The rain patters against the ground with a soft yet relentless persistence."
- Crowd-based: "A group of pedestrians hurries past, their footsteps echoing off wet pavement."
- Time-based: "The evening shadows grow longer, deepening the gloom between streetlights."
- Combined factors: "Despite the drizzle, street vendors continue their calls, their voices mixing with the hiss of tires on wet asphalt."

**Technical Implementation:**
- **Message Pool Integration**: Leverage existing weather/crowd message pools with ambient-specific variants
- **Frequency Management**: Configurable timing system to prevent message spam
- **Context Awareness**: Messages selected based on current room state (weather, crowd, time)
- **Player Filtering**: Optional ambient message preferences (full/reduced/off)
- **Room-Specific Pools**: Different ambient message types for different room types/themes

## Enhanced System Architecture

### 1. Sensory Category Framework

**Core Sensory Categories:**
- **Visual**: Lighting, colors, visual effects, environmental details
- **Auditory**: Ambient sounds, distant noises, activity sounds
- **Olfactory**: Scents, odors, atmospheric smells
- **Tactile**: Temperature, humidity, air movement, surface textures
- **Atmospheric**: General mood, tension, environmental pressure

**Sensory Category Implementation:**
- **Equal Priority**: All sensory categories treated with equal importance
- **Artful Combination**: Room can be described three ways, then combined non-redundantly
- **Graceful Degradation**: Categories with no content simply don't display
- **Medical Condition Support**: By design - players with sensory limitations see reduced content
  - **HONOURED BY EVERY LAYER LISTED HERE since 2026-10-08.** The predicate is one function,
    `can_perceive_sense(looker, "visual")` (`world/perception.py`), and these are its readers:
    room description (`Room.get_display_desc`, the void line), weather and crowd (both split by
    sense, #591), @integrate content including the flying-object line (#3373, #3479), the object
    list and the character placements (`get_display_things` / `get_display_characters`, #3479),
    the adjacent and doorway glances (#2793), the exit's atmospheric half and authored desc
    (`Exit.get_display_desc`, #3382) and the closed door (`DoorExit.return_appearance`, #3382).
    Two things are told to a blind looker on purpose: the **exits footer** (a character can know a
    room's exits by other means; the #2793 test records the choice) and, from `look <dir>`, the
    **kind** of exit the footer or the refused walk already names (an edge, a gap, open air, the
    street's shape, with the street counted the way the footer counts it), so the footer, the look
    and the refused walk never disagree about one exit. The passive stealth roll still runs for a
    blind looker (Resonance, "the sense that someone's there", stealth spec §3.1, as on arrival)
    but neither names anyone nor shows the prickling-sense cue to them: a character standing in the
    open gives blind eyes nothing, so a cue from a hidden one would make hiding the worse
    concealment. **OPEN:** whether a blind character should sense anyone's presence at all.
    Not covered by this bullet, and not by the fixes: `look <object>`, `look <character>`,
    `examine` and `search` render through their own paths.
    Measured 2026-09-11, before those fixes, three of the five layers honoured it and two did not;
    the record of the two, kept for the history of the bullet:
    - **@integrate object content** (`typeclasses/rooms.py:462-478`, "for now, use all available
      senses", falling back to the single-blob `integration_desc` at `:497`) — so a blind looker
      is told "The walls have been daubed with colorful graffiti" (`typeclasses/objects.py:360`)
      immediately after being told they can't see a thing.
    - **exit-examination prose** (`typeclasses/exits.py:534-556`, `:608-655`, `:730-760`) — the
      character half of `get_display_desc` is sight-gated (`:785-787`), the atmospheric half is not.
    Same defect class as #2793 / #2734 (both CLOSED; neither covered these two layers). Both were
    then filed and fixed (#3373, #3382). Do not reconcile by weakening this bullet.
- **Complementary Description**: Multiple approaches to describing same space, combined artfully

### 2. Component-Based Description Assembly

**Assembly Order:**
1. **Room Name & Base Description**: the sense layers the looker can perceive (`Room.get_display_desc`)
2. **@integrate Object Integration, then Weather**: appended to the first line of the description (`Room._compose_room_layers`)
3. **Traditional Object Listing**: Non-integrated objects listed separately (`Room.get_display_things`)
4. **Crowd line, characters, neighbour glance, suspicion cue**: one paragraph (`Room.get_display_characters`)
5. **Smart Exit Descriptions**: Context-aware exit information

> **CORRECTION 2026-09-11 — the list as first written put the crowd line before the object
> listing.** The crowd line is emitted by `Room.get_display_characters`, and the room's
> `Room.appearance_template` is `{header}{name}\n{desc}\n{things}\n{characters}\n{footer}`
> — so `{things}` (the traditional object listing) renders **before** the crowd line, not
> after. Actual order: name, desc (with @integrate + weather appended to the desc
> line, `Room._compose_room_layers`), things, crowd + characters, exits.

### 3. @integrate Object System

**Integration Mechanism:**
Items, graffiti, blood pools, shop containers and furniture with the `integrate` attribute set are woven into the room description (appended to its first line, before weather), stacking together without limits.

**Integration Stacking:**
- **No Limits**: All @integrate objects display together
- **Stacking Order**: Objects stack in discovery/creation order
  - **CORRECTION 2026-09-11:** order is by **integration priority, ascending** —
    `integrated_objects.sort(key=lambda x: x[0])` (`Room.get_integrated_objects_content`), unset
    defaults to 5, and flying objects take priority 1 and are added first, so they lead unless
    an object's priority is below 1.
    Creation order survives only as the tie-break within one priority (Python's sort is
    stable). This matches §7's "Priority System" bullet, not the line above.
- **No Conflicts**: Multiple objects contributing similar content is acceptable
- **End Positioning**: @integrate content, then weather, is appended to the first line of the room description (the end of the description only when it is a single line), before the object listing and the crowd/characters paragraph (`Room._compose_room_layers`)

**Enhanced Integration by Sensory Category:**
- **Visual Integration**: "bullet-ridden vehicles pass through", "colorful graffiti"
- **Auditory Integration**: Engine sounds, crowd noise, activity sounds
- **Olfactory Integration**: Vehicle exhaust, food smells, industrial odors
- **Tactile Integration**: Surface textures, temperature effects
- **Atmospheric Integration**: Tension, mood contributions

**Special Integration Systems:**
- **Graffiti System**: @integrate items with enhanced code logic for procedural variety
- **Vehicle System**: 📋 UNBUILT (no issue): moving objects that would contribute dynamic sensory elements
- **Art/Architecture**: Static integrated elements adding atmosphere

### 4. Dynamic Message Pool Systems

**Weather System Design:**
✅ **Implemented with comprehensive message pools following combat system architecture:**
```python
# Located in world/weather/weather_messages.py
# Generated by _build_weather_messages from WEATHER_POOLS, TIME_LIGHT and TIME_ACTIVITY;
# the lines below are illustrative, and real pools also carry 'tactile'.
WEATHER_MESSAGES = {
    'default': {
        'rain_early_evening': {
            'visual': [
                'steady rain turns the streets into dark mirrors reflecting neon light',
                'water streams down building facades and pools in street corners',
                'the city takes on a noir-like quality under the rain-washed evening light'
            ],
            'auditory': [
                'rain patters steadily against concrete and metal surfaces',
                'tires splash through growing puddles with wet hissing sounds', 
                'the rainfall creates a white noise that muffles other city sounds'
            ],
            'olfactory': [
                'petrichor mingles with urban scents of wet concrete and metal',
                'the rain releases stored smells from the pavement and gutters',
                'clean water scent fights against underlying industrial odors'
            ],
            'atmospheric': [
                'the rain creates an intimate, enclosed feeling despite the open space',
                'the city feels washed clean yet somehow more mysterious',
                'there\'s a sense of renewal mixed with urban grit'
            ]
        },
        'clear_midday': {
            'visual': [
                'harsh sun beats down mercilessly',
                'heat shimmer rises from every baked surface',
                'shadows shrink to sharp, minimal lines'
            ],
            'auditory': [
                'everything thrums with peak activity and motion',
                'cooling systems hum and rattle desperately',
                'background noise forms a steady symphony'
            ],
            'olfactory': [
                'heated surfaces create distinctive burning scents',
                'exhaust and industrial odors hang heavy',
                'overheated machinery adds acrid notes'
            ],
            'atmospheric': [
                'heat creates pressing, almost oppressive weight',
                'the air itself vibrates with intense energy',
                'energy levels feel maxed out everywhere'
            ]
        }
    }
}
```

**Weather Integration Implementation:**
- **Message Selection**: Random selection from appropriate pools per look command
- **Formatting**: Weather text appears with |w (bold white) formatting followed by |n reset
- **Integration Point**: Weather messages integrated directly into room description via modified `return_appearance()` 
- **19 Weather Types**: Complete coverage from mild (clear, overcast) to extreme (torrential_rain, flashstorm)
- **Time Variations**: every weather type has all 12 time periods, so there are 228 weather+time pools, built at import from per-weather sense pools plus per-period light and street-activity lines (`_build_weather_messages`)
- **Intensity Scaling**: Message length/complexity scales with weather intensity level
  - **CORRECTION 2026-09-11: it does not.** Measured means are 8.58 / 8.34 / 8.32 / 8.65
    words for mild / moderate / intense / extreme, and no line in the corpus exceeds 13
    words. Nothing in `world/weather/` reads `WEATHER_INTENSITY` to pick or shape a line.
```

**Crowd System Design:**
```python
crowd_messages = {
    'heavy': {
        'visual': ['people shoulder past each other', 'constant movement'],
        'auditory': ['mix of conversations', 'footsteps echo'],
        'atmospheric': ['bustling energy', 'urban intensity']
    },
    'moderate': {
        'visual': ['foot traffic starting to get heavy', 'still have personal space'],
        'auditory': ['occasional conversation fragments', 'moderate activity'],
        'atmospheric': ['building energy', 'comfortable activity level']
    }
}
```

**Ambient Message System Design:**
```python
ambient_messages = {
    'weather_rain': [
        "The rain patters against the ground with a soft yet relentless persistence.",
        "Water drips steadily from overhead fixtures, creating small puddles below.",
        "A gentle mist rises from the wet pavement as rain continues to fall."
    ],
    'crowd_moderate': [
        "A group of pedestrians hurries past, their footsteps echoing off wet pavement.",
        "Quiet conversations drift from nearby groups before fading into background noise.",
        "Someone's footsteps approach from behind, then veer off down a side path."
    ],
    'combined_rain_crowd': [
        "Despite the drizzle, street vendors continue their calls, their voices mixing with the hiss of tires on wet asphalt.",
        "Umbrellas bob and weave through the crowd as people navigate the rain-slicked street.",
        "The sound of hurried footsteps on wet concrete mingles with the steady patter of rain."
    ],
    'time_evening': [
        "The evening shadows grow longer, deepening the gloom between streetlights.",
        "As darkness approaches, windows begin to glow with warm artificial light.",
        "The day's heat slowly radiates from pavement and brick walls."
    ]
}
```

**Ambient Message Technical Implementation:**
```python
class AmbientMessageSystem:
    def __init__(self, room):
        self.room = room
        self.last_message_time = time.time()
        self.base_interval = 180  # 3 minutes base interval
        self.variance = 60       # +/- 1 minute variance
    
    def should_send_ambient_message(self):
        """Determine if it's time for an ambient message"""
        current_time = time.time()
        time_since_last = current_time - self.last_message_time
        
        # Calculate next interval with variance
        target_interval = self.base_interval + random.randint(-self.variance, self.variance)
        
        return time_since_last >= target_interval
    
    def select_ambient_message(self):
        """Select appropriate ambient message based on current conditions"""
        conditions = []
        
        # Check weather
        weather = self.room.get_current_weather()
        if weather != 'clear':
            conditions.append(f'weather_{weather}')
        
        # Check crowd level
        crowd_level = self.room.get_crowd_level()
        if crowd_level != 'sparse':
            conditions.append(f'crowd_{crowd_level}')
        
        # Check time of day
        time_period = self.room.get_time_period()
        if time_period in ['evening', 'night', 'dawn']:
            conditions.append(f'time_{time_period}')
        
        # Try combined conditions first, then individual
        message_pools = []
        if len(conditions) > 1:
            combined_key = '_'.join(sorted(conditions))
            if combined_key in ambient_messages:
                message_pools.append(ambient_messages[combined_key])
        
        # Add individual condition pools
        for condition in conditions:
            if condition in ambient_messages:
                message_pools.append(ambient_messages[condition])
        
        # Select random message from available pools
        if message_pools:
            selected_pool = random.choice(message_pools)
            return random.choice(selected_pool)
        
        return None
    
    def send_ambient_message(self):
        """Send ambient message to all players in room"""
        message = self.select_ambient_message()
        if message:
            # Send to all players in room with special formatting
            self.room.msg_contents(f"|K{message}|n", exclude_disconnected=True)
            self.last_message_time = time.time()
```

**Message Selection System:**
✅ **Implemented with the following features:**
- **Per Look Command**: New random selection each time room is looked at
- **Combat Message Architecture**: Uses weather system variables to select from description pools
- **Equal Probability**: All messages in pool have equal selection chance
- **Variable-Driven Selection**: Weather type + time of day inform available message pools
- **Intensity-Based Scaling**: Message complexity scales with weather intensity (mild/moderate/intense/extreme)
  - **CORRECTION 2026-09-11:** not implemented — see the correction under **Weather Types
    Implemented**. The selector reads weather type and time period only
    (`WeatherSystem.get_weather_contributions`); intensity never enters message selection.
- **Noir/Cinematic Style**: Adult-focused atmospheric writing with sophisticated descriptions
- **Grounded Descriptions**: Weather lines are grounded in the colony's texture; `ROOM_TYPE_POOLS` adds lines for specific kinds of place

**Message Pool Structure:**
✅ **Implemented with comprehensive structure:**
```python
# Located in world/weather/weather_messages.py
WEATHER_INTENSITY = {
    # Mild weather
    'clear': 'mild', 'overcast': 'mild', 'windy': 'mild',
    # Moderate weather
    'fog': 'moderate', 'rain': 'moderate', 'soft_snow': 'moderate', 
    'foggy_rain': 'moderate', 'light_rain': 'moderate',
    # Intense weather
    'dry_thunderstorm': 'intense', 'rainy_thunderstorm': 'intense',
    'hard_snow': 'intense', 'blizzard': 'intense', 'gray_pall': 'intense',
    'tox_rain': 'intense', 'sandstorm': 'intense', 'blind_fog': 'intense', 
    'heavy_fog': 'intense',
    # Extreme weather
    'flashstorm': 'extreme', 'torrential_rain': 'extreme'
}

WEATHER_MESSAGES = {
    'default': {
        'clear_midday': { 'visual': [...], 'auditory': [...], 'olfactory': [...], 'atmospheric': [...] },
        'rain_early_evening': { 'visual': [...], 'auditory': [...], 'olfactory': [...], 'atmospheric': [...] },
        'torrential_rain_night': { 'visual': [...], 'auditory': [...], 'olfactory': [...], 'atmospheric': [...] }
        # ... 228 weather+time pools in all (19 weather types x 12 time periods); each pool also has 'tactile'
    }
}
```
**Selection Logic**: `weather_type + "_" + time_period` determines message pool (e.g., `clear_midday`, `rain_early_evening`)
**Coverage**: All 19 weather types, each with all 12 time periods
**Integration**: Weather system in `world/weather/weather_system.py` selects and formats messages with |w bolding

### 5. Smart Exit System Enhancement

**Room Type System:**
- **Storage**: `room.db.type` attribute for room classification
- **Street wording**: `street` is a stored type; "dead-end", "continues" and "intersection" are wording chosen from the destination street's layout (below), not stored room types
- **Custom Types**: `courier service`, `cube hotel`, `hospital`, `stairway` (builder-defined)
- **Integration**: Auto-detected and custom types work together for mixed scenarios

**Auto-Detection Rules:**
For each exit into a `street` room, the destination's exits that lead to other `street` rooms are counted (exits to other kinds of room do not count):
- **Dead-end**: 0 or 1 → "There is a dead-end ..."
- **Street**: exactly 2 → "The street continues ..."
- **Intersection**: 3 or more → "There is an intersection ..."

**Natural Language Exit Patterns:**
1. **Grouped by Type**: "The street continues to the north (n) and south (s)."
2. **Individual Destinations**: one sentence per type: "There is a courier service to the west (w). There is a cube hotel to the east (e)."
3. **Mixed Integration**: "The street continues to the north (n). There is a hospital to the east (e). There is an edge to the south (s)."
4. **Fallback Format**: "There is an exit to the south (s)" when no type information available

Two or more exits of one kind take the plural ("There are edges to the south (s) and west (w)."). Groups are never joined with "and": each gets its own sentence, in this order: dead-ends, continuing streets, intersections, each custom type, edges, gaps, then other exits (`Room.format_exit_groups`).

**Exit Display Examples:**
```
Example 1 (Mixed types):
"The street continues to the south (s) and north (n). There is a courier service to the west (w). There is a cube hotel to the east (e)."

Example 2 (Utilitarian/Complex):  
"There are exits to the east (e), west (w), C01 (01), C02 (02), C03 (03), C04 (04), C05 (05), and C06 (06)."

Example 3 (Simple mixed):
"The street continues to the north (n). There is an intersection to the south (s). There is a stairway to the west (w)."
```

**Alias Integration:**
- **Standard Format**: "north (n)" - shows the exit's key and its shortest alias ("elevator (in)", not "(car)")
- **No Alias**: "north" - omits parentheses when no alias exists, or when the alias is the key itself
- **Complex Exits**: Custom exit names with their shortest alias

**Edge/Gap Integration:**
- **Natural Language**: "There are edges to the south (s) and west (w)."
- **Mixed Content**: Edges integrated with other exit types naturally
- **Multiple Edges**: Grouped using natural language conjunctions

**Implementation Logic:**
1. **Analyze Destinations**: Check each exit's destination `room.db.type`
2. **Group by Type**: Collect exits leading to same destination types
3. **Apply Grouping Rules**: each street exit is worded by its destination's count of street exits (dead-end, continues, intersection)
4. **Format Individual Types**: "There is a [type] to the [direction]"
5. **Integrate Edges/Gaps**: Include in natural language flow
6. **Fallback Handling**: Use generic format for unknown types

Inside a venue, exits to rooms of the same type read "The {type} continues ..." instead of "There is a ...". Articles come from `world.grammar.get_article`, and irregular plurals from `TYPE_PLURALS` ("constabularies"). Exits into sky rooms are not listed unless they are edges or gaps, and a sky room lists no exits at all. View-locked (secret) exits are not listed unless this looker has found them (`Room._visible_exits`, `db.found_exits`).

### 6. Character Integration Enhancement

**Sensory-Aware Character Descriptions:**
- **Visual**: Equipment, posture, condition visible elements
- **Auditory**: Character-generated sounds, movement noise
- **Atmospheric**: How characters affect room tension/mood

**Integration with Existing Systems:**
- **Hand/Inventory System**: What characters are visibly holding
- **Combat System**: Character condition affects their sensory contribution
- **Proximity System**: Character positioning and interactions

## Technical Implementation Details

### Message Pool Architecture

**System Design:**
```python
# Message pool structure following combat system patterns
weather_pools = {
    'clear_visual': [
        "clear evening sky shows above",
        "streetlights cast steady pools of amber light", 
        "shadows are sharp and well-defined"
    ],
    'rain_auditory': [
        "steady patter of rain on concrete",
        "splash of tires through puddles",
        "water dripping from gutters and awnings"
    ],
    'rain_tactile': [
        "dampness in the air",
        "cool moisture on exposed skin",
        "slick surfaces underfoot"
    ]
}

crowd_pools = {
    'sparse_atmospheric': [
        "quiet emptiness broken by occasional footsteps",
        "sense of solitude in urban space", 
        "echoes carry further in the empty air"
    ],
    'heavy_auditory': [
        "constant murmur of conversations",
        "shuffle and scrape of many feet",
        "occasional burst of laughter or shouting"
    ]
}
```

**Selection Mechanics:**
- Fresh random selection per look command (like combat messages)
- Every line in a pool is equally likely; there are no weights
- No variable substitution in weather or crowd lines; only the room's own description renders time tokens (`render_time_tokens` in `Room.get_display_desc`)
- Conditional pools based on environmental state

### Component Integration System

**Assembly Order:**
1. **Room Name**: Static title
2. **Base Description**: the visual `desc` plus any `sense_descs` layers the looker perceives (`Room.get_display_desc`)
3. **@integrate Objects**: Stacked at end of room description text
4. **Weather**: appended after the @integrate text on the same description line, outdoor rooms only. The crowd line is not here: it opens the character paragraph (`Room.get_display_characters`)
5. **Character Listings**: Enhanced character descriptions
6. **Traditional Objects**: Remaining visible objects

> **CORRECTION 2026-09-11:** 5 and 6 are reversed in the shipped renderer — the
> `Room.appearance_template` (`typeclasses/rooms.py`) puts `{things}` before
> `{characters}`. This is the second of two Assembly Order lists in this file and it also
> disagrees with the first (§2 Component-Based Description Assembly); neither matches the
> template. The template is authoritative.
7. **Exit Information**: Smart categorized exits

**Integration Processing:**
```python
def assemble_room_description(self, looker):
    components = []
    
    # 1. Base room description
    components.append(self.get_base_description())
    
    # 2. @integrate objects (stack at end of base description)
    integrate_content = self.get_integrated_objects()
    if integrate_content:
        components[-1] += " " + integrate_content
    
    # 3. Sensory layer assembly
    sensory_content = self.assemble_sensory_layers(looker)
    if sensory_content:
        components.append(sensory_content)
    
    # 4. Character descriptions  
    char_content = self.get_enhanced_character_descriptions(looker)
    if char_content:
        components.append(char_content)
    
    # 5. Traditional objects
    obj_content = self.get_traditional_objects(looker)
    if obj_content:
        components.append(obj_content)
    
    # 6. Exit information
    exit_content = self.get_smart_exits(looker)
    if exit_content:
        components.append(exit_content)
    
    return "\n\n".join(components)
```

**Performance Considerations:**
- Message pool evaluation happens per look command for freshness
- Static content caching where appropriate  
- Minimal database queries for dynamic content
- Graceful degradation when components unavailable

## Technical Implementation

### Enhanced Room Attributes

**Sensory Message Storage:**
```python
# Room attributes (AttributeProperty on Room, typeclasses/rooms.py)
room.desc = "..."          # the visual layer
room.sense_descs = {        # non-visual layers, each shown only to a looker who has that sense
    'auditory': "sounds of traffic and urban activity",
    'olfactory': "sewage and raw garbage",
    'tactile': "acidic moisture in the air",
    'atmospheric': "tension of dangerous territory"
}
room.outside = True         # weather shows only when True
room.crowd_base_level = 2   # int; 0 means no crowd line, ever
room.is_sky_room = False

# Room type for smart exit labeling: set by a builder, or by the room typeclass
# (StreetRoom sets 'street', IndoorRoom 'interior'); nothing detects it.
room.type = 'street'  # e.g. 'street', 'corner store', 'courier service', 'stairwell'
# Dead-end, continuing street or intersection is worked out when the exits line is
# written (Room.format_exit_groups), from how many street exits the far room has.
# Nothing is stored.
```

**Smart Exit Implementation:**
```python
# NAME CORRECTION 2026-09-11: no method of this name exists. The real code is
# Room.get_custom_exit_display(looker) plus Room.format_exit_groups(exit_groups) in
# typeclasses/rooms.py, reached via get_display_footer. Differences from the sketch below:
# it walks _visible_exits(looker) rather than self.exits, so a view:false() exit stays
# out of the exit prose (#2588); the paren hint is the shortest alias; it tests
# destination.type; exits into sky rooms are skipped unless they are edges or gaps; a sky
# room shows no exits; a group of the room's own type reads "The <type> continues ...";
# up and down are phrased by format_exit_phrases ("above"/"below").
def get_smart_exit_description(self, looker):
    """Generate natural language exit descriptions."""
    
    # Group exits by destination type and special properties
    exit_groups = {
        'streets': [],
        'edges': [],
        'gaps': [],
        'custom_types': {},
        'fallback': []
    }
    
    # Analyze each exit
    for exit_obj in self.exits:
        direction = exit_obj.key
        alias = exit_obj.aliases[0] if exit_obj.aliases else None
        destination = exit_obj.destination
        
        # Check for edge/gap first
        if getattr(exit_obj.db, "is_edge", False):
            exit_groups['edges'].append((direction, alias))
        elif getattr(exit_obj.db, "is_gap", False):
            exit_groups['gaps'].append((direction, alias))
        # Check destination type
        elif destination and hasattr(destination.db, 'type'):
            dest_type = destination.db.type
            if dest_type == 'street':
                exit_groups['streets'].append((direction, alias))
            else:
                if dest_type not in exit_groups['custom_types']:
                    exit_groups['custom_types'][dest_type] = []
                exit_groups['custom_types'][dest_type].append((direction, alias))
        else:
            # Fallback for exits without type information
            exit_groups['fallback'].append((direction, alias))
    
    # Generate natural language descriptions
    return self.format_exit_groups(exit_groups)
```

### Enhanced return_appearance Method

**Assembly Process:**
1. **Initialize Sensory Categories**: Start with base room sensory content
2. **Process @integrate Objects**: Add object sensory contributions to categories
3. **Apply Weather System**: Add current weather sensory messages
4. **Apply Crowd System**: Add current crowd sensory messages  
5. **Assemble Narrative**: Combine sensory categories into flowing description
6. **Add Traditional Objects**: List non-integrated objects separately
7. **Add Smart Exits**: Context-aware exit descriptions
8. **Apply Player Filters**: Modify based on player condition/equipment

**Method Signature:**
```python
def return_appearance(self, looker, **kwargs):
    """
    Enhanced appearance method with component-based sensory assembly.
    
    Assembles room description from:
    - Base room description and sensory content
    - @integrate objects woven into narrative  
    - Weather system sensory contributions
    - Crowd system sensory contributions
    - Smart exit descriptions
    - Traditional object listings
    
    Args:
        looker: Character looking at the room
        **kwargs: Additional parameters for customization
        
    Returns:
        str: Assembled room description with all components
    """
```

## Component System Details

### @integrate Object System

**Object Integration Attributes:**
```python
# On objects that should integrate into room description
@integrate = True
integration_priority = 10  # Lower = appears earlier; unset = 5; flying objects are always 1
sensory_contributions = {
    'visual': "bullet-ridden vehicles pass through",
    'auditory': "engine noise and grinding gears",
    'atmospheric': "sense of urban danger"
}
```

**Integration Processing:**
- Objects with `@integrate = True` contribute to room description
- Priority determines integration order
- Each object's perceivable `sensory_contributions` are joined into its own text, in the order visual, auditory, olfactory, tactile, gustatory, then any others, and appended to the description line in priority order
- With no contributions an object falls back to `integration_desc`, then `integration_fallback`, then "<key> is here"; this fallback is visual only
- `integrate` is honoured only on Items, graffiti, blood pools, shop containers and furniture (`Room.get_integrated_objects_content`)
- Objects do not appear in traditional object listing

### Weather System Integration

**Weather State Management:**
- Current weather state affects all sensory categories
- Message pools provide variety like combat system
- Weather type and time of day choose the message pool; intensity plays no part in selection
- Integration with room base description

### Crowd System Integration

**Crowd Level Management:**
- Dynamic crowd levels: sparse, moderate, heavy, packed
- Each level has message pools for different sensory categories
- The crowd line is one sentence per look, from one sense the looker perceives (any of the five), from a pool chosen by room type (`crowd_profile_for_room_type`: shop, market, nightclub, constabulary, residential, interior, an empty pool for sky, the street pool otherwise); a room with `crowd_base_level` 0 never shows one
- Integration with character listing and social dynamics

### Smart Exit Enhancement

**Exit Context Detection:**
- Analyze destination room types to determine exit labels
- For an exit into a `street` room, work out at render time whether it is a dead-end, a continuing street or an intersection, from how many street exits that room has (`Room.format_exit_groups`); nothing is stored
- Other exits are named from the far room's `type`, which builders set
- Exits render as their own last paragraph, after the people

## Example Implementation

**Component Assembly Example:**
```
Base Room: "Large intersection where Sinn crosses Knife"
+ Weather (acid rain): "dismal acidic shower falls from platform above"  
+ Crowd (moderate): "foot traffic starting to get heavy but personal space"
+ @integrate Vehicles: "bullet-ridden vehicles pass through on drive-bys"
+ @integrate Graffiti: "walls daubed with colorful graffiti"
+ Traditional Objects: "You see a flyer [Nyrek the Unwired]"
+ Smart Exits: "street to the south/west/east" (intersection detected)
= Final assembled description
```

## Integration Points

### Weather System Integration ✅
**Rendering only; the weather driver is 📋 UNBUILT (see §8b):**
- Weather contributes to all sensory categories (visual, auditory, olfactory, atmospheric)
  - **CORRECTION 2026-09-11: five layers, not four** — `tactile` is authored and emitted for
    every pool (`_build_weather_messages`, `world/weather/weather_messages.py:1078-1088`),
    matching this spec's own "Core Sensory Categories" list. Sight gates `visual`, hearing
    gates `auditory` and smell gates `olfactory`; tactile and atmospheric always show
    (`blocked_senses` in `world/perception.py`, read by `WeatherSystem.get_weather_contributions`).
- Message pools rotated like combat messages with fresh selection per look command
- 17 weather types with intensity-based message complexity scaling
  - **CORRECTION 2026-09-11, two errors:** the count is **19** (`WEATHER_INTENSITY`,
    `world/weather/weather_messages.py:37-64`), and the intensity-based complexity scaling
    was never implemented — line length is flat across all four tiers (see the correction
    under **Weather Types Implemented**).
- Time period variations for atmospheric consistency (1-12 time periods per weather type)
  - **CORRECTION 2026-09-11: every weather has all 12 periods**, with no asymmetry — the
    dict is generated, not hand-authored (`_build_weather_messages`,
    `world/weather/weather_messages.py:1069-1096`; `TIME_PERIODS` at `:67-71`). Measured:
    19 x 12 = 228 pools, 12 periods for every weather without exception.
- Noir/cinematic writing style with adult-focused sophisticated descriptions
- |w formatting integration for bold white weather text display
- Universal weather descriptions avoid location-specific references
- Direct integration into room descriptions via modified `return_appearance()` method

**Technical Implementation:**
- `world/weather/weather_messages.py`: Comprehensive message pools with 4 sensory categories
  - **CORRECTION 2026-09-11:** five categories (visual / auditory / olfactory / **tactile** /
    atmospheric), and the dict is composed at import by `_build_weather_messages()` (`:1069`)
    from `WEATHER_POOLS` + `TIME_LIGHT` / `TIME_ACTIVITY` — 228 pools, 3,192 lines, measured.
- `world/weather/weather_system.py`: Message selection and formatting logic  
- `typeclasses/rooms.py`: `Room._compose_room_layers`, used for your own room and for the room you aim into
- Weather shows only in rooms with `outside` set; it mixes in the room type's ambience pool (`ROOM_TYPE_POOLS`) where one exists, and shows two lines from two different senses the looker perceives (three when the looker is missing a sense), appended after any @integrate text on the description line, before the things line

### Crowd System Integration  
- Crowd level chooses the pool tier; the line can come from any sense the looker perceives
- Character interactions influenced by crowd density
- Dynamic social context for room descriptions

### Combat System Integration
- Character condition affects perception and sensory input
- Weapon visibility integrated with character descriptions
- Proximity system affects social positioning descriptions

### Inventory System Integration
- @integrate objects blend into room narrative
- Traditional objects listed separately
- Hand system integration for character equipment visibility

## Future Extensions

### Advanced Component Systems
- **Economic Activity**: Market sounds, commercial atmosphere
- **Security Level**: Patrol presence, safety indicators  
- **Time Cycling**: weather lines, the crowd level and time tokens in room descriptions follow the colony clock; day/night variation in other systems is 📋 UNBUILT (no issue)
- **Seasonal Changes**: Long-term environmental variations
- **Ambient Message System**: Periodic atmospheric messages based on current room conditions

### Enhanced Integration
- **Cross-Component Effects**: Weather affecting crowd behavior
- **Player Influence**: How player actions affect room atmosphere
- **Historical Layering**: Past events affecting current descriptions
- **Dynamic Events**: Real-time events integrated into descriptions

## Technical Implementation

### Enhanced Room Attributes

**New Room Properties:**
```python
# Sensory message storage
sensory_messages = {
    'visual': ['dim lighting', 'shadows in corners'],
    'auditory': ['distant traffic', 'muffled conversations'],
    'olfactory': ['stale air', 'hint of smoke'],
    'tactile': ['cool dampness', 'sticky humidity'],
    'atmospheric': ['tense quiet', 'underlying unease']
}

# Environmental conditions
environmental_state = {
    'weather': 'clear',
    'time_of_day': 'evening',
    'crowd_level': 'sparse',
    'activity_level': 'low'
}

# Building/design theme
room_theme = {
    'style': 'industrial',
    'condition': 'deteriorating',
    'lighting': 'artificial',
    'size': 'medium'
}
```

### Enhanced return_appearance Method

**Method Signature:**
```python
def return_appearance(self, looker, **kwargs):
    """
    Enhanced appearance method with sensory integration and conditional parsing.
    
    Args:
        looker: Character looking at the room
        **kwargs: Additional parameters for customization
        
    Returns:
        str: Formatted room description with integrated elements
    """
```

**Processing Flow:**
1. **Base Description Assembly**: Static room description
2. **Environmental Assessment**: Current weather, time, conditions
3. **Sensory Layer Selection**: Choose appropriate sensory messages
4. **Character Integration**: Enhanced character descriptions
5. **Object Contextualization**: Objects with interaction hints
6. **Exit Integration**: Descriptive exit information
7. **Atmosphere Addition**: Weather, crowd, ambient activity
8. **Player Filter Application**: Modify based on player conditions
9. **Final Assembly**: Combine all elements into cohesive narrative

### Character Enhancement Integration

**Enhanced Character Display:**
- Integration with existing hand/inventory system
- Weapon and equipment visibility based on wielded items
- Health status integration with combat system
- Proximity system awareness for social positioning

### Object System Integration

**Item Integration:**
- Leverage existing Item typeclass system
- Integration with throw mechanics and flying objects
- Proximity-based interaction hints
- State-aware descriptions

## Command Variations

### Primary Look Command
- `look` - Full room description with all enhancements
- `l` - Alias for look

### Targeted Look Commands  
- `look <character>` - Detailed character examination
- `look <object>` - Detailed object examination  
- `examine <target>` - Deep examination with interaction hints
  - **NOT BUILT, confirmed 2026-09-11.** No `examine` command exists in this repo —
    `commands/` defines none and `commands/default_cmdsets.py` adds none — so `examine` is
    Evennia's stock builder-locked debug command: no interaction hints, and not a player verb.
    The game's deep-examination verbs are `inspect` / `autopsy` for corpses and blood pools
    (`CmdInspect` in `commands/forensics.py`, alias `autopsy`). Whether this line is still a
    plan or should join the `listen` / `smell` / `feel` ruling (#1510) is an open owner question.

**🎯 Aiming Integration Enhancement:**
- **REPLACED 2026-10-24 (#3596).** `look <target>` while aiming is `commands.CmdLook`: it
  resolves the target in the aimed room first (`Room.aimed_room_for`, the same seam the aim
  view reads), a person by description through the identity pipeline, then a thing by name,
  then falls back to the ordinary reach (your room, your pockets). Ordinals count the aimed
  room alone. Nothing else widens: `Character.get_search_candidates` no longer adds the
  aimed room to the default search, so `put`, `scan`, `diagnose`, `tune`, `remember`, `to`,
  `whisper` and targeted emotes reach this room only while aiming. `attack` and `throw`
  name the aimed room themselves and did not change. Owner, on the audit: `look
  <description>` down the barrel works; emotes, `to` and `whisper` across the aim do not.
  Tests: `world/tests/test_aiming_does_not_widen_every_search.py`,
  `test_the_aimed_look_reaches_the_ground.py`. The bullets below describe the old scheme.
- ~~When aiming in a direction, targeted look commands search both current room AND aimed-at room~~
- ~~Unified ordinal numbering across both spaces ("2nd goblin" finds 2nd goblin whether in current or aimed room)~~
- ~~Implemented via `Character.get_search_candidates()` override using Evennia's designed hook points~~
- ~~Universal system affects ALL commands using `caller.search()`, not just look commands~~
  - No longer true: `Character.get_search_candidates` does not add the aimed room to
    `caller.search()` (#3596); see the note above.
- Maintains backward compatibility when not aiming

### Sensory Focus Commands
**Not to be built** (owner decision, 2026-08-03, #1510; see the header note).

- `listen` - Focus on auditory information
- `smell` - Focus on olfactory information
- `feel` - Focus on tactile information

## Integration Points

### Weather System Integration
- Weather affects all sensory layers
- Temperature impacts tactile descriptions
- Precipitation affects visibility and sound

### Combat System Integration  
- Character status affects perception
- Weapon visibility based on wielded items
- Proximity system affects character positioning
- ~~**Universal Aiming Search**: All commands automatically search aimed-at rooms when aiming (look, get, attack, etc.)~~
  - **REMOVED 2026-10-24 (#3596).** No command's default search reaches the aimed room any more.
    `look <target>` resolves there itself (`commands.CmdLook`); `attack` and `throw` always did.
  - **FALSE FOR `attack`, corrected 2026-09-11.** `attack` does not use the
    `get_search_candidates` hook at all. It resolves the aimed exit itself and scopes
    candidates to the people in the far room **only** (`CmdAttack.func` in
    `commands/combat/core_actions.py`, passing them to `resolve_character_target`), so while
    aiming, the **current** room drops out of scope entirely. No command's default
    `caller.search()` reaches the aimed room; `look <target>` resolves it in `commands.CmdLook`.

### Inventory System Integration
- Held items affect available interactions
- Equipment affects sensory perception
- Item states visible in descriptions

### Building/Design System Integration
- Room themes affect sensory messages
- Architectural details impact descriptions
- Interactive environment elements

## Example Output

**Previous Basic Output:**
```
Braddock Avenue
A wide street stretching north and south.

You see: Nick Kramer

Exits: north, south
Edges: down
```

**Current Enhanced Output (✅ Implemented):**
```
Braddock Avenue
Tall, grim-faced tenement buildings flank the way here, seeming to lean in 
towards each other and restricting overhead light. A labyrinth of rusted fire 
escapes clings to their facades, some sections looking dangerously unstable. 
Most windows are dark or covered with yellowed blinds, offering little sign 
of life within their depths. The street level is a mix of boarded-up shops 
with faded signage and the entrances to dimly lit alleyways, the air carrying 
the scent of stale cooking oil, damp concrete, and a faint trace of mildew. 
Loose paving stones and crumbling curbs line the edge of the narrow street.

Kathy Cohen-Gold is doing a handstand. Nick Kramer is in a full-split. 
Sterling Hobbs, Janice Burns, and Dean Keith are standing here.
The street continues to the west (w) and east (e). There is a corner store 
to the north (n). There is a laundromat to the south (s).
```

**Future Enhanced Output (🚧 Planned):**
```
Braddock Avenue
Tall, grim-faced tenement buildings flank the way here, seeming to lean in 
towards each other and restricting overhead light. A labyrinth of rusted fire 
escapes clings to their facades, some sections looking dangerously unstable. 
Most windows are dark or covered with yellowed blinds, offering little sign 
of life within their depths. The street level is a mix of boarded-up shops 
with faded signage and the entrances to dimly lit alleyways, the air carrying 
the scent of stale cooking oil, damp concrete, and a faint trace of mildew. 
Loose paving stones and crumbling curbs line the edge of the narrow street. 
|wCool evening air carries hints of exhaust and distant cooking, while the 
soft murmur of traffic drifts from the main thoroughfare. A light breeze 
stirs loose papers along the gutter.|n
[Crowd integration: Despite the fortress-like precautions, there's a 
neighborhood warmth here — this is where locals come for milk at midnight.]

Kathy Cohen-Gold is doing a handstand, her Colt M1911 pistol secured in 
her belt holster. Nick Kramer is in a full-split, appearing alert and 
scanning the shadows with practiced wariness. Sterling Hobbs, Janice Burns, 
and Dean Keith are standing here.

[Object integration: A manhole cover lies slightly askew near the curb, 
its edges worn smooth by countless footsteps.]

The street continues to the west (w) and east (e). There is a corner store 
to the north (n). There is a laundromat to the south (s).
```
**Note**: Weather integration is ✅ **currently implemented** - the |w formatted weather text appears directly in room descriptions.

## Future Extensions

### Scriptable City Generation Support

**Template-Driven Room Generation:**
```python
# Room generation templates for automated city building
room_templates = {
    'street_intersection': {
        'base_description_template': "{{size}} intersection where {{street1}} crosses {{street2}}",
        'sensory_pools': {
            'visual': ['urban_intersection_visual', 'traffic_visual'],
            'auditory': ['traffic_audio', 'urban_ambient'],
            'atmospheric': ['city_energy', 'intersection_mood']
        },
        'required_variables': ['street1', 'street2', 'size'],
        'optional_variables': ['district_type', 'time_period', 'economic_level']
    },
    'commercial_street': {
        'base_description_template': "{{street_name}}, lined with {{business_density}} storefronts",
        'sensory_pools': {
            'visual': ['commercial_visual', 'storefront_variety'],
            'auditory': ['commerce_sounds', 'foot_traffic'],
            'olfactory': ['food_smells', 'urban_scents']
        },
        'auto_integrate_objects': ['signs', 'storefronts', 'street_furniture']
    }
}
```

**Procedural Content Generation:**
- **Message Pool Inheritance**: Child rooms inherit and modify parent pools
- **Variable-Driven Content**: Template variables drive sensory message selection
- **Contextual Integration**: Auto-generate @integrate objects based on room type
- **Thematic Consistency**: Ensure generated content maintains narrative coherence

**Neighborhood-Scale Coordination:**
```python
# District-level coordination for consistent atmosphere
district_themes = {
    'industrial': {
        'ambient_weather_modifier': 'smoggy',
        'crowd_behavior_modifier': 'hurried',
        'base_sensory_palette': ['metallic', 'mechanical', 'industrial'],
        'integration_object_types': ['machinery', 'industrial_debris', 'worker_equipment']
    },
    'residential': {
        'ambient_weather_modifier': 'clean',
        'crowd_behavior_modifier': 'relaxed',
        'base_sensory_palette': ['domestic', 'peaceful', 'lived_in'],
        'integration_object_types': ['personal_items', 'garden_elements', 'home_features']
    }
}
```

**Automated Content Scaling:**
- **Performance Tiers**: Different detail levels for performance optimization
- **Content Density Controls**: Adjust richness based on server load
- **Batch Generation**: Efficient creation of large room networks
- **Consistency Validation**: Automated checks for thematic coherence

### Advanced Features
- **Seasonal Variations**: Descriptions change with game seasons
- **Historical Layering**: Rooms show signs of past events
- **Dynamic Events**: Real-time events affect descriptions
- **Player Memory**: Descriptions change based on player familiarity
- **Procedural Narrative**: AI-assisted content generation for unique descriptions

### Technical Enhancements
- **Caching System**: Optimize description generation
- **Template System**: Modular sensory message management
- **Scripting Integration**: Advanced conditional logic
- **Performance Optimization**: Efficient large-scale description handling
- **Generation API**: Standardized interface for automated room creation

### Automation-Friendly Design Principles

**Separation of Content and Logic:**
```python
# Content pools separate from display logic
class RoomContentManager:
    def __init__(self, room_type, district_theme, variables):
        self.content_pools = self.load_content_pools(room_type)
        self.theme_modifiers = self.load_theme_modifiers(district_theme)
        self.variables = variables
    
    def generate_description_components(self):
        """Generate all components for automated assembly"""
        return {
            'base_description': self.generate_base_description(),
            'sensory_content': self.generate_sensory_content(),
            'integrate_objects': self.generate_integration_objects(),
            'atmospheric_elements': self.generate_atmosphere()
        }
```

**Composable Component Architecture:**
- **Atomic Content Units**: Individual sensory messages as building blocks
- **Combinatorial Assembly**: Mix and match components for variety
- **Inheritance Hierarchies**: District → neighborhood → street → room content flow
- **Override Systems**: Specific rooms can override inherited content

**Data-Driven Configuration:**
```python
# Configuration-driven room generation
automation_config = {
    'content_density': {
        'minimal': {'sensory_messages_per_category': 1, 'integrate_objects_max': 2},
        'rich': {'sensory_messages_per_category': 3, 'integrate_objects_max': 5},
        'maximum': {'sensory_messages_per_category': 5, 'integrate_objects_max': 8}
    },
    'generation_constraints': {
        'performance_budget': 'medium',  # affects complexity of generated content
        'uniqueness_threshold': 0.7,     # how different rooms should be
        'theme_consistency': 'strict'    # how closely to follow district themes
    },
    'scalability_settings': {
        'batch_size': 50,               # rooms to generate per batch
        'cache_generated_content': True,
        'lazy_load_sensory_content': True
    }
}
```

**Validation and Quality Control:**
- **Coherence Checking**: Automated validation of generated content combinations
- **Uniqueness Scoring**: Prevent overly similar adjacent rooms
- **Performance Impact Assessment**: Estimate computational cost of generated rooms
- **Narrative Flow Validation**: Ensure descriptions read naturally

**Extension Points for Automation:**
- **Plugin Architecture**: Third-party content generators
- **Event Hooks**: Callbacks for room generation events
- **Content Validation API**: External quality control systems
- **Generation Metrics**: Track and optimize generation quality

## Implementation Priority

**Phase 1: Foundation**
1. Enhanced return_appearance method with sensory framework
2. Basic sensory message storage and retrieval
3. Simple environmental condition parsing

**Phase 2: Integration**
1. Character enhancement integration
2. Object detail level implementation
3. Weather system integration

**Phase 3: Advanced Features**
1. Complex conditional parsing
2. Dynamic environmental elements
3. ~~Advanced sensory focus commands~~ (not to be built, #1510)

**Phase 4: Optimization**
1. Performance optimization
2. Caching systems
3. Template management tools
