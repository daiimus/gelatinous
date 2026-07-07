# Graffiti System Specification

## Overview
Unified graffiti system providing player-driven street expression through spray paint and graffiti cleaning mechanics. Features resource-managed tagging with finite aerosol supplies, color selection, Mr. Hands integration, and enhanced atmospheric messaging with delayed effects.

## Core Components

### 1. Spray Paint Cans (SprayCanItem Typeclass)
**Attributes:**
- `aerosol_level`: Integer (256 default) - remaining paint characters
- `current_color`: String - selected ANSI color (red, green, yellow, blue, magenta, cyan, white)
- `max_aerosol`: Integer - starting paint capacity (256)
- `aerosol_contents`: String - "spraypaint" (identifies can type)
- `available_colors`: List - cycling color palette
- `weapon_type`: String - "spraycan" (combat system integration)

**Functionality:**
- Color selection via `press <color> on <can>` command
- Paint depletion tracking (1 character = 1 paint unit) 
- **Automatic deletion** when empty with integrated cleanup messaging
- **Mr. Hands integration** - works from inventory or wielded
- Combat weapon capability with spraycan-specific messages

### 2. Solvent Cans (SolventCanItem Typeclass)  
**Attributes:**
- `aerosol_level`: Integer (256 default) - remaining solvent uses
- `max_aerosol`: Integer - starting capacity (256)
- `aerosol_contents`: String - "solvent" (identifies can type)
- `weapon_type`: String - "spraycan" (combat system integration)

**Functionality:**
- **Character-based cleaning** - removes random characters from graffiti entries
- **Enhanced atmospheric messaging** with immediate + delayed effects
- **Automatic deletion** when empty
- **Mr. Hands integration** - works from inventory or wielded
- Combat weapon capability

### 3. Graffiti Storage Object (GraffitiObject Typeclass)
**Storage Mechanics:**
- **Unlimited entries** (no arbitrary cap)
- Each entry format: `"Scrawled in <color> paint: <message>"`
- **Persistent storage** with color-coded display
- **Character replacement system** for solvent effects ("Wheel of Fortune" style)

**Integration:**
- Room description integration: "The walls have been daubed with colorful graffiti"
- Examinable object: `look graffiti`
- Auto-creation on first graffiti entry
- Persists through partial cleaning

### 4. Unified Spray Command (CmdGraffiti)
**Syntax:** 
- `spray "message" with <spray_can>` - Paint graffiti
- `spray here with <solvent_can>` - Clean graffiti

**Intelligent Routing:**
- **Can type detection** via `aerosol_contents` attribute
- **Intent-based routing** - "here with" = clean, quoted message = paint
- **Error prevention** - solvent can't paint, paint can't clean
- **Mr. Hands integration** - searches inventory AND wielded items

**Spray Paint Mechanics:**
- Validates spray can has paint and correct contents
- Enforces 100-character message limit
- **Graceful paint depletion** with ellipsis truncation ("message...")
- **Consolidated messaging** for runout scenarios
- **Automatic can deletion** with narrative cleanup
- Color-coded output with current can color

**Solvent Mechanics:**
- **Character-level removal** (10 units per use)
- **Immediate feedback** + **3-second delayed atmospheric message**
- **Random character replacement** with spaces (not deletion)
- Progressive graffiti degradation over multiple applications

### 5. Color Management (CmdPress)
**Syntax:** `press <color> on <spray_can>`

**Functionality:**
- **Available color validation** against can's color palette
- **Color-coded feedback** showing available options
- **Mr. Hands integration** - works on inventory or wielded cans
- **Error handling** for non-spray items and invalid colors

**Supported Colors:** red, green, yellow, blue, magenta, cyan, white
**Visual feedback:** Colored text showing available options

## Integration Systems

### Room Description Integration
- **Automatic integration** on first graffiti entry creation
- Atmospheric line: "The walls have been daubed with colorful graffiti"
- **Persistent visibility** - integration remains until all graffiti removed
- **Smart cleanup** - integration removed only when graffiti object deleted

### Mr. Hands Equipment System
- **Dual search capability** - checks inventory AND wielded items
- **Alias support** - matches both item names and aliases
- **Seamless operation** - no difference between carried/wielded functionality
- **Automatic cleanup** - empty cans removed from hands on deletion
- **Combat integration** - spray cans function as weapons when wielded

### Enhanced Atmospheric Messaging
**Immediate Effects:**
- Paint: "You spray 'message' on the wall with [can]"  
- Clean: "You apply solvent to the graffiti, watching the colors dissolve away"

**Delayed Effects (3-second delay):**
- "The colors break down and the solvent evaporates, taking the graffiti with it"
- **Location-wide messaging** - affects all players in room
- **Persistence checking** - safely handles location changes

### Combat System Integration
- **Weapon classification** - both can types use "spraycan" weapon_type
- **Custom combat messages** - 114 unique spraycan-specific combat messages
- **Balanced stats** - 2 damage, non-ranged, 1-handed weapons
- **Message variety** - initiate, miss, hit, and kill phases with thematic content

## Resource Economy & User Experience

### Smart Resource Management
- **Finite aerosol supplies** encourage thoughtful messaging (256 characters/can)
- **Character-based depletion** prevents spam while allowing creativity
- **Automatic cleanup** - empty cans self-destruct with narrative flair
- **Graceful degradation** - partial messages with ellipsis show resource exhaustion

### Enhanced Cleaning Mechanics  
- **Progressive degradation** - "Wheel of Fortune" style character replacement
- **Balanced resource costs** - 10 solvent units per cleaning action
- **Visual feedback** - spaces replace removed characters, maintaining layout
- **Multi-stage process** - multiple applications needed for complete removal

### Improved User Messaging
**Successful Operations:**
- Standard: "You spray 'message' on the wall with [can]"
- Resource exhaustion: "You start to spray on the wall with [can], but it runs out of paint mid-message! You manage to spray 'truncated...' before the can crumples up and becomes useless."

**Error Prevention:**
- Clear intent-based routing with helpful error messages
- "You can't clean with [paint can] - it contains paint, not solvent"
- "You can't spray paint with [solvent can] - it contains solvent, not paint"

### Quality Control Measures
- **100-character message limit** prevents description bloat
- **Ellipsis truncation** shows incomplete messages clearly
- **Can type validation** prevents misuse
- **Robust error handling** with informative feedback

## Technical Implementation Details

### Unified Command Structure (`commands/CmdGraffiti.py`)
- **Single command file** handles both spray painting and cleaning
- **Intelligent parsing** determines user intent from syntax
- **Graceful error handling** with defensive programming practices
- **Mr. Hands integration** with proper alias handling (`aliases.all()`)
- **Resource state management** - stores can info before potential deletion

### Advanced Item Management (`typeclasses/items.py`)
**SprayCanItem:**
- **Smart deletion** - removes from hands before self-destructing
- **Color persistence** - maintains current color across sessions  
- **Combat integration** - dual-purpose as weapon and tool
- **Aerosol system** - standardized aerosol_level tracking

**SolventCanItem:**
- **Parallel functionality** - mirrors spray can behavior
- **Silent deletion** - lets command handle user messaging
- **Unified interface** - same aerosol system as paint cans

### Enhanced Graffiti Storage (`typeclasses/objects.py`)  
- **Character replacement algorithm** - spaces maintain message structure
- **Null-safe color handling** - graceful fallback to white
- **Persistent storage** - maintains graffiti across server restarts
- **Color-coded display** - proper ANSI color formatting

### Prototype System (`world/prototypes.py`)
- **Aerosol standardization** - both can types use aerosol_contents identifier
- **Combat stats** - balanced weapon attributes for both can types
- **Consistent capacity** - 256 aerosol units standard across all cans

### Combat Message Integration (`world/combat/messages/spraycan.py`)
- **114 unique messages** across all combat phases
- **Thematic consistency** - corporate dystopia aesthetic
- **Variety** - prevents repetitive combat descriptions
- **Narrative coherence** - matches game world tone

## Implementation Files

### Core Command Files
- `commands/CmdGraffiti.py` - Unified spray/clean command with intelligent routing
- `commands/default_cmdsets.py` - Command registration and integration

### Typeclass Definitions
- `typeclasses/items.py` - SprayCanItem and SolventCanItem with Mr. Hands integration
- `typeclasses/objects.py` - GraffitiObject with character replacement system

### Configuration & Data
- `world/prototypes.py` - SPRAYPAINT_CAN and SOLVENT_CAN prototypes
- `world/combat/messages/spraycan.py` - Combat message definitions

### Integration Dependencies
- Mr. Hands system (`typeclasses/characters.py` - hands attribute)
- Combat system (spraycan weapon_type support)
- Room description integration system
- Delayed messaging system (`evennia.utils.delay`)

## Current Status: **PRODUCTION READY**

### Completed Features ✅
- **Unified command system** with intelligent can-type routing
- **Mr. Hands integration** - full inventory and wielded item support  
- **Enhanced atmospheric messaging** with delayed effects
- **Automatic resource cleanup** - empty cans self-destruct gracefully
- **Progressive graffiti degradation** - character-based solvent cleaning
- **Combat system integration** - spray cans as weapons
- **Robust error handling** - defensive programming throughout
- **Consolidated user messaging** - clear, narrative feedback
- **Ellipsis truncation** - visual indication of incomplete messages

### Known Limitations
- No message persistence across server restarts for graffiti objects
- Color palette fixed to 7 standard ANSI colors

### Future Enhancement Opportunities
- ~~Action delays~~ — ✅ SHIPPED (2026-07-06, CHANNELED_ACTIONS_SPEC):
  spraying is a channeled act (3s setup + 1s/letter — duration proportional
  to tag length, the anti-spam that is also the fiction); movement blocked,
  violence interrupts (partial tag lands with ellipsis, pro-rata paint), and
  tagging files a real `vandalism` crime report (crowd-gated witness).
  Cleaning delays: next consumer.
- **Identical tag stacking** - repeated messages get consolidated with quantity descriptors
  - Single: "Scrawled in red paint: WAKKA RULES"  
  - Multiple colors: "Scrawled in |rp|ba|gi|yn|mt obsessively: WAKKA RULES"
  - Visual composition using ANSI color codes reflects spraypaint colors used
  - Euphemistic progression: few/several/many/countless/obsessively repeated/nearly everywhere
  - Display priority: unique tags first, stacked tags after (de-emphasized)
  - Rewards variety, discourages spam with vague acknowledgment
  - Cleaning interaction: solvent still works character-by-character, ignores stacking
  - Case-insensitive matching for consolidation
- **Graffiti aging mechanics** - fade over time
- **Gang/faction-specific colors** - restricted color palettes
- **Skill-based quality levels** - novice vs expert graffiti
- **Paint refill system** - economic sustainability
- **Advanced cleaning tools** - pressure washers, paint-over mechanics
- **Graffiti contests/events** - community engagement features
