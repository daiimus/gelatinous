# Enhanced Look Command System Specification

`look` builds a room's description from parts: the room's own description and
its sense layers, objects woven into that description (@integrate), weather,
a crowd line, the objects lying about, the people present and where they
stand, a glance at who stands in the rooms next door, and a sentence about
the exits. It builds on Evennia's `return_appearance`. Every part is fresh on
each look: random lines are drawn again every time. Looking at an exit or a
direction (`look <dir>`) has its own renderer (`Exit.get_display_desc`), and
so do `look <character>`, `look <object>`, `examine` and `search`.

Names in the examples below assume the looker knows the people. A stranger
is shown by short description ("A lanky man in a Black Trenchcoat is doing a
handstand."), from `Character.get_display_name`.

## The room render, in order

`Room.appearance_template` is
`{header}{name}\n{desc}\n{things}\n{characters}\n{footer}`. The template is
authoritative. A look reads, top to bottom:

1. **Room name.**
2. **Description**: the sense layers the looker can perceive
   (`Room.get_display_desc`). Then, appended to the first line of the
   description (the end of the description only when it is a single line):
   the @integrate content, then the weather (`Room._compose_room_layers`).
3. **Object listing**: the objects that do not integrate
   (`Room.get_display_things`).
4. **One paragraph**: the crowd line, the characters and their placements,
   the glance at the neighbouring rooms, and the suspicion cue
   (`Room.get_display_characters`). The crowd line opens the paragraph.
5. **Exits**: the exits sentence(s), last (`Room.get_custom_exit_display`,
   reached through `get_display_footer`).

Static content may be cached where appropriate; dynamic content keeps
database queries minimal; a component that is unavailable degrades
gracefully.

`Room._compose_room_layers` is used both for the room you stand in and for
the room you aim into, so a room reads the same either way.

**Spacing** (`Room.format_appearance`). A blank line follows the description
when an object listing or a characters paragraph follows it, and a blank line
follows the object listing. Empty sections add no spacing. The exits run
directly under the characters paragraph. An undescribed room with nothing on
the floor and nobody shown runs its exits directly under "You see nothing
special." Blank lines are placed by position (footer, characters, things,
counted from the end of the render), not by matching text, so a description
authored over several lines gets its blank line too.

Example (weather lines are bold white, `|w ... |n`):

```
Braddock Avenue
Tall, grim-faced tenement buildings flank the way here, seeming to lean in
towards each other and restricting overhead light. |wCool evening air carries
hints of exhaust and distant cooking, while the soft murmur of traffic drifts
from the main thoroughfare.|n

Kathy Cohen-Gold is doing a handstand. Nick Kramer is in a full-split.
The street continues to the west (w) and east (e).
```

## Room attributes

All are `AttributeProperty` on `Room` (`typeclasses/rooms.py`), with
`autocreate=True`.

| attribute | what it does |
|---|---|
| `desc` | the visual description |
| `sense_descs` | optional dict of `auditory`, `olfactory`, `tactile`, `atmospheric` layers shown after the visual `desc`, each only to a looker who has that sense |
| `outside` | weather shows only when it is set; the exit look's weather framing needs it on this room or the destination |
| `crowd_base_level` | int, the crowd base; default 0; 0 means no crowd line, ever (the builder's off switch) |
| `is_sky_room` | marks a sky room, for aerial navigation |
| `type` | the room's kind, for exit wording, crowd pools and the neighbour glance (`street`, `corner store`, `courier service`, `stairwell`, ...) |

`type` is set by a builder, or by the room typeclass (`StreetRoom` sets
`street`, `IndoorRoom` `interior`). Nothing detects it. Builder-defined types
include `courier service`, `cube hotel`, `hospital`, `stairway`.

```python
room.desc = "..."
room.sense_descs = {
    'auditory': "sounds of traffic and urban activity",
    'olfactory': "sewage and raw garbage",
    'tactile': "acidic moisture in the air",
    'atmospheric': "tension of dangerous territory"
}
room.outside = True
room.crowd_base_level = 2
room.is_sky_room = False
room.type = 'street'
```

## Sensory Category Framework

Five sense categories run through the room look: **visual** (lighting,
colours, visual effects, environmental details), **auditory** (ambient
sounds, distant noises, activity sounds), **olfactory** (scents, odours),
**tactile** (temperature, humidity, air movement, surface textures) and
**atmospheric** (mood, tension, environmental pressure). All are treated with
equal importance. A category with no content simply doesn't display. A room
can be described three ways, and the ways are combined without repeating each
other.

Medical condition support: by design, players with sensory limitations see
reduced content. The predicate is one
function, `can_perceive_sense(looker, "visual")` (`world/perception.py`;
`blocked_senses` there for the other senses). Every layer of the room look
honours it:

- the room description (`Room.get_display_desc`, the void line);
- weather and crowd, both split by sense (#591);
- @integrate content, including the flying-object line (#3373, #3479);
- the object listing and the character placements (`get_display_things`,
  `get_display_characters`, #3479);
- the neighbour glance and the doorway glance (#2793);
- the exit's atmospheric half and its authored desc (`Exit.get_display_desc`,
  #3382), and the closed door (`DoorExit.return_appearance`, #3382).

Two things are told to a blind looker on purpose:

- the **exits footer**: a character can know a room's exits by other means
  (the #2793 test records the choice);
- from `look <dir>`, the **kind** of exit the footer or the refused walk
  already names (an edge, a gap, open air, the street's shape, with the
  street counted the way the footer counts it), so the footer, the look and
  the refused walk never disagree about one exit.

The passive stealth roll still runs for a blind looker (Resonance, "the sense
that someone's there", stealth spec §3.1, as on arrival), but it neither
names anyone nor shows the prickling-sense cue to them. A character standing
in the open gives blind eyes nothing, so a cue from a hidden one would make
hiding the worse concealment. Whether a blind character should sense anyone's
presence at all is not decided (see Not decided).

`look <object>`, `look <character>`, `examine` and `search` render through
their own paths and are not covered by this section.

## @integrate objects

An object woven into the room description instead of listed separately.
There is no `@integrate` command: an object integrates by having its
`integrate` attribute set (`db.integrate`). Only Items, graffiti, blood
pools, shop containers and furniture honour it
(`Room.get_integrated_objects_content`); any other object with `integrate`
set stays in the object list.

- **Where**: all integrated content, then the weather, is appended to the
  first line of the room description, before the object listing and the
  crowd/characters paragraph.
- **No limits**: every integrated object shows, stacked together. Several
  objects contributing similar content is acceptable.
- **Order**: by integration priority, ascending (lower appears first). Unset
  priority is 5. Flying objects (throw mechanics) integrate automatically,
  take priority 1 and are added first, so they lead unless an object's
  priority is below 1. Within one priority, creation order breaks the tie.
- **Content**: each object's perceivable `sensory_contributions` are joined
  into its own text, in the order visual, auditory, olfactory, tactile,
  gustatory, then any others. With no contributions the object falls back to
  `integration_desc`, then `integration_fallback`, then "{key} is here"; this
  fallback is visual only.
- **Refresh**: an object may define `refresh_integration_desc()` to update
  its line before it is read (blood pools age this way).
- An integrated object does not appear in the object listing.
- **Graffiti** are integrated items with their own code logic for procedural
  variety. **Art and architecture** are static integrated elements adding
  atmosphere.

Data shape on an integrating object:

```python
obj.db.integrate = True
obj.db.integration_priority = 10   # lower = earlier; unset = 5; flying objects are always 1
obj.db.sensory_contributions = {
    'visual': "bullet-ridden vehicles pass through",
    'auditory': "engine noise and grinding gears",
    'atmospheric': "sense of urban danger"
}
```

Examples by sense: visual "colorful graffiti"; auditory engine sounds, crowd
noise, activity sounds; olfactory vehicle exhaust, food smells, industrial
odours; tactile surface textures, temperature effects; atmospheric tension and
mood. (Vehicles are unbuilt; see Unbuilt.)

## Weather

Weather shows only in rooms with `outside` set
(`WeatherSystem.get_weather_contributions`, `world/weather/weather_system.py`).

- **What a look shows**: one line from each of two different senses the
  looker can perceive (three when the looker is missing a sense), drawn at
  random from the pool for the current weather and time period. Rooms whose
  type has an entry in `ROOM_TYPE_POOLS` (`fire escape` is the one entry) get
  that type's lines mixed into the draw.
- **Senses**: every pool has five: visual, auditory, olfactory, tactile,
  atmospheric. Sight gates visual, hearing gates auditory, smell gates
  olfactory; tactile and atmospheric always show.
- **Where**: appended to the first line of the room description, after any
  @integrate content and before the object listing, characters and exits.
- **Format**: bold white, `|w` ... `|n`.
- **Selection**: the pool key is `weather_type + "_" + time_period` (e.g.
  `clear_midday`, `rain_early_evening`). Every line in a pool is equally
  likely; there are no weights. A fresh draw is made on every look, like
  combat messages. Weather type and time period choose the pool; intensity
  plays no part in selection.
- **No substitution**: weather and crowd lines take no variables. Only the
  room's own description renders time tokens (`render_time_tokens` in
  `Room.get_display_desc`).

**Pools** (`world/weather/weather_messages.py`). `WEATHER_MESSAGES` is built
at import by `_build_weather_messages` from `WEATHER_POOLS` (per weather
type, lines per sense) and `TIME_LIGHT` / `TIME_ACTIVITY` (per-period light
and street-activity lines). Every one of the 19 weather types has all 12 time
periods (`TIME_PERIODS`): 228 weather+time pools, 3,192 lines. Shape:
`WEATHER_MESSAGES['default']['<weather>_<period>'][<sense>] = [lines]`.

**Style**: observational ambience, grounded in the colony's texture (crater
rim, channel, prefab roofs), each line standing alone. Lines avoid
references to any one location. The module docstring
of `world/weather/weather_messages.py` states the authoring principles.
`ROOM_TYPE_POOLS` adds lines for specific kinds of place. Temperature shows
in tactile lines; precipitation in what is seen and heard.

**Intensity tiers.** `WEATHER_INTENSITY` assigns each of the 19 types a tier.
The tier does not shape any message: line length is flat across all four
tiers (mean words per line: mild 8.58, moderate 8.34, intense 8.32, extreme
8.65; no line in the corpus exceeds 13 words), and nothing in
`world/weather/` reads the tier to pick or shape a line. Its readers are
`WeatherSystem.set_weather` (validation), `WeatherSystem.get_weather_intensity()`
(read only by the `@weather` admin command), the `@weather` admin listing in
`commands/CmdAdmin.py`, and two tests, one of which pins
`CrowdSystem.weather_modifiers` to its keys.

| tier | weather types |
|---|---|
| mild | clear, overcast, windy |
| moderate | fog, rain, soft_snow, foggy_rain, light_rain |
| intense | dry_thunderstorm, rainy_thunderstorm, hard_snow, blizzard, gray_pall, tox_rain, sandstorm, blind_fog, heavy_fog |
| extreme | flashstorm, torrential_rain |

**What sets the weather.** `WeatherSystem` is a module-global instance
(`world/weather/__init__.py`) holding `current_weather` in memory,
initialised to `"clear"`. `set_weather` has one caller, the `@weather` admin
command. Nothing advances weather on a clock, so the colony runs `clear`
unless a builder sets it by hand, and reverts at the next reload. The weather
driver is unbuilt by ruling; see Unbuilt.

## Crowd

- **Crowd level** (`CrowdSystem.calculate_crowd_level`,
  `world/crowd/crowd_system.py`): `crowd_base_level` + room-type modifier +
  0.5 per body in the room (NPCs and hidden characters count) + weather
  modifier (`CrowdSystem.weather_modifiers`; rain reduces, clear weather
  increases) + colony-hour modifier (`time_modifiers`), rounded, never below
  0. A `sky` room is always 0.
- **Tiers**: four levels: sparse (1), moderate (2), heavy (3), packed (4 and
  above); 0 is no crowd.
- **The crowd line**: one sentence per look. One sense the looker can
  perceive (any of the five) is picked at random, then one line from it, from
  the pool for the level and the room type (`crowd_profile_for_room_type`:
  shop, market, nightclub, constabulary, residential, interior, an empty pool
  for sky, the street pool otherwise). Pools are in
  `world/crowd/crowd_messages.py`. Bold white, `|w`. It opens the characters
  paragraph.
- **Base 0**: a room with `crowd_base_level` 0 never shows a crowd line,
  however many stand there.
- **Other readers**: the same level drives witness chance
  (`world/director/witness.py`) and the stealth concealment bonus
  (`world/stealth.py`).

`CrowdSystem.weather_modifiers` matches the `WEATHER_INTENSITY` vocabulary,
and a set-equality test pins the two (#3027). Its magnitudes are
shaped-right, not tuned: no system in this game has had its balance pass.

## Object listing

`Room.get_display_things` lists the objects that do not integrate, in one
sentence with conjunctions, and articles every singleton: "You see a
chainsaw, a frag grenade, and a baseball bat." Identical items stack behind
spelled-out quantity words up to fifty. Above fifty a profane euphemism is
chosen at random ("a shitload of ...").

## Characters: placement

Each character shows with a placement sentence: "Kathy Cohen-Gold is doing a
handstand. Nick Kramer is in a full-split." Characters with the same
placement share one sentence ("Sterling Hobbs, Janice Burns, and Dean Keith
are standing here.").

**Hierarchy** (`Room.get_display_characters`): `override_place` >
`temp_place` > `look_place` > "standing here." Above all of them, a hidden
character who is still seen reads with the stealth lurking line
(`world.stealth.lurk_placement`: "lurking in the shadows.", or a nervous face
in the crowd when the room is busy); this line is not stored but applied at
render time. `{aim_target}` in a placement becomes the target's name, or
"aiming carefully." when the target is gone.

- `look_place` and `temp_place` are set by players with `@look_place` and
  `@temp_place` (`CmdLookPlace`, `CmdTempPlace` in `commands/CmdCharacter.py`;
  registered in `commands/default_cmdsets.py`).
- `override_place` is not player-settable and there is no command for it. It
  is an `AttributeProperty` (`typeclasses/characters.py`, category
  `description`) that only the game writes: aiming and showdown
  (`commands/combat/special_actions.py`, `commands/combat/core_actions.py`;
  cleared on movement and when the aim stops), combat entry ("locked in
  combat.", `world/combat/utils.py`), channeled acts (`world/channeled.py`),
  unconsciousness and death (`typeclasses/characters.py`), and one admin
  cleanup (`commands/CmdAdmin.py`).

## The neighbour glance

`Room.get_adjacent_character_sightings` tells the looker who stands in the
rooms next door. It is part of the characters paragraph, after the local
characters. The intent: it encourages interaction and chase scenes.

What the looker reads:

- "You see a lone figure to the south." (one character)
- "You see a group of people standing to the east." (two or more)
- "You see a crowd to the west." / "You see crowds to the north and south."
  (heavy or packed over there, whoever is in it)
- up and down read "above" / "below": "You see a lone figure above.", "You
  see a crowd below."

It is a lightweight scan of the adjacent rooms' contents on each look. It
runs even when the looker is alone in the room, together with the crowd line
and the suspicion cue, and the three share one paragraph alone as with
company.

**Gates**, in effect together:

1. **Sight.** It returns nothing for a looker who cannot see
   (`can_perceive_sense(looker, "visual")`, #2793).
2. **Secret exits.** It walks `_visible_exits(looker)`, not raw `self.exits`,
   so a `view:false()` secret exit is never named (#2588).
3. **Hidden people.** Each counted character must pass `can_perceive(looker,
   obj)`, the stealth presence gate (stealth spec §7): no leak through the
   doorway glance.
4. **Door state (#3750).** It skips any exit whose `blocks_sight()` is true:
   a closed `DoorExit` (a broken one hangs open), a landing's elevator door
   while the car is elsewhere, the car's `out` while it moves.
   `Exit.blocks_sight()` is the one predicate; the exit look's far-room people
   (`Exit.get_display_desc`) ask it too.
5. **A sightline into open ground (#3753).** It skips a destination whose
   `type` is not in `world.crowd.crowd_messages.OPEN_AIR_ROOM_TYPES` (street,
   alley, market, bridge, rooftop, courtyard, balcony, fire escape, farm,
   hull, garden, agridome, stairwell; `room_type_is_open_air`). The list is
   the room types you can see into from next door, so a pursuer sees where
   someone went and a crowd can hide them (#3759, 2026-10-24); it is not a
   list of outdoor rooms, whatever its name says. Owner, 2026-10-17 (#3753):
   "Streets, sure. Cubes? Not so much." / "I think it makes more sense for us
   to have room types...which I think we already do. It's a very standard mud
   design." Farm, hull, garden and agridome joined the list on 2026-10-19
   (owner: "I feel like those types should allow 'glance'"). No room was
   retyped for this. The word is the whole test,
   so two words take in more than open ground: `market` covers the open-air
   Shipbreaker yard and the covered galleries (`MarketRoom`, `outside=False`)
   alike; `farm` covers the Greenhaus growing platforms and their 6 ground
   bays (`outside=False`). `stairwell` covers the 17 Brackett stairs and the
   33 Greenhaus stairways (#3757), so a figure on the stairs shows from the
   platform or landing beside them and from the flight above or below ("You
   see a lone figure above.", #3755). Any other type (a rented unit, a
   tenement hall, the constabulary) is never glanced into, open door or not,
   and an untyped room is treated the same. `sky` is not listed: nobody
   stands in the air. The Brackett and Halcyon units are untyped. `look
   <door>` through an open door is its own renderer and still shows who is
   inside. Every room of the types farm, hull, garden and agridome has crowd
   base 0 on live, so the glance into them always names figures and never a
   crowd. In play on 2026-10-19: `garden` is the six Greenhaus lawns; no exit leads into any
   of the nine `hull` rooms, so that word changes nothing yet; the five
   `agridome` rooms include the Pre-Fab Agridome airlock, where a keeper
   stands, so Kaspar Street reads "You see a lone figure to the south."
6. **The far crowd (#3753).** Owner, 2026-10-17: "I think open air should be
   a combination of room types and crowd size.", then "1." on: room type says
   the far room is open air, its crowd size says what you can make out. Heavy or packed
   (`crowd_system.crowd_hides_figures`: the level the room's own crowd line
   reads, and silent at base 0, however many stand there) the glance reports
   the crowd and no figures; thinner, the lone-figure / group sentences. The
   level counts hidden bodies like any other (#2497), so a hider can tip a
   far street from moderate to heavy and switch the crowd sentence on; that
   is the density the hider blends into. `look <direction>` reads the same
   level for its crowd wording only when someone visible stands beyond, so
   with nobody visible there the crowd sentence is the one line from next
   door that shows the density moved; it names no one, and anyone standing in
   that street reads the same tier from its own crowd line (round-4 review).
   Unlike the glance, `look <direction>` does not honour base 0 (see Looking
   at an exit).

**Two rooms are never glanced from or into** (review of #3753):

- a sky cell, which shows no exits and so names no directions either (a
  faller passing a populated roof would otherwise read "You see a lone figure
  to the east." in every cell);
- the room the looker stands in. The aim view renders the far room, and its
  exit back would otherwise report the shooter's own company. The far room's
  own glance into its other neighbours does render in the aim view, like the
  rest of that room, whether or not anyone stands in the far room.

A live census on 2026-10-17, with the people then present and under clear
skies (each body adds 0.5, so any open-air room with a base above 0 reads
heavy once enough gather; rain and worse pull every level down): 48 streets
and 9 markets reached heavy at the shift-change peaks, no other open-air room
did, and at night none.

## The exits footer

`Room.get_custom_exit_display(looker)` groups the exits and
`Room.format_exit_groups(exit_groups)` writes them, in natural language
instead of a repetitive list: "The street continues to the west (w) and east
(e)."

**Which exits are listed.** It walks `Room._visible_exits(looker)`: a
view-locked (`view:false()`, secret) exit is not listed unless this looker
has found it (`db.found_exits`, #2588). Exits into sky rooms are not listed
unless they are edges or gaps, and a sky room lists no exits at all.

**Alias.** Each exit shows its key and its shortest alias in parentheses:
"north (n)", "elevator (in)" (not "(car)"). With no alias, or when the alias
is the key itself, there are no parentheses: "north".

**Grouping.** Each exit is grouped by its kind: an edge, a gap, or the far
room's `type`.

- **Street wording.** For each exit into a `street` room, the destination's
  exits that lead to other `street` rooms are counted (exits to other kinds
  of room do not count): 0 or 1 is a dead-end ("There is a dead-end ..."),
  exactly 2 is a continuing street ("The street continues ..."), 3 or more is
  an intersection ("There is an intersection ..."). This is worked out when
  the line is written; nothing is stored. `street` is the only stored type
  here; "dead-end", "continues" and "intersection" are wording.
- **Other types**: "There is a [type] to the [direction]", one sentence per
  type.
- **Inside a venue**, exits to rooms of the room's own type read "The {type}
  continues ..." instead of "There is a ...".
- **Fallback**, when the far room has no type: "There is an exit to the
  south (s)."
- **Plural**: two or more exits of one kind take the plural ("There are edges
  to the south (s) and west (w)."). Articles come from
  `world.grammar.get_article`, and irregular plurals from `TYPE_PLURALS`
  ("constabularies").
- **Order**: groups are never joined with "and". Each gets its own sentence,
  in this order: dead-ends, continuing streets, intersections, each custom
  type, edges, gaps, then other exits.

Examples:

```
The street continues to the north (n) and south (s).
There is a courier service to the west (w). There is a cube hotel to the east (e).
The street continues to the north (n). There is a hospital to the east (e). There is an edge to the south (s).
The street continues to the north (n). There is an intersection to the south (s). There is a stairway to the west (w).
There are exits to the east (e), west (w), C01 (01), C02 (02), C03 (03), C04 (04), C05 (05), and C06 (06).
```

**Up and down are not compass points (#3755, 2026-10-23).** Owner: "Up and
down are very common exit names - so we should probably account for them."
Every group renders through `Room.format_exit_phrases`: compass and named
exits behind one "to the", and exits keyed `up` / `down`
(`typeclasses.rooms.VERTICAL_EXITS`) as a phrase of their own with no
preposition: "up" / "down" in a "continues" sentence, "above" / "below" in a
"there is" sentence or the glance. So a vertical exit never reads "continues
to the up (u)".

| sentence | reads |
|---|---|
| continues | The fire escape continues up (u) and down (d). |
| continues, mixed | The tenement continues to the southeast (se). It continues up (u) and down (d). |
| there is | There is a fire escape above (u). |
| there are | There are exits above (u) and below (d). |
| there is, mixed | There is an exit to the north (n). There are exits above (u) and below (d). |
| glance | You see a lone figure above. |
| glance, crowd | You see a crowd below. |

A group holding both kinds gets two sentences, compass first
(`Room.format_exit_phrases` returns one phrase per kind;
`Room.continues_sentences` writes "It continues ..." for the second), so the
"and" never doubles. The joined form ("to the southeast (se), and up (u) and
down (d)") would show in 42 live rooms, the 15 Brackett stairwells and 27
Greenhaus stair cores; owner, shown both (review of PR #3756): "That's fine"
to the split. The exit's key decides, so `hatch`, `breach` and `drop` (exits
that merely answer to `down`) stay named exits. Named exits ("to the
window", "to the 3B") keep "to the" by the same ruling: "The others can be
put off for now. I don't take issue with them."

## Looking at an exit: `look <dir>`

`Exit.get_display_desc` replaces Evennia's generic "This is an exit." It
describes the passage itself, then the people beyond.

1. **Authored desc.** An exit's authored desc is shown first and the
   atmospheric line follows it; it does not replace it. A closed door
   (`DoorExit`) shows only its own desc and "It is closed." or "It is sealed;
   ..."
2. **The atmospheric line** (`Exit._get_atmospheric_description`), the first
   that applies: edge and gap together, edge, gap (edges and gaps need the
   jump command), a sky destination ("The opening leads into open air, where
   gravity makes the rules."), a street destination's shape
   (`Exit._analyze_street_context`: dead-end, intersection or continuing
   street, from the destination's exit counts and types), a `fire escape`
   destination (its own lines keyed by exit: window, up, down, drop, else a
   default), the direction defaults (compass points, up, down, in, out), and
   last "The passage stretches into shadows and uncertainty." `{time}` tokens
   are rendered. The atmospheric lines, including the direction defaults, are
   written to match the game's noir aesthetic.
3. **Weather framing** ("Through the steady rain, the street stretches
   eastward...") is added only to the street-shape sentence, only when this
   room or the destination is `outside`, and never in clear weather
   (`Exit._get_weather_context`).
4. **Far-room people** (`Exit._get_exit_character_display`): the characters
   in the room the exit leads to, unless the exit blocks sight
   (`Exit.blocks_sight()`, a shut door). Hidden characters are left out, and
   a blind looker gets no names.

A blind looker is told only the exit's kind, or "A passageway leading
elsewhere." A looker who is aiming is told "You cannot see any further."
instead of an exit description, keeping their combat focus.

**Far-room crowd wording.** The people are worded by the far room's crowd
level, `crowd_system.calculate_crowd_level()`, raw: unlike the glance and the
crowd line, `look <direction>` does not honour base 0, so a base-0 room with
enough people in it reads as a crowd here while its own crowd line stays
silent. Any number of characters joins with proper grammar.

| far crowd | reads |
|---|---|
| heavy / packed (3+) | To the west you can see a bustling crowd of people going about their business, amidst them John Wilson. |
| moderate (2) | To the west you see figures moving through the urban maze, among them Juan and Maria. |
| sparse (1) | To the west you catch glimpses of movement in the shadows, including Juan. |
| empty (0) | To the west you see Juan. |

**Direction words.** Only the four compass keys north, south, east and west
get "To the ..."; any other exit key is capitalised as given ("Northeast you
see ...", "Up you see ..."), without the "above" / "below" phrasing the
footer and the glance use.

Examples:

```
Through the gentle snowfall, the street stretches westward through the urban canyon, where scattered streetlight illuminates the continuing path between deteriorating storefronts. To the west you can see a bustling crowd of people going about their business, amidst them Janice Burns and Dean Keith.

The street stretches eastward through the urban canyon, where scattered streetlight illuminates the continuing path between deteriorating storefronts. To the east you see figures moving through the urban maze, among them Sterling Hobbs and Charlene Fisk.

To the north you catch glimpses of movement in the shadows, including Maria Santos.

To the south you see Juan Rodriguez.
```

**Residence doors (#3508, 2026-10-13).** Looking at a unit's corridor-side
door, the one the rental build registered as `cube.db.cube_door`, ends with
the tenancy word: `Occupied.` for a live resident, `Vacant.` when the unit
can be claimed, `Being vacated.` while a mover's 48-hour relocation window
holds it off the market (`world.rental.residence_status`,
`DoorExit._residence_status`). Open or closed, sighted lookers only; the
unit's own door leading out says nothing. The look is the touch that prunes
a dead tenancy, so a unit whose tenant was deleted reads Vacant the moment
anyone looks at its door.

## Targeted look and aiming

- `look` / `l`: the full room description.
- `look <character>`: detailed character examination.
- `look <object>`: detailed object examination.
- `examine`: no `examine` command exists in this repo (`commands/` defines
  none and `commands/default_cmdsets.py` adds none), so `examine` is
  Evennia's stock builder-locked debug command: no interaction hints, and not
  a player verb. The game's deep-examination verbs are `inspect` / `autopsy`
  for corpses and blood pools (`CmdInspect` in `commands/forensics.py`, alias
  `autopsy`). Whether "`examine <target>` — deep examination with
  interaction hints" is still wanted is not decided (see Not decided).

**While aiming (#3596, 2026-10-24).** `look <target>` while aiming is
`commands.CmdLook`: it resolves the target in the aimed room first
(`Room.aimed_room_for`, the same seam the aim view reads), a person by
description through the identity pipeline, then a thing by name, then falls
back to the ordinary reach (your room, your pockets). Ordinals count the
aimed room alone. Nothing else widens: `Character.get_search_candidates` does
not add the aimed room to the default search, so `put`, `scan`, `diagnose`,
`tune`, `remember`, `to`, `whisper` and targeted emotes reach this room only
while aiming. No command's default `caller.search()` reaches the aimed room.
When not aiming, targeted look behaves as ever. Owner, on the audit: `look
<description>` down the barrel works; emotes, `to` and `whisper` across the
aim do not.

`attack` and `throw` name the aimed room themselves. `attack` does not use
`get_search_candidates`: it resolves the aimed exit itself and scopes
candidates to the people in the far room only (`CmdAttack.func` in
`commands/combat/core_actions.py`, passing them to
`resolve_character_target`), so while aiming the current room drops out of
scope entirely.

Overturned design: targeted commands were to search both the current and
the aimed room, with one ordinal count across both, for every command using
`caller.search()` (via `Character.get_search_candidates`). #3596
(2026-10-24) replaced this with the scheme above.

## Sensory focus commands: not to be built

`listen`, `smell` and `feel` (focus on auditory, olfactory, tactile
information) were planned. Owner decision, 2026-08-03 (#1510): they do not
exist and will not be built. `look` is the time-tested MUD verb and already
surfaces every sense layer the room carries, perception-gated. Separate
per-sense verbs would be syntax for its own sake.

## Links to other systems

- Character condition and status affect perception and sensory input.
- The proximity system affects how characters are positioned socially.
- Crowd density influences character interactions and gives the room its
  social context.
- Held items affect available interactions. Equipment affects sensory
  perception. Item states show in descriptions.
- Integration with throw mechanics: flying objects integrate (see @integrate
  objects).

The neighbour glance once had no visibility logic at all; the six gates above
were added deliberately. The intent it served, interaction and chase scenes,
stands.

## Unbuilt

### The weather driver — 📋 UNBUILT (#3028)

Everything in Weather above is what happens once a weather is set. Nothing
sets one. Owner ruling, 2026-09-08 (#3028, raised from the audit as #2446
§4):

> "This isn't done. Ultimately, there will be elements of the game like
> mining, the terraformer, electrical usage, etc. and maybe even
> pseudo-weather patterns that are seasonal but they'll all influence
> the system. Weather isn't fully wired in yet."

Weather is meant to be an OUTPUT of colony systems, not an independent
generator. It is gated on mining, the terraformer, electrical usage, and
seasonal pseudo-weather patterns. Until those exist there is nothing for a
weather driver to read. Until then the 19 weather types and ~3,200 authored
lines are effectively unreachable in play, and the consumers of weather
(crowd density, and through it `world/director/witness.py` and
`world/stealth.py`) are wired-but-unfed.

This is a known gap, not a defect. Do not "fix" it by adding persistence or a
random weather ticker; both would pre-empt the design.

### Vehicles — 📋 UNBUILT (no issue)

Moving objects that would contribute dynamic sensory elements through
@integrate ("bullet-ridden vehicles pass through on drive-bys"). No vehicle
objects exist.

### Ambient Message System — 📋 UNBUILT (no issue)

No ticker or interval script emits atmospheric messages; the weather and
crowd pools are read at `look` time only. What is wanted:

- **Periodic atmospheric messages** at random intervals (every 2-5 minutes)
  to players in a room, without player action: brief flavour text that keeps
  environmental awareness and reflects current conditions.
- **Context**: informed by the same systems as `look`: weather, crowd level,
  time of day, room characteristics.
- **Pools**: leverage the weather and crowd pools with ambient-specific
  variants; different ambient types for different room types or themes.
- **Frequency management**: configurable timing to prevent spam. The design
  sketch uses a 3-minute base interval with +/- 1 minute variance.
- **Selection in the sketch**: conditions are collected (weather when not
  clear, as `weather_<type>`; crowd level when not sparse, as
  `crowd_<level>`; time period when evening, night or dawn, as
  `time_<period>`). With more than one condition, a combined pool keyed by
  the sorted conditions joined with `_` is tried first; then each single
  condition's pool. A random pool among those found, then a random line.
- **Delivery in the sketch**: sent to everyone in the room with `|K ... |n`
  formatting, excluding disconnected players.
- **Player filtering**: optional ambient preferences (full / reduced / off).

Example messages:

- Weather-based: "The rain patters against the ground with a soft yet
  relentless persistence."
- Crowd-based: "A group of pedestrians hurries past, their footsteps echoing
  off wet pavement."
- Time-based: "The evening shadows grow longer, deepening the gloom between
  streetlights."
- Combined factors: "Despite the drizzle, street vendors continue their
  calls, their voices mixing with the hiss of tires on wet asphalt."

Example pools from the sketch:

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

### Time cycling in other systems — 📋 UNBUILT (no issue)

Weather lines, the crowd level and time tokens in room descriptions follow
the colony clock. Day/night variation in other systems is unbuilt.

### Character presence in the room look — 📋 UNBUILT (no issue)

Sensory-aware character descriptions in the room look: visual (equipment,
posture, visible condition), auditory (sounds a character makes, movement
noise), atmospheric (how characters affect the room's tension and mood).
What characters visibly hold, weapon and equipment visibility from wielded
items, and health status from the combat system, shown with their placement.
A stranger's short description already names a wielded weapon or explosive
(`Character.get_distinguishing_feature`); the placement line shows no other
equipment and no health status. The wanted shape:

```
Kathy Cohen-Gold is doing a handstand, her Colt M1911 pistol secured in
her belt holster. Nick Kramer is in a full-split, appearing alert and
scanning the shadows with practiced wariness. Sterling Hobbs, Janice Burns,
and Dean Keith are standing here.
```

The same mock-up shows a crowd line written as room integration ("Despite
the fortress-like precautions, there's a neighborhood warmth here — this is
where locals come for milk at midnight.") and an integrated object with its
own paragraph ("A manhole cover lies slightly askew near the curb, its edges
worn smooth by countless footsteps.").

### Future extensions — 📋 UNBUILT (no issue)

Ideas the specification records without an issue:

- **Component systems**: economic activity (market sounds, commercial
  atmosphere); security level (patrol presence, safety indicators); seasonal
  changes (long-term environmental variation); dynamic environmental
  elements.
- **Integration**: weather affecting crowd behaviour; player actions
  affecting room atmosphere; historical layering (past events showing in
  descriptions); dynamic real-time events in descriptions; player memory
  (descriptions change with familiarity); procedural, AI-assisted narrative.
- **Objects**: interaction hints, proximity-based hints, state-aware
  descriptions; object detail levels.
- **Room data**: per-room sensory message pools, an environmental-state
  record (weather, time of day, crowd level, activity level) and a room theme
  (style, condition, lighting, size), with room themes and architectural
  details shaping sensory messages; interactive environment elements.
- **Technical**: complex conditional parsing; caching of description
  generation; a template system for sensory messages and template management
  tools; scripting integration for conditional logic; performance
  optimisation for large-scale description handling; a generation API.
- **Scriptable city generation**: room templates (a base description template
  with variables such as `{{street1}}`, `{{street2}}`, `{{size}}`, sensory
  pool names per sense, objects to auto-integrate); message pool inheritance
  from parent rooms; template variables driving message selection;
  @integrate objects generated from room type; district themes (weather and
  crowd modifiers, a sensory palette, integration object types) coordinating
  a neighbourhood; content-density tiers and performance budgets; batch
  generation; inheritance district → neighbourhood → street → room with
  per-room overrides; automated checks for coherence, uniqueness between
  adjacent rooms, performance cost and narrative flow; plugin generators,
  event hooks, a content-validation API and generation metrics. Content is
  kept separate from display logic; individual sensory messages are atomic
  units combined for variety; density tiers (minimal: 1 message per
  category, at most 2 integrated objects; rich: 3/5; maximum: 5/8) adjust to
  server load; a uniqueness threshold (0.7 in the sketch) between rooms;
  batches of 50 rooms.

Suggested order: character and object detail first, then conditional
parsing and dynamic environment, then performance, caching and template
tools.

## Not decided

- Should a blind character sense anyone's presence at all? Today the passive
  stealth roll runs for a blind looker but neither names anyone nor shows the
  cue.
- Is "`examine <target>` — deep examination with interaction hints" still a
  plan, or should it join the `listen` / `smell` / `feel` ruling (#1510)?
- Is the Ambient Message System (periodic room messages) still wanted, and
  under which issue?
- Are health status and proximity in the room's character listing still
  wanted?

## Related documents

- `specs/STEALTH_AND_DETECTION_SPEC.md`: §3.1 (Resonance, the passive roll
  on arrival), §7 (the presence gate, no leak through the doorway glance).
