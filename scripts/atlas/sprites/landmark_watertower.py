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

steel = rig.make_material("wtsteel", (0.42, 0.45, 0.42), 0.85, noise=0.30)  # matte weathered paint — colour, not light
rust = rig.make_material("wtrust", (0.30, 0.19, 0.12), 0.9, noise=0.45)
# Greenhaus green, softly floodlit — the big band surface is what makes
# the tank exist at night (small bulbs alone leave it a silhouette)
band = rig.make_material("wtband", (0.20, 0.34, 0.22), 0.8, noise=0.25)
seam = rig.make_material("wtseam", (0.06, 0.07, 0.08), 0.9)
paint = rig.make_material("wtpaint", (0.55, 0.62, 0.50), 0.8,
                          emit=(0.62, 0.85, 0.58), emit_strength=1.2)  # lit brand
beacon = rig.make_material("wtbeacon", (0.9, 0.15, 0.1), 0.4,
                           emit=(1.0, 0.12, 0.08), emit_strength=4.0)
lamp = rig.make_material("wtlamp", (1.0, 0.62, 0.28), 0.4,
                         emit=(1.0, 0.62, 0.28), emit_strength=2.5)
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
# the drum is BOXES, not rig.cylinder: the cylinder helper's faces wind
# inward and the live viewer culls back-faces, so a cylinder tube renders
# INVISIBLE (see-through barrel, live-verified). Boxes are what every
# building that reads correctly is made of. Chamfered-octagon drum: an
# axis box + a 45°-rotated box; the rotated one is sized so its corners
# stay inside the one-cell bounds (side * √2/2 ≤ 0.5).
rig.box("tankA", (0.88, 0.88, 1.70), (0, 0, 3.15), steel)
rig.box("tankB", (0.62, 0.62, 1.70), (0, 0, 3.15), steel, rot=(0, 0, math.radians(45)))
# belly plate and lid follow the SAME octagon as the drum (axis + 45°
# pair) so the roof lines up with the body instead of overhanging it
rig.box("tankbtmA", (0.92, 0.92, 0.10), (0, 0, 2.32), seam)
rig.box("tankbtmB", (0.65, 0.65, 0.10), (0, 0, 2.32), seam, rot=(0, 0, math.radians(45)))
rig.box("lidA", (0.94, 0.94, 0.10), (0, 0, 4.02), steel)
rig.box("lidB", (0.66, 0.66, 0.10), (0, 0, 4.02), steel, rot=(0, 0, math.radians(45)))
rig.box("lidcapA", (0.56, 0.56, 0.10), (0, 0, 4.10), rust)
rig.box("lidcapB", (0.40, 0.40, 0.10), (0, 0, 4.10), rust, rot=(0, 0, math.radians(45)))
rig.box("bandA", (0.90, 0.90, 0.42), (0, 0, 3.30), band)         # Greenhaus band
rig.box("bandB", (0.635, 0.635, 0.42), (0, 0, 3.30), band, rot=(0, 0, math.radians(45)))
for k in range(3):                                               # hoop seams
    rig.box(f"hoopA{k}", (0.91, 0.91, 0.05), (0, 0, 2.55 + k * 0.62), seam)
    rig.box(f"hoopB{k}", (0.64, 0.64, 0.05), (0, 0, 2.55 + k * 0.62), seam,
            rot=(0, 0, math.radians(45)))

# the brand, painted on the band, facing the street (west) and readable
# at the home view (mirrored render): same trick as the liner decks
bpy.ops.object.text_add(location=(0.0, -0.462, 3.30))
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

# 5 — the night read, the same way every other building does it: a plain
# matte body, small emissive ACCENTS only (the viewer draws emissive tris
# additively — a glowing body reads transparent, so the body never glows).
rig.box("beacon", (0.12, 0.12, 0.12), (0, 0, 4.21), beacon)
rig.box("worklamp", (0.20, 0.20, 0.06), (0, 0.30, 2.28), lamp)   # under-belly
rig.box("worklamp2", (0.20, 0.20, 0.06), (0.28, -0.14, 2.28), lamp)
# a string of warm bulbs around the catwalk rail — the classic ring
for k in range(10):
    a = 2 * math.pi * k / 10
    rig.box(f"bulb{k}", (0.055, 0.055, 0.055),
            (0.46 * math.cos(a), 0.46 * math.sin(a), 2.66), lamp)

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
