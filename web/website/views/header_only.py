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


# The skin has to be resolved SERVER-SIDE for this view, unlike everywhere
# else, because the header is an iframe sitting directly against the forum
# body — and Discourse renders its own palette server-side from a cookie.
# Letting skins.js apply the skin after load meant the header painted the
# default ground while the body was already skinned, showing a seam along the
# join until the script ran. A fresh forum page replays that every time; an
# in-forum click does not reload the iframe, which is why it looked like it
# healed itself.
#
# Values are the `--terminal-bg-dark` of each skin in custom.css. They must be
# LITERALS here for the same reason the critical CSS block in the template
# uses literals: custom.css has not arrived at first paint, and an undefined
# custom property invalidates the whole declaration. Keep the two in sync.
SKIN_INK = {
    "atlas": "#0b0e14",
    "terminal": "#1a1a1a",
    "stray": "#0d0a12",
}
DEFAULT_SKIN = "atlas"


def _requested_skin(request):
    """
    The skin named by the `gel_skin` cookie, or the default.

    Whitelisted against SKIN_INK rather than trusted: the value reaches a
    template attribute and a stylesheet, and it is set by client-side script
    on a domain-scoped cookie, so anyone can put anything in it.
    """
    skin = request.COOKIES.get("gel_skin", DEFAULT_SKIN)
    return skin if skin in SKIN_INK else DEFAULT_SKIN


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
    skin = _requested_skin(request)

    context = {
        # Only stamped when it is not the default, matching what skins.js does
        # to the <html> element so the two agree about what "no skin" means.
        'skin': '' if skin == DEFAULT_SKIN else skin,
        'skin_ink': SKIN_INK[skin],
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
