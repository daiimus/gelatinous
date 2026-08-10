"""Cookie-free icon responses.

Evennia's SharedLoginMiddleware saves a session on every request that
arrives without one, so even /favicon.ico responses carry Set-Cookie —
and Cloudflare refuses to cache any response that sets a cookie
(cf-cache-status: BYPASS). That single header is why swapping the icon
files never propagated: the root icon paths could not be edge-cached
and Safari was never told to revalidate.

This middleware sits at the TOP of the stack (its response pass runs
LAST, after SessionMiddleware has attached the cookie) and strips all
cookies from the handful of root icon paths. Nothing about a favicon
needs a session.
"""

ICON_PATHS = ("/favicon.ico", "/apple-touch-icon")


class CookieFreeIconMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path == ICON_PATHS[0] or request.path.startswith(ICON_PATHS[1]):
            response.cookies.clear()
        return response
