"""The atlas, served (COLONY_MAPPING_SPEC §M2.5): a thin shim over
world.atlas.build_atlas_html, gated to superusers. The renderer is the
same self-contained document the generator script writes — served live,
it is simply never stale."""

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden

from world.atlas import build_atlas_html


@login_required
def atlas_view(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Surveyor access only.")
    game_dir = getattr(settings, "GAME_DIR", ".")
    return HttpResponse(build_atlas_html(game_dir))
