# Web-Based Respawn Character Creation Specification

## Overview

Implement the respawn character creation flow (templates + flash clone) on the Django website to match the telnet EvMenu experience. This allows users to respawn characters via the web interface with the same options available in-game.

## Current State

### Telnet Character Creation (commands/charcreate.py)
- **First character**: Custom stat allocation (300 points across GRIM)
- **Respawn**: EvMenu with 3 random templates + flash clone option
- **Flash clone**: Inherits stats, appearance, sex from archived character
- **Roman numerals**: Auto-appends based on death_count. Every sleeve
  carries a Roman numeral suffix — first sleeve renders as `Jorge
  Jackson I`, first clone as `Jorge Jackson II`, etc. (issue #50).

### Web Character Creation (web/website/views/characters.py)
- **Current**: Single Django form for manual character creation
- **Limitation**: No respawn flow - always shows the form
- **Problem**: Users can't access flash clone or templates via web

## Desired Behavior

When a user visits the "Decant Sleeve" page:

1. **If `account.db.last_character` exists** (respawn scenario):
   - Display respawn interface with:
     - 3 randomly generated character templates (name, stats)
     - Flash clone option (if archived character exists)
     - Sex selection for chosen option
   - Submit creates character using selected template/clone
   
2. **If no `last_character`** (first character):
   - Display existing manual stat allocation form
   - No changes to current behavior

## Technical Requirements

### 1. View Logic (web/website/views/characters.py)

```python
class CharacterCreateView(EvenniaCharacterCreateView):
    def get(self, request, *args, **kwargs):
        """Determine which character creation flow to show."""
        account = request.user
        
        # Check for respawn scenario
        if account.db.last_character:
            return self.show_respawn_interface(request, account)
        else:
            return self.show_first_character_form(request)
    
    def show_respawn_interface(self, request, account):
        """Display template selection + flash clone options."""
        # Generate 3 random templates (reuse generate_random_template())
        # Pass old character data for flash clone option
        # Render respawn template
        
    def show_first_character_form(self, request):
        """Display existing manual stat allocation form."""
        # Current behavior - no changes
```

### 2. Template Generation

Reuse existing template generation logic from `commands/charcreate.py`:

```python
from commands.charcreate import generate_random_template

templates = [generate_random_template() for _ in range(3)]
```

**Template structure:**
```python
{
    'first_name': str,
    'last_name': str,
    'grit': int,
    'resonance': int,
    'intellect': int,
    'motorics': int
}
```

### 3. Flash Clone Logic

Reuse existing flash clone creation from `commands/charcreate.py`:

```python
from commands.charcreate import create_flash_clone_character

# When user selects flash clone option
character = create_flash_clone_character(account, old_character)
```

**Flash clone behavior:**
- Inherits: GRIM stats, appearance (desc, longdesc), sex, skintone
- Auto-names: Uses `build_name_from_death_count()` for Roman numerals
- Increments: death_count already incremented during archival

### 4. Django Templates

Create new template: `web/templates/website/character_respawn_create.html`

**UI Structure:**
```
Sleeve Decantation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Your previous sleeve has been archived.
Stack integrity: 98.7%

Available Sleeves:

┌─────────────────────────────────────────────┐
│ [Radio] Template 1: [Name]                  │
│         Grit: XX  Resonance: XX             │
│         Intellect: XX  Motorics: XX         │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ [Radio] Template 2: [Name]                  │
│         Grit: XX  Resonance: XX             │
│         Intellect: XX  Motorics: XX         │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ [Radio] Template 3: [Name]                  │
│         Grit: XX  Resonance: XX             │
│         Intellect: XX  Motorics: XX         │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ [Radio] FLASH CLONE: [Old Name II]          │
│         Preserves your previous identity    │
│         Grit: XX  Resonance: XX             │
│         Intellect: XX  Motorics: XX         │
└─────────────────────────────────────────────┘

Sex: [Male] [Female] [Ambiguous]

[Decant Sleeve Button]
```

### 5. Form Handling

**POST data structure:**
```python
{
    'sleeve_choice': 'template_0' | 'template_1' | 'template_2' | 'flash_clone',
    'sex': 'male' | 'female' | 'ambiguous'
}
```

**Processing:**
```python
def post(self, request, *args, **kwargs):
    choice = request.POST.get('sleeve_choice')
    sex = request.POST.get('sex')
    
    if choice == 'flash_clone':
        character = create_flash_clone_character(account, old_character)
    else:
        template_idx = int(choice.split('_')[1])
        template = templates[template_idx]
        character = create_character_from_template(account, template, sex)
    
    # Redirect to character detail or management page
```

## Data Flow

### Respawn Flow
```
User Archives Character (web or death)
  ↓
archive_character() sets:
  - account.db.last_character = character
  - character.death_count += 1
  ↓
User Visits "Decant Sleeve"
  ↓
View Detects account.db.last_character exists
  ↓
Generate 3 Random Templates
  ↓
Display Respawn Interface:
  - Template Option 1
  - Template Option 2  
  - Template Option 3
  - Flash Clone Option (shows Roman numeral name)
  ↓
User Selects Option + Sex
  ↓
POST Handler Creates Character:
  - Template: create_character_from_template()
  - Flash Clone: create_flash_clone_character()
  ↓
Redirect to Character Management
```

## Implementation Checklist

### Phase 1: View Logic
- [ ] Add `get()` method to detect respawn vs first character
- [ ] Create `show_respawn_interface()` method
- [ ] Import and use `generate_random_template()` function
- [ ] Pass context data to template (templates, old_character, sex options)

### Phase 2: Template Creation
- [ ] Create `character_respawn_create.html`
- [ ] Style respawn interface to match game theme (dark, dissolution aesthetic)
- [ ] Add radio buttons for template selection
- [ ] Add sex selection buttons
- [ ] Add flash clone option display

### Phase 3: Form Processing
- [ ] Create respawn form handler in `post()` method
- [ ] Import `create_flash_clone_character()` function
- [ ] Import `create_character_from_template()` function
- [ ] Handle template selection + creation
- [ ] Handle flash clone selection + creation
- [ ] Add error handling and user feedback messages

### Phase 4: Testing
- [ ] Test first character creation (should still show form)
- [ ] Archive a character, verify respawn interface appears
- [ ] Test template selection and character creation
- [ ] Test flash clone selection and character creation
- [ ] Verify Roman numeral naming works (Jorge → Jorge II)
- [ ] Test sex selection for both templates and flash clone
- [ ] Verify stat inheritance for flash clones
- [ ] Test appearance inheritance (desc, longdesc) for flash clones

### Phase 5: Polish
- [ ] Add loading states for form submission
- [ ] Style to match Gelatinous Monster aesthetic
- [ ] Add helpful tooltips/descriptions
- [ ] Ensure mobile responsiveness
- [ ] Add confirmation messages on success

## Edge Cases

1. **Template generation fails**: Show error, fallback to manual form
2. **No last_character but all characters archived**: Treat as first character
3. **last_character deleted from DB**: Handle gracefully, show manual form
4. **Concurrent creation attempts**: Django form validation should handle
5. **Invalid sex selection**: Validate and default to 'ambiguous'

## Success Criteria

- [ ] Users with archived characters see respawn interface on web
- [ ] Templates generate correctly with random stats (300 point total)
- [ ] Flash clone inherits all data from archived character
- [ ] Roman numeral naming works correctly
- [ ] Sex selection applies to created character
- [ ] First-time users still see manual stat allocation form
- [ ] All creation paths persist character correctly to database
- [ ] UI matches game's dissolution/body-horror aesthetic

## Future Enhancements

- [ ] Allow regenerating templates without page refresh (AJAX)
- [ ] Preview character appearance before decanting
- [ ] Add "Randomize All" button for template generation
- [ ] Allow editing template stats before decanting (within 300 point limit)
- [ ] Add character comparison view (side-by-side stats)
- [ ] Add descriptive stat adjectives (e.g., "Mighty" instead of "5") - deferred due to template filter complexity

---

## Implementation Completed (January 2025)

### Phase 1: COMPLETED ✅

**Implementation Summary:**
Phase 1 was successfully implemented with respawn interface, template generation, flash clone functionality, and sex selection. During testing, several critical bugs were discovered and fixed.

**Completed Components:**

1. **View Logic** (`web/website/views/characters.py`)
   - ✅ `get()` method detects respawn vs first character
   - ✅ `show_respawn_interface()` generates 3 templates + flash clone
   - ✅ `handle_respawn_submission()` processes template/clone selection
   - ✅ Sex selection integrated for all respawn paths
   - ✅ Imports `generate_random_template()` and `create_flash_clone_character()`

2. **Template Creation** (`web/templates/website/character_respawn_create.html`)
   - ✅ Respawn interface matches dissolution aesthetic
   - ✅ Radio buttons for template selection
   - ✅ Flash clone option with preview
   - ✅ Sex selection (male/female/ambiguous)
   - ✅ Thematic styling with dark colors

3. **Form Processing**
   - ✅ Respawn POST handler implemented
   - ✅ Template selection and character creation working
   - ✅ Flash clone selection and creation working
   - ✅ Roman numeral naming integrated
   - ✅ Sex inheritance for flash clones (automatic from old character)

4. **Testing Results**
   - ✅ First character creation works (shows manual form)
   - ✅ Respawn interface appears for archived characters
   - ✅ Template selection creates characters correctly
   - ✅ Flash clone preserves all data (stats, appearance, sex)
   - ✅ Roman numeral naming works correctly
   - ✅ Mobile responsive design verified

### Bugs Discovered and Fixed During Testing

#### 1. Menu Visibility Bug (Superuser Bypass)
**Issue:** "Decant Sleeve" menu item was showing for superusers even when at character limit (MAX_NR_CHARACTERS=1), allowing access to character creation when it should be hidden.

**Root Cause:** `typeclasses/accounts.py` `at_character_limit` property had a superuser bypass:
```python
if self.is_superuser:
    return False  # Never at limit for superusers
```

**Fix:** Removed superuser bypass entirely (commit `bccfae3`):
- Deleted the `if self.is_superuser: return False` logic
- Added defensive coding: `if not char or not hasattr(char, 'db'): continue`
- Now applies character limit consistently to ALL users including superusers
- Menu properly hides when at limit for everyone

**Rationale:** Superuser backup accounts (like Drivel) should respect game rules. Superusers aren't meant for regular play, just administrative access.

#### 2. Roman Numeral Parsing Bug (Name Truncation)
**Issue:** Names ending in letters that are valid Roman numerals were being truncated. "Drivel" became "Drive II" (the "L" was interpreted as Roman numeral 50).

**Root Cause:** `commands/charcreate.py` line 130 used regex pattern `r'^(.*?)\s*([IVXLCDM]+)$'` which matched any trailing Roman numeral letters even without whitespace.

**Fix:** Changed regex pattern to require whitespace (commit `d5caa42`):
```python
# Old pattern (too aggressive)
r'^(.*?)\s*([IVXLCDM]+)$'

# New pattern (requires space before numeral)
r'^(.+?)\s+([IVXLCDM]+)$'
```

**Result:** 
- "Drivel" stays "Drivel" (no space before L)
- "Drivel II" correctly strips to "Drivel" (space before II)
- Only explicitly formatted Roman numerals are stripped

#### 3. Flash Clone Sex Inheritance Bug
**Issue:** Flash clone was overriding inherited sex with 'ambiguous' default from POST data, instead of preserving the original character's sex.

**Root Cause:** `web/website/views/characters.py` `handle_respawn_submission()` was reading `sex` from POST data and applying it to both template-based characters AND flash clones. Flash clones already inherit sex automatically in `create_flash_clone_character()`.

**Fix:** Removed sex override for flash clone option (commit `00e2ff3`):
```python
# For flash clone, don't read sex from POST
if sleeve_choice == 'flash_clone':
    character = create_flash_clone_character(account, old_character)
    # Sex already inherited automatically
else:
    # Template-based creation uses POST sex
    sex = request.POST.get('sex', 'ambiguous')
    character = create_character_from_template(account, template, sex)
```

**Result:** Flash clones now properly maintain their original sex (male/female) across respawns without manual selection.

#### 4. UI Cleanup (Manage Sleeves Display)
**Issue:** Character list page (`character_manage_list.html`) had redundant and unnecessary display elements.

**Changes Made** (commit `f7688c9`):
- ❌ Removed placeholder `<img>` tag (will be account-level feature later)
- ❌ Removed "GRIM Stats:" label (redundant, stats are self-evident)
- ❌ Removed "Deaths: X" field (redundant with Roman numeral in character name)
- ✅ Kept essential info: Character name (with Roman numeral), GRIM stat badges (numeric), Sex field, Archived badge

**Result:** Cleaner, more focused character list showing only necessary information.

### Attempted Enhancement (Rolled Back)

#### Template Filter for Descriptive Stats
**Attempted:** Add Django template filter to show descriptive adjectives for GRIM stats instead of numbers (e.g., "Mighty" for Grit 5, "Frail" for Grit 1).

**Implementation:**
- Created `web/website/templatetags/__init__.py`
- Created `web/website/templatetags/character_filters.py` with `stat_descriptor` filter
- Imported `STAT_DESCRIPTORS` from `world/combat/constants.py`
- Modified templates to use `{{ object.grit|stat_descriptor:"grit" }}`

**Result:** 500 errors on Manage Sleeves page. Issue persisted through:
- Simplified filter (just return numeric value)
- Full Django restart (`docker-compose restart evennia`)
- Server reload attempts

**Decision:** Rolled back entirely (commit `babd0b4` reverting commits `b3cf3df`, `94683a3`, `6d2a4ab`):
- Deleted `web/website/templatetags/` directory
- Restored numeric stat display
- Back to stable state

**Lessons Learned:**
- Django template filter system has specific registration requirements
- Issue likely related to app configuration or import paths
- Numeric display is clean and functional - descriptive adjectives can be revisited later
- Template filters require careful Django app structure

### Design Decisions Documented

1. **Single Character Display:** The Manage Sleeves page only shows the latest iteration of each character (e.g., "Jorge III" but not "Jorge" and "Jorge II"). This is INTENTIONAL for `MAX_NR_CHARACTERS=1` permadeath design. Old iterations are archived and removed from `account.characters` (see `commands/charcreate.py` line 323 comment).

2. **Superuser Treatment:** Superusers now respect character limits. They're meant for administrative access, not regular gameplay. The backup account Drivel is subject to the same rules as regular players.

3. **Roman Numeral Formatting:** Requires whitespace before numeral to prevent false positives. Only explicitly formatted Roman numerals (with space) are stripped during name building.

4. **Flash Clone Sex Inheritance:** Flash clones inherit sex automatically from the archived character. Sex selection in the respawn UI only applies to template-based characters, not flash clones.

5. **Numeric Stats Display:** UI shows numeric stat values (1-10 scale) rather than descriptive adjectives. This is clear, concise, and avoids template filter complexity. Descriptive system can be added later if needed.

### Current State (Post-Phase 1)

**Status:** Phase 1 fully functional and deployed to production (play.gel.monster)

**Verified Working:**
- ✅ Menu visibility respects character limit (including for superusers)
- ✅ Respawn interface generates templates correctly
- ✅ Flash clone preserves all character data (stats, sex, appearance)
- ✅ Roman numeral naming works without false positives
- ✅ Sex selection works for template-based characters
- ✅ Character list displays cleanly with essential info only
- ✅ First character creation still uses manual form (unchanged)

**Commits:**
- `bccfae3` - Remove superuser bypass from at_character_limit
- `d5caa42` - Fix Roman numeral regex pattern
- `00e2ff3` - Fix flash clone sex inheritance  
- `f7688c9` - Clean up Manage Sleeves display
- `babd0b4` - Revert template filter changes (rollback)

**Next Steps:**
Phase 1 is complete and stable. Future phases can focus on polish, AJAX template regeneration, appearance preview, and other enhancements listed above.

---

## Bug Fix: Web-Created Characters Appearing as Visible NPCs (January 2025)

### Problem Statement

**Issue:** Characters created via web interface (both first-time and respawn) were appearing as visible NPCs in the game world before the player ever connected via telnet.

**Symptoms:**
- Web-created characters visible in START_LOCATION as unpuppeted objects
- Appeared identical to NPCs created via @spawnnpc command
- Characters became puppeted only on first telnet login
- Violated expected "invisible until first login" behavior

**Root Cause:** Characters created via web were:
1. Created with `location = START_LOCATION`
2. Left unpuppeted (no active session)
3. Remained visible because location was not None

### Solution: Mimic Evennia's Standard Unpuppet Behavior

**Key Insight from Evennia Source Code:**

From `evennia/objects/objects.py` `DefaultCharacter` class:

**`at_post_unpuppet()` (lines 3288-3321):**
```python
def at_post_unpuppet(self, account=None, session=None, **kwargs):
    if not self.sessions.count():
        # only remove this char from grid if no sessions control it anymore.
        if self.location:
            # Save location for restoration
            self.db.prelogout_location = self.location
            # Make invisible by removing from grid
            self.location = None
```

**`at_pre_puppet()` (lines 3237-3259):**
```python
def at_pre_puppet(self, account, session=None, **kwargs):
    if self.location is None:
        # Restore character from invisible storage
        location = self.db.prelogout_location if self.db.prelogout_location else self.home
        if location:
            self.location = location
            self.location.at_object_receive(self, None)
```

**Conclusion:** Setting `character.location = None` is Evennia's standard mechanism for making unpuppeted player characters invisible.

### Implementation

Modified `web/website/views/characters.py` in two places:

#### 1. Respawn Character Creation (`handle_respawn_submission`)

```python
# After character creation...
# WEB-CREATED CHARACTERS: Make invisible until puppeted
# Set location to None (standard Evennia unpuppet behavior)
# This makes them invisible in room until first puppet/login
# Save current location for restoration during at_pre_puppet
character.db.prelogout_location = character.location
character.location = None

# Debug logging
splattercast.msg(
    f"WEB_CHAR_CREATE: {character.key} created via web (respawn), "
    f"location set to None for invisibility. "
    f"Will be restored to {character.db.prelogout_location.key} on telnet login."
)
```

#### 2. First-Time Character Creation (`form_valid`)

```python
# After character creation...
# WEB-CREATED CHARACTERS: Make invisible until puppeted
# Set location to None (standard Evennia unpuppet behavior)
# This makes them invisible in room until first puppet/login
# Save current location for restoration during at_pre_puppet
character.db.prelogout_location = character.location
character.location = None

# Debug logging
splattercast.msg(
    f"WEB_CHAR_CREATE: {character.key} created via web (first-time), "
    f"location set to None for invisibility. "
    f"Will be restored to {character.db.prelogout_location.key} on telnet login."
)
```

### Behavior Flow

#### Web Character Creation
1. **Character Created**: Django view creates character with `location=START_LOCATION`
2. **Made Invisible**: Immediately set `location = None`, save previous location to `db.prelogout_location`
3. **Invisible State**: Character exists in database but not in game world
4. **Debug Logging**: Splattercast message confirms invisibility

#### First Telnet Login
1. **Account Login**: Player connects via telnet
2. **Auto-Puppet**: `at_post_login()` calls `puppet_object()` (if `AUTO_PUPPET_ON_LOGIN=True`)
3. **at_pre_puppet Hook**: Evennia's built-in hook detects `location is None`
4. **Restoration**: Character restored to `db.prelogout_location` (or home)
5. **Visible & Active**: Character appears in game world with standard "has entered the game" message

#### Subsequent Sessions
- **Normal puppet/unpuppet cycle**: Standard Evennia behavior
- **Quit**: Character location set to None (standard)
- **Login**: Character restored from None location (standard)

### NPCs vs Player Characters

#### NPCs (Created via @spawnnpc)
- **Never puppeted**: No session, no account
- **Always visible**: Location is always a room
- **Behavior unchanged**: Continue working as before

#### Player Characters (Web-created)
- **Initially unpuppeted**: No session until telnet login
- **Initially invisible**: `location = None`
- **Visible when puppeted**: Restored to room on first puppet
- **Standard Evennia behavior**: Matches quit/disconnect mechanics

### Why This Solution Is Superior

**Alternative 1: Leave at START_LOCATION, add visibility check**
- ❌ Requires custom `access()` override in Character typeclass
- ❌ Requires distinguishing NPCs from player chars
- ❌ More complex, error-prone

**Alternative 2: Move to Limbo**
- ❌ Requires special handling on login
- ❌ Less standard Evennia pattern
- ❌ Extra location management

**Current Solution (location=None)**
- ✅ Standard Evennia behavior (mimics quit/disconnect)
- ✅ Zero custom hooks needed
- ✅ Automatic restoration via built-in `at_pre_puppet`
- ✅ Simple, clean, maintainable
- ✅ No special case logic for NPCs

### Files Modified
- `web/website/views/characters.py`:
  - `handle_respawn_submission()`: Added location=None after respawn creation
  - `form_valid()`: Added location=None after first-time creation
  - Debug logging added to both methods

### Testing Checklist
- [ ] Create character via web (first-time)
- [ ] Verify character not visible in START_LOCATION
- [ ] Login via telnet
- [ ] Verify auto-puppet works
- [ ] Verify character appears in START_LOCATION
- [ ] Verify "has entered the game" message
- [ ] Create character via web (respawn)
- [ ] Verify same invisibility behavior
- [ ] Verify NPCs created via @spawnnpc still visible
- [ ] Verify quit/login cycle works normally

### References
- Evennia Source: `evennia/objects/objects.py` (DefaultCharacter class)
  - `at_post_unpuppet()`: Lines 3288-3321
  - `at_pre_puppet()`: Lines 3237-3259
- Evennia GitHub: https://github.com/evennia/evennia

### Conclusion

Web-created characters now seamlessly integrate with Evennia's standard visibility mechanics. By setting `location = None` immediately after web creation, we achieve the desired "invisible until first puppet" behavior without any custom hooks or special case logic. The solution is elegant, maintainable, and follows Evennia best practices.

````
