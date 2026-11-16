# -*- coding: utf-8 -*-
# Левая рука Юрчика, которая держит телефон — по фото «рука в чёрной вязаной перчатке без пальцев».
#   * ладонь за спинкой телефона, четыре пальца обхватывают левый край и лежат подушечками на лице
#     (указательный — на уровне левой софт-клавиши, мизинец — у нижнего края);
#   * большой палец идёт вдоль правого края, кончик заходит на лицо у нижнего края экрана;
#   * перчатка закрывает ладонь и основные фаланги (обрезана сразу за средним суставом, с валиком-манжетой),
#     дальше голая кожа с ногтями; запястье в перчатке, потом серый вязаный рукав, уходящий вниз-вправо к камере.
#
# Запуск (Blender 5.2, из корня проекта):
#   blender -b --factory-startup --python tools/blender/build_phone_hand.py
# Результат: assets/textures/hand_skin.png, hand_knit.png, hand_sleeve.png; assets/models/phone_hand.gltf
#   (объект PhoneHand_nocol). Координаты — те же, что у телефона (build_phone.py): мм, u вправо, v вверх,
#   w к зрителю, начало — центр телефона. В phone.gd рука — дочерний узел телефона, ничего двигать не нужно.
#
# Каждая часть — «лофт»: цепочка сечений-суперэллипсов вдоль гладкого пути (Катмулл-Ром через суставы).
import bpy, bmesh, os, sys, math
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else r"C:\Users\mrs\Documents\yuranchik_game\tools\blender"
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
from tex_lib import save, TEX_DIR
from ps2_style import noise

OUT = os.path.join(ROOT, "assets", "models")
MM = 0.001
R = np.random.default_rng(1207)
KNIT_TILE = 24.0        # мм на повтор текстуры перчатки
SLEEVE_TILE = 40.0

# ---- пальцы: суставы (u, v, w) в мм; радиусы в суставах; центр «обхвата» для направления тыльной стороны
FINGERS = {
    #          начало в ладони      MCP               PIP              DIP              кончик
    "index":  ([(-2, -7, -24), (-15, -6, -24), (-37, -4, 1), (-25, -2, 14.0), (-10, -1, 13.0)], [8.6, 8.4, 7.8, 6.9, 6.2]),
    "middle": ([(-2, -24, -24), (-15, -23, -24), (-38, -22, 1), (-25, -21, 14.3), (-8, -21, 13.2)], [8.8, 8.6, 8.0, 7.1, 6.4]),
    "ring":   ([(-2, -40, -24), (-15, -39, -24), (-37, -39, 1), (-25, -39, 14.0), (-10, -40, 13.0)], [8.4, 8.2, 7.6, 6.7, 6.0]),
    "pinky":  ([(-2, -55, -23), (-14, -54, -23), (-33, -56, -1), (-24, -57, 11.5), (-13, -58, 12.0)], [7.4, 7.1, 6.5, 5.8, 5.2]),
}
FINGER_C = Vector((-26.0, 0.0, 2.0))           # ось обхвата (вдоль v) — тыл пальцев смотрит от неё
THUMB = ([(8, -60, -26), (24, -62, -20), (37, -38, -9), (38, -11, 4), (26, 8, 12.5)], [14.0, 12.0, 9.8, 8.6, 7.6])
THUMB_C = Vector((20.0, 0.0, -12.0))
PALM = [  # центр, полуширина (вдоль v), полутолщина (вдоль w), степень суперэллипса
    ((-22, -31, -22), 37.0, 11.5, 2.8),
    ((-4, -32, -22), 38.0, 13.0, 2.8),
    ((16, -40, -21), 36.0, 14.0, 2.6),
    ((34, -55, -17), 29.0, 14.0, 2.4),
    ((50, -73, -10), 27.0, 18.0, 2.1),
    ((72, -103, 2), 28.0, 23.0, 2.0),
    ((104, -150, 20), 33.0, 29.0, 2.0),
    ((140, -205, 40), 36.0, 32.0, 2.0),
]
CUFF_S = 75.0           # от начала ладони до края перчатки на запястье (дальше рукав)
SEGS = 16


# =============================================================================== текстуры
def knit(w, h, base, hi, cols, rows, fuzz=0.25):
    """Вязка «косичками»: в каждой петле две наклонные дольки (V), между столбиками тёмная бороздка."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cw, ch = w / cols, h / rows
    fx = (xx % cw) / cw - 0.5                      # -0.5..0.5 поперёк столбика
    fy = (yy % ch) / ch                            # 0..1 вдоль петли
    arm = np.abs(fx) - (0.10 + 0.28 * fy)
    lobe = np.exp(-(arm / 0.13) ** 2) * np.sin(np.pi * np.clip(fy, 0, 1)) ** 0.6
    groove = np.exp(-((np.abs(fx) - 0.5) / 0.06) ** 2)
    n = noise(w, h, 8, 8, R, oct=3)
    t = np.clip(lobe * (0.75 + 0.5 * n) - 0.5 * groove, 0, 1)
    a = np.ones((h, w, 3), np.float32) * np.array(base, np.float32)
    a += (np.array(hi, np.float32) - np.array(base, np.float32)) * t[..., None]
    a *= (1 - fuzz / 2 + fuzz * R.random((h, w)).astype(np.float32))[..., None]       # ворс
    return a


def tex_skin():
    """Кожа пальцев: u — вокруг пальца (0.5 = тыл), v — от края перчатки (0) к кончику (1).
    Ноготь на тыльной стороне последней фаланги, складка-морщинки на среднем суставе."""
    w = h = 256
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u, v = xx / w, yy / h
    base = np.array((0.80, 0.56, 0.46), np.float32)
    a = np.ones((h, w, 3), np.float32) * base
    a *= (0.9 + 0.2 * noise(w, h, 6, 6, R, oct=3))[..., None]
    dorsal = np.exp(-((u - 0.5) / 0.22) ** 2)
    a *= (0.97 - 0.07 * (1 - dorsal))[..., None]                                     # подушечки чуть темнее
    red = np.exp(-((v - 0.05) / 0.07) ** 2) + 0.6 * np.exp(-((v - 0.45) / 0.05) ** 2)  # покрасневшие суставы
    a += (np.array((0.06, -0.03, -0.03), np.float32) * (red * dorsal)[..., None])
    for k in range(3):                                                               # морщинки на DIP
        line = np.exp(-((v - (0.41 + 0.035 * k)) / 0.005) ** 2) * dorsal
        a *= (1 - 0.18 * line)[..., None]
    du, dv = (u - 0.5) / 0.115, (v - 0.80) / 0.17
    nail = smooth_box(du, dv, 4.0)
    nail_col = np.array((0.88, 0.70, 0.66), np.float32) * (0.95 + 0.1 * noise(w, h, 4, 16, R, oct=2))[..., None]
    a = a * (1 - nail[..., None]) + nail_col * nail[..., None]
    tip = nail * np.clip((v - 0.93) / 0.03, 0, 1)                                    # светлый свободный край
    a = a * (1 - tip[..., None]) + np.array((0.93, 0.88, 0.82), np.float32) * tip[..., None]
    rim = np.clip(smooth_box(du * 1.12, dv * 1.06, 4.0) - nail, 0, 1)                 # тень валика вокруг ногтя
    a *= (1 - 0.35 * rim)[..., None]
    return a


def smooth_box(x, y, p):
    return np.clip(1.0 - (np.abs(x) ** p + np.abs(y) ** p), 0, 1) ** 0.3


def textures():
    save("hand_knit", knit(128, 128, (0.035, 0.035, 0.038), (0.16, 0.16, 0.17), 8, 11))
    save("hand_sleeve", knit(128, 128, (0.32, 0.32, 0.33), (0.52, 0.52, 0.53), 8, 11, fuzz=0.25))
    save("hand_skin", tex_skin())


def material(name, tex, rough):
    m = bpy.data.materials.get(name)
    if m:
        bpy.data.materials.remove(m)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = rough
    img = bpy.data.images.load(os.path.join(TEX_DIR, tex + ".png"), check_existing=True)
    img.reload()
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = img
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    return m


# =============================================================================== геометрия
def P(p):
    u, v, w = p
    return Vector((u * MM, -w * MM, v * MM))


def catmull(pts, n):
    """Гладкий путь через точки: n отсчётов на отрезок."""
    pts = [Vector(p) for p in pts]
    ext = [pts[0] * 2 - pts[1]] + pts + [pts[-1] * 2 - pts[-2]]
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for k in range(n):
            t = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(pts[-1])
    return out


def interp(arr_s, arr_v, s):
    return float(np.interp(s, arr_s, arr_v))


def superellipse(a, b, n, th):
    c, s = math.cos(th), math.sin(th)
    return a * math.copysign(abs(c) ** (2 / n), c), b * math.copysign(abs(s) ** (2 / n), s)


class Loft:
    def __init__(self, bm, uv):
        self.bm, self.uv = bm, uv

    def run(self, rings, mat_of, uv_of, cap0=True, cap1=True):
        """rings: [(s, [точки])]; mat_of(s0, s1) — материал полосы; uv_of(s, i, mat) — UV."""
        bm, uvl = self.bm, self.uv
        verts = [[bm.verts.new(P(p)) for p in pts] for _, pts in rings]
        n = len(rings[0][1])
        for k in range(len(rings) - 1):
            s0, s1 = rings[k][0], rings[k + 1][0]
            m = mat_of(s0, s1)
            for i in range(n):
                j = (i + 1) % n
                f = bm.faces.new((verts[k][i], verts[k][j], verts[k + 1][j], verts[k + 1][i]))
                f.material_index = m
                for lp, (kk, ii, jj) in zip(f.loops, ((k, i, i), (k, j, i + 1), (k + 1, j, i + 1), (k + 1, i, i))):
                    lp[uvl].uv = uv_of(rings[kk][0], jj, m)
                f.smooth = True
        for end, k in ((cap0, 0), (cap1, len(rings) - 1)):
            if not end:
                continue
            ring = verts[k] if k else verts[k][::-1]
            c = bm.verts.new(sum((v.co for v in ring), Vector()) / len(ring))
            m = mat_of(rings[k][0], rings[k][0])
            for i in range(n):
                j = (i + 1) % n
                f = bm.faces.new((ring[i], ring[j], c))
                f.material_index = m
                f.smooth = True
                for lp in f.loops:
                    lp[uvl].uv = uv_of(rings[k][0], 0, m)
        bmesh.ops.recalc_face_normals(bm, faces=[f for f in bm.faces if not f.tag])
        for f in bm.faces:
            f.tag = True


SKIN, GLOVE, SLEEVE = 0, 1, 2


def digit(lf, joints, radii, center, cut_joint, cut_off, n=8):
    """Палец: путь через суставы, кончик скруглён полусферой, до края перчатки — вязка, дальше кожа."""
    path = catmull(joints, n)
    s = [0.0]
    for a, b in zip(path, path[1:]):
        s.append(s[-1] + (b - a).length)
    js = [0.0]
    for a, b in zip(joints, joints[1:]):
        js.append(js[-1] + (Vector(b) - Vector(a)).length)
    js = np.array(js) * (s[-1] / js[-1])
    L = s[-1]
    cut = js[cut_joint] + cut_off
    r_tip = radii[-1]
    # отсчёты по длине: путь + сгущение у края перчатки и на кончике
    samples = sorted(set([round(x, 3) for x in s if x < L - r_tip] +
                         [cut - 2.5, cut - 1.2, cut - 0.01, cut] +
                         [L - r_tip * (1 - math.sin(math.pi / 2 * k / 5)) for k in range(6)]))
    samples = [x for x in samples if 0 <= x <= L]
    sv = np.array(s)
    pts = np.array([tuple(p) for p in path])
    rings = []
    for x in samples:
        p = Vector([np.interp(x, sv, pts[:, i]) for i in range(3)])
        x2 = min(x + 0.5, L); x1 = max(x - 0.5, 0)
        T = (Vector([np.interp(x2, sv, pts[:, i]) for i in range(3)]) -
             Vector([np.interp(x1, sv, pts[:, i]) for i in range(3)])).normalized()
        D = p - Vector((center.x, p.y, center.z)) if center is not None else Vector((0, 0, 1))
        D = (D - T * D.dot(T)).normalized()
        Y = T.cross(D)
        r = interp(js, radii, x)
        if x > L - r_tip:                                   # полусфера кончика
            r = r_tip * math.sqrt(max(0.0, 1 - ((x - (L - r_tip)) / r_tip) ** 2))
            r = max(r, 0.15)
        if cut - 2.6 <= x <= cut:                            # валик на краю перчатки
            r += 1.1
        elif x < cut:
            r += 0.5                                         # толщина вязки
        ring = []
        for i in range(SEGS):
            th = 2 * math.pi * i / SEGS
            a, b = superellipse(r * 0.92, r, 2.3, th)        # чуть приплюснут: тыл-ладонь (b) толще ширины (a)
            q = p + D * b + Y * a
            q = q - D * r * 0.15 * max(0.0, -math.cos(th)) ** 2   # подушечка приплюснута
            ring.append(tuple(q))
        rings.append((x, ring))

    circ = 2 * math.pi * radii[1]

    def mat_of(s0, s1):
        return GLOVE if (s0 + s1) / 2 < cut else SKIN

    def uv_of(x, i, m):
        a = i / SEGS                                         # 0..1 вокруг пальца, тыл — на 0.5
        if m == GLOVE:
            return (a * circ / KNIT_TILE, x / KNIT_TILE)
        return (a, 1 - (x - cut) / (L - cut))
    # тыл (th=0) должен быть в середине текстуры кожи: сдвигаем отсчёт угла на половину оборота
    lf.run([(x, ring[SEGS // 2:] + ring[:SEGS // 2]) for x, ring in rings], mat_of, uv_of, cap0=True, cap1=True)


def palm(lf):
    rings = []
    s = 0.0
    prev = None
    cen = [Vector(c) for c, *_ in PALM]
    for k, (c, hw, ht, n) in enumerate(PALM):
        c = Vector(c)
        if prev is not None:
            s += (c - prev).length
        prev = c
        T = (cen[min(k + 1, len(cen) - 1)] - cen[max(k - 1, 0)]).normalized()
        D = Vector((0, 0, 1)) if k < 3 else Vector((0.35, 0.25, 1)).normalized()
        D = (D - T * D.dot(T)).normalized()
        Y = T.cross(D)
        extra = 0.0
        ring = []
        for i in range(SEGS * 2):
            th = 2 * math.pi * i / (SEGS * 2)
            a, b = superellipse(hw, ht, n, th)
            ring.append(tuple(c + Y * a + D * b))
        rings.append((s, ring))
    # край перчатки на запястье: два кольца — вязка и валик рукава
    out = []
    for k in range(len(rings) - 1):
        out.append(rings[k])
        s0, s1 = rings[k][0], rings[k + 1][0]
        if s0 < CUFF_S < s1:
            t = (CUFF_S - s0) / (s1 - s0)
            r0, r1 = rings[k][1], rings[k + 1][1]
            mid = [tuple(Vector(a).lerp(Vector(b), t)) for a, b in zip(r0, r1)]
            c = sum((Vector(p) for p in mid), Vector()) / len(mid)
            out.append((CUFF_S - 0.01, mid))
            out.append((CUFF_S, [tuple(c + (Vector(p) - c) * 1.12) for p in mid]))   # рукав шире перчатки
    out.append(rings[-1])
    per = 2 * math.pi * 30

    def mat_of(s0, s1):
        return GLOVE if (s0 + s1) / 2 < CUFF_S else SLEEVE

    def uv_of(x, i, m):
        tile = KNIT_TILE if m == GLOVE else SLEEVE_TILE
        return (i / (SEGS * 2) * per / tile, x / tile)
    lf.run(out, mat_of, uv_of, cap0=True, cap1=True)


def build():
    textures()
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    lf = Loft(bm, uv)
    palm(lf)
    for name, (joints, radii) in FINGERS.items():
        digit(lf, joints, [r * 0.9 for r in radii], FINGER_C, 2, 3.0)
    digit(lf, THUMB[0], THUMB[1], THUMB_C, 3, -4.0)
    me = bpy.data.meshes.new("PhoneHand")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(material("HandSkin", "hand_skin", 0.6))
    me.materials.append(material("HandGlove", "hand_knit", 0.95))
    me.materials.append(material("HandSleeve", "hand_sleeve", 0.95))
    return me


def main():
    if bpy.context.window:
        sc = bpy.data.scenes.get("PhoneHand") or bpy.data.scenes.new("PhoneHand")
        bpy.context.window.scene = sc
    else:
        sc = bpy.context.scene
    for ob in list(sc.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    me = build()
    ob = bpy.data.objects.new("PhoneHand_nocol", me)
    sc.collection.objects.link(ob)
    bpy.context.view_layer.update()
    for o in sc.objects:
        o.select_set(o == ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "phone_hand.gltf"), use_selection=True, use_active_scene=True,
                              export_format='GLTF_SEPARATE', export_apply=True, export_yup=True)
    return {"tris": sum(len(p.vertices) - 2 for p in me.polygons)}


if __name__ == "__main__" or "NO_MAIN" not in globals():
    RESULT = main()
    print("BUILD_PHONE_HAND", RESULT)
