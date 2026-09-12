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
  - **Correction 2026-09-12 (#2469 / #2952):** the *API* is standard —
    `character.msg()` — but the *filter* is not. This game overrides
    `Character.msg` (`typeclasses/characters.py:288-344`) to drop almost
    everything addressed to a dead character: no `from_obj` is blocked
    outright, non-staff and non-`death_progression` senders are blocked, and
    only a `death_curtain=True` kwarg lets the curtain's own traffic through
    (`curtain_of_death.py:277`, `:291`; the flag is popped before `super()`
    so it never reaches the client as an outputfunc). The filter previously
    sniffed for `▓` in the text, which is true of the opening frames and
    false of the trailing drip, the three blank frames and the
    cause-of-death line — so the animation cut out partway and the dying
    player was never told what killed them.
- **Observer Support**: Provides different messages for dying character vs. room observers
  - **Re-checked 2026-09-12:** true as written, but narrower than it reads, and the
    banner's blunter "**false**" overstates it. What observers never get is the
    *animation*: every frame goes to `self.character` alone
    (`DeathCurtain._show_next_frame`, `curtain_of_death.py:285-296`), and the
    initial cause line is sent to the victim only, deliberately
    (`:279-280`). Observers do get their own, genuinely different message —
    one cause- and species-keyed template at completion, rendered per
    watcher by `msg_room_identity` (`:377-382`). So: different messages yes,
    different frames no, and nothing at all until the curtain ends.
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
   - **Correction 2026-09-12:** the animation never returns to the message.
     After the text is erased, `curtain_of_death` appends 12 trailing
     sparse-drip frames (`curtain_of_death.py:190-213`) and then three
     **all-blank** frames (`" " * curtain_width`, `:215-218`). The complete
     message is shown exactly once, as frame 0 (`:139`). The player's last
     sight is an empty line, not the message. Measured by running the
     shipped generator 200× on the default message at width 78: **33-41
     frames** per run.

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
# CORRECTION 2026-09-12: the live values are frame_delay = 0.05 and
# delay_multiplier = 1.02 (curtain_of_death.py:256-257). Measured over 200
# runs of the shipped generator on the default message at width 78: 33-41
# frames, scheduled over ~2.3-3.1 s -- not the "~5-10 seconds" claimed twice
# further down.
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
  - **Correction 2026-09-12:** the curtain calls `character.get_death_cause()`
    (`typeclasses/characters.py:624-662`) at `curtain_of_death.py:266` and
    `:373`. `debug_death_analysis()` (`characters.py:494`) is a
    splattercast-only report fired from `at_death` (`characters.py:813`) and
    never touches the curtain's path. The logic is **duplicated, not
    shared**, and the copies diverge three ways: `debug_death_analysis`
    lists *every* fatal condition while `get_death_cause` returns only the
    first in priority order (blood loss first, `:648`); zero `digestion`
    reads "LIVER FAILURE" in the debug report (`characters.py:536`) but
    "organ failure" in the player-facing cause (`characters.py:656`); and
    only the player-facing path appends the killing blow via
    `_with_death_blow` (`characters.py:103-121`), so the victim can hear
    "blood loss from a stab wound to the chest" where the debug report says
    just "BLOOD LOSS".
- **Informed Messaging**: Shows specific causes like "blood loss", "heart failure", "respiratory failure"
- **Fallback Gracefully**: Returns to beautiful mixed red message if cause detection fails

#### Message Flow:
1. **Initial Death Messages**: Both victim and observers get cause-specific messages
   - **Correction 2026-09-12:** the victim only. See the note on the
     Observers sub-bullet below — the observer half was deliberately removed
     (`curtain_of_death.py:279-280`). The victim's line is real
     (`:271-277`), and with a recorded killing blow it reads longer than the
     example below: `_with_death_blow` (`characters.py:103-121`) can make it
     "Your body succumbs to blood loss from a stab wound to the chest."
   - Victim: "Your body succumbs to blood loss. The end draws near..."
   - Observers: "Nick Kramer is dying from blood loss..."
2. **Death Curtain**: Always uses the beautiful mixed red message for immersion
   - **Qualification 2026-09-12:** "always" holds only on the death path,
     where `at_death` calls `show_death_curtain(self)` with no message and
     the default is substituted (`curtain_of_death.py:249-251`). Any caller
     that passes a `message` overrides it — including the custom-message form
     documented in this spec's own *Usage* section and
     `@testdeathcurtain <message>` (`commands/CmdAdmin.py:768-776`), whose
     text is animated uncoloured.
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

The death system consists of two parts: the death curtain animation (~5-10 seconds — **measured 2026-09-12: ~2.3-3.1 s**, 33-41 frames at `frame_delay` 0.05 × 1.02ⁿ, `curtain_of_death.py:256-257`) followed by a configurable death progression timer.

### Configuration Constants

All death progression timing is controlled in `world/combat/constants.py`:

```python
# Death progression timing
DEATH_PROGRESSION_DURATION = 90           # Total time before permanent death (seconds)
DEATH_PROGRESSION_CHECK_INTERVAL = 30     # How often to check and send messages (seconds)
# CORRECTION 2026-09-12: no longer a literal. world/combat/constants.py:878-879
# DERIVES it from the other two:
#     _message_spacing = DEATH_PROGRESSION_DURATION // DEATH_PROGRESSION_MESSAGE_COUNT
#     DEATH_PROGRESSION_CHECK_INTERVAL = max(1, int(_message_spacing * 0.6))
# At the live 90 s / 11 messages that is 8 * 0.6 -> 4. The death_progression
# script therefore ticks every 4 s, not 30 s, and re-asserts that from
# constants on every restart (death_progression.py:196-211, #501 Phase 2) --
# so editing the number as printed above has no effect at all.
# specs/proposals/DEATH_AND_SLEEVE_LIFECYCLE_SPEC.md:89 still carries the
# stale 30 s in its timing table (its :88 row already says 90 s correctly).
DEATH_PROGRESSION_MESSAGE_COUNT = 11      # Number of progression messages to send
```

### Common Configurations

**Production (Default):**
```python
DEATH_PROGRESSION_DURATION = 360          # 6 minutes - full dramatic experience
# ⚠ NOT WHAT THE WORLD RUNS ON (checked 2026-09-12). world/combat/constants.py:869
# has shipped 90 since the constant was introduced (commit 0ce97a06,
# 2025-10-27); `git log -S` finds no other value, so 360 has never been live
# for a single commit, and the "Testing: 90" line below therefore describes
# production. The rest of the code is written against 90
# (world/director/medical.py:74-76, world/tests/test_medic_dispatch_and_triage.py:11-12,
# issue #2757's title). The same stale 360 s also appears in
# specs/roadmaps/MEDICAL_SUBSTRATE_ROADMAP.md:213-214 and :330 -- the
# designated authority for medical behaviour -- and in
# typeclasses/death_progression.py:14-16.
# Whether 360 is still the INTENDED production value is an owner question and
# is left open here. The stale "Default: 360 seconds" comments at
# constants.py:867 and death_progression.py:14 are a code defect, not a spec one.
```

**Testing:**
```python
DEATH_PROGRESSION_DURATION = 90           # 90 seconds - faster iteration
DEATH_PROGRESSION_DURATION = 60           # 60 seconds - very fast testing
```

### How It Works

1. **Death Curtain** → Animation plays (~5-10 seconds) — *measured 2026-09-12: ~2.3-3.1 s (33-41 frames)*
2. **Death Progression** → Timer begins with periodic messages
3. **Medical Window** → Characters can attempt revival during this time
4. **Final Death** → After duration expires, permanent death occurs

Messages are automatically distributed evenly across the total duration. For example, with 90 seconds and 11 messages, they appear every ~8 seconds.

To apply changes: Edit constants, then `@reload` or restart the server.

> **Qualification 2026-09-12:** true for *future* deaths only. `total_duration`
> and `message_intervals` are seeded once at `at_script_creation`
> (`typeclasses/death_progression.py:129-136`) and persist on the script, so a
> death already in flight keeps the old duration and spacing across a reload.
> Only `interval` is re-derived from constants on restart
> (`at_start`, `:196-211`, the #501 Phase 2 guarantee). A duration change
> therefore takes effect at the next death, not at the next reload.

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
