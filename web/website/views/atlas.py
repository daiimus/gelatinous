"""The atlas, served (COLONY_MAPPING_SPEC §M2.5) — inside the site's own
page, so the colony's header and footer carry through. Any logged-in
account may read the plate; the analytical overlays are staff
instruments and only render their controls for staff."""

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils.safestring import mark_safe

from world.atlas import build_atlas_html


@login_required
def atlas_view(request):
    game_dir = getattr(settings, "GAME_DIR", ".")
    staff = bool(request.user.is_superuser or request.user.is_staff)
    plate = build_atlas_html(game_dir, staff=staff, fragment=True)
    return render(request, "website/atlas.html",
                  {"atlas": mark_safe(plate), "page_title": "Atlas"})
