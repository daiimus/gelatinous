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

# the heel: a larger-radius vault section on the SAME axis — the
# boot's thick end, not a separate object; steps down to the shank
# at a heavy shoulder hoop
rig.cylinder("heelvault", 0.74, 1.0, (0.30, 0, 0), hull,
             arc=math.pi * 0.94)
rig.box("heelgable", (0.10, 1.44, 0.70), (-0.16, 0, 0.35), hull)
rig.cylinder("shoulder", 0.76, 0.10, (0.78, 0, 0), weld,
             arc=math.pi * 0.9)

# the hangar vault: one continuous barrel over the market street,
# hooped like a quonset — the enclosure IS the architecture
rig.cylinder("vault", 0.60, 5.0, (2.75, 0, 0), hull, arc=math.pi * 0.94)
for i in range(10):                                # the hoops
    wx = 0.85 + i * 0.46
    rig.cylinder(f"hoop{i}", 0.635, 0.07, (wx, 0, 0), weld,
                 arc=math.pi * 0.9)
for i in range(4):                                 # crown glazing: market
    gx = 1.3 + i * 1.0                             # light through the skin
    rig.cylinder(f"glaze{i}", 0.615, 0.30, (gx, 0, 0), glow,
                 arc=math.pi * 0.16)
    for o in bpy.context.collection.objects:
        if o.name == f"glaze{i}":
            o.rotation_euler = (math.radians(48), 0, 0)
rig.cylinder("plate", 0.645, 0.9, (2.2, 0, 0), pale, arc=math.pi * 0.4)
# toe cap: the hangar's blunt gable end
rig.cylinder("toe", 0.57, 0.9, (5.0, 0, 0), hull, arc=math.pi * 0.95)
rig.box("toecap", (0.10, 1.08, 0.54), (5.44, 0, 0.27), hull)
# the junction: a heavy weld collar where drum meets vault — one
# continuous piece of salvage, no holes in the hull
rig.cylinder("collar", 0.655, 0.14, (0.42, 0, 0), weld,
             arc=math.pi * 0.9)
# the Throat: a flush entrance door in the north flank — no geometry
# leaves the hull; the opening is surface language, like a real hangar
rig.box("throat_door", (0.46, 0.05, 0.34), (0.45, 0.565, 0.17), dark,
        rot=(math.radians(-16), 0, 0))
rig.box("throat_lintel", (0.54, 0.05, 0.06), (0.45, 0.545, 0.37), weld,
        rot=(math.radians(-16), 0, 0))
rig.box("throat_glow", (0.34, 0.04, 0.10), (0.45, 0.585, 0.08), glow,
        rot=(math.radians(-16), 0, 0))

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
        (1.55, 0.615 * math.cos(math.pi * 0.35),
         0.615 * math.sin(math.pi * 0.35)), stenc,
        rot=(math.pi * 0.35 - math.pi / 2, 0, 0))
# --- market-hall language: the silhouette must not read as a pipe ---
lit = rig.make_material("mlit", (0.9, 0.6, 0.3), 0.4,
                        emit=(1.0, 0.62, 0.28), emit_strength=2.0)
canvas_a = rig.make_material("canv_a", (0.42, 0.16, 0.13), 0.9, noise=0.3)
canvas_b = rig.make_material("canv_b", (0.52, 0.44, 0.20), 0.9, noise=0.3)

# clerestory: a raised lit ridge along the crown — the giveaway that this
# is a hall people are inside of, not a length of conduit
rig.box("clerestory", (4.3, 0.34, 0.20), (2.85, 0, 0.68), hull)
for i in range(11):
    rig.box(f"cwin{i}", (0.22, 0.36, 0.10), (0.95 + i * 0.40, 0, 0.70), lit)
rig.box("ridge", (4.4, 0.42, 0.06), (2.85, 0, 0.80), weld)

# ridge vents: three turbine cowls standing off the ridge
for vx in (1.45, 2.85, 4.25):
    rig.cylinder(f"vent{int(vx*100)}", 0.10, 0.14, (0, 0, 0), weld, seg=12,
                 arc=math.pi * 2)
    for o in bpy.context.collection.objects:
        if o.name == f"vent{int(vx*100)}":
            o.location = (vx, 0.0, 0.90)

# stall awnings along the south flank — the market spilling out
for i, ax in enumerate((1.15, 1.95, 2.75, 3.55, 4.35)):
    mat = canvas_a if i % 2 == 0 else canvas_b
    rig.box(f"awn{i}", (0.62, 0.44, 0.05), (ax, 0.74, 0.36), mat,
            rot=(math.radians(-16), 0, 0))
    rig.box(f"awnpost{i}a", (0.04, 0.04, 0.30), (ax - 0.26, 0.92, 0.15), weld)
    rig.box(f"awnpost{i}b", (0.04, 0.04, 0.30), (ax + 0.26, 0.92, 0.15), weld)
    rig.box(f"stallglow{i}", (0.46, 0.06, 0.05), (ax, 0.70, 0.22), lit)

# ground shadow catcher
catcher = rig.make_material("ground", (0.5, 0.5, 0.5), 1.0)
g = rig.box("gplane", (10, 6, 0.01), (2.5, 0, -0.005), catcher)
g.is_shadow_catcher = True

rig.rig_camera_and_light(ortho=8.125, target=(2.5, 0, 0.4))
rig.render("boot", res=1600)

# self-calibration: the local origin under THIS camera
rig.clear_scene()
m = rig.make_material("mk", (1, 1, 1), 0.2, emit=(1, 1, 1))
rig.box("marker", (0.04, 0.04, 0.04), (0, 0, 0), m)
rig.rig_camera_and_light(ortho=8.125, target=(2.5, 0, 0.4))
rig.render("calib_boot", res=1600)
print("landmark boot rendered")
