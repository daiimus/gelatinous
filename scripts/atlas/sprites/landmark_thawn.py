"""Thawn-Harrison Cryogenics (§3.5 landmark #5): the sleeve cathedral.

    blender --background --python scripts/atlas/sprites/landmark_thawn.py

Corporate brutalism wearing cathedral bones: a two-cell poured-concrete
monolith (Lobby + Decantation Chamber) with buttress ribs in organ-pipe
rhythm, a cold clerestory band glowing between them, and one tall
recessed portal holding the only warm light. The condenser deck rides
the roofline like an organ loft — fan cowls, frost-lagged pipe runs —
and an intake campanile crowns the east end with a cold beacon slit.
The forecourt (the Courtyard cell) is a bare paved apron with a single
lamp: the warm threshold before the cold interior. Immortality as
infrastructure. Local origin = the Lobby's base center; anchor (2,10,0).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import rig  # noqa: E402

rig.clear_scene()

conc = rig.make_material("tconc", (0.30, 0.32, 0.35), 0.85, noise=0.25)
plinth = rig.make_material("tplinth", (0.20, 0.215, 0.24), 0.9, noise=0.3)
rib = rig.make_material("trib", (0.36, 0.38, 0.41), 0.8, noise=0.2)
frost = rig.make_material("tfrost", (0.45, 0.80, 0.95), 0.3,
                          emit=(0.35, 0.80, 1.0), emit_strength=1.6)
coldslit = rig.make_material("tslit", (0.35, 0.70, 0.90), 0.3,
                             emit=(0.30, 0.72, 0.95), emit_strength=1.0)
amber = rig.make_material("tamber", (1.0, 0.72, 0.38), 0.4,
                          emit=(1.0, 0.65, 0.3), emit_strength=2.0)
dark = rig.make_material("tdark", (0.05, 0.06, 0.08), 0.6)
steel = rig.make_material("tsteel", (0.30, 0.29, 0.26), 0.55, noise=0.2)
pipe = rig.make_material("tpipe", (0.62, 0.70, 0.74), 0.5, noise=0.15)
pave = rig.make_material("tpave", (0.16, 0.165, 0.19), 0.6, noise=0.35)

H = 1.30           # the nave height — taller than its storeys, on purpose

# --- plinth and monolith: Lobby (0,0) + Chamber (1,0) ----------------
rig.box("plinth", (2.10, 1.06, 0.12), (0.5, 0, 0.06), plinth)
rig.box("mass", (2.0, 0.96, H), (0.5, 0, 0.12 + H / 2), conc)

# --- buttress ribs, organ-pipe rhythm (north + east faces) -----------
for i in range(7):                       # north face: x from -0.85 .. 1.85
    rx = -0.85 + i * 0.45
    rig.box(f"ribN{i}", (0.10, 0.07, H * 0.94), (rx, 0.50, 0.12 + H * 0.47), rib)
for i in range(3):                       # east face
    ry = -0.30 + i * 0.30
    rig.box(f"ribE{i}", (0.07, 0.10, H * 0.94), (1.52, ry, 0.12 + H * 0.47), rib)

# far faces wear the same rhythm — a cathedral has no back
for i in range(7):
    rx = -0.85 + i * 0.45
    rig.box(f"ribS{i}", (0.10, 0.07, H * 0.94), (rx, -0.50, 0.12 + H * 0.47), rib)
for i in range(3):
    ry = -0.30 + i * 0.30
    rig.box(f"ribW{i}", (0.07, 0.10, H * 0.94), (-0.52, ry, 0.12 + H * 0.47), rib)

# --- the clerestory: cold band riding high between the ribs ----------
rig.box("clereN", (1.95, 0.03, 0.12), (0.5, 0.505, 0.12 + H - 0.22), frost)
rig.box("clereE", (0.03, 0.90, 0.12), (1.525, 0, 0.12 + H - 0.22), frost)
rig.box("clereS", (1.95, 0.03, 0.12), (0.5, -0.505, 0.12 + H - 0.22), frost)
rig.box("clereW", (0.03, 0.90, 0.12), (-0.525, 0, 0.12 + H - 0.22), frost)
for i in range(6):
    sx2 = -0.62 + i * 0.45
    rig.box(f"slitS{i}", (0.05, 0.03, 0.42), (sx2, -0.505, 0.55), coldslit)
# narrow slit windows low on the north face, one per bay
for i in range(6):
    sx = -0.62 + i * 0.45
    rig.box(f"slit{i}", (0.05, 0.03, 0.42), (sx, 0.505, 0.55), coldslit)

# --- the portal: one tall recess, the only warm light ----------------
rig.box("portal_recess", (0.34, 0.06, 0.92), (-0.40, 0.50, 0.12 + 0.46), dark)
rig.box("portal_lamp", (0.20, 0.03, 0.05), (-0.40, 0.52, 1.02), amber)

# --- the organ loft: condenser deck as roofline plant ----------------
rig.box("loft", (1.9, 0.80, 0.10), (0.5, 0, 0.12 + H + 0.05), steel)
for i in range(3):                       # fan cowls
    rig.cylinder(f"cowl{i}", 0.14, 0.10, (0, 0, 0), dark, seg=16,
                 arc=math.pi * 2)
for i, o in enumerate([o for o in bpy.context.collection.objects
                       if o.name.startswith("cowl")]):
    o.location = (-0.10 + i * 0.55, 0.10, 0.12 + H + 0.16)
for i in range(2):                       # frost-lagged pipe runs
    rig.box(f"fpipe{i}", (1.7, 0.05, 0.05),
            (0.45, -0.28 + i * 0.14, 0.12 + H + 0.14), pipe)

# --- the campanile: intake tower, cold beacon slit -------------------
rig.box("campanile", (0.26, 0.26, 0.85), (1.30, -0.26, 0.12 + H + 0.42), conc)
rig.box("camp_slit", (0.05, 0.05, 0.55), (1.30, -0.115, 0.12 + H + 0.44), frost)
rig.box("camp_cap", (0.32, 0.32, 0.06), (1.30, -0.26, 0.12 + H + 0.87), steel)

# --- the forecourt: bare paved apron, one warm lamp ------------------
rig.box("court", (1.0, 1.0, 0.06), (-1.0, -1.0, 0.03), pave)
rig.box("lamp_post", (0.04, 0.04, 0.55), (-0.72, -0.72, 0.33), steel)
rig.box("lamp_head", (0.10, 0.10, 0.06), (-0.72, -0.72, 0.62), amber)
rig.box("stencil", (0.40, 0.26, 0.004), (-1.10, -1.10, 0.065), plinth)

catcher = rig.make_material("tgnd", (0.5, 0.5, 0.5), 1.0)
g = rig.box("gplane", (6, 6, 0.01), (0.3, -0.4, -0.005), catcher)
g.is_shadow_catcher = True

RES = 1200
rig.rig_camera_and_light(ortho=2.6 * RES / 512, target=(0.3, -0.4, 0.6))
rig.render("thawn", res=RES)

rig.clear_scene()
m = rig.make_material("mk", (1, 1, 1), 0.2, emit=(1, 1, 1))
rig.box("marker", (0.04, 0.04, 0.04), (0, 0, 0), m)
rig.rig_camera_and_light(ortho=2.6 * RES / 512, target=(0.3, -0.4, 0.6))
rig.render("calib_thawn", res=RES)
print("landmark thawn rendered")
