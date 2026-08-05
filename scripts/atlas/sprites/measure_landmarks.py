"""Per-landmark origin: centroid of each hero's own calibration marker,
written into landmarks.json (final-image pixel space).

Origins are measured PER VIEW: heroes rotate about their camera target,
so the marker (at the local origin) lands somewhere different in each
compass view. lm["origins"] carries [v0, v1, v2, v3]; lm["origin"]
stays as v0 for compatibility."""
import json
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
lms = json.load(open(os.path.join(HERE, "landmarks.json")))


def centroid(path, size):
    raw = Image.open(path).transpose(Image.FLIP_LEFT_RIGHT)
    a = raw.getchannel("A")
    w, h = a.size
    px = a.load()
    sx = sy = n = 0
    for y in range(h):
        for x in range(w):
            v = px[x, y]
            if v > 32:
                sx += x * v; sy += y * v; n += v
    scale = size / w                       # raw -> final
    return [round(sx / n * scale, 2), round(sy / n * scale, 2)]


for lm in lms:
    origins = [centroid(os.path.join(HERE, "raw", f"calib_{lm['sprite']}.png"),
                        lm["size"])]
    for k in (1, 2, 3):
        vpath = os.path.join(HERE, "raw", f"v{k}", f"calib_{lm['sprite']}.png")
        origins.append(centroid(vpath, lm["size"])
                       if os.path.exists(vpath) else origins[0])
    lm["origin"] = origins[0]
    lm["origins"] = origins
    print(lm["sprite"], "origins:", origins)
json.dump(lms, open(os.path.join(HERE, "landmarks.json"), "w"), indent=1)
print("landmarks measured")
