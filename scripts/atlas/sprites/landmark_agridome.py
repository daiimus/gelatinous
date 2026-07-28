"""The Pre-Fab Agridome (§3.5 landmark #3): the colony's glasshouse.

    blender --background --python scripts/atlas/sprites/landmark_agridome.py

A U-shaped growhouse: a long glass vault over the south row glowing with
grow-light, two gabled glass wings reaching north at the ends, an airlock
stub. Local origin = West Growbeds' base center; anchor (1,-18,0).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import rig  # noqa: E402

rig.clear_scene()

frame = rig.make_material("aframe", (0.30, 0.30, 0.26), 0.6, noise=0.3)
glass = rig.make_material("aglass", (0.35, 0.5, 0.35), 0.15,
                          emit=(0.55, 0.75, 0.45))
warm = rig.make_material("awarm", (0.9, 0.6, 0.3), 0.3,
                         emit=(0.95, 0.6, 0.3))
base = rig.make_material("abase", (0.20, 0.19, 0.16), 0.85, noise=0.35)
dark = rig.make_material("adark", (0.04, 0.05, 0.04), 0.4)

# footing skirt along the U
for (bx, by, sx_, sy_) in ((1.0, 0.0, 3.1, 1.0), (0.0, 0.5, 1.0, 2.0),
                           (2.0, 0.5, 1.0, 2.0)):
    rig.box(f"skirt{bx}{by}", (sx_, sy_, 0.16), (bx, by, 0.08), base)

# the main growhouse vault (south row, x 0..2)
rig.cylinder("vault", 0.52, 2.9, (1.0, 0, 0), glass, arc=math.pi * 0.92)
for i in range(7):
    wx = -0.35 + i * 0.45
    rig.cylinder(f"rib{i}", 0.535, 0.05, (wx + 1.0 - 0.9, 0, 0), frame,
                 arc=math.pi * 0.9)
rig.box("gableW", (0.06, 1.02, 0.5), (-0.44, 0, 0.25), frame)
rig.box("gableE", (0.06, 1.02, 0.5), (2.44, 0, 0.25), frame)

# north wings at x=0 and x=2: gabled glass sheds along y
for wx in (0.0, 2.0):
    rig.cylinder(f"wing{wx}", 0.42, 1.2, (0, 0, 0), glass,
                 arc=math.pi * 0.9)
    for o in bpy.context.collection.objects:
        if o.name == f"wing{wx}":
            o.rotation_euler = (0, 0, math.radians(90))
            o.location = (wx, 0.7, 0)
    rig.box(f"wgable{wx}", (0.86, 0.06, 0.42), (wx, 1.32, 0.21), frame)
    rig.box(f"wdoor{wx}", (0.22, 0.05, 0.30), (wx, 1.33, 0.15), dark)

# the airlock stub: warm-lit entry on the west wing's gable
rig.box("airlockglow", (0.16, 0.04, 0.06), (0.0, 1.34, 0.34), warm)

catcher = rig.make_material("agnd", (0.5, 0.5, 0.5), 1.0)
g = rig.box("gplane", (6, 5, 0.01), (1.0, 0.6, -0.005), catcher)
g.is_shadow_catcher = True

RES = 1200
rig.rig_camera_and_light(ortho=2.6 * RES / 512, target=(1.0, 0.5, 0.4))
rig.render("agridome", res=RES)

rig.clear_scene()
m = rig.make_material("mk", (1, 1, 1), 0.2, emit=(1, 1, 1))
rig.box("marker", (0.04, 0.04, 0.04), (0, 0, 0), m)
rig.rig_camera_and_light(ortho=2.6 * RES / 512, target=(1.0, 0.5, 0.4))
rig.render("calib_agridome", res=RES)
print("landmark agridome rendered")
