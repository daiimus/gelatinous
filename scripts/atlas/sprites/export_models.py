"""Export every sprite model to models.json for the live 3D atlas.

    blender --background --python scripts/atlas/sprites/export_models.py

v2: the models carry their Cycles verdict with them. Each captured
scene is joined, subdivided to bake resolution, and COMBINED-baked
(sun + teal fill + world, GI and soft shadows and material noise all
included) into vertex colors. The live atlas replays that lighting
from any camera angle - the old renderer IS the new renderer; only
the viewpoint went dynamic. Emissive-material faces are exported with
an emissive flag so windows still bloom past the bake.
"""
import importlib.util
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["RIG_VIEWS"] = "0"

import bmesh  # noqa: E402
import bpy  # noqa: E402
import rig  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = {}


def _emissive(mat):
    try:
        bsdf = mat.node_tree.nodes["Principled BSDF"]
        estr = float(bsdf.inputs["Emission Strength"].default_value)
        ecol = list(bsdf.inputs["Emission Color"].default_value)[:3]
        if estr > 0.05 and any(v > 0.01 for v in ecol):
            return [round(v, 3) for v in ecol], round(estr, 2)
    except Exception:  # noqa: BLE001
        pass
    return None, 0


def capture(name, res=None):
    """Stand-in for rig.render: join, subdivide, bake, serialize."""
    if name.startswith("calib_"):
        return
    meshes = [o for o in bpy.context.collection.objects
              if o.type == "MESH" and not getattr(o, "is_shadow_catcher", False)]
    if not meshes:
        MODELS[name] = {}
        return

    # per-material emissive flags, gathered before the join
    emiss = {}
    for o in meshes:
        for mat in o.data.materials:
            if mat and mat.name not in emiss:
                emiss[mat.name] = _emissive(mat)

    # the rig scenes have no camera yet at render() time in this flow -
    # the capture replaces it - but baking needs the world lights the
    # renders had, so recreate them without a camera
    rig.rig_camera_and_light()
    for o in list(bpy.context.collection.objects):
        if o.type == "CAMERA":
            bpy.data.objects.remove(o)

    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # subdivide long edges toward bake resolution
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    for _ in range(2):
        long_edges = [e for e in bm.edges if e.calc_length() > 0.34]
        if not long_edges:
            break
        bmesh.ops.subdivide_edges(bm, edges=long_edges, cuts=1,
                                  use_grid_fill=True)
    bm.to_mesh(obj.data)
    bm.free()

    obj.data.color_attributes.new(name="bake", type="BYTE_COLOR",
                                  domain="POINT")

    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 48
    sc.cycles.use_denoising = False       # vertex bake: no denoiser
    sc.render.bake.target = "VERTEX_COLORS"
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.bake(type="COMBINED")

    mesh = obj.data
    col = mesh.color_attributes["bake"].data
    verts = []
    for v in mesh.vertices:
        verts.extend((round(v.co.x, 3), round(v.co.y, 3), round(v.co.z, 3)))
    # per-POINT colors: average loop-domain if needed (POINT domain is 1:1)
    colors = []
    for i in range(len(mesh.vertices)):
        c = col[i].color
        colors.extend((min(255, int(c[0] * 255)),
                       min(255, int(c[1] * 255)),
                       min(255, int(c[2] * 255))))
    faces = []
    face_mats = []
    for poly in mesh.polygons:
        vs = poly.vertices
        for i in range(1, len(vs) - 1):
            faces.extend((vs[0], vs[i], vs[i + 1]))
            face_mats.append(poly.material_index)
    # emissive triangles listed by index so the viewer can boost them
    mat_names = [m.name if m else "" for m in mesh.materials]
    etris = []
    for ti, mi in enumerate(face_mats):
        nm = mat_names[mi] if mi < len(mat_names) else ""
        ecol, estr = emiss.get(nm, (None, 0))
        if ecol:
            etris.append(ti)
    MODELS[name] = {"v": verts, "c": colors, "f": faces, "e": etris}
    print(f"baked {name}: {len(verts)//3} verts, {len(faces)//3} tris,"
          f" {len(etris)} emissive tris")


rig.render = capture

# ── the class-sprite library: replay rig.py's own main block ──────────
src = open(rig.__file__).read()
guard = 'if __name__ == "__main__":'
main_block = src.split(guard, 1)[1]
main_lines = [ln[4:] if ln.startswith("    ") else ln
              for ln in main_block.splitlines()]
exec("\n".join(main_lines), vars(rig))  # noqa: S102 - our own source

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
