#!/usr/bin/env python3
"""
Build the brand assets from one definition.

Everything the mark appears as — the header SVG, the favicon, the forum's
icons, the social card — comes from here, so there is no second place to
remember to edit when the mark changes.

TWO OUTPUTS, TWO COLOUR STRATEGIES, and the difference matters:

  * The SVGs keep `var(--terminal-accent, #e0a86f)` so that when they are
    inlined in a page they follow the skin — the brand mark turns jade under
    Terminal and pink under Stray along with everything else.

  * The rasterised PNG/ICO output is FLATTENED to literal hex, because a
    bitmap cannot be themed by anything, and because librsvg — which does the
    rasterising — does not implement CSS custom properties and silently
    renders unresolved ones as grey.

The body is bone rather than accent on purpose. It keeps the planet legible
against the ring on every skin, and it is the highest-contrast shape available
at 16px, where an outline-only mark turns to mush.

Usage:  build_brand.py <outdir>       (requires ImageMagick with an RSVG
                                       delegate, and Monaspace installed if
                                       the wordmark is being rendered)
"""
import math
import subprocess
import sys
from pathlib import Path

INK, BONE, AMBER = "#0b0e14", "#d8d3c4", "#e0a86f"
FONT = "Monaspace Xenon Var, ui-monospace, monospace"

CANT = -22          # ring tilt. Level reads as a line; canted reads as a ring.
R_PLATE = 49.0
R_WORD = 43.0       # framing arcs and wordmark share this radius
GAP_TOP, GAP_BOTTOM = 70.0, 54.0


def _var(name, literal, flat):
    return literal if flat else f"var(--{name}, {literal})"


def device(flat):
    """The canted ringed world: far arc, body, near arc, moon.

    The near arc is drawn twice — an ink underlay, then the accent — so that
    where the ring crosses the lit body the two do not merge into one blob
    when the image is scaled down.
    """
    accent = _var("terminal-accent", AMBER, flat)
    body = _var("terminal-text", BONE, flat)
    ink = _var("terminal-bg-dark", INK, flat)
    return f'''
    <defs><clipPath id="gm-near"><rect x="-36" y="0" width="72" height="36"/></clipPath></defs>
    <g transform="rotate({CANT})">
      <ellipse class="ring" rx="26" ry="7.6" fill="none" stroke="{accent}"
               stroke-width="1.5" stroke-opacity="0.34"/>
    </g>
    <circle class="body" r="14" fill="{body}"/>
    <g transform="rotate({CANT})" clip-path="url(#gm-near)">
      <ellipse class="knock" rx="26" ry="7.6" fill="none" stroke="{ink}" stroke-width="4.4"/>
      <ellipse class="ring" rx="26" ry="7.6" fill="none" stroke="{accent}" stroke-width="2.3"/>
    </g>
    <circle class="knock" cx="24.5" cy="-6.2" r="4.4" fill="{ink}"/>
    <circle class="node" cx="24.5" cy="-6.2" r="3.0" fill="{accent}"/>'''


def _pt(a, r):
    t = math.radians(a)
    return (50 + r * math.sin(t), 50 - r * math.cos(t))


def _arc(a0, a1, r):
    x1, y1 = _pt(a0, r)
    x2, y2 = _pt(a1, r)
    large = 1 if (a1 - a0) % 360 > 180 else 0
    return f'M {x1:.2f},{y1:.2f} A {r},{r} 0 {large} 1 {x2:.2f},{y2:.2f}'


def _arc_text(word, centre, step, size, flat, flip=False):
    fill = _var("terminal-text", BONE, flat)
    out = []
    n = len(word)
    for i, ch in enumerate(word):
        if flip:
            a = centre + (n - 1) * step / 2 - i * step
            t = f"translate(50,50) rotate({a:.3f}) translate(0,{-R_WORD}) rotate(180)"
        else:
            a = centre - (n - 1) * step / 2 + i * step
            t = f"translate(50,50) rotate({a:.3f}) translate(0,{-R_WORD})"
        out.append(f'    <text class="word" transform="{t}" text-anchor="middle" '
                   f'font-family="{FONT}" font-size="{size}" font-weight="600" '
                   f'fill="{fill}" dy="0.34em">{ch}</text>')
    return "\n".join(out)


def build(flat, wordmark):
    accent = _var("terminal-accent", AMBER, flat)
    ink = _var("terminal-bg-dark", INK, flat)
    words = ""
    if wordmark:
        words = f'''
  <g class="ring" fill="none" stroke="{accent}" stroke-width="2.0" stroke-linecap="round">
    <path d="{_arc(GAP_TOP, 180 - GAP_BOTTOM, R_WORD)}"/>
    <path d="{_arc(180 + GAP_BOTTOM, 360 - GAP_TOP, R_WORD)}"/>
  </g>
  <g>
{_arc_text("GELATINOUS", 0.0, 12.4, 7.9, flat)}
{_arc_text("MONSTER", 180.0, 14.4, 7.9, flat, flip=True)}
  </g>'''
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"
     role="img" aria-label="Gelatinous Monster">
  <title>Gelatinous Monster</title>
  <circle class="plate" cx="50" cy="50" r="{R_PLATE}" fill="{ink}"/>
  <circle class="rim" cx="50" cy="50" r="{R_PLATE}" fill="none" stroke="{accent}"
          stroke-width="1.1" stroke-opacity="0.9"/>{words}
  <g transform="translate(50,50)">{device(flat)}
  </g>
</svg>
'''


def sh(*cmd):
    subprocess.run(cmd, check=True, capture_output=True)


def main(outdir):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)

    # themeable sources — these are what get committed and inlined
    (out / "gm-mark.svg").write_text(build(flat=False, wordmark=False))
    (out / "gm-patch.svg").write_text(build(flat=False, wordmark=True))

    # flattened, for rasterising only
    (out / "_flat-mark.svg").write_text(build(flat=True, wordmark=False))
    (out / "_flat-patch.svg").write_text(build(flat=True, wordmark=True))

    fm, fp = str(out / "_flat-mark.svg"), str(out / "_flat-patch.svg")

    # the patch, for surfaces with room for the wordmark
    for size in (512, 192):
        sh("magick", "-background", "none", fp, "-resize", f"{size}x{size}",
           f"PNG32:{out}/gm-patch-{size}.png")

    # the mark alone, for everything small
    for size in (256, 180, 64):
        sh("magick", "-background", "none", fm, "-resize", f"{size}x{size}",
           f"PNG32:{out}/gm-mark-{size}.png")

    # favicon: the mark at the three sizes browsers actually request. The
    # wordmark is deliberately absent — it is illegible below ~128px, and a
    # mark that degrades into a smudge is worse than one that stays a mark.
    sh("magick", "-background", "none", fm, "-define",
       "icon:auto-resize=48,32,16", f"{out}/favicon.ico")

    for f in (out / "_flat-mark.svg", out / "_flat-patch.svg"):
        f.unlink()

    for p in sorted(out.iterdir()):
        print(f"  {p.name:24} {p.stat().st_size:>7,} bytes")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "build")
