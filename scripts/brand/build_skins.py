#!/usr/bin/env python3
"""
Build every surface a skin touches from one manifest per skin.

A skin used to be defined in SIX places — custom.css token blocks, the
webclient's chrome block, the SKINS array in skins.js, SKIN_INK in the
header view, a Discourse colour palette, and the nginx gel_skin map. The
2026-08-04 seam saga was a guided tour of what that fragmentation costs:
three of its five bugs lived in the gaps between those files. This
generator collapses them: adding a skin is one manifest plus one run.

THE MANIFEST IS A VALID GHOSTTY THEME. Standard keys (palette = N=#hex,
background, foreground, cursor-color, selection-*) express the skin as any
terminal understands it; our extensions ride in `# gel:` comments, which
Ghostty ignores. Drop the same file into a terminal emulator and it just
works — the manifests are served publicly under /static/website/skins/ as
downloadable terminal themes, and any theme from the iTerm2-Color-Schemes
ghostty exports is a candidate skin at the cost of a few gel: lines.

The webclient's GAME TEXT is untouched by all of this: the protocol owns
game colour ([[STYLING_SPEC]]). Skins dress chrome. The ANSI-16 palette in
each manifest is real for terminals today and reserved for an opt-in
webclient rendering mode someday.

Targets are rewritten IN PLACE between marker comments:
    <token>  GENERATED SKINS (build_skins.py) BEGIN / END
Everything outside the markers is handwritten and untouched (the stray
cat-ears CSS, for instance, stays art, not data).

Usage:
    build_skins.py            regenerate all targets
    build_skins.py --check    exit non-zero if any target would change
"""

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MANIFEST_DIR = REPO / "web" / "static" / "website" / "skins"

# every skin must keep its ground dark enough that the fixed ANSI game
# palette stays legible — the one house rule imports cannot override
MAX_BG_LUMINANCE = 0.35

DEFAULT_SKIN = "atlas"

#: font role -> (CSS custom property, full font stack). A manifest may
#: override a role with a bare face name (neon/xenon/argon/radon).
FONT_ROLES = {
    "prose": ("--font-prose", "'Monaspace {face}', ui-monospace, 'SF Mono', Menlo, monospace"),
    "reading": ("--font-reading", "'Monaspace {face}', ui-monospace, 'SF Mono', Menlo, monospace"),
    "display": ("--font-display", "'Monaspace {face}', ui-monospace, 'SF Mono', Menlo, monospace"),
    "data": ("--font-data", "'Monaspace {face}', ui-monospace, 'SF Mono', Menlo, monospace"),
    "hand": ("--font-hand", "'Monaspace {face}', 'Monaspace Neon', cursive"),
}
FACES = {"neon": "Neon", "xenon": "Xenon", "argon": "Argon", "radon": "Radon"}


# ── colour helpers ──────────────────────────────────────────────────────

def _rgb(hexstr):
    h = hexstr.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _hex(rgb):
    return "#" + "".join(f"{max(0, min(255, round(c))):02x}" for c in rgb)


def mix(a, b, t):
    """Linear mix of two hex colours, t toward b."""
    ra, rb = _rgb(a), _rgb(b)
    return _hex(tuple(ra[i] + (rb[i] - ra[i]) * t for i in range(3)))


def luminance(hexstr):
    r, g, b = (c / 255 for c in _rgb(hexstr))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


# ── manifest parsing ────────────────────────────────────────────────────

class Skin:
    def __init__(self, path):
        self.path = path
        self.palette = {}
        self.std = {}
        self.gel = {}
        for raw in path.read_text().splitlines():
            line = raw.strip()
            if line.startswith("# gel:"):
                k, _, v = line[6:].partition("=")
                self.gel[k.strip()] = v.strip()
            elif line.startswith("#") or not line:
                continue
            else:
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip()
                if k == "palette":
                    idx, _, colour = v.partition("=")
                    self.palette[int(idx)] = colour.strip()
                else:
                    self.std[k] = v

        self.slug = self.gel["slug"]
        self.bg = self.std["background"]
        self.fg = self.std["foreground"]

        if luminance(self.bg) > MAX_BG_LUMINANCE:
            sys.exit(f"{path.name}: background {self.bg} is too light "
                     f"(luminance {luminance(self.bg):.2f} > {MAX_BG_LUMINANCE}) — "
                     "all skins stay dark so the fixed ANSI game palette stays legible")

    def _resolve(self, value):
        """A gel value may be a bare palette slot number or a hex colour."""
        if value and not value.startswith("#") and value.isdigit():
            return self.palette[int(value)]
        return value

    def token(self, name, fallback):
        v = self.gel.get(name)
        return self._resolve(v) if v else fallback

    # derived-with-override: the legacy skins pin shipped values exactly;
    # new skins may lean on the derivations
    @property
    def accent(self):
        return self._resolve(self.gel["accent"])

    @property
    def accent_dim(self):
        return self.token("accent-dim", mix(self.accent, self.bg, 0.35))

    @property
    def bg_medium(self):
        return self.token("bg-medium", mix(self.bg, self.fg, 0.06))

    @property
    def bg_light(self):
        return self.token("bg-light", mix(self.bg, self.fg, 0.12))

    @property
    def text_muted(self):
        return self.token("text-muted", mix(self.fg, self.bg, 0.40))

    @property
    def border(self):
        return self.token("border", mix(self.bg, self.fg, 0.16))

    @property
    def glow_alpha(self):
        return self.gel.get("glow-alpha", "0.30")

    @property
    def glow(self):
        r, g, b = _rgb(self.accent)
        return f"rgba({r}, {g}, {b}, {self.glow_alpha})"

    @property
    def quaternary(self):
        return self.token("quaternary", self.accent_dim)

    @property
    def primary_low_mid(self):
        return self.token("primary-low-mid", mix(self.fg, self.bg, 0.55))

    @property
    def palette_name(self):
        return self.gel["palette-name"]

    @property
    def palette_id(self):
        """Discourse id, or None until first seeded."""
        v = self.gel.get("palette-id")
        return int(v) if v else None

    @property
    def font_overrides(self):
        out = {}
        for role in FONT_ROLES:
            face = self.gel.get(f"font-{role}")
            if face:
                out[role] = FACES[face.lower()]
        return out

    @property
    def extra_css(self):
        """Free-form declarations for one-off skin flourishes (prism's
        spectrum zones), carried as gel: css-* lines: `css-<prop> = value`
        becomes `<prop>: value;` inside the skin's token block."""
        out = []
        for k, v in self.gel.items():
            if k.startswith("css-"):
                out.append((f"--{k[4:]}", v))
        return out


def load_skins():
    skins = [Skin(p) for p in sorted(MANIFEST_DIR.glob("*.ghostty"))]
    order = {s.gel.get("order", s.slug): s for s in skins}
    skins.sort(key=lambda s: int(s.gel.get("order", "99")))
    if not any(s.slug == DEFAULT_SKIN for s in skins):
        sys.exit(f"no manifest for default skin '{DEFAULT_SKIN}'")
    return skins


# ── emitters ────────────────────────────────────────────────────────────

def emit_custom_css(skins):
    """Site token blocks. The default skin's values live in :root by hand;
    generated blocks cover every non-default skin."""
    out = []
    for s in skins:
        if s.slug == DEFAULT_SKIN:
            continue
        out.append(f'[data-skin="{s.slug}"] {{')
        out.append(f"    --terminal-bg-dark: {s.bg};")
        out.append(f"    --terminal-bg-medium: {s.bg_medium};")
        out.append(f"    --terminal-bg-light: {s.bg_light};")
        out.append(f"    --terminal-accent: {s.accent};")
        out.append(f"    --terminal-accent-dim: {s.accent_dim};")
        out.append(f"    --terminal-text: {s.fg};")
        out.append(f"    --terminal-text-muted: {s.text_muted};")
        out.append(f"    --terminal-border: {s.border};")
        out.append(f"    --terminal-glow: {s.glow};")
        for prop, (var, stack) in FONT_ROLES.items():
            if prop in s.font_overrides:
                out.append(f"    {var}: {stack.format(face=s.font_overrides[prop])};")
        for var, val in s.extra_css:
            out.append(f"    {var}: {val};")
        out.append("}")
    return "\n".join(out)


def emit_webclient_css(skins):
    """Webclient CHROME tokens only — game text stays the protocol's."""
    out = []
    for s in skins:
        if s.slug == DEFAULT_SKIN:
            continue
        out.append(f'[data-skin="{s.slug}"] {{')
        out.append(f"    --bg-dark: {s.bg};")
        out.append(f"    --bg-medium: {s.bg_medium};")
        out.append(f"    --bg-light: {s.bg_light};")
        out.append(f"    --amber: {s.accent};")
        out.append(f"    --amber-dim: {s.accent_dim};")
        out.append(f"    --amber-glow: {s.glow};")
        out.append(f"    --text: {s.fg};")
        out.append(f"    --text-muted: {s.text_muted};")
        out.append(f"    --border: {s.border};")
        out.append("}")
    return "\n".join(out)


def emit_skins_js(skins):
    slugs = ", ".join(f'"{s.slug}"' for s in skins)
    return f"  var SKINS = [{slugs}];"


def emit_skin_ink(skins):
    lines = ["SKIN_INK = {"]
    for s in skins:
        lines.append(f'    "{s.slug}": "{s.bg}",')
    lines.append("}")
    return "\n".join(lines)


def emit_palettes_gjs(skins):
    lines = ["const PALETTES = {"]
    for s in skins:
        lines.append(f'  {s.slug}: "{s.palette_name}",')
    lines.append("};")
    return "\n".join(lines)


def emit_nginx_map(skins):
    """The infra map fragment. Only skins with a known Discourse id appear;
    a freshly authored skin joins after its first seed run reports the id."""
    lines = ["map $cookie_gel_skin $gel_scheme_id {", '    default   "";']
    for s in skins:
        if s.palette_id is not None:
            lines.append(f"    {s.slug:<9} {s.palette_id};   # {s.palette_name}")
    lines.append("}")
    return "\n".join(lines)


def emit_seed_rb(skins):
    """Rails seed for the Discourse palettes. Idempotent; prints each
    palette's id so new ones can be written back into their manifest."""
    entries = []
    for s in skins:
        colors = {
            "primary": s.fg.lstrip("#"),
            "secondary": s.bg.lstrip("#"),
            "tertiary": s.accent.lstrip("#"),
            "quaternary": s.quaternary.lstrip("#"),
            "header_background": s.bg.lstrip("#"),
            "header_primary": s.fg.lstrip("#"),
            "highlight": s.accent.lstrip("#"),
            "danger": "e85555",
            "success": "5fd38d",
            "love": s.token("love", s.accent).lstrip("#"),
            "selected": s.bg_medium.lstrip("#"),
            "hover": s.bg_light.lstrip("#"),
            "primary-medium": s.text_muted.lstrip("#"),
            "primary-low-mid": s.primary_low_mid.lstrip("#"),
        }
        pairs = ", ".join(f'"{k}" => "{v}"' for k, v in colors.items())
        entries.append(f'  "{s.palette_name}" => {{ {pairs} }},')
    body = "\n".join(entries)
    return f"""# GENERATED by scripts/brand/build_skins.py — do not hand-edit.
# Seeds/updates the Discourse colour palette for every skin manifest.
# Idempotent. Prints name => id so new palettes can be written back into
# their manifest's `# gel: palette-id` line (the nginx map needs it).
#
# user_selectable is REQUIRED: application_helper.rb#user_scheme_id ignores
# the color_scheme_id cookie for palettes without it, which silently kills
# the whole first-paint path.
SCHEMES = {{
{body}
}}

SCHEMES.each do |name, colors|
  scheme = ColorScheme.find_by(name: name) || ColorScheme.new(name: name)
  colors.each do |cname, hex|
    existing = scheme.color_scheme_colors.find {{ |c| c.name == cname }}
    if existing
      existing.hex = hex
    else
      scheme.color_scheme_colors << ColorSchemeColor.new(name: cname, hex: hex)
    end
  end
  scheme.user_selectable = true
  scheme.save!
  # mutated CHILD rows do not autosave with the parent — persisting the
  # scheme alone silently drops colour updates (creation works, update
  # no-ops; found when Dub's hearts stayed gold)
  scheme.color_scheme_colors.each(&:save!)
  scheme.touch
  puts "#{{name}} => #{{scheme.id}}"
end
"""


# ── in-place region rewriting ───────────────────────────────────────────

TARGETS = [
    (REPO / "web/static/website/css/custom.css", "/*", "*/", emit_custom_css),
    (REPO / "web/static/webclient/css/webclient.css", "/*", "*/", emit_webclient_css),
    (REPO / "web/static/website/js/skins.js", "//", "", emit_skins_js),
    (REPO / "web/website/views/header_only.py", "#", "", emit_skin_ink),
    (REPO / "web/discourse-theme/javascripts/discourse/api-initializers/skins.gjs",
     "//", "", emit_palettes_gjs),
]

SEED_RB = REPO / "scripts/brand/seed_skins.rb"
NGINX_MAP_FRAGMENT = REPO / "scripts/brand/nginx-gel-skin-map.generated.conf"


def marker(comment_open, comment_close, which):
    tail = f" {comment_close}" if comment_close else ""
    return f"{comment_open} GENERATED SKINS (build_skins.py) {which}{tail}"


def rewrite(path, comment_open, comment_close, content, check):
    text = path.read_text()
    begin = marker(comment_open, comment_close, "BEGIN")
    end = marker(comment_open, comment_close, "END")
    if begin not in text or end not in text:
        sys.exit(f"{path}: markers missing — install them once by hand")
    pattern = re.compile(re.escape(begin) + r"\n.*?" + re.escape(end), re.S)
    new = pattern.sub(begin + "\n" + content + "\n" + end, text)
    if new != text:
        if check:
            return False
        path.write_text(new)
    return True


def main():
    check = "--check" in sys.argv
    skins = load_skins()
    clean = True
    for path, co, cc, emitter in TARGETS:
        if not rewrite(path, co, cc, emitter(skins), check):
            print(f"  STALE: {path.relative_to(REPO)}")
            clean = False
    for path, emitter in ((SEED_RB, emit_seed_rb), (NGINX_MAP_FRAGMENT, emit_nginx_map)):
        content = emitter(skins)
        if path.exists() and path.read_text() == content:
            continue
        if check:
            print(f"  STALE: {path.relative_to(REPO)}")
            clean = False
        else:
            path.write_text(content)
    if check and not clean:
        sys.exit(1)
    print(f"  {'clean' if check else 'regenerated'}: "
          f"{len(skins)} skins ({', '.join(s.slug for s in skins)})")


if __name__ == "__main__":
    main()
