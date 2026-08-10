"""The first landmark hero: Hammett's Boot, entire (§3.5).

    blender --background --python scripts/atlas/sprites/landmark_boot.py

ONE model for the whole fallen derelict — the remnants of a ship's
landing gear / a giant mech leg, boot-shaped where it came to rest. It
is a single solid dark hull (no per-cell tiles), spanning the entire
footprint: a raised heel counter at the west, the long armoured sole,
the blunt toe box at the east. The market lives INSIDE it — the glow
shows only at the mouth (the toe's east arch), the throat door, and the
clerestory windows along the north crown. Everything else is matte
riveted plate.

The footprint it must cover (world cells, anchor = Heel at -8,-18,0):
    y-17:      -8 -7 -6 -5          -3          (north flank + spur)
    y-18: -9   -8 -7 -6 -5 -4 -3                (the sole / market spine)
    y-19:      -8 -7 -6 -5 -4 -3                (south flank + lug)
Local origin = the Heel cell's base center; +X runs east toward the
toe, +Y north, one unit per cell. Rendered at 1600px (same px/unit as
the base rig), ground to 400px by the darkroom.

Visible faces are NORTH and EAST (the projection): all glow and detail
live there; south/west carry only structural mass.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import rig  # noqa: E402

rig.clear_scene()

# --- palette: dark heavy machinery, warm light only where the market is ---
plate = rig.make_material("plate", (0.11, 0.12, 0.13), 0.85, noise=0.35)
plateN = rig.make_material("plateN", (0.15, 0.16, 0.17), 0.80, noise=0.30)
seam = rig.make_material("seam", (0.055, 0.06, 0.07), 0.90)
tread = rig.make_material("tread", (0.09, 0.10, 0.11), 0.95, noise=0.30)
glow = rig.make_material("glow", (1.0, 0.58, 0.24), 0.5,
                         emit=(1.0, 0.55, 0.22), emit_strength=2.6)
lit = rig.make_material("lit", (0.9, 0.6, 0.3), 0.4,
                        emit=(1.0, 0.62, 0.28), emit_strength=2.0)
canvas_a = rig.make_material("canv_a", (0.30, 0.14, 0.12), 0.9, noise=0.3)
canvas_b = rig.make_material("canv_b", (0.34, 0.30, 0.16), 0.9, noise=0.3)
stenc = rig.make_material("stenc", (0.5, 0.46, 0.40), 0.9)

# 1 — the solid foot: one honest slab covering the whole 3-deep footprint
rig.box("base", (7.2, 3.0, 0.62), (2.0, 0, 0.31), plate)      # X[-1.6..5.6], Y±1.5
rig.box("basebev", (6.9, 2.7, 0.12), (2.05, 0, 0.66), plateN)  # inset top rim
# north-face weld stringers + rivet columns (the visible flank reads as plate)
rig.box("seamN1", (7.0, 0.04, 0.05), (2.0, 1.505, 0.22), seam)
rig.box("seamN2", (7.0, 0.04, 0.05), (2.0, 1.505, 0.48), seam)
for i in range(-1, 6):
    rig.box(f"rivN{i}", (0.05, 0.04, 0.52), (i + 0.0, 1.508, 0.33), seam)

# 2 — the heel counter: a taller mass at the west, the boot's thick end
rig.box("heel", (1.5, 2.9, 0.52), (-0.55, 0, 0.86), plate)     # X[-1.3..0.2]
rig.box("heeltop", (1.3, 2.7, 0.12), (-0.55, 0, 1.14), plateN)
rig.box("heelshoulder", (0.08, 2.9, 0.66), (0.22, 0, 0.55), seam)  # vertical weld

# 3 — the spine vault: a hooped hull camber over the market street,
#     giving the derelict its curved back (one continuous barrel)
rig.cylinder("vault", 0.90, 5.2, (2.7, 0, 0.62), plate, arc=math.pi * 0.92)
for i in range(8):                                            # rib hoops
    rig.cylinder(f"hoop{i}", 0.92, 0.06, (0.55 + i * 0.66, 0, 0.62), seam,
                 arc=math.pi * 0.9)

# 4 — the clerestory: a lit ridge along the NORTH crown — the giveaway
#     that this hull is a hall people are inside of, not a dead pipe
rig.box("clere", (4.7, 0.30, 0.34), (2.7, 0.55, 1.24), plate)
for i in range(9):
    rig.box(f"cwin{i}", (0.34, 0.05, 0.16), (0.75 + i * 0.5, 0.71, 1.24), lit)
rig.box("clereridge", (4.8, 0.40, 0.06), (2.7, 0.52, 1.43), seam)
# two turbine cowls standing off the ridge — salvage machinery
for j, vx in enumerate((1.7, 3.9)):
    v = rig.cylinder(f"vent{j}", 0.10, 0.16, (0, 0, 0), seam, seg=12,
                     arc=math.pi * 2)
    v.location = (vx, 0.1, 1.52)

# 5 — the toe box: a blunt raised end covering Spur / Toe / Lug (x-3),
#     and the MARKET MOUTH — a warm arch on the visible EAST face
rig.box("toe", (1.1, 3.0, 1.16), (5.0, 0, 0.58), plate)        # X[4.45..5.55]
rig.box("toetop", (1.0, 2.7, 0.12), (5.0, 0, 1.20), plateN)
rig.box("mouth", (0.05, 1.7, 0.86), (5.565, 0, 0.50), glow)    # east glowing bay
rig.box("mouthlintel", (0.12, 2.0, 0.12), (5.565, 0, 0.98), seam)
rig.box("mouthjambL", (0.12, 0.12, 0.92), (5.565, 0.94, 0.50), seam)
rig.box("mouthjambR", (0.12, 0.12, 0.92), (5.565, -0.94, 0.50), seam)
# the spur horn: an angled lug off the toe's north-top corner (x-3,y-17)
rig.box("spur", (0.72, 0.18, 0.18), (5.0, 1.18, 1.22), plate,
        rot=(0, math.radians(-20), math.radians(30)))
# lug treads sunk into the south toe (structural mass, south = unseen)
for i in range(3):
    rig.box(f"lug{i}", (0.24, 0.30, 0.40), (4.7 + i * 0.32, -1.2, 0.20), tread)

# 6 — the throat: a lit entrance flush in the NORTH face at the heel end
rig.box("throat", (0.5, 0.06, 0.5), (0.0, 1.505, 0.30), seam)
rig.box("throatglow", (0.34, 0.05, 0.34), (0.0, 1.515, 0.26), glow)

# 7 — stall awnings: the market spilling onto the north curb (visible face)
for i, ax in enumerate((1.4, 2.4, 3.4, 4.4)):
    mat = canvas_a if i % 2 == 0 else canvas_b
    rig.box(f"awn{i}", (0.72, 0.5, 0.05), (ax, 1.74, 0.52), mat,
            rot=(math.radians(18), 0, 0))
    rig.box(f"awnglow{i}", (0.5, 0.06, 0.05), (ax, 1.60, 0.30), lit)
    rig.box(f"awnpostL{i}", (0.04, 0.04, 0.5), (ax - 0.30, 1.96, 0.25), seam)
    rig.box(f"awnpostR{i}", (0.04, 0.04, 0.5), (ax + 0.30, 1.96, 0.25), seam)

# 8 — a stencil plate on the north base flank (brand/hull number)
rig.box("stencil", (0.9, 0.03, 0.16), (2.0, 1.515, 0.50), stenc)

# ground shadow catcher
catcher = rig.make_material("ground", (0.5, 0.5, 0.5), 1.0)
g = rig.box("gplane", (11, 7, 0.01), (2.5, 0, -0.005), catcher)
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
