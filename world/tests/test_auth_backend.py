"""The two protections lost by overriding ModelBackend (#2750, #2751).

`EmailAuthenticationBackend` overrides `authenticate` and `get_user` to
accept an email in place of a username. Overriding them means opting out
of two things ModelBackend does for free, and both were dropped
silently. Evennia's own `CaseInsensitiveModelBackend` defines only
`authenticate` and keeps the rest — the divergence was local here.
"""
from unittest import mock

from django.test import TestCase
from evennia.accounts.models import AccountDB

from web.utils.auth_backends import EmailAuthenticationBackend


class _Base(TestCase):
    def setUp(self):
        self.backend = EmailAuthenticationBackend()
        self.account = AccountDB.objects.create(
            username="tester2750", email="tester2750@example.com")
        self.account.set_password("correct horse")
        self.account.save()


class TestTheTimingChannelIsClosed(_Base):
    """Account enumeration is a stated in-scope threat: both doors give
    one generic message for "no such account" and "wrong password". But
    an unknown email skipped the password hash entirely, returning in
    ~0.5ms against ~457ms for a wrong password -- roughly 850x, which
    answers the question the message refuses to (#2750).

    Asserted structurally rather than by wall-clock, which would be
    flaky under load: the guarantee is "a hash is computed on every
    failing path", and that is what is checked.
    """

    def _hashes_burned(self, email, password):
        with mock.patch.object(AccountDB, "set_password") as burned:
            self.backend.authenticate(None, username=email, password=password)
            return burned.call_count

    def test_an_unknown_email_still_costs_a_hash(self):
        self.assertEqual(
            self._hashes_burned("nobody@example.com", "guess"), 1,
            "the miss path returned without hashing")

    def test_a_known_email_with_a_bad_password_hashes_too(self):
        """The comparison case: it must remain indistinguishable."""
        with mock.patch.object(AccountDB, "check_password",
                               return_value=False) as checked:
            self.backend.authenticate(None,
                                      username="tester2750@example.com",
                                      password="wrong")
        self.assertEqual(checked.call_count, 1)

    def test_a_correct_login_still_succeeds(self):
        """The pin: the mitigation must not break the happy path."""
        out = self.backend.authenticate(
            None, username="tester2750@example.com", password="correct horse")
        self.assertIsNotNone(out)
        self.assertEqual(out.pk, self.account.pk)

    def test_email_matching_stays_case_insensitive(self):
        out = self.backend.authenticate(
            None, username="TESTER2750@EXAMPLE.COM", password="correct horse")
        self.assertIsNotNone(out)


class TestDeactivationTakesEffect(_Base):
    """`get_user` runs on EVERY request carrying an auth session and is
    where a deactivated account's existing sessions die. The override
    dropped that gate, so unchecking "Active" -- the only lever this
    codebase surfaces -- did nothing to a browser already holding a
    cookie, for up to the full 14-day SESSION_COOKIE_AGE (#2751).

    It was dropped from `authenticate` too, so a deactivated account
    could also log in FRESH; the issue described only the session half.
    """

    def test_an_active_account_is_returned(self):
        self.assertIsNotNone(self.backend.get_user(self.account.pk))

    def test_a_deactivated_account_loses_its_session(self):
        self.account.is_active = False
        self.account.save()
        self.assertIsNone(self.backend.get_user(self.account.pk),
                          "the session survived deactivation")

    def test_a_deactivated_account_cannot_log_in_either(self):
        self.account.is_active = False
        self.account.save()
        self.assertIsNone(
            self.backend.authenticate(None,
                                      username="tester2750@example.com",
                                      password="correct horse"),
            "deactivation did not stop a fresh login")

    def test_an_unknown_id_is_still_none(self):
        self.assertIsNone(self.backend.get_user(99999999))
