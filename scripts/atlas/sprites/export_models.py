"""Export every sprite model to models.json for the live 3D atlas.

    blender --background --python scripts/atlas/sprites/export_models.py

The same scenes that render the sprite library ARE the models: this
script patches ``rig.render`` to capture the built scene (world-space
triangles + Principled material parameters) instead of photographing
it, then replays the class-sprite main block and every hero script.
One source of truth, two renderers.
"""
import importlib.util
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["RIG_VIEWS"] = "0"

import bpy  # noqa: E402
import rig  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = {}


def _material(obj):
    if not obj.data.materials:
        return {"c": [0.5, 0.5, 0.5], "r": 0.8}
    mat = obj.data.materials[0]
    try:
        bsdf = mat.node_tree.nodes["Principled BSDF"]
    except Exception:  # noqa: BLE001
        return {"c": [0.5, 0.5, 0.5], "r": 0.8}
    base = list(bsdf.inputs["Base Color"].default_value)[:3]
    rough = float(bsdf.inputs["Roughness"].default_value)
    out = {"c": [round(v, 4) for v in base], "r": round(rough, 3)}
    try:
        estr = float(bsdf.inputs["Emission Strength"].default_value)
        if estr > 0.001:
            ecol = list(bsdf.inputs["Emission Color"].default_value)[:3]
            if any(v > 0.001 for v in ecol):
                out["e"] = [round(v, 4) for v in ecol]
                out["es"] = round(estr, 3)
    except Exception:  # noqa: BLE001
        pass
    return out


def capture(name, res=None):
    """Stand-in for rig.render: serialize the scene instead."""
    if name.startswith("calib_"):
        return
    objs = []
    for o in bpy.context.collection.objects:
        if o.type != "MESH" or getattr(o, "is_shadow_catcher", False):
            continue
        mw = o.matrix_world
        verts = []
        for v in o.data.vertices:
            w = mw @ v.co
            verts.extend((round(w.x, 3), round(w.y, 3), round(w.z, 3)))
        faces = []
        for poly in o.data.polygons:
            vs = poly.vertices
            for i in range(1, len(vs) - 1):          # fan-triangulate
                faces.extend((vs[0], vs[i], vs[i + 1]))
        objs.append({"v": verts, "f": faces, "m": _material(o)})
    MODELS[name] = objs
    print(f"captured {name}: {len(objs)} objects")


rig.render = capture

# ── the class-sprite library: replay rig.py's own main block ──────────
src = open(rig.__file__).read()
guard = 'if __name__ == "__main__":'
main_block = src.split(guard, 1)[1]
main_lines = [ln[4:] if ln.startswith("    ") else ln
              for ln in main_block.splitlines()]
exec("\n".join(main_lines), vars(rig))  # noqa: S102 — our own source

# ── the heroes ────────────────────────────────────────────────────────
for hero in ("landmark_boot", "landmark_bridge", "landmark_agridome",
             "landmark_brackett_roof", "landmark_thawn"):
    spec = importlib.util.spec_from_file_location(
        hero, os.path.join(HERE, f"{hero}.py"))
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except SystemExit:
        pass

out_path = os.path.join(HERE, "models.json")
json.dump(MODELS, open(out_path, "w"), separators=(",", ":"))
size = os.path.getsize(out_path)
print(f"models.json: {len(MODELS)} models, {size // 1024}KB")
