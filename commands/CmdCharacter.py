from evennia import Command
from evennia.utils.search import search_object
from commands._identity_targeting import resolve_admin_target
from world.combat.constants import (
    PERM_BUILDER, PERM_DEVELOPER,
    BOX_TOP_LEFT, BOX_TOP_RIGHT, BOX_BOTTOM_LEFT, BOX_BOTTOM_RIGHT,
    BOX_HORIZONTAL, BOX_VERTICAL, BOX_TEE_RIGHT, BOX_TEE_LEFT,
    COLOR_SUCCESS, COLOR_NORMAL,
    MAX_DESCRIPTION_LENGTH,
    VALID_LONGDESC_LOCATIONS,
    SKINTONE_PALETTE, VALID_SKINTONES,
    STAT_DESCRIPTORS, STAT_TIER_RANGES,
    ANATOMICAL_REGIONS, ANATOMICAL_DISPLAY_ORDER,
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
        
        # Calculate the actual padding that center() applied
        padding_needed = message_width - len(visible_text)
        left_padding = padding_needed // 2
        
        # Apply the same left padding to the original colored text
        centered_line = " " * left_padding + line
        centered_lines.append(centered_line)
    
    return '\n'.join(centered_lines)


# ===================================================================
# PLACEMENT DESCRIPTION PARSER
# ===================================================================

def _parse_placement_description(raw_input):
    """
    Parse various input formats to extract a placement description.

    Handles patterns like:
    - "standing here"
    - "me is standing here"
    - "me are lounging lazily"
    - "me is \"standing here\""
    - "is standing here"
    - "are crouched in the shadows"
    - "\"standing here\""
    - "me is \"is standing here\""

    Args:
        raw_input (str): The raw command arguments.

    Returns:
        str: The cleaned placement description.
    """
    text = raw_input.strip()

    # Remove outer quotes if present
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        text = text[1:-1]

    # Handle "me is ..." / "me are ..." patterns
    if text.lower().startswith('me is '):
        text = text[6:].strip()
        # Remove inner quotes if present after "me is"
        if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
            text = text[1:-1]
    elif text.lower().startswith('me are '):
        text = text[7:].strip()
        if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
            text = text[1:-1]

    # Handle "is ..." / "are ..." patterns (without "me")
    elif text.lower().startswith('is '):
        text = text[3:].strip()
    elif text.lower().startswith('are '):
        text = text[4:].strip()

    # Clean up redundant "is"/"are" at the beginning
    # Handle cases like "me is \"is standing here\""
    if text.lower().startswith('is '):
        text = text[3:].strip()
    elif text.lower().startswith('are '):
        text = text[4:].strip()

    return text.strip()


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
        """Delegate to module-level parser."""
        return _parse_placement_description(raw_input)


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
        """Delegate to module-level parser."""
        return _parse_placement_description(raw_input)


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
            # Staff can target other characters via identity-aware lookup
            # (same-room sdesc/recognition match) with global key fallback.
            parts = args.split(None, 1)
            if len(parts) >= 1:
                actual_target = resolve_admin_target(caller, parts[0])
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
                potential_target = resolve_admin_target(caller, parts[0])
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
        if len(parts) == 2 and caller.locks.check_lockstring(caller, f"dummy:perm({PERM_BUILDER}) or perm_above({PERM_BUILDER})"):
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
        if skintone is not None:
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
        """Find a character by name for staff targeting.

        Uses the identity-aware admin lookup: local sdesc/recognition
        match in caller's room first, then global key search fallback.
        """
        return resolve_admin_target(caller, character_name)


# ===================================================================
# IDENTITY SYSTEM COMMANDS
# ===================================================================


class CmdShortdesc(Command):
    """
    View or change your short description keyword.

    Usage:
      @shortdesc               - show current keyword and open selection menu
      @shortdesc change        - open selection menu
      @shortdesc <keyword>     - instantly set your keyword

    Your short description (sdesc) is how strangers see you before they
    learn your name.  It consists of a physical descriptor (derived from
    your height and build), a keyword (set here), and a distinguishing
    feature (auto-derived from what you're wielding or wearing).

    Example sdesc: "a lanky man in a Black Trenchcoat"
                         ^^^
                      keyword

    Available keywords depend on your character's gender.
    """

    key = "@shortdesc"
    aliases = ["shortdesc"]
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        args = self.args.strip().lower()

        if not args or args == "change":
            self._show_menu(caller)
            return

        # Instant-set mode
        self._set_keyword(caller, args)

    def _set_keyword(self, caller, keyword):
        """Validate and set a keyword directly."""
        from world.identity import (
            get_all_keywords,
            is_valid_keyword,
            log_custom_keyword,
            validate_custom_keyword,
        )

        gender = caller.gender

        # Approved-list keyword for this gender — accept immediately.
        if is_valid_keyword(keyword, gender):
            self._apply_keyword(caller, keyword)
            return

        # Gender-restricted approved keyword — reject with clear message.
        if keyword in get_all_keywords():
            caller.msg(
                f"|r'{keyword}' is not available for your character.|n\n"
                f"Use |w@shortdesc|n to see the full list."
            )
            return

        # Not on any approved list — validate as a custom keyword.
        valid, reason = validate_custom_keyword(keyword)
        if not valid:
            caller.msg(f"|r'{keyword}' is not a valid keyword.|n {reason}")
            return

        # Accept the custom keyword, log it to the catalog.
        account = caller.account if caller.account else None
        log_custom_keyword(keyword, caller.key, account=account)
        self._apply_keyword(caller, keyword)

    def _apply_keyword(self, caller, keyword):
        """Set the keyword on the caller and show confirmation."""
        old_keyword = caller.sdesc_keyword
        caller.sdesc_keyword = keyword

        sdesc = caller.get_sdesc()
        if old_keyword:
            caller.msg(
                f"Changed keyword from |w{old_keyword}|n to |w{keyword}|n.\n"
                f"You now appear as: |c{sdesc}|n"
            )
        else:
            caller.msg(
                f"Set keyword to |w{keyword}|n.\n"
                f"You now appear as: |c{sdesc}|n"
            )

    def _show_menu(self, caller):
        """Open the EvMenu keyword selection interface."""
        from evennia.utils.evmenu import EvMenu
        from world.identity import get_valid_keywords
        from world.grammar import DEFAULT_SDESC_KEYWORDS

        gender = caller.gender
        valid_keywords = sorted(get_valid_keywords(gender))
        current = caller.sdesc_keyword
        sdesc = caller.get_sdesc()

        # Store data for the menu node
        caller.ndb._shortdesc_keywords = valid_keywords
        caller.ndb._shortdesc_gender = gender

        EvMenu(
            caller,
            {"node_keyword_list": _node_keyword_list},
            startnode="node_keyword_list",
            cmd_on_exit=_shortdesc_exit,
        )


def _shortdesc_exit(caller, menu):
    """Clean up ndb data when the menu closes."""
    if hasattr(caller.ndb, "_shortdesc_keywords"):
        del caller.ndb._shortdesc_keywords
    if hasattr(caller.ndb, "_shortdesc_gender"):
        del caller.ndb._shortdesc_gender


def _node_keyword_list(caller, raw_string, **kwargs):
    """EvMenu node: display keyword list and accept selection."""
    from world.identity import get_valid_keywords
    from world.grammar import DEFAULT_SDESC_KEYWORDS

    gender = getattr(caller.ndb, "_shortdesc_gender", caller.gender)
    keywords = getattr(caller.ndb, "_shortdesc_keywords", None)
    if keywords is None:
        keywords = sorted(get_valid_keywords(gender))
        caller.ndb._shortdesc_keywords = keywords

    current = caller.sdesc_keyword
    default_kw = DEFAULT_SDESC_KEYWORDS.get(gender, "person")
    display_current = current if current else f"{default_kw} (default)"
    sdesc = caller.get_sdesc()

    # Build numbered list in columns
    text = f"\n|c=== Short Description Keyword ===|n\n"
    text += f"\n  Current keyword: |w{display_current}|n"
    text += f"  |xYou appear as: |c{sdesc}|n|x\n"
    text += f"\n|yAvailable keywords for your character:|n\n"

    # Render in 3 columns
    col_width = 26
    cols = 3
    rows = (len(keywords) + cols - 1) // cols
    for row in range(rows):
        line = "  "
        for col in range(cols):
            idx = col * rows + row
            if idx < len(keywords):
                kw = keywords[idx]
                num = f"{idx + 1}"
                marker = "|g*|n" if kw == current else " "
                entry = f"|w{num:>3}|n{marker}{kw}"
                # Pad to column width (accounting for color codes)
                padding = col_width - len(f"{num:>3} {kw}")
                line += entry + " " * max(padding, 1)
        text += line.rstrip() + "\n"

    text += (
        f"\n|wEnter a number (1-{len(keywords)}) or keyword name to select."
        f"\nYou can also use |y@shortdesc <word>|w to set a custom keyword."
        f"\nType |yquit|w to exit.|n"
    )

    options = ({"key": "_default", "goto": _process_keyword_choice},)
    return text, options


def _process_keyword_choice(caller, raw_string, **kwargs):
    """Goto-callable: process numbered or text keyword input."""
    choice = raw_string.strip().lower()
    keywords = getattr(caller.ndb, "_shortdesc_keywords", [])

    if not choice:
        return None  # Re-display

    # Try as a number
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(keywords):
            keyword = keywords[idx]
            return _apply_keyword(caller, keyword)
        else:
            caller.msg(f"|rInvalid number. Enter 1-{len(keywords)}.|n")
            return None  # Re-display
    except ValueError:
        pass

    # Try as a keyword name
    if choice in {kw.lower() for kw in keywords}:
        # Find the actual-case keyword
        keyword = next(kw for kw in keywords if kw.lower() == choice)
        return _apply_keyword(caller, keyword)

    caller.msg(f"|r'{raw_string.strip()}' is not a valid keyword or number.|n")
    return None  # Re-display


def _apply_keyword(caller, keyword):
    """Set the keyword and exit the menu."""
    old = caller.sdesc_keyword
    caller.sdesc_keyword = keyword
    sdesc = caller.get_sdesc()

    if old and old != keyword:
        caller.msg(
            f"\nChanged keyword from |w{old}|n to |w{keyword}|n."
            f"\nYou now appear as: |c{sdesc}|n"
        )
    elif old == keyword:
        caller.msg(f"\nKeyword is already |w{keyword}|n.")
    else:
        caller.msg(
            f"\nSet keyword to |w{keyword}|n."
            f"\nYou now appear as: |c{sdesc}|n"
        )
    return None  # Exit menu after setting


class CmdRemember(Command):
    """
    Remember someone you can see by a name of your choosing.

    Usage:
      remember <target> as <name>
      remember me as <persona name>

    When you encounter someone for the first time, you see their short
    description (e.g. "a lanky man in a Black Trenchcoat").  Use this
    command to remember them by a name — any name you choose.  From then
    on you'll see that name instead of their sdesc.

    You can remember people by false or partial names.  Other characters
    won't know what name you've chosen.

    The |wremember me as <name>|n form saves your *current* presentation
    overrides (height, build, keyword) as a named persona that you can
    restore later via |wappear <name>|n.  See also |wpersonas|n and
    |wpersona <name>|n.

    To change an existing name, simply remember them again.
    To clear a remembered name, use the |wforget|n command.

    Examples:
      remember man as Jorge
      remember woman as Sketchy Lady
      remember 2nd man as Big J
      remember me as Hooded Wanderer
    """

    key = "remember"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        args = self.args.strip()

        if not args or " as " not in args:
            caller.msg("Usage: remember <target> as <name>")
            return

        # Split on first " as " to allow names with spaces
        parts = args.split(" as ", 1)
        target_str = parts[0].strip()
        name = parts[1].strip()

        if not target_str:
            caller.msg("Who do you want to remember?")
            return
        if not name:
            caller.msg("What name do you want to remember them by?")
            return

        # "remember me as <name>" branch — save a persona snapshot.
        if target_str.lower() == "me":
            self._remember_self_as_persona(caller, name)
            return

        # Find the target
        target = caller.search(target_str)
        if not target:
            return  # caller.search already sends error messages

        # Must be a character (not an item/exit)
        from typeclasses.characters import Character
        if not isinstance(target, Character):
            caller.msg("You can only remember characters by name.")
            return

        # Can't remember yourself by another name
        if target is caller:
            caller.msg("You already know your own name.")
            return

        # Target must have a derivable Apparent UID (requires a real
        # sleeve_uid — pre-chargen shells return None).
        from world.identity import get_apparent_uid

        apparent_uid = get_apparent_uid(target)
        if apparent_uid is None:
            caller.msg("You can't remember that character.")
            return

        # Cross-namespace uniqueness: a remembered name for someone else
        # must not collide with one of our own persona names or a valid
        # keyword (which would shadow `appear <keyword>`).
        taken, reason = _name_is_taken(
            caller, name, allow_assigned_uid=apparent_uid
        )
        if taken:
            caller.msg(reason)
            return

        # Apply the assignment
        self._remember_target(caller, target, apparent_uid, name)

    def _remember_self_as_persona(self, caller, name):
        """Save the caller's current overrides as a named persona."""
        taken, reason = _name_is_taken(caller, name)
        if taken:
            caller.msg(reason)
            return

        personas = caller.db.personas
        if personas is None:
            personas = {}

        entry = _build_persona_entry(caller, name)
        personas[name] = entry
        caller.db.personas = personas

        # Echo a summary so the player can see what got captured.
        summary = _persona_summary_line(entry)
        caller.msg(
            f"Saved persona |w{name}|n: {summary}\n"
            f"Restore later with |wappear {name}|n."
        )

    def _remember_target(self, caller, target, apparent_uid, name):
        """Store a name assignment in the caller's recognition memory.

        The recognition entry is keyed on the target's current
        Apparent UID, NOT on real ``sleeve_uid``.  A character under
        a different disguise produces a different Apparent UID and
        gets its own recognition entry.
        """
        from world.identity import _recognition_now_iso

        memory = caller.recognition_memory
        if memory is None:
            memory = {}

        old_entry = memory.get(apparent_uid, {})
        old_name = old_entry.get("assigned_name", "")

        # Build/update the recognition entry
        now = _recognition_now_iso()
        location_name = caller.location.key if caller.location else "unknown"
        real_sleeve_uid = getattr(target, "sleeve_uid", None)

        if apparent_uid in memory:
            entry = memory[apparent_uid]
            entry["assigned_name"] = name
            entry["last_seen"] = now
            entry["times_seen"] = entry.get("times_seen", 0) + 1
            entry["location_last_seen"] = location_name
            if location_name not in entry.get("locations_seen", []):
                entry.setdefault("locations_seen", []).append(location_name)
            entry["sdesc_at_last_encounter"] = target.get_sdesc()
            # Re-encountering this UID clears any stale lost-contact flag.
            entry["lost_contact"] = False
            # Lazy backfill: schema gained `real_sleeve_uid` for reverse
            # lookup; pre-schema entries don't have it.  Set when missing,
            # leave alone when present (sleeve_uid never changes for a
            # given underlying character).
            if entry.get("real_sleeve_uid") is None and real_sleeve_uid:
                entry["real_sleeve_uid"] = real_sleeve_uid
        else:
            entry = {
                "assigned_name": name,
                "first_seen": now,
                "last_seen": now,
                "times_seen": 1,
                "location_first_seen": location_name,
                "location_last_seen": location_name,
                "locations_seen": [location_name],
                "sdesc_at_first_encounter": target.get_sdesc(),
                "sdesc_at_last_encounter": target.get_sdesc(),
                "notes": "",
                "tags": [],
                "confidence": 1.0,
                "relationship_valence": "neutral",
                "lost_contact": False,
                "recent_interactions": [],
                "real_sleeve_uid": real_sleeve_uid,
            }
            # Auto-link this fresh entry to any *other* presentation of
            # the same underlying sleeve the caller has already
            # remembered.  This closes the pierce-then-remember loop
            # promised in spec §Disguise Piercing: if the looker
            # pierced a disguise and then `remember`s the pierced name,
            # the new entry chains back to the bare-face entry so
            # `recall` / `memory` render the aka-line correctly.
            #
            # First match (insertion order) wins, mirroring
            # `attempt_display_pierce`.  No-op when no prior
            # presentation exists, when the sleeve is unknown, or when
            # an unmasking hook has already populated `linked_to`.
            if real_sleeve_uid and entry.get("linked_to") is None:
                from world.identity import find_entries_by_real_sleeve_uid

                for other_uid, _other_entry in (
                    find_entries_by_real_sleeve_uid(caller, real_sleeve_uid)
                ):
                    if other_uid != apparent_uid:
                        entry["linked_to"] = other_uid
                        break

        memory[apparent_uid] = entry
        caller.recognition_memory = memory

        # Provide feedback using the newly assigned name
        if old_name and old_name != name:
            caller.msg(
                f"You now know {target.get_display_name(caller)} "
                f"(previously '{old_name}') as |w{name}|n."
            )
        else:
            # After setting, get_display_name should return the new name
            caller.msg(
                f"You will now recognize "
                f"{target.get_sdesc()} as |w{name}|n."
            )

    def _clear_assignment(self, caller, target, apparent_uid):
        """Remove a name assignment from recognition memory.

        Retained for backward-compatible internal use; player-facing clear
        is now the |wforget|n command (:class:`CmdForget`).
        """
        memory = caller.recognition_memory
        if not memory or apparent_uid not in memory:
            caller.msg("You don't have a name assigned to them.")
            return

        old_name = memory[apparent_uid].get("assigned_name", "")
        # Clear the assigned name but keep the memory entry
        memory[apparent_uid]["assigned_name"] = ""
        caller.recognition_memory = memory

        sdesc = target.get_sdesc()
        if old_name:
            caller.msg(
                f"Cleared name '{old_name}'. "
                f"They will now appear as their description."
            )
        else:
            caller.msg("No name was assigned to clear.")


# ===================================================================
# forget / recall / memory — observer-memory verb cluster
# ===================================================================


def _find_remembered_uid_by_name(caller, name):
    """Look up an Apparent UID in caller's recognition_memory by assigned_name.

    Case-insensitive match against ``assigned_name``.  Returns the first
    matching ``(apparent_uid, entry)`` tuple, or ``(None, None)`` if no
    match.  The returned UID is the recognition_memory dict key (an
    Apparent UID derived from the target's identity signature at the
    time the entry was written), not the target's real ``sleeve_uid``.
    """
    memory = caller.recognition_memory
    if not memory:
        return None, None
    needle = name.lower()
    for uid, entry in memory.items():
        assigned = (entry.get("assigned_name") or "").lower()
        if assigned and assigned == needle:
            return uid, entry
    return None, None


def _format_relative_time(iso_timestamp):
    """Return a human-friendly 'X ago' string for an ISO timestamp.

    The stored ISO string is interpreted as **naive UTC** (the
    convention enforced by :func:`world.identity._recognition_now_iso`);
    the delta is computed against the matching naive-UTC "now" so the
    result is independent of the server's local timezone.

    Falls back to the raw timestamp if parsing fails.
    """
    from evennia.utils.utils import time_format
    from world.identity import (
        _parse_recognition_timestamp,
        _recognition_utcnow,
    )

    if not iso_timestamp:
        return "unknown"
    try:
        then = _parse_recognition_timestamp(iso_timestamp)
        delta = (_recognition_utcnow() - then).total_seconds()
        if delta < 1:
            return "just now"
        return f"{time_format(int(delta), 4)} ago"
    except (ValueError, TypeError):
        return iso_timestamp


def _refresh_lost_contact(caller):
    """Flip ``lost_contact`` on stale recognition entries before rendering.

    Lazy, render-time pattern (see
    :func:`world.identity.mark_lost_contact_entries`).  Gathers the
    Apparent UIDs currently visible in the caller's room so the helper
    can skip entries whose subjects are right in front of the caller.

    Safe to call when ``caller`` has no location or no recognition
    memory; the underlying helper short-circuits cleanly.
    """
    from world.identity import get_apparent_uid, mark_lost_contact_entries
    from typeclasses.characters import Character

    location = getattr(caller, "location", None)
    current_uids = set()
    if location is not None:
        for obj in location.contents:
            if isinstance(obj, Character) and obj is not caller:
                uid = get_apparent_uid(obj)
                if uid is not None:
                    current_uids.add(uid)
    mark_lost_contact_entries(caller, current_uids)


class CmdForget(Command):
    """
    Forget the name you remembered for someone, or delete a saved persona.

    Usage:
      forget <target>
      forget <persona name>

    Clears the name you assigned to someone.  They will appear as their
    description again until you remember them by a new name.

    You can forget someone whether or not they're currently present —
    pass either their current description or the name you remembered
    them by.

    If the argument matches one of your saved personas (see |wpersonas|n)
    instead of a remembered person, the persona is deleted.  If that
    persona is currently adopted, all your presentation overrides are
    cleared at the same time (equivalent to |wstop appearing|n).

    Examples:
      forget man
      forget Jorge
      forget Hooded Wanderer
    """

    key = "forget"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        args = self.args.strip()

        if not args:
            caller.msg("Forget who?")
            return

        from typeclasses.characters import Character

        # Try visible-target resolution first (silent on failure so we can
        # fall back to remembered-name lookup).
        target = caller.search(args, quiet=True)
        if target:
            # caller.search with quiet=True returns a list
            if isinstance(target, list):
                target = target[0] if target else None

        if target and isinstance(target, Character):
            from world.identity import get_apparent_uid

            apparent_uid = get_apparent_uid(target)
            if apparent_uid is None:
                caller.msg("You can't forget that character.")
                return
            self._forget_visible(caller, target, apparent_uid)
            return

        # Fall back to remembered-name lookup
        apparent_uid, entry = _find_remembered_uid_by_name(caller, args)
        if apparent_uid is not None:
            self._forget_remembered(caller, apparent_uid, entry)
            return

        # Final fallback: persona lookup.
        if self._forget_persona(caller, args):
            return

        caller.msg("You don't remember anyone — or any persona — by that name.")

    def _forget_persona(self, caller, name):
        """Delete a saved persona by name.  Returns True on success."""
        personas = caller.db.personas
        if not personas:
            return False

        # Case-insensitive lookup; preserve stored casing for the message.
        match_key = None
        needle = name.lower()
        for key in personas:
            if key.lower() == needle:
                match_key = key
                break
        if match_key is None:
            return False

        was_active = (caller.db.active_persona == match_key)
        del personas[match_key]
        caller.db.personas = personas

        if was_active:
            _clear_all_overrides(caller)
            caller.msg(
                f"Forgot persona |w{match_key}|n. "
                f"It was active — your presentation overrides have been cleared."
            )
        else:
            caller.msg(f"Forgot persona |w{match_key}|n.")
        return True

    def _forget_visible(self, caller, target, apparent_uid):
        """Forget a target who is currently present.

        Keyed on the target's *Apparent UID* (derived from their current
        identity signature), so forgetting under a disguise only forgets
        the disguised persona — the real-form entry is untouched.

        Also invalidates every cached pierce verdict for any
        presentation of the target's sleeve (issue #210): without this,
        a cached ``True`` in ``observer.db.disguise_pierce_cache``
        survives forget and the rendering pipeline keeps surfacing the
        forgotten name through any disguise.
        """
        memory = caller.recognition_memory
        if not memory or apparent_uid not in memory:
            caller.msg("You don't have a name remembered for them.")
            return

        old_name = memory[apparent_uid].get("assigned_name", "")
        if not old_name:
            caller.msg("You don't have a name remembered for them.")
            return

        memory[apparent_uid]["assigned_name"] = ""
        caller.recognition_memory = memory

        # Drop stale pierce-cache verdicts for this sleeve so the next
        # look re-evaluates against the now-nameless memory.  Prefer
        # the entry's stored ``real_sleeve_uid`` (covers all backfilled
        # presentations); fall back to the target's live sleeve_uid
        # for pre-schema entries.
        from world.identity import invalidate_pierce_cache_for_sleeve

        entry_sleeve = memory[apparent_uid].get("real_sleeve_uid")
        live_sleeve = getattr(target, "sleeve_uid", None)
        sleeve_uid = entry_sleeve or live_sleeve
        if sleeve_uid:
            invalidate_pierce_cache_for_sleeve(caller, sleeve_uid)

        caller.msg(
            f"You forget the name '{old_name}'. "
            f"They will now appear as their description."
        )

    def _forget_remembered(self, caller, apparent_uid, entry):
        """Forget someone by remembered name; they may not be present.

        ``apparent_uid`` is the recognition_memory dict key (an Apparent
        UID derived from the target's signature at recording time).

        Also invalidates pierce-cache entries for the sleeve (issue
        #210); pre-schema entries (no ``real_sleeve_uid``) skip
        invalidation since there is no other handle on the sleeve when
        the target is absent.  The pierce candidate filter in
        :func:`world.identity.attempt_display_pierce` still guards
        rendering correctness in that degraded case — it requires a
        truthy ``assigned_name``, which the forget just cleared.
        """
        old_name = entry.get("assigned_name", "")
        sdesc = entry.get("sdesc_at_last_encounter", "someone")
        location = entry.get("location_last_seen", "somewhere")
        last_seen = entry.get("last_seen", "")
        when = _format_relative_time(last_seen)

        memory = caller.recognition_memory
        memory[apparent_uid]["assigned_name"] = ""
        caller.recognition_memory = memory

        from world.identity import invalidate_pierce_cache_for_sleeve

        sleeve_uid = entry.get("real_sleeve_uid")
        if sleeve_uid:
            invalidate_pierce_cache_for_sleeve(caller, sleeve_uid)

        caller.msg(
            f"You forget the name '{old_name}'. "
            f"(Last seen: {sdesc} in {location}, {when}.)"
        )


class CmdRecall(Command):
    """
    Recall what you remember about someone.

    Usage:
      recall <target>

    Shows the name you remembered them by, what they looked like when
    you first met them, where, when, and how many times you've seen
    them.

    The target may be someone currently present (by description or by
    remembered name) or someone you've remembered before but isn't
    here now (by remembered name).

    To see everyone you've remembered, use the |wmemory|n command.

    Examples:
      recall man
      recall Jorge
    """

    key = "recall"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        args = self.args.strip()

        if not args:
            caller.msg("Recall who? (Try |wmemory|n to see everyone you remember.)")
            return

        from typeclasses.characters import Character

        # Lazy lost-contact evaluation: flip the flag on stale entries
        # before any rendering so the (lost contact) annotation is
        # current at display time.  Re-meets clear the flag separately
        # via the recognition writer; this helper only flips True.
        _refresh_lost_contact(caller)

        # Try visible-target resolution first
        target = caller.search(args, quiet=True)
        if target:
            if isinstance(target, list):
                target = target[0] if target else None

        entry = None

        if target and isinstance(target, Character):
            from world.identity import get_apparent_uid

            apparent_uid = get_apparent_uid(target)
            if apparent_uid is None:
                caller.msg("You can't recall anything about that character.")
                return
            memory = caller.recognition_memory or {}
            entry = memory.get(apparent_uid)
        else:
            # Fall back to remembered-name lookup
            apparent_uid, entry = _find_remembered_uid_by_name(caller, args)

        if entry is None:
            caller.msg("You don't recognize that person.")
            return

        self._render_entry(caller, entry, apparent_uid)

    def _render_entry(self, caller, entry, apparent_uid=None):
        """Format and send a recognition_memory entry to the caller.

        Adds a ``(lost contact)`` annotation when the stored entry's
        ``lost_contact`` flag is True (set by the periodic prune scan;
        cleared on re-encounter).  Old entries that predate the flag
        default to False.

        When ``apparent_uid`` is provided and the entry is part of a
        linked-presentation chain (built up by the unmasking-moments
        broadcast), an ``Also known as: ...`` line lists the assigned
        names of every other named presentation in the chain — letting
        the player see at a glance which of their remembered names refer
        to the same underlying sleeve.
        """
        assigned_name = entry.get("assigned_name", "")
        sdesc_first = entry.get("sdesc_at_first_encounter", "(unknown)")
        location_first = entry.get("location_first_seen", "(unknown)")
        first_seen = entry.get("first_seen", "")
        times_seen = entry.get("times_seen", 0)
        lost_contact = entry.get("lost_contact", False)

        when = _format_relative_time(first_seen)

        if assigned_name:
            header = f"You remember them as: |w{assigned_name}|n"
            if lost_contact:
                header += " |y(lost contact)|n"
        else:
            header = (
                "You've encountered them before but don't have a "
                "name for them."
            )
            if lost_contact:
                header += " |y(lost contact)|n"

        lines = [
            header,
            f"First seen: {sdesc_first}",
            f"Location: {location_first}",
            f"When: {when} (seen {times_seen} time{'s' if times_seen != 1 else ''})",
        ]

        if apparent_uid is not None:
            from world.identity import get_linked_aliases

            memory = caller.recognition_memory or {}
            aliases = get_linked_aliases(memory, apparent_uid)
            if aliases:
                lines.append(
                    f"Also known as: |w{'|n, |w'.join(aliases)}|n"
                )

        caller.msg("\n".join(lines))


class CmdMemory(Command):
    """
    List everyone you remember by name.

    Usage:
      memory

    Shows a table of every person you've remembered, sorted by who
    you've seen most recently.  People you've forgotten (cleared with
    |wforget|n) are not listed, even though their record is preserved.

    Use |wrecall <name>|n to inspect a specific entry.
    """

    key = "memory"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        args = self.args.strip()

        if args:
            caller.msg("Usage: memory  (no arguments)")
            return

        # Lazy lost-contact evaluation — see CmdRecall.func.
        _refresh_lost_contact(caller)

        memory = caller.recognition_memory or {}

        # Filter to entries with a non-blank assigned_name
        named = [
            (uid, entry)
            for uid, entry in memory.items()
            if (entry.get("assigned_name") or "").strip()
        ]

        if not named:
            caller.msg("You don't remember anyone yet.")
            return

        # Sort by last_seen descending (recency).  Missing values sort last.
        named.sort(
            key=lambda pair: pair[1].get("last_seen") or "",
            reverse=True,
        )

        from evennia.utils.evtable import EvTable
        from world.identity import get_linked_aliases

        table = EvTable(
            "|wName|n",
            "|wLast seen as|n",
            "|wWhere|n",
            "|wWhen|n",
            border="cells",
        )
        for uid, entry in named:
            name_cell = entry.get("assigned_name", "")
            if entry.get("lost_contact", False):
                name_cell = f"{name_cell} |y(lost contact)|n"
            aliases = get_linked_aliases(memory, uid)
            if aliases:
                name_cell = f"{name_cell}\n|x(aka {', '.join(aliases)})|n"
            table.add_row(
                name_cell,
                entry.get("sdesc_at_last_encounter", "(unknown)"),
                entry.get("location_last_seen", "(unknown)"),
                _format_relative_time(entry.get("last_seen", "")),
            )

        caller.msg(str(table))


# ===================================================================
# appear / stop appearing / personas / persona — disguise surface
# ===================================================================
#
# Foundation cut for Phase 3 (Disguise System).  This layer ships the
# *command surface* and *persistent storage* for presentation overrides
# and saved personas only.  The signature engine, Apparent UID
# derivation, sdesc-render consumption, item flags, and lifecycle hooks
# all live in subsequent PRs — overrides set here are persisted but not
# yet rendered into the sdesc.  See ``specs/IDENTITY_RECOGNITION_SPEC.md``
# for the full Disguise System design.


# -- Persona / override helpers ---------------------------------------


def _override_axes(caller):
    """Return the caller's three override axes as a dict."""
    return {
        "height_override": caller.db.height_override,
        "build_override": caller.db.build_override,
        "keyword_override": caller.db.keyword_override,
    }


def _has_any_override(caller):
    """True if the caller has at least one active override axis."""
    axes = _override_axes(caller)
    return any(value is not None for value in axes.values())


def _clear_all_overrides(caller):
    """Wipe all override axes and the active-persona pointer."""
    from world.identity import apply_signature_change

    with apply_signature_change(caller, source="stop_appearing"):
        caller.db.height_override = None
        caller.db.build_override = None
        caller.db.keyword_override = None
        caller.db.active_persona = None


def _build_persona_entry(caller, name):
    """Snapshot the caller's current overrides into a persona dict.

    The shape matches the persona schema documented in the disguise
    spec.  ``essential_item_types`` captures the currently-equipped
    essential disguise items (via :func:`get_essential_item_type_ids`)
    so adoption can advise the player when the saved composition no
    longer matches what's worn.  ``notes`` remains reserved for a
    future player-annotation feature.
    """
    import time

    from world.identity import get_essential_item_type_ids

    location_name = caller.location.key if caller.location else "unknown"
    return {
        "name": name,
        "height_override": caller.db.height_override,
        "build_override": caller.db.build_override,
        "keyword_override": caller.db.keyword_override,
        "saved_at": time.time(),
        "saved_in": location_name,
        "essential_item_types": list(get_essential_item_type_ids(caller)),
        "notes": "",
    }


def _persona_summary_line(entry):
    """Single-line summary of a persona's three axes for list/save echoes."""
    parts = []
    height = entry.get("height_override")
    build = entry.get("build_override")
    keyword = entry.get("keyword_override")
    if height:
        parts.append(f"height={height}")
    if build:
        parts.append(f"build={build}")
    if keyword:
        parts.append(f"keyword={keyword}")
    if not parts:
        return "(no overrides)"
    return ", ".join(parts)


def _format_relative_unixtime(unix_ts):
    """Human-friendly 'X ago' string for a unix timestamp."""
    import time
    from evennia.utils.utils import time_format

    if not unix_ts:
        return "unknown"
    try:
        delta = time.time() - float(unix_ts)
        if delta < 1:
            return "just now"
        return f"{time_format(int(delta), 4)} ago"
    except (ValueError, TypeError):
        return "unknown"


def _name_is_taken(caller, name, allow_assigned_uid=None):
    """Check whether *name* collides with any reserved identity namespace.

    A persona name (or a remembered-as name) must be unique against:

    * the keyword catalog (so ``appear <name>`` is unambiguous),
    * the caller's recognition_memory ``assigned_name`` values
      (so ``forget <name>`` is unambiguous), and
    * the caller's existing persona names.

    Args:
        caller: The character whose namespaces are being checked.
        name: The candidate name (case-insensitive).
        allow_assigned_uid: When checking a remembered-as assignment,
            the existing recognition entry for *that* Apparent UID does
            not count as a collision (re-naming the same persona).

    Returns:
        Tuple ``(taken: bool, reason: str)``.  *reason* is a
        player-facing message; empty string when ``taken`` is False.
    """
    from world.identity import get_all_keywords

    needle = name.strip().lower()
    if not needle:
        return True, "Name cannot be blank."

    if needle in {kw.lower() for kw in get_all_keywords()}:
        return True, (
            f"|r'{name}' is a reserved keyword.|n  Pick a different name "
            f"so |wappear {name}|n stays unambiguous."
        )

    memory = caller.recognition_memory or {}
    for uid, entry in memory.items():
        assigned = (entry.get("assigned_name") or "").strip().lower()
        if assigned and assigned == needle and uid != allow_assigned_uid:
            return True, (
                f"|rYou already remember someone else as '{name}'.|n  "
                f"Pick a different name."
            )

    personas = caller.db.personas or {}
    for persona_name in personas:
        if persona_name.lower() == needle:
            return True, (
                f"|rYou already have a persona named '{persona_name}'.|n  "
                f"Forget it first or pick a different name."
            )

    return False, ""


def _nudge_axis(values, current, real, direction):
    """Return the next axis value one step from current toward direction.

    Args:
        values: Ordered tuple of valid values (e.g. ``HEIGHTS``).
        current: The current override value, or ``None`` to use *real*.
        real: The character's real (un-overridden) axis value.
        direction: ``+1`` (e.g. taller / fatter) or ``-1`` (shorter /
            thinner).

    Returns:
        The new axis value, or ``None`` if the nudge would step off
        either end of the scale.
    """
    base = current if current is not None else real
    if base not in values:
        return None
    idx = values.index(base) + direction
    if idx < 0 or idx >= len(values):
        return None
    return values[idx]


def _describe_appearance(caller):
    """Render the bare ``appear`` status display for the caller."""
    real_height = caller.height
    real_build = caller.build
    real_keyword = caller.sdesc_keyword

    h_over = caller.db.height_override
    b_over = caller.db.build_override
    k_over = caller.db.keyword_override
    active = caller.db.active_persona

    def _row(label, real, override):
        if override is None:
            return f"  {label:<8} {real or '(unset)'}"
        return f"  {label:<8} |w{override}|n  |x(real: {real or 'unset'})|n"

    lines = ["|cYour current appearance:|n"]
    lines.append(_row("Height:", real_height, h_over))
    lines.append(_row("Build:", real_build, b_over))
    lines.append(_row("Keyword:", real_keyword, k_over))

    if not _has_any_override(caller):
        lines.append("")
        lines.append("|xNo presentation overrides active.|n")
    if active:
        lines.append("")
        lines.append(f"|y(Persona: {active})|n")
    return "\n".join(lines)


def _render_persona(entry):
    """Multi-line render of a single persona entry for ``persona <name>``."""
    name = entry.get("name", "(unnamed)")
    when = _format_relative_unixtime(entry.get("saved_at"))
    where = entry.get("saved_in") or "unknown"

    lines = [f"|cPersona: |w{name}|n"]

    h = entry.get("height_override")
    b = entry.get("build_override")
    k = entry.get("keyword_override")
    lines.append(f"  Height:   {h if h is not None else '|x(unchanged)|n'}")
    lines.append(f"  Build:    {b if b is not None else '|x(unchanged)|n'}")
    lines.append(f"  Keyword:  {k if k is not None else '|x(unchanged)|n'}")
    lines.append(f"  Saved:    {when} in {where}")
    return "\n".join(lines)


# -- Commands ---------------------------------------------------------


class CmdAppear(Command):
    """
    Adopt a presentation override, restore a saved persona, or check status.

    Usage:
      appear                          - show current overrides and persona
      appear taller | shorter         - nudge perceived height one step
      appear thinner | fatter         - nudge perceived build one step
      appear <keyword>                - present as the given keyword
      appear <persona name>           - restore a saved persona

    The |wappear|n command is your interface to *presentation overrides* —
    per-axis changes to how others perceive you.  Each override stays
    in effect until you change it, replace it, or use |wstop appearing|n.

    Height and build nudges step one notch on a fixed scale.  If you're
    already at the extreme of the scale in that direction, the command
    refuses (some descriptors are simply unreachable for your real
    sleeve — that's a tell).

    A keyword override accepts any keyword from the full catalog
    (gender restrictions don't apply to disguise).  Use |w@shortdesc|n
    to introduce new keywords to the catalog.

    A persona is a previously saved snapshot of all three override axes
    (see |wremember me as <name>|n).  Adopting a persona overwrites all
    three axes — including clearing axes the persona doesn't set.

    Manually changing an axis after adopting a persona dissociates from
    that persona; the persona itself is left intact.

    Examples:
      appear taller
      appear thinner
      appear droog
      appear Hooded Wanderer
    """

    key = "appear"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        args = self.args.strip()

        if not args:
            caller.msg(_describe_appearance(caller))
            return

        # Resolution order: persona name > axis nudge > keyword.
        personas = caller.db.personas or {}
        for persona_name in personas:
            if persona_name.lower() == args.lower():
                self._adopt_persona(caller, persona_name, personas[persona_name])
                return

        lower = args.lower()
        if lower in ("taller", "shorter"):
            self._nudge_height(caller, +1 if lower == "taller" else -1)
            return
        if lower in ("thinner", "fatter"):
            self._nudge_build(caller, +1 if lower == "fatter" else -1)
            return

        # Keyword override.
        self._set_keyword_override(caller, args)

    # -- axis handlers ---------------------------------------------------

    def _nudge_height(self, caller, direction):
        from world.identity import HEIGHTS, apply_signature_change

        new = _nudge_axis(
            HEIGHTS, caller.db.height_override, caller.height, direction
        )
        if new is None:
            word = "taller" if direction > 0 else "shorter"
            caller.msg(
                f"You can't appear any {word} than that — your real frame "
                f"won't sell it."
            )
            return
        self._maybe_break_persona(caller)
        with apply_signature_change(caller, source="override:height"):
            caller.db.height_override = new
        caller.msg(f"You now carry yourself as |w{new}|n.")

    def _nudge_build(self, caller, direction):
        from world.identity import BUILDS, apply_signature_change

        new = _nudge_axis(
            BUILDS, caller.db.build_override, caller.build, direction
        )
        if new is None:
            word = "bulkier" if direction > 0 else "leaner"
            caller.msg(
                f"You can't appear any {word} than that — your real frame "
                f"won't sell it."
            )
            return
        self._maybe_break_persona(caller)
        with apply_signature_change(caller, source="override:build"):
            caller.db.build_override = new
        caller.msg(f"You now carry yourself as |w{new}|n.")

    def _set_keyword_override(self, caller, raw_keyword):
        from world.identity import apply_signature_change, get_all_keywords

        keyword = raw_keyword.lower()
        if keyword not in {kw.lower() for kw in get_all_keywords()}:
            caller.msg(
                f"|r'{raw_keyword}' isn't a recognized keyword or persona.|n  "
                f"Use |w@shortdesc|n to introduce new keywords to the "
                f"catalog first."
            )
            return
        self._maybe_break_persona(caller)
        with apply_signature_change(caller, source="override:keyword"):
            caller.db.keyword_override = keyword
        caller.msg(f"You now present yourself as a |w{keyword}|n.")

    # -- persona adoption ------------------------------------------------

    def _adopt_persona(self, caller, name, entry):
        """Clean swap: overwrite all three axes from the persona snapshot.

        If the persona's saved ``essential_item_types`` diverges from
        the caller's currently-equipped essential disguise items, emit
        a yellow advisory naming missing and extra type IDs before the
        override swap.  Adoption is not refused — the player can choose
        to proceed and accept the resulting Apparent UID divergence.
        """
        from world.identity import (
            apply_signature_change,
            get_essential_item_type_ids,
        )

        saved = tuple(entry.get("essential_item_types") or ())
        current = get_essential_item_type_ids(caller)
        missing = tuple(t for t in saved if t not in current)
        extra = tuple(t for t in current if t not in saved)
        if missing or extra:
            advisory_lines = [
                f"|y(Heads up: '{name}' was saved with a different set of "
                f"essential disguise items than you have on now.)|n"
            ]
            if missing:
                advisory_lines.append(
                    f"|y  Missing: {', '.join(missing)}|n"
                )
            if extra:
                advisory_lines.append(
                    f"|y  Extra:   {', '.join(extra)}|n"
                )
            advisory_lines.append(
                "|y  Your Apparent UID will not match the saved persona "
                "exactly.|n"
            )
            caller.msg("\n".join(advisory_lines))

        with apply_signature_change(caller, source=f"persona:{name}"):
            caller.db.height_override = entry.get("height_override")
            caller.db.build_override = entry.get("build_override")
            caller.db.keyword_override = entry.get("keyword_override")
            caller.db.active_persona = name

        summary = _persona_summary_line(entry)
        caller.msg(
            f"You adopt the persona |w{name}|n.\n  {summary}"
        )

    def _maybe_break_persona(self, caller):
        """Manual axis change dissociates from any active persona."""
        active = caller.db.active_persona
        if active:
            caller.db.active_persona = None
            caller.msg(
                f"|x(Manual change — no longer presenting as persona "
                f"'{active}'.)|n"
            )


class CmdStopAppearing(Command):
    """
    Drop all presentation overrides and return to your real appearance.

    Usage:
      stop appearing

    Clears every active override (height, build, keyword) and any
    adopted persona pointer.  You will be perceived as your real sleeve
    again, modulo any disguise items you have equipped (those are
    handled separately by the items themselves).

    To delete a saved persona instead of just stepping out of it, use
    |wforget <persona name>|n.
    """

    key = "stop appearing"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller

        if not _has_any_override(caller) and not caller.db.active_persona:
            caller.msg("You aren't presenting as anything but yourself.")
            return

        _clear_all_overrides(caller)
        caller.msg(
            "You drop the act and present yourself as you really are."
        )


class CmdPersonas(Command):
    """
    List the personas you've saved.

    Usage:
      personas

    Shows every persona you've stored via |wremember me as <name>|n,
    most-recently-saved first.  An asterisk marks the persona you are
    currently adopting (if any).

    Use |wpersona <name>|n to inspect a single persona, |wappear <name>|n
    to adopt one, and |wforget <name>|n to delete one.
    """

    key = "personas"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        if self.args.strip():
            caller.msg("Usage: personas  (no arguments)")
            return

        personas = caller.db.personas or {}
        if not personas:
            caller.msg(
                "You haven't saved any personas yet.  Use "
                "|wremember me as <name>|n to save your current "
                "presentation overrides as a persona."
            )
            return

        # Recency sort, newest first.  Missing timestamps sort last.
        ordered = sorted(
            personas.items(),
            key=lambda pair: pair[1].get("saved_at") or 0,
            reverse=True,
        )

        active = caller.db.active_persona

        from evennia.utils.evtable import EvTable

        table = EvTable(
            "|wPersona|n",
            "|wOverrides|n",
            "|wSaved|n",
            border="cells",
        )
        for name, entry in ordered:
            marker = "|g*|n " if name == active else "  "
            table.add_row(
                f"{marker}{name}",
                _persona_summary_line(entry),
                _format_relative_unixtime(entry.get("saved_at")),
            )

        caller.msg(str(table))


class CmdPersona(Command):
    """
    Inspect a single saved persona.

    Usage:
      persona <name>

    Shows the height/build/keyword overrides captured in the persona
    and where/when it was saved.

    Use |wpersonas|n to list every persona you've saved.
    """

    key = "persona"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        args = self.args.strip()

        if not args:
            caller.msg("Usage: persona <name>")
            return

        personas = caller.db.personas or {}
        match = None
        for name, entry in personas.items():
            if name.lower() == args.lower():
                match = (name, entry)
                break

        if match is None:
            caller.msg(
                f"You don't have a persona named '{args}'.  "
                f"Try |wpersonas|n to see what you've saved."
            )
            return

        caller.msg(_render_persona(match[1]))

