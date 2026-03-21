"""
Django logout view with optional Discourse logout synchronization.

If Discourse integration is configured, this view will also log the user out
of Discourse when they log out of Django. If Discourse is not configured,
it simply logs them out of Django normally.

OPTIONAL SETUP (for Discourse integration):
1. DISCOURSE_URL in Django settings
2. DISCOURSE_API_KEY in Django settings (admin API key)
3. DISCOURSE_SSO_SECRET in Django settings (for SSO)

If these settings are not configured, this view falls back to normal Django logout.

References:
- https://meta.discourse.org/t/logout-post-request/192601
- https://meta.discourse.org/t/discourseconnect-official-single-sign-on-for-discourse-sso/13045
"""

import requests
import hmac
import hashlib
import base64
from urllib.parse import urlencode, parse_qs
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import HttpResponseRedirect
from django.conf import settings


def get_discourse_user_id(user):
    """
    Get Discourse user ID for a Django user.
    For DiscourseConnect, this is the external_id which is the Django user ID.
    """
    discourse_url = getattr(settings, 'DISCOURSE_URL', '')
    api_key = getattr(settings, 'DISCOURSE_API_KEY', None)

    if not discourse_url or not api_key:
        return None
    
    # Use the by-external endpoint to find user by Django user ID
    url = f"{discourse_url}/users/by-external/{user.id}.json"
    headers = {
        'Api-Key': api_key,
        'Api-Username': 'system',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            user_data = response.json()
            return user_data.get('user', {}).get('id')
    except Exception:
        pass
    
    return None


def logout_discourse_user(discourse_user_id):
    """
    Log out a user from Discourse using the admin API.
    This invalidates their session in Discourse's database.
    """
    if not discourse_user_id:
        return False
    
    discourse_url = getattr(settings, 'DISCOURSE_URL', '')
    api_key = getattr(settings, 'DISCOURSE_API_KEY', None)

    if not discourse_url or not api_key:
        return False

    url = f"{discourse_url}/admin/users/{discourse_user_id}/log_out"
    headers = {
        'Api-Key': api_key,
        'Api-Username': 'system',
        'Content-Type': 'application/json',
    }
    
    try:
        response = requests.post(url, headers=headers, timeout=5)
        return response.status_code == 200
    except Exception:
        return False


@login_required
@require_http_methods(["GET", "POST"])
def logout_with_discourse(request):
    """
    Log out from Django and optionally from Discourse.
    
    If Discourse is configured:
    1. Look up Discourse user ID via external_id (Django user ID)
    2. Call Discourse API to invalidate their session
    3. Log out from Django
    4. Redirect to Django home page
    
    If Discourse is not configured:
    - Simply logs out from Django normally
    
    The API call invalidates the Discourse session in the database,
    so when the browser sends cookies on next request, they will be
    treated as invalid and the user will appear logged out.
    """
    user = request.user
    
    # Try to logout from Discourse first (if configured)
    discourse_user_id = get_discourse_user_id(user)
    if discourse_user_id:
        logout_discourse_user(discourse_user_id)
    # If Discourse is not configured, get_discourse_user_id returns None
    # and we just skip the Discourse logout gracefully
    
    # Log out from Django
    logout(request)
    
    # Redirect to home page
    return HttpResponseRedirect('/')
