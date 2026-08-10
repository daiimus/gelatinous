"""
This is the starting point when a user enters a url in their web browser.

The urls is matched (by regex) and mapped to a 'view' - a Python function or
callable class that in turn (usually) makes use of a 'template' (a html file
with slots that can be replaced by dynamic content) in order to render a HTML
page to show the user.

This file includes the urls in website, webclient and admin. To override you
should modify urls.py in those sub directories.

Search the Django documentation for "URL dispatcher" for more help.

"""

from django.urls import include, path
from django.views.generic import RedirectView

# default evennia patterns
from evennia.web.urls import urlpatterns as evennia_default_urlpatterns

# iOS/iPadOS probe these ROOT paths on their own whenever a page doesn't
# declare an apple-touch-icon link (ours mostly don't — Evennia's base.html
# isn't forked). Without these routes the probes 404 (and the Cloudflare
# path allowlist blocked them outright), so Apple devices improvised their
# tab/home-screen icons. Same redirect pattern Evennia uses for favicon.ico.
_TOUCH_ICON = RedirectView.as_view(
    url="/static/website/images/apple-touch-icon.png", permanent=False
)

# add patterns
urlpatterns = [
    # website
    path("", include("web.website.urls")),
    # webclient
    path("webclient/", include("web.webclient.urls")),
    # web admin
    path("admin/", include("web.admin.urls")),
    # apple-touch-icon probe targets (see note above)
    path("apple-touch-icon.png", _TOUCH_ICON),
    path("apple-touch-icon-precomposed.png", _TOUCH_ICON),
    path("apple-touch-icon-120x120.png", _TOUCH_ICON),
    path("apple-touch-icon-120x120-precomposed.png", _TOUCH_ICON),
    path("apple-touch-icon-152x152.png", _TOUCH_ICON),
    path("apple-touch-icon-180x180.png", _TOUCH_ICON),
]

# 'urlpatterns' must be named such for Django to find it.
urlpatterns = urlpatterns + evennia_default_urlpatterns
