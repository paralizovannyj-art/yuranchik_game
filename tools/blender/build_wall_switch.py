# -*- coding: utf-8 -*-
# Настенный выключатель — квадратная рамка и большая клавиша-качелька (обычный одноклавишный выключатель
# в квартире). Один на всю квартиру: прихожая у входной двери и комната Юрчика (stairwell.tscn — дочерняя модель
# у HallSwitchUse и LightSwitchUse).
#
# Под PS2, чтобы не выделялся: никаких гладких скруглений — простые ящики с одной фаской, а весь вид — в крошечной
# текстуре 24×24 (assets/textures/wall_switch.png): пожелтевший старый пластик, грязь, залапанная клавиша,
# тёмная щель и риска нарисованы пикселями. Рамка и клавиша берут её проекцией спереди.
#
#   WallSwitch_nocol     — рамка; точка опоры — центр задней стороны (плоскость стены), лицо смотрит в −X Godot;
#   WallSwitchKey_nocol  — клавиша, дочерняя к рамке; ось качания — горизонталь вдоль стены (rotation.z в Godot),
#                          игра качает её ±8° (stairwell.gd).
#
# Запуск — только через Blender MCP (живой Blender), строит в своей сцене «WallSwitch»:
#   exec(open(r"<корень>/tools/blender/build_wall_switch.py", encoding="utf-8").read(),
#        {"__file__": r"<корень>/tools/blender/build_wall_switch.py", "__name__": "__main__"})
# Blender: Z вверх, стена — плоскость x = 0, выключатель торчит в −X.
import bpy, os, sys
import numpy as np
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from tex_lib import save, fbm

OUT = os.path.normpath(os.path.join(HERE, "..", "..", "assets", "models", "props"))

FRAME = 0.086          # м — рамка 86×86 мм
FRAME_T = 0.008        # толщина рамки
KEY = 0.056            # клавиша 56×56 мм
KEY_T = 0.006          # толщина клавиши над рамкой
TEX = 24               # px — вся рамка в текстуре (≈3.6 мм на пиксель)


def tex():
    """24×24: старый пластик цвета слоновой кости, тёмная щель вокруг клавиши, риска, грязь у краёв и на клавише."""
    rng = np.random.default_rng(86)
    n = TEX
    base = np.array((0.74, 0.71, 0.62), np.float32)                      # пожелтевший белый
    a = np.ones((n, n, 3), np.float32) * base
    a *= (0.92 + 0.12 * fbm(n, n, 3, 3, rng, oct=2))[..., None]            # неровно пожелтел
    yy, xx = np.mgrid[0:n, 0:n]
    edge = np.minimum(np.minimum(xx, n - 1 - xx), np.minimum(yy, n - 1 - yy))
    a[edge == 0] *= 0.72                                                   # грязь по краю рамки
    a[edge == 1] *= 0.9
    k0, k1 = 4, n - 4                                                      # клавиша 16 px
    ring = ((xx >= k0 - 1) & (xx <= k1) & (yy >= k0 - 1) & (yy <= k1)) & \
           ~((xx >= k0) & (xx < k1) & (yy >= k0) & (yy < k1))
    a[ring] *= 0.55                                                        # щель — тень, не чёрная линия
    key = (xx >= k0) & (xx < k1) & (yy >= k0) & (yy < k1)
    a[key] *= 1.04
    a[(yy == k1 - 1) & key] *= 0.82                                        # нижний край клавиши в тени
    smear = np.exp(-(((xx - 14.5) / 3.5) ** 2 + ((yy - 13.5) / 3.0) ** 2))  # залапано пальцем
    a *= (1 - 0.22 * smear)[..., None]
    a[1:3, 11:13] = (0.45, 0.44, 0.40)                                     # риска «|»
    return save("wall_switch", np.clip(a, 0, 1))


def mat_tex(name):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.85
    bsdf.inputs["Metallic"].default_value = 0.0
    t = nt.nodes.get("Tex") or nt.nodes.new("ShaderNodeTexImage")
    t.name = "Tex"
    t.image = bpy.data.images["wall_switch"]
    t.interpolation = 'Closest'
    nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
    return m


def box(name, sx, sy, sz, center, chamfer, m, coll):
    """Ящик sx×sy×sz, передние рёбра срезаны одной фаской (low-poly), UV — проекция спереди по рамке."""
    old = bpy.data.meshes.get(name)
    if old:
        bpy.data.meshes.remove(old)               # пересборка — без «.001» в именах
    me = bpy.data.meshes.new(name)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    c = chamfer
    # задняя грань (к стене, +X) полная, передняя (−X) меньше на фаску
    back = [(hx, -hy, -hz), (hx, hy, -hz), (hx, hy, hz), (hx, -hy, hz)]
    front = [(-hx, -hy + c, -hz + c), (-hx, hy - c, -hz + c), (-hx, hy - c, hz - c), (-hx, -hy + c, hz - c)]
    v = back + front
    f = [(4, 7, 6, 5),                                       # лицо
         (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]   # скошенные бока
    me.from_pydata(v, [], f)
    me.transform(Matrix.Translation(center))
    me.materials.append(m)
    uv = me.uv_layers.new(name="UV")
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = (0.5 - co.y / FRAME, 0.5 + co.z / FRAME)   # вид спереди (из −X): +Y Blender — влево
    return ob


def build():
    sc = bpy.data.scenes.get("WallSwitch") or bpy.data.scenes.new("WallSwitch")
    bpy.context.window.scene = sc
    coll = sc.collection
    for o in list(coll.all_objects):
        bpy.data.objects.remove(o, do_unlink=True)

    tex()
    m = mat_tex("WsPlastic")
    frame = box("WallSwitch_nocol", FRAME_T, FRAME, FRAME, (-FRAME_T / 2, 0, 0), 0.004, m, coll)
    key = box("WallSwitchKey_nocol", KEY_T, KEY, KEY, (-KEY_T / 2, 0, 0), 0.0015, m, coll)
    key.parent = frame
    key.location = (-FRAME_T, 0, 0)

    os.makedirs(OUT, exist_ok=True)
    for o in coll.all_objects:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "wall_switch.gltf"), use_selection=True, use_active_scene=True,
                              export_format='GLTF_SEPARATE', export_apply=True, export_yup=True,
                              export_keep_originals=True)          # ссылка на assets/textures/wall_switch.png
    return {"out": os.path.join(OUT, "wall_switch.gltf"), "objects": [o.name for o in coll.all_objects]}


if __name__ == "__main__":
    RESULT = build()
