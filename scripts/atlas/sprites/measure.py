"""Marker centroids -> anchors.json (in FINAL 128px sprite space)."""
import json
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SCALE = 128 / 512                     # raw -> final


def centroid(name):
    img = Image.open(os.path.join(HERE, "raw", f"calib_{name}.png"))
    a = img.getchannel("A")
    w, h = a.size
    px = a.load()
    sx = sy = n = 0
    for y in range(h):
        for x in range(w):
            v = px[x, y]
            if v > 32:
                sx += x * v; sy += y * v; n += v
    return (sx / n * SCALE, sy / n * SCALE)


o = centroid("origin")
ux = centroid("unitx")
uz = centroid("unitz")
anchors = {
    "origin": [round(o[0], 2), round(o[1], 2)],
    "xvec": [round(ux[0] - o[0], 3), round(ux[1] - o[1], 3)],
    "zvec": [round(uz[0] - o[0], 3), round(uz[1] - o[1], 3)],
    "size": 128,
}
out = os.path.join(HERE, "anchors.json")
json.dump(anchors, open(out, "w"), indent=1)
print("anchors:", anchors)
