"""The game's only login door throttles and logs.

Regression pin for #2557. `commands/unloggedin_email.py` does its own
credential check instead of routing through
`DefaultAccount.authenticate()`, so everything the framework wraps
around the password comparison was absent:

    LOGIN_THROTTLE.check(ip)     no
    LOGIN_THROTTLE.update(ip)    no
    logger.log_sec(...)          no
    account.at_failed_login()    no

`CMDSET_UNLOGGEDIN` makes this the ONLY login door -- Evennia's
`CmdUnconnectedConnect` is not in the cmdset -- so there was no second
path behaving correctly. Unlimited guesses at any rate, and not one line
in the security log to show for them.

Evennia's own throttle is reused rather than a new one invented: it is
the same object the web and guest doors share, so a bad actor cannot
dodge a lockout by switching doors.

The refusal MESSAGE stays generic for every reason -- enumeration is the
threat the original comment named, and a reason that varies by outcome
hands it straight back. The reason goes to the LOG, whose reader is
already trusted.
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.conf import settings

from commands.unloggedin_email import CmdEmailConnect


def _attempt(ip="203.0.113.9", email="nobody@example.com", pw="wrong"):
    cmd = CmdEmailConnect()
    cmd.caller = MagicMock()
    # the shape production hands the command: Evennia's portal resolves a
    # session's address to the host STRING. A tuple here hid #3732, where
    # `address[0]` keyed the throttle on the first character.
    cmd.caller.address = ip
    cmd.arglist = [email, pw]
    cmd.func()
    return " ".join(str(c.args[0]) for c in cmd.caller.msg.call_args_list
                    if c.args)


class TestTheOnlyLoginDoorHasAThrottle(TestCase):

    # Each test uses its OWN address. The throttle is a process-global
    # keyed on IP, and clearing it by poking at internals is a guess
    # about a structure this test does not own — a distinct address is
    # the same isolation without the guess.
    _next = iter(f"203.0.113.{n}" for n in range(10, 250))

    def _ip(self):
        return next(self._next)

    def test_repeated_failures_are_throttled(self):
        ip = self._ip()
        limit = int(settings.LOGIN_THROTTLE_LIMIT)
        for _ in range(limit):
            _attempt(ip=ip)
        self.assertIn("Too many login failures", _attempt(ip=ip))

    def test_a_failure_is_logged(self):
        import commands.unloggedin_email as mod

        # Checked before patching: on an unfixed tree the module has no
        # `logger` at all, and `patch` would raise AttributeError —
        # which reads like a broken harness rather than a door that
        # logs nothing.
        self.assertTrue(
            hasattr(mod, "logger"),
            "the login door imports no logger, so a failed login leaves "
            "no trace at all")
        with patch.object(mod, "logger") as log:
            _attempt(ip=self._ip())
        self.assertTrue(log.log_sec.called)
        self.assertIn("Authentication Failure",
                      str(log.log_sec.call_args.args[0]))

    def test_the_refusal_never_says_why(self):
        """Enumeration is the threat; the reason goes to the log."""
        said = _attempt(ip=self._ip())
        self.assertIn("Invalid email or password", said)
        for leak in ("unknown", "inactive", "bad password", "no account"):
            self.assertNotIn(leak, said.lower())

    # -- controls ----------------------------------------------------

    def test_a_fresh_address_is_not_throttled(self):
        """The control — a throttle that blocked everyone would pass
        the first test."""
        busy, fresh = self._ip(), self._ip()
        limit = int(settings.LOGIN_THROTTLE_LIMIT)
        for _ in range(limit + 1):
            _attempt(ip=busy)
        self.assertNotIn("Too many login failures", _attempt(ip=fresh))

    def test_a_missing_address_does_not_crash(self):
        cmd = CmdEmailConnect()
        cmd.caller = MagicMock()
        cmd.caller.address = None
        cmd.arglist = ["nobody@example.com", "wrong"]
        cmd.func()
        cmd.caller.msg.assert_called()


class TestTheKeyIsTheWholeAddress(TestCase):
    """#3732: `address[0]` of a string is one character. Two addresses that
    share a first digit must not share a throttle bucket, and the
    security log must name the whole address."""

    def test_a_neighbours_failures_do_not_lock_you_out(self):
        limit = int(settings.LOGIN_THROTTLE_LIMIT)
        for _ in range(limit + 1):
            _attempt(ip="198.51.100.77")
        out = _attempt(ip="198.51.100.78")
        self.assertNotIn("Too many login failures", out)

    def test_the_log_names_the_address_not_a_digit(self):
        with patch("commands.unloggedin_email.logger.log_sec") as sec:
            _attempt(ip="198.51.100.79")
        logged = " ".join(str(c.args[0]) for c in sec.call_args_list if c.args)
        self.assertIn("IP: 198.51.100.79", logged)
        self.assertNotIn("IP: 1)", logged)
