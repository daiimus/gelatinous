"""
Custom account views for Gelatinous Monster.

Extends Evennia's AccountCreateView with Cloudflare Turnstile verification.
"""

import requests
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from evennia.web.website.views.accounts import (
    AccountCreateView as EvenniaAccountCreateView
)
from web.website.forms import TurnstileAccountForm

import logging
logger = logging.getLogger("web")



def turnstile_config():
    """The ONE answer to "is the CAPTCHA on?".

    Returns ``(site_key, secret_key, enabled)``. Enabled requires BOTH
    keys, because either alone is worse than neither:

    * **site key only** — the widget renders and the inline script
      blocks submission, so the operator sees a working CAPTCHA, while
      the server verifies nothing. A request posted straight to the
      registration endpoint is unchallenged. Client-side theatre.
    * **secret key only** — the widget never renders, the field is
      ``required=False`` so the form still validates, and verification
      then submits an empty response to Cloudflare, which fails. EVERY
      registration is rejected, with a message blaming the user.

    The two states fail in opposite directions and neither logged
    anything, because rendering and enforcement were decided separately,
    from different settings, in different methods (#2747). A
    half-configured deployment now says so on every read.
    """
    site_key = getattr(settings, 'TURNSTILE_SITE_KEY', '') or ''
    secret_key = getattr(settings, 'TURNSTILE_SECRET_KEY', '') or ''
    if bool(site_key) != bool(secret_key):
        logger.error(
            "Turnstile is half-configured: %s is set and %s is not. The "
            "CAPTCHA is NOT protecting registration. Set both or neither.",
            "TURNSTILE_SITE_KEY" if site_key else "TURNSTILE_SECRET_KEY",
            "TURNSTILE_SECRET_KEY" if site_key else "TURNSTILE_SITE_KEY")
    return site_key, secret_key, bool(site_key and secret_key)


class TurnstileAccountCreateView(EvenniaAccountCreateView):
    """
    Account creation view with Cloudflare Turnstile verification.
    
    Extends Evennia's default account creation to include CAPTCHA verification
    using Cloudflare Turnstile (free, privacy-friendly alternative to reCAPTCHA).
    """
    
    # -- Django constructs --
    template_name = "website/registration/register.html"
    success_url = reverse_lazy("login")
    form_class = TurnstileAccountForm
    
    def get_context_data(self, **kwargs):
        """Add Turnstile site key to template context."""
        context = super().get_context_data(**kwargs)
        site_key, _secret, enabled = turnstile_config()
        context['turnstile_site_key'] = site_key
        context['turnstile_enabled'] = enabled
        return context
    
    def form_valid(self, form):
        """
        Validate form including Turnstile verification and duplicate checking.
        
        This extends the parent form_valid() to first verify the Cloudflare
        Turnstile response and ensure Django's form validation (including our
        custom clean_email() and clean_username() methods) has run before
        proceeding with account creation.
        
        Note: Evennia's AccountCreateView.form_valid() bypasses Django's
        standard form validation, so we must ensure it happens here.
        
        Turnstile verification is optional - if not configured, registration
        proceeds without CAPTCHA (useful for development and forks).
        """
        from evennia.accounts.models import AccountDB
        
        # Only verify Turnstile if configured
        # This allows the game to work for developers who clone from GitHub
        # without requiring Cloudflare Turnstile setup.
        # ONE decision, shared with get_context_data — rendering the
        # widget and enforcing the token used to be decided separately,
        # from different settings, in different methods (#2747).
        _site, _secret, enabled = turnstile_config()
        if enabled:
            turnstile_response = form.cleaned_data.get('cf_turnstile_response')
            if not self.verify_turnstile(turnstile_response):
                form.add_error(None, "CAPTCHA verification failed. Please try again.")
                return self.form_invalid(form)
        
        # Validate email and username uniqueness
        # This provides defense-in-depth since Evennia's parent class
        # bypasses Django's standard form validation flow
        email = form.cleaned_data.get('email', '').strip()
        username = form.cleaned_data.get('username', '').strip()
        
        # Check email uniqueness (case-insensitive)
        if email and AccountDB.objects.filter(email__iexact=email).exists():
            form.add_error('email', "An account with this email address already exists.")
            return self.form_invalid(form)
            
        # Check username uniqueness (case-insensitive)
        if username and AccountDB.objects.filter(username__iexact=username).exists():
            form.add_error('username', "An account with this username already exists.")
            return self.form_invalid(form)
        
        # All validations passed - proceed with account creation
        return super().form_valid(form)
    
    def verify_turnstile(self, token):
        """
        Verify Cloudflare Turnstile response token.
        
        Args:
            token (str): The cf-turnstile-response token from the form
            
        Returns:
            bool: True if verification successful, False otherwise
        """
        # Get secret key from settings
        _site, secret_key, _enabled = turnstile_config()

        if not secret_key:
            # Unreachable by construction — the caller checks `enabled`,
            # which requires this key. It used to return True, and a
            # security control whose unreachable branch fails OPEN is
            # one refactor away from failing open reachably, so it fails
            # CLOSED instead. Nothing depends on the old behaviour: the
            # branch could never run then either, which is exactly why
            # its warning never fired and the site-key-only
            # misconfiguration produced zero log output (#2747).
            logger.error("TURNSTILE_SECRET_KEY missing at verification "
                         "time - refusing to treat the CAPTCHA as passed")
            return False
        
        # Cloudflare Turnstile verification endpoint
        verify_url = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'
        
        # Prepare verification data
        data = {
            'secret': secret_key,
            'response': token,
            'remoteip': self.get_client_ip(),  # Optional but recommended
        }
        
        try:
            # Send verification request to Cloudflare
            response = requests.post(verify_url, data=data, timeout=10)
            result = response.json()
            
            # Check if verification was successful
            return result.get('success', False)
            
        except Exception as e:
            # Deliberate fail-closed guard: ANY failure verifying the
            # captcha with Cloudflare (network, JSON, timeout) must
            # reject the registration attempt, never wave it through
            # or 500. Logged for diagnosis.
            logger.error("Turnstile verification error: %s", e)
            return False
    
    def get_client_ip(self):
        """
        Get the client's IP address from the request.
        
        Returns:
            str: Client IP address
        """
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip

