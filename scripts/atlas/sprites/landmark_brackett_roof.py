"""The Brackett Arms rooftop (§3.5 landmark #4): the colony's crown, v2.

    blender --background --python scripts/atlas/sprites/landmark_brackett_roof.py

The full z7 roofline after the rooftop accuracy pass: an L of eight
cells — west column (Northwest/West/Southwest Roof), center column
(North Roof/Roof Deck/South Roof), east pair (East/Southeast Roof with
the elevator headhouse) — with the tower's true notch at local (1,0)
left open. The AWE Sentinel-9 mast keeps its post on North Roof; tanks
hold the west column; laundry runs the Deck; the painted arrow now
marks the SOUTH rim, where the drop is real. Local origin = North
Roof's base center; anchor (-10,-17,7).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import rig  # noqa: E402

rig.clear_scene()

tar = rig.make_material("btar", (0.14, 0.135, 0.13), 0.85, noise=0.4)
tar_w = rig.make_material("btarw", (0.13, 0.125, 0.122), 0.85, noise=0.5)
para = rig.make_material("bpara", (0.23, 0.22, 0.19), 0.9, noise=0.3)
steel = rig.make_material("bsteel", (0.30, 0.29, 0.26), 0.55, noise=0.2)
rust = rig.make_material("brust", (0.34, 0.21, 0.13), 0.8, noise=0.4)
house = rig.make_material("bhouse", (0.17, 0.20, 0.23), 0.85, noise=0.3)
cable = rig.make_material("bcable", (0.07, 0.07, 0.08), 0.6)
lamp = rig.make_material("blamp", (1.0, 0.7, 0.35), 0.4,
                         emit=(1.0, 0.62, 0.28), emit_strength=2.2)
beacon = rig.make_material("bbeacon", (0.2, 0.9, 0.9), 0.3,
                           emit=(0.35, 0.95, 1.0), emit_strength=3.0)
paint = rig.make_material("bpaint", (0.55, 0.50, 0.42), 0.9)
patch = rig.make_material("bpatch", (0.10, 0.10, 0.10), 0.9)

# --- the deck: an L of eight cells; (1, 0) is the tower's true notch --
CELLS = [(-1, 0), (-1, -1), (-1, -2),      # west column (new roofs)
         (0, 0), (0, -1), (0, -2),        # center column (the originals)
         (1, -1), (1, -2)]                # east pair (headhouse, southeast)
for cx, cy in CELLS:
    mat = tar_w if cx == -1 else tar
    rig.box(f"deck{cx}{cy}", (1.0, 1.0, 0.10), (cx, cy, 0.05), mat)

# parapet ring tracing the L (outer rim + the notch's two inner walls)
PAR = [((-1.465, -1.0), (0.07, 3.0)),       # west rim
       ((1.465, -1.5), (0.07, 2.0)),        # east rim (short leg)
       ((-0.5, 0.465), (2.0, 0.07)),        # north rim (west+center)
       ((0.0, -2.465), (3.0, 0.07)),        # south rim (full width)
       ((0.535, 0.0), (0.07, 1.0)),         # notch west wall
       ((1.0, -0.535), (1.0, 0.07))]        # notch south wall
for i, ((px, py), (sx, sy)) in enumerate(PAR):
    rig.box(f"par{i}", (sx, sy, 0.20), (px, py, 0.15), para)

# --- the elevator headhouse on East Roof (local 1,-1) ----------------
rig.box("head", (0.66, 0.72, 0.52), (1.0, -1.0, 0.36), house)
rig.box("headcap", (0.72, 0.78, 0.05), (1.0, -1.0, 0.64), steel)
rig.box("headdoor", (0.26, 0.03, 0.34), (0.86, -1.37, 0.27),
        rig.make_material("bdoor", (0.04, 0.05, 0.06), 0.4))
rig.box("headlamp", (0.10, 0.04, 0.04), (0.86, -1.38, 0.50), lamp)

# --- the Sentinel: lattice mast keeps its post on North Roof ---------
MX, MY = -0.16, 0.10
for leg in ((-0.09, -0.09), (0.09, -0.09), (-0.09, 0.09), (0.09, 0.09)):
    rig.box(f"leg{leg}", (0.035, 0.035, 1.45), (MX + leg[0], MY + leg[1], 0.80),
            steel)
for j in range(5):                          # lattice bracing
    z = 0.22 + j * 0.30
    rig.box(f"brN{j}", (0.20, 0.03, 0.03), (MX, MY - 0.09, z), steel)
    rig.box(f"brS{j}", (0.20, 0.03, 0.03), (MX, MY + 0.09, z), steel)
    rig.box(f"brE{j}", (0.03, 0.20, 0.03), (MX + 0.09, MY, z), steel)
    rig.box(f"brW{j}", (0.03, 0.20, 0.03), (MX - 0.09, MY, z), steel)
rig.box("dipole_a", (0.46, 0.03, 0.03), (MX, MY, 1.56), steel)
rig.box("dipole_b", (0.03, 0.40, 0.03), (MX, MY, 1.62), steel)
rig.box("sentinel_beacon", (0.07, 0.07, 0.07), (MX, MY, 1.72), beacon)
rig.box("cabinet", (0.22, 0.18, 0.20), (MX + 0.26, MY - 0.02, 0.20), rust)
for gx, gy in ((-0.40, 0.40), (0.42, 0.34), (0.0, -0.42)):   # guy wires
    steps = 7
    for k in range(steps):
        t = (k + 0.5) / steps
        rig.box(f"guy{gx}{gy}{k}",
                (0.018, 0.018, 0.10),
                (MX + (gx - MX) * t, MY + (gy - MY) * t,
                 1.40 * (1 - t) + 0.12), cable,
                rot=(math.atan2(gy - MY, 1.28) * 0.6, 0, 0))

# --- west column: the tank farm and the seized fan -------------------
rig.cylinder("tank_a", 0.17, 0.34, (0, 0, 0), rust, seg=16, arc=math.pi * 2)
rig.cylinder("tank_b", 0.13, 0.26, (0, 0, 0), rust, seg=14, arc=math.pi * 2)
for o in bpy.context.collection.objects:
    if o.name == "tank_a":
        o.location = (-1.10, -0.94, 0.28)
    elif o.name == "tank_b":
        o.location = (-0.78, -1.24, 0.24)
rig.box("cradle_a", (0.40, 0.10, 0.10), (-1.10, -0.94, 0.13), steel)
rig.box("fanhouse", (0.30, 0.30, 0.14), (-1.06, 0.10, 0.17), steel)
rig.cylinder("fanring", 0.11, 0.06, (0, 0, 0), cable, seg=16, arc=math.pi * 2)
for o in bpy.context.collection.objects:
    if o.name == "fanring":
        o.rotation_euler = (0, math.radians(90), 0)
        o.location = (-1.06, 0.10, 0.25)
rig.box("hutch", (0.34, 0.30, 0.26), (-1.20, -2.10, 0.23), house)
rig.box("patch_w1", (0.34, 0.22, 0.004), (-0.86, -1.78, 0.102), patch)
rig.box("patch_w2", (0.20, 0.28, 0.004), (-1.24, -0.30, 0.102), patch)

# --- center column: vents, laundry, the hutch line -------------------
rig.box("vent_a", (0.16, 0.16, 0.22), (-0.30, -0.62, 0.21), steel)
rig.box("vent_b", (0.12, 0.12, 0.16), (0.28, -0.34, 0.18), steel)
for i, lx in enumerate((-0.30, 0.06)):
    rig.box(f"pole{i}a", (0.03, 0.03, 0.34), (lx, -0.90, 0.27), steel)
    rig.box(f"pole{i}b", (0.03, 0.03, 0.34), (lx, -2.10, 0.27), steel)
    rig.box(f"line{i}", (0.02, 1.20, 0.015), (lx, -1.50, 0.42), cable)
    for k in range(4):
        cm = rig.make_material(f"cloth{i}{k}", (0.28 + 0.1 * k, 0.22, 0.18),
                               0.9)
        rig.box(f"cloth{i}{k}", (0.05, 0.10, 0.13),
                (lx, -1.10 - k * 0.28, 0.35), cm)

# --- east pair: capped stacks where the pigeons hold the rim ---------
rig.box("stack_e1", (0.10, 0.10, 0.14), (1.28, -1.72, 0.17), steel)
rig.box("stack_e2", (0.10, 0.10, 0.12), (1.10, -2.16, 0.16), steel)

# the painted arrow at the SOUTH rim of South Roof — the real drop
rig.box("arrow_shaft", (0.06, 0.26, 0.004), (0.10, -2.16, 0.101), paint)
rig.box("arrow_headA", (0.13, 0.07, 0.004), (0.10, -2.34, 0.101), paint,
        rot=(0, 0, math.radians(35)))
rig.box("arrow_headB", (0.13, 0.07, 0.004), (0.10, -2.34, 0.101), paint,
        rot=(0, 0, math.radians(-35)))

catcher = rig.make_material("bgnd", (0.5, 0.5, 0.5), 1.0)
g = rig.box("gplane", (6, 6, 0.01), (0, -1.0, -0.005), catcher)
g.is_shadow_catcher = True

RES = 1600
rig.rig_camera_and_light(ortho=2.6 * RES / 512, target=(0.0, -1.0, 0.5))
rig.render("brackett_roof", res=RES)

rig.clear_scene()
m = rig.make_material("mk", (1, 1, 1), 0.2, emit=(1, 1, 1))
rig.box("marker", (0.04, 0.04, 0.04), (0, 0, 0), m)
rig.rig_camera_and_light(ortho=2.6 * RES / 512, target=(0.0, -1.0, 0.5))
rig.render("calib_brackett_roof", res=RES)
print("landmark brackett roof v2 rendered")
