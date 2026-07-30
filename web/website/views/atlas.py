"""The atlas, served (COLONY_MAPPING_SPEC §M2.5). Any logged-in
account may read the plate; the analytical overlays (air lattice, jump
routes, radio coverage) are staff instruments and only render their
controls for staff."""

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse

from world.atlas import build_atlas_html


@login_required
def atlas_view(request):
    game_dir = getattr(settings, "GAME_DIR", ".")
    staff = bool(request.user.is_superuser or request.user.is_staff)
    return HttpResponse(build_atlas_html(game_dir, staff=staff))
