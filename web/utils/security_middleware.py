"""
Content Security Policy middleware.

Adds CSP headers to all responses. This is a lightweight alternative to
django-csp that doesn't require installing an external package.

The policy is tuned for this specific site:
- Evennia's upstream base.html loads jQuery, Popper, and Bootstrap from CDNs
- custom.css @imports Google Fonts
- Cloudflare Turnstile needs script + frame access
- The webclient uses WebSockets and blob-based Web Workers
- header_only view is embedded in an iframe on the Discourse forum
- Inline scripts and styles are used throughout (requires 'unsafe-inline')

NOTE: 'unsafe-inline' for script-src weakens XSS protection. The long-term
fix is migrating to CSP nonces, which requires modifying every template
(including Evennia's upstream base.html). This policy still provides value
by restricting script/style sources to known CDNs, blocking object/embed,
restricting frame-ancestors, and preventing base-uri injection.
"""

# -- CDN domains used by Evennia's base.html and our templates -----------

_SCRIPT_CDNS = (
    "https://cdn.jsdelivr.net",        # Bootstrap JS (header_only)
    "https://code.jquery.com",         # jQuery (base.html + header_only)
    "https://cdnjs.cloudflare.com",    # Popper.js (base.html)
    "https://maxcdn.bootstrapcdn.com", # Bootstrap JS (base.html)
    "https://challenges.cloudflare.com",  # Cloudflare Turnstile
)

_STYLE_CDNS = (
    "https://cdn.jsdelivr.net",        # Bootstrap CSS
    "https://fonts.googleapis.com",    # Google Fonts CSS (@import in custom.css)
)

# -- Build the default CSP directives ------------------------------------

_DEFAULT_CSP = "; ".join((
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' " + " ".join(_SCRIPT_CDNS),
    "style-src 'self' 'unsafe-inline' " + " ".join(_STYLE_CDNS),
    "font-src 'self' https://fonts.gstatic.com",
    "img-src 'self' data:",
    "connect-src 'self' wss://gel.monster ws://gel.monster",
    "frame-src https://challenges.cloudflare.com",
    "frame-ancestors 'self'",
    "worker-src 'self' blob:",
    "object-src 'none'",
    "base-uri 'self'",
))

# header_only is embedded in Discourse -- allow the forum as a frame ancestor
_HEADER_ONLY_CSP = _DEFAULT_CSP.replace(
    "frame-ancestors 'self'",
    "frame-ancestors 'self' https://forum.gel.monster",
)


class ContentSecurityPolicyMiddleware:
    """Add Content-Security-Policy header to every response."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Don't override if a view already set its own CSP
        if response.has_header("Content-Security-Policy"):
            return response

        if request.path.startswith("/header-only"):
            response["Content-Security-Policy"] = _HEADER_ONLY_CSP
        else:
            response["Content-Security-Policy"] = _DEFAULT_CSP

        return response
