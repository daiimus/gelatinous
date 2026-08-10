"""The atlas, served (COLONY_MAPPING_SPEC §M2.5) — inside the site's own
page, so the colony's header and footer carry through. The plate chrome
is the design; only the picture inside it went live-rendered. PUBLIC:
anyone with the link may view it (owner call, 2026-08-23 — it's the
colony's shop window). The 'you are here' beacons still require a
login by nature: player_positions() only ever reports the requesting
account's own characters, and returns empty for anonymous viewers. The
builder's staff-overlay plate still exists only as a generated file
(scripts/atlas/generate.py) and is not served.

The 'you are here' beacons poll ?feed=here on this same path — the
edge allowlist admits exact paths only, and query strings pass.

THE PLATE IS CACHED: building it rereads the whole map from the DB and
embeds ~4MB of baked models per request, identical for every viewer.
Build it once, account-neutral (empty beacon seed — the client's
?feed=here poll fills beacons within one tick for logged-in players),
and reuse for PLATE_TTL. In-game building shows up within the TTL; a
reload clears the cache instantly (fresh process). Benign build race
under threads: worst case two identical builds.
"""

import time

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.safestring import mark_safe

from world.atlas import build_atlas3d_html, player_positions

PLATE_TTL = 120  # seconds
_plate = {"html": None, "at": 0.0}


def atlas_view(request):
    game_dir = getattr(settings, "GAME_DIR", ".")
    if request.GET.get("feed") == "here":
        return JsonResponse({"here": player_positions(request.user)})
    now = time.monotonic()
    if _plate["html"] is None or now - _plate["at"] > PLATE_TTL:
        _plate["html"] = build_atlas3d_html(game_dir, fragment=True,
                                            account=None)
        _plate["at"] = now
    return render(request, "website/atlas.html",
                  {"atlas": mark_safe(_plate["html"]),
                   "page_title": "Atlas"})
