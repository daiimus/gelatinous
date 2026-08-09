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
FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "MonaspaceXenon.ttf")   # brand/heading flavour, for signage


# ---------------------------------------------------------------- helpers
def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def make_material(name, base, rough=0.8, emit=None, noise=0.0,
                  wet=False, emit_strength=6.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*base, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    if emit is not None:
        bsdf.inputs["Emission Color"].default_value = (*emit, 1.0)
        bsdf.inputs["Emission Strength"].default_value = emit_strength
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


def _rotate_meshes_90(pivot=(0.0, 0.0)):
    """Quarter-turn the MODEL only — camera and lights stay world-fixed.
    Rendering after each turn yields the next compass view (v1..v3):
    the sun stays put, so far faces sit in honest shadow.

    Rotation is about *pivot* (the camera target's xy) — long heroes
    whose content is offset from the local origin would otherwise swing
    out of the fixed frame. The calibration marker rides along, which
    is why hero origins are measured PER VIEW."""
    px, py = pivot
    for o in list(bpy.context.collection.objects):
        if o.type in ("CAMERA", "LIGHT"):
            continue
        x, y, z = o.location
        o.location = (px - (y - py), py + (x - px), z)
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


LAST_TARGET = (0.0, 0.0)


def rig_camera_and_light(ortho=2.6, target=(0, 0, 0.4)):
    global LAST_TARGET
    LAST_TARGET = (target[0], target[1])
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
    # The other three compass views: rotate the model about the camera
    # target under the fixed camera and shoot again. Calibration markers
    # ride the rotation, so hero origins are measured per view.
    if os.environ.get("RIG_VIEWS") == "0":
        return
    for k in (1, 2, 3):
        _rotate_meshes_90(LAST_TARGET)
        vdir = os.path.join(OUT, f"v{k}")
        os.makedirs(vdir, exist_ok=True)
        sc.render.filepath = os.path.join(vdir, f"{name}.png")
        bpy.ops.render.render(write_still=True)
    _rotate_meshes_90(LAST_TARGET)   # fourth turn: back where we started
    print(f"rendered {name} v1-v3")


# ---------------------------------------------------------------- models
def _street_base():
    asphalt = make_material("asphalt", (0.075, 0.075, 0.095), 0.3,
                            noise=0.4, wet=True)
    curb = make_material("curb", (0.17, 0.16, 0.15), 0.9, noise=0.3)
    paint = make_material("paint", (0.55, 0.52, 0.42), 0.85)
    iron = make_material("iron", (0.06, 0.06, 0.065), 0.6)
    box("slab", (1, 1, 0.08), (0, 0, 0.04), asphalt)
    box("curb_n", (1, 0.07, 0.055), (0, 0.465, 0.055), curb)
    box("curb_s", (1, 0.07, 0.055), (0, -0.465, 0.055), curb)
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
    # the far faces: same bones, sparser life — these show when the
    # atlas rotates, and emission is the only light on the shadow side
    for wx, litw in [(-0.28, False), (0.0, True), (0.28, False)]:
        box(f"wfn{wx}", (0.16, 0.02, 0.30), (wx, -0.505, 0.55), frame)
        box(f"wgn{wx}", (0.12, 0.015, 0.24), (wx, -0.512, 0.55),
            lit if litw else dark)
    for wy, litw in [(-0.28, True), (0.28, False)]:
        box(f"wfw{wy}", (0.02, 0.16, 0.30), (-0.505, wy, 0.55), frame)
        box(f"wgw{wy}", (0.015, 0.12, 0.24), (-0.512, wy, 0.55),
            lit if litw else dark)
    box("ac_w", (0.14, 0.10, 0.10), (-0.56, -0.20, 0.45), duct)
    box("downpipe", (0.03, 0.03, 1.0), (-0.515, 0.30, 0.5), pipe)
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
    tar = make_material("tar", (0.14, 0.135, 0.13), 0.85, noise=0.4)
    bone = make_material("parapet", (0.23, 0.22, 0.19), 0.9, noise=0.3)
    tank = make_material("tank", (0.35, 0.33, 0.28), 0.6)
    vent = make_material("vent", (0.22, 0.22, 0.20), 0.6)
    box("slab", (1, 1, 0.10), (0, 0, 0.05), tar)
    for loc, size in ((( 0, 0.47, 0.115), (1, 0.05, 0.07)),
                      (( 0, -0.47, 0.115), (1, 0.05, 0.07)),
                      ((0.47, 0, 0.115), (0.05, 0.88, 0.07)),
                      ((-0.47, 0, 0.115), (0.05, 0.88, 0.07))):
        box(f"par{loc}", size, loc, bone)
    cylinder("tankd", 0.16, 0.30, (-0.18, 0.16, 0.24), tank,
             seg=16, arc=math.pi * 2)
    box("vent", (0.16, 0.16, 0.18), (0.24, -0.2, 0.19), vent)
    box("duct", (0.30, 0.08, 0.08), (0.10, -0.2, 0.14), vent)
    rig_camera_and_light()
    render("roof")


def _disc(name, r, loc, mat, seg=16):
    """A flat n-gon disc facing ±y (both windings, so it reads from
    either side) — the porthole primitive."""
    verts = [(loc[0] + r * math.cos(2 * math.pi * i / seg), loc[1],
              loc[2] + r * math.sin(2 * math.pi * i / seg))
             for i in range(seg)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], [tuple(range(seg)),
                                 tuple(reversed(range(seg)))])
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(mat)
    bpy.context.collection.objects.link(obj)
    return obj


def _disc_x(name, r, loc, mat, seg=16):
    """The same disc facing ±x (for the east/west hull faces)."""
    verts = [(loc[0], loc[1] + r * math.cos(2 * math.pi * i / seg),
              loc[2] + r * math.sin(2 * math.pi * i / seg))
             for i in range(seg)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], [tuple(range(seg)),
                                 tuple(reversed(range(seg)))])
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(mat)
    bpy.context.collection.objects.link(obj)
    return obj


def _liner_base():
    """One prefab module of the Halcyon's hull — a Slowboat liner grown
    into a walk-up. Painted-steel plate (bone livery), corner frame
    posts and top/bottom flanges so each storey reads as a bolted-on
    component, a teal boot-stripe band, and PORTHOLES where a tenement
    would have windows. Returns the shared materials for variants."""
    plate = make_material("lnplate", (0.40, 0.41, 0.37), 0.6, noise=0.35)
    teal = make_material("lnteal", (0.10, 0.30, 0.32), 0.55, noise=0.25)
    steel = make_material("lnsteel", (0.14, 0.15, 0.15), 0.6, noise=0.2)
    ring = make_material("lnring", (0.35, 0.28, 0.16), 0.5)
    lit = make_material("lnlit", (0.9, 0.6, 0.3), 0.4, emit=(1.0, 0.62, 0.28))
    dark = make_material("lndark", (0.03, 0.035, 0.05), 0.3)
    grime = make_material("lngrime", (0.16, 0.17, 0.16), 0.9, noise=0.3)
    box("module", (1, 1, 1), (0, 0, 0.5), plate)
    box("band", (1.008, 1.008, 0.14), (0, 0, 0.22), teal)      # boot stripe
    box("grime", (1.004, 1.004, 0.10), (0, 0, 0.05), grime)
    box("flange_t", (1.01, 1.01, 0.06), (0, 0, 0.97), steel)   # module seams
    box("flange_b", (1.01, 1.01, 0.05), (0, 0, 0.025), steel)
    for cx, cy in ((0.48, 0.48), (0.48, -0.48), (-0.48, 0.48), (-0.48, -0.48)):
        box(f"post{cx}{cy}", (0.06, 0.06, 1.0), (cx, cy, 0.5), steel)
    for i in range(5):                                         # flange bolts
        box(f"bolt{i}", (0.04, 0.02, 0.04), (-0.32 + i * 0.16, 0.508, 0.97), ring)
    # portholes, the tenement window rhythm gone round
    def ports_y(y_ring, y_glass, pattern):
        for (wx, litw) in pattern:
            _disc(f"pr{y_ring}{wx}", 0.085, (wx, y_ring, 0.60), ring)
            _disc(f"pg{y_ring}{wx}", 0.060, (wx, y_glass, 0.60),
                  lit if litw else dark)
    def ports_x(x_ring, x_glass, pattern):
        for (wy, litw) in pattern:
            _disc_x(f"pr{x_ring}{wy}", 0.085, (x_ring, wy, 0.60), ring)
            _disc_x(f"pg{x_ring}{wy}", 0.060, (x_glass, wy, 0.60),
                    lit if litw else dark)
    ports_y(0.505, 0.512, [(-0.28, True), (0.0, False), (0.28, True)])    # +y
    ports_y(-0.505, -0.512, [(-0.28, False), (0.0, True), (0.28, False)])  # -y
    ports_x(0.505, 0.512, [(-0.28, False), (0.0, True), (0.28, False)])   # +x
    ports_x(-0.505, -0.512, [(-0.24, True), (0.24, False)])               # -x
    return plate, teal


def liner_cell():
    clear_scene()
    _liner_base()
    rig_camera_and_light()
    render("liner")


def _liner_reg(name, text):
    """A hull module carrying part of the registry — SBL-0117 stenciled
    big across two adjacent modules on the home-visible face, the way a
    hull wears its number."""
    clear_scene()
    _liner_base()
    stencil = make_material("lnreg", (0.55, 0.52, 0.44), 0.8,
                            emit=(0.60, 0.57, 0.48), emit_strength=1.2)
    _xenon(text, (0, 0.512, 0.36), 0.26, stencil)
    rig_camera_and_light()
    render(name)


def _liner_deck_base():
    """The sun deck: teal-painted steel, plating strips, a low bulwark
    lip, deck furniture sparse enough to jump across."""
    slab = make_material("ldslab", (0.16, 0.28, 0.27), 0.7, noise=0.3)
    bone = make_material("ldbone", (0.44, 0.44, 0.38), 0.7, noise=0.25)
    vent = make_material("ldvent", (0.22, 0.24, 0.22), 0.6)
    box("deck", (1, 1, 0.10), (0, 0, 0.05), slab)
    for i in range(3):                                     # plating strips
        box(f"strip{i}", (1.0, 0.02, 0.012), (0, -0.30 + i * 0.30, 0.105), bone)
    for loc, size in (((0, 0.47, 0.13), (1, 0.05, 0.06)),   # bulwark lip
                      ((0, -0.47, 0.13), (1, 0.05, 0.06)),
                      ((0.47, 0, 0.13), (0.05, 0.88, 0.06)),
                      ((-0.47, 0, 0.13), (0.05, 0.88, 0.06))):
        box(f"bul{loc}", size, loc, bone)
    box("vent", (0.14, 0.14, 0.12), (0.30, 0.30, 0.16), vent)


def liner_deck_cell():
    clear_scene()
    _liner_deck_base()
    rig_camera_and_light()
    render("liner_deck")


def _liner_deck_stencil(name, text):
    """A deck tile with painted lettering lying flat — HALCYON DAYS
    across the sun deck. Mirrored in x and rotated 45° so it reads
    left-to-right along the atlas's (horizontally mirrored) screen
    axis at the home view."""
    clear_scene()
    _liner_deck_base()
    paint = make_material("ldpaint", (0.60, 0.58, 0.50), 0.8,
                          emit=(0.62, 0.60, 0.52), emit_strength=0.8)
    bpy.ops.object.text_add(location=(0, 0, 0.115))
    t = bpy.context.active_object
    t.data.body = text
    t.data.font = bpy.data.fonts.load(FONT)
    t.data.size = 0.26
    t.data.extrude = 0.01
    t.data.align_x = "CENTER"
    t.data.align_y = "CENTER"
    t.rotation_euler = (0, 0, 0.7854)
    t.scale = (-1, 1, 1)
    t.data.materials.append(paint)
    bpy.ops.object.convert(target="MESH")
    rig_camera_and_light()
    render(name)


def fire_escape_cell():
    """Iron clinging to an implied wall: grated landing, north rail,
    and the downward ladder off the east edge — it drops BELOW the
    deck so stacked landings read as one continuous ladder column."""
    clear_scene()
    iron = make_material("firon", (0.16, 0.15, 0.15), 0.55, noise=0.35)
    rust = make_material("frust", (0.30, 0.19, 0.13), 0.7, noise=0.45)
    # grated landing: two slats with a seam read as grate at map scale
    box("plat1", (0.92, 0.22, 0.045), (0, -0.13, 0.10), iron)
    box("plat2", (0.92, 0.22, 0.045), (0, 0.12, 0.10), iron)
    # railing on the visible north edge
    for i, x in enumerate((-0.42, 0.0, 0.42)):
        box(f"fpost{i}", (0.035, 0.035, 0.30), (x, 0.24, 0.27), rust)
    box("frail", (0.92, 0.035, 0.04), (0, 0.24, 0.43), rust)
    # the downward ladder, hung off the east edge, dropping below deck
    for j, sy in enumerate((0.10, -0.10)):
        box(f"fstr{j}", (0.035, 0.035, 0.62), (0.47, sy, -0.19), rust)
    for i in range(4):
        box(f"frung{i}", (0.035, 0.24, 0.03), (0.47, 0, -0.42 + i * 0.15), iron)
    rig_camera_and_light()
    render("fire_escape")


def _garden_lawn():
    """Full-cell green groundcover — the shared base every garden tile
    stands on, so adjacent cells mesh edge-to-edge into one parklet."""
    grass = make_material("ggrass", (0.27, 0.44, 0.21), 0.85, noise=0.32)
    box("lawn", (1.0, 1.0, 0.10), (0, 0, 0.05), grass)


def garden_cell():
    """The open green tile: lawn and a few low tufts, nothing centered."""
    clear_scene()
    _garden_lawn()
    tuft = make_material("gtuft", (0.34, 0.55, 0.24), 0.7, noise=0.4)
    for i, (tx, ty) in enumerate(((-0.28, 0.20), (0.24, -0.26), (0.30, 0.30))):
        box(f"tuft{i}", (0.13, 0.13, 0.11), (tx, ty, 0.15), tuft)
    rig_camera_and_light()
    render("garden")


def garden_bed_cell():
    """A planted tile: one low bed of crops along a single edge."""
    clear_scene()
    _garden_lawn()
    soil = make_material("g2soil", (0.17, 0.12, 0.08), 0.9, noise=0.4)
    crop = make_material("g2crop", (0.34, 0.55, 0.24), 0.7, noise=0.4)
    edge = make_material("g2edge", (0.32, 0.28, 0.22), 0.7)
    box("bframe", (0.90, 0.24, 0.13), (0, 0.33, 0.13), edge)
    box("bsoil", (0.84, 0.18, 0.05), (0, 0.33, 0.19), soil)
    for i, bx in enumerate((-0.30, -0.02, 0.26)):
        box(f"crop{i}", (0.16, 0.16, 0.18), (bx, 0.33, 0.26), crop)
    rig_camera_and_light()
    render("garden_2")


def garden_bench_cell():
    """A sitting tile: a bench and a shrub on the green."""
    clear_scene()
    _garden_lawn()
    wood = make_material("g3wood", (0.30, 0.22, 0.14), 0.7)
    shrub = make_material("g3shrub", (0.28, 0.47, 0.20), 0.7, noise=0.4)
    box("seat", (0.46, 0.13, 0.04), (-0.13, -0.06, 0.18), wood)
    box("back", (0.46, 0.04, 0.14), (-0.13, -0.12, 0.24), wood)
    for i, lx in enumerate((-0.32, 0.04)):
        box(f"leg{i}", (0.04, 0.11, 0.14), (lx, -0.06, 0.10), wood)
    box("shrub", (0.24, 0.24, 0.28), (0.29, 0.27, 0.19), shrub)
    rig_camera_and_light()
    render("garden_3")


def machine_cell():
    """The service riser: elevator shafts and machinery bays. Blank
    concrete in the tenement palette with a louver stack and conduit —
    a windowless strip that reads as intentional service core, not
    missing geometry (stacked full-height in the Brackett flank)."""
    clear_scene()
    concrete = make_material("mrcon", (0.13, 0.165, 0.20), 0.85, noise=0.45)
    louver = make_material("mrlouv", (0.09, 0.10, 0.11), 0.6)
    conduit = make_material("mrcond", (0.24, 0.20, 0.15), 0.5)
    lamp = make_material("mrlamp", (0.9, 0.65, 0.3), 0.4,
                         emit=(1.0, 0.62, 0.28), emit_strength=1.6)
    box("block", (1, 1, 1), (0, 0, 0.5), concrete)
    # louver stack on each face — slatted vents, no glass
    for face, (lx, ly, sx, sy) in enumerate((
            (0, 0.504, 0.34, 0.02), (0, -0.504, 0.34, 0.02),
            (0.504, 0, 0.02, 0.34), (-0.504, 0, 0.02, 0.34))):
        for i in range(3):
            box(f"lv{face}_{i}", (sx, sy, 0.06), (lx, ly, 0.30 + i * 0.16),
                louver)
    # cable conduit climbing one corner, service lamp above the vents
    box("conduit", (0.05, 0.05, 1.0), (0.42, 0.42, 0.5), conduit)
    box("lamp", (0.10, 0.02, 0.05), (-0.28, 0.508, 0.78), lamp)
    rig_camera_and_light()
    render("machine")


def mast_segment_cell():
    """A repeating lattice-mast segment: four legs run the full cell
    height plus X-bracing, so stacked cells read as one continuous
    antenna climbing the sky."""
    clear_scene()
    steel = make_material("msteel", (0.21, 0.20, 0.19), 0.6, noise=0.2)
    rust = make_material("mrust", (0.31, 0.20, 0.13), 0.7, noise=0.4)
    R = 0.15
    for i, (lx, ly) in enumerate(((R, R), (R, -R), (-R, R), (-R, -R))):
        box(f"leg{i}", (0.05, 0.05, 1.0), (lx, ly, 0.5), steel)
    for i, zc in enumerate((0.06, 0.5, 0.94)):           # horizontal ties
        box(f"tieN{i}", (2 * R, 0.04, 0.04), (0, R, zc), steel)
        box(f"tieS{i}", (2 * R, 0.04, 0.04), (0, -R, zc), steel)
        box(f"tieE{i}", (0.04, 2 * R, 0.04), (R, 0, zc), steel)
        box(f"tieW{i}", (0.04, 2 * R, 0.04), (-R, 0, zc), steel)
    th = math.atan(2 * R / 1.0)                          # X-braces, lit faces
    box("bX1", (0.035, 0.035, 1.02), (R, 0, 0.5), steel, rot=(th, 0, 0))
    box("bX2", (0.035, 0.035, 1.02), (R, 0, 0.5), steel, rot=(-th, 0, 0))
    box("bY1", (0.035, 0.035, 1.02), (0, R, 0.5), steel, rot=(0, th, 0))
    box("bY2", (0.035, 0.035, 1.02), (0, R, 0.5), steel, rot=(0, -th, 0))
    for i in range(5):                                   # climb ladder
        box(f"rung{i}", (0.04, 0.26, 0.025), (-R, 0, 0.12 + i * 0.2), rust)
    rig_camera_and_light()
    render("mast")


def _fallen_lattice(cx, length):
    """A horizontal lattice tube lying along x (the fallen mast), with a
    rust-plank walkway on top. Shared by the base and span tiles so they
    read as one continuous toppled tower across cells."""
    steel = make_material("flsteel", (0.22, 0.21, 0.20), 0.6, noise=0.2)
    rust = make_material("flrust", (0.32, 0.20, 0.13), 0.7, noise=0.4)
    R, base = 0.13, 0.16
    for i, (ry, rz) in enumerate(((R, base), (-R, base),
                                  (R, base + 2 * R), (-R, base + 2 * R))):
        box(f"rail{i}", (length, 0.05, 0.05), (cx, ry, rz), steel)
    n = max(2, int(length / 0.24))
    for i in range(n + 1):
        rx = cx - length / 2 + i * length / n
        box(f"rt{i}", (0.045, 2 * R + 0.06, 0.045), (rx, 0, base + 2 * R), steel)
        box(f"rb{i}", (0.045, 2 * R + 0.06, 0.045), (rx, 0, base), steel)
        box(f"rl{i}", (0.045, 0.045, 2 * R + 0.06), (rx, R, base + R), steel)
        box(f"rr{i}", (0.045, 0.045, 2 * R + 0.06), (rx, -R, base + R), steel)
    box("plank", (length, 0.22, 0.03), (cx, 0, base + 2 * R + 0.05), rust)


def fallen_span_cell():
    """A section of the toppled antenna spanning the gap — the lattice
    over the void, nothing under it but the drop."""
    clear_scene()
    _fallen_lattice(0.0, 1.06)
    rig_camera_and_light()
    render("fallen_span")


def fallen_tower_cell():
    """Where the mast toppled: a roof deck, the snapped stump, and the
    fallen lattice rooted here and running off toward the gap."""
    clear_scene()
    tar = make_material("fttar", (0.14, 0.135, 0.13), 0.85, noise=0.4)
    steel = make_material("ftsteel", (0.22, 0.21, 0.20), 0.6, noise=0.2)
    box("slab", (1, 1, 0.10), (0, 0, 0.05), tar)
    box("pad", (0.34, 0.34, 0.06), (0.30, 0, 0.13), steel)      # base pad
    box("stump", (0.10, 0.30, 0.20), (0.42, 0, 0.20), steel)    # snapped root
    _fallen_lattice(-0.12, 0.86)                                # lies off west
    rig_camera_and_light()
    render("fallen_tower")


def catwalk_cell():
    """A bare maintenance catwalk — grated floor and a railing, nothing
    else. Just the perch; the sign lives on the building now."""
    clear_scene()
    grate = make_material("cwgrate", (0.20, 0.26, 0.19), 0.6, noise=0.4)   # match the garden path
    steel = make_material("cwsteel", (0.21, 0.20, 0.19), 0.6, noise=0.2)
    # deck reaches the west (garden) edge at the same height/grating as
    # the path, so the two read as one continuous run
    box("deck", (0.52, 0.28, 0.04), (-0.24, 0, 0.11), grate)
    for ey in (-0.12, 0.12):                               # rails, long edges
        box(f"rail{ey}", (0.52, 0.03, 0.03), (-0.24, ey, 0.24), steel)
        for px in (-0.46, -0.04):
            box(f"post{ey}{px}", (0.03, 0.03, 0.13), (px, ey, 0.17), steel)
    rig_camera_and_light()
    render("catwalk")


def _xenon(ch, loc, size, mat, rot=(1.5708, 0, 3.1416), wide=1.0):
    """One Monaspace Xenon glyph, extruded, baked to mesh so it glows in
    the atlas. Default rot faces +y (the home-visible face); pass
    (1.5708, 0, 0) for a copy that reads correctly from the -y side.
    `wide` stretches the glyph along its reading axis for legibility."""
    bpy.ops.object.text_add(location=loc)
    t = bpy.context.active_object
    t.data.body = ch
    t.data.font = bpy.data.fonts.load(FONT)
    t.data.size = size
    t.data.extrude = 0.02
    t.data.align_x = "CENTER"
    t.data.align_y = "CENTER"
    t.rotation_euler = rot
    t.scale = (wide, 1, 1)
    t.data.materials.append(mat)
    bpy.ops.object.convert(target="MESH")


def _marquee_base():
    """Tenement wall + windows (so it matches the building) with a dark
    central sign strip up the +y face for the lettering."""
    concrete = make_material("mqcon", (0.13, 0.165, 0.20), 0.85, noise=0.45)
    grime = make_material("mqgr", (0.09, 0.11, 0.13), 0.95, noise=0.3)
    wf = make_material("mqwf", (0.07, 0.08, 0.09), 0.8)
    lit = make_material("mqlit", (0.9, 0.6, 0.3), 0.4, emit=(1.0, 0.62, 0.28))
    dark = make_material("mqdk", (0.03, 0.035, 0.05), 0.3)
    panel = make_material("mqpanel", (0.07, 0.09, 0.08), 0.7)
    box("block", (1, 1, 1), (0, 0, 0.5), concrete)
    box("grime", (1.002, 1.002, 0.16), (0, 0, 0.08), grime)
    for wx, w in [(-0.34, True), (0.34, True)]:                # +y side windows, lit
        box(f"wfy{wx}", (0.15, 0.02, 0.30), (wx, 0.505, 0.55), wf)
        box(f"wgy{wx}", (0.11, 0.015, 0.24), (wx, 0.512, 0.55), lit if w else dark)
    for wy, w in [(-0.28, True), (0.0, True), (0.28, True)]:    # +x face windows, lit
        box(f"wfx{wy}", (0.02, 0.16, 0.30), (0.505, wy, 0.55), wf)
        box(f"wgx{wy}", (0.015, 0.12, 0.24), (0.512, wy, 0.55), lit if w else dark)
    box("sign", (0.34, 0.03, 1.02), (0, 0.505, 0.5), panel)    # central sign strip


def _loggia_base():
    """The 6th-storey glass band (matches Units 6E/6F next door)."""
    bone = make_material("l6bone", (0.13, 0.165, 0.20), 0.85, noise=0.45)
    frame = make_material("l6frame", (0.07, 0.08, 0.09), 0.8)
    glass = make_material("l6glass", (0.42, 0.40, 0.22), 0.25,
                          emit=(0.92, 0.80, 0.42), emit_strength=4.0)
    box("lbase", (1, 1, 0.30), (0, 0, 0.15), bone)
    box("llint", (1, 1, 0.18), (0, 0, 0.81), bone)
    box("lcore", (0.88, 0.88, 0.42), (0, 0, 0.51), frame)
    for i, (gx, gy, sx, sy) in enumerate((
            (0, 0.505, 0.90, 0.03), (0, -0.505, 0.90, 0.03),
            (0.505, 0, 0.03, 0.90), (-0.505, 0, 0.03, 0.90))):
        box(f"lg{i}", (sx, sy, 0.40), (gx, gy, 0.51), glass)


def _marquee_loggia(name, glyphs):
    """The 6th-floor marquee tile: the loggia glass band with the green
    sign strip and its glyphs riding the band."""
    clear_scene()
    _loggia_base()
    panel = make_material("m6panel", (0.07, 0.09, 0.08), 0.7)
    holo = make_material("m6holo", (0.4, 1.0, 0.55), 0.1,
                         emit=(0.45, 1.0, 0.6), emit_strength=8.0)
    box("sign", (0.30, 0.03, 0.7), (0, 0.52, 0.45), panel)
    for ch, z in glyphs:
        _xenon(ch, (0, 0.55, z), 0.26, holo)
    rig_camera_and_light()
    render(name)


def garden_path_cell():
    """The roof-garden landing where the crossing meets the building: a
    grated service path and a pipe threading through the greenery, tying
    the catwalk (east) to the roof and the marquee below (west)."""
    clear_scene()
    _garden_lawn()
    grate = make_material("gpgrate", (0.20, 0.26, 0.19), 0.6, noise=0.4)   # mossy, blends in
    pipe = make_material("gppipe", (0.31, 0.29, 0.23), 0.5, noise=0.2)
    crop = make_material("gpcrop", (0.34, 0.55, 0.24), 0.7, noise=0.4)
    moss = make_material("gpmoss", (0.30, 0.48, 0.22), 0.75, noise=0.4)
    box("path", (1.0, 0.28, 0.04), (0, 0, 0.11), grate)        # grated path, E-W, roof height
    box("pipe", (1.02, 0.09, 0.09), (0, -0.26, 0.16), pipe)    # pipe alongside
    box("sad", (0.06, 0.13, 0.10), (-0.10, -0.26, 0.12), pipe)
    for i, (mx, my) in enumerate(((-0.34, 0.07), (0.26, -0.09), (0.06, 0.10))):
        box(f"moss{i}", (0.11, 0.09, 0.05), (mx, my, 0.14), moss)   # greenery creeps onto it
    for i, (tx, ty) in enumerate(((-0.36, 0.36), (0.32, 0.38), (0.38, -0.38))):
        box(f"crop{i}", (0.12, 0.12, 0.15), (tx, ty, 0.16), crop)
    rig_camera_and_light()
    render("garden_path")


def _marquee_glyphs(name, glyphs):
    """One marquee tile carrying whatever glyphs of the continuous
    vertical name fall in its z-band (list of (char, local_z)); even
    letter spacing across tiles, a wide gap for the word break."""
    clear_scene()
    _marquee_base()
    holo = make_material("mqholo", (0.4, 1.0, 0.55), 0.1,
                         emit=(0.45, 1.0, 0.6), emit_strength=8.0)
    for ch, z in glyphs:
        _xenon(ch, (0, 0.53, z), 0.28, holo)
    rig_camera_and_light()
    render(name)


def _air_marquee(name, glyphs, ribs, crown=False, finial=False):
    """A salvaged theater blade sign hung in the canyon below the
    catwalk — a solid art-deco fin, oxblood body wrapped in gold banding
    ribs, the letters projected in green holo on BOTH broad faces (back
    copy unmirrored). Tiles stack into one continuous blade; the top
    tile wears the crown, the bottom one the finial end-cap. Same glyph
    z-bands as the flank run so the name reads identically."""
    clear_scene()
    body = make_material("ambody", (0.24, 0.09, 0.08), 0.75, noise=0.25)   # oxblood
    chan = make_material("amchan", (0.03, 0.05, 0.04), 0.9)     # dark sign channel
    trim = make_material("amtrim", (0.62, 0.48, 0.28), 0.5,
                         emit=(0.85, 0.66, 0.35), emit_strength=1.2)       # gold banding
    tube = make_material("amtube", (0.5, 0.35, 0.15), 0.4,
                         emit=(1.0, 0.7, 0.35), emit_strength=4.0)         # edge neon
    holo = make_material("amholo", (0.4, 1.0, 0.55), 0.1,
                         emit=(0.45, 1.0, 0.6), emit_strength=8.0)
    # the fin: centred under the catwalk deck (x=-0.24, y=0), full tile
    # height so stacked tiles read as one blade
    bz, bh = (0.55, 0.90) if finial else (0.5, 1.0)
    box("blade", (0.36, 0.12, bh), (-0.24, 0, bz), body)
    # dark channel behind the letters: soaks up the baked letter-glow
    # (no more stray flares on the oxblood) and lifts the contrast
    box("chanF", (0.30, 0.005, bh), (-0.24, 0.0625, bz), chan)
    box("chanB", (0.30, 0.005, bh), (-0.24, -0.0625, bz), chan)
    # the flare, made deliberate: a neon tube up the blade's +x edge
    # (screen-LEFT at the home view), clear of the letter column
    box("edgetube", (0.03, 0.14, bh), (-0.065, 0, bz), tube)
    for i, rz in enumerate(ribs):                          # banding wraps the fin
        box(f"rib{i}", (0.38, 0.15, 0.02), (-0.24, 0, rz), trim)
    if crown:                                              # deco shoulders at the top
        box("crownband", (0.40, 0.16, 0.05), (-0.24, 0, 0.975), trim)
        box("scrollL", (0.06, 0.13, 0.10), (-0.45, 0, 0.93), body)
        box("scrollR", (0.06, 0.13, 0.10), (-0.03, 0, 0.93), body)
    if finial:                                             # the blade ends, capped
        box("endcap", (0.38, 0.15, 0.04), (-0.24, 0, 0.10), trim)
        box("tip", (0.20, 0.12, 0.06), (-0.24, 0, 0.05), body)
    for ch, z in glyphs:                                   # letters on BOTH faces
        _xenon(ch, (-0.24, 0.070, z), 0.31, holo, wide=1.25)        # front (+y)
        _xenon(ch, (-0.24, -0.070, z), 0.31, holo, (1.5708, 0, 0),
               wide=1.25)                                           # back (-y), unmirrored
    rig_camera_and_light()
    render(name)


def garden_cap_cell():
    """The comprehensive cap where the crossing meets the roof: a slice
    of roof garden, the marquee topping out, and a stub of catwalk — one
    unit instead of three abutting tiles."""
    clear_scene()
    grass = make_material("gclawn", (0.27, 0.44, 0.21), 0.85, noise=0.35)
    soil = make_material("gcsoil", (0.17, 0.12, 0.08), 0.9, noise=0.4)
    crop = make_material("gccrop", (0.34, 0.55, 0.24), 0.7, noise=0.4)
    steel = make_material("gcsteel", (0.21, 0.20, 0.19), 0.6)
    grate = make_material("gcgrate", (0.15, 0.14, 0.14), 0.55, noise=0.35)
    holo = make_material("gcholo", (0.4, 1.0, 0.55), 0.1,
                         emit=(0.45, 1.0, 0.6), emit_strength=7.0)
    box("lawn", (1, 1, 0.10), (0, 0, 0.05), grass)
    box("bed", (0.5, 0.24, 0.09), (-0.18, -0.2, 0.14), soil)    # a garden bed
    for i, bx in enumerate((-0.34, -0.12, 0.10)):
        box(f"crop{i}", (0.12, 0.12, 0.15), (bx, -0.2, 0.21), crop)
    box("mcap", (0.34, 0.05, 0.6), (0, 0.5, 0.28), holo)        # marquee topping out (+y)
    box("cw", (0.22, 0.52, 0.05), (0.42, 0, 0.12), grate)       # catwalk stub (+x)
    for py in (-0.22, 0.22):
        box(f"cwp{py}", (0.03, 0.03, 0.16), (0.50, py, 0.18), steel)
    box("cwr", (0.03, 0.52, 0.03), (0.50, 0, 0.26), steel)
    rig_camera_and_light()
    render("garden_cap")


def marquee_cell():
    """A segment of the holo-marquee running down the Brackett's flank:
    the tenement wall plus a full-height green sign channel on the east
    face, sized to stack seamlessly into one long running sign."""
    clear_scene()
    # matches the tenement (concrete + grime + lit/unlit windows) so it
    # reads as the same building, with the marquee as an add-on
    concrete = make_material("mqcon", (0.13, 0.165, 0.20), 0.85, noise=0.45)
    grime = make_material("mqgrime", (0.09, 0.11, 0.13), 0.95, noise=0.3)
    wframe = make_material("mqwf", (0.07, 0.08, 0.09), 0.8)
    lit = make_material("mqlit", (0.9, 0.6, 0.3), 0.4, emit=(1.0, 0.62, 0.28))
    dark = make_material("mqdk", (0.03, 0.035, 0.05), 0.3)
    holo = make_material("mqholo", (0.35, 0.95, 0.5), 0.1,
                         emit=(0.4, 1.0, 0.55), emit_strength=6.0)
    hframe = make_material("mqhf", (0.10, 0.11, 0.11), 0.7)
    box("block", (1, 1, 1), (0, 0, 0.5), concrete)
    box("grime", (1.002, 1.002, 0.16), (0, 0, 0.08), grime)
    for wx, w in [(-0.28, True), (0.0, False), (0.28, True)]:   # +y face
        box(f"wfy{wx}", (0.16, 0.02, 0.30), (wx, 0.505, 0.55), wframe)
        box(f"wgy{wx}", (0.12, 0.015, 0.24), (wx, 0.512, 0.55),
            lit if w else dark)
    for wy, w in [(-0.28, False), (0.0, True), (0.28, False)]:  # +x face
        box(f"wfx{wy}", (0.02, 0.16, 0.30), (0.505, wy, 0.55), wframe)
        box(f"wgx{wy}", (0.015, 0.12, 0.24), (0.512, wy, 0.55),
            lit if w else dark)
    # the marquee: a WIDE green blade wrapping the NE corner, full height,
    # so stacked cells make one continuous running sign
    box("mchx", (0.06, 0.6, 1.03), (0.512, 0.18, 0.5), hframe)  # +x panel
    box("msgx", (0.03, 0.5, 1.04), (0.55, 0.18, 0.5), holo)
    box("mchy", (0.6, 0.06, 1.03), (0.18, 0.512, 0.5), hframe)  # +y panel
    box("msgy", (0.5, 0.03, 1.04), (0.18, 0.55, 0.5), holo)
    rig_camera_and_light()
    render("marquee")


def billboard_cell():
    """The dead terraform board: a truss-mounted panel over the street
    still projecting a green-world hologram that never came true, a
    maintenance catwalk at its foot (the walkable perch)."""
    clear_scene()
    frame = make_material("bbframe", (0.20, 0.19, 0.18), 0.6, noise=0.25)
    house = make_material("bbhouse", (0.11, 0.12, 0.11), 0.7)
    holo = make_material("bbholo", (0.35, 0.95, 0.5), 0.1,
                         emit=(0.4, 1.0, 0.55), emit_strength=7.0)
    grate = make_material("bbgrate", (0.15, 0.14, 0.14), 0.55, noise=0.35)
    # the whole rig hangs off the WEST edge (-x), bolted to the building
    # flank in the neighbouring cell, and cantilevers east over the gap.
    box("plate", (0.06, 0.86, 0.92), (-0.5, 0, 0.5), frame)     # flush mount
    for i, by in enumerate((-0.30, 0.30)):                      # arms east
        box(f"arm{i}", (0.62, 0.07, 0.07), (-0.16, by, 0.66), frame)
        box(f"stay{i}", (0.5, 0.06, 0.06), (-0.22, by, 0.16), frame)  # under-brace
    # walk-through catwalk spanning the cell, under the sign
    box("catwalk", (0.92, 0.5, 0.05), (0.04, 0, 0.10), grate)
    for i, ry in enumerate((-0.30, 0.30)):
        box(f"rail{i}", (0.92, 0.03, 0.15), (0.04, ry, 0.19), frame)
    # the sign panel hung from the arms, up high, facing out over the drop
    box("board", (0.09, 0.68, 0.46), (0.10, 0, 0.68), house)
    # the holographic globe projecting east off the panel, out over the gap
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.25,
                                           location=(0.40, 0, 0.70))
    globe = bpy.context.active_object
    globe.data.materials.append(holo)
    rig_camera_and_light()
    render("billboard")


def mast_base_cell():
    """The antenna's foot in the green park: lawn (so it meshes with
    the parklet), a concrete pad, and the lattice mast rising to meet
    the segments above, guyed off to anchors on the grass."""
    clear_scene()
    _garden_lawn()
    concrete = make_material("mbpad", (0.33, 0.32, 0.30), 0.7, noise=0.2)
    steel = make_material("mbsteel", (0.21, 0.20, 0.19), 0.6, noise=0.2)
    box("pad", (0.52, 0.52, 0.09), (0, 0, 0.13), concrete)
    R = 0.15
    for i, (lx, ly) in enumerate(((R, R), (R, -R), (-R, R), (-R, -R))):
        box(f"leg{i}", (0.06, 0.06, 0.82), (lx, ly, 0.55), steel)
    box("tieN", (2 * R, 0.04, 0.04), (0, R, 0.90), steel)
    box("tieE", (0.04, 2 * R, 0.04), (R, 0, 0.90), steel)
    for i, (gx, gy) in enumerate(((0.42, 0.42), (0.42, -0.42),
                                  (-0.42, 0.42), (-0.42, -0.42))):
        box(f"anchor{i}", (0.06, 0.06, 0.14), (gx, gy, 0.16), steel)
    rig_camera_and_light()
    render("mast_base")


def loggia_cell():
    """The terrace-suite motif: old terrace bones in masonry, glazing
    above, and a lit skylight grid on the crown — a warm glasshouse
    glint among the tar roofs, for the perceptive to notice."""
    clear_scene()
    # sill/lintel wear the tower's own concrete (owner: colour matches,
    # the glass band is the whole tell — a subtle distinction)
    bone = make_material("lbone", (0.13, 0.165, 0.20), 0.85, noise=0.45)
    frame = make_material("lframe", (0.07, 0.08, 0.09), 0.8)
    glass = make_material("lglass", (0.42, 0.40, 0.22), 0.25,
                          emit=(0.92, 0.80, 0.42), emit_strength=4.0)
    green = make_material("lgreen", (0.22, 0.36, 0.18), 0.8, noise=0.3)
    # these cells sit EMBEDDED in a tower flank — only whichever side
    # face the wall exposes is ever seen. So the motif is the facade:
    # masonry sill and lintel with a lit glazing band on ALL four
    # faces, proud of the wall plane so the glass catches from any
    # angle. No crown detail — the storey above buries it.
    box("lbase", (1, 1, 0.30), (0, 0, 0.15), bone)
    box("llint", (1, 1, 0.18), (0, 0, 0.81), bone)
    box("lcore", (0.88, 0.88, 0.42), (0, 0, 0.51), frame)
    for i, (gx, gy, sx, sy) in enumerate((
            (0, 0.505, 0.90, 0.03), (0, -0.505, 0.90, 0.03),
            (0.505, 0, 0.03, 0.90), (-0.505, 0, 0.03, 0.90))):
        box(f"lg{i}", (sx, sy, 0.40), (gx, gy, 0.51), glass)
    # mullions splitting each pane — greenhouse rhythm, not a window;
    # they must PIERCE the glass plane (glass outer face sits at 0.52)
    # or the band bakes to a flat unbroken stripe
    for i, mx in enumerate((-0.24, 0.0, 0.24)):
        box(f"lmn{i}", (0.05, 1.07, 0.42), (mx, 0, 0.51), frame)
        box(f"lme{i}", (1.07, 0.05, 0.42), (0, mx, 0.51), frame)
    # planter boxes riding the sill on the south and east faces
    for i, (px, py) in enumerate(((-0.26, -0.46), (0.18, -0.46),
                                  (0.46, -0.22), (0.46, 0.22))):
        box(f"lplant{i}", (0.16, 0.16, 0.10), (px, py, 0.35), green)
    rig_camera_and_light()
    render("loggia")


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
    for face, sign in (("s", 1), ("n", -1)):
        for i in range(2):
            for j in range(3):
                k += 1
                mat = litw if (k % 3 == 0) else darkw
                box(f"c{face}{i}{j}", (0.20, 0.02, 0.16),
                    (-0.22 + i * 0.44, sign * 0.508, 0.25 + j * 0.28), frame)
                box(f"g{face}{i}{j}", (0.16, 0.015, 0.12),
                    (-0.22 + i * 0.44, sign * 0.515, 0.25 + j * 0.28), mat)
    for face, sign in (("e", 1), ("w", -1)):
        for i in range(2):
            for j in range(3):
                k += 1
                mat = litw if (k % 3 == 0) else darkw
                box(f"c{face}{i}{j}", (0.02, 0.20, 0.16),
                    (sign * 0.508, -0.22 + i * 0.44, 0.25 + j * 0.28), frame)
                box(f"g{face}{i}{j}", (0.015, 0.16, 0.12),
                    (sign * 0.515, -0.22 + i * 0.44, 0.25 + j * 0.28), mat)
    rig_camera_and_light()
    render("hotel")


def _crane_lattice(z0=0.0, h=1.0, lit=False):
    """A Boiler-Run tower-crane mast segment — four yellow legs, ties and
    X-braces, a climb ladder up the west face. Stacks continuously into
    one tower. Returns (steel, yellow) for callers to keep building."""
    steel = make_material("crsteel", (0.21, 0.20, 0.19), 0.6, noise=0.2)
    yellow = make_material("cryellow", (0.60, 0.50, 0.10), 0.6, noise=0.3)
    rust = make_material("crrust", (0.31, 0.20, 0.13), 0.7, noise=0.4)
    R = 0.16
    cz = z0 + h / 2
    for i, (lx, ly) in enumerate(((R, R), (R, -R), (-R, R), (-R, -R))):
        box(f"leg{i}", (0.06, 0.06, h), (lx, ly, cz), yellow)
    for zc in (z0 + 0.06, cz, z0 + h - 0.06):            # horizontal ties
        for tag, sz, loc in (("N", (2 * R, 0.04, 0.04), (0, R, zc)),
                             ("S", (2 * R, 0.04, 0.04), (0, -R, zc)),
                             ("E", (0.04, 2 * R, 0.04), (R, 0, zc)),
                             ("W", (0.04, 2 * R, 0.04), (-R, 0, zc))):
            box(f"tie{tag}{zc:.2f}", sz, loc, steel)
    th = math.atan(2 * R / h)                            # X-braces on lit faces
    box("bX1", (0.035, 0.035, h + 0.02), (R, 0, cz), steel, rot=(th, 0, 0))
    box("bX2", (0.035, 0.035, h + 0.02), (R, 0, cz), steel, rot=(-th, 0, 0))
    box("bY1", (0.035, 0.035, h + 0.02), (0, R, cz), steel, rot=(0, th, 0))
    box("bY2", (0.035, 0.035, h + 0.02), (0, R, cz), steel, rot=(0, -th, 0))
    rungs = max(2, int(h / 0.2))
    for i in range(rungs):                               # ladder, west face
        box(f"rung{i}", (0.04, 0.26, 0.025), (-R, 0, z0 + 0.12 + i * 0.2), rust)
    return steel, yellow


def crane_mast_cell():
    clear_scene()
    _crane_lattice()
    rig_camera_and_light()
    render("crane_mast")


def crane_cab_cell():
    """The operator's cab topping the mast, with the jib reaching north
    over the lot and a stubby counter-jib with its weight to the south."""
    clear_scene()
    steel, yellow = _crane_lattice(z0=0.0, h=0.55)         # tower stub
    glass = make_material("ccglass", (0.9, 0.72, 0.35), 0.3,
                          emit=(1.0, 0.72, 0.30), emit_strength=3.0)
    cab = make_material("cccab", (0.60, 0.50, 0.10), 0.6, noise=0.3)
    dark = make_material("ccdark", (0.10, 0.10, 0.11), 0.7)
    # the cab box
    box("cab", (0.34, 0.34, 0.30), (0, 0, 0.68), cab)
    box("winN", (0.26, 0.02, 0.16), (0, 0.175, 0.70), glass)   # window over the lot
    box("winW", (0.02, 0.26, 0.16), (-0.175, 0, 0.70), glass)  # window west
    # the jib ROOT: the boom leaves the cab reaching north (+y) to the
    # cell edge, where the jib-arm cell picks it up (the hook now lives
    # out at the tip, two cells north over the container)
    for rail_z in (0.86, 0.98):
        box(f"jibT{rail_z}", (0.06, 0.62, 0.03), (0, 0.34, rail_z), yellow)
    for i in range(6):
        jy = 0.10 + i * 0.11
        box(f"jibd{i}", (0.04, 0.04, 0.13), (0, jy, 0.92), steel, rot=(0.6, 0, 0))
    # counter-jib + counterweight, short to the south
    box("cjib", (0.06, 0.26, 0.03), (0, -0.22, 0.90), yellow)
    box("cweight", (0.16, 0.12, 0.16), (0, -0.30, 0.84), steel)
    rig_camera_and_light()
    render("crane_cab")


def crane_jib_cell():
    """A run of the crane's jib — the horizontal boom cantilevering north
    over the lot. Two yellow chords along the N-S axis with a steel web
    and a maintenance walkway, so cab, arm and tip read as one boom."""
    clear_scene()
    steel = make_material("cjsteel", (0.21, 0.20, 0.19), 0.6, noise=0.2)
    yellow = make_material("cjyellow", (0.60, 0.50, 0.10), 0.6, noise=0.3)
    for cz in (0.86, 0.98):                               # chords, full cell N-S
        box(f"chord{cz}", (0.06, 1.02, 0.04), (0, 0, cz), yellow)
    for i in range(7):                                    # web between the chords
        yy = -0.5 + i * (1.0 / 6)
        box(f"web{i}", (0.04, 0.04, 0.12), (0, yy, 0.92), steel)
    box("walk", (0.05, 1.02, 0.02), (0, 0, 1.005), steel)  # top walkway
    rig_camera_and_light()
    render("crane_jib")


def crane_jibtip_cell():
    """The jib's outer end, right over the container: the boom tips in
    from the south to a sheave block, and the hoist cable drops from the
    trolley straight down the shaft to the hanging box."""
    clear_scene()
    steel = make_material("jtsteel", (0.21, 0.20, 0.19), 0.6, noise=0.2)
    yellow = make_material("jtyellow", (0.60, 0.50, 0.10), 0.6, noise=0.3)
    dark = make_material("jtdark", (0.08, 0.08, 0.09), 0.5)
    for cz in (0.86, 0.98):                               # boom in from the south
        box(f"chord{cz}", (0.06, 0.55, 0.04), (0, -0.25, cz), yellow)
    box("sheave", (0.12, 0.14, 0.16), (0, 0, 0.90), steel)     # end sheave block
    box("trolley", (0.10, 0.10, 0.06), (0, 0, 0.82), dark)
    box("cable", (0.02, 0.02, 0.80), (0, 0, 0.42), dark)       # cable down the shaft
    box("hook", (0.05, 0.05, 0.06), (0, 0, 0.04), dark)
    rig_camera_and_light()
    render("crane_jibtip")


def crane_container_cell():
    """The Longhaul container slung on the cable — a corrugated box with
    a lift frame and cable up top, doors chained open on the west end.
    Renders wherever the car currently hangs (the room really moves)."""
    clear_scene()
    body = make_material("cnbody", (0.30, 0.36, 0.30), 0.7, noise=0.3)   # weathered green
    rib = make_material("cnrib", (0.22, 0.27, 0.22), 0.75, noise=0.2)
    steel = make_material("cnsteel", (0.21, 0.20, 0.19), 0.6)
    teal = make_material("cnteal", (0.10, 0.30, 0.32), 0.55)
    dark = make_material("cndark", (0.06, 0.07, 0.07), 0.6)
    box("box", (0.72, 0.42, 0.34), (0, 0, 0.34), body)
    for i in range(7):                                    # corrugation ribs
        rx = -0.30 + i * 0.10
        box(f"rib{i}", (0.02, 0.44, 0.34), (rx, 0, 0.34), rib)
    box("band", (0.73, 0.43, 0.05), (0, 0, 0.20), teal)   # boot stripe
    box("doorW", (0.03, 0.40, 0.32), (-0.36, 0, 0.34), dark)   # open doors, west
    for cx in (-0.34, 0.34):                              # corner castings
        for cy in (-0.20, 0.20):
            box(f"cc{cx}{cy}", (0.05, 0.05, 0.05), (cx, cy, 0.52), steel)
    # lift frame + cable up to the (implied) jib
    box("frameL", (0.03, 0.03, 0.14), (-0.30, 0, 0.58), steel, rot=(0, 0.5, 0))
    box("frameR", (0.03, 0.03, 0.14), (0.30, 0, 0.58), steel, rot=(0, -0.5, 0))
    box("cable", (0.015, 0.015, 0.45), (0, 0, 0.82), dark)
    rig_camera_and_light()
    render("crane_container")


def crane_chain_cell():
    """A hanging length of the crane's hoist cable — a thin greased line
    with periodic chain links, centred and full-height so stacked cells
    read as one continuous cable from the jib down to the container."""
    clear_scene()
    cable = make_material("chcable", (0.09, 0.09, 0.10), 0.45)
    link = make_material("chlink", (0.17, 0.16, 0.14), 0.55, noise=0.25)
    box("cable", (0.025, 0.025, 1.0), (0, 0, 0.5), cable)
    for i in range(5):                                    # chain links down the run
        box(f"lk{i}", (0.06, 0.05, 0.05), (0, 0, 0.1 + i * 0.2), link)
    rig_camera_and_light()
    render("crane_chain")


def _hoarding(sides, permit=False):
    """Plywood hoarding on the named lot edges (a subset of 'NSEW'). The
    three ground cells each fence only their OUTER edges, so together they
    ring the whole dig as one continuous perimeter — interior edges left
    open, no way in. N/S run E-W along the +/-y edge; E/W run N-S along
    the +/-x edge."""
    ply = make_material("hoardply", (0.45, 0.33, 0.16), 0.8, noise=0.35)
    post = make_material("hoardpost", (0.20, 0.16, 0.11), 0.7)
    haz = make_material("hoardhaz", (0.62, 0.50, 0.10), 0.7)
    edge = {"N": ((1.0, 0.06, 0.42), (0, 0.47, 0.24), "y"),
            "S": ((1.0, 0.06, 0.42), (0, -0.47, 0.24), "y"),
            "E": ((0.06, 1.0, 0.42), (0.47, 0, 0.24), "x"),
            "W": ((0.06, 1.0, 0.42), (-0.47, 0, 0.24), "x")}
    for s in sides:
        size, loc, axis = edge[s]
        box(f"hoard{s}", size, loc, ply)
        for t in (-0.42, 0.0, 0.42):                      # posts along the run
            p = (t, loc[1], 0.23) if axis == "y" else (loc[0], t, 0.23)
            box(f"post{s}{t}", (0.05, 0.05, 0.46), p, post)
    if permit and "E" in sides:                           # a permit taped streetside
        box("permit", (0.02, 0.16, 0.12), (0.505, 0.05, 0.30), haz)


def crane_lot_cell():
    """The open yard under the jib — churned mud, boxed in on its street
    (east/west) faces by the lot's plywood hoarding."""
    clear_scene()
    mud = make_material("ltmud", (0.16, 0.13, 0.10), 0.9, noise=0.4)
    box("yard", (1, 1, 0.06), (0, 0, 0.03), mud)
    _hoarding("EW", permit=True)                          # middle cell: side walls only
    rig_camera_and_light()
    render("crane_lot")


def crane_base_cell():
    """The crane's foot: the concrete pad the mast is bolted to, with the
    lattice legs rising the FULL cell so the ground reads continuous with
    the mast above (no floating gap) — plus a dead generator and pallets
    of block in the mud."""
    clear_scene()
    mud = make_material("cbmud", (0.16, 0.13, 0.10), 0.9, noise=0.4)
    pad = make_material("cbpad", (0.32, 0.31, 0.30), 0.8, noise=0.25)
    box("yard", (1, 1, 0.06), (0, 0, 0.03), mud)
    box("pad", (0.5, 0.5, 0.16), (0, 0, 0.09), pad)         # the crane foot pad
    steel, yellow = _crane_lattice(z0=0.16, h=0.84)        # legs rise off the pad
    box("gen", (0.20, 0.14, 0.12), (0.34, -0.20, 0.13), steel)   # generator
    for i in range(3):                                     # block pallets
        box(f"pal{i}", (0.16, 0.16, 0.08),
            (-0.34, -0.20 + i * 0.02, 0.10 + i * 0.05), pad)
    _hoarding("SEW")                                       # south cap + side walls
    rig_camera_and_light()
    render("crane_base")


def crane_dig_cell():
    """The poured foundation under the cable — wet concrete and a forest
    of upright rebar. The pit you land in if a jump comes up short."""
    clear_scene()
    mud = make_material("cdmud", (0.15, 0.12, 0.09), 0.9, noise=0.45)
    conc = make_material("cdconc", (0.28, 0.27, 0.26), 0.85, noise=0.3)
    rebar = make_material("cdrebar", (0.34, 0.22, 0.14), 0.6, noise=0.4)
    water = make_material("cdwater", (0.10, 0.12, 0.13), 0.2, wet=True)
    box("pit", (1, 1, 0.05), (0, 0, 0.025), mud)
    box("pour", (0.7, 0.7, 0.05), (0, 0, 0.05), conc)
    box("puddle", (0.4, 0.3, 0.012), (0.1, 0.1, 0.075), water)
    for i in range(16):                                    # rebar forest
        gx = -0.24 + (i % 4) * 0.16
        gy = -0.24 + (i // 4) * 0.16
        box(f"reb{i}", (0.02, 0.02, 0.22), (gx, gy, 0.16), rebar)
    _hoarding("NEW")                                       # north cap + side walls
    rig_camera_and_light()
    render("crane_dig")


# ---------------------------------------------------------------- The Midden
# One bespoke sprite per yard cell — no shared tiles, so the yard never
# reads as a repeated pattern. Each cell = dirt ground + its own distinct
# scrap, plus chain-link on its outer edges (or the Halcyon's hull on the
# east cells, which borrow the liner's steel for a wall).
def _scrap_mats():
    return {
        "dirt": make_material("scdirt", (0.17, 0.14, 0.11), 0.9, noise=0.4),
        "rust": make_material("scrust", (0.34, 0.20, 0.13), 0.7, noise=0.5),
        "steel": make_material("scsteel", (0.30, 0.31, 0.32), 0.5, noise=0.4),
        "drum": make_material("scdrum", (0.30, 0.34, 0.22), 0.6, noise=0.3),
        "tyre": make_material("sctyre", (0.09, 0.09, 0.10), 0.85),
        "paint": make_material("scpaint", (0.36, 0.22, 0.24), 0.6, noise=0.4),
        "brass": make_material("scbrass", (0.45, 0.38, 0.18), 0.5),
        "teal": make_material("scteal", (0.10, 0.30, 0.32), 0.55, noise=0.25),
        "bone": make_material("scbone", (0.44, 0.44, 0.38), 0.7, noise=0.25),
    }


def _chainlink(sides, m):
    """Chain-link on the named outer edges — posts, a top rail, a grey mesh
    panel — so the yard's outer cells ring it as one fence."""
    mesh = make_material("clmesh", (0.26, 0.27, 0.28), 0.5, noise=0.6)
    edge = {"N": (0, 0.47, "x"), "S": (0, -0.47, "x"),
            "E": (0.47, 0, "y"), "W": (-0.47, 0, "y")}
    for s in sides:
        cx, cy, ax = edge[s]
        if ax == "x":
            box(f"clm{s}", (1.0, 0.02, 0.40), (0, cy, 0.22), mesh)
            box(f"clr{s}", (1.0, 0.03, 0.03), (0, cy, 0.42), m["steel"])
            for t in (-0.42, -0.14, 0.14, 0.42):
                box(f"clp{s}{t}", (0.04, 0.04, 0.46), (t, cy, 0.23), m["steel"])
        else:
            box(f"clm{s}", (0.02, 1.0, 0.40), (cx, 0, 0.22), mesh)
            box(f"clr{s}", (0.03, 1.0, 0.03), (cx, 0, 0.42), m["steel"])
            for t in (-0.42, -0.14, 0.14, 0.42):
                box(f"clp{s}{t}", (0.04, 0.04, 0.46), (cx, t, 0.23), m["steel"])


def _hull_wall(m):
    """The east wall of the yard's Halcyon-side cells: the liner's painted
    steel doubling as a fence, teal boot-stripe and all."""
    box("hull", (0.08, 1.0, 0.90), (0.50, 0, 0.45), m["bone"])
    box("hband", (0.09, 1.02, 0.14), (0.50, 0, 0.22), m["teal"])


def _dirt(m):
    box("ground", (1, 1, 0.05), (0, 0, 0.025), m["dirt"])


def scrap_nw_cell():                          # appliance stack in the corner
    clear_scene(); m = _scrap_mats(); _dirt(m)
    box("fridge", (0.20, 0.16, 0.34), (0.12, 0.08, 0.19), m["steel"])
    box("stove", (0.18, 0.18, 0.22), (-0.04, -0.08, 0.13), m["paint"])
    box("plate", (0.30, 0.03, 0.28), (0.22, 0.22, 0.18), m["rust"], rot=(0, 0, 0.35))
    box("junk", (0.14, 0.14, 0.10), (-0.22, 0.16, 0.07), m["rust"])
    _chainlink("NW", m); rig_camera_and_light(); render("scrap_nw")


def scrap_n1_cell():                          # tarp + drying junk on the fence
    clear_scene(); m = _scrap_mats(); _dirt(m)
    box("tarp", (0.5, 0.02, 0.26), (0, 0.44, 0.30), m["drum"])
    box("heap", (0.24, 0.22, 0.14), (-0.10, -0.06, 0.10), m["rust"])
    box("bucket", (0.10, 0.10, 0.12), (0.18, 0.12, 0.08), m["steel"])
    for i in range(3):
        box(f"tyre{i}", (0.16, 0.16, 0.05), (0.26, -0.22, 0.03 + i * 0.055), m["tyre"])
    _chainlink("N", m); rig_camera_and_light(); render("scrap_n1")


def scrap_n2_cell():                          # the oldest pile: a sunken car
    clear_scene(); m = _scrap_mats(); _dirt(m)
    moss = make_material("scmoss", (0.24, 0.32, 0.18), 0.8, noise=0.5)
    box("body", (0.52, 0.26, 0.16), (0, -0.04, 0.10), m["rust"])
    box("cab", (0.24, 0.24, 0.12), (0.08, -0.04, 0.20), m["rust"])
    box("moss", (0.54, 0.28, 0.02), (0, -0.04, 0.19), moss)
    box("wheel", (0.04, 0.14, 0.12), (-0.24, 0.12, 0.07), m["tyre"])
    _chainlink("N", m); rig_camera_and_light(); render("scrap_n2")


def scrap_ne_cell():                          # shredded drift + a bathtub of bolts
    clear_scene(); m = _scrap_mats(); _dirt(m)
    box("drift", (0.42, 0.42, 0.09), (-0.08, -0.10, 0.06), m["steel"])
    for i, (sx, sy) in enumerate(((-0.20, -0.04), (0.02, -0.20), (-0.12, -0.24))):
        box(f"jag{i}", (0.08, 0.06, 0.14), (sx, sy, 0.10), m["rust"], rot=(0, 0.3, 0))
    box("tub", (0.20, 0.14, 0.12), (-0.24, 0.22, 0.08), m["bone"])
    box("bolts", (0.16, 0.10, 0.05), (-0.24, 0.22, 0.15), m["brass"])
    _chainlink("NE", m); rig_camera_and_light(); render("scrap_ne")


def scrap_w_cell():                           # a windbreak of stacked doors
    clear_scene(); m = _scrap_mats(); _dirt(m)
    for i, c in enumerate((m["paint"], m["steel"], m["drum"], m["rust"])):
        box(f"door{i}", (0.06, 0.30, 0.40), (-0.30 + i * 0.06, -0.14 + i * 0.10, 0.22), c)
    box("crate", (0.16, 0.16, 0.14), (0.22, -0.12, 0.10), m["rust"])
    _chainlink("W", m); rig_camera_and_light(); render("scrap_w")


def scrap_heap_cell():                         # THE HEAP — the yard's mountain
    clear_scene(); m = _scrap_mats(); _dirt(m)
    box("base", (0.72, 0.72, 0.24), (0, 0, 0.14), m["rust"])
    box("mid", (0.50, 0.50, 0.22), (0.06, -0.04, 0.32), m["steel"])
    box("top", (0.30, 0.30, 0.18), (-0.06, 0.08, 0.48), m["rust"])
    box("spar", (0.6, 0.04, 0.04), (0.10, 0.10, 0.42), m["steel"], rot=(0, 0.5, 0.4))
    box("drum", (0.12, 0.12, 0.20), (-0.30, -0.28, 0.12), m["drum"])
    rig_camera_and_light(); render("scrap_heap")


def scrap_mid_cell():                          # open ground, a cart, a car door
    clear_scene(); m = _scrap_mats(); _dirt(m)
    box("cart", (0.16, 0.22, 0.12), (0.14, 0.10, 0.10), m["steel"])
    box("cartleg", (0.02, 0.22, 0.02), (0.22, 0.10, 0.02), m["steel"])
    box("door", (0.04, 0.24, 0.22), (-0.20, -0.06, 0.13), m["paint"], rot=(0, 0.25, 0))
    box("heapA", (0.18, 0.18, 0.12), (0.30, -0.28, 0.09), m["rust"])
    box("heapB", (0.16, 0.16, 0.10), (-0.30, 0.30, 0.08), m["rust"])
    rig_camera_and_light(); render("scrap_mid")


def scrap_hull_cell():                          # salvage leaning on the Halcyon
    clear_scene(); m = _scrap_mats(); _dirt(m)
    _hull_wall(m)
    box("lean1", (0.10, 0.04, 0.44), (0.40, -0.12, 0.24), m["rust"], rot=(0.35, 0, 0))
    box("lean2", (0.10, 0.04, 0.40), (0.38, 0.16, 0.22), m["steel"], rot=(0.38, 0, 0))
    cylinder("spool", 0.12, 0.20, (-0.10, -0.06, 0.12), m["steel"], arc=math.pi * 2, seg=14)
    box("heap", (0.20, 0.20, 0.14), (-0.24, 0.20, 0.10), m["rust"])
    rig_camera_and_light(); render("scrap_hull")


def scrap_sw_cell():                            # engine-block cairn, greased black
    clear_scene(); m = _scrap_mats(); _dirt(m)
    blk = make_material("scblk", (0.10, 0.10, 0.11), 0.4, noise=0.3)
    box("e1", (0.18, 0.16, 0.14), (0.08, 0.06, 0.09), blk)
    box("e2", (0.16, 0.14, 0.12), (0.12, -0.04, 0.20), blk)
    box("e3", (0.14, 0.12, 0.10), (0.04, 0.10, 0.28), blk)
    box("drum", (0.12, 0.12, 0.18), (-0.22, 0.24, 0.11), m["drum"])
    _chainlink("SW", m); rig_camera_and_light(); render("scrap_sw")


def scrap_gate_cell():                          # the rolled-back gate + the sign
    clear_scene(); m = _scrap_mats(); _dirt(m)
    mesh = make_material("gmesh", (0.26, 0.27, 0.28), 0.5, noise=0.6)
    board = make_material("gboard", (0.50, 0.42, 0.20), 0.7, noise=0.3)
    for px in (-0.30, 0.30):                    # gate posts flanking the S opening
        box(f"gp{px}", (0.06, 0.06, 0.55), (px, -0.47, 0.27), m["steel"])
    box("gate", (0.30, 0.03, 0.42), (-0.16, -0.44, 0.23), mesh)   # rolled aside (open)
    box("grail", (0.34, 0.04, 0.03), (-0.14, -0.44, 0.42), m["steel"])
    box("sign", (0.22, 0.02, 0.14), (0.24, -0.46, 0.34), board)   # the board on the fence
    box("heap", (0.16, 0.16, 0.12), (0.26, 0.22, 0.09), m["rust"])
    rig_camera_and_light(); render("scrap_gate")


def scrap_weigh_cell():                         # the weighbridge + a crooked scale
    clear_scene(); m = _scrap_mats(); _dirt(m)
    box("plate", (0.5, 0.34, 0.03), (0, -0.04, 0.035), m["steel"])
    box("scalepost", (0.05, 0.05, 0.42), (0.28, 0.22, 0.23), m["steel"])
    box("dial", (0.14, 0.05, 0.14), (0.28, 0.25, 0.42), m["bone"])
    box("heap", (0.16, 0.16, 0.12), (-0.28, 0.22, 0.09), m["rust"])
    _chainlink("S", m); rig_camera_and_light(); render("scrap_weigh")


def scrap_se_cell():                            # crushed-cube tower + the dog-run
    clear_scene(); m = _scrap_mats(); _dirt(m)
    _hull_wall(m)
    cube = make_material("sccube", (0.30, 0.30, 0.26), 0.6, noise=0.3)
    for i in range(4):
        box(f"cube{i}", (0.24, 0.24, 0.06), (-0.08, 0.16, 0.05 + i * 0.065), cube)
    box("stake", (0.03, 0.03, 0.16), (-0.30, -0.18, 0.08), m["steel"])
    box("dish", (0.08, 0.08, 0.03), (-0.14, -0.24, 0.03), m["bone"])
    box("kennel", (0.16, 0.14, 0.12), (-0.30, -0.30, 0.08), m["rust"])
    _chainlink("S", m); rig_camera_and_light(); render("scrap_se")


# ------------------------------------------------- Queen of Cups rack roof
# One bespoke sprite per cell (the NW keeps its fallen mast). Parapet only
# on OUTER edges, so the rack reads as one roof, not a grid of tiles.
def _rack_mats():
    return {
        "tar": make_material("rktar", (0.14, 0.135, 0.13), 0.85, noise=0.4),
        "bone": make_material("rkbone", (0.25, 0.24, 0.21), 0.9, noise=0.3),
        "steel": make_material("rksteel", (0.34, 0.35, 0.36), 0.5, noise=0.3),
        "vent": make_material("rkvent", (0.22, 0.22, 0.20), 0.6),
        "pipe": make_material("rkpipe", (0.28, 0.34, 0.26), 0.5, noise=0.3),
        "warm": make_material("rkwarm", (0.9, 0.6, 0.3), 0.4,
                              emit=(1.0, 0.62, 0.30), emit_strength=2.4),
    }


def _parapet(sides, m):
    edge = {"N": (0, 0.47, "x"), "S": (0, -0.47, "x"),
            "E": (0.47, 0, "y"), "W": (-0.47, 0, "y")}
    for s in sides:
        cx, cy, ax = edge[s]
        sz = (1.0, 0.06, 0.11) if ax == "x" else (0.06, 1.0, 0.11)
        box(f"par{s}", sz, (cx, cy, 0.12), m["bone"])


def rack_sw_cell():                            # a bank of condensers
    clear_scene(); m = _rack_mats()
    box("deck", (1, 1, 0.10), (0, 0, 0.05), m["tar"])
    for i, (cx, cy) in enumerate(((0.10, 0.12), (0.30, 0.12), (0.10, -0.14))):
        box(f"cond{i}", (0.16, 0.16, 0.18), (cx, cy, 0.19), m["steel"])
        box(f"grl{i}", (0.12, 0.12, 0.02), (cx, cy, 0.29), m["warm"])
    _parapet("SW", m); rig_camera_and_light(); render("rack_sw")


def rack_s_cell():                             # condensate lines + roof vents
    clear_scene(); m = _rack_mats()
    box("deck", (1, 1, 0.10), (0, 0, 0.05), m["tar"])
    box("pipe1", (0.9, 0.05, 0.05), (0, 0.12, 0.15), m["pipe"])
    box("pipe2", (0.9, 0.05, 0.05), (0, 0.00, 0.13), m["pipe"])
    box("dive", (0.05, 0.05, 0.14), (0.22, 0.12, 0.10), m["pipe"])
    for cx in (-0.28, 0.28):
        cylinder(f"vent{cx}", 0.08, 0.14, (cx, -0.22, 0.16), m["vent"],
                 arc=math.pi * 2, seg=12)
        box(f"cap{cx}", (0.18, 0.18, 0.03), (cx, -0.22, 0.25), m["vent"])
    _parapet("S", m); rig_camera_and_light(); render("rack_s")


def rack_n_cell():                             # the hub: HVAC, aerial, laundry
    clear_scene(); m = _rack_mats()
    box("deck", (1, 1, 0.10), (0, 0, 0.05), m["tar"])
    box("hvac", (0.30, 0.24, 0.20), (-0.10, 0.06, 0.15), m["steel"])
    box("hvac2", (0.18, 0.18, 0.16), (0.22, -0.10, 0.13), m["vent"])
    box("mast", (0.03, 0.03, 0.50), (0.30, 0.24, 0.30), m["steel"])
    box("xarm", (0.22, 0.02, 0.02), (0.30, 0.24, 0.48), m["steel"])
    box("line", (0.6, 0.01, 0.01), (-0.05, -0.24, 0.34), m["steel"])
    for i, lx in enumerate((-0.20, 0.00, 0.16)):
        box(f"cloth{i}", (0.06, 0.02, 0.10), (lx, -0.24, 0.28), m["bone"])
    rig_camera_and_light(); render("rack_n")


def rack_se_cell():                            # the crane-jump corner
    clear_scene(); m = _rack_mats()
    worn = make_material("rkworn", (0.60, 0.62, 0.60), 0.35)
    box("deck", (1, 1, 0.10), (0, 0, 0.05), m["tar"])
    _parapet("E", m)                           # solid on the east, open to the jump
    box("rail", (0.7, 0.03, 0.03), (0, -0.44, 0.22), worn)      # worn grab-rail, S
    for px in (-0.28, 0.28):
        box(f"post{px}", (0.04, 0.04, 0.20), (px, -0.44, 0.14), m["steel"])
    box("coil", (0.12, 0.12, 0.06), (0.18, -0.18, 0.08), m["pipe"])
    rig_camera_and_light(); render("rack_se")


def rack_ne_cell():                            # the quiet milk-crate corner
    clear_scene(); m = _rack_mats()
    crate = make_material("rkcrate", (0.20, 0.30, 0.50), 0.6)
    wood = make_material("rkwood", (0.40, 0.30, 0.18), 0.8, noise=0.4)
    box("deck", (1, 1, 0.10), (0, 0, 0.05), m["tar"])
    _parapet("NE", m)
    box("crate", (0.14, 0.14, 0.14), (0.06, 0.06, 0.12), crate)
    box("pallet", (0.34, 0.04, 0.28), (0.02, 0.40, 0.21), wood)
    box("bottle", (0.04, 0.04, 0.10), (-0.14, 0.02, 0.10), m["pipe"])
    rig_camera_and_light(); render("rack_ne")


def rack_crown_cell():                         # the crown: stair hatch + sign
    clear_scene(); m = _rack_mats()
    brand = make_material("rkbrand", (0.72, 0.56, 0.22), 0.4,
                          emit=(0.8, 0.6, 0.25), emit_strength=1.6)
    box("deck", (1, 1, 0.10), (0, 0, 0.05), m["tar"])
    _parapet("NEW", m)                         # open south, toward the rack
    box("hatch", (0.28, 0.28, 0.16), (0, -0.02, 0.13), m["steel"])
    box("lid", (0.30, 0.22, 0.03), (0, 0.10, 0.24), m["steel"], rot=(0.4, 0, 0))
    box("plate", (0.34, 0.03, 0.12), (0, 0.46, 0.30), brand)   # brand plate
    rig_camera_and_light(); render("rack_crown")


# ----------------------------------------------------- Halcyon sun deck
# One consistent teal plating in every cell, with a ship's railing only on
# the OUTER perimeter edges, so the 2x2 reads as one deck, not four tiles.
def _deck_rail(sides, bone, steel):
    edge = {"N": (0, 0.47, "x"), "S": (0, -0.47, "x"),
            "E": (0.47, 0, "y"), "W": (-0.47, 0, "y")}
    for s in sides:
        cx, cy, ax = edge[s]
        lip = (1.0, 0.05, 0.05) if ax == "x" else (0.05, 1.0, 0.05)
        rail = (1.0, 0.02, 0.02) if ax == "x" else (0.02, 1.0, 0.02)
        box(f"lip{s}", lip, (cx, cy, 0.10), bone)
        box(f"rail{s}", rail, (cx, cy, 0.26), steel)
        for t in (-0.36, -0.12, 0.12, 0.36):
            p = (t, cy, 0.18) if ax == "x" else (cx, t, 0.18)
            box(f"stanch{s}{t}", (0.02, 0.02, 0.18), p, steel)


def _hdeck(name, sides, text=None):
    clear_scene()
    slab = make_material("hdslab", (0.16, 0.28, 0.27), 0.7, noise=0.3)
    bone = make_material("hdbone", (0.44, 0.44, 0.38), 0.7, noise=0.25)
    steel = make_material("hdsteel", (0.30, 0.31, 0.30), 0.55, noise=0.2)
    box("deck", (1, 1, 0.10), (0, 0, 0.05), slab)
    for i in range(3):                         # plating strips, consistent E-W
        box(f"strip{i}", (1.0, 0.02, 0.012), (0, -0.30 + i * 0.30, 0.105), bone)
    _deck_rail(sides, bone, steel)
    if text:
        paint = make_material("hdpaint", (0.60, 0.58, 0.50), 0.8,
                              emit=(0.62, 0.60, 0.52), emit_strength=0.8)
        bpy.ops.object.text_add(location=(0, 0, 0.115))
        t = bpy.context.active_object
        t.data.body = text
        t.data.font = bpy.data.fonts.load(FONT)
        t.data.size = 0.24
        t.data.extrude = 0.01
        t.data.align_x = "CENTER"; t.data.align_y = "CENTER"
        t.rotation_euler = (0, 0, 0.7854)
        t.scale = (-1, 1, 1)
        t.data.materials.append(paint)
        bpy.ops.object.convert(target="MESH")
    rig_camera_and_light(); render(name)


# -------------------------------------------------- The Kettle (bathhouse)
# A low worker bathhouse wearing onsen bones. Plaster walls on OUTER edges
# only + a consistent dark-tile roof, so the six cells read as one squat
# building under the towers; features (noren door, steaming chimney, the
# raised roof-lantern over the bath hall) keep the cells from tiling.
def _bath_mats():
    return {
        "tile": make_material("bktile", (0.16, 0.19, 0.24), 0.6, noise=0.3),
        "wall": make_material("bkwall", (0.42, 0.40, 0.35), 0.8, noise=0.3),
        "timber": make_material("bktimber", (0.24, 0.16, 0.11), 0.7, noise=0.3),
        "steam": make_material("bksteam", (0.80, 0.85, 0.90), 0.2,
                               emit=(0.70, 0.75, 0.82), emit_strength=1.5),
        "brick": make_material("bkbrick", (0.34, 0.20, 0.15), 0.7, noise=0.4),
        "indigo": make_material("bkindigo", (0.14, 0.18, 0.34), 0.6, noise=0.2),
        "warm": make_material("bkwarm", (0.9, 0.7, 0.4), 0.4,
                              emit=(1.0, 0.7, 0.35), emit_strength=2.0),
        "faded": make_material("bkfaded", (0.40, 0.34, 0.30), 0.8),
    }


def _kettle_shell(sides, m, eave=0.60):
    edge = {"N": (0, 0.5, "x"), "S": (0, -0.5, "x"),
            "E": (0.5, 0, "y"), "W": (-0.5, 0, "y")}
    for s in sides:
        cx, cy, ax = edge[s]
        wsz = (1.0, 0.06, eave) if ax == "x" else (0.06, 1.0, eave)
        box(f"wall{s}", wsz, (cx, cy, eave / 2), m["wall"])
    box("roof", (1.03, 1.03, 0.06), (0, 0, eave + 0.03), m["tile"])
    box("ridge", (1.03, 0.16, 0.06), (0, 0, eave + 0.09), m["tile"])
    for ey in (0.5, -0.5):
        box(f"eave{ey}", (1.05, 0.05, 0.03), (0, ey, eave - 0.01), m["timber"])


def kettle_entrance_cell():                    # noren door on the Pessoa face
    clear_scene(); m = _bath_mats()
    _kettle_shell("SE", m)
    box("recess", (0.30, 0.06, 0.42), (-0.12, -0.5, 0.21), m["warm"])   # lit doorway
    for nx in (-0.20, -0.04):                                           # noren panels
        box(f"noren{nx}", (0.12, 0.02, 0.20), (nx, -0.52, 0.34), m["indigo"])
    box("sign", (0.34, 0.03, 0.10), (-0.12, -0.53, 0.50), m["faded"])   # faded board
    box("peak", (0.08, 0.02, 0.06), (-0.12, -0.55, 0.52), m["timber"])  # a worn mountain glyph
    rig_camera_and_light(); render("kettle_entrance")


def kettle_boiler_cell():                      # the heat exchanger's chimney
    clear_scene(); m = _bath_mats()
    _kettle_shell("SW", m)
    box("stack", (0.16, 0.16, 0.55), (0.24, 0.24, 0.88), m["brick"])    # chimney
    box("cap", (0.20, 0.20, 0.05), (0.24, 0.24, 1.16), m["timber"])
    box("plume", (0.14, 0.14, 0.28), (0.24, 0.24, 1.34), m["steam"])    # steam
    box("plume2", (0.20, 0.20, 0.16), (0.24, 0.20, 1.52), m["steam"])
    rig_camera_and_light(); render("kettle_boiler")


def kettle_changing_cell():                    # a modest roof vent
    clear_scene(); m = _bath_mats()
    _kettle_shell("E", m)
    box("vent", (0.20, 0.20, 0.10), (-0.10, 0.10, 0.72), m["timber"])
    box("vsteam", (0.10, 0.10, 0.14), (-0.10, 0.10, 0.84), m["steam"])
    rig_camera_and_light(); render("kettle_changing")


def kettle_plunge_cell():                      # cold side, a small vent
    clear_scene(); m = _bath_mats()
    _kettle_shell("W", m)
    box("vent", (0.18, 0.18, 0.08), (0.12, -0.08, 0.70), m["timber"])
    rig_camera_and_light(); render("kettle_plunge")


def _kettle_lantern(m):                         # the raised roof-lantern (yagura)
    box("yagbase", (0.46, 0.46, 0.16), (0, 0, 0.74), m["timber"])
    box("yagroof", (0.54, 0.54, 0.05), (0, 0, 0.85), m["tile"])
    box("yagsteam", (0.30, 0.30, 0.22), (0, 0, 0.98), m["steam"])


def kettle_hall_cell():                         # the great bath, steaming
    clear_scene(); m = _bath_mats()
    _kettle_shell("NE", m)
    _kettle_lantern(m)
    rig_camera_and_light(); render("kettle_hall")


def kettle_mural_cell():                        # the mural wall of the hall
    clear_scene(); m = _bath_mats()
    _kettle_shell("NW", m)
    _kettle_lantern(m)
    box("skylight", (0.16, 0.16, 0.03), (0.14, 0.14, 0.65), m["warm"])
    rig_camera_and_light(); render("kettle_mural")


#: The Boot's hull, matched to hull_cell — SAME material, camber and rivets,
#: so sealed sections read as one continuous derelict with the walkable
#: decks, only welded shut (a dark crown where the deck's pale plate would be).
def _boot_hull_mats():
    return (make_material("bhhull", (0.42, 0.26, 0.17), 0.75, noise=0.55),
            make_material("bhweld", (0.20, 0.13, 0.10), 0.9),
            make_material("bhrivet", (0.30, 0.20, 0.14), 0.6))


def _boot_hull_crown(weld, rivet, base=0.0, r=0.635):
    """The welded-shut crown treatment (in place of hull_cell's pale deck):
    a dark sealed plate, a longitudinal weld, banded welds, a faded stencil,
    a rivet row — all riding a camber whose crest sits at ``base + r``."""
    seal = make_material(f"bhseal{base}", (0.30, 0.21, 0.15), 0.85, noise=0.35)
    sten = make_material(f"bhsten{base}", (0.40, 0.34, 0.28), 0.9)
    cylinder("plate", r, r * 0.66, (0, 0, base), seal, arc=math.pi * 0.6)
    box("seamL", (2 * r - 0.1, 0.035, 0.02), (0, 0, base + r), weld)
    for wx in (-0.34, 0.02, 0.38):
        cylinder(f"weld{wx}", r + 0.01, 0.05, (wx, 0, base), weld,
                 arc=math.pi * 0.85)
    box("mark", (0.18, 0.02, 0.09),
        (-0.18, (r - 0.05) * math.cos(math.pi * 0.35),
         base + (r - 0.05) * math.sin(math.pi * 0.35)),
        sten, rot=(math.pi * 0.35 - math.pi / 2, 0, 0))
    for i in range(7):
        a = math.pi * (0.18 + 0.09 * i)
        box(f"riv{i}", (0.035, 0.035, 0.035),
            (-0.42 + i * 0.14, (r - 0.02) * math.cos(a),
             base + (r - 0.02) * math.sin(a)), rivet)


def sealed_hull_cell():
    """A welded-shut hull-TOP cap between the walkable decks — hull_cell's
    own 0.62 camber and material, sealed, so it flows straight into them."""
    clear_scene()
    hullm, weld, rivet = _boot_hull_mats()
    cylinder("camber", 0.62, 1.0, (0, 0, 0), hullm, arc=math.pi * 0.9)
    _boot_hull_crown(weld, rivet, base=0.0, r=0.635)
    rig_camera_and_light()
    render("sealed_hull")


def hull_mass_cell():
    """The dead ground around the market, decked over — a low, flat,
    welded-shut hull plate in the Boot's own material: no hump, no wall to
    occlude the market, just closed riveted steel that says 'not here'."""
    clear_scene()
    hullm, weld, rivet = _boot_hull_mats()
    dark = make_material("hmdark", (0.24, 0.16, 0.11), 0.85, noise=0.4)
    box("plate", (0.98, 0.98, 0.14), (0, 0, 0.07), hullm)      # flat hull plate
    box("edge", (1.0, 1.0, 0.05), (0, 0, 0.02), dark)          # grimy shadow edge
    box("weldX1", (1.02, 0.06, 0.035), (0, 0, 0.15), weld, rot=(0, 0, 0.6))
    box("weldX2", (1.02, 0.06, 0.035), (0, 0, 0.15), weld, rot=(0, 0, -0.6))
    for sx, sy in ((0.44, 0.44), (-0.44, 0.44), (0.44, -0.44), (-0.44, -0.44)):
        box(f"bolt{sx}{sy}", (0.06, 0.06, 0.05), (sx, sy, 0.15), rivet)
    for rx in (-0.28, 0.0, 0.28):
        for ry in (-0.28, 0.0, 0.28):
            box(f"riv{rx}{ry}", (0.03, 0.03, 0.03), (rx, ry, 0.15), rivet)
    rig_camera_and_light()
    render("hull_mass")


# ---------------------------------------------- Hammett's Boot: copper vault
# The derelict re-clad as ONE hooped copper hull that reads as a boot: a
# verdigris barrel vault over the market (the foot), rising into the ankle at
# the heel and a star-peaked spur at the toe. Copper streaked through the
# patina to hint at the vague, grander origin.
def _boot_copper():
    return (make_material("bcpat", (0.26, 0.44, 0.38), 0.5, noise=0.45),   # verdigris
            make_material("bccop", (0.54, 0.34, 0.18), 0.45, noise=0.35),  # bright copper
            make_material("bclit", (0.9, 0.6, 0.3), 0.4, emit=(1.0, 0.62, 0.28)))


def _boot_ribs(r, base, mat):
    for wx in (-0.35, 0.0, 0.35):                       # hoop ribs across the vault
        cylinder(f"rib{wx}", r + 0.02, 0.05, (wx, 0, base), mat, arc=math.pi)


#: Uniform cladding: every Boot cell is the SAME copper hull at the SAME
#: height, flat parapet top, vertical copper strakes — so they tile flush and
#: the footprint (not per-cell curves) carries the boot shape.
_BOOT_H = 0.88


def _boot_clad(pat, cop):
    box("wall", (0.99, 0.99, _BOOT_H), (0, 0, _BOOT_H / 2), pat)
    box("grime", (1.0, 1.0, 0.14), (0, 0, 0.07), cop)              # waterline
    box("cap", (0.93, 0.93, 0.06), (0, 0, _BOOT_H), cop)           # copper roof cap
    box("rim", (1.0, 1.0, 0.05), (0, 0, _BOOT_H - 0.03), pat)      # parapet rim
    for t in (-0.36, -0.12, 0.12, 0.36):                          # vertical strakes
        box(f"strY{t}", (0.03, 0.02, _BOOT_H - 0.14), (t, 0.50, _BOOT_H / 2), cop)
        box(f"strX{t}", (0.02, 0.03, _BOOT_H - 0.14), (-0.50, t, _BOOT_H / 2), cop)


def boot_arch_cell():
    """A market bay of the copper Boot — full-height verdigris hull, copper
    strakes and a flat parapet, lit market windows. Tiles flush with its
    neighbours so the footprint reads as one cohesive copper hull."""
    clear_scene()
    pat, cop, lit = _boot_copper()
    _boot_clad(pat, cop)
    for t in (-0.28, 0.0, 0.28):                                   # lit windows
        box(f"winY{t}", (0.13, 0.02, 0.22), (t, 0.505, 0.42), lit)
        box(f"winX{t}", (0.02, 0.13, 0.22), (-0.505, t, 0.42), lit)
    rig_camera_and_light()
    render("boot_arch")


def boot_flank_cell():
    """A blank copper-hull section at the Boot's edges — same cladding and
    height as the bays but no windows, so the sides read as solid hull and
    line up flush."""
    clear_scene()
    pat, cop, _ = _boot_copper()
    _boot_clad(pat, cop)
    for i in range(4):                                            # rivet rows
        for j in range(3):
            box(f"riv{i}{j}", (0.03, 0.03, 0.03),
                (-0.30 + i * 0.20, 0.505, 0.22 + j * 0.22), cop)
    rig_camera_and_light()
    render("boot_flank")


def boot_spur_cell():
    """The toe's spur — the copper hull carried up into a faceted star-peak
    roof with a finial. The one flourish (a single cell, so it needn't tile)
    that earns the boot its silhouette."""
    clear_scene()
    pat, cop, lit = _boot_copper()
    box("drum", (0.9, 0.9, 0.62), (0, 0, 0.31), pat)
    box("grime", (0.92, 0.92, 0.12), (0, 0, 0.06), cop)
    for t in (-0.2, 0.2):
        box(f"slitY{t}", (0.10, 0.02, 0.18), (t, 0.46, 0.36), lit)
        box(f"slitX{t}", (0.02, 0.10, 0.18), (-0.46, t, 0.36), lit)
    for i, (rr, zz) in enumerate(((0.48, 0.62), (0.36, 0.80),
                                  (0.24, 0.96), (0.11, 1.10))):
        cylinder(f"peak{i}", rr, 0.16, (0, 0, zz), cop if i % 2 else pat,
                 arc=math.pi * 2, seg=6)
    box("finial", (0.05, 0.05, 0.22), (0, 0, 1.18), cop)
    rig_camera_and_light()
    render("boot_spur")


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
    curb = make_material("curb1", (0.17, 0.16, 0.15), 0.9, noise=0.3)
    oil = make_material("oil", (0.03, 0.035, 0.05), 0.15)
    box("slab", (1, 1, 0.08), (0, 0, 0.04), asphalt)
    box("curb_n", (1, 0.07, 0.055), (0, 0.465, 0.055), curb)
    box("curb_s", (1, 0.07, 0.055), (0, -0.465, 0.055), curb)
    box("patch1", (0.34, 0.26, 0.004), (-0.16, 0.10, 0.084), patch)
    box("patch2", (0.22, 0.18, 0.004), (0.24, -0.14, 0.084), patch)
    cylinder("oilstain", 0.14, 0.006, (0.05, 0.22, 0.083), oil,
             seg=14, arc=math.pi * 2)


def _street_cracked():
    """Cracked and littered — the colony's deferred maintenance."""
    asphalt = make_material("asphalt2", (0.08, 0.078, 0.09), 0.45,
                            noise=0.5, wet=True)
    curb = make_material("curb2", (0.16, 0.15, 0.14), 0.9, noise=0.3)
    crackm = make_material("crack2", (0.04, 0.04, 0.05), 1.0)
    debris = make_material("debris", (0.20, 0.16, 0.12), 0.95, noise=0.4)
    box("slab", (1, 1, 0.08), (0, 0, 0.04), asphalt)
    box("curb_n", (1, 0.07, 0.055), (0, 0.465, 0.055), curb)
    box("curb_s", (1, 0.07, 0.055), (0, -0.465, 0.055), curb)
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
        # Rotate the LOCATION and the box, and leave the size alone.
        #
        # This used to swap size[0]/size[1] at 90 degrees AND apply the
        # rotation, which cancel: a 0.55x0.30 bed became 0.30x0.55 and then
        # rotated back to 0.55 along X. The parts still moved a quarter turn
        # though, so hauler_y came out with its cab beside the bed instead of
        # at the end of it — a truck that does not line up with anything.
        x, y = R(loc[0], loc[1])
        box(n, size, (x, y, loc[2]), mat, rot=(0, 0, rz + extra_rz))
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
            # Same fix as the hauler: rotate the location and the box, never
            # the size. Swapping the dimensions AND rotating cancels out, so
            # van_y kept an X-aligned shell while its parts moved a quarter
            # turn — the windscreen ended up on the long side.
            x, y = R(loc[0], loc[1])
            box(n, size, (x, y, loc[2]), mat, rot=(0, 0, rz))
        rbox("shell", (0.52, 0.24, 0.24), (0, 0, 0.20), body)
        rbox("wind", (0.02, 0.20, 0.09), (0.265, 0, 0.26), glass)
        for wx in (-0.16, 0.16):
            for side in (-0.14, 0.14):
                x, y = R(wx, side)
                box(f"vw{wx}{side}", (0.09, 0.03, 0.09), (x, y, 0.05), tire,
                    rot=(0, 0, rz))
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
    # the far faces
    for wx, litw in [(-0.20, False), (0.22, True)]:
        box(f"wfn{wx}", (0.24, 0.02, 0.34), (wx, -0.505, 0.52), frame)
        box(f"wgn{wx}", (0.20, 0.015, 0.28), (wx, -0.512, 0.52),
            lit if litw else dark)
    for we, litw in [(-0.10, True), (0.24, False)]:
        box(f"wew{we}", (0.02, 0.20, 0.30), (-0.505, we, 0.60), frame)
        box(f"wgew{we}", (0.015, 0.16, 0.24), (-0.512, we, 0.60),
            lit if litw else dark)
    box("balc_w", (0.34, 0.10, 0.03), (-0.51, 0.16, 0.62), rail)
    box("balcr_w", (0.34, 0.02, 0.10), (-0.51, 0.205, 0.69), rail)
    rig_camera_and_light()
    render("tenement_1")


def roof_variant_1():
    """Skylight and pipework instead of the tank."""
    clear_scene()
    tar = make_material("tar1", (0.14, 0.135, 0.13), 0.85, noise=0.4)
    bone = make_material("parapet1", (0.23, 0.22, 0.19), 0.9, noise=0.3)
    glass = make_material("sky1", (0.14, 0.30, 0.34), 0.2,
                          emit=(0.22, 0.42, 0.46), emit_strength=0.5)
    pipe = make_material("rpipe", (0.24, 0.22, 0.20), 0.55)
    box("slab", (1, 1, 0.10), (0, 0, 0.05), tar)
    for loc, size in ((( 0, 0.47, 0.115), (1, 0.05, 0.07)),
                      (( 0, -0.47, 0.115), (1, 0.05, 0.07)),
                      ((0.47, 0, 0.115), (0.05, 0.88, 0.07)),
                      ((-0.47, 0, 0.115), (0.05, 0.88, 0.07))):
        box(f"par{loc}", size, loc, bone)
    box("skylight", (0.30, 0.24, 0.06), (-0.14, 0.10, 0.13), glass,
        rot=(0, math.radians(-8), 0))
    box("pipe1", (0.50, 0.05, 0.05), (0.10, -0.24, 0.13), pipe)
    box("pipe2", (0.05, 0.05, 0.22), (0.33, -0.24, 0.21), pipe)
    rig_camera_and_light()
    render("roof_1")


def roof_variant_2():
    """The HVAC cluster: condenser pair, fan cowl, duct run."""
    clear_scene()
    tar = make_material("tar2", (0.14, 0.135, 0.13), 0.85, noise=0.4)
    bone = make_material("parapet2", (0.23, 0.22, 0.19), 0.9, noise=0.3)
    unit = make_material("hvac", (0.30, 0.30, 0.28), 0.55, noise=0.2)
    grill = make_material("grill", (0.10, 0.11, 0.11), 0.5)
    duct = make_material("duct2", (0.26, 0.25, 0.22), 0.6)
    box("slab", (1, 1, 0.10), (0, 0, 0.05), tar)
    for loc, size in ((( 0, 0.47, 0.115), (1, 0.05, 0.07)),
                      (( 0, -0.47, 0.115), (1, 0.05, 0.07)),
                      ((0.47, 0, 0.115), (0.05, 0.88, 0.07)),
                      ((-0.47, 0, 0.115), (0.05, 0.88, 0.07))):
        box(f"par{loc}", size, loc, bone)
    box("unit_a", (0.30, 0.24, 0.24), (-0.16, 0.14, 0.22), unit)
    box("grill_a", (0.02, 0.20, 0.18), (-0.005, 0.14, 0.22), grill)
    box("unit_b", (0.26, 0.22, 0.20), (0.20, 0.16, 0.20), unit)
    cylinder("cowl", 0.13, 0.10, (0, 0, 0), grill, seg=16, arc=math.pi * 2)
    for o in bpy.context.collection.objects:
        if o.name == "cowl":
            o.rotation_euler = (0, math.radians(90), 0)
            o.location = (0.06, -0.24, 0.155)
    box("duct_r", (0.44, 0.09, 0.09), (-0.12, -0.24, 0.145), duct)
    box("duct_d", (0.09, 0.09, 0.10), (-0.32, -0.24, 0.10), duct)
    rig_camera_and_light()
    render("roof_2")


def roof_variant_3():
    """The sealed roof: bare blistered field, capped stack, no service."""
    clear_scene()
    tar = make_material("tar3", (0.135, 0.13, 0.125), 0.85, noise=0.5)
    bone = make_material("parapet3", (0.22, 0.21, 0.18), 0.9, noise=0.3)
    patch = make_material("patch", (0.10, 0.10, 0.10), 0.9)
    stack = make_material("stack3", (0.24, 0.22, 0.20), 0.6, noise=0.2)
    box("slab", (1, 1, 0.10), (0, 0, 0.05), tar)
    for loc, size in ((( 0, 0.47, 0.115), (1, 0.05, 0.07)),
                      (( 0, -0.47, 0.115), (1, 0.05, 0.07)),
                      ((0.47, 0, 0.115), (0.05, 0.88, 0.07)),
                      ((-0.47, 0, 0.115), (0.05, 0.88, 0.07))):
        box(f"par{loc}", size, loc, bone)
    box("patch_a", (0.30, 0.22, 0.004), (-0.14, 0.16, 0.102), patch)
    box("patch_b", (0.18, 0.26, 0.004), (0.22, -0.18, 0.102), patch)
    box("patch_c", (0.14, 0.12, 0.004), (0.10, 0.30, 0.102), patch)
    box("stack", (0.10, 0.10, 0.16), (0.30, 0.28, 0.18), stack)
    box("stackcap", (0.14, 0.14, 0.03), (0.30, 0.28, 0.27), stack)
    rig_camera_and_light()
    render("roof_3")


def _street_intersection():
    """The crossing: orientation-free — corner nubs, no through-curbs."""
    asphalt = make_material("asphalti", (0.075, 0.075, 0.095), 0.3,
                            noise=0.4, wet=True)
    curb = make_material("curbi", (0.17, 0.16, 0.15), 0.9, noise=0.3)
    iron = make_material("ironi", (0.06, 0.06, 0.065), 0.6)
    box("slab", (1, 1, 0.08), (0, 0, 0.04), asphalt)
    for cx in (-0.44, 0.44):
        for cy in (-0.44, 0.44):
            box(f"nub{cx}{cy}", (0.10, 0.10, 0.055), (cx, cy, 0.055), curb)
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
                          emit=(0.12, 0.30, 0.34), emit_strength=1.4)
    frost = make_material("cryow", (0.34, 0.39, 0.41), 0.7, noise=0.3)
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
    fire_escape_cell()
    machine_cell()
    garden_cell()
    garden_bed_cell()
    garden_bench_cell()
    mast_segment_cell()
    mast_base_cell()
    fallen_span_cell()
    fallen_tower_cell()
    catwalk_cell()
    garden_path_cell()
    # BRACKETT ARMS as a continuous vertical run, even spacing (~0.45),
    # a wide word gap between the T and the A; z11 (top) down to z6.
    for nm, g in (("marquee_1", [("B", 0.85), ("R", 0.40)]),
                  ("marquee_2", [("A", 0.95), ("C", 0.50), ("K", 0.05)]),
                  ("marquee_3", [("E", 0.60), ("T", 0.15)]),
                  ("marquee_4", [("T", 0.70)]),
                  ("marquee_5", [("A", 0.50), ("R", 0.05)])):
        _marquee_glyphs(nm, g)
    _marquee_loggia("marquee_6", [("M", 0.60), ("S", 0.20)])   # 6th-floor band
    # the same name as a deco blade sign hanging in the canyon (below
    # the catwalk); identical z-bands so the lettering lines up, z11->z6;
    # ribs = the gold banding, placed between the letters per tile.
    _air_marquee("air_marquee_1", [("B", 0.85), ("R", 0.40)],
                 [0.625, 0.175, 0.02], crown=True)
    _air_marquee("air_marquee_2", [("A", 0.95), ("C", 0.50), ("K", 0.05)],
                 [0.725, 0.275])
    _air_marquee("air_marquee_3", [("E", 0.60), ("T", 0.15)],
                 [0.98, 0.375])
    _air_marquee("air_marquee_4", [("T", 0.70)],
                 [0.98, 0.45, 0.20])              # word-gap tile, banded
    _air_marquee("air_marquee_5", [("A", 0.50), ("R", 0.05)],
                 [0.98, 0.75, 0.275])
    _air_marquee("air_marquee_6", [("M", 0.60), ("S", 0.20)],
                 [0.98, 0.40], finial=True)
    # the Halcyon's own identity: prefab liner hull modules + sun deck
    liner_cell()
    _liner_reg("liner_reg_a", "SBL-")
    _liner_reg("liner_reg_b", "0117")
    liner_deck_cell()
    _liner_deck_stencil("liner_deck_halcyon", "HALCYON")
    _liner_deck_stencil("liner_deck_days", "DAYS")
    # the Marlowe Lot: Boiler Run tower crane + fenced dig
    crane_mast_cell()
    crane_cab_cell()
    crane_jib_cell()
    crane_jibtip_cell()
    crane_container_cell()
    crane_chain_cell()
    # The Midden — one bespoke sprite per cell, no repeats
    scrap_nw_cell(); scrap_n1_cell(); scrap_n2_cell(); scrap_ne_cell()
    scrap_w_cell(); scrap_heap_cell(); scrap_mid_cell(); scrap_hull_cell()
    scrap_sw_cell(); scrap_gate_cell(); scrap_weigh_cell(); scrap_se_cell()
    # Queen of Cups rack roof — bespoke per cell (NW keeps fallen_tower)
    rack_sw_cell(); rack_s_cell(); rack_n_cell()
    rack_se_cell(); rack_ne_cell(); rack_crown_cell()
    # Halcyon sun deck — one consistent deck, railing on the outer perimeter
    _hdeck("hdeck_sw", "SW", text="DAYS")
    _hdeck("hdeck_se", "SE")
    _hdeck("hdeck_nw", "NW")
    _hdeck("hdeck_ne", "NE", text="HALCYON")
    # The Kettle — worker bathhouse, onsen bones
    kettle_entrance_cell(); kettle_boiler_cell(); kettle_changing_cell()
    kettle_plunge_cell(); kettle_hall_cell(); kettle_mural_cell()
    sealed_hull_cell(); hull_mass_cell()
    boot_arch_cell(); boot_flank_cell(); boot_spur_cell()  # Hammett copper vault
    crane_lot_cell()
    crane_base_cell()
    crane_dig_cell()
    loggia_cell()
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
    roof_variant_2()
    roof_variant_3()
    print("rig complete")


if __name__ == "__main__":
    main()
