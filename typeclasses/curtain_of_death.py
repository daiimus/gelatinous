"""
Curtain of Death - Death Animation System for Evennia

This module provides a "dripping blood" death animation that creates
a curtain effect by progressively removing characters from a message.
Based on the elegant design that centers text in a "sea" of characters
and creates a dripping effect by removing characters in sequence.
Compatible with Evennia's messaging and delay systems.
"""

import random
from evennia.utils import delay


def _get_terminal_width(session=None):
    """
    Get terminal width from session, defaulting to 78 for MUD compatibility.
    
    Args:
        session: Evennia session object to get width from
        
    Returns:
        int: Terminal width in characters
    """
    if session:
        # Use Evennia's built-in screen width detection
        try:
            detected_width = session.protocol_flags.get("SCREENWIDTH", [78])[0]
            return max(60, detected_width)  # Minimum 60 for readability
        except (IndexError, KeyError, TypeError):
            # Fallback if protocol flags aren't available or malformed
            pass
    return 78


def _colorize_evennia(text):
    """Apply Evennia color codes to text for a blood-red effect."""
    # Use Evennia's color system - random red variations for blood effect
    colors = ["|r", "|R"]  # Red variations for blood effect
    
    colored = []
    for char in text:
        if char != " ":  # Don't colorize spaces
            colored.append(f"{random.choice(colors)}{char}")
        else:
            colored.append(char)
    
    colored.append("|n")  # Always reset color at the end
    return "".join(colored)


def _strip_color_codes(text):
    """
    Remove Evennia color codes to get the visible text length.
    
    Args:
        text (str): Text with color codes
        
    Returns:
        str: Text without color codes
    """
    import re
    # Remove all |x and |xx codes (where x is any character)
    return re.sub(r'\|.', '', text)


def curtain_of_death(text, width=None, session=None):
    """
    Create a "dripping blood" death curtain animation.
    
    Args:
        text (str): The message to animate
        width (int, optional): Width of the display area
        session: Evennia session object for width detection
        
    Returns:
        List[str]: Animation frames
    """
    if width is None:
        width = _get_terminal_width(session)
    
    # Reserve small buffer for color codes in curtain animation
    # Since we add color codes to padding blocks, we need to account for them
    curtain_width = width - 1  # Small buffer for color code overhead
    
    # Calculate visible text length (without color codes)
    visible_text = _strip_color_codes(text)
    
    # For the first frame, use the text as-is (with its color codes)
    # Center it with colored blocks, but ensure total doesn't exceed width
    padding_needed = curtain_width - len(visible_text)
    
    if padding_needed <= 0:
        # Message is too long for terminal, use as-is without padding
        first_frame = text
    else:
        left_padding = padding_needed // 2
        right_padding = padding_needed - left_padding
        
        # Create colored padding blocks
        left_blocks = _colorize_evennia("▓" * left_padding)
        right_blocks = _colorize_evennia("▓" * right_padding)
        
        first_frame = left_blocks + text + right_blocks
    
    # For subsequent frames, work with a plain version for character removal
    plain_padded = visible_text.center(curtain_width, "▓")
    chars = list(plain_padded)
    
    # Build the "plan": a shuffled list of (index, drop-distance) pairs
    plan = [(i, random.randint(1, i + 1)) for i in range(len(chars))]
    random.shuffle(plan)
    
    frames = [first_frame]  # First frame with proper colors
    
    # Create dripping effect by removing characters in planned sequence
    # Process every 3rd character initially for the main text removal
    text_chars = [i for i, c in enumerate(chars) if c not in [" ", "▓", "█"]]  # Track text chars from start
    
    for frame_num, (idx, _) in enumerate(plan[::3]):  # Skip every 3rd character to reduce frame count
        if chars[idx] == " ":  # Skip spaces
            continue
        chars[idx] = " "  # 'Erase' the character
        
        # After a few frames, start also removing text characters exponentially
        if frame_num > len(plan) // 6:  # Start text removal after 1/6 of main dripping
            # Exponentially increase text character removal as dripping progresses
            text_removal_rate = min(0.4, 0.05 * (frame_num - len(plan) // 6) ** 1.3)
            chars_to_remove = int(len(text_chars) * text_removal_rate)
            
            for _ in range(min(chars_to_remove, len(text_chars))):
                if text_chars:
                    text_idx = text_chars.pop(random.randint(0, len(text_chars) - 1))
                    chars[text_idx] = " "
        
        frame = "".join(chars).center(curtain_width, "█")  # Replace the sea with different char
        frames.append(_colorize_evennia(frame))
    
    # Clean up any remaining text characters more gently
    # Find all remaining non-space, non-block characters (the text)
    remaining_text_chars = [i for i, c in enumerate(chars) if c not in [" ", "▓", "█"]]
    
    # More gradually remove remaining text in fewer frames since most should be gone
    text_removal_frames = 4  # Reduced since most text should already be removed
    for frame_num in range(text_removal_frames):
        if not remaining_text_chars:
            break
        
        # Remove remaining text each frame 
        chars_per_frame = max(1, len(remaining_text_chars) // (text_removal_frames - frame_num + 1))
        
        for _ in range(min(chars_per_frame, len(remaining_text_chars))):
            if remaining_text_chars:
                idx = remaining_text_chars.pop(random.randint(0, len(remaining_text_chars) - 1))
                chars[idx] = " "
        
        frame = "".join(chars).center(curtain_width, "█")
        frames.append(_colorize_evennia(frame))

    # Add several more frames of continued dripping
    # Create trailing drip effect - scattered blocks that continue falling
    remaining_blocks = [i for i, c in enumerate(chars) if c == "▓"]    # Create 8-12 trailing frames with sparse dripping
    trailing_frames = 12
    for frame_num in range(trailing_frames):
        # Gradually remove more blocks with each frame, but not all at once
        removal_rate = 0.15 + (frame_num * 0.05)  # Start slow, speed up
        blocks_to_remove = max(1, int(len(remaining_blocks) * removal_rate))
        
        # Remove random blocks with some clustering for more organic feel
        for _ in range(min(blocks_to_remove, len(remaining_blocks))):
            if remaining_blocks:
                # Sometimes remove clustered blocks for streaky drip effect
                if random.random() < 0.3 and len(remaining_blocks) > 1:
                    # Find adjacent blocks occasionally
                    idx = random.choice(remaining_blocks)
                    adjacent = [i for i in remaining_blocks if abs(i - idx) <= 2]
                    if adjacent:
                        idx = random.choice(adjacent)
                else:
                    idx = random.choice(remaining_blocks)
                remaining_blocks.remove(idx)
                chars[idx] = " "
        
        # Create sparse frame with remaining blocks
        frame = "".join(chars)
        frames.append(_colorize_evennia(frame))
    
    # Add a few final empty frames for smooth transition
    for i in range(3):
        final_frame = " " * curtain_width
        frames.append(_colorize_evennia(final_frame))
    
    return frames


class DeathCurtain:
    """
    Creates a "dripping blood" death animation by progressively removing
    characters from a death message to create a curtain effect.
    """
    
    def __init__(self, character, message=None):
        """
        Initialize the death curtain animation.
        
        Args:
            character: The character object to send the animation to
            message (str, optional): Custom death message
        """
        self.character = character
        self.location = character.location
        
        # Get session for width detection
        self.session = None
        if character and hasattr(character, 'sessions') and character.sessions.get():
            self.session = character.sessions.get()[0]
        
        # Get terminal width for this character's session
        self.width = _get_terminal_width(self.session)
        
        # Create informed death message based on cause
        if message is None:
            # Always use the beautiful mixed red message for the curtain
            message = "|rA |Rred |rhaze |Rblurs |ryour |Rvision |ras |Rthe |rworld |Rslips |raway|R...|n"
        
        self.message = message
        self.frames = curtain_of_death(message, session=self.session)
        self.current_frame = 0
        self.frame_delay = 0.05  # Start slower than before (was 0.015)
        self.delay_multiplier = 1.02  # More significant slowdown (was 1.005)
        
    def start_animation(self):
        """Start the death curtain animation."""
        # Send initial death messages before the curtain starts
        if self.location:
            # Get death cause for both messages
            death_cause = None
            if hasattr(self.character, 'get_death_cause'):
                death_cause = self.character.get_death_cause()
            
            # Send victim's initial death message
            if self.character:
                if death_cause:
                    victim_msg = f"|rYour body succumbs to {death_cause}. The end draws near...|n"
                else:
                    victim_msg = f"|rYour body fails you. The end draws near...|n"
                self.character.msg(victim_msg)
            
            # Don't send initial "dying from" message to observers - 
            # we'll send a combined death message later
        
        self.current_frame = 0
        self._show_next_frame()
        
    def _show_next_frame(self):
        """Show the next frame of the animation."""
        if self.current_frame < len(self.frames):
            # Send current frame to the dying character
            if self.character:
                self.character.msg(self.frames[self.current_frame])
            
            self.current_frame += 1
            
            # Schedule next frame with increasing delay (like original)
            delay(self.frame_delay, self._show_next_frame)
            self.frame_delay *= self.delay_multiplier
        else:
            # Animation complete, trigger death
            self._on_animation_complete()
            
    def _on_animation_complete(self):
        """Called when the animation completes."""
        # Send a single, vivid death message that incorporates the cause
        if self.location:
            death_cause = None
            if hasattr(self.character, 'get_death_cause'):
                death_cause = self.character.get_death_cause()
            
            if death_cause:
                # Create vivid death descriptions based on cause
                if 'blood loss' in death_cause.lower():
                    death_msg = f"|R{self.character.key}'s lifeblood pools crimson around their still form.|n"
                elif 'heart failure' in death_cause.lower():
                    death_msg = f"|R{self.character.key} clutches their chest one last time before going still.|n"
                elif 'head' in death_cause.lower() or 'brain' in death_cause.lower():
                    death_msg = f"|R{self.character.key}'s eyes lose focus as they collapse, unmoving.|n"
                elif 'poison' in death_cause.lower():
                    death_msg = f"|R{self.character.key} convulses violently before falling silent.|n"
                elif 'fire' in death_cause.lower() or 'burn' in death_cause.lower():
                    death_msg = f"|R{self.character.key}'s charred form crumples to the ground.|n"
                elif 'stab' in death_cause.lower() or 'slash' in death_cause.lower():
                    death_msg = f"|R{self.character.key} gasps once, crimson flowing, then goes still.|n"
                else:
                    # Generic death message with cause hint
                    death_msg = f"|R{self.character.key} draws their final breath and grows still.|n"
            else:
                # No cause specified
                death_msg = f"|R{self.character.key} draws their final breath and grows still.|n"
                
            self.location.msg_contents(death_msg, exclude=[self.character])
        
        # Start death progression system after death curtain completes
        try:
            from .death_progression import start_death_progression
            script = start_death_progression(self.character)
            
            # Debug logging
            try:
                from evennia.comms.models import ChannelDB
                splattercast = ChannelDB.objects.get_channel("Splattercast")
                splattercast.msg(f"DEATH_CURTAIN: Death progression started for {self.character.key}, script: {script}")
            except Exception:
                pass
                
        except Exception as e:
            # Debug logging for any errors
            try:
                from evennia.comms.models import ChannelDB
                splattercast = ChannelDB.objects.get_channel("Splattercast")
                splattercast.msg(f"DEATH_CURTAIN_ERROR: Failed to start death progression for {self.character.key}: {e}")
            except Exception:
                pass


def show_death_curtain(character, message=None):
    """
    Convenience function to show the death curtain animation.
    
    Args:
        character: The character object to show the animation to
        message (str, optional): Custom death message
    """
    curtain = DeathCurtain(character, message)
    curtain.start_animation()