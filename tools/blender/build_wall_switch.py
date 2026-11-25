# -*- coding: utf-8 -*-
# Настенный выключатель — белая квадратная рамка со скруглёнными краями и большая клавиша-качелька
# (как обычный одноклавишный выключатель в квартире). Один на всю квартиру: прихожая у входной двери
# и комната Юрчика (stairwell.tscn — дочерняя модель у HallSwitchUse и LightSwitchUse).
#
#   WallSwitch_nocol     — рамка; точка опоры — центр задней стороны (плоскость стены), лицо смотрит в −X Godot;
#   WallSwitchKey_nocol  — клавиша, дочерняя к рамке; ось качания — горизонталь вдоль стены (rotation.z в Godot),
#                          игра качает её ±8° (stairwell.gd).
# Тёмная щель вокруг клавиши — тонкая тёмная подложка чуть больше клавиши.
#
# Запуск — только через Blender MCP (живой Blender), строит в своей сцене «WallSwitch»:
#   exec(open(r"<корень>/tools/blender/build_wall_switch.py", encoding="utf-8").read(),
#        {"__file__": r"<корень>/tools/blender/build_wall_switch.py", "__name__": "__main__"})
# Blender: Z вверх, стена — плоскость x = 0, выключатель торчит в −X.
import bpy, os
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "..", "assets", "models", "props"))

FRAME = 0.086          # м — рамка 86×86 мм
FRAME_T = 0.009        # толщина рамки
KEY = 0.056            # клавиша 56×56 мм
KEY_T = 0.008          # толщина клавиши над рамкой
GAP = 0.0018           # тёмная щель вокруг клавиши


def mat(name, rgb, rough):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = 0.0
    return m


def rounded_box(name, sx, sy, sz, center, bevel, segs, m, coll):
    """Ящик sx×sy×sz со скруглёнными рёбрами (модификатор Bevel применён)."""
    old = bpy.data.meshes.get(name)
    if old:
        bpy.data.meshes.remove(old)               # пересборка — без «.001» в именах
    me = bpy.data.meshes.new(name)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    v = [(x, y, z) for x in (-hx, hx) for y in (-hy, hy) for z in (-hz, hz)]
    f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    me.from_pydata(v, [], f)
    me.materials.append(m)
    ob.location = center
    if bevel > 0:
        bv = ob.modifiers.new("Bevel", 'BEVEL')
        bv.width = bevel
        bv.segments = segs
        bv.limit_method = 'NONE'
        bpy.context.view_layer.objects.active = ob
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        ob.select_set(True)
        bpy.ops.object.modifier_apply(modifier="Bevel")
    me.transform(Matrix.Translation(center))      # положение — в вершины, точка опоры остаётся в (0, 0, 0)
    ob.location = (0, 0, 0)
    return ob


def build():
    sc = bpy.data.scenes.get("WallSwitch") or bpy.data.scenes.new("WallSwitch")
    bpy.context.window.scene = sc
    coll = sc.collection
    for o in list(coll.all_objects):
        bpy.data.objects.remove(o, do_unlink=True)

    white = mat("WsWhite", (0.86, 0.86, 0.83), 0.45)
    gap = mat("WsGap", (0.16, 0.16, 0.16), 0.8)
    mark = mat("WsMark", (0.45, 0.45, 0.44), 0.6)

    # рамка: мягкая «подушка», передние края сильно скруглены
    frame = rounded_box("WallSwitch_nocol", FRAME_T, FRAME, FRAME, (-FRAME_T / 2, 0, 0), 0.0045, 3, white, coll)
    # тёмная щель под клавишей
    rounded_box("WsGap", 0.002, KEY + GAP * 2, KEY + GAP * 2, (-FRAME_T - 0.0005, 0, 0), 0.0, 0, gap, coll)
    # риска «|» над клавишей
    rounded_box("WsMark", 0.0006, 0.0012, 0.006, (-FRAME_T - 0.0002, 0, KEY / 2 + 0.0085), 0.0, 0, mark, coll)
    # клавиша: точка опоры в центре её задней стороны — качается вокруг горизонтали вдоль стены
    key = rounded_box("WallSwitchKey_nocol", KEY_T, KEY, KEY, (-KEY_T / 2, 0, 0), 0.0016, 2, white, coll)

    # щель и риску — в рамку одним мешем (меньше узлов в Godot)
    for o in coll.all_objects:
        o.select_set(o.name in ("WallSwitch_nocol", "WsGap", "WsMark"))
    bpy.context.view_layer.objects.active = frame
    bpy.ops.object.join()
    key.parent = frame
    key.location = (-FRAME_T, 0, 0)

    os.makedirs(OUT, exist_ok=True)
    for o in coll.all_objects:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "wall_switch.gltf"), use_selection=True, use_active_scene=True,
                              export_format='GLTF_SEPARATE', export_apply=True, export_yup=True)
    return {"out": os.path.join(OUT, "wall_switch.gltf"), "objects": [o.name for o in coll.all_objects]}


if __name__ == "__main__":
    RESULT = build()
