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
