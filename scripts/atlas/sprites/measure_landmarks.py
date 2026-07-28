"""Per-landmark origin: centroid of each hero's own calibration marker,
written into landmarks.json (final-image pixel space)."""
import json
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
lms = json.load(open(os.path.join(HERE, "landmarks.json")))
for lm in lms:
    raw = Image.open(os.path.join(HERE, "raw", f"calib_{lm['sprite']}.png"))
    a = raw.getchannel("A")
    w, h = a.size
    px = a.load()
    sx = sy = n = 0
    for y in range(h):
        for x in range(w):
            v = px[x, y]
            if v > 32:
                sx += x * v; sy += y * v; n += v
    scale = lm["size"] / w                     # raw -> final
    lm["origin"] = [round(sx / n * scale, 2), round(sy / n * scale, 2)]
    print(lm["sprite"], "origin:", lm["origin"])
json.dump(lms, open(os.path.join(HERE, "landmarks.json"), "w"), indent=1)
print("landmarks measured")
