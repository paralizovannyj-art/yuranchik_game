# Временная (placeholder) модель Юрчика: сегментированный low-poly человек + молоток.
# Каждая часть — отдельный объект с центром в суставе, иерархия: Pelvis → Spine → Head / руки, Pelvis → ноги.
# Анимация — процедурная в Godot (scripts/player/yurchik_anim.gd).
# Запуск в Blender: exec(open(r"...\tools\blender\build_yurchik.py", encoding="utf-8").read())
import bpy, os, sys, math
import numpy as np
from mathutils import Vector, Matrix

BL = r"C:\Users\mrs\Documents\yuranchik_game\tools\blender"
sys.path.insert(0, BL)
import importlib, tex_lib
importlib.reload(tex_lib)
from tex_lib import *

NO_MAIN = True
exec(open(os.path.join(BL, "build_yard.py"), encoding="utf-8").read())  # даёт B, mat, OUT

R = np.random.default_rng(7)


# ---------------- текстуры персонажа ----------------
def textures():
    # чёрная дутая куртка: горизонтальная стёжка + блики нейлона
    w = h = 128
    a = fill(h, w, (0.07, 0.075, 0.085)) * (0.8 + fbm(w, h, 6, 6, R)[..., None] * 0.4)
    yy = np.arange(h)
    quilt = (np.sin(yy / h * math.pi * 2 * 6) * 0.5 + 0.5)[:, None, None]
    a = a * (0.75 + 0.5 * quilt)
    a[(yy % 21) < 2] *= 0.4
    a[:, 62:66] = rgb((0.15, 0.15, 0.16))  # молния
    save("yur_jacket", a)
    # джинсы
    n = fbm(w, h, 32, 64, R, oct=2)
    a = fill(h, w, (0.13, 0.17, 0.27)) * (0.75 + n[..., None] * 0.5)
    a *= (0.9 + 0.2 * fbm(w, h, 3, 6, R))[..., None]
    a[:, 0:3] *= 0.6
    save("yur_jeans", a)
    # кожа
    s = fill(32, 32, (0.78, 0.6, 0.5)) * (0.92 + fbm(32, 32, 4, 4, R)[..., None] * 0.16)
    save("yur_skin", s)
    # лицо 64x64 (перед головы)
    f = fill(64, 64, (0.78, 0.6, 0.5)) * (0.92 + fbm(64, 64, 6, 6, R)[..., None] * 0.14)
    f[22:25, 14:27] = rgb((0.22, 0.15, 0.1)); f[22:25, 37:50] = rgb((0.22, 0.15, 0.1))  # брови
    for cx in (20, 44):
        f[28:33, cx-5:cx+5] = rgb((0.85, 0.82, 0.78))
        f[28:33, cx-2:cx+2] = rgb((0.15, 0.1, 0.08))
        f[27:28, cx-5:cx+5] = rgb((0.4, 0.28, 0.22))
    f[30:44, 30:34] *= 0.9; f[42:45, 28:36] *= 0.75  # нос
    f[50:52, 24:40] = rgb((0.48, 0.28, 0.26))  # рот
    f[40:64] *= (1 - fbm(64, 24, 16, 8, R)[..., None] * 0.12)  # лёгкая щетина
    f[56:64] *= 0.9
    save("yur_face", f)
    # кроссовки
    a = fill(64, 64, (0.75, 0.75, 0.73)) * (0.85 + fbm(64, 64, 6, 6, R)[..., None] * 0.3)
    a[48:] = rgb((0.25, 0.24, 0.22))
    a[20:24, 10:54] = rgb((0.1, 0.1, 0.12))
    save("yur_shoes", a)
    # шапка
    a = fill(32, 64, (0.12, 0.12, 0.13)) * (0.8 + (np.arange(64) % 4 < 2)[None, :, None] * 0.25)
    save("yur_beanie", a)


# ---------------- части тела ----------------
def tbox(b, c0, c1, sz0, sz1, m, rect=None):
    """Сужающийся бокс вдоль Z: нижнее сечение sz0=(x,y) в c0, верхнее sz1 в c1."""
    (x0, y0), (x1, y1) = sz0, sz1
    p = [Vector((c0[0] - x0/2, c0[1] - y0/2, c0[2])), Vector((c0[0] + x0/2, c0[1] - y0/2, c0[2])),
         Vector((c0[0] + x0/2, c0[1] + y0/2, c0[2])), Vector((c0[0] - x0/2, c0[1] + y0/2, c0[2])),
         Vector((c1[0] - x1/2, c1[1] - y1/2, c1[2])), Vector((c1[0] + x1/2, c1[1] - y1/2, c1[2])),
         Vector((c1[0] + x1/2, c1[1] + y1/2, c1[2])), Vector((c1[0] - x1/2, c1[1] + y1/2, c1[2]))]
    quads = {'-Y': (0, 1, 5, 4), '+X': (1, 2, 6, 5), '+Y': (2, 3, 7, 6), '-X': (3, 0, 4, 7),
             '+Z': (4, 5, 6, 7), '-Z': (3, 2, 1, 0)}
    for k, q in quads.items():
        mm = m[k] if isinstance(m, dict) else m
        if mm is None:
            continue
        u = [(0, 0), (1, 0), (1, 1), (0, 1)]
        if k in ('+X', '-X', '+Y'):
            u = [(0.0, 0), (0.5, 0), (0.5, 1), (0.0, 1)]
        b.poly([p[i] for i in q], u, mm)


def part(name, coll, pivot, parent, build_fn):
    b = B()
    build_fn(b)
    ob = b.build(name, coll)
    # сдвигаем вершины так, чтобы origin был в суставе
    me = ob.data
    for v in me.vertices:
        v.co -= Vector(pivot)
    ob.location = Vector(pivot)
    if parent:
        ob.parent = parent
        ob.matrix_parent_inverse = parent.matrix_world.inverted()
    bpy.context.view_layer.update()
    return ob


def main_yur():
    sc = bpy.data.scenes.get("Yurchik") or bpy.data.scenes.new("Yurchik")
    for ob in list(sc.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)
    bpy.context.window.scene = sc
    textures()
    J = mat("YurJacket", "yur_jacket", rough=0.45)
    D = mat("YurJeans", "yur_jeans")
    S = mat("YurSkin", "yur_skin", rough=0.7)
    F = mat("YurFace", "yur_face", rough=0.7)
    SH = mat("YurShoes", "yur_shoes")
    BN = mat("YurBeanie", "yur_beanie")
    WD = mat("HammerWood", "wood", rough=0.7)
    MT = mat("HammerMetal", "metal", rough=0.4, metal=0.6)
    coll = sc.collection

    pelvis = part("Pelvis", coll, (0, 0, 0.95), None,
                  lambda b: tbox(b, (0, 0, 0.86), (0, 0, 1.03), (0.34, 0.21), (0.36, 0.22), D))
    spine = part("Spine", coll, (0, 0, 1.0), pelvis, lambda b: (
        tbox(b, (0, 0, 0.98), (0, 0, 1.3), (0.40, 0.27), (0.46, 0.29), J),
        tbox(b, (0, 0, 1.3), (0, 0, 1.47), (0.46, 0.29), (0.38, 0.24), J),
        tbox(b, (0, 0, 1.44), (0, 0.01, 1.53), (0.2, 0.17), (0.18, 0.15), J)))  # воротник
    def head_fn(b):
        tbox(b, (0, 0, 1.5), (0, 0, 1.58), (0.1, 0.1), (0.1, 0.1), S)
        tbox(b, (0, 0, 1.56), (0, 0, 1.78), (0.19, 0.21), (0.2, 0.22),
             {'-Y': F, '+X': S, '-X': S, '+Y': S, '+Z': None, '-Z': S})
        tbox(b, (0, 0.005, 1.72), (0, 0.01, 1.84), (0.215, 0.235), (0.17, 0.19), BN)
    head = part("Head", coll, (0, 0, 1.52), spine, head_fn)

    arms = {}
    for side, sx in (("L", 1), ("R", -1)):
        # в Blender перед — это -Y, значит левая рука персонажа — +X
        x = 0.27 * sx
        ua = part("UpperArm" + side, coll, (x, 0, 1.43), spine,
                  lambda b, x=x: tbox(b, (x, 0, 1.13), (x, 0, 1.46), (0.12, 0.13), (0.15, 0.16), J))
        fa = part("Forearm" + side, coll, (x, 0, 1.15), ua, lambda b, x=x: (
            tbox(b, (x, 0, 0.92), (x, 0, 1.17), (0.1, 0.11), (0.12, 0.13), J),
            tbox(b, (x, 0, 0.8), (x, 0, 0.92), (0.06, 0.1), (0.07, 0.09), S)))
        arms[side] = fa
        xl = 0.1 * sx
        th = part("Thigh" + side, coll, (xl, 0, 0.92), pelvis,
                  lambda b, xl=xl: tbox(b, (xl, 0, 0.5), (xl, 0, 0.94), (0.13, 0.14), (0.17, 0.18), D))
        part("Shin" + side, coll, (xl, 0, 0.5), th, lambda b, xl=xl: (
            tbox(b, (xl, 0, 0.09), (xl, 0, 0.52), (0.11, 0.12), (0.13, 0.14), D),
            tbox(b, (xl, -0.05, 0.0), (xl, -0.04, 0.1), (0.12, 0.3), (0.11, 0.26), SH)))

    # молоток в правой руке: рукоять вниз-вперёд, боёк внизу
    def hammer_fn(b):
        x = -0.27
        b.cyl((x, -0.03, 0.97), (x, -0.03, 0.62), 0.016, 0.018, WD, segs=6)
        tbox(b, (x, -0.03, 0.58), (x, -0.03, 0.635), (0.04, 0.14), (0.04, 0.14), MT)
    part("Hammer", coll, (-0.27, -0.03, 0.86), arms["R"], hammer_fn)

    # экспорт
    for o in sc.objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = pelvis
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "yurchik_placeholder.gltf"), use_selection=True,
                              export_keep_originals=True, export_format='GLTF_SEPARATE', export_apply=True)
    return {o.name: (o.parent.name if o.parent else None) for o in sc.objects}


result = main_yur()
