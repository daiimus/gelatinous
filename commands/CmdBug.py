"""
Bug reporting command for creating GitHub issues directly from in-game.

This module provides the @bug command that allows players to submit bug reports
that automatically create GitHub issues in the repository. Includes rate limiting,
input validation, and privacy-conscious reporting.
"""

from evennia.commands.default.muxcommand import MuxCommand
from django.conf import settings
from datetime import datetime, timedelta, timezone
import requests
import json


class CmdBug(MuxCommand):
    """
    Report a bug to the development team.
    
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
    to review. All players can submit up to 30 bug reports per day.
    
    Be clear and descriptive - good bug reports help us fix issues faster!
    """
    
    key = "@bug"
    aliases = ["bug"]
    locks = "cmd:all()"
    help_category = "General"
    switch_options = ("list", "show")
    
    def func(self):
        """Execute the bug report command."""
        caller = self.caller
        account = caller.account
        
        # Check if bug reporting is configured
        if not hasattr(settings, 'GITHUB_TOKEN') or not settings.GITHUB_TOKEN:
            caller.msg("|rBug reporting is not currently configured.|n")
            caller.msg("Please contact staff directly to report bugs.")
            return
        
        if not hasattr(settings, 'GITHUB_REPO') or not settings.GITHUB_REPO:
            caller.msg("|rBug reporting is not currently configured.|n")
            caller.msg("Please contact staff directly to report bugs.")
            return
        
        # Handle /list switch
        if "list" in self.switches:
            self.show_bug_list(caller)
            return
        
        # Handle /show switch
        if "show" in self.switches:
            if not self.args:
                caller.msg("|yUsage: @bug/show <number>|n")
                caller.msg("Example: @bug/show 15")
                return
            
            # Strip # prefix if present
            arg = self.args.strip()
            if arg.startswith('#'):
                arg = arg[1:]
            
            try:
                issue_number = int(arg)
            except ValueError:
                caller.msg("|rInvalid issue number. Please provide a number.|n")
                return
            
            self.show_bug_detail(caller, issue_number)
            return
        
        # Any other arguments show usage
        if self.args:
            caller.msg("|yUsage:|n @bug  or  @bug/list")
            return
        
        # Open the detailed bug report workflow
        self.start_detail_editor(caller)
    
    def check_rate_limit(self, account):
        """Check if account is within rate limit."""
        today = datetime.now(timezone.utc).date()
        last_date = account.db.bug_report_date
        
        # Reset counter if it's a new day
        if last_date != today:
            account.db.bug_report_count = 0
            account.db.bug_report_date = today
        
        count = account.db.bug_report_count or 0
        limit = getattr(settings, 'BUG_REPORT_DAILY_LIMIT', 30)
        
        return count < limit
    
    def increment_report_count(self, account):
        """Increment the bug report counter for the account."""
        today = datetime.now(timezone.utc).date()
        
        if account.db.bug_report_date != today:
            account.db.bug_report_count = 1
            account.db.bug_report_date = today
        else:
            account.db.bug_report_count = (account.db.bug_report_count or 0) + 1
    
    def get_time_until_reset(self, account):
        """Get human-readable time until rate limit resets."""
        now = datetime.now(timezone.utc)
        tomorrow = datetime(now.year, now.month, now.day, tzinfo=timezone.utc) + timedelta(days=1)
        
        delta = tomorrow - now
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        
        if hours > 0:
            return f"{hours} hours, {minutes} minutes"
        else:
            return f"{minutes} minutes"
    
    def gather_context(self, caller):
        """Gather environmental context for the bug report."""
        account = caller.account
        location = caller.location
        
        # Get git commit hash
        commit_hash = self.get_git_commit_hash()
        
        # Get location info
        if location:
            location_dbref = f"#{location.id}"
        else:
            location_dbref = "None"
        
        context = {
            'account_username': account.key,
            'location_dbref': location_dbref,
            'commit_hash': commit_hash,
            'server': 'play.gel.monster'
        }
        
        return context
    
    def get_git_commit_hash(self):
        """Get the current git commit hash."""
        try:
            import os
            
            # In Docker, the game is mounted at /usr/src/game
            # Try multiple possible paths
            possible_paths = [
                '/usr/src/game/.git/refs/heads/master',  # Docker absolute path
                os.path.join(os.getcwd(), '.git', 'refs', 'heads', 'master'),  # From current working dir
            ]
            
            # Also try calculating from this file's location
            try:
                git_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                possible_paths.append(os.path.join(git_dir, '.git', 'refs', 'heads', 'master'))
            except:
                pass
            
            # Try each possible path
            for ref_file in possible_paths:
                if os.path.exists(ref_file):
                    with open(ref_file, 'r') as f:
                        full_hash = f.read().strip()
                        # Return short hash (first 7 characters)
                        return full_hash[:7] if full_hash else "unknown"
            
            # Fallback: try git command if available
            try:
                import subprocess
                result = subprocess.run(
                    ['git', 'rev-parse', '--short', 'HEAD'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    return result.stdout.strip()
            except Exception:
                pass
                
        except Exception:
            pass
        
        return "unknown"
    
    def sanitize_description(self, text):
        """Sanitize user input to prevent issues."""
        # Limit length
        if len(text) > 5000:
            text = text[:5000] + "\n\n[Description truncated at 5000 characters]"
        
        # Basic sanitization - preserve most formatting but prevent extreme cases
        text = text.strip()
        
        return text
    
    def create_github_issue(self, description, context):
        """
        Create a GitHub issue via the API.
        
        Returns:
            tuple: (success: bool, result: dict or error_message: str)
        """
        # Sanitize description
        description = self.sanitize_description(description)
        
        # Get title - use provided title or extract from description
        title = context.get('title')
        if title:
            # Title was provided separately (from detail editor)
            title = title[:100]  # Truncate if too long
        else:
            # Extract title from description (for regular @bug command)
            title = description.split('\n')[0][:100]  # First line, truncated
        
        # Build issue body
        body = self.format_issue_body(description, context)
        
        # Prepare API request
        url = f"https://api.github.com/repos/{settings.GITHUB_REPO}/issues"
        
        headers = {
            "Authorization": f"token {settings.GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Gelatinous-MUD-Bug-Reporter"
        }
        
        payload = {
            "title": title,
            "body": body,
            "labels": self.get_labels(context)
        }
        
        # Make API request
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            response.raise_for_status()
            
            # Success
            return (True, response.json())
            
        except requests.exceptions.Timeout:
            return (False, "Request timed out. Please try again.")
        
        except requests.exceptions.ConnectionError:
            return (False, "Unable to connect to GitHub. Please try again later.")
        
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            
            if status_code == 401:
                return (False, "GitHub authentication failed. Please contact staff.")
            elif status_code == 403:
                return (False, "Rate limited by GitHub. Please try again later.")
            elif status_code == 422:
                return (False, "Invalid request data. Please contact staff.")
            else:
                return (False, f"GitHub API error (status {status_code})")
        
        except Exception as e:
            return (False, f"Unexpected error: {str(e)}")
    
    def show_bug_list(self, caller):
        """Show list of recent bug reports from GitHub."""
        repo = settings.GITHUB_REPO
        token = settings.GITHUB_TOKEN
        
        url = f"https://api.github.com/repos/{repo}/issues"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        params = {
            "state": "all",  # Show both open and closed
            "labels": "player-reported",
            "per_page": 10,
            "sort": "created",
            "direction": "desc"
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code != 200:
                caller.msg(f"|rFailed to fetch bug list: HTTP {response.status_code}|n")
                return
            
            issues = response.json()
            
            if not issues:
                caller.msg("\n|yNo bug reports found.|n")
                return
            
            # Display header
            caller.msg("\n|c=== Recent Bug Reports ===|n\n")
            
            for issue in issues:
                number = issue['number']
                title = issue['title']
                state = issue['state']
                created = issue['created_at'][:10]  # Just date
                url = issue['html_url']
                
                # Color code by state
                if state == "open":
                    state_display = "|gOPEN|n"
                else:
                    state_display = "|wCLOSED|n"
                
                # Extract category from labels if present
                labels = [label['name'] for label in issue.get('labels', [])]
                category = None
                for label in labels:
                    if label in {'combat', 'medical', 'movement', 'items', 'commands',
                                'web', 'world', 'social', 'system', 'other'}:
                        category = label.capitalize()
                        break
                
                category_display = f" |y[{category}]|n" if category else ""
                
                caller.msg(f"|w#{number}|n {state_display}{category_display} - {title}")
                caller.msg(f"  |wCreated: {created}|n")
                caller.msg(f"  |c{url}|n\n")
            
            caller.msg("|wShowing 10 most recent reports. Visit GitHub for full history.|n\n")
            
        except requests.exceptions.Timeout:
            caller.msg("|rRequest timed out. Please try again later.|n")
        except requests.exceptions.RequestException as e:
            caller.msg(f"|rFailed to fetch bug list: {str(e)}|n")
        except Exception as e:
            caller.msg(f"|rUnexpected error: {str(e)}|n")
    
    def show_bug_detail(self, caller, issue_number):
        """Show detailed information about a specific bug report."""
        repo = settings.GITHUB_REPO
        token = settings.GITHUB_TOKEN
        
        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        try:
            # Fetch the issue
            issue_url = f"https://api.github.com/repos/{repo}/issues/{issue_number}"
            response = requests.get(issue_url, headers=headers, timeout=10)
            
            if response.status_code == 404:
                caller.msg(f"|rIssue #{issue_number} not found.|n")
                return
            
            response.raise_for_status()
            issue = response.json()
            
            # Fetch comments
            comments_url = issue['comments_url']
            comments_response = requests.get(comments_url, headers=headers, timeout=10)
            comments_response.raise_for_status()
            comments = comments_response.json()
            
            # Display issue details
            title = issue['title']
            state = issue['state'].upper()
            state_display = "|g[OPEN]|n" if state == "OPEN" else "|r[CLOSED]|n"
            created = issue['created_at'][:10]
            updated = issue['updated_at'][:10]
            body = issue.get('body', 'No description provided.')
            url = issue['html_url']
            
            # Extract labels
            labels = [label['name'] for label in issue.get('labels', [])]
            category = None
            for label in labels:
                if label in {'combat', 'medical', 'movement', 'items', 'commands',
                            'web', 'world', 'social', 'system', 'other'}:
                    category = label.capitalize()
                    break
            
            # Build display
            caller.msg(f"\n|w{'=' * 70}|n")
            caller.msg(f"|wIssue #{issue_number}|n {state_display}")
            caller.msg(f"|w{'=' * 70}|n\n")
            
            caller.msg(f"|wTitle:|n {title}")
            if category:
                caller.msg(f"|wCategory:|n |y{category}|n")
            caller.msg(f"|wCreated:|n {created}")
            caller.msg(f"|wUpdated:|n {updated}")
            caller.msg(f"|wURL:|n |c{url}|n\n")
            
            caller.msg(f"|w{'-' * 70}|n")
            caller.msg(f"|wDescription:|n\n")
            caller.msg(body)
            caller.msg(f"\n|w{'-' * 70}|n")
            
            # Display comments
            if comments:
                caller.msg(f"\n|wComments ({len(comments)}):|n\n")
                for i, comment in enumerate(comments, 1):
                    author = comment['user']['login']
                    created = comment['created_at'][:10]
                    comment_body = comment['body']
                    
                    caller.msg(f"|w{i}. {author}|n |c({created})|n")
                    caller.msg(f"{comment_body}\n")
            else:
                caller.msg(f"\n|wNo comments yet.|n\n")
            
            caller.msg(f"|w{'=' * 70}|n\n")
            
        except requests.exceptions.Timeout:
            caller.msg("|rRequest timed out. Please try again later.|n")
        except requests.exceptions.RequestException as e:
            caller.msg(f"|rFailed to fetch bug details: {str(e)}|n")
        except Exception as e:
            caller.msg(f"|rUnexpected error: {str(e)}|n")
    
    def format_issue_body(self, description, context):
        """Format the GitHub issue body with context."""
        category = context.get('category', None)
        category_display = category.capitalize() if category else "Uncategorized"
        
        body = f"""**Reported By:** {context['account_username']}
**Location:** {context['location_dbref']}

**Category:** {category_display}

---

## Description

{description}

---

## Technical Environment

- **Server:** {context['server']}
- **Commit:** {context['commit_hash']}
"""
        
        return body
    
    def get_labels(self, context):
        """Get GitHub labels for the issue based on category."""
        labels = ["bug", "player-reported"]
        
        category = context.get('category')
        if category and category in {'combat', 'medical', 'movement', 'items', 'commands', 
                                      'web', 'world', 'social', 'system', 'other'}:
            labels.append(category)
        
        return labels
    
    def start_detail_editor(self, caller):
        """Start the multi-line detail editor for bug reports using EvMenu."""
        from evennia.utils.evmenu import EvMenu
        from evennia.utils.eveditor import EvEditor
        
        # Store a reference to self for callbacks
        cmd_instance = self
        
        def _validate_title_input(caller, raw_string, **kwargs):
            """Process and validate title input (goto callable, not a node)."""
            title = raw_string.strip()
            
            if not title:
                caller.msg("|yBug report cancelled.|n")
                return None  # Exit menu
            
            if len(title) < 10:
                caller.msg("|rTitle too short. Please provide at least 10 characters.|n")
                caller.msg("|yBug report cancelled.|n")
                return None  # Exit menu
            
            # Store title in menu session
            caller.ndb._evmenu.bug_title = title
            
            # Move to category node
            return "node_category"
        
        def node_title(caller, raw_string, **kwargs):
            """EvMenu node to get the bug title."""
            text = "\n|c=== Detailed Bug Report ===|n\n"
            text += "\nProvide a short title for the bug (minimum 10 characters):"
            
            options = (
                {
                    "key": "_default",
                    "goto": _validate_title_input  # Callable, not string
                },
            )
            
            return text, options
        
        def node_category(caller, raw_string, **kwargs):
            """EvMenu node to select category."""
            title = caller.ndb._evmenu.bug_title
            
            text = f"\n|gTitle:|n {title}\n"
            text += "\n|ySelect a category:|n"
            
            options = (
                {"key": ("1", "combat"), "desc": "Combat", "goto": ("node_open_editor", {"category": "combat"})},
                {"key": ("2", "medical"), "desc": "Medical", "goto": ("node_open_editor", {"category": "medical"})},
                {"key": ("3", "movement"), "desc": "Movement", "goto": ("node_open_editor", {"category": "movement"})},
                {"key": ("4", "items"), "desc": "Items/Inventory", "goto": ("node_open_editor", {"category": "items"})},
                {"key": ("5", "commands"), "desc": "Commands", "goto": ("node_open_editor", {"category": "commands"})},
                {"key": ("6", "web"), "desc": "Web Interface", "goto": ("node_open_editor", {"category": "web"})},
                {"key": ("7", "world"), "desc": "World/Environment", "goto": ("node_open_editor", {"category": "world"})},
                {"key": ("8", "social"), "desc": "Social/Communication", "goto": ("node_open_editor", {"category": "social"})},
                {"key": ("9", "system"), "desc": "System/Performance", "goto": ("node_open_editor", {"category": "system"})},
                {"key": ("0", "other"), "desc": "Other", "goto": ("node_open_editor", {"category": "other"})},
                {"key": "_default", "goto": ("node_open_editor", {"category": "other"})},
            )
            
            return text, options
        
        def node_open_editor(caller, raw_string, **kwargs):
            """Open the EvEditor for detailed description."""
            title = caller.ndb._evmenu.bug_title
            category = kwargs.get("category", "other")
            
            # Store category
            caller.ndb._evmenu.bug_category = category
            
            # Flag to track if save was called
            caller.ndb._bug_editor_saved = False
            
            # Show confirmation and instructions
            caller.msg(f"\n|gTitle:|n {title}")
            caller.msg(f"|gCategory:|n {category.capitalize()}")
            caller.msg("\n|yNow provide detailed information:|n")
            caller.msg("  - What you were trying to do")
            caller.msg("  - What you expected to happen")
            caller.msg("  - What actually happened")
            caller.msg("  - Steps to reproduce (if possible)")
            caller.msg("\n|yEditor Commands:|n")
            caller.msg("  |w:w|n or |w:wq|n - Save and submit bug report")
            caller.msg("  |w:q|n or |w:q!|n - Cancel without submitting")
            caller.msg("  |w:h|n - Show editor help")
            caller.msg("\n|yOpening editor...|n\n")
            
            # Define EvEditor save callback
            def _save_callback(caller, buffer):
                """Called when the player saves the editor."""
                # Mark that save was called
                caller.ndb._bug_editor_saved = True
                
                if isinstance(buffer, str):
                    details = buffer.strip()
                else:
                    details = "\n".join(buffer).strip()
                
                if not details or len(details) < 10:
                    caller.msg("|rDetails too short. Minimum 10 characters required.|n")
                    caller.msg("|yBug report cancelled.|n")
                    return
                
                # Check rate limit
                account = caller.account
                if not cmd_instance.check_rate_limit(account):
                    remaining_time = cmd_instance.get_time_until_reset(account)
                    caller.msg("|rYou've reached the daily limit of 30 bug reports.|n")
                    caller.msg(f"The limit resets in {remaining_time}.")
                    return
                
                # Get environment context
                context = cmd_instance.gather_context(caller)
                context['category'] = category
                context['title'] = title
                
                # Create GitHub issue
                caller.msg(f"\n|gCreating detailed bug report (category: |c{category}|g)...|n")
                
                success, result = cmd_instance.create_github_issue(details, context)
                
                if success:
                    issue_url = result.get('html_url', '')
                    issue_number = result.get('number', '?')
                    
                    # Increment bug report counter
                    cmd_instance.increment_report_count(account)
                    remaining = 30 - account.db.bug_report_count
                    
                    caller.msg(f"\n|g✓|n Issue created: |c{issue_url}|n")
                    caller.msg("\nThank you for the detailed report! The development team will investigate.")
                    
                    if remaining <= 5:
                        caller.msg(f"You have |y{remaining}|n bug reports remaining today.")
                    else:
                        caller.msg(f"You have {remaining} bug reports remaining today.")
                else:
                    error_msg = result
                    caller.msg(f"\n|rFailed to create bug report:|n {error_msg}")
                    caller.msg("|yPlease try again in a moment. If the problem persists, contact staff.|n")
            
            def _quit_callback(caller):
                """Called when the player quits the editor."""
                # Only show cancellation message if save wasn't called
                if not getattr(caller.ndb, '_bug_editor_saved', False):
                    caller.msg("|yBug report cancelled.|n")
                # Clean up flag
                if hasattr(caller.ndb, '_bug_editor_saved'):
                    del caller.ndb._bug_editor_saved
            
            # Open the EvEditor
            EvEditor(caller, 
                    loadfunc=lambda caller: "",
                    savefunc=_save_callback,
                    quitfunc=_quit_callback,
                    key="bug_report_editor",
                    persistent=False)
            
            # Return None to exit the menu
            return None, None
        
        # Start the EvMenu
        EvMenu(caller, 
               {"node_title": node_title,
                "node_category": node_category,
                "node_open_editor": node_open_editor},
               startnode="node_title",
               cmd_on_exit=None)  # Don't run 'look' when menu exits
