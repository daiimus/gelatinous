"""The sprite rig (COLONY_MAPPING_SPEC §3.5 pilot).

Run headless:  blender --background --python scripts/atlas/sprites/rig.py

One fixed camera (2:1 pixel-isometric: azimuth 45°, elevation
atan(1/2)), one hard low warm sun — the Fallout key — and three
procedurally built pilot models: a street cell, a tenement floor cell,
and a Boot hull segment. Each renders to a transparent PNG in
``scripts/atlas/sprites/raw/`` at 4x, for the post chain to grind down.
Everything is code; rerun and the library regenerates.
"""

import math
import os

import bpy

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")
os.makedirs(OUT, exist_ok=True)
RES = 512          # 4x supersample; post downsamples


# ---------------------------------------------------------------- helpers
def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def make_material(name, base, rough=0.8, emit=None, noise=0.0, wet=False):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*base, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    if emit is not None:
        bsdf.inputs["Emission Color"].default_value = (*emit, 1.0)
        bsdf.inputs["Emission Strength"].default_value = 6.0
    if wet:
        tex = nt.nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = 7.0
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position = 0.42
        ramp.color_ramp.elements[0].color = (0.05, 0.05, 0.05, 1)   # puddle
        ramp.color_ramp.elements[1].position = 0.6
        ramp.color_ramp.elements[1].color = (0.55, 0.55, 0.55, 1)   # damp
        nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], bsdf.inputs["Roughness"])
    if noise > 0:
        tex = nt.nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = 18.0
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (*[c * (1 - noise) for c in base], 1)
        ramp.color_ramp.elements[1].color = (*[min(1, c * (1 + noise)) for c in base], 1)
        nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


def box(name, size, loc, mat, rot=(0, 0, 0)):
    mesh = bpy.data.meshes.new(name)
    sx, sy, sz = [s / 2 for s in size]
    verts = [(x, y, z) for x in (-sx, sx) for y in (-sy, sy) for z in (-sz, sz)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 2, 6, 4),
             (1, 5, 7, 3), (0, 4, 5, 1), (2, 3, 7, 6)]
    mesh.from_pydata(verts, [], faces)
    obj = bpy.data.objects.new(name, mesh)
    obj.location = loc
    obj.rotation_euler = rot
    obj.data.materials.append(mat)
    bpy.context.collection.objects.link(obj)
    return obj


def cylinder(name, r, length, loc, mat, axis="X", seg=24, arc=math.pi):
    """Upper half-cylinder along *axis* — the hull camber."""
    verts, faces = [], []
    for i in range(seg + 1):
        a = arc * i / seg
        y, z = r * math.cos(a), r * math.sin(a)
        verts.append((-length / 2, y, z))
        verts.append((length / 2, y, z))
    for i in range(seg):
        j = i * 2
        faces.append((j, j + 1, j + 3, j + 2))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    obj = bpy.data.objects.new(name, mesh)
    obj.location = loc
    obj.data.materials.append(mat)
    bpy.context.collection.objects.link(obj)
    return obj


def rig_camera_and_light():
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = 2.6
    cam = bpy.data.objects.new("cam", cam_data)
    elev = math.atan(0.5)                       # 2:1 pixel isometric
    cam.rotation_euler = (math.pi / 2 - elev, 0, math.radians(45))
    d = 10
    cam.location = (d * math.sin(math.radians(45)) * math.cos(elev),
                    -d * math.cos(math.radians(45)) * math.cos(elev),
                    d * math.sin(elev) + 0.4)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam

    sun_data = bpy.data.lights.new("sun", type="SUN")
    sun_data.energy = 3.2
    sun_data.angle = math.radians(2)            # hard shadow
    sun_data.color = (1.0, 0.78, 0.55)          # sodium worklight
    sun = bpy.data.objects.new("sun", sun_data)
    sun.rotation_euler = (math.radians(55), 0, math.radians(160))
    bpy.context.collection.objects.link(sun)

    fill_data = bpy.data.lights.new("fill", type="SUN")
    fill_data.energy = 1.1
    fill_data.color = (0.35, 0.75, 0.85)        # the teal rim
    fill = bpy.data.objects.new("fill", fill_data)
    fill.rotation_euler = (math.radians(70), 0, math.radians(-30))
    bpy.context.collection.objects.link(fill)

    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.015, 0.025, 0.04, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.6
    bpy.context.scene.world = world


def render(name):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 96
    sc.cycles.use_denoising = True
    sc.render.film_transparent = True
    sc.render.resolution_x = RES
    sc.render.resolution_y = RES
    sc.render.filepath = os.path.join(OUT, f"{name}.png")
    bpy.ops.render.render(write_still=True)
    print(f"rendered {name}")


# ---------------------------------------------------------------- models
def street_cell():
    clear_scene()
    asphalt = make_material("asphalt", (0.075, 0.075, 0.095), 0.3,
                            noise=0.4, wet=True)
    curb = make_material("curb", (0.28, 0.26, 0.24), 0.9, noise=0.3)
    paint = make_material("paint", (0.55, 0.52, 0.42), 0.85)
    iron = make_material("iron", (0.06, 0.06, 0.065), 0.6)
    box("slab", (1, 1, 0.08), (0, 0, 0.04), asphalt)
    box("curb_n", (1, 0.09, 0.13), (0, 0.455, 0.065), curb)
    box("curb_s", (1, 0.09, 0.13), (0, -0.455, 0.065), curb)
    box("lane", (0.62, 0.045, 0.005), (0.02, 0.03, 0.085), paint)
    box("crack", (0.4, 0.015, 0.004), (-0.2, -0.2, 0.084),
        make_material("crack", (0.05, 0.05, 0.055), 1.0))
    cylinder("manhole", 0.09, 0.02, (0.22, -0.18, 0.085), iron,
             seg=16, arc=math.pi * 2)
    hazard_y = make_material("hazY", (0.75, 0.6, 0.1), 0.7)
    hazard_k = make_material("hazK", (0.05, 0.05, 0.05), 0.7)
    for i in range(6):                           # chevron strip on the curb
        box(f"chev{i}", (0.16, 0.05, 0.02), (-0.42 + i * 0.168, 0.46, 0.135),
            hazard_y if i % 2 == 0 else hazard_k)
    stencil = make_material("stencil", (0.6, 0.58, 0.5), 0.9)
    box("arrow", (0.22, 0.06, 0.004), (-0.18, 0.16, 0.085), stencil)
    box("arrow2", (0.06, 0.14, 0.004), (-0.10, 0.13, 0.085), stencil)
    rig_camera_and_light()
    render("street")


def tenement_cell():
    clear_scene()
    concrete = make_material("concrete", (0.13, 0.165, 0.20), 0.85,
                             noise=0.45)
    grime = make_material("grime", (0.09, 0.11, 0.13), 0.95, noise=0.3)
    frame = make_material("frame", (0.07, 0.08, 0.09), 0.8)
    lit = make_material("lit", (0.9, 0.6, 0.3), 0.4, emit=(1.0, 0.62, 0.28))
    dark = make_material("dark", (0.03, 0.035, 0.05), 0.3)
    duct = make_material("duct", (0.30, 0.30, 0.28), 0.5)
    box("block", (1, 1, 1), (0, 0, 0.5), concrete)
    box("grime_band", (1.002, 1.002, 0.16), (0, 0, 0.08), grime)
    windows = [(-0.28, True), (0.0, False), (0.28, True)]
    for wx, litw in windows:                     # south face
        box(f"wfs{wx}", (0.16, 0.02, 0.30), (wx, -0.505, 0.55), frame)
        box(f"wgs{wx}", (0.12, 0.015, 0.24), (wx, -0.512, 0.55),
            lit if litw else dark)
    for wy, litw in [(-0.28, False), (0.0, True), (0.28, False)]:  # east face
        box(f"wfe{wy}", (0.02, 0.16, 0.30), (0.505, wy, 0.55), frame)
        box(f"wge{wy}", (0.015, 0.12, 0.24), (0.512, wy, 0.55),
            lit if litw else dark)
    box("ac", (0.14, 0.10, 0.10), (0.56, 0.28, 0.72), duct)
    pipe = make_material("pipe", (0.22, 0.20, 0.18), 0.55)
    box("conduit1", (0.03, 0.03, 1.0), (0.515, -0.12, 0.5), pipe)
    box("conduit2", (0.03, 0.03, 1.0), (0.515, -0.20, 0.5), pipe)
    box("conduit_elbow", (0.03, 0.14, 0.03), (0.515, -0.13, 0.94), pipe)
    neon = make_material("neon", (0.2, 0.9, 0.9), 0.3,
                         emit=(0.25, 0.95, 1.0))
    box("sign", (0.05, 0.30, 0.07), (-0.515, 0.05, 0.86), neon)
    hazard_y = make_material("thazY", (0.7, 0.55, 0.1), 0.7)
    hazard_k = make_material("thazK", (0.05, 0.05, 0.05), 0.7)
    for i in range(4):                           # dock stripe at the base
        box(f"tchev{i}", (0.02, 0.12, 0.05),
            (-0.512, -0.30 + i * 0.125, 0.05),
            hazard_y if i % 2 == 0 else hazard_k)
    rig_camera_and_light()
    render("tenement")


def hull_cell():
    clear_scene()
    hullm = make_material("hull", (0.42, 0.26, 0.17), 0.75, noise=0.55)
    weld = make_material("weld", (0.20, 0.13, 0.10), 0.9)
    rivet = make_material("rivet", (0.30, 0.20, 0.14), 0.6)
    pale = make_material("pale", (0.62, 0.50, 0.38), 0.8, noise=0.35)
    cylinder("camber", 0.62, 1.0, (0, 0, 0), hullm, arc=math.pi * 0.9)
    cylinder("plate", 0.635, 0.34, (0.0, 0, 0), pale, arc=math.pi * 0.55)
    for wx in (-0.34, 0.02, 0.38):               # weld bands across the camber
        cylinder(f"weld{wx}", 0.645, 0.05, (wx, 0, 0), weld,
                 arc=math.pi * 0.85)
    stencil = make_material("hstencil", (0.55, 0.50, 0.40), 0.9)
    box("marking", (0.20, 0.02, 0.10),
        (-0.18, 0.585 * math.cos(math.pi * 0.35),
         0.585 * math.sin(math.pi * 0.35)), stencil,
        rot=(math.pi * 0.35 - math.pi / 2, 0, 0))
    for i in range(7):                           # rivet row along the crown
        a = math.pi * (0.18 + 0.09 * i)
        box(f"riv{i}", (0.035, 0.035, 0.035),
            (-0.42 + i * 0.14, 0.6 * math.cos(a), 0.6 * math.sin(a)), rivet)
    rig_camera_and_light()
    render("hull")


street_cell()
tenement_cell()
hull_cell()
print("rig complete")
