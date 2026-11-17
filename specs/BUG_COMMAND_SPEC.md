# Bug Command Specification

> **Status:** ✅ **SHIPPED** — verified against code 2026-08-02.

## Overview

The `@bug` command allows players and staff to submit bug reports directly to the GitHub repository as issues. This integrates in-game feedback with the development workflow while maintaining appropriate privacy boundaries.

**Current Status**: ✅ **Production Ready** - All planned features implemented and deployed.

## Features

- **@bug**: Interactive workflow for creating detailed bug reports with title, category, and description
- **@bug/list**: View the 10 most recent bug reports from GitHub
- **@bug/show <number>**: View full details of a specific bug including all comments (supports `#15` format)
- **Rate Limiting**: a daily cap per account (`BUG_REPORT_DAILY_LIMIT`, default 30), shared by all of that account's characters
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

`bug` (without the @) works too. A plain `@bug` takes no text: `@bug <text>` only prints the usage line. A blank title cancels the report. Every GitHub call runs in a background thread, so a slow GitHub does not freeze the game (#460); `/list` and `/show` first print a "Fetching..." line.

### List Recent Bugs
```
@bug/list
```
Shows the 10 most recent bug reports from GitHub (open and closed). Only issues labelled `player-reported` (those filed with `@bug`) are listed. `@bug/show` displays any issue number in the repository, not only player reports.

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
- `<category>`: always one of `combat`, `medical`, `movement`, `items`, `commands`, `web`, `world`, `social`, `system`, `other`. At the menu the digit or the word picks a category, and anything else picks `other`.

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
The commit is the short (7-character) hash of `master`, read once per server process from the git checkout, or from `git rev-parse --short HEAD` if that file cannot be read; it is "unknown" if neither works.

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
  secret_settings.py # Store GITHUB_TOKEN and GITHUB_REPO (gitignored)
```

### GitHub API Integration

**Endpoint:**
```
POST https://api.github.com/repos/daiimus/gelatinous/issues
```
The `owner/repo` part comes from `settings.GITHUB_REPO`.

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
    "title": sanitize_title(player_title),  # the player's title, @/# escaped, max 100 characters, no prefix
    "body": formatted_issue_body,
    "labels": ["bug", "player-reported", category]  # get_labels adds the category only if it is one of the ten known ones
}
```

### Dependencies
- `requests` library (HTTP client for GitHub API)
- `json` (standard library, payload formatting)
- `datetime` (standard library: the UTC date for the daily cap and the time until it resets)
- `django.conf.settings` (token, repository and daily limit)
- `git` command line (to get current commit hash)

> **Correction 2026-09-11:** `json` is not imported — see the corrections
> under "Technical Implementation → Dependencies" below, which apply to
> this list too. Missing here as well: `run_async` (#460) and `re`
> (#2527).

---

## Rate Limiting

### Per-Player Limits
- **Daily Limit:** `settings.BUG_REPORT_DAILY_LIMIT` (default 30) bug reports per account per day (resets at midnight UTC). The cap is checked twice: when `@bug` is typed, so a capped player is refused before the editor opens (#3367), and again at save (`_save_callback`), which takes the slot at once, before GitHub is called (#2526). If GitHub then fails, the slot is given back, unless the count has already rolled over to a new day.
- **Cooldown:** None (no delay between reports)
- **Storage:** `account.db.bug_report_count` (reports today) and `account.db.bug_report_date` (the UTC date of that count)

### Rate Limit Messages

> **Correction 2026-09-11:** neither string is what a player sees.
> The refusal is two lines and does not say "try again tomorrow" —
> "You've reached the daily limit of 30 bug reports." then "The limit
> resets in {time}." (`func` and `_save_callback` in `commands/CmdBug.py`), which is what the
> "Rate Limit Reached" flow further down shows. The remaining-count line
> is not conditional on the limit being "approached": it is sent after
> **every** successful report (`_on_created`), as "You have N bug
> reports remaining today.", merely highlighted in yellow when N ≤ 5.
> The "30" in the refusal was a hardcoded literal while the limit itself
> read `BUG_REPORT_DAILY_LIMIT` — fixed under #3408 (2026-09-15): the
> tracked `settings.py` now declares the default, every read is a plain
> settings lookup, the refusal interpolates it and the help names no number.
```python
# When the limit is reached (on typing @bug, and again at save)
f"You've reached the daily limit of {limit} bug reports."
f"The limit resets in {time}."

# After every successful report (the number is yellow when it is 5 or less)
f"You have {remaining} bug reports remaining today."
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
    return count < settings.BUG_REPORT_DAILY_LIMIT
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
  :q! - Cancel without submitting
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
Issue #44 [OPEN]
======================================================================

Title: Grenades don't explode when rigged to exits
Category: Combat
Created: 2025-10-22
Updated: 2025-10-22
URL: https://github.com/daiimus/gelatinous/issues/44

----------------------------------------------------------------------
Description:

**Reported By:** PlayerName
**Location:** #123

**Category:** Combat

---

## Description

I tried to rig a grenade to the north exit.
I expected it to explode when someone walked through.
Instead, nothing happens and the grenade vanishes.

Steps:
1. Get grenade from inventory
2. Type "rig grenade to north"
3. Command succeeds but grenade disappears
4. Someone walks through exit - no explosion

---

## Technical Environment

- **Server:** play.gel.monster
- **Commit:** <short commit hash>

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
> :q!

Bug report cancelled.
```

### Network Error
```
> @bug

[... workflow completes ...]

Creating detailed bug report (category: combat)...

Failed to create bug report: Request timed out. Please try again.
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
- The editor opens inside the last menu node (`node_open_editor`), which then returns `None, None` to close the menu. There is no delay.

### EvEditor Integration
Multi-line editor for bug descriptions. **The editor is stock Evennia
and its commands are Evennia's** — this command supplies callbacks, not
key bindings, and does not subclass or override `EvEditor` (#2525).

- `loadfunc`: Returns empty string (blank buffer)
- `savefunc`: Creates GitHub issue if description valid (min 10 chars).
  **Returns a truthy value on submit**, which is the only thing that
  clears the editor's `_unsaved` flag — without it a second `:w` files
  the report again (#2524)
- `quitfunc`: Shows cancellation message only if save wasn't called
- Uses flag `caller.ndb._bug_editor_saved` to track save state

**Editor keys, as Evennia defines them:**

| key | effect |
|---|---|
| `:w` / `:wq` | save — submits the report |
| `:q!` | quit without saving — cancels |
| `:q` | quit; with an unsaved buffer this **prompts** *"Save before quitting?"*, and `SaveYesNoCmdSet` treats everything except a literal `no`/`n` as yes — a bare Enter included |

An earlier version of this spec described `:q` and `:q!` as synonyms
that both cancel. They are not, and the code never did that; the spec
was wrong, not the implementation. Making `:q` cancel outright would
mean overriding a core Evennia class, which this project does not do.

### Dependencies
- `evennia.commands.default.muxcommand.MuxCommand` - For switch support
- `evennia.utils.evmenu.EvMenu` - Interactive menu system
- `evennia.utils.eveditor.EvEditor` - Multi-line text editor
- `requests` library (HTTP client for GitHub API)
- `json` (standard library, payload formatting)
- `datetime` (standard library: the UTC date for the daily cap and the time until it resets)
- `django.conf.settings` (token, repository and daily limit)
- `git` command line (to get current commit hash)

> **Corrections 2026-09-11** (apply to both Dependencies lists in this
> file — this one and the one under "GitHub API Integration"): `json` is
> **not** imported. `requests` handles serialisation through its `json=`
> kwarg and `.json()` (`create_github_issue` in `commands/CmdBug.py`); the imports are at the
> top of that file. Two real dependencies are missing from both lists:
> `evennia.utils.utils.run_async`, which carries every
> GitHub call off the reactor thread (#460), and `re`, which the
> mention/xref sanitizer needs (#2527). The `git` command line is a
> *fallback* only: the hash is read from `.git/refs/heads/master` first
> and cached for the process lifetime (`get_git_commit_hash` and `_compute_git_commit_hash`).

### Network Failures
`create_github_issue` does not message the player. It returns `(False, message)`, with one of these messages:
- timeout: "Request timed out. Please try again."
- no connection: "Unable to connect to GitHub. Please try again later."
- HTTP 401: "GitHub authentication failed. Please contact staff."
- HTTP 403: "Rate limited by GitHub. Please try again later."
- HTTP 422: "Invalid request data. Please contact staff."
- any other HTTP error: "GitHub API error (status N)"
- anything else: "Unexpected error: ..."

`_on_created` then shows "Failed to create bug report: <message>" and "Please try again in a moment. If the problem persists, contact staff.", and gives the daily slot back (#2526).

### Input Validation
`sanitize_description` cuts the text at 5000 characters (adding "[Description truncated at 5000 characters]"), strips it, and puts a zero-width space after `@` in `@name` and after `#` in `#123`, so the public issue pings no one and links to no other issue (#2527). Markdown and HTML are left as typed. `sanitize_title` gives the title the same treatment and caps it at 100 characters.

### Missing Configuration

> **Correction 2026-09-11:** the block below is close but not the live
> code. There are **two** gates, not one — `GITHUB_TOKEN` and then
> `GITHUB_REPO` (`CmdBug.func`) — and the message is two
> lines: "Bug reporting is not currently configured." followed by "Please
> contact staff directly to report bugs." Both gates run before any
> switch is dispatched, so `@bug/list` and `@bug/show` refuse too.
```python
if not hasattr(settings, 'GITHUB_TOKEN') or not settings.GITHUB_TOKEN:
    caller.msg("|rBug reporting is not currently configured.|n")
    caller.msg("Please contact staff directly to report bugs.")
    return
# then the same check, with the same two lines, for GITHUB_REPO
```

---

## Admin Features

> **Correction 2026-09-11: nothing in this command is staff-gated.**
> `locks = "cmd:all()"` (`CmdBug.locks` in `commands/CmdBug.py`) and neither
> `show_bug_list` nor `show_bug_detail` checks permissions, so every
> player can run `@bug/list` and `@bug/show` — as "Command Syntax" above
> already documents them. Read this heading as "Read-only switches", not
> as an access boundary.

### List Recent Issues
```
@bug/list
```

`@bug/list` takes no count. Any text after it is ignored, and it always shows the 10 newest player reports. Its output is shown under "User Experience Flow" → "List Recent Bugs" above.

### Future Admin Commands (Phase 2)
- `@bug/close <issue_number>` - Close an issue from in-game
- `@bug/comment <issue_number> <comment>` - Add comment to issue
- `@bug/search <query>` - Search existing issues

> **Note 2026-09-11:** mis-phased — read the heading as "Phase 3". "Phase
> 2" is marked ✅ COMPLETE below with a different, finished list, and
> `close`/`comment` appear there again as "Admin close/comment commands
> from in-game" under **Phase 3: Future Enhancements (Not Currently
> Planned)**. `@bug/search` is not listed in any phase. None of the three
> exist: `switch_options = ("list", "show")`, `CmdBug.switch_options` in `commands/CmdBug.py`.

---

## Security Considerations

### Token Security
- ✅ Store token in `secret_settings.py` (gitignored)
- ✅ Never log or display token in error messages
- ✅ Restrict token scope to the minimum required (`public_repo`; full `repo` only if the repository were private)

### Input Sanitization
- ✅ Limit description length (5000 characters)
- Escape `@name` mentions and `#123` references with a zero-width space, in the title and the description (#2527); markdown is left as typed
- ✅ Validate category against whitelist

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
- [x] EvEditor :q! cancels without submitting
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
# Complete workflow but type :q! instead of :wq
# Expected: "Bug report cancelled" message only
#
# NOTE: :q is NOT a synonym for :q!. With an unsaved buffer it prompts
# "Save before quitting?" and submits on anything but a literal no/n.

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

### settings.py
```python
BUG_REPORT_DAILY_LIMIT = 30
```
`settings.py` declares one default, `BUG_REPORT_DAILY_LIMIT = 30` (#3408). It then imports `secret_settings.py`, which can override it. It gives no default for `GITHUB_TOKEN` or `GITHUB_REPO`, so both must be set in `secret_settings.py`. If either is missing, `@bug`, `@bug/list` and `@bug/show` all refuse.

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
  @bug/show <number>

Opens an interactive bug report workflow that will guide you through:
1. Entering a title/summary for the bug
2. Selecting a category
3. Writing a detailed description in a multi-line editor

Use @bug/list to view recent bug reports from the GitHub repository.
Use @bug/show <number> to view full details of a specific bug report.

Your report will be created as a GitHub issue for the development team
to review. Reports are capped per player per day; after each one the
game tells you how many you have left.

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
