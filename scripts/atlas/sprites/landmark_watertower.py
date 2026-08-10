"""The Spillane water tower: Greenhaus Cistern No. 3 (§3.5 hero).

    blender --background --python scripts/atlas/sprites/landmark_watertower.py

The agricultural quarter's first piece of street furniture — a fat
riveted cistern on four splayed legs, tucked against the crater wall on
Spillane's east band at world (13,-15). Greenhaus-branded (the ag
brand), condensation-streaked, overflow pipe weeping down one leg. A
square service catwalk rings the tank's waist — future low-line
waypoint. Night read: a red air-hazard beacon on the crown, a warm work
lamp under the belly, and a lit level-gauge strip so it glows enough to
exist after dark.

ONE CELL footprint: every part inside local X/Y [±0.5] (verified
numerically against the bake). Local origin = the cell's base center;
crest ~z4.5 so it reads above the future growrack tiers (z2-4).
Solid volumes only — the tank gets a lid; no open shells.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import rig  # noqa: E402

rig.clear_scene()

steel = rig.make_material("wtsteel", (0.50, 0.54, 0.49), 0.8, noise=0.30)  # pale weathered paint
rust = rig.make_material("wtrust", (0.30, 0.19, 0.12), 0.9, noise=0.45)
# Greenhaus green, softly floodlit — the big band surface is what makes
# the tank exist at night (small bulbs alone leave it a silhouette)
band = rig.make_material("wtband", (0.14, 0.26, 0.17), 0.75, noise=0.25,
                         emit=(0.35, 0.62, 0.40), emit_strength=1.3)
seam = rig.make_material("wtseam", (0.06, 0.07, 0.08), 0.9)
paint = rig.make_material("wtpaint", (0.55, 0.62, 0.50), 0.8,
                          emit=(0.65, 0.95, 0.60), emit_strength=2.4)  # lit brand
beacon = rig.make_material("wtbeacon", (0.9, 0.15, 0.1), 0.4,
                           emit=(1.0, 0.12, 0.08), emit_strength=4.0)
lamp = rig.make_material("wtlamp", (1.0, 0.62, 0.28), 0.4,
                         emit=(1.0, 0.62, 0.28), emit_strength=2.5)
gauge = rig.make_material("wtgauge", (0.2, 0.5, 0.3), 0.4,
                          emit=(0.25, 0.6, 0.35), emit_strength=0.9)
wet = rig.make_material("wtwet", (0.10, 0.13, 0.14), 0.2, wet=True)

# 1 — four splayed legs, ground to the tank belly (z2.3), cross-braced
for i, (sx, sy) in enumerate(((1, 1), (1, -1), (-1, 1), (-1, -1))):
    rig.box(f"leg{i}", (0.10, 0.10, 2.45), (sx * 0.30, sy * 0.30, 1.18), rust,
            rot=(math.radians(-7 * sy), math.radians(7 * sx), 0))
    rig.box(f"foot{i}", (0.16, 0.16, 0.08), (sx * 0.40, sy * 0.40, 0.04), seam)
rig.box("braceX", (0.84, 0.07, 0.07), (0, 0, 0.95), rust, rot=(0, 0, math.radians(45)))
rig.box("braceY", (0.84, 0.07, 0.07), (0, 0, 1.55), rust, rot=(0, 0, math.radians(-45)))

# 2 — the tank: a fat closed drum (full-arc cylinder stood upright + lid,
#     so nothing is see-through from above), riveted, green brand band
tank = rig.cylinder("tank", 0.45, 1.7, (0, 0, 0), steel, seg=20, arc=math.pi * 2)
tank.location = (0, 0, 3.15)
tank.rotation_euler = (0, math.radians(90), 0)
rig.box("tankbtm", (0.66, 0.66, 0.10), (0, 0, 2.32), seam)      # belly plate
rig.box("lid", (0.80, 0.80, 0.10), (0, 0, 4.02), steel)          # wide lid
rig.box("lidcap", (0.5, 0.5, 0.10), (0, 0, 4.10), rust)          # crown step
gb = rig.cylinder("brandband", 0.465, 0.42, (0, 0, 0), band, seg=20, arc=math.pi * 2)
gb.location = (0, 0, 3.30)
gb.rotation_euler = (0, math.radians(90), 0)
for k in range(3):                                               # hoop seams
    h = rig.cylinder(f"hoop{k}", 0.462, 0.05, (0, 0, 0), seam, seg=20, arc=math.pi * 2)
    h.location = (0, 0, 2.55 + k * 0.62)
    h.rotation_euler = (0, math.radians(90), 0)

# the brand, painted on the band, facing the street (west) and readable
# at the home view (mirrored render): same trick as the liner decks
bpy.ops.object.text_add(location=(0.0, -0.475, 3.30))
t = bpy.context.active_object
t.data.body = "GREENHAUS"
t.data.font = bpy.data.fonts.load(rig.FONT)
t.data.size = 0.17
t.data.extrude = 0.008
t.data.align_x = "CENTER"
t.data.align_y = "CENTER"
t.rotation_euler = (math.radians(90), 0, math.radians(180))
t.scale = (-1, 1, 1)
t.data.materials.append(paint)
bpy.ops.object.convert(target="MESH")

# 3 — service catwalk ringing the waist + rail, the future low-line perch
rig.box("catwalk", (0.98, 0.98, 0.05), (0, 0, 2.42), seam)
for sx, sy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
    rig.box(f"rail{sx}{sy}", (0.98 if sy else 0.03, 0.98 if sx else 0.03, 0.03),
            (sx * 0.475, sy * 0.475, 2.62), rust)
# ladder up the north face to the catwalk
rig.box("ladderL", (0.03, 0.03, 2.4), (0.10, 0.47, 1.2), rust)
rig.box("ladderR", (0.03, 0.03, 2.4), (-0.10, 0.47, 1.2), rust)
for k in range(6):
    rig.box(f"rung{k}", (0.20, 0.03, 0.03), (0, 0.47, 0.35 + k * 0.38), rust)

# 4 — the plumbing: standpipe down to the mains, overflow weeping wet
rig.box("standpipe", (0.09, 0.09, 2.3), (0, 0, 1.16), seam)
rig.box("overflow", (0.05, 0.05, 2.2), (0.36, -0.36, 1.25), rust)
rig.box("puddle", (0.38, 0.34, 0.02), (0.28, -0.30, 0.01), wet)

# 5 — the night read: beacon, work lamps, bulb string, level gauge.
# The tank is dark steel; without its own light it bakes to a black
# silhouette (live-verified) — so FLOODLIGHT the tank itself: cornice
# strips under the lid wash light DOWN the drum, catwalk uplights wash
# it UP. The Cycles bake turns those into gradients on the steel.
rig.box("beacon", (0.12, 0.12, 0.12), (0, 0, 4.21), beacon)
rig.box("worklamp", (0.20, 0.20, 0.06), (0, 0.30, 2.28), lamp)   # under-belly
rig.box("worklamp2", (0.20, 0.20, 0.06), (0.28, -0.14, 2.28), lamp)
for sx, sy in ((1, 0), (-1, 0), (0, 1), (0, -1)):                # cornice floods
    rig.box(f"flood{sx}{sy}", (0.62 if sy else 0.05, 0.62 if sx else 0.05, 0.05),
            (sx * 0.44, sy * 0.44, 3.94), lamp)
for k in range(4):                                               # catwalk uplights
    a = math.pi / 4 + 2 * math.pi * k / 4
    rig.box(f"uplight{k}", (0.10, 0.10, 0.04),
            (0.40 * math.cos(a), 0.40 * math.sin(a), 2.46), lamp)
# a string of warm bulbs around the catwalk rail — the classic ring
for k in range(10):
    a = 2 * math.pi * k / 10
    rig.box(f"bulb{k}", (0.055, 0.055, 0.055),
            (0.46 * math.cos(a), 0.46 * math.sin(a), 2.66), lamp)
rig.box("gaugestrip", (0.06, 0.025, 1.3), (0.20, -0.465, 3.10), gauge)

# ground shadow catcher
catcher = rig.make_material("wtgnd", (0.5, 0.5, 0.5), 1.0)
g = rig.box("gplane", (5, 5, 0.01), (0, 0, -0.005), catcher)
g.is_shadow_catcher = True

rig.rig_camera_and_light(ortho=8.125, target=(0, 0, 2.0))
rig.render("watertower", res=1600)

# self-calibration: the local origin under THIS camera
rig.clear_scene()
m = rig.make_material("mk", (1, 1, 1), 0.2, emit=(1, 1, 1))
rig.box("marker", (0.04, 0.04, 0.04), (0, 0, 0), m)
rig.rig_camera_and_light(ortho=8.125, target=(0, 0, 2.0))
rig.render("calib_watertower", res=1600)
print("landmark watertower rendered")
