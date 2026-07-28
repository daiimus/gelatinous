"""Calibration renders: three emissive markers — world origin, +1x, +1z —
under the exact rig camera. measure.py turns them into anchors.json.

    blender --background --python scripts/atlas/sprites/calibrate.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rig  # noqa: E402  (auto-run is __main__-guarded)


def marker(name, loc):
    rig.clear_scene()
    mat = rig.make_material("m", (1, 1, 1), 0.2, emit=(1, 1, 1))
    rig.box(name, (0.04, 0.04, 0.04), loc, mat)
    rig.rig_camera_and_light()
    rig.render(f"calib_{name}")


marker("origin", (0, 0, 0))
marker("unitx", (1, 0, 0))
marker("unitz", (0, 0, 1))
print("calibration renders complete")
