# Enhanced Look Command System Specification

> **Status:** 🚧 **PARTIAL** — features 1-12 shipped; **§13 Ambient Message System not built**. Verified 2026-08-02.
>
> **⚠ Spec-vs-code corrections — the following claims were FALSE when audited:**
> - The header's "Implementation Status: COMPLETED ✅" contradicted its own "12/13 Features Complete". 12/13 is correct.
> - **§Sensory Focus Commands (`listen`, `smell`, `feel`) do not exist and will not be built** (owner decision, 2026-08-03): `look` is the time-tested MUD verb and already surfaces every sense layer the room carries, perception-gated. Separate per-sense verbs would be syntax for its own sake. The section is retained as history, not as a plan.
> - §13 Ambient Message System is confirmed unbuilt — no ticker or interval script emits atmospheric messages; the pools are pulled at `look` time only.
> - Crowd-aware directional look **is** built (`typeclasses/exits.py:662`), contrary to earlier notes.

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

### 1. Character Placement System
- **Natural Language Positioning**: Implemented `@temp_place`, `@look_place`, `@override_place` commands
- **Hierarchy **Example Implementation:**

**Component Assembly Example:**
```
Base Room: "Large intersection where Sinn crosses Knife"
+ ✅ Weather Integration: "cool evening air carries hints of exhaust and distant cooking, while the soft murmur of traffic drifts from the main thoroughfare"
+ Crowd (moderate): "foot traffic starting to get heavy but personal space"
+ @integrate Vehicles: "bullet-ridden vehicles pass through on drive-bys"
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
- Messages selected randomly from appropriate time+weather pools  
- Integrates directly into room description flow after base text
- All 17 weather types covered with intensity-appropriate message complexityverride_place` > `@temp_place` > `@look_place` > default fallback
- **Character Commands**: `CmdLookPlace` and `CmdTempPlace` classes in `commands/CmdCharacter.py`
- **Natural Language Output**: Characters show with placement descriptions like "Kathy Cohen-Gold is doing a handstand. Nick Kramer is in a full-split."

### 2. Room Section Spacing  
- **Proper Line Breaks**: Added conditional spacing between room description, items, characters, and exits
- **Template Integration**: Modified `appearance_template` and `format_appearance()` method
- **Clean Visual Flow**: Empty sections don't create extra spacing

### 3. Natural Language Items
- **Grammar-Aware Display**: "You see a chainsaw, frag grenade, and baseball bat" with proper conjunctions
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
- **Auto-Creation**: All attributes use `autocreate=True` for seamless integration

### 6. Exit Display Enhancements
- **Alias Integration**: Shows direction and primary alias: "north (n)"
- **Edge/Gap Support**: Integrates edges and gaps into natural language flow
- **Fallback Handling**: Generic exit format for unknown destination types
- **Bug Fixes**: Resolved AliasHandler indexing issues with proper `.all()` method usage

### 7. @integrate Object System
- **Sensory Integration**: Objects contribute to room description via sensory categories
- **Priority System**: Integration priority controls display order (lower = first)
- **Flying Object Integration**: Flying objects automatically integrated with priority
- **Sensory Contributions**: Objects use `sensory_contributions` dict for rich integration
- **Fallback System**: `integration_desc` and `integration_fallback` for simple integration
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
- ✅ **Sensory Categories**: Visual, auditory, olfactory, atmospheric weather contributions
- ✅ **Intensity-Based Messages**: Weather types scaled by intensity (mild/moderate/intense/extreme)
- ✅ **Time Period Variations**: Weather messages vary by time of day for atmospheric consistency
- **Comprehensive Coverage**: All 17 weather types from `WEATHER_INTENSITY` mapping implemented
- **Noir/Cinematic Style**: Adult-focused atmospheric descriptions with proper intensity scaling
- **Formatting Integration**: Weather text displayed with |w (bold white) formatting
- **Message Pool Architecture**: Extensive message pools following combat system patterns
- **Universal Descriptions**: Weather-focused messages avoid location-specific references

**Weather Types Implemented:**
- **Mild Intensity**: clear, overcast, windy (8-12 word messages)
- **Moderate Intensity**: fog, rain, soft_snow, foggy_rain, light_rain (12-16 word messages) 
- **Intense Intensity**: dry_thunderstorm, rainy_thunderstorm, hard_snow, blizzard, gray_pall, tox_rain, sandstorm, blind_fog, heavy_fog (16-20 word messages)
- **Extreme Intensity**: flashstorm, torrential_rain (20+ word epic messages)

**Technical Implementation:**
- Message pools in `world/weather/weather_messages.py` with 4 sensory categories per weather type
- Integration via `world/weather/weather_system.py` with proper |w formatting
- Room integration through modified `return_appearance()` method in `typeclasses/rooms.py`
- Weather appears directly in room description after base text, before characters/exits

### 9. Crowd System ✅ 
- **Population Density**: Crowd levels affecting room atmosphere based on room type, weather, and character presence
- **Dynamic Descriptions**: Crowd-based sensory messages with 4 intensity levels (sparse/moderate/heavy/packed)
- **Activity Integration**: Crowd noise, movement, and presence effects integrated into room descriptions
- **Weather Integration**: Weather conditions affect crowd levels (rain reduces, clear weather increases)
- **Message Pool Architecture**: Following weather system patterns with sensory categories and random selection

**Technical Implementation:**
- Message pools in `world/crowd/crowd_messages.py` with visual, auditory, atmospheric categories
- Integration via `world/crowd/crowd_system.py` with proper |W formatting  
- Room integration through modified `get_display_characters()` method in `typeclasses/rooms.py`
- Crowd messages appear before character listings with environmental context

### 10. Adjacent Room Character Visibility ✅
- **Spatial Awareness**: Detect characters in adjacent rooms through exits
- **Simple Detection**: No complex visibility logic - encourages interaction and chase scenes
- **Natural Language**: "You see a lone figure to the south" (1 character) or "You see a group of people standing to the east" (2+ characters)  
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
- **Weather Integration**: Integrates with existing weather system for enhanced atmospheric context
- **Edge/Gap Support**: Specialized descriptions for edge and gap exits requiring jump commands
- **Street Context Analysis**: Analyzes destination room layout for dead-end/intersection/continuing street descriptions
- **Directional Defaults**: Noir-aesthetic atmospheric descriptions based on cardinal directions
- **Character Display Integration**: Shows other characters in current room following standard patterns
- **Aiming Restrictions**: Blocks exit examination when character is aiming (maintains combat focus)
- **Custom Description Support**: Maintains existing @desc functionality as priority override
- **Fallback System**: Graceful degradation with atmospheric fallbacks for edge cases

**Technical Implementation:**
- Custom `get_display_desc()` method in Exit class overriding DefaultExit behavior
- Integration with weather system for contextual atmospheric descriptions  
- Street type analysis using destination room exit counting and type classification
- Specialized handling for edge/gap exits, sky rooms, and custom room types
- Character display using current room contents (not destination room)
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
- **Weather Integration**: Weather context appears in directional descriptions ("Through the gentle snowfall, the street stretches westward...")
- **Stylized Descriptions**: Atmospheric descriptions matching game's noir aesthetic
- **Dynamic Character Presentation**: Characters presented with crowd context rather than generic "standing here" format
- **Natural Language Flow**: Proper directional phrasing ("To the west you see..." / "To the north you can see...")

**Crowd Level Integration:**
- **Heavy/Packed Crowds (Level 3+)**: "To the west you can see a bustling crowd of people going about their business, amidst them John Wilson."
- **Moderate Crowds (Level 2)**: "To the west you see figures moving through the urban maze, among them Juan and Maria."
- **Sparse Crowds (Level 1)**: "To the west you catch glimpses of movement in the shadows, including Juan."
- **Empty Areas (Level 0)**: "To the west you see Juan."

**Technical Implementation:**
- Integrated with existing crowd system via `crowd_system.calculate_crowd_level()`
- Weather context integration through exit weather system
- Directional context detection using exit key analysis
- Graceful scaling for any number of characters with proper grammar
- Maintains existing character display functionality while enhancing atmospheric presentation

**Example Outputs:**
```
# Heavy crowd with weather:
"Through the gentle snowfall, the street stretches westward through the urban canyon, where scattered streetlight illuminates the continuing path between deteriorating storefronts. You can see a bustling crowd of people going about their business, amidst them Janice Burns and Dean Keith."

# Moderate crowd, no weather:
"The street stretches eastward through the urban canyon, where scattered streetlight illuminates the continuing path between deteriorating storefronts. You see figures moving through the urban maze, among them Sterling Hobbs and Charlene Fisk."

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
- **Complementary Description**: Multiple approaches to describing same space, combined artfully

### 2. Component-Based Description Assembly

**Assembly Order:**
1. **Room Name & Base Description**: Foundation sensory content
2. **@integrate Object Integration**: Objects stacked at end of room description
3. **Weather System Contribution**: ✅ **Current weather sensory additions via integrated weather system**
4. **Crowd System Contribution**: Current crowd level sensory additions
5. **Traditional Object Listing**: Non-integrated objects listed separately
6. **Smart Exit Descriptions**: Context-aware exit information

### 3. @integrate Object System

**Integration Mechanism:**
Objects with `@integrate` attribute appear at end of room description, stacking together without limits.

**Integration Stacking:**
- **No Limits**: All @integrate objects display together
- **Stacking Order**: Objects stack in discovery/creation order
- **No Conflicts**: Multiple objects contributing similar content is acceptable
- **End Positioning**: @integrate content appears after base room description but before weather/crowds

**Enhanced Integration by Sensory Category:**
- **Visual Integration**: "bullet-ridden vehicles pass through", "colorful graffiti"
- **Auditory Integration**: Engine sounds, crowd noise, activity sounds
- **Olfactory Integration**: Vehicle exhaust, food smells, industrial odors
- **Tactile Integration**: Surface textures, temperature effects
- **Atmospheric Integration**: Tension, mood contributions

**Special Integration Systems:**
- **Graffiti System**: @integrate items with enhanced code logic for procedural variety
- **Vehicle System**: Moving objects that contribute dynamic sensory elements
- **Art/Architecture**: Static integrated elements adding atmosphere

### 4. Dynamic Message Pool Systems

**Weather System Design:**
✅ **Implemented with comprehensive message pools following combat system architecture:**
```python
# Located in world/weather/weather_messages.py
weather_messages = {
    'default': {
        'rain_evening': {
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
- **17 Weather Types**: Complete coverage from mild (clear, overcast) to extreme (torrential_rain, flashstorm)
- **Time Variations**: Weather messages vary by time of day (clear has 12 time periods, others have 1-4)
- **Intensity Scaling**: Message length/complexity scales with weather intensity level
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
- **Noir/Cinematic Style**: Adult-focused atmospheric writing with sophisticated descriptions
- **Universal Descriptions**: Weather messages avoid location-specific references for broad applicability

**Message Pool Structure:**
✅ **Implemented with comprehensive structure:**
```python
# Located in world/weather/weather_messages.py
WEATHER_INTENSITY = {
    # Mild weather (8-12 word messages)
    'clear': 'mild', 'overcast': 'mild', 'windy': 'mild',
    # Moderate weather (12-16 word messages)
    'fog': 'moderate', 'rain': 'moderate', 'soft_snow': 'moderate', 
    'foggy_rain': 'moderate', 'light_rain': 'moderate',
    # Intense weather (16-20 word messages)
    'dry_thunderstorm': 'intense', 'rainy_thunderstorm': 'intense',
    'hard_snow': 'intense', 'blizzard': 'intense', 'gray_pall': 'intense',
    'tox_rain': 'intense', 'sandstorm': 'intense', 'blind_fog': 'intense', 
    'heavy_fog': 'intense',
    # Extreme weather (20+ word epic messages)
    'flashstorm': 'extreme', 'torrential_rain': 'extreme'
}

WEATHER_MESSAGES = {
    'default': {
        'clear_midday': { 'visual': [...], 'auditory': [...], 'olfactory': [...], 'atmospheric': [...] },
        'rain_evening': { 'visual': [...], 'auditory': [...], 'olfactory': [...], 'atmospheric': [...] },
        'torrential_rain_night': { 'visual': [...], 'auditory': [...], 'olfactory': [...], 'atmospheric': [...] }
        # ... 44 total weather+time combinations implemented
    }
}
```
**Selection Logic**: `weather_type + "_" + time_period` determines message pool (e.g., `clear_midday`, `rain_evening`)
**Coverage**: All 17 weather types implemented with 1-12 time period variations each
**Integration**: Weather system in `world/weather/weather_system.py` selects and formats messages with |w bolding

### 5. Smart Exit System Enhancement

**Room Type System:**
- **Storage**: `room.db.type` attribute for room classification
- **Auto-Detected Types**: `street`, `intersection`, `dead-end` (based on adjacent room analysis)
- **Custom Types**: `courier service`, `cube hotel`, `hospital`, `stairway` (builder-defined)
- **Integration**: Auto-detected and custom types work together for mixed scenarios

**Auto-Detection Rules:**
- **Intersection**: 3+ exits leading to rooms with `type="street"`
- **Dead-end**: 1 exit from a room with `type="street"`
- **Street**: Connected to other street-type rooms in linear fashion

**Natural Language Exit Patterns:**
1. **Grouped by Type**: "The street continues north and south"
2. **Individual Destinations**: "There is a courier service to the west and a cube hotel to the east"
3. **Mixed Integration**: "The street continues north. There is a hospital to the east and an edge to the south"
4. **Fallback Format**: "There is an exit to the south (s)" when no type information available

**Exit Display Examples:**
```
Example 1 (Mixed types):
"The street continues south and north. There is a courier service to the west and a cube hotel to the east."

Example 2 (Utilitarian/Complex):  
"There are exits to the east (e), west (w), C01 (01), C02 (02), C03 (03), C04 (04), C05 (05), C06 (06)."

Example 3 (Simple mixed):
"The street continues north. There is an intersection to the south and a stairway to the west."
```

**Alias Integration:**
- **Standard Format**: "north (n)" - shows direction and first alias
- **No Alias**: "north" - omits parentheses when no alias exists
- **Complex Exits**: Custom exit names with their primary alias

**Edge/Gap Integration:**
- **Natural Language**: "There is an edge to the south and west"
- **Mixed Content**: Edges integrated with other exit types naturally
- **Multiple Edges**: Grouped using natural language conjunctions

**Implementation Logic:**
1. **Analyze Destinations**: Check each exit's destination `room.db.type`
2. **Group by Type**: Collect exits leading to same destination types
3. **Apply Grouping Rules**: "street continues" for multiple street destinations
4. **Format Individual Types**: "There is a [type] to the [direction]"
5. **Integrate Edges/Gaps**: Include in natural language flow
6. **Fallback Handling**: Use generic format for unknown types

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
- Optional probability weights for rare/common messages
- Variable substitution for dynamic content
- Conditional pools based on environmental state

### Component Integration System

**Assembly Order:**
1. **Room Name**: Static title
2. **Base Description**: Core room visual content  
3. **@integrate Objects**: Stacked at end of room description text
4. **Sensory Layer Assembly**: Weather/crowd/atmospheric content
5. **Character Listings**: Enhanced character descriptions
6. **Traditional Objects**: Remaining visible objects
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
- Efficient variable substitution system
- Minimal database queries for dynamic content
- Graceful degradation when components unavailable

## Technical Implementation

### Enhanced Room Attributes

**Sensory Message Storage:**
```python
# Base sensory content
base_sensory = {
    'visual': "pungent smell floods your nostrils",
    'auditory': "sounds of traffic and urban activity", 
    'olfactory': "sewage and raw garbage",
    'tactile': "acidic moisture in the air",
    'atmospheric': "tension of dangerous territory"
}

# Integration settings
integration_settings = {
    'allow_weather': True,
    'allow_crowds': True,
    'weather_intensity': 'normal',
    'crowd_base_level': 'moderate'
}

# Room type for smart exit labeling
room.db.type = 'street'  # Can be auto-detected or manually set
# Auto-detected: 'street', 'intersection', 'dead-end'
# Custom: 'courier service', 'cube hotel', 'hospital', 'stairway', etc.
```

**Smart Exit Implementation:**
```python
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
integration_priority = 10  # Higher = appears earlier in description
sensory_contributions = {
    'visual': "bullet-ridden vehicles pass through",
    'auditory': "engine noise and grinding gears",
    'atmospheric': "sense of urban danger"
}
```

**Integration Processing:**
- Objects with `@integrate = True` contribute to room description
- Priority determines integration order
- Sensory contributions added to appropriate categories
- Objects do not appear in traditional object listing

### Weather System Integration

**Weather State Management:**
- Current weather state affects all sensory categories
- Message pools provide variety like combat system
- Weather intensity affects message selection
- Integration with room base description

### Crowd System Integration

**Crowd Level Management:**
- Dynamic crowd levels: sparse, moderate, heavy, packed
- Each level has message pools for different sensory categories
- Crowd messages add to atmospheric and auditory primarily
- Integration with character listing and social dynamics

### Smart Exit Enhancement

**Exit Context Detection:**
- Analyze destination room types to determine exit labels
- Auto-detect intersections, dead ends, special areas
- Allow manual override for custom labeling
- Integrate exit information into room narrative flow

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
✅ **Fully Implemented:**
- Weather contributes to all sensory categories (visual, auditory, olfactory, atmospheric)
- Message pools rotated like combat messages with fresh selection per look command
- 17 weather types with intensity-based message complexity scaling
- Time period variations for atmospheric consistency (1-12 time periods per weather type)
- Noir/cinematic writing style with adult-focused sophisticated descriptions
- |w formatting integration for bold white weather text display
- Universal weather descriptions avoid location-specific references
- Direct integration into room descriptions via modified `return_appearance()` method

**Technical Implementation:**
- `world/weather/weather_messages.py`: Comprehensive message pools with 4 sensory categories
- `world/weather/weather_system.py`: Message selection and formatting logic  
- `typeclasses/rooms.py`: Integration point in `return_appearance()` method
- Weather appears directly in room description after base text, before characters/exits

### Crowd System Integration  
- Crowd levels affect atmospheric and auditory categories
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
- **Time Cycling**: Day/night variations in all systems
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

**🎯 Aiming Integration Enhancement:**
- When aiming in a direction, targeted look commands search both current room AND aimed-at room
- Unified ordinal numbering across both spaces ("2nd goblin" finds 2nd goblin whether in current or aimed room)
- Implemented via `Character.get_search_candidates()` override using Evennia's designed hook points
- Universal system affects ALL commands using `caller.search()`, not just look commands
- Maintains backward compatibility when not aiming

### Sensory Focus Commands
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
- **Universal Aiming Search**: All commands automatically search aimed-at rooms when aiming (look, get, attack, etc.)

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
3. Advanced sensory focus commands

**Phase 4: Optimization**
1. Performance optimization
2. Caching systems
3. Template management tools
