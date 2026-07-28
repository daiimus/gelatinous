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


def _rotate_scene_90():
    """Spin built geometry a quarter turn about the world origin —
    the E-W tile becomes the N-S tile under the same fixed camera."""
    for o in list(bpy.context.collection.objects):
        x, y, z = o.location
        o.location = (-y, x, z)
        o.rotation_euler.rotate_axis("Z", math.radians(90))


def _oriented(base, build, variant=None):
    """Render *build* as <base>_ew[_n] and <base>_ns[_n]."""
    tail = f"_{variant}" if variant else ""
    for suffix, rot in (("_ew", False), ("_ns", True)):
        clear_scene()
        build()
        if rot:
            _rotate_scene_90()
        rig_camera_and_light()
        render(f"{base}{suffix}{tail}")


def rig_camera_and_light(ortho=2.6, target=(0, 0, 0.4)):
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = ortho
    cam = bpy.data.objects.new("cam", cam_data)
    elev = math.atan(0.5)                       # 2:1 pixel isometric
    # viewer matches the atlas projection: +x right-down, +y LEFT-down
    cam.rotation_euler = (math.pi / 2 - elev, 0, math.radians(135))
    d = 10
    cam.location = (target[0] + d * math.sin(math.radians(45)) * math.cos(elev),
                    target[1] + d * math.cos(math.radians(45)) * math.cos(elev),
                    target[2] + d * math.sin(elev))
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


def render(name, res=RES):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 96
    sc.cycles.use_denoising = True
    sc.render.film_transparent = True
    sc.render.resolution_x = res
    sc.render.resolution_y = res
    sc.render.filepath = os.path.join(OUT, f"{name}.png")
    bpy.ops.render.render(write_still=True)
    print(f"rendered {name}")


# ---------------------------------------------------------------- models
def _street_base():
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
        box(f"wfs{wx}", (0.16, 0.02, 0.30), (wx, 0.505, 0.55), frame)
        box(f"wgs{wx}", (0.12, 0.015, 0.24), (wx, 0.512, 0.55),
            lit if litw else dark)
    for wy, litw in [(-0.28, False), (0.0, True), (0.28, False)]:  # east face
        box(f"wfe{wy}", (0.02, 0.16, 0.30), (0.505, wy, 0.55), frame)
        box(f"wge{wy}", (0.015, 0.12, 0.24), (0.512, wy, 0.55),
            lit if litw else dark)
    box("ac", (0.14, 0.10, 0.10), (0.56, 0.28, 0.72), duct)
    pipe = make_material("pipe", (0.22, 0.20, 0.18), 0.55)
    box("conduit1", (0.03, 0.03, 1.0), (0.515, 0.12, 0.5), pipe)
    box("conduit2", (0.03, 0.03, 1.0), (0.515, 0.20, 0.5), pipe)
    box("conduit_elbow", (0.03, 0.14, 0.03), (0.515, 0.13, 0.94), pipe)
    neon = make_material("neon", (0.2, 0.9, 0.9), 0.3,
                         emit=(0.25, 0.95, 1.0))
    box("sign", (0.30, 0.05, 0.07), (0.05, 0.515, 0.86), neon)
    hazard_y = make_material("thazY", (0.7, 0.55, 0.1), 0.7)
    hazard_k = make_material("thazK", (0.05, 0.05, 0.05), 0.7)
    for i in range(4):                           # dock stripe at the base
        box(f"tchev{i}", (0.12, 0.02, 0.05),
            (-0.30 + i * 0.125, 0.512, 0.05),
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


def roof_cell():
    clear_scene()
    tar = make_material("tar", (0.10, 0.10, 0.10), 0.85, noise=0.4)
    bone = make_material("parapet", (0.42, 0.40, 0.34), 0.9, noise=0.3)
    tank = make_material("tank", (0.35, 0.33, 0.28), 0.6)
    vent = make_material("vent", (0.22, 0.22, 0.20), 0.6)
    box("slab", (1, 1, 0.10), (0, 0, 0.05), tar)
    for loc, size in ((( 0, 0.47, 0.16), (1, 0.06, 0.12)),
                      (( 0, -0.47, 0.16), (1, 0.06, 0.12)),
                      ((0.47, 0, 0.16), (0.06, 0.88, 0.12)),
                      ((-0.47, 0, 0.16), (0.06, 0.88, 0.12))):
        box(f"par{loc}", size, loc, bone)
    cylinder("tankd", 0.16, 0.30, (-0.18, 0.16, 0.24), tank,
             seg=16, arc=math.pi * 2)
    box("vent", (0.16, 0.16, 0.18), (0.24, -0.2, 0.19), vent)
    box("duct", (0.30, 0.08, 0.08), (0.10, -0.2, 0.14), vent)
    rig_camera_and_light()
    render("roof")


def shop_cell():
    clear_scene()
    wall = make_material("swall", (0.20, 0.17, 0.14), 0.85, noise=0.4)
    awn = make_material("awn", (0.45, 0.28, 0.12), 0.8)
    lit = make_material("slit", (0.9, 0.6, 0.3), 0.4, emit=(1.0, 0.6, 0.25))
    neon = make_material("sneon", (0.2, 0.9, 0.9), 0.3, emit=(0.3, 0.95, 1.0))
    dark = make_material("sdark", (0.04, 0.04, 0.05), 0.4)
    box("block", (1, 1, 0.9), (0, 0, 0.45), wall)
    box("front", (0.5, 0.03, 0.5), (-0.1, 0.512, 0.35), dark)   # window
    box("glow", (0.42, 0.01, 0.42), (-0.1, 0.52, 0.35), lit)
    box("door", (0.2, 0.03, 0.6), (0.32, 0.512, 0.3), dark)
    box("awning", (0.75, 0.16, 0.03), (0.02, 0.56, 0.66), awn)
    box("sign", (0.06, 0.05, 0.30), (-0.48, 0.53, 0.75), neon)
    rig_camera_and_light()
    render("shop")


def hotel_cell():
    clear_scene()
    violet = make_material("violet", (0.20, 0.17, 0.28), 0.8, noise=0.35)
    frame = make_material("hframe", (0.08, 0.08, 0.11), 0.7)
    litw = make_material("hlit", (0.9, 0.62, 0.3), 0.4, emit=(1.0, 0.62, 0.3))
    darkw = make_material("hdark", (0.03, 0.03, 0.05), 0.3)
    box("block", (1, 1, 1), (0, 0, 0.5), violet)
    k = 0
    for face, side in (("s", -1), ("e", 1)):
        for i in range(2):
            for j in range(3):
                k += 1
                mat = litw if (k % 3 == 0) else darkw
                if face == "s":
                    box(f"c{face}{i}{j}", (0.20, 0.02, 0.16),
                        (-0.22 + i * 0.44, 0.508, 0.25 + j * 0.28), frame)
                    box(f"g{face}{i}{j}", (0.16, 0.015, 0.12),
                        (-0.22 + i * 0.44, 0.515, 0.25 + j * 0.28), mat)
                else:
                    box(f"c{face}{i}{j}", (0.02, 0.20, 0.16),
                        (0.508, -0.22 + i * 0.44, 0.25 + j * 0.28), frame)
                    box(f"g{face}{i}{j}", (0.015, 0.16, 0.12),
                        (0.515, -0.22 + i * 0.44, 0.25 + j * 0.28), mat)
    rig_camera_and_light()
    render("hotel")


def generic_cell():
    clear_scene()
    m = make_material("gen", (0.17, 0.16, 0.19), 0.9, noise=0.4)
    trim = make_material("gtrim", (0.10, 0.10, 0.12), 0.8)
    box("block", (1, 1, 0.8), (0, 0, 0.4), m)
    box("trim", (1.004, 1.004, 0.08), (0, 0, 0.76), trim)
    rig_camera_and_light()
    render("generic")


def _street_patched():
    """Patched and stained — a street that has been repaired in anger."""
    asphalt = make_material("asphalt1", (0.075, 0.075, 0.095), 0.3,
                            noise=0.4, wet=True)
    patch = make_material("patch", (0.12, 0.11, 0.12), 0.8, noise=0.3)
    curb = make_material("curb1", (0.28, 0.26, 0.24), 0.9, noise=0.3)
    oil = make_material("oil", (0.03, 0.035, 0.05), 0.15)
    box("slab", (1, 1, 0.08), (0, 0, 0.04), asphalt)
    box("curb_n", (1, 0.09, 0.13), (0, 0.455, 0.065), curb)
    box("curb_s", (1, 0.09, 0.13), (0, -0.455, 0.065), curb)
    box("patch1", (0.34, 0.26, 0.004), (-0.16, 0.10, 0.084), patch)
    box("patch2", (0.22, 0.18, 0.004), (0.24, -0.14, 0.084), patch)
    cylinder("oilstain", 0.14, 0.006, (0.05, 0.22, 0.083), oil,
             seg=14, arc=math.pi * 2)


def _street_cracked():
    """Cracked and littered — the colony's deferred maintenance."""
    asphalt = make_material("asphalt2", (0.08, 0.078, 0.09), 0.45,
                            noise=0.5, wet=True)
    curb = make_material("curb2", (0.26, 0.24, 0.22), 0.9, noise=0.3)
    crackm = make_material("crack2", (0.04, 0.04, 0.05), 1.0)
    debris = make_material("debris", (0.20, 0.16, 0.12), 0.95, noise=0.4)
    box("slab", (1, 1, 0.08), (0, 0, 0.04), asphalt)
    box("curb_n", (1, 0.09, 0.13), (0, 0.455, 0.065), curb)
    box("curb_s", (1, 0.09, 0.13), (0, -0.455, 0.065), curb)
    box("crackA", (0.5, 0.018, 0.004), (-0.1, 0.05, 0.084), crackm,
        rot=(0, 0, math.radians(20)))
    box("crackB", (0.34, 0.015, 0.004), (0.12, -0.08, 0.084), crackm,
        rot=(0, 0, math.radians(-35)))
    box("crackC", (0.2, 0.012, 0.004), (-0.3, -0.22, 0.084), crackm,
        rot=(0, 0, math.radians(60)))
    for i, (dx, dy) in enumerate([(0.3, 0.3), (-0.35, -0.3), (0.1, -0.35)]):
        box(f"junk{i}", (0.07, 0.05, 0.05), (dx, dy, 0.10), debris)


def _alley_base():
    """The gnarly cut-through: dumpster, cables, steam, standing water."""
    ground = make_material("agnd", (0.06, 0.062, 0.07), 0.25,
                           noise=0.5, wet=True)
    grime = make_material("agrime", (0.09, 0.10, 0.08), 0.95, noise=0.5)
    dump = make_material("dump", (0.14, 0.20, 0.16), 0.7, noise=0.3)
    rust_lid = make_material("dlid", (0.30, 0.18, 0.10), 0.8)
    trash = make_material("trash", (0.16, 0.14, 0.10), 0.95, noise=0.4)
    cable = make_material("cable", (0.05, 0.05, 0.055), 0.6)
    steam = make_material("steamv", (0.25, 0.25, 0.24), 0.6)
    box("slab", (1, 1, 0.06), (0, 0, 0.03), ground)
    box("gutter", (1, 0.12, 0.02), (0, -0.40, 0.05), grime)
    box("dumpster", (0.42, 0.22, 0.26), (-0.22, 0.30, 0.19), dump)
    box("dumplid", (0.44, 0.24, 0.03), (-0.22, 0.30, 0.335), rust_lid,
        rot=(math.radians(-8), 0, 0))
    for i, (dx, dy) in enumerate([(0.05, 0.32), (0.32, 0.18),
                                  (0.25, -0.25)]):
        box(f"bag{i}", (0.10, 0.09, 0.09), (dx, dy, 0.10), trash)
    cylinder("steamvent", 0.07, 0.05, (0.38, -0.30, 0), steam,
             seg=12, arc=math.pi * 2)
    for o in bpy.context.collection.objects:
        if o.name == "steamvent":
            o.location = (0.38, -0.30, 0.065)
    for i in range(3):                       # sagging cable shadows overhead
        box(f"cab{i}", (1.05, 0.012, 0.012), (0, -0.1 + i * 0.16, 0.9 - i * 0.06),
            cable, rot=(0, 0, math.radians(-6 + i * 5)))


def _person(idx, loc, coat, r):
    torso = box(f"p{idx}t", (0.07, 0.055, 0.17), (loc[0], loc[1], 0.20), coat,
                rot=(0, 0, r))
    head = make_material(f"p{idx}h", (0.55, 0.44, 0.36), 0.8)
    box(f"p{idx}hd", (0.045, 0.045, 0.05), (loc[0], loc[1], 0.32), head)
    return torso


def _crowd_scene(name, spots):
    clear_scene()
    coats = [(0.28, 0.16, 0.10), (0.12, 0.16, 0.18), (0.20, 0.19, 0.12),
             (0.10, 0.10, 0.12)]
    for i, (x, y, rot) in enumerate(spots):
        coat = make_material(f"coat{name}{i}", coats[i % len(coats)],
                             0.85, noise=0.25)
        _person(f"{name}{i}", (x, y), coat, math.radians(rot))
    catcher = make_material(f"gnd{name}", (0.5, 0.5, 0.5), 1.0)
    g = box("gplane", (2, 2, 0.01), (0, 0, -0.005), catcher)
    g.is_shadow_catcher = True
    rig_camera_and_light()
    render(name)


def crowd_sprites():
    _crowd_scene("crowd_0", [(-0.06, 0.02, 15), (0.08, -0.05, -30)])
    _crowd_scene("crowd_1", [(-0.10, 0.06, 40), (0.04, 0.0, -10),
                             (0.12, -0.10, 75)])
    _crowd_scene("crowd_2", [(0.0, 0.0, 55)])


def _hauler(rotz):
    clear_scene()
    body = make_material("hbody", (0.22, 0.16, 0.10), 0.6, noise=0.3)
    cab = make_material("hcab", (0.16, 0.18, 0.16), 0.5)
    glass = make_material("hglass", (0.05, 0.08, 0.10), 0.15)
    tire = make_material("tire", (0.04, 0.04, 0.045), 0.9)
    hazY = make_material("hhazY", (0.7, 0.55, 0.1), 0.7)
    lamp = make_material("hlamp", (1.0, 0.75, 0.4), 0.4,
                         emit=(1.0, 0.7, 0.35))
    rz = math.radians(rotz)
    def R(x, y):
        c, s_ = math.cos(rz), math.sin(rz)
        return (x * c - y * s_, x * s_ + y * c)
    def rbox(n, size, loc, mat, extra_rz=0.0):
        x, y = R(loc[0], loc[1])
        sz = size if rotz == 0 else (size[1], size[0], size[2])             if abs(rotz) == 90 else size
        box(n, sz, (x, y, loc[2]), mat, rot=(0, 0, rz + extra_rz))
    rbox("bed", (0.55, 0.30, 0.18), (-0.10, 0, 0.20), body)
    rbox("cab", (0.20, 0.28, 0.24), (0.28, 0, 0.23), cab)
    rbox("glassf", (0.02, 0.24, 0.10), (0.385, 0, 0.28), glass)
    rbox("stripe", (0.04, 0.30, 0.06), (-0.365, 0, 0.20), hazY)
    rbox("lampL", (0.02, 0.05, 0.04), (0.385, 0.09, 0.16), lamp)
    rbox("lampR", (0.02, 0.05, 0.04), (0.385, -0.09, 0.16), lamp)
    for i, wx in enumerate((-0.28, 0.02, 0.28)):
        for side in (-0.17, 0.17):
            x, y = R(wx, side)
            box(f"w{i}{side}", (0.10, 0.04, 0.10), (x, y, 0.06), tire,
                rot=(0, 0, rz))
    catcher = make_material("hgnd", (0.5, 0.5, 0.5), 1.0)
    g = box("gplane", (2.4, 2.4, 0.01), (0, 0, -0.005), catcher)
    g.is_shadow_catcher = True
    rig_camera_and_light()


def vehicle_sprites():
    _hauler(0);  render("hauler_x")
    _hauler(90); render("hauler_y")
    # the cart: small utility rover, orientation-agnostic
    clear_scene()
    body = make_material("cbody", (0.18, 0.20, 0.14), 0.6, noise=0.3)
    tire = make_material("ctire", (0.04, 0.04, 0.045), 0.9)
    box("cbed", (0.30, 0.20, 0.14), (0, 0, 0.15), body)
    box("cbar", (0.03, 0.18, 0.16), (0.14, 0, 0.30), body)
    for wx in (-0.10, 0.10):
        for wy in (-0.12, 0.12):
            box(f"cw{wx}{wy}", (0.07, 0.03, 0.07), (wx, wy, 0.05), tire)
    catcher = make_material("cgnd", (0.5, 0.5, 0.5), 1.0)
    g = box("gplane", (2, 2, 0.01), (0, 0, -0.005), catcher)
    g.is_shadow_catcher = True
    rig_camera_and_light()
    render("cart")


def _prop_scene(name, build):
    clear_scene()
    build()
    catcher = make_material(f"pg{name}", (0.5, 0.5, 0.5), 1.0)
    g = box("gplane", (2, 2, 0.01), (0, 0, -0.005), catcher)
    g.is_shadow_catcher = True
    rig_camera_and_light()
    render(name)


def prop_sprites():
    hazY = lambda: make_material("pbY", (0.7, 0.55, 0.1), 0.8)
    hazK = lambda: make_material("pbK", (0.05, 0.05, 0.05), 0.8)
    def barrier(rot):
        def build():
            y, k = hazY(), hazK()
            for i in range(3):
                m = y if i % 2 == 0 else k
                if rot == 0:               # blocks an E-W lane: runs N-S
                    box(f"b{i}", (0.05, 0.14, 0.05), (0, -0.14 + i * 0.14, 0.22), m)
                else:
                    box(f"b{i}", (0.14, 0.05, 0.05), (-0.14 + i * 0.14, 0, 0.22), m)
            if rot == 0:
                box("legA", (0.03, 0.03, 0.2), (0, -0.16, 0.1), k)
                box("legB", (0.03, 0.03, 0.2), (0, 0.16, 0.1), k)
            else:
                box("legA", (0.03, 0.03, 0.2), (-0.16, 0, 0.1), k)
                box("legB", (0.03, 0.03, 0.2), (0.16, 0, 0.1), k)
        return build
    _prop_scene("barrier_x", barrier(0))
    _prop_scene("barrier_y", barrier(90))

    def crates():
        m = make_material("crate", (0.24, 0.18, 0.11), 0.85, noise=0.3)
        box("c1", (0.16, 0.16, 0.14), (0, 0.02, 0.07), m)
        box("c2", (0.14, 0.14, 0.12), (0.14, -0.1, 0.06), m)
        box("c3", (0.12, 0.12, 0.11), (0.04, -0.02, 0.20), m)
    _prop_scene("crates", crates)

    def barrels():
        m = make_material("barrel", (0.16, 0.20, 0.22), 0.6, noise=0.3)
        r = make_material("barrelr", (0.30, 0.16, 0.09), 0.75)
        for i, (dx, dy, mm) in enumerate([(0, 0.04, m), (0.15, -0.08, r)]):
            cylinder(f"bl{i}", 0.08, 0.03, (dx, dy, 0), mm,
                     seg=12, arc=math.pi * 2)
            for o in bpy.context.collection.objects:
                if o.name == f"bl{i}":
                    o.scale = (1, 1, 8)
                    o.location = (dx, dy, 0.12)
    _prop_scene("barrels", barrels)


def _van(rotz):
    def build():
        body = make_material("vbody", (0.15, 0.19, 0.20), 0.55, noise=0.25)
        glass = make_material("vglass", (0.05, 0.08, 0.10), 0.15)
        tire = make_material("vtire", (0.04, 0.04, 0.045), 0.9)
        rz = math.radians(rotz)
        c, s_ = math.cos(rz), math.sin(rz)
        R = lambda x, y: (x * c - y * s_, x * s_ + y * c)
        def rbox(n, size, loc, mat):
            x, y = R(loc[0], loc[1])
            sz = (size[1], size[0], size[2]) if rotz == 90 else size
            box(n, sz, (x, y, loc[2]), mat, rot=(0, 0, rz))
        rbox("shell", (0.52, 0.24, 0.24), (0, 0, 0.20), body)
        rbox("wind", (0.02, 0.20, 0.09), (0.265, 0, 0.26), glass)
        for wx in (-0.16, 0.16):
            for side in (-0.14, 0.14):
                x, y = R(wx, side)
                box(f"vw{wx}{side}", (0.09, 0.03, 0.09), (x, y, 0.05), tire)
    return build


def vehicle_variety():
    _prop_scene("van_x", _van(0))
    _prop_scene("van_y", _van(90))

    def wreck():
        body = make_material("wbody", (0.10, 0.09, 0.08), 0.95, noise=0.5)
        char = make_material("wchar", (0.04, 0.035, 0.03), 1.0)
        box("hulk", (0.48, 0.22, 0.14), (0, 0, 0.10), body,
            rot=(0, math.radians(4), math.radians(20)))
        box("cabin", (0.18, 0.20, 0.10), (0.10, 0.02, 0.20), char,
            rot=(0, 0, math.radians(20)))
    _prop_scene("wreck", wreck)


def tenement_variant_1():
    """Different rhythm: balcony slab, strung laundry, two-pane windows."""
    clear_scene()
    concrete = make_material("concrete1", (0.14, 0.17, 0.21), 0.85,
                             noise=0.45)
    frame = make_material("frame1", (0.07, 0.08, 0.09), 0.8)
    lit = make_material("lit1", (0.9, 0.6, 0.3), 0.4, emit=(1.0, 0.62, 0.28))
    dark = make_material("dark1", (0.03, 0.035, 0.05), 0.3)
    rail = make_material("rail1", (0.20, 0.18, 0.16), 0.6)
    box("block", (1, 1, 1), (0, 0, 0.5), concrete)
    for wx, litw in [(-0.20, True), (0.22, False)]:      # south, two wide
        box(f"wf{wx}", (0.24, 0.02, 0.34), (wx, 0.505, 0.52), frame)
        box(f"wg{wx}", (0.20, 0.015, 0.28), (wx, 0.512, 0.52),
            lit if litw else dark)
    box("balc", (0.34, 0.10, 0.03), (0.51, -0.20, 0.36), rail)
    box("balcr", (0.34, 0.02, 0.10), (0.51, -0.245, 0.43), rail)
    for we, litw in [(-0.24, False), (0.10, True)]:      # east
        box(f"we{we}", (0.02, 0.20, 0.30), (0.505, we, 0.60), frame)
        box(f"wge{we}", (0.015, 0.16, 0.24), (0.512, we, 0.60),
            lit if litw else dark)
    line = make_material("lline", (0.35, 0.33, 0.30), 0.8)
    box("laundry", (0.44, 0.02, 0.015), (0.0, 0.51, 0.88), line)
    for i in range(3):
        cm = make_material(f"cloth{i}", (0.25 + i * 0.1, 0.2, 0.15), 0.9)
        box(f"cl{i}", (0.07, 0.015, 0.09), (-0.14 + i * 0.14, 0.515, 0.83), cm)
    rig_camera_and_light()
    render("tenement_1")


def roof_variant_1():
    """Skylight and pipework instead of the tank."""
    clear_scene()
    tar = make_material("tar1", (0.11, 0.10, 0.10), 0.85, noise=0.4)
    bone = make_material("parapet1", (0.42, 0.40, 0.34), 0.9, noise=0.3)
    glass = make_material("sky1", (0.20, 0.45, 0.50), 0.2,
                          emit=(0.3, 0.6, 0.65))
    pipe = make_material("rpipe", (0.24, 0.22, 0.20), 0.55)
    box("slab", (1, 1, 0.10), (0, 0, 0.05), tar)
    for loc, size in ((( 0, 0.47, 0.16), (1, 0.06, 0.12)),
                      (( 0, -0.47, 0.16), (1, 0.06, 0.12)),
                      ((0.47, 0, 0.16), (0.06, 0.88, 0.12)),
                      ((-0.47, 0, 0.16), (0.06, 0.88, 0.12))):
        box(f"par{loc}", size, loc, bone)
    box("skylight", (0.30, 0.24, 0.06), (-0.14, 0.10, 0.13), glass,
        rot=(0, math.radians(-8), 0))
    box("pipe1", (0.50, 0.05, 0.05), (0.10, -0.24, 0.13), pipe)
    box("pipe2", (0.05, 0.05, 0.22), (0.33, -0.24, 0.21), pipe)
    rig_camera_and_light()
    render("roof_1")


def _street_intersection():
    """The crossing: orientation-free — corner nubs, no through-curbs."""
    asphalt = make_material("asphalti", (0.075, 0.075, 0.095), 0.3,
                            noise=0.4, wet=True)
    curb = make_material("curbi", (0.28, 0.26, 0.24), 0.9, noise=0.3)
    iron = make_material("ironi", (0.06, 0.06, 0.065), 0.6)
    box("slab", (1, 1, 0.08), (0, 0, 0.04), asphalt)
    for cx in (-0.44, 0.44):
        for cy in (-0.44, 0.44):
            box(f"nub{cx}{cy}", (0.12, 0.12, 0.13), (cx, cy, 0.065), curb)
    cylinder("manhole", 0.09, 0.02, (0.10, -0.08, 0.085), iron,
             seg=16, arc=math.pi * 2)


def street_tiles():
    _oriented("street", _street_base)
    _oriented("street", _street_patched, 1)
    _oriented("street", _street_cracked, 2)
    clear_scene(); _street_intersection(); rig_camera_and_light()
    render("street_ix")
    _oriented("alley", _alley_base)


def constab_cell():
    """The law: slab concrete, barred slits, floodlight, orange trim."""
    clear_scene()
    slab = make_material("cslab", (0.22, 0.21, 0.19), 0.9, noise=0.3)
    bar = make_material("cbar", (0.10, 0.10, 0.11), 0.6)
    orange = make_material("corange", (0.75, 0.35, 0.08), 0.7)
    flood = make_material("cflood", (1.0, 0.95, 0.85), 0.4,
                          emit=(1.0, 0.95, 0.8))
    box("block", (1, 1, 0.95), (0, 0, 0.475), slab)
    box("trim", (1.004, 1.004, 0.06), (0, 0, 0.90), orange)
    for wy in (-0.25, 0.05, 0.35):               # barred slit windows, north
        box(f"slit{wy}", (0.14, 0.02, 0.08), (wy, 0.508, 0.62), bar)
        box(f"slitg{wy}", (0.10, 0.015, 0.05), (wy, 0.515, 0.62),
            make_material(f"sg{wy}", (0.03, 0.04, 0.05), 0.3))
    for we in (-0.20, 0.20):                     # east slits
        box(f"esl{we}", (0.02, 0.14, 0.08), (0.508, we, 0.62), bar)
    box("floodm", (0.05, 0.05, 0.16), (0.42, 0.42, 1.0), bar)
    box("floodh", (0.09, 0.09, 0.06), (0.42, 0.42, 1.10), flood)
    rig_camera_and_light()
    render("constab")


def cryo_cell():
    """Thawn-Harrison: corporate frost — teal glass, chrome mullions."""
    clear_scene()
    frame = make_material("cryof", (0.28, 0.30, 0.32), 0.4)
    glass = make_material("cryog", (0.10, 0.22, 0.26), 0.15,
                          emit=(0.12, 0.30, 0.34))
    frost = make_material("cryow", (0.55, 0.62, 0.65), 0.7, noise=0.3)
    box("block", (1, 1, 1), (0, 0, 0.5), frame)
    for face, side in (("n", 1), ("e", 1)):
        for i in range(3):
            if face == "n":
                box(f"gn{i}", (0.26, 0.02, 0.78), (-0.30 + i * 0.30, 0.508, 0.52), glass)
            else:
                box(f"ge{i}", (0.02, 0.26, 0.78), (0.508, -0.30 + i * 0.30, 0.52), glass)
    box("cap", (1.006, 1.006, 0.08), (0, 0, 0.99), frost)
    rig_camera_and_light()
    render("cryo")


def lounge_cell():
    """Helix Lounge: black-violet velvet box, big neon helix."""
    clear_scene()
    wall = make_material("lwall", (0.10, 0.07, 0.13), 0.75, noise=0.3)
    neonp = make_material("lneonp", (0.85, 0.3, 0.8), 0.3,
                          emit=(0.95, 0.35, 0.9))
    neonc = make_material("lneonc", (0.2, 0.9, 0.9), 0.3,
                          emit=(0.3, 0.95, 1.0))
    dark = make_material("ldark", (0.03, 0.03, 0.04), 0.4)
    box("block", (1, 1, 0.9), (0, 0, 0.45), wall)
    box("door", (0.22, 0.03, 0.55), (-0.25, 0.512, 0.28), dark)
    for i in range(4):                            # the helix: staggered strokes
        box(f"nx{i}", (0.05, 0.04, 0.16),
            (0.18 + (i % 2) * 0.14, 0.515, 0.30 + i * 0.15),
            neonp if i % 2 == 0 else neonc)
    box("marquee", (0.6, 0.05, 0.04), (0.0, 0.53, 0.78), neonc)
    rig_camera_and_light()
    render("lounge")


def bar_cell():
    """The colony bar: warm brick, hanging sign, window glow."""
    clear_scene()
    brick = make_material("bbrick", (0.24, 0.13, 0.09), 0.85, noise=0.4)
    glow = make_material("bglow", (0.9, 0.6, 0.3), 0.4, emit=(1.0, 0.6, 0.25))
    dark = make_material("bdark", (0.04, 0.04, 0.05), 0.4)
    signm = make_material("bsign", (0.5, 0.38, 0.15), 0.6)
    box("block", (1, 1, 0.85), (0, 0, 0.425), brick)
    box("win", (0.4, 0.03, 0.34), (-0.15, 0.512, 0.42), dark)
    box("wing", (0.34, 0.015, 0.28), (-0.15, 0.52, 0.42), glow)
    box("door", (0.2, 0.03, 0.58), (0.28, 0.512, 0.29), dark)
    box("signarm", (0.03, 0.16, 0.03), (0.44, 0.55, 0.72), signm)
    box("sign", (0.14, 0.03, 0.12), (0.44, 0.62, 0.62), glow)
    rig_camera_and_light()
    render("bar")


def pad_cell():
    """The Colonial Landing Pad: markings, blast scoring, beacons."""
    clear_scene()
    deck = make_material("pdeck", (0.16, 0.16, 0.17), 0.6, noise=0.35)
    mark = make_material("pmark", (0.6, 0.55, 0.4), 0.8)
    scorch = make_material("pscorch", (0.05, 0.05, 0.05), 0.9)
    bcn = make_material("pbcn", (0.9, 0.4, 0.2), 0.4, emit=(1.0, 0.45, 0.2))
    box("slab", (1, 1, 0.10), (0, 0, 0.05), deck)
    cylinder("ring", 0.34, 0.01, (0, 0, 0), mark, seg=24, arc=math.pi * 2)
    for o in bpy.context.collection.objects:
        if o.name == "ring":
            o.location = (0, 0, 0.105)
    cylinder("score", 0.2, 0.008, (0.1, -0.1, 0), scorch,
             seg=16, arc=math.pi * 2)
    for o in bpy.context.collection.objects:
        if o.name == "score":
            o.location = (0.1, -0.1, 0.104)
    for cx, cy in ((-0.44, -0.44), (0.44, -0.44), (-0.44, 0.44), (0.44, 0.44)):
        box(f"b{cx}{cy}", (0.05, 0.05, 0.07), (cx, cy, 0.14), bcn)
    rig_camera_and_light()
    render("pad")


def shuttered_cell():
    """The Shuttered Storefront: boarded, chained, TO LET."""
    clear_scene()
    wall = make_material("shwall", (0.18, 0.16, 0.14), 0.9, noise=0.4)
    board = make_material("shboard", (0.28, 0.20, 0.12), 0.95, noise=0.35)
    chain = make_material("shchain", (0.10, 0.10, 0.11), 0.5)
    paper = make_material("shpaper", (0.55, 0.52, 0.44), 0.9)
    box("block", (1, 1, 0.85), (0, 0, 0.425), wall)
    for i in range(3):                            # boards over the front
        box(f"bd{i}", (0.5, 0.03, 0.10), (-0.05, 0.512, 0.25 + i * 0.16),
            board, rot=(0, 0, math.radians(-4 + i * 4)))
    box("chainbar", (0.4, 0.02, 0.03), (-0.05, 0.52, 0.52), chain)
    box("tolet", (0.14, 0.015, 0.10), (0.32, 0.52, 0.60), paper)
    rig_camera_and_light()
    render("shuttered")


def medical_cell():
    """The colony's medicine: clinical panels, red-cross ghost, lit
    intake."""
    clear_scene()
    panel = make_material("mpanel", (0.42, 0.44, 0.43), 0.8, noise=0.25)
    grime = make_material("mgrime", (0.22, 0.24, 0.23), 0.9, noise=0.4)
    cross = make_material("mcross", (0.55, 0.16, 0.12), 0.85)
    intake = make_material("mintake", (0.9, 0.95, 0.9), 0.4,
                           emit=(0.85, 0.95, 0.85))
    dark = make_material("mdark", (0.04, 0.05, 0.05), 0.4)
    box("block", (1, 1, 0.9), (0, 0, 0.45), panel)
    box("grimeband", (1.004, 1.004, 0.14), (0, 0, 0.07), grime)
    box("crossV", (0.06, 0.02, 0.20), (0.22, 0.508, 0.62), cross)
    box("crossH", (0.18, 0.02, 0.07), (0.22, 0.508, 0.62), cross)
    box("intakedoor", (0.26, 0.03, 0.55), (-0.20, 0.512, 0.28), dark)
    box("intakelight", (0.30, 0.02, 0.05), (-0.20, 0.52, 0.60), intake)
    box("ewin", (0.02, 0.30, 0.22), (0.508, -0.05, 0.55), dark)
    rig_camera_and_light()
    render("medical")


def main():
    street_tiles()
    tenement_cell()
    hull_cell()
    roof_cell()
    shop_cell()
    hotel_cell()
    generic_cell()
    constab_cell()
    cryo_cell()
    lounge_cell()
    bar_cell()
    pad_cell()
    shuttered_cell()
    medical_cell()
    crowd_sprites()
    vehicle_sprites()
    prop_sprites()
    vehicle_variety()
    tenement_variant_1()
    roof_variant_1()
    print("rig complete")


if __name__ == "__main__":
    main()
