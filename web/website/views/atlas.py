"""The atlas, served (COLONY_MAPPING_SPEC §M2.5) — inside the site's own
page, so the colony's header and footer carry through. The plate chrome
is the design; only the picture inside it went live-rendered. Any
logged-in account may read it. The builder's staff-overlay plate still
exists as a generated file (scripts/atlas/generate.py)."""

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils.safestring import mark_safe

from world.atlas import build_atlas3d_html


@login_required
def atlas_view(request):
    game_dir = getattr(settings, "GAME_DIR", ".")
    plate = build_atlas3d_html(game_dir, fragment=True, account=request.user)
    return render(request, "website/atlas.html",
                  {"atlas": mark_safe(plate), "page_title": "Atlas"})
