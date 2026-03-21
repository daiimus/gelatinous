"""
Discourse SSO (DiscourseConnect) Provider

Handles SSO authentication requests from Discourse forum.
Users authenticate via Django/Evennia and are automatically logged into Discourse.

SSO Flow:
1. User clicks "Login" on Discourse
2. Discourse redirects to this endpoint with payload and signature
3. Django verifies signature, checks if user is logged in
4. Django generates response with user info
5. Redirects back to Discourse with signed payload
6. Discourse logs user in automatically

References:
- https://meta.discourse.org/t/discourseconnect-official-single-sign-on-for-discourse-sso/13045
"""

import base64
import hmac
import hashlib
from urllib.parse import parse_qs, urlencode, unquote, urlparse, urlunparse
from django.utils.http import url_has_allowed_host_and_scheme

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.views.decorators.http import require_http_methods

import logging
logger = logging.getLogger(__name__)

def get_discourse_sso_secret():
    """Get the SSO secret from settings."""
    return getattr(settings, 'DISCOURSE_SSO_SECRET', None)


def verify_payload(payload, signature):
    """
    Verify that the payload signature is valid.
    
    Args:
        payload: Base64 encoded SSO payload from Discourse
        signature: HMAC-SHA256 signature of the payload
        
    Returns:
        bool: True if signature is valid
    """
    secret = get_discourse_sso_secret()
    if not secret:
        return False
    
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_signature, signature)


def sign_payload(payload):
    """
    Sign a payload with HMAC-SHA256.
    
    Args:
        payload: String to sign
        
    Returns:
        str: Hexadecimal signature
    """
    secret = get_discourse_sso_secret()
    return hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()


@login_required
@require_http_methods(["GET"])
def discourse_sso(request):
    """
    Handle SSO authentication request from Discourse.
    
    Query Parameters:
        sso: Base64 encoded payload from Discourse containing nonce and return_sso_url
        sig: HMAC-SHA256 signature of the sso parameter
        
    Returns:
        HttpResponseRedirect: Redirects back to Discourse with signed user data
        HttpResponseBadRequest: If parameters are invalid or signature doesn't match
    """
    # Check if SSO is configured
    if not get_discourse_sso_secret():
        return HttpResponseBadRequest("SSO is not configured")
    
    # Get SSO parameters from request
    payload = request.GET.get('sso')
    signature = request.GET.get('sig')
    
    if not payload or not signature:
        return HttpResponseBadRequest("Missing SSO parameters")
    
    # Verify the payload signature
    if not verify_payload(payload, signature):
        return HttpResponseBadRequest("Invalid signature")
    
    # Decode the payload
    try:
        decoded_payload = base64.b64decode(payload).decode('utf-8')
        params = parse_qs(decoded_payload)
    except Exception as e:
        logger.exception("Failed to decode or parse SSO payload")
        return HttpResponseBadRequest("Invalid payload")
    
    # Extract nonce (required by Discourse)
    nonce = params.get('nonce', [None])[0]
    if not nonce:
        return HttpResponseBadRequest("Missing nonce in payload")
    
    # Get authenticated user
    user = request.user
    
    # Build response payload with user information
    response_params = {
        'nonce': nonce,
        'email': user.email,
        'external_id': str(user.id),  # User's Django ID
        'username': user.username,
        'name': user.get_full_name() or user.username,  # Full name or username fallback
    }
    
    # Optional: Add avatar URL if available
    # if hasattr(user, 'avatar_url'):
    #     response_params['avatar_url'] = user.avatar_url
    
    # Optional: Make user admin in Discourse
    # if user.is_superuser:
    #     response_params['admin'] = 'true'
    
    # Optional: Make user moderator in Discourse
    # if user.is_staff:
    #     response_params['moderator'] = 'true'
    
    # Encode response payload
    response_payload = base64.b64encode(urlencode(response_params).encode('utf-8')).decode('utf-8')
    
    # Sign the response payload
    response_signature = sign_payload(response_payload)
    
    # Get return URL from original payload
    return_sso_url = params.get('return_sso_url', [None])[0]
    if not return_sso_url:
        return HttpResponseBadRequest("Missing return_sso_url in payload")
    
    # Validate the return URL to prevent open redirect attacks
    discourse_url = getattr(settings, 'DISCOURSE_URL', '')
    if not discourse_url:
        logger.error("DISCOURSE_URL not configured - SSO redirect blocked for security")
        return HttpResponseBadRequest("SSO not properly configured")
    
    # Parse both URLs to validate
    parsed_discourse = urlparse(discourse_url)
    parsed_return = urlparse(return_sso_url)
    
    if not parsed_discourse.hostname:
        logger.error("Invalid DISCOURSE_URL configuration - SSO redirect blocked")
        return HttpResponseBadRequest("SSO not properly configured")
    
    # Strict hostname validation - only allow exact match to configured Discourse host
    if parsed_return.hostname != parsed_discourse.hostname:
        logger.warning("SSO redirect to unauthorized host blocked. Expected: %s, Got: %s", 
                      parsed_discourse.hostname, parsed_return.hostname)
        return HttpResponseBadRequest("Invalid return URL - host mismatch")
    
    # Validate scheme is http or https
    if parsed_return.scheme not in ('http', 'https'):
        logger.warning("SSO redirect with invalid scheme blocked: %s", parsed_return.scheme)
        return HttpResponseBadRequest("Invalid return URL - invalid scheme")
    
    # Build redirect URL with SSO response parameters
    # Reconstruct from validated components to ensure no injection
    base_url = urlunparse((
        parsed_return.scheme,
        parsed_discourse.hostname,  # Use the trusted hostname from settings
        parsed_return.path,
        '',  # No params
        parsed_return.query,
        ''   # No fragment
    ))
    
    separator = '&' if parsed_return.query else '?'
    redirect_params = urlencode({'sso': response_payload, 'sig': response_signature})
    final_redirect_url = f"{base_url}{separator}{redirect_params}"
    
    # Final validation with explicit allowlist before redirect
    allowed_hosts = [parsed_discourse.hostname]
    if not url_has_allowed_host_and_scheme(final_redirect_url, allowed_hosts=allowed_hosts, require_https=True):
        logger.error("Final redirect validation failed for URL: %s", final_redirect_url)
        return HttpResponseBadRequest("Invalid redirect URL")
    
    return HttpResponseRedirect(final_redirect_url)
