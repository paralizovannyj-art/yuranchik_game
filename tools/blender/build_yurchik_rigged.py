# Юрчик v2: цельная low-poly модель в стиле PS2 со скелетом.
# Тело — из Skin-модификатора (графа «палочного человечка» с радиусами), голова и шапка — отдельные оболочки.
# Веса — по расстоянию до костей (детерминированно). UV — цилиндрические вокруг кости (стёжка куртки идёт кольцами).
# Анимация — процедурная в Godot (scripts/player/yurchik_anim.gd) через Skeleton3D.
# Запуск в Blender: exec(open(r"...\tools\blender\build_yurchik_rigged.py", encoding="utf-8").read())
import bpy, bmesh, os, sys, math
import numpy as np
from mathutils import Vector, Matrix

BL = r"C:\Users\mrs\Documents\yuranchik_game\tools\blender"
sys.path.insert(0, BL)
import importlib, tex_lib
importlib.reload(tex_lib)
from tex_lib import *

NO_MAIN = True
exec(open(os.path.join(BL, "build_yard.py"), encoding="utf-8").read())  # mat(), OUT

R = np.random.default_rng(11)

# ---------------- кости: имя, голова, хвост, родитель ----------------
BONES = [
    ("Pelvis", (0, 0, 0.94), (0, 0, 1.06), None),
    ("Spine", (0, 0, 1.06), (0, 0, 1.44), "Pelvis"),
    ("Head", (0, 0, 1.5), (0, 0, 1.82), "Spine"),
]
for s, sx in (("L", 1), ("R", -1)):
    BONES += [
        ("UpperArm" + s, (0.2 * sx, 0, 1.41), (0.27 * sx, 0.01, 1.15), "Spine"),
        ("Forearm" + s, (0.27 * sx, 0.01, 1.15), (0.29 * sx, -0.01, 0.9), "UpperArm" + s),
        ("Hand" + s, (0.29 * sx, -0.01, 0.9), (0.3 * sx, -0.02, 0.78), "Forearm" + s),
        ("Thigh" + s, (0.1 * sx, 0, 0.92), (0.1 * sx, -0.01, 0.5), "Pelvis"),
        ("Shin" + s, (0.1 * sx, -0.01, 0.5), (0.1 * sx, 0.01, 0.1), "Thigh" + s),
        ("Foot" + s, (0.1 * sx, 0.01, 0.1), (0.1 * sx, -0.15, 0.04), "Shin" + s),
    ]
BONE = {b[0]: b for b in BONES}
ADJ = {}
for n, h, t, p in BONES:
    ADJ.setdefault(n, set()).add(n)
    if p:
        ADJ[n].add(p); ADJ.setdefault(p, set()).add(n)


# ---------------- текстуры ----------------
def textures():
    # куртка: чёрный нейлон, стёжка кольцами по V (v — вдоль кости)
    w = h = 128
    a = fill(h, w, (0.075, 0.08, 0.09)) * (0.8 + fbm(w, h, 6, 6, R)[..., None] * 0.4)
    yy = np.arange(h)
    quilt = (np.sin(yy / h * math.pi * 2 * 5) * 0.5 + 0.5)[:, None, None]
    a = a * (0.65 + 0.7 * quilt)
    a[(yy % 26) < 2] *= 0.35
    a += (fbm(w, h, 3, 3, R)[..., None] - 0.5) * 0.04
    save("yur2_jacket", a)
    # джинсы: вертикальная диагональ + потёртости
    n = fbm(w, h, 48, 96, R, oct=2)
    a = fill(h, w, (0.12, 0.16, 0.26)) * (0.7 + n[..., None] * 0.55)
    wear = np.clip((fbm(w, h, 3, 4, R) - 0.5) * 2.5, 0, 1)
    a = a * (1 - wear[..., None] * 0.3) + wear[..., None] * rgb((0.12, 0.13, 0.15))
    a[:, 0:2] *= 0.55; a[:, 64:66] *= 0.55  # швы
    save("yur2_jeans", a)
    # кожа (руки, шея)
    s = fill(64, 64, (0.74, 0.56, 0.46)) * (0.9 + fbm(64, 64, 6, 6, R)[..., None] * 0.2)
    save("yur2_skin", s)
    # голова: цилиндрическая развёртка 128 (360°) x 64 (высота головы). Лицо — по центру (u = 0.5).
    W, H = 128, 64
    f = fill(H, W, (0.74, 0.56, 0.46)) * (0.9 + fbm(W, H, 8, 4, R)[..., None] * 0.18)
    xs = np.arange(W)[None, :]
    ys = np.arange(H)[:, None]
    # щёки и виски чуть темнее, середина светлее
    side = np.abs(xs - 64) / 64.0
    f *= (1.05 - side * 0.25)[..., None]
    # стрижка под машинку: всё, что не лицо и выше ушей
    hair = ((np.abs(xs - 64) > 22) & (ys < 30)) | (ys < 14)
    f[hair] = f[hair] * 0.35 + rgb((0.05, 0.04, 0.035))
    # уши
    for ex in (32, 96):
        m = ((xs - ex) ** 2 / 16 + (ys - 32) ** 2 / 50) < 1
        f[m] *= 0.82
        m2 = ((xs - ex) ** 2 / 5 + (ys - 33) ** 2 / 20) < 1
        f[m2] *= 0.7
    # брови
    f[24:26, 53:61] = rgb((0.2, 0.13, 0.09)); f[24:26, 67:75] = rgb((0.2, 0.13, 0.09))
    f[23, 55:60] = rgb((0.25, 0.17, 0.12)); f[23, 68:73] = rgb((0.25, 0.17, 0.12))
    # глаза: веко, белок, радужка, тень под глазом
    for cx in (57, 71):
        f[27, cx - 4:cx + 4] = rgb((0.3, 0.2, 0.16))
        f[28:30, cx - 3:cx + 3] = rgb((0.8, 0.77, 0.72))
        f[28:30, cx - 1:cx + 1] = rgb((0.18, 0.14, 0.1))
        f[31, cx - 3:cx + 3] *= 0.85
        f[32, cx - 3:cx + 3] *= 0.9
    # нос: светлая спинка, тень снизу, ноздри
    f[29:38, 63:65] *= 1.08
    f[30:38, 61:62] *= 0.9; f[30:38, 66:67] *= 0.9
    f[38:40, 61:67] *= 0.72
    f[39, 61:62] = rgb((0.3, 0.2, 0.17)); f[39, 66:67] = rgb((0.3, 0.2, 0.17))
    # рот
    f[44, 59:69] = rgb((0.42, 0.24, 0.22))
    f[45, 60:68] = rgb((0.55, 0.33, 0.3))
    f[46, 61:67] *= 0.95
    # щетина на челюсти и подбородок
    jaw = (ys > 38) & (np.abs(xs - 64) < 24)
    stub = (R.random((H, W)) > 0.8) & jaw
    f[stub] *= 0.92
    f[jaw] *= 0.96
    f[50:53, 56:72] *= 0.85
    f[H - 6:] *= 0.8
    save("yur2_face", f)
    # шапка: вязка рубчиком
    a = fill(64, 128, (0.1, 0.1, 0.11)) * (0.75 + ((np.arange(128) % 4) < 2)[None, :, None] * 0.35)
    a *= (0.9 + fbm(128, 64, 8, 4, R)[..., None] * 0.2)
    save("yur2_beanie", a)
    # кроссовки: белые, тёмная подошва внизу (v мал), полоска
    a = fill(64, 64, (0.78, 0.78, 0.76)) * (0.85 + fbm(64, 64, 6, 6, R)[..., None] * 0.25)
    a[:, :] *= np.where((np.arange(64) % 64 > 40)[None, :, None], 1.0, 1.0)
    a[54:] = rgb((0.22, 0.21, 0.2))
    a[30:34] = rgb((0.12, 0.12, 0.14))
    a *= (1 - np.clip((fbm(64, 64, 4, 4, R) - 0.55) * 2, 0, 1)[..., None] * 0.4)  # грязь
    save("yur2_shoes", a)


# ---------------- геометрия ----------------
def body_skin(coll):
    """Тело через Skin-модификатор."""
    S = 1.0
    V = {
        "pelvis": ((0, 0, 0.95), (0.165, 0.115)),
        "belly": ((0, 0, 1.1), (0.19, 0.13)),
        "chest": ((0, 0, 1.3), (0.215, 0.14)),
        "neck0": ((0, 0, 1.46), (0.075, 0.07)),
        "neck1": ((0, 0, 1.56), (0.055, 0.055)),
    }
    E = [("pelvis", "belly"), ("belly", "chest"), ("chest", "neck0"), ("neck0", "neck1")]
    for s, sx in (("L", 1), ("R", -1)):
        V["sh" + s] = ((0.2 * sx, 0, 1.41), (0.085, 0.085))
        V["el" + s] = ((0.27 * sx, 0.01, 1.15), (0.068, 0.068))
        V["wr" + s] = ((0.29 * sx, -0.01, 0.92), (0.058, 0.058))
        V["wr2" + s] = ((0.292 * sx, -0.012, 0.88), (0.035, 0.03))
        V["hd" + s] = ((0.3 * sx, -0.02, 0.79), (0.045, 0.026))
        V["hp" + s] = ((0.1 * sx, 0, 0.9), (0.09, 0.095))
        V["kn" + s] = ((0.1 * sx, -0.01, 0.5), (0.062, 0.065))
        V["an" + s] = ((0.1 * sx, 0.01, 0.12), (0.05, 0.05))
        V["hl" + s] = ((0.1 * sx, 0.04, 0.05), (0.05, 0.045))
        V["to" + s] = ((0.1 * sx, -0.16, 0.045), (0.052, 0.04))
        E += [("chest", "sh" + s), ("sh" + s, "el" + s), ("el" + s, "wr" + s), ("wr" + s, "wr2" + s),
              ("wr2" + s, "hd" + s), ("pelvis", "hp" + s), ("hp" + s, "kn" + s), ("kn" + s, "an" + s),
              ("an" + s, "hl" + s), ("hl" + s, "to" + s)]
    names = list(V.keys())
    me = bpy.data.meshes.new("YurBodySkin")
    me.from_pydata([V[n][0] for n in names], [(names.index(a), names.index(b)) for a, b in E], [])
    ob = bpy.data.objects.new("YurBody", me)
    coll.objects.link(ob)
    mod = ob.modifiers.new("Skin", 'SKIN')
    mod.branch_smoothing = 0.6
    mod.use_smooth_shade = True
    sk = me.skin_vertices[0].data
    for i, n in enumerate(names):
        sk[i].radius = V[n][1]
        sk[i].use_root = (n == "pelvis")
    sub = ob.modifiers.new("Sub", 'SUBSURF')
    sub.levels = 1; sub.render_levels = 1
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.ops.object.modifier_apply(modifier="Skin")
    bpy.ops.object.modifier_apply(modifier="Sub")
    return ob


def add_sphere(bm, center, radii, segs, rings, zmin=None):
    cx, cy, cz = center
    verts = []
    ring_list = []
    for r in range(1, rings):
        th = math.pi * r / rings
        z = math.cos(th)
        if zmin is not None and cz + z * radii[2] < zmin:
            break
        row = []
        for s in range(segs):
            ph = 2 * math.pi * s / segs
            x = math.sin(th) * math.cos(ph); y = math.sin(th) * math.sin(ph)
            row.append(bm.verts.new((cx + x * radii[0], cy + y * radii[1], cz + z * radii[2])))
        ring_list.append(row)
    top = bm.verts.new((cx, cy, cz + radii[2]))
    faces = []
    for s in range(segs):
        faces.append(bm.faces.new((top, ring_list[0][s], ring_list[0][(s + 1) % segs])))
    for r in range(len(ring_list) - 1):
        a, b = ring_list[r], ring_list[r + 1]
        for s in range(segs):
            faces.append(bm.faces.new((a[s], b[s], b[(s + 1) % segs], a[(s + 1) % segs])))
    last = ring_list[-1]
    if zmin is None:
        bot = bm.verts.new((cx, cy, cz - radii[2]))
        for s in range(segs):
            faces.append(bm.faces.new((bot, last[(s + 1) % segs], last[s])))
    return faces, last


def head_parts(coll, mats):
    """Голова, воротник и шапка — отдельный меш, потом присоединяется к телу."""
    me = bpy.data.meshes.new("YurHeadMesh")
    for m in mats:
        me.materials.append(m)
    bm = bmesh.new()
    # голова
    hf, _ = add_sphere(bm, (0, 0.0, 1.665), (0.098, 0.112, 0.125), 14, 10)
    for f in hf:
        f.material_index = 0
    for v in {v for f in hf for v in f.verts}:
        x, y, z = v.co
        if z < 1.64:  # сужаем челюсть
            k = 1 - (1.64 - z) * 2.2
            v.co.x *= k
            v.co.y = y * (k if y > 0 else 1 - (1.64 - z) * 1.2)
        if y < -0.08 and 1.625 < z < 1.68 and abs(x) < 0.02:  # нос
            v.co.y -= 0.022
        if y < -0.06 and 1.685 < z < 1.705 and 0.02 < abs(x) < 0.06:  # надбровья
            v.co.y -= 0.006
        if y > 0.02 and z > 1.6:  # затылок
            v.co.y *= 1.05
    # шапка: купол + отворот
    bf, last = add_sphere(bm, (0, 0.005, 1.725), (0.106, 0.12, 0.1), 14, 8, zmin=1.72)
    for f in bf:
        f.material_index = 1
    rim0, rim1 = [], []
    for s in range(14):
        ph = 2 * math.pi * s / 14
        rim0.append(bm.verts.new((math.cos(ph) * 0.112, 0.005 + math.sin(ph) * 0.124, 1.708)))
        rim1.append(bm.verts.new((math.cos(ph) * 0.112, 0.005 + math.sin(ph) * 0.124, 1.76)))
    for s in range(14):
        f = bm.faces.new((rim0[s], rim0[(s + 1) % 14], rim1[(s + 1) % 14], rim1[s])); f.material_index = 1
    # воротник куртки
    c0, c1 = [], []
    for s in range(12):
        ph = 2 * math.pi * s / 12
        c0.append(bm.verts.new((math.cos(ph) * 0.11, math.sin(ph) * 0.1, 1.42)))
        c1.append(bm.verts.new((math.cos(ph) * 0.085, math.sin(ph) * 0.08 + 0.005, 1.53)))
    for s in range(12):
        f = bm.faces.new((c0[s], c0[(s + 1) % 12], c1[(s + 1) % 12], c1[s])); f.material_index = 2
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new("YurHead", me)
    coll.objects.link(ob)
    return ob


# ---------------- UV, материалы, веса ----------------
def seg_closest(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    return t, (a + ab * t)


def nearest_bone(p, exclude_head=False):
    best = None
    for n, h, t, par in BONES:
        if exclude_head and n == "Head":
            continue
        a, b = Vector(h), Vector(t)
        tt, q = seg_closest(p, a, b)
        d = (p - q).length
        if best is None or d < best[1]:
            best = (n, d, tt)
    return best


def make_mats():
    return dict(MJ=mat("Yur2Jacket", "yur2_jacket", rough=0.4), MD=mat("Yur2Jeans", "yur2_jeans"),
                MS=mat("Yur2Skin", "yur2_skin", rough=0.7), MF=mat("Yur2Face", "yur2_face", rough=0.7),
                MB=mat("Yur2Beanie", "yur2_beanie"), MSH=mat("Yur2Shoes", "yur2_shoes", rough=0.6))


def finish(body, head, M2):
    MJ, MD, MS, MSH = M2["MJ"], M2["MD"], M2["MS"], M2["MSH"]
    # материалы тела по области
    me = body.data
    for m in (MJ, MD, MS, MSH):
        me.materials.append(m)
    for p in me.polygons:
        c = p.center
        ax = abs(c.x)
        if c.z < 0.16:
            p.material_index = 3
        elif ax > 0.22 and c.z < 0.925:
            p.material_index = 2  # кисти
        elif c.z > 1.5:
            p.material_index = 2  # шея
        elif c.z < 1.0 and ax < 0.24:
            p.material_index = 1  # джинсы
        else:
            p.material_index = 0  # куртка
    # объединяем
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    body.select_set(True); head.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()
    ob = body
    me = ob.data
    # UV: цилиндрическая развёртка вокруг ближайшей кости
    uvl = me.uv_layers.new(name="UVMap")
    for p in me.polygons:
        mname = me.materials[p.material_index].name
        us, vs = [], []
        for li in p.loop_indices:
            v = me.vertices[me.loops[li].vertex_index].co
            if mname == "Yur2Face":
                u = math.atan2(v.x, -v.y) / (2 * math.pi) + 0.5
                vv = (v.z - 1.54) / 0.25
            elif mname == "Yur2Beanie":
                u = (math.atan2(v.x, -v.y) / (2 * math.pi) + 0.5) * 2
                vv = (v.z - 1.708) / 0.12
            else:
                n, d, tt = nearest_bone(v, exclude_head=True)
                _, hd, tl, _ = BONE[n]
                a, b = Vector(hd), Vector(tl)
                axis = (b - a).normalized()
                ref = Vector((0, -1, 0)) if abs(axis.y) < 0.8 else Vector((0, 0, 1))
                x1 = (ref - axis * ref.dot(axis)).normalized()
                y1 = axis.cross(x1)
                r = v - a
                ang = math.atan2(r.dot(y1), r.dot(x1))
                u = ang / (2 * math.pi) + 0.5
                vv = -r.dot(axis) / 0.45 if n not in ("Pelvis", "Spine") else v.z / 0.45
                if mname == "Yur2Shoes":
                    vv = v.z / 0.16
            us.append(u); vs.append(vv)
        # шов развёртки: не даём полигону «растянуться» через 0/1
        if max(us) - min(us) > 0.5:
            us = [u + 1 if u < 0.5 else u for u in us]
        for k, li in enumerate(p.loop_indices):
            uvl.data[li].uv = (us[k], vs[k])
    return ob


def rig(ob, coll):
    arm_data = bpy.data.armatures.new("YurchikRig")
    arm = bpy.data.objects.new("Yurchik", arm_data)
    coll.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    arm.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm_data.edit_bones
    for n, h, t, p in BONES:
        b = eb.new(n)
        b.head = h; b.tail = t
        b.roll = 0.0
        if p:
            b.parent = eb[p]
    bpy.ops.object.mode_set(mode='OBJECT')
    # веса по расстоянию до костей (с плавным переходом только между соседними костями)
    groups = {n: ob.vertex_groups.new(name=n) for n, *_ in BONES}
    me = ob.data
    head_mats = {i for i, m in enumerate(me.materials) if m.name in ("Yur2Face", "Yur2Beanie")}
    head_verts = set()
    for p in me.polygons:
        if p.material_index in head_mats:
            head_verts.update(p.vertices)
    for v in me.vertices:
        if v.index in head_verts:
            groups["Head"].add([v.index], 1.0, 'REPLACE')
            continue
        p = v.co
        ds = []
        for n, h, t, par in BONES:
            if n == "Head" and p.z < 1.5:
                continue
            _, q = seg_closest(p, Vector(h), Vector(t))
            ds.append(((p - q).length, n))
        ds.sort()
        d1, n1 = ds[0]
        cand = [(d1, n1)] + [(d, n) for d, n in ds[1:4] if n in ADJ[n1] and d < d1 * 1.8 + 0.02]
        ws = [(1.0 / max(d, 0.01) ** 4, n) for d, n in cand]
        tot = sum(w for w, _ in ws)
        for w, n in ws:
            groups[n].add([v.index], w / tot, 'REPLACE')
    ob.parent = arm
    mod = ob.modifiers.new("Armature", 'ARMATURE')
    mod.object = arm
    return arm


def hammer(arm, coll):
    b = B()
    WD = mat("Yur2HammerWood", "wood", rough=0.7)
    MT = mat("Yur2HammerMetal", "metal", rough=0.4, metal=0.6)
    x = -0.3
    b.cyl((x, -0.02, 0.88), (x, -0.02, 0.55), 0.016, 0.019, WD, segs=6)
    b.box((x - 0.022, -0.1, 0.5), (x + 0.022, 0.06, 0.555), {k: MT for k in ('+X', '-X', '+Y', '-Y', '+Z', '-Z')}, scale=(0.2, 0.2))
    ob = b.build("Hammer", coll)
    # origin в кисть, родитель — кость HandR
    piv = Vector((x, -0.02, 0.84))
    for v in ob.data.vertices:
        v.co -= piv
    ob.location = piv
    ob.parent = arm
    ob.parent_type = 'BONE'
    ob.parent_bone = "HandR"
    bpy.context.view_layer.update()
    # parent_type BONE считает от хвоста кости — компенсируем
    pb = arm.pose.bones["HandR"]
    tail_m = arm.matrix_world @ Matrix.Translation(pb.tail) @ pb.matrix.to_3x3().to_4x4()
    ob.matrix_parent_inverse = tail_m.inverted()
    ob.location = piv
    return ob


def main():
    sc = bpy.data.scenes.get("Yurchik2") or bpy.data.scenes.new("Yurchik2")
    for ob in list(sc.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)
    for a in list(bpy.data.armatures):
        if a.users == 0:
            bpy.data.armatures.remove(a)
    bpy.context.window.scene = sc
    coll = sc.collection
    textures()
    M2 = make_mats()
    body = body_skin(coll)
    head = head_parts(coll, (M2["MF"], M2["MB"], M2["MJ"]))
    ob = finish(body, head, M2)
    ob.name = "YurchikMesh"
    arm = rig(ob, coll)
    hm = hammer(arm, coll)
    tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    for o in sc.objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "yurchik.gltf"), use_selection=True,
                              export_keep_originals=True, export_format='GLTF_SEPARATE',
                              export_apply=False, export_skins=True, export_animations=False)
    return {"tris": tris, "verts": len(ob.data.vertices), "objects": [o.name for o in sc.objects]}


result = main()
