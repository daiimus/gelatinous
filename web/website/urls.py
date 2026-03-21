"""
This reroutes from an URL to a python view-function/class.

The main web/urls.py includes these routes for all urls (the root of the url)
so it can reroute to all website pages.

"""

from django.urls import path
from django.views.generic import RedirectView, TemplateView
from django.conf import settings

from evennia.web.website.urls import urlpatterns as evennia_website_urlpatterns
from web.website.views.characters import (
    CharacterCreateView, 
    CharacterArchiveView,
    StaffCharacterListView,
    OwnerOnlyCharacterDetailView,
    OwnerOnlyCharacterUpdateView
)
from web.website.views.channels import StaffChannelListView, StaffChannelDetailView
from web.website.views.accounts import TurnstileAccountCreateView
from web.website.views.discourse_sso import discourse_sso
from web.website.views.discourse_logout import discourse_logout
from web.website.views.logout_with_discourse import logout_with_discourse
from web.website.views.discourse_session_sync import discourse_session_sync
from web.website.views.header_only import header_only

# Override default character creation, account registration, and other views
urlpatterns = [
    # robots.txt - served as plain text for search engine crawlers
    path("robots.txt", TemplateView.as_view(template_name="robots.txt", content_type="text/plain"), name="robots-txt"),

    # Forum redirect - uses DISCOURSE_URL from settings, falls back to homepage
    path("forum/", RedirectView.as_view(
        url=getattr(settings, 'DISCOURSE_URL', '') or '/',
        permanent=False,
    ), name="forum-redirect"),
    
    # Header-only endpoint for iframe embedding (optional - for forum integration)
    path("header-only/", header_only, name="header-only"),
    
    # Discourse SSO endpoints (optional - only needed if using Discourse forum)
    path("sso/discourse/", discourse_sso, name="discourse-sso"),
    
    # Discourse logout endpoint (redirect target from Discourse logout)
    path("sso/discourse/logout/", discourse_logout, name="discourse-logout"),
    
    # Discourse session sync endpoint (automatic login sync)
    path("sso/discourse/session-sync/", discourse_session_sync, name="discourse-session-sync"),
    
    # Override default logout to also log out of Discourse (if configured)
    path("auth/logout/", logout_with_discourse, name="logout"),
    
    # Custom account registration with Cloudflare Turnstile
    path("auth/register", TurnstileAccountCreateView.as_view(), name="register"),
    
    # Custom character creation with GRIM stats
    path("characters/create/", CharacterCreateView.as_view(), name="character-create"),
    
    # Custom archive (instead of delete) - preserves Stack data
    path(
        "characters/delete/<str:slug>/<int:pk>/",
        CharacterArchiveView.as_view(),
        name="character-delete",
    ),
    
    # Owner-only character detail and update (staff can view/edit all)
    path(
        "characters/detail/<str:slug>/<int:pk>/",
        OwnerOnlyCharacterDetailView.as_view(),
        name="character-detail",
    ),
    path(
        "characters/update/<str:slug>/<int:pk>/",
        OwnerOnlyCharacterUpdateView.as_view(),
        name="character-update",
    ),
    
    # Staff-only character list (replaces default)
    path("characters/", StaffCharacterListView.as_view(), name="characters"),
    
    # Staff-only channel views (replaces defaults)
    path("channels/", StaffChannelListView.as_view(), name="channels"),
    path("channels/<str:slug>/", StaffChannelDetailView.as_view(), name="channel-detail"),
]

# read by Django
urlpatterns = urlpatterns + evennia_website_urlpatterns
