"""The website login door throttles and bans like the game door (#3734).

Django's LoginView has no lockout and Evennia's web package adds none, so
`EmailAuthenticationBackend` took unlimited guesses after the game door had
locked an attacker out, and never checked server bans. Both doors now key
Evennia's LOGIN_THROTTLE through `world.client_address.bucket`: IPv4 exact,
IPv6 by /64.
"""
from unittest import mock

from django.conf import settings
from django.test import TestCase
from evennia.accounts.models import AccountDB

from web.utils.auth_backends import EmailAuthenticationBackend
from world.client_address import bucket


def _request(ip):
    return mock.Mock(META={"HTTP_CF_CONNECTING_IP": ip} if ip else {})


class _Door(TestCase):
    def setUp(self):
        self.backend = EmailAuthenticationBackend()
        self.account = AccountDB.objects.create_user(
            username="webdoor", email="webdoor@example.com", password="right-one")

    def attempt(self, ip, password="wrong-one"):
        return self.backend.authenticate(_request(ip), username="webdoor@example.com", password=password)


class TestTheWebDoorThrottles(_Door):
    def test_the_right_password_still_works(self):
        self.assertIsNotNone(self.attempt("203.0.113.50", "right-one"))

    def test_repeated_failures_lock_the_address_out(self):
        limit = int(settings.LOGIN_THROTTLE_LIMIT)
        for _ in range(limit):
            self.assertIsNone(self.attempt("203.0.113.51"))
        # locked out now: even the right password is refused
        self.assertIsNone(self.attempt("203.0.113.51", "right-one"))

    def test_a_neighbour_is_not_locked_out(self):
        limit = int(settings.LOGIN_THROTTLE_LIMIT)
        for _ in range(limit + 1):
            self.attempt("203.0.113.52")
        self.assertIsNotNone(self.attempt("203.0.113.53", "right-one"))

    def test_no_trusted_address_means_no_throttle_but_still_a_password_check(self):
        self.assertIsNone(self.attempt(None))
        self.assertIsNotNone(self.attempt(None, "right-one"))


class TestIPv6IsBucketedByItsSlash64(TestCase):
    def test_ipv4_is_exact(self):
        self.assertEqual(bucket("203.0.113.9"), "203.0.113.9")

    def test_ipv6_rotating_inside_the_prefix_shares_a_bucket(self):
        a = bucket("2001:db8:1234:5678::1")
        b = bucket("2001:db8:1234:5678:ffff:ffff:ffff:fffe")
        self.assertEqual(a, b)
        self.assertEqual(a, "2001:db8:1234:5678::/64")

    def test_a_different_prefix_is_a_different_bucket(self):
        self.assertNotEqual(bucket("2001:db8:1234:5678::1"), bucket("2001:db8:1234:5679::1"))

    def test_nothing_is_empty(self):
        self.assertEqual(bucket(None), "")
        self.assertEqual(bucket(""), "")


class TestTheWebDoorHonoursBans(_Door):
    def test_a_banned_name_is_refused_with_the_right_password(self):
        with mock.patch("typeclasses.accounts.Account.is_banned", return_value=True):
            self.assertIsNone(self.attempt("203.0.113.60", "right-one"))

    def test_a_banned_name_is_logged_and_counted(self):
        with mock.patch("typeclasses.accounts.Account.is_banned", return_value=True), \
                mock.patch("web.utils.auth_backends.logger.log_sec") as sec, \
                mock.patch("web.utils.auth_backends.LOGIN_THROTTLE.update") as upd:
            self.attempt("203.0.113.61", "right-one")
        self.assertIn("Banned", " ".join(str(c.args[0]) for c in sec.call_args_list))
        self.assertTrue(upd.called)
