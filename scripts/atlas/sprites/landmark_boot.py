"""The first landmark hero: Hammett's Boot, entire (§3.5).

    blender --background --python scripts/atlas/sprites/landmark_boot.py

ONE model for the whole fallen derelict — the remnants of a ship's
landing gear / a giant mech leg, boot-shaped where it came to rest: one
solid dark hull (no per-cell tiles, no hollow shells) across the entire
footprint — heel counter at the west, the long armoured sole, the blunt
toe box at the east.

Built for the LIVE atlas, which shows BAKED vertex colours and toggles
day/night with no lights of its own. So the hull reads the tenement's
way: a dark concrete mass STUDDED WITH WARM WINDOWS that glow from
within at night (the market inside it), a bright market mouth at the
toe, and lit stalls on the north curb. Everything solid — every crown
is a filled volume, never an open half-shell (front-face-only material
would see straight through it).

Footprint it covers (world cells, anchor = Heel at -8,-18,0):
    y-17:      -8 -7 -6 -5          -3          (north flank + spur)
    y-18: -9   -8 -7 -6 -5 -4 -3                (the sole / market spine)
    y-19:      -8 -7 -6 -5 -4 -3                (south flank + lug)
Local origin = the Heel cell's base center; +X east toward the toe, +Y
north, one unit per cell. Visible faces are NORTH and EAST; the far
faces carry sparser windows for when the atlas rotates.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import rig  # noqa: E402

rig.clear_scene()

# --- palette: the tenement's night-proven dark concrete + bright glass ---
hull = rig.make_material("hull", (0.13, 0.165, 0.20), 0.85, noise=0.40)
hullN = rig.make_material("hullN", (0.16, 0.20, 0.24), 0.80, noise=0.30)
grime = rig.make_material("grime", (0.09, 0.11, 0.13), 0.95, noise=0.30)
frame = rig.make_material("frame", (0.07, 0.08, 0.09), 0.80)
seam = rig.make_material("seam", (0.06, 0.07, 0.08), 0.90)
lit = rig.make_material("lit", (0.9, 0.6, 0.3), 0.4, emit=(1.0, 0.62, 0.28))
dark = rig.make_material("darkw", (0.03, 0.035, 0.05), 0.3)
glow = rig.make_material("glow", (1.0, 0.6, 0.28), 0.4, emit=(1.0, 0.58, 0.24))
tread = rig.make_material("tread", (0.09, 0.10, 0.12), 0.95, noise=0.30)
canvas_a = rig.make_material("canv_a", (0.42, 0.16, 0.13), 0.9, noise=0.3)
canvas_b = rig.make_material("canv_b", (0.52, 0.44, 0.20), 0.9, noise=0.3)
stenc = rig.make_material("stenc", (0.5, 0.46, 0.40), 0.9)


def window(tag, loc, face, w=0.30, h=0.30, on=True):
    """A framed pane on the named face (N=+Y, S=-Y, E=+X, W=-X)."""
    pane = lit if on else dark
    x, y, z = loc
    if face in ("N", "S"):
        oy = 0.008 if face == "N" else -0.008
        rig.box(f"wf{tag}", (w, 0.02, h), (x, y, z), frame)
        rig.box(f"wg{tag}", (w * 0.8, 0.015, h * 0.8), (x, y + oy, z), pane)
    else:
        ox = 0.008 if face == "E" else -0.008
        rig.box(f"wf{tag}", (0.02, w, h), (x, y, z), frame)
        rig.box(f"wg{tag}", (0.015, w * 0.8, h * 0.8), (x + ox, y, z), pane)


# 1 — the solid foot: one honest slab across the whole 3-deep footprint
rig.box("base", (7.2, 3.0, 0.64), (2.0, 0, 0.32), hull)        # X[-1.6..5.6], Y±1.5
rig.box("grimeband", (7.21, 3.01, 0.14), (2.0, 0, 0.07), grime)
rig.box("basecap", (6.9, 2.7, 0.10), (2.05, 0, 0.66), hullN)   # inset top rim

# 2 — the heel counter: a taller mass at the west, the boot's thick end
rig.box("heel", (1.5, 3.0, 0.70), (-0.55, 0, 0.95), hull)      # X[-1.3..0.2]
rig.box("heelcap", (1.3, 2.7, 0.10), (-0.55, 0, 1.30), hullN)
rig.box("heelshoulder", (0.10, 3.0, 0.9), (0.22, 0, 0.66), seam)  # vertical weld

# 3 — the crown: a SOLID filled hull-back over the market spine (a box
#     core, so nothing is a see-through shell), stepped like a hull
rig.box("crownA", (5.4, 2.0, 0.42), (2.7, 0, 0.85), hull)     # wide lower
rig.box("crownB", (5.0, 1.5, 0.40), (2.7, 0, 1.18), hullN)    # mid
rig.box("crownC", (4.6, 0.9, 0.34), (2.7, 0, 1.48), hull)     # ridge
rig.box("crownridge", (4.7, 1.0, 0.05), (2.7, 0, 1.66), seam)
for i in range(7):                                            # rib seams
    rig.box(f"rib{i}", (0.05, 2.02, 0.44), (0.5 + i * 0.72, 0, 0.85), seam)
# two turbine cowls on the ridge — salvage machinery
for j, vx in enumerate((1.6, 3.9)):
    v = rig.cylinder(f"vent{j}", 0.10, 0.16, (0, 0, 0), seam, seg=12,
                     arc=math.pi * 2)
    v.location = (vx, 0.15, 1.72)

# 4 — the toe box: a blunt raised end covering Spur / Toe / Lug (x-3)
rig.box("toe", (1.15, 3.0, 1.30), (5.0, 0, 0.65), hull)       # X[4.42..5.57]
rig.box("toecap", (1.0, 2.7, 0.10), (5.0, 0, 1.30), hullN)
# the spur horn off the toe's north-top corner (x-3, y-17)
rig.box("spur", (0.8, 0.20, 0.20), (5.0, 1.25, 1.35), hull,
        rot=(0, math.radians(-20), math.radians(30)))
# lug treads sunk into the south toe (south = unseen; structural mass)
for i in range(3):
    rig.box(f"lug{i}", (0.24, 0.30, 0.44), (4.7 + i * 0.32, -1.25, 0.22), tread)

# ── the night read: warm windows glowing from within the hull ──────────
# north base flank — the long market wall (mostly lit)
for i, x in enumerate((-1.05, -0.15, 0.72, 1.6, 2.48, 3.36, 4.24, 5.05)):
    window(f"nb{i}", (x, 1.505, 0.40), "N", on=(i not in (2, 6)))
# north clerestory — the hall's upper light, on the crown's north face
for i, x in enumerate((0.6, 1.35, 2.1, 2.85, 3.6, 4.35)):
    window(f"nc{i}", (x, 0.985, 1.20), "N", w=0.34, h=0.20, on=(i != 3))
# east toe face — the MARKET MOUTH: a tall bright arch + flankers
rig.box("mouthframe", (0.10, 1.5, 1.0), (5.55, 0, 0.55), seam)
rig.box("mouth", (0.05, 1.2, 0.82), (5.575, 0, 0.52), glow)
window("et0", (5.57, 0, 1.15), "E", w=0.5, h=0.16, on=True)   # transom
window("et1", (5.57, 0.95, 0.6), "E", w=0.28, h=0.34, on=True)
window("et2", (5.57, -0.95, 0.6), "E", w=0.28, h=0.34, on=False)
# the throat: a lit entrance flush in the north face at the heel end
rig.box("throatframe", (0.5, 0.05, 0.56), (0.0, 1.505, 0.30), seam)
rig.box("throat", (0.34, 0.04, 0.40), (0.0, 1.515, 0.26), glow)
# far faces — sparse windows for the rotated atlas views
for i, x in enumerate((-0.6, 0.6, 1.8, 3.0, 4.2)):            # south flank
    window(f"sb{i}", (x, -1.505, 0.40), "S", on=(i % 2 == 0))
for i, y in enumerate((-0.7, 0.0, 0.7)):                      # west heel face
    window(f"wb{i}", (-1.305, y, 0.55), "W", on=(i == 1))

# ── the market spilling out: lit stalls on the north curb (visible) ────
for i, ax in enumerate((1.4, 2.4, 3.4, 4.4)):
    mat = canvas_a if i % 2 == 0 else canvas_b
    rig.box(f"awn{i}", (0.72, 0.5, 0.05), (ax, 1.74, 0.54), mat,
            rot=(math.radians(18), 0, 0))
    rig.box(f"awnglow{i}", (0.52, 0.06, 0.06), (ax, 1.58, 0.26), lit)
    rig.box(f"awnpostL{i}", (0.04, 0.04, 0.5), (ax - 0.30, 1.96, 0.25), seam)
    rig.box(f"awnpostR{i}", (0.04, 0.04, 0.5), (ax + 0.30, 1.96, 0.25), seam)

# a stencil plate on the north base flank (brand / hull number)
rig.box("stencil", (0.9, 0.03, 0.16), (2.0, 1.515, 0.56), stenc)

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
