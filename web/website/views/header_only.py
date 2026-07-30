"""
Header-only view for iframe embedding.

This view renders just the navigation header without the full page layout,
allowing it to be embedded in an iframe on external sites (e.g., Discourse forum)
while maintaining visual consistency.

This endpoint is optional and only useful if you're embedding the header elsewhere.
"""

from django.shortcuts import render
from django.views.decorators.cache import cache_control
from django.views.decorators.clickjacking import xframe_options_exempt
from django.conf import settings


# NOT cached. This response is auth state: it names the logged-in account and
# renders a different menu for anonymous visitors. A five-minute cache meant
# the forum header could keep saying "Logged in as X" for five minutes after
# logging out, and that template changes appeared not to ship — the iframe
# kept serving the copy the browser already had.
#
# `private` alone was not enough: it stops shared caches, not the browser's.
@cache_control(no_store=True, no_cache=True, must_revalidate=True, private=True)
@xframe_options_exempt  # This view is embedded in a Discourse iframe; CSP frame-ancestors handles security
def header_only(request):
    """
    Render just the navbar for iframe embedding on external sites.

    This minimal view provides the Django header with full functionality
    (authentication state, dropdowns, etc.) without page chrome.

    The header detects it's in an iframe context and adjusts link behavior
    to prevent navigation issues.

    Deliberately uncached — see the decorator. The response embeds auth
    state, so a stale copy is both wrong and confusing.

    Optional: Only useful if you're embedding the header elsewhere (e.g., forum).
    """
    context = {
        'game_name': 'Gelatinous Monster',
        'game_slogan': 'An abomination to behold',
        'account': request.user if request.user.is_authenticated else None,
        'webclient_enabled': True,
        'register_enabled': True,
        'rest_api_enabled': request.user.is_staff if request.user.is_authenticated else False,
        'is_iframe': True,  # Signal to template that this is iframe context
        'discourse_url': getattr(settings, 'DISCOURSE_URL', ''),
    }

    return render(request, 'website/header_only.html', context)
