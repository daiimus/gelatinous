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

    def _load_sprite_dir(d):
        out = {}
        if os.path.isdir(d):
            for fname in sorted(os.listdir(d)):
                if fname.endswith(".png"):
                    with open(os.path.join(d, fname), "rb") as f:
                        out[fname[:-4]] = (
                            "data:image/png;base64,"
                            + base64.b64encode(f.read()).decode())
        return out

    sprites = _load_sprite_dir(sprite_dir)
    # the other compass views (rotation): final/v1..v3, same names
    sprite_views = {str(k): _load_sprite_dir(os.path.join(sprite_dir, f"v{k}"))
                    for k in (1, 2, 3)}

    anchor_path = os.path.join(game_dir, "scripts/atlas/sprites/anchors.json")
    data["anchor"] = (json.load(open(anchor_path))
                      if os.path.exists(anchor_path) else None)

    lm_path = os.path.join(game_dir, "scripts/atlas/sprites/landmarks.json")
    landmarks = json.load(open(lm_path)) if os.path.exists(lm_path) else []
    for lm in landmarks:
        lm["uri"] = sprites.pop(lm["sprite"], None)
        lm["uri_views"] = {k: v.pop(lm["sprite"], None)
                           for k, v in sprite_views.items()}
    data["landmarks"] = [lm for lm in landmarks if lm.get("uri")]
    data["sprites"] = sprites
    data["sprites_views"] = sprite_views

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


def build_atlas3d_html(game_dir=".", fragment=False):
    """The live-render atlas: three.js + exported models, wearing the
    same plate chrome as the sprite atlas did. In *fragment* mode it
    embeds in the site's own page (header and footer carry through),
    exactly the way the 2D plate was served.
    """
    data = export_map()

    lm_path = os.path.join(game_dir, "scripts/atlas/sprites/landmarks.json")
    landmarks = json.load(open(lm_path)) if os.path.exists(lm_path) else []
    data["landmarks"] = [
        {"name": lm["name"], "sprite": lm["sprite"],
         "anchor": lm["anchor"], "covers": lm["covers"]}
        for lm in landmarks
    ]

    three_path = os.path.join(game_dir, "scripts/atlas/vendor/three.min.js")
    models_path = os.path.join(game_dir, "scripts/atlas/sprites/models.json")
    tpl_path = os.path.join(game_dir, "scripts/atlas/template3d.html")
    three_src = open(three_path).read()
    models_src = open(models_path).read()
    html = open(tpl_path).read()
    html = html.replace("/*__THREE__*/", three_src)
    html = html.replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":")))
    html = html.replace("/*__MODELS__*/null", models_src)
    if fragment:
        # served inside the site's own page: the shell owns <title>,
        # the charset, and the page background
        html = re.sub(r"/\* __STANDALONE_ONLY__ \*/.*?/\* __END_STANDALONE__ \*/",
                      "", html, flags=re.S)
        html = re.sub(r"<meta charset[^>]*>\s*", "", html)
        html = re.sub(r"<title>.*?</title>\s*", "", html, flags=re.S)
    return html
