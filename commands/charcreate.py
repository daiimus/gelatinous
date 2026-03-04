"""
Character Creation System for Gelatinous Monster

This module handles both first-time character creation and respawn/flash cloning
after death. It uses Evennia's EvMenu system for the interactive interface.

Flow:
1. First Character: Name input → Sex selection → GRIM distribution (300 points)
2. Respawn: Choose from 3 random templates OR flash clone previous character
"""

from evennia import create_object
from evennia.utils.evmenu import EvMenu
from django.conf import settings
import random
import time
import re


# =============================================================================
# CUSTOM EV MENU CLASS
# =============================================================================

class CharCreateEvMenu(EvMenu):
    """
    Custom EvMenu that suppresses automatic option display.
    
    The character creation menu includes option keys in the node text itself,
    so we don't want EvMenu to auto-display them again.
    """
    
    def options_formatter(self, optionlist):
        """
        Override to suppress automatic option display.
        
        Returns:
            str: Empty string to prevent option display.
        """
        return ""


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def generate_random_template():
    """
    Generate a random character template with 300 GRIM points distributed.
    
    Returns:
        dict: Template with 'grit', 'resonance', 'intellect', 'motorics', 
              'first_name', 'last_name'
    """
    from world.namebank import FIRST_NAMES_MALE, FIRST_NAMES_FEMALE, LAST_NAMES
    
    # Randomly pick gender for name selection and character sex
    sex_choices = ['male', 'female', 'ambiguous']
    sex = random.choice(sex_choices)
    
    # Use gendered names for male/female, random choice for ambiguous
    if sex == 'ambiguous':
        use_male = random.choice([True, False])
    else:
        use_male = (sex == 'male')
    
    first_name = random.choice(FIRST_NAMES_MALE if use_male else FIRST_NAMES_FEMALE)
    last_name = random.choice(LAST_NAMES)
    
    # Generate GRIM distribution totaling 300 points
    # Use weighted random distribution to create varied but viable templates
    points_left = 300
    stats = []
    
    # Assign 3 stats randomly, then give remainder to 4th
    for i in range(3):
        # Each stat gets between 25-100 points (avoid extremes)
        min_points = max(25, points_left - (150 * (3 - i)))  # Ensure enough left
        max_points = min(100, points_left - (25 * (3 - i)))  # Ensure minimum for others
        
        if max_points > min_points:
            points = random.randint(min_points, max_points)
        else:
            points = min_points
            
        stats.append(points)
        points_left -= points
    
    # Give remainder to 4th stat (clamped to max 150)
    stats.append(min(150, points_left))
    
    # Shuffle so variance isn't predictable by position
    random.shuffle(stats)
    
    return {
        'first_name': first_name,
        'last_name': last_name,
        'name': f"{first_name} {last_name}",  # Full name for display
        'sex': sex,
        'grit': stats[0],
        'resonance': stats[1],
        'intellect': stats[2],
        'motorics': stats[3]
    }


def build_name_from_death_count(base_name, death_count):
    """
    Build character name with Roman numeral based on death_count.
    
    The death_count is the source of truth - it's incremented at death (at_death()).
    - death_count = 1: No Roman numeral (original character)
    - death_count = 2: Roman numeral II (first death/clone)
    - death_count = 3: Roman numeral III (second death/clone)
    - etc.
    
    Examples:
        ("Brock", 1) → "Brock"
        ("Brock", 2) → "Brock II"
        ("Brock", 3) → "Brock III"
        ("Marcus", 10) → "Marcus X"
    
    Args:
        base_name (str): Character base name (may include old Roman numeral to strip)
        death_count (int): Current death_count value
        
    Returns:
        str: Name with appropriate Roman numeral (or none if death_count=1)
    """
    # Strip any existing Roman numeral from base_name
    # Only strip if there's whitespace before the Roman numeral to avoid
    # stripping letters from names like "Drivel" (ends with "L")
    pattern = r'^(.+?)\s+([IVXLCDM]+)$'
    match = re.match(pattern, base_name.strip(), re.IGNORECASE)
    if match:
        base_name = match.group(1).strip()
    
    # Original character (death_count=1) has no Roman numeral
    if death_count == 1:
        return base_name
    
    # death_count 2+ gets Roman numeral (2=II, 3=III, etc.)
    roman = int_to_roman(death_count)
    return f"{base_name} {roman}"


def int_to_roman(num):
    """Convert integer to Roman numeral."""
    values = [
        (1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'),
        (100, 'C'), (90, 'XC'), (50, 'L'), (40, 'XL'),
        (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')
    ]
    
    result = ''
    for value, numeral in values:
        count = num // value
        if count:
            result += numeral * count
            num -= value * count
    return result


def validate_name(name):
    """
    Validate a character name.
    
    Rules:
    - 2-30 characters
    - Letters, spaces, hyphens, apostrophes only
    - Cannot start/end with space or punctuation
    - No profanity (basic filter)
    
    Args:
        name (str): Name to validate
        
    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    name = name.strip()
    
    if len(name) < 2:
        return (False, "Name must be at least 2 characters long.")
    
    if len(name) > 30:
        return (False, "Name must be 30 characters or less.")
    
    # Check allowed characters
    if not re.match(r"^[a-zA-Z][a-zA-Z\s\-']*[a-zA-Z]$", name):
        return (False, "Name can only contain letters, spaces, hyphens, and apostrophes.")
    
    # Basic profanity filter (expandable)
    profanity_list = ['fuck', 'shit', 'damn', 'bitch', 'ass', 'cunt', 'dick', 'cock', 'pussy']
    name_lower = name.lower()
    for word in profanity_list:
        if word in name_lower:
            return (False, "That name is not allowed.")
    
    # Check uniqueness
    from typeclasses.characters import Character
    if Character.objects.filter(db_key__iexact=name).exists():
        return (False, "That name is already taken.")
    
    return (True, None)


def validate_grim_distribution(grit, resonance, intellect, motorics):
    """
    Validate GRIM stat distribution.
    
    Rules:
    - All stats between 1 and 150
    - Total equals 300
    
    Args:
        grit, resonance, intellect, motorics (int): Stat values
        
    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    stats = [grit, resonance, intellect, motorics]
    
    # Check range
    for stat in stats:
        if stat < 1:
            return (False, "All stats must be at least 1.")
        if stat > 150:
            return (False, "No stat can exceed 150.")
    
    # Check total
    total = sum(stats)
    if total != 300:
        return (False, f"Stats must total 300 (current total: {total}).")
    
    return (True, None)


def create_character_from_template(account, template, sex="ambiguous"):
    """
    Create a character from a template (for respawn).
    
    Args:
        account: Account object
        template (dict): Template with name and GRIM stats
        sex (str): Biological sex
        
    Returns:
        Character: New character object
    """
    from typeclasses.characters import Character
    
    # Get spawn location
    start_location = get_start_location()
    
    # Create full name
    full_name = f"{template['first_name']} {template['last_name']}"
    
    # Use Evennia's proper character creation method
    char, errors = account.create_character(
        key=full_name,
        location=start_location,
        home=start_location,
        typeclass="typeclasses.characters.Character"
    )
    
    if errors:
        # Handle creation errors
        raise Exception(f"Character creation failed: {errors}")
    
    # Set GRIM stats
    char.grit = template['grit']
    char.resonance = template['resonance']
    char.intellect = template['intellect']
    char.motorics = template['motorics']
    
    # Set sex
    char.sex = sex
    
    # Debug: Verify sex was set correctly
    from evennia.comms.models import ChannelDB
    try:
        splattercast = ChannelDB.objects.get_channel("Splattercast")
        splattercast.msg(f"CHARCREATE_SEX_SET: {char.key} sex set to '{sex}', current value: '{char.sex}', gender property: '{char.gender}'")
    except:
        pass
    
    # Set defaults
    # death_count starts at 1 via AttributeProperty in Character class
    char.db.archived = False
    
    return char


def create_flash_clone(account, old_character):
    """
    Create a flash clone from a dead character.
    Inherits: GRIM stats, longdesc, desc, sex, skintone
    Name: Built from base name + Roman numeral based on old_character's death_count
    
    Note: death_count is incremented on the OLD character at death (at_death()).
    The Roman numeral in the name reflects this death_count value.
    The NEW clone starts with default death_count=1 from AttributeProperty.
    
    Args:
        account: Account object
        old_character: Dead character to clone from
        
    Returns:
        Character: New cloned character
    """
    from typeclasses.characters import Character
    
    # Get spawn location
    start_location = get_start_location()
    
    # Get old character's death_count (already incremented at death)
    # Use AttributeProperty directly to access the correct categorized attribute
    old_death_count = old_character.death_count
    if old_death_count is None:
        old_death_count = 1  # Default from AttributeProperty
    
    # Build name using death_count as Roman numeral source
    new_name = build_name_from_death_count(old_character.key, old_death_count)
    
    # NOTE: We do NOT remove old_character from account.characters here.
    # check_available_slots() excludes archived characters from the count,
    # so the slot check passes with the archived char still in the list.
    # Keeping it ensures archived characters appear on the manage sleeves page.
    
    # Use Evennia's proper character creation method
    char, errors = account.create_character(
        key=new_name,
        location=start_location,
        home=start_location,
        typeclass="typeclasses.characters.Character"
    )
    
    if errors:
        # Handle creation errors
        raise Exception(f"Flash clone creation failed: {errors}")
    
    # INHERIT: GRIM stats (with fallback defaults)
    char.grit = old_character.grit if old_character.grit is not None else 1
    char.resonance = old_character.resonance if old_character.resonance is not None else 1
    char.intellect = old_character.intellect if old_character.intellect is not None else 1
    char.motorics = old_character.motorics if old_character.motorics is not None else 1
    
    # INHERIT: Appearance
    char.db.desc = old_character.db.desc
    if old_character.longdesc:
        char.longdesc = dict(old_character.longdesc)  # Copy dictionary
    
    # INHERIT: Biology
    char.sex = old_character.sex
    if old_character.db.skintone is not None:
        char.db.skintone = old_character.db.skintone
    
    # Debug: Verify sex was inherited correctly
    from evennia.comms.models import ChannelDB
    try:
        splattercast = ChannelDB.objects.get_channel("Splattercast")
        splattercast.msg(f"FLASH_CLONE_SEX_INHERIT: {char.key} inherited sex '{old_character.sex}' from {old_character.key}, current value: '{char.sex}', gender property: '{char.gender}'")
    except:
        pass
    
    # INHERIT: death_count from old character
    # The old character's death_count was already incremented at death (at_death())
    # The new clone inherits this value to continue the progression
    # Use AttributeProperty directly, not db.death_count
    char.death_count = old_death_count
    
    # Link to previous incarnation
    char.db.previous_clone_dbref = old_character.dbref
    
    # Stack ID (consciousness identifier)
    old_stack_id = old_character.db.stack_id
    if old_stack_id is not None:
        char.db.stack_id = old_stack_id
    else:
        # Create new stack ID if old char didn't have one
        import uuid
        char.db.stack_id = str(uuid.uuid4())
    
    # Reset state
    char.db.archived = False
    char.db.current_sleeve_birth = time.time()
    
    return char


def get_start_location():
    """
    Get the staging location where characters are initially created.
    
    Characters are created in Limbo (#2) as a safe staging area,
    then teleported to the spawn location on creation completion.
    
    Returns:
        Room: Limbo (#2) or None as last resort
    """
    from evennia import search_object
    
    try:
        return search_object("#2")[0]
    except (IndexError, AttributeError):
        return None


def get_spawn_location():
    """
    Get the in-game spawn location where characters appear after creation.
    
    Uses START_LOCATION from settings (e.g. "#1989" for Thawn-Harrison
    Cryogenics). Falls back to Limbo (#2) if not configured or not found.
    
    Returns:
        Room: Spawn location object
    """
    from evennia.objects.models import ObjectDB
    
    start_location_setting = getattr(settings, 'START_LOCATION', None)
    if start_location_setting:
        spawn = ObjectDB.objects.get_id(start_location_setting)
        if spawn:
            return spawn
    
    # Fallback to Limbo (#2)
    from evennia import search_object
    try:
        return search_object("#2")[0]
    except (IndexError, AttributeError):
        return None


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def _charcreate_exit_callback(caller, menu):
    """
    Called when the character creation menu exits.
    Only disconnects if character creation was NOT completed.
    """
    # Check if they have any ACTIVE (non-archived) characters
    active_characters = [char for char in caller.characters if not char.db.archived]
    
    if active_characters:
        # They completed creation - just close menu, don't disconnect
        return
    
    # No active characters - they exited without completing
    # Disconnect them so they restart character creation on reconnect
    sessions = caller.sessions.all()
    if not sessions:
        # Already disconnected (e.g. connection dropped during menu)
        return
    sessions[0].sessionhandler.disconnect(sessions[0], reason="|ySleeve decantation incomplete. Please reconnect to try again.|n")


def start_character_creation(account, is_respawn=False, old_character=None):
    """
    Start the character creation process.
    
    Args:
        account: Account object
        is_respawn (bool): True if respawning after death, False if first character
        old_character: If respawn, the dead character object
    """
    # Store context in account NDB for menu access
    account.ndb.charcreate_is_respawn = is_respawn
    account.ndb.charcreate_old_character = old_character
    account.ndb.charcreate_data = {}
    
    # Start appropriate menu
    if is_respawn:
        # Respawn menu: show templates + flash clone option
        CharCreateEvMenu(
            account,
            "commands.charcreate",
            startnode="respawn_welcome",
            cmdset_mergetype="Replace",
            cmd_on_exit=_charcreate_exit_callback
        )
    else:
        # First character menu: custom creation
        CharCreateEvMenu(
            account,
            "commands.charcreate",
            startnode="first_char_welcome",
            cmdset_mergetype="Replace",
            cmd_on_exit=_charcreate_exit_callback
        )


# =============================================================================
# RESPAWN MENU NODES
# =============================================================================

def _respawn_process_choice(caller, raw_string, **kwargs):
    """Process user's respawn menu choice and route to appropriate node."""
    choice = raw_string.strip()
    old_char = caller.ndb.charcreate_old_character
    
    if choice == "1":
        return "respawn_confirm_template", {"template_idx": 0}
    elif choice == "2":
        return "respawn_confirm_template", {"template_idx": 1}
    elif choice == "3":
        return "respawn_confirm_template", {"template_idx": 2}
    elif choice == "4" and old_char:
        return "respawn_flash_clone"
    else:
        caller.msg("|rInvalid choice. Please enter a number from the available options.|n")
        # Return None to re-display current node
        return None


def respawn_welcome(caller, raw_string, **kwargs):
    """Respawn menu entry point - combined welcome + options screen."""
    
    # Generate 3 random templates (only on first view)
    if not caller.ndb.charcreate_data.get('templates'):
        templates = [generate_random_template() for _ in range(3)]
        caller.ndb.charcreate_data['templates'] = templates
    else:
        templates = caller.ndb.charcreate_data['templates']
    
    text = """
|r╔════════════════════════════════════════════════════════════════╗
║  CONSCIOUSNESS BACKUP PROTOCOL INITIATED                       ║
║  VECTOR INDUSTRIES - MEDICAL RECONSTRUCTION DIVISION           ║
╚════════════════════════════════════════════════════════════════╝|n

|yYour previous sleeve has been terminated.|n
|yMemory upload successful. Stack integrity: |g98.7%|n

|wPreparing new sleeve for consciousness transfer...|n

|w╔════════════════════════════════════════════════════════════════╗
║  AVAILABLE SLEEVES                                             ║
╚════════════════════════════════════════════════════════════════╝|n

Select a consciousness vessel:

"""
    
    # Display templates
    for i, template in enumerate(templates, 1):
        text += f"\n|w[{i}]|n |c{template['first_name']} {template['last_name']}|n\n"
        text += f"    |gGrit:|n {template['grit']:3d}  "
        text += f"|yResonance:|n {template['resonance']:3d}  "
        text += f"|bIntellect:|n {template['intellect']:3d}  "
        text += f"|mMotorics:|n {template['motorics']:3d}\n"
    
    # Flash clone option
    old_char = caller.ndb.charcreate_old_character
    if old_char:
        text += f"\n|w[4]|n |rFLASH CLONE|n - |c{old_char.key}|n (preserve current identity)\n"
        text += f"    |gGrit:|n {old_char.grit:3d}  "
        text += f"|yResonance:|n {old_char.resonance:3d}  "
        text += f"|bIntellect:|n {old_char.intellect:3d}  "
        text += f"|mMotorics:|n {old_char.motorics:3d}\n"
        text += f"    |wInherits appearance, stats, and memories from previous incarnation|n\n"
    
    # Build prompt based on available options
    if old_char:
        text += "\n|wEnter choice [1-4]:|n"
    else:
        text += "\n|wEnter choice [1-3]:|n"
    
    # Use only _default to catch all input (prevents EvMenu from displaying option keys)
    # IMPORTANT: Must be a tuple, not a bare dict, or EvMenu will auto-generate numbered options
    # The goto points to a callable that processes the input and routes to the correct node
    options = ({"key": "_default", "goto": _respawn_process_choice},)
    
    return text, options


def respawn_confirm_template(caller, raw_string, template_idx=0, **kwargs):
    """Confirm template selection and choose sex."""
    
    templates = caller.ndb.charcreate_data.get('templates', [])
    if template_idx >= len(templates):
        return "respawn_welcome"
    
    template = templates[template_idx]
    caller.ndb.charcreate_data['selected_template'] = template
    
    text = f"""
|w╔════════════════════════════════════════════════════════════════╗
║  SLEEVE CONFIGURATION                                          ║
╚════════════════════════════════════════════════════════════════╝|n

Selected: |c{template['first_name']} {template['last_name']}|n

|gGrit:|n      {template['grit']:3d}
|yResonance:|n {template['resonance']:3d}
|bIntellect:|n {template['intellect']:3d}
|mMotorics:|n {template['motorics']:3d}

Select biological sex for this sleeve:

|w[1]|n Male
|w[2]|n Female
|w[3]|n Androgynous

|w[B]|n Back to template selection

|wEnter choice:|n """
    
    options = (
        {"key": "1",
         "goto": ("respawn_finalize_template", {"sex": "male"}),
         "auto_help": False,
         "auto_look": False},
        {"key": "2",
         "goto": ("respawn_finalize_template", {"sex": "female"}),
         "auto_help": False,
         "auto_look": False},
        {"key": "3",
         "goto": ("respawn_finalize_template", {"sex": "ambiguous"}),
         "auto_help": False,
         "auto_look": False},
        {"key": ("b", "back"),
         "goto": "respawn_welcome",
         "auto_help": False,
         "auto_look": False},
        {"key": "_default",
         "goto": ("respawn_confirm_template", {"template_idx": template_idx}),
         "auto_help": False,
         "auto_look": False},
    )
    
    return text, options


def respawn_finalize_template(caller, raw_string, **kwargs):
    """Create character from template and finalize respawn."""
    
    # Extract sex from kwargs (EvMenu passes goto dict params as kwargs)
    sex = kwargs.get('sex', 'ambiguous')
    
    template = caller.ndb.charcreate_data.get('selected_template')
    if not template:
        return "respawn_welcome"
    
    # Create character
    try:
        char = create_character_from_template(caller, template, sex)
        
        # Puppet the new character
        caller.puppet_object(caller.sessions.all()[0], char)
        
        # Teleport from Limbo staging area to spawn location
        spawn_location = get_spawn_location()
        if spawn_location and spawn_location != char.location:
            char.move_to(spawn_location, quiet=True)
        
        # Send welcome message
        char.msg("|g╔════════════════════════════════════════════════════════════════╗")
        char.msg("|g║  CONSCIOUSNESS TRANSFER COMPLETE                               ║")
        char.msg("|g╚════════════════════════════════════════════════════════════════╝|n")
        char.msg("")
        char.msg(f"|wWelcome back, |c{char.key}|w.|n")
        char.msg(f"|wClone Generation:|n |w1|n")
        char.msg("")
        char.msg("|yYou open your eyes in an unfamiliar body.|n")
        char.msg("|yThe memories feel... borrowed. But they're yours now.|n")
        char.msg("")
        
        # Clear last_character after successful respawn (matches web path behavior)
        caller.db.last_character = None
        
        # Clean up
        _cleanup_charcreate_ndb(caller)
        
        # Exit menu
        return None
        
    except Exception as e:
        # Error - show message and return to selection
        caller.msg(f"|rError creating character: {e}|n")
        from evennia.comms.models import ChannelDB
        try:
            splattercast = ChannelDB.objects.get_channel("Splattercast")
            splattercast.msg(f"CHARCREATE_ERROR: {e}")
        except:
            pass
        return "respawn_welcome"


def respawn_flash_clone(caller, raw_string, **kwargs):
    """Create flash clone and finalize respawn."""
    
    old_char = caller.ndb.charcreate_old_character
    if not old_char:
        caller.msg("|rError: No previous character found.|n")
        return "respawn_welcome"
    
    # Create flash clone
    try:
        char = create_flash_clone(caller, old_char)
        
        # Puppet the new character
        caller.puppet_object(caller.sessions.all()[0], char)
        
        # Teleport from Limbo staging area to spawn location
        spawn_location = get_spawn_location()
        if spawn_location and spawn_location != char.location:
            char.move_to(spawn_location, quiet=True)
        
        # Send welcome message
        # Use AttributeProperty to access the correct categorized attribute
        death_count = char.death_count
        char.msg("|r╔════════════════════════════════════════════════════════════════╗")
        char.msg("|r║  FLASH CLONE PROTOCOL COMPLETE                                 ║")
        char.msg("|r╚════════════════════════════════════════════════════════════════╝|n")
        char.msg("")
        char.msg(f"|wWelcome back, |c{char.key}|w.|n")
        char.msg(f"|wDeath Count:|n |w{death_count}|n")
        char.msg("")
        
        # Death count-specific flavor
        if death_count == 2:
            char.msg("|wThis is your first death. The sensation of resleeving is disorienting.|n")
            char.msg("|wYour old body's final moments echo in your mind like static on a dead channel.|n")
        elif death_count < 5:
            char.msg("|wThe memories of your previous body fade like analog videotape degradation.|n")
            char.msg("|wYou know you've done this before, but each time feels like the first.|n")
        elif death_count < 10:
            char.msg("|wYou've died enough times to know: this never gets easier.|n")
            char.msg("|wBut at least you're still you. Mostly.|n")
        else:
            char.msg("|rHow many times have you done this? The memories blur together like overexposed film.|n")
            char.msg("|rAre you still the person who first stepped into this world?|n")
        
        char.msg("")
        char.msg(f"|wPrevious cause of death:|n |r{old_char.db.death_cause or 'Unknown'}|n")
        char.msg("")
        
        # Clear last_character after successful respawn (matches web path behavior)
        caller.db.last_character = None
        
        # Clean up
        _cleanup_charcreate_ndb(caller)
        
        # Exit menu
        return None
        
    except Exception as e:
        # Error - show message and return to selection
        caller.msg(f"|rError creating flash clone: {e}|n")
        from evennia.comms.models import ChannelDB
        try:
            splattercast = ChannelDB.objects.get_channel("Splattercast")
            splattercast.msg(f"FLASH_CLONE_ERROR: {e}")
        except:
            pass
        return "respawn_welcome"


# =============================================================================
# FIRST CHARACTER MENU NODES
# =============================================================================

def first_char_welcome(caller, raw_string, **kwargs):
    """First character creation entry point."""
    
    text = """
|b╔════════════════════════════════════════════════════════════════╗
║  WELCOME TO THE GELATINOUS MONSTER                             ║
║  CHARACTER INITIALIZATION PROTOCOL                             ║
╚════════════════════════════════════════════════════════════════╝|n

|wBeginning consciousness upload sequence...|n

|wThe year is 198█. The broadcast never ends.|n
|wYour memories are... incomplete. But you're here now.|n

Press |w<Enter>|n to begin character creation.
"""
    
    options = (
        {"key": "_default",
         "goto": "first_char_name_first"},
    )
    
    return text, options


def first_char_name_first(caller, raw_string, **kwargs):
    """Get first name."""
    
    # If input provided, validate it
    if raw_string and raw_string.strip():
        name = raw_string.strip()
        
        # Validate format (not uniqueness yet - need full name)
        if len(name) < 2 or len(name) > 30:
            caller.msg(f"|rInvalid name: Name must be 2-30 characters.|n")
            # Return None to re-display current node
            return None
        
        if not re.match(r"^[a-zA-Z][a-zA-Z\-']*[a-zA-Z]$", name):
            caller.msg(f"|rInvalid name: Only letters, hyphens, and apostrophes allowed.|n")
            # Return None to re-display current node
            return None
        
        # Store first name and advance to next node
        caller.ndb.charcreate_data['first_name'] = name
        # Call next node directly and return its result
        return first_char_name_last(caller, "", **kwargs)
    
    # Display prompt (first time or after error)
    text = """
|w╔════════════════════════════════════════════════════════════════╗
║  IDENTITY VERIFICATION                                         ║
╚════════════════════════════════════════════════════════════════╝|n

|wWhat is your FIRST name?|n

(2-30 characters, letters only)

|w>|n """
    
    options = (
        {"key": "_default",
         "goto": "first_char_name_first"},
    )
    
    return text, options


def first_char_name_last(caller, raw_string, **kwargs):
    """Get last name."""
    
    first_name = caller.ndb.charcreate_data.get('first_name', '')
    
    # If input provided, validate it
    if raw_string and raw_string.strip():
        name = raw_string.strip()
        
        if len(name) < 2 or len(name) > 30:
            caller.msg(f"|rInvalid name: Name must be 2-30 characters.|n")
            # Return None to re-display current node
            return None
        
        if not re.match(r"^[a-zA-Z][a-zA-Z\-']*[a-zA-Z]$", name):
            caller.msg(f"|rInvalid name: Only letters, hyphens, and apostrophes allowed.|n")
            # Return None to re-display current node
            return None
        
        # Check full name uniqueness
        full_name = f"{first_name} {name}"
        is_valid, error = validate_name(full_name)
        if not is_valid:
            caller.msg(f"|r{error}|n")
            # Return None to re-display current node
            return None
        
        # Store last name and advance to next node
        caller.ndb.charcreate_data['last_name'] = name
        # Call next node directly and return its result
        return first_char_sex(caller, "", **kwargs)
    
    # Display prompt (first time or after error)
    text = f"""
|w╔════════════════════════════════════════════════════════════════╗
║  IDENTITY VERIFICATION                                         ║
╚════════════════════════════════════════════════════════════════╝|n

First name: |c{first_name}|n

|wWhat is your LAST name?|n

(2-30 characters, letters only)

|w>|n """
    
    options = (
        {"key": "_default",
         "goto": "first_char_name_last"},
    )
    
    return text, options


def first_char_sex(caller, raw_string, **kwargs):
    """Select biological sex."""
    
    first_name = caller.ndb.charcreate_data.get('first_name', '')
    last_name = caller.ndb.charcreate_data.get('last_name', '')
    
    text = f"""
|w╔════════════════════════════════════════════════════════════════╗
║  BIOLOGICAL CONFIGURATION                                      ║
╚════════════════════════════════════════════════════════════════╝|n

Name: |c{first_name} {last_name}|n

Select biological sex:

|w[1]|n Male
|w[2]|n Female
|w[3]|n Androgynous

|wEnter choice:|n """
    
    options = (
        {"key": "1",
         "goto": ("first_char_grim", {"sex": "male"}),
         "auto_help": False,
         "auto_look": False},
        {"key": "2",
         "goto": ("first_char_grim", {"sex": "female"}),
         "auto_help": False,
         "auto_look": False},
        {"key": "3",
         "goto": ("first_char_grim", {"sex": "ambiguous"}),
         "auto_help": False,
         "auto_look": False},
        {"key": "_default",
         "goto": "first_char_sex",
         "auto_help": False,
         "auto_look": False},
    )
    
    return text, options


def first_char_grim(caller, raw_string, **kwargs):
    """Distribute GRIM points."""
    
    # Store sex if explicitly provided in kwargs (from EvMenu goto dict)
    # Only update if 'sex' key exists in kwargs to avoid overwriting with default
    if 'sex' in kwargs:
        caller.ndb.charcreate_data['sex'] = kwargs['sex']
    
    first_name = caller.ndb.charcreate_data.get('first_name', '')
    last_name = caller.ndb.charcreate_data.get('last_name', '')
    sex = caller.ndb.charcreate_data.get('sex', 'ambiguous')
    
    # Get current GRIM values (or defaults)
    grit = caller.ndb.charcreate_data.get('grit', 75)
    resonance = caller.ndb.charcreate_data.get('resonance', 75)
    intellect = caller.ndb.charcreate_data.get('intellect', 75)
    motorics = caller.ndb.charcreate_data.get('motorics', 75)
    
    total = grit + resonance + intellect + motorics
    remaining = 300 - total
    
    # Process input ONLY if it's a valid command (not just transitioning from previous node)
    # Valid commands: stat assignments, reset, done
    # Invalid to process: single numbers like "1", "2", "3" from sex selection
    if raw_string and raw_string.strip():
        args = raw_string.strip().lower().split()
        
        if not args:
            # Re-display current node (ignore empty command)
            return first_char_grim(caller, "", **kwargs)
        
        command = args[0]
        
        # Only process if it's a known command (not leftover input from previous node)
        # Commands: grit, resonance, intellect, motorics, reset, done
        # Ignore: single digits (from sex selection) or other garbage
        valid_commands = ['grit', 'g', 'resonance', 'r', 'res', 'intellect', 'i', 'int', 
                         'motorics', 'm', 'mot', 'reset', 'done', 'd', 'finish', 'finalize']
        
        if command in valid_commands:
            # Reset command
            if command in ["reset", "r"]:
                caller.ndb.charcreate_data['grit'] = 75
                caller.ndb.charcreate_data['resonance'] = 75
                caller.ndb.charcreate_data['intellect'] = 75
                caller.ndb.charcreate_data['motorics'] = 75
                # Re-display the menu with reset values by calling self recursively
                return first_char_grim(caller, "", **kwargs)
            
            # Done command
            if command in ["done", "d", "finish", "finalize"]:
                # Validate distribution
                is_valid, error = validate_grim_distribution(grit, resonance, intellect, motorics)
                if not is_valid:
                    caller.msg(f"|r{error}|n")
                    # Re-display current node with error message
                    return first_char_grim(caller, "", **kwargs)
                # Call next node directly and return its result
                return first_char_confirm(caller, "", **kwargs)
            
            # Stat assignment commands
            if len(args) < 2:
                caller.msg("|rUsage: <stat> <value>  (e.g., 'grit 100')|n")
                # Re-display current node
                return first_char_grim(caller, "", **kwargs)
            
            try:
                value = int(args[1])
            except ValueError:
                caller.msg("|rValue must be a number.|n")
                # Re-display current node
                return first_char_grim(caller, "", **kwargs)
            
            if value < 1 or value > 150:
                caller.msg("|rValue must be between 1 and 150.|n")
                # Re-display current node
                return first_char_grim(caller, "", **kwargs)
            
            # Set the stat
            if command in ["grit", "g"]:
                caller.ndb.charcreate_data['grit'] = value
            elif command in ["resonance", "r", "res"]:
                caller.ndb.charcreate_data['resonance'] = value
            elif command in ["intellect", "i", "int"]:
                caller.ndb.charcreate_data['intellect'] = value
            elif command in ["motorics", "m", "mot"]:
                caller.ndb.charcreate_data['motorics'] = value
            
            # Re-display the menu with updated values by calling self recursively
            return first_char_grim(caller, "", **kwargs)
        # If not a valid command, just ignore and display the menu
    
    # Display the GRIM distribution screen
    text = f"""
|w╔════════════════════════════════════════════════════════════════╗
║  G.R.I.M. ATTRIBUTE DISTRIBUTION                               ║
╚════════════════════════════════════════════════════════════════╝|n

Name: |c{first_name} {last_name}|n
Sex: |c{sex.capitalize()}|n

Distribute |w300 points|n across your attributes (min 1, max 150 per stat):

|gGrit:|n      {grit:3d}  (Physical resilience, endurance, toughness)
|yResonance:|n {resonance:3d}  (Social awareness, empathy, influence)
|bIntellect:|n {intellect:3d}  (Mental acuity, reasoning, knowledge)
|mMotorics:|n  {motorics:3d}  (Physical coordination, reflexes, dexterity)

|wTotal:|n {total}/300  {'REMAINING: ' + str(remaining) if remaining >= 0 else '|rOVER BY:|n ' + str(abs(remaining))}

Commands:
  |wgrit <value>|n     - Set Grit
  |wresonance <value>|n - Set Resonance
  |wintellect <value>|n - Set Intellect
  |wmotorics <value>|n  - Set Motorics
  |wreset|n             - Reset to defaults (75 each)
  |wdone|n              - Finalize character (when total = 300)

|w>|n """
    
    options = (
        {"key": "_default",
         "goto": "first_char_grim"},
    )
    
    return text, options


def first_char_confirm(caller, raw_string, **kwargs):
    """Final confirmation and character creation."""
    
    first_name = caller.ndb.charcreate_data.get('first_name', '')
    last_name = caller.ndb.charcreate_data.get('last_name', '')
    sex = caller.ndb.charcreate_data.get('sex', 'ambiguous')
    grit = caller.ndb.charcreate_data.get('grit', 75)
    resonance = caller.ndb.charcreate_data.get('resonance', 75)
    intellect = caller.ndb.charcreate_data.get('intellect', 75)
    motorics = caller.ndb.charcreate_data.get('motorics', 75)
    
    text = f"""
|w╔════════════════════════════════════════════════════════════════╗
║  FINAL CONFIRMATION                                            ║
╚════════════════════════════════════════════════════════════════╝|n

|wName:|n |c{first_name} {last_name}|n
|wSex:|n |c{sex.capitalize()}|n

|wG.R.I.M. Attributes:|n
  |gGrit:|n      {grit:3d}
  |yResonance:|n {resonance:3d}
  |bIntellect:|n {intellect:3d}
  |mMotorics:|n {motorics:3d}

|wTotal:|n 300/300

|yOnce created, your name cannot be changed.|n
|yStats can be modified through gameplay.|n

Create this character?

|w[Y]|n Yes, finalize character
|w[N]|n No, go back to GRIM distribution

|w>|n """
    
    options = (
        {"key": ("y", "yes"),
         "goto": "first_char_finalize",
         "auto_help": False,
         "auto_look": False},
        {"key": ("n", "no"),
         "goto": "first_char_grim",
         "auto_help": False,
         "auto_look": False},
        {"key": "_default",
         "goto": "first_char_confirm",
         "auto_help": False,
         "auto_look": False},
    )
    
    return text, options


def first_char_finalize(caller, raw_string, **kwargs):
    """Create the character and enter game."""
    
    from typeclasses.characters import Character
    
    # Get data
    first_name = caller.ndb.charcreate_data.get('first_name', '')
    last_name = caller.ndb.charcreate_data.get('last_name', '')
    full_name = f"{first_name} {last_name}"
    sex = caller.ndb.charcreate_data.get('sex', 'ambiguous')
    grit = caller.ndb.charcreate_data.get('grit', 75)
    resonance = caller.ndb.charcreate_data.get('resonance', 75)
    intellect = caller.ndb.charcreate_data.get('intellect', 75)
    motorics = caller.ndb.charcreate_data.get('motorics', 75)
    
    # Get spawn location
    start_location = get_start_location()
    
    # Create character
    try:
        # Use Evennia's proper character creation method
        char, errors = caller.create_character(
            key=full_name,
            location=start_location,
            home=start_location,
            typeclass="typeclasses.characters.Character"
        )
        
        if errors:
            # Handle creation errors
            raise Exception(f"Character creation failed: {errors}")
        
        # Set GRIM stats
        char.grit = grit
        char.resonance = resonance
        char.intellect = intellect
        char.motorics = motorics
        
        # Set sex
        char.sex = sex
        
        # Set defaults
        # death_count starts at 1 via AttributeProperty in Character class
        char.db.archived = False
        
        # Generate unique Stack ID
        import uuid
        char.db.stack_id = str(uuid.uuid4())
        char.db.original_creation = time.time()
        char.db.current_sleeve_birth = time.time()
        
        # Puppet the character
        caller.puppet_object(caller.sessions.all()[0], char)
        
        # Teleport from Limbo staging area to spawn location
        spawn_location = get_spawn_location()
        if spawn_location and spawn_location != char.location:
            char.move_to(spawn_location, quiet=True)
        
        # Send welcome message
        char.msg("|g╔════════════════════════════════════════════════════════════════╗")
        char.msg("|g║  CONSCIOUSNESS UPLOAD COMPLETE                                 ║")
        char.msg("|g╚════════════════════════════════════════════════════════════════╝|n")
        char.msg("")
        char.msg(f"|wWelcome to Gelatinous Monster, |c{char.key}|w.|n")
        char.msg("")
        char.msg("|wThe static clears. You open your eyes.|n")
        char.msg("|wThe year is 198█. The broadcast continues.|n")
        char.msg("|wYou are here. You are real. You are... something.|n")
        char.msg("")
        char.msg("|yType |wlook|y to examine your surroundings.|n")
        char.msg("|yType |whelp|y for a list of commands.|n")
        char.msg("")
        
        # Clean up
        _cleanup_charcreate_ndb(caller)
        
        # Exit menu
        return None
        
    except Exception as e:
        # Error - show message and return to confirmation
        caller.msg(f"|rError creating character: {e}|n")
        from evennia.comms.models import ChannelDB
        try:
            splattercast = ChannelDB.objects.get_channel("Splattercast")
            splattercast.msg(f"CHARCREATE_ERROR: {e}")
        except:
            pass
        return "first_char_confirm"


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def _cleanup_charcreate_ndb(caller):
    """Clean up character creation NDB data."""
    if hasattr(caller.ndb, 'charcreate_is_respawn'):
        delattr(caller.ndb, 'charcreate_is_respawn')
    if hasattr(caller.ndb, 'charcreate_old_character'):
        delattr(caller.ndb, 'charcreate_old_character')
    if hasattr(caller.ndb, 'charcreate_data'):
        delattr(caller.ndb, 'charcreate_data')
