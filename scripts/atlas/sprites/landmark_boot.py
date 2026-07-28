"""The first landmark hero: Hammett's Boot, entire (§3.5).

    blender --background --python scripts/atlas/sprites/landmark_boot.py

One model for the whole fallen leg — heel shock cylinder, shank camber,
toe cap, Throat and Spur lobes, Lug treads — with the interior glowing
through the open seam and the toe breach, on a shadow-catcher ground.
Local origin = the Heel cell's base center; the registry maps it onto
world anchor (-8,-18,0). Rendered at 1600px (same px/unit as the cell
rig: ortho scales with resolution), ground to 400px by the darkroom.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import rig  # noqa: E402

rig.clear_scene()

hull = rig.make_material("hull", (0.40, 0.25, 0.16), 0.75, noise=0.55)
pale = rig.make_material("pale", (0.60, 0.48, 0.36), 0.8, noise=0.35)
weld = rig.make_material("weld", (0.18, 0.12, 0.09), 0.9)
dark = rig.make_material("dark", (0.02, 0.02, 0.025), 0.9)
glow = rig.make_material("glow", (1.0, 0.6, 0.25), 0.5,
                         emit=(1.0, 0.55, 0.22))
stenc = rig.make_material("stenc", (0.55, 0.50, 0.40), 0.9)
tread = rig.make_material("tread", (0.14, 0.11, 0.09), 0.95, noise=0.3)

# heel: the shock cylinder, vertical
rig.cylinder("heel", 0.46, 1.5, (0.15, 0, 0), hull,
             seg=20, arc=math.pi * 2)
for o in bpy.context.collection.objects:
    if o.name == "heel":
        o.rotation_euler = (0, math.pi / 2, 0)
        o.location = (0.15, 0, 0.6)
# shank camber along x
rig.cylinder("shank", 0.62, 3.4, (2.3, 0, 0), hull, arc=math.pi * 0.92)
rig.cylinder("plate", 0.635, 1.1, (2.0, 0, 0), pale, arc=math.pi * 0.5)
for wx in (1.2, 2.0, 2.8, 3.6):
    rig.cylinder(f"weld{wx}", 0.645, 0.06, (wx, 0, 0), weld,
                 arc=math.pi * 0.88)
# vamp/toe cap
rig.cylinder("toe", 0.55, 1.6, (4.6, 0, 0), hull, arc=math.pi * 0.95)
rig.box("toecap", (0.10, 1.05, 0.52), (5.42, 0, 0.26), hull)
# the seam: dark gap + interior glow between heel and shank
rig.box("seam_dark", (0.22, 1.0, 0.62), (0.62, 0, 0.31), dark)
rig.box("seam_glow", (0.06, 0.72, 0.40), (0.62, 0, 0.30), glow)
# throat lobe (north hip opening) with its own glow mouth
rig.cylinder("throat", 0.42, 1.0, (0.35, 0.85, 0), hull,
             arc=math.pi * 0.9)
rig.box("throat_dark", (0.62, 0.16, 0.5), (0.35, 1.28, 0.25), dark)
rig.box("throat_glow", (0.40, 0.06, 0.32), (0.35, 1.27, 0.22), glow)
# the toe breach: rosette glow on the cap crown
rig.cylinder("breach", 0.17, 0.05, (4.7, 0, 0), glow,
             seg=14, arc=math.pi * 2)
for o in bpy.context.collection.objects:
    if o.name == "breach":
        o.location = (4.7, 0, 0.545)
rig.cylinder("breach_rim", 0.21, 0.06, (4.7, 0, 0), weld,
             seg=14, arc=math.pi * 2)
for o in bpy.context.collection.objects:
    if o.name == "breach_rim":
        o.location = (4.7, 0, 0.535)
# spur horn (northeast) and lug treads (south row)
rig.box("spur", (0.75, 0.16, 0.16), (5.0, 0.85, 0.45), hull,
        rot=(0, math.radians(-18), math.radians(35)))
for i in range(4):
    rig.box(f"lug{i}", (0.26, 0.34, 0.42),
            (3.9 + i * 0.4, -0.82, 0.21), tread)
# stencil plate on the shank crown
rig.box("stencil", (0.5, 0.03, 0.14),
        (1.55, 0.598 * math.cos(math.pi * 0.35),
         0.598 * math.sin(math.pi * 0.35) + 0.02), stenc,
        rot=(math.pi * 0.35 - math.pi / 2, 0, 0))
# ground shadow catcher
catcher = rig.make_material("ground", (0.5, 0.5, 0.5), 1.0)
g = rig.box("gplane", (10, 6, 0.01), (2.5, 0, -0.005), catcher)
g.is_shadow_catcher = True

rig.rig_camera_and_light(ortho=8.125, target=(2.5, 0, 0.4))
rig.render("boot", res=1600)
print("landmark boot rendered")
