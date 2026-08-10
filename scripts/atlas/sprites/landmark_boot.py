"""The first landmark hero: Hammett's Boot, entire (§3.5).

    blender --background --python scripts/atlas/sprites/landmark_boot.py

ONE model for the whole fallen derelict — the remnants of a ship's
landing gear / a giant mech leg, boot-shaped where it came to rest: one
solid dark hull (no per-cell tiles, no hollow shells) across the whole
footprint, sculpted into an actual BOOT PROFILE:
  - the HEEL rises thick at the west, and a sheared-off mech-leg ANKLE
    stub leans back off it (the leg the thing came down on);
  - the INSTEP dips low through the middle — the boot's arch;
  - the TOE box lifts and curls up at the east, over the market mouth;
  - SPURS: landing-gear struts splay off the heel to foot-pads on the
    ground, a spiked ROWEL at the heel point, claw struts at the toe.

Built for the LIVE atlas, which shows BAKED vertex colours and toggles
day/night with no lights of its own, on a FREE-ROTATING camera. So the
hull reads the tenement's way — dark concrete STUDDED WITH WARM WINDOWS
on every face — with a bright market mouth at the toe. Everything solid;
no open half-shell (the front-face-only bake would see through it).

Footprint it covers (world cells, anchor = Heel at -8,-18,0):
    y-17:      -8 -7 -6 -5          -3          (north flank + spur)
    y-18: -9   -8 -7 -6 -5 -4 -3                (the sole / market spine)
    y-19:      -8 -7 -6 -5 -4 -3                (south flank + lug)
Local origin = the Heel cell's base center; +X east toward the toe, +Y
north, one unit per cell.
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
rig.box("base", (7.2, 3.0, 0.64), (2.0, 0, 0.32), hull)        # X[-1.6..5.6]
rig.box("grimeband", (7.21, 3.01, 0.14), (2.0, 0, 0.07), grime)
rig.box("basecap", (6.9, 2.7, 0.08), (2.05, 0, 0.64), hullN)

# ── the BOOT PROFILE (west→east: heel · instep · toe) ──────────────────
# 2 — HEEL & ANKLE (west): thick raised back + a sheared mech-leg stub
rig.box("heel", (1.9, 2.9, 1.32), (-0.35, 0, 1.28), hull)      # z0.62..1.94
rig.box("heelcap", (1.7, 2.6, 0.10), (-0.35, 0, 1.94), hullN)
rig.box("counter", (0.14, 2.9, 1.5), (0.62, 0, 1.20), seam)    # heel↔instep step
# the ankle: a thick leg stub standing near-vertical on the heel (a slight
# lean, kept over the heel cell so it doesn't crowd the Brackett tower west)
rig.box("ankle", (1.05, 1.7, 1.5), (-0.25, 0, 2.5), hull, rot=(0, math.radians(7), 0))
rig.box("ankleband", (1.10, 1.75, 0.10), (-0.22, 0, 2.28), seam,
        rot=(0, math.radians(7), 0))
rig.box("shear1", (0.7, 1.3, 0.30), (-0.42, 0.28, 3.12), hull,
        rot=(math.radians(12), math.radians(18), 0))
rig.box("shear2", (0.55, 1.0, 0.26), (-0.28, -0.42, 3.06), hull,
        rot=(math.radians(-14), math.radians(15), 0))

# 3 — INSTEP / ARCH (middle): the crown DIPS low here — the boot's arch
rig.box("instep", (2.9, 2.0, 0.42), (2.05, 0, 0.83), hull)     # z0.62..1.04
rig.box("insteptop", (2.7, 1.7, 0.06), (2.05, 0, 1.04), hullN)
for i in range(4):                                             # rib seams
    rig.box(f"irib{i}", (0.05, 2.02, 0.44), (1.05 + i * 0.6, 0, 0.83), seam)

# 4 — TOE (east): a rounded toe box that curls UP at the tip
rig.box("toe", (1.6, 2.7, 1.02), (4.85, 0, 0.85), hull)        # X[4.05..5.65], z0.62..1.36
rig.box("toecap", (1.4, 2.4, 0.08), (4.85, 0, 1.36), hullN)
rig.box("toeup", (0.55, 2.5, 0.72), (5.5, 0, 1.42), hull, rot=(0, math.radians(-34), 0))
rig.box("toeupcap", (0.12, 2.3, 0.72), (5.74, 0, 1.60), hullN, rot=(0, math.radians(-34), 0))
for j, vx in enumerate((4.35, 4.9)):                           # cowls on the toe crown
    v = rig.cylinder(f"vent{j}", 0.09, 0.14, (0, 0, 0), seam, seg=12, arc=math.pi * 2)
    v.location = (vx, 0.2, 1.44)

# ── SPURS: mech landing-gear struts gripping the ground ────────────────
def spur(tag, xyz, ang_z, ang_p, length=1.0):
    x, y, z = xyz
    rig.box(f"spur_{tag}", (length, 0.15, 0.15), (x, y, z), seam,
            rot=(0, ang_p, ang_z))
    dx, dy = 0.55 * math.cos(ang_z), 0.55 * math.sin(ang_z)
    rig.box(f"spurfoot_{tag}", (0.26, 0.26, 0.10), (x + dx, y + dy, 0.05), tread)
    rig.box(f"spurhyd_{tag}", (0.20, 0.09, 0.09), (x, y, z + 0.02), glow)  # lit joint

spur("rn", (-1.05, 0.85, 0.55), math.radians(38), math.radians(40), 0.8)   # heel rear, N
spur("rs", (-1.05, -0.85, 0.55), math.radians(-38), math.radians(40), 0.8)  # heel rear, S
spur("tn", (5.35, 1.05, 0.50), math.radians(150), math.radians(44), 0.8)  # toe claw, N
spur("ts", (5.35, -1.05, 0.50), math.radians(-150), math.radians(44), 0.8)  # toe claw, S
# the ROWEL: a spiked spur wheel at the heel's rear point (the classic spur)
rw = rig.cylinder("rowel", 0.22, 0.09, (0, 0, 0), seam, seg=16, arc=math.pi * 2)
rw.location = (-1.4, 0, 0.70); rw.rotation_euler = (0, math.radians(90), 0)
for k in range(8):
    a = 2 * math.pi * k / 8
    rig.box(f"rowsp{k}", (0.06, 0.06, 0.18),
            (-1.4, 0.30 * math.cos(a), 0.70 + 0.30 * math.sin(a)), seam, rot=(a, 0, 0))

# ── the night read: warm windows glowing from within, every face ───────
# base flank windows, both long sides (the market wall)
for i, x in enumerate((-1.05, -0.15, 0.72, 1.6, 2.48, 3.36, 4.24, 5.05)):
    window(f"nb{i}", (x, 1.505, 0.40), "N", on=(i not in (2, 6)))
    window(f"sb{i}", (x, -1.505, 0.40), "S", on=(i not in (3, 5)))
# heel upper ports (the ankle/counter reads lit at night)
for i, x in enumerate((-0.9, -0.35, 0.2)):
    window(f"hn{i}", (x, 1.455, 1.30), "N", w=0.26, h=0.30, on=(i != 1))
    window(f"hs{i}", (x, -1.455, 1.30), "S", w=0.26, h=0.30, on=(i != 0))
window("an", (-0.5, 0.86, 2.35), "N", w=0.24, h=0.26, on=True)   # ankle port
window("as", (-0.5, -0.86, 2.35), "S", w=0.24, h=0.26, on=False)
# toe clerestory (on the toe box, above the instep dip)
for i, x in enumerate((4.3, 4.75, 5.2)):
    window(f"tcn{i}", (x, 1.36, 1.12), "N", w=0.28, h=0.20, on=(i != 1))
    window(f"tcs{i}", (x, -1.36, 1.12), "S", w=0.28, h=0.20, on=(i != 2))
# east toe face — the MARKET MOUTH: a tall bright arch + flankers
rig.box("mouthframe", (0.10, 1.5, 1.0), (5.62, 0, 0.55), seam)
rig.box("mouth", (0.05, 1.2, 0.82), (5.645, 0, 0.52), glow)
window("et1", (5.64, 0.95, 0.6), "E", w=0.28, h=0.34, on=True)
window("et2", (5.64, -0.95, 0.6), "E", w=0.28, h=0.34, on=False)
# throat doors, north and south, at the heel end
rig.box("throatframe", (0.5, 0.05, 0.56), (0.0, 1.505, 0.30), seam)
rig.box("throat", (0.34, 0.04, 0.40), (0.0, 1.515, 0.26), glow)
rig.box("throatframeS", (0.5, 0.05, 0.56), (0.5, -1.505, 0.30), seam)
rig.box("throatS", (0.34, 0.04, 0.40), (0.5, -1.515, 0.26), glow)
# west heel face — a couple of lit ports for the rotated view
for i, y in enumerate((-0.7, 0.0, 0.7)):
    window(f"wb{i}", (-1.305, y, 0.55), "W", on=(i != 2))

# ── the market spilling out: lit stalls on the north curb ──────────────
for i, ax in enumerate((1.4, 2.4, 3.4)):
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
g = rig.box("gplane", (12, 8, 0.01), (2.2, 0, -0.005), catcher)
g.is_shadow_catcher = True

rig.rig_camera_and_light(ortho=8.125, target=(2.5, 0, 0.7))
rig.render("boot", res=1600)

# self-calibration: the local origin under THIS camera
rig.clear_scene()
m = rig.make_material("mk", (1, 1, 1), 0.2, emit=(1, 1, 1))
rig.box("marker", (0.04, 0.04, 0.04), (0, 0, 0), m)
rig.rig_camera_and_light(ortho=8.125, target=(2.5, 0, 0.7))
rig.render("calib_boot", res=1600)
print("landmark boot rendered")
