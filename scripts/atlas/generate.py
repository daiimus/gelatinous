"""Generate the colony atlas file (COLONY_MAPPING_SPEC §M2).

    evennia shell < scripts/atlas/generate.py

Writes self-contained /tmp/atlas.html from the live DB. The website view
(§M2.5) serves the same builder at /atlas/ for superusers.
"""

from world.atlas import build_atlas_html

html = build_atlas_html(".", staff=True)
with open("/tmp/atlas.html", "w") as f:
    f.write(html)
print(f"atlas written: /tmp/atlas.html ({len(html)} bytes)")
