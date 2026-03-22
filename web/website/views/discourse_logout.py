"""
DiscourseConnect logout handler.

This is the official logout endpoint for DiscourseConnect SSO as documented at:
https://meta.discourse.org/t/setup-discourseconnect-official-single-sign-on-for-discourse-sso/13045

SETUP INSTRUCTIONS:
1. Add DISCOURSE_URL to your Django settings (required):
   DISCOURSE_URL = "https://forum.example.com"

2. Optional: Customize the post-logout redirect:
   DISCOURSE_LOGOUT_REDIRECT = "/custom-page/"  # Default: "/"

3. In Discourse admin, set the 'logout_redirect' setting to:
   https://yoursite.com/sso/discourse/logout/

SECURITY:
- Requires authentication (anonymous requests are ignored)
- Validates Referer header to prevent logout CSRF attacks
- Rejects requests with missing Referer when DISCOURSE_URL is configured
- CSRF-exempt is required per DiscourseConnect spec (simple GET redirect)
- Only logs out current session (non-destructive)

Per the DiscourseConnect specification:
- This is a simple GET redirect (no signed payloads)
- The endpoint should log out the user and redirect to a landing page
"""

from django.contrib.auth import logout
from django.shortcuts import redirect
from django.http import HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from urllib.parse import urlparse


@csrf_exempt
@require_http_methods(["GET"])
def discourse_logout(request):
    """
    Official DiscourseConnect logout endpoint.

    Called by Discourse's logout_redirect setting when a user logs out.
    Logs out the Django session and redirects to configured landing page.

    This follows the standard DiscourseConnect logout flow as documented
    in the official Discourse SSO documentation.

    Security:
        - Only processes logout for authenticated users
        - Validates Referer header against DISCOURSE_URL
        - Rejects requests with missing or mismatched Referer

    Configuration:
        DISCOURSE_URL (required): Your Discourse forum URL
        DISCOURSE_LOGOUT_REDIRECT (optional): Where to redirect after logout
    """
    redirect_url = getattr(settings, 'DISCOURSE_LOGOUT_REDIRECT', '/')

    # If user is not authenticated, just redirect — nothing to log out
    if not request.user.is_authenticated:
        return redirect(redirect_url)

    # Verify request is coming from configured Discourse forum
    # This prevents malicious sites from forcing users to logout via embedded links
    referer = request.META.get('HTTP_REFERER', '')
    discourse_url = getattr(settings, 'DISCOURSE_URL', '')

    if discourse_url:
        # Require a valid Referer from the configured Discourse instance.
        # A missing Referer is rejected because attackers can trivially strip
        # it (e.g. <meta name="referrer" content="no-referrer">).
        # Compare hostnames (not prefix) to prevent bypass via subdomains
        # like https://forum.gel.monster.evil.com.
        discourse_host = urlparse(discourse_url).hostname
        referer_host = urlparse(referer).hostname if referer else None
        if not referer_host or referer_host != discourse_host:
            return HttpResponseForbidden(
                "Invalid logout request. "
                "Please log out through your account page."
            )
    else:
        # DISCOURSE_URL not configured — refuse to process the logout.
        # Fail-closed: without a URL to validate against, we can't verify
        # the request origin.
        try:
            from evennia.utils import logger
            logger.log_warn(
                "DISCOURSE_URL not configured in settings. "
                "Discourse logout endpoint is non-functional until configured."
            )
        except ImportError:
            pass
        return HttpResponseForbidden(
            "Discourse logout is not configured. "
            "Please log out through your account page."
        )

    # Log the user out of Django
    logout(request)

    # Redirect to configured landing page (default: home page)
    return redirect(redirect_url)
