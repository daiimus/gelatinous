"""
Custom email-based login commands for gelatinous
Adapted from evennia.contrib.base_systems.email_login
"""

from django.conf import settings
from evennia.accounts.accounts import LOGIN_THROTTLE
from evennia.accounts.models import AccountDB
from evennia.utils import logger

from world.client_address import bucket
from evennia.commands.default.muxcommand import MuxCommand
from evennia.utils import class_from_module, utils


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
        # `session.address` is the HOST STRING Evennia's portal resolved
        # (telnet, websocket and ssh all hand init_session a str). It was
        # indexed `[0]` here, so the throttle and the security log keyed
        # on the first CHARACTER of the address: five failures from any
        # 1xx address locked out every 1xx player, and an IP ban could
        # never match (#3732). Evennia's own doors pass the whole string.
        ip = str(address) if address else ""
        key = bucket(ip)   # IPv4 exact, IPv6 by /64; the same key the web door uses (#3734)

        # THE THROTTLE, and the security log (#2557).
        #
        # This door does its own credential check instead of routing
        # through `DefaultAccount.authenticate()`, so everything the
        # framework wraps around the password comparison was absent --
        # and `CMDSET_UNLOGGEDIN` makes this the ONLY login door, so
        # there was no second path behaving correctly. Unlimited guesses
        # at any rate, and not one line in the security log to show for
        # them.
        #
        # Reusing Evennia's own throttle rather than inventing one: it
        # is the same object the web door and the guest door already
        # share, so a bad actor cannot dodge a lockout by switching
        # doors.
        if key and LOGIN_THROTTLE.check(key):
            session.msg(
                "Too many login failures. Please wait a while and try "
                "again."
            )
            logger.log_sec(f"Authentication Denied (Throttled): {email} "
                           f"(IP: {ip}).")
            return

        # An IP ban is refused BEFORE any credential work, logged and
        # counted, as Evennia's own door does; it used to be checked
        # after the password hash, unlogged, so a banned address could
        # grind hashes forever and only learn of the ban on a correct
        # password (#3736). `is_banned` is Evennia's own check, which
        # also lowercases names so a mixed-case username can be banned.
        from typeclasses.accounts import Account
        if ip and Account.is_banned(ip=ip):
            self._banned(session, email, ip, key)
            return

        # Look up account by email and verify password.
        # Use a generic error message for both "no account" and "wrong password"
        # to prevent user enumeration attacks.
        account = AccountDB.objects.filter(email__iexact=email).first()

        if account is None:
            # Spend the same work a real password check costs. `or`
            # short-circuits, so an unknown email never reached
            # check_password and returned in ~0.5ms against ~457ms for a
            # wrong password — roughly 850x, which answers the question
            # the generic message below deliberately refuses to. The
            # comment above states enumeration is the threat; the
            # message channel was closed and the timing channel was not
            # (#2750).
            try:
                AccountDB().set_password(password)
            except Exception:  # noqa: BLE001 — a mitigation is not a fault
                pass
            self._deny(session, email, ip, "unknown email")
            return

        if Account.is_banned(username=account.username):
            self._banned(session, email, ip, key)
            return

        if not account.check_password(password):
            self._deny(session, email, ip, "bad password", account=account)
            return

        # A deactivated account is refused here too. The web door gets
        # this from Django's `user_can_authenticate`; this door does not
        # go through a Django backend at all (#2557), so it has to say
        # so itself — otherwise "Active" unchecked stops the website and
        # not the game (#2751).
        if not getattr(account, "is_active", True):
            self._deny(session, email, ip, "inactive", account=account)
            return

        # Login successful
        logger.log_sec(f"Authentication Success: {account} (IP: {ip}).")
        session.sessionhandler.login(session, account)

    def _banned(self, session, email, ip, key):
        """A banned address or name: refused, logged, and counted against
        the throttle, exactly as Evennia's own door does."""
        logger.log_sec(f"Authentication Denied (Banned): {email} (IP: {ip}).")
        if key:
            LOGIN_THROTTLE.update(key, "Too many sightings of banned artifact.")
        session.msg("|rYou have been banned and cannot continue.|n")
        session.execute_cmd("quit")

    def _deny(self, session, email, ip, reason, account=None):
        """One refusal: same message, logged, and counted.

        The message stays generic for every reason -- enumeration is the
        threat the original comment named, and a reason that varies by
        outcome hands it straight back. The LOG is where the reason
        goes, because that reader is already trusted (#2557).
        """
        logger.log_sec(
            f"Authentication Failure ({reason}): {email} (IP: {ip}).")
        key = bucket(ip)
        if key:
            LOGIN_THROTTLE.update(key, "Too many authentication failures.")
        if account is not None:
            # The framework's post-failure hook, which this door never
            # reached. An account that wants to notice its own failed
            # logins can.
            try:
                account.at_failed_login(session)
            except Exception:  # noqa: BLE001 — a hook never blocks a refusal
                logger.log_trace("at_failed_login hook failed")
        session.msg("Invalid email or password.")


def derive_username(email):
    """A free database username derived from *email*'s local part.

    Users never see or type this -- `create` takes only an email and a
    password -- so its only job is to be unique.

    __iexact, because the constraint this guards is case-INSENSITIVE:
    EvenniaUsernameAvailabilityValidator, run inside Account.create,
    filters on username__iexact. The email arrives lowercased, so a
    case-SENSITIVE test could never collide with a mixed-case account:
    the loop exited after zero iterations and Account.create then
    rejected the very name it was written to avoid, naming a username
    the user never supplied and cannot override. Nine of the 24 live
    accounts have mixed-case usernames, each permanently blocking a
    distinct unused email (#2560).

    Extracted from the command body so the loop can be tested against
    the real database rather than against a copy of itself.
    """
    base_username = email.split('@')[0]
    username = base_username
    counter = 1
    while AccountDB.objects.filter(username__iexact=username).exists():
        username = f"{base_username}_{counter}"
        counter += 1
    return username


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
        username = derive_username(email)

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