"""The Central Span, glorious (§3.5 landmark #2).

    blender --background --python scripts/atlas/sprites/landmark_bridge.py

Seven cells of suspension bridge running north-south: rusted towers with
hazard-striped bases and teal beacons, catenary main cables with hangers,
a lamplit deck. Local origin = the southern end cell's base center;
anchor (0,-3,0). Rendered at 2000px (exact px/unit: ortho scales with
resolution), ground to 500px.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import rig  # noqa: E402

rig.clear_scene()

steel = rig.make_material("steel", (0.30, 0.19, 0.13), 0.7, noise=0.45)
deckm = rig.make_material("deck", (0.10, 0.10, 0.12), 0.35,
                          noise=0.4, wet=True)
cable = rig.make_material("cable", (0.07, 0.07, 0.08), 0.6)
rail = rig.make_material("rail", (0.16, 0.14, 0.12), 0.6)
hazY = rig.make_material("hazY", (0.7, 0.55, 0.1), 0.8)
hazK = rig.make_material("hazK", (0.05, 0.05, 0.05), 0.8)
lamp = rig.make_material("lamp", (1.0, 0.7, 0.35), 0.4,
                         emit=(1.0, 0.62, 0.28))
beacon = rig.make_material("beacon", (0.2, 0.9, 0.9), 0.3,
                           emit=(0.3, 0.95, 1.0))

SPAN = 7.0
# deck with a gentle rise at center
for i in range(14):
    y = i * 0.5
    rise = 0.16 * math.sin(math.pi * y / (SPAN - 0.5))
    rig.box(f"deck{i}", (0.86, 0.52, 0.10), (0, y, 0.20 + rise), deckm)
    rig.box(f"railW{i}", (0.03, 0.52, 0.10), (-0.42, y, 0.32 + rise), rail)
    rig.box(f"railE{i}", (0.03, 0.52, 0.10), (0.42, y, 0.32 + rise), rail)
    if i % 3 == 1:
        rig.box(f"post{i}", (0.03, 0.03, 0.30), (0.40, y, 0.50 + rise), rail)
        rig.box(f"lamph{i}", (0.05, 0.05, 0.05), (0.40, y, 0.68 + rise), lamp)

# towers at 1/4 and 3/4 span
for k, ty in enumerate((1.75, 5.25)):
    for tx in (-0.40, 0.40):
        rig.box(f"leg{k}{tx}", (0.10, 0.10, 2.2), (tx, ty, 1.1), steel)
        for j in range(3):                        # hazard base
            rig.box(f"hz{k}{tx}{j}", (0.11, 0.11, 0.08),
                    (tx, ty, 0.10 + j * 0.08),
                    hazY if j % 2 == 0 else hazK)
    rig.box(f"cross{k}a", (0.90, 0.08, 0.08), (0, ty, 1.6), steel)
    rig.box(f"cross{k}b", (0.90, 0.08, 0.08), (0, ty, 2.14), steel)
    rig.box(f"bcn{k}", (0.06, 0.06, 0.06), (-0.40, ty, 2.26), beacon)
    rig.box(f"bcn{k}b", (0.06, 0.06, 0.06), (0.40, ty, 2.26), beacon)

# catenary main cables: tower tops sag to deck between anchors
def catenary(x, y0, y1, z0, z1, sag, n=12):
    for i in range(n):
        t = i / (n - 1)
        y = y0 + (y1 - y0) * t
        z = z0 + (z1 - z0) * t - sag * math.sin(math.pi * t)
        rig.box(f"cab{x}{y0}{i}", (0.035, (y1 - y0) / n + 0.04, 0.035),
                (x, y, z), cable)

for x in (-0.40, 0.40):
    catenary(x, 0.0, 1.75, 0.45, 2.18, -0.0, 8)     # south approach
    catenary(x, 1.75, 5.25, 2.18, 2.18, 1.05, 16)   # main sag
    catenary(x, 5.25, 7.0 - 0.5, 2.18, 0.45, 0.0, 8)
    for hy in (2.4, 3.0, 3.5, 4.0, 4.6):            # hangers
        t = (hy - 1.75) / 3.5
        cz = 2.18 - 1.05 * math.sin(math.pi * t)
        rig.box(f"hang{x}{hy}", (0.025, 0.025, max(0.05, cz - 0.36)),
                (x, hy, (cz + 0.36) / 2), cable)

catcher = rig.make_material("bgnd", (0.5, 0.5, 0.5), 1.0)
g = rig.box("gplane", (6, 12, 0.01), (0, 3.25, -0.005), catcher)
g.is_shadow_catcher = True

RES = 2000
rig.rig_camera_and_light(ortho=2.6 * RES / 512, target=(0, 3.25, 0.9))
rig.render("bridge", res=RES)

# self-calibration: the local origin under THIS camera
rig.clear_scene()
m = rig.make_material("mk", (1, 1, 1), 0.2, emit=(1, 1, 1))
rig.box("marker", (0.04, 0.04, 0.04), (0, 0, 0), m)
rig.rig_camera_and_light(ortho=2.6 * RES / 512, target=(0, 3.25, 0.9))
rig.render("calib_bridge", res=RES)
print("landmark bridge rendered")
