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

import os

from django.conf import settings
from django.http import FileResponse, Http404
from django.urls import include, path
from django.views.decorators.cache import cache_control

# default evennia patterns
from evennia.web.urls import urlpatterns as evennia_default_urlpatterns

# Safari (macOS and iOS) largely ignores rel=icon and lives off the ROOT
# /favicon.ico; iOS additionally probes root /apple-touch-icon*.png paths.
# Evennia's default is a 302 into /media/, but a redirect through Django
# session middleware sets a cookie, which makes Cloudflare BYPASS the cache
# and gives Safari a hop it caches badly — icon swaps never propagated.
# Serve the bytes DIRECTLY at the root with explicit cache headers instead:
# edge-cacheable, cookie-free, and must-revalidate so a replaced icon
# actually reaches devices. (These routes shadow Evennia's favicon redirect
# because our urlpatterns are matched first.)


def _icon(relpath, content_type):
    @cache_control(public=True, max_age=86400, must_revalidate=True)
    def view(request):
        candidates = [os.path.join(settings.STATIC_ROOT or "", relpath)]
        try:
            from django.contrib.staticfiles import finders

            found = finders.find(relpath)
            if found:
                candidates.insert(0, found)
        except Exception:
            pass
        for p in candidates:
            if p and os.path.isfile(p):
                return FileResponse(open(p, "rb"), content_type=content_type)
        raise Http404(relpath)

    return view


_FAVICON = _icon("website/images/favicon.ico", "image/vnd.microsoft.icon")
_TOUCH_ICON = _icon("website/images/apple-touch-icon.png", "image/png")

# add patterns
urlpatterns = [
    # website
    path("", include("web.website.urls")),
    # webclient
    path("webclient/", include("web.webclient.urls")),
    # web admin
    path("admin/", include("web.admin.urls")),
    # root icon paths Safari/iOS actually use (see note above)
    path("favicon.ico", _FAVICON),
    path("apple-touch-icon.png", _TOUCH_ICON),
    path("apple-touch-icon-precomposed.png", _TOUCH_ICON),
    path("apple-touch-icon-120x120.png", _TOUCH_ICON),
    path("apple-touch-icon-120x120-precomposed.png", _TOUCH_ICON),
    path("apple-touch-icon-152x152.png", _TOUCH_ICON),
    path("apple-touch-icon-180x180.png", _TOUCH_ICON),
]

# 'urlpatterns' must be named such for Django to find it.
urlpatterns = urlpatterns + evennia_default_urlpatterns
