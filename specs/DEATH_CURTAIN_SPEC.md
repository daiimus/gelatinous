# Death Curtain Animation System

## Overview

When a character dies, the dying player sees a "dripping blood" animation: a death message centred in a "sea" of block characters, with characters erased frame by frame until nothing is left. The animation is followed by the death progression timer, the window in which the character can still be revived. The animation lives in `typeclasses/curtain_of_death.py`; the timer lives in `typeclasses/death_progression.py`.

The design: a meaningful death message at the centre; characters "drip away" from it in a planned, randomized sequence; the effect suggests fading consciousness and dissolving reality; it works with any message; it is subtle, not overwhelming.

## What the dying player sees

### The curtain

1. **The cause line.** Before the animation starts, the victim alone gets one line naming the cause: "Your body succumbs to {cause}. The end draws near..." If no cause comes back at all, it reads "Your body fails you. The end draws near...". Observers get nothing at this point; this is deliberate, because they get one combined message when the curtain ends.
2. **Frame 0.** The message, centred in a line of `▓`, shown in its own colours. This is the only frame that shows the complete message.
3. **The drip.** Each frame erases one character, taken from every third step of the shuffled plan (sea or text alike). About halfway through, each frame also erases a growing batch of message letters, and up to four more frames clear what is left of the text. From the second frame on, the sea is `█` instead of `▓`, and gaps open in the sea as well as in the words.
4. **The trailing drip.** 12 trailing sparse-drip frames.
5. **The end.** Three all-blank frames. The animation never returns to the message: the player's last sight is an empty line.

On the default message at width 78 the curtain runs 33-41 frames.

Example progression (colour codes left out):

```
▓▓▓▓▓▓A red haze blurs your vision as the world slips away...▓▓▓▓▓▓
██████A red h ze blurs your vision as the world slips away...██████
██ ███A red h ze blur  your vision as the world slips away...██████
██ ███A red h ze blur  your vision as the world slip  away...███ ██
# ... continues until message dissolves
```

### The message

The default message is "A red haze blurs your vision as the world slips away...", in mixed `|r`/`|R` red. On the death path, `at_death` calls `show_death_curtain(self)` with no message, and the default is used. A caller that passes a `message` overrides it, and that text is animated uncoloured. No caller in the tree passes one: the attack path and `at_death` both call `show_death_curtain(target)` bare. The curtain text itself never depends on the cause.

### Colour and centring

- Every `▓` and `█` gets a random `|r` or `|R`; colour sequences are always terminated with `|n`.
- Frame 0 shows the message in its own colours. From the second frame on, every remaining character, letters included, is randomly `|r` or `|R`.
- Centring strips Evennia colour codes (`_strip_color_codes`) before working out the padding, so the message is centred by its visible length, whatever its colour codes.
- Width: `_get_terminal_width(session)` gives the client's screen width, at least 60, or 78 if unknown. The curtain is one character narrower than that.

### Timing

- `frame_delay = 0.05`: the first gap between frames, in seconds.
- `delay_multiplier = 1.02`: each gap is 2% longer than the last, so the animation starts fast and slows down.
- On the default message at width 78: 33-41 frames over about 2.3-3.1 s.
- Set in `DeathCurtain.__init__`.

## What the room sees

Observers never see the animation: every frame goes to the dying character alone (`DeathCurtain._show_next_frame`), and the opening cause line goes to the victim alone.

When the curtain ends, observers get one line, chosen by cause and species (`get_death_cause_template`), rendered for each watcher by `msg_room_identity` so each sees the dying character by the name they know them by; the dying character is excluded. For a human who bled out: "{actor}'s lifeblood pools crimson around their still form."

When the death window closes, observers get "{actor}'s form grows utterly still, life's final spark extinguished forever."

## The cause of death

The curtain reads the cause from `Character.get_death_cause()` (`typeclasses/characters.py`), in `DeathCurtain.start_animation` and `DeathCurtain._on_animation_complete`.

Causes are checked in this order, and the first match wins: blood loss, heart failure, decapitation, a broken neck, brain death, organ failure (a septic spine), respiratory failure, organ failure (digestion), critical injuries. If the killing blow was recorded, `_with_death_blow` adds it after the cause: "blood loss from a stab wound to the chest", so the victim can read "Your body succumbs to blood loss from a stab wound to the chest."

If no cause can be read, `get_death_cause` returns "unknown causes", so the victim reads "Your body succumbs to unknown causes. The end draws near..." (or "Your body fails you. The end draws near..." if no cause comes back at all).

`debug_death_analysis()` is a separate splattercast-only report fired from `Character.at_death`; it never touches the curtain's path. The logic is duplicated, not shared, and the two copies differ three ways:

- `debug_death_analysis` lists every fatal condition; `get_death_cause` returns only the first in priority order.
- Zero `digestion` reads "LIVER FAILURE" in the debug report but "organ failure" in the player-facing cause.
- Only the player-facing path appends the killing blow, so the victim can hear "blood loss from a stab wound to the chest" where the debug report says just "BLOOD LOSS".

## Starting the curtain

`Character.at_death` starts the curtain with `show_death_curtain(self)`.

If the character dies in combat, `at_death` holds the curtain back (`ndb.death_curtain_pending`) so the kill message is read first. The attack code in `world/combat/attack.py` starts the curtain after the kill message; if it has not started 5 seconds later, a fallback in `at_death` starts it.

There is no test command. The curtain is exercised by dying. `@testdeathcurtain` (and `@testdeath` / `@murder`) were removed 2026-10-09 (#3383): the "animation test" ran the real completion pipeline on the living builder, attaching a death-progression script and narrating a death and a false revival to the room. Owner: *"That is a legacy command for...testing. We may not need it at all."*

## Messages to a dead character

This game overrides `Character.msg` (`typeclasses/characters.py`) to drop almost everything addressed to a dead character. The API the curtain uses is standard `character.msg()`, but the filter is not:

- A message with no `from_obj` is blocked outright.
- Non-staff and non-`death_progression` senders are blocked.
- Only a `death_curtain=True` kwarg lets the curtain's own traffic through. The curtain sets it on every frame and on the cause line. The flag is popped before `super()`, so it never reaches the client as an outputfunc.

The filter does not look at the text: frames with no `▓` in them (the trailing drip, which shows only `█`, the blank frames and the cause line) must still get through.

## Keeping other messages out

The death curtain has exclusive control over death messaging:

- Once a character is dead, the medical script sends no bleeding messages, and it stops ticking (it is kept, stopped, in case of revival). The medical ticker does not interrupt the animation with bleeding updates.
- The cause line is sent before the animation starts; the medical system stays silent during the curtain; the final death confirmation comes after the curtain completes.

## When the curtain ends

`DeathCurtain._on_animation_complete` starts the death progression and tells the room (above). For a beheading, the death then completes at once (see Death Progression Configuration).

All frames are generated before playback. They are scheduled with a non-persistent `delay`, so a reload during the curtain cuts it off before the death progression starts; `sweep_wedged_deaths` (`typeclasses/death_progression.py`) starts that progression at the next server start.

The curtain sends complete frames, not incremental changes.

## Death Progression Configuration

> **A beheading has no death window (#3835, owner ruling 2026-11-14).** "Is someone really dying if there head is missing? They should be a corpse." When the death is a beheading, the curtain plays for the dying player and tells the room the cause as for any death, and then the progression completes at once: no revival check and none of the dying messages. A player character gets the two closing lines, the room gets the final "form grows utterly still" line, and the corpse is made. The script's next tick is the backstop if that did not happen. Every other death keeps the window described here. That includes a destroyed brain, the other case #330 listed: the owner ruled it a "Death with a window" (#3248, 2026-09-26). The body is dead on the blow, and a new brain put in during the window is the one thing that brings it back, so a brain transplant needs the window.

The death system has two parts: the death curtain animation (about 2.3-3.1 seconds, 33-41 frames at `frame_delay` 0.05 × 1.02ⁿ, `DeathCurtain.__init__`) followed by a configurable death progression timer.

### Configuration Constants

All death progression timing is set in `world/combat/constants.py`:

| constant | value | meaning |
|---|---|---|
| `DEATH_PROGRESSION_DURATION` | 90 | total time before permanent death, in seconds |
| `DEATH_PROGRESSION_MESSAGE_COUNT` | 11 | number of progression messages sent |
| `DEATH_PROGRESSION_CHECK_INTERVAL` | derived: 4 | how often the script ticks, in seconds |

`DEATH_PROGRESSION_CHECK_INTERVAL` is not a literal. It is derived from the other two: the message spacing is `DEATH_PROGRESSION_DURATION // DEATH_PROGRESSION_MESSAGE_COUNT`, and the interval is `max(1, int(spacing * 0.6))`. At 90 s and 11 messages that is 8 × 0.6 → 4, so the death progression script ticks every 4 s. It re-asserts that interval from constants on every restart (`at_start`, #501 Phase 2).

### Common Configurations

- **Production (default):** `DEATH_PROGRESSION_DURATION = 90`, what the game runs on.
- **Testing:** `60` (faster iteration) or `30` (very fast testing).

### How It Works

1. **Death Curtain**: the animation plays (about 2.3-3.1 seconds, 33-41 frames).
2. **Death Progression**: the timer begins, with periodic messages.
3. **Medical Window**: characters can attempt revival during this time.
4. **Final Death**: after the duration expires, permanent death occurs.

Messages are spread evenly across the total duration. With 90 seconds and 11 messages, they come every ~8 seconds.

To apply a change, edit the constants, then `@reload` or restart the server. A change applies to future deaths only: `total_duration` and `message_intervals` are set once at `at_script_creation` and persist on the script, so a death already in flight keeps the old duration and spacing across a reload. Only `interval` is re-derived from constants on restart. A duration change therefore takes effect at the next death, not at the next reload.

## Writing death messages

For a caller that passes its own message to `show_death_curtain(character, message)`:

- Keep messages under 60 characters for the best visual effect.
- Use evocative, atmospheric language, and consider the pacing of the animation.
- Test with various message lengths; consider context-specific death messages.
- Examples: "The darkness claims your soul...", "You drift away into eternal rest...", "Your blood pools beneath you...", "Your essence fades into the void...".
- Watch animation performance on slower connections and client capabilities; adjust timing for server load.

## Unbuilt

- 📋 UNBUILT (no issue) **Multiple sea characters**: different background patterns for different death types.
- 📋 UNBUILT (no issue) **Colour themes**: ice (blue), fire (red/orange), nature (green), etc.
- 📋 UNBUILT (no issue) **Speed variations**: different timing profiles for different death causes.
- 📋 UNBUILT (no issue) **Sound integration**: audio cues synchronized with the visual effects.
- 📋 UNBUILT (no issue) **Multi-line support**: animate longer death messages across multiple lines.

## Not decided

- Whether 90 seconds is the intended production death window, or 360 seconds (6 minutes) is still wanted.

## Related documents

- [`proposals/DEATH_AND_SLEEVE_LIFECYCLE_SPEC.md`](proposals/DEATH_AND_SLEEVE_LIFECYCLE_SPEC.md): the death and sleeve lifecycle around the curtain and the progression timer.
