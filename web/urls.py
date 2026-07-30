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

from django.shortcuts import redirect
from django.templatetags.static import static
from django.urls import include, path

# default evennia patterns
from evennia.web.urls import urlpatterns as evennia_default_urlpatterns


def favicon(request):
    """
    Serve the brand mark at /favicon.ico.

    Evennia routes this to ``/media/images/favicon.ico``, which does not exist
    here — the root probe 404s. Browsers still ask for it regardless of the
    ``<link rel="icon">`` in the page: Safari in particular uses it for tab
    icons, bookmarks and the reading list, which is why a correct link tag was
    not enough to make the new mark appear.

    Resolved per request rather than at import, so the hashed filename stays
    correct after the mark is restyled and re-collected.
    """
    return redirect(static("website/images/evennia_logo.png"))


# add patterns
urlpatterns = [
    # Ours must precede Evennia's, which points these at /media paths that
    # do not exist in this deployment.
    path("favicon.ico", favicon),
    path("apple-touch-icon.png", favicon),
    path("apple-touch-icon-precomposed.png", favicon),
    # website
    path("", include("web.website.urls")),
    # webclient
    path("webclient/", include("web.webclient.urls")),
    # web admin
    path("admin/", include("web.admin.urls")),
    # add any extra urls here:
    # path("mypath/", include("path.to.my.urls.file")),
]

# 'urlpatterns' must be named such for Django to find it.
urlpatterns = urlpatterns + evennia_default_urlpatterns
