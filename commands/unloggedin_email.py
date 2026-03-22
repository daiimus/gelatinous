"""
Custom email-based login commands for gelatinous
Adapted from evennia.contrib.base_systems.email_login
"""

from django.conf import settings
from evennia.accounts.models import AccountDB
from evennia.commands.default.muxcommand import MuxCommand
from evennia.utils import class_from_module, utils
from evennia.server.models import ServerConfig


class CmdEmailConnect(MuxCommand):
    """
    Connect to the game using email address.

    Usage (at login screen):
        connect <email@address.com> <password>

    Use your registered email address to connect.
    """

    key = "connect"
    aliases = ["conn", "con", "co"]
    locks = "cmd:all()"

    def func(self):
        """Email-based connection logic"""
        session = self.caller
        address = session.address
        arglist = self.arglist

        if not arglist or len(arglist) < 2:
            session.msg("\n\r Usage: connect <email@address.com> <password>")
            return
            
        email = arglist[0].lower().strip()
        password = arglist[1]

        # Look up account by email and verify password.
        # Use a generic error message for both "no account" and "wrong password"
        # to prevent user enumeration attacks.
        account = AccountDB.objects.filter(email__iexact=email).first()

        if not account or not account.check_password(password):
            session.msg("Invalid email or password.")
            return

        # Check IP and/or name bans
        bans = ServerConfig.objects.conf("server_bans")
        if bans and (
            any(tup[0] == account.username for tup in bans)
            or any(tup[2].match(address[0]) for tup in bans if tup[2])
        ):
            session.msg("|rYou have been banned and cannot continue.|n")
            session.execute_cmd("quit")
            return

        # Login successful
        session.sessionhandler.login(session, account)


class CmdEmailCreate(MuxCommand):
    """
    Create a new account with email only.

    Usage (at login screen):
        create <email@address.com> <password>

    Creates a new account using only your email address.
    Character creation happens after login.
    """

    key = "create"
    aliases = ["cre", "cr"]
    locks = "cmd:all()"

    def func(self):
        """Email-only account creation"""
        session = self.caller
        address = session.address
        arglist = self.arglist

        # Check if account registration is enabled
        if not settings.NEW_ACCOUNT_REGISTRATION_ENABLED:
            session.msg("|rAccount creation is currently disabled.|n")
            session.msg("Contact an administrator if you need an account.")
            return

        if not arglist or len(arglist) < 2:
            session.msg("\n\r Usage: create <email@address.com> <password>")
            return
            
        email = arglist[0].lower().strip()
        password = arglist[1]
        
        # Validate email format
        if not utils.validate_email_address(email):
            session.msg(f"'{email}' is not a valid email address.")
            return

        # Check if email already exists
        existing_account = AccountDB.objects.filter(email__iexact=email).first()
        if existing_account:
            session.msg(f"An account with email '{email}' already exists.")
            session.msg("Use 'connect' to log in to your existing account.")
            return

        # Generate username from email (for internal use)
        # This is just for the database - users never see/use this
        base_username = email.split('@')[0]
        username = base_username
        counter = 1
        
        # Ensure username uniqueness (though users won't see this)
        while AccountDB.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1

        # Create account
        Account = class_from_module(settings.BASE_ACCOUNT_TYPECLASS)
        account, errors = Account.create(
            username=username,  # Internal identifier
            email=email,        # What users actually use
            password=password, 
            ip=address
        )
        
        if account:
            session.msg(f"|gAccount created successfully!|n")
            session.msg(f"You can now connect with: |wconnect {email} <password>|n")
            session.msg("Character creation will happen after you log in.")
        else:
            session.msg(f"|rAccount creation failed:|n {'; '.join(errors)}")


# Command set to replace the default unloggedin commands
from evennia.commands.cmdset import CmdSet

class UnloggedinEmailCmdSet(CmdSet):
    """
    Command set for unloggedin users with email-based authentication.
    """
    key = "UnloggedinEmail"
    priority = 0

    def at_cmdset_creation(self):
        """Populate the command set."""
        self.add(CmdEmailConnect())
        self.add(CmdEmailCreate())
        
        # Keep other default unloggedin commands
        from evennia.commands.default.unloggedin import (
            CmdUnconnectedQuit, CmdUnconnectedLook, CmdUnconnectedHelp
        )
        self.add(CmdUnconnectedQuit())
        self.add(CmdUnconnectedLook())
        self.add(CmdUnconnectedHelp())