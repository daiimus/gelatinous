"""The atlas, served (COLONY_MAPPING_SPEC §M2.5) — the live render IS
the atlas. One version: the three.js viewer with the Cycles verdict
baked into its vertices, day and night skies aboard. The builder's
staff-overlay plate still exists as a generated file (scripts/atlas/
generate.py); it is an instrument, not a page."""

from django.conf import settings
from django.contrib.auth.decorators import login_required

from django.http import HttpResponse

from world.atlas import build_atlas3d_html


@login_required
def atlas_view(request):
    game_dir = getattr(settings, "GAME_DIR", ".")
    return HttpResponse(build_atlas3d_html(game_dir))
