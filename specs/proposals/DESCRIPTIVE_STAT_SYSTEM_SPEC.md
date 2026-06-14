# Descriptive Stat System Specification

> **Status:** 📋 Proposal — not implemented. The four G.R.I.M. stats exist on the Character, but the A–Z descriptor display layer and any skill system described below are unbuilt.

## Overview

The G.R.I.M. (Grit, Resonance, Intellect, Motorics) system will be enhanced with descriptive words that replace raw numerical displays for players. Each stat will have 26 alphabetical descriptive tiers (A-Z) representing power levels from 0-150, with each tier covering a 6-point range.

## System Design

### Numerical Mapping

The 0-150 stat range is divided into 26 alphabetical tiers:

- **A**: 145-150 (Apex tier)
- **B**: 139-144 
- **C**: 133-138
- **D**: 127-132
- **E**: 121-126
- **F**: 115-120
- **G**: 109-114
- **H**: 103-108
- **I**: 97-102
- **J**: 91-96
- **K**: 85-90
- **L**: 79-84
- **M**: 73-78
- **N**: 67-72
- **O**: 61-66
- **P**: 55-60
- **Q**: 49-54
- **R**: 43-48
- **S**: 37-42
- **T**: 31-36
- **U**: 25-30
- **V**: 19-24
- **W**: 13-18
- **X**: 7-12
- **Y**: 1-6 (Near-zero tier)
- **Z**: 0 (Zero tier)

### Display Philosophy

- **Player Facing**: Only descriptive words are shown to players
- **Administrative**: Help files and admin commands show both word and numerical range
- **Universal Application**: All Character typeclass entities (PCs, NPCs, mobs) use this system
- **Thematic Consistency**: Each stat has its own vocabulary that reflects its nature

## Stat Progressions

### GRIT (Physical Toughness & Endurance)

Grit represents physical resilience, pain tolerance, and the ability to endure hardship.

- **A (145-150)**: Apex - Legendary physical resilience
- **B (139-144)**: Bulletproof - Extreme damage resistance  
- **C (133-138)**: Concrete - Nearly unbreakable toughness
- **D (127-132)**: Durable - Exceptional physical resilience
- **E (121-126)**: Enduring - Superior stamina and toughness
- **F (115-120)**: Fortified - Well-hardened constitution
- **G (109-114)**: Granite - Rock-solid physical foundation
- **H (103-108)**: Hardy - Robust and resilient
- **I (97-102)**: Iron-willed - Strong determination and endurance
- **J (91-96)**: Juggernaut - Unstoppable physical momentum
- **K (85-90)**: Keen - Sharp physical awareness and endurance
- **L (79-84)**: Lasting - Good sustained endurance
- **M (73-78)**: Moderate - Average physical resilience
- **N (67-72)**: Normal - Typical toughness levels
- **O (61-66)**: Ordinary - Standard physical endurance
- **P (55-60)**: Passable - Adequate but unremarkable
- **Q (49-54)**: Questionable - Below-average resilience
- **R (43-48)**: Rough - Poor physical condition
- **S (37-42)**: Soft - Weak physical constitution
- **T (31-36)**: Tender - Easily damaged or exhausted
- **U (25-30)**: Unstable - Very poor physical state
- **V (19-24)**: Vulnerable - Extremely fragile condition
- **W (13-18)**: Weak - Severely compromised toughness
- **X (7-12)**: Xerotic - Dried out, withered resilience
- **Y (1-6)**: Yielding - Virtually no resistance left
- **Z (0)**: Zero - Complete physical breakdown

### RESONANCE (Social Connection & Empathy)

Resonance represents social awareness, empathy, and the ability to connect with others.

- **A (145-150)**: Attuned - Perfect social synchronization
- **B (139-144)**: Bonded - Deep emotional connections
- **C (133-138)**: Charismatic - Naturally magnetic presence
- **D (127-132)**: Dynamic - Energetic social engagement
- **E (121-126)**: Empathetic - Exceptional emotional understanding
- **F (115-120)**: Fluid - Smooth social interactions
- **G (109-114)**: Gracious - Naturally diplomatic and kind
- **H (103-108)**: Harmonious - Well-balanced social skills
- **I (97-102)**: Intuitive - Strong social instincts
- **J (91-96)**: Jovial - Naturally uplifting presence
- **K (85-90)**: Kind - Genuine warmth and consideration
- **L (79-84)**: Likeable - Generally pleasant company
- **M (73-78)**: Moderate - Average social capabilities
- **N (67-72)**: Natural - Standard social functioning
- **O (61-66)**: Open - Reasonably approachable
- **P (55-60)**: Polite - Basic social courtesies
- **Q (49-54)**: Quiet - Limited social engagement
- **R (43-48)**: Reserved - Withdrawn from others
- **S (37-42)**: Stiff - Awkward social interactions
- **T (31-36)**: Tense - Uncomfortable social presence
- **U (25-30)**: Uncomfortable - Poor social ease
- **V (19-24)**: Vacant - Emotionally disconnected
- **W (13-18)**: Withdrawn - Severely isolated
- **X (7-12)**: Xenophobic - Fear and hatred of others
- **Y (1-6)**: Yearning - Desperately lonely
- **Z (0)**: Zero - Complete social isolation

### INTELLECT (Reasoning & Knowledge)

Intellect represents analytical thinking, problem-solving, and accumulated knowledge.

- **A (145-150)**: Absolute - Perfect cognitive clarity
- **B (139-144)**: Brilliant - Exceptional intellectual capability
- **C (133-138)**: Calculating - Precise analytical mind
- **D (127-132)**: Discerning - Sharp judgment and insight
- **E (121-126)**: Enlightened - Superior understanding
- **F (115-120)**: Focused - Clear, concentrated thinking
- **G (109-114)**: Gifted - Naturally talented intellect
- **H (103-108)**: Heightened - Enhanced mental acuity
- **I (97-102)**: Incisive - Sharp, penetrating analysis
- **J (91-96)**: Judicious - Wise decision-making
- **K (85-90)**: Knowledgeable - Well-informed understanding
- **L (79-84)**: Logical - Sound reasoning abilities
- **M (73-78)**: Methodical - Systematic thinking approach
- **N (67-72)**: Normal - Standard cognitive function
- **O (61-66)**: Observant - Good attention to detail
- **P (55-60)**: Practical - Basic problem-solving skills
- **Q (49-54)**: Questioning - Uncertain mental clarity
- **R (43-48)**: Rough - Poor cognitive processing
- **S (37-42)**: Slow - Sluggish mental responses
- **T (31-36)**: Troubled - Confused thinking patterns
- **U (25-30)**: Unclear - Muddled thought processes
- **V (19-24)**: Vacant - Empty mental state
- **W (13-18)**: Wandering - Severely unfocused mind
- **X (7-12)**: Xeric - Barren, desert-like cognition
- **Y (1-6)**: Yearning - Grasping for basic understanding
- **Z (0)**: Zero - Complete cognitive shutdown

### MOTORICS (Physical Coordination & Dexterity)

Motorics represents fine motor control, hand-eye coordination, and physical grace.

- **A (145-150)**: Artful - Perfect physical expression
- **B (139-144)**: Balletic - Graceful, flowing movement
- **C (133-138)**: Coordinated - Exceptional body control
- **D (127-132)**: Dexterous - Skilled hand-eye coordination
- **E (121-126)**: Elegant - Refined physical grace
- **F (115-120)**: Fluid - Smooth, natural movement
- **G (109-114)**: Graceful - Naturally beautiful motion
- **H (103-108)**: Harmonized - Well-balanced coordination
- **I (97-102)**: Intuitive - Natural movement instincts
- **J (91-96)**: Jaunty - Confident, sprightly movement
- **K (85-90)**: Kinetic - Good physical energy and control
- **L (79-84)**: Limber - Flexible and responsive
- **M (73-78)**: Mobile - Standard movement capabilities
- **N (67-72)**: Nimble - Reasonably quick and agile
- **O (61-66)**: Ordinary - Average physical coordination
- **P (55-60)**: Passable - Adequate but unremarkable
- **Q (49-54)**: Questionable - Uncertain coordination
- **R (43-48)**: Rigid - Stiff, uncomfortable movement
- **S (37-42)**: Stilted - Awkward physical expression
- **T (31-36)**: Trembling - Unsteady motor control
- **U (25-30)**: Unsteady - Poor physical stability
- **V (19-24)**: Vacant - Disconnected from body
- **W (13-18)**: Wobbly - Severely impaired coordination
- **X (7-12)**: Xyloid - Wooden, stiff motor function
- **Y (1-6)**: Yielding - Barely controllable movement
- **Z (0)**: Zero - Complete motor shutdown

## Technical Implementation

### Code Integration

The descriptive system integrates with existing G.R.I.M. stat handling:

```python
# Constants for stat conversion
STAT_DESCRIPTORS = {
    "grit": {
        145: "Apex", 139: "Bulletproof", 133: "Concrete",
        # ... complete mapping
        1: "Yielding", 0: "Zero"
    },
    "resonance": {
        145: "Attuned", 139: "Bonded", 133: "Charismatic",
        # ... complete mapping
        1: "Yearning", 0: "Zero"
    },
    "intellect": {
        145: "Absolute", 139: "Brilliant", 133: "Calculating",
        # ... complete mapping
        1: "Yearning", 0: "Zero"
    },
    "motorics": {
        145: "Artful", 139: "Balletic", 133: "Coordinated",
        # ... complete mapping
        1: "Yielding", 0: "Zero"
    }
}

def get_stat_descriptor(stat_name, numeric_value):
    """Convert numeric stat to descriptive word."""
    # Find appropriate tier based on 6-point ranges
    # Return descriptive word
    
def get_stat_range(descriptor_word, stat_name):
    """Get numeric range for a descriptive word."""
    # Return (min_value, max_value) tuple
```

### Display Formats

**Character Sheet Display:**
```
GRIT: Granite        RESONANCE: Harmonious
INTELLECT: Logical   MOTORICS: Fluid
```

**Admin/Debug Display:**
```
GRIT: Granite (109-114, actual: 112)
RESONANCE: Harmonious (103-108, actual: 105)
```

**Help File Content:**
```
@stats - Character Statistics

Your character's capabilities are measured in four core areas:

GRIT (Physical Toughness): From Apex (145-150) to Zero (0)
RESONANCE (Social Connection): From Attuned (145-150) to Zero (0)
INTELLECT (Reasoning): From Absolute (145-150) to Zero (0)
MOTORICS (Coordination): From Artful (145-150) to Zero (0)

Each descriptor represents a 6-point range of capability.
```

### Backward Compatibility

- Existing numeric stat storage remains unchanged
- All current combat calculations continue using numeric values
- Only display layer is modified to show descriptive words
- Admin commands can toggle between numeric and descriptive views

## Design Rationale

### Alphabetical Organization
- **Intuitive**: A-Z progression is universally understood
- **Memorable**: Easier to remember relative power levels
- **Elegant**: Clean, systematic organization

### Six-Point Ranges
- **Meaningful Differences**: Each tier represents noticeable capability difference
- **Granular Enough**: 26 tiers provide sufficient progression granularity
- **Round Numbers**: Clean mathematical progression

### Thematic Vocabularies
- **Immersive**: Reinforces the gritty, realistic tone
- **Distinctive**: Each stat has its own personality through word choice
- **Progressive**: Words clearly indicate relative capability levels

### Universal Application
- **Consistency**: All entities use same descriptive system
- **Simplicity**: Single system to learn and understand
- **Scalability**: Easy to add new content using existing framework

## Future Extensions

### Potential Enhancements
- Colored tier displays (green for high, red for low)
- Detailed tier descriptions in help files
- Stat comparison tools using descriptive words
- Integration with character generation system
- Narrative text generation based on stat descriptors

### Customization Options
- Server-configurable descriptor word sets
- Language localization support
- Theme-specific vocabulary variations
- Player preference for numeric vs. descriptive display

---

*This specification provides the foundation for a more immersive and narrative-focused character progression system while maintaining full compatibility with existing combat and character mechanics.*