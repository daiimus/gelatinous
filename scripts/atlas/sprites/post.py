"""The darkroom (COLONY_MAPPING_SPEC §3.5): raw renders -> Fallout sprites.

    python3 post.py [raw_dir] [out_dir]

Downsample 4x, pull the palette toward the brown/olive band, quantize
with dithering, add grain — the pre-rendered-3D grit. Deterministic:
grain is seeded per sprite name.
"""

import os
import random
import sys

from PIL import Image, ImageEnhance

RAW = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "raw")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "final")
os.makedirs(OUT, exist_ok=True)

FINAL = 128            # sprite edge, px
COLORS = 40            # quantize band
WARMTH = (1.06, 1.0, 0.88)   # channel pull toward sodium/rust


def grind(name, img):
    rng = random.Random(name)                     # deterministic grain
    img = img.convert("RGBA")
    alpha = img.getchannel("A").resize((FINAL, FINAL), Image.LANCZOS)
    rgb = img.convert("RGB").resize((FINAL, FINAL), Image.LANCZOS)

    r, g, b = rgb.split()                         # warm the plate
    rgb = Image.merge("RGB", (
        r.point(lambda v: min(255, int(v * WARMTH[0]))),
        g.point(lambda v: min(255, int(v * WARMTH[1]))),
        b.point(lambda v: min(255, int(v * WARMTH[2])))))
    rgb = ImageEnhance.Color(rgb).enhance(0.9)    # sun-starved
    rgb = ImageEnhance.Contrast(rgb).enhance(1.12)

    rgb = rgb.quantize(COLORS, dither=Image.FLOYDSTEINBERG).convert("RGB")

    px = rgb.load()                               # grain
    for _ in range(FINAL * FINAL // 6):
        x, y = rng.randrange(FINAL), rng.randrange(FINAL)
        n = rng.randint(-14, 10)
        pr, pg, pb = px[x, y]
        px[x, y] = (max(0, min(255, pr + n)), max(0, min(255, pg + n)),
                    max(0, min(255, pb + n)))

    out = Image.merge("RGBA", (*rgb.split(), alpha))
    out.save(os.path.join(OUT, f"{name}.png"))
    print(f"ground {name}: {FINAL}px, {COLORS} colors")


for fname in sorted(os.listdir(RAW)):
    if fname.endswith(".png"):
        grind(fname[:-4], Image.open(os.path.join(RAW, fname)))
print("post complete")
