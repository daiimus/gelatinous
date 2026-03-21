"""
DiscourseConnect Session Sync

This view redirects a logged-in Django user to Discourse to establish a proper
browser session with cookies. Simply redirecting to /session/sso triggers the
SSO flow which logs the user into Discourse.

Setup:
1. Configure settings in server/conf/secret_settings.py:
   DISCOURSE_URL = 'https://forum.example.com'
   DISCOURSE_SSO_SECRET = 'your-sso-secret-here'

2. Link to this view (opens in same tab, redirects through SSO):
   <a href="{% url 'discourse-session-sync' %}">Visit Forum</a>

How it works:
- User clicks link and is redirected to Discourse /session/sso
- Discourse initiates DiscourseConnect SSO flow back to Django
- Django's discourse_sso view authenticates and returns user data
- Discourse creates browser session with cookies
- User is redirected to Discourse home page, logged in

This is the proper way to establish a Discourse session from Django.
When auth_immediately=true, this happens automatically without user prompt.
"""

from django.conf import settings
from django.http import HttpResponseRedirect
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required


@login_required
@require_http_methods(["GET"])
def discourse_session_sync(request):
    """
    Redirect logged-in Django user to Discourse to establish session.
    
    This triggers the SSO flow which will:
    1. Redirect user to Discourse /session/sso
    2. Discourse initiates SSO back to Django /sso/discourse/
    3. Django authenticates and returns signed user data
    4. Discourse creates session and redirects to forum home
    
    With auth_immediately=true, this happens silently without user interaction.
    
    Returns:
        HttpResponseRedirect: Redirect to Discourse SSO endpoint
    """
    discourse_url = getattr(settings, 'DISCOURSE_URL', '')

    if not discourse_url:
        # DISCOURSE_URL not configured — redirect home instead of to a
        # hardcoded external domain.
        return HttpResponseRedirect('/')

    # Redirect to Discourse's SSO endpoint
    # Discourse will then initiate the SSO flow back to our discourse_sso view
    sso_url = f"{discourse_url}/session/sso"
    
    return HttpResponseRedirect(sso_url)
