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
