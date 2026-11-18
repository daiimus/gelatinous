# Bug Command Specification

## Overview

The `@bug` command lets players and staff file bug reports from inside the game. Each report becomes an issue in the GitHub repository. Players can also list recent reports and read any issue with its comments. Reports carry enough context to debug, but no private player data. The command is `CmdBug` in `commands/CmdBug.py`, added to the default cmdset in `commands/default_cmdsets.py`.

## Design Principles

1. **Accessible**: all players can report bugs. Nothing in the command is staff-gated (see "Read-only switches").
2. **Privacy-conscious**: no email addresses or sensitive player data are exposed.
3. **Context-rich**: each report captures the technical environment for debugging.
4. **Generous rate limiting**: a daily cap per account, 30 by default, and no cooldown between reports (trust players).
5. **Developer-friendly**: issues are created with proper formatting and labels.

---

## Command Syntax

| command | does |
|---|---|
| `@bug` | opens the interactive report workflow: title, category, description |
| `@bug/list` | shows the 10 most recent player reports from GitHub |
| `@bug/show <number>` or `@bug/show #<number>` | shows one issue in full, with all its comments |

- `bug` (without the @) works too.
- A plain `@bug` takes no text. `@bug <text>` only prints the usage line. There is no one-line report form: it encouraged poor reports.
- Every GitHub call runs in a background thread (`run_async`, through `_run_github_call`), so a slow GitHub does not freeze the game (#460). `/list` and `/show` first print a "Fetching..." line.
- Both configuration checks (see "Configuration") run before any switch is handled, so with bug reporting unconfigured `@bug/list` and `@bug/show` refuse too.

### `@bug` — filing a report

1. Enter a title of at least 10 characters. A blank title cancels the report.
2. Pick a category from a numbered menu.
3. Write the description in a multi-line editor. It must be at least 10 characters.

Before the menu opens, the daily cap is checked: a capped player is refused before the editor opens (#3367). See "Rate Limiting".

### `@bug/list`

Shows the 10 most recent reports (open and closed). Only issues labelled `player-reported` (those filed with `@bug`) are listed. `@bug/list` takes no count: any text after it is ignored, and it always shows the 10 newest player reports.

### `@bug/show <number>`

Shows any issue number in the repository, not only player reports. A leading `#` is accepted (`@bug/show 15` and `@bug/show #15` are the same). It shows:

- the issue title, state and category;
- creation and last-update dates;
- the full description;
- all comments from GitHub;
- a direct link to the issue.

An issue that does not exist gives "Issue #99999 not found." (for `@bug/show 99999`).

### Read-only switches

Nothing in this command is staff-gated. `CmdBug.locks` is `cmd:all()`, and neither `show_bug_list` nor `show_bug_detail` checks permissions, so every player can run `@bug/list` and `@bug/show`. The only switches are `list` and `show` (`CmdBug.switch_options`).

---

## GitHub Issue Format

### Issue Title

The player's title is used directly as the issue title, with no `[BUG]` prefix. `sanitize_title` escapes it (see "Input Validation") and caps it at 100 characters.

### Issue Labels

- `bug` (always applied)
- `player-reported` (always applied)
- `<category>`: always one of `combat`, `medical`, `movement`, `items`, `commands`, `web`, `world`, `social`, `system`, `other`. At the menu the digit or the word picks a category, and anything else picks `other`. `get_labels` adds the category only if it is one of these ten.

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

The commit is the short (7-character) hash of `master`, read once per server process from the git checkout (`.git/refs/heads/master`) and cached for the life of the process. The `git` command line (`git rev-parse --short HEAD`) is only a fallback, used if that file cannot be read. The hash is "unknown" if neither works (`get_git_commit_hash` and `_compute_git_commit_hash`).

### Privacy

**Included:**
- Account username (display name, not email)
- Current room #dbref (for context)
- Git commit hash (for version tracking)

**Excluded:**
- Email addresses
- Character names
- Character G.R.I.M. stats
- Room descriptive names (only #dbref)
- Account IP addresses
- Session information
- Internal account IDs (the reporter is named by account username only)
- Personal identifying information
- Timestamps (GitHub Issues tracks creation time automatically)

---

## GitHub API

- Issues are created by a `POST` to `https://api.github.com/repos/daiimus/gelatinous/issues` (`create_github_issue`). The `owner/repo` part comes from `settings.GITHUB_REPO`.
- The request authenticates with a personal access token from `settings.GITHUB_TOKEN` (`Authorization: token ...`), asks for the GitHub v3 JSON format, and sends the User-Agent `Gelatinous-MUD-Bug-Reporter`.
- The payload is the sanitized title, the formatted body (`format_issue_body`) and the labels from `get_labels`.
- The token needs the `public_repo` scope (issue creation in a public repository). If the repository were private it would need the full `repo` scope.

---

## Rate Limiting

- **Daily limit:** `settings.BUG_REPORT_DAILY_LIMIT` (default 30) reports per account per day, shared by all of that account's characters. It resets at midnight UTC, the same moment for every account.
- **Checked twice:** when `@bug` is typed, so a capped player is refused before the editor opens (#3367), and again at save (`_save_callback`), which takes the slot at once, before GitHub is called (#2526). If GitHub then fails, the slot is given back (`refund_report_count`), unless the count has already rolled over to a new day.
- **Reset:** `check_rate_limit` compares the stored date with today's UTC date. On a new day it sets the count to 0 and the date to today. The report is allowed while the count is below the limit. With the default, the 30th report of a day succeeds and the 31st is refused.
- **Cooldown:** none; there is no delay between reports.
- **Storage:** `account.db.bug_report_count` (reports today) and `account.db.bug_report_date` (the UTC date of that count).

### Rate limit messages

When the limit is reached (on typing `@bug`, and again at save), the player reads two lines (`func` and `_save_callback`):

```
You've reached the daily limit of {limit} bug reports.
The limit resets in {time}.
```

The limit is read from `BUG_REPORT_DAILY_LIMIT`, never written as a number (#3408). `{time}` comes from `get_time_until_reset`.

After **every** successful report (`_on_created`) the player reads:

```
You have {remaining} bug reports remaining today.
```

The number is yellow when it is 5 or less.

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

### Description Too Short

Saving the editor with an empty description, or one under 10 characters, gives "Details too short. Minimum 10 characters required." and "Bug report cancelled."; nothing is filed.

### Editor Cancellation

```
> @bug

[... workflow starts ...]

Opening editor...

> This is my bug description
> :q!

Bug report cancelled.
```

Only "Bug report cancelled" is shown. After a successful save, quitting the editor does not show it.

### Network Error

```
> @bug

[... workflow completes ...]

Creating detailed bug report (category: combat)...

Failed to create bug report: Request timed out. Please try again.
Please try again in a moment. If the problem persists, contact staff.
```

All text colors are readable: no dark gray is used; text is white or cyan.

---

## Menu and Editor

### The menu (EvMenu)

`start_detail_editor` runs the workflow on Evennia's EvMenu:

- `node_title` asks for the title (text input).
- `_validate_title_input` is a goto callable that validates the title. Validation steps use goto callables, not node functions.
- `node_category` is the numbered category menu.
- `node_open_editor` opens the editor for the description. The editor opens inside this last node, which then returns `None, None` to close the menu. There is no delay.
- The menu runs with `cmd_on_exit=None`, so no "look" command runs when the menu exits and none lands in the editor buffer.

### The editor (EvEditor)

The editor is stock Evennia and its commands are Evennia's. This command supplies callbacks, not key bindings, and does not subclass or override `EvEditor` (#2525).

- `loadfunc` returns an empty string (blank buffer).
- `savefunc` (`_save_callback`) creates the GitHub issue if the description is valid (at least 10 characters). It **returns a truthy value on submit**, which is the only thing that clears the editor's `_unsaved` flag; without it a second `:w` would file the report again (#2524).
- `quitfunc` (`_quit_callback`) shows the cancellation message only if save was not called.
- The flag `caller.ndb._bug_editor_saved` tracks whether save was called.

**Editor keys, as Evennia defines them:**

| key | effect |
|---|---|
| `:w` / `:wq` | save — submits the report |
| `:q!` | quit without saving — cancels |
| `:q` | quit; with an unsaved buffer this **prompts** *"Save before quitting?"*, and `SaveYesNoCmdSet` treats everything except a literal `no`/`n` as yes — a bare Enter included |

`:q` and `:q!` are not synonyms: `:q` with an unsaved buffer can submit the report. Making `:q` cancel outright would mean overriding a core Evennia class, which this project does not do.

---

## Errors

### Network failures

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

`sanitize_description` cuts the text at 5000 characters (adding "[Description truncated at 5000 characters]"), strips it, and puts a zero-width space after `@` in `@name` and after `#` in `#123`, so the public issue pings no one and links to no other issue (#2527). Markdown and HTML are left as typed. `sanitize_title` gives the title the same treatment and caps it at 100 characters. The category is checked against the list of ten (`get_labels`).

### Missing configuration

There are two gates in `CmdBug.func`: first `GITHUB_TOKEN`, then `GITHUB_REPO`. If either is missing or empty, the player reads two lines:

```
Bug reporting is not currently configured.
Please contact staff directly to report bugs.
```

Both gates run before any switch is handled, so `@bug`, `@bug/list` and `@bug/show` all refuse.

---

## Security

### Token

- The token is stored in `secret_settings.py`, which is gitignored.
- The token is never logged or shown in error messages.
- The token scope is the minimum required: `public_repo`; full `repo` only if the repository were private.

### Abuse

The daily cap per account prevents spam and abuse. There is no cooldown between reports (trust players).

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

`settings.py` declares one default, `BUG_REPORT_DAILY_LIMIT = 30` (#3408). It then imports `secret_settings.py`, which can override it. It gives no default for `GITHUB_TOKEN` or `GITHUB_REPO`, so both must be set in `secret_settings.py`. If either is missing, `@bug`, `@bug/list` and `@bug/show` all refuse. Every read of the limit is a plain settings lookup, and the help text names no number (#3408).

---

## In-Game Help

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

The workflow itself guides players toward good reports: the 10-character title minimum, the numbered category menu, the editor instructions shown before the editor opens, and the 10-character description minimum.

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

## Unbuilt

Not currently planned; these could be added in the future if needed. None exists today: the only switches are `list` and `show`.

- 📋 UNBUILT (no issue) — `@bug/close <issue_number>`: close an issue from in-game (admin).
- 📋 UNBUILT (no issue) — `@bug/comment <issue_number> <comment>`: add a comment to an issue (admin).
- 📋 UNBUILT (no issue) — `@bug/search <query>`: search existing issues (admin; not placed in any phase).
- 📋 UNBUILT (no issue) — Duplicate detection before creating issues.
- 📋 UNBUILT (no issue) — Issue status tracking/notifications for players.
- 📋 UNBUILT (no issue) — Player notification when their bugs are resolved.
- 📋 UNBUILT (no issue) — Attachment support (command history, combat logs).
- 📋 UNBUILT (no issue) — Integration with staff channels for new bug alerts.

---

## Related

- `commands/CmdBug.py` — the command (`CmdBug`).
