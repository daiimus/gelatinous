"""Atlas HTML builder (COLONY_MAPPING_SPEC §M2/§M2.5) — one function,
two consumers: the offline generator script and the superuser website
view. Read-only over the DB; paths resolve against *game_dir* so both
the shell and the Django process find the template and sprite library.
"""

import base64
import json
import os
import re

from world.mapping import export_map


def build_atlas_html(game_dir=".", staff=False, fragment=False):
    data = export_map()

    sprite_dir = os.path.join(game_dir, "scripts/atlas/sprites/final")
    sprites = {}
    if os.path.isdir(sprite_dir):
        for fname in sorted(os.listdir(sprite_dir)):
            if fname.endswith(".png"):
                with open(os.path.join(sprite_dir, fname), "rb") as f:
                    sprites[fname[:-4]] = (
                        "data:image/png;base64,"
                        + base64.b64encode(f.read()).decode())

    anchor_path = os.path.join(game_dir, "scripts/atlas/sprites/anchors.json")
    data["anchor"] = (json.load(open(anchor_path))
                      if os.path.exists(anchor_path) else None)

    lm_path = os.path.join(game_dir, "scripts/atlas/sprites/landmarks.json")
    landmarks = json.load(open(lm_path)) if os.path.exists(lm_path) else []
    for lm in landmarks:
        lm["uri"] = sprites.pop(lm["sprite"], None)
    data["landmarks"] = [lm for lm in landmarks if lm.get("uri")]
    data["sprites"] = sprites

    masts = []
    try:
        from world.radio import (_all_powered_radios, _antenna_site,
                                 _effective_tx_range, _grid_room)
        from world.spatial import get_xyz
        for radio in _all_powered_radios():
            if radio.db.is_base_station is not True:
                continue
            site = _antenna_site(radio)
            if site is None:
                room = _grid_room(radio)
                site = get_xyz(room) if room is not None else None
            if site is None:
                continue
            reach = _effective_tx_range(radio, site)
            masts.append({"x": site[0], "y": site[1], "name": radio.key,
                          "freq": str(radio.db.frequency or ""),
                          "crisp": round(0.7 * reach, 1),
                          "reach": round(reach, 1)})
    except Exception:  # noqa: BLE001 — coverage is annotation, not truth
        pass
    data["masts"] = sorted(masts, key=lambda m: m["name"])
    data["staff"] = bool(staff)

    template = open(os.path.join(game_dir,
                                 "scripts/atlas/template.html")).read()
    # json.dumps does NOT escape "</script>", so a string containing it would
    # close the script element and everything after it would parse as markup.
    # Escaping "<" (plus the two line separators JS treats as newlines) is the
    # standard hardening — \u003c is a valid escape inside a JS string, and
    # "<" only ever occurs inside string values in JSON.
    payload = (
        json.dumps(data)
        .replace("<", "\\u003c")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
    html = template.replace("/*__DATA__*/null", payload)
    if fragment:
        # served inside the site's own page: the shell owns <title> and
        # the page background, and Evennia's sticky footer needs the
        # body margin the standalone rules would clear
        html = re.sub(r"/\* __STANDALONE_ONLY__ \*/.*?/\* __END_STANDALONE__ \*/",
                      "", html, flags=re.S)
        html = re.sub(r"<title>.*?</title>\s*", "", html, flags=re.S)
    return html
