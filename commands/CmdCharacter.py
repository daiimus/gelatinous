from evennia import Command
from evennia.utils.search import search_object
from evennia.utils.utils import inherits_from
from world.combat.constants import (
    PERM_BUILDER, PERM_DEVELOPER,
    BOX_TOP_LEFT, BOX_TOP_RIGHT, BOX_BOTTOM_LEFT, BOX_BOTTOM_RIGHT,
    BOX_HORIZONTAL, BOX_VERTICAL, BOX_TEE_RIGHT, BOX_TEE_LEFT,
    COLOR_SUCCESS, COLOR_NORMAL,
    MAX_DESCRIPTION_LENGTH,
    VALID_LONGDESC_LOCATIONS,
    SKINTONE_PALETTE, VALID_SKINTONES,
    STAT_DESCRIPTORS, STAT_TIER_RANGES
)
from world.medical.utils import get_medical_status_description
import re


# ===================================================================
# CENTERING UTILITIES (from death_progression.py)
# ===================================================================

def _get_terminal_width(session=None):
    """Get terminal width from session, defaulting to 78 for MUD compatibility."""
    if session:
        try:
            detected_width = session.protocol_flags.get("SCREENWIDTH", [78])[0]
            return max(60, detected_width)  # Minimum 60 for readability
        except (IndexError, KeyError, TypeError):
            pass
    return 78


def _strip_color_codes(text):
    """Remove Evennia color codes from text to get actual visible length."""
    # Remove all |x codes (where x is any character) - same pattern as death curtain
    return re.sub(r'\|.', '', text)


def _center_text(text, width=None, session=None):
    """Center text using same approach as curtain_of_death.py for consistency."""
    if width is None:
        width = _get_terminal_width(session)
    
    # Use same width calculation as curtain for consistent centering
    # Reserve small buffer for color codes like the curtain does
    message_width = width - 1  # Match curtain_width calculation
    
    # Split into lines and center each line - same as curtain
    lines = text.split('\n')
    centered_lines = []
    
    for line in lines:
        if not line.strip():  # Empty line
            centered_lines.append("")
            continue
            
        # Calculate visible text length (without color codes) - same as curtain
        visible_text = _strip_color_codes(line)
        
        # Use Python's built-in center method for proper centering - same as curtain  
        centered_visible = visible_text.center(message_width)
        
        # Calculate the actual padding that center() applied
        padding_needed = message_width - len(visible_text)
        left_padding = padding_needed // 2
        
        # Apply the same left padding to the original colored text
        centered_line = " " * left_padding + line
        centered_lines.append(centered_line)
    
    return '\n'.join(centered_lines)


# ===================================================================
# STAT DESCRIPTOR UTILITIES
# ===================================================================

def get_stat_descriptor(stat_name, numeric_value):
    """
    Convert numeric stat value to descriptive word.
    
    Args:
        stat_name (str): Name of the stat ('grit', 'resonance', 'intellect', 'motorics')
        numeric_value (int): Numeric stat value (0-150)
        
    Returns:
        str: Descriptive word for the stat tier, or "Unknown" if invalid
    """
    # Validate stat name
    if stat_name not in STAT_DESCRIPTORS:
        return "Unknown"
    
    # Ensure numeric value is valid
    if not isinstance(numeric_value, (int, float)) or numeric_value < 0:
        numeric_value = 0
    
    numeric_value = int(numeric_value)
    
    # Handle values over 150
    if numeric_value > 150:
        numeric_value = 150
    
    # Find the appropriate tier
    for min_val, max_val in STAT_TIER_RANGES:
        if min_val <= numeric_value <= max_val:
            # Find the descriptor key for this range
            # The keys in STAT_DESCRIPTORS correspond to the max values of each range
            descriptor_key = max_val
            return STAT_DESCRIPTORS[stat_name].get(descriptor_key, "Unknown")
    
    # Fallback
    return "Unknown"


def get_stat_range(descriptor_word, stat_name):
    """
    Get numeric range for a descriptive word.
    
    Args:
        descriptor_word (str): Descriptive word (e.g., "Granite", "Moderate")
        stat_name (str): Name of the stat ('grit', 'resonance', 'intellect', 'motorics')
        
    Returns:
        tuple: (min_value, max_value) tuple, or (0, 0) if not found
    """
    # Validate stat name
    if stat_name not in STAT_DESCRIPTORS:
        return (0, 0)
    
    # Find the descriptor in the stat's mapping
    stat_descriptors = STAT_DESCRIPTORS[stat_name]
    
    # Look for the descriptor word (case-insensitive)
    descriptor_word = descriptor_word.lower()
    for max_val, word in stat_descriptors.items():
        if word.lower() == descriptor_word:
            # Find the corresponding range
            for min_val, range_max_val in STAT_TIER_RANGES:
                if range_max_val == max_val:
                    return (min_val, max_val)
    
    # Not found
    return (0, 0)


def get_stat_tier_info(stat_name, numeric_value):
    """
    Get comprehensive tier information for a stat value.
    
    Args:
        stat_name (str): Name of the stat
        numeric_value (int): Numeric stat value
        
    Returns:
        dict: Dictionary with 'descriptor', 'min_range', 'max_range', 'tier_letter'
    """
    descriptor = get_stat_descriptor(stat_name, numeric_value)
    min_range, max_range = get_stat_range(descriptor, stat_name)
    
    # Calculate tier letter (A-Z)
    tier_letter = "Z"  # Default
    if 0 <= numeric_value <= 150:
        for i, (min_val, max_val) in enumerate(STAT_TIER_RANGES):
            if min_val <= numeric_value <= max_val:
                tier_letter = chr(ord('A') + i)
                break
    
    return {
        'descriptor': descriptor,
        'min_range': min_range,
        'max_range': max_range,
        'tier_letter': tier_letter,
        'numeric_value': numeric_value
    }

class CmdStats(Command):
    """
    Access your GEL-MST psychophysical evaluation report.

    Usage:
      @stats / score
      @stats <target>          (Authorized personnel only)
      @stats/numeric           (Authorized personnel only - diagnostic mode)
      @stats/numeric <target>  (Authorized personnel only)

    Displays your subject evaluation from the Genetic Expression Liability - 
    Medical & Sociological Testing program. G.R.I.M. assessment parameters 
    are shown using standardized classification descriptors (A-Z tiers) for 
    efficient liability assessment.
    
    File reference includes subject ID and mortality revision count in Roman 
    numerals. Authorized personnel may access diagnostic numeric values for 
    detailed risk evaluation and resource allocation purposes.
    """

    key = "@stats"
    aliases = ["score"]
    locks = "cmd:all()"

    def func(self):
        "Implement the command."

        caller = self.caller
        target = caller
        
        # Parse switches manually
        raw_args = self.args.strip()
        switches = []
        args = raw_args
        
        if raw_args.startswith('/'):
            # Find the end of switches
            parts = raw_args[1:].split(None, 1)
            if parts:
                switch_part = parts[0]
                args = parts[1] if len(parts) > 1 else ""
                switches = [s.lower() for s in switch_part.split('/') if s]

        if args:
            if (
                self.account.check_permstring(PERM_BUILDER)
                or self.account.check_permstring(PERM_DEVELOPER)
            ):
                matches = search_object(args.strip(), exact=False)
                if matches:
                    target = matches[0]

        grit = target.grit
        resonance = target.resonance
        intellect = target.intellect
        motorics = target.motorics
        
        # Get descriptive words for stats
        grit_desc = get_stat_descriptor("grit", grit)
        resonance_desc = get_stat_descriptor("resonance", resonance)
        intellect_desc = get_stat_descriptor("intellect", intellect)
        motorics_desc = get_stat_descriptor("motorics", motorics)
        
        # Check if caller has admin permissions for detailed view
        show_numeric = (
            self.account.check_permstring(PERM_BUILDER) or 
            self.account.check_permstring(PERM_DEVELOPER)
        ) and "numeric" in switches
        
        # Get medical status using medical terminology
        if hasattr(target, 'medical_state') and target.medical_state:
            status_text, color_code = get_medical_status_description(target.medical_state)
            vitals_display = status_text
            vitals_color = color_code
        else:
            vitals_display = "NO DATA"
            vitals_color = ""

        # Format stat displays based on permissions
        if show_numeric:
            # Admin view: show descriptive word with exact numeric value
            grit_display = f"{grit_desc} ({grit})"
            resonance_display = f"{resonance_desc} ({resonance})"
            intellect_display = f"{intellect_desc} ({intellect})"
            motorics_display = f"{motorics_desc} ({motorics})"
        else:
            # Player view: only descriptive words
            grit_display = grit_desc
            resonance_display = resonance_desc
            intellect_display = intellect_desc
            motorics_display = motorics_desc

        # Convert death count to Roman numerals for file reference
        def to_roman(num):
            """Convert integer to Roman numeral."""
            val = [
                1000, 900, 500, 400,
                100, 90, 50, 40,
                10, 9, 5, 4,
                1
            ]
            syms = [
                "M", "CM", "D", "CD",
                "C", "XC", "L", "XL",
                "X", "IX", "V", "IV",
                "I"
            ]
            roman_num = ''
            i = 0
            while num > 0:
                for _ in range(num // val[i]):
                    roman_num += syms[i]
                    num -= val[i]
                i += 1
            return roman_num

        # Generate dynamic file reference and subject name
        # Note: Character name already includes Roman numeral (e.g., "Laszlo V")
        file_ref = f"GEL-MST/PR-{target.id}"
        file_ref_padded = f" File Reference: {file_ref}".ljust(48)
        
        # Use character name directly (already has Roman numeral)
        subject_name = target.key
        subject_line = f" Subject: {subject_name[:38]:<38}"

        # Dynamic formatting based on display mode
        if show_numeric:
            # Calculate exact padding for numeric mode to maintain 48-char width
            grit_content = f"              Grit:       {grit_display}"
            resonance_content = f"              Resonance:  {resonance_display}"
            intellect_content = f"              Intellect:  {intellect_display}"
            motorics_content = f"              Motorics:   {motorics_display}"
            
            # Pad each line to exactly 48 characters
            grit_line = grit_content.ljust(48)
            resonance_line = resonance_content.ljust(48)
            intellect_line = intellect_content.ljust(48)
            motorics_line = motorics_content.ljust(48)
        else:
            # Standard format for descriptive mode - centered stats
            grit_line = f"              Grit:       {grit_display:<12}          "
            resonance_line = f"              Resonance:  {resonance_display:<12}          "
            intellect_line = f"              Intellect:  {intellect_display:<12}          "
            motorics_line = f"              Motorics:   {motorics_display:<12}          "

        # Add vitals formatting to match other GRIM descriptors
        if show_numeric:
            # For numeric mode, vitals should follow the same pattern as other stats
            vitals_content = f"              Vitals:     {vitals_display}"
            vitals_line = vitals_content.ljust(48)
        else:
            # Standard format for descriptive mode - centered vitals
            vitals_line = f"              Vitals:     {vitals_color}{vitals_display:<12}{COLOR_SUCCESS}          "

        # Fixed format to exactly 48 visible characters per row
        string = f"""{COLOR_SUCCESS}{BOX_TOP_LEFT}{BOX_HORIZONTAL * 48}{BOX_TOP_RIGHT}{COLOR_NORMAL}
{COLOR_SUCCESS}{BOX_VERTICAL} PSYCHOPHYSICAL EVALUATION REPORT               {BOX_VERTICAL}{COLOR_NORMAL}
{COLOR_SUCCESS}{BOX_VERTICAL}{subject_line}{BOX_VERTICAL}{COLOR_NORMAL}
{COLOR_SUCCESS}{BOX_VERTICAL}{file_ref_padded}{BOX_VERTICAL}{COLOR_NORMAL}
{COLOR_SUCCESS}{BOX_TEE_RIGHT}{BOX_HORIZONTAL * 48}{BOX_TEE_LEFT}{COLOR_NORMAL}
{COLOR_SUCCESS}{BOX_VERTICAL}                                                {BOX_VERTICAL}{COLOR_NORMAL}
{COLOR_SUCCESS}{BOX_VERTICAL}{grit_line}{BOX_VERTICAL}{COLOR_NORMAL}
{COLOR_SUCCESS}{BOX_VERTICAL}{resonance_line}{BOX_VERTICAL}{COLOR_NORMAL}
{COLOR_SUCCESS}{BOX_VERTICAL}{intellect_line}{BOX_VERTICAL}{COLOR_NORMAL}
{COLOR_SUCCESS}{BOX_VERTICAL}{motorics_line}{BOX_VERTICAL}{COLOR_NORMAL}
{COLOR_SUCCESS}{BOX_VERTICAL}                                                {BOX_VERTICAL}{COLOR_NORMAL}
{COLOR_SUCCESS}{BOX_VERTICAL}{vitals_line}{BOX_VERTICAL}{COLOR_NORMAL}
{COLOR_SUCCESS}{BOX_VERTICAL}                                                {BOX_VERTICAL}{COLOR_NORMAL}
{COLOR_SUCCESS}{BOX_TEE_RIGHT}{BOX_HORIZONTAL * 48}{BOX_TEE_LEFT}{COLOR_NORMAL}
{COLOR_SUCCESS}{BOX_VERTICAL} Notes:                                         {BOX_VERTICAL}{COLOR_NORMAL}
{COLOR_SUCCESS}{BOX_VERTICAL}                                                {BOX_VERTICAL}{COLOR_NORMAL}
{COLOR_SUCCESS}{BOX_VERTICAL}                                                {BOX_VERTICAL}{COLOR_NORMAL}
{COLOR_SUCCESS}{BOX_BOTTOM_LEFT}{BOX_HORIZONTAL * 48}{BOX_BOTTOM_RIGHT}{COLOR_NORMAL}"""

        # Get session for terminal width detection
        session = None
        if hasattr(caller, 'sessions') and caller.sessions.all():
            session = caller.sessions.all()[0]
        
        # Center the entire stats display using death curtain approach
        centered_string = _center_text(string, session=session)
        caller.msg(centered_string)


class CmdLookPlace(Command):
    """
    Set your default room positioning description.
    
    Usage:
        @look_place <description>
        @look_place me is <description>
        @look_place me are <description>
        @look_place me is "<description>"
        @look_place is <description>
        @look_place are <description>
        @look_place "<description>"
        @look_place clear
    
    Examples:
        @look_place standing here.
        @look_place me is "sitting on a rock"
        @look_place me are "lounging lazily"
        @look_place me is "is lounging lazily"
        @look_place are crouched in the shadows
        @look_place clear
    
    This sets your default positioning that others see when they look at a room.
    Instead of appearing in a separate "Characters:" section, you'll appear naturally
    in the room description as "YourName is <your description>".
    
    Use 'clear' to remove your look_place and return to default display.
    """
    
    key = "@look_place"
    aliases = ["@lookplace"]
    locks = "cmd:all()"
    help_category = "Character"
    
    def func(self):
        """Execute the command."""
        caller = self.caller
        
        if not self.args:
            # Show current setting
            current = caller.look_place or "standing here."
            caller.msg(f"Your current look_place: '{current}'")
            return
        
        # Handle 'clear' command
        if self.args.strip().lower() in ('clear', 'none', 'remove'):
            caller.look_place = "standing here."
            caller.msg("Your look_place has been cleared and reset to 'standing here.'")
            return
        
        # Parse the description with smart 'is' handling
        description = self.parse_placement_description(self.args)
        
        if not description:
            caller.msg("Please provide a description for your look_place.")
            return
        
        # Check length limit to prevent abuse while allowing creativity
        if len(description) > 200:
            caller.msg(f"Your look_place description is too long ({len(description)} characters). Please keep it under 200 characters.")
            return
        
        # Ensure description ends with proper punctuation
        if not description.endswith(('.', '!', '?')):
            description += '.'
        
        # Set the look_place
        caller.look_place = description
        caller.msg(f"Your look_place is now: '{description}'")
        caller.msg("Others will see: '|c" + caller.get_display_name(caller) + f"|n is {description}'")
    
    def parse_placement_description(self, raw_input):
        """
        Parse various input formats to extract the placement description.
        
        Handles patterns like:
        - "standing here"
        - "me is standing here"  
        - "me is \"standing here\""
        - "is standing here"
        - "\"standing here\""
        - "me is \"is standing here\""
        
        Args:
            raw_input (str): The raw command arguments
            
        Returns:
            str: The cleaned placement description
        """
        text = raw_input.strip()
        
        # Remove outer quotes if present
        if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
            text = text[1:-1]
        
        # Handle "me is ..." pattern
        if text.lower().startswith('me is '):
            text = text[6:].strip()  # Remove "me is "
            
            # Remove inner quotes if present after "me is"
            if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
                text = text[1:-1]
        
        # Handle "is ..." pattern (without "me")
        elif text.lower().startswith('is '):
            text = text[3:].strip()  # Remove "is "
        
        # Clean up redundant "is" at the beginning
        # Handle cases like "me is \"is standing here\""
        if text.lower().startswith('is '):
            text = text[3:].strip()
        
        return text.strip()


class CmdTempPlace(Command):
    """
    Set a temporary room positioning description.
    
    Usage:
        @temp_place <description>
        @temp_place me is <description>
        @temp_place me are <description>
        @temp_place me is "<description>"
        @temp_place is <description>
        @temp_place are <description>
        @temp_place "<description>"
        @temp_place clear
    
    Examples:
        @temp_place hiding behind a tree.
        @temp_place me is "examining the wall closely"
        @temp_place me are "investigating something"
        @temp_place me is "is investigating something"
        @temp_place are crouched and ready to spring
        @temp_place clear
    
    This sets a temporary positioning that overrides your @look_place.
    It will be automatically cleared when you move to a different room.
    
    Use 'clear' to remove your temp_place immediately.
    """
    
    key = "@temp_place"
    aliases = ["@tempplace"]
    locks = "cmd:all()"
    help_category = "Character"
    
    def func(self):
        """Execute the command."""
        caller = self.caller
        
        if not self.args:
            # Show current setting
            current = caller.temp_place or ""
            if current:
                caller.msg(f"Your current temp_place: '{current}'")
            else:
                caller.msg("You have no temp_place set.")
            return
        
        # Handle 'clear' command
        if self.args.strip().lower() in ('clear', 'none', 'remove'):
            caller.temp_place = ""
            caller.msg("Your temp_place has been cleared.")
            return
        
        # Parse the description with smart 'is' handling
        description = self.parse_placement_description(self.args)
        
        if not description:
            caller.msg("Please provide a description for your temp_place.")
            return
        
        # Check length limit to prevent abuse while allowing creativity
        if len(description) > 200:
            caller.msg(f"Your temp_place description is too long ({len(description)} characters). Please keep it under 200 characters.")
            return
        
        # Ensure description ends with proper punctuation
        if not description.endswith(('.', '!', '?')):
            description += '.'
        
        # Set the temp_place
        caller.temp_place = description
        caller.msg(f"Your temp_place is now: '{description}'")
        caller.msg("Others will see: '|c" + caller.get_display_name(caller) + f"|n is {description}'")
        caller.msg("This will be cleared when you move to a different room.")
    
    def parse_placement_description(self, raw_input):
        """
        Parse various input formats to extract the placement description.
        
        Same logic as CmdLookPlace for consistency.
        """
        text = raw_input.strip()
        
        # Remove outer quotes if present
        if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
            text = text[1:-1]
        
        # Handle "me is ..." pattern
        if text.lower().startswith('me is '):
            text = text[6:].strip()  # Remove "me is "
            
            # Remove inner quotes if present after "me is"
            if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
                text = text[1:-1]
        
        # Handle "is ..." pattern (without "me")
        elif text.lower().startswith('is '):
            text = text[3:].strip()  # Remove "is "
        
        # Clean up redundant "is" at the beginning
        # Handle cases like "me is \"is standing here\""
        if text.lower().startswith('is '):
            text = text[3:].strip()
        
        return text.strip()


class CmdLongdesc(Command):
    """
    Set or view detailed descriptions for your character's body parts.

    Usage:
        @longdesc <location> "<description>"    - Set description for a body part
        @longdesc <location>                    - View current description for location
        @longdesc                               - List all your current longdescs
        @longdesc/list                          - List all available body locations
        @longdesc/clear <location>              - Remove description for location

    Staff Usage:
        @longdesc <character> <location> "<description>"  - Set on another character
        @longdesc/clear <character> <location>             - Clear on another character

    Examples:
        @longdesc face "weathered features with high cheekbones"
        @longdesc left_eye "a piercing blue eye with flecks of gold"
        @longdesc right_hand "a prosthetic metal hand with intricate engravings"
        @longdesc/clear face
        @longdesc face
        @longdesc/list

    Body locations include: head, face, left_eye, right_eye, left_ear, right_ear,
    neck, chest, back, abdomen, groin, left_arm, right_arm, left_hand, right_hand,
    left_thigh, right_thigh, left_shin, right_shin, left_foot, right_foot.

    Extended anatomy (tails, wings, etc.) is supported for modified characters.
    Descriptions appear when others look at you, integrated with your base description.
    """

    key = "@longdesc"
    aliases = []
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        """Execute the longdesc command."""
        caller = self.caller
        raw_args = self.args.strip()
        
        # Parse switches manually since we're not using MuxCommand
        switches = []
        args = raw_args
        
        if raw_args.startswith('/'):
            # Find the end of switches
            parts = raw_args[1:].split(None, 1)
            if parts:
                switch_part = parts[0]
                args = parts[1] if len(parts) > 1 else ""
                switches = [s.lower() for s in switch_part.split('/') if s]

        # Handle switches
        if "list" in switches:
            self._handle_list_locations(caller)
            return

        if "clear" in switches:
            self._handle_clear(caller, args)
            return

        # Parse arguments for main command
        if not args:
            # Show all current longdescs
            self._show_all_longdescs(caller)
            return

        # Check if this is staff targeting another character
        target_char = None
        remaining_args = args

        if caller.locks.check_lockstring(caller, f"dummy:perm({PERM_BUILDER}) or perm_above({PERM_BUILDER})"):
            # Staff can target other characters
            parts = args.split(None, 1)
            if len(parts) >= 1:
                # Try different search approaches
                potential_target = caller.search(parts[0], global_search=True, quiet=True)
                
                if not potential_target:
                    # Try searching without global_search
                    potential_target = caller.search(parts[0], quiet=True)
                
                if not potential_target:
                    # Try searching in the same location as the caller
                    if caller.location:
                        potential_target = caller.location.search(parts[0], quiet=True)
                        
                        # If not found in location, try searching the location's contents more broadly
                        if not potential_target:
                            for obj in caller.location.contents:
                                if obj.key.lower() == parts[0].lower():
                                    potential_target = obj
                                    break
                
                if potential_target:
                    # If it's a list, get the first item
                    if isinstance(potential_target, list):
                        if potential_target:
                            actual_target = potential_target[0]
                        else:
                            actual_target = None
                    else:
                        actual_target = potential_target
                    
                    if actual_target and hasattr(actual_target, 'longdesc'):
                        target_char = actual_target
                        remaining_args = parts[1] if len(parts) > 1 else ""

        if not target_char:
            target_char = caller
            remaining_args = args

        # Parse location and description
        if '"' in remaining_args:
            # Setting a description
            if remaining_args.count('"') < 2:
                caller.msg("Please enclose the description in quotes.")
                return

            quote_start = remaining_args.find('"')
            quote_end = remaining_args.rfind('"')

            if quote_start == quote_end:
                caller.msg("Please provide both opening and closing quotes.")
                return

            location = remaining_args[:quote_start].strip()
            description = remaining_args[quote_start + 1:quote_end]

            self._set_longdesc(caller, target_char, location, description)

        else:
            # Viewing a specific location
            location = remaining_args.strip()
            if location:
                self._view_longdesc(caller, target_char, location)
            else:
                self._show_all_longdescs(caller, target_char)

    def _handle_list_locations(self, caller):
        """Show all available body locations for the character."""
        locations = caller.get_available_locations()
        if not locations:
            caller.msg("No body locations available.")
            return

        # Group locations by type for better display
        from world.combat.constants import ANATOMICAL_REGIONS

        grouped_locations = {}
        extended_locations = []

        for location in locations:
            found_region = None
            for region_name, region_locations in ANATOMICAL_REGIONS.items():
                if location in region_locations:
                    if region_name not in grouped_locations:
                        grouped_locations[region_name] = []
                    grouped_locations[region_name].append(location)
                    found_region = True
                    break
            
            if not found_region:
                extended_locations.append(location)

        # Display grouped locations
        caller.msg("|wAvailable body locations:|n")
        
        region_display_names = {
            "head_region": "Head Region",
            "torso_region": "Torso Region", 
            "arm_region": "Arm Region",
            "leg_region": "Leg Region"
        }

        for region_name in ["head_region", "torso_region", "arm_region", "leg_region"]:
            if region_name in grouped_locations:
                display_name = region_display_names[region_name]
                locations_list = ", ".join(grouped_locations[region_name])
                caller.msg(f"  |c{display_name}:|n {locations_list}")

        if extended_locations:
            caller.msg(f"  |cExtended Anatomy:|n {', '.join(extended_locations)}")

    def _handle_clear(self, caller, args):
        """Handle clear commands."""
        if not args:
            # Clear all longdescs with confirmation
            self._clear_all_longdescs(caller)
            return

        # Check if targeting another character (staff only)
        target_char = None
        location = args

        if caller.locks.check_lockstring(caller, f"dummy:perm({PERM_BUILDER}) or perm_above({PERM_BUILDER})"):
            parts = args.split(None, 1)
            if len(parts) >= 1:
                # Use quiet=True to prevent "Could not find" messages
                potential_target = caller.search(parts[0], global_search=True, quiet=True)
                if potential_target and hasattr(potential_target, 'longdesc'):
                    target_char = potential_target
                    location = parts[1] if len(parts) > 1 else ""

        if not target_char:
            target_char = caller
            location = args

        if not location:
            # Clear all for target character
            self._clear_all_longdescs(caller, target_char)
        else:
            # Clear specific location
            self._clear_specific_location(caller, target_char, location)

    def _set_longdesc(self, caller, target_char, location, description):
        """Set a longdesc for a specific location."""
        if not location:
            caller.msg("Please specify a body location.")
            return

        # Validate location exists on character
        if not target_char.has_location(location):
            caller.msg(f"'{location}' is not a valid body location for {target_char.get_display_name(caller)}.")
            available = ", ".join(target_char.get_available_locations()[:10])  # Show first 10
            caller.msg(f"Available locations include: {available}...")
            caller.msg("Use '@longdesc/list' to see all available locations.")
            return

        # Validate description length
        if len(description) > MAX_DESCRIPTION_LENGTH:
            caller.msg(f"Description is too long ({len(description)} characters). Maximum is {MAX_DESCRIPTION_LENGTH} characters.")
            return

        if len(description.strip()) == 0:
            # Empty description means clear
            target_char.set_longdesc(location, None)
            if target_char == caller:
                caller.msg(f"Cleared description for {location}.")
            else:
                caller.msg(f"Cleared description for {location} on {target_char.get_display_name(caller)}.")
            return

        # Set the description
        success = target_char.set_longdesc(location, description.strip())
        if success:
            if target_char == caller:
                caller.msg(f"Set description for {location}: \"{description.strip()}\"")
            else:
                caller.msg(f"Set description for {location} on {target_char.get_display_name(caller)}: \"{description.strip()}\"")
        else:
            caller.msg("Failed to set description. Please try again.")

    def _view_longdesc(self, caller, target_char, location):
        """View a specific longdesc."""
        if not target_char.has_location(location):
            caller.msg(f"'{location}' is not a valid body location.")
            return

        description = target_char.get_longdesc(location)
        if description:
            if target_char == caller:
                caller.msg(f"{location}: \"{description}\"")
            else:
                caller.msg(f"{target_char.get_display_name(caller)}'s {location}: \"{description}\"")
        else:
            if target_char == caller:
                caller.msg(f"No description set for {location}.")
            else:
                caller.msg(f"No description set for {location} on {target_char.get_display_name(caller)}.")

    def _show_all_longdescs(self, caller, target_char=None):
        """Show all current longdescs for a character."""
        if not target_char:
            target_char = caller

        longdescs = target_char.longdesc or {}
        set_descriptions = {loc: desc for loc, desc in longdescs.items() if desc}

        if not set_descriptions:
            if target_char == caller:
                caller.msg("You have no longdesc descriptions set.")
            else:
                caller.msg(f"{target_char.get_display_name(caller)} has no longdesc descriptions set.")
            return

        if target_char == caller:
            caller.msg("|wYour current longdesc descriptions:|n")
        else:
            caller.msg(f"|w{target_char.get_display_name(caller)}'s longdesc descriptions:|n")

        # Show in anatomical order
        from world.combat.constants import ANATOMICAL_DISPLAY_ORDER

        displayed = set()
        for location in ANATOMICAL_DISPLAY_ORDER:
            if location in set_descriptions:
                caller.msg(f"  |c{location}:|n \"{set_descriptions[location]}\"")
                displayed.add(location)

        # Show any extended anatomy
        for location, description in set_descriptions.items():
            if location not in displayed:
                caller.msg(f"  |c{location}:|n \"{description}\"")

    def _clear_specific_location(self, caller, target_char, location):
        """Clear a specific location's longdesc."""
        if not target_char.has_location(location):
            caller.msg(f"'{location}' is not a valid body location.")
            return

        current_desc = target_char.get_longdesc(location)
        if not current_desc:
            if target_char == caller:
                caller.msg(f"No description set for {location}.")
            else:
                caller.msg(f"No description set for {location} on {target_char.get_display_name(caller)}.")
            return

        target_char.set_longdesc(location, None)
        if target_char == caller:
            caller.msg(f"Cleared description for {location}.")
        else:
            caller.msg(f"Cleared description for {location} on {target_char.get_display_name(caller)}.")

    def _clear_all_longdescs(self, caller, target_char=None):
        """Clear all longdescs with confirmation."""
        if not target_char:
            target_char = caller

        longdescs = target_char.longdesc or {}
        set_descriptions = {loc: desc for loc, desc in longdescs.items() if desc}

        if not set_descriptions:
            if target_char == caller:
                caller.msg("You have no longdesc descriptions to clear.")
            else:
                caller.msg(f"{target_char.get_display_name(caller)} has no longdesc descriptions to clear.")
            return

        # Simple confirmation - clear all
        for location in set_descriptions:
            target_char.set_longdesc(location, None)

        count = len(set_descriptions)
        if target_char == caller:
            caller.msg(f"Cleared all {count} longdesc descriptions.")
        else:
            caller.msg(f"Cleared all {count} longdesc descriptions from {target_char.get_display_name(caller)}.")


class CmdSkintone(Command):
    """
    Set your character's skintone for longdesc display coloring.

    Usage:
      @skintone <tone>
      @skintone list
      @skintone clear
      @skintone <character> <tone>    (staff only)
      @skintone <character> clear     (staff only)

    Sets the color tone used for your character's longdesc descriptions.
    This creates visual distinction between your character's body/skin
    descriptions and clothing descriptions.

    Available tones: porcelain, pale, fair, light, medium, olive, tan, brown, dark, deep

    Examples:
      @skintone tan
      @skintone list
      @skintone clear
    """
    
    key = "@skintone"
    aliases = ["skintone"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller
        args = self.args.strip()
        
        if not args:
            self._show_current_skintone(caller)
            return
            
        # Handle list command
        if args.lower() == "list":
            self._show_available_tones(caller)
            return
            
        # Handle clear command
        if args.lower() == "clear":
            self._clear_skintone(caller, caller)
            return
            
        # Check if this might be staff targeting another character
        parts = args.split()
        if len(parts) == 2 and caller.locks.check_lockstring(caller, "perm(Builder)"):
            character_name, tone_or_clear = parts
            target = self._find_character(caller, character_name)
            if target:
                if tone_or_clear.lower() == "clear":
                    self._clear_skintone(caller, target)
                else:
                    self._set_skintone(caller, target, tone_or_clear.lower())
                return
            else:
                caller.msg(f"Could not find character '{character_name}'.")
                return
        
        # Single argument - set skintone on self
        tone = args.lower()
        self._set_skintone(caller, caller, tone)

    def _show_current_skintone(self, caller):
        """Show the caller's current skintone setting"""
        skintone = caller.db.skintone
        if skintone:
            color_code = SKINTONE_PALETTE.get(skintone, "")
            if color_code:
                colored_skintone = f"{color_code}{skintone}|n"
                caller.msg(f"Your current skintone is: {colored_skintone}")
            else:
                caller.msg(f"Your current skintone is: {skintone} (invalid)")
        else:
            caller.msg("You have no skintone set. Longdescs will appear uncolored.")
            
    def _show_available_tones(self, caller):
        """Display available skintones with previews"""
        caller.msg("|wAvailable Skintones:|n")
        caller.msg("")
        
        # All tones in order
        all_tones = ["porcelain", "pale", "fair", "light", "golden", "tan", "olive", "brown", "rich"]
        for tone in all_tones:
            color_code = SKINTONE_PALETTE[tone]
            caller.msg("  " + tone.ljust(10) + " - " + f"{color_code}Sample text|n")
            
        caller.msg("")
        caller.msg("Use: |w@skintone <tone>|n to set your skintone")
        caller.msg("Use: |w@skintone clear|n to remove coloring")

    def _set_skintone(self, caller, target, tone):
        """Set skintone on target character"""
        if tone not in VALID_SKINTONES:
            caller.msg(f"'{tone}' is not a valid skintone. Use '@skintone list' to see available options.")
            return
            
        target.db.skintone = tone
        color_code = SKINTONE_PALETTE[tone]
        colored_tone = color_code + tone + "|n"
        
        if target == caller:
            caller.msg(f"Set your skintone to: {colored_tone}")
        else:
            caller.msg(f"Set {target.name}'s skintone to: {colored_tone}")
            target.msg(f"{caller.name} has set your skintone to: {colored_tone}")

    def _clear_skintone(self, caller, target):
        """Clear skintone from target character"""
        if target.db.skintone is not None:
            del target.db.skintone
            
        if target == caller:
            caller.msg("Cleared your skintone. Longdescs will appear uncolored.")
        else:
            caller.msg(f"Cleared {target.name}'s skintone.")
            target.msg(f"{caller.name} has cleared your skintone setting.")

    def _find_character(self, caller, character_name):
        """Find a character by name for staff targeting"""
        # Use Evennia's search system to find the character
        results = search_object(character_name, typeclass="typeclasses.characters.Character")
        
        if not results:
            return None
        elif len(results) > 1:
            # Multiple matches - try to find exact match
            exact_matches = [obj for obj in results if obj.name.lower() == character_name.lower()]
            if len(exact_matches) == 1:
                return exact_matches[0]
            else:
                caller.msg(f"Multiple characters match '{character_name}': {', '.join(obj.name for obj in results)}")
                return None
        else:
            return results[0]
