"""The Pre-Fab Agridome (§3.5 landmark #3): one dome, as advertised.

    blender --background --python scripts/atlas/sprites/landmark_agridome.py

A single elliptical glass dome over the whole footprint — grow-light
through the panes, a foundation ring, a frame band, one airlock stub.
Local origin = West Growbeds' base center; anchor (1,-18,0).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import rig  # noqa: E402

rig.clear_scene()

frame = rig.make_material("aframe", (0.28, 0.28, 0.24), 0.6, noise=0.3)
glass = rig.make_material("aglass", (0.18, 0.30, 0.20), 0.25)
_nt = glass.node_tree
_bsdf = _nt.nodes["Principled BSDF"]
_wave = _nt.nodes.new("ShaderNodeTexWave")
_wave.inputs["Scale"].default_value = 2.2          # crop rows under glass
_ramp = _nt.nodes.new("ShaderNodeValToRGB")
_ramp.color_ramp.elements[0].position = 0.45
_ramp.color_ramp.elements[0].color = (0.04, 0.16, 0.07, 1)   # leaf dark
_ramp.color_ramp.elements[1].position = 0.62
_ramp.color_ramp.elements[1].color = (0.90, 0.10, 0.72, 1)   # grow-light
_nt.links.new(_wave.outputs["Fac"], _ramp.inputs["Fac"])
_nt.links.new(_ramp.outputs["Color"], _bsdf.inputs["Emission Color"])
_bsdf.inputs["Emission Strength"].default_value = 1.5
warm = rig.make_material("awarm", (0.9, 0.6, 0.3), 0.3,
                         emit=(0.95, 0.6, 0.3))
base = rig.make_material("abase", (0.20, 0.19, 0.16), 0.85, noise=0.35)
dark = rig.make_material("adark", (0.04, 0.05, 0.04), 0.4)


def dome(name, cx, cy, rx, ry, rz, mat, seg=20, rings=7):
    verts, faces = [], []
    for j in range(rings + 1):
        phi = (math.pi / 2) * j / rings
        for i in range(seg):
            th = 2 * math.pi * i / seg
            verts.append((cx + rx * math.cos(phi) * math.cos(th),
                          cy + ry * math.cos(phi) * math.sin(th),
                          rz * math.sin(phi)))
    for j in range(rings):
        for i in range(seg):
            a = j * seg + i
            b = j * seg + (i + 1) % seg
            c = (j + 1) * seg + (i + 1) % seg
            d = (j + 1) * seg + i
            faces.append((a, b, c, d))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(mat)
    bpy.context.collection.objects.link(obj)
    return obj


CX, CY = 1.0, 0.5


def ring(name, cx, cy, rx, ry, z0, z1, mat, seg=28):
    """A true horizontal band: two stacked ellipses, quad walls."""
    verts, faces = [], []
    for z in (z0, z1):
        for i in range(seg):
            th = 2 * math.pi * i / seg
            verts.append((cx + rx * math.cos(th),
                          cy + ry * math.sin(th), z))
    for i in range(seg):
        a, b = i, (i + 1) % seg
        faces.append((a, b, seg + b, seg + a))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(mat)
    bpy.context.collection.objects.link(obj)
    return obj


dome("shell", CX, CY, 1.42, 0.95, 0.80, glass)
ring("foundation", CX, CY, 1.49, 1.02, 0.0, 0.14, base)
ring("band", CX, CY, 1.20, 0.78, 0.38, 0.46, frame)
# one airlock: a squat stub with a single hatch, south base
rig.box("airlock", (0.38, 0.28, 0.24), (CX, CY - 1.02, 0.12), base)
rig.box("hatch", (0.15, 0.04, 0.15), (CX, CY - 1.17, 0.10), dark)
rig.box("hatchglow", (0.18, 0.03, 0.032), (CX, CY - 1.175, 0.22), warm)

# the lot shows its age: fence runs, drifted trash, a cracked pane
fence = rig.make_material("afence", (0.16, 0.15, 0.13), 0.6)
junk = rig.make_material("ajunk", (0.15, 0.13, 0.10), 0.95, noise=0.4)
crackm = rig.make_material("acrack", (0.03, 0.04, 0.03), 0.9)

def fence_run(tag, x0, y0, x1, y1, n, lean=0.0):
    for i in range(n + 1):
        t = i / n
        fx, fy = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        rig.box(f"fp{tag}{i}", (0.03, 0.03, 0.30), (fx, fy, 0.15), fence,
                rot=(lean * ((i % 3) - 1), 0, 0))
    rig.box(f"fr{tag}", (abs(x1 - x0) + 0.06 or 0.05,
                         abs(y1 - y0) + 0.06 or 0.05, 0.025),
            ((x0 + x1) / 2, (y0 + y1) / 2, 0.28), fence)

fence_run("s", -0.35, -0.42, 0.55, -0.42, 3, lean=0.10)   # south, gappy
fence_run("e", 2.42, -0.30, 2.42, 0.9, 4, lean=0.08)      # east run
fence_run("n", 0.9, 1.42, 2.1, 1.42, 4)                   # north stretch
for i, (jx, jy) in enumerate(((-0.30, -0.30), (0.30, -0.34),
                              (2.30, -0.14), (2.28, 0.55), (1.6, 1.34))):
    rig.box(f"junk{i}", (0.13, 0.10, 0.10), (jx, jy, 0.05 + 0.02 * (i % 2)),
            junk, rot=(0, 0, 0.5 * i))

# the crack: a jagged dark seam down the east flank, one clamp plate
import math as _m
for i, (ph, th, rr) in enumerate(((0.78, 0.30, 30), (0.62, 0.36, -20),
                                  (0.48, 0.30, 25), (0.34, 0.38, -15))):
    phi = ph * _m.pi / 2
    theta = th * _m.pi
    cxx = CX + 1.42 * _m.cos(phi) * _m.cos(theta)
    cyy = CY + 0.95 * _m.cos(phi) * _m.sin(theta)
    czz = 0.80 * _m.sin(phi)
    rig.box(f"crack{i}", (0.16, 0.022, 0.022), (cxx, cyy, czz), crackm,
            rot=(0, phi, theta + _m.radians(rr)))
rig.box("clamp", (0.10, 0.05, 0.03),
        (CX + 1.42 * _m.cos(0.55 * _m.pi / 2) * _m.cos(0.33 * _m.pi),
         CY + 0.95 * _m.cos(0.55 * _m.pi / 2) * _m.sin(0.33 * _m.pi),
         0.80 * _m.sin(0.55 * _m.pi / 2)), frame,
        rot=(0, 0.55 * _m.pi / 2, 0.33 * _m.pi))

catcher = rig.make_material("agnd", (0.5, 0.5, 0.5), 1.0)
g = rig.box("gplane", (6, 5, 0.01), (CX, CY, -0.005), catcher)
g.is_shadow_catcher = True

RES = 1200
rig.rig_camera_and_light(ortho=2.6 * RES / 512, target=(CX, CY, 0.4))
rig.render("agridome", res=RES)

rig.clear_scene()
m = rig.make_material("mk", (1, 1, 1), 0.2, emit=(1, 1, 1))
rig.box("marker", (0.04, 0.04, 0.04), (0, 0, 0), m)
rig.rig_camera_and_light(ortho=2.6 * RES / 512, target=(CX, CY, 0.4))
rig.render("calib_agridome", res=RES)
print("landmark agridome rendered")
