# -*- coding: utf-8 -*-
# Проверка позы сна Хьюги на диване Юрчика — в открытом Blender, после build_hyuga.py.
# Импортирует диван, плед и подушку (assets/models/yurchik_room/*.gltf) в сцену «Hyuga», в коллекцию «HyugaBed»,
# и ставит их вокруг собаки ровно так, как они стоят в игре: позиции и повороты читаются из
# scenes/levels/stairwell.tscn (узлы YurchikRoom/Sofa, SofaBlanket, Pillow относительно узла Hyuga).
# Собака остаётся в начале координат — мебель ставится в её систему (корень «HyugaBedRoot» = обратная к Hyuga).
# Перевод осей Godot → Blender: (x, y, z) → (x, −z, y).
#
# Запуск через Blender MCP:
#   exec(open(r"<проект>\tools\blender\hyuga_bed_check.py", encoding="utf-8").read(),
#        {"__file__": r"<проект>\tools\blender\hyuga_bed_check.py"})
# Повторный запуск пересоздаёт коллекцию. На экспорт собаки не влияет (экспортируются только выбранные скелет и меш).
import bpy, os, re
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(globals().get("__file__") or __file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
TSCN = os.path.join(ROOT, "scenes", "levels", "stairwell.tscn")
ROOM = os.path.join(ROOT, "assets", "models", "yurchik_room")
PARTS = {"Sofa": "sofa.gltf", "SofaBlanket": "sofa_blanket.gltf", "Pillow": "pillow.gltf"}
COLL = "HyugaBed"
C = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))      # Godot → Blender


def node_xforms(names):
    """Transform3D узлов YurchikRoom/<имя> из .tscn → матрицы Blender."""
    txt = open(TSCN, encoding="utf-8").read()
    out = {}
    for n in names:
        m = re.search(r'\[node name="%s" parent="YurchikRoom"[^\]]*\]\s*\ntransform = Transform3D\(([^)]*)\)' % n, txt)
        v = [float(x) for x in m.group(1).split(",")]
        g = Matrix(((v[0], v[1], v[2], v[9]), (v[3], v[4], v[5], v[10]), (v[6], v[7], v[8], v[11]), (0, 0, 0, 1)))
        out[n] = C @ g @ C.inverted()
    return out


def main():
    sc = bpy.data.scenes["Hyuga"]
    bpy.context.window.scene = sc
    old = bpy.data.collections.get(COLL)
    if old:
        for ob in list(old.all_objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.collections.remove(old)
    coll = bpy.data.collections.new(COLL)
    sc.collection.children.link(coll)
    lc = bpy.context.view_layer.layer_collection.children[COLL]
    bpy.context.view_layer.active_layer_collection = lc

    X = node_xforms(["Hyuga"] + list(PARTS))
    root = bpy.data.objects.new("HyugaBedRoot", None)
    coll.objects.link(root)
    root.matrix_world = X["Hyuga"].inverted()
    made = {}
    for name, fn in PARTS.items():
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=os.path.join(ROOM, fn))
        new = [o for o in bpy.data.objects if o not in before]
        holder = bpy.data.objects.new("Bed_" + name, None)
        coll.objects.link(holder)
        holder.parent = root
        holder.matrix_basis = X[name]
        for o in new:
            for c in list(o.users_collection):
                if c != coll:
                    c.objects.unlink(o)
            if o.name not in coll.objects:
                coll.objects.link(o)
            if o.parent is None:
                o.parent = holder
        made[name] = [o.name for o in new]
    bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection
    bpy.context.view_layer.update()
    return {"parts": made, "hyuga_room": [round(x, 3) for x in X["Hyuga"].translation]}


result = main()
