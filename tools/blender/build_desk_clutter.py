# -*- coding: utf-8 -*-
# Мелочь на столе Юрчика v2: бутылки воды «Моршинська» 1,5 л и «Миргородська» 0,5 л, белая кружка «MAYSKIY»
# с чаем, белая миска с синей каймой, остатками борща и ложкой. Заменяет восьмигранные цилиндры из
# build_yurchik_room.py (там эти предметы больше не строятся).
#
# Порядок:
#   1) python tools/blender/desk_clutter_textures.py           — текстура assets/textures/dc_atlas.png
#   2) через Blender MCP: exec(open(r"<путь>\tools\blender\build_desk_clutter.py", encoding="utf-8").read(),
#                              {"__file__": r"<путь>\tools\blender\build_desk_clutter.py", "__name__": "__main__"})
#      (строит всё в своей сцене DeskClutter, остальные сцены не трогает)
# Результат: assets/models/yurchik_room/{desk_bottle_tall,desk_bottle_short,mug,bowl}.gltf — те же файлы, что и раньше,
# точка опоры там же (узлы в stairwell.tscn не двигаются). Предмет строится вокруг своей точки опоры ANCHOR (Godot).
#
# Материалы: DcAtlas — непрозрачное (этикетки, крышки, кружка, миска), DcSteel — ложка (двусторонняя),
# DcClear — прозрачный пластик бутылок (альфа из текстуры). Всё — без коллизии (…_nocol).
import bpy, bmesh, os, sys, math, json
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else r"C:\Users\mrs\Documents\yuranchik_game\tools\blender"
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import importlib
import desk_clutter_textures as T
importlib.reload(T)

TEX = os.path.join(ROOT, "assets", "textures")
ITEM_DIR = os.path.join(ROOT, "assets", "models", "yurchik_room")
SCENE = "DeskClutter"
SZ = T.SIZE

# точки опоры (координаты Godot: x, y — верх столешницы, z) — как у узлов в stairwell.tscn
ANCHOR = {
    "desk_bottle_tall": (-7.43, 9.14, -3.80),
    "desk_bottle_short": (-7.43, 9.14, -3.70),
    "mug": (-7.36, 9.14, -3.52),
    "bowl": (-7.285, 9.14, -3.361),
}


def UV(name, pad=2.0):
    """Кусок атласа в UV; pad — отступ в пикселях внутрь, чтобы фильтрация и мипмапы не цепляли соседние куски
    (иначе на шве миски проступают синие и красные точки)."""
    x0, y0, x1, y1 = T.A[name]
    return ((x0 + pad) / SZ, 1 - (y1 - pad) / SZ, (x1 - pad) / SZ, 1 - (y0 + pad) / SZ)


# =====================================================================================
#  Построитель сетки
# =====================================================================================
class Mesh:
    def __init__(self):
        self.v, self.f, self.uv, self.mi, self.mats = [], [], [], [], []

    def poly(self, pts, uvs, m):
        if m not in self.mats:
            self.mats.append(m)
        base = len(self.v)
        self.v += [tuple(p) for p in pts]
        self.f.append(tuple(range(base, base + len(pts))))
        self.uv.append([tuple(u) for u in uvs])
        self.mi.append(self.mats.index(m))

    def build(self, name, coll, sharp=35):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        for m in self.mats:
            me.materials.append(m)
        uvl = me.uv_layers.new(name="UVMap")
        for pi, poly in enumerate(me.polygons):
            poly.material_index = self.mi[pi]
            for k, li in enumerate(poly.loop_indices):
                uvl.data[li].uv = self.uv[pi][k]
        bm = bmesh.new(); bm.from_mesh(me)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
        bm.to_mesh(me); bm.free()
        for p in me.polygons:
            p.use_smooth = True
        me.set_sharp_from_angle(angle=math.radians(sharp))       # гладкие стенки, острые кромки
        me.validate(); me.update()
        ob = bpy.data.objects.new(name, me)
        coll.objects.link(ob)
        return ob


def lathe(b, prof, m, rect, segs=16, rfun=None, a0=0.0, flip=False):
    """Тело вращения вокруг оси Z. prof — [(r, z)] снизу вверх; u — по кругу, v — по длине профиля.
    rfun(a, z) — множитель радиуса (лепестки дна бутылки). flip — нормали внутрь (стенка изнутри)."""
    L = [0.0]
    for (r0, z0), (r1, z1) in zip(prof, prof[1:]):
        L.append(L[-1] + math.hypot(r1 - r0, z1 - z0))
    tot = L[-1] or 1.0
    u0, v0, u1, v1 = rect

    def P(i, k):
        r, z = prof[k]
        a = a0 + 2 * math.pi * i / segs
        if rfun:
            r *= rfun(a, z)
        return (r * math.cos(a), r * math.sin(a), z)

    for k in range(len(prof) - 1):
        va, vb = v0 + (v1 - v0) * L[k] / tot, v0 + (v1 - v0) * L[k + 1] / tot
        for i in range(segs):
            ua, ub = u0 + (u1 - u0) * i / segs, u0 + (u1 - u0) * (i + 1) / segs
            pts = [P(i, k), P(i + 1, k), P(i + 1, k + 1), P(i, k + 1)]
            uvs = [(ua, va), (ub, va), (ub, vb), (ua, vb)]
            if prof[k][0] < 1e-6:                       # полюс — треугольник
                pts, uvs = pts[1:], uvs[1:]
            elif prof[k + 1][0] < 1e-6:
                pts, uvs = pts[:3], uvs[:3]
            if flip:
                pts, uvs = pts[::-1], uvs[::-1]
            b.poly(pts, uvs, m)


def disc(b, r, z, m, rect, segs=16, down=False, wob=None):
    """Плоский круг; текстура — круглым «штампом» в rect. wob(a) — множитель радиуса (неровный край лужицы)."""
    u0, v0, u1, v1 = rect
    angs = [2 * math.pi * i / segs for i in range(segs)]
    if down:
        angs = angs[::-1]
    pts, uvs = [], []
    for a in angs:
        rr = r * (wob(a) if wob else 1.0)
        pts.append((rr * math.cos(a), rr * math.sin(a), z))
        uvs.append((u0 + (u1 - u0) * (0.5 + 0.5 * math.cos(a) * rr / r), v0 + (v1 - v0) * (0.5 + 0.5 * math.sin(a) * rr / r)))
    b.poly(pts, uvs, m)


def sweep(b, path, rx, ry, m, rect, segs=6):
    """Труба эллиптического сечения rx x ry вдоль ломаной path (ручка кружки). Сечение: rx — в плоскости
    изгиба, ry — поперёк (ось Y)."""
    path = [Vector(p) for p in path]
    rings = []
    for k, p in enumerate(path):
        t = (path[min(k + 1, len(path) - 1)] - path[max(k - 1, 0)]).normalized()
        side = Vector((0, 1, 0))
        nrm = side.cross(t).normalized()
        rings.append([p + nrm * (rx * math.cos(2 * math.pi * i / segs)) + side * (ry * math.sin(2 * math.pi * i / segs))
                      for i in range(segs)])
    u0, v0, u1, v1 = rect
    for k in range(len(rings) - 1):
        for i in range(segs):
            j = (i + 1) % segs
            b.poly([rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i]],
                   [(u0 + (u1 - u0) * i / segs, v0), (u0 + (u1 - u0) * (i + 1) / segs, v0),
                    (u0 + (u1 - u0) * (i + 1) / segs, v1), (u0 + (u1 - u0) * i / segs, v1)], m)


# =====================================================================================
#  Предметы
# =====================================================================================
def bottle(M, item, prof, label, label_rect, cap, cap_rect, capt_rect, segs=16):
    """Бутылка: прозрачный корпус с лепестковым дном, этикетка (непрозрачная полоса чуть шире корпуса),
    кольцо горлышка, рифлёная крышка. prof — корпус [(r, z)]; label = (r, z0, z1); cap = (r, z0, z1)."""
    glass, body = Mesh(), Mesh()
    foot = prof[3][1]                                                   # лепестки — до этой высоты
    petals = lambda a, z: 1.0 - 0.13 * max(0.0, 1 - z / foot) * (0.5 + 0.5 * math.cos(5 * a))
    lathe(glass, prof, M["clear"], UV("clear"), segs, rfun=petals)
    lr, lz0, lz1 = label
    lathe(body, [(lr, lz0), (lr, lz1)], M["atlas"], label_rect, segs)
    nr, nz = prof[-1]
    cr, cz0, cz1 = cap
    lathe(body, [(nr, nz), (cr + 0.003, nz), (cr + 0.003, nz + 0.003), (nr, nz + 0.003)], M["atlas"], UV("ring"), segs)
    lathe(body, [(cr, cz0), (cr, cz1), (cr * 0.92, cz1 + 0.0015)], M["atlas"], cap_rect, segs)
    disc(body, cr * 0.92, cz1 + 0.0015, M["atlas"], capt_rect, segs)
    camel = "".join(w.capitalize() for w in item.split("_"))
    return {camel + "_nocol": body, camel + "Glass_nocol": glass}


def bottles(M):
    out = {}
    # «Моршинська» 1,5 л: 33 см, Ø 8,8 см; талия-хват посередине, этикетка под плечом
    out["desk_bottle_tall"] = bottle(M, "desk_bottle_tall",
        [(0.0, 0.004), (0.022, 0.0), (0.037, 0.003), (0.043, 0.014), (0.044, 0.028), (0.044, 0.085),
         (0.0405, 0.098), (0.039, 0.112), (0.0405, 0.126), (0.039, 0.140), (0.0405, 0.152), (0.044, 0.166),
         (0.044, 0.258), (0.042, 0.272), (0.036, 0.288), (0.026, 0.302), (0.017, 0.312), (0.0145, 0.318)],
        (0.0447, 0.196, 0.258), UV("m_label"), (0.0155, 0.321, 0.341), UV("cap_g"), UV("capt_g"))
    # «Миргородська» 0,5 л: 21 см, Ø 6,2 см
    out["desk_bottle_short"] = bottle(M, "desk_bottle_short",
        [(0.0, 0.003), (0.016, 0.0), (0.027, 0.003), (0.0305, 0.011), (0.031, 0.02), (0.031, 0.062),
         (0.0292, 0.070), (0.031, 0.078), (0.031, 0.146), (0.029, 0.160), (0.023, 0.177), (0.016, 0.188), (0.0135, 0.194)],
        (0.0315, 0.086, 0.140), UV("y_label"), (0.0148, 0.197, 0.214), UV("cap_b"), UV("capt_b"))
    return out


def mug(M):
    """Белая кружка «MAYSKIY» (с фото) 300 мл: Ø 8,4 см, высота 9,8 см, чай допит до половины, внутри налёт;
    ручка повёрнута к дивану."""
    b = Mesh()
    a0 = math.radians(-60)                                              # направление ручки
    R, H = 0.042, 0.098
    lathe(b, [(0.0, 0.0015), (0.033, 0.0015), (0.036, 0.0), (0.039, 0.004), (0.041, 0.014), (R, H - 0.004)],
          M["atlas"], UV("mug_out"), 20, a0=a0)
    lathe(b, [(R, H - 0.004), (R, H), (0.0385, H)], M["atlas"], UV("mug_in"), 20, a0=a0)                    # ободок
    lathe(b, [(0.0365, 0.048), (0.0385, H)], M["atlas"], UV("mug_in"), 20, a0=a0, flip=True)                # стенка изнутри
    disc(b, 0.0365, 0.048, M["atlas"], UV("tea"), 20)                                                        # чай
    # ручка: «С» из 9 точек, сечение 6 x 9 мм
    path = []
    for k in range(9):
        t = k / 8
        ang = math.pi * (0.5 - t)                                       # от верха к низу по дуге
        path.append((R - 0.003 + 0.024 * math.cos(ang) * (1.0 if 0 < k < 8 else 0.0), 0.0, 0.050 + 0.030 * math.sin(ang)))
    path[0] = (R - 0.004, 0.0, 0.082); path[-1] = (R - 0.004, 0.0, 0.020)
    hb = Mesh()
    sweep(hb, path, 0.0045, 0.0060, M["atlas"], UV("handle"), 8)
    rot = Matrix.Rotation(a0, 4, 'Z')
    for i, p in enumerate(hb.v):
        hb.v[i] = tuple(rot @ Vector(p))
    for f, uv, mi in zip(hb.f, hb.uv, hb.mi):
        b.poly([hb.v[j] for j in f], uv, hb.mats[mi])
    return {"Mug_nocol": b}


def bowl(M):
    """Белая миска с синей каймой, на дне остатки борща, в миске ложка (ручка лежит на краю)."""
    b, sp = Mesh(), Mesh()
    off = Vector((-0.025, 0.031, 0.0))                                 # центр миски от точки опоры (Blender XY)
    outer = [(0.0, 0.004), (0.027, 0.004), (0.029, 0.0), (0.033, 0.0), (0.036, 0.007), (0.050, 0.021),
             (0.063, 0.038), (0.071, 0.052), (0.074, 0.059)]
    inner = [(0.074, 0.059), (0.070, 0.060), (0.067, 0.049), (0.058, 0.033), (0.045, 0.021), (0.030, 0.014), (0.0, 0.012)]
    lathe(b, outer, M["atlas"], UV("bowl_out"), 24)       # v: край — сверху картинки
    lathe(b, inner, M["atlas"], (lambda u: (u[0], u[3], u[2], u[1]))(UV("bowl_in")), 24)
    # лужица борща: тонкий слой, лежит по дну миски (края приподняты вслед за стенкой, сквозь неё не протыкают)
    def inner_z(r):
        pr = inner[::-1]                                              # от центра к краю
        for (r0, z0), (r1, z1) in zip(pr, pr[1:]):
            if r <= r1:
                return z0 + (z1 - z0) * (r - r0) / (r1 - r0)
        return pr[-1][1]
    su = UV("soup", pad=4)
    wob = lambda a: 1.0 + 0.10 * math.sin(3 * a + 1) + 0.06 * math.sin(7 * a)
    n, R0 = 20, 0.029
    suv = lambda x, y: (su[0] + (su[2] - su[0]) * (0.5 + x / (2.4 * R0)), su[1] + (su[3] - su[1]) * (0.5 + y / (2.4 * R0)))
    ring = []
    for i in range(n):
        a = 2 * math.pi * i / n
        rr = R0 * wob(a)
        ring.append((rr * math.cos(a), rr * math.sin(a), inner_z(rr) + 0.0012))
    mid = [(x * 0.5, y * 0.5, inner_z(math.hypot(x, y) * 0.5) + 0.0035) for (x, y, _) in ring]
    cz = (0.0, 0.0, inner_z(0.0) + 0.0040)
    for i in range(n):
        j = (i + 1) % n
        b.poly([ring[i], ring[j], mid[j], mid[i]], [suv(*ring[i][:2]), suv(*ring[j][:2]), suv(*mid[j][:2]), suv(*mid[i][:2])], M["atlas"])
        b.poly([mid[i], mid[j], cz], [suv(*mid[i][:2]), suv(*mid[j][:2]), suv(0, 0)], M["atlas"])
    # ложка: черпало (эллипс с углублением) + ручка, изгиб вверх у шейки
    st = UV("steel")
    n = 14
    rim = [(0.026 * math.cos(2 * math.pi * i / n), 0.017 * math.sin(2 * math.pi * i / n), 0.0) for i in range(n)]
    mid = [(x * 0.55, y * 0.55, -0.0035) for (x, y, _) in rim]
    cen = (0.0, 0.0, -0.005)
    cl = lambda t: min(0.9, max(0.1, t))                               # не вылезать из куска «steel» (рядом — борщ)
    suv = lambda p: (st[0] + (st[2] - st[0]) * cl(0.5 + p[0] / 0.06), st[1] + (st[3] - st[1]) * cl(0.5 + p[1] / 0.04))
    for i in range(n):
        j = (i + 1) % n
        sp.poly([rim[i], rim[j], mid[j], mid[i]], [suv(rim[i]), suv(rim[j]), suv(mid[j]), suv(mid[i])], M["steel"])
        sp.poly([mid[i], mid[j], cen], [suv(mid[i]), suv(mid[j]), suv(cen)], M["steel"])
    hp = [(0.024, 0.0, 0.001), (0.040, 0.0, 0.006), (0.080, 0.0, 0.008), (0.125, 0.0, 0.010), (0.150, 0.0, 0.011)]
    hw = [0.0035, 0.0028, 0.0045, 0.0065, 0.0060]
    for k in range(len(hp) - 1):
        (x0, _, z0), (x1, _, z1), w0, w1 = hp[k], hp[k + 1], hw[k], hw[k + 1]
        q = [(x0, -w0, z0), (x1, -w1, z1), (x1, w1, z1), (x0, w0, z0)]
        sp.poly(q, [(st[0] + (st[2] - st[0]) * (0.3 + 0.4 * (p[1] / w + 1) / 2), st[1] + (st[3] - st[1]) * (0.1 + 0.8 * p[0] / 0.15))
                    for p, w in zip(q, (w0, w1, w1, w0))], M["steel"])
    # укладка: черпало на борще, ручка через край миски
    pitch = math.atan2(0.062 - 0.027, 0.088)
    xf = (Matrix.Translation(off + Vector((-0.012, 0.0, 0.027))) @ Matrix.Rotation(math.radians(-55), 4, 'Z')
          @ Matrix.Rotation(-pitch, 4, 'Y'))
    sp.v = [tuple(xf @ Vector(p)) for p in sp.v]
    b.v = [tuple(Vector(p) + off) for p in b.v]
    return {"Bowl_nocol": b, "BowlSpoon_nocol": sp}


def build_items(M):
    items = {}
    items.update(bottles(M))
    items["mug"] = mug(M)
    items["bowl"] = bowl(M)
    return items


# =====================================================================================
def material(name, alpha=False, cull=True, rough=0.5):
    m = bpy.data.materials.get(name)
    if m:
        bpy.data.materials.remove(m)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = rough
    img = bpy.data.images.load(os.path.join(TEX, "dc_atlas.png"), check_existing=True)
    img.reload()
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = img
    nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
    if alpha:
        nt.links.new(t.outputs["Alpha"], bsdf.inputs["Alpha"])
        m.surface_render_method = 'BLENDED'
    m.use_backface_culling = cull
    return m


def export_items(items, coll):
    lpath = os.path.join(ITEM_DIR, "layout.json")
    with open(lpath, encoding="utf-8") as f:
        layout = json.load(f)
    tris = {}
    for item, parts in items.items():
        sub_ = bpy.data.collections.new("dc_" + item)
        coll.children.link(sub_)
        obs = [mb.build(nm, sub_) for nm, mb in parts.items()]
        for o in bpy.data.objects:
            try:
                o.select_set(o in obs)
            except RuntimeError:
                pass
        bpy.context.view_layer.objects.active = obs[0]
        bpy.ops.export_scene.gltf(filepath=os.path.join(ITEM_DIR, item + ".gltf"), use_selection=True,
                                  export_keep_originals=True, export_format='GLTF_SEPARATE', export_apply=True,
                                  export_yup=True, use_active_scene=True)
        gx, gy, gz = ANCHOR[item]
        for ob in obs:                                    # в Blender — на своём месте в комнате
            ob.location = Vector((gx, -gz, gy))
        tris[item] = sum(sum(len(p.vertices) - 2 for p in ob.data.polygons) for ob in obs)
        layout[item] = [gx, gy, gz]
    with open(lpath, "w", encoding="utf-8", newline="\n") as f:
        json.dump(layout, f, ensure_ascii=False, indent=1)
    return tris


def main():
    sc = bpy.data.scenes.get(SCENE) or bpy.data.scenes.new(SCENE)
    bpy.context.window.scene = sc
    old = bpy.data.collections.get("DeskClutter")
    if old:
        for c in [old] + list(old.children_recursive):
            for ob in list(c.objects):
                bpy.data.objects.remove(ob, do_unlink=True)
        for c in list(old.children_recursive) + [old]:
            bpy.data.collections.remove(c)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)
    coll = bpy.data.collections.new("DeskClutter")
    sc.collection.children.link(coll)
    M = {
        "atlas": material("DcAtlas", rough=0.35),
        "steel": material("DcSteel", cull=False, rough=0.25),
        "clear": material("DcClear", alpha=True, rough=0.15),
    }
    tris = export_items(build_items(M), coll)
    res = {"tris": tris}
    print("BUILD_DESK_CLUTTER " + json.dumps(res))
    return res


if __name__ == "__main__":
    result = main()
