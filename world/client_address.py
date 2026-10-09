"""The client address a login door may trust, and the key it throttles on.

Two doors take a password: the game's `connect` (commands/unloggedin_email.py)
and the website's login form (web/utils/auth_backends.py). Both key
Evennia's LOGIN_THROTTLE on the client address, and they must key the same
way or an attacker plays one door against the other (#3734).

`from_request` is the address Cloudflare saw (`CF-Connecting-IP`, set at the
edge, unforgeable through the tunnel) or None. Nothing else is trusted:
`X-Forwarded-For` is the client's own claim, and Evennia's webserver copies
that claim into `REMOTE_ADDR` behind an upstream proxy (#3398).

`bucket` is what the throttle counts against. IPv4 is exact. An IPv6 client
usually holds a whole /64 and could rotate through it to dodge a per-address
count, so IPv6 is bucketed by its /64 network, the convention fail2ban and
friends use (#3734). The security log still records the full address.
"""
import ipaddress


def from_request(request):
    """The address Cloudflare saw for *request*, or None."""
    meta = getattr(request, "META", None) or {}
    return meta.get("HTTP_CF_CONNECTING_IP") or None


def bucket(address) -> str:
    """The throttle key for *address*: the address itself for IPv4, its /64
    for IPv6, "" when there is nothing to key on."""
    text = str(address or "").strip()
    if not text:
        return ""
    try:
        parsed = ipaddress.ip_address(text)
    except ValueError:
        return text
    if parsed.version == 6:
        mapped = parsed.ipv4_mapped
        if mapped is not None:          # ::ffff:203.0.113.9 is an IPv4 client
            return str(mapped)
        return str(ipaddress.ip_network((parsed, 64), strict=False))
    return text
