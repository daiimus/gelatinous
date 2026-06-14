# Clothing System Specification

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
- **Single source of truth**: `world/combat/constants.py` defines locations for both systems
- **Validation harmony**: Same validation rules apply to both clothing coverage and longdesc locations

### Coverage Rules
- **Hidden longdescs**: When clothing covers a body location, that location's longdesc is not displayed
- **Clothing descriptions**: Worn items contribute their own appearance descriptions
- **Layering order**: Multiple items on same location follow layering rules (outer layers visible)
- **Partial coverage**: Items can cover multiple locations (e.g., shirt covers chest, back, abdomen)

## Clothing Item Architecture

### Wearable Item Class
```python
# Items become clothing simply by having coverage and worn_desc populated
# All functionality implemented in base Item class via AttributeProperty

class Item(DefaultObject):
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
    
    # Layer priority for stacking items (higher = outer layer)
    layer = AttributeProperty(2, autocreate=True)
    
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

### Coverage System Design

## Enhanced Features

### Perspective-Aware Descriptions (NOT using $pron())
**Important**: After testing, we discovered that `$pron()` functions are **NOT available in prototypes**. They only work in `msg_contents()` calls during runtime messaging.

Instead, clothing descriptions use static pronouns and rely on the Item class methods for perspective handling:

```python
# Correct approach - static descriptions in prototypes
HOODIE_WORN_DESC = "A menacing black developer hoodie that clings to their frame like digital shadow incarnate, command-line text pulsing ominously across the chest"

JEANS_WORN_DESC = "Battle-tested denim jeans that cling to their form with urban authority, the faded indigo surface scarred by countless encounters"

BOOTS_WORN_DESC = "Imposing black leather combat boots laced with military precision, steel-reinforced toes speaking of serious intent"
```

**Perspective handling** occurs in the `get_current_worn_desc_with_perspective()` method in the Item class, not in the prototype definitions.

### ANSI Color System Integration
Clothing items support primary and secondary color attributes for enhanced visual immersion:

```python
# Color definitions using Evennia ANSI constants
COLOR_DEFINITIONS = {
    "black": "|x",        # Black
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

### Color and Material Enhanced Descriptions
Clothing descriptions can dynamically incorporate color and material information for future use:

```python
def get_colored_description(self):
    """Return description with ANSI color codes applied"""
    desc = self.worn_desc
    
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
- **Layer 1**: Undergarments (underwear, undershirts)
- **Layer 2**: Base clothing (shirts, pants, dresses)
- **Layer 3**: Outer wear (jackets, coats, robes)
- **Layer 4**: Accessories (belts, jewelry) 
- **Layer 5**: Outerwear (cloaks, heavy coats)

### Dynamic Styling System

#### Style States
Each clothing item can have multiple wear configurations that modify both coverage and appearance:

**Core Style Commands:**
- `rollup <item>` / `unroll <item>` - Roll sleeves, cuffs, pant legs, or hoods up/down
- `zip <item>` / `unzip <item>` - Zip or unzip jackets, boots, bags, etc.

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

#### Style Validation
- **Configuration check**: Commands only work if item has the required style_configs
- **Meaningful transition validation**: Style changes require both coverage_mod and desc_mod to be populated
- **Defensive command validation**: Commands prevent transitions that would have no meaningful effect
- **IC failure messages**: "The shirt doesn't have sleeves to roll up." / "The jacket doesn't have a zipper."
- **State tracking**: Items remember their current style_properties across sessions
- **Layer interaction**: Style changes check for layer conflicts with other worn items

#### Defensive Validation Logic
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
You are carrying:
a black leather jacket (worn, rolled up, unzipped)
a weathered tricorn hat (worn)  
a steel dagger
some copper coins
a worn leather pouch

# Other examples:
a denim jacket (worn, unzipped)
a cotton shirt (worn, rolled up)  
leather boots (worn)
```

**Default State Convention**: Items showing only `(worn)` are in their default state with all style properties set to "normal" (e.g., zipped and unrolled). Only non-default style states are displayed, keeping the interface clean while providing complete information.

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

### Style Commands

#### `rollup <item>` / `unroll <item>`
**Purpose**: Roll sleeves or similar features up/down  
**Syntax**: `rollup <item>` or `unroll <item>`  
**Examples**:
```
rollup shirt
unroll sleeves
rollup 2nd jacket
```

#### `zip <item>` / `unzip <item>`
**Purpose**: Zip or unzip items with closures  
**Syntax**: `zip <item>` or `unzip <item>`  
**Examples**:
```
zip jacket
unzip boots
zip up coat
```

### Staff Commands
Following longdesc pattern, staff can manage clothing on other characters using OOC commands:
```
@wear <character> <item>     - Force wear item on character
@remove <character> <item>   - Force remove item from character
```

## Coverage and Visibility Logic

### Visibility Algorithm
1. **Get all worn clothing** in layer order (outer to inner)
2. **Build coverage map** of which locations are covered by which items
3. **For each body location** (in anatomical display order):
   - If covered by clothing: Add outermost clothing's worn_desc for that location
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
- **Anatomy checking**: Can only wear items covering locations the character has
- **Layer conflicts**: Prevent wearing conflicting items in wrong order
- **Slot limits**: Reasonable limits on items per location (e.g., one hat, two rings)

## Data Storage

### Character Clothing Storage
```python
# In Character class
worn_items = AttributeProperty({}, autocreate=True)

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
# In Clothing class
coverage = AttributeProperty([], autocreate=True)            # Base body locations covered
worn_desc = AttributeProperty("", autocreate=True)           # Base description when worn
layer = AttributeProperty(2, autocreate=True)                # Layer priority
style_properties = AttributeProperty({}, autocreate=True)    # Current style states
style_configs = AttributeProperty({}, autocreate=True)       # Style variations (optional)
```

## Integration Points

### With Longdesc System
- **Shared constants**: Both systems use `world/combat/constants.py` body locations
- **Visibility override**: `_get_visible_longdescs()` checks clothing coverage
- **Appearance assembly**: `return_appearance()` combines clothing and longdescs
- **Paragraph formatting**: Clothing descriptions participate in smart formatting

### With Inventory System
- **Wearable detection**: Items with `coverage` property are wearable
- **Worn item display**: Inventory command shows `(worn)` indicator for equipped items
- **Style state display**: Worn items show current style states: `(worn, rolled up, unzipped)`
- **Comprehensive status**: Players see full clothing configuration at a glance in inventory
- **Transfer rules**: Can't drop worn items, must remove first
- **Unified interface**: Players use standard `inventory` command to see all items including worn status

### With Combat System
- **Armor integration**: Clothing can provide damage reduction
- **Targeting modifiers**: Covered locations harder to target precisely
- **Equipment visibility**: Combat messages reflect what's visible vs covered

## Technical Implementation

### Clothing Detection Pattern
Instead of separate clothing classes, wearable items are identified by the presence of clothing-specific attributes:

```python
def is_wearable(item):
    """Check if an item is wearable clothing"""
    return hasattr(item, 'coverage') and bool(item.coverage)

def is_clothing_worn(item):
    """Check if a clothing item is currently worn"""
    return hasattr(item, 'worn_desc') and bool(item.location and hasattr(item.location, 'worn_items'))
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
```

#### Item Methods (Clothing Functionality)
```python
def can_wear_on(self, character):
    """Check if this item can be worn by character (anatomy validation)"""
    
def conflicts_with(self, other_item):
    """Check for layer or logical conflicts with another worn item"""
    
def get_worn_appearance(self):
    """Get description when worn on character (current style state)"""
    
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
    
    # Validate meaningful transition
    config = self.style_configs[property_name][state_name]
    has_coverage_change = bool(config.get("coverage_mod", []))
    has_desc_change = bool(config.get("desc_mod", "").strip())
    
    return has_coverage_change and has_desc_change

def set_style_property(self, property_name, state_name):
    """Set specific style property to given state with validation"""
    if not self.can_style_property_to(property_name, state_name):
        return False
    
    if not self.style_properties:
        self.style_properties = {}
    
    self.style_properties[property_name] = state_name
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
    """Get current worn description with brace-token and color processing"""
    # Get base description (considering current style state)
    desc = self.get_current_worn_desc()
    
    # Process color placeholders
    desc = self._process_color_codes(desc)
    
    # Process {their}/{they} brace tokens with perspective
    if looker and from_obj:
        from evennia.utils.funcparser import FuncParser
        parser = FuncParser(desc)
        desc = parser.parse(caller=from_obj, receiver=looker)
    
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

## Command Implementation

### Wear Command Logic
1. **Find item** in character's inventory
2. **Validate wearability** (anatomy check, item type)
3. **Check layer conflicts** with currently worn items
4. **Remove conflicting items** if necessary (with confirmation)
5. **Wear item** and update worn_items storage
6. **Provide feedback** with appearance change summary

### Remove Command Logic
1. **Find worn item** by name or location
2. **Validate removal** (not locked, accessible)
3. **Update worn_items** storage
4. **Move to inventory** 
5. **Provide feedback** with appearance change summary

### Style Command Logic
1. **Find worn item** by name
2. **Determine style property** from command (rollup = adjustable, zip = closure, etc.)
3. **Validate style capability** (item has required style property configured)
4. **Check target state** (rollup sets to "rolled", zip sets to "zipped", etc.)
5. **Validate meaningful transition** (target state has both coverage_mod and desc_mod populated)
6. **Validate layer conflicts** (new combined coverage doesn't conflict with other worn items)
7. **Apply style change** (update specific property in style_properties)
8. **Provide feedback** with style change description

#### Command to Property Mapping
- `rollup/unroll` → `adjustable` property → `rolled/normal` states (could be sleeves, hood, cuffs, pant legs, etc.)
- `zip/unzip` → `closure` property → `zipped/unzipped` states (could be zipper, buttons, laces, etc.)
- Commands automatically detect which property they affect based on item configuration
- Items can have one, both, or neither style property configured

#### Style Command Examples
```
> rollup jacket
You roll up the sleeves of your leather jacket.

> zip jacket  
You zip up your leather jacket.

> look me
Sterling wears a black leather jacket with sleeves rolled up, zipped tight against the cold.

> unzip jacket
You unzip your leather jacket, letting it hang open.

> look me  
Sterling wears a black leather jacket with sleeves rolled up, hanging open.

> unroll jacket
You unroll the sleeves of your leather jacket.

> look me
Sterling wears a black leather jacket hanging open.

> rollup shirt
The shirt doesn't have sleeves that can be rolled up.

> zip shirt
The shirt doesn't have a zipper.
```

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
- ✅ **Staff targeting for clothing management** - Admin functionality tested
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
- [x] Modify `_get_visible_longdescs()` to check clothing coverage
- [x] Implement clothing description display in appearance
- [x] Add layer resolution logic for overlapping items
- [x] Test appearance assembly with clothing + longdescs

### Phase 3: Advanced Features 📋 PENDING
- [ ] Layer conflict detection and resolution
- [ ] Staff targeting for clothing management
- [ ] Comprehensive error handling and user feedback
- [ ] Performance optimization and testing

## Design Summary

### Key Design Decisions

**Multi-Property Style System**: Items can have multiple independent style properties (`adjustable`, `closure`) that combine to create rich variation. A jacket can be both rolled up and unzipped simultaneously, creating four distinct states with different coverage and descriptions.

**Meaningful Transition Validation**: All style commands require both coverage changes AND description changes. This ensures every player interaction has both functional and visual impact, preventing meaningless commands.

**Generic Property Naming**: The `adjustable` property covers any rollup/unroll functionality (sleeves, hoods, cuffs, pant legs), making the system flexible and extensible without requiring specific properties for each adjustment type.

**Defensive Command Logic**: Commands perform comprehensive validation before execution, checking for capability, meaningful transitions, and current state to provide helpful feedback and prevent invalid operations.

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
- [x] Base clothing descriptions **implemented** with static pronouns in prototypes 
- [x] Style descriptions **implemented** without `$pron()` tags (not available in prototypes)
- [x] Character appearance system **implemented** with proper perspective handling in methods
- [x] `get_current_worn_desc_with_perspective()` method **implemented** in Item class for future enhancement
- [x] All prototype examples **corrected** to use static descriptions

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
**Next Steps**: Implement Phase 2 color & material system enhancements in codebase
