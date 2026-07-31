"""
Street life for the Atlas — the things that make a road look inhabited.

The map had thirteen ambient sprites: three crowds, four vehicles, a cart, a
wreck, two barriers, crates and barrels. Enough to say "a street exists", not
enough to say "people live here, and they got here on a ship that never came
back".

Everything here is built from the same primitives and at the same scale as
``rig.py`` (a cell is 1.0 across; props sit in the 0.2-0.5 range) and is
rendered through the same camera, so it lands on the mirrored-isometric basis
without special handling.

WHAT THIS LEANS ON, thematically:

- **Freight that stopped arriving.** Cargo pods repurposed as street furniture,
  pallets, cable spools. The colony was a waypoint; its infrastructure is other
  people's shipping.
- **Water and power as visible scarcity.** Bowsers, tanks on legs, gensets,
  junction boxes with cable runs. Nothing is buried, because burying it was
  never in the budget.
- **Salvage.** Scrap heaps, a scooter, the vending kiosk that outlived its
  brand.
- **The one green thing.** A planter trough. On a colony with a botched
  terraform, a row of living plants on a street is a statement.

Run headless:
    blender -b -noaudio --python-expr "import sys;sys.path.insert(0,'.');\
import street_life;street_life.render_all()"
"""

import math

import rig
from rig import box, cylinder, make_material, _prop_scene, _crowd_scene


# ── palette helpers ────────────────────────────────────────────────────
# Kept local so a new prop cannot drift the established colour language.

def _steel(n):
    return make_material(f"sl_{n}", (0.20, 0.21, 0.22), 0.75, noise=0.3)


def _rust(n):
    return make_material(f"rs_{n}", (0.30, 0.16, 0.09), 0.9, noise=0.45)


def _plastic(n, rgb=(0.16, 0.19, 0.20)):
    return make_material(f"pl_{n}", rgb, 0.55, noise=0.2)


def _dark(n):
    return make_material(f"dk_{n}", (0.07, 0.07, 0.08), 0.7)


def _amber(n):
    return make_material(f"am_{n}", (0.75, 0.55, 0.15), 0.6)


def _lit(n, rgb=(1.0, 0.78, 0.45)):
    return make_material(f"lt_{n}", rgb, 0.3, emit=rgb, emit_strength=5.0)


def _green(n):
    return make_material(f"gr_{n}", (0.26, 0.46, 0.20), 0.8, noise=0.35)


# ── freight ────────────────────────────────────────────────────────────

def _cargo_pod():
    """A shipping pod, grounded and never collected. Ribbed, rusted, tagged."""
    shell = _rust("pod")
    rib = _steel("podrib")
    box("pod", (0.46, 0.26, 0.24), (0, 0, 0.12), shell)
    for i in range(4):                       # end ribs read at 128px
        box(f"rib{i}", (0.015, 0.27, 0.25), (-0.19 + i * 0.13, 0, 0.125), rib)
    box("door", (0.02, 0.20, 0.18), (0.232, 0, 0.11), _dark("poddoor"))
    box("tag", (0.10, 0.02, 0.05), (-0.05, -0.134, 0.16), _amber("podtag"))


def _pallets():
    """A stack of pallets, slumped. Freight furniture."""
    wood = make_material("pw", (0.32, 0.24, 0.14), 0.9, noise=0.4)
    for i in range(4):
        box(f"pal{i}", (0.30, 0.26, 0.035),
            (0.01 * i, -0.005 * i, 0.02 + i * 0.04), wood,
            rot=(0, 0, math.radians(3 * i)))


def _spool():
    """Cable spool on its side — industrial, and it reads as a circle."""
    drum = make_material("spd", (0.26, 0.20, 0.13), 0.9, noise=0.35)
    coil = _dark("spc")
    cylinder("spool_a", 0.16, 0.04, (0, 0, 0.16), drum, axis="Y", seg=20,
             arc=math.pi * 2)
    cylinder("spool_b", 0.16, 0.04, (0, 0.14, 0.16), drum, axis="Y", seg=20,
             arc=math.pi * 2)
    cylinder("coil", 0.11, 0.13, (0, 0.07, 0.16), coil, axis="Y", seg=18,
             arc=math.pi * 2)


def _scrap():
    """A heap. Deliberately irregular — salvage is the local industry."""
    mats = [_rust("sc1"), _steel("sc2"), _dark("sc3")]
    bits = [((0.32, 0.26, 0.10), (0, 0, 0.05), 12),
            ((0.24, 0.20, 0.09), (0.08, -0.07, 0.14), -34),
            ((0.19, 0.13, 0.11), (-0.10, 0.06, 0.18), 55),
            ((0.14, 0.12, 0.08), (0.03, 0.10, 0.24), -8)]
    for i, (size, loc, rot) in enumerate(bits):
        box(f"scrap{i}", size, loc, mats[i % len(mats)],
            rot=(0, 0, math.radians(rot)))


# ── water and power, worn on the outside ───────────────────────────────

def _water_tank():
    """Tank on legs. Water is the thing you notice first on a bad world."""
    drum = _steel("wt")
    leg = _dark("wtl")
    cylinder("tank", 0.13, 0.30, (0, 0, 0.30), drum, axis="X", seg=20,
             arc=math.pi * 2)
    for lx in (-0.11, 0.11):
        for ly in (-0.09, 0.09):
            box(f"wl{lx}{ly}", (0.022, 0.022, 0.17), (lx, ly, 0.085), leg)
    box("wtap", (0.03, 0.03, 0.05), (0.16, 0, 0.20), _amber("wtp"))


def _genset():
    """Generator: box, vents, exhaust stack, one warm indicator."""
    shell = _plastic("gs", (0.19, 0.20, 0.18))
    box("gbody", (0.30, 0.22, 0.16), (0, 0, 0.08), shell)
    for i in range(4):
        box(f"gv{i}", (0.02, 0.16, 0.09), (-0.10 + i * 0.06, 0.112, 0.09),
            _dark(f"gvd{i}"))
    cylinder("gstack", 0.02, 0.16, (-0.12, -0.07, 0.24), _steel("gst"),
             axis="Z", seg=10, arc=math.pi * 2)
    box("glamp", (0.02, 0.02, 0.02), (0.15, 0.06, 0.14), _lit("gl"))


def _junction():
    """Power junction with a cable run — nothing here is buried."""
    cab = _plastic("jb", (0.22, 0.20, 0.15))
    box("jbody", (0.14, 0.12, 0.28), (0, 0, 0.14), cab)
    box("jdoor", (0.015, 0.10, 0.22), (0.072, 0, 0.15), _dark("jd"))
    box("jhaz", (0.05, 0.02, 0.03), (0, -0.062, 0.24), _amber("jh"))
    conduit = _dark("jc")                    # cables sagging to the kerb
    for i, (dx, dy) in enumerate(((0.10, 0.10), (0.16, 0.02), (0.12, -0.09))):
        box(f"jcab{i}", (0.16, 0.012, 0.012), (dx, dy, 0.03), conduit,
            rot=(0, 0, math.radians(20 * i - 20)))


def _lamp():
    """Street lamp. The only light source that shows in daylight renders."""
    # Everything here is deliberately chunky: a scale-accurate lamp post is
    # one pixel wide at 128px and reads as a scratch on the plate.
    post = _steel("lp")
    cylinder("lpost", 0.026, 0.46, (0, 0, 0.23), post, axis="Z", seg=12,
             arc=math.pi * 2)
    box("lbase", (0.08, 0.08, 0.04), (0, 0, 0.02), _dark("lb"))
    box("larm", (0.16, 0.035, 0.035), (0.08, 0, 0.45), post)
    box("lhead", (0.12, 0.08, 0.05), (0.15, 0, 0.42), _dark("lh"))
    box("lglow", (0.10, 0.065, 0.025), (0.15, 0, 0.393), _lit("lg"))


# ── commerce and the one green thing ───────────────────────────────────

def _kiosk():
    """Vending machine that outlived its brand. Mandatory goods come from these."""
    shell = _plastic("kk", (0.17, 0.21, 0.22))
    box("kbody", (0.20, 0.16, 0.34), (0, 0, 0.17), shell)
    box("kface", (0.015, 0.13, 0.22), (0.10, 0, 0.21), _lit("kf", (0.45, 0.70, 0.75)))
    box("ktray", (0.04, 0.11, 0.03), (0.10, 0, 0.07), _dark("kt"))
    box("khood", (0.23, 0.18, 0.02), (0, 0, 0.35), _steel("kh"))


def _stall(rotz=0.0):
    """Market stall with an awning. Built along X; rotate for the N-S run."""
    def build():
        rz = math.radians(rotz)
        c, s = math.cos(rz), math.sin(rz)
        R = lambda x, y: (x * c - y * s, x * s + y * c)
        cloth = make_material(f"stc{rotz}", (0.44, 0.18, 0.14), 0.9, noise=0.3)
        frame = _steel(f"stf{rotz}")
        goods = _amber(f"stg{rotz}")

        def rb(n, size, loc, mat):
            x, y = R(loc[0], loc[1])
            box(n, size, (x, y, loc[2]), mat, rot=(0, 0, rz))

        rb("stall_top", (0.34, 0.24, 0.015), (0, 0, 0.34), cloth)
        for px in (-0.15, 0.15):
            for py in (-0.10, 0.10):
                x, y = R(px, py)
                box(f"sp{px}{py}{rotz}", (0.015, 0.015, 0.34),
                    (x, y, 0.17), frame)
        rb("stall_tbl", (0.30, 0.16, 0.03), (0, 0, 0.20), frame)
        rb("stall_gd1", (0.08, 0.06, 0.05), (-0.07, 0.01, 0.24), goods)
        rb("stall_gd2", (0.06, 0.05, 0.04), (0.06, -0.02, 0.235), cloth)
    return build


def _planter():
    """A trough of living plants. On this world that is nearly a monument."""
    trough = make_material("ptr", (0.26, 0.25, 0.23), 0.9, noise=0.3)
    box("ptrough", (0.34, 0.12, 0.10), (0, 0, 0.05), trough)
    box("psoil", (0.31, 0.09, 0.02), (0, 0, 0.10), make_material(
        "psl", (0.12, 0.09, 0.07), 1.0, noise=0.5))
    leaf = _green("pl")
    for i in range(6):                       # scruffy, uneven, alive
        h = 0.13 + 0.05 * (i % 3)
        box(f"pleaf{i}", (0.05, 0.05, h),
            (-0.13 + i * 0.052, (i % 2) * 0.03 - 0.015, 0.10 + h / 2), leaf,
            rot=(0, 0, math.radians(20 * i)))


def _dumpster():
    """Grime. Every inhabited street has one."""
    shell = make_material("dmp", (0.16, 0.24, 0.20), 0.85, noise=0.35)
    box("dbody", (0.28, 0.18, 0.16), (0, 0, 0.08), shell)
    box("dlid", (0.29, 0.19, 0.02), (0, 0.01, 0.17), _dark("dl"),
        rot=(0, math.radians(-6), 0))
    for lx in (-0.12, 0.12):
        box(f"dw{lx}", (0.04, 0.03, 0.04), (lx, 0.08, 0.02), _dark(f"dwl{lx}"))


def _bollards():
    """A short row of bollards — the kerb-line tell of a controlled approach."""
    post = _steel("bl")
    stripe = _amber("bls")
    for i in range(3):
        y = -0.16 + i * 0.16
        cylinder(f"bl{i}", 0.038, 0.28, (0, y, 0.14), post, axis="Z",
                 seg=12, arc=math.pi * 2)
        box(f"bls{i}", (0.085, 0.085, 0.03), (0, y, 0.26), stripe)


# ── vehicles ───────────────────────────────────────────────────────────

def _scooter(rotz=0.0):
    """Cheap two-wheeler. Rotate location AND box; never swap the size."""
    def build():
        rz = math.radians(rotz)
        c, s = math.cos(rz), math.sin(rz)
        R = lambda x, y: (x * c - y * s, x * s + y * c)

        def rb(n, size, loc, mat):
            x, y = R(loc[0], loc[1])
            box(n, size, (x, y, loc[2]), mat, rot=(0, 0, rz))

        frame = make_material(f"scf{rotz}", (0.30, 0.14, 0.12), 0.6)
        rb("sc_deck", (0.30, 0.10, 0.05), (0, 0, 0.11), frame)
        rb("sc_seat", (0.12, 0.11, 0.05), (-0.07, 0, 0.18), _dark(f"scs{rotz}"))
        rb("sc_col", (0.04, 0.04, 0.19), (0.12, 0, 0.20), frame)
        rb("sc_bar", (0.03, 0.19, 0.03), (0.12, 0, 0.30), _dark(f"scb{rotz}"))
        for wx in (-0.13, 0.13):
            x, y = R(wx, 0)
            box(f"scw{wx}{rotz}", (0.11, 0.04, 0.11), (x, y, 0.06),
                _dark(f"scwm{wx}{rotz}"), rot=(0, 0, rz))
    return build


def _bowser(rotz=0.0):
    """Water bowser. The tanker is the most colonial vehicle there is."""
    def build():
        rz = math.radians(rotz)
        c, s = math.cos(rz), math.sin(rz)
        R = lambda x, y: (x * c - y * s, x * s + y * c)

        def rb(n, size, loc, mat, extra=0.0):
            x, y = R(loc[0], loc[1])
            box(n, size, (x, y, loc[2]), mat, rot=(0, 0, rz + extra))

        cab = _plastic(f"bwc{rotz}", (0.18, 0.20, 0.19))
        rb("bw_cab", (0.16, 0.22, 0.20), (0.20, 0, 0.20), cab)
        rb("bw_glass", (0.02, 0.18, 0.08), (0.275, 0, 0.25),
           make_material(f"bwg{rotz}", (0.05, 0.08, 0.10), 0.15))
        tx, ty = R(-0.06, 0)
        cylinder(f"bw_tank{rotz}", 0.11, 0.30, (tx, ty, 0.21),
                 _steel(f"bwt{rotz}"),
                 axis="X" if rotz == 0 else "Y", seg=18, arc=math.pi * 2)
        rb("bw_band", (0.02, 0.23, 0.23), (-0.06, 0, 0.21), _amber(f"bwb{rotz}"))
        for wx in (-0.16, 0.04, 0.20):
            for side in (-0.10, 0.10):
                x, y = R(wx, side)
                box(f"bww{wx}{side}{rotz}", (0.08, 0.03, 0.08), (x, y, 0.05),
                    _dark(f"bwwm{wx}{side}{rotz}"), rot=(0, 0, rz))
    return build


# ── more people ────────────────────────────────────────────────────────

def crowd_extras():
    """
    Queues and pairs. A line of people says something a scatter cannot:
    that something here is rationed.
    """
    _crowd_scene("crowd_3", [(-0.14, 0.04, 0), (-0.05, 0.03, 5),
                             (0.04, 0.02, -5), (0.13, 0.01, 0)])   # queue
    _crowd_scene("crowd_4", [(-0.05, 0.0, 90), (0.05, 0.0, -90)])  # facing pair
    _crowd_scene("crowd_5", [(-0.09, 0.05, 25), (0.0, -0.02, -60),
                             (0.10, 0.06, 130), (0.03, 0.12, 10),
                             (-0.12, -0.08, -20)])                 # press


# ── entry point ────────────────────────────────────────────────────────

PROPS = {
    "cargo_pod": _cargo_pod,
    "pallets": _pallets,
    "spool": _spool,
    "scrap": _scrap,
    "water_tank": _water_tank,
    "genset": _genset,
    "junction": _junction,
    "lamp": _lamp,
    "kiosk": _kiosk,
    "planter": _planter,
    "dumpster": _dumpster,
    "bollards": _bollards,
}


def render_all():
    for name, build in PROPS.items():
        _prop_scene(name, build)
    _prop_scene("stall_x", _stall(0))
    _prop_scene("stall_y", _stall(90))
    _prop_scene("scooter_x", _scooter(0))
    _prop_scene("scooter_y", _scooter(90))
    _prop_scene("bowser_x", _bowser(0))
    _prop_scene("bowser_y", _bowser(90))
    crowd_extras()
