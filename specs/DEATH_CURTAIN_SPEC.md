# Death Curtain Animation System

> **Status:** ✅ **SHIPPED** — verified against code 2026-08-02.
>
> **⚠ Spec-vs-code corrections — the following claims were FALSE when audited:**
> - "Observer Support: different messages for dying character vs. room observers" — **false**. Animation frames go only to the dying character (`curtain_of_death.py:255-262`); observers get one message at completion.
> - Config values drifted: spec says `frame_delay = 0.015`, `delay_multiplier = 1.01`, four colours, `DEATH_PROGRESSION_DURATION = 360`. Code ships `0.05`, `1.02`, **two** colours, and **90**.

## Overview

The `curtain_of_death.py` module provides an elegant "dripping blood" death animation for characters in the Evennia MUD. This system creates a sophisticated visual effect by centering a death message in a "sea" of characters and progressively removing characters to create a dripping effect.

## Design Philosophy

This animation system is based on a beautiful and subtle design:

1. **Message-Centered**: Places a meaningful death message at the center of the animation
2. **Progressive Decay**: Characters "drip away" from the message in a planned sequence
3. **Visual Poetry**: Creates a sense of fading consciousness and dissolving reality
4. **Flexible**: Works with any death message, making it reusable
5. **Elegant**: The effect is subtle and artistic, not overwhelming

## Features

### Visual Effects
- **Dripping Animation**: Characters progressively disappear from the message in a randomized sequence
- **Color Variation**: Uses Evennia's color system with red variations for blood-like effect
- **Dynamic Timing**: Animation starts fast and slows down over time for dramatic effect
- **Centered Layout**: Message is centered in a "sea" of block characters

### Technical Features
- **Evennia-Native**: Uses Evennia's built-in `delay()` function and color system
- **Message Flexibility**: Can animate any text message
- **Character Messaging**: Integrates with standard Evennia character messaging
- **Observer Support**: Provides different messages for dying character vs. room observers
- **Configurable**: Timing, colors, and characters can be easily adjusted

## Usage

### Basic Usage

```python
from typeclasses.curtain_of_death import show_death_curtain

# Use default death message
show_death_curtain(character)

# Use custom death message
show_death_curtain(character, "Your vision fades to black...")
```

### Integration with Character Death

```python
def at_death(self):
    from .curtain_of_death import show_death_curtain
    show_death_curtain(self)
```

### Testing with Various Messages

```
testdeathcurtain
testdeathcurtain You feel your strength ebbing away...
testdeathcurtain The darkness consumes you
testdeathcurtain A red haze blurs your vision as the world slips away...
```

## Implementation Details

### Core Algorithm

The animation works through these steps:

1. **Center the Message**: Place the death message in the center of a line filled with block characters (`▓`)
2. **Create Removal Plan**: Generate a randomized sequence for removing characters
3. **Progressive Removal**: Remove characters one by one according to the plan
4. **Color Enhancement**: Apply random red-spectrum colors to remaining characters
5. **Final Frame**: Show the complete message one last time

### Key Functions

**`curtain_of_death(text, width=None)`**: Core animation generator
- Creates the sequence of frames for the dripping effect
- Handles message centering and character removal planning
- Applies Evennia color codes

**`DeathCurtain`**: Animation controller class
- Manages timing and frame display
- Handles character messaging
- Provides observer notifications

**`show_death_curtain(character, message=None)`**: Convenience function
- Easy integration point for character death
- Supports custom messages

### Animation Characteristics

```python
# Default message
"A red haze blurs your vision as the world slips away..."

# Frame progression example:
"▓▓▓▓▓▓A red haze blurs your vision as the world slips away...▓▓▓▓▓▓"
"▓▓▓▓▓▓A red h ze blurs your vision as the world slips away...▓▓▓▓▓▓"
"▓▓▓▓▓▓A red h ze blur  your vision as the world slips away...▓▓▓▓▓▓"
"▓▓▓▓▓▓A red h ze blur  your vision as the world slip  away...▓▓▓▓▓▓"
# ... continues until message dissolves
```

## Configuration

### Timing Parameters

```python
self.frame_delay = 0.015        # Starting delay between frames
self.delay_multiplier = 1.01    # Acceleration factor (gets slower)
```

### Visual Parameters

```python
_get_terminal_width()           # Width of animation area (default 78)
sea_char = "▓"                  # Character surrounding the message
replacement_char = "█"          # Character used during dripping
```

### Color Customization

```python
colors = ["|r", "|R", "|y", "|Y"]  # Evennia color codes for effect
```

## Evennia Integration

### Color System Compatibility
- Uses Evennia's native color codes (`|r`, `|R`, `|y`, `|Y`, `|n`)
- Avoids conflicts with color parsing
- Properly terminates color sequences

### Messaging Patterns
- Standard `character.msg()` for dying character
- `location.msg_contents()` for observers
- Proper exclusion handling for room messaging

### Performance Considerations
- Pre-generates all frames for smooth playback
- Limits observer messages to reduce spam
- Uses efficient string operations

## Best Practices

### Message Design
- Keep messages under 60 characters for best visual effect
- Use evocative, atmospheric language
- Consider the pacing of the animation

### Integration Tips
- Test with various message lengths
- Consider context-specific death messages
- Integrate with existing death handling systems

### Performance Guidelines
- Monitor animation performance on slower connections
- Adjust timing for different server loads
- Consider client capabilities

## Examples

### Default Death Message
```python
show_death_curtain(character)
# Uses: "A red haze blurs your vision as the world slips away..."
```

### Custom Death Messages
```python
# Dramatic
show_death_curtain(character, "The darkness claims your soul...")

# Peaceful
show_death_curtain(character, "You drift away into eternal rest...")

# Violent
show_death_curtain(character, "Your blood pools beneath you...")

# Mystical
show_death_curtain(character, "Your essence fades into the void...")
```

## Recent Enhancements (Sept 2024)

### Medical System Integration
The death curtain now integrates with the medical system for informed death messaging:

#### Intelligent Death Cause Messages:
- **Cause Detection**: Uses existing `debug_death_analysis()` logic to determine death cause
- **Informed Messaging**: Shows specific causes like "blood loss", "heart failure", "respiratory failure"
- **Fallback Gracefully**: Returns to beautiful mixed red message if cause detection fails

#### Message Flow:
1. **Initial Death Messages**: Both victim and observers get cause-specific messages
   - Victim: "Your body succumbs to blood loss. The end draws near..."
   - Observers: "Nick Kramer is dying from blood loss..."
2. **Death Curtain**: Always uses the beautiful mixed red message for immersion
3. **Final Notification**: "Nick Kramer has died." for observers

### Visual Improvements
Fixed color and centering issues for optimal presentation:

#### Color Code Fixes:
- **Proper Color Parsing**: Text centering now accounts for color code length
- **Random Block Coloring**: Each ▓ and █ character gets random |r or |R coloring
- **Preserved Message Colors**: Original mixed red death message maintains perfect coloring

#### Centering Algorithm:
- **Visible Length Calculation**: Strips color codes before calculating padding
- **Accurate Centering**: Message appears properly centered regardless of color complexity
- **Clean Animation**: No more malformed frames from color code counting errors

### Race Condition Prevention
Eliminated message conflicts between death curtain and medical system:

#### Medical Message Suppression:
- **Bleeding Messages**: All "lifeless body" messages suppressed for dead characters
- **Clean Narrative**: Death curtain gets exclusive control over death messaging
- **No Interference**: Medical ticker won't interrupt death animation with bleeding updates

#### Timing Coordination:
- **Pre-Curtain Messages**: Initial death cause messages sent before animation starts
- **Exclusive Animation**: Medical system stays silent during death curtain
- **Post-Animation**: Final death confirmation after curtain completes

### Technical Refinements
Multiple technical improvements for robustness and maintainability:

#### Color Code Handling:
```python
def _strip_color_codes(text):
    """Remove Evennia color codes to get visible text length."""
    return re.sub(r'\|.', '', text)
```

#### Smart Message Selection:
- **Cause-Based Selection**: Uses medical analysis for informed messages when available
- **Elegant Fallback**: Always has beautiful default message as backup
- **Consistent Experience**: Both paths provide rich, atmospheric death experience

---

## Death Progression Configuration

The death system consists of two parts: the death curtain animation (~5-10 seconds) followed by a configurable death progression timer.

### Configuration Constants

All death progression timing is controlled in `world/combat/constants.py`:

```python
# Death progression timing
DEATH_PROGRESSION_DURATION = 90           # Total time before permanent death (seconds)
DEATH_PROGRESSION_CHECK_INTERVAL = 30     # How often to check and send messages (seconds)
DEATH_PROGRESSION_MESSAGE_COUNT = 11      # Number of progression messages to send
```

### Common Configurations

**Production (Default):**
```python
DEATH_PROGRESSION_DURATION = 360          # 6 minutes - full dramatic experience
```

**Testing:**
```python
DEATH_PROGRESSION_DURATION = 90           # 90 seconds - faster iteration
DEATH_PROGRESSION_DURATION = 60           # 60 seconds - very fast testing
```

### How It Works

1. **Death Curtain** → Animation plays (~5-10 seconds)
2. **Death Progression** → Timer begins with periodic messages
3. **Medical Window** → Characters can attempt revival during this time
4. **Final Death** → After duration expires, permanent death occurs

Messages are automatically distributed evenly across the total duration. For example, with 90 seconds and 11 messages, they appear every ~8 seconds.

To apply changes: Edit constants, then `@reload` or restart the server.

---

## Future Enhancements

- **Multiple Sea Characters**: Different background patterns for different death types
- **Color Themes**: Ice (blue), fire (red/orange), nature (green), etc.
- **Speed Variations**: Different timing profiles for different death causes
- **Sound Integration**: Audio cues synchronized with visual effects
- **Multi-line Support**: Animate longer death messages across multiple lines

## Technical Notes

### Algorithm Beauty
The core algorithm elegantly balances:
- **Randomness**: Unpredictable character removal creates organic feel
- **Structure**: Planned sequence ensures complete message dissolution
- **Timing**: Progressive slowdown creates dramatic pacing
- **Flexibility**: Same system works for any message length

### Performance Characteristics
- **Memory Efficient**: Generates frames on-demand
- **Network Friendly**: Sends complete frames, not incremental changes
- **Server Optimized**: Uses Evennia's delay system for proper scheduling

---

*This system transforms character death from a simple event into a poetic, visual experience that enhances the storytelling aspect of the game while maintaining technical excellence.*
