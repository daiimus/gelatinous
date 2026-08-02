# Bug Command Specification

> **Status:** ✅ **SHIPPED** — verified against code 2026-08-02.

## Overview

The `@bug` command allows players and staff to submit bug reports directly to the GitHub repository as issues. This integrates in-game feedback with the development workflow while maintaining appropriate privacy boundaries.

**Current Status**: ✅ **Production Ready** - All planned features implemented and deployed.

## Features

- **@bug**: Interactive workflow for creating detailed bug reports with title, category, and description
- **@bug/list**: View the 10 most recent bug reports from GitHub
- **@bug/show <number>**: View full details of a specific bug including all comments (supports `#15` format)
- **Rate Limiting**: 30 reports per player per day
- **Privacy-Conscious**: No email addresses or sensitive player data exposed
- **GitHub Integration**: Issues automatically created with proper formatting and labels

## Design Principles

1. **Accessible**: All players can report bugs
2. **Privacy-Conscious**: No email addresses or sensitive player data exposed
3. **Context-Rich**: Captures technical environment for debugging
4. **Generous Rate Limiting**: Players can report up to 30 bugs per day
5. **Developer-Friendly**: Issues created with proper formatting and labels

---

## Command Syntax

### Basic Usage
```
@bug
```
Opens an interactive workflow for creating detailed bug reports:
1. Enter a title (minimum 10 characters)
2. Select a category from a menu
3. Write detailed description in a multi-line editor

### List Recent Bugs
```
@bug/list
```
Shows the 10 most recent bug reports from GitHub (open and closed).

### View Bug Details
```
@bug/show <number>
@bug/show #<number>
```
Displays full details of a specific bug report including:
- Issue title, state, and category
- Creation and last update dates
- Full description
- All comments from GitHub
- Direct link to the issue

Examples:
- `@bug/show 15`
- `@bug/show #15`

---

## GitHub Issue Format

### Issue Title
The player's title input is used directly as the issue title (no [BUG] prefix).

### Issue Labels
- `bug` (always applied)
- `player-reported` (always applied)
- `<category>` (if specified, e.g., `combat`, `medical`)

### Issue Body Template
```markdown
**Reported By:** <account_username>
**Location:** <room #dbref>

**Category:** <category or "Uncategorized">

---

## Description

<player's detailed description>

---

## Technical Environment

- **Server:** play.gel.monster
- **Commit:** <git commit hash>
```

### Privacy Considerations

**✅ INCLUDED:**
- Account username (display name, not email)
- Current room #dbref (for context)
- Git commit hash (for version tracking)

**❌ EXCLUDED:**
- Email addresses
- Character names
- Character G.R.I.M. stats
- Room descriptive names (only #dbref)
- Account IP addresses
- Session information
- Personal identifying information
- Timestamps (GitHub Issues tracks creation time automatically)

---

## Technical Implementation

### File Structure
```
commands/
  CmdBug.py          # New command implementation
  default_cmdsets.py # Add CmdBug to default cmdset

server/conf/
  secret_settings.py # Store GITHUB_TOKEN (gitignored)
```

### GitHub API Integration

**Endpoint:**
```
POST https://api.github.com/repos/daiimus/gelatinous/issues
```

**Authentication:**
- Personal Access Token (PAT) stored in `secret_settings.py`
- Required scope: `public_repo` (for issue creation in public repositories)
  - Note: If repository were private, would need full `repo` scope
- Token format: `GITHUB_TOKEN = "ghp_your_token_here"`

**Request Headers:**
```python
{
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "Gelatinous-MUD-Bug-Reporter"
}
```

**Request Payload:**
```python
{
    "title": f"[BUG] {player_description}",
    "body": formatted_issue_body,
    "labels": ["bug", "player-reported", category]
}
```

### Dependencies
- `requests` library (HTTP client for GitHub API)
- `json` (standard library, payload formatting)
- `datetime` (standard library, timestamps)
- `git` command line (to get current commit hash)

---

## Rate Limiting

### Per-Player Limits
- **Daily Limit:** 30 bug reports per account per day (resets at midnight UTC)
- **Cooldown:** None (no delay between reports)
- **Storage:** Track in `account.db.bug_reports_today` with date stamp

### Rate Limit Messages
```python
# When limit reached
"You've reached the daily limit of 30 bug reports. Please try again tomorrow."

# When limit approaching
"Bug report submitted! (You have {remaining} reports remaining today.)"
```

### Reset Logic
```python
def check_rate_limit(account):
    today = datetime.now(UTC).date()
    last_date = account.db.bug_report_date
    
    if last_date != today:
        # New day, reset counter
        account.db.bug_report_count = 0
        account.db.bug_report_date = today
    
    count = account.db.bug_report_count or 0
    return count < 30
```

---

## User Experience Flow

### Interactive Bug Report Flow
```
> @bug

=== Detailed Bug Report ===

Provide a short title for the bug (minimum 10 characters):

> Grenades don't explode when rigged to exits

Title: Grenades don't explode when rigged to exits

Select a category:

  1 - Combat
  2 - Medical
  3 - Movement
  4 - Items/Inventory
  5 - Commands
  6 - Web Interface
  7 - World/Environment
  8 - Social/Communication
  9 - System/Performance
  0 - Other

> 1

Title: Grenades don't explode when rigged to exits
Category: Combat

Now provide detailed information:
  - What you were trying to do
  - What you expected to happen
  - What actually happened
  - Steps to reproduce (if possible)

Editor Commands:
  :w or :wq - Save and submit bug report
  :q or :q! - Cancel without submitting
  :h - Show editor help

Opening editor...

---------Line Editor [bug_report_editor]-----------------------------

---------[1:01 w:000 c:0000]-----------(:h for help)-----------------

> I tried to rig a grenade to the north exit.
> I expected it to explode when someone walked through.
> Instead, nothing happens and the grenade vanishes.
> 
> Steps:
> 1. Get grenade from inventory
> 2. Type "rig grenade to north"
> 3. Command succeeds but grenade disappears
> 4. Someone walks through exit - no explosion
> :wq

Creating detailed bug report (category: combat)...

✓ Issue created: https://github.com/daiimus/gelatinous/issues/44

Thank you for the detailed report! The development team will investigate.
You have 29 bug reports remaining today.
```

### List Recent Bugs
```
> @bug/list

=== Recent Bug Reports ===

#44 OPEN [Combat] - Grenades don't explode when rigged to exits
  Created: 2025-10-22
  https://github.com/daiimus/gelatinous/issues/44

#43 CLOSED [Medical] - Healing doesn't restore full HP
  Created: 2025-10-21
  https://github.com/daiimus/gelatinous/issues/43

[... 8 more issues ...]

Showing 10 most recent reports. Visit GitHub for full history.
```

### View Bug Details
```
> @bug/show 44

======================================================================
Issue #44 OPEN
======================================================================

Title: Grenades don't explode when rigged to exits
Category: Combat
Created: 2025-10-22
Updated: 2025-10-22
URL: https://github.com/daiimus/gelatinous/issues/44

----------------------------------------------------------------------
Description:

**Reported By:** PlayerName
**Location:** Room #123

**Category:** Combat

**Description:**

I tried to rig a grenade to the north exit.
I expected it to explode when someone walked through.
Instead, nothing happens and the grenade vanishes.

Steps:
1. Get grenade from inventory
2. Type "rig grenade to north"
3. Command succeeds but grenade disappears
4. Someone walks through exit - no explosion

----------------------------------------------------------------------

Comments (2):

1. daiimus (2025-10-22)
Thanks for the report! I can reproduce this. The issue is in the exit trigger 
system not properly handling deferred explosions. Working on a fix.

2. daiimus (2025-10-23)
Fixed in commit abc123f. The trap system now properly defers explosion logic
until the trigger fires. Will be in next deployment.

======================================================================
```

### Rate Limit Reached
```
> @bug

You've reached the daily limit of 30 bug reports.
The limit resets in 4 hours, 23 minutes.
```

### Short Title Error
```
> @bug

=== Detailed Bug Report ===

Provide a short title for the bug (minimum 10 characters):

> test bug

Title too short. Please provide at least 10 characters.

Bug report cancelled.
```

### Editor Cancellation
```
> @bug

[... workflow starts ...]

Opening editor...

> This is my bug description
> :q

Bug report cancelled.
```

### Network Error
```
> @bug

[... workflow completes ...]

Creating detailed bug report (category: combat)...

Failed to create bug report: Connection timeout.
Please try again in a moment. If the problem persists, contact staff.
```

---

## Technical Implementation

### EvMenu Integration
The command uses Evennia's EvMenu system for the interactive workflow:
- `node_title`: Prompts for bug title (text input node)
- `_validate_title_input`: Goto callable that validates title
- `node_category`: Category selection menu (numbered options)
- `node_open_editor`: Opens EvEditor for detailed description

**Key Settings:**
- `cmd_on_exit=None` - Prevents default "look" command when menu exits
- Uses goto callables instead of node functions for validation steps
- EvEditor opens with 0.1s delay after menu closes to avoid input capture

### EvEditor Integration
Multi-line editor for bug descriptions:
- `loadfunc`: Returns empty string (blank buffer)
- `savefunc`: Creates GitHub issue if description valid (min 10 chars)
- `quitfunc`: Shows cancellation message only if save wasn't called
- Uses flag `caller.ndb._bug_editor_saved` to track save state

### Dependencies
- `evennia.commands.default.muxcommand.MuxCommand` - For switch support
- `evennia.utils.evmenu.EvMenu` - Interactive menu system
- `evennia.utils.eveditor.EvEditor` - Multi-line text editor
- `requests` library (HTTP client for GitHub API)
- `json` (standard library, payload formatting)
- `datetime` (standard library, timestamps)
- `git` command line (to get current commit hash)

### Network Failures
```python
try:
    response = requests.post(url, headers=headers, json=payload, timeout=10)
    response.raise_for_status()
except requests.exceptions.Timeout:
    caller.msg("|rBug report timed out. Please try again.|n")
except requests.exceptions.ConnectionError:
    caller.msg("|rUnable to connect to GitHub. Please try again later.|n")
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 401:
        caller.msg("|rGitHub authentication failed. Please contact staff.|n")
    elif e.response.status_code == 403:
        caller.msg("|rRate limited by GitHub. Please try again later.|n")
    else:
        caller.msg(f"|rGitHub API error: {e.response.status_code}|n")
```

### Input Validation
```python
def sanitize_bug_description(text):
    """Sanitize user input to prevent markdown injection or excessive content."""
    # Limit length
    if len(text) > 5000:
        return text[:5000] + "\n\n[Description truncated at 5000 characters]"
    
    # Escape potential markdown injection (but allow basic formatting)
    # Keep newlines, basic formatting, but escape potentially malicious patterns
    
    return text.strip()
```

### Missing Configuration
```python
if not hasattr(settings, 'GITHUB_TOKEN') or not settings.GITHUB_TOKEN:
    caller.msg("|rBug reporting is not configured. Please contact staff.|n")
    return
```

---

## Admin Features

### List Recent Issues
```
@bug/list [count]
```

**Example Output:**
```
> @bug/list 5

|cRecent Bug Reports (Last 5):|n

|y#44|n [combat] Grapple release doesn't work after knockout
  Reported by: Alice (2 hours ago)
  |chttps://github.com/daiimus/gelatinous/issues/44|n

|y#43|n Grenades vanish when rigged to exits
  Reported by: Bob (3 hours ago)
  |chttps://github.com/daiimus/gelatinous/issues/43|n

|y#42|n Web character creation form validation error
  Reported by: Carol (5 hours ago)
  |chttps://github.com/daiimus/gelatinous/issues/42|n

[... truncated ...]
```

### Future Admin Commands (Phase 2)
- `@bug/close <issue_number>` - Close an issue from in-game
- `@bug/comment <issue_number> <comment>` - Add comment to issue
- `@bug/search <query>` - Search existing issues

---

## Security Considerations

### Token Security
- ✅ Store token in `secret_settings.py` (gitignored)
- ✅ Never log or display token in error messages
- ✅ Use environment variable as fallback: `os.getenv('GITHUB_TOKEN')`
- ✅ Restrict token scope to minimum required (`repo` only)

### Input Sanitization
- ✅ Limit description length (5000 characters)
- ✅ Strip potentially malicious markdown patterns
- ✅ Validate category against whitelist
- ✅ Escape special characters appropriately

### Rate Limiting
- ✅ 30 reports per account per day
- ✅ Prevent spam/abuse
- ✅ No cooldown between reports (trust players)

### Data Privacy
- ✅ No email addresses exposed
- ✅ No G.R.I.M. stats leaked
- ✅ Only #dbref for location (not descriptive room name)
- ✅ Account username only (not internal IDs)

---

## Testing Strategy

### Manual Testing Checklist
- [x] Interactive workflow creates issue successfully
- [x] Title validation enforces 10 character minimum
- [x] Category selection menu displays all options
- [x] EvEditor opens and accepts multi-line input
- [x] EvEditor :wq saves and submits report
- [x] EvEditor :q cancels without submitting
- [x] Rate limiting enforces 30/day limit
- [x] Rate limit resets at midnight UTC
- [x] GitHub link is returned and functional
- [x] @bug/list shows recent 10 issues
- [x] @bug/show displays full issue details and comments
- [x] @bug/show supports both "15" and "#15" formats
- [x] Error handling for network failures
- [x] Error handling for invalid GitHub token
- [x] Privacy: no emails or stats in issues
- [x] No spurious "look" command in editor buffer
- [x] No "Bug report cancelled" after successful save
- [x] All text colors are readable (no dark gray)

### Test Cases
```python
# Test 1: Full workflow
@bug
# Enter title: "Test bug report title"
# Select category: 1 (Combat)
# Enter description: "This is a test\nwith multiple lines"
# :wq
# Expected: Issue created with all data

# Test 2: Title too short
@bug
# Enter title: "test"
# Expected: Error message, workflow cancelled

# Test 3: Empty description
@bug
# Enter valid title and category
# Enter nothing in editor, just :wq
# Expected: Error about minimum 10 characters

# Test 4: Cancel in editor
@bug
# Complete workflow but type :q instead of :wq
# Expected: "Bug report cancelled" message only

# Test 5: Rate limiting
# Create 30 reports rapidly
# Expected: 30th succeeds, 31st shows rate limit message

# Test 6: List command
@bug/list
# Expected: Shows 10 most recent issues with links

# Test 7: Show command
@bug/show 15
# Expected: Shows full issue details with comments

# Test 8: Show command with # prefix
@bug/show #15
# Expected: Same as Test 7

# Test 9: Show non-existent issue
@bug/show 99999
# Expected: "Issue #99999 not found."
```

---

## Implementation Phases

### Phase 1: Core Functionality ✅ COMPLETE
- ✅ Interactive EvMenu workflow for title and category
- ✅ EvEditor for detailed multi-line descriptions  
- ✅ GitHub issue creation via API
- ✅ Rate limiting (30/day)
- ✅ Privacy-conscious issue format
- ✅ Error handling
- ✅ @bug/list command for viewing recent issues

### Phase 2: Completed Enhancements ✅ COMPLETE
- ✅ Fixed EvMenu cmd_on_exit causing "look" in editor
- ✅ Fixed duplicate cancellation messages
- ✅ Removed quick @bug <message> format (encouraged poor reports)
- ✅ Simplified help text
- ✅ Added @bug/show command for viewing full issue details
- ✅ Support for both "15" and "#15" formats in @bug/show
- ✅ Replaced all unreadable dark gray colors with white/cyan
- ✅ Display issue comments from GitHub in-game

**Status**: All planned features implemented. System is production-ready.

### Phase 3: Future Enhancements (Not Currently Planned) ⏳
The following features could be added in the future if needed:
- ⏳ Duplicate detection before creating issues
- ⏳ Issue status tracking/notifications for players
- ⏳ Admin close/comment commands from in-game
- ⏳ Player notification when their bugs are resolved
- ⏳ Attachment support (command history, combat logs)
- ⏳ Integration with staff channels for new bug alerts

---

## Configuration

### secret_settings.py
```python
# GitHub Bug Reporting Configuration
GITHUB_TOKEN = "ghp_your_personal_access_token_here"
GITHUB_REPO = "daiimus/gelatinous"
BUG_REPORT_DAILY_LIMIT = 30
```

### settings.py (if needed)
```python
# Bug reporting defaults (can override in secret_settings.py)
BUG_REPORT_DAILY_LIMIT = getattr(secret_settings, 'BUG_REPORT_DAILY_LIMIT', 30)
GITHUB_REPO = getattr(secret_settings, 'GITHUB_REPO', 'daiimus/gelatinous')
```

---

## Success Metrics

### Adoption
- Number of bug reports submitted per week
- Percentage of players who use the command
- Average time to first bug report (new players)

### Quality
- Actionable bug reports (contain enough info to reproduce)
- False positive rate (non-bugs reported as bugs)
- Duplicate report rate

### Developer Impact
- Bugs fixed from player reports vs. other sources
- Average time from report to fix
- Player satisfaction with bug resolution

---

## Documentation

### In-Game Help
```
> help @bug

@bug - Report a bug to the development team

Usage:
  @bug
  @bug/list

Opens an interactive bug report workflow that will guide you through:
1. Entering a title/summary for the bug
2. Selecting a category
3. Writing a detailed description in a multi-line editor

Use @bug/list to view recent bug reports from the GitHub repository.

Your report will be created as a GitHub issue for the development team
to review. All players can submit up to 30 bug reports per day.

Be clear and descriptive - good bug reports help us fix issues faster!
```

### Player Documentation
The interactive workflow guides players through creating good bug reports:
- Title must be at least 10 characters
- Category selection from numbered menu
- EvEditor instructions shown before opening
- Minimum 10 characters required in description

---

*This specification reflects the implemented system as of October 2025.*

````
