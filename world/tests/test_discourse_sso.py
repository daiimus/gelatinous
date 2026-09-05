"""Malformed SSO input must yield a clean 400, never a 500 (#2743).

The view says so itself, in the comment above its only try/except:

    Deliberate guard: the payload is attacker-controllable external
    input -- anything malformed gets a clean HTTP 400 (logged with
    traceback), never a 500.

`verify_payload` runs ABOVE that guard. `hmac.compare_digest` refuses
str arguments that are not ASCII-only and raises TypeError, so a `sig`
query parameter containing any non-ASCII character produced an unhandled
exception and an HTTP 500 with a traceback in the web log.

Not an authentication bypass: the failure is on the REJECT path, so no
SSO payload is ever signed or returned.
"""
import hashlib
import hmac
from unittest import TestCase, mock

import web.website.views.discourse_sso as sso

SECRET = "test-sso-secret"
PAYLOAD = "bm9uY2U9YWJjZGVm"


def _good_signature(payload=PAYLOAD, secret=SECRET):
    return hmac.new(secret.encode("utf-8"), payload.encode("utf-8"),
                    hashlib.sha256).hexdigest()


class TestMalformedSignaturesAreRejectedNotRaised(TestCase):
    def setUp(self):
        patcher = mock.patch.object(sso, "get_discourse_sso_secret",
                                    return_value=SECRET)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_a_non_ascii_signature_is_false_not_a_crash(self):
        for sig in ("café", "你好", "ÿ" * 64, "sig "):
            with self.subTest(sig=sig):
                self.assertFalse(sso.verify_payload(PAYLOAD, sig))

    def test_ascii_junk_is_still_just_false(self):
        self.assertFalse(sso.verify_payload(PAYLOAD, "deadbeef"))

    def test_an_empty_signature_is_false(self):
        self.assertFalse(sso.verify_payload(PAYLOAD, ""))

    def test_a_non_string_signature_is_false(self):
        for sig in (None, 12345, [], {}):
            with self.subTest(sig=sig):
                self.assertFalse(sso.verify_payload(PAYLOAD, sig))

    def test_a_valid_signature_still_verifies(self):
        """The pin that matters: hardening the reject path must not
        break the accept path, or SSO login stops working entirely."""
        self.assertTrue(sso.verify_payload(PAYLOAD, _good_signature()))

    def test_a_tampered_signature_is_rejected(self):
        good = _good_signature()
        flipped = good[:-1] + ("0" if good[-1] != "0" else "1")
        self.assertFalse(sso.verify_payload(PAYLOAD, flipped))

    def test_a_signature_for_a_different_payload_is_rejected(self):
        self.assertFalse(
            sso.verify_payload(PAYLOAD, _good_signature("b3RoZXI=")))

    def test_a_signature_from_a_different_secret_is_rejected(self):
        self.assertFalse(
            sso.verify_payload(PAYLOAD, _good_signature(secret="wrong")))


class TestNoSecretMeansNoVerification(TestCase):
    def test_an_unconfigured_secret_verifies_nothing(self):
        with mock.patch.object(sso, "get_discourse_sso_secret",
                               return_value=""):
            self.assertFalse(sso.verify_payload(PAYLOAD, _good_signature()))


class TestTheRedirectIsRebuiltFaithfully(TestCase):
    """The redirect is rebuilt from the SETTINGS host rather than the
    caller's -- correct intent, wrong accessor. `urlparse(...).hostname`
    is normalised for COMPARISON: it lowercases, strips the port, and
    strips the brackets from an IPv6 literal.

    So a self-hosted forum on a non-default port was redirected to the
    default port instead (the browser lands somewhere that is not the
    forum), and an IPv6 host produced a syntactically invalid URL
    (#2745).

    The two halves had to move together: Django's
    `url_has_allowed_host_and_scheme` compares the URL's full host:port
    against `allowed_hosts`, so restoring the port while leaving a bare
    hostname in the allowlist would have made the final gate reject
    every custom-port redirect. Verified: bare-host allowlist vs a
    ported URL returns False.
    """

    def _rebuild(self, discourse_url, return_url):
        """Mirror of the view's reconstruction, so the test pins the
        SHAPE without needing a full request cycle."""
        from urllib.parse import urlparse, urlunparse

        from django.utils.http import url_has_allowed_host_and_scheme
        pd, pr = urlparse(discourse_url), urlparse(return_url)
        base = urlunparse((pr.scheme, pd.netloc, pr.path, "", pr.query, ""))
        url = base + ("&" if pr.query else "?") + "sso=X&sig=Y"
        allowed = url_has_allowed_host_and_scheme(
            url, allowed_hosts=[pd.netloc], require_https=True)
        return url, allowed

    def test_a_default_port_host_is_unchanged(self):
        url, allowed = self._rebuild("https://forum.example.com",
                                     "https://forum.example.com/session/sso_login")
        self.assertTrue(allowed)
        self.assertIn("forum.example.com/session/sso_login", url)

    def test_a_custom_port_survives(self):
        url, allowed = self._rebuild(
            "https://forum.example.com:8443",
            "https://forum.example.com:8443/session/sso_login")
        self.assertIn(":8443", url, "the port was dropped")
        self.assertTrue(allowed, "the final gate rejected its own port")

    def test_an_ipv6_host_keeps_its_brackets(self):
        url, allowed = self._rebuild("https://[2001:db8::1]:3000",
                                     "https://[2001:db8::1]:3000/session/sso_login")
        self.assertIn("[2001:db8::1]:3000", url)
        self.assertTrue(allowed)

    def test_the_view_uses_netloc_on_both_sides(self):
        """Structural, because the two must not drift apart again."""
        import inspect
        src = inspect.getsource(sso)
        self.assertIn("parsed_discourse.netloc,  # trusted host:port", src)
        self.assertIn("allowed_hosts = [parsed_discourse.netloc]", src)


class TestTheSchemeGuardsAgree(TestCase):
    """The allowlist admitted http while the final gate required https,
    so an http return URL passed two checks and died at the third with a
    message naming the URL rather than the scheme (#2744)."""

    def test_the_early_guard_requires_https(self):
        import inspect
        src = inspect.getsource(sso)
        self.assertIn("if parsed_return.scheme != 'https':", src)
        self.assertNotIn("if parsed_return.scheme not in ('http', 'https'):", src)


class TestTheLogDoesNotCarryTheEmail(TestCase):
    """The failure log wrote `final_redirect_url` in full. That URL
    carries the signed SSO payload, which is base64 -- not encrypted --
    and contains the user's email address, so every failing SSO attempt
    wrote a real address into the web log (#2744)."""

    def test_the_failure_log_omits_the_query_string(self):
        import inspect
        src = inspect.getsource(sso)
        self.assertNotIn(
            'logger.error("Final redirect validation failed for URL: %s", final_redirect_url)',
            src)
        self.assertIn("Final redirect validation failed for %s://%s%s", src)

    def test_no_log_call_passes_the_payload_or_full_url(self):
        import inspect
        for line in inspect.getsource(sso).splitlines():
            if "logger." in line:
                self.assertNotIn("final_redirect_url", line)
                self.assertNotIn("response_payload", line)
