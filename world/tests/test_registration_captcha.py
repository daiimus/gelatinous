"""The registration CAPTCHA had two independent on-switches (#2747).

Whether the widget RENDERS was decided from TURNSTILE_SITE_KEY in
`get_context_data`; whether the token is ENFORCED was decided from
TURNSTILE_SECRET_KEY in `form_valid`. Nothing tied them together, and
the two half-configured states fail in opposite directions:

* site key only  -> widget renders, server verifies nothing. A request
  posted straight to the endpoint is unchallenged: client-side theatre.
* secret key only -> widget never renders, the field is required=False
  so the form still validates, and an empty token is submitted to
  Cloudflare, which fails. EVERY registration is rejected.

Neither logged anything. The warning that would have caught the first
re-read the setting its only caller had already tested, so it could
never fire.
"""
from unittest import mock

from django.test import TestCase, override_settings

from web.website.views.accounts import turnstile_config


class TestOneDecision(TestCase):
    @override_settings(TURNSTILE_SITE_KEY="site", TURNSTILE_SECRET_KEY="secret")
    def test_both_keys_means_on(self):
        site, secret, enabled = turnstile_config()
        self.assertTrue(enabled)
        self.assertEqual((site, secret), ("site", "secret"))

    @override_settings(TURNSTILE_SITE_KEY="", TURNSTILE_SECRET_KEY="")
    def test_neither_key_means_off(self):
        """The documented dev path: a fork with no Cloudflare setup
        still registers accounts."""
        _site, _secret, enabled = turnstile_config()
        self.assertFalse(enabled)

    @override_settings(TURNSTILE_SITE_KEY="site", TURNSTILE_SECRET_KEY="")
    def test_site_key_only_is_not_enabled(self):
        """Was: widget renders, nothing enforced."""
        _site, _secret, enabled = turnstile_config()
        self.assertFalse(enabled)

    @override_settings(TURNSTILE_SITE_KEY="", TURNSTILE_SECRET_KEY="secret")
    def test_secret_key_only_is_not_enabled(self):
        """Was: every registration rejected, blaming the user."""
        _site, _secret, enabled = turnstile_config()
        self.assertFalse(enabled)


class TestAHalfConfiguredDeploymentSaysSo(TestCase):
    @override_settings(TURNSTILE_SITE_KEY="site", TURNSTILE_SECRET_KEY="")
    def test_site_key_only_logs_an_error(self):
        with mock.patch("web.website.views.accounts.logger.error") as err:
            turnstile_config()
        self.assertTrue(err.called, "the silent misconfiguration stayed silent")
        self.assertIn("TURNSTILE_SECRET_KEY", err.call_args.args[2])

    @override_settings(TURNSTILE_SITE_KEY="", TURNSTILE_SECRET_KEY="secret")
    def test_secret_key_only_logs_an_error(self):
        with mock.patch("web.website.views.accounts.logger.error") as err:
            turnstile_config()
        self.assertTrue(err.called)

    @override_settings(TURNSTILE_SITE_KEY="site", TURNSTILE_SECRET_KEY="secret")
    def test_a_correct_configuration_is_quiet(self):
        with mock.patch("web.website.views.accounts.logger.error") as err:
            turnstile_config()
        self.assertFalse(err.called)

    @override_settings(TURNSTILE_SITE_KEY="", TURNSTILE_SECRET_KEY="")
    def test_a_deliberate_opt_out_is_quiet(self):
        """The pin: not configuring it at all is a supported choice and
        must not nag on every page render."""
        with mock.patch("web.website.views.accounts.logger.error") as err:
            turnstile_config()
        self.assertFalse(err.called)


class TestVerificationFailsClosed(TestCase):
    @override_settings(TURNSTILE_SITE_KEY="", TURNSTILE_SECRET_KEY="")
    def test_no_secret_at_verification_time_is_not_a_pass(self):
        """Unreachable by construction, but a security control whose
        unreachable branch fails OPEN is one refactor from failing open
        reachably. It used to `return True`."""
        from web.website.views.accounts import TurnstileAccountCreateView
        view = TurnstileAccountCreateView()
        self.assertFalse(view.verify_turnstile("any-token"))


class TestTheClientAddressIsTheOneCloudflareSaw(TestCase):
    """`remoteip` is read from `CF-Connecting-IP`, which the tunnel sets and
    a client cannot forge through it, with the socket address as the
    fallback. `X-Forwarded-For` is never read: proxies append to it, so
    its leftmost element is the client's own claim (#3398)."""

    def _view(self, **meta):
        from web.website.views.accounts import TurnstileAccountCreateView
        view = TurnstileAccountCreateView()
        view.request = mock.Mock(META=meta)
        return view

    def test_cloudflares_header_wins(self):
        view = self._view(HTTP_CF_CONNECTING_IP="203.0.113.7",
                          HTTP_X_FORWARDED_FOR="10.0.0.1, 203.0.113.7",
                          REMOTE_ADDR="172.16.0.2")
        self.assertEqual(view.get_client_ip(), "203.0.113.7")

    def test_a_forged_forwarded_for_is_ignored(self):
        view = self._view(HTTP_X_FORWARDED_FOR="1.2.3.4", REMOTE_ADDR="172.16.0.2")
        self.assertEqual(view.get_client_ip(), "172.16.0.2")

    def test_nothing_known_is_none_not_a_blank(self):
        self.assertIsNone(self._view().get_client_ip())


class TestARefusalSaysWhy(TestCase):
    """A failed siteverify logs Cloudflare's error-codes; a pass is quiet."""

    @override_settings(TURNSTILE_SITE_KEY="1x00000000000000000000AA",
                       TURNSTILE_SECRET_KEY="1x0000000000000000000000000000000AA")
    def _verify(self, body):
        from web.website.views.accounts import TurnstileAccountCreateView
        view = TurnstileAccountCreateView()
        view.request = mock.Mock(META={"HTTP_CF_CONNECTING_IP": "203.0.113.7"})
        reply = mock.Mock(); reply.json.return_value = body
        with mock.patch("web.website.views.accounts.requests.post", return_value=reply) as post, \
                mock.patch("web.website.views.accounts.logger.warning") as warn:
            ok = view.verify_turnstile("tok")
        return ok, post, warn

    def test_a_refusal_logs_the_codes_and_fails(self):
        ok, post, warn = self._verify({"success": False, "error-codes": ["invalid-input-response"]})
        self.assertFalse(ok)
        self.assertTrue(warn.called)
        self.assertIn("invalid-input-response", str(warn.call_args))

    def test_a_pass_is_quiet_and_sends_the_trusted_address(self):
        ok, post, warn = self._verify({"success": True})
        self.assertTrue(ok)
        self.assertFalse(warn.called)
        self.assertEqual(post.call_args.kwargs["data"]["remoteip"], "203.0.113.7")

    def test_no_address_means_no_remoteip_field(self):
        from web.website.views.accounts import TurnstileAccountCreateView
        view = TurnstileAccountCreateView()
        view.request = mock.Mock(META={})
        reply = mock.Mock(); reply.json.return_value = {"success": True}
        with override_settings(TURNSTILE_SITE_KEY="1x00000000000000000000AA",
                               TURNSTILE_SECRET_KEY="1x0000000000000000000000000000000AA"), \
                mock.patch("web.website.views.accounts.requests.post", return_value=reply) as post:
            self.assertTrue(view.verify_turnstile("tok"))
        self.assertNotIn("remoteip", post.call_args.kwargs["data"])
